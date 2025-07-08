from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.quiz import Quiz, Question, QuizAttempt
from app import db
import time

quiz_bp = Blueprint('quiz', __name__, url_prefix='/quiz')

@quiz_bp.route('/all')
def all_quizzes():
    quizzes = Quiz.query.all()
    return render_template('quiz/quizzes.html', quizzes=quizzes)

@quiz_bp.route('/take/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        score = 0
        answers = request.form.to_dict()
        start_time = float(answers.pop('start_time', time.time()))
        duration = int(time.time() - start_time)

        for q in quiz.questions:
            user_answer = answers.get(str(q.id))
            if user_answer and user_answer.upper() == q.correct_answer:
                score += 1

        percent_score = (score / len(quiz.questions)) * 100
        attempt = QuizAttempt(user_id=current_user.id, quiz_id=quiz.id, score=percent_score, duration=duration)
        db.session.add(attempt)
        db.session.commit()

        flash(f'You scored {percent_score:.2f}%', 'success')
        return redirect(url_for('quiz.results'))

    return render_template('quiz/take_quiz.html', quiz=quiz, start_time=time.time())

@quiz_bp.route('/results')
@login_required
def results():
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    return render_template('quiz/results.html', attempts=attempts)

@quiz_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if current_user.role != 'admin':
        flash('Admins only.', 'danger')
        return redirect(url_for('quiz.all_quizzes'))

    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        limit = int(request.form.get('time_limit', 0))

        quiz = Quiz(title=title, description=desc, time_limit=limit)
        db.session.add(quiz)
        db.session.commit()
        flash('Quiz created. Add questions below.', 'success')
        return redirect(url_for('quiz.add_question', quiz_id=quiz.id))
    return render_template('quiz/create_quiz.html')

@quiz_bp.route('/<int:quiz_id>/add_question', methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    if current_user.role != 'admin':
        flash('Admins only.', 'danger')
        return redirect(url_for('quiz.all_quizzes'))

    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        content = request.form['content']
        options = {
            'A': request.form['option_a'],
            'B': request.form['option_b'],
            'C': request.form['option_c'],
            'D': request.form['option_d']
        }
        correct = request.form['correct']
        explain = request.form.get('explanation', '')

        question = Question(content=content, options=options, correct_answer=correct, explanation=explain, quiz_id=quiz.id)
        db.session.add(question)
        db.session.commit()
        flash('Question added.', 'info')
        return redirect(url_for('quiz.add_question', quiz_id=quiz.id))

    return render_template('quiz/add_question.html', quiz=quiz)
