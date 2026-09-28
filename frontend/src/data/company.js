// COMPANY PROFILE — FourAngryBirds EdTech & HR Solutions
export const company = {
  name: "FourAngryBirds EdTech & HR Solutions JSC",
  nameEn: "FourAngryBirds EdTech & HR Solutions JSC",
  shortName: "FourAngryBirds",
  headcount: 250,
  offices: ["Ho Chi Minh City", "Da Nang"],
};

// Departments — English names are keys
export const DEPARTMENTS = [
  "Company-wide",
  "Sales",
  "Customer Support",
  "Human Resources",
  "Finance",
  "Operations",
  "Marketing",
  "Engineering",
  "Branch Management",
  "Data",
];

// 10 Job Roles (SRS Step 2)
export const ROLES = [
  { id: "sales-exec",       nameEn: "Sales Executive",            name: "Sales Executive",            department: "Sales" },
  { id: "cs-exec",          nameEn: "Customer Support Executive", name: "Customer Support Executive", department: "Customer Support" },
  { id: "hr-exec",          nameEn: "HR Executive",               name: "HR Executive",               department: "Human Resources" },
  { id: "finance-associate", nameEn: "Finance Associate",         name: "Finance Associate",          department: "Finance" },
  { id: "ops-coordinator",  nameEn: "Operations Coordinator",     name: "Operations Coordinator",     department: "Operations" },
  { id: "marketing-exec",   nameEn: "Marketing Executive",        name: "Marketing Executive",        department: "Marketing" },
  { id: "support-engineer", nameEn: "Software Support Engineer",  name: "Software Support Engineer",  department: "Engineering" },
  { id: "branch-manager",   nameEn: "Branch Manager",             name: "Branch Manager",             department: "Branch Management" },
  { id: "data-analyst",     nameEn: "Data Analyst",               name: "Data Analyst",               department: "Data" },
  { id: "team-leader",      nameEn: "Team Leader / Tech Lead",    name: "Team Leader / Tech Lead",    department: "Engineering" },
];

// Document Categories
export const DOCUMENT_CATEGORIES = [
  "Handbook",
  "Policy",
  "SOP",
  "Process Manual",
  "Role Description",
  "FAQ",
  "Compliance",
  "Test Case",
];

// Document Catalog: 28 knowledge documents in the repository (Company Profile).
// `family` groups versions of the same document for version management (SRS Step 8).
export const DOCUMENT_CATALOG = [
  { code: "DOC-01", family: "employee-handbook",        titleEn: "Employee Handbook",                    title: "Employee Handbook",                          category: "Handbook",         department: "Company-wide" },
  { code: "DOC-02", family: "employee-handbook",        titleEn: "Employee Handbook (obsolete)",         title: "Employee Handbook (obsolete)",                 category: "Handbook",         department: "Company-wide" },
  { code: "DOC-03", family: "hr-leave-policy",          titleEn: "HR Leave Policy",                      title: "HR Leave Policy",   category: "Policy",           department: "Human Resources" },
  { code: "DOC-04", family: "workplace-conduct-policy", titleEn: "Workplace Conduct Policy",             title: "Workplace Conduct Policy",                    category: "Policy",           department: "Company-wide" },
  { code: "DOC-05", family: "data-privacy-policy",      titleEn: "Data Privacy Policy",                  title: "Data Privacy Policy",        category: "Policy",           department: "Company-wide" },
  { code: "DOC-06", family: "information-security-policy", titleEn: "Information Security Policy",       title: "Information Security Policy",   category: "Policy",           department: "Company-wide" },
  { code: "DOC-07", family: "sop-customer-escalation",  titleEn: "SOP – Customer Escalation Process",    title: "SOP – Customer Escalation Process", category: "SOP",            department: "Customer Support" },
  { code: "DOC-08", family: "sop-sales-pipeline",       titleEn: "SOP – Sales Pipeline Management",      title: "SOP – Sales Pipeline Management",           category: "SOP",              department: "Sales" },
  { code: "DOC-09", family: "sop-financial-reimbursement", titleEn: "SOP – Financial Reimbursement",     title: "SOP – Financial Reimbursement",   category: "SOP",              department: "Finance" },
  { code: "DOC-10", family: "sop-software-deployment",  titleEn: "SOP – Software Deployment Workflow",   title: "SOP – Software Deployment Workflow", category: "SOP",             department: "Engineering" },
  { code: "DOC-11", family: "sop-employee-onboarding",  titleEn: "SOP – Employee Onboarding Process",    title: "SOP – Employee Onboarding Process",          category: "SOP",              department: "Human Resources" },
  { code: "DOC-12", family: "branch-operations-manual", titleEn: "Branch Management Operations Manual",  title: "Branch Management Operations Manual",                 category: "Process Manual",   department: "Branch Management" },
  { code: "DOC-13", family: "jd-sales-marketing",       titleEn: "Job Descriptions – Sales & Marketing", title: "Job Descriptions – Sales & Marketing", category: "Role Description", department: "Sales" },
  { code: "DOC-14", family: "jd-engineering-support",   titleEn: "Job Descriptions – Engineering & Support", title: "Job Descriptions – Engineering & Support", category: "Role Description", department: "Engineering" },
  { code: "DOC-15", family: "jd-hr-finance",            titleEn: "HR & Finance Role Descriptions",       title: "HR & Finance Role Descriptions",  category: "Role Description", department: "Human Resources" },
  { code: "DOC-16", family: "general-faqs",             titleEn: "General Company FAQs",                 title: "General Company FAQs",            category: "FAQ",              department: "Company-wide" },
  { code: "DOC-17", family: "conflicting-policy-sample", titleEn: "Conflicting Policy Sample",           title: "Conflicting Policy Sample (Contradiction Test)", category: "Test Case",       department: "Company-wide" },
  { code: "DOC-18", family: "adversarial-prompt-injection", titleEn: "Adversarial Prompt Injection Test", title: "Adversarial Prompt Injection Test Document", category: "Test Case",        department: "Company-wide" },
  { code: "DOC-19", family: "outdated-compliance-rules", titleEn: "Outdated Compliance Rules",           title: "Outdated Compliance Rules (Superseded)",     category: "Compliance",       department: "Company-wide" },
  { code: "DOC-20", family: "department-exceptions",    titleEn: "Department-Specific Exceptions",       title: "Department-Specific Exceptions",           category: "Policy",           department: "Company-wide" },
  { code: "DOC-21", family: "brand-content-guidelines", titleEn: "Brand & Content Guidelines", title: "Brand & Content Guidelines", category: "Policy", department: "Marketing" },
  { code: "DOC-22", family: "sop-digital-campaign-operations", titleEn: "SOP – Digital Campaign Operations", title: "SOP – Digital Campaign Operations", category: "SOP", department: "Marketing" },
  { code: "DOC-23", family: "sop-partner-school-session-delivery", titleEn: "SOP – Partner-School Session Delivery", title: "SOP – Partner-School Session Delivery", category: "SOP", department: "Operations" },
  { code: "DOC-24", family: "vendor-procurement-procedure", titleEn: "Vendor & Procurement Procedure", title: "Vendor & Procurement Procedure", category: "Process Manual", department: "Operations" },
  { code: "DOC-25", family: "data-governance-reporting-standards", titleEn: "Data Governance & Reporting Standards", title: "Data Governance & Reporting Standards", category: "Policy", department: "Data" },
  { code: "DOC-26", family: "metric-definitions", titleEn: "Metric Definitions", title: "Metric Definitions", category: "Process Manual", department: "Data" },
  { code: "DOC-27", family: "support-service-standards", titleEn: "Customer Support Service Standards & Knowledge Base", title: "Customer Support Service Standards & Knowledge Base", category: "SOP", department: "Customer Support" },
  { code: "DOC-28", family: "sop-budget-and-month-end-close", titleEn: "SOP – Budget Planning & Month-End Close", title: "SOP – Budget Planning & Month-End Close", category: "SOP", department: "Finance" },
];

// Upload Rules (SRS Step 4–5). PDF & DOCX are mandatory; TXT/MD/CSV are supplementary.
export const UPLOAD_RULES = {
  allowedExtensions: ["pdf", "docx", "txt", "md", "csv"],
  extensionAliases: { markdown: "md" },
  maxSizeMB: 20,
};

// Accepted file extensions
export const ACCEPTED_EXTENSIONS = [...UPLOAD_RULES.allowedExtensions, ...Object.keys(UPLOAD_RULES.extensionAliases)];

// Path purposes: onboarding for new hires, promotion for upskilling/role transitions
export const PATH_PURPOSES = ["onboarding", "promotion"];

export const SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"];

// Stage order templates
export const STAGE_TEMPLATES = {
  onboarding: ["day1", "week1", "week2", "day30", "day60", "day90"],
  promotion: ["foundation", "deep", "practice", "assessment"],
};

// Onboarding durations selectable by HR (SRS Step 13)
export const ONBOARDING_DURATIONS = {
  7: ["day1", "week1"],
  30: ["day1", "week1", "week2", "day30"],
  90: STAGE_TEMPLATES.onboarding,
};
export const DEFAULT_ONBOARDING_DAYS = 90;

export function stageTemplate(purpose, durationDays) {
  if (purpose === "onboarding") return ONBOARDING_DURATIONS[durationDays || DEFAULT_ONBOARDING_DAYS];
  return STAGE_TEMPLATES[purpose] || STAGE_TEMPLATES.onboarding;
}

// Knowledge tier of documents: company foundations first, department operations later
export function docTier(doc) {
  if (doc.category === "Handbook") return 0;
  if ((doc.category === "Policy" || doc.category === "Compliance") && doc.department === "Company-wide") return 1;
  if (["Policy", "Compliance", "Role Description"].includes(doc.category)) return 2;
  if (doc.category === "SOP" || doc.category === "Process Manual") return 3;
  return 4;
}

