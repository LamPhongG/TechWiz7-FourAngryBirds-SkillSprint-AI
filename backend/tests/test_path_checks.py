"""Duplicate Detection (SRS Step 35): semantic duplicate quiz questions / tasks across modules.

Pure function (check_duplicates), tested directly with mock stages — no DB/API needed.
"""
from app.services.path_checks import check_duplicates


def _stages(*modules: dict) -> list[dict]:
    return [{"key": "day1", "modules": list(modules)}]


def _module(module_id: str, quiz: list[dict] | None = None, tasks: list[dict] | None = None) -> dict:
    return {"id": module_id, "lessons": [], "tasks": tasks or [], "quiz": quiz or []}


def test_check_duplicates_flags_near_identical_quiz_questions_across_modules():
    stages = _stages(
        _module("M1", quiz=[{"id": "Q1", "question": "What is the maximum annual leave for new hires?"}]),
        _module("M2", quiz=[{"id": "Q2", "question": "What is the maximum annual leave for new hires ?"}]),
    )

    duplicates = check_duplicates(stages)

    assert len(duplicates) == 1
    assert duplicates[0]["kind"] == "quiz"
    assert {duplicates[0]["item_id_a"], duplicates[0]["item_id_b"]} == {"Q1", "Q2"}
    assert duplicates[0]["similarity"] >= 0.85


def test_check_duplicates_ignores_genuinely_different_questions():
    stages = _stages(
        _module("M1", quiz=[{"id": "Q1", "question": "What is the maximum annual leave for new hires?"}]),
        _module("M2", quiz=[{"id": "Q2", "question": "Who approves an expense claim above 200000 VND?"}]),
    )

    assert check_duplicates(stages) == []


def test_check_duplicates_flags_near_identical_tasks_across_stages():
    stage1 = {"key": "day1", "modules": [_module("M1", tasks=[{"id": "T1", "title": "Install the corporate VPN client"}])]}
    stage2 = {"key": "week1", "modules": [_module("M2", tasks=[{"id": "T2", "title": "Install the corporate VPN client."}])]}

    duplicates = check_duplicates([stage1, stage2])

    assert len(duplicates) == 1
    assert duplicates[0]["kind"] == "task"


def test_check_duplicates_does_not_compare_quiz_against_task():
    stages = _stages(_module(
        "M1",
        quiz=[{"id": "Q1", "question": "Install the corporate VPN client"}],
        tasks=[{"id": "T1", "title": "Install the corporate VPN client"}],
    ))

    assert check_duplicates(stages) == []


def test_check_duplicates_skips_blank_items():
    stages = _stages(
        _module("M1", quiz=[{"id": "Q1", "question": ""}]),
        _module("M2", quiz=[{"id": "Q2", "question": "   "}]),
    )

    assert check_duplicates(stages) == []
