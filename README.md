# TechWiz 7 — SkillSprint AI

Dual-Pipeline AI Document Verification System for Personalized Onboarding.

SkillSprint AI turns a company's internal documents (policies, SOPs, handbooks, job descriptions) into learning paths for each job position. HR uploads documents and generates a path. A Reviewer checks that every lesson, task and quiz question is backed by a verbatim quote from the source, then publishes the path to a department or position. Employees study the path stage by stage.

## Repository layout

| Folder / File | Content |
| :--- | :--- |
| `src/` | **Core Architecture**: document_processing, document_validation, genai_pipeline, prompt_templates, python_validation, role_matrix, comparison_engine, hallucination_checks, contradiction_checks, security ([src/README.md](src/README.md)) |
| `frontend/` | React + Vite web app for HR, Reviewer and Employee ([frontend/README.md](frontend/README.md)) |
| `backend/` | FastAPI API, SQLAlchemy + Alembic database, document ingestion, Gemini pipeline, server-side checks ([backend/README.md](backend/README.md)) |
| `tests/` | Root test suite (adversarial tests, comparison engine, consistency, document processing, rule engine) |
| `sample_documents/` | Corporate dataset DOC-01…DOC-28 (PDF, DOCX, MD, TXT, CSV), RD-01…RD-10, adversarial CTX samples ([sample_documents/README.md](sample_documents/README.md)) |
| `hidden_test_ready/` | Automated test harness for unseen evaluator documents |
| `documentation/` | Video demonstration script, presentation deck, database ERD, diagrams, and UI screenshots ([documentation/README.md](documentation/README.md)) |
| `reports/` | Official SRS submission deliverables: Project Report, Comparison CSV, Validation, Security, Technical Blog, and Team Records ([reports/README.md](reports/README.md)) |
| `AI_USAGE.md` | Complete declaration of AI assistance across development ([AI_USAGE.md](AI_USAGE.md)) |

Detailed setup and execution walkthrough: **[GETTING_STARTED.md](GETTING_STARTED.md)**

## Quick start

### Option 1: One-Click Docker (Recommended)

Run the entire production stack (PostgreSQL + FastAPI Backend + React Nginx Frontend) with a single command:

```bash
docker compose up --build -d
```

- **Frontend Application**: `http://localhost:3000`
- **Backend API Docs (Swagger)**: `http://localhost:8000/api/docs`
- **PostgreSQL Database**: Port `5432` (Auto-migrated, seeds 203 matrix rules, ingests 28 documents)

### Option 2: Local Development Setup

```powershell
# Backend  →  http://localhost:8000/api/docs
cd backend
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then set JWT_SECRET (and GEMINI_API_KEY to use Gemini)
python setup_database.py        # creates all tables, seeds users, role matrix and ingests 28 docs
uvicorn app.main:app --reload

# Frontend  →  http://localhost:3000
cd frontend
npm install
echo VITE_API_URL=http://localhost:8000/api > .env.local
npm run dev
```

Demo accounts (password `Demo@123` or `password123`):
- **Admin**: `admin@fourangrybirds.vn`
- **HR Manager**: `hr@fourangrybirds.vn`
- **Reviewer**: `reviewer@fourangrybirds.vn`
- **Employee**: `alex.morgan@fourangrybirds.vn` (or `sales.emp@fourangrybirds.vn`)

### Evaluator Note on Email Notifications (SMTP)
- **Real Gmail Delivery**: To test live email delivery when HR creates new employee accounts, configure `SMTP_USER` and `SMTP_PASSWORD` (16-character Google App Password) in `backend/.env`.
- **Zero-Setup Fallback**: If SMTP is unconfigured or offline, the system gracefully fallbacks by returning the generated temporary password directly on screen with a one-click copy button, ensuring 100% testability under all evaluation conditions.

## Tests

```powershell
cd backend;  pytest;  ruff check app tests alembic
cd frontend; npm test; npm run build
```
