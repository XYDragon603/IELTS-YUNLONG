#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect raw OCR tokens in page 123 to write generic answer parser."""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "cambridge-importer" / "a3fe27d4ad3c2b97"
a_data = json.loads((CACHE / "answers" / "test-1-listening.json").read_text(encoding="utf-8"))

p123 = a_data['pages'][0]

print("=== Column 1 Top (Part 1, lines 5-14) ===")
for l_idx in range(5, 15):
    l = p123['lines'][l_idx]
    w = [w for w in l['words'] if w['boundingBox'][1] < 0.4]
    print(f"L{l_idx:02d}: {[ascii(x['text']) for x in w]}")

print("\n=== Column 2 Top (Part 3, lines 5-16) ===")
for l_idx in range(5, 17):
    l = p123['lines'][l_idx]
    w = [w for w in l['words'] if w['boundingBox'][1] >= 0.4]
    print(f"L{l_idx:02d}: {[ascii(x['text']) for x in w]}")

print("\n=== Column 1 Bottom (Part 2, lines 18-28) ===")
for l_idx in range(18, 29):
    l = p123['lines'][l_idx]
    w = [w for w in l['words'] if w['boundingBox'][1] < 0.4]
    print(f"L{l_idx:02d}: {[ascii(x['text']) for x in w]}")

print("\n=== Column 2 Bottom (Part 4, lines 19-28) ===")
for l_idx in range(19, 29):
    l = p123['lines'][l_idx]
    w = [w for w in l['words'] if w['boundingBox'][1] >= 0.4]
    print(f"L{l_idx:02d}: {[ascii(x['text']) for x in w]}")
