"""Gemini client returning validated Pydantic objects (Rules section 4: no raw text from the LLM)."""
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Protocol, TypeVar

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Transient statuses the SDK retries itself with exponential backoff (2s, 4s, …).
_RETRY_STATUSES = [408, 429, 500, 502, 503, 504]
# Finish reasons where the model stopped for policy reasons: retrying the same prompt will not help.
_BLOCKED = {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}
# Errors that mean "this model, not this prompt": the next model in the list may still work.
MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
# A model that ran out of quota is skipped for this long, so the remaining modules of a run fall back at once
# instead of each waiting through the SDK's retries. Free-tier quotas reset per minute or per day.
QUOTA_COOLDOWN_S = 300
_FENCE = re.compile(r"^\s*```(?:json|JSON)?\s*|\s*```\s*$")

# Shared by every client in the process: model name → time until which it is skipped (inf = retired).
_benched: dict[str, float] = {}
_bench_lock = threading.Lock()


class GenerationError(Exception):
    """LLM call failed. `code` ends up in the generation report the Reviewer sees."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass
class LLMResult:
    data: BaseModel
    model: str
    input_tokens: int
    output_tokens: int


class LLMClient(Protocol):
    model: str

    def generate(self, *, system: str, prompt: str, schema: type[T], temperature: float) -> LLMResult: ...


def json_text(text: str | None) -> str:
    """The JSON object inside a reply. Models sometimes wrap it in a ```json fence or add a sentence around it
    despite the JSON response type; strip that instead of spending a retry."""
    text = _FENCE.sub("", (text or "").strip())
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if 0 <= start < end else text


def _bench(model: str, seconds: float) -> None:
    with _bench_lock:
        _benched[model] = time.monotonic() + seconds


def _usable(model: str) -> bool:
    with _bench_lock:
        return _benched.get(model, 0) <= time.monotonic()


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout_s: int, fallback_models: list[str] | None = None):
        self.models = list(dict.fromkeys([model, *(fallback_models or [])]))
        self.model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_s * 1000,
                retry_options=types.HttpRetryOptions(attempts=3, initial_delay=2.0, exp_base=2.0,
                                                     http_status_codes=_RETRY_STATUSES),
            ),
        )

    def generate(self, *, system: str, prompt: str, schema: type[T], temperature: float) -> LLMResult:
        """Call the first usable model; move to the next one when a model is retired or out of quota.

        Raises:
            GenerationError: the last model's error, or QUOTA_EXCEEDED / MODEL_UNAVAILABLE when every model is
                benched (then no request is sent at all).
        """
        last: GenerationError | None = None
        for model in self.models:
            if not _usable(model):
                continue
            try:
                return self._generate_with(model, system=system, prompt=prompt, schema=schema, temperature=temperature)
            except GenerationError as exc:
                if exc.code == MODEL_UNAVAILABLE:
                    _bench(model, float("inf"))
                elif exc.code == QUOTA_EXCEEDED:
                    _bench(model, QUOTA_COOLDOWN_S)
                else:
                    raise
                log.warning("Gemini model %s unusable (%s); trying the next one", model, exc.code)
                last = exc
        raise last or GenerationError(QUOTA_EXCEEDED, f"no usable model among {', '.join(self.models)}")

    def _generate_with(self, model: str, *, system: str, prompt: str, schema: type[T], temperature: float) -> LLMResult:
        """Call one model with `schema` as the structured-output contract.

        One extra attempt is made when the model returns JSON that does not validate; transport errors
        are already retried by the SDK.

        Raises:
            GenerationError: QUOTA_EXCEEDED (429), MODEL_UNAVAILABLE (404), UPSTREAM_REJECTED (other 4xx),
                UPSTREAM_UNAVAILABLE (5xx / timeout after retries), BLOCKED_<REASON>, INVALID_OUTPUT.
        """
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
            # No tools are passed; disabling AFC stops the SDK from warning on every call.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        last_error = ""
        for _attempt in range(2):
            try:
                response = self._client.models.generate_content(model=model, contents=prompt, config=config)
            except genai_errors.ClientError as exc:
                code = {429: QUOTA_EXCEEDED, 404: MODEL_UNAVAILABLE}.get(exc.code, "UPSTREAM_REJECTED")
                raise GenerationError(code, f"{model}: {exc.code} {exc.message}") from None
            except genai_errors.ServerError as exc:
                raise GenerationError("UPSTREAM_UNAVAILABLE", f"{exc.code} {exc.message}") from None
            except httpx.TimeoutException:
                raise GenerationError("UPSTREAM_UNAVAILABLE", "timeout") from None

            blocked = _blocked_reason(response)
            if blocked:
                raise GenerationError(f"BLOCKED_{blocked}")
            try:
                data = (response.parsed if isinstance(response.parsed, schema)
                        else schema.model_validate_json(json_text(response.text)))
            except ValidationError as exc:
                last_error = str(exc.errors()[:3])
                log.warning("Gemini output failed validation, retrying: %s", last_error)
                continue
            usage = response.usage_metadata
            return LLMResult(
                data=data,
                model=response.model_version or model,
                input_tokens=(usage.prompt_token_count or 0) if usage else 0,
                output_tokens=(usage.candidates_token_count or 0) if usage else 0,
            )
        raise GenerationError("INVALID_OUTPUT", last_error)


def _blocked_reason(response: types.GenerateContentResponse) -> str | None:
    feedback = response.prompt_feedback
    if feedback is not None and feedback.block_reason is not None:
        return str(feedback.block_reason.name)
    for candidate in response.candidates or []:
        reason = candidate.finish_reason.name if candidate.finish_reason else None
        if reason in _BLOCKED:
            return reason
    return None


def get_llm_client() -> LLMClient | None:
    """Gemini when GEMINI_API_KEY is set; None means the rule-based draft generator is used."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    fallbacks = [m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()]
    return GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout_s, fallbacks)
