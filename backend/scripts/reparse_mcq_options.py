"""Re-read answer options for multiple-choice reading groups from the source pages.

Many imported multiple-choice groups have no usable options: the stored list is
empty or holds the instruction line misread as an option ("C: hoose the correct
letter"), and the stored context often stops after the question sentence. This
script OCRs the page region from the start of the group to the start of the next
group (possibly across a page break), splits it into question lines ("27 What
is ...") and option lines ("A ...", "B ..."), and stores the options:

  * single-answer groups ("Choose the correct letter, A, B, C or D"): q.options per question
  * multi-answer groups ("Choose TWO letters, A-E"): one shared group.options list

A group is only updated when the parse is complete and consistent: letters in
order from A, the letter count matches the instruction, and every question in a
single-answer group has its own list. Anything else is reported and left as is.
Changes are logged in <test>/ocr-cleanup.json and files are backed up first.
This is machine OCR; needsReview / verified flags are not changed.

Usage:
  python scripts/reparse_mcq_options.py --book 19 --test 4     # dry run for one test
  python scripts/reparse_mcq_options.py                         # dry run, all tests
  python scripts/reparse_mcq_options.py --write                 # apply and log
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import cv2
import fitz
import numpy as np

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / "resources" / "cambridge"
TESSERACT = shutil.which("tesseract") or r"C:/Program Files/Tesseract-OCR/tesseract.exe"
DPI = 300
METHOD = "ocr-mcq-reparse"
LETTERS = "ABCDEFGHI"
MISREAD = {"©": "C", "¢": "C", "(": "C", "0": "D", "O": "D", "8": "B", "|": "I", "l": "I", "1": "I"}
STOP = re.compile(r"^(Questions?\s+\d|Choose\b|Do the following|Complete the|Look at|Write the correct|Reading Passage|Classify|Match)", re.I)


_VOCAB: set[str] | None = None
LEADING = ("a", "i", "it", "he", "she", "we", "they", "an", "the", "can", "how", "to")


def split_words(text: str) -> str:
    """Split OCR merges like 'Hecontrasted', 'Ithas', 'avery' when both parts are known words."""
    global _VOCAB
    if _VOCAB is None:
        # Frequent passage words plus the vocabulary books; rare tokens may themselves be OCR merges.
        from collections import Counter
        counts: Counter = Counter()
        for path in ROOT.glob("c*/test-*/reading.json"):
            for p in json.loads(path.read_text(encoding="utf-8")).get("passages", []):
                for b in p.get("blocks", []):
                    counts.update(t.lower() for t in re.findall(r"[A-Za-z]{2,}", b.get("text") or ""))
        _VOCAB = {w for w, n in counts.items() if n >= 3}
        for path in (WORKSPACE / "resources" / "words").glob("*.json"):
            try:
                book = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for w in book.get("words", []) if isinstance(book, dict) else []:
                if isinstance(w, dict) and isinstance(w.get("word"), str) and w["word"].isalpha():
                    _VOCAB.add(w["word"].lower())

    def fix(m: re.Match) -> str:
        word = m.group(0)
        low = word.lower()
        if low in _VOCAB or any(low.endswith(s) and low[:-len(s)] in _VOCAB for s in ("s", "es", "d", "ed", "ing")):
            return word
        for lead in sorted(LEADING, key=len, reverse=True):
            rest = word[len(lead):]
            base = rest.lower().split("-")[0]
            stems = {base, re.sub(r"(ed|d|s|es|ing)$", "", base)}
            if word.lower().startswith(lead) and len(rest) >= 3 and stems & _VOCAB:
                return f"{word[:len(lead)]} {rest}"
        return word

    text = re.sub(r"\bAl\b", "AI", text)  # artificial intelligence read as "Al"
    return re.sub(r"\b[A-Za-z][a-z]+(?:-[a-z]+)?\b", fix, text)


MCQ_INSTRUCTION = re.compile(r"Choose the correct letter|correct letter, A, B, C or D, in boxes|Write the correct letter in boxes|Choose (TWO|THREE) letters", re.I)
NOT_MCQ = re.compile(r"NB You may use|list of|correct ending|Match each|Look at the following", re.I)


def needs_fix(group: dict) -> bool:
    # Some multiple-choice groups were imported as "unclassified" or "summary-completion".
    context = group.get("context") or ""
    own = re.split(r"\nQuestions?\s+\d", context, maxsplit=1)[0]  # ignore a following group's instruction
    looks_mcq = MCQ_INSTRUCTION.search(own) and not NOT_MCQ.search(own)
    if not (str(group.get("type", "")).startswith("multiple") or looks_mcq):
        return False
    if any(q.get("options") for q in group.get("questions", [])):
        return False
    opts = group.get("options") or []
    values = [o.get("value") for o in opts]
    instruction_like = any(re.match(r"(h?oose|choose|write)\b|which\s+(TWO|THREE)\b", (o.get("label") or "").strip(), re.I) for o in opts)
    return len(opts) < 3 or instruction_like or len(values) != len(set(values))


def expected_letters(context: str) -> tuple[int | None, bool]:
    """(number of letters, multi-answer?) from the instruction text."""
    context = re.split(r"\nQuestions?\s+\d", context, maxsplit=1)[0]
    multi = re.search(r"Choose\s+(TWO|THREE|FOUR)\s+letters", context, re.I) is not None
    m = re.search(r"\bA\s*[-–—]\s*([B-I])\b", context)
    if m:
        return LETTERS.index(m[1]) + 1, multi
    m = re.search(r"A,\s*B,\s*C\s*(?:,\s*D\s*)?(?:or|and)\s*([C-I])\b", context)
    if m:
        return LETTERS.index(m[1]) + 1, multi
    return None, multi


def ocr_region(page: fitz.Page, y0: float, y1: float) -> list[dict]:
    """OCR one vertical band of a page; return lines with text and boxes (0-1 page coords)."""
    r = page.rect
    clip = fitz.Rect(r.width * 0.04, r.height * y0, r.width * 0.97, r.height * y1)
    pix = page.get_pixmap(dpi=DPI, clip=clip, colorspace=fitz.csGRAY)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    ok, png = cv2.imencode(".png", img)
    tsv = subprocess.run([TESSERACT, "stdin", "-", "--psm", "4", "-l", "eng", "tsv"], input=png.tobytes(),
                         capture_output=True).stdout.decode("utf-8", "replace")
    lines: dict[tuple, dict] = {}
    for row in tsv.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        key = (int(c[2]), int(c[3]), int(c[4]))
        left, top, w, h, conf = float(c[6]), float(c[7]), float(c[8]), float(c[9]), float(c[10])
        line = lines.setdefault(key, {"words": [], "x0": left, "y0": top, "x1": left + w, "y1": top + h, "conf": []})
        line["words"].append((left, c[11]))
        line["x0"], line["y0"] = min(line["x0"], left), min(line["y0"], top)
        line["x1"], line["y1"] = max(line["x1"], left + w), max(line["y1"], top + h)
        if conf >= 0:
            line["conf"].append(conf)
    out = []
    for ln in sorted(lines.values(), key=lambda l: (l["y0"], l["x0"])):
        text = " ".join(t for _, t in sorted(ln["words"]))
        to_page = lambda px, py: (y0 + py / pix.height * (y1 - y0), 0.04 + px / pix.width * 0.93)
        a, b = to_page(ln["x0"], ln["y0"])
        c2, d = to_page(ln["x1"], ln["y1"])
        out.append({"text": text, "x0": ln["x0"] / pix.width, "box": [round(a, 4), round(b, 4), round(c2, 4), round(d, 4)],
                    "confidence": round(sum(ln["conf"]) / len(ln["conf"]) / 100, 4) if ln["conf"] else None})
    return out


def option_line(text: str, expected: str, glued: bool = False):
    """Return (letter, label) if text starts with the expected option letter (allowing common misreads).

    With glued=True (mid-sequence) a letter run into its text is accepted too: "DA few", "Eto collect"."""
    m = re.match(r"^\s*([A-I©¢(08|l1O])[\s_|.,:;—–-]+(.+)$", text)
    if not m and glued:
        m = re.match(rf"^\s*({expected})((?:[A-Z]\s|[a-z]{{2,}}\s).+)$", text)
    if not m:
        return None
    letter = MISREAD.get(m[1], m[1]) if m[1] not in LETTERS else m[1]
    if letter != expected:
        return None
    label = re.sub(r"^[_|.,:;\s—–-]+", "", m[2]).strip()
    return (letter, label) if label else None


def parse(lines: list[dict], numbers: list[int], count: int, multi: bool):
    """Split OCR lines into {question number: [options]} (or shared list under key 0 for multi)."""
    result: dict[int, list[dict]] = {}
    current: int | None = 0 if multi else None
    for ln in lines:
        text = ln["text"].strip()
        if not text:
            continue
        qm = re.match(r"^(\d{1,2})(?:[\s.,]+\S|\s*$)", text)  # "27 What", "38.What" or a bare "32"
        if qm and not multi:
            n = int(qm[1])
            upcoming = [k for k in numbers if current is None or k > current]
            if n not in numbers and upcoming and n % 10 == upcoming[0] % 10 and (current is None or len(result.get(current, [])) == count):
                n = upcoming[0]  # misread tens digit, e.g. "45" for 15 right after question 14
            if n in upcoming:
                current = n
                result.setdefault(current, [])
                continue
        if current is None:
            continue
        opts = result.setdefault(current, [])
        if len(opts) < count:
            hit = option_line(text, LETTERS[len(opts)], glued=bool(opts))
            if hit:
                opts.append({"value": hit[0], "label": hit[1], "source": {"box": ln["box"], "confidence": ln["confidence"]}})
                continue
        if opts and STOP.match(text):
            if multi or current == numbers[-1]:
                break
            continue
        if opts and len(opts) <= count and re.match(r"^[a-z(‘'“\"]", text) and opts[-1].get("wraps", 0) < 2:
            # A wrapped option continues mid-sentence, so it starts in lower case.
            opts[-1]["label"] = f"{opts[-1]['label']} {text}"
            opts[-1]["wraps"] = opts[-1].get("wraps", 0) + 1
            continue
        if opts and len(opts) == count and (multi or current == numbers[-1]):
            break  # all options read; anything else belongs to the next section
    return result


def region_lines(doc: fitz.Document, group: dict, nxt: dict | None) -> list[dict]:
    src = group.get("source") or {}
    page_no = src.get("pdfPage")
    if not page_no or not src.get("boundingBox"):
        return []
    start_y = max(0.0, src["boundingBox"][0] - 0.01)
    nsrc = (nxt or {}).get("source") or {}
    lines = []
    for offset in (0, 1):  # a group can continue onto the next page
        pno = page_no + offset
        if pno > len(doc):
            break
        y0 = start_y if offset == 0 else 0.04
        y1 = 0.96
        if nsrc.get("pdfPage") == pno and nsrc.get("boundingBox") and nsrc["boundingBox"][0] > y0:
            y1 = nsrc["boundingBox"][0]
        band = ocr_region(doc[pno - 1], y0, y1)
        for ln in band:
            ln["pdfPage"] = pno
        lines += band
        if y1 < 0.96:
            break
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int)
    ap.add_argument("--test", type=int)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    fixed = failed = 0
    for path in sorted(ROOT.glob("c*/test-*/reading.json")):
        book, test = int(path.parent.parent.name[1:]), int(path.parent.name.split("-")[1])
        if (args.book and book != args.book) or (args.test and test != args.test):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        groups = [g for p in data.get("passages", []) for g in p.get("groups", [])]
        targets = [i for i, g in enumerate(groups) if needs_fix(g)]
        if not targets:
            continue
        changes = []
        with fitz.open(WORKSPACE / data["sources"]["paper"]["path"]) as doc:
            for i in targets:
                g, nxt = groups[i], groups[i + 1] if i + 1 < len(groups) else None
                numbers = sorted(q["number"] for q in g["questions"])
                count, multi = expected_letters(g.get("context") or "")
                lines = region_lines(doc, g, nxt)
                if count is None and lines:
                    count, multi2 = expected_letters("\n".join(l["text"] for l in lines[:6]))
                    multi = multi or multi2
                parsed = parse(lines, numbers, count or 4, multi) if lines else {}
                keys = [0] if multi else numbers
                good = count is not None and all(
                    len(parsed.get(k, [])) == count and [o["value"] for o in parsed[k]] == list(LETTERS[:count]) for k in keys)
                where = f"c{book} t{test} {g['id']}"
                if not good:
                    failed += 1
                    print(f"SKIP {where}: count={count} multi={multi} parsed={ {k: len(v) for k, v in parsed.items()} }")
                    if args.verbose:
                        print("   " + "\n   ".join(l["text"] for l in lines[:30]))
                    continue
                fixed += 1
                def tidy(o):
                    label = re.sub(r"^(?:l\||\||lI)(?=[a-zA-Z])", "I", o["label"])  # "l|ts", "lIt" -> "Its", "It"
                    label = re.sub(r"^I(?=[A-Z][a-z])", "", label)
                    label = re.sub(r"^lt(?=[a-z]*\b)", "It", label)                       # "lt is", "ltis"
                    label = re.sub(r"\bI\|t", "It", label)                                    # "I|tleads"
                    label = re.sub(r"\b(It|it|[Cc]an)(is|be)\b", r"\1 \2", label)                # "Itis", "canbe"
                    label = re.sub(r"\b([A-Z]{2,})(has|is|was)\b", r"\1 \2", label)           # "USAhas"
                    label = re.sub(r"(?<=[a-z])\.(?=[a-z])", " ", label)                      # "that.can"
                    label = re.sub(r"(?<!\S)/l(?=[a-z])", "Il", label)                        # "/liad" -> "Iliad"
                    label = re.sub(r"^arising (?=number\b)", "a rising ", label)              # "a rising number"
                    if o["source"]["box"][2] > 0.85:  # last lines on the page: drop the page footer
                        label = re.split(r"\s+(?=\S{0,4}\s?p\.?\s?\d{2,3}\b)", label)[0]           # "[© p. 123] 47 Test 2"
                        label = re.sub(r"\s+\d{1,3}(?:\s+(?:Reading|Reaaing|Listening|Test\s*\d))?\s*$", "", label)
                        tail = re.search(r"([.?!])\s+(\S.*)$", label)
                        if tail and not re.search(r"\b[a-z]{3,}\b", tail[2]):                    # ". RO & | Fe 2 407 Reaaing"
                            label = label[:tail.start(2)].rstrip()
                    return split_words(label.strip())

                def build(opts):
                    labels = [tidy(o) for o in opts]
                    if any(re.match(r"Its?\b", l) for l in labels):  # sentence options: "it was" -> "It was"
                        labels = [re.sub(r"^(its?)\b", lambda m: m[1].capitalize(), l) for l in labels]
                    return [{"value": o["value"], "label": label,
                             "source": {"pdfPage": next(l["pdfPage"] for l in lines if l["box"] == o["source"]["box"]),
                                        "method": METHOD, "boundingBox": o["source"]["box"], "confidence": o["source"]["confidence"]}}
                            for o, label in zip(opts, labels)]
                before = {"groupOptions": g.get("options"), "questionOptions": {q["number"]: q.get("options") for q in g["questions"]}}
                if multi:
                    g["options"] = build(parsed[0])
                    for q in g["questions"]:
                        q.pop("options", None)
                else:
                    g["options"] = []
                    for q in g["questions"]:
                        q["options"] = build(parsed[q["number"]])
                after = {"groupOptions": g.get("options"), "questionOptions": {q["number"]: q.get("options") for q in g["questions"]}}
                changes.append({"skill": "reading", "location": f"group {g['id']} options", "method": METHOD,
                                "original": before, "reparsed": after, "dpi": DPI,
                                "paperSha256": data["sources"]["paper"].get("sha256")})
                print(f"OK   {where}: {'shared' if multi else 'per question'} {count} options")
                if args.verbose:
                    for q in ([None] if multi else g["questions"]):
                        for o in (g["options"] if q is None else q["options"]):
                            print(f"     {q['number'] if q else 'shared'} {o['value']} {o['label']}")
        if changes and args.write:
            backup = WORKSPACE / ".cache" / "data-backup" / path.parent.relative_to(ROOT) / "reading.json"
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log_path = path.parent / "ocr-cleanup.json"
            log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {
                "schemaVersion": 1, "description": "Machine OCR clean-up log. Not a human or visual review; needsReview and verified flags are unchanged.", "changes": []}
            log["changes"].extend({**c, "date": date.today().isoformat(), "script": "scripts/reparse_mcq_options.py"} for c in changes)
            log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("applied" if args.write else "dry run"), {"fixed": fixed, "skipped": failed})


if __name__ == "__main__":
    main()
