from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired

from config import DEFAULT_LOCATION


class BookForm(FlaskForm):
    id = StringField('id')
    title = StringField('Title')
    author = StringField('Author')
    isbn = StringField('ISBN', validators=[DataRequired()])
    location = StringField('Location', default=DEFAULT_LOCATION)
    submit = SubmitField('Submit')


class BulkEditLocationForm(FlaskForm):
    location = StringField('New Location', validators=[DataRequired()])
    book_ids = HiddenField()
    submit = SubmitField('Update Locations')
