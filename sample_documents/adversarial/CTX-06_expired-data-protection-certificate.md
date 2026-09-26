---
trap_id: CTX-06
title: Data Protection Compliance Certificate
category: Contradiction Test Case
status: Active
version: 1.0
effective_date: 2024-07-01
expiry_date: 2025-06-30
conflicts_with: DOC-05 (Data Privacy Policy, current) — this certificate is cited as its compliance basis but has expired
contradiction_type: outdated_source — expiry_date has passed but document is still marked status Active and still referenced
---

# Data Protection Compliance Certificate
**Issued by: (fictional) Vietnam Data Protection Assessment Board**
**Certificate No.: VDPA-2024-0417**

This certifies that FourAngryBirds EdTech & HR Solutions JSC has been assessed and found
compliant with applicable personal-data-protection requirements for the period below.

- **Effective date:** 1 July 2024
- **Expiry date:** 30 June 2025
- **Scope:** Employee and customer personal data handling practices.

This certificate must be renewed annually. Onboarding materials referencing data-privacy
compliance should cite the current certificate.

<!--
TEST NOTE: this certificate's own `expiry_date` (2025-06-30) has already
passed relative to the company's current onboarding documents (all
effective 2026-01-01), yet its `status` field still says Active and nothing
in the document set formally retires it. This tests SRS Step 8 (Document
Version Control) and the "Outdated Source" validation status specifically
via the `expiry_date` field, which is a different signal than the
`supersedes`/`superseded_by` mechanism used by DOC-01/DOC-02 — a checker
that only looks at supersede links will miss a document that is stale
purely because its own expiry date has lapsed.
-->
