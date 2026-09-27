#!/usr/bin/env python3
"""Assemble Vision OCR output into per-chapter Markdown under book/.

Usage:
  python3 tools/build_book.py                 # all chapters
  python3 tools/build_book.py --chapters 01   # only some chapters (comma separated "no" values)

Each page is rendered and OCR'd at 150, 220 and 300 DPI (tools/render_pages + tools/ocr_pages,
cached under .cache/). Layout comes from the 150 DPI pass; every word is then put to a vote
against the other two passes: if both agree on a different reading, theirs wins; if all three
disagree, the 150 DPI reading is kept and marked "[?]".
Regions listed in tools/ocr_fix/pNNN.json (re-OCR'd by tools/ocr_fix.py) replace the lines of all passes.

Writes book/NN-slug.md, book/00-muc-luc.md and book/_bao-cao.md.
"""
import argparse
import difflib
import json
import os
import re
import statistics
import subprocess
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "Luat TamThuc2.pdf")
BOOK = os.path.join(ROOT, "book")
PASSES = [  # (dpi, rendered pages dir, ocr json dir) — the first pass drives layout
    (150, ".cache/pages", ".cache/ocr"),
    (220, ".cache/pages220", ".cache/ocr220"),
    (300, ".cache/pages300", ".cache/ocr300"),
]
FOOTER_PASSES = [  # bottom strip only, small text allowed: catches page numbers the full passes miss
    (150, ".cache/pages", ".cache/ocrfoot"),
    (220, ".cache/pages220", ".cache/ocrfoot220"),
]
FIX_DIR = os.path.join(ROOT, "tools/ocr_fix")  # regions re-OCR'd by tools/ocr_fix.py, replacing all passes
PAGE_NO = re.compile(r"[^\w]*(\d(?:\s?\d){0,2})[^\w]*")

LOW_CONF = 0.8          # Vision confidence below this counts as a low-confidence line
FEW_CHARS = 400         # body text shorter than this -> likely an illustration page
FIGURE_GAP = 0.12       # vertical gap (fraction of page height) treated as a figure area
SHORT = 0.45            # lines narrower than this (fraction of page width) are not running text
with open(os.path.join(ROOT, "tools/page_notes.json")) as f:
    NOTES = json.load(f)    # {"23": "..."}: manual remarks shown under a page's marker and in the report

# ---------------------------------------------------------------- text helpers

def norm(s):
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def similar(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


HEADERS = ["LUẬT TÂM THỨC", "Ngô Sa Thạch"]
WATERMARK = "yeukindlevietnam.com"


def is_watermark(text):
    n = norm(text)
    return "kindle" in n or "vietnamcom" in n or similar(text, WATERMARK) > 0.7


# Vietnamese syllable check: flags OCR output that cannot be a Vietnamese word.
TONES = {"̀": "huyen", "́": "sac", "̃": "nga", "̉": "hoi", "̣": "nang"}
ONSETS = sorted("ngh ng nh ch gh gi kh ph th tr qu b c d đ g h k l m n p r s t v x".split(), key=len, reverse=True)
RHYMES = set("""
a ac ach ai am an ang anh ao ap at au ay ăc ăm ăn ăng ăp ăt âc âm ân âng âp ât âu ây
e ec em en eng eo ep et ê êch êm ên ênh êp êt êu
i ia ich im in inh ip it iu iêc iêm iên iêng iêp iêt iêu y yêm yên yêt yêu
o oc oi om on ong op ot oong ooc oa oac oach oai oam oan oang oanh oao oap oat oay oăc oăm oăn oăng oăt oe oen oeo oet
ô ôc ôi ôm ôn ông ôp ôt ơ ơi ơm ơn ơp ơt
u uc ui um un ung up ut ua uân uâng uât uây uê uêch uênh uy uya uych uyên uyêt uynh uyt uyu uôc uôi uôm uôn uông uôt uơ
ư ưc ưi ưm ưn ưng ưt ưu ưa ươc ươi ươm ươn ương ươp ươt ươu
""".split())


def valid_syllable(word):
    w = unicodedata.normalize("NFD", word.lower())
    tones = [TONES[c] for c in w if c in TONES]
    if len(tones) > 1:
        return False
    base = unicodedata.normalize("NFC", "".join(c for c in w if c not in TONES))
    if tones and re.search(r"(p|t|c|ch)$", base) and tones[0] not in ("sac", "nang"):
        return False
    for on in ONSETS + [""]:
        if base.startswith(on):
            rest = base[len(on):]
            if rest in RHYMES or (on == "gi" and rest == ""):
                return True
    return False


def suspicious_words(text):
    """Words with Vietnamese diacritics that are not valid syllables (pure ASCII is skipped: may be English)."""
    return [t for t in re.findall(r"[^\W\d_]+", text) if not t.isascii() and not valid_syllable(t)]

# ---------------------------------------------------------------- OCR passes

def ensure_ocr(first, last):
    for dpi, pages, ocr in PASSES + FOOTER_PASSES:
        pages, ocr = os.path.join(ROOT, pages), os.path.join(ROOT, ocr)
        todo = [n for n in range(first, last + 1) if not os.path.exists(f"{ocr}/p{n:03d}.json")]
        if not todo:
            continue
        a, b = str(min(todo)), str(max(todo))
        if not all(os.path.exists(f"{pages}/p{n:03d}.png") for n in todo):
            subprocess.run([os.path.join(ROOT, "tools/render_pages"), PDF, pages, a, b, str(dpi)],
                           check=True, stdout=subprocess.DEVNULL)
        mode = ["footer"] if (dpi, ocr) in [(d, os.path.join(ROOT, o)) for d, _, o in FOOTER_PASSES] else []
        subprocess.run([os.path.join(ROOT, "tools/ocr_pages"), pages, ocr, a, b] + mode,
                       check=True, stdout=subprocess.DEVNULL)


def read_fixes(n):
    """Re-OCR'd regions of page n from tools/ocr_fix/pNNN.json (written by tools/ocr_fix.py), or []."""
    path = os.path.join(FIX_DIR, f"p{n:03d}.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["fixes"]


def apply_fixes(lines, n):
    """Drop the lines whose centre lies in a fixed region and add that region's re-OCR'd lines.
    Every full pass gets the same lines, so the word vote keeps them as they are."""
    for fx in read_fixes(n):
        x, y, w, h = fx["replace"]
        lines = [l for l in lines if not (x <= l["x"] + l["w"] / 2 <= x + w and y <= l["y"] + l["h"] / 2 <= y + h)]
        lines += [dict(l) for l in fx["lines"]]
    return lines


def read_json(ocr_dir, n):
    with open(os.path.join(ROOT, ocr_dir, f"p{n:03d}.json")) as f:
        lines = json.load(f)["lines"]
    if ocr_dir in [o for _, _, o in PASSES]:
        lines = apply_fixes(lines, n)
    for l in lines:
        l["text"] = l["text"].strip()
    return [l for l in lines if l["text"]]


def into_rows(lines):
    """Reading order: lines whose vertical centres are close form a row, left to right within a row."""
    lines = sorted(lines, key=lambda l: l["y"] + l["h"] / 2)
    rows, cur = [], []
    for l in lines:
        c = l["y"] + l["h"] / 2
        if cur and abs(c - (cur[0]["y"] + cur[0]["h"] / 2)) > 0.5 * max(l["h"], cur[0]["h"]):
            rows.append(sorted(cur, key=lambda l: l["x"]))
            cur = []
        cur.append(l)
    if cur:
        rows.append(sorted(cur, key=lambda l: l["x"]))
    return rows


def vote(rows, n, stats):
    """Replace each word of the primary pass by the majority reading across the three passes."""
    words = [(r, i, k, w) for r, row in enumerate(rows) for i, l in enumerate(row)
             for k, w in enumerate(l["text"].split())]
    prim = [w for *_, w in words]
    alts = []
    for _, _, ocr in PASSES[1:]:
        other = [w for row in into_rows(read_json(ocr, n)) for l in row for w in l["text"].split()]
        m = [None] * len(prim)
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, prim, other, autojunk=False).get_opcodes():
            if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
                for d in range(i2 - i1):
                    m[i1 + d] = other[j1 + d]
        alts.append(m)
    out = list(prim)
    for idx, p in enumerate(prim):
        a, b = alts[0][idx], alts[1][idx]
        if a is not None and a == b and a != p:
            out[idx] = a
            stats["voted"].append((n, p, a))
        elif (a is not None and a != p) and (b is None or b != p):
            cands = " / ".join(dict.fromkeys(x for x in (p, a, b) if x))
            out[idx] = p + "[?]"
            stats["unsure"].append((n, cands))
        elif a is None and b is not None and b != p:
            out[idx] = p + "[?]"
            stats["unsure"].append((n, f"{p} / {b}"))
    # write words back into their lines
    buf = {}
    for (r, i, k, _), w in zip(words, out):
        buf.setdefault((r, i), []).append(w)
    for (r, i), ws in buf.items():
        rows[r][i]["text"] = " ".join(ws)


def page_number(l):
    m = PAGE_NO.fullmatch(l["text"]) if l["y"] > 0.92 else None
    return int(re.sub(r"\s", "", m.group(1))) if m else None


def printed_page(n):
    """Majority vote over every pass that read a page number at the bottom of the page."""
    seen = [page_number(l) for _, _, ocr in PASSES + FOOTER_PASSES for l in read_json(ocr, n)]
    seen = [v for v in seen if v is not None]
    if not seen:
        return None
    return max(set(seen), key=lambda v: (seen.count(v), -abs(v - n)))


def load_page(n, stats):
    rows = into_rows(read_json(PASSES[0][2], n))
    page = {"n": n, "printed": printed_page(n), "rows": []}
    for row in rows:
        keep = []
        for l in row:
            t = l["text"]
            if is_watermark(t):
                continue
            if l["y"] < 0.07 and any(similar(t, h) > 0.75 for h in HEADERS):
                continue
            if page_number(l) is not None:
                continue
            keep.append(l)
        if keep:
            page["rows"].append(keep)
    vote(page["rows"], n, stats)
    return page

# ---------------------------------------------------------------- layout

def row_kind(row, margin, prev_kind):
    """text: running prose · pre: aligned formulas / columns · label: short labels inside a figure."""
    if len(row) == 1 and row[0]["w"] >= SHORT:
        return "text"
    joined = " ".join(l["text"] for l in row)
    if all(len(l["text"]) <= 4 for l in row) and "=" not in joined:
        return "label"
    if len(row) > 1 or re.search(r"[=+×/]\s*\d", joined):
        return "pre"
    # a short single line: paragraph end, caption or short standalone line
    return "text"


def body_margin(rows):
    xs = sorted(l["x"] for r in rows for l in r if l["w"] > SHORT)
    if not xs:
        xs = sorted(l["x"] for r in rows for l in r) or [0.1]
    return xs[len(xs) // 4]


def line_step(rows):
    ys = [r[0]["y"] for r in rows]
    steps = [b - a for a, b in zip(ys, ys[1:]) if 0.005 < b - a < 0.06]
    return statistics.median(steps) if steps else 0.026


BULLET = re.compile(r"^[•●○◦·]\s*")
HEAD_JUNK = re.compile(r"^(?:[•●○◦·®\-\s]|\[\?\])*")   # bullet / OCR'd section icon before a title


def page_blocks(page, ch, stats):
    """Turn one page's rows into blocks: {"kind": para|heading|pre|figure, "text"/"lines"/"labels", "indent"}."""
    n = page["n"]
    rows = page["rows"]
    sec_title = {p: t for t, p in ch["sections"]}.get(n)
    if n == ch["first"] and "label" in ch:
        head = norm(ch["label"] + ch["title"])
        rows = [r for r in ([l for l in r if norm(l["text"]) not in head] for r in rows) if r]

    margin, step = body_margin(rows), line_step(rows)
    blocks, prev, prev_kind = [], None, None
    skip = False
    for i, row in enumerate(rows):
        if skip:            # second line of a two-line section title, already emitted
            skip = False
            continue
        first = row[0]
        for l in row:
            for w in suspicious_words(l["text"].replace("[?]", "")):
                stats["suspicious"].append((n, w, l["text"]))
            if l["conf"] < LOW_CONF:
                stats["low_lines"].append((n, l["text"], l["conf"]))
                l["text"] += " [?]"
        kind = row_kind(row, margin, prev_kind)
        gap = first["y"] - (prev["y"] + prev["h"]) if prev else 0
        if prev and gap > FIGURE_GAP and not (blocks and blocks[-1]["kind"] == "figure"):
            blocks.append({"kind": "figure", "labels": []})
            stats["figures"].append(n)

        text = " ".join(l["text"] for l in row)
        bare = HEAD_JUNK.sub("", text)
        # a title printed over two lines: this row must be the start of the title
        two = ""
        if sec_title and i + 1 < len(rows) and norm(bare) and norm(sec_title).startswith(norm(bare)[:10]):
            two = bare + " " + " ".join(l["text"] for l in rows[i + 1])
        if sec_title and similar(bare, sec_title) > 0.8:
            blocks.append({"kind": "heading", "text": "## " + bare})
            sec_title = None        # one heading per section; later look-alikes are figure labels
        elif two and similar(two, sec_title) > 0.8:
            blocks.append({"kind": "heading", "text": "## " + two})
            sec_title = None
            skip = True
        elif kind == "label":
            if not (blocks and blocks[-1]["kind"] == "figure"):
                blocks.append({"kind": "figure", "labels": []})
                stats["figures"].append(n)
            blocks[-1]["labels"] += [l["text"] for l in row]
        elif kind == "pre":
            line = "    ".join(l["text"] for l in row)
            if blocks and blocks[-1]["kind"] == "pre" and prev_kind == "pre":
                blocks[-1]["lines"].append(line)
            else:
                blocks.append({"kind": "pre", "lines": [line]})
        else:
            indent = first["x"] - margin
            bullet = BULLET.match(text)
            last = blocks[-1] if blocks else None
            # Text wrapped beside a figure is one narrow column away from the margin: only a line
            # that starts at a different x than the line above it can open a new paragraph.
            shifted = abs(first["x"] - prev["x"]) > 0.015 if prev else True
            new_para = (
                last is None or last["kind"] != "para" or prev_kind != "text"
                or bullet
                or (indent > 0.035 and shifted)
                or ((prev["x"] - margin) > 0.15 and shifted)  # previous line was centred / a caption
                or first["y"] - prev["y"] > 1.7 * step
            )
            if bullet:
                text = "- " + text[bullet.end():]
            if new_para:
                blocks.append({"kind": "para", "text": text, "indent": indent > 0.035 or bool(bullet)})
            else:
                last["text"] += " " + text
        prev, prev_kind = first, kind
    return blocks


def render_block(b, n):
    if b["kind"] in ("para", "heading"):
        return b["text"]
    if b["kind"] == "pre":
        return "```text\n" + "\n".join(b["lines"]) + "\n```"
    labels = f" Chữ/số đọc được trong hình: {', '.join(b['labels'])}." if b["labels"] else ""
    return f"> [Hình — xem ảnh trang {n}.{labels}]"

# ---------------------------------------------------------------- chapter assembly

def build_chapter(ch, stats):
    title = f"{ch['label']}: {ch['title']}" if "label" in ch else ch["title"]
    out = [f"# {title}"]
    last_para = None     # index in `out` of the last running paragraph, if it is still open

    for n in range(ch["first"], ch["last"] + 1):
        page = load_page(n, stats)
        blocks = page_blocks(page, ch, stats)
        printed = page["printed"]
        marker = f"<!-- pdf:{n} | sach:{printed if printed is not None else '?'} -->"
        if str(n) in NOTES:
            marker += f"\n> [Ghi chú: {NOTES[str(n)]}]"
        chars = sum(len(l["text"]) for r in page["rows"] for l in r)
        stats["pages"].append({"n": n, "printed": printed, "chars": chars,
                               "lines": sum(len(r) for r in page["rows"])})

        if not blocks:
            out.append(marker + "\n> [Trang không có chữ — trang trắng hoặc chỉ có hình]")
            last_para = None
            continue

        # A paragraph that runs over from the previous page stays one paragraph, marker inside it.
        b0 = blocks[0]
        if (last_para is not None and b0["kind"] == "para" and not b0["indent"] and str(n) not in NOTES
                and not re.search(r"[.!?:…\"”)]$", out[last_para])):
            out[last_para] += "\n" + marker + "\n" + b0["text"]
            blocks = blocks[1:]
            head = None
        else:
            head = marker
        for b in blocks:
            text = render_block(b, n)
            if head:
                text, head = head + "\n" + text, None
            out.append(text)
        if blocks:  # otherwise the whole page continued the open paragraph, which stays open
            last_para = len(out) - 1 if blocks[-1]["kind"] == "para" else None
    return "\n\n".join(out) + "\n"


def fname(ch):
    return f"{ch['no']}-{ch['slug']}.md"


def write_toc(chapters):
    rows = ["# Mục lục — Luật Tâm Thức (Ngô Sa Thạch)", "",
            "Trang in trong sách trùng số trang PDF. Mục lục gốc in ở trang 435–438.", "",
            "| Chương | Tiêu đề | File | Trang PDF |", "|---|---|---|---|"]
    for ch in chapters:
        rows.append(f"| {ch.get('label', '—')} | {ch['title']} | [{fname(ch)}]({fname(ch)}) | {ch['first']}–{ch['last']} |")
    rows += ["", "## Các mục trong chương", ""]
    for ch in chapters:
        if ch["sections"] and "label" in ch:
            rows += [f"**{ch['label']}: {ch['title']}** (tr. {ch['first']})", ""]
            rows += [f"- {t} — tr. {p}" for t, p in ch["sections"]] + [""]
    with open(os.path.join(BOOK, "00-muc-luc.md"), "w") as f:
        f.write("\n".join(rows))


def cell(s):
    return s.replace("|", "/")


def write_report(stats, chapters_done):
    pages = stats["pages"]
    total_lines = sum(p["lines"] for p in pages)
    low, unsure = len(stats["low_lines"]), len(stats["unsure"])
    r = ["# Báo cáo OCR", "",
         "Tạo tự động bởi `tools/build_book.py`: macOS Vision (vi-VT, .accurate, language correction),",
         "OCR mỗi trang ở 150/220/300 DPI rồi bỏ phiếu từng từ.", "",
         f"- Chương đã xử lý: {', '.join(chapters_done)}",
         f"- Số trang: {len(pages)}",
         f"- Số dòng chữ (sau khi bỏ đầu trang/số trang/watermark): {total_lines}",
         f"- Từ được sửa theo đa số (220 và 300 DPI cùng đọc khác 150 DPI): {len(stats['voted'])}",
         f"- Từ không thống nhất giữa các lần OCR, đánh dấu `từ[?]`: {unsure}",
         f"- Dòng Vision báo tin cậy thấp (conf < {LOW_CONF}), đánh dấu `[?]` cuối dòng: {low} ({low / max(total_lines, 1):.1%})",
         f"- Từ không phải âm tiết tiếng Việt hợp lệ (sau bỏ phiếu): {len(stats['suspicious'])}",
         f"- Trang có vùng OCR lại (`tools/ocr_fix/`): "
         f"{', '.join(str(p['n']) for p in pages if read_fixes(p['n'])) or 'không có'}",
         ""]
    no_num = [p["n"] for p in pages if p["printed"] is None]
    mismatch = [(p["n"], p["printed"]) for p in pages if p["printed"] is not None and p["printed"] != p["n"]]
    r += ["## Trang ít chữ (có thể là trang hình/sơ đồ/trang trắng)", ""]
    r += [f"- pdf {p['n']}: {p['chars']} ký tự" for p in pages if p["chars"] < FEW_CHARS] or ["- (không có)"]
    r += ["", "## Trang có hình (chỗ trống lớn hoặc cụm nhãn ngắn)", ""]
    r += [", ".join(str(n) for n in sorted(set(stats["figures"])))] if stats["figures"] else ["- (không có)"]
    r += ["", "## Trang không đọc được số trang in (sach:?)", ""]
    r += [", ".join(str(n) for n in no_num)] if no_num else ["- (không có)"]
    if mismatch:
        r += ["", "## Số trang in khác số trang PDF (kiểm tra lại)", ""]
        r += [f"- pdf {n}: đọc được {p}" for n, p in mismatch]
    notes = [(int(k), v) for k, v in NOTES.items() if int(k) in {p["n"] for p in pages}]
    if notes:
        r += ["", "## Ghi chú thủ công theo trang", ""] + [f"- pdf {k}: {v}" for k, v in sorted(notes)]
    r += ["", "## Từ không thống nhất (150 / 220 / 300 DPI)", "", "| Trang | Các cách đọc |", "|---|---|"]
    r += [f"| {n} | {cell(c)} |" for n, c in stats["unsure"]]
    r += ["", "## Từ không phải âm tiết hợp lệ", "", "| Trang | Từ | Dòng |", "|---|---|---|"]
    r += [f"| {n} | {w} | {cell(t)} |" for n, w, t in stats["suspicious"]]
    r += ["", "## Dòng tin cậy thấp", "", "| Trang | Conf | Dòng |", "|---|---|---|"]
    r += [f"| {n} | {c:.2f} | {cell(t)} |" for n, t, c in stats["low_lines"]]
    per_page = {}
    for n, *_ in stats["unsure"] + stats["suspicious"] + stats["low_lines"]:
        per_page[n] = per_page.get(n, 0) + 1
    r += ["", "## Trang cần người xem lại", "",
          "Số chỗ `[?]`/nghi sai trên mỗi trang (nhiều nhất trước); cộng các trang sach:? ở trên.", ""]
    r += [", ".join(f"{n} ({c})" for n, c in sorted(per_page.items(), key=lambda x: (-x[1], x[0])))] or ["- (không có)"]
    with open(os.path.join(BOOK, "_bao-cao.md"), "w") as f:
        f.write("\n".join(r) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", help="comma separated chapter numbers, e.g. 00,01")
    args = ap.parse_args()
    with open(os.path.join(ROOT, "tools/chapters.json")) as f:
        chapters = json.load(f)
    todo = [c for c in chapters if not args.chapters or c["no"] in args.chapters.split(",")]
    os.makedirs(BOOK, exist_ok=True)
    write_toc(chapters)
    stats = {"pages": [], "low_lines": [], "suspicious": [], "figures": [], "voted": [], "unsure": []}
    for ch in todo:
        ensure_ocr(ch["first"], ch["last"])
        with open(os.path.join(BOOK, fname(ch)), "w") as f:
            f.write(build_chapter(ch, stats))
        print("wrote", fname(ch))
    write_report(stats, [c["no"] for c in todo])


if __name__ == "__main__":
    main()
