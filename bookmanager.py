# bookmanager.py

from flask import Flask, render_template, request, redirect, jsonify

import os
import json
import csv
import xml.etree.ElementTree as ET
import pandas as pd
from werkzeug.utils import secure_filename

# Boot up the flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads' # keep original vendor files in this folder

ALLOWED_EXTENSIONS = {'csv', 'xml', 'json', 'xlsx'}

# This is our central storage file, which we will use to store all the books 
# from different vendors/shopkeepers
BOOKS_FILE = 'books.json'


# Initialize books storage
def load_books():
    if os.path.exists(BOOKS_FILE):
        with open(BOOKS_FILE, 'r') as f:
            return json.load(f);
    return [];

# Saving books to the central storage file ---> book.json
def save_books(books):
    with open(BOOKS_FILE, 'w') as f:
        json.dump(books, f, indent=2)


# Checks if a file format is allowed or not
# filename.csv  ----> ["filename", "csv"] ---> "CSV" ---> "csv" --> true/false
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# API ROUTES/API ENDPOINTS
# READ/CREATE
@app.route("/", methods=['GET', 'POST'])
def home():
    # 1. Allow user to add new books
    # 2. Display all the books in the central file storage

    books = load_books()

    # This means new books are getting added
    if request.method == 'POST':
        # Save the book in the books.json file
        new_book = {
            'title': request.form.get('title'),
            'author': request.form.get('author', ''),
            'isbn': request.form.get('isbn', '')
        }

        books.append(new_book)

        save_books(books)

    return render_template('home.html', books = books)


# This route is used to save books in case of file uploads
# HTTP Status codes
# 200 --> OK
# 201 --> OK CREATED
# 2xx --> Positive code


# 400 --> BAD REQUEST CLIENT SIDE
# 401 --> UNAUTHORIZED
# 402 --> FORBIDDEN REQUEST
# 404 --> NOT FOUND
# 4xx --> SOMETHING WRONG ON CLIENT SIDE

# 500 --> INTERNAL SERVER ERROR
# 5xx --> SOMETHING WRONG ON THE SERVER SIDE

# CREATE
# for single entry in the books.json
@app.route("/api/books", methods = ['POST'])
def add_book_json():

    if not request.is_json():
        return jsonify({"error": "Content-Type must be application/json"}), 400

    # book data we are getting
    data = request.get_json()

    # Validate teh JSON Data

    if 'title' not in data:
        return jsonify({"error": "Title is required"}), 400

    # load all the old books
    books = load_books()

    books.append(
        {
            'title': data['title'],
            'author': data.get('author', ''),
            'isbn': data.get('isbn', '')
        }
    )

    save_books(books)

    return jsonify(data), 201

# CREATE
# Upload a file

"""
request = {  
    files: {
        'file' : [file in json format]
    }
    method : GET/POST
 }
"""
#CREATE
@app.route("/upload", methods = ['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided in the request"}), 400

    # process files based on file format
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        file.save(file_path)

        # Process different file formats

        try:
            if filename.endswith('.csv'):
                process_csv(file_path)
            elif filename.endswith('.xml'):
                process_xml(file_path)
            elif filename.endswith('.xslx'):
                process_xslx(file_path)
            elif filename.endswith('.json'):
                process_json(file_path)

            return jsonify({"message": "File processed successfully"}), 200
        
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": str(e)}), 400

    return jsonify({"error": "File type not supported"}), 400


# All the process methods
def process_csv(file_path):
    #load books in books.json
    books = load_books()

    with open(file_path,'r') as file:

        csv_reader = csv.DictReader(file)

        for row in csv_reader:
            # Only process books which have a title, else ignore
            if 'title' in row:
                books.append(
                    {
                        'title': row['title'],
                        'author': row.get('author', ''),
                        'isbn': row.get('isbn', '')
                    }
                )
        
    # SAVE IT
    save_books(books)

def process_xml(file_path):
    books = load_books()

    tree = ET.parse(file_path)

    root = tree.getroot() # What is the root of the tree? ---> BOOKS

    for book_elem in root.findall('book'):
        title_elem = book_elem.findall('title')

        if title_elem is not None:
            books.append({
                'title': title_elem.text,
                'author': book_elem.find('author').text if book_elem.find('author') is not None else '',
                'isbn': book_elem.find('isbn').text if book_elem.find('isbn') is not None else ''
            })
    

    # Last Step?

    save_books(books)

def process_xslx(file_path):

    books = load_books()

    # Very common syntax to read excel/csv in a pandas dataframe
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        if 'title' in row:
            books.append(
                {
                    'title': row['title'],
                    'author': row.get('author', ''),
                    'isbn': row.get('isbn', '')
                }
            )

    save_books(books)

def process_json(file_path):
    books = load_books()

    with open(file_path, 'r') as file:
        data = json.load(file)

        for book_data in data:
            if 'title' in book_data:

                books.append({
                    'title': book_data['title'],
                    'author': book_data.get('author', ''),
                    'isbn': book_data.get('isbn', '')
                })
    save_books(books)



# UPDATE
@app.route("/update", methods = ['POST'])
def update():
    books = load_books()

    oldtitle = request.form.get('oldtitle')

    newtitle = request.form.get('newtitle')

    for book in books:
        if book['title'] == oldtitle:
            book['title'] = newtitle
            break

    save_books(books)

    # reloading the homepage with updated book title
    return redirect("/")


# DELETE
@app.route("/delete", methods = ["POST"])
def delete():
    books = load_books()

    del_title = request.form.get('title')

    books = [book for book in books if book['title'] !=  del_title]
    
    # Another way to do deletion
    # updated_books = []

    # for book in books:
    #     if book['title'] != del_title:

    #         updated_books.append(book)
        
    save_books(books)

    # refresh the homepage reflecting the deleted book
    return redirect("/")



# Start the flask app

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # check for the central storage file ---> books.json
    if not os.path.exists(BOOKS_FILE):
        save_books([])

    app.run(debug=True, port=8080)



