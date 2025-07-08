from app import create_app, db
from app.models.user import User, UserRole
from app.models.pdf import PDF, Purchase
from app.models.quiz import Quiz, Question, QuizAttempt
from app.models.review import Review
from decimal import Decimal

app = create_app()

def seed_data():
    print("Starting database seeding...")

    # --- Users ---
    users_data = [
        {'email': 'admin@example.com', 'password': 'AdminPassword123!', 'role': UserRole.ADMIN, 'is_verified': True},
        {'email': 'user1@example.com', 'password': 'UserPassword123!', 'role': UserRole.VERIFIED_USER, 'is_verified': True},
        {'email': 'user2@example.com', 'password': 'UserPassword123!', 'role': UserRole.VERIFIED_USER, 'is_verified': True},
        {'email': 'unverified@example.com', 'password': 'UserPassword123!', 'role': UserRole.VERIFIED_USER, 'is_verified': False},
    ]
    created_users = {}
    for user_data in users_data:
        user = User.query.filter_by(email=user_data['email']).first()
        if not user:
            user = User(email=user_data['email'], role=user_data['role'], email_verified=user_data['is_verified'])
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f"Created user: {user.email}")
        created_users[user_data['email']] = user
    db.session.commit()

    admin_user = created_users.get('admin@example.com')
    user1 = created_users.get('user1@example.com')
    user2 = created_users.get('user2@example.com')

    # --- PDFs ---
    pdfs_data = [
        {
            'title': 'The Ultimate Flask Guide',
            'description': 'A comprehensive guide to mastering Flask for web development. Covers basics to advanced topics.',
            'filename': 'flask_guide_v1.pdf', # Ensure these dummy files exist in UPLOAD_FOLDER if testing downloads
            'cover_image_filename': 'flask_guide_cover.png',
            'is_paid': True,
            'price': Decimal('19.99'),
            'category': 'Programming',
            'tags': 'flask,python,web development,backend',
            'uploader_id': admin_user.id if admin_user else None
        },
        {
            'title': 'Introduction to Python Programming',
            'description': 'Perfect for beginners wanting to learn Python from scratch. Simple examples and clear explanations.',
            'filename': 'python_intro_free.pdf',
            'cover_image_filename': 'python_intro_cover.jpg',
            'is_paid': False,
            'price': None,
            'category': 'Programming',
            'tags': 'python,beginner,programming fundamentals',
            'uploader_id': admin_user.id if admin_user else None
        },
        {
            'title': 'Advanced SQLAlchemy Techniques',
            'description': 'Dive deep into SQLAlchemy ORM, covering complex queries, relationships, and performance tuning.',
            'filename': 'sqlalchemy_advanced.pdf',
            'is_paid': True,
            'price': Decimal('29.50'),
            'category': 'Databases',
            'tags': 'sqlalchemy,python,orm,database',
            'uploader_id': admin_user.id if admin_user else None
        },
        {
            'title': 'Healthy Cooking Recipes',
            'description': 'A collection of delicious and healthy recipes for everyday meals.',
            'filename': 'healthy_recipes_free.pdf',
            'cover_image_filename': 'healthy_recipes_cover.png',
            'is_paid': False,
            'price': None,
            'category': 'Lifestyle',
            'tags': 'cooking,health,recipes,food',
            'uploader_id': admin_user.id if admin_user else None
        }
    ]
    created_pdfs = {}
    for pdf_data in pdfs_data:
        pdf = PDF.query.filter_by(filename=pdf_data['filename']).first() # Assume filename is unique
        if not pdf:
            pdf = PDF(**pdf_data)
            db.session.add(pdf)
            print(f"Created PDF: {pdf.title}")
        created_pdfs[pdf_data['filename']] = pdf
    db.session.commit()

    flask_guide_pdf = created_pdfs.get('flask_guide_v1.pdf')
    python_intro_pdf = created_pdfs.get('python_intro_free.pdf')

    # --- Reviews ---
    if flask_guide_pdf and user1:
        review1 = Review.query.filter_by(user_id=user1.id, pdf_id=flask_guide_pdf.id).first()
        if not review1:
            db.session.add(Review(user_id=user1.id, pdf_id=flask_guide_pdf.id, rating=5, comment="Excellent guide, very comprehensive!"))
            print(f"Added review for '{flask_guide_pdf.title}' by {user1.email}")
    if python_intro_pdf and user2:
        review2 = Review.query.filter_by(user_id=user2.id, pdf_id=python_intro_pdf.id).first()
        if not review2:
            db.session.add(Review(user_id=user2.id, pdf_id=python_intro_pdf.id, rating=4, comment="Great for beginners, easy to follow."))
            print(f"Added review for '{python_intro_pdf.title}' by {user2.email}")
    db.session.commit()

    # --- Purchases (for testing download history & paid access) ---
    if flask_guide_pdf and user1: # User1 "buys" the Flask guide
        purchase1 = Purchase.query.filter_by(user_id=user1.id, pdf_id=flask_guide_pdf.id).first()
        if not purchase1:
            db.session.add(Purchase(user_id=user1.id, pdf_id=flask_guide_pdf.id, amount_paid=flask_guide_pdf.price, status='success', transaction_reference='seed_purchase_001'))
            print(f"Added purchase for '{flask_guide_pdf.title}' by {user1.email}")

    if python_intro_pdf and user1: # User1 "accesses" the free Python intro
        purchase2 = Purchase.query.filter_by(user_id=user1.id, pdf_id=python_intro_pdf.id).first()
        if not purchase2:
            db.session.add(Purchase(user_id=user1.id, pdf_id=python_intro_pdf.id, amount_paid=Decimal('0.00'), status='free_download')) # or 'success' if that's the general term
            print(f"Added free access log for '{python_intro_pdf.title}' by {user1.email}")
    db.session.commit()

    # --- Quizzes and Questions ---
    quizzes_data = [
        {
            'title': 'Basic Python Quiz',
            'description': 'Test your fundamental Python knowledge.',
            'time_limit': 10,
            'questions': [
                {'content': 'What keyword is used to define a function in Python?', 'options': {'A': 'func', 'B': 'def', 'C': 'function', 'D': 'define'}, 'correct_answer': 'B', 'explanation': '`def` is the keyword for defining functions.'},
                {'content': 'Which of these is mutable: tuple, string, list, frozenset?', 'options': {'A': 'tuple', 'B': 'string', 'C': 'list', 'D': 'frozenset'}, 'correct_answer': 'C', 'explanation': 'Lists are mutable; tuples, strings, and frozensets are immutable.'},
            ]
        },
        {
            'title': 'Flask Concepts Quiz',
            'description': 'A quiz on core Flask concepts.',
            'time_limit': 15,
            'questions': [
                {'content': 'What decorator is used to define a route in Flask?', 'options': {'A': '@app.url', 'B': '@app.route', 'C': '@Flask.route', 'D': '@route.url'}, 'correct_answer': 'B', 'explanation': '`@app.route()` is used to bind a URL to a view function.'},
                {'content': 'What object holds data sent from the client to the server?', 'options': {'A': 'session', 'B': 'g', 'C': 'request', 'D': 'response'}, 'correct_answer': 'C', 'explanation': 'The `request` object contains incoming request data.'},
            ]
        }
    ]

    for quiz_data in quizzes_data:
        quiz = Quiz.query.filter_by(title=quiz_data['title']).first()
        if not quiz:
            quiz = Quiz(title=quiz_data['title'], description=quiz_data['description'], time_limit=quiz_data['time_limit'])
            db.session.add(quiz)
            db.session.commit() # Commit quiz to get its ID for questions
            print(f"Created Quiz: {quiz.title}")
            for q_data in quiz_data['questions']:
                # Check if question content already exists for this quiz to avoid duplicates if script is run multiple times
                existing_q = Question.query.filter_by(quiz_id=quiz.id, content=q_data['content']).first()
                if not existing_q:
                    q = Question(quiz_id=quiz.id, **q_data)
                    db.session.add(q)
            db.session.commit() # Commit questions for this quiz

    print("Database seeding completed.")

if __name__ == '__main__':
    with app.app_context():
        # Consider dropping all tables for a clean seed, or handle existing data carefully.
        # For development, dropping might be okay. For staging/prod, never.
        # db.drop_all() # Use with caution!
        db.create_all() # Ensure all tables are created based on models
        seed_data()
