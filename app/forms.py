from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired


class BookForm(FlaskForm):
    id = StringField('id')
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    isbn = StringField('ISBN', validators=[DataRequired()])
    location = StringField('Location')
    submit = SubmitField('Submit')


class BulkEditLocationForm(FlaskForm):
    location = StringField('New Location', validators=[DataRequired()])
    book_ids = HiddenField()
    submit = SubmitField('Update Locations')
