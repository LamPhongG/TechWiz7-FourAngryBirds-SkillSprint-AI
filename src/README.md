# SkillSprint AI — Core Algorithm & Source Architecture (`src/`)

Dual-Pipeline Ground-Truth Verification System designed for automated, verifiable employee onboarding curriculum generation and audit compliance.

## Core Module Architecture

| Directory | Primary Responsibility | Technical Components |
| :--- | :--- | :--- |
| [`document_processing/`](document_processing/) | Document extraction and structuring | PyMuPDF, python-docx, structural section chunking |
| [`document_validation/`](document_validation/) | File integrity and authenticity | Magic-byte headers, SHA-256 deduplication hashing |
| [`genai_pipeline/`](genai_pipeline/) | Generative AI pipeline (Pipeline 1) | Gemini API, Pydantic structured output, exact-quote grounding |
| [`prompt_templates/`](prompt_templates/) | Prompt template versioning | Versioned system instructions (`v1.0`, `v1.1`) |
| [`python_validation/`](python_validation/) | Pure Python rule engine (Pipeline 2) | Deterministic coverage scoring, prerequisite DAG validation |
| [`role_matrix/`](role_matrix/) | Role Requirement Matrix (RRM) | Position requirement parsing, mandatory vs optional extraction |
| [`comparison_engine/`](comparison_engine/) | Dual-pipeline cross-validation | Field-by-field diff comparison, Match / Mismatch / Warning classification |
| [`hallucination_checks/`](hallucination_checks/) | Hallucination detection | Ground-truth quote verification against raw database chunks |
| [`contradiction_checks/`](contradiction_checks/) | Policy contradiction detection | Policy precedence rules (Policy v2 > v1, SOP > FAQ) |
| [`security/`](security/) | Adversarial defense and safety | Dual-language prompt injection filter (EN & VI), jailbreak shields |
| [`schemas/`](schemas/) | Pydantic data contracts | Comparison schemas, pipeline interchange models |
| [`database/`](database/) | Database persistence | PostgreSQL connection management, SQLAlchemy ORM models |

Developed and maintained by **FourAngryBirds Team — TechWiz 7**.
