#!/usr/bin/env python3
"""Checks 1 and 2a of the OCR audit (read-only).

  1. Page attribution: for a random sample of pages, the first and last line of text under marker
     pdf:N must come from .cache/ocr/pNNN.json of page N, and match it better than pages N-1 / N+1.
  2a. OCR -> book: every line of .cache/ocr/pNNN.json (except running head, page number, watermark)
     must appear in the text of page N in book/ (diacritics ignored, small differences allowed).
  2c. Other passes -> book: lines of the 300 DPI pass (confirmed by the 220 DPI pass) that are not in
     book/. build_book.py takes its lines from the 150 DPI pass only, so a line that pass lost or
     garbled beyond the word vote shows up here (e.g. the line beside a drop cap).

Usage: python3 tools/verify_pages.py [--sample 20] [--seed 2026] [--min 0.8] [--json out.json]
"""
import argparse
import json
import random

from verify_common import book_pages, coverage, is_furniture, norm, ocr_lines

TOTAL = 440


def page_ocr_norm(n):
    return norm(" ".join(l["text"] for l in ocr_lines(n)))


def edge_lines(text):
    lines = [l.strip() for l in text.splitlines() if len(norm(l)) >= 12]
    if not lines:
        return None, None
    return lines[0], lines[-1]


def check_attribution(pages, sample):
    out = []
    for n in sample:
        first, last = edge_lines(pages.get(n, ""))
        if first is None:
            out.append({"page": n, "status": "no text"})
            continue
        row = {"page": n}
        for name, line in (("first", first[:80]), ("last", last[-80:])):
            key = norm(line)[:50] if name == "first" else norm(line)[-50:]
            scores = {m: coverage(key, page_ocr_norm(m)) for m in (n - 1, n, n + 1) if 1 <= m <= TOTAL}
            best = max(scores, key=scores.get)
            row[name] = {"score": round(scores[n], 3), "best_page": best,
                         "ok": best == n and scores[n] >= 0.8}
        row["status"] = "ok" if row["first"]["ok"] and row["last"]["ok"] else "FAIL"
        out.append(row)
    return out


def check_dropped(pages, min_cov):
    dropped, total = [], 0
    for n in range(1, TOTAL + 1):
        hay = norm(pages.get(n, ""))
        for idx, l in enumerate(ocr_lines(n)):
            if is_furniture(l):
                continue
            key = norm(l["text"])
            if len(key) < 2:
                continue
            total += 1
            c = coverage(key, hay)
            if c < min_cov:
                dropped.append({"page": n, "line": idx + 1, "y": round(l["y"], 3), "chars": len(key),
                                "cov": round(c, 2)})
    return total, dropped


def check_other_passes(pages, min_cov=0.6, min_chars=12):
    out = []
    for n in range(1, TOTAL + 1):
        hay = norm(pages.get(n, ""))
        p220 = norm(" ".join(l["text"] for l in ocr_lines(n, ".cache/ocr220")))
        for idx, l in enumerate(ocr_lines(n, ".cache/ocr300")):
            key = norm(l["text"])
            if is_furniture(l) or len(key) < min_chars:
                continue
            c = coverage(key, hay)
            if c < min_cov and coverage(key, p220) >= 0.8:
                out.append({"page": n, "line300": idx + 1, "y": round(l["y"], 3), "chars": len(key), "cov": round(c, 2)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--min", type=float, default=0.8)
    ap.add_argument("--json")
    a = ap.parse_args()
    pages = book_pages()
    candidates = [n for n in range(1, TOTAL + 1) if len(norm(pages.get(n, ""))) > 200]
    sample = sorted(random.Random(a.seed).sample(candidates, a.sample))
    attr = check_attribution(pages, sample)
    print(f"== Phép 1: gán trang, mẫu {len(sample)} trang (seed {a.seed})")
    for r in attr:
        if r["status"] == "no text":
            print(f"  tr.{r['page']}: không có chữ")
            continue
        f, l = r["first"], r["last"]
        print(f"  tr.{r['page']:3}: {r['status']:4}  đầu {f['score']:.2f} (khớp nhất tr.{f['best_page']})"
              f"  cuối {l['score']:.2f} (khớp nhất tr.{l['best_page']})")
    ok = sum(r["status"] == "ok" for r in attr)
    print(f"  => {ok}/{len(attr)} trang đúng")

    total, dropped = check_dropped(pages, a.min)
    print(f"\n== Phép 2a: dòng OCR có trong book/ (ngưỡng {a.min})")
    print(f"  dòng OCR xét: {total}; dòng thiếu: {len(dropped)}")
    for d in dropped:
        print(f"  tr.{d['page']:3} dòng {d['line']:2} (y={d['y']:.2f}, {d['chars']} ký tự): cov {d['cov']}")
    other = check_other_passes(pages)
    print("\n== Phép 2c: dòng lượt 300 DPI (lượt 220 DPI xác nhận) không có trong book/")
    print(f"  số dòng: {len(other)}")
    for d in other:
        print(f"  tr.{d['page']:3} dòng300 {d['line300']:2} (y={d['y']:.2f}, {d['chars']} ký tự): cov {d['cov']}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"sample": sample, "attribution": attr, "ocr_lines": total, "dropped": dropped,
                       "other_passes": other}, f, indent=1)


if __name__ == "__main__":
    main()
