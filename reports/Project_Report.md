# SkillSprint AI — Comprehensive Project Report
**Project:** SkillSprint AI – Dual-Pipeline AI Document Verification System  
**Track:** TechWiz 7 – Generative AI Powerplay Track  
**Team:** Four Angry Birds  
**Submission Deliverable:** Deliverable #1 – Project Report (SRS §1.10.1)  

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Introduction & Background](#2-introduction--background)
3. [System Scope, Purpose & Constraints](#3-system-scope-purpose--constraints)
4. [System Requirements](#4-system-requirements)
   - 4.1. Functional Requirements (FR i–lxvi)
   - 4.2. Non-Functional Requirements (NFR 1–5)
5. [System Architecture & Design](#5-system-architecture--design)
   - 5.1. Overall Architecture
   - 5.2. Data Flow Diagrams (DFD Level 0 & Level 1)
   - 5.3. Use Case Diagram
   - 5.4. Activity Diagram
   - 5.5. Sequence Diagram
   - 5.6. Database Design & Entity Relationship Diagram (ERD)
6. [Document-Processing Pipeline & Chunking](#6-document-processing-pipeline--chunking)
7. [Role Requirement Matrix & Competency Setup](#7-role-requirement-matrix--competency-setup)
8. [Pipeline 1 — Generative AI Pipeline](#8-pipeline-1--generative-ai-pipeline)
   - 8.1. Model Selection & Configuration
   - 8.2. Prompt Engineering & Versioning (v1.0 & v1.1)
   - 8.3. Pydantic Structured Output Schemas
   - 8.4. Source-Grounded Generation & Exact-Quote Enforcement
9. [Pipeline 2 — Deterministic Python Rule Engine](#9-pipeline-2--deterministic-python-rule-engine)
   - 9.1. Zero-AI Architecture Guarantee
   - 9.2. Coverage Score Algorithm
   - 9.3. Traceability Validation
   - 9.4. Prerequisite DAG & Instructional Sequence
10. [Dual-Pipeline Comparison Engine & Verification](#10-dual-pipeline-comparison-engine--verification)
   - 10.1. Field-by-Field Diff Comparison (Table 1)
   - 10.2. Verification Status Classification
   - 10.3. Human-in-the-Loop Review & Audit Trail
11. [Adversarial Defense & Security Engineering](#11-adversarial-defense--security-engineering)
   - 11.1. Hallucination Detection
   - 11.2. Contradiction Detection & Policy Precedence
   - 11.3. Dual-Language Prompt Injection Filter (EN & VI)
12. [Testing Strategy & Quantitative Results](#12-testing-strategy--quantitative-results)
13. [Deployment Architecture & Production Readiness](#13-deployment-architecture--production-readiness)
14. [Limitations & Future Enhancements](#14-limitations--future-enhancements)
15. [Conclusion](#15-conclusion)

---

## 1. Executive Summary

Enterprise employee onboarding requires assimilating extensive corporate knowledge bases: operational SOPs, regulatory compliance mandates, IT security policies, and departmental handbooks. Traditional onboarding approaches suffer from prolonged ramp-up periods, high administrative overhead, and cognitive fatigue. While applying commercial Large Language Models (LLMs) offers automated curriculum generation, standard LLM applications introduce unacceptable corporate risks: **hallucinated entitlements or policies**, **failure to address mandatory regulatory clauses**, and **vulnerability to adversarial prompt injections**.

**SkillSprint AI** resolves these risks through an innovative **Dual-Pipeline Ground-Truth Verification Architecture**:
- **Pipeline 1 (Generative AI Pipeline):** Employs Google Gemini with strict Pydantic Structured Output schemas and exact-quote grounding to synthesize modular onboarding curricula.
- **Pipeline 2 (Deterministic Python Rule Engine):** Completely decoupled from AI, executing pure deterministic algorithms against an objective Role Requirement Matrix (203 standardized rules across 10 corporate positions). It calculates Coverage Scores, enforces prerequisite Directed Acyclic Graphs (DAGs), and verifies chunk cryptographic hashes.
- **Comparator Engine:** Executes field-by-field cross-validation between GenAI claims and Python ground truth (SRS Table 1). Content is approved and published only when mandatory requirements achieve 100% verified coverage and zero hallucination flags.

The system is validated by **586 automated tests (100% pass rate)**, includes a catalog of 28 enterprise documents across multiple formats (PDF, DOCX, TXT, MD, CSV), and provides production Docker orchestration.

---

## 2. Introduction & Background

### 2.1. The Corporate Onboarding Dilemma
Modern enterprises face increasing complexity in workforce enablement:
1. **Knowledge Overload:** New recruits must absorb hundreds of pages of documentation across disparate repositories.
2. **Regulatory & Compliance Risk:** Missing mandatory safety, data privacy (e.g., GDPR/Decree 13), or information security clauses creates severe legal liability.
3. **Role Specialization:** Modern job roles require tailored curricula rather than generic company-wide overviews.

### 2.2. The Failure of Naive GenAI Approaches
Directly querying generic LLMs (such as ungrounded ChatGPT or Gemini prompts) introduces critical enterprise failure modes:
- **Hallucination:** Generative models synthesize plausible yet fabricated facts, such as fictitious reimbursement limits or unapproved leave allowances.
- **Inconsistent Output Structure:** Unstructured text output cannot be safely parsed into relational databases or automated LMS workflows.
- **Adversarial Exploitation:** Malicious or rogue documents containing prompt injection directives can override system instructions and hijack review approvals.

SkillSprint AI bridges the gap between AI flexibility and deterministic compliance verification.

---

## 3. System Scope, Purpose & Constraints

### 3.1. System Purpose
To provide an automated, source-grounded, and mathematically verified onboarding intelligence platform that transforms internal documents into personalized curricula for 10 distinct job roles while guaranteeing zero hallucinated policies.

### 3.2. Project Scope
- **In Scope:**
  - Multi-format ingestion and section-aware chunking (PDF, DOCX, TXT, MD, CSV).
  - Role-Based Access Control (Admin, HR Specialist, Content Reviewer, Employee).
  - Version lifecycle management (`active`, `superseded`, `expired`, `upcoming`).
  - Dual-pipeline generation and deterministic rule comparison.
  - Interactive learner portal with inline source citations, operational tasks, and server-graded quizzes.
  - Automated resume parsing (CV ingestion) and account provisioning.
  - Policy update detection, impact analysis, and selective regeneration.
- **Out of Scope:**
  - Direct integration with real-time financial payroll processing engines.
  - Optical Character Recognition (OCR) for degraded, unreadable scanned physical papers.

### 3.3. Technical Constraints
- Execution under Python 3.12+ and modern Node.js environments.
- Pipeline 2 must execute with strictly zero AI SDK dependencies.
- Zero credential leaks; API keys managed exclusively via environment variables.

---

## 4. System Requirements

### 4.1. Functional Requirements (FR i–lxvi Mapping)
The system satisfies all 66 functional requirements detailed in SRS Section 1.6:
- **Authentication & RBAC (FR i–iv):** JWT tokens, bcrypt encryption, role separation (Admin, HR, Reviewer, Employee), department assignment.
- **Document Management (FR v–ix):** Ingestion of PDF, DOCX, TXT, MD, CSV; magic-byte validation; SHA-256 deduplication; section chunking; lifecycle state tracking.
- **Role Requirement Matrix (FR x–xii):** Tabular specification of mandatory and optional requirements per role.
- **Curriculum Generation (FR xiii–xxvii):** Multi-stage timelines (Day 1, Week 1, Month 1, 90 Days); modules; checklists; practical tasks; grounded multiple-choice quizzes; difficulty levels (Beginner, Intermediate, Advanced); prerequisite enforcement.
- **Python Rule Engine (FR xxviii–xxxvi):** Coverage Score calculation, Traceability Score, hallucination detection, contradiction handling, duplicate content detection.
- **GenAI Structured Output (FR xxxvii–xli):** Pydantic schema enforcement, JSON parsing sanitizers, exponential backoff retries, prompt version tracking.
- **Adversarial Defense (FR xlii–xliii):** Dual-language prompt injection filtering (English & Vietnamese), adversarial test suite execution.
- **Cross-Validation & Review (FR xliv–xlix):** Dual-pipeline comparison matrix, status classification, Reviewer approval/override with mandatory audit logging.
- **Learner Experience (FR l–lvi):** Personalized dashboard, interactive lesson view, server-side quiz grading, weak-area analytics, digital completion certificates.
- **Policy Updates & Regeneration (FR lvii–lx):** Version update detection, impact analysis, selective module regeneration.
- **Analytics & Export (FR lxi–lxvi):** Multi-criteria search and filtering, compliance reporting, CSV/JSON/PDF data export.

### 4.2. Non-Functional Requirements (NFR 1–5)
1. **Performance:** Full path synthesis and verification completes in under 30 seconds; synchronous Validation Gate checks execute in under 2 seconds.
2. **Scalability:** Architected to support 1,000 employee profiles, 100 job roles, and 1,000 enterprise documents via PostgreSQL indexing and section chunking.
3. **Usability:** Responsive glassmorphism interface with complete bilingual parity (English and Vietnamese).
4. **Accuracy & Grounding:** Mandatory requirements require 100% verified coverage to achieve `Verified` status; 100% of curriculum content links to verbatim exact quotes.
5. **High Availability:** Fully containerized Docker orchestration with health check probes ensuring ≥99% uptime.

---

## 5. System Architecture & Design

### 5.1. Overall Architecture
SkillSprint AI adheres to an 8-block modular architecture:
```
Company Documents ──> Ingestion & Validation ──> Role & Requirement Matrix
                              │                              │
                    ┌─────────┴─────────┐                    │
                    ▼                   ▼                    │
            Pipeline 1 (GenAI)   Pipeline 2 (Python) ◄───────┘
                    │                   │
                    └─────────┬─────────┘
                              ▼
                   Dual-Pipeline Comparator
                              │
                              ▼
                Reviewer Workspace & Decisions
                              │
                              ▼
                 Employee LMS & Analytics
```

### 5.2. Data Flow Diagrams (DFD)
- **DFD Level 0 (Context):**
  - External Entities: HR Specialist, Content Reviewer, Employee, Administrator.
  - Central Process: SkillSprint AI Verification Platform.
  - Data Stores: Enterprise Knowledge Base, Role Requirement Matrix, Learning Paths, Audit Trail.
- **DFD Level 1 (Decomposition):**
  - Process 1.0: Ingestion & Format Validation.
  - Process 2.0: Generative Curriculum Synthesis.
  - Process 3.0: Deterministic Rule Validation.
  - Process 4.0: Cross-Pipeline Diff Comparison.
  - Process 5.0: Reviewer Audit & Publishing.
  - Process 6.0: Learner Execution & Evaluation.

### 5.3. Use Case Diagram
- **Administrator:** Manage user accounts, upload CVs for automated employee onboarding, review system-wide audit telemetry.
- **HR Specialist:** Upload documents, configure role requirements, trigger AI path generation, review and edit drafts, submit to review queue.
- **Content Reviewer:** Inspect Dual-Pipeline Comparison Table, perform field-by-field verification, add inline feedback, approve/reject/override paths.
- **Employee:** Study grounded lessons, open inline source citations, check off operational tasks, submit server-evaluated quizzes, earn completion certificates.

### 5.4. Activity Diagram: Path Lifecycle
`[Upload Documents] → [Validate & Chunk] → [Select Role] → [Generate AI Path & Python Matrix] → [Execute Comparator Engine] → [Submit to Review Queue] → [Reviewer Audit] → {Approved?} → [Publish & Auto-Enroll Learners]`

### 5.5. Sequence Diagram: Dual-Pipeline Generation Transaction
1. HR sends `POST /api/paths/jobs` with `role_id` and document sources.
2. Background Job initiates `generation_jobs.py`.
3. Pipeline 1 synthesizes module drafts concurrently via Gemini API.
4. Grounding validator cross-references every `exact_quote` against database chunks.
5. Pipeline 2 calculates Coverage Score against `role_matrix.csv`.
6. Comparator Engine diffs results and attaches verification metadata.
7. Job completes; path stored in `draft` status ready for HR review.

### 5.6. Database Design & Entity Relationship Diagram (ERD)
The operational database includes 13 core relational entities:
- `departments` (Department codes and localized metadata).
- `job_positions` (Role definitions linked to parent departments).
- `users` (Account credentials, bcrypt password hashes, assigned role and department).
- `documents` (Uploaded files, version metadata, SHA-256 hashes, lifecycle statuses).
- `document_chunks` (Cryptographically indexed chunks with section headers and page numbers).
- `injection_flags` (Security scan results per chunk).
- `learning_paths` (Curriculum metadata, JSON stages hierarchy, revision counters).
- `path_sources` (Many-to-many mapping of document versions used in generation).
- `path_assignments` (Publication targeting by department and position).
- `path_comments` (Reviewer annotations and feedback threads).
- `audit_logs` (Append-only immutable event log).
- `enrollments` (Employee curriculum progress, completion timestamps, due dates).
- `quiz_attempts` (Examination submissions and server-side scores).

---

## 6. Document-Processing Pipeline & Chunking

The ingestion subsystem (`backend/app/ingestion/`) processes multi-format enterprise documentation:
- **Format Extraction:** PyMuPDF (`fitz`) for PDF documents, `python-docx` for Word files, native readers for TXT, Markdown, and CSV.
- **Magic-Byte Integrity:** Pre-validates file headers (e.g., `%PDF-`, `PK\x03\x04`) preventing extension spoofing.
- **Section-Aware Chunking:** Analyzes document hierarchy, splitting text strictly at section boundaries. Each chunk complies with the data contract:
  ```json
  {
    "doc_id": "DOC-06",
    "chunk_id": "DOC-06-C0003",
    "section_id": "5.0",
    "heading": "Incident Reporting SLA",
    "page": 4,
    "content": "..."
  }
  ```
- **Lifecycle Tracking:** Categorizes documents as `active`, `superseded`, `expired`, or `upcoming`, preventing obsolete policies from influencing current curricula.

---

## 7. Role Requirement Matrix & Competency Setup

The Role Requirement Matrix (`role_matrix/role_matrix.csv`) defines 203 standardized rules covering 156 unique operational and compliance requirements across 10 corporate positions.
- **Data Attributes:** `Role`, `Requirement_ID`, `Topic`, `Source_Document`, `Source_Section`, `Source_Version`, `Scope` (Company-wide vs Role-specific), `Priority` (Mandatory vs Optional).
- **Mandatory Document Locking:** The creation workspace automatically identifies and locks mandatory documents, preventing HR from generating non-compliant curricula.

---

## 8. Pipeline 1 — Generative AI Pipeline

### 8.1. Model Selection & Configuration
Utilizes Google Gemini (Gemini 1.5 Flash / Pro) with dynamic fallback routing across `GEMINI_FALLBACK_MODELS`. If quota exhaustion (HTTP 429) occurs, the engine automatically rolls over to backup models or utilizes deterministic local fallback drafts without failing.

### 8.2. Prompt Engineering & Versioning
Prompts are isolated as modular versioned markdown templates under `backend/app/genai_pipeline/prompts/`:
- **v1.0:** Baseline structured curriculum generation.
- **v1.1:** Pedagogical rules enforcement (instruction precedes assessment, mandatory completion criteria for tasks, tiered difficulty).

### 8.3. Pydantic Structured Output Schemas
LLM output is constrained to strict Pydantic schemas (`schemas.ModuleDraft`, `schemas.QuizDraft`), stripping raw markdown formatting and guaranteeing structural validity.

### 8.4. Source-Grounded Generation
Every lesson, task, and quiz question must include a verifiable `source_reference` with a verbatim `exact_quote`. Grounding validators reject unquoted claims, eliminating hallucinations at generation time.

---

## 9. Pipeline 2 — Deterministic Python Rule Engine

### 9.1. Zero-AI Architecture Guarantee
Pipeline 2 (`backend/app/rule_pipeline/`) operates strictly without AI SDK imports, relying on deterministic set logic, regex parsing, and cryptographic chunk matching.

### 9.2. Coverage Score Algorithm
Calculates the exact percentage of mandatory Role Matrix requirements addressed by the curriculum:
$$\text{Coverage Score} = \frac{|\text{Addressed Mandatory Requirements}|}{|\text{Total Position Mandatory Requirements}|} \times 100\%$$
Paths must achieve 100% Coverage to receive `Verified` status.

### 9.3. Traceability Validation
Cross-references every citation against raw database chunk hashes, guaranteeing that 100% of curriculum content links to authentic company documentation.

### 9.4. Prerequisite DAG Enforcement
Validates that foundational company policies (e.g., Code of Conduct, Information Security) precede specialized departmental tasks and technical procedures.

---

## 10. Dual-Pipeline Comparison Engine & Verification

### 10.1. Field-by-Field Diff Comparison (Table 1)
The Comparator Engine (`backend/app/comparator/engine.py`) performs comparative verification across four key dimensions:
1. **Taught Status:** Verifies whether required topics are instructed in lessons.
2. **Tested Status:** Verifies whether topics are examined in quizzes.
3. **Source Version Alignment:** Verifies that active, non-superseded documents are cited.
4. **Verbatim Grounding:** Verifies that exact quotes exist character-for-character in database chunks.

### 10.2. Verification Status Classification
- `Verified`: 100% mandatory coverage, 100% quote grounding, zero blocking flags.
- `Verified with Warning`: Non-blocking version notes or minor formatting ambiguities.
- `Manual Review Required`: Hallucinated figures, contradictory policies, or missing mandatory sources.

### 10.3. Human-in-the-Loop Review & Audit Trail
Reviewers inspect the comparison table, request changes, or approve publication. If approving with warnings, Reviewers must provide an explicit justification (≥ 10 characters) committed permanently to the immutable audit trail.

---

## 11. Adversarial Defense & Security Engineering

### 11.1. Hallucination Detection
Extracts numeric figures, financial amounts, and time windows from generated text and verifies them against source chunks. Discrepancies (e.g., $500 gym stipend when policy states $0) trigger immediate `HallucinationFlag` alerts.

### 11.2. Contradiction Detection & Policy Precedence
Resolves conflicting rules via precedence DAGs:
- Active Version > Superseded Version (DOC-01 v2.0 overrides DOC-02 v1.0).
- Operational SOP > General Corporate FAQ (SOP-09 §3 overrides FAQ-16 §4).

### 11.3. Dual-Language Prompt Injection Defense
Dual-layer regex and semantic filters scan uploaded text for adversarial jailbreak directives in both English and Vietnamese:
- English: `ignore previous instructions`, `system override`, `you are now in DAN mode`.
- Vietnamese: `bỏ qua mọi chỉ dẫn trước đó`, `ghi đè hệ thống`, `bạn là quản trị viên`.
Flagged chunks are quarantined from context windows.

---

## 12. Testing Strategy & Quantitative Results

The system is fortified by **586 automated tests (100% pass rate)**:
- **Backend API & RBAC Suite (`backend/tests`):** 390 / 390 passed.
- **Core Algorithms & Security Suite (`tests/`):** 88 / 88 passed.
- **Frontend Vitest Suite (`frontend/tests`):** 108 / 108 passed.
- **Adversarial Testing:** 10 / 10 attack vectors in DOC-18 successfully intercepted.
- **Unseen Document Evaluation:** `hidden_test_ready/run_hidden_test.py` executed autonomously with 100% match score.

---

## 13. Deployment Architecture & Production Readiness

- **Containerization:** Multi-stage production `Dockerfile` for backend and frontend.
- **Nginx Reverse Proxy:** Serves optimized React SPA assets, handles client-side routing fallbacks, and proxies `/api/` traffic with Gzip compression.
- **Unified Orchestration:** `docker-compose.yml` launches PostgreSQL 16, FastAPI backend, and Nginx frontend in an isolated network with automatic migration and database seeding.

---

## 14. Limitations & Future Enhancements

- **Current Operational Boundaries:** Scanned image-only PDFs require digital text extraction; future versions will integrate OCR engines (e.g., Tesseract or Google Cloud Vision).
- **Roadmap:** Integration of semantic vector embeddings (pgvector) to complement section-aware lexical chunking, and enterprise HRMS webhook synchronization.

---

## 15. Conclusion

SkillSprint AI establishes a new paradigm for enterprise Generative AI adoption. By pairing LLM generative synthesis with an independent, deterministic Python Rule Engine, the platform eliminates hallucination risks, guarantees 100% compliance with corporate policies, and provides complete cryptographic traceability. The system stands fully implemented, comprehensively tested, and production-ready for the TechWiz 7 competition.
