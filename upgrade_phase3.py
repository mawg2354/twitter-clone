import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upgrade():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL not found in environment variables.")
        return

    # Create engine
    engine = create_engine(database_url)
    
    # Columns to add to 'user' table
    user_columns = {
        'bio': 'VARCHAR(160)',
        'location': 'VARCHAR(30)',
        'profile_image': "VARCHAR(255) DEFAULT 'default_profile.png'",
        'cover_image': "VARCHAR(255) DEFAULT 'default_cover.png'"
    }

    with engine.connect() as connection:
        # Add columns to 'user' table
        for col, col_type in user_columns.items():
            try:
                connection.execute(text(f'ALTER TABLE "user" ADD COLUMN {col} {col_type};'))
                connection.commit()
                print(f"Successfully added column '{col}' to 'user' table.")
            except Exception as e:
                connection.rollback()
                # Check if it's already there
                if "already exists" in str(e).lower():
                    print(f"Column '{col}' already exists in 'user' table.")
                else:
                    print(f"Error adding column '{col}': {e}")

        # Add column to 'post' table
        try:
            connection.execute(text('ALTER TABLE "post" ADD COLUMN image_url VARCHAR(255);'))
            connection.commit()
            print("Successfully added column 'image_url' to 'post' table.")
        except Exception as e:
            connection.rollback()
            if "already exists" in str(e).lower():
                print("Column 'image_url' already exists in 'post' table.")
            else:
                print(f"Error adding column 'image_url': {e}")

        # Create 'notification' table
        try:
            create_notification_sql = """
            CREATE TABLE IF NOT EXISTS notification (
                id SERIAL PRIMARY KEY,
                type VARCHAR(20) NOT NULL,
                sender_id INTEGER NOT NULL REFERENCES "user"(id),
                recipient_id INTEGER NOT NULL REFERENCES "user"(id),
                post_id INTEGER REFERENCES post(id),
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            connection.execute(text(create_notification_sql))
            connection.commit()
            print("Successfully created 'notification' table (or it already existed).")
        except Exception as e:
            connection.rollback()
            print(f"Error creating 'notification' table: {e}")

if __name__ == "__main__":
    upgrade()
    print("\nMigration completed.")
