from app import db
from datetime import datetime

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    time_limit = db.Column(db.Integer, nullable=True)  # in minutes
    # Ensure questions are deleted if the quiz is deleted
    questions = db.relationship('Question', backref='quiz', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Quiz {self.id}: {self.title}>"

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)  # {A: "x", B: "y", ...}
    correct_answer = db.Column(db.String(1), nullable=False)
    explanation = db.Column(db.Text)

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    score = db.Column(db.Float, nullable=True) # Percentage score
    duration = db.Column(db.Integer, nullable=True) # Duration in seconds
    user_answers_json = db.Column(db.JSON, nullable=True) # Store user's answers, e.g., {"question_id": "user_choice", ...}
    attempted_on = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    # user = db.relationship('User', backref='quiz_attempts') # Backref already defined in User model
    quiz_details = db.relationship('Quiz', backref='attempts') # Renamed backref for clarity

    def __repr__(self):
        return f"<QuizAttempt {self.id} by User {self.user_id} for Quiz {self.quiz_id} - Score: {self.score}%>"
