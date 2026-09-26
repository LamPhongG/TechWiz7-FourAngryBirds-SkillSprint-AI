# Adversarial Documents — ContradictionChecker Test Fixtures (WBS Phase 3, line 152)

10 "trap" documents (`CTX-01` → `CTX-10`), each deliberately conflicting with a real,
currently-active document in `sample_documents/` or a row in `role_matrix/role_matrix.csv`.
These exist to give the future `contradiction_checks/` module (and the Python Ground-Truth
Validation Pipeline generally, SRS Steps 33-34) concrete, varied cases to detect — covering
different *kinds* of contradiction, not just repeats of the same pattern.

Each file's front-matter carries `conflicts_with` (the real document/row it contradicts) and
`contradiction_type` (the category below), and an inline `TEST NOTE` HTML comment explains
exactly what the checker should catch and why. Comments are inline for traceability while the
set is small; if this grows, move the notes into this README only.

## Scenario summary

| ID | Title | Conflicts with | Contradiction type | What it specifically tests |
| --- | --- | --- | --- | --- |
| CTX-01 | HR Memo — Annual Leave Rules (2022) | DOC-01 §6 | Silent staleness | Undated/unversioned policy claim with no supersede metadata, contradicting a current versioned document |
| CTX-02 | Employee FAQ — Leave & Benefits | DOC-01 §6 | FAQ vs. Policy precedence | Precedence hierarchy (Policy > FAQ) per SRS Step 34 |
| CTX-03 | Sales Team Playbook (unofficial) | DOC-08 §5; R011, R058 | Role/authority conflict | Cross-checking generated content against the Role Requirement Matrix, not just source text |
| CTX-04 | IT Access Bulletin — MFA Rollout | Itself (§2 vs §5); DOC-06 §2 | Self-contradiction | Detecting inconsistency *within* a single document |
| CTX-05 | Finance Quick Reference Card | DOC-09 §4; R026, R059 | Numeric threshold conflict | Fact-level validation (3 of 4 facts correct, 1 number wrong) — must not pass/fail a whole document as one unit |
| CTX-06 | Data Protection Compliance Certificate | DOC-05 (cited basis) | Outdated source (expiry_date) | Staleness detected via `expiry_date`, distinct from the `supersedes` mechanism |
| CTX-07 | Customer Support Quick Guide | DOC-07 §4.2-4.3; R001, R073 | Process/sequence conflict | Skipped-step detection (Tier 2 bypassed), distinct from a wrong number or self-contradiction |
| CTX-08 | Branch Front-Office Circular | DOC-04 §4 | Overgeneralization | Role-relevance/scope checking — a narrow, role-specific rule incorrectly broadened to everyone |
| CTX-09 | Remote Work Addendum (draft) | DOC-01 (invalid §11) | Dangling reference | Invalid Source Section ID detection (SRS Step 38) + Draft-status documents must not be treated as approved sources |
| CTX-10 | Workplace Conduct Policy — Disciplinary Procedure (fragment) | DOC-04 §6 | Dual active version | Two sources both claiming to be the current v1.0 with identical metadata but conflicting rules — no `document_id` field, missing metadata should itself be flagged; likely requires Manual Review Required rather than automatic resolution |

## Coverage rationale
The 10 cases are spread across contradiction *mechanisms*, not just contradiction *topics*,
so a checker that handles one pattern well can't accidentally look complete:
- **Metadata-based** (version/status/expiry): CTX-01, CTX-06, CTX-10
- **Precedence-based** (document type hierarchy): CTX-02
- **Business-rule-based** (matrix cross-check, not just text diff): CTX-03, CTX-05, CTX-07
- **Structural** (self-contradiction, invalid reference, missing ID): CTX-04, CTX-09, CTX-10
- **Scope-based** (role-relevance / overgeneralization): CTX-08

## How to use these
1. Ingest all 10 alongside the real `sample_documents/` set (DOC-01→10) so the checker sees
   both the authoritative source and the trap in the same run — a contradiction can only be
   detected in contrast to something.
2. For each `CTX-XX`, the expected outcome is a `Contradiction Detected` (or `Outdated Source`
   / `Manual Review Required` per CTX-06/CTX-10) validation status, resolved in favor of the
   real DOC-XX document — never in favor of the trap.
3. None of these should be surfaced to an employee as part of a real onboarding plan; if a
   generated plan ever cites a `CTX-XX` file as its source, that is itself a bug to report.

## Known gap
These are English-only, consistent with the rest of `sample_documents/`. Per the same
Vietnamese-language gap noted in `tests/test_adversarial.py`, Vietnamese-language contradiction
cases (e.g. a Vietnamese-language leaked memo) should be added when `contradiction_checks/` is
implemented in Phase 3's collaborative build (Phong & Nhi, WBS line 132).
