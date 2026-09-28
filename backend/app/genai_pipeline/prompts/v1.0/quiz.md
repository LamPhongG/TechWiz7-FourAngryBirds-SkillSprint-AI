Write $quiz_count multiple-choice questions that check whether a $level $role_name has understood the most important rules of this document.

Question style for this level: $level_style

Rules for every question
- It tests one fact that is stated in one chunk. Prefer a different section for each question.
- `options` has exactly 4 entries written in the document's language. The correct option is a short phrase — a number, deadline, role, system, channel or step — that appears word-for-word inside `exact_quote`.
- The 3 wrong options have the same type and a similar length as the correct one (numbers for a number, roles for a role), are plausible to someone who has not read the document, contradict the document, and do not appear inside `exact_quote`.
- Do not ask about document codes, version numbers, section numbers or page numbers.
- `explanation` states the rule from the document that makes the answer correct.

$hr_instructions
$document
