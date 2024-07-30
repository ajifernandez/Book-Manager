import os

SECRET_KEY = os.urandom(32)
CSV_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'books.csv')
THUMBNAILS_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'thumbnails')
DEFAULT_LOCATION = 'Casa'
