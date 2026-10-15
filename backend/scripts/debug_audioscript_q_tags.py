#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect Q references in audioscript lines."""

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "cambridge-importer" / "a3fe27d4ad3c2b97"
s_data = json.loads((CACHE / "audioscripts" / "test-1-listening.json").read_text(encoding="utf-8"))

for p in s_data["pages"]:
    p_num = p["pdfPage"]
    print(f"\n=== Page {p_num} ===")
    for l_idx, l in enumerate(p["lines"]):
        txt = l["text"]
        # check if line contains Q or digit near right margin (xmin > 0.75)
        has_q = bool(re.search(r"\bQ\d+\b", txt, re.IGNORECASE))
        right_words = [w['text'] for w in l['words'] if w['boundingBox'][1] > 0.75]
        if has_q or right_words:
            print(f"  L{l_idx:02d} [top={l['boundingBox'][0]:.3f}]: {ascii(txt)} || Right: {right_words}")
