from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, RadioField
from wtforms.validators import DataRequired, Length

class QuizForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3)])
    description = TextAreaField('Description')
    time_limit = IntegerField('Time Limit (minutes)')
    submit = SubmitField('Create Quiz')

class QuestionForm(FlaskForm):
    content = TextAreaField('Question Content', validators=[DataRequired()])
    option_a = StringField('Option A', validators=[DataRequired()])
    option_b = StringField('Option B', validators=[DataRequired()])
    option_c = StringField('Option C', validators=[DataRequired()])
    option_d = StringField('Option D', validators=[DataRequired()])
    correct = RadioField('Correct Answer', choices=[('A','A'),('B','B'),('C','C'),('D','D')], validators=[DataRequired()])
    explanation = TextAreaField('Explanation')
    submit = SubmitField('Add Question')
