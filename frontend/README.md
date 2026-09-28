# SkillSprint AI — Frontend

Web user interface for SkillSprint AI, designed for the simulated corporate environment of **FourAngryBirds EdTech & HR Solutions**.

SkillSprint AI transforms internal company documents (PDF, DOCX, TXT, MD/MARKDOWN, CSV) into structured, verifiable **learning paths** for employee onboarding and role promotions.

### Primary Workflow
1. **HR Specialists** upload internal policy documents, SOPs, and job descriptions, then configure requirements and initiate AI-assisted path generation.
2. **Content Reviewers** audit synthesized learning paths for knowledge accuracy, prerequisite sequencing, and role relevance. Reviewers approve and publish paths to target departments or request modifications with granular feedback.
3. **Employees** complete assigned paths: study source-grounded lessons, view source documents directly in an inline viewer, execute tasks, and complete server-evaluated quizzes.

The interface supports seamless **English and Vietnamese** localization.

📄 **Comprehensive Architecture & System Workflows:** [`reports/Project_Report.md`](../reports/Project_Report.md)

---

## 1. Quick Start

Prerequisite: **Node.js ≥ 18**.

```bash
cd frontend
npm install        # or: npm ci
npm run dev        # Development server: http://localhost:3000
npm test           # Unit and component test suite (Vitest)
npm run build      # Production bundle output to dist/
npm run preview    # Preview production build locally
```

### Demo Login Accounts
The application includes a modern glassmorphism login screen at `/login`. You can sign in using email and password credentials or click any demo role chip to auto-populate test accounts:

| Role | Email | Password | Default Workspace |
| :--- | :--- | :--- | :--- |
| HR Manager | `hr@fourangrybirds.vn` | `password123` / `Demo@123` | `/hr/dashboard` |
| Content Reviewer | `reviewer@fourangrybirds.vn` | `password123` / `Demo@123` | `/reviewer/dashboard` |
| Employee (Learner) | `alex.morgan@fourangrybirds.vn` | `password123` / `Demo@123` | `/employee/dashboard` |
| System Admin | `admin@fourangrybirds.vn` | `password123` / `Demo@123` | `/admin/dashboard` |

### Backend API Integration
To connect with the FastAPI backend, copy `.env.example` to `.env.local` and configure `VITE_API_URL`:

```env
VITE_API_URL=http://localhost:8000/api
```

When connected to the backend API:
- Authentication is verified via JWT tokens (`POST /auth/login`).
- Document repositories, learning paths, and audit logs synchronize with the database.
- Server-side generation jobs provide real-time step telemetry and dual-pipeline verification reports.

---

## 2. Technology Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| Core Framework | React 18, React Router 7 | Role-based component architecture and routing |
| Build Tool | Vite 6 | Fast development server and production bundler |
| Document Parsing | pdfjs-dist 5, mammoth 1.12 | In-browser fallback document extraction (dynamic import) |
| Local Persistence | IndexedDB, localStorage, sessionStorage | Client-side document cache, offline draft store |
| Cryptography | Web Crypto API (SHA-256) | Client-side deduplication checksums |
| Icons | Lucide React | Modern interface iconography |
| Internationalization | Custom `LanguageContext` | Reactive multi-language dictionary (`t()`, `tv()`, `pick()`) |
| Testing | Vitest 3 | Unit and component test suites |

---

## 3. Directory Layout

```
frontend/
├── .env.example
├── tests/                         # Vitest test suites (chunking, injection scan, verification, progress)
└── src/
    ├── App.jsx                    # Central route definitions, RBAC navigation guards
    ├── layouts/                   # AuthLayout, RoleLayout (HR, Reviewer, Employee, Admin frames)
    ├── contexts/
    │   ├── DocumentsContext.jsx   # Document catalog, upload states, extracted chunk store
    │   ├── PathsContext.jsx       # Learning paths, review actions, and audit logs
    │   ├── EnrollmentContext.jsx  # Employee learning progress and quiz submissions
    │   └── LanguageContext.jsx    # Internationalization state and formatters
    ├── components/
    │   ├── path/                  # DualComparisonTable, GenerationProgress, CertificateModal, etc.
    │   └── UI/                    # Modal, Badge, Citation, DocumentViewer, ErrorBoundary
    ├── hooks/                     # Custom React hooks (useAuth, useMyPaths)
    ├── pages/
    │   ├── hr/                    # Dashboard, Documents, CreatePath, Learners, Reports
    │   ├── reviewer/              # Dashboard, ReviewQueue, AuditLog
    │   ├── shared/                # PathList, PathDetail, AuditLog
    │   ├── employee/              # Dashboard, MyPaths, ModuleView, Explore, Profile
    │   ├── admin/                 # Dashboard, Users
    │   └── auth/                  # Glassmorphism Login, SelfRegister
    ├── services/                  # apiClient, documentStore, textExtraction, pipelineService
    ├── utils/                     # chunker, injectionScan, pathGenerator, pathChecks, pathWorkflow
    ├── data/                      # company.js (roles, departments, document catalog)
    ├── locales/                   # en.js, vi.js
    └── styles/                    # index.css (tokens, typography, layout), features.css
```

---

## 4. Testing & Verification

- **Automated Vitest Suite:** `npm test -- --run` runs all component and utility test suites (108/108 passed).
- **Production Build:** `npm run build` compiles clean assets with zero type or packaging errors.
- **End-to-End User Flow:** Verified end-to-end across all 4 roles (Admin user management → HR document upload & generation → Reviewer dual-pipeline audit & approval → Employee learning progress & certificate unlock).
