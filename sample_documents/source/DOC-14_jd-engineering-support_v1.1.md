---
document_id: DOC-14
family: jd-engineering-support
title_en: Job Descriptions – Engineering & Support
category: Role Description
department: Engineering
version: 1.1
status: Active
effective_date: 2026-06-01
owner: Head of Engineering
supersedes: DOC-14 v1.0
---

# Job Descriptions – Engineering & Support

## 1. Purpose

This document describes the four technical and service roles that keep the Company's platform running for customers: Software Support Engineer, Team Leader / Tech Lead, Customer Support Executive and Data Analyst. It is the reference for recruitment, the onboarding learning path of each role (DOC-11) and probation reviews.

## 2. Common Standards for Technical Roles [MANDATORY]

- Access production customer data only through approved, logged tooling, never through direct database exports (DOC-06 §4).
- Use multi-factor authentication on every system that holds customer or financial data (DOC-06 §2).
- Report any suspected security incident to IT Security within 1 hour of discovery (DOC-06 §5).
- Complete the Information Security (DOC-06) and Data Privacy (DOC-05) modules within the first 30 days before production access is granted (DOC-01 §7, DOC-11 §6.3).

## 3. Software Support Engineer

### 3.1 Mission

Deliver software releases to customers safely and resolve technical issues that Customer Support cannot solve at Tier 1.

### 3.2 Key Responsibilities [MANDATORY]

- Execute deployments and run the pre-deployment checklist: passing test suite, updated release notes, documented rollback plan, and customer notified at least 24 hours in advance (DOC-10 §3).
- Record the Team Leader's sign-off in the deployment log before any production deployment (DOC-10 §4).
- Execute the rollback plan if critical issues appear within 2 hours of a deployment and inform the Team Leader immediately (DOC-10 §5).
- Confirm functionality with the customer at handover and close the deployment ticket (DOC-10 §6).
- Take technical ownership of Tier 2 tickets assigned by the Team Leader and update the ticket at least twice per business day, before 12:00 and before 17:00, until resolved.

### 3.3 Decision Limits [ROLE-SPECIFIC: Software Support Engineer]

- May execute a rollback without prior approval when the rollback criteria of DOC-10 §5 are met.
- May not deploy to production without a recorded Team Leader sign-off; deployments without sign-off are policy violations (DOC-10 §4, DOC-04 §6).

### 3.4 Performance Indicators

- Share of deployments completed without rollback.
- Share of deployments with a complete checklist and recorded sign-off (target: 100 percent).
- Median time to resolve Tier 2 technical tickets.

## 4. Team Leader / Tech Lead

### 4.1 Mission

Lead an engineering team, guard the quality of every release and act as the Tier 2 escalation owner for customer issues.

### 4.2 Key Responsibilities [MANDATORY]

- Review and sign off every production deployment of the team in the deployment log (DOC-10 §2, §4).
- Own Tier 2 customer escalations jointly with the Customer Support Executive (DOC-07 §3).
- Escalate any Tier 2 escalation still unresolved after 48 hours to the Branch Manager (DOC-07 §4.3).
- Run a weekly team review of open tickets, deployments and incidents.
- Coach new engineers through the role-critical modules of their onboarding learning path (DOC-11 §6.2).

### 4.3 Decision Limits [ROLE-SPECIFIC: Team Leader / Tech Lead]

- May approve flexible start times for Engineering and Data staff (DOC-01 §3.1).
- May accept a delegation from the Branch Manager for deals of 500,000,000 VND or more and for Tier 3 compensation only when named in a written delegation (DOC-12 §3.2).
- Annual leave entitlement is 15 days per year (DOC-03 §2.1).

### 4.4 Performance Indicators

- Number of Tier 2 escalations older than 48 hours.
- Change failure rate of the team's releases.
- Onboarding completion of new team members within deadlines.

## 5. Customer Support Executive

### 5.1 Mission

Be the first point of contact for customers and resolve issues quickly, escalating in time when an issue exceeds Tier 1.

### 5.2 Key Responsibilities [MANDATORY]

- Acknowledge every incoming customer issue within 2 business hours and attempt first-contact resolution using the approved knowledge base (DOC-07 §4.1).
- Escalate to a Team Leader within 1 business hour any complaint unresolved after 24 hours, or any complaint involving a safety, legal or financial risk (DOC-07 §4.2, requirement R001).
- Log every escalation with ticket ID, customer ID, tier reached, resolution and time-to-resolution (DOC-07 §5).
- Handle customer personal data during escalations only as allowed by DOC-05 §4 and DOC-06 §4.

### 5.3 Required Training [ROLE-SPECIFIC: Customer Support Executive]

Tier 2 Escalation Authority training must be completed during Week 1 of onboarding, before handling escalations unsupervised (DOC-07 §4.2, DOC-11 §6.2).

### 5.4 Performance Indicators

- Share of issues acknowledged within 2 business hours.
- First-contact resolution rate.
- Share of escalations raised within 1 business hour of the trigger.

## 6. Data Analyst

### 6.1 Mission

Turn the Company's operational and learning data into reports and insights while protecting the personal data behind them.

### 6.2 Key Responsibilities [MANDATORY]

- Use anonymised or aggregated datasets for analysis by default (DOC-05 §4, DOC-06 §4).
- Request access to identifiable data only with written approval from the Data Privacy Officer, stating the purpose and the retention period.
- Publish every recurring report with a data dictionary that names the source system and the date range.
- Delete working extracts that contain personal data within 14 days of the analysis being completed.

### 6.3 Decision Limits [ROLE-SPECIFIC: Data Analyst]

- May create dashboards from aggregated data without further approval.
- May not share row-level customer or learner data outside the Data team without Data Privacy Officer approval (DOC-05 §6).
- Flexible start time is available with manager approval (DOC-01 §3.1).

### 6.4 Performance Indicators

- On-time delivery of recurring reports.
- Number of data-handling exceptions found in the quarterly access review (target: zero).

## 7. On-Call Rotation

Engineering and Support take part in an on-call rotation outside working hours for incidents affecting all customers. On-call rules and their compensation are department-specific exceptions to the standard working hours and are defined in DOC-20.

## 8. Career Path

- Software Support Engineer → Senior Engineer → Team Leader / Tech Lead.
- Customer Support Executive → Senior Support Executive → Team Leader (Support).
- Data Analyst → Senior Data Analyst → Data Lead.

## 9. Revision History

| Version | Effective date | Section | Change |
| :--- | :--- | :--- | :--- |
| v1.1 | 2026-06-01 | §3.2 | Software Support Engineers update Tier 2 tickets twice per business day, before 12:00 and before 17:00 (was once). |
| v1.1 | 2026-06-01 | §6.2 | Data Analysts delete working extracts with personal data within 14 days of completing the analysis (was 30). |

## 10. Cross-References

- Deployment workflow: DOC-10 §2–§6
- Escalation tiers: DOC-07 §3–§5
- Data access and sharing: DOC-05 §4, §6; DOC-06 §2, §4, §5
- Leave entitlement for Team Leader: DOC-03 §2.1
- Delegation from Branch Manager: DOC-12 §3.2
- On-call exceptions: DOC-20
