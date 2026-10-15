"""Remove OCR symbol residue from imported Cambridge text, rule by rule.

Rules (symbol-level only; no words are invented):
  bullet-glyph     leading bullet read as ¢ © ® * or "e —" in a list line
  pipe-as-I        "|" that is really the pronoun I ("when | became" -> "when I became"),
                   only when the next word is one that commonly follows I
  pipe-residue     any other standalone "|" (column gutter / table rule residue)

Fields: reading passages, group contexts, question prompts and options; writing
prompts; speaking questions and cue cards. Listening prompts are curated by hand
and are not touched.

Every change is appended to <test>/ocr-cleanup.json with the original text, the
new text and the rules that fired. This is a rule-based clean-up, not a human
or visual review; needsReview / verified flags are unchanged.

Usage:
  python scripts/tidy_ocr_symbols.py            # dry run
  python scripts/tidy_ocr_symbols.py --write    # apply, back up and log
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / "resources" / "cambridge"

# Words that commonly follow the pronoun I in these passages.
AFTER_I = {
    "am", "was", "have", "had", "think", "thought", "became", "become", "really", "would", "will", "can", "could",
    "do", "did", "don't", "didn't", "know", "knew", "believe", "feel", "felt", "found", "find", "saw", "see", "said",
    "say", "went", "at", "also", "never", "often", "just", "mean", "meant", "want", "wanted", "should", "must", "may",
    "might", "got", "started", "decided", "began", "remember", "came", "asked", "told", "looked", "like", "liked",
    "love", "hope", "used", "wrote", "realised", "realized", "need", "needed", "suppose", "guess", "agree", "tried",
    "spent", "met", "heard", "noticed", "always", "still", "only", "first", "then", "now", "personally", "myself",
    "and", "who", "had", "get", "went", "made", "make", "took", "take", "study", "studied", "worked", "work", "learned",
    "learnt", "discovered", "expected", "wonder", "wondered", "understand", "understood", "argue", "would've", "i'm",
}
BULLET_LINE = re.compile(r"^[ \t]*(?:[¢©®*•]|e(?=[ \t]*[—–-][ \t]))[ \t]*[—–-]?[ \t]+(?=\S)", re.M)
PIPE_AS_I = re.compile(r"(^|[\s‘“'\"(])\|(?=[ \t]+([A-Za-z’']+))", re.M)
# Printed page reference + page number, e.g. ">/@ p.121| 19", "3/Q p.120| 23", "[© p. 123] 47".
PAGE_FOOTER = re.compile(r"\n?^[^\w\n]{0,4}\w?[^\w\n]{0,3}\s*p\.?\s*\d{2,3}[^\w\n]{0,3}\s*\d{1,3}[ \t]*$", re.M)
PIPE_RESIDUE = re.compile(r"[ \t]*(?<![A-Za-z0-9])\|(?![A-Za-z0-9])[ \t]*")


def tidy(text: str, list_field: bool) -> tuple[str, list[str]]:
    fired = []
    out = text
    if list_field:
        new = BULLET_LINE.sub("" if list_field == "drop" else "• ", out)
        if new != out:
            fired.append("bullet-glyph")
            out = new

    def as_i(m: re.Match) -> str:
        return f"{m.group(1)}I" if m.group(2).lower() in AFTER_I else m.group(0)

    new = PAGE_FOOTER.sub("", out)
    if new != out:
        fired.append("page-footer")
        out = new
    new = re.sub(r"^([A-H]|[ivx]{1,4})[ \t]*_+[ \t.]*(?=\S)", r"\1 ", out, flags=re.M)   # "B__. Its" -> "B Its"
    new = re.sub(r"(?<![A-Za-z])l\|(?=t)", "I", new)                                      # "l|ts" -> "Its"
    if new != out:
        fired.append("option-label")
        out = new
    new = PIPE_AS_I.sub(as_i, out)
    if new != out:
        fired.append("pipe-as-I")
        out = new
    lines = []
    for line in out.split("\n"):
        if "|" in line:
            cleaned = re.sub(r"[ \t]{2,}", " ", PIPE_RESIDUE.sub(" ", line)).strip(" \t")
            if not cleaned:
                continue  # the line was only table-rule residue
            line = cleaned
        lines.append(line)
    new = "\n".join(lines)
    if new != out:
        fired.append("pipe-residue")
        out = new
    return out, fired


def slots(data: dict):
    """Yield (location, container, key, list_mode). list_mode: 'drop' removes bullets, 'dot' keeps a • bullet."""
    skill = data.get("skill")
    if skill == "reading":
        for p in data.get("passages", []):
            yield f"passage {p.get('number')} title", p, "title", None
            for i, b in enumerate(p.get("blocks", [])):
                yield f"passage {p.get('number')} block {i + 1}", b, "text", None
            for g in p.get("groups", []):
                yield f"group {g.get('id')} context", g, "context", "dot"
                for o in g.get("options", []) or []:
                    yield f"group {g.get('id')} option {o.get('value')}", o, "label", None
                for q in g.get("questions", []):
                    yield f"Q{q.get('number')} prompt", q, "prompt", "dot"
    elif skill == "writing":
        for t in data.get("tasks", []):
            yield f"task {t.get('number')} prompt", t, "prompt", "dot"
    elif skill == "speaking":
        for part in data.get("parts", []):
            if part.get("cueCard"):
                yield f"part {part.get('part')} cue card", part["cueCard"], "text", "dot"
            for topic in part.get("topics", []):
                for i, q in enumerate(topic.get("questions", [])):
                    yield f"part {part.get('part')} {topic.get('title')} q{i + 1}", q, "text", "drop"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args()
    total, by_rule, examples = 0, {}, []
    for path in sorted(ROOT.glob("c*/test-*/*.json")):
        if path.stem not in {"reading", "writing", "speaking"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        changes = []
        for location, container, key, mode in slots(data):
            before = container.get(key)
            if not isinstance(before, str) or not re.search(r"[|¢©®]|^[ \t]*e[ \t]*[—–-]|^[A-H][ \t]*_|p\.?\s*\d{2,3}", before, re.M):
                continue
            after, fired = tidy(before, mode)
            if after == before:
                continue
            for r in fired:
                by_rule[r] = by_rule.get(r, 0) + 1
            changes.append({"skill": path.stem, "location": location, "rules": fired, "original": before, "tidied": after})
            examples.append((f"{path.parent.relative_to(ROOT).as_posix()} {path.stem} {location}", before, after))
            container[key] = after
        if not changes:
            continue
        total += len(changes)
        if args.write:
            backup = WORKSPACE / ".cache" / "data-backup" / path.parent.relative_to(ROOT) / path.name
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log_path = path.parent / "ocr-cleanup.json"
            log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {
                "schemaVersion": 1, "description": "Machine OCR clean-up log. Not a human or visual review; needsReview and verified flags are unchanged.", "changes": []}
            log["changes"].extend({**c, "method": "rule", "date": date.today().isoformat(), "script": "scripts/tidy_ocr_symbols.py"} for c in changes)
            log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("applied" if args.write else "dry run"), total, "field(s)", by_rule)
    for where, before, after in examples[:args.show]:
        i = next((k for k, (a, b) in enumerate(zip(before, after)) if a != b), min(len(before), len(after)))
        print(f"\n[{where}]\n  - {before[max(0, i - 40):i + 60]!r}\n  + {after[max(0, i - 40):i + 60]!r}")


if __name__ == "__main__":
    main()
