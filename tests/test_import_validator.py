#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive tests for the unified Cambridge import validator.

Tests both positive valid imports across all four skills and negative cases:
- Missing questions (< 40 scoring points)
- Duplicate question IDs
- Non-continuous question numbers
- Missing reading passages (< 3)
- Missing / broken asset files
- Tampered PDF hashes
- Inconsistent status / verified flags
- Fake review claims
"""

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.validate_cambridge_import import (
    validate_import,
    validate_listening,
    validate_reading,
    validate_speaking,
    validate_test_directory,
    validate_writing,
)

ROOT = Path(__file__).resolve().parent.parent
C13_T1_DIR = ROOT / "resources" / "cambridge" / "c13" / "test-1"
C16_T1_DIR = ROOT / "resources" / "cambridge" / "c16" / "test-1"
C16_T2_DIR = ROOT / "resources" / "cambridge" / "c16" / "test-2"
C16_T3_DIR = ROOT / "resources" / "cambridge" / "c16" / "test-3"
C16_T4_DIR = ROOT / "resources" / "cambridge" / "c16" / "test-4"
C18_T1_DIR = ROOT / "resources" / "cambridge" / "c18" / "test-1"
C18_T2_DIR = ROOT / "resources" / "cambridge" / "c18" / "test-2"
C18_T3_DIR = ROOT / "resources" / "cambridge" / "c18" / "test-3"
C18_T4_DIR = ROOT / "resources" / "cambridge" / "c18" / "test-4"
C19_T1_DIR = ROOT / "resources" / "cambridge" / "c19" / "test-1"
C19_T2_DIR = ROOT / "resources" / "cambridge" / "c19" / "test-2"
C19_T3_DIR = ROOT / "resources" / "cambridge" / "c19" / "test-3"
C19_T4_DIR = ROOT / "resources" / "cambridge" / "c19" / "test-4"
C20_T1_DIR = ROOT / "resources" / "cambridge" / "c20" / "test-1"
C20_T2_DIR = ROOT / "resources" / "cambridge" / "c20" / "test-2"
C20_T3_DIR = ROOT / "resources" / "cambridge" / "c20" / "test-3"
C20_T4_DIR = ROOT / "resources" / "cambridge" / "c20" / "test-4"


class TestImportValidatorPositive(unittest.TestCase):
    def test_reading_import_valid(self):
        res = validate_reading(C18_T1_DIR / "reading.json")
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["checksFailed"], 0)
        self.assertEqual(res["checksPassed"], 10)

    def test_writing_import_valid(self):
        res = validate_writing(C18_T1_DIR / "writing.json")
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["checksFailed"], 0)
        self.assertEqual(res["checksPassed"], 7)

    def test_speaking_import_valid(self):
        res = validate_speaking(C18_T1_DIR / "speaking.json")
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["checksFailed"], 0)
        self.assertEqual(res["checksPassed"], 6)

    def test_listening_import_valid_checks(self):
        res = validate_listening(C18_T1_DIR / "listening.json")
        self.assertEqual(res["checksPassed"], 17)
        self.assertEqual(res["checksFailed"], 0)
        self.assertEqual(res["status"], "PASSED")
        self.assertFalse(res["verified"])
        failed_names = [c["name"] for c in res["checks"] if not c["passed"]]
        self.assertEqual(failed_names, [])

    def test_directory_validation(self):
        res = validate_test_directory(C18_T1_DIR)
        self.assertIn("reading", res["skills"])
        self.assertIn("writing", res["skills"])
        self.assertIn("speaking", res["skills"])
        self.assertIn("listening", res["skills"])
        self.assertEqual(res["skills"]["reading"]["status"], "PASSED")
        self.assertEqual(res["skills"]["writing"]["status"], "PASSED")
        self.assertEqual(res["skills"]["speaking"]["status"], "PASSED")

    def test_c18_t2_all_skills_valid(self):
        res_r = validate_reading(C18_T2_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C18_T2_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C18_T2_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C18_T2_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C18_T2_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c18_t3_all_skills_valid(self):
        res_r = validate_reading(C18_T3_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C18_T3_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C18_T3_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C18_T3_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C18_T3_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c18_t4_all_skills_valid(self):
        res_r = validate_reading(C18_T4_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C18_T4_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C18_T4_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C18_T4_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C18_T4_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c19_t1_all_skills_valid(self):
        res_r = validate_reading(C19_T1_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C19_T1_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C19_T1_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C19_T1_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C19_T1_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c19_t2_all_skills_valid(self):
        res_r = validate_reading(C19_T2_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C19_T2_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C19_T2_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C19_T2_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C19_T2_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c19_t3_all_skills_valid(self):
        res_r = validate_reading(C19_T3_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C19_T3_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C19_T3_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C19_T3_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C19_T3_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c19_t4_all_skills_valid(self):
        res_r = validate_reading(C19_T4_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C19_T4_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C19_T4_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C19_T4_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C19_T4_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c20_t1_all_skills_valid(self):
        res_r = validate_reading(C20_T1_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C20_T1_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C20_T1_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C20_T1_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C20_T1_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c20_t2_all_skills_valid(self):
        res_r = validate_reading(C20_T2_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C20_T2_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C20_T2_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C20_T2_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C20_T2_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c20_t3_all_skills_valid(self):
        res_r = validate_reading(C20_T3_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C20_T3_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C20_T3_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C20_T3_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C20_T3_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c20_t4_all_skills_valid(self):
        res_r = validate_reading(C20_T4_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C20_T4_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C20_T4_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C20_T4_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C20_T4_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c16_t1_all_skills_valid(self):
        res_r = validate_reading(C16_T1_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C16_T1_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C16_T1_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C16_T1_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C16_T1_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c16_t2_all_skills_valid(self):
        res_r = validate_reading(C16_T2_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C16_T2_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C16_T2_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C16_T2_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C16_T2_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c16_t3_all_skills_valid(self):
        res_r = validate_reading(C16_T3_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C16_T3_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C16_T3_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C16_T3_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C16_T3_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)

    def test_c16_t4_all_skills_valid(self):
        res_r = validate_reading(C16_T4_DIR / "reading.json")
        self.assertEqual(res_r["status"], "PASSED")
        self.assertEqual(res_r["checksPassed"], 10)

        res_w = validate_writing(C16_T4_DIR / "writing.json")
        self.assertEqual(res_w["status"], "PASSED")
        self.assertEqual(res_w["checksPassed"], 7)

        res_s = validate_speaking(C16_T4_DIR / "speaking.json")
        self.assertEqual(res_s["status"], "PASSED")
        self.assertEqual(res_s["checksPassed"], 6)

        res_l = validate_listening(C16_T4_DIR / "listening.json")
        self.assertEqual(res_l["checksPassed"], 17)
        self.assertEqual(res_l["checksFailed"], 0)

        res_dir = validate_test_directory(C16_T4_DIR)
        self.assertEqual(res_dir["checksPassed"], 41)
        self.assertEqual(res_dir["checksFailed"], 0)


class TestImportValidatorNegative(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_rejects_missing_questions(self):
        # Create reading dataset with only 39 questions
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        data["passages"][0]["groups"][0]["questions"].pop()
        data["detectedScoringPoints"] = 39

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_scoring_points_count_40", failed)

    def test_rejects_duplicate_question_ids(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        # Duplicate q1
        data["passages"][0]["groups"][0]["questions"][1]["id"] = "q1"

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_unique_question_ids", failed)

    def test_rejects_missing_passages(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        data["passages"] = data["passages"][:2]

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_three_passages", failed)

    def test_rejects_tampered_source_pdf_hash(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        data["sources"]["paper"]["sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_source_pdf_verified", failed)

    def test_rejects_missing_asset_file(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        data["passages"][0]["groups"][1]["asset"]["asset"] = "./assets/non_existent_image.png"

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_assets_verified", failed)

    def test_rejects_fake_human_verification(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        # Tamper curation reviewMethod to invalid value
        data["answerKey"]["1"]["curation"]["reviewMethod"] = "unauthorized-auto"

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_curation_provenance", failed)

    def test_rejects_untraceable_text_curation(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")
        entry = {"skill": "reading", "field": "Q1 prompt", "originalOcr": "x", "curatedValue": "y",
                 "sourcePdfPage": 20, "evidenceBoundingBox": [0.1, 0.1, 0.2, 0.9],
                 "evidenceImageSha256": "a" * 64, "reviewMethod": "assistant-visual"}
        cur_file = self.temp_path / "text-curations.json"

        cur_file.write_text(json.dumps({"curations": [entry]}), encoding="utf-8")
        self.assertNotIn("reading_curation_provenance",
                         {c["name"] for c in validate_reading(test_file)["checks"] if not c["passed"]})

        for broken in ({"reviewMethod": "auto"}, {"evidenceImageSha256": "not-a-hash"}, {"evidenceBoundingBox": [0.5, 0.1, 0.2, 0.9]}):
            cur_file.write_text(json.dumps({"curations": [{**entry, **broken}]}), encoding="utf-8")
            failed = {c["name"] for c in validate_reading(test_file)["checks"] if not c["passed"]}
            self.assertIn("reading_curation_provenance", failed, broken)

    def test_rejects_status_ready_when_needs_review_is_present(self):
        data = json.loads((C18_T1_DIR / "writing.json").read_text(encoding="utf-8"))
        # Inconsistent state: claim verified=true, status="ready" while needsReview is not empty
        data["verified"] = True
        data["status"] = "ready"
        self.assertTrue(len(data.get("needsReview", [])) > 0)

        test_file = self.temp_path / "writing.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_writing(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("writing_status_integrity", failed)

    def test_rejects_speaking_without_cue_card(self):
        data = json.loads((C18_T1_DIR / "speaking.json").read_text(encoding="utf-8"))
        # Remove cueCard from Part 2
        p2 = next(p for p in data["parts"] if p["part"] == 2)
        del p2["cueCard"]

        test_file = self.temp_path / "speaking.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_speaking(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("speaking_part2_cue_card", failed)

    def test_rejects_empty_reading_passage_blocks(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        data["passages"][1]["blocks"] = []

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_three_passages", failed)

    def test_rejects_instruction_like_reading_passage_title(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        data["passages"][1]["title"] = "Passage 2 on pages 66 and 67."

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_three_passages", failed)

    def test_rejects_out_of_bounds_transcript_evidence_page(self):
        data = json.loads((C18_T1_DIR / "listening.json").read_text(encoding="utf-8"))
        data["parts"][0]["questions"][0]["transcriptEvidence"]["sourcePdfPage"] = 999

        test_file = self.temp_path / "listening.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_listening(test_file)
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("valid_pdf_pages", failed)

    def test_rejects_out_of_bounds_question_source_page(self):
        data = json.loads((C18_T1_DIR / "listening.json").read_text(encoding="utf-8"))
        data["parts"][0]["questions"][0]["source"]["pdfPage"] = 999

        test_file = self.temp_path / "listening.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_listening(test_file)
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("valid_pdf_pages", failed)


    def test_rejects_reading_passage_under_100_words(self):
        data = json.loads((C18_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        data["passages"][0]["blocks"] = [{"type": "paragraph", "text": "This is a short passage with only ten words total here."}]

        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_reading(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("reading_three_passages", failed)

    def test_rejects_question_without_prompt_or_group_context(self):
        data = json.loads((C13_T1_DIR / "reading.json").read_text(encoding="utf-8"))
        group = next(g for p in data["passages"] for g in p["groups"] if g["questionRange"] == [27, 31])
        group["questions"][0]["prompt"] = None
        group["context"] = ""
        test_file = self.temp_path / "reading.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")
        result = validate_reading(test_file)
        failed = {check["name"] for check in result["checks"] if not check["passed"]}
        self.assertIn("reading_scoring_points_count_40", failed)

    def test_rejects_listening_curations_missing_or_invalid_review_method(self):
        data = json.loads((C18_T1_DIR / "listening.json").read_text(encoding="utf-8"))
        # Tamper provenance generationMode
        data["importProvenance"]["generationMode"] = "unknown-mode"

        test_file = self.temp_path / "listening.json"
        test_file.write_text(json.dumps(data), encoding="utf-8")

        res = validate_listening(test_file)
        self.assertEqual(res["status"], "FAILED")
        failed = {c["name"] for c in res["checks"] if not c["passed"]}
        self.assertIn("fully_parser_derived_import_mode", failed)

    def test_rejects_invalid_curation_coordinates_and_pdf_page(self):
        target = C18_T1_DIR / "listening.json"
        curation_path = (C18_T1_DIR / "curations.json").resolve()
        original_read_text = Path.read_text
        original = json.loads(original_read_text(curation_path, encoding="utf-8"))

        for field, value in (
            ("evidenceBoundingBox", [0.46, 0.488, 0.475, 0.22]),
            ("sourcePdfPage", 999999),
        ):
            modified = json.loads(json.dumps(original))
            listening_curation = next(c for c in modified["curations"] if c.get("skill") == "listening")
            listening_curation[field] = value

            def read_with_invalid_curation(path, *args, **kwargs):
                if path.resolve() == curation_path:
                    return json.dumps(modified)
                return original_read_text(path, *args, **kwargs)

            with self.subTest(field=field), patch.object(Path, "read_text", read_with_invalid_curation):
                result = validate_listening(target)
                failed = {check["name"] for check in result["checks"] if not check["passed"]}
                self.assertIn("fully_parser_derived_import_mode", failed)


if __name__ == "__main__":
    unittest.main()

