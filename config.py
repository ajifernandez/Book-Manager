import os


class Config:
    CSV_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'books.csv')
    THUMBNAILS_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'thumbnails')
