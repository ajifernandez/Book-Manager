import csv
import threading

import cv2
import requests
from flask import render_template, redirect, url_for, request
from pyzbar.pyzbar import decode

from app import app
from app.csv_utils import read_books, add_book, get_next_id, delete_book, get_map_books, update_book
from app.forms import BookForm

camera_running = True


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
            location = book_data.get('location', 'Unknown location')

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


def camera_thread():
    global camera_running
    cap = cv2.VideoCapture(0)
    # if not cap.isOpened():
    #     print("No se pudo acceder a la cámara.")
    #     return

    while camera_running:
        ret, frame = cap.read()
        # if not ret:
        #     break

        decoded_objects = decode(frame)
        for obj in decoded_objects:
            barcode_data = obj.data.decode('utf-8')

            book_map = get_map_books()
            if barcode_data in book_map:
                print(f"El libro con ISBN {barcode_data} ya está en la lista.")
            else:
                title, authors, thumbnail, location = get_book_info(barcode_data)
                if title and authors:
                    book = {
                        'id': get_next_id(),
                        'title': title,
                        'author': authors,
                        'isbn': barcode_data,
                        'thumbnail': save_thumbnail(thumbnail, barcode_data) if barcode_data else '',
                        'location': location
                    }
                    add_book(book)
                else:
                    # No se encontró información del libro, sigue capturando
                    print("No se encontró información del libro.")

        cv2.imshow('Barcode Scanner', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            camera_running = False

            cap.release()
            cv2.destroyAllWindows()

    cap.release()
    cv2.destroyAllWindows()


@app.route('/scan')
def scan():
    start_camera()
    return redirect(url_for('index'))


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


@app.route('/add', methods=['GET', 'POST'])
def add_book_view():
    isbn = request.args.get('isbn')
    error = request.args.get('error')
    form = BookForm()

    if isbn:
        # Si se pasa un ISBN a través de parámetros, pre-llenar el formulario
        title, author, thumbnail, location = get_book_info(isbn)
        form.isbn.data = isbn
        # form.title.data = title
        # form.author.data = author

        if form.validate_on_submit():
            book = {
                'id': get_next_id(),
                'title': title,
                'author': author,
                'isbn': isbn,
                'thumbnail': save_thumbnail(thumbnail, isbn) if isbn else ''
            }
            add_book(book)
            return redirect(url_for('index'))

    return render_template('add_book.html', form=form, error=error)


@app.route('/delete/<int:book_id>')
def delete_book_view(book_id):
    delete_book(book_id)
    return redirect(url_for('index'))


def start_camera():
    camera_thread_instance = threading.Thread(target=camera_thread)
    camera_thread_instance.start()


@app.route('/search')
def search_books():
    query = request.args.get('query', '').lower()
    books = read_books()
    if query:
        books = [book for book in books if query in book['title'].lower() or query in book['author'].lower()]
    return render_template('index.html', books=books)


# Agregamos al inicio las importaciones necesarias
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired


# Definimos un nuevo formulario para la edición múltiple
class BulkEditLocationForm(FlaskForm):
    location = StringField('New Location', validators=[DataRequired()])
    book_ids = HiddenField()
    submit = SubmitField('Update Locations')


@app.route('/bulk_edit_location', methods=['POST'])
def bulk_edit_location():
    form = BulkEditLocationForm()
    book_ids = request.form.getlist('book_ids')

    if request.method == 'POST' and book_ids:
        book_ids_str = ','.join(book_ids)
        return render_template('bulk_edit_location.html', form=form, book_ids=book_ids_str)

    return redirect(url_for('index'))


@app.route('/update_bulk_location', methods=['POST'])
def update_bulk_location():
    form = BulkEditLocationForm()
    if form.validate_on_submit():
        book_ids = form.book_ids.data.split(',')
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


if __name__ == '__main__':
    import os

    SECRET_KEY = os.urandom(32)
    app.config['SECRET_KEY'] = SECRET_KEY

    # start_camera()
    app.run(debug=True)
