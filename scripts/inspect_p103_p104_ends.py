#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect lines on Page 103 and 104 to see Q1-Q7 and Q12-Q15 margin tokens."""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "cambridge-importer" / "a3fe27d4ad3c2b97"
s_data = json.loads((CACHE / "audioscripts" / "test-1-listening.json").read_text(encoding="utf-8"))

for page_idx in [0, 1]:
    p = s_data["pages"][page_idx]
    print(f"\n=== Page {p['pdfPage']} ===")
    for l_idx, l in enumerate(p["lines"]):
        words = [w['text'] for w in l['words']]
        print(f"L{l_idx:02d}: {words[-3:]}")
