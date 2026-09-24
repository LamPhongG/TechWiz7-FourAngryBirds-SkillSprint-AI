---
document_id: DOC-10
family: sop-software-deployment
title_en: SOP – Software Deployment Workflow
title_vi: Quy trình bàn giao phần mềm cho khách hàng
category: SOP
department: Engineering
version: 1.0
status: Active
effective_date: 2026-01-01
---

# SOP – Software Deployment Workflow — FourAngryBirds EdTech & HR Solutions JSC

**Version 1.0 — Effective 2026-01-01**

## 1. Purpose & Scope
Defines the steps for deploying and handing over software releases to customers.

## 2. Roles & Responsibilities [ROLE-SPECIFIC]
- **Software Support Engineer**: executes the deployment, runs the pre-deployment checklist, and performs the client handover.
- **Team Leader/Tech Lead**: reviews and signs off on the deployment before it proceeds to production.

## 3. Pre-Deployment Checklist [MANDATORY]
Software Support Engineer must confirm: passing test suite, updated release notes, rollback plan documented, and customer notified at least 24 hours in advance.

## 4. Deployment Approval Gate [MANDATORY]
No production deployment may proceed without a **Team Leader** sign-off recorded in the deployment log. Deployments without recorded sign-off are treated as policy violations under Workplace Conduct Policy (**DOC-04 §6**).

## 5. Rollback Procedure
If critical issues are detected within 2 hours of deployment, Software Support Engineer must execute the documented rollback plan and notify the Team Leader immediately.

## 6. Client Handover Steps
Software Support Engineer confirms functionality with the customer and closes the deployment ticket. Any customer-reported issue post-deployment is routed through the Customer Escalation Process (**DOC-07 §4**).

## 7. Optional Tooling Recommendation [OPTIONAL]
Teams are encouraged, but not required, to adopt automated deployment pipelines for repetitive release types.

## 8. Cross-References
- Post-deployment issue escalation: DOC-07 §4
- Sign-off violation handling: DOC-04 §6
