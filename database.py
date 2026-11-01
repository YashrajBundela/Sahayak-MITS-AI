import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "sahayak.db"


def get_db():
    """Open a connection to the SAHAYAK SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create required tables and safely migrate existing databases."""

    connection = get_db()

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS courses (
                course_code TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                course_type TEXT
            );

            CREATE TABLE IF NOT EXISTS timetable (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                course_code TEXT,
                course_name TEXT NOT NULL,
                room TEXT,
                faculty TEXT
            );

            CREATE TABLE IF NOT EXISTS exam_dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT,
                exam_name TEXT,
                exam_date TEXT,
                exam_time TEXT,
                branch TEXT,
                semester TEXT,
                venue TEXT,
                enrollment_range TEXT,
                instructions TEXT
            );

            CREATE TABLE IF NOT EXISTS fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semester TEXT,
                total_fee REAL,
                caution_money REAL,
                total_including_caution REAL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS library_timings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT,
                opening_time TEXT,
                closing_time TEXT,
                status TEXT
            );

            CREATE TABLE IF NOT EXISTS hostel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                information TEXT
            );

            CREATE TABLE IF NOT EXISTS scholarships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scholarship_name TEXT,
                eligibility TEXT,
                required_documents TEXT,
                category TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                branch TEXT,
                semester TEXT
            );

            CREATE TABLE IF NOT EXISTS student_preferences (
                user_email TEXT PRIMARY KEY,
                branch TEXT NOT NULL,
                semester TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Preserve existing documents while adding missing columns.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(knowledge_documents)"
            ).fetchall()
        }

        if "branch" not in columns:
            connection.execute("""
                ALTER TABLE knowledge_documents
                ADD COLUMN branch TEXT
            """)

        if "semester" not in columns:
            connection.execute("""
                ALTER TABLE knowledge_documents
                ADD COLUMN semester TEXT
            """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_docs_branch_semester
            ON knowledge_documents (branch, semester)
        """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
    print("SAHAYAK database initialized successfully.")