#!/usr/bin/env python3
"""Build index/chi-muc-khai-niem.md from index/khai-niem.tsv (term<TAB>pages<TAB>note).

Sorted in Vietnamese alphabetical order, grouped by first letter; each page range links nowhere
but can be looked up in book/ with the marker <!-- pdf:N. Also checks every page is within 1–440.
"""
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "index/khai-niem.tsv")
OUT = os.path.join(ROOT, "index/chi-muc-khai-niem.md")
ALPHA = "aăâbcdđeêghiklmnoôơpqrstuưvxy"


def sort_key(term):
    base = unicodedata.normalize("NFD", term.lower())
    tone = "".join(c for c in base if c in "̣̀́̃̉")
    letters = unicodedata.normalize("NFC", "".join(c for c in base if c not in "̣̀́̃̉"))
    return ([ALPHA.index(c) if c in ALPHA else 100 + ord(c) for c in letters], tone)


def first_letter(term):
    c = unicodedata.normalize("NFC", "".join(ch for ch in unicodedata.normalize("NFD", term[0].lower())
                                              if ch not in "̣̀́̃̉"))
    return c.upper() if c in ALPHA else "#"


def main():
    rows = []
    with open(SRC) as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            term, pages, note = line.split("\t")
            for a, b in re.findall(r"(\d+)(?:-(\d+))?", pages):
                for p in (a, b):
                    if p and not 1 <= int(p) <= 440:
                        raise SystemExit(f"dòng {i}: trang {p} ngoài 1–440")
            rows.append((term, pages.replace("-", "–"), note))
    rows.sort(key=lambda r: sort_key(r[0]))
    out = ["# Chỉ mục khái niệm — Luật Tâm Thức (Ngô Sa Thạch)", "",
           f"{len(rows)} mục, sắp theo vần. Số là trang PDF (trùng trang in); tìm trong `book/` bằng marker "
           "`<!-- pdf:N`. Ghi chú viết lại bằng lời người lập chỉ mục, không phải trích nguyên văn; "
           "chỗ ghi \"theo tác giả\" là quan điểm riêng của sách.", "",
           "Nguồn: `index/khai-niem.tsv` — sửa file đó rồi chạy `python3 tools/build_index.py`.", ""]
    letter = None
    for term, pages, note in rows:
        l = first_letter(term)
        if l != letter:
            out += ["", f"## {l}", "", "| Khái niệm | Trang | Ghi chú |", "|---|---|---|"]
            letter = l
        out.append(f"| {term} | {pages} | {note} |")
    with open(OUT, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"{len(rows)} khái niệm -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
