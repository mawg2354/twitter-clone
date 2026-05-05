from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN date_of_birth DATE;'))
        db.session.commit()
        print("Column added successfully!")
    except Exception as e:
        print(f"Error (maybe already exists?): {e}")
