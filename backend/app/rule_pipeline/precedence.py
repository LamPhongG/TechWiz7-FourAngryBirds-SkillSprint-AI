"""Policy precedence resolution.

When documents relate to the same requirement but differ in precedence
tier or version, this module determines which document has higher authority.
"""
from functools import cmp_to_key

from app.ingestion.validation import compare_versions
from app.models import Document

# Tier 1 (highest): Company-wide policies and compliance. Tier 2: Department SOPs and process manuals.
# Tier 3: FAQs (informational guidance). Unknown categories default to the lowest tier.
PRECEDENCE_TIER = {
    "Handbook": 1,
    "Policy": 1,
    "Compliance": 1,
    "SOP": 2,
    "Process Manual": 2,
    "Role Description": 2,
    "FAQ": 3,
}
_LOWEST_TIER = max(PRECEDENCE_TIER.values()) + 1


def precedence_tier(document: Document) -> int:
    return PRECEDENCE_TIER.get(document.category, _LOWEST_TIER)


def resolve_precedence(doc_a: Document, doc_b: Document) -> Document:
    """Document with higher tier (smaller number) wins; ties broken by higher version."""
    tier_a, tier_b = precedence_tier(doc_a), precedence_tier(doc_b)
    if tier_a != tier_b:
        return doc_a if tier_a < tier_b else doc_b
    return doc_a if compare_versions(doc_a.version, doc_b.version) >= 0 else doc_b


def _compare(doc_a: Document, doc_b: Document) -> int:
    """>0 if doc_a has lower precedence than doc_b (used for sorted(): higher precedence first)."""
    tier_a, tier_b = precedence_tier(doc_a), precedence_tier(doc_b)
    if tier_a != tier_b:
        return tier_a - tier_b
    return -compare_versions(doc_a.version, doc_b.version)


def sort_by_precedence(documents: list[Document]) -> list[Document]:
    """Sort by precedence: higher tier first, ties broken by newer version."""
    return sorted(documents, key=cmp_to_key(_compare))

