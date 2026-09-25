// Vòng đời lộ trình và quyền thao tác theo vai trò.
//
//   HR tạo ──► draft ──(HR gửi duyệt)──► in_review ──(Reviewer duyệt)──► published ──► archived
//                ▲                           │
//                └──── changes_requested ◄───┘ (Reviewer yêu cầu sửa, kèm góp ý)
//
// HR sửa nội dung khi draft / changes_requested; Reviewer sửa trực tiếp khi in_review.
// Nội dung đã phát hành chỉ đọc — muốn đổi thì thu hồi và tạo bản mới.
import { MIN_REASON_LENGTH } from "./pathChecks";

const ACTIONS = {
  hr: {
    edit: ["draft", "changes_requested"],
    regenerate: ["draft", "changes_requested"],
    submit: ["draft", "changes_requested"],
    delete: ["draft"],
    archive: ["published"],
    comment: ["draft", "in_review", "changes_requested", "published"],
  },
  reviewer: {
    edit: ["in_review"],
    request_changes: ["in_review"],
    approve: ["in_review"],
    archive: ["published"],
    comment: ["in_review", "changes_requested", "published"],
  },
};

export function can(userRole, action, path) {
  return !!path && (ACTIONS[userRole]?.[action] || []).includes(path.status);
}

/**
 * Điều kiện để Reviewer duyệt và phát hành.
 * Nội dung sai kiến thức / có câu lệnh tấn công / lỗi cấu trúc thì không được phát hành dù có lý do —
 * Reviewer phải sửa trực tiếp hoặc trả về HR. Các cảnh báo khác cho phép duyệt nếu ghi lý do.
 */
export function approvalRule(checks) {
  if (checks.blocking) return { allowed: false, reasonRequired: false };
  return { allowed: true, reasonRequired: checks.final_status !== "verified" };
}

export function validReason(text) {
  return (text || "").trim().length >= MIN_REASON_LENGTH;
}

/** Nhân viên thấy lộ trình khi đã phát hành cho phòng ban, cho "Toàn công ty", hoặc cho đúng vị trí của mình */
export function visibleToEmployee(path, user) {
  if (path.status !== "published" || !path.published_to || !user) return false;
  const { departments = [], roles = [] } = path.published_to;
  return departments.includes("Company-wide") || departments.includes(user.department) || roles.includes(user.role_id);
}
