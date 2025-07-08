from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.user import User
from app.models.pdf import PDF
from app.models.quiz import Quiz
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def restrict():
    if current_user.role != 'admin':
        flash('Admin access only.', 'danger')
        return redirect(url_for('auth.login'))

@admin_bp.route('/dashboard')
def dashboard():
    users = User.query.all()
    pdfs = PDF.query.all()
    quizzes = Quiz.query.all()
    return render_template('admin/dashboard.html', users=users, pdfs=pdfs, quizzes=quizzes)

@admin_bp.route('/ban_user/<int:user_id>')
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        user.is_active = False
        db.session.commit()
        flash(f'User {user.email} has been banned.', 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_pdf/<int:pdf_id>')
def delete_pdf(pdf_id):
    pdf = PDF.query.get_or_404(pdf_id)
    db.session.delete(pdf)
    db.session.commit()
    flash(f'Deleted "{pdf.title}".', 'danger')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/analytics')
def analytics():
    total_users = User.query.count()
    total_pdfs = PDF.query.count()
    total_quizzes = Quiz.query.count()
    return render_template('admin/analytics.html', total_users=total_users, total_pdfs=total_pdfs, total_quizzes=total_quizzes)
