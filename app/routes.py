import csv
import io
import os
import threading
import zipfile

import cv2
import requests
from flask import render_template, redirect, url_for, request, jsonify
from flask import send_file
from pyzbar.pyzbar import decode

from app import app
from app.csv_utils import read_books, add_book, get_next_id, delete_book, get_map_books, update_book
from app.forms import BookForm, BulkEditLocationForm

camera_running = True


def start_camera():
    camera_thread_instance = threading.Thread(target=camera_thread)
    camera_thread_instance.start()


def get_book_info(isbn):
    # Intentar obtener información del libro desde Google Books
    google_books_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    response = requests.get(google_books_url)
    title, authors, thumbnail, location = None, None, None, None

    if response.status_code == 200:
        data = response.json()
        print(data)
        if "items" in data:
            book_data = data["items"][0]["volumeInfo"]
            title = book_data.get("title", "Unknown Title")
            authors = ", ".join(book_data.get("authors", []))
            thumbnail = book_data.get("imageLinks", {}).get("thumbnail", "")
            location = app.config.get("DEFAULT_LOCATION")

    # Si falta autor o thumbnail, intentar obtener información del libro desde Open Library
    if not authors or not thumbnail:
        open_library_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        response = requests.get(open_library_url)
        if response.status_code == 200:
            data = response.json()
            print(data)
            key = f"ISBN:{isbn}"
            if key in data:
                book_data = data[key]
                if not title:
                    title = book_data.get("title", "Unknown Title")
                if not authors:
                    authors = ", ".join([author["name"] for author in book_data.get("authors", [])])
                if not thumbnail and "cover" in book_data:
                    thumbnail = book_data["cover"].get("large", "")

    return title, authors, thumbnail, location


def save_thumbnail(thumbnail_url, isbn):
    if thumbnail_url:
        response = requests.get(thumbnail_url)
        if response.status_code == 200:
            os.makedirs('app/static/thumbnails', exist_ok=True)
            thumbnail_path = os.path.join('app/static/thumbnails', f"{isbn}.jpg")
            with open(thumbnail_path, 'wb') as file:
                file.write(response.content)
            return f"thumbnails/{isbn}.jpg"
    return 'no_thumbnail.png'


import base64

import numpy as np


@app.route('/scan_process', methods=['POST'])
def scan_process():
    data_url = request.form['frame']
    header, encoded = data_url.split(",", 1)
    np_img = np.frombuffer(base64.b64decode(encoded), np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    # Verificar el tamaño de la imagen
    # height, width = img.shape[:2]
    # print(f"Image size: {width}x{height}")
    # # Guardar el frame en un archivo
    # timestamp = int(time.time())
    # filename = f'app/static/frames/frame_{timestamp}.png'
    # cv2.imwrite(filename, img, [cv2.IMWRITE_PNG_COMPRESSION, 0])

    try:
        barcodes = decode(img)
        for barcode in barcodes:
            isbn = barcode.data.decode('utf-8')

            book_map = get_map_books()
            if isbn in book_map:
                print(f"El libro con ISBN {isbn} ya está en la lista.")
            else:
                title, authors, thumbnail, location = get_book_info(isbn)
                if title and authors:
                    book = {
                        'id': get_next_id(),
                        'title': title,
                        'author': authors,
                        'isbn': isbn,
                        'thumbnail': save_thumbnail(thumbnail, isbn) if isbn else '',
                        'location': location
                    }
                    add_book(book)
                    return jsonify({'isbn': isbn, 'title': title, 'author': authors, 'thumbnail': thumbnail})
                else:
                    # No se encontró información del libro, sigue capturando
                    print("No se encontró información del libro.")
            return jsonify({'isbn': isbn})
    except Exception as e:
        pass
    return jsonify({'isbn': 'Searching...'})


@app.route('/scan')
def scan():
    return render_template('scan.html')


@app.route('/')
def index():
    books = read_books()
    return render_template('index.html', books=books)


@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book_view(book_id):
    books = read_books()
    book = next((b for b in books if b['id'] == str(book_id)), None)
    if not book:
        return redirect(url_for('index'))

    form = BookForm(data=book)

    if form.validate_on_submit():
        book.update({
            'title': form.title.data,
            'author': form.author.data,
            'isbn': form.isbn.data,
            'location': form.location.data,
            'thumbnail': book.get('thumbnail', '')
        })
        update_book(book)
        return redirect(url_for('index'))

    return render_template('edit_book.html', form=form)


@app.route('/add', methods=['GET', 'POST'])
def add_book_view():
    form = BookForm()
    isbn = request.args.get('isbn') or form.isbn.data
    location = form.location.data
    error = request.args.get('error')

    if isbn:
        # Si se pasa un ISBN a través de parámetros, pre-llenar el formulario
        title, author, thumbnail, _ = get_book_info(isbn)
        # form.isbn.data = isbn
        # form.title.data = title
        # form.author.data = author

        # if form.validate_on_submit():
        book = {
            'id': get_next_id(),
            'title': title,
            'author': author,
            'isbn': isbn,
            'thumbnail': save_thumbnail(thumbnail, isbn) if isbn else '',
            'location': location
        }
        add_book(book)
        return redirect(url_for('index'))

    return render_template('add_book.html', form=form, error=error)


@app.route('/delete/<int:book_id>')
def delete_book_view(book_id):
    books = read_books()
    book_to_delete = next((book for book in books if book['id'] == str(book_id)), None)
    if book_to_delete:
        if book_to_delete.get('thumbnail'):
            thumbnail_path = os.path.join('app/static', book_to_delete['thumbnail'])
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)

        delete_book(book_to_delete)
    return redirect(url_for('index'))


@app.route('/search')
def search_books():
    query = request.args.get('query', '').lower()
    books = read_books()
    if query:
        books = [book for book in books if query in book['title'].lower() or query in book['author'].lower()]
    return render_template('index.html', books=books)


@app.route('/bulk_edit_location', methods=['POST'])
def bulk_edit_location():
    form = BulkEditLocationForm()
    book_ids = request.form.getlist('book_ids[]')
    if book_ids:

        if request.method == 'POST' and book_ids:
            book_ids_str = ','.join(book_ids)
            return render_template('bulk_edit_location.html', form=form, book_ids=book_ids_str)

    return redirect(url_for('index'))


@app.route('/update_bulk_location', methods=['POST'])
def update_bulk_location():
    form = BulkEditLocationForm()
    if form.validate_on_submit():
        book_ids = form.book_ids.raw_data[1].split(',')
        new_location = form.location.data

        books = read_books()
        for book in books:
            if book['id'] in book_ids:
                book['location'] = new_location

        with open('books.csv', 'w', newline='') as csvfile:
            fieldnames = ['id', 'title', 'author', 'isbn', 'thumbnail', 'location']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(books)

        return redirect(url_for('index'))

    return render_template('bulk_edit_location.html', form=form, book_ids=form.book_ids.data)


@app.route('/edit_default_location', methods=['GET', 'POST'])
def edit_default_location():
    if request.method == 'POST':
        new_location = request.form['default_location']
        app.config['DEFAULT_LOCATION'] = new_location
        return redirect(url_for('index'))
    return render_template('edit_default_location.html', default_location=app.config.get('DEFAULT_LOCATION', 'Unknown'))


@app.route('/download_thumbnails')
def download_thumbnails():
    # Obtener todos los libros
    books_map = get_map_books()

    # Crear un buffer de memoria para escribir el archivo ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for book in books_map.values():
            thumbnail_path = book.get('thumbnail')
            if thumbnail_path:
                thumbnail_path = os.path.join('app/static', thumbnail_path)
                if os.path.exists(thumbnail_path):
                    zip_file.write(thumbnail_path, os.path.basename(thumbnail_path))

    # Mover el cursor al principio del buffer
    zip_buffer.seek(0)

    # Enviar el archivo ZIP como respuesta
    return send_file(
        io.BytesIO(zip_buffer.getvalue()),
        download_name='thumbnails.zip',
        as_attachment=True,
        mimetype='application/zip'
    )


@app.route('/download_csv')
def download_csv():
    # Obtener todos los libros
    books_map = get_map_books()

    # Crear un buffer de memoria para escribir el CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Escribir encabezado
    writer.writerow(['ID', 'Thumbnail', 'Title', 'Author', 'ISBN', 'Location'])

    # Escribir datos de libros
    for book in books_map.values():
        writer.writerow(
            [book['id'], book.get('thumbnail', ''), book['title'], book['author'], book['isbn'], book['location']])

    # Mover el cursor al principio del buffer
    output.seek(0)

    # Enviar el archivo CSV como respuesta
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        download_name='books.csv',
        as_attachment=True,
        mimetype='text/csv'
    )
