#!/usr/bin/env python3
"""Repair only inverted C15 listening answer coordinates from local answer-page OCR."""
import json
import re
import sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ocr_extractor import extract_page_ocr, get_tesseract_cmd


def valid_box(box):
    return (isinstance(box, list) and len(box) == 4
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in box)
            and box[0] < box[2] and box[1] < box[3])


def find_boxes(lines, questions):
    boxes = {}
    for line in lines:
        words = line["words"]
        for i, word in enumerate(words):
            match = re.fullmatch(r"(\d{2})[.,]?", word["text"])
            if not match or int(match[1]) not in questions or word["boundingBox"][1] < .4:
                continue
            number = int(match[1])
            chosen = [w for w in words[i:i + 5] if w["boundingBox"][1] < .8]
            if len(chosen) < 2 or number in boxes:
                raise ValueError(f"Q{number}: OCR answer row is ambiguous")
            box = [round(min(w["boundingBox"][0] for w in chosen) - .002, 4),
                   round(min(w["boundingBox"][1] for w in chosen) - .002, 4),
                   round(max(w["boundingBox"][2] for w in chosen) + .002, 4),
                   round(max(w["boundingBox"][3] for w in chosen) + .002, 4)]
            if not valid_box(box):
                raise ValueError(f"Q{number}: OCR returned invalid box {box}")
            boxes[number] = box
    if set(boxes) != set(questions):
        raise ValueError(f"OCR did not uniquely locate {sorted(set(questions) - set(boxes))}")
    return boxes


def main():
    planned = []
    for test in range(1, 5):
        directory = ROOT / f"resources/cambridge/c15/test-{test}"
        cur_path, lis_path = directory / "curations.json", directory / "listening.json"
        cur_raw, lis_raw = cur_path.read_bytes(), lis_path.read_bytes()
        cur, listening = json.loads(cur_raw), json.loads(lis_raw)
        bad = {c["question"] for c in cur["curations"] if c.get("skill") == "listening"
               and c.get("target") == "answer" and not valid_box(c.get("evidenceBoundingBox"))}
        expected = 16 if test == 3 else 10
        if not bad:
            print(f"C15 T{test}: answer boxes already valid")
            continue
        if len(bad) != expected:
            raise ValueError(f"C15 T{test}: expected {expected} inverted answer boxes, found {len(bad)}")
        page = listening["sources"]["answerPdfPages"][0]
        with fitz.open(ROOT / listening["sources"]["paper"]["path"]) as pdf:
            lines = extract_page_ocr(pdf, page - 1, get_tesseract_cmd(), dpi=240)["lines"]
        boxes = find_boxes(lines, bad)
        for c in cur["curations"]:
            if c.get("skill") == "listening" and c.get("target") == "answer" and c.get("question") in boxes:
                c["evidenceBoundingBox"] = boxes[c["question"]]
                c["boundingBoxMethod"] = "local-tesseract-tsv-240dpi"
        changed = set()
        for part in listening["parts"]:
            for question in part["questions"]:
                n = question["number"]
                if n in boxes:
                    question["answer"]["boundingBox"] = boxes[n]
                    changed.add(n)
        if changed != bad:
            raise ValueError(f"C15 T{test}: question references do not match curations")
        planned.extend([(cur_path, cur_raw, cur), (lis_path, lis_raw, listening)])
        print(f"C15 T{test}: {len(bad)} answer regions located on PDF page {page}")
    if not planned:
        return
    backup = ROOT / ".cache/cambridge-importer/c15-curation-box-backup"
    backup.mkdir(parents=True, exist_ok=True)
    # Preserve the exact pre-repair source for rollback; never overwrite a prior backup.
    for path, raw, _ in planned:
        copy = backup / f"test-{path.parent.name.split('-')[-1]}-{path.name}"
        if not copy.exists():
            copy.write_bytes(raw)
    for path, _, payload in planned:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
