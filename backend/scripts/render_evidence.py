"""Render the source-page region behind a reading text field, for visual checking.

Prints the field's current text and writes a PNG crop of its bounding box to
.cache/evidence/. The PNG's SHA-256 is printed so a correction recorded in
text-curations.json can point at the exact image that was checked.

Usage:
  python scripts/render_evidence.py --book 12 --test 1 --field "Q6 prompt"
  python scripts/render_evidence.py --book 16 --test 3 --field "group group-6-13 context"
  python scripts/render_evidence.py --book 12 --test 1 --field "passage 1 block 2"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import fitz

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = WORKSPACE / "resources" / "cambridge"
OUT = WORKSPACE / ".cache" / "evidence"


def find_field(data: dict, field: str):
    """Return (container, key) for a location string as used by audit_ocr_text.py."""
    m = re.fullmatch(r"Q(\d+) prompt", field)
    if m:
        for p in data["passages"]:
            for g in p.get("groups", []):
                for q in g.get("questions", []):
                    if q.get("number") == int(m[1]):
                        return q, "prompt"
    m = re.fullmatch(r"group (\S+) context", field)
    if m:
        for p in data["passages"]:
            for g in p.get("groups", []):
                if g.get("id") == m[1]:
                    return g, "context"
    m = re.fullmatch(r"group (\S+) option (\S+)", field)
    if m:
        for p in data["passages"]:
            for g in p.get("groups", []):
                if g.get("id") == m[1]:
                    for o in g.get("options", []) or []:
                        if str(o.get("value")) == m[2]:
                            return o, "label"
    m = re.fullmatch(r"passage (\d+) block (\d+)", field)
    if m:
        for p in data["passages"]:
            if p.get("number") == int(m[1]):
                return p["blocks"][int(m[2]) - 1], "text"
    raise SystemExit(f"field not found: {field}")


def render(book: int, test: int, field: str, dpi: int = 200, pad: float = 0.01) -> dict:
    data = json.loads((ROOT / f"c{book}" / f"test-{test}" / "reading.json").read_text(encoding="utf-8"))
    container, key = find_field(data, field)
    source = container.get("source") or {}
    if not source.get("pdfPage") or not source.get("boundingBox"):
        raise SystemExit(f"{field}: no pdfPage/boundingBox in source")
    paper = data["sources"]["paper"]
    with fitz.open(WORKSPACE / paper["path"]) as doc:
        page = doc[source["pdfPage"] - 1]
        ymin, xmin, ymax, xmax = source["boundingBox"]
        r = page.rect
        clip = fitz.Rect(r.width * max(0, xmin - pad), r.height * max(0, ymin - pad),
                         r.width * min(1, xmax + pad), r.height * min(1, ymax + pad))
        png = page.get_pixmap(dpi=dpi, clip=clip).tobytes("png")
    OUT.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9]+", "-", f"c{book}-t{test}-{field}").strip("-") + ".png"
    (OUT / name).write_bytes(png)
    return {"file": (OUT / name).relative_to(WORKSPACE).as_posix(), "sha256": hashlib.sha256(png).hexdigest(),
            "pdfPage": source["pdfPage"], "boundingBox": source["boundingBox"], "paperSha256": paper.get("sha256"),
            "text": container.get(key)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--test", type=int, required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args()
    info = render(args.book, args.test, args.field, args.dpi)
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
