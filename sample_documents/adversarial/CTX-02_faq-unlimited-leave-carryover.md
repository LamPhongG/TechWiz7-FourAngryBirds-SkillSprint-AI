---
trap_id: CTX-02
title: Employee FAQ — Leave & Benefits
category: Contradiction Test Case
status: Active
version: 1.0
effective_date: 2026-01-15
conflicts_with: DOC-01 §6 (Leave Carryover Rule, v2.0, current)
contradiction_type: faq_contradicts_policy — precedence test (Policy > FAQ)
---

# Employee FAQ — Leave & Benefits

**Q: How much of my unused annual leave can I carry over to next year?**
A: You can carry over **all** of your unused annual leave — there's no cap, and there's
no deadline to use it either. Take your time!

**Q: Do I need to submit anything to use carried-over leave?**
A: No, carried-over leave works exactly like regular leave. Just submit your request as usual.

<!--
TEST NOTE: this FAQ directly contradicts the authoritative rule in DOC-01 §6
(max 5 days carried over, must be used by 31 March). Per SRS Step 34
(Policy Precedence Rules) and the precedence hierarchy documented in
sample_documents/README.md, an approved Policy document must outrank an FAQ.
The Python validation pipeline must resolve this in favor of DOC-01 §6 and
flag CTX-02 as a Contradiction Detected / lower-precedence source, not
silently prefer whichever document was chunked first.
-->
