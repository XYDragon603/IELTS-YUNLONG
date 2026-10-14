"""Move question-page text out of reading passages.

The importer cut passages by page, so text from the question pages that follow
a passage (instructions, option lists, lists of names or headings, word banks)
was stored as extra passage blocks. This script finds, on each block's page,
the nearest "Questions N–M" heading above the block (PDF text layer, or
Tesseract on scanned pages). A block is treated as question material only when
that heading's numbers belong to the same passage, so a passage that starts
below the previous passage's questions is left alone.

Each such block is removed from the passage. Its content is not thrown away:

  * if the target group has no options and the block is a clean letter list
    (A, B, C … in order), it becomes the group's shared option list;
  * otherwise lines that the group does not already contain are appended to the
    group context, unless the group image (asset) already covers that region.

Every move is logged in <test>/ocr-cleanup.json (original block, heading used
as evidence, destination) and files are backed up first. This is a rule-based
re-segmentation, not a human or visual review; needsReview / verified flags are
unchanged.

Usage:
  python scripts/resegment_passages.py                 # dry run, all tests
  python scripts/resegment_passages.py --book 13       # dry run, one book
  python scripts/resegment_passages.py --write         # apply, back up and log
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reparse_mcq_options import split_words  # noqa: E402
from render_evidence import render  # noqa: E402

WORKSPACE = Path(__file__).resolve().parent.parent
ROOT = WORKSPACE / "resources" / "cambridge"
TESSERACT = shutil.which("tesseract") or r"C:/Program Files/Tesseract-OCR/tesseract.exe"
METHOD = "passage-resegment"
HEADING = re.compile(r"^\s*Questions?\s+(\d{1,2})(?:\s*(?:[-–—]|and)\s*(\d{1,2}))?")
LETTER_MISREAD = {"Cc": "C", "c": "C", "©": "C", "(": "C", "0": "D", "8": "B", "l": "I", "|": "I", "1": "I"}

fitz.TOOLS.mupdf_display_errors(False)

# Blocks removed after looking at the rendered region (reviewMethod "assistant-visual").
# Keyed by (book, test, pdfPage, text prefix) so a re-run never matches a different block.
VISUAL_REMOVALS = {
    (14, 1, 23, "£8 Ey FS"): "Promotional QR-code advertisement inserted into the PDF; not part of the exam paper.",
}


def visual_removal(book: int, test: int, block: dict) -> str | None:
    page = (block.get("source") or {}).get("pdfPage")
    text = block.get("text") or ""
    return next((why for (b, t, p, prefix), why in VISUAL_REMOVALS.items()
                 if (b, t, p) == (book, test, page) and text.startswith(prefix)), None)


def edge_fragment(block: dict) -> bool:
    """A few characters in the top or bottom 2% of the page: watermark or scan-edge residue."""
    box = (block.get("source") or {}).get("boundingBox") or [0.5, 0, 0.5, 1]
    return len((block.get("text") or "").strip()) < 20 and (box[2] <= 0.02 or box[0] >= 0.98)


@functools.lru_cache(None)
def page_lines(paper: str, page_no: int) -> tuple[str, tuple]:
    """(source, ((y, text), ...)) for one page, y in 0-1 page coordinates."""
    cache = WORKSPACE / ".cache" / "page-lines" / f"{re.sub(r'[^A-Za-z0-9]+', '_', paper)[-60:]}-{page_no}.json"
    if cache.exists():
        kind, lines = json.loads(cache.read_text(encoding="utf-8"))
        return kind, tuple(tuple(l) for l in lines)
    kind, lines = _page_lines(paper, page_no)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps([kind, lines], ensure_ascii=False), encoding="utf-8")
    return kind, lines


def _page_lines(paper: str, page_no: int) -> tuple[str, tuple]:
    with fitz.open(WORKSPACE / paper) as doc:
        page = doc[page_no - 1]
        height = page.rect.height
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                if text:
                    lines.append((line["bbox"][1] / height, text))
        if len(lines) > 5:
            return "text-layer", tuple(sorted(lines))
        pix = page.get_pixmap(dpi=200)
    tsv = subprocess.run([TESSERACT, "stdin", "stdout", "--psm", "4", "tsv"], input=pix.tobytes("png"),
                         capture_output=True).stdout.decode("utf-8", "replace")
    rows: dict[tuple, list] = {}
    for row in tsv.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        rows.setdefault((c[2], c[3], c[4]), [int(c[7]) / pix.height, []])[1].append(c[11])
    return "tesseract", tuple(sorted((y, " ".join(words)) for y, words in rows.values()))


def heading_above(paper: str, block: dict):
    src = block.get("source") or {}
    page_no, box = src.get("pdfPage"), src.get("boundingBox")
    if not page_no or not box:
        return None
    kind, lines = page_lines(paper, page_no)
    above = [(y, t, HEADING.match(t)) for y, t in lines if y <= box[0] + 0.01 and HEADING.match(t)]
    if not above:
        return None
    y, text, m = above[-1]
    first = int(m[1])
    last = int(m[2]) if m[2] else first
    return {"pdfPage": page_no, "y": round(y, 4), "text": text, "numbers": (first, last), "lines": kind}


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def group_text(group: dict) -> str:
    parts = [group.get("context") or "", group.get("instruction") or ""]
    parts += [o.get("label") or "" for o in group.get("options") or []]
    for q in group.get("questions", []):
        parts.append(q.get("prompt") or "")
        parts += [o.get("label") or "" for o in q.get("options") or []]
    return norm(" ".join(parts))


def letter_list(text: str) -> list[dict] | None:
    """Parse "A Kanayo F. Nwanze\\nB Sophia Murphy" or "A trees B endangered species" into options."""
    tokens = re.findall(r"\S+", text)
    options: list[dict] = []
    expected = "A"
    for tok in tokens:
        bare = re.sub(r"[_~\-—.:]+$", "", tok)
        letter = bare if re.fullmatch(r"[A-L]", bare) else LETTER_MISREAD.get(bare)
        if letter == expected:
            options.append({"value": letter, "words": []})
            expected = chr(ord(expected) + 1)
        elif options:
            options[-1]["words"].append(tok)
        else:
            return None
    if len(options) < 2 or any(not o["words"] for o in options):
        return None
    out = []
    for o in options:
        label = re.sub(r"^[_~\-—.:\s]+", "", " ".join(o["words"])).strip()
        if len(o["words"]) > 14:  # a sentence, not an option label: the list is not clean
            return None
        out.append({"value": o["value"], "label": split_words(label)})
    return out


def inside(box: list, asset: dict | None, page_no: int) -> bool:
    if not asset or asset.get("sourcePdfPage") != page_no or not asset.get("boundingBox"):
        return False
    a = asset["boundingBox"]
    return box[0] >= a[0] - 0.01 and box[2] <= a[2] + 0.01


def target_group(passage: dict, heading: dict, block: dict) -> dict | None:
    first, last = heading["numbers"]
    for g in passage.get("groups", []):
        numbers = [q["number"] for q in g.get("questions", [])]
        if numbers and min(numbers) <= first <= max(numbers):
            return g
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int)
    ap.add_argument("--test", type=int)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    totals = {"removed": 0, "options": 0, "context": 0, "asset": 0, "covered": 0}
    for path in sorted(ROOT.glob("c*/test-*/reading.json")):
        book, test = int(path.parent.parent.name[1:]), int(path.parent.name.split("-")[1])
        if (args.book and book != args.book) or (args.test and test != args.test):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        paper = data["sources"]["paper"]["path"]
        changes = []
        for passage in data.get("passages", []):
            numbers = [q["number"] for g in passage.get("groups", []) for q in g.get("questions", [])]
            if not numbers:
                continue
            keep = []
            for index, block in enumerate(passage.get("blocks", [])):
                location = f"passage {passage.get('number')} block {index + 1}"
                why = visual_removal(book, test, block)
                if why or edge_fragment(block):
                    entry = {"skill": "reading", "location": location, "method": METHOD, "original": block,
                             "rules": ["assistant-visual" if why else "page-edge-fragment"], "movedTo": None}
                    if why:
                        ev = render(book, test, location)
                        entry.update(reviewMethod="assistant-visual", rationale=why, evidenceImageSha256=ev["sha256"],
                                     sourcePdfPage=ev["pdfPage"], evidenceBoundingBox=ev["boundingBox"])
                    changes.append(entry)
                    totals["removed"] += 1
                    print(f"c{book} t{test} P{passage.get('number')} b{index + 1}".ljust(16), "-> removed", entry["rules"][0], repr(block.get("text", "")[:40]))
                    continue
                heading = heading_above(paper, block)
                if not heading or not (min(numbers) <= heading["numbers"][0] <= max(numbers)):
                    keep.append(block)
                    continue
                group = target_group(passage, heading, block)
                text = block.get("text") or ""
                have = group_text(group) if group else ""
                missing = [l for l in text.split("\n")
                           if len(norm(l)) >= 4 and norm(re.sub(r"^\W*(?:[A-L]|\d{1,2})?[\W_]+", "", l))[:25] not in have]
                destination = None
                box = block["source"].get("boundingBox") or [0, 0, 0, 0]
                per_question = any(q.get("options") for q in group.get("questions", [])) if group else False
                if group is not None and missing and not per_question:
                    valid = [o for o in group.get("options") or []
                             if not re.match(r"(h?oose|choose|write)\b", (o.get("label") or "").strip(), re.I)]
                    parsed = None if len(valid) >= 2 or str(group.get("type", "")).startswith("multiple") else letter_list(text)
                    if parsed:
                        for o in parsed:
                            o["source"] = {"pdfPage": block["source"].get("pdfPage"), "method": METHOD, "boundingBox": box,
                                           "fromBlock": f"passage {passage.get('number')} block {index + 1}"}
                        group["options"] = parsed
                        destination = {"group": group["id"], "field": "options"}
                        totals["options"] += 1
                    elif inside(box, group.get("asset"), block["source"].get("pdfPage")):
                        destination = {"group": group["id"], "field": "asset", "note": "region shown in the group image"}
                        totals["asset"] += 1
                    else:
                        extra = "\n".join(missing).strip()
                        group["context"] = f"{(group.get('context') or '').rstrip()}\n\n{extra}".strip()
                        destination = {"group": group["id"], "field": "context", "appended": extra}
                        totals["context"] += 1
                elif group is not None:
                    note = "question options already stored per question" if per_question and missing else "content already in group"
                    destination = {"group": group["id"], "field": None, "note": note}
                    totals["covered"] += 1
                totals["removed"] += 1
                where = f"c{book} t{test} P{passage.get('number')} b{index + 1}"
                print(f"{where:<16} -> {destination and destination['group']} {destination and destination['field']}"
                      f"  [{heading['text'][:22]} @ y={heading['y']}]  {text[:70]!r}")
                changes.append({"skill": "reading", "location": f"passage {passage.get('number')} block {index + 1}",
                                "method": METHOD, "rules": ["question-page-block"], "original": block,
                                "evidence": heading, "movedTo": destination})
            passage["blocks"] = keep
        if changes and args.write:
            backup = WORKSPACE / ".cache" / "data-backup" / path.parent.relative_to(ROOT) / "reading.json"
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log_path = path.parent / "ocr-cleanup.json"
            log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {
                "schemaVersion": 1, "description": "Machine OCR clean-up log. Not a human or visual review; needsReview and verified flags are unchanged.", "changes": []}
            log["changes"].extend({**c, "date": date.today().isoformat(), "script": "scripts/resegment_passages.py",
                                   "paperSha256": data["sources"]["paper"].get("sha256")} for c in changes)
            log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("applied" if args.write else "dry run"), totals)


if __name__ == "__main__":
    main()
