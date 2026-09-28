# SkillSprint AI — Backend

FastAPI service for SkillSprint AI: authentication, document repository, learning path generation, human-in-the-loop review, employee learning progress tracking, and dual GenAI / Python rule pipelines.

> Updated: September 25, 2026 · Architect: Pham Tan Tai
> This document serves as the team's standard specification for backend development. All new code must follow these directory structures and conventions.

---

## 1. Local Setup and Execution

Prerequisite: **Python 3.12 or newer** (tested on Python 3.14).

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env            # macOS/Linux: cp .env.example .env
# Open .env and configure JWT_SECRET (generate using the command in .env.example)

alembic upgrade head              # Run schema migrations
python -m app.db.seed             # Seed 10 departments, 10 positions, and 3 demo accounts
uvicorn app.main:app --reload     # Swagger UI accessible at: http://localhost:8000/api/docs
```

- Default storage uses SQLite at `backend/skillsprint.db`. To switch to PostgreSQL, set `DATABASE_URL=postgresql+psycopg://...` in `.env`.
- Frontend connectivity: configure `frontend/.env.local` with `VITE_API_URL=http://localhost:8000/api`.
- Run test suite: `pytest` (executes against an isolated in-memory/temporary test database without altering development data).

Demo accounts (default password `Demo@123` / `password123`, stored as bcrypt hashes):

| Role | Email |
| :--- | :--- |
| HR Manager | `hr@fourangrybirds.vn` |
| Content Reviewer | `reviewer@fourangrybirds.vn` |
| Employee (Learner) | `alex.morgan@fourangrybirds.vn` |
| System Admin | `admin@fourangrybirds.vn` |

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application factory, CORS middleware, router registration at /api
│   ├── core/                # config.py (settings & environment), security.py (bcrypt, JWT tokens)
│   ├── db/                  # base.py (declarative Base, new_id, str_enum), session.py (engine, get_db), seed.py
│   ├── models/              # SQLAlchemy ORM models organized by business domain
│   ├── schemas/             # Pydantic schemas: API request and response data contracts
│   ├── api/
│   │   ├── deps.py          # Dependencies: DbSession, CurrentUser, require_roles(...)
│   │   ├── router.py        # Central API router aggregation
│   │   └── routes/          # Endpoint groupings (auth, documents, paths, users, reports, etc.)
│   ├── services/            # Domain logic: documents, paths, path_workflow, audit, visibility
│   ├── ingestion/           # Document extraction (PDF/DOCX/TXT/MD/CSV), chunking, magic-byte checks
│   ├── genai_pipeline/      # Pipeline 1: Gemini integration + structured prompts
│   ├── rule_pipeline/       # Pipeline 2: Pure deterministic Python (Role Matrix, coverage, prerequisites)
│   └── comparator/          # Cross-validation engine: dual-pipeline diff, hallucination, contradiction detection
├── alembic/                 # Schema migrations (manual SQL modifications prohibited)
├── tests/                   # Automated pytest suites
├── requirements.txt
└── .env.example
```

| Member | Primary Ownership |
| :--- | :--- |
| Pham Tan Tai | `core/`, `db/`, `models/`, `schemas/`, `api/`, `services/`, `alembic/` |
| Chau Quoc Lam Phong | `ingestion/`, `genai_pipeline/` |
| Doan Thi Quynh Nhi | `rule_pipeline/`, `comparator/`, `core/injection_filter.py` |
| Le Thi Kieu Duyen | `tests/` (adversarial attack scenarios, validation test sets) |

**Architecture Rule:** Pipeline modules **must not open database sessions or define web routes directly**. They take pure data structures (chunk lists, dicts) and return Pydantic models. HTTP route handlers in `api/routes/` invoke pipelines and handle database persistence. This ensures pipelines remain 100% testable in isolation.

---

## 3. Database Schema

13 tables managed via Alembic migrations (`alembic/versions/*_initial_schema.py`):

| Table | Purpose and Description |
| :--- | :--- |
| `departments` | 10 corporate departments. Primary key uses standardized English codes (`Engineering`, etc.) |
| `job_positions` | 10 job positions (`support-engineer`, etc.), linked to a parent department |
| `users` | Accounts: `user_role` (`admin`, `hr`, `reviewer`, `employee`), bcrypt password hash, department, position |
| `documents` | Document versions: identifier, `family`, version, effective/expiry dates, SHA-256 hash (deduplication), storage path, ingestion status |
| `document_chunks` | Chunks adhering to the contract `{doc_id, chunk_id, section_id, heading, page, content}` |
| `injection_flags` | Per-chunk adversarial prompt injection detection flags |
| `learning_paths` | Learning paths: status, revision, purpose, difficulty, target role; **stages → modules → lessons/tasks/quizzes stored in JSON `stages` column** |
| `path_sources` | Mapping of document versions used to synthesize the learning path |
| `path_assignments` | Publication scope targeted to specific departments and/or positions |
| `path_comments` | Reviewer ↔ HR feedback threads, attachable down to individual item level |
| `audit_logs` | Append-only audit trail. Foreign keys to learning paths are intentionally loose to preserve history upon draft deletion |
| `enrollments` | Employee onboarding and learning progress per assigned path |
| `quiz_attempts` | Submitted quiz examination records and server-side grading results |

**Rationale for storing path content in JSON rather than normalized `modules`/`tasks`/`quizzes` tables:**
- HR and Reviewers review, modify, and publish the **entire hierarchical tree** as an atomic unit.
- Each item carries its own self-contained `source_reference`.
- Relational decomposition creates excessive joins without transactional benefit during hierarchical editing.
- Employee progress points to stable item IDs within the JSON structure; published paths are immutable.

For detailed JSON schema specifications, see Section 7 of [reports/Project_Report.md](../reports/Project_Report.md).

---

## 4. API Endpoints

All endpoints are registered under **`/api`**. Interactive Swagger UI: `http://localhost:8000/api/docs`.

Authentication header: `Authorization: Bearer <access_token>`.

Business errors return standardized JSON: `{"detail": "...", "code": "err_...", "vars": {...}}`:
- `code` corresponds to frontend translation keys (`err_duplicate_file`, `err_action_not_allowed`, etc.).
- `detail` provides an English technical explanation as a fallback.
- Validation errors adhere to FastAPI's standard HTTP 422 Unprocessable Entity payload.

**System Administrator** (`admin@fourangrybirds.vn`) manages user accounts (`/users`) and has **read-only oversight** across all other domains (SRS Step 51): learning paths in all states, verification results, comparison matrices, documents and chunks, learners, reports, and audit logs. Administrators cannot upload documents, draft paths, submit for review, or approve paths. HR manages employee accounts only; administrator, HR, and reviewer account provisioning is reserved for Admin.

| Endpoint | Authorization | Status |
| :--- | :--- | :---: |
| `GET /ping`, `GET /health` (Database health check) | Public | ✅ |
| `POST /auth/login` → `{access_token, expires_in, user}` | Public | ✅ |
| `GET /auth/me` | Authenticated | ✅ |
| `POST /auth/change-password` `{current_password, new_password}` | Authenticated | ✅ |
| `POST /users/cv/parse` (multipart `file`: PDF, DOCX, TXT, MD) → profile draft; `POST /users/from-cv` → provision employee account, assign path, dispatch credentials | Admin, HR | ✅ |
| `GET /departments`, `GET /job-positions` | Authenticated | ✅ |
| `POST /paths/jobs`, `POST /paths/{id}/regenerate/jobs` → 202 Accepted + job; `GET /paths/jobs/{job_id}` | HR (job owner) | ✅ |
| `GET /job-positions/{id}/required-sources`: matrix mandatory sources resolved to active versions | HR, Reviewer | ✅ |
| `GET /documents`, `GET /documents/{id}` (includes `lifecycle_status`: active, obsolete, expired, upcoming) | Role-filtered | ✅ |
| `POST /documents` (multipart: `file` + metadata) → validate, store, extract, chunk, scan injection | HR | ✅ |
| `GET /documents/{id}/chunks`, `POST /documents/{id}/process`, `DELETE /documents/{id}` | HR (Reviewer view) | ✅ |
| `GET /documents/{id}/file` (inline viewer with `#page=N` support) | Document Viewer | ✅ |
| `GET /paths`, `GET /paths/{id}` (includes `allowed_actions` for current actor) | Role-filtered | ✅ |
| `POST /paths`, `PATCH /paths/{id}`, `DELETE /paths/{id}`, `/regenerate`, `/submit`, `/archive` | HR (Reviewer view) | ✅ |
| `POST /paths/{id}/comments`, `/comments/{cid}/resolve` | HR, Reviewer | ✅ |
| `GET /audit-logs?path_id=&action=&limit=&offset=` | HR, Reviewer | ✅ |
| `GET /me/enrollments`, `POST /me/enrollments/{path_id}/lessons/{lesson_id}`, `PUT …/tasks/{task_id}`, `POST …/quizzes/{module_id}` | Employee | ✅ |
| `GET /paths/{id}/enrollments` (roster of enrolled learners) | HR, Reviewer | ✅ |
| `GET /explore/paths`, `GET /explore/paths/{id}`, `POST /explore/paths/{id}/enroll` (self-enrollment) | Employee | ✅ |
| `POST /invite`, `GET /invite`, `DELETE /invite/{token}` | HR (creator only) | ✅ |
| `GET /invite/{token}`, `POST /invite/{token}/register` | Public (valid token) | ✅ |
| `/paths/{id}/approve` (triggers server-side re-verification), `/request-changes` | Reviewer | ✅ |
| `GET /paths/{id}/checks` (server-side verification report) | HR, Reviewer | ✅ |
| `GET /reports/comparison`, `GET /reports/comparison.csv` (Dual-pipeline comparison audit) | HR, Reviewer, Admin | ✅ |

---

## 5. Development Conventions

**Code Standards:**
- Code, docstrings, internal comments, and error messages must be written in **English**.
- Comments must explain *why* an architectural choice was made, not *what* the code does (Rules Section 1).
- Catch specific exceptions; never use bare `except Exception: pass`.
- Thin HTTP routes: validate permissions → delegate to service/pipeline → serialize schema. Shared business logic belongs in `services/`.
- Access control: `user: CurrentUser` for authenticated endpoints; `Depends(require_roles(UserRole.HR))` for role restriction. **All permissions and state transitions are strictly validated server-side**.
- Public entity IDs use prefixed nanoid/hex format: `new_id("LP")` → `LP-3F9A1C0B2E`.
- Database enums use `str_enum(EnumClass, "<column_name>")` to maintain uniform string storage with CHECK constraints across SQLite and PostgreSQL.
- Configuration and secrets are accessed exclusively via `get_settings()`; never hard-code strings or scatter raw `os.getenv` calls.

**Database Schema Changes:**
1. Modify or add models under `app/models/`. Register new models in `app/models/__init__.py`.
2. Generate migration: `alembic revision --autogenerate -m "describe change"`, then **review the generated script** before committing.
3. Apply migration: `alembic upgrade head` and execute test suite: `pytest`.
4. Commit model changes and Alembic migrations within the same git commit. **Never alter previously merged migrations**: apply changes via subsequent migration scripts.

---

## 6. Pipeline 1: Generative AI Path Generation (`app/genai_pipeline/`)

```
Source Documents (chunks with injection flags filtered out)
  └─ local_draft.generate      → Structural stage sequencing + fallback local draft
       └─ Per-module concurrent generation (GENERATION_WORKERS):
            Gemini Call 1: Lessons + Tasks (schemas.ModuleDraft)
            Gemini Call 2: Quizzes           (schemas.QuizDraft)
            grounding.py: Verify exact_quote against database chunks, discard invalid items
            Gemini failure → Fallback to local deterministic draft for that module
  └─ arrange_stages            → Template structuring (Day 1 → 90 Days / Foundation → Capstone)
  └─ learning_paths.generation → Audit telemetry: model, tokens, duration, discarded count
```

- **Local Fallback:** When `GEMINI_API_KEY` is not configured, the generator runs in deterministic local mode (`engine = local-draft`), synthesizing structured drafts from raw document chunks with verified citations.
- **Pedagogical Structure:** Stage and module hierarchy is determined by deterministic Python heuristics (`local_draft.plan_stages`), guaranteeing structural flow consistency.
- **Grounding Verification:**
  - `exact_quote` must exist verbatim within source chunks. If the model cites an incorrect `chunk_id`, the system re-indexes and maps it to the correct chunk.
  - Tasks lacking clear `completion_criteria` are automatically rejected (`task_no_criteria`).
  - Tasks asserting numeric thresholds unsupported by source chunks are discarded (`task_criteria_unsupported`).
  - Quizzes are discarded if the correct answer does not appear in the source quote or if distractors contain conflicting statements.
  - Citation metadata (`doc_id`, section, page) is populated strictly from the database, never trusted from model hallucinations.
- **Prompt Injection Defense:** Flagged chunks are omitted from model context windows. Inputs and outputs undergo secondary regex and semantic sanitization filters.

---

## 7. Pipeline 2: Python Deterministic Rule Engine (`app/rule_pipeline/`)

Pipeline 2 operates completely independent of AI:
- Evaluates the **Role Requirement Matrix** against synthesized modules.
- Calculates objective **Coverage Score** (% of mandatory position requirements addressed).
- Verifies policy precedence DAGs (e.g., Policy v2 > Policy v1, SOP > General FAQ).
- Validates prerequisite relationships and learning sequences (instruction must precede evaluation).

The results from Pipeline 1 and Pipeline 2 feed into the **Comparator Engine** (`app/comparator/`), producing the final dual-pipeline audit matrix exportable to CSV and visible in the Reviewer workspace.