"""The Gemini client's resilience without the network: fenced JSON, retired models, exhausted quotas."""
from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.genai_pipeline import client as client_module
from app.genai_pipeline.client import GeminiClient, GenerationError, json_text


class Answer(BaseModel):
    answer: str


def _reply(text: str, model: str):
    return SimpleNamespace(prompt_feedback=None, candidates=[], parsed=None, text=text, usage_metadata=None,
                           model_version=model)


def _error(code: int, status: str):
    return genai_errors.ClientError(code, {"error": {"code": code, "message": status.lower(), "status": status}})


class FakeModels:
    """Stands in for `genai.Client().models`: per model, either an error to raise or a reply text."""

    def __init__(self, behaviour: dict):
        self.behaviour = behaviour
        self.calls: list[str] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        outcome = self.behaviour[model]
        if isinstance(outcome, Exception):
            raise outcome
        return _reply(outcome, model)


@pytest.fixture(autouse=True)
def fresh_bench():
    client_module._benched.clear()
    yield
    client_module._benched.clear()


def _client(behaviour: dict, models=("primary", "backup")) -> tuple[GeminiClient, FakeModels]:
    llm = GeminiClient("test-key", models[0], timeout_s=5, fallback_models=list(models[1:]))
    fake = FakeModels(behaviour)
    llm._client = SimpleNamespace(models=fake)
    return llm, fake


def _ask(llm):
    return llm.generate(system="s", prompt="p", schema=Answer, temperature=0)


@pytest.mark.parametrize(("raw", "expected"), [
    ('```json\n{"answer": "blue"}\n```', '{"answer": "blue"}'),
    ('Here is the JSON:\n{"answer": {"x": 1}}\nThanks!', '{"answer": {"x": 1}}'),
    ('{"answer": "plain"}', '{"answer": "plain"}'),
])
def test_json_is_taken_out_of_markdown_fences_and_chatter(raw, expected):
    assert json_text(raw) == expected


def test_fenced_reply_is_parsed_without_spending_a_retry():
    llm, fake = _client({"primary": '```json\n{"answer": "blue"}\n```'})

    result = _ask(llm)

    assert result.data.answer == "blue"
    assert fake.calls == ["primary"]


def test_a_retired_model_is_skipped_for_good():
    llm, fake = _client({"primary": _error(404, "NOT_FOUND"), "backup": '{"answer": "ok"}'})

    assert _ask(llm).model == "backup"
    assert _ask(llm).model == "backup"
    assert fake.calls == ["primary", "backup", "backup"]  # the retired model is not asked again


def test_an_exhausted_model_hands_over_to_the_next_one():
    llm, fake = _client({"primary": _error(429, "RESOURCE_EXHAUSTED"), "backup": '{"answer": "ok"}'})

    result = _ask(llm)

    assert result.model == "backup"
    assert fake.calls == ["primary", "backup"]


def test_when_every_model_is_out_of_quota_later_calls_fail_without_a_request():
    llm, fake = _client({"primary": _error(429, "RESOURCE_EXHAUSTED"), "backup": _error(429, "RESOURCE_EXHAUSTED")})

    with pytest.raises(GenerationError) as first:
        _ask(llm)
    with pytest.raises(GenerationError) as second:
        _ask(llm)

    assert first.value.code == second.value.code == "QUOTA_EXCEEDED"
    assert fake.calls == ["primary", "backup"]  # the second call went nowhere: the rest of the run falls back at once


def test_other_client_errors_are_not_retried_on_another_model():
    llm, fake = _client({"primary": _error(400, "INVALID_ARGUMENT"), "backup": '{"answer": "ok"}'})

    with pytest.raises(GenerationError) as exc:
        _ask(llm)

    assert exc.value.code == "UPSTREAM_REJECTED"
    assert fake.calls == ["primary"]  # a bad request stays bad on any model
