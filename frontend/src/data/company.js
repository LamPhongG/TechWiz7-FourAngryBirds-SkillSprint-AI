// HỒ SƠ CÔNG TY — FourAngryBirds EdTech & HR Solutions
// Field song ngữ: `xxx` = tiếng Việt, `xxxEn` = tiếng Anh (đọc bằng pick())
export const company = {
  name: "Công ty Cổ phần Công nghệ Giáo dục và Giải pháp Nhân sự FourAngryBirds",
  nameEn: "FourAngryBirds EdTech & HR Solutions JSC",
  shortName: "FourAngryBirds",
  headcount: 250,
  offices: ["TP. Hồ Chí Minh", "Đà Nẵng"],
};

// Phòng ban — giá trị tiếng Anh là khóa, dịch qua tv()
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

// 10 vị trí công việc (SRS Step 2)
export const ROLES = [
  { id: "sales-exec",       nameEn: "Sales Executive",            name: "Nhân viên Kinh doanh phần mềm B2B",         department: "Sales" },
  { id: "cs-exec",          nameEn: "Customer Support Executive", name: "Nhân viên Chăm sóc khách hàng",             department: "Customer Support" },
  { id: "hr-exec",          nameEn: "HR Executive",               name: "Nhân viên Nhân sự / Tuyển dụng & Onboarding", department: "Human Resources" },
  { id: "finance-associate", nameEn: "Finance Associate",         name: "Chuyên viên Tài chính - Kế toán",           department: "Finance" },
  { id: "ops-coordinator",  nameEn: "Operations Coordinator",     name: "Điều phối viên Vận hành hệ thống",          department: "Operations" },
  { id: "marketing-exec",   nameEn: "Marketing Executive",        name: "Nhân viên Tiếp thị kỹ thuật số",            department: "Marketing" },
  { id: "support-engineer", nameEn: "Software Support Engineer",  name: "Kỹ sư Hỗ trợ Kỹ thuật phần mềm",            department: "Engineering" },
  { id: "branch-manager",   nameEn: "Branch Manager",             name: "Giám quản Chi nhánh",                       department: "Branch Management" },
  { id: "data-analyst",     nameEn: "Data Analyst",               name: "Chuyên viên Phân tích dữ liệu doanh nghiệp", department: "Data" },
  { id: "team-leader",      nameEn: "Team Leader / Tech Lead",    name: "Trưởng nhóm Kỹ thuật / Phát triển sản phẩm", department: "Engineering" },
];

// Loại tài liệu — giá trị tiếng Anh là khóa, dịch qua tv()
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

// Danh mục 20 tài liệu tri thức cần có trong kho (hồ sơ công ty).
// `family` gom các phiên bản của cùng một tài liệu để quản lý version (SRS Step 8).
export const DOCUMENT_CATALOG = [
  { code: "DOC-01", family: "employee-handbook",        titleEn: "Employee Handbook",                    title: "Sổ tay nhân viên",                          category: "Handbook",         department: "Company-wide" },
  { code: "DOC-02", family: "employee-handbook",        titleEn: "Employee Handbook (obsolete)",         title: "Sổ tay nhân viên (bản cũ)",                 category: "Handbook",         department: "Company-wide" },
  { code: "DOC-03", family: "hr-leave-policy",          titleEn: "HR Leave Policy",                      title: "Chính sách nghỉ phép, nghỉ ốm, thai sản",   category: "Policy",           department: "Human Resources" },
  { code: "DOC-04", family: "workplace-conduct-policy", titleEn: "Workplace Conduct Policy",             title: "Quy tắc ứng xử công sở",                    category: "Policy",           department: "Company-wide" },
  { code: "DOC-05", family: "data-privacy-policy",      titleEn: "Data Privacy Policy",                  title: "Chính sách bảo mật dữ liệu cá nhân",        category: "Policy",           department: "Company-wide" },
  { code: "DOC-06", family: "information-security-policy", titleEn: "Information Security Policy",       title: "Chính sách an toàn thông tin & mật khẩu",   category: "Policy",           department: "Company-wide" },
  { code: "DOC-07", family: "sop-customer-escalation",  titleEn: "SOP – Customer Escalation Process",    title: "Quy trình xử lý khiếu nại & leo thang sự cố", category: "SOP",            department: "Customer Support" },
  { code: "DOC-08", family: "sop-sales-pipeline",       titleEn: "SOP – Sales Pipeline Management",      title: "Quy trình quản lý phễu bán hàng",           category: "SOP",              department: "Sales" },
  { code: "DOC-09", family: "sop-financial-reimbursement", titleEn: "SOP – Financial Reimbursement",     title: "Quy trình hoàn tiền, thanh toán chi phí",   category: "SOP",              department: "Finance" },
  { code: "DOC-10", family: "sop-software-deployment",  titleEn: "SOP – Software Deployment Workflow",   title: "Quy trình bàn giao phần mềm cho khách hàng", category: "SOP",             department: "Engineering" },
  { code: "DOC-11", family: "sop-employee-onboarding",  titleEn: "SOP – Employee Onboarding Process",    title: "Quy trình hội nhập nhân sự chuẩn",          category: "SOP",              department: "Human Resources" },
  { code: "DOC-12", family: "branch-operations-manual", titleEn: "Branch Management Operations Manual",  title: "Sổ tay vận hành chi nhánh",                 category: "Process Manual",   department: "Branch Management" },
  { code: "DOC-13", family: "jd-sales-marketing",       titleEn: "Job Descriptions – Sales & Marketing", title: "Mô tả công việc khối Kinh doanh & Marketing", category: "Role Description", department: "Sales" },
  { code: "DOC-14", family: "jd-engineering-support",   titleEn: "Job Descriptions – Engineering & Support", title: "Mô tả công việc khối Kỹ thuật & Hỗ trợ", category: "Role Description", department: "Engineering" },
  { code: "DOC-15", family: "jd-hr-finance",            titleEn: "HR & Finance Role Descriptions",       title: "Mô tả công việc khối Nhân sự & Tài chính",  category: "Role Description", department: "Human Resources" },
  { code: "DOC-16", family: "general-faqs",             titleEn: "General Company FAQs",                 title: "Câu hỏi thường gặp về phúc lợi",            category: "FAQ",              department: "Company-wide" },
  { code: "DOC-17", family: "conflicting-policy-sample", titleEn: "Conflicting Policy Sample",           title: "Mẫu quy định xung đột (test Contradiction)", category: "Test Case",       department: "Company-wide" },
  { code: "DOC-18", family: "adversarial-prompt-injection", titleEn: "Adversarial Prompt Injection Test", title: "Tài liệu tấn công Prompt Injection (test)", category: "Test Case",        department: "Company-wide" },
  { code: "DOC-19", family: "outdated-compliance-rules", titleEn: "Outdated Compliance Rules",           title: "Quy định tuân thủ cũ (đã bị thay thế)",     category: "Compliance",       department: "Company-wide" },
  { code: "DOC-20", family: "department-exceptions",    titleEn: "Department-Specific Exceptions",       title: "Ngoại lệ đặc thù theo phòng ban",           category: "Policy",           department: "Company-wide" },
];

// Quy tắc tải lên (SRS Step 4–5). PDF & DOCX là bắt buộc, TXT/MD/CSV là bổ sung.
export const UPLOAD_RULES = {
  allowedExtensions: ["pdf", "docx", "txt", "md", "csv"],
  maxSizeMB: 20,
};

// Mục đích lộ trình: nhân viên mới hội nhập, hoặc bồi dưỡng khi thăng chức / chuyển vị trí
export const PATH_PURPOSES = ["onboarding", "promotion"];

export const SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"];

// Thứ tự giai đoạn theo mục đích — thứ tự này là chuẩn để kiểm tra "đúng luồng"
export const STAGE_TEMPLATES = {
  onboarding: ["day1", "week1", "week2", "day30", "day60", "day90"],
  promotion: ["foundation", "deep", "practice", "assessment"],
};

// Tầng kiến thức của tài liệu: nền tảng công ty học trước, nghiệp vụ phòng ban học sau
export function docTier(doc) {
  if (doc.category === "Handbook") return 0;
  if ((doc.category === "Policy" || doc.category === "Compliance") && doc.department === "Company-wide") return 1;
  if (["Policy", "Compliance", "Role Description"].includes(doc.category)) return 2;
  if (doc.category === "SOP" || doc.category === "Process Manual") return 3;
  return 4;
}
