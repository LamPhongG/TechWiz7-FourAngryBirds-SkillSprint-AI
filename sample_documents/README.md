# Sample Documents — Phase 1 (DOC-01 → DOC-10, RD-01 → RD-10)

Source drafts for the FourAngryBirds EdTech & HR Solutions JSC document set defined in
[`frontend/src/data/company.js`](../frontend/src/data/company.js) (`DOCUMENT_CATALOG`).
DOC-11 → DOC-20 are added in Phase 2 per the WBS.

`RD-01` → `RD-10` are a second set: one Role Description per role in `role_matrix/role_matrix.csv`
(10 roles), consolidating the policy/SOP clauses scattered across DOC-01→DOC-10 into a single
per-role reference — mirroring the SRS's own framing (§1.1) that onboarding information is
normally "distributed across policy documents, SOPs, role descriptions, FAQs, process manuals."
They are not part of the original `company.js` `DOCUMENT_CATALOG` (which only allocates DOC-13/14/15
as grouped, multi-role job descriptions); the `RD-` prefix avoids colliding with the DOC-11→DOC-20
IDs reserved for Phase 2.

## Status

| ID | Family | Title | Status |
| --- | --- | --- | --- |
| DOC-01 | employee-handbook | Employee Handbook (current, v2.0) | **.pdf + .docx generated** |
| DOC-02 | employee-handbook | Employee Handbook (obsolete, v1.0) | **.pdf generated** |
| DOC-03 | hr-leave-policy | HR Leave Policy | **.docx generated** |
| DOC-04 | workplace-conduct-policy | Workplace Conduct Policy | **.txt generated** |
| DOC-05 | data-privacy-policy | Data Privacy Policy | **.docx generated** |
| DOC-06 | information-security-policy | Information Security Policy | Draft written — needs conversion + review |
| DOC-07 | sop-customer-escalation | SOP – Customer Escalation Process | **.pdf + .docx generated** |
| DOC-08 | sop-sales-pipeline | SOP – Sales Pipeline Management | Draft written — needs conversion + review |
| DOC-09 | sop-financial-reimbursement | SOP – Financial Reimbursement | Draft written — needs conversion + review |
| DOC-10 | sop-software-deployment | SOP – Software Deployment Workflow | **.csv generated** (section-chunk export, see below) |
| RD-01 | role-description-sales-executive | Role Description – Sales Executive | Draft written — needs conversion + review |
| RD-02 | role-description-customer-support-executive | Role Description – Customer Support Executive | **.docx generated** |
| RD-03 | role-description-hr-executive | Role Description – HR Executive | Draft written — needs conversion + review |
| RD-04 | role-description-finance-associate | Role Description – Finance Associate | Draft written — needs conversion + review |
| RD-05 | role-description-operations-coordinator | Role Description – Operations Coordinator | **.csv generated** (requirements-table export, see below); documents its own coverage gap, §8 |
| RD-06 | role-description-marketing-executive | Role Description – Marketing Executive | Draft written — needs conversion + review (documents its own coverage gap, §8) |
| RD-07 | role-description-software-support-engineer | Role Description – Software Support Engineer | Draft written — needs conversion + review |
| RD-08 | role-description-branch-manager | Role Description – Branch Manager | **.txt generated** |
| RD-09 | role-description-data-analyst | Role Description – Data Analyst | Draft written — needs conversion + review |
| RD-10 | role-description-team-leader-tech-lead | Role Description – Team Leader / Tech Lead | Draft written — needs conversion + review |

### Format coverage (SRS Step 4: PDF, DOCX, TXT, Markdown, CSV)
Every document exists as `.md` (the authoring source). On top of that, at least one example
of every SRS-listed format is now present in this folder:
- **PDF** (mandatory): DOC-01, DOC-02, DOC-07
- **DOCX** (mandatory): DOC-01, DOC-03, DOC-05, DOC-07, RD-02
- **TXT** (optional format): DOC-04, RD-08 — plain-text rendering with markdown syntax
  stripped but headings/sections/lists still visually structured.
- **CSV** (optional format, "wherever required"): two different, purposeful shapes rather
  than an awkward prose-to-CSV conversion —
  - `DOC-10_sop-software-deployment-chunks.csv`: a **section-chunk export**
    (`document_id, chunk_id, section_id, heading, version, effective_date, content`) —
    this is the same shape `document_processing/chunker.py` is expected to produce per
    SRS Step 7, so it doubles as a fixture for that module.
  - `RD-05_role-operations-coordinator-requirements.csv`: a **per-role requirements
    export** pulled straight from `role_matrix/role_matrix.csv`, including its flagged
    coverage-gap row (R040) — demonstrating how a single role's matrix slice can be
    handed to a reviewer or the frontend without the full 80-row file.

Each `RD-XX` document includes: role summary, core responsibilities, required competencies,
governing DOC-01→DOC-10 references, a full table of that role's requirement rows pulled directly
from `role_matrix/role_matrix.csv` (kept in sync — if the CSV changes, these tables need updating
too), 2–3 role-specific FAQs, and its escalation/reporting line. RD-05 and RD-06 additionally
document the same coverage gap already flagged as R040/R048 in the CSV.

## How the .md → .pdf/.docx conversion was done
No pandoc, LibreOffice, or Microsoft Word were available on this machine, so conversion
uses a small custom pipeline (kept in the session scratchpad, not committed — re-run
manually or ask for it to be added to the repo if you want it as a reusable tool):
- **PDF**: the `.md` is rendered to a styled HTML page, then printed to PDF via headless
  Microsoft Edge (`msedge --headless --print-to-pdf`).
- **DOCX**: the `.md` is parsed into headings/paragraphs/lists and assembled directly
  into a minimal valid Office Open XML package (`[Content_Types].xml`, `word/document.xml`,
  `word/styles.xml`, relationship parts) zipped with .NET's `System.IO.Compression`.
Both were spot-checked: PDF files start with a valid `%PDF-1.4` header, and DOC-07's
DOCX was unzipped and grepped to confirm the "Requirement ID R001" clause text survived
intact. Formatting is basic (headings, bold, blockquotes, bullet lists) — good enough
for the document-processing pipeline to ingest and chunk, but not polished for a human
reader. Worth a quick visual open in Word/Acrobat before these go into any human-facing
deliverable (e.g. the project report or demo).

## Conventions used across all documents
- Front-matter block: `document_id`, `family`, `title_en`, `title_vi`, `category`, `department`, `version`, `status`, `effective_date` (+ `supersedes`/`superseded_by` where relevant) — mirrors the fields `document_processing/` must extract (SRS Step 6).
- Numbered sections/sub-sections (`§4.2` style) so the Role Requirement Matrix and later chunking can cite a stable `Source Section ID`.
- Inline tags mark structural intent for requirement extraction:
  - `[MANDATORY]` / `[OPTIONAL]` — maps to SRS Step 11 requirement classification
  - `[ROLE-SPECIFIC: ...]` — role-relevance validation (SRS Step 36)
  - `[EXCEPTION]` / `Conditional` — document-variation complexity (SRS Step 3)
  - `Cross-References` section per doc — feeds contradiction/precedence checks (SRS Step 33–34)

## Known cross-document dependencies (do not break these when editing)
- **DOC-01 §6** (leave carryover, v2.0, current) directly **contradicts DOC-02 §6** (no carryover, v1.0, obsolete) — this is the intentional version-control/contradiction test case (SRS Step 8, Step 33).
- **DOC-07 §4.2** is the literal worked example from SRS Table 1: Requirement ID `R001`, Role `Customer Support Executive`, Source Document `SOP-07` (= DOC-07), Source Section `4.2`, Mandatory `Yes`, Priority `High`, Due Stage `Week 1`. The Role Requirement Matrix's first row must reference this exact clause.
- DOC-03 §7 intentionally does **not** restate the carryover number — it defers to DOC-01 §6 — so there is exactly one authoritative source per rule.

## Next steps
1. Convert each `.md` file to PDF and/or DOCX (pandoc or manual formatting) to satisfy the SRS's mandatory PDF/DOCX ingestion formats.
2. Build `role_matrix/role_matrix.csv` against these 10 documents (WBS Phase 1, 6h–9h task).
3. Phase 2: add DOC-11 → DOC-20 (remaining catalog entries, including the intentionally adversarial/conflicting/outdated test-case documents DOC-17–DOC-20).
