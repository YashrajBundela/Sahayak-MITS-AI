from database import get_db, init_db


COURSES = [
    ("34252101", "Numerical Techniques", "Theory"),
    ("34252102", "Design and Analysis of Algorithms", "Theory"),
    ("34252103", "Computer Networks", "Theory"),
    ("34252104", "Computer Organization and Architecture", "Theory"),
    ("34252105", "Database Management System", "Theory"),
    ("34252106", "Design and Analysis of Algorithms Lab", "Lab"),
    ("34252107", "Database Management System Lab", "Lab"),
    ("34252108", "Problem Solving through Python Programming", "Lab"),
    ("34252109", "Semester Proficiency", "Other"),
    ("34252110", "Macro Project-I", "Project"),
    ("34252111", "Self-learning Presentation", "Presentation"),
    ("34252112", "Cyber Security", "Theory"),
]


def seed_courses():
    init_db()
    connection = get_db()

    try:
        connection.executemany(
            """
            INSERT OR IGNORE INTO courses
            (course_code, course_name, course_type)
            VALUES (?, ?, ?)
            """,
            COURSES
        )

        connection.commit()
        print("SAHAYAK courses added successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    seed_courses()