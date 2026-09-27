#!/usr/bin/env python3
"""Crop every illustration of the book into hinh/.

Usage:
  python3 tools/export_figures.py            # detect, apply tools/figure_overrides.json, crop, write lists
  python3 tools/export_figures.py --no-detect   # reuse the last detection, e.g. after editing the overrides

Needs .cache/pages/pNNN.png (150 DPI) and .cache/ocr/pNNN.json from tools/build_book.py.
Writes:
  hinh/NN/pNNN-K.jpg   figure K of page NNN, cropped from a 300 DPI render, NN = chapter file number
  hinh/_khung.json     final boxes per page (normalized x, y, w, h; top-left origin)
  hinh/danh-sach.md    chapter -> section -> page -> files
  hinh/xem-truoc.html  local preview of every figure, grouped by chapter
"""
import argparse
import html
import json
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "Luat TamThuc2.pdf")
OUT = os.path.join(ROOT, "hinh")
TOOL = os.path.join(ROOT, "tools/crop_figures")
AUTO = os.path.join(ROOT, ".cache/fig/boxes-auto.json")
BOXES = os.path.join(OUT, "_khung.json")


def chapter_of(page, chapters):
    for ch in chapters:
        if ch["first"] <= page <= ch["last"]:
            section = ch["title"]
            for title, start in ch["sections"]:
                if start <= page:
                    section = title
            return ch, section
    raise ValueError(f"page {page} is in no chapter")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-detect", action="store_true")
    args = ap.parse_args()
    os.chdir(ROOT)
    chapters = json.load(open("tools/chapters.json"))
    overrides = json.load(open("tools/figure_overrides.json"))

    if not args.no_detect:
        os.makedirs(os.path.dirname(AUTO), exist_ok=True)
        subprocess.run([TOOL, "detect", ".cache/pages", ".cache/ocr", "1", "440", AUTO], check=True)
    boxes = json.load(open(AUTO))
    for page in overrides["exclude"]:
        boxes.pop(str(page), None)
    boxes.update(overrides["boxes"])

    pages = sorted(boxes, key=int)
    jobs, by_chapter = [], {}
    for p in pages:
        n = int(p)
        ch, section = chapter_of(n, chapters)
        files = []
        for k, box in enumerate(boxes[p], 1):
            rel = f"{ch['no']}/p{n:03d}-{k}.jpg"
            jobs.append({"page": n, "box": box, "out": os.path.join(OUT, rel)})
            files.append(rel)
        by_chapter.setdefault(ch["no"], {"ch": ch, "rows": []})["rows"].append((n, section, files))

    # start clean so boxes removed by overrides do not leave stale crops behind
    for entry in os.listdir(OUT) if os.path.isdir(OUT) else []:
        if len(entry) == 2 and entry.isdigit():
            shutil.rmtree(os.path.join(OUT, entry))
    os.makedirs(OUT, exist_ok=True)
    with open(BOXES, "w") as f:
        json.dump({p: boxes[p] for p in pages}, f, indent=1, sort_keys=False)
    jobs_path = os.path.join(ROOT, ".cache/fig/jobs.json")
    with open(jobs_path, "w") as f:
        json.dump(jobs, f)
    subprocess.run([TOOL, "crop", PDF, jobs_path, "300", "0.9"], check=True)

    write_list(by_chapter, len(pages), len(jobs))
    write_preview(by_chapter, len(pages), len(jobs))
    print(f"{len(jobs)} figures on {len(pages)} pages -> hinh/")


def chapter_name(ch):
    return f"{ch['label']}: {ch['title']}" if "label" in ch else ch["title"]


def write_list(by_chapter, n_pages, n_figs):
    r = ["# Hình minh hoạ trong sách", "",
         f"{n_figs} hình trên {n_pages} trang, cắt tự động từ ảnh trang 300 DPI (xem `tools/export_figures.py`).",
         "Tên file: `NN/pNNN-K.jpg` = chương NN, trang NNN (trùng số trang in), hình thứ K trên trang.", "",
         "Chỉ dùng cá nhân: sách còn bản quyền.", ""]
    for no in sorted(by_chapter):
        ch = by_chapter[no]["ch"]
        r += [f"## {chapter_name(ch)}", "", "| Trang | Mục | Hình |", "|---|---|---|"]
        for n, section, files in by_chapter[no]["rows"]:
            links = ", ".join(f"[{os.path.basename(f)}]({f})" for f in files)
            r.append(f"| {n} | {section} | {links} |")
        r.append("")
    with open(os.path.join(OUT, "danh-sach.md"), "w") as f:
        f.write("\n".join(r))


def write_preview(by_chapter, n_pages, n_figs):
    e = html.escape
    parts = []
    for no in sorted(by_chapter):
        ch = by_chapter[no]["ch"]
        cards = []
        for n, section, files in by_chapter[no]["rows"]:
            for f in files:
                cards.append(f'<figure><a href="{e(f)}"><img src="{e(f)}" loading="lazy" alt="Trang {n}"></a>'
                             f'<figcaption><b>tr. {n}</b> · {e(section)}</figcaption></figure>')
        parts.append(f'<section><h2>{e(chapter_name(ch))}</h2><div class="grid">{"".join(cards)}</div></section>')
    page = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hình minh hoạ</title>
<style>
:root {{ --bg: #faf9f6; --card: #fff; --text: #222; --muted: #666; --line: #e3e0da; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #1b1b1d; --card: #26262a; --text: #eee; --muted: #aaa; --line: #3a3a40; }} }}
body {{ margin: 0; padding: 24px 16px 64px; background: var(--bg); color: var(--text);
       font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
main {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin: 0 0 4px; }}
p.meta {{ color: var(--muted); margin: 0 0 24px; }}
h2 {{ font-size: 18px; margin: 32px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }}
figure {{ margin: 0; background: var(--card); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
figure img {{ display: block; width: 100%; height: 200px; object-fit: contain; background: #fff; }}
figcaption {{ padding: 8px 10px; font-size: 13px; color: var(--muted); }}
figcaption b {{ color: var(--text); }}
</style></head>
<body><main>
<h1>Hình minh hoạ — Luật Tâm Thức</h1>
<p class="meta">{n_figs} hình trên {n_pages} trang. Bấm vào hình để xem cỡ lớn. Chỉ dùng cá nhân.</p>
{"".join(parts)}
</main></body></html>
"""
    with open(os.path.join(OUT, "xem-truoc.html"), "w") as f:
        f.write(page)


if __name__ == "__main__":
    main()
