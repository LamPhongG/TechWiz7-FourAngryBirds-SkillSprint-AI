// Path lifecycle and role-based permissions.
//
//   HR creates ──► draft ──(HR submits)──► in_review ──(Reviewer approves)──► published ──► archived
//                    ▲                           │
//                    └──── changes_requested ◄───┘ (Reviewer requests changes with comments)
//
// HR edits content during draft / changes_requested; Reviewer edits directly during in_review.
// Published content is read-only — modifications require creating a new revision.
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
 * Conditions for Reviewer approval and publication.
 * Hallucinations, prompt injections, or structural flow errors strictly block publication —
 * Reviewer must edit directly or request changes from HR. Other warnings permit approval with justification.
 */
export function approvalRule(checks) {
  if (checks.blocking) return { allowed: false, reasonRequired: false };
  return { allowed: true, reasonRequired: checks.final_status !== "verified" };
}

export function validReason(text) {
  return (text || "").trim().length >= MIN_REASON_LENGTH;
}

/** Employee sees path when published to their department, "Company-wide", or their specific role */
export function visibleToEmployee(path, user) {
  if (path.status !== "published" || !path.published_to || !user) return false;
  const { departments = [], roles = [] } = path.published_to;
  return departments.includes("Company-wide") || departments.includes(user.department) || roles.includes(user.role_id);
}
