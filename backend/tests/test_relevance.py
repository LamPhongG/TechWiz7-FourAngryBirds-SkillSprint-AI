"""Role filter: the model only sees the sections the target role needs."""
import pytest

from app.genai_pipeline.generator import generate_content
from app.genai_pipeline.relevance import belongs_to_others, filter_for_role
from app.genai_pipeline.types import RoleScope, SourceDoc
from app.ingestion.chunker import chunk_blocks, outline
from app.ingestion.extract import Block
from tests.test_generation import _req

CS = RoleScope(role="Customer Support Executive", department="Customer Support",
               other_roles=["Sales Executive", "Team Leader / Tech Lead", "Branch Manager", "Data Analyst"],
               other_departments=["Sales", "Engineering", "Finance", "Data"])

JD_TEXT = ("1. Purpose\nThis document describes the roles of the Company.\n"
           "3. Sales Executive\n3.1 Mission\nSales Executives must log every deal in the CRM within 24 hours.\n"
           "3.2 Decision Limits [ROLE-SPECIFIC: Sales Executive]\nDeals above the limit need approval.\n"
           "5. Customer Support Executive\n5.1 Mission\nAgents must acknowledge every issue within 2 business hours.\n"
           "6. Shared Rules\nCustomer data must never be copied to personal devices.")


def _jd(code="DOC-14") -> SourceDoc:
    blocks = [Block(page=1, text=JD_TEXT)]
    return SourceDoc(id=f"id-{code}", code=code, version="1.0", title=code, title_en=code, category="Role Description",
                     department="Engineering", chunks=chunk_blocks(code, blocks), outline=outline(blocks))


@pytest.mark.parametrize(("heading", "expected"), [
    ("3. Sales Executive", True),
    ("5. Customer Support Executive", False),
    ("4. Team Leader/Tech Lead", True),                           # spacing around "/" does not matter
    ("3. Branch Manager Authority [ROLE-SPECIFIC: Branch Manager]", True),
    ("6.2 Week 1 – Role-Critical Training [ROLE-SPECIFIC]", False),  # tagged, but for no one in particular
    ("5. Finance – Month-End Leave Blackout [EXCEPTION]", True),
    ("3. Customer Support – Extended Service Hours [EXCEPTION]", False),
    ("9. Đà Nẵng Office – Purchase Approval [EXCEPTION]", False),  # a site, not a department
    ("12. Records & Data Retention", False),                     # "Data" in a heading is not the Data department
])
def test_who_a_heading_belongs_to(heading, expected):
    assert belongs_to_others(heading, CS) is expected


def test_subsections_follow_their_parent_heading():
    """"3.1 Mission" has no role name; its parent "3. Sales Executive", which never becomes a chunk, decides."""
    kept, dropped = filter_for_role(_jd(), CS, cited_sections=["5.1"])

    assert [c["heading"] for c in kept.chunks] == ["1. Purpose", "5.1 Mission", "6. Shared Rules"]
    assert dropped == [{"doc": "DOC-14", "section": "3", "heading": "3. Sales Executive", "chunks": 2}]


def test_a_section_the_roles_matrix_cites_is_always_kept():
    kept, _ = filter_for_role(_jd(), CS, cited_sections=["3.1"])

    assert "3.1 Mission" in [c["heading"] for c in kept.chunks]


def test_a_requirement_on_the_whole_document_keeps_everything():
    doc = _jd()
    kept, dropped = filter_for_role(doc, CS, cited_sections=[None])

    assert kept.chunks == doc.chunks and dropped == []


def test_generation_sees_only_the_roles_sections_and_reports_the_rest():
    result = generate_content(_req(scope=CS), [_jd()], llm=None)

    lessons = [lesson["title"] for s in result.stages for m in s["modules"] for lesson in m["lessons"]]
    assert not any(title.startswith("3.") for title in lessons)
    assert result.report["off_role_sections"] == [
        {"doc": "DOC-14", "section": "3", "heading": "3. Sales Executive", "chunks": 2}]


def test_without_a_scope_nothing_is_filtered():
    result = generate_content(_req(), [_jd()], llm=None)

    assert "off_role_sections" not in result.report
    assert any(lesson["title"] == "3.1 Mission" for s in result.stages for m in s["modules"] for lesson in m["lessons"])
