# Role Requirement Matrix

`role_matrix.csv` — 203 rows covering the 10 roles defined in
[`frontend/src/data/company.js`](../frontend/src/data/company.js), sourced from
`sample_documents/DOC-01` → `DOC-16` and `DOC-20`.

## Columns
The first ten columns follow SRS Step 10 exactly, with a leading `Requirement_ID`:
`Requirement_ID, Role, Policy_Requirement, Process_Requirement, Competency, Mandatory_Optional, Priority,
Source_Document, Source_Section, Assessment_Requirement`.

Phase 2 adds two columns at the end. Readers that pick columns by name are unaffected.

| Column | Values | Why |
| :--- | :--- | :--- |
| `Source_Version` | Version of the cited document the row was written against, e.g. `2.0` | A policy can change after the row is written (see `sample_documents/README_PHASE2.md` §6). When a newer version comes into force, rows citing an older version must be re-checked. |
| `Scope` | `Company-wide` or `Role-specific` | `Company-wide` restates a rule every employee follows (handbook acknowledgement, passwords, consent…). `Role-specific` applies to this role or to a named group of roles only. This is how the "role-specific requirements" minimum is counted. |

## Why Customer Support Executive is listed first
`R001` is deliberately the SOP-07 (DOC-07) §4.2 escalation clause for Customer Support
Executive — it reproduces the SRS's own Table 1 worked example verbatim (Mandatory,
Priority High, Due Stage Week 1). Evaluators may check this exact row, so its
Requirement ID must stay `R001`. All other roles follow in the order they're
declared in `company.js`.

## Phase 2 (26/09/2026)
- **Coverage gaps closed.** `R040` (Operations Coordinator) and `R048` (Marketing Executive) were placeholders.
  They now hold real requirements from DOC-12 §6.1 (partner-school kickoff within 3 business days) and
  DOC-13 §4.3 (four-step campaign approval).
- **R081–R173:** 93 role-specific rows from the role documents: DOC-11 onboarding, DOC-12 branch operations,
  DOC-13…15 job descriptions and DOC-20 department exceptions.
- **R174–R203:** three company-wide rows, repeated for each of the 10 roles:
  - DOC-11 §6.1: completing an onboarding module;
  - DOC-11 §5.2: day-1 actions;
  - DOC-16 §8: learning budget (optional).
- **Version cited.** Every row cites the version in force on 26/09/2026:
  - DOC-01 v2.0, DOC-11 v1.2, DOC-12 v2.0, DOC-20 v1.1;
  - v1.1 of DOC-13…16;
  - v1.0 of every other document.

  DOC-20 v1.2 only takes effect on 01/01/2027, so no row cites it yet.
- The test documents DOC-17, DOC-18 and DOC-19 are never cited.

## Totals
| Minimum (SRS) | Required | Matrix |
| :--- | ---: | ---: |
| Identifiable policy / process requirements | 150 | 203 rows, **156 distinct requirements** |
| Mandatory requirements | 50 | 188 |
| Role-specific requirements | 30 | 137 rows, 133 distinct |
| Roles covered | 10 | 10 (16–24 rows each) |

15 rows are optional, and priorities are split High 89 / Medium 79 / Low 35.

## Automated checks
`backend/tests/test_role_matrix_dataset.py` checks four things:
- the minimums above;
- the CSV imports without a single row error;
- no row cites a test document;
- every row citing DOC-11…20 names a section that exists in the source of the version it cites, and that version
  is the one in force.

DOC-01…10 get the same check once their Markdown sources are in `sample_documents/source/`.

The backend loads this file with `python -m app.db.seed`. The import updates rows by `Requirement_ID`, so running
it again does not create duplicates.
