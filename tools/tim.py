#!/usr/bin/env python3
"""Search the local OCR text of "Luật Tâm Thức", ignoring Vietnamese diacritics.

The OCR text has scattered diacritic errors ("tổng" read as "tống") and words glued together, so
matching is done on text with diacritics removed (đ -> d), syllable-final y read as i (tỷ = tỉ),
and, only when nothing matches, whitespace ignored. Results only locate pages: read the page image
before answering.

Usage:
  tim.py <từ khoá> [<từ khoá> ...]     paragraphs containing every keyword (book/)
  tim.py --any <a> <b>                 paragraphs containing any keyword
  tim.py --index <từ khoá>             also search index/ (concepts, chapter summaries, figure notes)
  tim.py --page 41                     text of page 41 + path of its page image + its figure files
  tim.py --max 50 ...                  more results (default 20)

Data folder: $LUAT_TAM_THUC_DIR, default the folder above tools/ (this project).
"""
import argparse
import glob
import os
import re
import sys
import unicodedata

ROOT = os.environ.get("LUAT_TAM_THUC_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MARKER = re.compile(r"<!-- pdf:(\d+) \| sach:(\S+) -->")


def fold(ch):
    if ch in "đĐ":
        return "d"
    base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
    return (base or ch)[:1].lower()


FINAL_Y = re.compile(r"(?<=[bcdghklmnpqrstvx])y(?![a-z])|(?<=qu)y(?![a-z])")  # tỷ/tỉ, lý/lí, quy/qui


def fold_text(s):
    return FINAL_Y.sub("i", "".join(fold(c) for c in s))  # same length as s, so match positions map back


def prepare(s, loose):
    """Folded text plus the original index of each kept char. Loose drops whitespace: OCR sometimes
    glues words together ("thấuhiểu"), but it also lets keys match across word boundaries."""
    folded = fold_text(s)
    idx = [i for i, c in enumerate(folded) if not (loose and c.isspace())]
    return "".join(folded[i] for i in idx), idx


def book_files():
    return sorted(f for f in glob.glob(os.path.join(ROOT, "book", "*.md"))
                  if not os.path.basename(f).startswith(("_", "00-muc-luc")))


def figure_files(page):
    return sorted(glob.glob(os.path.join(ROOT, "hinh", "*", f"p{page:03d}-*.jpg")))


def snippet(text, start, end, width=90):
    a, b = max(0, start - width), min(len(text), end + width)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


def search(files, terms, any_mode, limit, track_pages, loose=False):
    keys = [k for k in (prepare(t, loose)[0].strip() for t in terms) if k]
    if not keys:
        return 0
    hits = 0
    for path in files:
        page = None
        with open(path, encoding="utf-8") as f:
            for no, line in enumerate(f, 1):
                m = MARKER.search(line)
                if m:
                    page = int(m.group(1))
                    continue
                low, idx = prepare(line, loose)
                found = [low.find(k) for k in keys]
                ok = any(i >= 0 for i in found) if any_mode else all(i >= 0 for i in found)
                if not ok:
                    continue
                i = min(x for x in found if x >= 0)
                k = keys[found.index(i)]
                start, end = idx[i], idx[i + len(k) - 1] + 1
                where = f"tr. {page}" if track_pages and page else os.path.basename(path)
                print(f"{os.path.relpath(path, ROOT)}:{no}  [{where}]  {snippet(line.rstrip(), start, end)}")
                hits += 1
                if hits >= limit:
                    print(f"… dừng ở {limit} kết quả (dùng --max để xem thêm)")
                    return hits
    return hits


def show_page(page):
    for path in book_files():
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        start = next((i for i, l in enumerate(lines) if (m := MARKER.search(l)) and int(m.group(1)) == page), None)
        if start is None:
            continue
        end = next((i for i in range(start + 1, len(lines)) if MARKER.search(lines[i])), len(lines))
        print(f"# {os.path.relpath(path, ROOT)}:{start + 1}  {lines[start].strip()}")
        print("".join(lines[start + 1:end]).strip())
        break
    else:
        print(f"Không thấy trang {page} trong book/")
    img = os.path.join(ROOT, ".cache", "pages", f"p{page:03d}.png")
    print(f"\nẢnh trang: {img}" + ("" if os.path.exists(img) else
          f"  (chưa có — render: {ROOT}/tools/render_pages \"{ROOT}/Luat TamThuc2.pdf\" {ROOT}/.cache/pages {page} {page} 150)"))
    figs = figure_files(page)
    print("Hình trên trang: " + (", ".join(figs) if figs else "không có"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("terms", nargs="*")
    ap.add_argument("--any", action="store_true")
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--page", type=int)
    ap.add_argument("--max", type=int, default=20)
    a = ap.parse_intermixed_args()  # flags may come after the keywords
    if not os.path.isdir(os.path.join(ROOT, "book")):
        sys.exit(f"Không thấy dữ liệu sách ở {ROOT} (đặt LUAT_TAM_THUC_DIR)")
    if a.page:
        show_page(a.page)
        return
    if not a.terms:
        ap.error("cần từ khoá hoặc --page")
    idx = sorted(glob.glob(os.path.join(ROOT, "index", "*.md"))) if a.index else []

    def run(loose):
        hits = search(idx, a.terms, a.any, a.max, track_pages=False, loose=loose) if idx else 0
        return hits + search(book_files(), a.terms, a.any, a.max, track_pages=True, loose=loose)

    hits = run(loose=False)
    if not hits:
        print("(Không khớp đúng từ; thử lại bỏ qua khoảng trắng — có thể khớp nhầm qua ranh giới từ)")
        hits = run(loose=True)
    if not hits:
        print("Không có kết quả. Thử từ đồng nghĩa, bớt từ khoá, hoặc --any / --index.")


if __name__ == "__main__":
    main()
