"""Shared helpers for the tools/verify_*.py quality checks (read-only over book/ and .cache/)."""
import difflib
import glob
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_book as bb  # noqa: E402  (only its helpers are used: header / watermark / page-number rules)

MARKER = re.compile(r"<!-- pdf:(\d+) \| sach:(\d+|\?) -->")
NOTE = re.compile(r"^> \[(Ghi chú|Trang không có chữ)[^\]]*\]\s*$")
FIG_PREFIX = re.compile(r"> \[Hình — xem ảnh trang \d+\.(?: Chữ/số đọc được trong hình:)?")


def fold(s):
    """Lower case, no diacritics, đ -> d; keeps spaces (same folding as the skill's tim.py)."""
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm(s):
    """fold() then letters/digits only."""
    return re.sub(r"[^a-z0-9]", "", fold(s))


def book_files():
    return sorted(f for f in glob.glob(os.path.join(ROOT, "book", "[0-9][0-9]-*.md"))
                  if not os.path.basename(f).startswith("00-muc-luc"))


def book_pages():
    """{pdf page: text of that page in book/} with markers, notes and figure boilerplate removed.
    Text before the first marker of a file (the chapter title) goes to that file's first page."""
    pages, pre = {}, ""
    for path in book_files():
        cur, buf = None, []
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = MARKER.search(line)
                if m:
                    if cur is not None:
                        pages[cur] = "".join(buf)
                    elif buf:
                        pre = "".join(buf)
                    cur, buf = int(m.group(1)), ([pre] if pre else [])
                    pre = ""
                    continue
                if NOTE.match(line):
                    continue
                line = FIG_PREFIX.sub("", line).replace("[?]", "").replace("```text", "").replace("```", "")
                buf.append(line)
        if cur is not None:
            pages[cur] = "".join(buf)
    return pages


def ocr_lines(n, ocr_dir=".cache/ocr", raw=False):
    """Lines of one OCR pass as build_book.py sees them: with the tools/ocr_fix/ regions applied
    (raw=True: the cached Vision output as is)."""
    path = os.path.join(ROOT, ocr_dir, f"p{n:03d}.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        lines = json.load(f)["lines"]
    if not raw:
        lines = bb.apply_fixes(lines, n)
    return [l for l in lines if l["text"].strip()]


def is_furniture(l):
    """Running head, page number or the scan site's watermark: dropped on purpose by build_book."""
    t = l["text"].strip()
    if bb.is_watermark(t):
        return True
    if l["y"] < 0.07 and any(bb.similar(t, h) > 0.75 for h in bb.HEADERS):
        return True
    return bb.page_number(l) is not None


def coverage(needle, hay):
    """Share of the characters of `needle` found, in order, in `hay` around the best local alignment.
    Both are norm()'d strings. 1.0 = present verbatim."""
    if not needle:
        return 1.0
    if needle in hay:
        return 1.0
    # restrict to the window of hay that matches the needle best, then count matched characters
    sm = difflib.SequenceMatcher(None, needle, hay, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 3]
    if not blocks:
        return 0.0
    best = 0.0
    L = len(needle)
    for b in blocks:
        start = max(0, b.b - b.a - 5)
        win = hay[start:start + L + 10]
        m = sum(x.size for x in difflib.SequenceMatcher(None, needle, win, autojunk=False).get_matching_blocks())
        best = max(best, m / L)
        if best >= 0.999:
            break
    return best
