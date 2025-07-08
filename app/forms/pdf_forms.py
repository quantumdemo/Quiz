from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, DecimalField, RadioField # Added RadioField
from wtforms.validators import DataRequired, Optional, Length, NumberRange

class PDFUploadForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=150)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=5000)])
    category = StringField('Category', validators=[Optional(), Length(max=100)])
    tags = StringField('Tags (comma-separated)', validators=[Optional(), Length(max=255)])

    pdf_file = FileField('PDF File', validators=[
        FileRequired(),
        FileAllowed(['pdf'], 'PDFs only!')
    ])
    cover_image = FileField('Cover Image (Optional)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only (jpg, png)!')
    ])

    is_paid = BooleanField('This is a paid PDF', default=False)
    price = DecimalField('Price (if paid)', validators=[Optional(), NumberRange(min=0)], places=2)

    submit = SubmitField('Upload PDF')

class PDFEditForm(FlaskForm): # For editing existing PDF details, similar to upload but file fields might be optional
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=150)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=5000)])
    category = StringField('Category', validators=[Optional(), Length(max=100)])
    tags = StringField('Tags (comma-separated)', validators=[Optional(), Length(max=255)])

    # PDF file and cover image are handled separately for edits or made optional
    # if we allow changing them. For now, focusing on metadata.
    # pdf_file = FileField('New PDF File (Optional)', validators=[
    #     Optional(),
    #     FileAllowed(['pdf'], 'PDFs only!')
    # ])
    # cover_image = FileField('New Cover Image (Optional)', validators=[
    #     Optional(),
    #     FileAllowed(['jpg', 'jpeg', 'png'], 'Images only (jpg, png)!')
    # ])

    is_paid = BooleanField('This is a paid PDF')
    price = DecimalField('Price (if paid)', validators=[Optional(), NumberRange(min=0)], places=2)

    submit = SubmitField('Update PDF Details')

class ReviewForm(FlaskForm):
    rating = RadioField('Rating', choices=[
        ('5', '★★★★★'), ('4', '★★★★☆'), ('3', '★★★☆☆'), ('2', '★★☆☆☆'), ('1', '★☆☆☆☆')
    ], validators=[DataRequired("Please select a rating.")])
    comment = TextAreaField('Comment (Optional)', validators=[Optional(), Length(max=2000)])
    submit = SubmitField('Submit Review')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[Optional(), Length(max=100)])
    category = StringField('Category', validators=[Optional(), Length(max=100)])
    # Add more fields like sort_by, price_range if needed
    submit = SubmitField('Filter')
