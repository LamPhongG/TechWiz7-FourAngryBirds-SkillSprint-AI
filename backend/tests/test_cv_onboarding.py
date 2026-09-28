"""Employee accounts created from a CV: profile read in Python, generated password emailed, password change."""
import uuid

import pytest
from sqlalchemy import select

from app.models import User
from app.services import enrollments
from app.services.cv_parser import level_from_years, parse_text
from tests.conftest import login
from tests.factories import make_docx, make_pdf


@pytest.fixture
def admin_headers(client):
    return login(client, "admin@fourangrybirds.vn")


def _email() -> str:
    return f"cv.{uuid.uuid4().hex[:8]}@example.com"


VI_CV = """NGUYỄN VĂN AN
Sơ yếu lý lịch
Email: An.Nguyen@Gmail.com | SĐT: 0901234567
Địa chỉ: 12 Lê Lợi, Quận 1
Ngày sinh: 01/01/1998
Kinh nghiệm làm việc
Công ty ABC (2021-2024): chăm sóc khách hàng, 3 năm kinh nghiệm hỗ trợ khách hàng.
Kỹ năng
Giao tiếp, Xử lý khiếu nại; CRM Salesforce
Học vấn
Đại học Kinh tế"""


def test_parse_text_reads_profile_fields_and_skips_personal_data():
    draft = parse_text(VI_CV)
    assert draft["name"] == "Nguyễn Văn An"
    assert draft["email"] == "an.nguyen@gmail.com"
    assert draft["years_of_experience"] == 3
    assert draft["experience_level"] == "Intermediate"
    assert draft["competencies"] == ["Giao tiếp", "Xử lý khiếu nại", "CRM Salesforce"]
    assert "Công ty ABC" in draft["previous_experience"]
    assert draft["warnings"] == []
    flat = str(draft)
    for personal in ("0901234567", "Lê Lợi", "01/01/1998", "Đại học"):
        assert personal not in flat


# Text as PyMuPDF extracts a two-column PDF CV: headings with a qualifier, skills as rows of tags under group labels,
# a footer with the name and email after the last section.
TAG_CV = """NGUYỄN LÂM PHONG
Senior Full-Stack Developer
Email: lamphong@example.com
SĐT: (+84) 912 345 678
TÓM TẮT CHUYÊN MÔN
Kỹ sư phần mềm Node.js/Go và React.
KINH NGHIỆM LÀM VIỆC
Senior Full-Stack Developer
03/2023 – Hiện tại
TechCorp Solutions | TP. Hồ Chí Minh
Junior Web Developer
01/2020 – 05/2021
DỰ ÁN TIÊU BIỂU
Omnichannel CRM Platform
HỌC VẤN
Đại học Bách Khoa TP.HCM
KỸ NĂNG CHUYÊN MÔN
Ngôn ngữ lập trình
TypeScript JavaScript Go
Front-end & UI
React Next.js TailwindCSS
Back-end & Cloud
AWS (S3, EC2)
CHỨNG CHỈ
IELTS Academic 7.5
KỸ NĂNG MỀM
• Quản trị dự án Agile/Scrum
• Làm việc nhóm & Mentoring
Nguyễn Lâm Phong — CV Demo Test
lamphong@example.com"""


def test_parse_text_reads_tag_rows_and_qualified_headings():
    draft = parse_text(TAG_CV)
    assert draft["competencies"] == ["TypeScript", "JavaScript", "Go", "React", "Next.js", "TailwindCSS", "AWS (S3, EC2)",
                                     "Quản trị dự án Agile/Scrum", "Làm việc nhóm & Mentoring"]
    # The experience section stops at the next heading (projects), not at the end of the CV.
    assert "TechCorp Solutions" in draft["previous_experience"]
    assert "Omnichannel" not in draft["previous_experience"]
    # No "N năm kinh nghiệm" sentence: the years come from the job dates (2020 to today).
    assert draft["years_of_experience"] >= 6
    assert draft["experience_level"] == "Advanced"
    assert draft["warnings"] == []


def test_parse_text_english_headings_with_colon():
    draft = parse_text("John Smith\njohn@example.com\nWork Experience:\nSupport agent 2022 - 2024\n"
                       "Technical Skills:\nExcel; SQL | Zendesk\nEducation\nBSc")
    assert draft["competencies"] == ["Excel", "SQL", "Zendesk"]
    assert draft["years_of_experience"] == 2
    assert draft["experience_level"] == "Intermediate"


def test_parse_text_lists_what_it_could_not_read():
    draft = parse_text("just some words without structure")
    assert draft["name"] is None and draft["email"] is None
    assert set(draft["warnings"]) == {"cv_warn_no_name", "cv_warn_no_email", "cv_warn_no_experience", "cv_warn_no_skills"}


@pytest.mark.parametrize(("years", "level"), [(None, None), (0, "Beginner"), (1, "Beginner"), (2, "Intermediate"),
                                              (5, "Intermediate"), (6, "Advanced")])
def test_level_from_years(years, level):
    assert level_from_years(years) == level


def test_parse_endpoint_reads_docx_and_pdf(client, admin_headers):
    content = make_docx([("Tran Thi Binh", ["binh.tran@example.com"]),
                         ("Work Experience", ["Sales executive at XYZ, 4 years of experience in retail banking."]),
                         ("Skills", ["Negotiation, Product knowledge, CRM"])])
    res = client.post("/api/users/cv/parse", headers=admin_headers,
                      files={"file": ("cv.docx", content, "application/octet-stream")})
    assert res.status_code == 200, res.text
    draft = res.json()
    assert draft["email"] == "binh.tran@example.com"
    assert draft["experience_level"] == "Intermediate"
    assert "Negotiation" in draft["competencies"]

    pdf = make_pdf(["Name: Le Van Cuong\ncuong.le@example.com\nSkills\nExcel, Reporting"])
    res = client.post("/api/users/cv/parse", headers=admin_headers, files={"file": ("cv.pdf", pdf, "application/pdf")})
    assert res.status_code == 200, res.text
    assert res.json()["name"] == "Le Van Cuong"
    assert res.json()["competencies"] == ["Excel", "Reporting"]


def test_parse_endpoint_rejects_images_and_non_staff(client, admin_headers, employee_headers):
    image = client.post("/api/users/cv/parse", headers=admin_headers, files={"file": ("cv.png", b"\x89PNG....", "image/png")})
    assert image.status_code == 415
    assert image.json()["code"] == "err_file_type"
    fake_pdf = client.post("/api/users/cv/parse", headers=admin_headers, files={"file": ("cv.pdf", b"not a pdf", "application/pdf")})
    assert fake_pdf.json()["code"] == "err_file_corrupt"
    denied = client.post("/api/users/cv/parse", headers=employee_headers, files={"file": ("cv.txt", b"x", "text/plain")})
    assert denied.status_code == 403


def test_onboard_emails_a_generated_password_that_logs_in(client, admin_headers, smtp, db, monkeypatch):  # noqa: F811
    assigned = []
    original = enrollments.assign_onboarding_to
    monkeypatch.setattr(enrollments, "assign_onboarding_to", lambda session, u: assigned.append(u.email) or original(session, u))
    address = _email()
    res = client.post("/api/users/from-cv", headers=admin_headers, json={
        "email": address, "name": "Pham Minh Chau", "job_position_id": "cs-exec",
        "experience_level": "Beginner", "competencies": ["Giao tiếp", " "], "previous_experience": "Intern at ABC",
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email_sent"] is True
    assert body["temporary_password"] is None  # the password is only in the email
    assert body["user"]["user_role"] == "employee"
    assert body["user"]["department_code"] == "Customer Support"
    assert body["user"]["password_is_temporary"] is True
    assert body["user"]["competencies"] == ["Giao tiếp"]

    assert len(smtp.sent) == 1
    message = smtp.sent[0]
    assert message["To"] == address
    text = message.get_body(("plain",)).get_content()
    password = next(line.split(": ", 1)[1] for line in text.splitlines() if line.lower().startswith("temporary password"))
    assert len(password) == 12

    user = db.scalar(select(User).where(User.email == address))
    assert password not in user.password_hash
    # Onboarding paths of the position are assigned right away.
    assert assigned == [address]
    me = client.get("/api/auth/me", headers=login(client, address, password)).json()
    assert me["password_is_temporary"] is True


def test_onboard_without_smtp_returns_the_password_once(client, admin_headers, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "smtp_host", "")
    address = _email()
    res = client.post("/api/users/from-cv", headers=admin_headers,
                      json={"email": address, "name": "No Mail User", "job_position_id": "sales-exec"})
    assert res.status_code == 201
    assert res.json()["email_sent"] is False
    password = res.json()["temporary_password"]
    assert password
    assert client.post("/api/auth/login", json={"email": address, "password": password}).status_code == 200

    again = client.post("/api/users/from-cv", headers=admin_headers,
                        json={"email": address, "name": "No Mail User", "job_position_id": "sales-exec"})
    assert again.status_code == 409
    unknown = client.post("/api/users/from-cv", headers=admin_headers,
                          json={"email": _email(), "name": "Someone", "job_position_id": "no-such-role"})
    assert unknown.status_code == 422


def test_onboard_is_for_admin_and_hr_only(client, reviewer_headers, employee_headers, hr_headers, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "smtp_host", "")
    payload = {"email": _email(), "name": "Some Employee", "job_position_id": "sales-exec"}
    for headers in (reviewer_headers, employee_headers):
        assert client.post("/api/users/from-cv", headers=headers, json=payload).status_code == 403
    # HR onboards employees (the only role this endpoint creates).
    assert client.post("/api/users/from-cv", headers=hr_headers, json=payload).status_code == 201


def test_change_password(client, admin_headers, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "smtp_host", "")
    address = _email()
    password = client.post("/api/users/from-cv", headers=admin_headers, json={
        "email": address, "name": "Change Me", "job_position_id": "sales-exec"}).json()["temporary_password"]
    headers = login(client, address, password)

    wrong = client.post("/api/auth/change-password", headers=headers,
                        json={"current_password": "wrong-one", "new_password": "NewPass#2026"})
    assert wrong.status_code == 400 and wrong.json()["code"] == "err_current_password"
    same = client.post("/api/auth/change-password", headers=headers,
                       json={"current_password": password, "new_password": password})
    assert same.status_code == 400 and same.json()["code"] == "err_password_unchanged"
    short = client.post("/api/auth/change-password", headers=headers,
                        json={"current_password": password, "new_password": "short"})
    assert short.status_code == 422
    too_long = client.post("/api/auth/change-password", headers=headers,
                           json={"current_password": password, "new_password": "ă" * 40})
    assert too_long.status_code == 422

    ok = client.post("/api/auth/change-password", headers=headers,
                     json={"current_password": password, "new_password": "NewPass#2026"})
    assert ok.status_code == 200
    assert ok.json()["password_is_temporary"] is False
    assert client.post("/api/auth/login", json={"email": address, "password": password}).status_code == 401
    assert client.post("/api/auth/login", json={"email": address, "password": "NewPass#2026"}).status_code == 200
    assert client.post("/api/auth/change-password", json={"current_password": "x", "new_password": "NewPass#2027"}).status_code == 401


def test_admin_reset_marks_the_password_temporary(client, admin_headers):
    staff = client.post("/api/users", headers=admin_headers, json={
        "email": _email(), "name": "Reset Me", "password": "Temp@1234", "user_role": "reviewer"}).json()
    assert staff["password_is_temporary"] is True
    reset = client.patch(f"/api/users/{staff['id']}", headers=admin_headers, json={"password": "Other@1234"})
    assert reset.json()["password_is_temporary"] is True
