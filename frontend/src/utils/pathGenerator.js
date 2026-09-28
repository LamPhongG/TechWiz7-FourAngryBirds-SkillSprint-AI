// Generate draft path from document structure in offline/draft mode (engine = "local-draft").
// Content is faithful to source documents: lessons are verbatim sections, quizzes and tasks are
// constructed from actual sentences, and each item links back via source_reference to the original chunk.
// When backend is active, Pipeline 1 (Gemini) produces this identical structure.
import { docTier, stageTemplate } from "../data/company";

const QUIZ_PER_MODULE = { Beginner: 3, Intermediate: 4, Advanced: 5 };
const TASKS_PER_MODULE = { Beginner: 1, Intermediate: 2, Advanced: 3 };
const LESSON_MAX_CHARS = 2500;
const DAY30_MAX_MODULES = 3;

// Sentences indicating obligations/rules — used for hands-on tasks
const OBLIGATION = /\b(must|should|shall|required|need to|ensure|never|always)\b/iu;

// Standalone numbers — used for cloze questions
const NUMBER = /(?<![\w.#/-])(\d{1,4})(?![\w/.-]?\d)(?![\w/-])/u;

export function splitSentences(text) {
  return String(text || "")
    .split(/\n{2,}|\n(?=[-•*]\s)/)
    .flatMap(p => p.replace(/\s+/g, " ").trim().split(/(?<=[.!?])\s+(?=["“(]?[\p{Lu}\d])/u))
    .map(s => s.replace(/^[-•*]\s+/, "").trim())
    .filter(s => s.length >= 25 && s.length <= 260);
}

// Deterministic string hash for stable distractor placement
function stableHash(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

function placeAnswer(correct, distractors, seed) {
  const pos = stableHash(seed) % (distractors.length + 1);
  const options = [...distractors];
  options.splice(pos, 0, correct);
  return { options, answer: pos };
}

function numberDistractors(n) {
  const candidates = [n * 2, n + (n >= 10 ? 5 : 1), n - (n >= 10 ? 5 : 1), Math.round(n / 2), n * 3, n + 2];
  return [...new Set(candidates.filter(x => x > 0 && x !== n))].slice(0, 3).map(String);
}

export function makeClozeQuestion(sentence) {
  // Strip leading list numbers ("1. Use ...")
  const body = sentence.replace(/^\d+[.)]\s+/, "");
  const offset = sentence.length - body.length;
  const m = body.match(NUMBER);
  if (!m) return null;
  const n = Number(m[1]);
  const distractors = numberDistractors(n);
  if (distractors.length < 3) return null;
  const start = offset + m.index;
  const blanked = `${sentence.slice(0, start)}_____${sentence.slice(start + m[1].length)}`;
  return { blanked, correct: m[1], distractors };
}

function groupSections(chunks) {
  const sections = [];
  for (const c of chunks) {
    const last = sections[sections.length - 1];
    if (last && last.section_id === c.section_id) last.chunks.push(c);
    else sections.push({ section_id: c.section_id, heading: c.heading, chunks: [c] });
  }
  return sections;
}

// Tasks generated from policy rules
function completionCriteria(code, section) {
  return {
    completion_criteria: `Carried out the quoted requirement (${code} · ${section}) correctly at least once in real work.`,
    completion_criteriaEn: `Carried out the quoted requirement (${code} · ${section}) correctly at least once in real work.`,
  };
}

function assignStage(purpose, tier, day30Count) {
  if (purpose === "promotion") return tier <= 2 ? "foundation" : tier === 3 ? "deep" : "practice";
  if (tier === 0) return "day1";
  if (tier === 1) return "week1";
  if (tier === 2) return "week2";
  if (tier === 3) return day30Count < DAY30_MAX_MODULES ? "day30" : "day60";
  return "day60";
}

/**
 * @param {object} p
 * @param {string} p.id                 Path ID
 * @param {string} p.level              Beginner | Intermediate | Advanced
 * @param {"onboarding"|"promotion"} p.purpose
 * @param {7|30|90} [p.durationDays]  Onboarding duration in days
 * @param {Array}  p.docs               Active source documents ({ id, code, version, title, titleEn, category, department })
 * @param {object} p.chunksByDocId      Doc ID to chunks mapping
 * @param {object} p.flagsByDocId       Doc ID to injection flags mapping
 * @returns {{stages, excluded_chunks}}
 * @throws {Error} "NO_CONTENT" when no document has extracted content
 */
export function generatePathContent({ id, level, purpose, durationDays, docs, chunksByDocId, flagsByDocId = {} }) {
  const ordered = [...docs].sort((a, b) => docTier(a) - docTier(b) || a.code.localeCompare(b.code));

  const excluded = [];
  const modules = [];
  for (const doc of ordered) {
    const flagged = new Map();
    for (const f of flagsByDocId[doc.id] || []) flagged.set(f.chunk_id, [...(flagged.get(f.chunk_id) || []), f.rule_id]);
    const chunks = (chunksByDocId[doc.id] || []).filter(c => {
      if (!flagged.has(c.chunk_id)) return true;
      excluded.push({ doc: doc.code, doc_id: doc.id, chunk_id: c.chunk_id, rule_ids: flagged.get(c.chunk_id) });
      return false;
    });
    if (chunks.length === 0) continue;

    const mId = `${id}-M${modules.length + 1}`;
    const lessons = groupSections(chunks).map((section, i) => {
      const full = section.chunks.map(c => c.content).join("\n\n");
      const content = full.length > LESSON_MAX_CHARS ? `${full.slice(0, LESSON_MAX_CHARS)}…` : full;
      const sentences = splitSentences(full);
      const first = section.chunks[0];
      return {
        id: `${mId}-L${i + 1}`,
        title: section.heading || "",
        content,
        minutes: Math.max(1, Math.ceil(full.split(/\s+/).length / 180)),
        sentences,
        source_reference: {
          doc_id: doc.id, doc: doc.code, section: section.heading || doc.titleEn || doc.title || section.section_id,
          page: first.page ?? null, chunk_id: first.chunk_id, exact_quote: sentences[0] || full.slice(0, 160).trim(),
        },
      };
    });
    modules.push({ id: mId, doc, tier: docTier(doc), lessons });
  }
  if (modules.length === 0) throw new Error("NO_CONTENT");

  const allSentences = modules.flatMap(m => m.lessons.flatMap(l => l.sentences.map(s => ({ s, lessonId: l.id, moduleId: m.id }))));

  const built = modules.map(m => {
    const quizTarget = QUIZ_PER_MODULE[level] ?? 4;
    const quiz = [];
    const used = new Set();
    const ref = (lesson, sentence) => ({ ...lesson.source_reference, exact_quote: sentence });
    const section = (lesson) => lesson.source_reference.section;

    // Round 1: numeric cloze questions
    for (const lesson of m.lessons) {
      for (const s of lesson.sentences) {
        if (quiz.length >= quizTarget) break;
        const cloze = makeClozeQuestion(s);
        if (!cloze) continue;
        const { options, answer } = placeAnswer(cloze.correct, cloze.distractors, s);
        quiz.push({
          id: `${m.id}-Q${quiz.length + 1}`, kind: "cloze",
          question: `Fill in the blank (${m.doc.code} · ${section(lesson)}): “${cloze.blanked}”`,
          questionEn: `Fill in the blank (${m.doc.code} · ${section(lesson)}): “${cloze.blanked}”`,
          options, answer, source_reference: ref(lesson, s),
        });
        used.add(s);
        break;
      }
    }
    // Round 2: statement verification
    for (const lesson of m.lessons) {
      if (quiz.length >= quizTarget) break;
      const s = lesson.sentences.find(x => !used.has(x));
      if (!s) continue;
      const others = allSentences.filter(x => x.lessonId !== lesson.id && x.s !== s);
      if (others.length < 3) continue;
      const step = Math.max(1, Math.floor(others.length / 3));
      const start = stableHash(s) % others.length;
      const distractors = [0, 1, 2].map(k => others[(start + k * step) % others.length].s);
      if (new Set(distractors).size < 3) continue;
      const { options, answer } = placeAnswer(s, distractors, s);
      quiz.push({
        id: `${m.id}-Q${quiz.length + 1}`, kind: "statement",
        question: `According to ${m.doc.code} · “${section(lesson)}”, which statement is correct?`,
        questionEn: `According to ${m.doc.code} · “${section(lesson)}”, which statement is correct?`,
        options, answer, source_reference: ref(lesson, s),
      });
      used.add(s);
    }

    const tasks = [];
    for (const lesson of m.lessons) {
      for (const s of lesson.sentences) {
        if (tasks.length >= (TASKS_PER_MODULE[level] ?? 2)) break;
        if (OBLIGATION.test(s) && !tasks.some(t => t.title === s)) {
          tasks.push({ id: `${m.id}-T${tasks.length + 1}`, title: s, ...completionCriteria(m.doc.code, section(lesson)), source_reference: ref(lesson, s) });
        }
      }
    }

    return {
      id: m.id,
      kind: "lesson",
      title: m.doc.titleEn || m.doc.title,
      titleEn: m.doc.titleEn || m.doc.title,
      doc_id: m.doc.id,
      doc_code: m.doc.code,
      tier: m.tier,
      lessons: m.lessons.map(({ sentences, ...l }) => l),
      tasks,
      quiz,
    };
  });

  const template = stageTemplate(purpose, durationDays);
  const stageMap = Object.fromEntries(template.map(k => [k, []]));
  let day30 = 0;
  for (const m of built) {
    const natural = assignStage(purpose, m.tier, day30);
    if (natural === "day30") day30++;
    stageMap[template.includes(natural) ? natural : template[template.length - 1]].push(m);
  }

  // Final Assessment: aggregate first question from each module
  const finalQuiz = built.filter(m => m.quiz.length).map((m, i) => ({ ...m.quiz[0], id: `${id}-FA-Q${i + 1}` }));
  const lastKey = template[template.length - 1];
  if (finalQuiz.length) {
    stageMap[lastKey].push({
      id: `${id}-FA`, kind: "assessment", title: "Final Assessment", titleEn: "Final Assessment",
      doc_id: null, doc_code: null, tier: 5, lessons: [], tasks: [], quiz: finalQuiz,
    });
  }

  const stages = template.filter(k => stageMap[k].length).map(k => ({ key: k, modules: stageMap[k] }));
  return { stages, excluded_chunks: excluded };
}

export function allModules(path) {
  return (path?.stages || []).flatMap(s => s.modules);
}

