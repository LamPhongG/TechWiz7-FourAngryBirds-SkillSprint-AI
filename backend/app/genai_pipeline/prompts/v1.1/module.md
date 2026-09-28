Build one learning module from the document below.

Learner: $role_name, $department department. Level: $level.
Purpose: $purpose_text
Timing: this is a $duration_text; the learner studies this module $stage_timing.
Studied before this module: $previous_modules

Role Requirement Matrix — what this role must learn from this document:
$requirements
Every mandatory requirement above must be taught by at least one lesson and, where the document states an obligation for it, practised by a task.

Learning objectives
- `learning_objectives`: 2 to 4 objectives in the output language. Each starts with an action verb and says what the learner can do after the module (for example "Escalate a complaint to Tier 2 within the deadline"). Cover the mandatory requirements first.

Lessons
- One lesson per section of the document, in document order. Merge sections that are only one or two sentences long into their neighbour. At most $max_lessons lessons.
- `content` explains what the learner must know or do, why it matters in their role, and any numbers, deadlines or responsibilities the section states. Use short paragraphs; start list items with "- ".
- `chunk_ids` lists every chunk the lesson draws on. Content that no lesson lists is content the learner has not been taught.
- `exact_quote` is the single most important sentence of the lesson.

Tasks
- Exactly $task_count tasks (fewer only if the document has fewer obligations).
- Style for this level: $task_style
- Each task is a concrete action the learner can perform at work $stage_timing, based on a sentence that states an obligation (must, should, required, never, always, ensure…).
- Only set tasks on what your lessons teach: `quote_chunk_id` must be one of the lessons' `chunk_ids`. A task on untaught content is rejected.
- `exact_quote` is that obligation sentence. It is the task's source; a task without a quote from the document is rejected.
- `completion_criteria` says how the learner and their manager can tell the task is done: the observable result, record, approval or document that proves it, and the deadline only when the chunk states one. Every number in it (days, hours, amounts, percentages) must appear in the cited chunk. A task without completion criteria is rejected.

$hr_instructions
$document
