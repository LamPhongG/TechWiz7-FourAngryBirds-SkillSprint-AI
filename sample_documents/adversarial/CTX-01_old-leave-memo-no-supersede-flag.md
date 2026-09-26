---
trap_id: CTX-01
title: HR Memo — Annual Leave Rules (2022)
category: Contradiction Test Case
status: Active
version: (none recorded)
effective_date: 2022-03-01
conflicts_with: DOC-01 §6 (Leave Carryover Rule, v2.0, current)
contradiction_type: silent_staleness — outdated rule with no supersede metadata
---

# HR Memo — Annual Leave Rules
**Internal HR Memo — 1 March 2022**

To all staff,

As a reminder, unused annual leave days **do not carry over** into the next calendar year
and are forfeited on 31 December each year. Please plan your leave accordingly before
year-end.

Thank you,
HR Team

<!--
TEST NOTE (not part of the document itself): unlike DOC-02, which is explicitly
tagged status: Obsolete / superseded_by: DOC-01, this memo carries NO version,
status, or supersede metadata at all. It reads as if it could still be current.
A ContradictionChecker that only compares explicitly-versioned documents will
miss this one; it must also flag undated/unversioned policy claims that
contradict a currently active, versioned document (DOC-01 §6: up to 5 days
carry over until 31 March).
-->
