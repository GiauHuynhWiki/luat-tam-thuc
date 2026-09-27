# Trợ lý đọc sách *Luật Tâm Thức*

Dự án biến cuốn *Luật Tâm Thức – Vũ Trụ Nhất Nguyên Luận* (Ngô Sa Thạch, Skybooks 2024) thành dữ liệu tra cứu, để khi đọc sách bạn hỏi AI (Claude Code, Codex, Gemini CLI…) và được giải thích kèm số trang, hình của sách, và liên hệ với kiến thức bên ngoài.

Repo **không chứa nội dung sách** (file PDF, chữ OCR, hình) vì sách còn bản quyền. Bạn cần có bản PDF của mình, rồi chạy một lệnh để tạo lại dữ liệu trên máy.

## Cài đặt

Yêu cầu: macOS, Xcode Command Line Tools (`xcode-select --install`), Python 3.

1. Clone repo, đặt file PDF vào thư mục gốc với đúng tên `Luat TamThuc2.pdf`.
2. Chạy (mất khoảng vài chục phút):

   ```bash
   bash tools/setup.sh
   ```

   Script tạo `.cache/pages/` (ảnh trang), `book/` (chữ OCR theo chương, có đánh dấu trang), `hinh/` (hình cắt riêng). Nếu PDF không đúng bản dự án dùng, script sẽ cảnh báo trước.

## Sử dụng

Mở Claude Code, Codex hoặc Gemini CLI **trong thư mục này** rồi hỏi, ví dụ:

- "Trang 41 nói gì về con số 142857?"
- "Giải thích Bánh đà nghiệp quả, liên hệ với nghiệp trong Phật giáo."
- "Sách giải thích thế nào từ Vô cực đến Bát quái?"

AI tự đọc hướng dẫn trong `AGENTS.md` (Claude Code đọc qua `CLAUDE.md`, Gemini qua `GEMINI.md`): tra chỉ mục, tìm trong sách, đọc ảnh trang gốc rồi mới trả lời.

## Cấu trúc

| Đường dẫn | Trong repo | Nội dung |
|---|---|---|
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | có | hướng dẫn cho AI |
| `index/` | có | tóm tắt chương, chỉ mục khái niệm, mô tả hình (viết lại bằng lời, không trích sách) |
| `tools/` | có | render, OCR, ghép chương, cắt hình, kiểm tra, tìm kiếm (`tim.py`) |
| `KE-HOACH.md`, `book/_kiem-tra.md` | có | cách dữ liệu được tạo và kết quả kiểm tra |
| `Luat TamThuc2.pdf`, `book/`, `hinh/`, `.cache/` | **không** | nội dung sách — tạo lại bằng `tools/setup.sh` |

Không đưa file PDF, `book/`, `hinh/`, `.cache/` lên GitHub hay nơi khác.
