from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.models.pdf import PDF, Purchase
from app import db

pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')

@pdf_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_pdf():
    if current_user.role != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('pdf.marketplace'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_user.app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        pdf = PDF(title=title, description=description, filename=filename, is_paid=request.form.get('is_paid') == 'true')
        db.session.add(pdf)
        db.session.commit()
        flash('PDF uploaded successfully.', 'success')
        return redirect(url_for('pdf.marketplace'))
    return render_template('pdf/upload.html')

@pdf_bp.route('/marketplace')
def marketplace():
    query = request.args.get('q')
    if query:
        pdfs = PDF.query.filter(PDF.title.ilike(f'%{query}%')).all()
    else:
        pdfs = PDF.query.all()
    return render_template('pdf/marketplace.html', pdfs=pdfs)

@pdf_bp.route('/download/<int:pdf_id>')
@login_required
def download(pdf_id):
    pdf = PDF.query.get_or_404(pdf_id)
    if pdf.is_paid:
        purchase = Purchase.query.filter_by(user_id=current_user.id, pdf_id=pdf.id).first()
        if not purchase:
            flash('Please purchase this document first.', 'danger')
            return redirect(url_for('pdf.marketplace'))
    return send_from_directory(os.path.join(current_user.app.config['UPLOAD_FOLDER']), pdf.filename, as_attachment=True)
