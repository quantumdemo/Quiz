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
        start_time = float(answers.pop('start_time', time.time())) # Get start_time from form, remove it from answers
        duration = int(time.time() - start_time)

        # Prepare user_answers for JSON storage, excluding non-answer fields like csrf_token if any
        user_answers_to_store = {k: v for k, v in answers.items() if k.startswith('question_')} # Assuming question inputs are named 'question_<id>'

        # Or, if answers dict contains only question responses after popping start_time:
        # user_answers_to_store = answers.copy()

        for q in quiz.questions:
            # Ensure question IDs are strings for keys in user_answers_to_store if form names are like "question_123"
            user_answer = user_answers_to_store.get(f'question_{q.id}')
            if user_answer and user_answer.upper() == q.correct_answer.upper(): # Case-insensitive check for correct answer key
                score += 1

        num_questions = len(quiz.questions.all()) # Use .all() if lazy='dynamic'
        percent_score = (score / num_questions) * 100 if num_questions > 0 else 0

        attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz.id,
            score=percent_score,
            duration=duration,
            user_answers_json=user_answers_to_store # Store the submitted answers
        )
        db.session.add(attempt)
        db.session.commit()

        flash(f'Quiz submitted! You scored {percent_score:.2f}%. View your detailed results below.', 'success')
        # Redirect to a new route that shows detailed results for this specific attempt
        return redirect(url_for('quiz.quiz_attempt_detail', attempt_id=attempt.id))

    return render_template('quiz/take_quiz.html', quiz=quiz, start_time=time.time())

@quiz_bp.route('/results_summary') # Renamed for clarity from just /results
@login_required
def results_summary():
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).order_by(QuizAttempt.attempted_on.desc()).all()
    return render_template('quiz/results_summary.html', attempts=attempts, title="My Quiz Attempts Summary")

@quiz_bp.route('/attempt/<int:attempt_id>/result_detail')
@login_required
def quiz_attempt_detail(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    # Ensure the current user owns this attempt, or is an admin
    if attempt.user_id != current_user.id and not current_user.is_admin:
        flash("You are not authorized to view this quiz attempt.", "danger")
        return redirect(url_for('quiz.results_summary'))

    quiz = Quiz.query.get_or_404(attempt.quiz_id)

    # To show detailed results, we need to reconstruct what the user answered for each question.
    # The current model `QuizAttempt` only stores the final score and duration.
    # To show question-by-question results, we'd need to store `user_answers` (JSON perhaps) in `QuizAttempt`.
    # For now, I can't display individual answers as they are not stored.
    # I will just display the overall score and quiz details.
    # A future enhancement would be to store user's answers per question in QuizAttempt.

    # Placeholder for user_answers if they were stored:
    # user_answers_data = attempt.user_answers # e.g., a JSON field like {"question_id_1": "A", "question_id_2": "C"}

    # For now, just passing the attempt and quiz. The template will show score and can list questions for review.
    return render_template('quiz/quiz_result_detail.html', attempt=attempt, quiz=quiz, title=f"Results for {quiz.title}")

# Admin routes for quiz creation and question management have been moved to app/routes/admin.py
# Removing them from here to avoid duplication and keep concerns separated.
