"""Record and apply visually checked corrections to reading text fields.

Corrections live in resources/cambridge/c<book>/test-<n>/text-curations.json,
separate from curations.json (which the generate_c*_curations.py scripts
rewrite). Each entry keeps the original OCR text, the corrected text, the page,
the evidence bounding box, the SHA-256 of the exact evidence image that was
checked (rendered by render_evidence.py), the paper hash, the review method and
a rationale.

Add corrections (renders evidence, records the current text as originalOcr,
writes the entry and applies it):
  python scripts/apply_text_curations.py --add corrections.json --review-method assistant-visual

  corrections.json: [{"book": 12, "test": 1, "field": "Q6 prompt",
                      "value": "do not affect the 6 ______ of the bottle contents",
                      "rationale": "..."}]

Re-apply every recorded correction (idempotent; a field is only replaced when
its current text still equals originalOcr or already equals the curated value):
  python scripts/apply_text_curations.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_evidence import find_field, render  # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / "resources" / "cambridge"
REVIEW_METHODS = {"assistant-visual", "human"}


def test_dir(book: int, test: int) -> Path:
    return ROOT / f"c{book}" / f"test-{test}"


def load_log(directory: Path) -> dict:
    path = directory / "text-curations.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schemaVersion": 1, "description": "Visually checked corrections to reading text fields. "
            "Each entry links to the evidence image hash; reviewMethod states who checked it.", "curations": []}


def apply_directory(directory: Path) -> tuple[int, list[str]]:
    """Apply every recorded correction in one test directory. Returns (applied, problems)."""
    log = load_log(directory)
    reading = directory / "reading.json"
    data = json.loads(reading.read_text(encoding="utf-8"))
    applied, problems = 0, []
    for c in log["curations"]:
        container, key = find_field(data, c["field"])
        current = container.get(key)
        if current == c["curatedValue"]:
            continue
        if current != c["originalOcr"]:
            problems.append(f"{directory.relative_to(ROOT).as_posix()} {c['field']}: current text differs from recorded originalOcr; skipped")
            continue
        container[key] = c["curatedValue"]
        source = container.setdefault("source", {})
        source["method"] = "curated"
        source["curation"] = {"file": "text-curations.json", "reviewMethod": c["reviewMethod"]}
        applied += 1
    if applied:
        backup = WORKSPACE / ".cache" / "data-backup" / directory.relative_to(ROOT) / "reading.json"
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(reading, backup)
        reading.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return applied, problems


def add(corrections: list[dict], review_method: str) -> None:
    if review_method not in REVIEW_METHODS:
        raise SystemExit(f"review method must be one of {sorted(REVIEW_METHODS)}")
    by_dir: dict[Path, list[dict]] = {}
    for c in corrections:
        by_dir.setdefault(test_dir(c["book"], c["test"]), []).append(c)
    for directory, items in by_dir.items():
        log = load_log(directory)
        data = json.loads((directory / "reading.json").read_text(encoding="utf-8"))
        for c in items:
            container, key = find_field(data, c["field"])
            # A field without its own source box (e.g. an empty prompt) can point at the region that shows it.
            evidence = render(c["book"], c["test"], c.get("evidenceField", c["field"]))
            existing = next((x for x in log["curations"] if x["field"] == c["field"]), None)
            entry = {
                "skill": "reading", "field": c["field"], "target": key,
                "evidenceField": c.get("evidenceField", c["field"]),
                "originalOcr": existing["originalOcr"] if existing else container.get(key),
                "curatedValue": c["value"],
                "sourcePdfPage": evidence["pdfPage"], "evidenceBoundingBox": evidence["boundingBox"],
                "evidenceImageSha256": evidence["sha256"], "paperSha256": evidence["paperSha256"],
                "reviewMethod": review_method, "rationale": c["rationale"], "date": date.today().isoformat(),
            }
            if existing:
                log["curations"][log["curations"].index(existing)] = entry
            else:
                log["curations"].append(entry)
        (directory / "text-curations.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", help="JSON file with corrections to record before applying")
    ap.add_argument("--review-method", default="assistant-visual")
    args = ap.parse_args()
    if args.add:
        add(json.loads(Path(args.add).read_text(encoding="utf-8")), args.review_method)
    total, problems = 0, []
    for log_path in sorted(ROOT.glob("c*/test-*/text-curations.json")):
        n, p = apply_directory(log_path.parent)
        total += n
        problems += p
    print(f"applied {total} correction(s)")
    for p in problems:
        print("WARN", p)


if __name__ == "__main__":
    main()
