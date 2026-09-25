# SkillSprint AI — Frontend

Giao diện web của SkillSprint AI cho công ty giả lập **FourAngryBirds EdTech & HR Solutions**.

Công cụ này **không** dùng để quản lý nhân sự. Nó biến tài liệu nội bộ (PDF, DOCX, TXT, MD, CSV) thành **lộ trình học** cho nhân viên mới hoặc nhân viên thăng chức. Luồng chính như sau:

1. **HR** tải tài liệu lên, rồi cho AI soạn lộ trình.
2. **Reviewer** kiểm tra lộ trình: đúng kiến thức, đúng luồng, đúng chức năng của vị trí. Sau đó phát hành cho phòng ban, hoặc trả về HR kèm góp ý.
3. **Nhân viên** học theo lộ trình được giao: đọc bài, mở tài liệu gốc, làm nhiệm vụ, làm bài kiểm tra.

Giao diện có đủ **tiếng Việt và tiếng Anh**.

📄 **Chức năng, luồng thực hiện và danh sách thay đổi:** [`documentation/FRONTEND_FLOWS.md`](../documentation/FRONTEND_FLOWS.md)

> **Trạng thái (25/09/2026):** chạy độc lập, chưa nối backend Python.
>
> **Đã chạy thật trong trình duyệt:**
> - Kho tài liệu.
> - Trích xuất và chia chunk.
> - Quét prompt injection.
> - Kiểm định lộ trình.
> - Vòng đời duyệt kèm audit log.
> - Tiến độ học của nhân viên.
>
> **Còn tạm thời:** nội dung lộ trình là *bản nháp dựng từ cấu trúc tài liệu* cho tới khi có Gemini, và dữ liệu chỉ lưu trong trình duyệt đang dùng.

---

## 1. Chạy dự án

Yêu cầu Node.js ≥ 18.

```bash
cd frontend
npm install        # hoặc: npm ci
npm run dev        # http://localhost:3000
npm test           # unit test (Vitest)
npm run build      # build production vào dist/
npm run preview    # chạy thử bản build
```

**Đăng nhập demo:** trang `/login` dạng glassmorphism. Nhập email + mật khẩu, hoặc bấm chip tài khoản demo để điền sẵn. Tài khoản nằm trong mã nguồn (`hooks/useAuth.js`) cho tới khi backend có xác thực thật.

| Vai trò | Email | Mật khẩu | Trang chính |
| :--- | :--- | :--- | :--- |
| HR | `hr@fourangrybirds.vn` (Jordan Lee) | `Demo@123` | `/hr/dashboard` |
| Người duyệt (Reviewer) | `reviewer@fourangrybirds.vn` (Sarah Chen) | `Demo@123` | `/reviewer/dashboard` |
| Nhân viên | `alex.morgan@fourangrybirds.vn` (Alex Morgan, Software Support Engineer, phòng Kỹ thuật; đổi được vị trí ở trang Hồ sơ) | `Demo@123` | `/employee/dashboard` |

*Ghi nhớ đăng nhập:* bật thì phiên còn sau khi đóng trình duyệt (`localStorage`); tắt thì hết khi đóng tab (`sessionStorage`). Không có trang đăng ký: tài khoản do HR cấp.

**Kịch bản demo nhanh:**
1. HR tải tài liệu ở **Tài liệu**.
2. HR vào **Tạo lộ trình**, bấm *Chọn tất cả tài liệu sẵn sàng* rồi *Sinh lộ trình*, sau đó bấm **Gửi kiểm duyệt**.
3. Reviewer mở **Hàng đợi duyệt**, xem tab **Kiểm định**, rồi bấm **Duyệt & phát hành** cho phòng Kỹ thuật.
4. Nhân viên mở **Lộ trình của tôi** và học.

**Nối backend:** copy `.env.example` thành `.env.local` và đặt `VITE_API_URL=http://localhost:8000`. Khi có biến này, frontend gọi `POST /upload` để xử lý tài liệu và `POST /paths/generate` để sinh lộ trình. Hợp đồng API ở mục 7 của tài liệu luồng.

---

## 2. Công nghệ

| Hạng mục | Công nghệ | Dùng để |
| :--- | :--- | :--- |
| UI | React 18, React Router 7 | Component, điều hướng theo vai trò |
| Build | Vite 6 | Dev server, build |
| Đọc PDF / DOCX | pdfjs-dist 5, mammoth 1.12 | Trích xuất văn bản trong trình duyệt (nạp động, chỉ tải khi cần) |
| Lưu trữ | IndexedDB, localStorage, sessionStorage | Tài liệu + chunk; lộ trình, audit log, tiến độ; phiên đăng nhập |
| Băm file | Web Crypto (SHA-256) | Phát hiện file trùng |
| Icon | lucide-react | |
| Đa ngôn ngữ | `LanguageContext` tự viết | `t()`, `tv()`, `pick()` — 567 khoá, vi/en khớp 100% |
| Test | Vitest 3 | `frontend/tests/` |

---

## 3. Cấu trúc thư mục

```
frontend/
├── .env.example
├── tests/                         # Vitest: chunker, injection, sinh lộ trình, kiểm định, phân quyền + tiến độ, lọc dữ liệu
└── src/
    ├── App.jsx                    # Route theo vai trò, chặn truy cập, chuyển hướng link cũ
    ├── layouts/                   # AuthLayout, RoleLayout (khung chung cho HR / Reviewer / Nhân viên)
    ├── contexts/
    │   ├── DocumentsContext.jsx   # Kho tài liệu, tiến độ xử lý, chunk
    │   ├── PathsContext.jsx       # Lộ trình + audit log + thao tác duyệt
    │   ├── EnrollmentContext.jsx  # Tiến độ học của nhân viên
    │   └── LanguageContext.jsx
    ├── components/
    │   ├── path/                  # PathContent, PathChecks, PathComments, PathActions, AuditTable, Badges
    │   └── Citation, DocumentProcessing, ErrorBoundary, InjectionFlagList, UI, ValidationTag...
    ├── hooks/                     # useAuth (đăng nhập demo, phiên), useMyPaths (lộ trình được giao)
    ├── pages/
    │   ├── hr/                    # Dashboard, Documents, CreatePath
    │   ├── reviewer/              # Dashboard
    │   ├── shared/                # PathList, PathDetail, AuditLog (HR + Reviewer)
    │   ├── employee/              # Dashboard, MyPaths, PathView, ModuleView, Documents, Profile
    │   └── auth/                  # Login (glassmorphism)
    ├── services/                  # apiClient, documentStore, documentProcessing, textExtraction, pipelineService, localStore, sanitize
    ├── utils/                     # chunker, injectionScan, pathGenerator, pathChecks, pathWorkflow, progress, documentValidation
    ├── data/                      # company.js (vị trí, phòng ban, danh mục 20 tài liệu, mẫu giai đoạn)
    ├── locales/                   # en.js, vi.js
    └── styles/                    # index.css (nền, layout), features.css (các tính năng)
```

---

## 4. Kiểm thử

| Kiểm thử | Kết quả |
| :--- | :--- |
| `npm test` — 77 test / 6 file | 77/77 đạt |
| `npm run build` | Thành công |
| E2E Chrome headless, toàn luồng HR → Reviewer (trả về, duyệt lại) → phát hành → Nhân viên học và làm bài | Chạy đúng, không lỗi console, 0 khoá dịch bị lộ ở cả vi/en |

Chi tiết các bước E2E ở mục 9 của [`FRONTEND_FLOWS.md`](../documentation/FRONTEND_FLOWS.md). Script E2E nằm ngoài repo.

---

## 5. Giới hạn hiện tại

- **Chưa nối Gemini:** lộ trình là bản nháp dựng từ tài liệu (bài học là nguyên văn các mục, câu hỏi và nhiệm vụ lấy từ câu có thật).
- **Dữ liệu chỉ lưu trong trình duyệt đang dùng:** lộ trình, góp ý, audit log, tiến độ học nằm ở `localStorage`; tài liệu nằm ở IndexedDB. Cần API backend để nhiều người dùng chung.
- **Đăng nhập là demo**, mỗi vai trò một tài khoản.
- **Chưa có OCR** cho PDF scan.
- **Coverage theo Role Requirement Matrix** do backend Python tính; frontend chỉ hiển thị kết quả trả về (chưa có thì ghi *chờ backend*).

**Trang trắng?** Không mở trực tiếp `dist/index.html`; hãy dùng `npm run dev` hoặc `npm run preview`. Nếu dữ liệu demo cũ trong trình duyệt bị hỏng, trang báo lỗi có nút **Xoá dữ liệu demo**.
