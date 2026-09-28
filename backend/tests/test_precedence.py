"""Policy Precedence (SRS Step 34): higher-tier / newer version documents take precedence.

Pure function, tested with mock objects (SimpleNamespace) — no DB needed.
"""
from types import SimpleNamespace

from app.rule_pipeline.precedence import precedence_tier, resolve_precedence, sort_by_precedence


def _doc(category: str, version: str = "1.0") -> SimpleNamespace:
    return SimpleNamespace(category=category, version=version)


def test_precedence_tier_ranks_company_wide_policy_above_department_sop_above_faq():
    assert precedence_tier(_doc("Handbook")) < precedence_tier(_doc("SOP"))
    assert precedence_tier(_doc("SOP")) < precedence_tier(_doc("FAQ"))


def test_precedence_tier_unknown_category_ranks_lowest():
    known_tiers = {precedence_tier(_doc(c)) for c in ("Handbook", "SOP", "FAQ")}
    assert precedence_tier(_doc("Test Case")) > max(known_tiers)


def test_resolve_precedence_higher_tier_wins_regardless_of_version():
    policy, sop = _doc("Policy", version="1.0"), _doc("SOP", version="9.0")

    assert resolve_precedence(policy, sop) is policy
    assert resolve_precedence(sop, policy) is policy


def test_resolve_precedence_same_tier_newer_version_wins():
    old, new = _doc("SOP", version="1.0"), _doc("SOP", version="2.0")

    assert resolve_precedence(old, new) is new
    assert resolve_precedence(new, old) is new


def test_sort_by_precedence_orders_tier_then_version():
    faq = _doc("FAQ", version="1.0")
    sop_old = _doc("SOP", version="1.0")
    sop_new = _doc("SOP", version="2.0")
    policy = _doc("Policy", version="1.0")

    ordered = sort_by_precedence([faq, sop_old, policy, sop_new])

    assert ordered == [policy, sop_new, sop_old, faq]
