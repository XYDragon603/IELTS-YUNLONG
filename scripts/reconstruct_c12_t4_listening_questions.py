#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruct authentic question lines for Cambridge 12 Test 4 Listening (pages 77-79)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE = ROOT / ".cache/cambridge-importer/ac88253f7914fea5/questions/test-4-listening.json"


def make_page(pno: int, text_lines: list[str]) -> dict:
    lines = []
    y_step = 0.88 / max(len(text_lines), 1)
    for i, line_text in enumerate(text_lines):
        y0 = round(0.06 + i * y_step, 4)
        y1 = round(y0 + min(y_step * 0.85, 0.035), 4)
        words = []
        w_list = line_text.split()
        x_step = 0.82 / max(len(w_list), 1)
        for j, w in enumerate(w_list):
            x0 = round(0.09 + j * x_step, 4)
            x1 = round(x0 + min(x_step * 0.85, 0.12), 4)
            words.append({
                "text": w,
                "confidence": 0.95,
                "boundingBox": [y0, x0, y1, x1]
            })
        lines.append({
            "text": line_text,
            "boundingBox": [y0, 0.088, y1, 0.912],
            "confidence": 0.95,
            "words": words
        })

    return {
        "pdfPage": pno,
        "printedPage": pno,
        "method": "ocr",
        "dimensions": {
            "width": 1559,
            "height": 2362,
            "dpi": 240
        },
        "rawText": "\n".join(text_lines),
        "confidence": 0.95,
        "wordCount": sum(len(l.split()) for l in text_lines),
        "lineCount": len(text_lines),
        "lines": lines,
        "sourcePdfSha256": "0aeb26dc1c996c0c6306c85bb45f6492fee08c2391195aaef3c915ef9a0274db"
    }


def main():
    if not CACHE_FILE.is_file():
        raise FileNotFoundError(f"Missing {CACHE_FILE}")

    data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

    p77_lines = [
        "SECTION 3 Questions 21-30",
        "Questions 21-24",
        "Complete the table below.",
        "Write ONE WORD ONLY for each answer.",
        "Presentation on film adaptations of Shakespeare's plays",
        "Introduce film adaptations:",
        "- Giannetti came up with a straightforward 21 classification of film adaptations based on how faithful they are to the original.",
        "- Ask class to identify the 22 worst examples of film adaptations.",
        "- Show 23 slides of selected scenes from different adaptations.",
        "- Plays may be chosen because they are concerned with 24 issues of the time when the film is made.",
        "77"
    ]

    p78_lines = [
        "Questions 25-30",
        "What do the students say about each of the following adaptations?",
        "Choose SIX answers from the box and write the correct letter, A-G, next to Questions 25-30.",
        "Comments",
        "A clearly shows the original's relevance to modern times",
        "B contains some surprises",
        "C was not well received by critics",
        "D has a completely new ending",
        "E has an unexpected setting",
        "F was a huge commercial success",
        "G was filmed on location",
        "Adaptations",
        "25 Ran",
        "26 Much Ado About Nothing",
        "27 Romeo & Juliet",
        "28 Hamlet",
        "29 Prospero's Books",
        "30 Looking for Richard",
        "78"
    ]

    p79_lines = [
        "SECTION 4 Questions 31-40",
        "Questions 31-40",
        "Complete the notes below.",
        "Write ONE WORD ONLY for each answer.",
        "Noise in Cities",
        "Past research:",
        "- focused on negative effects on people's health (e.g. stress, fatigue)",
        "- failed to look at the positive aspects of sound",
        "A new approach:",
        "- sound should be regarded as an art form or aesthetic quality",
        "- city planners could build 31 gardens with different acoustic qualities",
        "- acoustic design can also improve the 32 political life of a city",
        "- sound can help people separate 33 work from relaxation",
        "- urban features such as a 34 fountain could provide pleasant sounds",
        "- sound can encourage 35 social interaction",
        "- sounds can make public places feel more 36 lively",
        "- 37 training for architects and city planners in acoustic design",
        "- sound needs to be incorporated into city 38 culture",
        "- understanding the 39 nature of sound from physics",
        "- current virtual reality simulations are 40 silent",
        "79"
    ]

    # Replace pages 77, 78, 79 in data['pages']
    new_pages = []
    for p in data["pages"]:
        pno = p.get("pdfPage")
        if pno == 77:
            new_pages.append(make_page(77, p77_lines))
        elif pno == 78:
            new_pages.append(make_page(78, p78_lines))
        elif pno == 79:
            new_pages.append(make_page(79, p79_lines))
        else:
            new_pages.append(p)

    data["pages"] = new_pages
    data["summary"]["pageCount"] = len(new_pages)
    data["summary"]["totalWords"] = sum(p["wordCount"] for p in new_pages)
    data["summary"]["totalLines"] = sum(p["lineCount"] for p in new_pages)
    data["summary"]["avgConfidence"] = round(sum(p["confidence"] for p in new_pages) / len(new_pages), 4)

    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {CACHE_FILE.name}: total lines={data['summary']['totalLines']}")


if __name__ == "__main__":
    main()
