#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate page maps for Cambridge IELTS 4–20 and write resources/import-report.json.

This script runs entirely locally. It never modifies raw files in IELTS/.
It skips re-OCR when a cache exists and handles missing-resource books cleanly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from cambridge_pdf_importer import (
    PageReader,
    build_map,
    build_missing_map,
    build_per_test_book20_map,
    compute_sha256,
    discover_boundaries,
    get_tesseract_cmd,
)


def run_batch_page_maps():
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "resources" / "import-manifest.json"
    if not manifest_path.is_file():
        print("Error: import-manifest.json not found. Run scripts/build_import_manifest.py first.")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    books_data = {b["book"]: b for b in manifest["books"]}
    page_maps_dir = root / "resources" / "page-maps"
    page_maps_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = root / ".cache" / "cambridge-importer"
    cache_dir.mkdir(parents=True, exist_ok=True)
    tesseract = get_tesseract_cmd()

    report_books = []
    total_sections_detected = 0
    total_text_layer = 0
    total_ocr = 0
    total_cached = 0

    print("=== Generating Cambridge IELTS 4–20 Page Maps ===")
    print(f"Using OCR engine: {tesseract or 'None'}")
    print(f"Cache root: {cache_dir.as_posix()}\n")

    for book_num in range(4, 21):
        book_info = books_data.get(book_num, {})
        canonical_status = book_info.get("canonicalStatus", "missing-resource")
        canonical = book_info.get("canonical")
        out_file = page_maps_dir / f"cambridge-{book_num:02d}.json"
        start_time = time.time()

        print(f"--- Book {book_num} [{canonical_status}] ---")

        # 1. Missing resource books (C12, C17)
        if canonical_status == "missing-resource" or not canonical:
            reason = book_info.get("canonicalRationale", "Original question paper PDF is 0 bytes or missing.")
            cand_path = book_info.get("academicCandidates", [{}])[0].get("path", "") if book_info.get("academicCandidates") else ""
            result = build_missing_map(book_num, reason, cand_path)
            out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report_books.append({
                "book": book_num,
                "status": "missing-resource",
                "canonicalPath": cand_path,
                "pageMapFile": out_file.relative_to(root).as_posix(),
                "detectedSections": 0,
                "totalExpectedSections": 16,
                "textLayerPages": 0,
                "ocrPages": 0,
                "cachedPages": 0,
                "needsReview": result["needsReview"],
                "elapsedSeconds": round(time.time() - start_time, 2),
            })
            print(f"  -> Generated missing-resource placeholder: {out_file.name}")
            continue

        # 2. Cambridge 20 per-test PDFs
        if book_num == 20:
            test_pdfs = {}
            for t_num in range(1, 5):
                t_str = str(t_num)
                t_path = root / canonical["tests"][t_str]["path"]
                test_pdfs[t_num] = t_path
            result = build_per_test_book20_map(book_num, test_pdfs, cache_dir, tesseract, dpi=120)
            out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            det_count = sum(len(v) for v in result["tests"].values())
            total_sections_detected += det_count
            ext = result["extraction"]
            total_text_layer += ext["textLayerPages"]
            total_ocr += ext["ocrPages"]
            total_cached += ext["cachedPages"]

            report_books.append({
                "book": book_num,
                "status": "ready" if not result["needsReview"] else "needs-review",
                "canonicalPath": "IELTS/剑20完整/ (per-test-pdfs)",
                "pageMapFile": out_file.relative_to(root).as_posix(),
                "detectedSections": det_count,
                "totalExpectedSections": 16,
                "textLayerPages": ext["textLayerPages"],
                "ocrPages": ext["ocrPages"],
                "cachedPages": ext["cachedPages"],
                "needsReview": result["needsReview"],
                "elapsedSeconds": round(time.time() - start_time, 2),
            })
            print(f"  -> Sections detected: {det_count}/16, OCR: {ext['ocrPages']}, Cached: {ext['cachedPages']}, Review: {len(result['needsReview'])}")
            continue

        # 3. Standard single PDF (Books 4-11, 13-16, 18, 19)
        pdf_path = root / canonical["path"]
        reader = PageReader(pdf_path, cache_dir, tesseract, dpi=120)
        events, landmarks = discover_boundaries(reader)
        result = build_map(book_num, pdf_path, reader, events, landmarks)
        result["source"]["path"] = canonical["path"]
        result["source"]["sha256"] = canonical["sha256"]

        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if book_num == 18 and out_file.name != "cambridge-18.json":
            (out_file.parent / "cambridge-18.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        det_count = sum(len(v) for v in result["tests"].values())
        total_sections_detected += det_count
        ext = result["extraction"]
        total_text_layer += ext["textLayerPages"]
        total_ocr += ext["ocrPages"]
        total_cached += ext["cachedPages"]

        report_books.append({
            "book": book_num,
            "status": "ready" if not result["needsReview"] else "needs-review",
            "canonicalPath": canonical["path"],
            "pageMapFile": out_file.relative_to(root).as_posix(),
            "detectedSections": det_count,
            "totalExpectedSections": 16,
            "textLayerPages": ext["textLayerPages"],
            "ocrPages": ext["ocrPages"],
            "cachedPages": ext["cachedPages"],
            "needsReview": result["needsReview"],
            "elapsedSeconds": round(time.time() - start_time, 2),
        })
        print(f"  -> Sections detected: {det_count}/16, Text: {ext['textLayerPages']}, OCR: {ext['ocrPages']}, Cached: {ext['cachedPages']}, Review: {len(result['needsReview'])}")

    # Write import-report.json
    report = {
        "schemaVersion": 1,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "page-maps-and-resource-manifest",
        "summary": {
            "totalBooks": 17,
            "readyBooks": [b["book"] for b in report_books if b["status"] == "ready"],
            "needsReviewBooks": [b["book"] for b in report_books if b["status"] == "needs-review"],
            "missingResourceBooks": [b["book"] for b in report_books if b["status"] == "missing-resource"],
            "totalSectionsDetected": total_sections_detected,
            "totalExpectedSections": 15 * 16,  # 15 existing books * 16 = 240
            "pageExtraction": {
                "textLayerPages": total_text_layer,
                "ocrPages": total_ocr,
                "cachedPages": total_cached,
            },
        },
        "books": report_books,
    }

    report_path = root / "resources" / "import-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nReport written to {report_path.as_posix()}")
    print("=== Batch Page Map Generation Complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_batch_page_maps())
