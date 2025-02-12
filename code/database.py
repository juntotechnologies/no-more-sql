import sqlite3
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="data/feedback.db"):
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create table for user interactions
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_prompt TEXT NOT NULL,
                    generated_sql TEXT NOT NULL,
                    worked_first_try BOOLEAN,
                    feedback TEXT
                )
                ''')

                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def log_interaction(self, user_prompt, generated_sql):
        """Log a new user interaction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO interactions (user_prompt, generated_sql) VALUES (?, ?)',
                    (user_prompt, generated_sql)
                )
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error logging interaction: {e}")
            return None

    def update_feedback(self, interaction_id, worked_first_try, feedback=None):
        """Update the feedback for a specific interaction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE interactions SET worked_first_try = ?, feedback = ? WHERE id = ?',
                    (worked_first_try, feedback, interaction_id)
                )
                return True
        except Exception as e:
            logger.error(f"Error updating feedback: {e}")
            return False

    def get_statistics(self):
        """Get statistics about SQL generation success rate."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN worked_first_try = 1 THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN worked_first_try = 0 THEN 1 ELSE 0 END) as failure
                FROM interactions
                WHERE worked_first_try IS NOT NULL
                ''')
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return None

    def view_all_interactions(self):
        """View all interactions in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM interactions')
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error viewing interactions: {e}")
            return None
