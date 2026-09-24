# Sample Documents — Phase 1 (DOC-01 → DOC-10)

Source drafts for the FourAngryBirds EdTech & HR Solutions JSC document set defined in
[`frontend/src/data/company.js`](../frontend/src/data/company.js) (`DOCUMENT_CATALOG`).
DOC-11 → DOC-20 are added in Phase 2 per the WBS.

## Status

| ID | Family | Title | Status |
| --- | --- | --- | --- |
| DOC-01 | employee-handbook | Employee Handbook (current, v2.0) | **.pdf + .docx generated** |
| DOC-02 | employee-handbook | Employee Handbook (obsolete, v1.0) | **.pdf generated** |
| DOC-03 | hr-leave-policy | HR Leave Policy | Draft written — needs PDF/DOCX conversion + review |
| DOC-04 | workplace-conduct-policy | Workplace Conduct Policy | Draft written — needs PDF/DOCX conversion + review |
| DOC-05 | data-privacy-policy | Data Privacy Policy | **.docx generated** |
| DOC-06 | information-security-policy | Information Security Policy | Draft written — needs PDF/DOCX conversion + review |
| DOC-07 | sop-customer-escalation | SOP – Customer Escalation Process | **.pdf + .docx generated** |
| DOC-08 | sop-sales-pipeline | SOP – Sales Pipeline Management | Draft written — needs PDF/DOCX conversion + review |
| DOC-09 | sop-financial-reimbursement | SOP – Financial Reimbursement | Draft written — needs PDF/DOCX conversion + review |
| DOC-10 | sop-software-deployment | SOP – Software Deployment Workflow | Draft written — needs PDF/DOCX conversion + review |

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
