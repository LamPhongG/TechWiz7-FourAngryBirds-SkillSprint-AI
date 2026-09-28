Write $quiz_count multiple-choice questions that check whether a $level $role_name has understood the most important rules of this document.

Question style for this level: $level_style

The learner has just studied these lessons. They are the only content you may assess:
<taught_lessons>
$taught_lessons
</taught_lessons>

Assessment the Role Requirement Matrix asks for on this document:
$assessments

Rules for every question
- It tests one fact that is stated in one chunk and taught by one of the lessons above: `quote_chunk_id` must be one of the lessons' chunk ids. A question on untaught content is rejected.
- Ask about the mandatory requirements first, in the way the matrix says they are assessed. Prefer a different section for each question.
- `options` has exactly 4 entries in the document's own language — the language of the chunks, even when `question` is in another language. Never translate an option. The correct option is a short phrase — a number, deadline, role, system, channel or step — copied character-for-character from `exact_quote`; a question whose correct option is not inside `exact_quote` is rejected.
- The 3 wrong options have the same type and a similar length as the correct one (numbers for a number, roles for a role), are plausible to someone who has not read the document, contradict the document, and do not appear inside `exact_quote`.
- Do not ask about document codes, version numbers, section numbers or page numbers.
- `explanation` states the rule from the document that makes the answer correct.

$hr_instructions
$document
