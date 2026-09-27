# Kiểm tra chất lượng OCR (phép 1–5)

Ngày 2026-09-23. Phép 1–4 đo trên dữ liệu **trước khi sửa**. Phép 5 làm sau khi bạn duyệt cách (A): OCR lại 10 trang, lưu vào `tools/ocr_fix/`, build lại book/, sửa chỉ mục #63. Các số liệu sau khi sửa nằm ở cột "Sau sửa" và ở mục [Phép 5](#phép-5-sửa-đã-làm).

## Kết luận

Dữ liệu **đã đủ tốt để dùng skill `luat-tam-thuc`**. Không trang nào bị gán sai (440/440 marker đúng, 20/20 trang mẫu khớp đúng trang N, không phải N±1). Khi ghép chương không rơi dòng nào (0/12.047 dòng OCR). Tìm không dấu ra đúng trang cho 282/286 khái niệm trong chỉ mục (98,6%). 4 ca trượt đều do chỉ mục đặt tên khác chữ trong sách, không do OCR. Ở trang chữ thường, lỗi gần như chỉ là sai dấu (~1% số từ), mà tìm không dấu thì bỏ qua dấu. Số từ sai chữ cái là 0 trên 5 trang mẫu. Lỗi thật dồn vào vài chỗ: **2 dòng đầu của cả 8 trang mở chương** (chữ cái lớn đầu đoạn): trang 302 và 372 mất hẳn dòng 2, trang 422 mất một phần, các trang còn lại sai chữ hoặc đảo thứ tự. Ngoài ra còn **chú thích cuối trang 87**, **nhãn trong hình** (bị tách, xoay, ký hiệu σ/μ đọc sai) và một dòng cuối trang 154. Skill luôn đọc ảnh trang khi trả lời, nên các lỗi này chỉ làm khó *tìm* đúng trang cho vài cụm từ, không làm sai câu trả lời. Nên sửa 8 trang mở chương và trang 87 (phép 5): ít việc mà bịt được chỗ sót chữ duy nhất trong phần chữ chính.

**Sau phép 5:** 8 trang mở chương, chú thích trang 87 và dòng cuối trang 154 đã được OCR lại từ ảnh 300 DPI và đọc đúng. Phần chữ chính của sách **không còn chỗ sót chữ nào đã biết**. Phép tìm bằng cụm từ đọc từ ảnh tăng từ 22/30 lên 26/30; 4 ca còn trượt đều là nhãn trong hình.

## Bảng tổng hợp

| Phép | Nội dung | Trước khi sửa | Sau sửa |
|---|---|---|---|
| 1 | `tools/check_markers.py` | 440/440 marker, không trùng, đúng thứ tự: OK | OK |
| 1 | 20 trang ngẫu nhiên (seed 2026): dòng đầu và dòng cuối dưới `pdf:N` nằm trong `.cache/ocr/pNNN.json` của trang N | 20/20 đúng; trang N luôn khớp hơn N±1 | 20/20 |
| 2a | Dòng OCR lượt 150 DPI (trừ đầu trang, số trang, watermark) có trong chữ trang N của book/ | 12.047 dòng; 0 dòng rơi (chi tiết bên dưới) | 12.050 dòng (tính cả dòng OCR lại); 0 dòng rơi |
| 2c | (bổ sung) Dòng lượt 300 DPI, được lượt 220 DPI xác nhận, không có trong book/ | 1 dòng: chú thích cuối trang 87 | 0 |
| 2b | Mực ngoài mọi khung dòng OCR và ngoài vùng hình, đã bỏ dải đầu/chân trang | 29 trang, 39 vùng; thật: 2 trang (8, 435); còn lại là giả | Trang 8 đã sửa; 435 để nguyên |
| 2b+ | Soát tay 8 trang mở chương, 8 trang chữ trắng nền đen, 4 trang khổ ngang, chú thích dưới hình, bảng | Mở chương: 8/8 hỏng 2 dòng đầu (3 trang mất chữ); nền đen, khổ ngang: đủ chữ | 8/8 trang mở chương đúng chữ, đúng thứ tự |
| 3 | 286 khái niệm trong `index/khai-niem.tsv`: tìm không dấu, có kết quả trong các trang được ghi (±1) | **282/286 (98,6%)**; 4 trượt đều loại (c) | 282/286 (4 ca (c) giữ nguyên) |
| 3+ | (bổ sung) Từng đoạn trang trong chỉ mục | 340/355 có kết quả; 15 đoạn trượt: 1 (b), 1 (a) nhẹ, 13 (c) | 340/354 (đã bỏ đoạn (b)); còn 1 (a) nhẹ, 13 (c) |
| 3+ | (bổ sung, độc lập) 30 cụm từ ngắn đọc từ **ảnh** 15 trang mẫu | 22/30; trang chữ thường 10/10; 8 trượt đều ở vùng yếu | **26/30**; 4 trượt đều là nhãn hình |
| 4 | Soát tay 15 trang (4.503 từ) | Sai dấu 1,4%, sai chữ 0,9%, thiếu ~0,6% từ | Sai dấu 1,4%, sai chữ 0,4%, thiếu ~0,04% (1 nhãn hình) |

## Phép 1: gán trang

Mẫu (seed 2026): 61, 72, 130, 182, 236, 272, 278, 283, 303, 307, 316, 330, 341, 354, 400, 410, 419, 422, 424, 428. Cả 20 trang, dòng đầu và dòng cuối đều khớp 1,00 với OCR của đúng trang N. Riêng dòng cuối trang 354 khớp 0,80 vì bố cục hai cột làm hai từ đứng xa nhau, nhưng vẫn là trang 354. Không trang nào khớp N±1 tốt hơn.

## Phép 2: sót chữ

### 2a. OCR → sách

0 dòng rơi khi ghép. Ở ngưỡng 0,8 có 2 dòng bị gắn cờ: trang 70 dòng 4 và trang 209 dòng 11. Cả hai là nhãn hình 2–3 ký tự bị bước bỏ phiếu đổi một ký tự. Ở ngưỡng chặt 0,95 có thêm 6 dòng (trang 1, 76, 132 ×2, 348, 395): mỗi dòng khác 1–3 ký tự so với book/, cũng do bỏ phiếu đổi từ, không mất chữ.

Hạn chế: 2a chỉ so lượt 150 DPI (lượt quyết định bố cục) với book/. Chỗ lượt 150 DPI đọc sai từ đầu thì 2a không thấy. Phép 2c bù phần này bằng hai lượt còn lại và chỉ tìm thêm được chú thích trang 87.

### 2b. Ảnh → OCR

`tools/verify_ink scan` xoá khung các dòng OCR và vùng hình khỏi ảnh 150 DPI, bỏ dải trên 6,5% và dưới 6,5%, tự đảo màu trang nền tối, rồi gom phần mực còn lại. Ảnh tổng hợp (khung đỏ): `.cache/verify/tong-hop-01.png`, `-02.png`. Ảnh phóng to từng vùng: `.cache/verify/phong-to-01…03.png`. Đã xem từng vùng:

| Loại | Trang | Kết luận |
|---|---|---|
| Chữ cái lớn đầu chương không được OCR, cùng phần cuối 2 từ ở cuối dòng | 8 | **Thật** |
| Số trang của chương 01 trong mục lục in | 435 | **Thật**, thiếu 1 số |
| Biểu tượng đầu mục (vòng tròn, khối đa diện) | 32, 33 (×3), 99, 137, 138, 140, 141, 150, 247, 279, 374, 410 | Giả |
| Viền đen trang tựa chương, trang nền tối bị đảo màu | 7, 49, 62, 95, 163, 233 | Giả |
| Số trang in xoay | 23, 165 | Giả |
| Nét hình thò ra ngoài khung hình, đốm bẩn | 45, 106, 261, 370, 440 | Giả |
| Logo, quảng cáo của website | 3, 48 | Giả (không thuộc sách) |

Phương pháp này **không thấy** chỗ sót nằm *bên trong* một khung OCR. Ở trang mở chương, Vision vẽ một khung cao gộp hai dòng cạnh chữ cái lớn, nên dòng 2 bị mất mà mực vẫn nằm trong khung. Vì vậy đã soát tay riêng các trang cần xem kỹ:

- **Trang mở chương** (8, 50, 96, 164, 234, 302, 372, 422): cả 8 trang hỏng 2 dòng đầu.
  - 302: mất hẳn dòng 2 (~11 từ); dòng 1 sai gần hết. Cả ba lượt OCR đều gộp hai dòng.
  - 372: mất hẳn dòng 2 (~11 từ); dòng 1 sai 6/10 từ. Lượt 300 DPI có đủ hai dòng, chỉ hỏng chữ cái đầu.
  - 422: mất ~7 từ ở cuối dòng 1 và đầu dòng 2; phần còn lại sai nhiều. Lượt 220 DPI đọc gần đúng.
  - 8: chữ cái lớn thành hai chữ số, thêm 3 từ sai chữ (vd "đắn → đắm").
  - 96: dòng 1 sai nhiều từ (lượt 220 DPI đọc đúng).
  - 50, 164, 234: đủ chữ nhưng hai dòng bị gộp thành khối `text`, **thứ tự dòng 1–2 bị đảo**; trang 164 còn dính chữ cái lớn vào đầu dòng 2.
- **Trang chữ trắng nền đen** (7, 49, 95, 163, 233, 301, 371, 421): đủ tên chương ở cả ba lượt, và tên chương có trong tiêu đề `#` của file chương. Không sót.
- **Trang khổ ngang** (23, 165, 176, 370): 165 và 176 đủ nhãn (đã soát tay). Dòng đầu trang in xoay bị lẫn vào khối nhãn, và một hàng nhãn đứng sai thứ tự. Trang 23 đã có ghi chú trong `page_notes.json`.
- **Chú thích cuối trang**: 7 trang có chữ nhỏ ở cuối trang (14, 37, 87, 111, 254, 302, 329). Chỉ trang 87 hỏng: dòng 1 sai phần lớn, dòng 2 gần như mất, cả hai bị nối vào đoạn văn cuối trang.
- **Chú thích dưới hình, bảng, dãy số**: đủ chữ trên các trang đã soát (39, 143, 153, 154, 176, 264, 398). Trang 286 thiếu một nhãn lặp lại trong hình, và phần chú thích in nghiêng cạnh hình bị xen kẽ từng dòng với nhãn hình.

## Danh sách trang sót chữ

| Trang | Vùng (toạ độ chuẩn hoá, gốc trên-trái) | Sót | Trạng thái |
|---|---|---|---|
| 302 | dòng 1–2 cạnh chữ cái lớn, y ≈ 0,15–0,21 | mất dòng 2, dòng 1 sai nặng | **Đã sửa** (phép 5) |
| 372 | dòng 1–2 cạnh chữ cái lớn, y ≈ 0,15–0,21 | mất dòng 2, dòng 1 sai nặng | **Đã sửa** |
| 422 | dòng 1–2 cạnh chữ cái lớn, y ≈ 0,15–0,20 | mất ~7 từ, còn lại sai nhiều | **Đã sửa** |
| 8 | chữ cái lớn và dòng 1–2, y ≈ 0,15–0,21 | chữ cái lớn và 3 từ | **Đã sửa** |
| 87 | chú thích cuối trang, y ≈ 0,88–0,93 | dòng 2 gần như mất, dòng 1 sai | **Đã sửa**; còn mất chỉ số mũ ² trong công thức (Vision không đọc chỉ số trên), và chú thích vẫn nối vào đoạn cuối trang |
| 435 | số trang chương 01 trong mục lục, x ≈ 0,85, y ≈ 0,34 | 1 số | Chưa sửa, không đáng sửa (mục lục có sẵn trong `00-muc-luc.md`) |
| 286 | nhãn vòng dưới của hình, trong vùng hình | 1 nhãn 2 từ | Chưa sửa: nằm trong hình, skill xem ảnh |
| 96, 50, 164, 234 | dòng 1–2 cạnh chữ cái lớn | không sót, nhưng sai chữ hoặc đảo thứ tự | **Đã sửa** |
| 154 | dòng chữ cuối trước hình, y ≈ 0,35 | không sót, 4 từ sai nặng (Vision tin cậy thấp) | **Đã sửa** |

## Phép 3: tìm kiếm

`tools/verify_search.py` lấy từ khoá từ tên khái niệm theo luật cố định: tên đầu tiên (trước "/" và "("), và tên trong ngoặc hoặc tên sau "/". Có 26/286 khái niệm có tên là một câu mô tả; với những khái niệm này, từ khoá được chọn tay trong `tools/verify_search_keys.tsv`, vẫn chỉ gồm các từ của tên. Tìm không dấu theo nguyên từ trong từng đoạn. Đoạn văn vắt qua hai trang được tính cho cả hai trang.

**Kết quả: 282/286 = 98,6%.** Lưu ý: chỉ mục được soạn từ chính chữ OCR, nên phép này phần nào tự khớp với chính nó. Phép tìm độc lập bằng cụm từ đọc từ ảnh ở cuối mục này bù cho điểm đó.

### Ca trượt theo khái niệm (4)

| # | Khái niệm | Trang ghi | Loại | Ghi chú |
|---|---|---|---|---|
| 116 | Năm vị | 138–146 | (c) | Sách nêu từng vị riêng, không có cụm "năm vị". Tìm "vi chua", "vi dang" thì ra 138, 139, 143, 145 |
| 117 | Cảm xúc và tạng phủ | 138–144 | (c) | Sách không dùng "tạng phủ" mà dùng "nội tạng" và tên từng cơ quan; "cam xuc" có ở 138, 140, 144 |
| 123 | Tỉ lệ dưỡng chất | 153 | (c) | Sách in "tỷ lệ", chỉ mục ghi "tỉ lệ": tìm không dấu vẫn phân biệt y/i. Tìm "ty le" ra 153 |
| 252 | Nhận diện bài học qua cảm xúc | 376–377 | (c) | Trang 376–377 dùng "cảm thấy", "bài học của bạn", không có "cảm xúc" |

Loại (a) OCR sót/sai nặng: 0. Loại (b) chỉ mục ghi sai trang: 0 (ở mức khái niệm).

### Ca trượt theo đoạn trang (bổ sung)

Xét từng đoạn trang của chỉ mục (vd "36-37" trong "11-12, 15-21, 36-37, 41"): 15/355 đoạn không có kết quả. Trong đó 4 đoạn là 4 khái niệm ở trên; 11 đoạn còn lại:

| # | Khái niệm | Đoạn trượt | Loại | Đề xuất / ghi chú |
|---|---|---|---|---|
| 63 | Thế giới song song | 67 | **(b)** | Trang 67 nói về mẫu hình rung động và lực hấp dẫn. Cụm này có ở 77, 80, 83, 84 (nhắc thêm ở 53). **Đã sửa thành "77-84"** trong `index/khai-niem.tsv`, đã chạy `build_index.py` |
| 62 | Dãy Fibonacci | 55 | (a) nhẹ | Sách có cụm này ở trang 55, nhưng OCR dính hai từ ("ốcFibonacci"). `tim.py` so chuỗi con nên vẫn tìm ra trang 55 |
| 8 | Vô cực sinh Thái cực | 13 | (c) | Trang 13 có nhãn hình "vô cực, thái cực", không có chữ "sinh" |
| 95 | Luân xa con mắt thứ ba | 118 | (c) | Trang 118 gọi là "luân xa số 6" |
| 106 | Kinh lạc / 12 kinh | 132–133 | (c) | Trang 132–133 liệt kê tên từng kinh |
| 212 | Trải nghiệm ngoài thân thể | 308 | (c) | Trang 308 dùng "thoát xác" |
| 214 | Thôi miên hồi quy | 322–324, 339–341 | (c) | Hai đoạn này dùng "ca thôi miên" |
| 215 | Tiền kiếp | 322–324, 346–347 | (c) | Dùng "kiếp sống trước", "kiếp sống" |
| 217 | Đường hầm ánh sáng | 305 | (c) | Hai từ đứng cách nhau trong câu |

### Tìm độc lập bằng cụm từ đọc từ ảnh (bổ sung)

`tools/verify_spot.py` và `tools/verify_spot_queries.tsv` dùng 30 cụm 1–5 từ, lấy 2 cụm trên mỗi trang mẫu của phép 4, đọc từ ảnh chứ không lấy từ OCR. Kết quả 22/30. Cả 10/10 cụm ở trang chữ thường đều tìm ra. 8 ca trượt đều ở vùng đã biết là yếu:

- Dòng 1 các trang mở chương 8 và 372; dòng 2 bị mất ở trang 372.
- Nhãn hình bị tách ở trang 143, hoặc đọc sai ở trang 286 (2 cụm) và 398.
- Chú thích cuối trang 87.

Sau phép 5: 26/30. Các cụm ở trang 8, 372 và chú thích trang 87 đều tìm ra. Còn 4 ca trượt, đều là nhãn trong hình: trang 143 (nhãn bị tách), trang 286 (2 cụm) và 398 (nhãn đọc sai).

## Phép 4: soát mẫu 15 trang

Cách đếm: so ảnh trang 150 DPI với chữ trong book/. **Sai dấu** = đúng chữ cái nhưng sai hoặc mất dấu (tìm không dấu vẫn ra). **Sai chữ** = sai cả chữ cái, gồm ký hiệu σ/μ đọc thành chữ hoặc số (tìm không dấu không ra). **Rác** = ký tự thừa như "•", "-", dòng đầu trang lẫn vào. **Thứ tự** = dòng hoặc nhãn bị đảo hay bị tách rời. Lỗi in sẵn trong sách thì không tính.

| Trang | Loại | Số từ | Dòng sót | Sai dấu | Sai chữ | Rác | Thứ tự |
|---|---|---|---|---|---|---|---|
| 104 | chữ thường | 432 | 0 | 11 | 0 | 2 | 0 |
| 194 | chữ thường | 329 | 0 | 1 | 0 | 0 | 0 |
| 255 | chữ thường | 403 | 0 | 2 | 0 | 0 | 0 |
| 259 | chữ thường | 424 | 0 | 3 | 0 | 0 | 0 |
| 319 | chữ thường | 380 | 0 | 4 | 0 | 0 | 0 |
| 8 | mở chương | 331 | 0 (chữ cái lớn tính vào sai chữ) | 2 | 4 | 2 | 0 |
| 372 | mở chương | 336 | 1 (~11 từ) | 6 | 6 | 1 | 0 |
| 398 | hình + nhãn | 324 | 0 | 8 | 2 | 1 | 0 |
| 143 | hình + nhãn | 59 | 0 | 1 | 0 | 1 | 8 nhãn bị tách |
| 264 | hình + nhãn | 308 | 0 | 2 | 11 (σ, μ) | 1 | 0 |
| 39 | dãy số | 263 | 0 | 2 | 1 | 0 | 0 |
| 154 | bảng số + hình | 168 | 0 | 1 | 4 | 1 | 0 |
| 176 | khổ ngang | 73 | 0 | 0 | 0 | 3 | 1 |
| 87 | nhiều [?] | 391 | 1 (chú thích) | 10 | 11 | 0 | 1 |
| 286 | nhiều [?] | 282 | 1 nhãn | 11 | 3 | 2 | 1 |
| **Tổng** | | **4.503** | **3 (~26 từ)** | **64 (1,4%)** | **42 (0,9%)** | **14** | **11** |

Tỉ lệ theo nhóm:

| Nhóm | Số từ | Sai dấu | Sai chữ | Thiếu |
|---|---|---|---|---|
| Chữ thường (5 trang) | 1.968 | 1,1% | 0% | 0% |
| Mở chương (2) | 667 | 1,2% | 1,5% | 1,6% |
| Hình, nhãn (3) | 691 | 1,6% | 1,9% (chủ yếu ký hiệu) | 0% |
| Bảng, dãy số (2) | 431 | 0,7% | 1,2% | 0% |
| Khổ ngang (1) | 73 | 0% | 0% | 0% |
| Nhiều [?] (2) | 673 | 3,1% | 2,1% | ~2% |

**Sau phép 5** (đếm lại trên cùng 15 trang; số từ giữ như lần đếm trước):

| Trang | Dòng sót | Sai dấu | Sai chữ | Rác | Thứ tự |
|---|---|---|---|---|---|
| 8 | 0 | 1 | 1 | 1 | 0 |
| 372 | 0 | 5 | 0 | 1 | 0 |
| 87 | 0 | 10 | 1 (mất chỉ số ²) | 0 | 1 (chú thích nối vào đoạn cuối trang) |
| 154 | 0 | 1 | 0 | 1 | 0 |
| 11 trang còn lại | không đổi | | | | |
| **Tổng** | **1 nhãn (~2 từ, trang 286)** | **62 (1,4%)** | **19 (0,4%)** | **13** | **11** |

Theo nhóm, sau sửa: mở chương sai dấu 0,9%, sai chữ 0,15%, thiếu 0%. Bảng và dãy số: sai chữ 0,2%. Nhóm nhiều [?]: sai chữ 0,6%, thiếu ~0,3% (chỉ còn nhãn trang 286). Nhóm chữ thường, hình và khổ ngang không đổi.

**Ước lượng cả sách:** 10/15 trang mẫu được chọn vì khó, nên tỉ lệ chung ở trên cao hơn thực tế. Phần lớn sách là chữ thường, kể cả phần chữ trên các trang có hình. Ước lượng: sai dấu khoảng 1–1,5% số từ; sai chữ khoảng 0,2–0,4% số từ, dồn vào 8 trang mở chương, nhãn hình, ký hiệu toán và chú thích cuối trang; sót chữ chỉ ở các chỗ trong danh sách trên, khoảng 40 từ trên cả sách. Sau phép 5, sai chữ trong phần chữ chính còn khoảng 0,1–0,2%, dồn vào nhãn hình và ký hiệu toán; sót chữ chỉ còn 1 nhãn hình (trang 286) và 1 số trong mục lục in (trang 435). Lỗi dấu hay gặp: dấu hỏi thành dấu sắc ("thể → thế", "để → đế", "tổng → tống"), "rối → rõi", "chỉ → chi", "nồng → nông". Tìm không dấu đều bỏ qua các lỗi này.

## Phép 5: sửa (đã làm)

Làm theo cách (A) bạn đã duyệt. Dòng OCR lại được lưu trong thư mục có track git `tools/ocr_fix/`, không để trong `.cache/`.

- **`tools/ocr_region.swift`**, biên dịch ra `tools/ocr_region` và đã gitignore.
  - `ocr`: cắt một vùng, phóng to, có thể đảo màu, rồi OCR bằng Vision (vi-VT, .accurate). Toạ độ trả về theo cả trang.
  - `dropcap-ocr`:
    - Tìm chữ cái lớn đầu đoạn (khối mực cao nhất) và hai dải dòng bên cạnh.
    - Xoá chữ cái lớn khỏi dải dòng, gồm cả viền xám mờ quanh nó.
    - Thu nhỏ chữ cái lớn bằng cỡ chữ hoa của dòng, rồi đặt lại ngay trước chữ đầu dòng 1, để Vision đọc trọn từ đầu tiên.
    - Chữ đó vẫn do Vision đọc, không gõ tay.
- **`tools/ocr_fix.py`**:
  - Đọc danh sách vùng `tools/ocr_fix/regions.json`, render trang 300 DPI vào `.cache/pages300` nếu thiếu, gọi `ocr_region`.
  - Ghi `tools/ocr_fix/pNNN.json`, gồm vùng thay thế `replace` và các dòng mới.
  - Hai dòng cạnh chữ cái lớn được gán cùng toạ độ x, để `build_book.py` giữ chúng trong một đoạn.
  - Trang 372 dùng `cap_keep: 0.8`: nét phải của chữ X chạm vào chữ đầu dòng 2, nên chỉ coi 80% bên trái là chữ cái lớn.
- **`tools/build_book.py`**:
  - Hàm mới `apply_fixes()`: với ba lượt OCR đầy đủ, bỏ các dòng có tâm nằm trong vùng `replace`, thay bằng dòng mới.
  - Ba lượt nhận cùng dòng, nên bước bỏ phiếu giữ nguyên chúng. Các lượt chỉ đọc chân trang không bị đụng tới.
  - `_bao-cao.md` có thêm dòng liệt kê các trang có vùng OCR lại.
  - Đã kiểm tra: mỗi vùng chỉ xoá đúng 1–2 dòng hỏng ở mỗi lượt; build lại chỉ đổi 10 trang này.
- **`tools/verify_common.py`**: `ocr_lines()` giờ áp dòng sửa như `build_book.py`; dùng `raw=True` để đọc cache gốc.

Kết quả sau khi sửa:

| Trang | Trước | Sau |
|---|---|---|
| 8 | chữ cái lớn thành hai chữ số, 3 từ sai | đúng cả hai dòng |
| 50, 164, 234 | đảo thứ tự dòng 1–2, khối `text` | đúng chữ, đúng thứ tự, liền đoạn |
| 96 | dòng 1 sai nhiều | đúng |
| 302, 372 | mất dòng 2, dòng 1 sai nặng | đủ và đúng cả hai dòng |
| 422 | mất ~7 từ | đủ và đúng |
| 87 | chú thích sai và mất dòng 2 | đủ hai dòng, chỉ mất chỉ số ² |
| 154 | 4 từ sai nặng | đúng |

`_bao-cao.md` sau khi build lại: số từ `[?]` giảm từ 215 xuống 197, dòng tin cậy thấp từ 49 xuống 47, từ không phải âm tiết hợp lệ từ 112 xuống 105. Đã chạy lại `check_markers.py --report` (OK), phép 2a/2c, phép 3 và phép tìm cụm từ từ ảnh (số liệu ở bảng tổng hợp).

## Việc còn nên làm

1. **`tim.py` của skill:** phiên khác đang làm. Đề xuất từ lần kiểm tra này: coi "y" và "i" cuối âm tiết là một khi tìm (tỷ/tỉ, lý/lí, kỹ/kĩ, mỹ/mĩ); thêm chế độ bỏ khoảng trắng khi so, để bắt từ OCR dính liền (trang 55).
2. **Chỉ mục, tuỳ chọn:** thêm tên gọi khác cho các ca (c): #117 "nội tạng", #123 "tỷ lệ", #212 "thoát xác", #95 "luân xa số 6".
3. **Nhãn hình** (bị tách, xoay, ký hiệu σ/μ), nhãn thiếu ở trang 286, số trang thiếu trong mục lục trang 435: không cần sửa, vì skill xem ảnh và `index/mo-ta-hinh.md` đã mô tả hình. Nếu muốn, thêm vùng `block` vào `tools/ocr_fix/regions.json` rồi chạy lại `ocr_fix.py` và `build_book.py`.

## Chạy lại

```bash
swiftc -O tools/ocr_region.swift -o tools/ocr_region
python3 tools/ocr_fix.py                                                # phép 5: ghi tools/ocr_fix/pNNN.json
python3 tools/build_book.py
python3 tools/check_markers.py --report
python3 tools/verify_pages.py --json .cache/verify/pages.json          # phép 1, 2a, 2c
swiftc -O tools/verify_ink.swift -o tools/verify_ink
tools/verify_ink scan .cache/pages .cache/ocr hinh/_khung.json 1 440 .cache/verify/ink.json   # phép 2b
tools/verify_ink sheet .cache/pages .cache/verify/ink.json .cache/verify/tong-hop- 6 3
tools/verify_ink zoom  .cache/pages .cache/verify/ink.json .cache/verify/phong-to- 14
python3 tools/verify_search.py --json .cache/verify/search.json         # phép 3
python3 tools/verify_spot.py                                            # tìm cụm từ đọc từ ảnh
```
