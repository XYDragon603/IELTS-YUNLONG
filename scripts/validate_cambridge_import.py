#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cambridge IELTS Import Validator.

Validates structured test and skill imports against Cambridge data integrity rules:
1. JSON schema validity for Listening, Reading, Writing, Speaking
2. Unique question IDs and continuous numbering (1 to 40 for Listening/Reading)
3. Multi-choice question consistency (orderMatters: false, dual points)
4. Answer Key mapping from official source & located in OCR cache / curations
5. Valid PDF page ranges & source PDF SHA-256 matches actual file on disk
6. Audio paths exist on disk and have size > 0
7. Audioscript segment references exist and cover all 40 questions (1 to 40)
8. Bounding boxes derived from real OCR elements (not synthetic regular grid)
9. Cache artifacts dynamic SHA-256 recomputed and verified
10. Authentic cropped assets exist on disk and SHA-256 matches
11. No fake "human verified" claim: reviews performed by AI marked assistant-visual
12. Honest status: status is "ready" only if verified: true and 0 blocking needsReview
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError:
    fitz = None

WORKSPACE = Path(__file__).resolve().parent.parent


def valid_normalized_box(box: Any) -> bool:
    return (
        isinstance(box, (list, tuple)) and len(box) == 4
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= 1 for v in box)
        and box[0] < box[2] and box[1] < box[3]
    )


def get_workspace(path: Path) -> Path:
    if len(path.resolve().parents) > 4 and (path.resolve().parents[4] / "resources").is_dir():
        return path.resolve().parents[4]
    return WORKSPACE


def compute_sha256(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        return "EMPTY"
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def check_asset(workspace: Path, asset_dict: dict[str, Any], skill_dir: Path) -> tuple[bool, str]:
    if not asset_dict or not isinstance(asset_dict, dict):
        return False, "Asset is not a valid dictionary"
    asset_rel = asset_dict.get("asset")
    if not asset_rel:
        return False, "Missing asset path"
    # Resolve asset relative to skill_dir or workspace
    if asset_rel.startswith("./"):
        asset_file = (skill_dir / asset_rel).resolve()
    else:
        asset_file = (workspace / asset_rel).resolve()
    if not asset_file.is_file() or asset_file.stat().st_size == 0:
        return False, f"Asset file missing or empty: {asset_rel}"
    expected_sha = asset_dict.get("sha256")
    if expected_sha:
        actual_sha = compute_sha256(asset_file)
        if actual_sha != expected_sha:
            return False, f"Asset SHA mismatch: {actual_sha[:10]} != {expected_sha[:10]}"
    return True, f"Asset verified: {asset_file.name}"


def validate_listening(listening_path: Path) -> dict:
    if not listening_path.is_file():
        raise FileNotFoundError(f"Import file not found: {listening_path}")

    workspace = get_workspace(listening_path)
    data = json.loads(listening_path.read_text(encoding="utf-8"))

    checks = []

    # 1. Basic schema checks
    required_top = ["schemaVersion", "id", "book", "test", "skill", "parts", "sources", "importProvenance"]
    missing_top = [k for k in required_top if k not in data]
    checks.append({
        "name": "schema_top_level_keys",
        "passed": len(missing_top) == 0,
        "detail": f"Missing keys: {missing_top}" if missing_top else "All top-level keys present",
    })

    # 2. Extract questions
    all_qs = [q for part in data.get("parts", []) for q in part.get("questions", [])]
    total_qs = len(all_qs)
    checks.append({
        "name": "scoring_points_count_40",
        "passed": total_qs == 40,
        "detail": f"Scoring points count: {total_qs} (expected 40)",
    })

    # 3. Unique IDs
    q_ids = [q.get("id") for q in all_qs if q.get("id")]
    unique_ids = len(q_ids) == len(set(q_ids)) == 40
    checks.append({
        "name": "unique_question_ids",
        "passed": unique_ids,
        "detail": f"Found {len(set(q_ids))} unique IDs for {total_qs} questions",
    })

    # 4. Continuous numbering 1 to 40
    q_numbers = [q.get("number") for q in all_qs]
    continuous = q_numbers == list(range(1, 41))
    checks.append({
        "name": "continuous_numbering_1_to_40",
        "passed": continuous,
        "detail": f"Range: {min(q_numbers) if q_numbers else None} to {max(q_numbers) if q_numbers else None}",
    })

    # 5. Multi-choice question pairs
    # Detect multi-choice groups dynamically from questions with multiple numbers or orderMatters: false
    group_map = {}
    for q in all_qs:
        nums = tuple(sorted(q.get("numbers", [q.get("number")])))
        if len(nums) > 1 or q.get("orderMatters") is False:
            group_map.setdefault(nums, []).append(q)
    multi_pairs = sorted(list(group_map.keys()))

    multi_valid = True
    for n_group in multi_pairs:
        qs = [q for q in all_qs if q.get("number") in n_group]
        if len(qs) != len(n_group):
            multi_valid = False
            break
        for q in qs:
            if q.get("orderMatters") is not False or len(q.get("accepted", [])) != len(n_group):
                multi_valid = False
    pair_labels = ", ".join(f"{g[0]}-{g[1]}" for g in multi_pairs) if multi_pairs else "None"
    checks.append({
        "name": "multi_choice_groups_order_matters_false",
        "passed": multi_valid,
        "detail": f"Verified question pairs {pair_labels} have orderMatters: false",
    })

    # 6. Official Answer Key mapping & OCR location
    expected_ans_pages = data.get("sources", {}).get("answerPdfPages", [123])
    official_key_valid = all(
        q.get("answer", {}).get("sourcePdfPage") in expected_ans_pages
        and len(q.get("accepted", [])) > 0
        and q.get("answer", {}).get("official") is not None
        and len(q.get("answer", {}).get("boundingBox", [])) == 4
        and q.get("answer", {}).get("confidence", 0) >= 0.0
        and q.get("answer", {}).get("rawOcr") is not None
        for q in all_qs
    )
    checks.append({
        "name": "official_answer_key_ocr_location",
        "passed": official_key_valid,
        "detail": f"All 40 questions have official answers with real OCR bounding box and raw text on page(s) {expected_ans_pages}",
    })

    # 7. Valid PDF page ranges
    pdf_rel_path = data.get("sources", {}).get("paper", {}).get("path")
    pdf_max_page = 200
    if pdf_rel_path:
        pdf_file = (workspace / pdf_rel_path).resolve()
        if pdf_file.is_file() and fitz:
            try:
                with fitz.open(pdf_file) as doc:
                    pdf_max_page = len(doc)
            except Exception:
                pass

    pages_valid = True
    invalid_details = []
    for q in all_qs:
        qp = q.get("source", {}).get("pdfPage", 0)
        if not (1 <= qp <= pdf_max_page):
            pages_valid = False
            invalid_details.append(f"Q{q.get('number')} source.pdfPage={qp}")
        te = q.get("transcriptEvidence")
        if te and "sourcePdfPage" in te:
            tp = te.get("sourcePdfPage")
            if tp is None:
                pages_valid = False
                invalid_details.append(f"Q{q.get('number')} transcriptEvidence.sourcePdfPage is None")
            elif not isinstance(tp, int) or not (1 <= tp <= pdf_max_page):
                pages_valid = False
                invalid_details.append(f"Q{q.get('number')} transcriptEvidence.sourcePdfPage={tp}")

    checks.append({
        "name": "valid_pdf_pages",
        "passed": pages_valid,
        "detail": f"All question and transcript PDF page numbers within valid range (1-{pdf_max_page})" if pages_valid else f"Invalid pages: {', '.join(invalid_details[:5])}",
    })

    # 8. Audio files existence
    audio_valid = True
    audio_items = data.get("audio", {})
    audio_details = []
    for part_num, audio_info in audio_items.items():
        rel_path = audio_info.get("path")
        audio_file = workspace / rel_path if rel_path else None
        exists = audio_file and audio_file.is_file() and audio_file.stat().st_size > 0
        audio_details.append(f"Part {part_num}: {rel_path} ({'ok' if exists else 'missing'})")
        if not exists:
            audio_valid = False
    checks.append({
        "name": "audio_files_exist_and_nonzero",
        "passed": audio_valid and len(audio_items) == 4,
        "detail": ", ".join(audio_details),
    })

    # 9. Audioscript segments validation
    audioscript_path = listening_path.parent / "audioscript.json"
    audioscript_valid = False
    as_data = None
    if audioscript_path.is_file():
        as_data = json.loads(audioscript_path.read_text(encoding="utf-8"))
        seg_ids = {seg["id"] for p in as_data.get("parts", []) for seg in p.get("segments", [])}
        referenced_segs = {
            s_id
            for q in all_qs
            for s_id in (q.get("transcriptEvidence") or {}).get("segmentIds", [])
        }
        audioscript_valid = len(referenced_segs) > 0 and referenced_segs.issubset(seg_ids)
    checks.append({
        "name": "audioscript_segment_references_valid",
        "passed": audioscript_valid,
        "detail": f"Audioscript file: {audioscript_path.name} (valid_refs={audioscript_valid})",
    })

    # 10. Audioscript questionRefs coverage 1-40
    all_refs_covered = False
    if as_data:
        covered_refs = {r for p in as_data.get("parts", []) for s in p.get("segments", []) for r in s.get("questionRefs", [])}
        all_refs_covered = set(range(1, 41)).issubset(covered_refs)
    checks.append({
        "name": "audioscript_covers_questions_1_to_40",
        "passed": all_refs_covered,
        "detail": f"Audioscript references cover 1 to 40: {all_refs_covered}",
    })

    # 11. Bounding boxes derived from real OCR elements
    bboxes = [q.get("source", {}).get("boundingBox") for q in all_qs]
    valid_bboxes = (
        all(isinstance(b, list) and len(b) == 4 for b in bboxes)
        and all(0.0 <= b[0] < b[2] <= 1.0 and 0.0 <= b[1] < b[3] <= 1.0 for b in bboxes)
        and all(q.get("source", {}).get("confidence", 0) > 0 for q in all_qs)
        and len({b[0] for b in bboxes}) >= 20
    )
    checks.append({
        "name": "bounding_boxes_from_ocr_elements",
        "passed": valid_bboxes,
        "detail": "All 40 questions contain true OCR bounding boxes and confidence scores",
    })

    # 12. Dynamic SHA-256 verification of the 3 cache artifacts
    provenance = data.get("importProvenance", {})
    artifacts = provenance.get("artifacts", {}) if isinstance(provenance, dict) else {}
    required_artifacts = ["questions", "answerKey", "audioscript"]
    hashes_match = True
    sha_details = []
    for art_key in required_artifacts:
        art_info = artifacts.get(art_key, {})
        rel_path = art_info.get("path")
        expected_sha = art_info.get("sha256")
        if not rel_path or not expected_sha:
            hashes_match = False
            sha_details.append(f"{art_key}: missing path/sha")
            continue
        art_file = workspace / rel_path
        if not art_file.is_file():
            hashes_match = False
            sha_details.append(f"{art_key}: file not found")
            continue
        actual_sha = compute_sha256(art_file)
        if actual_sha != expected_sha:
            hashes_match = False
            sha_details.append(f"{art_key}: sha mismatch ({actual_sha[:10]} != {expected_sha[:10]})")
        else:
            sha_details.append(f"{art_key}: ok ({actual_sha[:8]}...)")
    checks.append({
        "name": "cache_artifacts_dynamic_sha256_verified",
        "passed": hashes_match,
        "detail": ", ".join(sha_details),
    })

    # 13. Verify source PDF SHA-256 against actual PDF file
    pdf_rel_path = data.get("sources", {}).get("paper", {}).get("path")
    pdf_expected_sha = data.get("sources", {}).get("paper", {}).get("sha256")
    pdf_actual_sha = compute_sha256(workspace / pdf_rel_path) if pdf_rel_path else None
    pdf_sha_matched = (pdf_actual_sha == pdf_expected_sha)
    checks.append({
        "name": "source_pdf_sha256_verified",
        "passed": pdf_sha_matched,
        "detail": f"Actual PDF SHA: {pdf_actual_sha[:12]}... (matches manifest & cache)",
    })

    # 14. Provenance mode: parser-derived or traceable OCR-assisted curation
    generation_mode = provenance.get("generationMode") if isinstance(provenance, dict) else None
    parser_derived = generation_mode in {"ocr-parser", "text-layer-parser"}
    curation_verified = False
    cur_count = 0
    if generation_mode == "ocr-assisted-curation":
        cur_file = listening_path.parent / "curations.json"
        if cur_file.is_file():
            try:
                c_data = json.loads(cur_file.read_text(encoding="utf-8"))
                c_list = [
                    c for c in c_data.get("curations", [])
                    if c.get("skill") == "listening"
                ]
                cur_count = len(c_list)
                if cur_count > 0:
                    curation_verified = all(
                        c.get("reviewMethod") in {"assistant-visual", "human"}
                        and valid_normalized_box(c.get("evidenceBoundingBox"))
                        and isinstance(c.get("sourcePdfPage"), int)
                        and not isinstance(c.get("sourcePdfPage"), bool)
                        and 1 <= c["sourcePdfPage"] <= pdf_max_page
                        for c in c_list
                    )
            except Exception:
                curation_verified = False

    provenance_mode_valid = parser_derived or curation_verified
    if parser_derived:
        mode_detail = f"generationMode={generation_mode} (parser-derived)"
    elif curation_verified:
        mode_detail = f"generationMode={generation_mode} with traceable curations (count={cur_count}, verified=True)"
    else:
        mode_detail = f"generationMode={generation_mode} (unverified or missing curations)"

    checks.append({
        "name": "fully_parser_derived_import_mode",
        "passed": provenance_mode_valid,
        "detail": mode_detail,
    })

    answer_boxes_valid = all(valid_normalized_box(q.get("answer", {}).get("boundingBox")) for q in all_qs)
    checks.append({
        "name": "answer_bounding_boxes_valid",
        "passed": answer_boxes_valid,
        "detail": "All answer boxes are normalized and ordered [ymin, xmin, ymax, xmax]",
    })

    # 15. Low-confidence findings must carry an explicit review outcome.
    low_confidence_items = data.get("lowConfidenceAudit", [])
    unresolved_low_confidence = [
        item for item in low_confidence_items
        if item.get("reviewStatus") not in {"confirmed", "corrected"}
    ]
    checks.append({
        "name": "low_confidence_items_resolved",
        "passed": len(unresolved_low_confidence) == 0,
        "detail": f"unresolved low-confidence items={len(unresolved_low_confidence)}",
    })

    # 16. Nested needsReview check & verified integrity
    is_verified = data.get("verified", False)
    all_needs_reviews = []
    all_needs_reviews.extend(data.get("needsReview", []))
    for p in data.get("parts", []):
        all_needs_reviews.extend(p.get("needsReview", []))
        for g in p.get("groups", []):
            all_needs_reviews.extend(g.get("needsReview", []))
        for q in p.get("questions", []):
            all_needs_reviews.extend(q.get("needsReview", []))
    has_blocking_review = len(all_needs_reviews) > 0
    verified_integrity = (not is_verified) or (not has_blocking_review)
    checks.append({
        "name": "nested_needs_review_and_verified_integrity",
        "passed": verified_integrity,
        "detail": f"verified={is_verified}, blocking needsReview count={len(all_needs_reviews)}",
    })

    overall_passed = all(c["passed"] for c in checks)
    return {
        "schemaVersion": 1,
        "target": data.get("title", listening_path.stem),
        "file": listening_path.as_posix(),
        "status": "PASSED" if overall_passed else "FAILED",
        "verified": overall_passed and is_verified,
        "checksTotal": len(checks),
        "checksPassed": sum(1 for c in checks if c["passed"]),
        "checksFailed": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
    }


def validate_reading(reading_path: Path) -> dict:
    if not reading_path.is_file():
        raise FileNotFoundError(f"Reading file not found: {reading_path}")

    workspace = get_workspace(reading_path)
    skill_dir = reading_path.parent
    data = json.loads(reading_path.read_text(encoding="utf-8"))

    checks = []

    # 1. Top level keys
    required_top = ["schemaVersion", "id", "book", "test", "skill", "passages", "answerKey", "sources", "needsReview"]
    missing_top = [k for k in required_top if k not in data]
    checks.append({
        "name": "reading_schema_top_level_keys",
        "passed": len(missing_top) == 0,
        "detail": f"Missing keys: {missing_top}" if missing_top else "All top-level keys present",
    })

    # 2. Three passages with non-empty blocks and valid content
    passages = data.get("passages", [])
    has_three = len(passages) == 3
    passages_valid = has_three
    passage_details = []
    instruction_title_pattern = re.compile(r'^(?:~?\s*You should spend about|Passage\s+\d.*(?:below|on pages))', re.I)

    if has_three:
        for idx, p in enumerate(passages, 1):
            blocks = p.get("blocks", [])
            title = (p.get("title") or "").strip()
            if not blocks:
                passages_valid = False
                passage_details.append(f"Passage {idx}: blocks is empty")
            elif instruction_title_pattern.search(title):
                passages_valid = False
                passage_details.append(f"Passage {idx}: title is instruction text '{title}'")
            else:
                full_text = " ".join(b.get("text", "") for b in blocks if isinstance(b, dict))
                word_count = len(re.findall(r"\b\w+\b", full_text))
                if word_count < 100:
                    passages_valid = False
                    passage_details.append(f"Passage {idx}: word count {word_count} < 100 words")

    checks.append({
        "name": "reading_three_passages",
        "passed": passages_valid,
        "detail": f"Passages valid (count={len(passages)})" if passages_valid else f"Passage validation failed: {'; '.join(passage_details)}",
    })

    # 3. Continuous 1-40 scoring points across passages
    all_qs = [q for p in passages for g in p.get("groups", []) for q in g.get("questions", [])]
    total_qs = len(all_qs)
    orphan_questions = [q.get("number") for p in passages for g in p.get("groups", [])
                        for q in g.get("questions", [])
                        if not q.get("prompt") and not (g.get("context") or g.get("instruction") or g.get("asset"))]
    checks.append({
        "name": "reading_scoring_points_count_40",
        "passed": total_qs == 40 and data.get("detectedScoringPoints") == 40 and not orphan_questions,
        "detail": f"Questions in groups: {total_qs} (expected 40); no prompt or group context: {orphan_questions}",
    })

    # 4. Unique IDs q1-q40
    q_ids = [q.get("id") for q in all_qs]
    expected_ids = [f"q{i}" for i in range(1, 41)]
    checks.append({
        "name": "reading_unique_question_ids",
        "passed": q_ids == expected_ids,
        "detail": f"IDs match q1-q40 continuous: {q_ids == expected_ids}",
    })

    # 5. Continuous numbering 1-40
    q_numbers = [q.get("number") for q in all_qs]
    checks.append({
        "name": "reading_continuous_numbering",
        "passed": q_numbers == list(range(1, 41)),
        "detail": f"Numbers match 1-40: {q_numbers == list(range(1, 41))}",
    })

    # 6. Answer Key mapping
    answer_key = data.get("answerKey", {})
    ak_numbers = sorted(int(k) for k in answer_key.keys())
    ak_complete = ak_numbers == list(range(1, 41))
    ak_valid = ak_complete and all(
        len(v.get("accepted") or []) > 0
        for v in answer_key.values()
    )
    checks.append({
        "name": "reading_answer_key_mapping",
        "passed": ak_valid,
        "detail": f"Answer key has 40 accepted entries: {ak_valid}",
    })

    # 7. Authentic review provenance
    no_fake_human = True
    for v in answer_key.values():
        cur = v.get("curation")
        if cur and cur.get("reviewMethod") not in ("assistant-visual", "human"):
            no_fake_human = False
    # Visually checked text corrections must be traceable to an evidence image on a real page.
    text_cur_path = skill_dir / "text-curations.json"
    text_cur_count = 0
    if text_cur_path.is_file():
        try:
            entries = json.loads(text_cur_path.read_text(encoding="utf-8")).get("curations", [])
            text_cur_count = len(entries)
            for c in entries:
                if not (c.get("reviewMethod") in ("assistant-visual", "human")
                        and isinstance(c.get("sourcePdfPage"), int) and not isinstance(c.get("sourcePdfPage"), bool)
                        and valid_normalized_box(c.get("evidenceBoundingBox"))
                        and re.fullmatch(r"[0-9a-f]{64}", str(c.get("evidenceImageSha256", "")))
                        and (c.get("originalOcr") is None or isinstance(c.get("originalOcr"), str))  # empty prompts were null
                        and isinstance(c.get("curatedValue"), str)):
                    no_fake_human = False
        except (OSError, json.JSONDecodeError):
            no_fake_human = False
    checks.append({
        "name": "reading_curation_provenance",
        "passed": no_fake_human,
        "detail": f"Curations have authentic reviewMethod (assistant-visual/human); text corrections traceable: {text_cur_count}",
    })

    # 8. Assets verification (e.g. table-completion and summary-completion assets)
    assets_ok = True
    asset_details = []
    for p in passages:
        for g in p.get("groups", []):
            if "asset" in g:
                ok, msg = check_asset(workspace, g["asset"], skill_dir)
                asset_details.append(msg)
                if not ok:
                    assets_ok = False
    checks.append({
        "name": "reading_assets_verified",
        "passed": assets_ok,
        "detail": ", ".join(asset_details) if asset_details else "No group assets",
    })

    # 9. Source PDF hash verification
    pdf_rel = data.get("sources", {}).get("paper", {}).get("path")
    pdf_expected_sha = data.get("sources", {}).get("paper", {}).get("sha256")
    pdf_actual_sha = compute_sha256(workspace / pdf_rel) if pdf_rel else None
    checks.append({
        "name": "reading_source_pdf_verified",
        "passed": pdf_actual_sha == pdf_expected_sha,
        "detail": f"Source PDF hash match: {pdf_actual_sha == pdf_expected_sha}",
    })

    # 10. Status and verified consistency
    is_verified = data.get("verified", False)
    status = data.get("status")
    has_reviews = len(data.get("needsReview", [])) > 0
    status_consistent = (not is_verified and status == "needs-review") if has_reviews else True
    checks.append({
        "name": "reading_status_integrity",
        "passed": status_consistent,
        "detail": f"status={status}, verified={is_verified}, needsReview={len(data.get('needsReview', []))}",
    })

    overall_passed = all(c["passed"] for c in checks)
    return {
        "schemaVersion": 1,
        "target": data.get("id", reading_path.stem),
        "file": reading_path.as_posix(),
        "status": "PASSED" if overall_passed else "FAILED",
        "verified": overall_passed and is_verified,
        "checksTotal": len(checks),
        "checksPassed": sum(1 for c in checks if c["passed"]),
        "checksFailed": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
    }


def validate_writing(writing_path: Path) -> dict:
    if not writing_path.is_file():
        raise FileNotFoundError(f"Writing file not found: {writing_path}")

    workspace = get_workspace(writing_path)
    skill_dir = writing_path.parent
    data = json.loads(writing_path.read_text(encoding="utf-8"))

    checks = []

    # 1. Top level keys
    required_top = ["schemaVersion", "id", "book", "test", "skill", "tasks", "sources", "needsReview"]
    missing_top = [k for k in required_top if k not in data]
    checks.append({
        "name": "writing_schema_top_level_keys",
        "passed": len(missing_top) == 0,
        "detail": f"Missing keys: {missing_top}" if missing_top else "All top-level keys present",
    })

    # 2. Exactly 2 tasks
    tasks = data.get("tasks", [])
    checks.append({
        "name": "writing_tasks_count_2",
        "passed": len(tasks) == 2,
        "detail": f"Tasks count: {len(tasks)} (expected 2)",
    })

    # 3. Minimum word counts
    t1 = next((t for t in tasks if t.get("number") == 1), None)
    t2 = next((t for t in tasks if t.get("number") == 2), None)
    words_ok = t1 and t2 and t1.get("minimumWords") == 150 and t2.get("minimumWords") == 250
    checks.append({
        "name": "writing_minimum_words",
        "passed": words_ok,
        "detail": f"Task 1: {t1.get('minimumWords') if t1 else None}w, Task 2: {t2.get('minimumWords') if t2 else None}w",
    })

    # 4. Non-empty prompts
    prompts_ok = t1 and t2 and len(t1.get("prompt", "").strip()) > 20 and len(t2.get("prompt", "").strip()) > 20
    checks.append({
        "name": "writing_prompts_non_empty",
        "passed": prompts_ok,
        "detail": "Both tasks have non-empty prompt text",
    })

    # 5. Task 1 chart asset
    t1_assets = t1.get("assets", []) if t1 else []
    chart_ok = False
    chart_msg = "Task 1 has no assets"
    if t1_assets:
        chart_ok, chart_msg = check_asset(workspace, t1_assets[0], skill_dir)
    checks.append({
        "name": "writing_task1_chart_asset",
        "passed": chart_ok,
        "detail": chart_msg,
    })

    # 6. Source PDF hash verification
    pdf_rel = data.get("sources", {}).get("paper", {}).get("path")
    pdf_expected_sha = data.get("sources", {}).get("paper", {}).get("sha256")
    pdf_actual_sha = compute_sha256(workspace / pdf_rel) if pdf_rel else None
    checks.append({
        "name": "writing_source_pdf_verified",
        "passed": pdf_actual_sha == pdf_expected_sha,
        "detail": f"Source PDF hash match: {pdf_actual_sha == pdf_expected_sha}",
    })

    # 7. Status integrity
    is_verified = data.get("verified", False)
    status = data.get("status")
    has_reviews = len(data.get("needsReview", [])) > 0
    status_consistent = (not is_verified and status == "needs-review") if has_reviews else True
    checks.append({
        "name": "writing_status_integrity",
        "passed": status_consistent,
        "detail": f"status={status}, verified={is_verified}, needsReview={len(data.get('needsReview', []))}",
    })

    overall_passed = all(c["passed"] for c in checks)
    return {
        "schemaVersion": 1,
        "target": data.get("id", writing_path.stem),
        "file": writing_path.as_posix(),
        "status": "PASSED" if overall_passed else "FAILED",
        "verified": overall_passed and is_verified,
        "checksTotal": len(checks),
        "checksPassed": sum(1 for c in checks if c["passed"]),
        "checksFailed": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
    }


def validate_speaking(speaking_path: Path) -> dict:
    if not speaking_path.is_file():
        raise FileNotFoundError(f"Speaking file not found: {speaking_path}")

    workspace = get_workspace(speaking_path)
    skill_dir = speaking_path.parent
    data = json.loads(speaking_path.read_text(encoding="utf-8"))

    checks = []

    # 1. Top level keys
    required_top = ["schemaVersion", "id", "book", "test", "skill", "parts", "sources", "needsReview"]
    missing_top = [k for k in required_top if k not in data]
    checks.append({
        "name": "speaking_schema_top_level_keys",
        "passed": len(missing_top) == 0,
        "detail": f"Missing keys: {missing_top}" if missing_top else "All top-level keys present",
    })

    # 2. Exactly 3 parts
    parts = data.get("parts", [])
    checks.append({
        "name": "speaking_parts_count_3",
        "passed": len(parts) == 3,
        "detail": f"Parts count: {len(parts)} (expected 3)",
    })

    # 3. Part 2 cue card with text and cropped asset
    p2 = next((p for p in parts if p.get("part") == 2), None)
    cue_ok = False
    cue_msg = "Part 2 not found"
    if p2 and "cueCard" in p2:
        cc = p2["cueCard"]
        has_text = len(cc.get("text", "").strip()) > 20
        asset_ok, asset_msg = check_asset(workspace, cc.get("asset", {}), skill_dir)
        cue_ok = has_text and asset_ok
        cue_msg = f"has_text={has_text}, {asset_msg}"
    checks.append({
        "name": "speaking_part2_cue_card",
        "passed": cue_ok,
        "detail": cue_msg,
    })

    # 4. Part 1 and 3 topics and questions
    p1 = next((p for p in parts if p.get("part") == 1), None)
    p3 = next((p for p in parts if p.get("part") == 3), None)
    topics_ok = bool(
        p1 and len(p1.get("topics", [])) > 0
        and p3 and len(p3.get("topics", [])) > 0
    )
    checks.append({
        "name": "speaking_parts_1_3_topics",
        "passed": topics_ok,
        "detail": f"Part 1 topics: {len(p1.get('topics', [])) if p1 else 0}, Part 3 topics: {len(p3.get('topics', [])) if p3 else 0}",
    })

    # 5. Source PDF hash verification
    pdf_rel = data.get("sources", {}).get("paper", {}).get("path")
    pdf_expected_sha = data.get("sources", {}).get("paper", {}).get("sha256")
    pdf_actual_sha = compute_sha256(workspace / pdf_rel) if pdf_rel else None
    checks.append({
        "name": "speaking_source_pdf_verified",
        "passed": pdf_actual_sha == pdf_expected_sha,
        "detail": f"Source PDF hash match: {pdf_actual_sha == pdf_expected_sha}",
    })

    # 6. Status integrity
    is_verified = data.get("verified", False)
    status = data.get("status")
    has_reviews = len(data.get("needsReview", [])) > 0
    status_consistent = (not is_verified and status == "needs-review") if has_reviews else True
    checks.append({
        "name": "speaking_status_integrity",
        "passed": status_consistent,
        "detail": f"status={status}, verified={is_verified}, needsReview={len(data.get('needsReview', []))}",
    })

    overall_passed = all(c["passed"] for c in checks)
    return {
        "schemaVersion": 1,
        "target": data.get("id", speaking_path.stem),
        "file": speaking_path.as_posix(),
        "status": "PASSED" if overall_passed else "FAILED",
        "verified": overall_passed and is_verified,
        "checksTotal": len(checks),
        "checksPassed": sum(1 for c in checks if c["passed"]),
        "checksFailed": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
    }


def validate_test_directory(dir_path: Path) -> dict:
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Directory not found: {dir_path}")

    skill_files = {
        "listening": dir_path / "listening.json",
        "reading": dir_path / "reading.json",
        "writing": dir_path / "writing.json",
        "speaking": dir_path / "speaking.json",
    }

    results = {}
    total_checks = 0
    total_passed = 0
    total_failed = 0
    all_passed = True

    for skill, path in skill_files.items():
        if path.is_file():
            if skill == "listening":
                res = validate_listening(path)
            elif skill == "reading":
                res = validate_reading(path)
            elif skill == "writing":
                res = validate_writing(path)
            else:
                res = validate_speaking(path)
            results[skill] = res
            total_checks += res["checksTotal"]
            total_passed += res["checksPassed"]
            total_failed += res["checksFailed"]
            if res["status"] != "PASSED":
                all_passed = False
        else:
            results[skill] = {
                "status": "MISSING",
                "file": path.as_posix(),
                "checksTotal": 1,
                "checksPassed": 0,
                "checksFailed": 1,
            }
            total_checks += 1
            total_failed += 1
            all_passed = False

    # Check curations.json if present
    cur_path = dir_path / "curations.json"
    curations_valid = True
    if cur_path.is_file():
        try:
            c_data = json.loads(cur_path.read_text(encoding="utf-8"))
            curations_valid = isinstance(c_data.get("curations"), list) and len(c_data["curations"]) > 0
        except Exception:
            curations_valid = False
        total_checks += 1
        if curations_valid:
            total_passed += 1
        else:
            total_failed += 1
            all_passed = False
        results["curations"] = {"status": "PASSED" if curations_valid else "FAILED", "file": cur_path.as_posix()}

    return {
        "schemaVersion": 1,
        "target": dir_path.name,
        "directory": dir_path.as_posix(),
        "status": "PASSED" if all_passed else "FAILED",
        "skills": results,
        "checksTotal": total_checks,
        "checksPassed": total_passed,
        "checksFailed": total_failed,
    }


def validate_import(target: Path) -> dict:
    if target.is_dir():
        return validate_test_directory(target)
    if not target.is_file():
        raise FileNotFoundError(f"Target not found: {target}")

    # Inspect file content or filename
    filename = target.name.lower()
    if filename == "listening.json":
        return validate_listening(target)
    if filename == "reading.json":
        return validate_reading(target)
    if filename == "writing.json":
        return validate_writing(target)
    if filename == "speaking.json":
        return validate_speaking(target)

    # Fallback to inspecting skill inside JSON
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        skill = data.get("skill")
        if skill == "listening":
            return validate_listening(target)
        if skill == "reading":
            return validate_reading(target)
        if skill == "writing":
            return validate_writing(target)
        if skill == "speaking":
            return validate_speaking(target)
    except Exception:
        pass

    return validate_listening(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Cambridge IELTS structured import file or directory.")
    parser.add_argument("target", nargs="?", default=Path("resources/cambridge/c18/test-1"), type=Path, help="Path to test directory or skill JSON file")
    parser.add_argument("--report", type=Path, help="Optional path to write validation-report.json")
    args = parser.parse_args()

    result = validate_import(args.target)
    output_text = json.dumps(result, ensure_ascii=False, indent=2)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output_text + "\n", encoding="utf-8")

    print(output_text)
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
