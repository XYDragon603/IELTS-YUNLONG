#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect raw OCR lines in question pages to write generic question parser."""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "cambridge-importer" / "a3fe27d4ad3c2b97"
q_data = json.loads((CACHE / "questions" / "test-1-listening.json").read_text(encoding="utf-8"))

for page_idx, p in enumerate(q_data['pages']):
    pdf_p = p['pdfPage']
    print(f"\n================ Page {pdf_p} ================")
    for l_idx, l in enumerate(p['lines']):
        txt = l['text']
        print(f"L{l_idx:02d} [{l['boundingBox'][0]:.3f}]: {txt}")
