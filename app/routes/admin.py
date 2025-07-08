from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.user import User, UserRole
from app.models.pdf import PDF, Purchase
from app.models.quiz import Quiz, QuizAttempt, Question # Added Question
from app.models.review import Review
from app import db
from sqlalchemy import func # For SUM and AVG
from app.forms.pdf_forms import PDFUploadForm, PDFEditForm # Import PDF forms

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from app.utils.decorators import admin_required # Use the decorator
import os
from flask import current_app, request # Added request
from werkzeug.utils import secure_filename
import uuid

# The admin_required decorator handles both login and admin role check.
# So, the before_request hook can be simplified or removed if all routes use the decorator.
# For now, let's update it to use the new role check logic.
# A better approach is to remove this before_request and apply @admin_required to each route.
# I will remove it and apply the decorator to each existing route.

# @admin_bp.before_request
# @login_required # This is implicitly handled by admin_required now
# def restrict_admin_access(): # Renamed for clarity
#     if not current_user.is_admin: # Using the property from User model
#         flash('This area is restricted to administrators only.', 'danger')
#         # Redirect to a more general page, or login if not authenticated (handled by @admin_required)
#         return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
@admin_required # Apply decorator here
def dashboard():
    users = User.query.all()
    pdfs = PDF.query.all()
    quizzes = Quiz.query.all()
    return render_template('admin/dashboard.html', users=users, pdfs=pdfs, quizzes=quizzes)

@admin_bp.route('/user/<int:user_id>/ban', methods=['POST']) # Changed to POST
@admin_required
def ban_user(user_id): # Renamed route function for clarity if needed, but endpoint name stays admin.ban_user if not changed in url_for
    user_to_ban = User.query.get_or_404(user_id)

    if user_to_ban.id == current_user.id:
        flash("You cannot ban yourself.", "warning")
        return redirect(url_for('admin.dashboard'))

    if user_to_ban.is_admin:
        flash('Administrators cannot be banned directly. Demote them first if necessary.', 'warning')
        return redirect(url_for('admin.dashboard'))

    user_to_ban.is_active = False # Ban the user
    db.session.commit()
    flash(f'User {user_to_ban.email} has been banned.', 'success')
    return redirect(url_for('admin.dashboard'))

# TODO: Add an unban_user route if needed.
# @admin_bp.route('/user/<int:user_id>/unban', methods=['POST'])
# @admin_required
# def unban_user(user_id): ...

@admin_bp.route('/user/<int:user_id>/toggle_admin', methods=['POST'])
@admin_required
def toggle_admin_role(user_id):
    user_to_modify = User.query.get_or_404(user_id)

    if user_to_modify.id == current_user.id:
        flash("You cannot change your own admin status.", "warning")
        return redirect(url_for('admin.dashboard')) # Or a user management page

    if user_to_modify.is_admin:
        # Demote from admin - ensure there's at least one other admin
        admin_count = User.query.filter_by(role=UserRole.ADMIN, is_active=True).count()
        if admin_count <= 1:
            flash("Cannot demote the last active admin. Create another admin first.", "danger")
            return redirect(url_for('admin.dashboard'))
        user_to_modify.role = UserRole.VERIFIED_USER
        flash(f"User {user_to_modify.email} has been demoted to Verified User.", "success")
    else:
        user_to_modify.role = UserRole.ADMIN
        flash(f"User {user_to_modify.email} has been promoted to Admin.", "success")

    db.session.commit()
    return redirect(url_for('admin.dashboard')) # Or specific user management page

@admin_bp.route('/delete_pdf/<int:pdf_id>', methods=['POST']) # Changed to POST for safety
@admin_required
def delete_pdf(pdf_id):
    pdf = PDF.query.get_or_404(pdf_id)

    # Delete actual files from filesystem
    if pdf.filename:
        try:
            pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf.filename)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as e:
            flash(f"Error deleting PDF file {pdf.filename}: {e}", "danger")
            # Decide if you want to proceed with DB deletion or not

    if pdf.cover_image_filename:
        try:
            cover_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf.cover_image_filename)
            if os.path.exists(cover_image_path):
                os.remove(cover_image_path)
        except Exception as e:
            flash(f"Error deleting cover image file {pdf.cover_image_filename}: {e}", "danger")

    db.session.delete(pdf)
    db.session.commit()
    flash(f'Deleted "{pdf.title}".', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/analytics')
@admin_required
def analytics():
    total_users = User.query.count()
    verified_users = User.query.filter_by(email_verified=True).count()
    admin_users = User.query.filter_by(role=UserRole.ADMIN).count()

    total_pdfs = PDF.query.count()
    paid_pdfs_count = PDF.query.filter_by(is_paid=True).count()
    free_pdfs_count = PDF.query.filter_by(is_paid=False).count()

    total_quizzes = Quiz.query.count()
    total_questions = Question.query.count() # Import Question model first

    # Sales analytics
    total_sales_value = db.session.query(func.sum(Purchase.amount_paid)).filter(Purchase.status == 'success').scalar() or 0.0
    total_purchases = Purchase.query.filter(Purchase.status == 'success').count() # Count successful purchases

    # Quiz analytics
    total_quiz_attempts = QuizAttempt.query.count()
    average_quiz_score = db.session.query(func.avg(QuizAttempt.score)).scalar()
    if average_quiz_score is not None:
        average_quiz_score = round(average_quiz_score, 2)
    else:
        average_quiz_score = 0.0

    # Number of reviews
    total_reviews = Review.query.count()

    return render_template('admin/analytics.html',
                           total_users=total_users, verified_users=verified_users, admin_users=admin_users,
                           total_pdfs=total_pdfs, paid_pdfs_count=paid_pdfs_count, free_pdfs_count=free_pdfs_count,
                           total_quizzes=total_quizzes, total_questions=total_questions,
                           total_sales_value=total_sales_value, total_purchases=total_purchases,
                           total_quiz_attempts=total_quiz_attempts, average_quiz_score=average_quiz_score,
                           total_reviews=total_reviews,
                           title="Site Analytics")

# PDF Management Routes
# ---------------------

def save_file(file, type_folder='pdfs'):
    """Saves a file to the UPLOAD_FOLDER and returns its unique filename."""
    if not file or not file.filename:
        return None

    original_filename = secure_filename(file.filename)
    filename_ext = os.path.splitext(original_filename)[1].lower()
    # Check against allowed extensions from config (more robust than FileAllowed in form alone)
    # This example assumes a general UPLOAD_FOLDER. For specific types, could use subfolders.
    # For PDFs: current_app.config['ALLOWED_EXTENSIONS'] might be {'pdf'}
    # For images: a separate list like {'png', 'jpg', 'jpeg'}

    # For this example, we rely on form validation for extension type for simplicity here,
    # but a check here would be good too.

    unique_filename = str(uuid.uuid4()) + filename_ext
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)

    try:
        file.save(file_path)
        return unique_filename
    except Exception as e:
        current_app.logger.error(f"Failed to save file {original_filename} as {unique_filename}: {e}")
        return None

@admin_bp.route('/upload_pdf', methods=['GET', 'POST'])
@admin_required
def upload_pdf():
    form = PDFUploadForm()
    if form.validate_on_submit():
        pdf_filename = None
        cover_image_filename = None

        if form.pdf_file.data:
            pdf_filename = save_file(form.pdf_file.data, type_folder='pdfs')
            if not pdf_filename:
                flash('PDF file could not be saved. Please try again.', 'danger')
                return render_template('admin/upload_pdf.html', form=form, title="Upload PDF")

        if form.cover_image.data:
            cover_image_filename = save_file(form.cover_image.data, type_folder='covers') # Assuming covers might go to same UPLOAD_FOLDER or a subfolder
            if not cover_image_filename:
                flash('Cover image could not be saved. Please try again.', 'warning')
                # Continue without cover if it fails, or make it critical

        new_pdf = PDF(
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            tags=form.tags.data,
            filename=pdf_filename,
            cover_image_filename=cover_image_filename,
            is_paid=form.is_paid.data,
            price=form.price.data if form.is_paid.data else None,
            uploader_id=current_user.id
        )
        db.session.add(new_pdf)
        db.session.commit()
        flash(f'PDF "{new_pdf.title}" uploaded successfully!', 'success')
        return redirect(url_for('admin.manage_pdfs')) # Redirect to a PDF management page

    return render_template('admin/upload_pdf.html', form=form, title="Upload PDF")

@admin_bp.route('/manage_pdfs')
@admin_required
def manage_pdfs():
    page = request.args.get('page', 1, type=int)
    pdfs = PDF.query.order_by(PDF.uploaded_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/manage_pdfs.html', pdfs=pdfs, title="Manage PDFs")

# Edit PDF route (metadata only for now)
@admin_bp.route('/edit_pdf/<int:pdf_id>', methods=['GET', 'POST'])
@admin_required
def edit_pdf(pdf_id):
    pdf_instance = PDF.query.get_or_404(pdf_id)
    form = PDFEditForm(obj=pdf_instance) # Populate form with existing data

    if form.validate_on_submit():
        pdf_instance.title = form.title.data
        pdf_instance.description = form.description.data
        pdf_instance.category = form.category.data
        pdf_instance.tags = form.tags.data
        pdf_instance.is_paid = form.is_paid.data
        pdf_instance.price = form.price.data if form.is_paid.data else None
        # Note: File uploads (changing PDF/cover) are not handled here yet.

        db.session.commit()
        flash(f'PDF "{pdf_instance.title}" updated successfully!', 'success')
        return redirect(url_for('admin.manage_pdfs'))

    return render_template('admin/edit_pdf.html', form=form, pdf=pdf_instance, title="Edit PDF")

# Quiz Management Routes
# --------------------
from app.forms.quiz_forms import QuizForm, QuestionForm # Import Quiz forms

@admin_bp.route('/manage_quizzes')
@admin_required
def manage_quizzes():
    quizzes = Quiz.query.order_by(Quiz.title).all()
    return render_template('admin/manage_quizzes.html', quizzes=quizzes, title="Manage Quizzes")

@admin_bp.route('/create_quiz', methods=['GET', 'POST'])
@admin_required
def create_quiz():
    form = QuizForm()
    if form.validate_on_submit():
        new_quiz = Quiz(
            title=form.title.data,
            description=form.description.data,
            time_limit=form.time_limit.data if form.time_limit.data else None
        )
        db.session.add(new_quiz)
        db.session.commit()
        flash(f'Quiz "{new_quiz.title}" created successfully. Now add questions.', 'success')
        return redirect(url_for('admin.edit_quiz', quiz_id=new_quiz.id))
    return render_template('admin/create_quiz.html', form=form, title="Create New Quiz")

@admin_bp.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@admin_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    form = QuizForm(obj=quiz) # For editing quiz metadata

    if form.validate_on_submit() and 'update_quiz_details' in request.form: # Check which form was submitted
        quiz.title = form.title.data
        quiz.description = form.description.data
        quiz.time_limit = form.time_limit.data if form.time_limit.data else None
        db.session.commit()
        flash(f'Quiz "{quiz.title}" details updated.', 'success')
        return redirect(url_for('admin.edit_quiz', quiz_id=quiz.id))

    # Questions related to this quiz
    questions = Question.query.filter_by(quiz_id=quiz.id).all()
    question_form = QuestionForm() # For adding a new question

    return render_template('admin/edit_quiz.html', quiz=quiz, form=form,
                           questions=questions, question_form=question_form, title=f"Edit Quiz: {quiz.title}")

@admin_bp.route('/quiz/<int:quiz_id>/add_question', methods=['POST'])
@admin_required
def add_question_to_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    # Re-instantiate forms for processing to avoid CSRF issues if using same form instance as display
    quiz_details_form = QuizForm(obj=quiz) # For re-rendering edit_quiz page
    question_form = QuestionForm() # For processing new question

    if question_form.validate_on_submit(): # Assuming QuestionForm is submitted
        options_dict = {
            "A": question_form.option_a.data,
            "B": question_form.option_b.data,
            "C": question_form.option_c.data,
            "D": question_form.option_d.data,
        }
        new_question = Question(
            quiz_id=quiz.id,
            content=question_form.content.data,
            options=options_dict,
            correct_answer=question_form.correct.data,
            explanation=question_form.explanation.data
        )
        db.session.add(new_question)
        db.session.commit()
        flash('New question added successfully.', 'success')
        return redirect(url_for('admin.edit_quiz', quiz_id=quiz.id))
    else:
        # If form validation fails, re-render the edit_quiz page with errors
        flash('Failed to add question. Please check the errors.', 'danger')
        questions = Question.query.filter_by(quiz_id=quiz.id).all()
        return render_template('admin/edit_quiz.html', quiz=quiz, form=quiz_details_form,
                               questions=questions, question_form=question_form, # Pass failing form back
                               title=f"Edit Quiz: {quiz.title}")


@admin_bp.route('/quiz/<int:quiz_id>/delete_question/<int:question_id>', methods=['POST'])
@admin_required
def delete_question_from_quiz(quiz_id, question_id):
    question = Question.query.filter_by(id=question_id, quiz_id=quiz_id).first_or_404()
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully.', 'success')
    return redirect(url_for('admin.edit_quiz', quiz_id=quiz_id))

# TODO: Route for editing an existing question. This would be similar to add_question.
# @admin_bp.route('/quiz/<int:quiz_id>/edit_question/<int:question_id>', methods=['GET', 'POST'])
# @admin_required
# def edit_question_in_quiz(quiz_id, question_id):
#     pass

@admin_bp.route('/quiz/delete/<int:quiz_id>', methods=['POST'])
@admin_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    # Associated questions will be deleted due to cascade="all, delete-orphan"
    # Also, QuizAttempt records should be handled. The current model does not have cascade for attempts from Quiz.
    # This might be desired: if a quiz is deleted, attempts are also deleted.
    # Or they might be kept for historical records, but would then have a null quiz_id if not handled (or FK constraint error).
    # For now, just deleting the quiz. If QuizAttempt.quiz_id is nullable, it's fine. If not, this will error.
    # Let's assume QuizAttempt.quiz_id should be made nullable or attempts deleted manually/cascaded.

    # Explicitly delete related QuizAttempts if not cascaded and FK is not nullable
    # Example: QuizAttempt.query.filter_by(quiz_id=quiz.id).delete()
    # This needs to be done before deleting the quiz if there's a non-nullable FK.
    # For now, assuming cascade or nullable FK handles this.

    db.session.delete(quiz)
    db.session.commit()
    flash(f'Quiz "{quiz.title}" and all its questions have been deleted.', 'success')
    return redirect(url_for('admin.manage_quizzes'))

# Review Management Routes
# ----------------------
@admin_bp.route('/manage_reviews')
@admin_required
def manage_reviews():
    page = request.args.get('page', 1, type=int)
    # Order by most recent first. Join with User and PDF to display related info.
    reviews_pagination = Review.query.join(User, Review.user_id == User.id)\
                                   .join(PDF, Review.pdf_id == PDF.id)\
                                   .add_columns(User.email, PDF.title.label("pdf_title"), Review.id, Review.rating, Review.comment, Review.created_at)\
                                   .order_by(Review.created_at.desc())\
                                   .paginate(page=page, per_page=15)

    return render_template('admin/manage_reviews.html', reviews_pagination=reviews_pagination, title="Manage Reviews")

@admin_bp.route('/delete_review/<int:review_id>', methods=['POST'])
@admin_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Review has been deleted successfully.', 'success')
    return redirect(request.referrer or url_for('admin.manage_reviews'))
