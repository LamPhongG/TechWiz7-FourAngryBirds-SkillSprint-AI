import json
import os
import time
from dotenv import load_dotenv
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai

from google.api_core.exceptions import (
    DeadlineExceeded,
    GoogleAPIError,
    InternalServerError,
    ResourceExhausted,
    ServiceUnavailable,
)

load_dotenv()


class GeminiAPIError(Exception):
    pass


def configure_client() -> str:
    """Setup Gemini API key from environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiAPIError("GEMINI_API_KEY is not set in environment or .env file.")
    genai.configure(api_key=api_key)
    return api_key


def generate_content_with_retry(
    prompt: str,
    response_schema=None,
    model_name: str | None = None,
    max_retries: int = 3,
    base_delay: float = 3.0,
) -> str:
    """Send prompt to Gemini with retry logic for rate limits or network issues."""
    configure_client()

    selected_model = model_name or os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    config = {
        "temperature": 0.2,
        "response_mime_type": "application/json",
    }

    full_prompt = prompt
    if response_schema is not None and hasattr(response_schema, "model_json_schema"):
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        full_prompt = (
            f"{prompt}\n\n"
            "Return valid JSON matching this schema:\n"
            f"{schema_json}"
        )

    model = genai.GenerativeModel(selected_model, generation_config=config)

    transient_exceptions = (
        DeadlineExceeded,
        ResourceExhausted,
        ServiceUnavailable,
        InternalServerError,
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            response = model.generate_content(full_prompt)
            if not response.text:
                raise GeminiAPIError(f"Model '{selected_model}' returned empty response.")
            return response.text.strip()
        except ResourceExhausted as e:
            last_error = e
            if attempt < max_retries - 1:
                # wait for rate limit cooldown
                delay = max(12.0, base_delay * (2 ** attempt))
                time.sleep(delay)
            else:
                break
        except transient_exceptions as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                break
        except GoogleAPIError as e:
            raise GeminiAPIError(f"Gemini API request failed: {e}") from e

    raise GeminiAPIError(
        f"Gemini API request failed after {max_retries} attempts: {last_error}"
    ) from last_error
