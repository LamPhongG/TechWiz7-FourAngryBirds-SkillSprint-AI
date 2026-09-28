# SkillSprint AI — Setup & Execution Guide

Comprehensive setup and walkthrough guide for evaluators, team members, and developers to run the SkillSprint AI system from scratch.

## 1. Prerequisites

- **Option A: Docker (Recommended)**: Requires only **Docker Desktop** (includes Docker Compose).
- **Option B: Local Host Environment**:
  - Python: Version 3.11, 3.12, 3.13, or 3.14 (`python --version`)
  - Node.js: Version 18.x or newer with npm (`node -v` and `npm -v`)
  - Git: Installed and available in PATH (`git --version`)

## 2. Clone the Repository

Open your terminal and run:

```bash
git clone https://github.com/LamPhongG/TechWiz7-FourAngryBirds-SkillSprint-AI.git
cd TechWiz7-FourAngryBirds-SkillSprint-AI
```

---

## 3. Option 1: One-Click Docker Execution (Recommended for Evaluators)

The full production stack (PostgreSQL 16 + FastAPI Backend + React Nginx Frontend) is containerized and starts with one command:

```bash
docker compose up --build -d
```

- **Frontend Web Application**: Access at `http://localhost:3000`
- **Interactive Swagger API Docs**: Access at `http://localhost:8000/api/docs`
- **PostgreSQL Database**: Port `5432` (Automatically creates schema, runs migrations, seeds 203 matrix rules, and ingests all 28 documents).

To stop the containers:
```bash
docker compose down
```

---

## 4. Option 2: Manual Local Host Setup

### Step 2.1: Python Virtual Environment & Dependencies

We recommend creating a virtual environment:

On Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
pip install -r requirements.txt
```

On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r requirements.txt
```

### Step 2.2: Environment Configuration (.env)

Create the backend environment file from the provided template:

On Windows (PowerShell):
```powershell
copy backend\.env.example backend\.env
```

On macOS / Linux:
```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` to configure optional variables:
- `JWT_SECRET`: Secret key of at least 32 characters (generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
- `DATABASE_URL`: Defaults to SQLite (`backend/skillsprint.db`) if left empty, requiring zero server setup. Configure PostgreSQL connection string if running PostgreSQL.
- `GEMINI_API_KEY`: Enter your Google Gemini API key to call live Gemini models. If omitted, the system activates the pedagogical Python `local-draft` generator, ensuring 100% full application functionality offline.

### Step 2.3: Database Initialization & Ingestion of 28 Knowledge Documents

Run the unified setup command from the repository root:

```powershell
python setup_database.py
```

This automated script performs:
1. Creates all 13 database tables and relational constraints.
2. Seeds 10 standardized departments and 10 job positions.
3. Imports all 203 business rules from the Role Requirement Matrix.
4. Pre-creates default demo accounts (Admin, HR, Reviewer, Employee).
5. Ingests, parses, and chunks all 28 company documents from `sample_documents/` into searchable text chunks.
6. Seeds a demo completed learning path and employee certificate for immediate evaluation.

*Tip: To reset and recreate the database from scratch at any time, run:*
```powershell
python setup_database.py --reset
```

### Step 2.4: Frontend Installation & Launch

In a new terminal window:

```bash
cd frontend
npm install
npm run dev
```

The frontend SPA will be live at `http://localhost:3000`.

### Step 2.5: Backend Server Launch (FastAPI)

In the terminal with `.venv` activated:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Swagger UI Documentation: `http://localhost:8000/api/docs`

---

## 5. Demo Login Accounts

The default password for all demo accounts is `password123` (or `Demo@123`):

| Role | Login Email | Password | Evaluation Purpose |
|:---|:---|:---|:---|
| Admin | `admin@fourangrybirds.vn` | `password123` | User account management, audit logs, system overview |
| HR Manager | `hr@fourangrybirds.vn` | `password123` | Browse 28 documents, generate AI paths, assign employees |
| Reviewer | `reviewer@fourangrybirds.vn` | `password123` | Audit paths, Dual-Pipeline Comparison Table, approve/publish |
| Employee (In Progress) | `alex.morgan@fourangrybirds.vn` | `password123` | Read lessons, submit quizzes, track progress |
| Employee (Completed) | `sales.emp@fourangrybirds.vn` | `password123` | View 100% completed path, open digital Certificate |

---

## 6. Automated Test Suites (586 Tests)

The system is validated by 586 automated tests (100% passing rate):

1. **Backend API, Role Matrix & Authentication (390 tests)**:
```powershell
pytest backend/tests
```

2. **Core Algorithm Package, Chunking & Prompt Injection Defense (88 tests)**:
```powershell
pytest -o pythonpath=. tests
```

3. **Frontend Vitest Component & Logic Suite (108 tests)**:
```powershell
cd frontend
npm test -- --run
```

4. **Evaluator Hidden Document Readiness Test**:
```powershell
python hidden_test_ready/run_hidden_test.py
```

---

## 7. Troubleshooting

- **Port Conflict (8000 or 3000 already in use)**:
  - Terminate the conflicting process or launch with an alternative port (e.g. `--port 8001` for backend).
- **Module Import Error during pytest**:
  - Verify that your virtual environment `.venv` is activated and `pip install -r backend/requirements.txt` has completed.
- **Frontend Cannot Connect to Backend**:
  - Verify `frontend/.env.local` contains `VITE_API_URL=http://localhost:8000/api` and that the backend server is running on port 8000.
