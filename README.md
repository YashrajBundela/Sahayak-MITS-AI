# Sahayak-MITS-AI: An AI-Based Virtual Assistant for College Services

A web chatbot that answers student questions about timetables, exam schedules, fees, courses, library, hostel and scholarships. It answers from official college documents uploaded by an administrator, filtered by the student's **branch** and **semester**. If the requested file has not been uploaded, it says so instead of guessing.

Built at the Centre for Computer Science and Technology, Madhav Institute of Technology & Science (MITS), Gwalior, session July-Dec 2026.

**Team:**Yashraj Singh Bundela, Aditya Singh Rathore
**Supervisor:** Dr. Shradha Dubey

---

## Features

**For students**
- Sign in with the college Google account (stays signed in for 30 days)
- Save branch (CST, CSBS, CSE, IT) and semester
- Ask in plain language, e.g. `CST sem 3 show my college timetable`
- Branch and semester written in the question override the saved profile
- Timetables shown as real tables, including two-hour labs and the lunch column
- Voice input, read-aloud with a stop button, copy button
- Quick-question chips, typing indicator, dark and light theme

**For administrators**
- Upload PDF, TXT, MD, CSV, DOCX and XLSX files (up to 8 MB)
- Tag one file with several branches and semesters at once
- Knowledge library with delete, and dashboard statistics

**Document processing**
- Text extraction from PDFs, Word, Excel and text files
- Table extraction from PDFs with merged and empty cells kept correct
- OCR for scanned or badly encoded PDFs
- Document-type detection (timetable, date sheet, fee, calendar, syllabus) so the right kind of file is returned

---

## How it works

```
Browser (HTML, CSS, JavaScript)
        |
Flask application (Python): login, question understanding, search, upload
        |
SQLite database: courses, exam dates, fees, library, hostel,
                 scholarships, uploaded documents, student profiles
```

1. The question is cleaned, and the branch, semester and document type are detected.
2. Stored tables are checked for exam, course, library, hostel and scholarship topics.
3. Uploaded documents are scored by keyword matches, with extra weight for matching branch and semester.
4. Files of the wrong type and weak matches are removed.
5. The reply shows the table or text with its source file, or a clear "not uploaded yet" message.

---

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, Flask |
| Authentication | Authlib (Google OAuth) |
| Database | SQLite |
| PDF and file reading | pypdf, pdfplumber, openpyxl |
| OCR | RapidOCR (ONNX Runtime) |
| Frontend | HTML, CSS, JavaScript, Web Speech API |

---

## Getting started

### Requirements
- Python 3.10 or newer
- A Google OAuth client (Web application) from Google Cloud Console
- Chrome or Edge (voice input works in these browsers)

### Installation

```bash
      git clone https://github.com/YashrajBundela/Sahayak-MITS-AI.git
   cd Sahayak-MITS-AI


python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux / macOS
# source .venv/bin/activate

python -m pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in:

```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
SAHAYAK_SESSION_SECRET=any-long-random-string
SAHAYAK_ADMIN_EMAILS=admin1@mitsgwl.ac.in,admin2@mitsgwl.ac.in
```

In Google Cloud Console, add this Authorized redirect URI to the OAuth client:

```
http://127.0.0.1:5000/auth/callback
```

Generate a session secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Run

```bash
python app.py
```

Then open **http://127.0.0.1:5000** and sign in with the college Google account. 
Always use `127.0.0.1`, not `localhost`, so the login cookie stays valid.

---

## Using the assistant

**Student**
1. Sign in and choose your branch and semester, then Save Profile.
2. Ask a question or tap a quick chip.

Examples:
- `CST sem 3 show my college timetable`
- `CSBS sem 1 fee structure`
- `CST minor theory examination 3rd semester time table`
- `CST sem 3 academic calendar`

**Administrator**
1. Open **Admin Dashboard**.
2. Choose the file, then pick the branches and semesters it applies to.
3. Click **Upload Document**. Scanned PDFs are read with OCR, which can take several seconds.
4. Use the **Knowledge Library** to check or delete files.

---

## Project structure

```
app.py               Flask application: login, chat logic, upload, library, dashboard
database.py          Database setup and helpers
seed_data.py         Starting data
seed_services.py     Courses, exam dates, library, hostel, scholarships
templates/           login.html, index.html
static/              style.css, script.js, glow.css, glow.js
requirements.txt     Python packages
.env.example         Template for secrets
```

---

## Security notes

- Never commit `.env` or `sahayak.db`. They contain secret keys and student emails, and are listed in `.gitignore`.
- Login is limited to the college Google domain.
- Administrator pages require the administrator email list.

---

## Limitations

- Retrieval is keyword-based; differently worded questions can miss a file.
- No language model, so replies are stored text or tables, not written summaries.
- A file that covers several branches returns its whole content.
- OCR can misread tiny or Hindi text.
- Designed for a pilot on one machine with SQLite.

## Future scope

- Semantic search with embeddings and a vector database
- Language-model answers with source citations (RAG)
- Hindi and English text and speech
- Section-wise splitting of multi-branch documents
- ERP integration, mobile app and server deployment

---

## Acknowledgements

Flask, Authlib, pdfplumber, pypdf, openpyxl and RapidOCR for the open-source tools that made this project possible.
