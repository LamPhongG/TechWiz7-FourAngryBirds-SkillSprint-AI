---
document_id: DOC-25
family: data-governance-reporting-standards
title_en: Data Governance & Reporting Standards
category: Policy
department: Data
version: 1.0
status: Active
effective_date: 2026-09-01
owner: Head of Data
---

# Data Governance & Reporting Standards

## 1. Purpose

This policy sets the rules the Data team follows when it collects, stores, analyses and publishes data. It applies the privacy and security rules of DOC-05 and DOC-06 to analytics work and describes how reports and dashboards are produced so that every department reads the same numbers. The Data Analyst role is described in DOC-14 §6.

## 2. Scope

The policy applies to every dataset held by the Data team, every report or dashboard it publishes and every employee who requests data from the Data team. Data kept inside operational systems (CRM, learning platform, accounting system) remains under the rules of the system owner until it is copied into the analytics environment.

## 3. Data Classification [MANDATORY]

Every dataset in the analytics environment carries one of four classes:

- **Public**: data already published by the Company, such as figures in a published report.
- **Internal**: business data without personal data, such as campaign spend or session counts. Available to employees who need it for their work.
- **Confidential**: aggregated data derived from personal data, such as learner completion rates per school. Available to named teams only.
- **Restricted**: data that identifies a person, such as learner records, customer contacts, employee records or payment records. Available only with Data Privacy Officer approval (DOC-05 §4).

When a dataset mixes classes, it takes the highest class it contains.

## 4. Dataset Register

- Every dataset in the analytics environment is listed in the dataset register with its owner, source system, class, refresh frequency and retention period.
- A dataset that is not in the register is deleted by the Data team during the quarterly access review of Section 12.
- The register is updated before a new dataset is shared with anyone outside the Data team.

## 5. Access to Data [MANDATORY]

### 5.1 Default Access

Data Analysts use anonymised or aggregated datasets by default (DOC-05 §4, DOC-06 §4). Access to Restricted data is not part of the default role.

### 5.2 Requesting Identifiable Data

A request for Restricted data is made in writing to the Data Privacy Officer. It states the purpose, the fields needed, the period covered and how long the data will be kept (DOC-14 §6.2). Access is granted for that purpose only and ends when the analysis is complete.

### 5.3 Fraud Review Exception

Access to identifiable payment records for a suspected reimbursement fraud or duplicate payment follows the exception in DOC-20 §7: written approval from the Data Privacy Officer, one named Data Analyst, access limited to 10 business days per investigation, and findings reported to the Finance Manager only.

### 5.4 Access for Other Departments

Other departments receive reports and dashboards, not row-level data. Row-level customer or learner data is not shared outside the Data team without Data Privacy Officer approval (DOC-05 §6, DOC-14 §6.3).

## 6. Anonymisation Standard [MANDATORY]

- Direct identifiers are removed: names, email addresses, phone numbers, national ID numbers, employee codes and exact addresses.
- Dates of birth are reduced to the year; locations are reduced to the office or the province.
- Any group with fewer than 5 people is not shown in a report or dashboard. It is merged with a neighbouring group or shown as "fewer than 5".
- Free-text fields, such as comments in surveys or tickets, are not included in anonymised datasets because they often contain names.
- An anonymised dataset is checked by a second Data Analyst before it is shared.

## 7. Working Extracts

- Working extracts are stored only in the analytics environment, never on a laptop's local disk, a USB drive or a personal account (DOC-06 §6).
- An extract that contains personal data is deleted within 14 days of the analysis being completed (DOC-14 §6.2).
- Extracts from production systems are made only through approved, logged tooling, never by direct database export (DOC-06 §4).

## 8. Data Quality Checks

Before a dataset is used in a published report, the Data Analyst checks:

- Completeness: the number of rows matches the source system for the period.
- Freshness: the latest record is not older than the refresh frequency in the dataset register.
- Duplicates: records that appear twice are removed and the number removed is noted.
- Consistency: totals match the totals of the previous report for periods that did not change.

A report is not published when a check fails; the owner of the report is told the reason and the new publication date.

## 9. Reports and Dashboards [MANDATORY]

- Every recurring report is published with a data dictionary that names the source system and the date range (DOC-14 §6.2).
- Metrics use the definitions in the metric catalogue DOC-26. A new metric is added to DOC-26 before it appears in a published report.
- Each report shows the date of the data it uses and the name of its owner.
- Dashboards built from aggregated data may be created by a Data Analyst without further approval (DOC-14 §6.3). Dashboards that show Restricted data are not allowed.
- Monthly reports are published by the 5th business day of the following month, the same day as the budget report of DOC-28 §4.

## 10. Retention and Deletion

- Datasets follow the retention periods of DOC-05 §5: customer data is kept for 3 years after the last active engagement, then anonymised or deleted; employee records are kept for 5 years after the end of employment.
- When a partner-school contract ends, learner data received from that school is deleted from the analytics environment within 30 calendar days, in line with DOC-12 §6.5.
- Aggregated datasets without personal data may be kept for as long as they are needed for trend reports.

## 11. Incidents

Any suspected loss or exposure of data, such as a report sent to the wrong recipient or an extract found outside the analytics environment, is reported to IT Security within 1 hour of discovery (DOC-06 §5). IT Security informs the Data Privacy Officer within 24 hours when personal data is involved (DOC-05 §7).

## 12. Quarterly Access Review

Every quarter the Data team reviews who has access to each dataset, removes access that is no longer needed and deletes datasets that are not in the register. The number of data-handling exceptions found in the review is a performance indicator of the Data Analyst role (DOC-14 §6.4), with a target of zero.

## 13. Optional Practice [OPTIONAL]

Report owners are encouraged to add a short "how to read this report" note at the top of every new report.

## 14. Cross-References

- Data Analyst role and decision limits: DOC-14 §6
- Personal data access, sharing, retention and breaches: DOC-05 §4–§7
- Production data tooling, remote access, incident reporting: DOC-06 §4–§6
- Fraud review exception: DOC-20 §7
- Metric definitions: DOC-26
- Partner-school offboarding: DOC-12 §6.5
- Monthly budget report: DOC-28 §4
