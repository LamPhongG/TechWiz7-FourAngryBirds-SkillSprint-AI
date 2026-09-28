"""Completion rules of a learning path (server copy of frontend `utils/progress.js`; change both together).

A module is complete when every lesson is read, every task is done and the quiz is passed (70 percent);
the path is complete when every module is.
"""
import math
from dataclasses import dataclass

PASS_RATIO = 0.7


@dataclass
class PathProgress:
    done: int
    total: int
    percent: int
    complete: bool


def score_quiz(questions: list[dict], answers: dict[str, int]) -> tuple[int, int, bool]:
    """(correct answers, questions, passed)."""
    correct = sum(1 for q in questions if answers.get(q["id"]) == q["answer"])
    total = len(questions)
    return correct, total, total > 0 and correct / total >= PASS_RATIO


def module_complete(module: dict, lessons_read: set[str], tasks_done: set[str], best_ratio: float | None) -> bool:
    quiz_passed = not module["quiz"] or (best_ratio is not None and best_ratio >= PASS_RATIO)
    return (all(lesson["id"] in lessons_read for lesson in module["lessons"])
            and all(task["id"] in tasks_done for task in module["tasks"])
            and quiz_passed)


def path_progress(stages: list[dict], lessons_read: list[str], tasks_done: list[str],
                  best_ratio_by_module: dict[str, float]) -> PathProgress:
    modules = [m for stage in stages for m in stage["modules"]]
    read, done_tasks = set(lessons_read), set(tasks_done)
    done = sum(1 for m in modules if module_complete(m, read, done_tasks, best_ratio_by_module.get(m["id"])))
    total = len(modules)
    # Math.round in JavaScript rounds .5 up; Python's round() would round it to even.
    percent = math.floor(done / total * 100 + 0.5) if total else 0
    return PathProgress(done, total, percent, total > 0 and done == total)
