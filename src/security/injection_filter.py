import re

INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+(rules?|directives?|prompts?)", re.IGNORECASE),
    re.compile(r"\bDAN\b|\bDAN\s+mode\b|\bjailbreak\b", re.IGNORECASE),
    re.compile(r"developer\s+mode\s+enabled?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+an?\s+(unfiltered|unrestricted)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|secret\s+key|api\s+key)", re.IGNORECASE),
]


def scan_for_prompt_injection(text: str) -> list[str]:
    """Scan text for common prompt injection attack patterns."""
    matched = []
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            matched.append(match.group(0).strip())
    return matched
