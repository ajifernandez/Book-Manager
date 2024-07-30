# Book Manager

A Flask web application for managing a collection of books. The application allows you to add, edit, delete, and search for books. It also features a barcode scanner using a webcam to facilitate adding books by scanning their ISBN.

## Features

- Add, edit, delete, and search for books
- Scan book barcodes using a webcam to automatically fetch book information
- Display book thumbnails if available
- Edit multiple book locations at once
- Set and update a default location for newly scanned books
- Responsive design with Bootstrap 4

## Installation

1. **Clone the repository:**
    ```sh
    git clone https://github.com/your-username/book-manager.git
    cd book-manager
    ```

2. **Set up a virtual environment and activate it:**
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4. **Run the application:**
    ```sh
    flask run
    ```

## Configuration

- **Secret Key:** Set the `SECRET_KEY` for CSRF protection in `app/__init__.py`.
- **Default Location:** The default location for newly scanned books can be set and updated via the application interface.

## Usage

### Adding Books

1. **Manually:**
    - Click on the "Add Book" button and fill in the details.
    
2. **Using Barcode Scanner:**
    - The webcam will activate on application start. Scan the book's barcode, and the book details will be fetched and displayed in the add book form.

### Editing Books

- Click the "Edit" button next to the book you want to edit, update the details, and save.

### Deleting Books

- Click the "Delete" button next to the book you want to delete.

### Bulk Edit Location

1. **Select Books:**
    - Use the checkboxes to select multiple books.

2. **Update Location:**
    - Click on "Edit Selected Locations" and enter the new location.

### Searching Books

- Use the search bar to filter books by title or author. Click "Clear Filter" to reset the search.

### Updating Default Location

- Click on "Edit Default Location" to update the location that will be set for newly scanned books.

## Dependencies

- Flask
- Flask-WTF
- OpenCV
- Requests
- CSV for data storage

## Folder Structure

book-manager/
│
├── app/
│ ├── init.py
│ ├── routes.py
│ ├── forms.py
│ ├── templates/
│ │ ├── index.html
│ │ ├── add_book.html
│ │ ├── edit_book.html
│ │ ├── bulk_edit_location.html
│ │ ├── edit_default_location.html
│ └── static/
│ ├── no_thumbnail.png
│ └── thumbnails/
│
├── .venv/
│
├── requirements.txt
│
└── README.md


## Contributing

Contributions are welcome! Please submit a pull request or open an issue to discuss changes.

## License

This project is licensed under the MIT License.
