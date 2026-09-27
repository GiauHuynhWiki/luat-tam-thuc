#!/usr/bin/env python3
"""Check 3 of the OCR audit: can a diacritic-free search of book/ find each index concept on its pages?

For every row of index/khai-niem.tsv, 1–2 queries are taken from the concept's name only:
  q1 = the first name (before "/" and "("), q2 = the text in parentheses, or the second name after "/".
Names can be overridden in tools/verify_search_keys.tsv ("row<TAB>q1<TAB>q2", row = 1-based line of the
TSV) when the automatic query is not a usable search term (e.g. a whole descriptive phrase); override
keywords are still words of the concept's name. "a + b" = both a and b in the same paragraph (tim.py a b).
A query matches a page when one paragraph of that page contains it (lower case, no diacritics, đ -> d,
punctuation -> space, whole words), like tim.py but tolerant of dashes/quotes. Paragraphs split by a page
marker count for both pages. A concept is FOUND when a query matches a listed page (±1).
"sub" repeats the check with substring matching over text with spaces removed (looser than tim.py; shows
matches lost only because OCR glued or split words).
For the misses it also reports: the pages where the queries do match (-> index page wrong?), and whether
all words of q1 occur on a listed page at all (-> the book words it differently vs OCR lost it).

Usage: python3 tools/verify_search.py [--json out.json] [--verbose]
"""
import argparse
import json
import os
import re

from verify_common import MARKER, ROOT, book_files, fold

TSV = os.path.join(ROOT, "index/khai-niem.tsv")
KEYS = os.path.join(ROOT, "tools/verify_search_keys.tsv")
STOP = set("va cua la cac nhung trong the cho mot co khi hay theo tac gia so".split())


def clean(s):
    return " " + re.sub(r"[^a-z0-9]+", " ", fold(s)).strip() + " "


def paragraphs():
    """[(set of pages, cleaned paragraph)]: page-marker lines split a paragraph; both halves also
    appear joined, attributed to both pages."""
    out = []
    for path in book_files():
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        # the chapter title above the first marker belongs to the chapter's first page
        page = next(int(m.group(1)) for l in lines if (m := MARKER.search(l)))
        prev = None
        for line in lines:
            m = MARKER.search(line)
            if m:
                page = int(m.group(1))
                continue
            if not line.strip():
                prev = None
                continue
            c = clean(line.replace("[?]", ""))
            out.append(({page}, c))
            if prev is not None and prev[0] != page:       # paragraph running over a page break
                out.append(({prev[0], page}, prev[1] + c[1:]))
            prev = (page, c)
    return out


def parse_pages(s):
    pages = set()
    for part in re.split(r"[,;]\s*", s):
        m = re.match(r"(\d+)\s*[-–]\s*(\d+)$", part.strip())
        if m:
            pages |= set(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.strip().isdigit():
            pages.add(int(part.strip()))
    return pages


def auto_queries(name):
    paren = re.findall(r"\(([^)]*)\)", name)
    main = re.sub(r"\([^)]*\)", "", name)
    alts = [a.strip() for a in main.split("/") if a.strip()]
    q = [alts[0]] if alts else []
    if paren:
        q.append(paren[0].split(",")[0])
    elif len(alts) > 1:
        q.append(alts[1])
    return [x for x in (clean(x).strip() for x in q) if x]


def load_overrides():
    over = {}
    if os.path.exists(KEYS):
        with open(KEYS, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                row, *qs = line.rstrip("\n").split("\t")
                over[int(row)] = [" + ".join(clean(p).strip() for p in q.split("+")) for q in qs if q.strip()]
    return over


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    paras = paragraphs()
    over = load_overrides()
    rows = []
    with open(TSV, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            name, pages, *_ = line.rstrip("\n").split("\t")
            listed = parse_pages(pages)
            near = {p + d for p in listed for d in (-1, 0, 1)}
            queries = over.get(i) or auto_queries(name)
            hit_pages, sub_pages = {}, {}
            for q in queries:
                hp, sp = set(), set()
                parts = q.split(" + ")
                for ps, text in paras:
                    if all(f" {p} " in text for p in parts):
                        hp |= ps
                    if all(p.replace(" ", "") in text.replace(" ", "") for p in parts):
                        sp |= ps
                hit_pages[q], sub_pages[q] = sorted(hp), sorted(sp)
            found = [q for q, hp in hit_pages.items() if set(hp) & near]
            found_sub = [q for q, sp in sub_pages.items() if set(sp) & near]
            words = [w for w in queries[0].replace(" + ", " ").split() if w not in STOP] if queries else []
            words_on_page = bool(words) and any(all(f" {w} " in t for w in words) for ps, t in paras if ps & near)
            rows.append({"row": i, "name": name, "pages": pages, "queries": queries, "override": i in over,
                         "found": bool(found), "found_sub": bool(found_sub),
                         "hit_pages": hit_pages, "sub_pages": sub_pages, "words_on_listed_page": words_on_page})
    ok, sub = sum(r["found"] for r in rows), sum(r["found_sub"] for r in rows)
    print(f"== Phép 3: tìm khái niệm theo chỉ mục — tìm thấy đúng trang (±1): {ok}/{len(rows)} ({ok / len(rows):.1%})"
          f"; khớp chuỗi con, bỏ khoảng trắng: {sub}/{len(rows)} ({sub / len(rows):.1%})")
    print(f"   (truy vấn tự động {sum(not r['override'] for r in rows)}, chỉnh tay {sum(r['override'] for r in rows)})")
    for r in rows:
        if r["found"] and not a.verbose:
            continue
        hp = "; ".join(f"'{q}' → {', '.join(map(str, p[:12])) or '—'}{' …' if len(p) > 12 else ''}"
                       for q, p in r["hit_pages"].items())
        flag = "ok  " if r["found"] else ("sub " if r["found_sub"] else "MISS")
        print(f"  {flag} #{r['row']:3} [{r['pages']}] {r['name']}  | {hp}"
              f"{'' if r['found'] else '  | đủ từ trên trang: ' + ('có' if r['words_on_listed_page'] else 'không')}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
