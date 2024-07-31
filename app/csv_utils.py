import csv
import os

import app


def read_books():
    books = []
    with open('books.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            books.append(row)
    return books


def get_map_books():
    book_map = {}
    try:
        with open('books.csv', mode='r', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                isbn = row['isbn']
                book_map[isbn] = {
                    'id': row['id'],
                    'title': row['title'],
                    'author': row['author'],
                    'thumbnail': row.get('thumbnail', '')
                }
    except FileNotFoundError:
        # Handle the case where the file doesn't exist
        print("No se encontró el archivo books.csv.")
    return book_map


def add_book(book):
    book_map = get_map_books()
    if book['isbn'] in book_map:
        print(f"El libro con ISBN {book['isbn']} ya está en la lista.")
        return False
    fieldnames = ['id', 'title', 'author', 'isbn', 'thumbnail', 'location']
    try:
        with open('books.csv', mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writerow(book)
            print(f"Libro con ISBN {book['isbn']} añadido exitosamente.")
            return True
    except FileNotFoundError:
        # Handle the case where the file doesn't exist
        print("No se encontró el archivo books.csv.")
        return False


def get_next_id():
    books = read_books()
    if books:
        return int(books[-1]['id']) + 1
    return 1


def update_book(updated_book):
    books = read_books()
    for i, book in enumerate(books):
        if book['id'] == updated_book['id']:
            books[i] = updated_book
            break
    with open('books.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'title', 'author', 'isbn', 'thumbnail', 'location']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(books)


def delete_book(book_to_delete):
    books = read_books()
    books = [book for book in books if book['id'] != book_to_delete['id']]
    with open('books.csv', mode='w', newline='') as file:
        fieldnames = ['id', 'title', 'author', 'isbn', 'thumbnail', 'location']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(books)
