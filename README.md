# Flask PDF Marketplace

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables (e.g., in `.env`):
   ```
   SECRET_KEY=your_secret
   DATABASE_URL=sqlite:///db.sqlite3
   MAIL_USERNAME=your@gmail.com
   MAIL_PASSWORD=yourpassword
   PAYSTACK_SECRET_KEY=your_paystack_key
   ```

4. **Flask-Migrate** Setup:

   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. Run seeder:
   ```bash
   python seeds.py
   ```

6. Run the app:
   ```bash
   python run.py
   ```
