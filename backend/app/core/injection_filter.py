"""Prompt-injection screening for document chunks (Rules section 5).

Same rules and flag shape as frontend `utils/injectionScan.js`, so a flag raised in the browser and
one raised here mean the same thing. Flagged chunks are excluded before any text reaches Gemini.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InjectionRule:
    id: str
    severity: str
    pattern: re.Pattern


INJECTION_RULES = [
    InjectionRule("ignore_instructions", "high", re.compile(
        r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|preceding|system)\s+(instructions?|prompts?|rules?|directions?)",
        re.IGNORECASE)),
    InjectionRule("system_override", "high", re.compile(r"\bsystem\s+(override|prompt\s+override|bypass)\b", re.IGNORECASE)),
    InjectionRule("dan_mode", "high", re.compile(
        r"\b(DAN\s+mode|do\s+anything\s+now|developer\s+mode\s+enabled|jailbreak)\b", re.IGNORECASE)),
    InjectionRule("role_hijack", "medium", re.compile(r"\byou\s+are\s+now\s+(a|an|in|the)\b", re.IGNORECASE)),
    InjectionRule("reveal_prompt", "medium", re.compile(
        r"\b(reveal|print|show|output|repeat)\s+(your|the)\s+(system\s+prompt|hidden\s+instructions?|initial\s+instructions?)",
        re.IGNORECASE)),
    InjectionRule("output_manipulation", "medium", re.compile(
        r"\b(mark|classify|label|report)\s+(this|all|every)\s+(\w+\s+){0,3}as\s+(verified|approved|compliant)\b",
        re.IGNORECASE)),
    InjectionRule("ignore_instructions_vi", "high", re.compile(
        r"(bỏ\s+qua|phớt\s+lờ|quên|không\s+tuân\s+theo)\s+(mọi|tất\s+cả|các|những)?\s*(chỉ\s+dẫn|hướng\s+dẫn|lệnh|quy\s+tắc|yêu\s+cầu)\s+(trước|trước\s+đó|ở\s+trên|hệ\s+thống)",
        re.IGNORECASE)),
    InjectionRule("system_override_vi", "high", re.compile(
        r"(ghi\s+đè|vượt\s+qua)\s+(hệ\s+thống|chỉ\s+dẫn\s+hệ\s+thống|system\s+prompt)", re.IGNORECASE)),
    InjectionRule("role_hijack_vi", "medium", re.compile(
        r"(từ\s+bây\s+giờ|kể\s+từ\s+giờ)\s+bạn\s+(là|sẽ\s+đóng\s+vai)", re.IGNORECASE)),
]

_EXCERPT_RADIUS = 80


def scan_chunks(chunks: list[dict]) -> list[dict]:
    """Return one flag per match: {chunk_id, page, rule_id, severity, match, excerpt}."""
    flags = []
    for chunk in chunks:
        text = chunk.get("content") or ""
        for rule in INJECTION_RULES:
            for m in rule.pattern.finditer(text):
                start = max(0, m.start() - _EXCERPT_RADIUS)
                end = min(len(text), m.end() + _EXCERPT_RADIUS)
                excerpt = ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")
                flags.append({
                    "chunk_id": chunk["chunk_id"],
                    "page": chunk.get("page"),
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "match": m.group(0),
                    "excerpt": excerpt,
                })
    return flags
