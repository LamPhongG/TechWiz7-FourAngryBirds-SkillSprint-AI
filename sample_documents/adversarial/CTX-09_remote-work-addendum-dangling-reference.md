---
trap_id: CTX-09
title: Remote Work Addendum (draft)
category: Contradiction Test Case
status: Draft
version: 0.1
effective_date: (not yet effective)
conflicts_with: DOC-01 (Employee Handbook) — cites a section that does not exist
contradiction_type: dangling_reference — invalid Source Section ID
---

# Remote Work Addendum (draft)
**Status: DRAFT — not yet approved or effective**

This addendum extends the Employee Handbook to cover remote-work eligibility and
equipment policy. Employees requesting remote work should refer to **Employee Handbook
Section 11** for the standard approval workflow before submitting a request through this
addendum.

<!--
TEST NOTE: DOC-01 (v2.0) only has sections 1 through 9 — there is no
Section 11. This document also has an internally inconsistent status:
front-matter marks it `status: Draft` / not yet effective, while the prose
still instructs employees to act on it ("should refer to... before
submitting a request"), as if it were already in force. This tests two
things at once: (1) SRS Step 38's "invalid source IDs" detection — the
Python validation pipeline must be able to tell that Section 11 of DOC-01
does not exist rather than silently accepting the citation, and (2) that a
Draft-status document should never be treated as an approved source for
generated onboarding content, regardless of how confidently its own prose
reads.
-->
