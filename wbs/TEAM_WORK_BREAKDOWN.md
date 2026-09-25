# SKILLSPRINT AI - WORK BREAKDOWN STRUCTURE (WBS)
**Dự án:** SkillSprint AI – Dual-Pipeline AI Document Verification System  
**Cuộc thi:** TechWiz 7 – Generative AI Powerplay Track  
**Quy mô đội thi:** 4 thành viên | **Thời gian:** 5 ngày × 10 giờ/ngày

---

## I. MA TRẬN TRÁCH NHIỆM (RACI MATRIX)

| Thành viên | Vai trò chuyên trách | Nhánh Git phụ trách | Thư mục code đảm nhận |
| :--- | :--- | :--- | :--- |
| **Châu Quốc Lâm Phong** | **AI & Ingestion Engineer** | `feat/genai-pipeline` | `src/document_processing/` `src/document_validation/` `src/genai_pipeline/` `src/prompt_templates/` |
| **Đoàn Thị Quỳnh Nhi** | **Backend & Rule Engine Engineer** | `feat/python-rule-engine` | `src/python_validation/` `src/role_matrix/` `src/comparison_engine/` `src/hallucination_checks/` `src/contradiction_checks/` |
| **Phạm Tấn Tài** | **Fullstack & Database Developer** | `feat/frontend-dashboard` | `src/database/` `templates/` `static/` `src/schemas/` |
| **Lê Thị Kiều Duyên** | **QA, Security, Data & Docs Lead** | `docs/test-and-reports` | `tests/` `sample_documents/` `hidden_test_ready/` `documentation/` `reports/` |

> **Quy ước:** Mỗi ngày làm việc 10 giờ. Ước tính giờ/task là tham chiếu — thực tế linh hoạt ±1h.

---

## II. LỊCH TRIỂN KHAI CHI TIẾT THEO GIỜ (5 PHASES)

---

### PHASE 1 — Ngày 24/9/2026: Thiết lập Môi trường, Dữ liệu Nền tảng & CSDL
**Tổng thời gian:** 10 giờ | **Mục tiêu:** Hạ tầng dự án hoàn chỉnh, DB chạy, module đọc file hoạt động.

#### Châu Quốc Lâm Phong — AI & Ingestion Engineer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 1h | Tạo nhánh `feat/genai-pipeline`, cài môi trường Python (venv, requirements.txt), tạo `.env` từ `.env.example` | `.env` `requirements.txt` | Chạy `python --version` và `pip list` không lỗi |
| 1h – 2h | Nghiên cứu PyMuPDF (fitz) và python-docx; viết hàm `read_pdf()` trích xuất text kèm `page_number` | `src/document_processing/pdf_reader.py` | Hàm đọc được PDF test, in ra text đúng từng trang |
| 2h – 4h | Viết module chunking: `split_into_chunks()` chia text theo heading/section, gán `chunk_id`, `section_id` | `src/document_processing/chunker.py` | Output: list dict `{doc_id, chunk_id, section_id, heading, page, content}` |
| 4h – 5h | Viết `read_docx()` cho file .docx, tích hợp vào interface chung `ingest_document(file_path)` | `src/document_processing/docx_reader.py` | Cả PDF và DOCX đi qua cùng 1 hàm entry point |
| 5h – 6h | Viết module `document_validation`: kiểm tra file hợp lệ (định dạng, kích thước, không rỗng) | `src/document_validation/validator.py` | Raise `ValueError` đúng với file sai định dạng, file rỗng |
| 6h – 7h | Viết unit test cho document_processing và validation | `tests/test_document_processing.py` | Ít nhất 5 test case pass, gồm cả test file lỗi |
| 7h – 8h | Tích hợp end-to-end: chạy pipeline với 2 PDF + 1 DOCX từ sample_documents/ | `src/document_processing/__init__.py` | Output ra JSON chunk list, không có lỗi runtime |
| 8h – 9h | Review code theo Rules: xóa comment thừa, đặt lại tên biến ngữ cảnh, bổ sung docstring chuẩn | Toàn bộ `src/document_processing/` | Code pass kiểm tra Rules mục 1 (Anti-AI signature) |
| 9h – 10h | Commit lên nhánh `feat/genai-pipeline`, cập nhật `AI_USAGE.md` | Git | 1 commit rõ ràng với diff đúng phạm vi task |

---

#### Đoàn Thị Quỳnh Nhi — Backend & Rule Engine Engineer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 2h | Dựng khung FastAPI: `main.py`, cấu hình CORS, health check endpoint `/ping` | `main.py` | Server khởi động, `/ping` trả `{"status": "ok"}` |
| 2h – 5h | Khai báo Pydantic Schemas: `OnboardingPlan`, `Module`, `Task`, `Quiz`, `DocumentChunk` | `src/schemas/models.py` | Swagger UI `/document_processing`, `/document_validation` hiển thị đầy đủ 5+ schema |
| 5h – 8h | Viết API endpoint nhận upload file, gọi module TV1 để lấy chunks | `src/schemas/requests.py` | Endpoint `/upload` nhận file và trả về chunk list |
| 8h – 10h | Test toàn bộ API + commit lên nhánh `feat/python-rule-engine` | Git | Swagger UI hoàn chỉnh, không lỗi |

---

#### Phạm Tấn Tài — Fullstack & Database Developer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 2h | Cấu hình SQLAlchemy kết nối `skillsprint_db` PostgreSQL | `src/database/connection.py` | Kết nối DB không lỗi, log hiển thị "Connected" |
| 2h – 6h | Tạo 11 ORM Models và chạy migration tạo bảng (users, roles, documents, chunks, plans, modules, tasks, quizzes, quiz_answers, audit_logs, policy_matrix) | `src/database/models.py` | `\dt` trong psql hiển thị đủ 11 bảng |
| 6h – 9h | Seed data: 3 tài khoản `admin`, `reviewer`, `employee` kèm dữ liệu mẫu cơ bản | `src/database/seed.py` | Login test được 3 tài khoản mẫu |
| 9h – 10h | Commit lên nhánh `feat/frontend-dashboard`, cập nhật nhật ký | Git | Commit rõ ràng |

---

#### Lê Thị Kiều Duyên — QA, Security & Docs Lead (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 6h | Soạn 10 tài liệu đầu tiên (DOC-01→DOC-10) đúng theo title/category/department đã định nghĩa sẵn trong `frontend/src/data/company.js` (công ty giả định **FourAngryBirds EdTech & HR Solutions**, PDF/DOCX, >1 trang/file, có Document ID, heading/section đánh số, version + effective date). Bắt buộc: DOC-02 là bản obsolete của DOC-01 (test version control – SRS Step 8); DOC-07 (SOP Customer Escalation) phải có đúng Section 4.2 khớp ví dụ Table 1 trong SRS | `sample_documents/` | 10 file thật, đúng công ty FourAngryBirds, đủ Document ID + section numbering; DOC-07 §4.2 khớp ví dụ SRS Table 1 |
| 6h – 9h | Lập `role_matrix/role_matrix.csv` cho đúng 10 roles đã có trong `company.js` (Sales Executive, Customer Support Executive, HR Executive, Finance Associate, Operations Coordinator, Marketing Executive, Software Support Engineer, Branch Manager, Data Analyst, Team Leader/Tech Lead), đủ cột theo SRS Step 10: Role, Policy requirement, Process requirement, Competency, Mandatory/Optional, Priority, Source document, Source section, Assessment requirement. Requirement đầu tiên R001 phải khớp đúng ví dụ Table 1 SRS (SOP-07 §4.2, Customer Support Executive, Mandatory, High) | `role_matrix/role_matrix.csv` | ≥ 80 dòng yêu cầu (≥ 8/role), mỗi role ≥ 3 mandatory, R001 khớp đúng SRS Table 1, mọi Source document/section trỏ đúng vào DOC-01→DOC-10 |
| 9h – 10h | Tạo & push nhánh `docs/test-and-reports` (hiện chưa có trên remote), commit, cập nhật `AI_USAGE.md` | Git | Nhánh xuất hiện trên remote, 1 commit rõ ràng đúng phạm vi |

---

### PHASE 2 — Ngày 25/9/2026: Xây dựng Dual Pipeline Core
**Tổng thời gian:** 10 giờ | **Mục tiêu:** 2 luồng vận hành độc lập, output đúng schema 100%.

#### Châu Quốc Lâm Phong — AI & Ingestion Engineer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 1h | Cấu hình Gemini Pro API client, đọc API key từ `.env`, viết wrapper retry (max 3 lần, exponential backoff 2s) | `src/genai_pipeline/gemini_client.py` | Gọi API thành công, retry đúng khi gặp `APITimeoutError` |
| 1h – 3h | Thiết kế Pydantic response schema đầu ra LLM: `OnboardingPlan` → `Module` → `Task` → `Quiz`, có `source_citation` trên mỗi field | `src/genai_pipeline/response_schemas.py` | Schema validate đúng JSON mẫu từ Gemini |
| 3h – 5h | Viết prompt template `v1.0` sinh kế hoạch onboarding từ document chunks; lưu trong file `.txt` riêng theo đúng tên version | `src/prompt_templates/onboarding_plan_v1.txt` | Prompt sinh output đúng cấu trúc khi test thủ công với Gemini |
| 5h – 7h | Viết hàm `generate_onboarding_plan(doc_chunks, role)` gọi Gemini với `response_schema`, validate output bằng Pydantic | `src/genai_pipeline/plan_generator.py` | Trả về object Pydantic hợp lệ, có `source_citation` đính kèm từng field |
| 7h – 8h | Viết hàm `generate_quiz(module_content)` sinh 3–5 câu hỏi trắc nghiệm kèm `source_reference` | `src/genai_pipeline/quiz_generator.py` | Output câu hỏi có đáp án đúng, trích dẫn từ chunk gốc |
| 8h – 9h | Quản lý `prompt_version`: thêm metadata version vào mỗi lần gọi, lưu log prompt đã dùng | `src/prompt_templates/prompt_registry.py` | Mỗi output JSON có field `"prompt_version": "v1.0"` |
| 9h – 10h | Test end-to-end: PDF → chunks → Gemini → `OnboardingPlan` JSON; commit + cập nhật `AI_USAGE.md` | Git | Pipeline 1 sinh JSON chuẩn schema, không có raw text |

---

#### Đoàn Thị Quỳnh Nhi — Backend & Rule Engine Engineer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 4h | Viết Python thuần: đọc `role_matrix.csv`, tính `Coverage Score` (% nội dung chunk khớp yêu cầu role) bằng thuật toán nội bộ | `src/python_validation/coverage_scorer.py` | Trả về float 0.0–1.0 đúng tỷ lệ thực tế, không phụ thuộc AI |
| 4h – 7h | Viết `PrerequisiteChecker`: kiểm tra thứ tự module bắt buộc theo ma trận (module A phải học trước module B) | `src/python_validation/prerequisite_checker.py` | Phát hiện đúng module thiếu tiên quyết, raise lỗi cụ thể |
| 7h – 10h | Viết unit test kiểm tra coverage scorer + prerequisite checker; commit lên nhánh `feat/python-rule-engine` | `tests/test_rule_engine.py` Git | Engine không import bất kỳ AI SDK nào, test pass |

---

#### Phạm Tấn Tài — Fullstack & Database Developer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 5h | Xây dựng màn hình Document Ingestion: upload file với drag-and-drop, progress bar, hiển thị kết quả chunks | `templates/ingestion.html` `static/js/upload.js` | Upload file, hiển thị progress 0–100%, nhận kết quả chunk list |
| 5h – 10h | Giao diện Plan Detail: hiển thị `OnboardingPlan` → Modules → Tasks dạng accordion có expand/collapse | `templates/plan_detail.html` | Plan load đúng data từ API, accordion hoạt động mượt |

---

#### Lê Thị Kiều Duyên — QA, Security & Docs Lead (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 6h | Bổ sung thêm 10 tài liệu (tổng đạt 20 file), đa dạng lĩnh vực và định dạng (mix PDF + DOCX) | `sample_documents/` | Tổng cộng ≥ 20 file thực tế, không placeholder |
| 6h – 10h | Viết dàn ý báo cáo đồ án chi tiết theo yêu cầu đề bài (Architecture, SRS Mapping, Test Results, Deployment) | `documentation/PROJECT_REPORT_OUTLINE.md` | Outline đủ các mục, có phân công viết từng phần |

---

### PHASE 3 — Ngày 26/09/2026: Tích hợp Comparison Engine & Giao diện Reviewer
**Tổng thời gian:** 10 giờ | **Mục tiêu:** Hệ thống đối soát tự động 2 luồng, giao diện Reviewer hoàn chỉnh.

#### Châu Quốc Lâm Phong & Đoàn Thị Quỳnh Nhi — Cộng tác (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 2h | Thiết kế data contract chung giữa 2 pipeline (cấu trúc JSON để so sánh), thống nhất field names | `src/schemas/comparison_contract.py` | Cả 2 pipeline output đúng contract đã thống nhất |
| 2h – 5h | Viết `ComparisonEngine`: so khớp field-by-field output Pipeline 1 (Gemini) vs Pipeline 2 (Python) | `src/comparison_engine/engine.py` | Trả về diff report với trạng thái từng field: `match`/`mismatch` |
| 5h – 7h | Viết `HallucinationDetector`: phát hiện giá trị AI không xuất hiện trong document gốc (so khớp ngược với chunks) | `src/hallucination_checks/detector.py` | Gắn cờ `"hallucination": true` đúng khi AI bịa số liệu |
| 7h – 8h | Viết logic phân loại trạng thái cuối: `Verified` / `Verified with Warning` / `Manual Review Required` | `src/comparison_engine/classifier.py` | 3 kịch bản test cho 3 trạng thái đều ra kết quả đúng |
| 8h – 9h | Viết `ContradictionChecker`: phát hiện nội dung mâu thuẫn trong cùng tài liệu (2 quy định trái nhau) | `src/contradiction_checks/checker.py` | Cờ mâu thuẫn đúng với test case có 2 policy xung đột |
| 9h – 10h | Commit riêng lẻ từng module theo convention, cập nhật `AI_USAGE.md` | Git | 3–4 commit rõ ràng, mỗi commit 1 module |

---

#### Phạm Tấn Tài — Fullstack & Database Developer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 6h | Giao diện **Dual Comparison View**: 2 cột song song Pipeline 1 vs Pipeline 2, highlight đỏ chỗ mismatch, highlight vàng chỗ warning | `templates/reviewer_dashboard.html` | Hiển thị đúng diff, màu sắc highlight đúng trạng thái |
| 6h – 9h | Nút `Approve`, `Reject`, `Override` ghi log đầy đủ vào bảng `audit_logs` (timestamp, reviewer_id, action, reason) | `static/js/comparison.js` | Mỗi click ghi DB đúng, log truy vấn được qua API |
| 9h – 10h | Commit lên nhánh `feat/frontend-dashboard` | Git | Commit rõ ràng |

---

#### Lê Thị Kiều Duyên — QA & Security (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 5h | Viết 10 kịch bản Prompt Injection test: "ignore previous instructions", "system override", "DAN mode"... | `tests/test_adversarial.py` | Hệ thống chặn/cảnh báo đúng 10/10 kịch bản |
| 5h – 10h | Chuẩn bị 10 tài liệu chính sách hết hạn / mâu thuẫn nội bộ để kiểm thử ContradictionChecker | `sample_documents/adversarial/` | 10 file bẫy sẵn sàng, có tài liệu ghi chú kịch bản kiểm thử |

---

### PHASE 4 — Ngày 27/09/2026: Hidden Test Ready, Blog & Video Demo
**Tổng thời gian:** 10 giờ | **Mục tiêu:** Sẵn sàng cho Hidden Test, ấn phẩm truyền thông hoàn chỉnh.

#### Châu Quốc Lâm Phong — AI & Ingestion Engineer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 2h | Kịch bản Hidden Test: nạp 1 tài liệu chính sách hoàn toàn mới, kiểm tra toàn bộ pipeline end-to-end không lỗi | `hidden_test_ready/` | Hệ thống tự động sinh plan từ tài liệu mới không cần can thiệp thủ công |
| 2h – 4h | Hardening pipeline: xử lý edge cases (file rỗng, PDF scan không text, encoding UTF-16, file >10MB) | `src/document_processing/` | Pipeline xử lý trơn tru ≥ 3 loại edge case, raise lỗi rõ ràng với loại còn lại |
| 4h – 6h | Viết kịch bản demo hoàn chỉnh + timeline chi tiết từng cảnh quay cho video | `documentation/demo_script.md` | Kịch bản ≤ 5 phút, có checklist tick từng cảnh quay |
| 6h – 10h | Quay và dựng video demo `.mp4` cùng cả nhóm — TV1 phụ trách phần demo pipeline xử lý tài liệu | `documentation/` | File `.mp4` xuất hoàn chỉnh, âm thanh rõ, caption đầy đủ |

---

#### Đoàn Thị Quỳnh Nhi — Backend & Rule Engine Engineer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 4h | Tham gia kiểm thử Hidden Test cùng TV1; kiểm tra Rule Engine hoạt động đúng với tài liệu mới | `src/python_validation/` | Coverage Score tính đúng với dữ liệu chưa từng thấy |
| 4h – 8h | Viết middleware bảo mật: lọc Prompt Injection trước khi text đi vào Gemini pipeline | `src/security/injection_filter.py` | Chặn đúng các chuỗi tấn công phổ biến, log cảnh báo |
| 8h – 10h | Hỗ trợ quay video + commit | Git | Commit rõ ràng |

---

#### Phạm Tấn Tài — Fullstack & Database Developer (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 5h | Learner Portal: hiển thị checklist module/task với ô tích hoàn thành, lưu tiến độ vào DB | `templates/learner_portal.html` | Tích task và lưu state vào DB, reload trang vẫn giữ trạng thái |
| 5h – 10h | Màn hình làm trắc nghiệm: hiển thị câu hỏi kèm trích dẫn nguồn, tính điểm ngay sau submit | `templates/quiz_view.html` | Điểm tính đúng, nguồn trích dẫn hiển thị rõ ràng |

---

#### Lê Thị Kiều Duyên — QA & Docs Lead (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 8h | Biên soạn và đăng tải bài viết Technical Blog >2.000 từ lên Medium/Dev.to (kiến trúc hệ thống, dual pipeline, kết quả) | `documentation/BLOG_DRAFT.md` | URL blog công khai, đã publish, >2.000 từ |
| 8h – 10h | Hỗ trợ dựng video demo + kiểm tra sơ bộ submission checklist | — | Checklist sơ bộ, ghi chú các hạng mục còn thiếu |

---

### PHASE 5 — Ngày 28/09/2026: Đóng gói Triển khai & Bàn giao
**Tổng thời gian:** 10 giờ | **Mục tiêu:** Deploy online ổn định, 100% submission checklist 18 tiêu chí xanh.

#### Châu Quốc Lâm Phong & Đoàn Thị Quỳnh Nhi — Code Quality & Documentation (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 3h | Tối ưu toàn bộ code: loại bỏ comment rác, kiểm tra exception handling theo Rules (không `except Exception: pass`) | Toàn bộ `src/` | Không còn `pass`, `# TODO`, `# logic here`, `except Exception: pass` |
| 3h – 5h | Viết `README.md` hoàn chỉnh: hướng dẫn A–Z (clone → venv → .env → DB migrate → run server) | `README.md` | Người ngoài nhóm chạy theo README thành công lần đầu |
| 5h – 7h | Kiểm tra toàn bộ Git history đảm bảo không có secret, verify `.env.example` chuẩn | `.env.example` Git history | `git log --all -p` không thấy key thật hoặc password thật |
| 7h – 9h | Chạy toàn bộ test suite, fix bug cuối, đảm bảo coverage ≥ 90% | `tests/` | CI test suite pass ≥ 90%, không có test bị skip vô lý |
| 9h – 10h | Commit cuối + tag release `v1.0.0` + kiểm tra biểu đồ commit GitHub 4 thành viên đều đặn | Git | Tag `v1.0.0` xuất hiện, commit graph đều các thành viên |

---

#### Phạm Tấn Tài — Fullstack & Deployment (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 2h | Viết `Dockerfile` và `docker-compose.yml` cho toàn bộ stack (app + PostgreSQL) | `Dockerfile` `docker-compose.yml` | `docker-compose up` chạy được toàn bộ hệ thống local |
| 2h – 6h | Deploy lên Render/Railway: cấu hình environment variables, kết nối DB cloud | `config/` | URL công khai truy cập được, API trả đúng response |
| 6h – 10h | Test smoke trên môi trường production: upload file, xem plan, trang reviewer, trang learner | — | Tất cả 5 luồng chính hoạt động đúng trên cloud |

---

#### Lê Thị Kiều Duyên — QA Final & Submission (10 giờ)

| Giờ | Công việc | File / Thư mục | Tiêu chí hoàn thành |
| :---: | :--- | :--- | :--- |
| 0h – 6h | Hoàn thiện Project Report PDF: sơ đồ kiến trúc, SRS mapping, ảnh screenshot, kết quả test, kết luận | `reports/Project_Report.pdf` | PDF ≥ 20 trang, đủ sơ đồ kiến trúc và ảnh minh họa |
| 6h – 9h | Rà soát toàn bộ 18 tiêu chí submission checklist, đảm bảo `AI_USAGE.md` đầy đủ mọi lần dùng AI | `AI_USAGE.md` | Checklist tick xanh 18/18 tiêu chí |
| 9h – 10h | Nộp bài chính thức: submit GitHub link, deployed URL, video, blog, report PDF | — | Xác nhận email nộp bài thành công |

---

## III. NGUYÊN TẮC LÀM VIỆC DỰ ÁN

| Tiêu chuẩn | Quy định bắt buộc |
| :--- | :--- |
| **Tần suất Commit** | Tối thiểu **1–2 commit/ngày/người** trên nhánh riêng để ghi nhận tiến độ liên tục |
| **Quy trình Merge** | Hoàn thành feature trên nhánh `feat/...` → Tạo **Pull Request** → Member khác review → Merge vào `main` |
| **Bảo mật tuyệt đối** | **Tuyệt đối không commit** file `.env`, API Key, mật khẩu DB lên GitHub |
| **Tính minh bạch AI** | Ghi đầy đủ vào `AI_USAGE.md` mọi đoạn code/tài liệu có hỗ trợ của AI |
| **Chất lượng code** | Tuân thủ Rules mục 1: không comment "What", chỉ docstring chuẩn + giải thích "Why" |