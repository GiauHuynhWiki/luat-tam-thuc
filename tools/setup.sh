#!/bin/bash
# Tạo lại dữ liệu sách từ file PDF: ảnh trang (.cache/pages), chữ OCR (book/), hình (hinh/).
# Cần: macOS (PDFKit + Vision có tiếng Việt), Xcode Command Line Tools (swiftc), python3,
# và file "Luat TamThuc2.pdf" đặt ở thư mục gốc dự án.
# Chạy: bash tools/setup.sh        (mất khoảng vài chục phút: 440 trang × 3 lượt OCR)
set -euo pipefail
cd "$(dirname "$0")/.."

PDF="Luat TamThuc2.pdf"
# Bản scan mà bộ công cụ được chỉnh theo (440 trang). Bản khác có thể lệch số trang → sửa tools/chapters.json.
EXPECTED_SHA256="f0f64b13c2a22427539923007ab32632e5a02980545fbe7a00164510af27c256"

[ "$(uname)" = "Darwin" ] || { echo "Cần macOS (công cụ dùng PDFKit và Vision của Apple)."; exit 1; }
[ -f "$PDF" ] || { echo "Thiếu file '$PDF' ở thư mục gốc dự án ($(pwd))."; exit 1; }
command -v swiftc >/dev/null || { echo "Thiếu swiftc. Cài bằng: xcode-select --install"; exit 1; }
command -v python3 >/dev/null || { echo "Thiếu python3."; exit 1; }

if [ "$(shasum -a 256 "$PDF" | cut -d' ' -f1)" != "$EXPECTED_SHA256" ]; then
  echo "Cảnh báo: '$PDF' không phải đúng bản PDF mà dự án dùng. Số trang trong index/ có thể lệch."
  read -r -p "Vẫn tiếp tục? [y/N] " ok
  [ "$ok" = "y" ] || exit 1
fi

echo "== Biên dịch công cụ"
for t in render_pages ocr_pages crop_figures; do
  swiftc -O "tools/$t.swift" -o "tools/$t"
done

echo "== Render + OCR 3 lượt + ghép chương vào book/"
python3 tools/build_book.py

echo "== Kiểm tra đủ trang 1–440"
python3 tools/check_markers.py

echo "== Cắt hình vào hinh/"
python3 tools/export_figures.py

# Ảnh 220/300 DPI chỉ dùng cho OCR; kết quả OCR đã lưu trong .cache/ocr*, nên xoá cho nhẹ.
rm -rf .cache/pages220 .cache/pages300

echo "Xong. Mở Claude Code, Codex hoặc Gemini CLI trong thư mục này rồi hỏi về sách."
