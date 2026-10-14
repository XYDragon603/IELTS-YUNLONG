"""Crop a region of the original paper and attach it to a reading question group.

Used for diagram / table / summary groups whose text alone cannot be answered
(e.g. "Label the diagrams below") but which were imported without an image.
The crop comes straight from the source PDF; nothing is redrawn. The asset
object matches the existing format (asset, sourcePdfPage, boundingBox,
boundingBoxFormat, width, height, sha256, alt).

Usage:
  python scripts/attach_group_asset.py --book 16 --test 4 --group group-1-6 \
      --page 86 --box 0.06 0.08 0.95 0.95 --alt "Persian and Roman qanat diagrams"
  (box is ymin xmin ymax xmax, 0-1)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import fitz

WORKSPACE = Path(__file__).resolve().parent.parent
ROOT = WORKSPACE / "resources" / "cambridge"
DPI = 200


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--test", type=int, required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--box", type=float, nargs=4, required=True, metavar=("YMIN", "XMIN", "YMAX", "XMAX"))
    ap.add_argument("--alt", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    directory = ROOT / f"c{args.book}" / f"test-{args.test}"
    reading = directory / "reading.json"
    data = json.loads(reading.read_text(encoding="utf-8"))
    group = next((g for p in data["passages"] for g in p.get("groups", []) if g.get("id") == args.group), None)
    if group is None:
        raise SystemExit(f"group not found: {args.group}")
    ymin, xmin, ymax, xmax = args.box
    if not (0 <= ymin < ymax <= 1 and 0 <= xmin < xmax <= 1):
        raise SystemExit("box must be ymin xmin ymax xmax within 0-1")
    with fitz.open(WORKSPACE / data["sources"]["paper"]["path"]) as doc:
        page = doc[args.page - 1]
        r = page.rect
        pix = page.get_pixmap(dpi=DPI, clip=fitz.Rect(r.width * xmin, r.height * ymin, r.width * xmax, r.height * ymax))
        png = pix.tobytes("png")
    name = f"reading-{args.group}.png"
    asset = {"asset": f"./assets/{name}", "sourcePdfPage": args.page, "boundingBox": [ymin, xmin, ymax, xmax],
             "boundingBoxFormat": "ymin,xmin,ymax,xmax", "width": pix.width, "height": pix.height,
             "sha256": hashlib.sha256(png).hexdigest(), "alt": args.alt}
    print(json.dumps(asset, ensure_ascii=False, indent=1))
    if not args.write:
        preview = WORKSPACE / ".cache" / "evidence" / f"asset-preview-c{args.book}-t{args.test}-{name}"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(png)
        print("dry run; preview:", preview.relative_to(WORKSPACE).as_posix())
        return
    backup = WORKSPACE / ".cache" / "data-backup" / directory.relative_to(ROOT) / "reading.json"
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(reading, backup)
    (directory / "assets").mkdir(exist_ok=True)
    (directory / "assets" / name).write_bytes(png)
    group["asset"] = asset
    reading.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("attached", asset["asset"])


if __name__ == "__main__":
    main()
