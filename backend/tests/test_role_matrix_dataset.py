"""The team's Role Requirement Matrix (role_matrix/role_matrix.csv) meets the dataset minimums and every requirement
traces to a real section of the document version it cites.

Only DOC-11..20 are traced here: their Markdown sources live in sample_documents/source/. DOC-01..10 are checked the
same way once their sources are merged into this folder.
"""
import csv
import re
from datetime import date
from pathlib import Path

import pytest

from app.db.seed import ROLE_MATRIX_CSV
from app.services.document_catalog import CATALOG
from app.services.role_matrix import import_csv, normalize_role

SOURCES = Path(__file__).resolve().parents[2] / "sample_documents" / "source"
TODAY = date(2026, 9, 26)


def matrix_rows() -> list[dict]:
    with ROLE_MATRIX_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def requirement_text(row: dict) -> str:
    return row["Process_Requirement"] if row["Process_Requirement"] != "—" else row["Policy_Requirement"]


def source_versions() -> dict[str, list[dict]]:
    """Document code → every version found in the sources, with its effective date and section numbers."""
    versions: dict[str, list[dict]] = {}
    for path in SOURCES.glob("DOC-*.md"):
        text = path.read_text(encoding="utf-8")
        meta = dict(line.split(": ", 1) for line in re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)[1].splitlines())
        sections = set(re.findall(r"^#{2,3} (\d+(?:\.\d+)*)\.? ", text, flags=re.M))
        versions.setdefault(meta["document_id"], []).append({
            "version": meta["version"], "effective": date.fromisoformat(meta["effective_date"]), "sections": sections,
        })
    return versions


def test_matrix_meets_the_dataset_minimums():
    rows = matrix_rows()
    mandatory = [r for r in rows if r["Mandatory_Optional"] == "Mandatory"]
    role_specific = {requirement_text(r) for r in rows if r["Scope"] == "Role-specific"}

    assert len({requirement_text(r) for r in rows}) >= 150
    assert len(mandatory) >= 50
    assert len(role_specific) >= 30
    assert len({normalize_role(r["Role"]) for r in rows}) == 10
    assert not [r["Requirement_ID"] for r in rows if "PENDING" in r["Source_Document"] or "[COVERAGE GAP]" in
                requirement_text(r)]
    assert len({r["Requirement_ID"] for r in rows}) == len(rows)


def test_matrix_imports_without_row_errors(db):
    report = import_csv(db, ROLE_MATRIX_CSV.read_text(encoding="utf-8"))
    db.rollback()

    assert report.errors == []
    assert report.created + report.updated == len(matrix_rows())


def test_matrix_never_cites_test_documents():
    test_docs = {code for code, entry in CATALOG.items() if entry.category == "Test Case"} | {"DOC-19"}

    assert not [r["Requirement_ID"] for r in matrix_rows() if r["Source_Document"] in test_docs]


@pytest.mark.parametrize("row", [r for r in matrix_rows() if r["Source_Document"] in source_versions()],
                         ids=lambda r: r["Requirement_ID"])
def test_requirement_cites_a_real_section_of_the_version_in_force(row):
    versions = source_versions()[row["Source_Document"]]
    in_force = max((v for v in versions if v["effective"] <= TODAY),
                   key=lambda v: [int(p) for p in v["version"].split(".")])
    cited = next((v for v in versions if v["version"] == row["Source_Version"]), None)

    assert cited is not None, f"{row['Source_Document']} v{row['Source_Version']} has no source"
    assert row["Source_Version"] == in_force["version"]
    assert row["Source_Section"] in cited["sections"]
