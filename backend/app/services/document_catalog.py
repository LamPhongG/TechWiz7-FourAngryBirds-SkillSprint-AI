"""The company's expected document list (frontend `data/company.js` DOCUMENT_CATALOG).

Used to derive a document's `family` (versions of the same document share it) and standard titles.
"""
import re
import unicodedata
from dataclasses import dataclass

CATEGORIES = ("Handbook", "Policy", "SOP", "Process Manual", "Role Description", "FAQ", "Compliance", "Test Case")


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    family: str
    title: str
    title_en: str
    category: str
    department: str


CATALOG = {e.code: e for e in [
    CatalogEntry("DOC-01", "employee-handbook", "Employee Handbook", "Employee Handbook", "Handbook", "Company-wide"),
    CatalogEntry("DOC-02", "employee-handbook", "Employee Handbook (obsolete)", "Employee Handbook (obsolete)", "Handbook", "Company-wide"),
    CatalogEntry("DOC-03", "hr-leave-policy", "HR Leave Policy", "HR Leave Policy", "Policy", "Human Resources"),
    CatalogEntry("DOC-04", "workplace-conduct-policy", "Workplace Conduct Policy", "Workplace Conduct Policy", "Policy", "Company-wide"),
    CatalogEntry("DOC-05", "data-privacy-policy", "Data Privacy Policy", "Data Privacy Policy", "Policy", "Company-wide"),
    CatalogEntry("DOC-06", "information-security-policy", "Information Security Policy", "Information Security Policy", "Policy", "Company-wide"),
    CatalogEntry("DOC-07", "sop-customer-escalation", "SOP – Customer Escalation Process", "SOP – Customer Escalation Process", "SOP", "Customer Support"),
    CatalogEntry("DOC-08", "sop-sales-pipeline", "SOP – Sales Pipeline Management", "SOP – Sales Pipeline Management", "SOP", "Sales"),
    CatalogEntry("DOC-09", "sop-financial-reimbursement", "SOP – Financial Reimbursement", "SOP – Financial Reimbursement", "SOP", "Finance"),
    CatalogEntry("DOC-10", "sop-software-deployment", "SOP – Software Deployment Workflow", "SOP – Software Deployment Workflow", "SOP", "Engineering"),
    CatalogEntry("DOC-11", "sop-employee-onboarding", "SOP – Employee Onboarding Process", "SOP – Employee Onboarding Process", "SOP", "Human Resources"),
    CatalogEntry("DOC-12", "branch-operations-manual", "Branch Management Operations Manual", "Branch Management Operations Manual", "Process Manual", "Branch Management"),
    CatalogEntry("DOC-13", "jd-sales-marketing", "Job Descriptions – Sales & Marketing", "Job Descriptions – Sales & Marketing", "Role Description", "Sales"),
    CatalogEntry("DOC-14", "jd-engineering-support", "Job Descriptions – Engineering & Support", "Job Descriptions – Engineering & Support", "Role Description", "Engineering"),
    CatalogEntry("DOC-15", "jd-hr-finance", "HR & Finance Role Descriptions", "HR & Finance Role Descriptions", "Role Description", "Human Resources"),
    CatalogEntry("DOC-16", "general-faqs", "General Company FAQs", "General Company FAQs", "FAQ", "Company-wide"),
    CatalogEntry("DOC-17", "conflicting-policy-sample", "Conflicting Policy Sample", "Conflicting Policy Sample", "Test Case", "Company-wide"),
    CatalogEntry("DOC-18", "adversarial-prompt-injection", "Adversarial Prompt Injection Test", "Adversarial Prompt Injection Test", "Test Case", "Company-wide"),
    CatalogEntry("DOC-19", "outdated-compliance-rules", "Outdated Compliance Rules", "Outdated Compliance Rules", "Compliance", "Company-wide"),
    CatalogEntry("DOC-20", "department-exceptions", "Department-Specific Exceptions", "Department-Specific Exceptions", "Policy", "Company-wide"),
    CatalogEntry("DOC-21", "brand-content-guidelines", "Brand & Content Guidelines", "Brand & Content Guidelines", "Policy", "Marketing"),
    CatalogEntry("DOC-22", "sop-digital-campaign-operations", "SOP – Digital Campaign Operations", "SOP – Digital Campaign Operations", "SOP", "Marketing"),
    CatalogEntry("DOC-23", "sop-partner-school-session-delivery", "SOP – Partner-School Session Delivery", "SOP – Partner-School Session Delivery", "SOP", "Operations"),
    CatalogEntry("DOC-24", "vendor-procurement-procedure", "Vendor & Procurement Procedure", "Vendor & Procurement Procedure", "Process Manual", "Operations"),
    CatalogEntry("DOC-25", "data-governance-reporting-standards", "Data Governance & Reporting Standards", "Data Governance & Reporting Standards", "Policy", "Data"),
    CatalogEntry("DOC-26", "metric-definitions", "Metric Definitions", "Metric Definitions", "Process Manual", "Data"),
    CatalogEntry("DOC-27", "support-service-standards", "Customer Support Service Standards & Knowledge Base", "Customer Support Service Standards & Knowledge Base", "SOP", "Customer Support"),
    CatalogEntry("DOC-28", "sop-budget-and-month-end-close", "SOP – Budget Planning & Month-End Close", "SOP – Budget Planning & Month-End Close", "SOP", "Finance"),
]}


def _slugify(text: str) -> str:
    text = re.sub(r"\bobsolete\b", "", text.lower())
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def family_of(code: str, title_en: str) -> str:
    """Catalog family when the code is known, otherwise a slug of the English title."""
    entry = CATALOG.get(code)
    return entry.family if entry else _slugify(title_en)


def catalog_title(code: str, title_en: str) -> str:
    entry = CATALOG.get(code)
    if entry is None:
        return title_en
    # The "(obsolete)" marker belongs to the catalog listing, not to the document itself.
    return re.sub(r"\s*\(obsolete\)$", "", entry.title_en or entry.title)


vietnamese_title = catalog_title

