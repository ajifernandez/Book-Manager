import base64
import csv
import io
import os
import zipfile

import cv2
import numpy as np
import requests
from flask import render_template, redirect, url_for, request, jsonify, flash
from flask import send_file
from pyzbar.pyzbar import decode
from werkzeug.utils import secure_filename

from app import app
from app.csv_utils import read_books, add_book, get_next_id, delete_book, get_map_books, save_books
from app.forms import BookForm, BulkEditLocationForm


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
