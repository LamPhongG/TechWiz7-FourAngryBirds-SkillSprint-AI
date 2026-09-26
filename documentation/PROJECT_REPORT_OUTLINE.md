# DÀN Ý BÁO CÁO ĐỒ ÁN — SKILLSPRINT AI
**Dự án:** SkillSprint AI – Dual-Pipeline AI Document Verification System
**Cuộc thi:** TechWiz 7 – Generative AI Powerplay Track
**Yêu cầu độ dài:** ≥ 20 trang (theo checklist nộp bài, Phase 5)
**Định dạng nộp:** PDF (`reports/Project_Report.pdf`)
**Người tổng hợp & rà soát cuối:** Lê Thị Kiều Duyên (QA, Security, Data & Docs Lead)

> Dàn ý này bám sát đúng danh mục nội dung bắt buộc của báo cáo đồ án nêu trong SRS
> (mục 1.10, hạng mục 1 – Project Report), đồng thời nhấn mạnh 4 mảng được yêu cầu
> riêng ở WBS Phase 2: **Architecture, SRS Mapping, Test Results, Deployment**.
> Mỗi mục có: nội dung cần viết, nguồn tài liệu/artifact tương ứng trong repo, người
> phụ trách chính, và trạng thái. Cập nhật cột "Trạng thái" khi từng phần được viết.

---

## 0. Trang bìa & Mục lục
- Tên đồ án, tên đội, TechWiz 7, logo (nếu có), ngày nộp.
- Mục lục tự động theo heading.
- **Phụ trách:** Lê Thị Kiều Duyên | **Trạng thái:** Chưa viết

---

## 1. Tóm tắt điều hành (Executive Summary)
- 1 trang: vấn đề, giải pháp, kết quả nổi bật (Coverage Score, Traceability Score đạt được), điểm khác biệt (dual-pipeline độc lập, không hard-code).
- **Nguồn:** tổng hợp từ mục 2, 8, 9 bên dưới.
- **Phụ trách:** Lê Thị Kiều Duyên | **Trạng thái:** Chưa viết

---

## 2. Giới thiệu & Bối cảnh (Problem Definition, Background)
- 2.1 Bối cảnh & sự cần thiết (SRS §1.1) — vấn đề onboarding thủ công hiện nay.
- 2.2 Giải pháp đề xuất (SRS §1.2) — tóm tắt kiến trúc dual-pipeline.
- 2.3 Mục đích tài liệu (SRS §1.3).
- 2.4 Phạm vi dự án (SRS §1.4) — trong/ngoài phạm vi (không tích hợp HRMS/payroll thật).
- 2.5 Ràng buộc (SRS §1.5) — phụ thuộc chất lượng tài liệu nguồn, biến thiên output GenAI.
- **Nguồn:** SRS gốc, [README.md](../README.md).
- **Phụ trách:** Lê Thị Kiều Duyên | **Trạng thái:** Chưa viết

---

## 3. Yêu cầu hệ thống (Functional & Non-Functional Requirements)
- 3.1 Danh sách đầy đủ 66 Functional Requirements (SRS §1.6, mục i–lxvi) — tóm tắt theo nhóm: Auth/RBAC, Document, Requirement Matrix, GenAI Pipeline, Python Validation, Comparison/Verification, Security, Dashboard, Search/Report.
- 3.2 Non-Functional Requirements (SRS §1.7): Performance (<30s), Scalable (1.000 hồ sơ/100 roles/1.000 docs), Usable, Accuracy & Grounding (100% mandatory coverage), Available (≥99% uptime).
- 3.3 Bảng đối chiếu **mỗi FR/NFR → module code implement → trạng thái Done/Partial/Not started** (đây chính là bảng dùng lại ở mục 8 — SRS Mapping).
- **Nguồn:** SRS §1.6–1.7, mã nguồn `backend/`/`src/`.
- **Phụ trách:** Đoàn Thị Quỳnh Nhi (rà theo backend) + Châu Quốc Lâm Phong (rà theo GenAI) | **Trạng thái:** Chưa viết

---

## 4. Kiến trúc hệ thống (Architecture) — trọng tâm WBS
### 4.1 Kiến trúc tổng quan
- Sơ đồ 8 khối theo đúng "Sample Architecture" của SRS (trang 11): Company Knowledge Sources → Document Upload & Processing → Role & Requirement Setup → Pipeline 1 (GenAI) / Pipeline 2 (Python Validation) → Result Comparison → Verification Decision → Final Onboarding Plan → Dashboard & Reports.
- Công nghệ dùng ở mỗi khối (tham chiếu bảng "Danh mục công nghệ chuẩn" của đội).

### 4.2 Sơ đồ bắt buộc (SRS §1.10 mục 1)
- Data Flow Diagram (DFD mức 0 và mức 1).
- Use Case Diagram (Admin, Reviewer, Employee, HR).
- Activity Diagram (luồng: upload → chunk → generate → validate → compare → review → publish).
- Sequence Diagram (1 luồng chi tiết: sinh & kiểm định 1 onboarding plan).

### 4.3 Kiến trúc Document-Processing Pipeline
- `document_processing/`, `document_validation/`: đọc PDF/DOCX/TXT/MD/CSV, chunking, metadata, version control.

### 4.4 Kiến trúc Backend & Database
- Sơ đồ ERD (11 bảng: users, roles, documents, chunks, plans, modules, tasks, quizzes, quiz_answers, audit_logs, policy_matrix).
- API contract chính (FastAPI endpoints, Swagger).

### 4.5 Kiến trúc Frontend
- Sơ đồ luồng màn hình theo vai trò (HR/Reviewer/Employee) — tham chiếu [documentation/FRONTEND_FLOWS.md](FRONTEND_FLOWS.md).

- **Nguồn:** [FRONTEND_FLOWS.md](FRONTEND_FLOWS.md), `backend/app/` hoặc `src/`, `role_matrix/`, `sample_documents/`.
- **Phụ trách:** Phạm Tấn Tài (4.4, 4.5) + Châu Quốc Lâm Phong (4.3) + Đoàn Thị Quỳnh Nhi (4.1 tổng hợp, 4.2 sơ đồ) | **Trạng thái:** Chưa viết

---

## 5. Pipeline 1 — GenAI Generation Pipeline
- 5.1 API/Model sử dụng (Gemini/OpenAI/Anthropic), cấu hình retry (SRS Step 39).
- 5.2 Thiết kế Prompt: template `prompts/`, quản lý version (`prompt_registry.py`), ví dụ prompt thật.
- 5.3 JSON Schema đầu ra (Pydantic `response_schemas.py`) — ví dụ JSON mẫu (đối chiếu SRS Step 37).
- 5.4 Luồng sinh: Onboarding Plan → Module → Task → Quiz → Assessment, kèm `source_citation` bắt buộc.
- 5.5 GenAI Consistency Check (Step 44–45) — kết quả so sánh 2 lần sinh cùng input.
- **Nguồn:** `genai_pipeline/`, `prompt_templates/`.
- **Phụ trách:** Châu Quốc Lâm Phong | **Trạng thái:** Chưa viết

---

## 6. Pipeline 2 — Python Ground-Truth Validation Pipeline
- 6.1 Role Requirement Matrix: cấu trúc, cách xây dựng từ `role_matrix/role_matrix.csv` (80 dòng, 10 roles — xem [role_matrix/README.md](../role_matrix/README.md)).
- 6.2 Thuật toán Coverage Score, Traceability Score, Requirement Consistency Score (công thức + code).
- 6.3 Hallucination Detection, Unsupported Content Detection.
- 6.4 Contradiction Detection & Policy Precedence Rules (ví dụ thật: DOC-01 §6 vs DOC-02 §6 — xem [sample_documents/README.md](../sample_documents/README.md)).
- 6.5 Duplicate Detection, Role-Relevance Validation, Prerequisite/Sequence Validation.
- 6.6 Xác nhận: pipeline này **không** import bất kỳ SDK AI nào (đối chiếu Rules mục 3).
- **Nguồn:** `python_validation/`, `role_matrix/`, `hallucination_checks/`, `contradiction_checks/`.
- **Phụ trách:** Đoàn Thị Quỳnh Nhi | **Trạng thái:** Chưa viết

---

## 7. Comparison Engine & Verification Workflow
- 7.1 Data contract chung giữa 2 pipeline (`comparison_contract.py`).
- 7.2 Bảng so sánh field-by-field (Requirement ID, Role, Source, kết quả Python vs GenAI, Match/Mismatch) — ví dụ thật tái hiện đúng SRS Table 1 (R001, SOP-07 §4.2).
- 7.3 Phân loại trạng thái cuối: Verified / Verified with Warning / Partially Verified / Manual Review Required...
- 7.4 Human Review Workflow: Approve/Reject/Edit/Regenerate, Reviewer Override, Audit Trail.
- **Nguồn:** `comparison_engine/`, `audit_logs`.
- **Phụ trách:** Đoàn Thị Quỳnh Nhi (logic) + Phạm Tấn Tài (giao diện Dual Comparison View) | **Trạng thái:** Chưa viết

---

## 8. Đối chiếu yêu cầu SRS (SRS Mapping) — trọng tâm WBS
- 8.1 **Bảng truy vết đầy đủ**: mỗi mục FR (i–lxvi) và NFR (1–5) → section báo cáo tương ứng → file code triển khai → trạng thái → người chịu trách nhiệm.
- 8.2 Đối chiếu 63 "Development Step" (SRS trang 12–27) → module/code tương ứng, đánh dấu Done/Partial/N/A.
- 8.3 Đối chiếu "Competition Integrity & Anti-Shortcut Requirements" (SRS §1.8, 16 mục) → bằng chứng cụ thể (VD: mục 11 "GitHub Activity" → link lịch sử commit; mục 16 "AI_USAGE.md" → link file).
- 8.4 Đối chiếu 18 tiêu chí Submission Checklist (SRS §1.10 cuối) → trạng thái xanh/vàng/đỏ.
- **Nguồn:** SRS gốc (toàn bộ), tất cả các module.
- **Phụ trách:** Lê Thị Kiều Duyên (tổng hợp bảng) — mỗi thành viên xác nhận đúng phần module mình phụ trách trước khi chốt | **Trạng thái:** Chưa viết

---

## 9. Bảo mật (Security)
- 9.1 Prompt Injection Defense: middleware lọc (`security/injection_filter.py`), danh sách chuỗi tấn công chặn được.
- 9.2 Adversarial Document Testing: 10 kịch bản trong `sample_documents/adversarial/` (Phase 3) — kết quả chặn/cảnh báo từng kịch bản.
- 9.3 Quản lý API Key & secrets (`.env`, `.env.example`, xác nhận không lộ key qua `git log --all -p`).
- 9.4 Access control theo vai trò (RBAC).
- **Nguồn:** `security/`, `tests/test_adversarial.py`, `reports/` (Security Testing Report).
- **Phụ trách:** Lê Thị Kiều Duyên (kịch bản & báo cáo) + Đoàn Thị Quỳnh Nhi (middleware) | **Trạng thái:** Chưa viết

---

## 10. Kiểm thử & Kết quả kiểm thử (Testing & Test Results) — trọng tâm WBS
### 10.1 Chiến lược kiểm thử
- Loại test: Functional, Document-upload, Parsing/Chunking, Requirement extraction, GenAI API, JSON schema, Python validation, Source traceability, Coverage, Hallucination, Contradiction, Prompt injection, Role-relevance, Policy-version, Regeneration, Hidden-document readiness, Security, Boundary (đúng 18 nhóm theo SRS deliverable #10).

### 10.2 Kết quả theo từng nhóm (bảng: Tổng test / Pass / Fail / Ghi chú)
- Unit test coverage % (mục tiêu ≥ 90% theo WBS Phase 5).
- Kết quả 10 kịch bản Prompt Injection (10/10 chặn đúng — mục tiêu Phase 3).
- Kết quả Hidden Test Readiness (Phase 4): nạp tài liệu hoàn toàn mới, pipeline chạy không cần can thiệp thủ công.

### 10.3 Báo cáo so sánh GenAI vs Python (≥ 100 requirement-level results — SRS deliverable #6)
- Bảng mẫu: Requirement ID, Role, Source, Python expected, GenAI result, Match/Mismatch, giải thích khi lệch nhau.

### 10.4 Giới hạn phát hiện qua kiểm thử (đưa vào mục 12 – Limitations)

- **Nguồn:** `tests/`, CI logs, `reports/`.
- **Phụ trách:** Lê Thị Kiều Duyên (tổng hợp + 10.1, 10.2) + Châu Quốc Lâm Phong & Đoàn Thị Quỳnh Nhi (10.3, số liệu từ pipeline của mình) | **Trạng thái:** Chưa viết

---

## 11. Triển khai (Deployment) — trọng tâm WBS
- 11.1 Đóng gói: `Dockerfile`, `docker-compose.yml` (app + PostgreSQL).
- 11.2 Nền tảng triển khai: Render/Railway — cấu hình environment variables, kết nối DB cloud.
- 11.3 URL công khai, tài khoản demo (evaluator/admin), hướng dẫn truy cập.
- 11.4 Kết quả smoke test trên production: upload file, xem plan, trang reviewer, trang learner (5 luồng chính).
- 11.5 Giới hạn hạ tầng (free-tier limits, cold start, v.v. nếu có).
- **Nguồn:** `Dockerfile`, `docker-compose.yml`, `config/`.
- **Phụ trách:** Phạm Tấn Tài | **Trạng thái:** Chưa viết

---

## 12. Giới hạn & Hướng phát triển (Limitations & Future Enhancements)
- Giới hạn hiện tại (VD: 2 role chưa có SOP riêng — Operations Coordinator, Marketing Executive, xem `role_matrix/README.md`; định dạng doc bổ sung TXT/CSV chưa bắt buộc; quy mô demo giới hạn so với NFR 1.000 hồ sơ).
- Hướng phát triển: tích hợp HRMS thật, mở rộng embeddings/semantic search, thêm ngôn ngữ, v.v.
- **Phụ trách:** Lê Thị Kiều Duyên | **Trạng thái:** Chưa viết

---

## 13. Kết luận
- Tóm tắt kết quả đạt được so với mục tiêu ban đầu, đóng góp của từng thành viên (ngắn gọn — chi tiết đã có ở `AI_USAGE.md` và Git history).
- **Phụ trách:** Lê Thị Kiều Duyên | **Trạng thái:** Chưa viết

---

## 14. Phụ lục (Appendices)
- A. Bộ tài liệu công ty mẫu (danh mục 20 tài liệu — `sample_documents/README.md`).
- B. Role Requirement Matrix đầy đủ (`role_matrix/role_matrix.csv`).
- C. AI Usage Declaration Log đầy đủ (`AI_USAGE.md`).
- D. Ảnh chụp màn hình chính (`screenshots/`).
- E. Link video demo (.mp4) và bài Technical Blog (>2.000 từ).
- F. Team Contribution Record (bảng phân công + % đóng góp mỗi thành viên).
- **Phụ trách:** Lê Thị Kiều Duyên (tổng hợp) — mỗi thành viên nộp phần liên quan trước Phase 5, 5h | **Trạng thái:** Chưa viết

---

## Bảng phân công tổng hợp (theo người)

| Thành viên | Mục phụ trách chính | Mục hỗ trợ / rà soát |
| :--- | :--- | :--- |
| **Châu Quốc Lâm Phong** | 5 (Pipeline 1 – GenAI) | 3.3, 4.3, 8.2, 10.3 |
| **Đoàn Thị Quỳnh Nhi** | 6 (Pipeline 2 – Python Validation), 7.1–7.3 | 3.3, 4.1/4.2, 8.2, 9.1, 10.3 |
| **Phạm Tấn Tài** | 4.4, 4.5 (Backend/Frontend Architecture), 7.4, 11 (Deployment) | — |
| **Lê Thị Kiều Duyên** | 0, 1, 2, 3.1 (rà soát), 8 (SRS Mapping), 9.2–9.3, 10.1/10.2/10.4, 12, 13, 14 | Tổng hợp & định dạng bản PDF cuối cùng |

## Quy trình hoàn thiện
1. Mỗi thành viên viết phần mình phụ trách trực tiếp vào các file nguồn tương ứng
   (không viết thẳng vào outline này — outline chỉ là khung).
2. Lê Thị Kiều Duyên gộp toàn bộ thành `reports/Project_Report.md` → export PDF ≥ 20 trang (Phase 5, 0h–6h).
3. Rà soát chéo: mỗi thành viên đọc lại phần của người khác một lượt trước khi chốt (Phase 5, 6h–9h — trùng với rà soát Submission Checklist 18 tiêu chí).
