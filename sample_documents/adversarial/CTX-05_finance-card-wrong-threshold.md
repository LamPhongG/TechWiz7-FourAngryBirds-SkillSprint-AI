---
trap_id: CTX-05
title: Finance Quick Reference Card
category: Contradiction Test Case
status: Active
version: 1.0
effective_date: 2026-02-05
conflicts_with: DOC-09 §4 (Approval Matrix); role_matrix.csv R026, R059
contradiction_type: numeric_threshold_conflict — same rule, two different numbers
---

# Finance Quick Reference Card
**Laminated desk card — Finance Department**

## Reimbursement Approval At A Glance
- Claims under 10,000,000 VND: your direct manager can approve.
- Claims of 10,000,000 VND or more: also needs Branch Manager sign-off.
- Submit receipts within 15 days.
- Payment within 10 business days of approval.

<!--
TEST NOTE: the official SOP (DOC-09 §4) and the Role Requirement Matrix
(R026, R059) both set the Branch Manager approval trigger at 5,000,000 VND,
not 10,000,000 VND. Everything else on this quick-reference card (15-day
submission window, 10-business-day payment) is correct and matches DOC-09
§3/§5 — only the threshold number is wrong. This is deliberately a
"mostly right, one number wrong" trap: a naive checker that only flags
documents which are entirely inconsistent will miss this, since 3 of the 4
facts on this card are correct. The checker must validate each individual
numeric claim against its source, not just the document as a whole.
-->
