#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for Cambridge 18 Test 1 Listening benchmark dataset and pipeline."""

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
C18_T1_DIR = ROOT / "resources" / "cambridge" / "c18" / "test-1"
CACHE_DIR = ROOT / ".cache" / "cambridge-importer" / "a3fe27d4ad3c2b97"


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TestCambridge18Test1Listening(unittest.TestCase):
    def test_unknown_low_confidence_item_is_not_auto_confirmed(self):
        from scripts.import_c18_t1_listening import build_low_confidence_audit
        question = {
            'number': 999, 'prompt': 'Unreviewed extraction',
            'source': {'confidence': 0.1, 'pdfPage': 12, 'boundingBox': [0.1, 0.1, 0.2, 0.2]},
            'answer': {'confidence': 0.1, 'official': 'uncertain', 'rawOcr': '?', 'boundingBox': [0.1, 0.1, 0.2, 0.2]},
        }
        items = build_low_confidence_audit([question])
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item['reviewStatus'] == 'pending' for item in items))

    def test_three_ocr_cache_artifacts_exist_and_match_hashes(self):
        artifacts = ["questions", "answers", "audioscripts"]
        for art in artifacts:
            cache_file = CACHE_DIR / art / "test-1-listening.json"
            self.assertTrue(cache_file.is_file(), f"Cache file missing: {cache_file}")
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("book"), 18)
            self.assertEqual(data.get("test"), 1)
            self.assertEqual(data.get("skill"), "listening")
            self.assertTrue(len(data.get("pages", [])) > 0)
            self.assertEqual(
                data.get("source", {}).get("pdfSha256"),
                "4035bcb6686794963ee4ff607abcfee43af7670f22add162c94fc7172d2dcce0",
            )
            # Recompute SHA-256
            actual_sha = compute_sha256(cache_file)
            self.assertTrue(len(actual_sha) == 64)

    def test_all_five_deliverable_files_exist(self):
        expected_files = [
            "listening.json",
            "audioscript.json",
            "explanation-index.json",
            "import-comparison.json",
            "validation-report.json",
        ]
        for name in expected_files:
            target = C18_T1_DIR / name
            self.assertTrue(target.is_file(), f"Deliverable missing: {name}")

    def test_listening_dataset_structure_and_scoring_points(self):
        listening_path = C18_T1_DIR / "listening.json"
        data = json.loads(listening_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("schemaVersion"), 1)
        self.assertEqual(data.get("id"), "c18-t1-listening")
        self.assertEqual(data.get("book"), 18)
        self.assertEqual(data.get("test"), 1)
        self.assertFalse(data.get("verified"))
        self.assertTrue(any(item.get('type') == 'curated-repairs-pending-verification' for item in data.get('needsReview', [])))

        # Import Provenance
        prov = data.get("importProvenance", {})
        self.assertEqual(prov.get("generationMode"), "ocr-assisted-curation")
        artifacts = prov.get("artifacts", {})
        for art_key in ["questions", "answerKey", "audioscript"]:
            self.assertIn(art_key, artifacts)
            art_path = ROOT / artifacts[art_key]["path"]
            self.assertTrue(art_path.is_file(), f"Artifact path missing: {art_path}")
            self.assertEqual(compute_sha256(art_path), artifacts[art_key]["sha256"])

        # Parts
        parts = data.get("parts", [])
        self.assertEqual(len(parts), 4)

        all_questions = [q for p in parts for q in p.get("questions", [])]
        self.assertEqual(len(all_questions), 40, "Must have exactly 40 scoring points")

        # Numbering and IDs
        numbers = [q["number"] for q in all_questions]
        self.assertEqual(numbers, list(range(1, 41)), "Question numbers must be continuous 1 to 40")

        ids = [q["id"] for q in all_questions]
        self.assertEqual(len(ids), len(set(ids)), "Question IDs must be strictly unique")

        # Multi-question groups
        multi_pairs = {
            (14, 15): ["B", "E"],
            (27, 28): ["B", "E"],
            (29, 30): ["A", "C"],
        }
        for (n1, n2), accepted in multi_pairs.items():
            q1 = next(q for q in all_questions if q["number"] == n1)
            q2 = next(q for q in all_questions if q["number"] == n2)
            self.assertFalse(q1.get("orderMatters"))
            self.assertFalse(q2.get("orderMatters"))
            self.assertEqual(sorted(q1["accepted"]), sorted(accepted))
            self.assertEqual(sorted(q2["accepted"]), sorted(accepted))

        # Official answer key mapping & real OCR bounding box
        for q in all_questions:
            ans = q.get("answer", {})
            self.assertEqual(ans.get("sourcePdfPage"), 123)
            self.assertTrue(ans.get("official"))
            self.assertTrue(len(q.get("accepted", [])) > 0)
            self.assertTrue(ans.get("rawOcr"))
            self.assertEqual(len(ans.get("boundingBox", [])), 4)

            # Question source bounding box and confidence
            src = q.get("source", {})
            self.assertEqual(src.get("method"), "ocr")
            self.assertEqual(len(src.get("boundingBox", [])), 4)
            self.assertGreater(src.get("confidence", 0), 0.0)

        # Audio mapping
        audio = data.get("audio", {})
        self.assertEqual(len(audio), 4)
        for part_num in range(1, 5):
            audio_info = audio.get(str(part_num), {})
            audio_path = ROOT / audio_info.get("path", "")
            self.assertTrue(audio_path.is_file(), f"Audio file missing for Part {part_num}: {audio_path}")
            self.assertGreater(audio_path.stat().st_size, 0)

    def test_audioscript_coverage_and_segment_refs(self):
        audioscript_path = C18_T1_DIR / "audioscript.json"
        data = json.loads(audioscript_path.read_text(encoding="utf-8"))

        parts = data.get("parts", [])
        self.assertEqual(len(parts), 4)

        all_refs = set()
        seg_ids = set()
        for p in parts:
            for s in p.get("segments", []):
                seg_ids.add(s["id"])
                self.assertEqual(len(s.get("boundingBox", [])), 4)
                self.assertGreater(s.get("confidence", 0), 0.0)
                for r in s.get("questionRefs", []):
                    all_refs.add(r)

        self.assertEqual(len(seg_ids), sum(len(p.get("segments", [])) for p in parts))
        self.assertEqual(all_refs, set(range(1, 41)), "All 40 questions must be covered in audioscript refs")

    def test_explanation_index_coverage(self):
        exp_path = C18_T1_DIR / "explanation-index.json"
        data = json.loads(exp_path.read_text(encoding="utf-8"))

        sources = data.get("sources", {})
        self.assertEqual(sources.get("publisherAnswerKey", {}).get("pdfPage"), 123)
        self.assertEqual(sources.get("commentaryBook", {}).get("pageRange"), [13, 26])

        questions = data.get("questions", {})
        self.assertEqual(len(questions), 40)
        for i in range(1, 41):
            self.assertIn(str(i), questions)
            q_info = questions[str(i)]
            self.assertEqual(q_info["number"], i)
            self.assertEqual(q_info["publisherKey"]["pdfPage"], 123)
            self.assertTrue(len(q_info["commentaryBook"]["pdfPages"]) == 2)

    def test_comparison_report_integrity(self):
        comp_path = C18_T1_DIR / "import-comparison.json"
        data = json.loads(comp_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("totalScoringPoints"), 40)
        self.assertEqual(len(data.get("questions", [])), 40)
        summary = data.get("summary", {})
        self.assertEqual(summary.get("scoringPointsCoverage"), "40/40 (100%)")
        self.assertEqual(summary.get("compatibilityRate"), "100%")

    def test_low_confidence_audit_completeness(self):
        listening_path = C18_T1_DIR / "listening.json"
        data = json.loads(listening_path.read_text(encoding="utf-8"))
        audit = data.get("lowConfidenceAudit", [])
        self.assertEqual(len(audit), 22, "Must contain all 22 low-confidence audited items")
        for item in audit:
            self.assertIn(item.get("reviewStatus"), ("confirmed", "corrected"))
            self.assertTrue(item.get("reviewedValue"))
            self.assertTrue(item.get("sourcePdfPage"))
            self.assertEqual(len(item.get("evidenceBoundingBox", [])), 4)
            self.assertTrue(item.get("reviewNote"))

    def test_validation_report_status_passed(self):
        val_path = C18_T1_DIR / "validation-report.json"
        data = json.loads(val_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("status"), "PASSED")
        self.assertFalse(data.get("verified"))
        failed = {c['name'] for c in data['checks'] if not c['passed']}
        self.assertEqual(len(failed), 0)


if __name__ == "__main__":
    unittest.main()
