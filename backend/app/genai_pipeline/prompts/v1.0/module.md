Build one learning module from the document below.

Learner: $role_name, $department department. Level: $level.
Purpose: $purpose_text

Lessons
- One lesson per section of the document, in document order. Merge sections that are only one or two sentences long into their neighbour. At most $max_lessons lessons.
- `content` explains what the learner must know or do, why it matters in their role, and any numbers, deadlines or responsibilities the section states. Use short paragraphs; start list items with "- ".
- `chunk_ids` lists every chunk the lesson draws on.
- `exact_quote` is the single most important sentence of the lesson.

Tasks
- Exactly $task_count tasks (fewer only if the document has fewer obligations).
- Each task is a concrete action the learner should perform at work, based on a sentence that states an obligation (must, should, required, never, always, ensure…).
- `exact_quote` is that obligation sentence.

$hr_instructions
$document
