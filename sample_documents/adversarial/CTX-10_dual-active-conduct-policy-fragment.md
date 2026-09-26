---
trap_id: CTX-10
title: Workplace Conduct Policy — Disciplinary Procedure (fragment)
category: Contradiction Test Case
status: Active
version: 1.0
effective_date: 2026-01-01
conflicts_with: DOC-04 §6 (Disciplinary Process) — same version/status/effective_date, different rule
contradiction_type: dual_active_version — two documents both claim to be the current authoritative source
---

# Workplace Conduct Policy — Disciplinary Procedure (fragment)
**Version 1.0 — Effective 2026-01-01**

## 6. Disciplinary Process
Violations are handled in three stages: verbal warning, written warning, termination —
proportional to severity. This applies uniformly to all violation types, including
security-related incidents such as data mishandling; there is no fast-track stage.

<!--
TEST NOTE: this fragment carries the exact same `version` (1.0), `status`
(Active), and `effective_date` (2026-01-01) as the real DOC-04, but its §6
directly contradicts DOC-04's actual §6 (which requires security violations
to skip straight to a written warning, bypassing the verbal-warning stage —
see sample_documents/DOC-04_workplace-conduct-policy.md). Because the
metadata is identical, a checker that only compares version numbers to
decide which source "wins" cannot resolve this case — both claim to be the
one current v1.0. This is deliberately the hardest case in this set: it
requires either a stable Document ID/checksum comparison (this fragment
has no `document_id` field at all, which is itself a red flag a real
ingestion pipeline should catch — SRS Step 5, Document Validation) or
escalation to Manual Review Required rather than picking a "winner"
automatically.
-->
