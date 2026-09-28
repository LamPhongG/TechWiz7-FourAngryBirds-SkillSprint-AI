---
document_id: RD-07
role_id: support-engineer
family: role-description-software-support-engineer
title_en: Role Description – Software Support Engineer
title_vi: Mô tả công việc – Kỹ sư Hỗ trợ Kỹ thuật phần mềm
category: Role Description
department: Engineering
version: 1.0
status: Active
effective_date: 2026-01-01
reports_to: Team Leader/Tech Lead
---

# Role Description — Software Support Engineer
**FourAngryBirds EdTech & HR Solutions JSC — Engineering Department**

## 1. Role Summary
The Software Support Engineer executes and hands over software deployments to customers, and reports to **Team Leader/Tech Lead**.

## 2. Core Responsibilities
- Complete the pre-deployment checklist before any production release.
- Execute rollback procedures immediately if critical issues appear post-deployment.
- Confirm functionality with the customer and close out the handover.
- Access production/customer data only through approved, logged tooling.
- Secure engineering systems with strong authentication.

## 3. Required Competencies
Pre-deployment readiness verification, incident rollback execution, client handover discipline, secure production-data access, least-privilege data access (Engineering), systems access security.

## 4. Governing Documents
- SOP – Software Deployment Workflow (**DOC-10**) — primary reference.
- Information Security Policy (**DOC-06**, §2 password/MFA, §4 data handling).
- Data Privacy Policy (**DOC-05**, §4 access roles).
- Employee Handbook (**DOC-01**) and HR Leave Policy (**DOC-03**).

## 5. Mandatory Onboarding Requirements (from `role_matrix/role_matrix.csv`)
| Requirement ID | Requirement | Mandatory/Optional | Priority | Source |
| --- | --- | --- | --- | --- |
| R049 | Confirm passing test suite, updated release notes, documented rollback plan, and 24-hour customer notice before deployment | Mandatory | High | DOC-10 §3 |
| R050 | Execute the documented rollback plan and notify the Team Leader immediately if critical issues appear within 2 hours | Mandatory | High | DOC-10 §5 |
| R051 | Confirm functionality with the customer and close the deployment ticket at handover | Mandatory | Medium | DOC-10 §6 |
| R052 | Access production customer data only through approved, logged tooling — never direct database export | Mandatory | High | DOC-06 §4 |
| R053 | Access only role-relevant data per least-privilege rules; use anonymized data unless explicitly authorized | Mandatory | High | DOC-05 §4 |
| R054 | Use passwords ≥ 12 characters with mixed case/numbers/symbols; enable MFA on all systems handling customer data | Mandatory | High | DOC-06 §2 |
| R055 | Digitally acknowledge the Employee Handbook within 5 business days of joining | Mandatory | High | DOC-01 §9 |
| R056 | Accrue and use the standard 12-day annual leave entitlement | Mandatory | Low | DOC-03 §2 |

## 6. Frequently Asked Questions
**Q: Can I deploy to production without Team Leader sign-off if the change is small?**
A: No — DOC-10 §4 requires sign-off on every production deployment, regardless of size (see RD-10, Team Leader/Tech Lead, R074).

**Q: A critical bug appears 3 hours after deployment — does the rollback rule still apply?**
A: R050's 2-hour rollback trigger applies to the initial detection window; a bug found later still requires immediate rollback and Team Leader notification, just outside the fastest-response SLA.

## 7. Escalation & Reporting Line
Software Support Engineer → **Team Leader/Tech Lead** (deployment sign-off, rollback notification, technical escalation).
