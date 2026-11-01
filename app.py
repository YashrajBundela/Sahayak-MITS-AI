import os
import re
import io
import zipfile
import xml.etree.ElementTree as ET
import csv

from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    flash,
)

from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename

from database import get_db, init_db


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SAHAYAK_SESSION_SECRET",
    "CHANGE-THIS-SESSION-SECRET-BEFORE-USE"
)

app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

# Stay signed in for 30 days (survives closing the browser and normal restarts)
from datetime import timedelta
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

COLLEGE_DOMAIN = "mitsgwl.ac.in"

ALLOWED_DOCUMENT_EXTENSIONS = {
    "txt",
    "md",
    "csv",
    "docx",
    "pdf",
    "xlsx",
}

VALID_BRANCHES = {
    "CSE",
    "CST",
    "CSBS",
    "IT",
    "ECE",
    "EE",
    "ME",
    "CE",
    "AI_DS",
    "OTHER",
    "ALL",
}

VALID_SEMESTERS = {
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "ALL",
}


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

try:
    from dotenv import load_dotenv

    load_dotenv()

except ImportError:
    pass


app.config["SECRET_KEY"] = os.environ.get(
    "SAHAYAK_SESSION_SECRET",
    app.config["SECRET_KEY"]
)


ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.environ.get(
        "SAHAYAK_ADMIN_EMAILS", ""
    ).split(",")
    if email.strip()
}


# =========================================================
# GOOGLE OAUTH CONFIGURATION
# =========================================================

oauth = OAuth(app)

GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID", ""
)

GOOGLE_CLIENT_SECRET = os.environ.get(
    "GOOGLE_CLIENT_SECRET", ""
)


if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:

    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,

        server_metadata_url=(
            "https://accounts.google.com/"
            ".well-known/openid-configuration"
        ),

        client_kwargs={
            "scope": "openid email profile"
        },
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

# Existing database records are preserved.
# The database module handles creation and migrations.

init_db()


# =========================================================
# ADMIN AUTHORIZATION
# =========================================================

def is_admin():

    email = session.get("user_email", "").lower()

    return bool(email) and email in ADMIN_EMAILS


def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("user_email"):

            return jsonify({
                "error": (
                    "Sign in with your college "
                    "Google account first."
                )
            }), 401

        if not is_admin():

            return jsonify({
                "error": (
                    "Admin access is not enabled "
                    "for this account."
                )
            }), 403

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# REQUIRE COLLEGE LOGIN
# =========================================================

@app.before_request
def require_college_login():

    allowed_endpoints = {
        "login",
        "google_login",
        "google_callback",
        "static",
    }

    if request.endpoint in allowed_endpoints:
        return None

    if request.endpoint is None:
        return None

    if not session.get("user_email"):

        if request.path.startswith("/api/"):

            return jsonify({
                "error": (
                    "Please sign in with your "
                    "college Google account."
                )
            }), 401

        return redirect(url_for("login"))

    return None


# =========================================================
# LOGIN PAGE
# =========================================================

@app.route("/login")
def login():

    if session.get("user_email"):
        return redirect(url_for("home"))

    configured = bool(
        os.environ.get("GOOGLE_CLIENT_ID")
        and os.environ.get("GOOGLE_CLIENT_SECRET")
    )

    return render_template(
        "login.html",
        oauth_configured=configured
    )


# =========================================================
# GOOGLE SIGN-IN
# =========================================================

@app.route("/auth/google")
def google_login():

    if not (
        os.environ.get("GOOGLE_CLIENT_ID")
        and os.environ.get("GOOGLE_CLIENT_SECRET")
    ):

        flash(
            "Google Sign-In is not configured yet. "
            "Add GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET to your .env file.",
            "error"
        )

        return redirect(url_for("login"))

    redirect_uri = url_for(
        "google_callback",
        _external=True
    )

    return oauth.google.authorize_redirect(
        redirect_uri,
        hd=COLLEGE_DOMAIN
    )


# =========================================================
# GOOGLE OAUTH CALLBACK
# =========================================================

@app.route("/auth/callback")
def google_callback():

    try:

        token = oauth.google.authorize_access_token()

        user = (
            token.get("userinfo")
            or oauth.google.userinfo()
        )

    except Exception:

        app.logger.exception(
            "Google OAuth callback failed"
        )

        flash(
            "Google Sign-In could not be completed. "
            "Please try again.",
            "error"
        )

        return redirect(url_for("login"))

    email = str(
        user.get("email", "")
    ).strip().lower()

    email_verified = (
        user.get("email_verified") is True
        or str(
            user.get("email_verified", "")
        ).lower() == "true"
    )

    hosted_domain = str(
        user.get("hd", "")
    ).strip().lower()

    # Only verified college email addresses are accepted.
    if (
        not email
        or not email_verified
        or "@" not in email
        or email.rsplit("@", 1)[-1] != COLLEGE_DOMAIN
        or (
            hosted_domain
            and hosted_domain != COLLEGE_DOMAIN
        )
    ):

        session.clear()

        flash(
            "Access denied. Sign in using a verified "
            f"@{COLLEGE_DOMAIN} Google account.",
            "error"
        )

        return redirect(url_for("login"))

    session.clear()

    session.permanent = True
    session["user_email"] = email

    session["user_name"] = str(
        user.get("name")
        or email.split("@")[0]
    )

    session["is_admin"] = email in ADMIN_EMAILS

    return redirect(url_for("home"))


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# STUDENT BRANCH AND SEMESTER PREFERENCES
# =========================================================

@app.route(
    "/api/student/preferences",
    methods=["GET"]
)
def get_student_preferences():

    email = session.get("user_email")

    if not email:

        return jsonify({
            "error": "Please sign in first."
        }), 401

    conn = get_db()

    try:

        row = conn.execute(
            """
            SELECT branch, semester
            FROM student_preferences
            WHERE user_email = ?
            """,
            (email,)
        ).fetchone()

        return jsonify({
            "success": True,
            "branch": row["branch"] if row else "",
            "semester": row["semester"] if row else "",
        })

    finally:

        conn.close()


@app.route(
    "/api/student/preferences",
    methods=["POST"]
)
def save_student_preferences():

    email = session.get("user_email")

    if not email:

        return jsonify({
            "error": "Please sign in first."
        }), 401

    data = request.get_json(silent=True) or {}

    branch = str(
        data.get("branch", "")
    ).strip().upper()

    semester = str(
        data.get("semester", "")
    ).strip().upper()

    if (
        branch not in VALID_BRANCHES - {"ALL"}
        or semester not in VALID_SEMESTERS - {"ALL"}
    ):

        return jsonify({
            "error": "Select a valid branch and semester."
        }), 400

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO student_preferences (
                user_email,
                branch,
                semester,
                updated_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)

            ON CONFLICT(user_email)
            DO UPDATE SET
                branch = excluded.branch,
                semester = excluded.semester,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                email,
                branch,
                semester
            )
        )

        conn.commit()

        return jsonify({
            "success": True,
            "branch": branch,
            "semester": semester,
            "message": "Your preferences have been saved."
        })

    except Exception:

        conn.rollback()

        app.logger.exception(
            "Unable to save student preferences"
        )

        return jsonify({
            "error": "Could not save preferences."
        }), 500

    finally:

        conn.close()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html",
        user_email=session.get("user_email", ""),
        user_name=session.get("user_name", "Student"),
        user_is_admin=is_admin()
    )
# =========================================================
# GENERAL HELPERS
# =========================================================

def normalize_text(value):
    """Normalize text for basic case-insensitive searching."""

    value = str(value or "").lower()
    value = re.sub(r"\s+", " ", value)

    return value.strip()



def split_meta(value):
    """'CST,CSBS' -> {'CST','CSBS'} (branch/semester of a document may list several)."""
    return {p.strip().upper() for p in str(value or "").split(",") if p.strip()}


def meta_has(stored, value):
    parts = split_meta(stored)
    return "ALL" in parts or str(value).strip().upper() in parts


def parse_meta_list(raw, valid):
    parts = [p.strip().upper() for p in str(raw or "ALL").split(",") if p.strip()]
    if not parts or "ALL" in parts:
        return "ALL"
    if any(p not in valid for p in parts):
        return None
    return ",".join(sorted(set(parts), key=lambda x: (len(x), x)))

BRANCH_ALIASES = {
    "CSBS": ["csbs", "computer science and business", "computer science & business", "business system"],
    "CST": ["cst", "computer science and technology", "computer science & technology"],
    "IT": ["information technology"],
    "CSE": ["cse", "computer science and engineering", "computer science & engineering"],
}
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8"}
ORDINAL = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
           "sixth": "6", "seventh": "7", "eighth": "8"}


def detect_branch(question):
    """Branch named in the question (specific names checked before CSE)."""
    q = " " + normalize_text(question) + " "
    for code in ("CSBS", "CST", "CSE", "IT"):
        for alias in BRANCH_ALIASES[code]:
            if code == "IT" or len(alias) <= 4:
                if re.search(r"\b" + re.escape(alias) + r"\b", q):
                    return code
            elif alias in q:
                return code
    return None


def semester_number(value):
    """'III Semester', 'sem 3', '3rd', 'third' -> '3' (or None)."""
    v = normalize_text(value)
    m = re.search(r"\b([1-8])(?:st|nd|rd|th)?\b", v)
    if m:
        return m.group(1)
    for word in re.findall(r"[a-z]+", v):
        if word in ORDINAL:
            return ORDINAL[word]
        if word in ROMAN:
            return ROMAN[word]
    return None


def detect_semester(question):
    q = normalize_text(question)
    # "third year" means year 3 (semesters 5-6), not semester 3: only react to "sem".
    if not re.search(r"\bsem(?:ester)?\b|\bsem\d", q):
        return None
    return semester_number(q)


def get_student_preferences_for_email(email):
    """Return a student's saved branch and semester."""

    conn = get_db()

    try:
        row = conn.execute(
            """
            SELECT branch, semester
            FROM student_preferences
            WHERE user_email = ?
            """,
            (email,)
        ).fetchone()

        if not row:
            return None

        return {
            "branch": row["branch"],
            "semester": row["semester"]
        }

    finally:
        conn.close()

def get_document_matches(question, branch, semester, limit=5):
    """
    Search only documents explicitly classified for the student's
    branch and semester, or explicitly marked ALL.

    NULL and UNCLASSIFIED metadata are never treated as ALL.
    """

    branch = str(branch or "").strip().upper()
    semester = str(semester or "").strip()

    if branch not in VALID_BRANCHES - {"ALL"}:
        return []

    if semester not in {str(n) for n in range(1, 9)}:
        return []

    stop_words = {
        "what", "when", "where", "which", "who", "why", "how",
        "can", "could", "would", "the", "a", "an", "is", "are",
        "was", "were", "to", "for", "of", "in", "on", "and", "or",
        "please", "tell", "me", "about", "my", "our", "college",
        "give", "show", "find", "information", "details"
    }

    question_normalized = normalize_text(question).replace("time table", "timetable")

    keywords = [
        word
        for word in re.findall(r"[a-zA-Z0-9]+", question_normalized)
        if len(word) > 1 and word not in stop_words
    ]

    if not keywords:
        return []

    if "timetable" in keywords:
        keywords += ["time", "table", "schedule"]

    # plural/singular: "fees" should also find "fee"
    keywords += [w[:-1] for w in keywords if len(w) > 3 and w.endswith("s")]

    conn = get_db()

    try:
        rows = [
            r for r in conn.execute(
                "SELECT id, filename, content, branch, semester "
                "FROM knowledge_documents ORDER BY id DESC"
            ).fetchall()
            if meta_has(r["branch"], branch) and meta_has(r["semester"], semester)
        ]

        scored_documents = []

        for row in rows:
            filename = row["filename"] or ""
            content = row["content"] or ""

            searchable_text = normalize_text(
                filename + " " + content
            )

            normalized_filename = normalize_text(filename)

            content_score = sum(
                1 for keyword in keywords
                if keyword in searchable_text
            )

            filename_score = sum(
                2 for keyword in keywords
                if keyword in normalized_filename
            )

            score = content_score + filename_score

            if score <= 0:
                continue

            doc_branch = str(row["branch"] or "").strip().upper()
            doc_semester = str(row["semester"] or "").strip().upper()

            # Prefer documents classified specifically for this student.
            if branch in split_meta(doc_branch):
                score += 3

            if semester in split_meta(doc_semester):
                score += 5

            scored_documents.append({
                "id": row["id"],
                "filename": filename,
                "content": content,
                "score": score,
                "branch": doc_branch,
                "semester": doc_semester
            })

        scored_documents.sort(
            key=lambda item: (
                item["score"],
                item["semester"] == semester,
                item["branch"] == branch
            ),
            reverse=True
        )

        # If the question names a document type, answer only from that type.
        def doc_is(kind, d):
            name = normalize_text(d["filename"])
            body = d["content"]
            plain = re.sub(r"\[TABLES\].*?\[/TABLES\]", " ", body, flags=re.S)
            head = normalize_text(plain[:1500])
            if kind == "timetable":
                return bool(
                    re.search(r"time\s*table|timetable", name)
                    or re.search(r"time\s*table|timetable", normalize_text(body[:6000]))
                    or (re.search(r"\bMON\b", body) and re.search(r"\bTUE\b", body) and re.search(r"\d\d:\d\d", body))
                )
            if kind == "datesheet":
                return bool(re.search(r"date\s*sheet|datesheet|examination|exam", name + " " + head))
            if kind == "calendar":
                return bool(re.search(r"calendar", name + " " + head))
            if kind == "syllabus":
                return bool(re.search(r"syllabus|scheme", name + " " + head))
            if kind == "fee":
                return bool(re.search(r"\bfees?\b", name + " " + head))
            return True

        intents = {
            "timetable": r"time\s*table|timetable",
            "datesheet": r"date\s*sheet|datesheet",
            "calendar": r"calendar",
            "syllabus": r"syllabus|scheme",
            "fee": r"\bfees?\b",
        }
        for key, pattern in intents.items():
            if re.search(pattern, question_normalized):
                # asked for a specific document type: never substitute another type
                scored_documents = [d for d in scored_documents if doc_is(key, d)]

                if key == "timetable" and re.search(r"exam|minor|major|quiz|date\s*sheet", question_normalized):
                    scored_documents = [
                        d for d in scored_documents
                        if doc_is("timetable", d) or doc_is("datesheet", d)
                    ]
                elif key == "timetable":
                    # class timetable wanted: drop exam schedules
                    scored_documents = [
                        d for d in scored_documents
                        if not re.search(r"exam|minor|major|quiz|date\s*sheet", normalize_text(d["filename"]))
                        and not re.search(r"date of exam|minor .*examination|major .*examination",
                                          normalize_text(re.sub(r"\[TABLES\].*?\[/TABLES\]", " ", d["content"], flags=re.S)[:1500]))
                    ]

                if key in ("timetable", "datesheet"):
                    specific = [
                        d for d in scored_documents
                        if "ALL" not in split_meta(d.get("branch")) and "ALL" not in split_meta(d.get("semester"))
                    ]
                    if specific:
                        scored_documents = specific
                break

        if scored_documents:
            top = scored_documents[0]["score"]
            scored_documents = [d for d in scored_documents if d["score"] >= 0.6 * top]

        return scored_documents[:limit]

    finally:
        conn.close()
def extract_relevant_passages(question, documents, max_passages=6):
    """
    Extract passages with meaningful overlap with the question.
    Returns no answer if no relevant passage is found.
    """

    stop_words = {
        "what", "when", "where", "which", "who", "why", "how",
        "can", "could", "would", "the", "a", "an", "is", "are",
        "was", "were", "to", "for", "of", "in", "on", "and", "or",
        "please", "tell", "me", "about", "my", "our", "college",
        "give", "show", "find", "information", "details"
    }

    question_words = [
        word for word in re.findall(
            r"[a-zA-Z0-9]+",
            normalize_text(question)
        )
        if len(word) > 1 and word not in stop_words
    ]

    if not question_words:
        return []

    passages = []

    for document in documents:
        content = document.get("content", "")

        parts = re.split(
            r"(?<=[.!?])\s+|\n+",
            content
        )

        for part in parts:
            part = part.strip()

            if not part:
                continue

            normalized_part = normalize_text(part)

            matched_words = [
                word for word in set(question_words)
                if word in normalized_part
            ]

            if not matched_words:
                continue

            # A passage must contain meaningful question terms.
            score = len(matched_words)

            if score >= min(2, len(set(question_words))):
                passages.append({
                    "text": part,
                    "source": document["filename"],
                    "score": score,
                    "document_id": document["id"]
                })

    passages.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # Avoid returning the same passage more than once.
    results = []
    seen = set()

    for passage in passages:
        key = normalize_text(passage["text"])

        if key in seen:
            continue

        seen.add(key)
        results.append(passage)

        if len(results) >= max_passages:
            break

    return results

def search_service_tables(question, branch=None, semester=None):
    """
    Search existing structured college data.

    This provides basic keyword-based retrieval.
    It does not guarantee that every record is filtered
    by branch or semester.
    """

    q = normalize_text(question)

    conn = get_db()

    try:

        # -------------------------------------------------
        # EXAM DATES
        # -------------------------------------------------

        exam_keywords = [
            "exam", "examination", "date sheet",
            "datesheet", "mid sem", "mid-sem",
            "end sem", "end-sem", "practical",
            "result", "paper", "test", "quiz", "minor", "major"
        ]

        if any(word in q for word in exam_keywords):

            all_rows = conn.execute(
                """
                SELECT
                    exam_type,
                    exam_name,
                    exam_date,
                    exam_time,
                    branch,
                    semester,
                    venue,
                    instructions
                FROM exam_dates
                ORDER BY exam_date
                """
            ).fetchall()

            # "minor", "major", "theory"... named in the question must match the table row
            # itself; otherwise the answer belongs to the uploaded documents.
            type_words = re.findall(r"\b(minor|major|theory|practical|quiz|midterm|backlog|supplementary)\b", q)
            if type_words:
                all_rows = [
                    r for r in all_rows
                    if all(w in normalize_text((r["exam_type"] or "") + " " + (r["exam_name"] or "")) for w in type_words)
                ]
                if not all_rows:
                    return None

            rows = [
                r for r in all_rows
                if (not branch or (r["branch"] or "").strip().upper() in (branch, "ALL", ""))
                and (not semester or semester_number(r["semester"] or "") in (semester, None))
            ][:20]

            if not rows and all_rows:
                have = sorted({(r["branch"] or "?") for r in all_rows})
                return (
                    f"I don't have a date sheet for {branch or 'that branch'}"
                    f"{', Semester ' + semester if semester else ''} yet. "
                    f"Date sheets currently available for: {', '.join(have)}. "
                    "Ask your admin to upload the missing one."
                )

            if rows:

                results = []

                for row in rows:
                    results.append(
                        "Exam: {name}\n"
                        "Type: {type}\n"
                        "Date: {date}\n"
                        "Time: {time}\n"
                        "Branch: {branch}\n"
                        "Semester: {semester}\n"
                        "Venue: {venue}\n"
                        "Instructions: {instructions}".format(
                            name=row["exam_name"] or "Not specified",
                            type=row["exam_type"] or "Not specified",
                            date=row["exam_date"] or "Not specified",
                            time=row["exam_time"] or "Not specified",
                            branch=row["branch"] or "Not specified",
                            semester=row["semester"] or "Not specified",
                            venue=row["venue"] or "Not specified",
                            instructions=row["instructions"] or "None"
                        )
                    )

                return "\n\n".join(results)

        # -------------------------------------------------
        # TIMETABLE
        # -------------------------------------------------

        timetable_keywords = [
            "timetable", "time table", "schedule",
            "lecture", "class timing", "class time",
            "which class", "today's class", "today class"
        ]

        if any(word in q for word in timetable_keywords):

            rows = conn.execute(
                """
                SELECT
                    day,
                    start_time,
                    end_time,
                    course_code,
                    course_name,
                    room,
                    faculty
                FROM timetable
                ORDER BY day, start_time
                LIMIT 30
                """
            ).fetchall()

            if not rows:
                return None

            if rows:

                results = []

                for row in rows:
                    results.append(
                        "{day}: {start} - {end}\n"
                        "Subject: {subject}\n"
                        "Course code: {code}\n"
                        "Room: {room}\n"
                        "Faculty: {faculty}".format(
                            day=row["day"] or "Not specified",
                            start=row["start_time"] or "Not specified",
                            end=row["end_time"] or "Not specified",
                            subject=row["course_name"] or "Not specified",
                            code=row["course_code"] or "Not specified",
                            room=row["room"] or "Not specified",
                            faculty=row["faculty"] or "Not specified"
                        )
                    )

                return "\n\n".join(results)

        # -------------------------------------------------
        # COURSES
        # -------------------------------------------------

        course_keywords = [
            "course", "subject", "syllabus",
            "credit", "course code", "curriculum"
        ]

        if any(word in q for word in course_keywords):

            rows = conn.execute(
                """
                SELECT course_code, course_name, course_type
                FROM courses
                ORDER BY course_name
                LIMIT 50
                """
            ).fetchall()

            if rows:

                return "\n".join(
                    (
                        f"{row['course_name']} "
                        f"(Code: {row['course_code'] or 'N/A'}, "
                        f"Type: {row['course_type'] or 'N/A'})"
                    )
                    for row in rows
                )

        # -------------------------------------------------
        # FEES
        # -------------------------------------------------

        fee_keywords = [
            "fee", "fees", "tuition", "caution money",
            "payment", "semester fee", "college fee"
        ]

        if any(word in q for word in fee_keywords):

            fee_docs = [
                d for d in get_document_matches("fee structure", branch, semester, limit=10)
                if re.search(r"\bfees?\b", normalize_text(d["filename"] + " " + re.sub(r"\[TABLES\].*?\[/TABLES\]", " ", d["content"], flags=re.S)[:1500]))
            ]
            if not fee_docs:
                return (
                    f"The fee structure for {branch or 'your branch'}, "
                    f"Semester {semester or ''} has not been uploaded yet. "
                    "Please ask your college admin to upload it."
                )
            return None

            rows = conn.execute(
                """
                SELECT
                    semester,
                    total_fee,
                    caution_money,
                    total_including_caution,
                    notes
                FROM fees
                ORDER BY semester
                """
            ).fetchall()

            if rows:

                results = []

                for row in rows:
                    results.append(
                        "Semester: {semester}\n"
                        "Total fee: {fee}\n"
                        "Caution money: {caution}\n"
                        "Total including caution: {total}\n"
                        "Notes: {notes}".format(
                            semester=row["semester"] or "Not specified",
                            fee=(
                                row["total_fee"]
                                if row["total_fee"] is not None
                                else "Not available"
                            ),
                            caution=(
                                row["caution_money"]
                                if row["caution_money"] is not None
                                else "Not available"
                            ),
                            total=(
                                row["total_including_caution"]
                                if row["total_including_caution"] is not None
                                else "Not available"
                            ),
                            notes=row["notes"] or "None"
                        )
                    )

                return "\n\n".join(results)

        # -------------------------------------------------
        # LIBRARY
        # -------------------------------------------------

        library_keywords = [
            "library", "reading room",
            "library timing", "library time",
            "library open", "library close"
        ]

        if any(word in q for word in library_keywords):

            rows = conn.execute(
                """
                SELECT day, opening_time, closing_time, status
                FROM library_timings
                ORDER BY id
                """
            ).fetchall()

            if rows:

                return "\n\n".join(
                    (
                        f"Day: {row['day'] or 'Not specified'}\n"
                        f"Opening: {row['opening_time'] or 'Not specified'}\n"
                        f"Closing: {row['closing_time'] or 'Not specified'}\n"
                        f"Status: {row['status'] or 'Not specified'}"
                    )
                    for row in rows
                )

        # -------------------------------------------------
        # HOSTEL
        # -------------------------------------------------

        hostel_keywords = [
            "hostel", "accommodation", "room",
            "mess", "hostel fee", "hostel facility"
        ]

        if any(word in q for word in hostel_keywords):

            rows = conn.execute(
                """
                SELECT category, information
                FROM hostel
                ORDER BY id
                """
            ).fetchall()

            if rows:

                return "\n\n".join(
                    (
                        f"{row['category'] or 'Hostel information'}:\n"
                        f"{row['information'] or 'Not available'}"
                    )
                    for row in rows
                )

        # -------------------------------------------------
        # SCHOLARSHIPS
        # -------------------------------------------------

        scholarship_keywords = [
            "scholarship", "financial aid",
            "education loan", "stipend",
            "scholarship eligibility"
        ]

        if any(word in q for word in scholarship_keywords):

            rows = conn.execute(
                """
                SELECT
                    scholarship_name,
                    eligibility,
                    required_documents,
                    category,
                    notes
                FROM scholarships
                ORDER BY scholarship_name
                """
            ).fetchall()

            if rows:

                results = []

                for row in rows:
                    results.append(
                        "Scholarship: {name}\n"
                        "Category: {category}\n"
                        "Eligibility: {eligibility}\n"
                        "Required documents: {documents}\n"
                        "Notes: {notes}".format(
                            name=row["scholarship_name"] or "Not specified",
                            category=row["category"] or "Not specified",
                            eligibility=row["eligibility"] or "Not specified",
                            documents=row["required_documents"] or "Not specified",
                            notes=row["notes"] or "None"
                        )
                    )

                return "\n\n".join(results)

        return None

    finally:
        conn.close()


# =========================================================
# CHAT API
# =========================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    email = session.get("user_email")

    if not email:

        return jsonify({
            "error": "Please sign in with your college account."
        }), 401

    data = request.get_json(silent=True) or {}

    question = str(
        data.get("message", "")
    ).strip()

    if not question:

        return jsonify({
            "error": "Please enter a question."
        }), 400

    if len(question) > 2000:

        return jsonify({
            "error": "Your question is too long. Please shorten it."
        }), 400

    preferences = get_student_preferences_for_email(email)

    if not preferences:

        return jsonify({
            "reply": (
                "Before asking questions, please select your "
                "branch and semester in your profile settings."
            ),
            "needs_preferences": True
        })

    branch = detect_branch(question) or preferences["branch"]
    semester = detect_semester(question) or preferences["semester"]

    # First search structured college information.
    try:

        service_answer = search_service_tables(question, branch, semester)

        if service_answer:

            return jsonify({
                "reply": service_answer,
                "source": "college_database"
            })

    except Exception:

        app.logger.exception(
            "College database search failed"
        )

    # Then search branch- and semester-relevant documents.
    try:

        documents = get_document_matches(
            question,
            branch,
            semester,
            limit=5
        )

        if documents:

            answer_parts = []

            for document in documents:

                content = document["content"].strip()
                m = re.search(r"\[TABLES\](.*?)\[/TABLES\]", content, re.S)
                wants_table = re.search(r"time\s*table|timetable|date\s*sheet|schedule", question.lower())

                if m and wants_table:
                    body = m.group(1).strip()
                else:
                    content = re.sub(r"\[/?TABLES\]", "", content).strip()
                    body = content[:3500] + ("..." if len(content) > 3500 else "")

                answer_parts.append(f"{body}\n\n(Source: {document['filename']})")

            reply = (
                f"Here is what I found for {branch}, Semester {semester}:\n\n"
                + "\n\n---\n\n".join(answer_parts)
            )

            return jsonify({
                "reply": reply,
                "source": "knowledge_documents",
                "documents": [
                    document["filename"]
                    for document in documents
                ]
            })

    except Exception:

        app.logger.exception(
            "Knowledge document search failed"
        )

    available = []
    try:
        _c = get_db()
        available = [r["filename"] for r in _c.execute(
            "SELECT filename, branch, semester FROM knowledge_documents").fetchall()
            if meta_has(r["branch"], branch) and meta_has(r["semester"], semester)]
        _c.close()
    except Exception:
        pass
    hint = ("\n\nDocuments I can search for you: " + ", ".join(available)) if available else (
        "\n\nNo documents are uploaded for " + f"{branch}, Semester {semester} yet.")

    return jsonify({
        "reply": (
            "I couldn't find a matching answer in the college "
            "database or in documents available for your branch "
            f"({branch}) and semester ({semester}). "
            "Please try different keywords, or ask your college "
            "admin to upload the relevant information." + hint
        ),
        "source": "no_match"
    })





# =========================================================
# DOCUMENT TEXT EXTRACTION
# =========================================================

OCR_FIXES = {
    "Computcr": "Computer", "Cormputer": "Computer", "Conputer": "Computer",
    "Progranming": "Programming", "Prograinming": "Programming",
    "Scicnce": "Science", "Busincss": "Business", "Systcms": "Systems",
}


def clean_ocr_words(text):
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)      # ComputerScience -> Computer Science
    text = re.sub(r"\b(and|of|to)(?=[A-Z])", r"\1 ", text)
    text = re.sub(r"\b(Dr|Mr|Ms|Mrs)\.(?=\S)", r"\1. ", text)
    for wrong, right in OCR_FIXES.items():
        text = text.replace(wrong, right)
    return text


DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]


def timetable_from_ocr(items, lines, widths=None):
    """Build a Day x Time grid straight from OCR boxes (items = (cx, cy, text))."""
    import difflib

    rng = r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}"
    times = []
    for cx, cy, t in items:
        found = re.findall(rng, t)
        if not found:
            continue
        w = (widths or {}).get((cx, cy, t), 0)
        for k, f in enumerate(found):          # one box may hold two slots
            x = cx - w / 2 + w * (k + 0.5) / len(found) if len(found) > 1 else cx
            times.append((x, cy, re.sub(r"\s*-\s*", "-", f)))
    if len(times) < 4:
        return ""
    times.sort()

    # a header that OCR missed completely leaves a double-width gap: insert placeholder slots
    gaps = sorted(times[i + 1][0] - times[i][0] for i in range(len(times) - 1))
    typical = gaps[len(gaps) // 2]
    filled = [times[0]]
    for nxt in times[1:]:
        missing = round((nxt[0] - filled[-1][0]) / typical) - 1
        for m in range(1, missing + 1):
            filled.append((filled[-1][0] + (nxt[0] - filled[-1][0]) / (missing - m + 2), nxt[1], ""))
        filled.append(nxt)
    times = filled

    def start_hour(label):
        m = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$", label)
        if m and m.group(2) == m.group(4) == "00" and 1 <= int(m.group(1)) <= 12 \
                and int(m.group(3)) == int(m.group(1)) % 12 + 1:
            return int(m.group(1))
        return None

    def hour_label(h):
        s = (h - 1) % 12 + 1
        return f"{s:02d}:00-{s % 12 + 1:02d}:00"

    # rebuild unreadable/missing headers from a good neighbour (9,10,11,12,1,2,...)
    base = next(((i, start_hour(t[2])) for i, t in enumerate(times) if start_hour(t[2]) is not None), None)
    if base:
        times = [(x, y, l if start_hour(l) is not None else hour_label(base[1] + k - base[0]))
                 for k, (x, y, l) in enumerate(times)]

    header_y = sum(t[1] for t in times) / len(times)
    xs = [t[0] for t in times]
    left_limit = xs[0] - (xs[1] - xs[0]) * 0.9

    days = []
    for cx, cy, t in items:
        if cy > header_y + 20 and cx < left_limit + (xs[1] - xs[0]) * 0.4 and re.fullmatch(r"[A-Za-z]{3}", t.strip()):
            m = difflib.get_close_matches(t.strip().upper(), DAY_NAMES, n=1, cutoff=0.6)
            if m:
                days.append((cy, m[0]))
    days.sort()
    if len(days) < 3:
        return ""

    gap = sum(days[i + 1][0] - days[i][0] for i in range(len(days) - 1)) / (len(days) - 1)
    bounds = [header_y + 20] + [(days[i][0] + days[i + 1][0]) / 2 for i in range(len(days) - 1)] + [days[-1][0] + gap / 2]
    width = (xs[-1] - xs[0]) / (len(xs) - 1)
    col_edges = [xs[0] - width / 2] + [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)] + [xs[-1] + width / 2]

    grid = [[[] for _ in xs] for _ in days]
    for cx, cy, t in items:
        if cx < col_edges[0] or cx > col_edges[-1] or cy < bounds[0] or cy > bounds[-1]:
            continue
        row = next(i for i in range(len(days)) if bounds[i] <= cy <= bounds[i + 1])
        col = min(range(len(xs)), key=lambda j: abs(xs[j] - cx))
        cols = [col]
        # text sitting on a column boundary belongs to a merged (2-slot) cell
        nearest_edge = min(range(1, len(xs)), key=lambda j: abs(col_edges[j] - cx))
        if abs(col_edges[nearest_edge] - cx) < width * 0.22:
            cols = [nearest_edge - 1, nearest_edge]
        for c in cols:
            grid[row][c].append((cy, cx, t))

    def cell(parts):
        parts.sort()
        out, last = [], None
        for cy, cx, t in parts:
            out.append(t)
        return " ".join(dict.fromkeys(out)) if len(set(out)) < len(out) else " ".join(out)

    table = [[re.sub(r"\bM(\d{3})\b", r"M \1", cell(c)) for c in row] for row in grid]
    # lunch column: only single letters (L U N C H) -> LUNCH
    for j in range(len(xs)):
        col_parts = [t for row in grid for _, _, t in row[j]]
        if col_parts and all(len(t) == 1 for t in col_parts):
            for i in range(len(days)):
                table[i][j] = "LUNCH"

    header = ["DAY"] + [t[2] for t in times]
    md = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for (cy, d), row in zip(days, table):
        md.append("| " + " | ".join([d] + [c.replace("|", "/") for c in row]) + " |")

    legend = []
    for line in lines:
        for part in re.split(r"\s(?=[A-Z]{2,3}\s?:)|\s(?=\d{8}\s)", line):
            part = clean_ocr_words(part.strip())
            if re.match(r"^[A-Z]{2,3}\s?:", part):
                legend.append(re.sub(r"\s*:\s*", ": ", part, count=1))
            elif re.match(r"^\d{8}\s+[A-Za-z]{3,}", part):
                legend.append(re.sub(r"^(\d{8})\s+", r"\1 - ", part))
    return "\n".join(md) + "\n\n" + "\n".join(legend)


_OCR_ENGINE = None


def ocr_pdf(raw_bytes, max_pages=6):
    """OCR for image-only PDFs. Returns (plain_text, tables_markdown).

    Text boxes found by OCR are placed into the PDF's own table cells, so empty
    slots, merged cells and the lunch column stay in the right place.
    """
    global _OCR_ENGINE
    import numpy as np
    import pdfplumber
    from rapidocr_onnxruntime import RapidOCR

    if _OCR_ENGINE is None:
        _OCR_ENGINE = RapidOCR()

    dpi = 300
    scale = dpi / 72.0
    texts, tables = [], []

    def join(parts):
        parts = [p for p in parts if p]
        if parts and all(len(p) == 1 for p in parts):
            return "".join(parts)
        return " ".join(parts)

    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
        for page in pdf.pages[:max_pages]:
            image = page.to_image(resolution=dpi).original.convert("RGB")
            result, _ = _OCR_ENGINE(np.array(image))
            items = []
            widths = {}
            for box, txt, _score in (result or []):
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                item = (sum(xs) / 4, sum(ys) / 4, txt.strip())
                items.append(item)
                widths[item] = max(xs) - min(xs)

            # plain text: group boxes into lines by y position
            items.sort(key=lambda t: (t[1], t[0]))
            lines, current, last_y = [], [], None
            for cx, cy, txt in items:
                if last_y is not None and abs(cy - last_y) > 14:
                    lines.append(" ".join(t for _, t in sorted(current)))
                    current = []
                current.append((cx, txt))
                last_y = cy
            if current:
                lines.append(" ".join(t for _, t in sorted(current)))
            texts.append("\n".join(lines))

            def cell_text(bbox):
                x0, top, x1, bottom = [v * scale for v in bbox]
                inside = [(cy, cx, t) for cx, cy, t in items
                          if x0 <= cx <= x1 and top <= cy <= bottom]
                inside.sort()
                rows, last = [], None
                for cy, cx, t in inside:
                    if last is not None and abs(cy - last) < 14 and rows:
                        rows[-1].append((cx, t))
                    else:
                        rows.append([(cx, t)])
                    last = cy
                return join([" ".join(t for _, t in sorted(r)) for r in rows]) if rows and all(
                    len(t) == 1 for r in rows for _, t in r) is False else join(
                    [t for r in rows for _, t in sorted(r)])

            timetable_md = timetable_from_ocr(items, lines, widths)
            if timetable_md:
                tables.append(timetable_md)
                continue

            for table in page.find_tables():
                grid_rows = table.rows
                columns = table.columns
                if len(grid_rows) < 2 or len(columns) < 2:
                    continue
                cache = {}

                def text_of(i, j):
                    cell = grid_rows[i].cells[j]
                    if cell is not None:
                        if cell not in cache:
                            cache[cell] = cell_text(cell)
                        return cache[cell]
                    # merged cell: take text from the cell above or to the left that covers it
                    row_top = grid_rows[i].bbox[1]
                    for k in range(i - 1, -1, -1):
                        up = grid_rows[k].cells[j]
                        if up is not None and up[3] > row_top + 1:
                            return text_of(k, j)
                    col_x0 = columns[j].bbox[0]
                    for m in range(j - 1, -1, -1):
                        left = grid_rows[i].cells[m]
                        if left is not None and left[2] > col_x0 + 1:
                            return text_of(i, m)
                    return ""

                data = [[re.sub(r"\s+", " ", text_of(i, j)).replace("|", "/").strip()
                         for j in range(len(columns))] for i in range(len(grid_rows))]
                data = [r for r in data if any(r)]
                if len(data) < 2:
                    continue
                width = len(data[0])
                md = ["| " + " | ".join(data[0]) + " |", "|" + "---|" * width]
                md += ["| " + " | ".join(r) + " |" for r in data[1:]]
                tables.append("\n".join(md))

    return "\n\n".join(texts), "\n\n".join(tables)


def pdf_tables_markdown(raw_bytes):
    """Real table grids from a PDF as markdown pipe tables (empty cells kept)."""
    try:
        import pdfplumber
    except ImportError:
        return ""
    blocks = []
    try:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    # pdfplumber: None = cell covered by a merged cell, "" = really empty
                    grid = [list(r) for r in table]
                    for ri, row in enumerate(grid):
                        for ci, cell in enumerate(row):
                            if cell is None:
                                if ci > 0 and (row[ci - 1] or "").strip():
                                    row[ci] = row[ci - 1]          # merged to the left
                                elif ri > 0 and (grid[ri - 1][ci] or "").strip():
                                    row[ci] = grid[ri - 1][ci]     # merged from above (e.g. LUNCH)
                    rows = []
                    for row in grid:
                        clean = []
                        for c in row:
                            t = re.sub(r"\s+", " ", (c or "")).strip().replace("|", "/")
                            if re.fullmatch(r"(?:\S ){2,}\S", t):   # "L U N C H" -> "LUNCH"
                                t = t.replace(" ", "")
                            clean.append(t)
                        rows.append(clean)
                    rows = [r for r in rows if any(r)]
                    width = max((len(r) for r in rows), default=0)
                    if len(rows) < 2 or width < 2:
                        continue
                    rows = [r + [""] * (width - len(r)) for r in rows]
                    lines = ["| " + " | ".join(rows[0]) + " |",
                             "|" + "---|" * width]
                    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
                    blocks.append("\n".join(lines))
    except Exception:
        return ""
    return "\n\n".join(blocks)


def pdf_is_scanned(raw_bytes):
    """True when pages are mostly one big picture (a scan with a rough hidden text layer)."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages[:3]:
                area = float(page.width * page.height) or 1.0
                covered = sum(
                    max(0.0, (im["x1"] - im["x0"])) * max(0.0, (im["bottom"] - im["top"]))
                    for im in page.images
                )
                if covered / area > 0.6:
                    return True
    except Exception:
        pass
    return False


def text_looks_garbled(text):
    """Broken font encodings give words like MA$HAV or vfltryu$at."""
    tokens = re.findall(r"\S+", text or "")
    if len(tokens) < 20:
        return False
    bad = sum(
        1 for t in tokens
        if re.search(r"[A-Za-z][\$\*\{\}\[\]\^~`][A-Za-z]|[a-z][A-Z]{2,}[a-z]|^\*[a-z]+\*", t)
    )
    return bad >= 4 or bad / len(tokens) > 0.02


def extract_document_text(filename, raw_bytes):
    """
    Extract text from supported document formats.

    Supported:
        PDF, TXT, MD, CSV, DOCX, XLSX

    No paid external API is used.
    """

    extension = filename.rsplit(".", 1)[-1].lower()

    text = ""

    # -----------------------------------------------------
    # TXT AND MARKDOWN
    # -----------------------------------------------------

    if extension in {"txt", "md"}:

        try:
            text = raw_bytes.decode("utf-8-sig")

        except UnicodeDecodeError:
            text = raw_bytes.decode(
                "utf-8",
                errors="replace"
            )

    # -----------------------------------------------------
    # CSV
    # -----------------------------------------------------

    elif extension == "csv":

        decoded = raw_bytes.decode(
            "utf-8-sig",
            errors="replace"
        )

        reader = csv.reader(
            io.StringIO(decoded)
        )

        rows = []

        for row in reader:
            rows.append(" | ".join(row))

        text = "\n".join(rows)

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    elif extension == "pdf":

        try:
            from pypdf import PdfReader

        except ImportError as exc:
            raise ValueError(
                "PDF support is unavailable. "
                "Install the pypdf package."
            ) from exc

        reader = PdfReader(
            io.BytesIO(raw_bytes)
        )

        page_texts = []

        for page in reader.pages:

            page_texts.append(
                page.extract_text() or ""
            )

        text = "\n\n".join(page_texts)

        tables_md = pdf_tables_markdown(raw_bytes) if text.strip() else ""
        if tables_md:
            text = "[TABLES]\n" + tables_md + "\n[/TABLES]\n\n" + text

        # Scanned / broken-font PDFs: the built-in text layer is unreliable, so re-read with OCR
        need_ocr = (not text.strip()) or pdf_is_scanned(raw_bytes) or text_looks_garbled(text)

        if need_ocr:

            try:
                ocr_text, ocr_tables = ocr_pdf(raw_bytes)
            except ImportError:
                if text.strip():
                    ocr_text, ocr_tables = None, ""
                else:
                  raise ValueError(
                    "This PDF is an image (no selectable text). To read it, "
                    "install OCR support: python -m pip install rapidocr-onnxruntime "
                    "(then restart the server and upload again)."
                  )

            if ocr_text and ocr_text.strip():
                if ocr_tables:
                    ocr_text = "[TABLES]\n" + ocr_tables + "\n[/TABLES]\n\n" + ocr_text
                text = ocr_text

        if not text.strip():

            raise ValueError(
                "No text could be read from this PDF, even with OCR. "
                "Please upload a clearer file."
            )

    # -----------------------------------------------------
    # DOCX
    # -----------------------------------------------------

    elif extension == "docx":

        try:
            with zipfile.ZipFile(
                io.BytesIO(raw_bytes)
            ) as archive:

                xml_content = archive.read(
                    "word/document.xml"
                )

        except (
            zipfile.BadZipFile,
            KeyError
        ) as exc:

            raise ValueError(
                "This DOCX file is invalid or damaged."
            ) from exc

        root = ET.fromstring(xml_content)

        namespace = {
            "w": (
                "http://schemas.openxmlformats.org/"
                "wordprocessingml/2006/main"
            )
        }

        paragraphs = []

        for paragraph in root.findall(
            ".//w:p",
            namespace
        ):

            pieces = []

            for element in paragraph.iter():

                if element.tag.endswith("}t"):
                    pieces.append(
                        element.text or ""
                    )

                elif element.tag.endswith("}tab"):
                    pieces.append("\t")

                elif element.tag.endswith("}br"):
                    pieces.append("\n")

            paragraph_text = "".join(pieces)

            if paragraph_text.strip():
                paragraphs.append(paragraph_text)

        text = "\n".join(paragraphs)

    # -----------------------------------------------------
    # XLSX
    # -----------------------------------------------------

    elif extension == "xlsx":

        try:
            from openpyxl import load_workbook

        except ImportError as exc:

            raise ValueError(
                "Excel support is unavailable. "
                "Install the openpyxl package."
            ) from exc

        try:
            workbook = load_workbook(
                io.BytesIO(raw_bytes),
                read_only=True,
                data_only=True
            )

        except Exception as exc:

            raise ValueError(
                "This XLSX file is invalid or damaged."
            ) from exc

        try:

            sheet_texts = []

            for worksheet in workbook.worksheets:

                sheet_texts.append(
                    f"Sheet: {worksheet.title}"
                )

                for row in worksheet.iter_rows(
                    values_only=True
                ):

                    values = [
                        str(value)
                        if value is not None
                        else ""
                        for value in row
                    ]

                    if any(value.strip() for value in values):

                        sheet_texts.append(
                            " | ".join(values)
                        )

            text = "\n".join(sheet_texts)

        finally:

            workbook.close()

    else:

        raise ValueError(
            "Unsupported file type."
        )

    # -----------------------------------------------------
    # TEXT VALIDATION
    # -----------------------------------------------------

    text = text.replace("\x00", "").strip()

    if not text:

        raise ValueError(
            "No readable text was found in this file."
        )

    # Prevent very large extracted documents from
    # overwhelming the database or search response.
    max_characters = 1_000_000

    if len(text) > max_characters:

        raise ValueError(
            "The extracted document is too large. "
            "Please upload a document containing no more "
            "than 1,000,000 characters."
        )

    return text


# =========================================================
# ADMIN DOCUMENT LIST
# =========================================================

@app.route(
    "/api/admin/documents",
    methods=["GET"]
)
@admin_required
def list_documents():

    conn = get_db()

    try:

        rows = conn.execute(
            """
            SELECT
                id,
                filename,
                uploaded_at,
                branch,
                semester,
                LENGTH(content) AS characters
            FROM knowledge_documents
            ORDER BY uploaded_at DESC, id DESC
            """
        ).fetchall()

        documents = []

        for row in rows:

            documents.append({
                "id": row["id"],
                "filename": row["filename"],
                "uploaded_at": row["uploaded_at"],
                "branch": (
                    row["branch"]
                    or "ALL"
                ),
                "semester": (
                    row["semester"]
                    or "ALL"
                ),
                "characters": (
                    row["characters"]
                    or 0
                )
            })

        return jsonify({
            "success": True,
            "documents": documents,
            "count": len(documents)
        })

    except Exception:

        app.logger.exception(
            "Could not list knowledge documents"
        )

        return jsonify({
            "error": "Could not load documents."
        }), 500

    finally:

        conn.close()


# =========================================================
# ADMIN DOCUMENT UPLOAD
# =========================================================

@app.route(
    "/api/admin/documents",
    methods=["POST"]
)
@admin_required
def upload_document():

    if "file" not in request.files:

        return jsonify({
            "error": "Please select a file."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:

        return jsonify({
            "error": "No file was selected."
        }), 400

    filename = secure_filename(
        uploaded_file.filename
    )

    if not filename or "." not in filename:

        return jsonify({
            "error": "Invalid filename."
        }), 400

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:

        return jsonify({
            "error": (
                "Unsupported file type. "
                "Allowed formats: PDF, TXT, MD, CSV, "
                "DOCX and XLSX."
            )
        }), 400

    branch = parse_meta_list(request.form.get("branch", "ALL"), VALID_BRANCHES)
    semester = parse_meta_list(request.form.get("semester", "ALL"), VALID_SEMESTERS)

    if branch is None:
        return jsonify({"error": "Please select a valid branch."}), 400

    if semester is None:
        return jsonify({"error": "Please select a valid semester."}), 400

    raw_bytes = uploaded_file.read(
        app.config["MAX_CONTENT_LENGTH"] + 1
    )

    if not raw_bytes:

        return jsonify({
            "error": "The selected file is empty."
        }), 400

    if len(raw_bytes) > app.config["MAX_CONTENT_LENGTH"]:

        return jsonify({
            "error": "File size cannot exceed 8 MB."
        }), 413

    try:

        extracted_text = extract_document_text(
            filename,
            raw_bytes
        )

    except ValueError as exc:

        return jsonify({
            "error": str(exc)
        }), 400

    except Exception:

        app.logger.exception(
            "Document extraction failed"
        )

        return jsonify({
            "error": "Could not read the uploaded document."
        }), 500

    conn = get_db()

    try:

        cursor = conn.execute(
            """
            INSERT INTO knowledge_documents (
                filename,
                content,
                uploaded_at,
                branch,
                semester
            )
            VALUES (
                ?,
                ?,
                CURRENT_TIMESTAMP,
                ?,
                ?
            )
            """,
            (
                filename,
                extracted_text,
                branch,
                semester
            )
        )

        document_id = cursor.lastrowid

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Document uploaded successfully.",
            "document": {
                "id": document_id,
                "filename": filename,
                "branch": branch,
                "semester": semester,
                "characters": len(extracted_text)
            }
        }), 201

    except Exception:

        conn.rollback()

        app.logger.exception(
            "Document could not be saved"
        )

        return jsonify({
            "error": "Could not save the document."
        }), 500

    finally:

        conn.close()


# =========================================================
# ADMIN DOCUMENT DELETE
# =========================================================

@app.route(
    "/api/admin/documents/<int:document_id>",
    methods=["DELETE"]
)
@admin_required
def delete_document(document_id):

    conn = get_db()

    try:

        existing = conn.execute(
            """
            SELECT id, filename
            FROM knowledge_documents
            WHERE id = ?
            """,
            (document_id,)
        ).fetchone()

        if not existing:

            return jsonify({
                "error": "Document not found."
            }), 404

        conn.execute(
            """
            DELETE FROM knowledge_documents
            WHERE id = ?
            """,
            (document_id,)
        )

        conn.commit()

        return jsonify({
            "success": True,
            "message": (
                f"Deleted document: {existing['filename']}"
            )
        })

    except Exception:

        conn.rollback()

        app.logger.exception(
            "Document deletion failed"
        )

        return jsonify({
            "error": "Could not delete the document."
        }), 500

    finally:

        conn.close()


# =========================================================
# ADMIN DASHBOARD DATA
# =========================================================

@app.route(
    "/api/admin/data",
    methods=["GET"]
)
@admin_required
def admin_data():

    conn = get_db()

    try:

        table_names = [
            "courses",
            "timetable",
            "exam_dates",
            "fees",
            "library_timings",
            "hostel",
            "scholarships",
            "knowledge_documents",
            "student_preferences",
        ]

        counts = {}

        for table_name in table_names:

            # Table names come only from the fixed list above.
            row = conn.execute(
                f"SELECT COUNT(*) AS total FROM {table_name}"
            ).fetchone()

            counts[table_name] = row["total"]

        return jsonify({
            "success": True,
            "counts": counts,
            "admin_email": session.get("user_email")
        })

    except Exception:

        app.logger.exception(
            "Could not load admin dashboard data"
        )

        return jsonify({
            "error": "Could not load dashboard data."
        }), 500

    finally:

        conn.close()


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(413)
def request_entity_too_large(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "The uploaded file exceeds the 8 MB limit."
        }), 413

    return (
        "The uploaded file exceeds the 8 MB limit.",
        413
    )


@app.errorhandler(404)
def page_not_found(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "The requested API endpoint was not found."
        }), 404

    return (
        "Page not found.",
        404
    )


@app.errorhandler(500)
def internal_server_error(error):

    app.logger.exception(
        "An internal server error occurred"
    )

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "An internal server error occurred."
        }), 500

    return (
        "An internal server error occurred.",
        500
    )


# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

if __name__ == "__main__":

    # Local development only.
    # debug=False avoids enabling the interactive debugger.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
