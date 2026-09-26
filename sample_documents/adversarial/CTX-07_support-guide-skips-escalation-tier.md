---
trap_id: CTX-07
title: Customer Support Quick Guide
category: Contradiction Test Case
status: Active
version: 1.0
effective_date: 2026-02-08
conflicts_with: DOC-07 §4.2-4.3 (Escalation Tiers); role_matrix.csv R001, R073
contradiction_type: process_sequence_conflict — skips a mandatory tier in the escalation chain
---

# Customer Support Quick Guide
**Printed handout for new Customer Support Executives**

## When Things Go Wrong
If a customer complaint is serious or you can't resolve it quickly, don't waste time —
send it straight to the **Branch Manager**. They can approve refunds and compensation
directly, so it's faster to go straight to the top.

<!--
TEST NOTE: DOC-07 §4.2 requires unresolved/high-risk complaints to escalate
to a Team Leader first (Tier 2); only if unresolved after 48 hours does it
advance to the Branch Manager (Tier 3, §4.3). role_matrix.csv rows R001
(Customer Support Executive) and R073 (Team Leader/Tech Lead) both encode
the Team Leader as the mandatory first escalation point. This handout skips
Tier 2 entirely. It tests SRS Step 27 (Learning Sequence Validation) applied
to a process/SOP rather than a learning-module sequence — the checker must
recognize that "skip a step" is a distinct contradiction type from
"wrong number" (CTX-05) or "self-contradiction" (CTX-04).
-->
