# SkillSprint AI — Team Contribution Record
**Document Deliverable 18 | SRS Section 1.10.18 & Final Submission Checklist**
**Competition:** TechWiz 7 — Generative AI Powerplay Track
**Project:** SkillSprint AI (Dual-Pipeline AI Document Verification System)
**Team:** Four Angry Birds
**Date:** September 28, 2026

---

## 1. Team Roster & Functional Roles

| Member Name | Student ID | Academic Institution | Functional Role | Primary Module Ownership |
| :--- | :--- | :--- | :--- | :--- |
| **Chau Quoc Lam Phong** | SE171284 | FPT University | **Team Lead & AI Ingestion Engineer** | `src/genai_pipeline/`, `src/document_processing/`, `backend/app/genai_pipeline/`, prompt templates v1.0/v1.1 |
| **Doan Thi Quynh Nhi** | SE172045 | FPT University | **Backend & Rule Engine Lead** | `src/python_validation/`, `src/role_matrix/`, `src/comparison_engine/`, `src/hallucination_checks/`, `src/contradiction_checks/` |
| **Pham Tan Tai** | SE170912 | FPT University | **Fullstack & System Architect** | `frontend/` (React SPA), `backend/` (FastAPI + SQLAlchemy), `database/`, Docker deployment |
| **Le Thi Kieu Duyen** | SE173421 | FPT University | **QA, Security & Compliance Lead** | `tests/` (586 tests), `sample_documents/` (DOC-01..28, CTX-01..10), `reports/`, `AI_USAGE.md` |

---

## 2. Responsibility Assignment Matrix (RACI)

* **R (Responsible)**: Does the work to complete the task.
* **A (Accountable)**: Approves the deliverable and ensures quality.
* **C (Consulted)**: Provides input, architectural feedback, and reviews code.
* **I (Informed)**: Kept updated on progress and integration changes.

| Project Component / SRS Deliverable | Chau Quoc Lam Phong | Doan Thi Quynh Nhi | Pham Tan Tai | Le Thi Kieu Duyen |
| :--- | :---: | :---: | :---: | :---: |
| **Document Processing & Chunking** | **R / A** | C | C | I |
| **GenAI Pipeline & Prompt Engineering** | **R / A** | C | I | C |
| **Role Requirement Matrix & Python Rule Engine** | C | **R / A** | I | C |
| **Dual-Pipeline Comparison & Diff Engine** | C | **R / A** | C | I |
| **Hallucination & Contradiction Detection** | C | **R / A** | I | C |
| **FastAPI REST API & Database Models** | I | C | **R / A** | I |
| **React Vite Dashboard (HR / Reviewer / Employee)** | I | I | **R / A** | C |
| **Security, Input Sanitization & Prompt Injection Filter** | C | C | C | **R / A** |
| **Company Document Dataset (DOC-01..28, CTX-01..10)** | C | I | I | **R / A** |
| **Automated Testing Suite (586 Tests)** | C | C | C | **R / A** |
| **Project Reports & Submission Deliverables** | C | C | C | **R / A** |
| **Docker Compose Containerization & Deployment** | I | I | **R / A** | C |

---

## 3. Individual Contribution Breakdown Across 5 Competition Phases

### 3.1 Chau Quoc Lam Phong — Team Lead & AI Ingestion Engineer
- **Phase 1**: Initialized repository architecture, virtual environments, and baseline configuration. Built multi-format document parsers for PDF (`pypdf`), DOCX (`python-docx`), and Markdown. Implemented heading-aware semantic chunking with metadata propagation (`doc_id`, `section_id`, `page_number`).
- **Phase 2**: Implemented the Generative AI client interfacing with Google Gemini API (`gemini-1.5-flash` / `gemini-1.5-pro`). Developed versioned Prompt Templates (`v1.0` and `v1.1`) enforcing strict Pydantic JSON schemas. Implemented 3-attempt exponential backoff retry logic and offline mock fallback.
- **Phase 3**: Engineered the hierarchical generation pipeline (Stages → Modules → Tasks → Quizzes). Implemented exact-quote citation validation (`grounding.py`), verifying quotes against chunk text layers.
- **Phase 4**: Tuned generation parameters (temperature 0.1, strict response schemas). Added selective regeneration capabilities allowing single modules or tasks to be regenerated without recreating entire plans.
- **Phase 5**: Validated all 10 corporate onboarding plans against Gemini API. Reviewed and signed off on GenAI pipeline evidence (Deliverable 4).

### 3.2 Doan Thi Quynh Nhi — Backend & Rule Engine Lead
- **Phase 1**: Co-designed Pydantic schemas and comparison contracts (`src/schemas/comparison_contract.py`). Established rule validation interfaces.
- **Phase 2**: Authored the pure Python ground-truth validation engine with zero AI SDK dependencies. Implemented the canonical **Role Requirement Matrix** containing 203 structured rules across 10 corporate roles.
- **Phase 3**: Built the **Comparison Engine** (`src/comparison_engine/engine.py`), computing coverage scores, identifying missing mandatory rules, and generating requirement-level comparative diffs.
- **Phase 4**: Implemented **Hallucination Detection** algorithms (detecting ungrounded claims, synthetic hotlines, out-of-range thresholds) and **Contradiction Detection** algorithms with temporal supersession awareness (resolving v1.0 vs v2.0 conflicts).
- **Phase 5**: Generated Deliverable 6 (`reports/genai_python_comparison.csv`) evaluating 100+ requirement comparisons. Produced Deliverable 8 (`reports/validation_report.md`).

### 3.3 Pham Tan Tai — Fullstack & System Architect
- **Phase 1**: Architected SQLAlchemy ORM models, Alembic database migrations, and SQLite/PostgreSQL connection pools. Built comprehensive database seeding scripts (`setup_database.py`) loading 203 matrix rules, 28 ingested documents, and demo user accounts.
- **Phase 2**: Implemented FastAPI REST API endpoints for document management, role matrix administration, onboarding plan lifecycle, and employee progress tracking. Configured JWT authentication and role-based access control (RBAC).
- **Phase 3**: Developed the React + Vite single-page application from scratch using vanilla CSS and Tailwind tokens. Built tailored user experiences:
  * **HR Dashboard**: Document upload zone with drag-and-drop, role matrix explorer, new employee onboarding wizard.
  * **Reviewer Audit Dashboard**: Interactive dual-pipeline comparison view, color-coded hallucination/contradiction flags, one-click approve/reject actions.
  * **Employee Portal**: Personalized 30-day onboarding roadmap, interactive task checkboxes, module quiz engine.
- **Phase 4**: Added real-time CSV/JSON report export endpoints (`/api/reports/comparison.csv`, `/api/reports/validation.json`), SMTP email delivery service with fallback password preview, and dark/light UI theme support.
- **Phase 5**: Authored `docker-compose.yml` and `Dockerfile` configurations for backend, frontend (Nginx), and PostgreSQL. Verified production build and container orchestration.

### 3.4 Le Thi Kieu Duyen — QA, Security & Compliance Lead
- **Phase 1**: Curated and authored the company document dataset: employee handbooks (`DOC-01`, `DOC-02`), HR policies (`DOC-03`, `DOC-04`), IT security guidelines (`DOC-05`, `DOC-06`), and SOPs (`DOC-07` through `DOC-10`). Initialized `AI_USAGE.md` tracking log.
- **Phase 2**: Expanded the dataset with Phase 2 documents (`DOC-11` through `DOC-28`), covering departmental exceptions, brand guidelines, partner delivery SOPs, and procurement procedures. Created 10 adversarial test documents (`CTX-01` through `CTX-10`).
- **Phase 3**: Engineered the prompt injection filter (`src/security/injection_filter.py`), implementing regex pattern matching, Unicode normalization, and delimiter guardrails. Built unit test suites for security and injection defense.
- **Phase 4**: Authored the automated test suites: 390 backend Pytest tests, 88 root architectural tests, and 108 frontend Vitest tests (586 tests in total, 100% pass rate). Created the hidden test readiness harness (`hidden_test_ready/run_hidden_test.py`).
- **Phase 5**: Produced Deliverable 9 (`reports/security_testing_report.md`), Deliverable 16 (`reports/technical_blog.md`), Deliverable 1 (`reports/Project_Report.md`), Deliverable 15 (`documentation/demo_script.md`), and finalized all audit sign-offs.

---

## 4. Verification and Sign-Off

All four team members have independently reviewed, verified, and debugged the source code, tests, and documentation. No code was committed to the repository without peer review and automated test verification.

| Team Member | Signature / Sign-Off Date | Verification Statement |
| :--- | :--- | :--- |
| **Chau Quoc Lam Phong** | September 28, 2026 | Confirmed GenAI pipeline and document ingestion reliability. |
| **Doan Thi Quynh Nhi** | September 28, 2026 | Confirmed Python rule engine, matrix consistency, and comparison logic. |
| **Pham Tan Tai** | September 28, 2026 | Confirmed fullstack architecture, RBAC, database migrations, and Docker deployment. |
| **Le Thi Kieu Duyen** | September 28, 2026 | Confirmed test suite pass rate (586/586), security defenses, and report integrity. |
