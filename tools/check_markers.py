#!/usr/bin/env python3
"""Check that book/NN-*.md contain page markers pdf:1..440 exactly once each, in order.

Usage: python3 tools/check_markers.py [total_pages=440]
Prints a summary and exits non-zero on any problem. With --report, also writes the
result into the "Kiểm tra marker" section of book/_bao-cao.md.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = re.compile(r"<!-- pdf:(\d+) \| sach:(\d+|\?) -->")


def check(total):
    seen = []   # (pdf page, file, line)
    for path in sorted(glob.glob(os.path.join(ROOT, "book/[0-9][0-9]-*.md"))):
        if os.path.basename(path).startswith("00-muc-luc"):
            continue
        with open(path) as f:
            for i, line in enumerate(f, 1):
                for m in MARKER.finditer(line):
                    seen.append((int(m.group(1)), os.path.basename(path), i))
    pages = [p for p, _, _ in seen]
    problems = []
    missing = sorted(set(range(1, total + 1)) - set(pages))
    if missing:
        problems.append(f"thiếu: {missing}")
    dups = sorted({p for p in pages if pages.count(p) > 1})
    if dups:
        problems.append("trùng: " + ", ".join(f"{p} ({[f'{f}:{l}' for q, f, l in seen if q == p]})" for p in dups))
    extra = sorted({p for p in pages if not 1 <= p <= total})
    if extra:
        problems.append(f"ngoài khoảng 1–{total}: {extra}")
    order = [(a, b) for a, b in zip(seen, seen[1:]) if b[0] <= a[0]]
    if order:
        problems.append("sai thứ tự: " + ", ".join(f"{a[0]}→{b[0]} ({b[1]}:{b[2]})" for a, b in order))
    return len(seen), problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    total = int(args[0]) if args else 440
    count, problems = check(total)
    lines = [f"- Số marker tìm thấy: {count} (cần {total})"]
    lines += [f"- LỖI {p}" for p in problems] or [f"- Đủ trang 1–{total}, không trùng, đúng thứ tự: OK"]
    print("\n".join(lines))
    if "--report" in sys.argv:
        path = os.path.join(ROOT, "book/_bao-cao.md")
        with open(path) as f:
            text = f.read()
        text = re.sub(r"\n## Kiểm tra marker\n.*?(?=\n## |\Z)", "", text, flags=re.S)
        head, sep, rest = text.partition("\n## ")
        text = head.rstrip("\n") + "\n\n## Kiểm tra marker\n\n" + "\n".join(lines) + "\n" + sep + rest
        with open(path, "w") as f:
            f.write(text)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
