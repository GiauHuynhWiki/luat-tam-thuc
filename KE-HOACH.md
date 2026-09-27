# Kế hoạch: Trợ lý đọc sách *Luật Tâm Thức*

## Hướng đi (cập nhật 2026-09-23)

Bản kế hoạch đầu tiên yêu cầu Claude chép lại nguyên văn cả 440 trang. Yêu cầu đó bị từ chối, vì làm vậy là tái tạo toàn bộ một cuốn sách còn bản quyền. Hướng hiện tại tách hai lớp:

- **Lớp tìm kiếm:** chữ do máy OCR (Vision của macOS) chạy trên chính file PDF. Có lỗi dấu rải rác, nên chỉ dùng để tìm đúng trang.
- **Lớp trả lời:** khi bạn hỏi, Claude mở ảnh gốc của trang liên quan, đọc rồi giải thích, dẫn số trang, chỉ trích ngắn.

Tóm tắt chương, chỉ mục khái niệm và mô tả hình do Claude viết bằng lời của mình.

## Tổng quan

| Giai đoạn | Việc | Ai làm | Đầu ra | Trạng thái |
|---|---|---|---|---|
| 1 | OCR cả sách | Script `tools/build_book.py` | `book/*.md`, `book/00-muc-luc.md`, `book/_bao-cao.md` | Xong: đủ 440 trang, còn 263 chỗ `[?]` |
| 2 | Chỉ mục: tóm tắt chương, khái niệm, mô tả hình | Claude, Opus 5.5 · Extra | `index/tom-tat-chuong.md`, `index/chi-muc-khai-niem.md` (286 khái niệm, sinh từ `khai-niem.tsv`), `index/mo-ta-hinh.md` | Xong |
| 2b | Cắt hình minh hoạ ra file riêng | Script `tools/export_figures.py` | `hinh/NN/pNNN-K.jpg`, `hinh/danh-sach.md`, `hinh/xem-truoc.html` | Xong: 202 hình trên 163 trang |
| 3 | Skill `luat-tam-thuc` | Claude, Opus 5.5 · High | `~/ai-skills/common/luat-tam-thuc/` (`SKILL.md`, `scripts/tim.py`) | Xong, đã cài symlink; chưa commit repo ai-skills |

## Dữ liệu và công cụ hiện có

- `tools/render_pages.swift` → `tools/render_pages`: render trang PDF ra PNG (PDFKit).
- `tools/ocr_pages.swift` → `tools/ocr_pages`: OCR bằng Vision (`vi-VT`, `.accurate`, language correction).
- `tools/build_book.py`: OCR mỗi trang ở 150/220/300 DPI, bỏ phiếu từng từ (3 bản khác nhau → `từ[?]`), ghép file chương.
- `tools/chapters.json`: ranh giới 11 phần/chương và các mục con (trang PDF).
- `.cache/pages/p001.png …`: ảnh trang 150 DPI, giữ lại để xem trang gốc. Nếu bị xoá: `tools/render_pages "Luat TamThuc2.pdf" .cache/pages <từ> <đến> 150`.
- Số trang in trên sách trùng số trang PDF. Marker đầu mỗi trang: `<!-- pdf:N | sach:N -->` (`sach:?` khi trang không in số).
- Hình minh hoạ: `hinh/NN/pNNN-K.jpg` (chương NN, trang NNN, hình thứ K), cắt từ ảnh render 300 DPI. `hinh/danh-sach.md` liệt kê chương → mục → trang → file; mở `hinh/xem-truoc.html` bằng trình duyệt để xem hết. Vùng hình được tìm tự động (`tools/crop_figures.swift`: xoá vùng chữ theo OCR, gom phần mực còn lại). Sửa tay trong `tools/figure_overrides.json` (bỏ trang, hoặc ghi khung thay thế) rồi chạy `python3 tools/export_figures.py --no-detect`. Chỉ dùng cá nhân: PDF bị khoá sao chép, nên hình được cắt từ ảnh trang (như chụp màn hình), không lấy ảnh gốc trong file.
- Lỗi OCR đã biết: mất/sai dấu ("tổng" → "tống", "vẫn" → "vân", "chỉ" → "chi"), "7/7" → "717", dòng đầu của trang mở chương (có chữ cái lớn đầu đoạn) bị hỏng.

---

## Prompt 2 — Lớp chỉ mục (đặc tả cho "mục 3")

```text
Bối cảnh
- Luật Tâm Thức/book/ có chữ OCR của sách "Luật Tâm Thức" (Ngô Sa Thạch), mỗi chương một file, marker trang <!-- pdf:N | sach:N -->. book/00-muc-luc.md và tools/chapters.json là bản đồ chương.
- Chữ OCR có lỗi dấu rải rác. Khi cần chắc chắn một ý, mở ảnh gốc .cache/pages/pNNN.png.
- Mục đích: sau này khi tôi hỏi, Claude chỉ cần đọc chỉ mục (vài nghìn token) là biết mở trang nào, không phải đọc cả cuốn.
- Mọi nội dung trong index/ viết bằng lời của bạn. Không chép lại các đoạn dài của sách.

Đầu ra
1. index/tom-tat-chuong.md — mỗi chương gồm: tiêu đề, file, khoảng trang; 5–10 dòng ý chính; các khái niệm chính (tên khớp với file khái niệm); các câu hỏi mà chương này trả lời.
2. index/khai-niem.md — mỗi thuật ngữ, khái niệm, mô hình, con số hay "luật" riêng của sách là một mục:
   - ### Tên khái niệm (kèm tên gọi khác nếu có)
   - Định nghĩa theo sách: 1–3 câu, diễn đạt lại.
   - Trang chính (nơi định nghĩa/giải thích kỹ) và các trang khác có nhắc đến.
   - Khái niệm liên quan.
   Đầu file có danh mục nhóm theo chủ đề; các mục bên dưới xếp theo thứ tự chữ cái.
3. index/hinh.md — mỗi hình/sơ đồ: trang, hình về cái gì, các nhãn/số chính, hình minh hoạ cho ý nào trong sách. Mô tả bằng lời của bạn sau khi xem ảnh trang.
4. Bổ sung cột "Chủ đề chính" vào book/00-muc-luc.md.

Cách làm
- Mỗi chương giao cho một subagent (Agent tool, model opus, song song tối đa 5): đọc trọn chương, xem ảnh các trang có hình, trả về nháp tóm tắt, danh sách khái niệm kèm trang, và mô tả hình.
- Sau đó bạn tự hợp nhất: gộp khái niệm trùng, thống nhất tên gọi, nối các khái niệm liên quan xuyên chương, và dùng grep marker để kiểm tra lại mọi số trang.

Nguyên tắc
- Trung thành với cách nhìn của sách. Ở bước này không thêm kiến thức bên ngoài, không phản biện.
- Mọi số trang phải kiểm chứng được bằng grep trong book/.

Báo cáo cuối: số chương, số khái niệm, số hình, và 3 mục khái niệm mẫu.
```

---

## Prompt 3 — Tạo skill `luat-tam-thuc`

```text
Tạo skill mới luat-tam-thuc theo quy trình của skill update-shared-skill (skill nguồn ở ~/ai-skills/common/, symlink sang Claude, Codex, Gemini).

Ràng buộc quan trọng
- Repo ~/ai-skills được push lên GitHub, nên KHÔNG chép nội dung sách vào skill. Skill chỉ chứa hướng dẫn và đường dẫn tuyệt đối tới dữ liệu ở <thư mục dự án>/ (book/, index/, tools/, .cache/pages/).
- Đọc KE-HOACH.md (phần "Dữ liệu và công cụ hiện có") để biết dữ liệu nằm đâu và lỗi OCR thường gặp.
- Đọc skill tamlinh để dùng lại giọng văn: ngắn, rõ, đời thường, ấm áp, không phán xét.

Chuẩn bị
- Viết tools/tim.py: tìm từ khoá trong book/ không phân biệt dấu (bỏ dấu cả từ khoá lẫn nội dung, đ → d), trả về file, dòng, trang pdf:N gần nhất và một đoạn ngắn quanh chỗ khớp. Lỗi OCR chủ yếu là lỗi dấu, nên tìm không dấu sẽ né được phần lớn lỗi.

Nội dung SKILL.md
- Khi nào dùng: tôi hỏi về cuốn "Luật Tâm Thức" / tác giả Ngô Sa Thạch; nhắc đến một trang, chương hay khái niệm của sách; hoặc muốn liên hệ ý trong sách với kiến thức bên ngoài.
- Quy trình tra cứu:
  1. Đọc index/khai-niem.md, index/tom-tat-chuong.md (và index/hinh.md khi hỏi về hình) để định vị.
  2. Chạy tools/tim.py với từ khoá (thử cả từ đồng nghĩa), hoặc tìm marker sach:N khi tôi nói số trang.
  3. Mở ảnh gốc .cache/pages/pNNN.png của các trang liên quan (thiếu ảnh thì render bằng tools/render_pages) và đọc từ ảnh trước khi trả lời. Chữ OCR chỉ dùng để định vị. Không trả lời về nội dung sách từ trí nhớ.
  4. Nếu các trang liên quan có hình (tra hinh/danh-sach.md theo số trang): xem hình đó, dùng nó khi giải thích, và đưa tôi đường dẫn file hình (link Markdown tới hinh/NN/pNNN-K.jpg) để tôi mở xem.
- "Trang N" tôi nói là số trang in trên sách (trùng số trang PDF).
- Cách trả lời:
  - Sách nói gì (kèm trang): diễn giải lại; chỉ trích nguyên văn một câu ngắn khi thật cần.
  - Hiểu đơn giản: ví dụ đời thường.
  - Liên hệ bên ngoài (khi tôi hỏi hoặc khi thật sự giúp hiểu): nối với khoa học, Phật giáo, tâm lý học, triết học…; ghi rõ đâu là ý của sách, đâu là của nguồn ngoài.
  - Tự hỏi (tuỳ chọn): một câu để tôi tự chiêm nghiệm.
  Câu hỏi đơn giản thì trả lời ngắn, không cần đủ các phần.
- Nguyên tắc:
  - Lấy hệ quy chiếu của sách làm nền tảng; không phản biện trừ khi tôi hỏi.
  - Khi nêu kiến thức bên ngoài, trình bày đúng những gì nguồn đó nói, không gán cho khoa học hay tôn giáo điều họ không khẳng định.
  - Sách không đề cập thì nói rõ "sách không nói đến", rồi mới dùng kiến thức ngoài.
  - Không bịa số trang. Không chép lại các đoạn dài của sách.

Kiểm thử
Soạn 8 câu hỏi mẫu (2 giải thích khái niệm, 2 hỏi theo số trang, 2 liên hệ bên ngoài, 1 câu sách không đề cập, 1 so sánh hai khái niệm), chạy thử, báo kết quả, sửa skill nếu trả lời lệch yêu cầu.
```

---

## Prompt 4 — Kiểm tra chất lượng OCR (chạy ở phiên mới, Opus 5.5 · High)

```text
Bối cảnh
- Thư mục: <thư mục dự án> — repo git riêng (commit 388d260), KHÔNG có remote. Không push, không thêm remote, không commit; cuối cùng liệt kê thay đổi để tôi tự commit.
- Đọc KE-HOACH.md trước để nắm cấu trúc dữ liệu và công cụ.
- Chữ OCR trong book/ chỉ dùng để TÌM trang; skill luat-tam-thuc luôn đọc ảnh trang gốc khi trả lời. Vì vậy mục tiêu kiểm tra là: (1) có sai trang không, (2) có sót chữ không, (3) tìm kiếm có tìm ra đúng trang không, (4) ước lượng tỉ lệ lỗi. Không nhằm làm chữ hoàn hảo.

Dữ liệu
- book/NN-*.md: chữ OCR theo chương, đầu mỗi trang có marker <!-- pdf:N | sach:N -->.
- .cache/pages/pNNN.png: ảnh trang 150 DPI (một số trang khổ ngang, ví dụ 165, 176).
- .cache/ocr/pNNN.json: dòng OCR Vision lượt 150 DPI: {"lines":[{"text","conf","x","y","w","h"}]}, toạ độ chuẩn hoá 0–1, gốc trên-trái. .cache/ocr220, .cache/ocr300: hai lượt OCR còn lại (ảnh 220/300 DPI đã xoá, render lại bằng tools/render_pages nếu cần).
- hinh/_khung.json: vùng hình theo trang (x, y, w, h chuẩn hoá, gốc trên-trái).
- index/khai-niem.tsv: 286 dòng "tên khái niệm<TAB>trang (vd 10-13, 17)<TAB>ghi chú".
- tools/: build_book.py (ghép chương từ OCR), check_markers.py, ocr_pages, render_pages, crop_figures.swift (có sẵn code đọc ảnh xám và lưới mực bằng CoreGraphics, tái dùng được), page_notes.json (trang 23 in xoay ngang, trang 48 là quảng cáo của website).
- Tìm không dấu: python3 ~/ai-skills/common/luat-tam-thuc/scripts/tim.py <từ khoá> | --page N
- Python trên máy không có numpy/PIL: xử lý ảnh bằng Swift như tools/crop_figures.swift. Lưu script kiểm tra vào tools/verify_*.py|.swift để chạy lại được.

Ràng buộc
- Không gõ lại hay chép lại nguyên văn nội dung trang sách, kể cả để sửa lỗi. Chữ bị sót chỉ được bổ sung bằng cách chạy lại OCR (Vision) trên đúng vùng đó.
- Trong báo cáo không trích đoạn văn của sách; chỉ ghi số trang, số dòng, và khi cần thì cặp từ ngắn "sai → đúng".
- Không sửa index/ và không sửa build_book.py khi chưa hỏi tôi.

Phép kiểm tra
1. Sai trang: chạy tools/check_markers.py. Chọn ngẫu nhiên 20 trang, xác nhận câu đầu và câu cuối dưới marker pdf:N có trong .cache/ocr/pNNN.json của đúng trang N (không phải N±1).
2. Sót chữ:
   a. OCR → sách: mọi dòng trong .cache/ocr/pNNN.json (trừ đầu trang, số trang, watermark website) phải có trong phần chữ của trang N ở book/ (so khớp không dấu, cho phép khác nhỏ). Liệt kê các dòng bị rơi khi ghép.
   b. Ảnh → OCR: trên mỗi ảnh trang, tìm vùng có mực dạng chữ nằm ngoài mọi khung dòng OCR và ngoài vùng hình, bỏ dải đầu/chân trang. Tạo ảnh tổng hợp các trang nghi ngờ có khung đỏ, rồi mở từng trang nghi ngờ để xác nhận thật hay giả.
   Xem kỹ: trang mở chương (8, 50, 96, 164, 234, 302, 372, 422 — chữ cái lớn đầu đoạn), trang chữ trắng nền đen (7, 49, 95, 163, 233, 301, 371, 421), trang khổ ngang, chú thích dưới hình, bảng.
3. Tìm kiếm (quan trọng nhất): với mỗi khái niệm trong index/khai-niem.tsv, lấy 1–2 từ khoá đặc trưng từ tên, tìm không dấu trong book/, kiểm tra có kết quả nằm trong các trang được ghi (±1). Báo tỉ lệ tìm thấy. Mỗi ca trượt: xem ảnh trang rồi xếp loại (a) OCR sót/sai nặng, (b) chỉ mục ghi sai trang, (c) sách diễn đạt khác tên khái niệm.
4. Soát mẫu 15 trang: 5 trang chữ thường ngẫu nhiên, 2 trang mở chương, 3 trang nhiều hình/nhãn, 2 trang bảng hoặc dãy số, 1 trang khổ ngang, 2 trang nhiều [?] nhất. Mỗi trang: xem ảnh, so với chữ, đếm số dòng sót, từ sai dấu, từ sai hẳn, lỗi thứ tự dòng.

DỪNG sau phép 4: ghi báo cáo vào book/_kiem-tra.md và chờ tôi duyệt trước khi sửa.

5. Sửa (sau khi tôi duyệt): với chỗ sót chữ đã xác nhận, render lại đúng trang ở 300 DPI, cắt vùng đó, phóng to/đảo màu nếu nền tối, OCR lại bằng Vision (vi-VT, .accurate), đưa kết quả vào pipeline để build_book.py ghép lại. Sau đó chạy lại check_markers.py và phép 2a, 3.

Báo cáo book/_kiem-tra.md
- Kết luận một đoạn: dữ liệu đã đủ tốt để dùng skill chưa.
- Bảng số liệu của từng phép.
- Danh sách trang sót chữ: trang, vùng, đã sửa / chưa sửa được và lý do.
- Tỉ lệ lỗi ước lượng từ 15 trang mẫu.
- Các ca trượt tìm kiếm theo loại (a)/(b)/(c); loại (b) kèm số trang đúng đề xuất.
- Việc còn nên làm, nếu có.
```
