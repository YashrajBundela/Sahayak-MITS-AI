import sqlite3

DB_NAME = "sahayak.db"

# =========================================================
# CONNECT TO DATABASE
# =========================================================

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

print("Connected to Sahayak database...")


# =========================================================
# 1. EXAM / QUIZ INFORMATION
# =========================================================

cursor.execute("DROP TABLE IF EXISTS exam_dates")

cursor.execute("""
CREATE TABLE exam_dates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_type TEXT NOT NULL,
    exam_name TEXT NOT NULL,
    exam_date TEXT NOT NULL,
    exam_time TEXT NOT NULL,
    branch TEXT,
    semester TEXT,
    venue TEXT,
    enrollment_range TEXT,
    instructions TEXT
)
""")

exam_data = [

    (
        "Quiz",
        "Quiz Examination",
        "19/09/2026",
        "02:00 PM - 03:15 PM",
        "CST",
        "III Semester",
        "M 105 (CAI)",
        "1-33",
        "Quizzes for all subjects will be conducted online in computer labs only. "
        "Students are allotted 15 minutes multiplied by the number of courses. "
        "For 5 courses, the maximum duration is 75 minutes. "
        "Students can attempt the quiz for the courses in any order."
    ),

    (
        "Quiz",
        "Quiz Examination",
        "19/09/2026",
        "02:00 PM - 03:15 PM",
        "CST",
        "III Semester",
        "Computer Lab-1 (EE)",
        "34-43",
        "Quizzes for all subjects will be conducted online in computer labs only."
    ),

    (
        "Quiz",
        "Quiz Examination",
        "19/09/2026",
        "02:00 PM - 03:15 PM",
        "CST",
        "III Semester",
        "Computer Lab-2 (EE)",
        "44-69",
        "Quizzes for all subjects will be conducted online in computer labs only."
    ),

    (
        "Quiz",
        "Quiz Examination",
        "19/09/2026",
        "02:00 PM - 03:15 PM",
        "CST",
        "III Semester",
        "Programming Lab-4 (CSE)",
        "70-75, ET10, D01, D02",
        "Quizzes for all subjects will be conducted online in computer labs only."
    ),

    (
        "Quiz",
        "Quiz Examination",
        "19/09/2026",
        "02:00 PM - 03:15 PM",
        "CSBS",
        "III Semester",
        "M 203 (CAI)",
        "1-66",
        "Quizzes for all subjects will be conducted online in computer labs only."
    ),

    (
        "Quiz",
        "Quiz Examination",
        "19/09/2026",
        "02:00 PM - 03:15 PM",
        "CSBS",
        "III Semester",
        "M 302 (CCST)",
        "67-136",
        "Quizzes for all subjects will be conducted online in computer labs only."
    ),

    (
        "Quiz",
        "Quiz Examination",
        "19/09/2026",
        "02:00 PM - 03:15 PM",
        "CSBS",
        "III Semester",
        "CoDe Lab (CCST)",
        "137-158, IO42, EE39, D01",
        "Quizzes for all subjects will be conducted online in computer labs only."
    )
]

cursor.executemany("""
INSERT INTO exam_dates (
    exam_type,
    exam_name,
    exam_date,
    exam_time,
    branch,
    semester,
    venue,
    enrollment_range,
    instructions
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", exam_data)

print("Exam data inserted.")


# =========================================================
# 2. FEE STRUCTURE
# =========================================================

cursor.execute("DROP TABLE IF EXISTS fees")

cursor.execute("""
CREATE TABLE fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester TEXT NOT NULL,
    total_fee INTEGER,
    caution_money INTEGER,
    total_including_caution INTEGER,
    notes TEXT
)
""")

fee_data = [

    (
        "I Semester",
        114000,
        10000,
        124000,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    ),

    (
        "II Semester",
        62000,
        0,
        62000,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    ),

    (
        "III Semester",
        84100,
        0,
        84100,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    ),

    (
        "IV Semester",
        62000,
        0,
        62000,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    ),

    (
        "V Semester",
        84100,
        0,
        84100,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    ),

    (
        "VI Semester",
        62000,
        0,
        62000,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    ),

    (
        "VII Semester",
        84100,
        0,
        84100,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    ),

    (
        "VIII Semester",
        63500,
        0,
        63500,
        "B.Tech Fee Structure for Admission Year 2025-2026."
    )
]

cursor.executemany("""
INSERT INTO fees (
    semester,
    total_fee,
    caution_money,
    total_including_caution,
    notes
)
VALUES (?, ?, ?, ?, ?)
""", fee_data)

print("Fee data inserted.")


# =========================================================
# 3. LIBRARY TIMINGS
# =========================================================

cursor.execute("DROP TABLE IF EXISTS library_timings")

cursor.execute("""
CREATE TABLE library_timings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    opening_time TEXT,
    closing_time TEXT,
    status TEXT
)
""")

library_data = [

    ("Monday", "10:00 AM", "06:00 PM", "Open"),
    ("Tuesday", "10:00 AM", "06:00 PM", "Open"),
    ("Wednesday", "10:00 AM", "06:00 PM", "Open"),
    ("Thursday", "10:00 AM", "06:00 PM", "Open"),
    ("Friday", "10:00 AM", "06:00 PM", "Open"),

    # Weekend information was not provided
    ("Saturday", None, None, "Information not provided"),
    ("Sunday", None, None, "Information not provided")
]

cursor.executemany("""
INSERT INTO library_timings (
    day,
    opening_time,
    closing_time,
    status
)
VALUES (?, ?, ?, ?)
""", library_data)

print("Library data inserted.")


# =========================================================
# 4. HOSTEL INFORMATION
# =========================================================

cursor.execute("DROP TABLE IF EXISTS hostel")

cursor.execute("""
CREATE TABLE hostel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    information TEXT NOT NULL
)
""")

hostel_data = [

    (
        "First Year",
        "Hostel allotment is available for first-year students."
    ),

    (
        "Second Year",
        "Hostel accommodation is not available for second-year students."
    )
]

cursor.executemany("""
INSERT INTO hostel (
    category,
    information
)
VALUES (?, ?)
""", hostel_data)

print("Hostel data inserted.")


# =========================================================
# 5. SCHOLARSHIPS
# =========================================================

cursor.execute("DROP TABLE IF EXISTS scholarships")

cursor.execute("""
CREATE TABLE scholarships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_name TEXT NOT NULL,
    eligibility TEXT,
    required_documents TEXT,
    category TEXT,
    notes TEXT
)
""")

scholarship_data = [

    (
        "MMWY - Mukhyamantri Medhavi Chhatra Yojna",

        "Available for all categories. "
        "Class 12 marks should be greater than 75% for MP Board "
        "or 85% or more for CBSE Board. "
        "Family income should be less than Rs. 8 lakh. "
        "Student should pass all courses in Semester 1 and Semester 2.",

        "Specific required documents were not provided.",

        "All Categories",

        "Scholarship information provided for Sahayak."
    ),

    (
        "MP TAS",

        "No predefined eligibility as such according to the "
        "information provided.",

        "12th marksheet, character certificate, domicile certificate, "
        "caste certificate.",

        "OBC, SC/ST",

        "Category and document information provided for Sahayak."
    ),

    (
        "Awas Yojna",

        "Applicable for SC/ST according to the information provided.",

        "Specific required documents were not provided.",

        "SC/ST",

        "Further eligibility information was not provided."
    )
]

cursor.executemany("""
INSERT INTO scholarships (
    scholarship_name,
    eligibility,
    required_documents,
    category,
    notes
)
VALUES (?, ?, ?, ?, ?)
""", scholarship_data)

print("Scholarship data inserted.")


# =========================================================
# SAVE ALL DATA
# =========================================================

conn.commit()

print()
print("==========================================")
print(" Sahayak service data added successfully!")
print("==========================================")
print("Exam records        :", len(exam_data))
print("Fee records         :", len(fee_data))
print("Library records     :", len(library_data))
print("Hostel records      :", len(hostel_data))
print("Scholarship records :", len(scholarship_data))
print("==========================================")

conn.close()

print("Database connection closed.")
print("Done!")