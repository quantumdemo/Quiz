from app import create_app, db
from app.models.user import User
from app.models.pdf import PDF
from app.models.quiz import Quiz, Question

app = create_app()
with app.app_context():
    db.create_all()
    # Create admin user
    admin = User(email='admin@example.com', password='$2b$12$...', role='admin')  # <-- replace hashed password
    db.session.add(admin)
    # Sample PDF
    pdf1 = PDF(title='Sample Free PDF', description='A free document.', filename='sample.pdf', is_paid=False)
    pdf2 = PDF(title='Sample Paid PDF', description='A paid document.', filename='sample_paid.pdf', is_paid=True)
    db.session.add_all([pdf1, pdf2])
    # Sample Quiz
    quiz = Quiz(title='Sample Quiz', description='Test your knowledge.', time_limit=5)
    db.session.add(quiz)
    db.session.commit()
    # Add a question
    q = Question(quiz_id=quiz.id, content='What is 2+2?', options={'A':'3','B':'4','C':'5','D':'6'}, correct_answer='B', explanation='2+2=4')
    db.session.add(q)
    db.session.commit()
    print('Seeding complete.')
