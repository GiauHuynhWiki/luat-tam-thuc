#!/usr/bin/env python3
"""Independent search spot check: short phrases read off the page IMAGES of the check-4 sample pages
(not taken from the OCR text or the index), searched diacritic-free in book/ like verify_search.py.

Input: tools/verify_spot_queries.tsv  "page<TAB>phrase<TAB>note"   ("a + b" = both in one paragraph)
Usage: python3 tools/verify_spot.py
"""
import os

from verify_common import ROOT
from verify_search import clean, paragraphs


def main():
    paras = paragraphs()
    rows = []
    with open(os.path.join(ROOT, "tools/verify_spot_queries.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            page, q, *note = line.rstrip("\n").split("\t")
            parts = [clean(p).strip() for p in q.split("+")]
            hits = sorted({p for ps, t in paras if all(f" {x} " in t for x in parts) for p in ps})
            sub = sorted({p for ps, t in paras
                          if all(x.replace(" ", "") in t.replace(" ", "") for x in parts) for p in ps})
            rows.append((int(page), q, int(page) in hits, int(page) in sub, hits, note[0] if note else ""))
    ok = sum(r[2] for r in rows)
    ok_sub = sum(r[3] for r in rows)
    print(f"== Tìm cụm từ đọc từ ảnh: {ok}/{len(rows)} tìm ra đúng trang; khớp chuỗi con (bỏ khoảng trắng): {ok_sub}/{len(rows)}")
    for page, q, found, fsub, hits, note in rows:
        flag = "ok  " if found else ("sub " if fsub else "MISS")
        print(f"  {flag} tr.{page:3}  '{q}' → {', '.join(map(str, hits[:8])) or '—'}  {note}")


if __name__ == "__main__":
    main()
