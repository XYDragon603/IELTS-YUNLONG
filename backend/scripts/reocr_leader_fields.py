"""Re-OCR reading text fields whose OCR was corrupted by dotted answer lines.

Gap-fill items print a dotted line where the answer goes. Tesseract reads those
dots as letter noise and, as a side effect, scrambles the case of neighbouring
words ("Grow StrAWDEITIES, ......oeerenen ANd herbs"). This script re-renders
each affected field from its own source page and bounding box, erases the
leader dots, runs Tesseract again, and puts a "______" placeholder where each
dotted line was.

The new text is kept only when it scores better than the old one (fewer OCR
noise hits, higher share of known words). Every accepted change is logged in
<test>/ocr-cleanup.json with the original text, the new text, page, bounding
box, DPI, Tesseract version and source PDF hash. This is still machine OCR:
needsReview / verified flags are not changed and nothing is marked reviewed.

Usage:
  python scripts/reocr_leader_fields.py --book 18 --test 1      # dry run for one test
  python scripts/reocr_leader_fields.py                          # dry run, all tests
  python scripts/reocr_leader_fields.py --write                  # apply and log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_ocr_text import check  # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / "resources" / "cambridge"
TESSERACT = shutil.which("tesseract") or r"C:/Program Files/Tesseract-OCR/tesseract.exe"
DPI = 300
BLANK = "______"
METHOD = "ocr-leader-stripped"
FIXES = [
    (re.compile(r"\bAND[I1l]OR\b"), "AND/OR"),
    (re.compile(r"^(\d+\.?\s+)?[‘'’]\s*(?=[A-Z])", re.M), r"\1"),          # stray quote before a capital
    (re.compile(r"[ \t]*[.…·]+[ \t]*(?=" + BLANK + ")"), " "),              # dot fragments before a blank
    (re.compile(r"[ \t]+([,;:])(?=[ \t]*" + BLANK + ")"), r"\1"),           # keep "word, ______" tight
    (re.compile("(" + BLANK + r")[ \t]*[.…·]+(?=[ \t]*$)", re.M), r"\1."),    # blank ends the sentence
    (re.compile("(" + BLANK + r")[ \t]*[.…·]+[ \t]+"), r"\1 "),             # dot fragments after a blank
]


def tesseract_version() -> str:
    out = subprocess.run([TESSERACT, "--version"], capture_output=True, text=True, encoding="utf-8")
    return (out.stdout or out.stderr).splitlines()[0].strip()


def strip_leaders(gray: np.ndarray, dpi: int):
    """Erase small specks that sit in horizontal runs (leader dots). Returns image and dot-run boxes."""
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(bw, 8)
    s = dpi / 300
    small = [i for i in range(1, n)
             if stats[i, cv2.CC_STAT_AREA] <= 40 * s * s and stats[i, cv2.CC_STAT_WIDTH] <= 8 * s and stats[i, cv2.CC_STAT_HEIGHT] <= 8 * s]
    out = gray.copy()
    # Leaders printed as touching dots (or a solid rule) form one long, flat component.
    flat_runs = []
    for i in range(1, n):
        w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if w >= 60 * s and h <= 7 * s:
            out[labels == i] = 255
            x, y = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
            flat_runs.append({"x0": float(x), "x1": float(x + w), "y": float(y + h / 2)})
    if len(small) < 3:
        return out, flat_runs
    pts = np.array([centroids[i] for i in small])
    dots = []
    for k, i in enumerate(small):
        dy, dx = np.abs(pts[:, 1] - pts[k, 1]), np.abs(pts[:, 0] - pts[k, 0])
        if ((dy < 3 * s) & (dx > 0) & (dx < 25 * s)).sum() >= 2:
            out[labels == i] = 255
            dots.append(pts[k])
    # Cluster removed dots into runs (same baseline, small gaps).
    runs = []
    for x, y in sorted(dots, key=lambda p: (round(p[1] / (6 * s)), p[0])):
        if runs and abs(runs[-1]["y"] - y) < 4 * s and x - runs[-1]["x1"] < 30 * s:
            runs[-1]["x0"], runs[-1]["x1"] = min(runs[-1]["x0"], x), max(runs[-1]["x1"], x)
        else:
            runs.append({"x0": x, "x1": x, "y": y})
    return out, [r for r in runs if r["x1"] - r["x0"] > 40 * s] + flat_runs


def ocr_lines(image: np.ndarray, runs: list[dict]):
    """Run Tesseract TSV and rebuild lines, inserting BLANK where a dot run sat."""
    ok, png = cv2.imencode(".png", image)
    tsv = subprocess.run([TESSERACT, "stdin", "-", "--psm", "6", "-l", "eng", "tsv"], input=png.tobytes(),
                         capture_output=True).stdout.decode("utf-8", "replace")
    words, confs = [], []
    for row in tsv.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or not cols[11].strip():
            continue
        left, top, width, height, conf = map(float, (cols[6], cols[7], cols[8], cols[9], cols[10]))
        words.append({"key": (int(cols[2]), int(cols[3]), int(cols[4])), "x0": left, "x1": left + width,
                      "top": top, "bottom": top + height, "h": height, "text": cols[11]})
        if conf >= 0:
            confs.append(conf)
    lines: dict[tuple, list] = {}
    for w in words:
        lines.setdefault(w["key"], []).append(w)
    ordered = sorted(lines.values(), key=lambda ws: min(w["top"] for w in ws))
    spans = [(min(w["top"] for w in ws), max(w["bottom"] for w in ws), max(w["h"] for w in ws)) for ws in ordered]
    tokens = [[(w["x0"], w["text"]) for w in ws] for ws in ordered]
    for run in runs:
        if not spans:
            break
        # Dot runs sit on the baseline: pick the line whose box contains the run, else the nearest line.
        inside = [i for i, (top, bottom, h) in enumerate(spans) if top - 0.2 * h <= run["y"] <= bottom + 0.4 * h]
        i = inside[0] if inside else min(range(len(spans)), key=lambda k: abs(spans[k][1] - run["y"]))
        tokens[i].append((run["x0"], BLANK))
    text_lines = [" ".join(t for _, t in sorted(line)) for line in tokens]
    text = "\n".join(text_lines)
    for rx, repl in FIXES:
        text = rx.sub(repl, text)
    return text, (sum(confs) / len(confs) / 100 if confs else None)


def load_vocabulary() -> set[str]:
    words: set[str] = set()
    token = re.compile(r"[A-Za-z]{3,}")
    for path in ROOT.glob("c*/test-*/reading.json"):
        for p in json.loads(path.read_text(encoding="utf-8")).get("passages", []):
            for b in p.get("blocks", []):
                words.update(t.lower() for t in token.findall(b.get("text") or ""))
    return words


def score(text: str, vocabulary: set[str]) -> tuple[int, float]:
    tokens = re.findall(r"[A-Za-z]{3,}", text)
    known = sum(t.lower() in vocabulary and (t.islower() or t.isupper() or t.istitle()) for t in tokens)
    return len(check(text)), known / len(tokens) if tokens else 0.0


def slots(data: dict):
    for p in data.get("passages", []):
        for g in p.get("groups", []):
            yield f"group {g.get('id')} context", g, "context"
            for q in g.get("questions", []):
                yield f"Q{q.get('number')} prompt", q, "prompt"


SHORT_WORDS = {"a", "i", "it", "is", "in", "on", "of", "to", "an", "as", "at", "by", "be", "or", "we", "he", "up", "can", "not", "has", "the"}
BULLET = re.compile(r"^(?:[e©¢*•®]\s*[—–-]?|[—–]\s*)\s+(?:\|\s*)?(?=\S)", re.M)
DOT_RUN = re.compile(r"[.…·]{3,}")


def repair(after: str, before: str, vocabulary: set[str]) -> str:
    """Tidy the new OCR using only evidence already in the text or the previous OCR."""
    after = re.sub(r"(?:" + BLANK + r"[ \t]*){2,}", BLANK + " ", after).replace(BLANK + " \n", BLANK + "\n").rstrip(" ")
    after = BULLET.sub("• ", after)
    after = re.sub(r"^([A-H]|[ivx]{1,4})[ \t]*[_|]+[ \t]*(?=\S)", r"\1 ", after, flags=re.M)  # "A __ text" option labels
    after = re.sub(r"[ \t]+\|[ \t]*$", "", after, flags=re.M)                         # table-rule residue at line end
    after = re.sub(r"([A-Za-z])(\d{1,2}[ \t]+" + BLANK + ")", r"\1 \2", after)        # "how5 ______"
    after = re.sub("(" + BLANK + r")[ \t]*[‘’'`]+[ \t]*$", r"\1", after, flags=re.M)  # stray quote after a blank
    known = vocabulary | SHORT_WORDS

    def split(match: re.Match) -> str:
        token = match.group(0)
        if token.lower() in known:
            return token
        for k in range(1, len(token)):
            left, right = token[:k], token[k:]
            if left.lower() in known and right.lower() in known and \
                    re.search(r"\b%s\s+%s\b" % (re.escape(left), re.escape(right)), before, re.I):
                return f"{left} {right}"  # previous OCR had the two words apart
        return token

    return re.sub(r"[A-Za-z]{3,}", split, after)


def render(doc: fitz.Document, source: dict):
    page = doc[source["pdfPage"] - 1]
    ymin, xmin, ymax, xmax = source["boundingBox"]
    r = page.rect
    pad_y, pad_x = 0.004, 0.01
    clip = fitz.Rect(r.width * max(0, xmin - pad_x), r.height * max(0, ymin - pad_y),
                     r.width * min(1, xmax + pad_x), r.height * min(1, ymax + pad_y))
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int)
    ap.add_argument("--test", type=int)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", type=int, default=6, help="number of before/after examples to print")
    ap.add_argument("--report", help="write every proposed change (before/after) to this JSON file")
    args = ap.parse_args()

    vocabulary, version = load_vocabulary(), tesseract_version()
    totals = {"flagged": 0, "accepted": 0, "rejected": 0, "skipped": 0}
    examples = []
    for path in sorted(ROOT.glob("c*/test-*/reading.json")):
        book, test = int(path.parent.parent.name[1:]), int(path.parent.name.split("-")[1])
        if (args.book and book != args.book) or (args.test and test != args.test):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        paper = data.get("sources", {}).get("paper", {})
        pdf_path = WORKSPACE / paper.get("path", "")
        changes = []
        doc = None
        for location, container, key in slots(data):
            before = container.get(key)
            source = container.get("source") or {}
            if not isinstance(before, str) or not check(before):
                continue
            totals["flagged"] += 1
            if source.get("method") not in ("ocr", METHOD) or not source.get("pdfPage") or not source.get("boundingBox") or not pdf_path.is_file():
                totals["skipped"] += 1
                continue
            doc = doc or fitz.open(pdf_path)
            image, runs = strip_leaders(render(doc, source), DPI)
            after, confidence = ocr_lines(image, runs)
            after = repair(after, before, vocabulary)
            old, new = score(before, vocabulary), score(after, vocabulary)
            # A region that grew by several lines picked up neighbouring text (e.g. a whole table).
            extra_lines = after.count("\n") - before.count("\n")
            too_long = extra_lines > (1 if key == "prompt" else 2)
            # Every dotted run in the old text is an answer gap; the new text must keep a blank for each.
            lost_blank = after.count(BLANK) < len(DOT_RUN.findall(before))
            if not after.strip() or too_long or lost_blank or new[0] > old[0] or (new[0] == old[0] and new[1] <= old[1]):
                totals["rejected"] += 1
                continue
            totals["accepted"] += 1
            changes.append({"skill": "reading", "location": location, "method": METHOD, "original": before, "reocr": after,
                            "sourcePdfPage": source["pdfPage"], "boundingBox": source["boundingBox"], "dpi": DPI,
                            "tesseract": version, "paperSha256": paper.get("sha256"),
                            "score": {"before": {"noiseHits": old[0], "knownWordShare": round(old[1], 3)},
                                      "after": {"noiseHits": new[0], "knownWordShare": round(new[1], 3)}}})
            examples.append((f"c{book} t{test} {location}", before, after))
            container[key] = after
            source["method"], source["confidence"] = METHOD, round(confidence, 4) if confidence is not None else None
        if doc:
            doc.close()
        if changes and args.write:
            backup = WORKSPACE / ".cache" / "data-backup" / path.parent.relative_to(ROOT) / "reading.json"
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log_path = path.parent / "ocr-cleanup.json"
            log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {
                "schemaVersion": 1, "description": "Machine re-OCR log. Not a human or visual review; needsReview and verified flags are unchanged.", "changes": []}
            log["changes"].extend({**c, "date": date.today().isoformat(), "script": "scripts/reocr_leader_fields.py"} for c in changes)
            log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if changes:
            print(f"c{book} t{test}: {len(changes)} field(s) improved")
    print(("applied" if args.write else "dry run"), totals)
    if args.report:
        Path(args.report).write_text(json.dumps([{"where": w, "before": x, "after": y} for w, x, y in examples], ensure_ascii=False, indent=1), encoding="utf-8")
    for where, before, after in examples[:args.show]:
        print(f"\n[{where}]\n  - {before[:220]!r}\n  + {after[:220]!r}")


if __name__ == "__main__":
    main()
