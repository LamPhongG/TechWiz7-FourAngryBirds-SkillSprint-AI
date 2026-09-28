"""SkillSprint AI — Core Architecture Root Package.

Dual-Pipeline AI Document Verification System for Personalized Onboarding.
TechWiz 7 — Generative AI Powerplay Track.

Modules:
- comparison_engine: Field-by-field diff and match classification.
- contradiction_checks: Policy contradiction and precedence conflict resolution.
- database: Connection management and schema migrations.
- document_processing: Ingestion, parsing (PDF/DOCX/TXT), and chunking.
- document_validation: File format, integrity, and duplicate detection.
- genai_pipeline: GenAI plan generation, quiz generation, and grounding.
- hallucination_checks: Grounded citation verification and hallucination detection.
- prompt_templates: Version-controlled prompt engineering (v1.0, v1.1).
- python_validation: Rule-based coverage calculation and prerequisite checks.
- role_matrix: Role Requirement Matrix (RRM) extraction and mapping.
- schemas: Pydantic schemas and comparison data contracts.
- security: Prompt injection filtering and adversarial defenses.
"""

__version__ = "1.0.0"
__author__ = "Chau Quoc Lam Phong & FourAngryBirds Team"
