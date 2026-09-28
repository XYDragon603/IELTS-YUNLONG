#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit and integration tests for Cambridge IELTS import manifest and page maps."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ImportManifestTest(unittest.TestCase):
    def setUp(self):
        self.manifest_path = ROOT / "resources" / "import-manifest.json"
        self.assertTrue(self.manifest_path.is_file(), "import-manifest.json must exist")
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def test_summary_and_book_counts(self):
        self.assertEqual(self.manifest["schemaVersion"], 1)
        self.assertEqual(len(self.manifest["books"]), 17)
        self.assertEqual(self.manifest["summary"]["booksCount"], 17)
        self.assertEqual(self.manifest["summary"]["totalAudioMapped"], 272)

    def test_canonical_status_and_audio_resources(self):
        books_by_id = {b["book"]: b for b in self.manifest["books"]}
        self.assertEqual(books_by_id[12]["canonicalStatus"], "ready")
        self.assertEqual(books_by_id[17]["canonicalStatus"], "ready")
        self.assertEqual(books_by_id[20]["canonicalStatus"], "ready")
        self.assertEqual(books_by_id[20]["canonical"]["type"], "per-test-pdfs")
        self.assertEqual(len(books_by_id[20]["canonical"]["tests"]), 4)

        # Cambridge 18 explanation check
        b18_exp = books_by_id[18].get("canonicalExplanation")
        self.assertIsNotNone(b18_exp, "Book 18 must have canonicalExplanation")
        self.assertEqual(b18_exp["sha256"], "bd7fbb1533bee4e309f17acc2ef61ec3b05b0a51d9b72da77d49f106d9716065")

        for b_num in range(4, 21):
            self.assertEqual(books_by_id[b_num]["canonicalStatus"], "ready")
            for t_num in range(1, 5):
                self.assertEqual(len(books_by_id[b_num]["audio"][str(t_num)]), 4)


class PageMapsTest(unittest.TestCase):
    def setUp(self):
        self.page_maps_dir = ROOT / "resources" / "page-maps"
        self.assertTrue(self.page_maps_dir.is_dir(), "page-maps dir must exist")

    def test_all_17_page_maps_exist(self):
        for b_num in range(4, 21):
            pm_file = self.page_maps_dir / f"cambridge-{b_num:02d}.json"
            self.assertTrue(pm_file.is_file(), f"Missing page map: {pm_file.name}")

    def test_ready_books_have_16_complete_sections(self):
        skills = ("listening", "reading", "writing", "speaking")
        for b_num in range(4, 21):
            pm_file = self.page_maps_dir / f"cambridge-{b_num:02d}.json"
            data = json.loads(pm_file.read_text(encoding="utf-8"))
            self.assertEqual(data["schemaVersion"], 1)
            self.assertEqual(data["book"], b_num)
            self.assertEqual(data.get("needsReview"), [], f"Book {b_num} has pending needsReview")

            tests = data.get("tests", {})
            self.assertEqual(len(tests), 4, f"Book {b_num} must have 4 tests")
            for t_num in range(1, 5):
                t_str = str(t_num)
                self.assertIn(t_str, tests)
                for s in skills:
                    self.assertIn(s, tests[t_str], f"Book {b_num} Test {t_num} missing {s}")
                    entry = tests[t_str][s]
                    self.assertIn("pdfStartPage", entry)
                    self.assertIn("pdfEndPage", entry)
                    self.assertIn("detectedBy", entry)
                    self.assertIn("confidence", entry)
                    self.assertIn("evidence", entry)
                    self.assertGreater(entry["pdfStartPage"], 0)
                    self.assertGreaterEqual(entry["pdfEndPage"], entry["pdfStartPage"])

    def test_formerly_missing_books_have_page_maps(self):
        for b_num in (12, 17):
            pm_file = self.page_maps_dir / f"cambridge-{b_num:02d}.json"
            data = json.loads(pm_file.read_text(encoding="utf-8"))
            self.assertEqual(data["book"], b_num)
            self.assertEqual(len(data.get("tests", {})), 4)
            self.assertEqual(data.get("needsReview"), [])
            self.assertGreater(data.get("extraction", {}).get("textLayerPages", 0) + data.get("extraction", {}).get("ocrPages", 0), 0)

    def test_import_report_integrity(self):
        report_path = ROOT / "resources" / "import-report.json"
        self.assertTrue(report_path.is_file())
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["totalBooks"], 17)
        self.assertEqual(len(report["summary"]["readyBooks"]), 17)
        self.assertEqual(report["summary"]["needsReviewBooks"], [])
        self.assertEqual(report["summary"]["missingResourceBooks"], [])
        self.assertEqual(report["summary"]["totalSectionsDetected"], 272)


if __name__ == "__main__":
    unittest.main()
