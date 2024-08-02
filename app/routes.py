import base64
import csv
import io
import os
import pathlib
import zipfile

import cv2
import numpy as np
import requests
from flask import render_template, redirect, url_for, request, jsonify, flash
from flask import send_file
from pyzbar.pyzbar import decode
from werkzeug.utils import secure_filename

from app import app
from app.book_apis import get_book_info
from app.csv_utils import read_books, add_book, get_next_id, delete_book, get_map_books, save_books
from app.forms import BookForm, BulkEditLocationForm


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
def edit_book(book_id):
    books = read_books()
    book = next((b for b in books if int(b['id']) == book_id), None)
    if not book:
        flash('Book not found', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        thumbnail = ''
        # Handle file upload
        if 'new_thumbnail' in request.files:
            new_thumbnail = request.files['new_thumbnail']
            if new_thumbnail.filename != '':
                ext = pathlib.Path(new_thumbnail.filename).suffix
                filename = secure_filename(f"{book['isbn']}{ext}")
                new_thumbnail.save(os.path.join('app/static/thumbnails', filename))
                thumbnail = f'thumbnails/{filename}'
        else:
            thumbnail = book.get('thumbnail', '')

        book.update({
            'title': request.form['title'],
            'author': request.form['author'],
            'isbn': request.form['isbn'],
            'location': request.form['location'],
            'thumbnail': thumbnail
        })
        # Save changes to the database
        save_books(books)
        flash('Book updated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('edit_book.html', book=book)


@app.route('/add_book', methods=['GET', 'POST'])
def add_book_view():
    form = BookForm()
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        location = request.form['location']

        if 'captured_thumbnail' in request.form:
            captured_thumbnail = request.form['captured_thumbnail']
            ext = '.jpg'
            filename = secure_filename(f"{isbn}{ext}")
            thumbnail_data = base64.b64decode(captured_thumbnail.split(',')[1])
            with open(filename, 'wb') as f:
                f.write(thumbnail_data)
            thumbnail = f'thumbnails/{filename}'
        elif 'new_thumbnail' in request.files:
            new_thumbnail = request.files['new_thumbnail']
            if new_thumbnail.filename != '':
                ext = pathlib.Path(new_thumbnail.filename).suffix
                filename = secure_filename(f"{isbn}{ext}")
                new_thumbnail.save(os.path.join('app/static/thumbnails', filename))
                thumbnail = f'thumbnails/{filename}'
        else:
            thumbnail = None

        book = {
            'title': title,
            'author': author,
            'isbn': isbn,
            'location': location,
            'thumbnail': thumbnail
        }
        add_book(book)
        return redirect(url_for('index'))

    return render_template('add_book.html', form=form)


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
        save_books(books)
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
