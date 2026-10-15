"""Flag suspicious OCR text in imported Cambridge JSON (read-only).

Scans reading prompts / group context / passage blocks, writing prompts,
speaking questions and listening prompts for common OCR failure patterns.
Writes a JSON report; never modifies resources.

Usage:
  python scripts/audit_ocr_text.py [--out artifacts/ocr-text-audit.json] [--book 18] [--test 1]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / "resources" / "cambridge"

# Each rule: (code, description, regex). Order matters only for reporting.
RULES = [
    ("dot-leader-garble", "dotted answer line read as letters", re.compile(r"[.…]{3,}[a-z]{4,}|[a-z]*(?:en|em|ne|me|nn|ee){4,}[a-z]*", re.I)),
    ("mixed-case-word", "word with random capitals", re.compile(r"\b(?=[A-Za-z]*[a-z][A-Z])(?=[A-Za-z]*[A-Z]{2})[A-Za-z]{5,}\b")),
    ("repeated-char", "same character 4+ times", re.compile(r"([A-Za-z])\1{3,}")),
    ("stray-symbols", "OCR symbol noise", re.compile(r"[|¢©®§]|[~^`]{2,}|\\[a-z]")),  # £ € ¥ are legitimate currency
    ("broken-hyphen", "word split by hyphen and space", re.compile(r"\b[a-z]{2,}- [a-z]{2,}\b")),
    ("digit-in-word", "digit inside a word (l/1, O/0 confusion)", re.compile(r"\b[a-z]+[0-9][a-z]+\b|\b[a-z]{2,}[0-9]\b", re.I)),
]
# Common legitimate tokens that trip digit-in-word.
DIGIT_OK = re.compile(r"^(?:\d+(?:st|nd|rd|th|s|am|pm|km|kg|cm|mm|m|g|ml|mph)|[A-Z]\d+|\d+[A-Z]|co2|mp3|covid19)$", re.I)


def check(text: str) -> list[dict]:
    hits = []
    for code, desc, rx in RULES:
        for m in rx.finditer(text):
            token = m.group(0)
            if code == "digit-in-word" and DIGIT_OK.match(token):
                continue
            hits.append({"rule": code, "match": token[:60]})
    return hits


def fields(skill: str, data: dict):
    """Yield (location, text) for user-visible text fields of one skill file."""
    if skill == "reading":
        for p in data.get("passages", []):
            pn = p.get("number")
            yield f"passage {pn} title", p.get("title") or ""
            for i, b in enumerate(p.get("blocks", [])):
                yield f"passage {pn} block {i + 1}", b.get("text") or ""
            for g in p.get("groups", []):
                yield f"group {g.get('id')} context", g.get("context") or ""
                for o in g.get("options", []) or []:
                    yield f"group {g.get('id')} option {o.get('value')}", o.get("label") or ""
                for q in g.get("questions", []):
                    yield f"Q{q.get('number')} prompt", q.get("prompt") or ""
    elif skill == "writing":
        for t in data.get("tasks", []):
            yield f"task {t.get('number')} prompt", t.get("prompt") or ""
    elif skill == "speaking":
        for part in data.get("parts", []):
            pn = part.get("part")
            if part.get("cueCard"):
                yield f"part {pn} cue card", part["cueCard"].get("text") or ""
            for topic in part.get("topics", []):
                for i, q in enumerate(topic.get("questions", [])):
                    yield f"part {pn} {topic.get('title')} q{i + 1}", q.get("text") or ""
    elif skill == "listening":
        for part in data.get("parts", []):
            for q in part.get("questions", []):
                yield f"Q{q.get('number')} prompt", q.get("prompt") or ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/ocr-text-audit.json")
    ap.add_argument("--book", type=int)
    ap.add_argument("--test", type=int)
    args = ap.parse_args()

    findings, by_file, by_rule, by_field = [], Counter(), Counter(), Counter()
    for path in sorted(ROOT.glob("c*/test-*/*.json")):
        skill = path.stem
        if skill not in {"reading", "writing", "speaking", "listening"}:
            continue
        book, test = int(path.parent.parent.name[1:]), int(path.parent.name.split("-")[1])
        if (args.book and book != args.book) or (args.test and test != args.test):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for location, text in fields(skill, data):
            hits = check(text)
            if not hits:
                continue
            kind = location.split(" ")[0] if not location.startswith("Q") else "question prompt"
            findings.append({"book": book, "test": test, "skill": skill, "location": location,
                             "rules": sorted({h["rule"] for h in hits}), "samples": [h["match"] for h in hits[:3]],
                             "text": text[:160]})
            by_file[f"c{book} t{test} {skill}"] += 1
            by_field[f"{skill} {kind}"] += 1
            for r in {h["rule"] for h in hits}:
                by_rule[r] += 1

    out = WORKSPACE / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"schemaVersion": 1, "total": len(findings), "byRule": by_rule, "byField": by_field,
                               "byFile": by_file, "findings": findings}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"flagged fields: {len(findings)} -> {args.out}")
    print("by rule:", dict(by_rule.most_common()))
    print("by field:", dict(by_field.most_common()))
    print("worst files:", dict(by_file.most_common(8)))


if __name__ == "__main__":
    main()
