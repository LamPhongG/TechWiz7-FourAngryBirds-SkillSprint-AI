"""Prompt registry: one folder per version under prompts/, one file per prompt (Rules section 4).

Templates use `$name` placeholders (string.Template) so JSON or braces in a prompt need no escaping.
To change a prompt, copy the folder to a new version and point PROMPT_VERSION at it; paths keep the
version they were generated with, so old output stays explainable.
"""
from functools import cache
from pathlib import Path
from string import Template

PROMPT_DIR = Path(__file__).parent / "prompts"
PROMPT_NAMES = ("system", "module", "quiz")


@cache
def load(version: str, name: str) -> Template:
    if name not in PROMPT_NAMES:
        raise ValueError(f"Unknown prompt: {name}")
    path = PROMPT_DIR / version / f"{name}.md"
    if not path.is_file():
        raise ValueError(f"Prompt version {version} has no {name}.md")
    return Template(path.read_text(encoding="utf-8"))


def available_versions() -> list[str]:
    return sorted(p.name for p in PROMPT_DIR.iterdir() if p.is_dir() and all((p / f"{n}.md").is_file() for n in PROMPT_NAMES))
