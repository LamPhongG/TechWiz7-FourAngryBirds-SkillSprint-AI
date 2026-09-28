"""The policy versions shipped in sample_documents/ go through the real upload pipeline and form the version chains
HR relies on: the newest version in force is active, older ones are obsolete, a future one is upcoming.
"""
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import Document
from app.services.documents import compute_lifecycle
from tests.conftest import login
from tests.factories import upload

SAMPLES = Path(__file__).resolve().parents[2] / "sample_documents"
VERSIONED = ("DOC-11", "DOC-12", "DOC-13", "DOC-14", "DOC-15", "DOC-16", "DOC-20")


def front_matter(pdf: Path) -> dict:
    """Metadata of the Markdown source the PDF was built from."""
    stem = pdf.stem.removesuffix("_v1.0")
    text = (SAMPLES / "source" / f"{stem}.md").read_text(encoding="utf-8")
    block = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S).group(1)
    return dict(line.split(": ", 1) for line in block.splitlines())


@pytest.fixture(scope="module")
def client_module():
    # Module scope: the 20 PDFs are uploaded once and shared by every test below.
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def hr_headers_module(client_module):
    return login(client_module, "hr@fourangrybirds.vn")


@pytest.fixture(scope="module")
def reviewer_headers_module(client_module):
    return login(client_module, "reviewer@fourangrybirds.vn")


@pytest.fixture(scope="module")
def uploaded(client_module, hr_headers_module):
    docs = {}
    for pdf in sorted(p for code in VERSIONED for p in SAMPLES.rglob(f"{code}_*.pdf")):
        meta = front_matter(pdf)
        res = upload(client_module, hr_headers_module, pdf.read_bytes(), pdf.name, code=meta["document_id"],
                     title_en=meta["title_en"], category=meta["category"], department_code=meta["department"],
                     version=meta["version"], effective_date=meta["effective_date"])
        assert res.status_code == 201, (pdf.name, res.text)
        docs[(meta["document_id"], meta["version"])] = res.json()
    return docs


def test_ten_new_versions_are_processed_like_the_originals(uploaded):
    new_versions = [key for key in uploaded if key[1] != "1.0"]

    assert len(new_versions) == 10
    for doc in uploaded.values():
        assert doc["processing_status"] == "ready"
        assert 3 <= doc["page_count"] <= 5
    # Each version of a document shares the family, so the repository treats them as one policy.
    assert len({uploaded[(c, "1.0")]["family"] for c in VERSIONED}) == len(VERSIONED)
    assert {uploaded[k]["family"] for k in uploaded if k[0] == "DOC-11"} == {"sop-employee-onboarding"}


def test_lifecycle_of_each_chain_on_a_fixed_day(uploaded, db):
    ids = {doc["id"]: key for key, doc in uploaded.items()}
    rows = db.scalars(select(Document).where(Document.id.in_(ids))).all()

    lifecycle = {ids[doc_id]: (status, ids.get(newer)) for doc_id, (status, newer)
                 in compute_lifecycle(list(rows), date(2026, 9, 26)).items()}

    assert lifecycle[("DOC-11", "1.0")] == ("obsolete", ("DOC-11", "1.2"))
    assert lifecycle[("DOC-11", "1.1")] == ("obsolete", ("DOC-11", "1.2"))
    assert lifecycle[("DOC-11", "1.2")] == ("active", None)
    assert lifecycle[("DOC-12", "2.0")] == ("active", None)
    assert lifecycle[("DOC-12", "1.1")] == ("obsolete", ("DOC-12", "2.0"))
    # v1.2 of the exception register is approved but not in force yet, so v1.1 still governs.
    assert lifecycle[("DOC-20", "1.2")] == ("upcoming", None)
    assert lifecycle[("DOC-20", "1.1")] == ("active", None)
    assert lifecycle[("DOC-20", "1.0")] == ("obsolete", ("DOC-20", "1.1"))

    on_new_year = compute_lifecycle(list(rows), date(2027, 1, 1))
    assert on_new_year[uploaded[("DOC-20", "1.2")]["id"]] == ("active", None)
    assert on_new_year[uploaded[("DOC-20", "1.1")]["id"]][0] == "obsolete"


def test_changed_clause_is_cited_from_the_right_version(client_module, reviewer_headers_module, uploaded):
    def chunk_with(key, needle):
        res = client_module.get(f"/api/documents/{uploaded[key]['id']}/chunks", headers=reviewer_headers_module)
        return [c for c in res.json()["chunks"] if needle in " ".join(c["content"].split())]

    kickoff_old = chunk_with(("DOC-12", "1.0"), "kickoff call with the school within 5 business days")
    kickoff_new = chunk_with(("DOC-12", "1.1"), "kickoff call with the school within 3 business days")
    offboarding = chunk_with(("DOC-12", "2.0"), "within 30 calendar days of the contract end date")

    assert kickoff_old and kickoff_new
    assert kickoff_new[0]["heading"] == kickoff_old[0]["heading"] == "6.1 Partner-School Onboarding [MANDATORY]"
    assert offboarding[0]["heading"] == "6.5 Partner-School Offboarding [MANDATORY]"
    history = chunk_with(("DOC-12", "2.0"), "was 50,000,000 VND")
    assert history[0]["heading"] == "10. Revision History"
