#!/usr/bin/env python3
"""Re-OCR the regions listed in tools/ocr_fix/regions.json and write tools/ocr_fix/pNNN.json.

Each output file replaces, in all three OCR passes read by tools/build_book.py, the lines whose centre
lies inside `replace` by the re-OCR'd `lines` (same format as .cache/ocr*/pNNN.json). The text comes
only from Vision; nothing is typed by hand.

  dropcap  the two lines beside a chapter's drop cap (tools/ocr_region dropcap-ocr): the cap is cut out
           of the lines and put back, shrunk, before the first line, so Vision reads the first word whole.
           Both lines get the x of the text beside the cap, so build_book keeps them in one paragraph.
  block    every line inside `box` (tools/ocr_region ocr), enlarged `scale` times.

Pages are rendered at 300 DPI into .cache/pages300 when missing.
Usage: python3 tools/ocr_fix.py [page ...]      then: python3 tools/build_book.py
Build the helper first: swiftc -O tools/ocr_region.swift -o tools/ocr_region
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tools/ocr_fix")
PAGES = os.path.join(ROOT, ".cache/pages300")
SEARCH = [0.08, 0.10, 0.95, 0.26]   # where a drop cap and its two lines sit: x0, y0, x1, y1


def page_png(n):
    path = os.path.join(PAGES, f"p{n:03d}.png")
    if not os.path.exists(path):
        subprocess.run([os.path.join(ROOT, "tools/render_pages"), os.path.join(ROOT, "Luat TamThuc2.pdf"),
                        PAGES, str(n), str(n), "300"], check=True, stdout=subprocess.DEVNULL)
    return path


def region_tool(*args, env=None):
    out = subprocess.run([os.path.join(ROOT, "tools/ocr_region"), *map(str, args)], check=True,
                         capture_output=True, text=True, env={**os.environ, **(env or {})}).stdout
    return json.loads(out)


def r4(v):
    return round(v, 4)


def fix_dropcap(n, spec):
    res = region_tool("dropcap-ocr", page_png(n), *SEARCH, spec.get("scale", 2),
                      env={"CAP_KEEP": str(spec.get("cap_keep", 1.0))})
    cx, cy, cw, ch = res["cap"]
    lines = res["lines"]
    if len(lines) != 2:
        sys.exit(f"p{n}: expected 2 lines beside the drop cap, got {len(lines)}")
    x = lines[1]["x"]                        # text beside the cap, shared by both lines
    right = max(l["x"] + l["w"] for l in lines)
    for l in lines:
        l["w"], l["x"] = right - x, x
    bottom = max(l["y"] + l["h"] for l in lines) + 0.006
    replace = [cx - 0.01, cy - 0.008, 0.97 - (cx - 0.01), bottom - (cy - 0.008)]
    return {"kind": "dropcap", "cap": [r4(v) for v in res["cap"]], "replace": [r4(v) for v in replace], "lines": lines}


def fix_block(n, spec):
    box = spec["box"]
    res = region_tool("ocr", page_png(n), *box, spec.get("scale", 2))
    return {"kind": "block", "replace": box, "lines": sorted(res["lines"], key=lambda l: l["y"])}


def main():
    with open(os.path.join(FIX, "regions.json")) as f:
        specs = json.load(f)["fixes"]
    only = {int(a) for a in sys.argv[1:]}
    by_page = {}
    for s in specs:
        if not only or s["page"] in only:
            by_page.setdefault(s["page"], []).append(s)
    for n, group in sorted(by_page.items()):
        fixes = [fix_dropcap(n, s) if s["kind"] == "dropcap" else fix_block(n, s) for s in group]
        for fx in fixes:
            fx["lines"] = [{"text": l["text"], "conf": round(l["conf"], 3),
                            **{k: r4(l[k]) for k in ("x", "y", "w", "h")}} for l in fx["lines"]]
        with open(os.path.join(FIX, f"p{n:03d}.json"), "w", encoding="utf-8") as f:
            json.dump({"page": n, "source": "tools/ocr_fix.py (Vision vi-VT .accurate, 300 DPI)", "fixes": fixes},
                      f, ensure_ascii=False, indent=1)
        print(f"p{n:03d}: " + " | ".join(l["text"][:40] for fx in fixes for l in fx["lines"]))


if __name__ == "__main__":
    main()
