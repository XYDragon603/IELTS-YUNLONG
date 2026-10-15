import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "backend" / "scripts" / "cambridge_pdf_importer.py"
SPEC = importlib.util.spec_from_file_location("cambridge_pdf_importer", MODULE_PATH)
IMPORTER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = IMPORTER
SPEC.loader.exec_module(IMPORTER)


class ImporterRulesTest(unittest.TestCase):
    def test_text_layer_detection_rejects_empty_scans(self):
        self.assertFalse(IMPORTER.usable_text_layer(""))
        self.assertFalse(IMPORTER.usable_text_layer("123 456" * 20))
        self.assertTrue(IMPORTER.usable_text_layer("Listening practice text and questions. " * 8))

    def test_heading_detection_tolerates_small_ocr_errors(self):
        self.assertEqual(IMPORTER.find_heading(["LISTENING"], "listening")[0], "LISTENING")
        self.assertIsNotNone(IMPORTER.find_heading(["AUDIOSCRlPTS"], "audioscripts"))
        self.assertEqual(IMPORTER.find_test(["TEST 3"])[0], 3)

    def test_heading_detection_recognizes_hyphenated_and_older_styles(self):
        self.assertIsNotNone(IMPORTER.find_heading(["Test1-listening-part1"], "listening"))
        self.assertIsNotNone(IMPORTER.find_heading(["Test1-reading-passage1"], "reading"))
        self.assertIsNotNone(IMPORTER.find_heading(["TAPESCRIPTS"], "audioscripts"))
        self.assertIsNotNone(IMPORTER.find_heading(["SAMPLE WRITING ANSWERS"], "sample_writing"))
        self.assertEqual(IMPORTER.find_test(["Test 1-listening-part1"])[0], 1)

    def test_page_number_prefers_last_standalone_number(self):
        self.assertEqual(IMPORTER.page_number_from_text(["Questions 1-10", "Cambridge", "10"]), 10)

    def test_build_missing_map_structure(self):
        missing_map = IMPORTER.build_missing_map(12, "0-byte file", "IELTS/test12.pdf")
        self.assertEqual(missing_map["book"], 12)
        self.assertEqual(missing_map["status"], "missing-resource")
        self.assertIn("0-byte file", missing_map["needsReview"][0])
        self.assertEqual(len(missing_map["tests"]), 4)


if __name__ == "__main__":
    unittest.main()
