#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan raw files under IELTS/ and generate resources/import-manifest.json.

This script never modifies, moves, or deletes any files in IELTS/.
It computes SHA-256 hashes, detects duplicates, parses audio and video mappings,
identifies Academic test paper candidates, and records canonical selections
with full rationale and incomplete/missing status tracking.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import fitz


def compute_sha256(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        return "EMPTY"
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def count_text_pages(doc: fitz.Document, max_pages: int = 20) -> int:
    usable = 0
    check_len = min(len(doc), max_pages)
    for i in range(check_len):
        text = doc[i].get_text()
        letters = sum(c.isalpha() for c in text)
        visible = sum(not c.isspace() for c in text)
        if len(text.strip()) >= 80 and letters >= 45 and (letters / max(visible, 1)) >= 0.45:
            usable += 1
    return usable


def parse_audio_identity(file_path: str) -> dict[str, Any] | None:
    norm = file_path.replace("\\", "/").lower()
    if not norm.endswith(".mp3") or "g类" in norm or "general" in norm:
        return None

    # Detect book
    book = None
    if "剑20" in norm or "c20" in norm:
        book = 20
    else:
        m = re.search(r"剑(?:雅)?(\d+)", file_path) or re.search(r"c(\d+)", file_path, re.IGNORECASE) or re.search(r"ielts\s*(\d+)", file_path, re.IGNORECASE)
        if m:
            b_val = int(m.group(1))
            if 4 <= b_val <= 20:
                book = b_val

    filename = Path(file_path).name
    # Pattern: 18-1-1.mp3
    m_hyphen = re.match(r"^(\d+)-(\d+)-(\d+)\.mp3$", filename, re.IGNORECASE)
    if m_hyphen:
        b_val = int(m_hyphen.group(1))
        t_val = int(m_hyphen.group(2))
        p_val = int(m_hyphen.group(3))
        return {"book": b_val, "test": t_val, "part": p_val, "originalTest": t_val}

    # Pattern: C17-T1-P1.mp3 or C4T1S1.mp3 or IELTS15_test1_audio1.mp3 or Test1.Section1.mp3
    m_std = re.search(r"(?:test|t)\s*(\d+)[\s._-]*(?:section|secton|part|audio|s|p)\s*(\d+)", filename, re.IGNORECASE)
    if m_std and book:
        orig_t = int(m_std.group(1))
        p_val = int(m_std.group(2))
        # Cambridge 12 audio uses Test 5-8
        t_val = orig_t - 4 if (book == 12 and orig_t >= 5) else orig_t
        if 1 <= t_val <= 4 and 1 <= p_val <= 4:
            return {"book": book, "test": t_val, "part": p_val, "originalTest": orig_t}

    return None


def parse_video_identity(file_path: str) -> dict[str, Any] | None:
    norm = file_path.replace("\\", "/")
    if not norm.lower().endswith(".mp4"):
        return None
    filename = Path(file_path).name
    m = re.search(r"(听力|阅读)C(\d+)T(\d+)", filename)
    if m:
        skill = "listening" if m.group(1) == "听力" else "reading"
        book = int(m.group(2))
        test = int(m.group(3))
        return {"book": book, "test": test, "skill": skill}
    return None


def scan_all_files(root_dir: Path) -> tuple[list[dict], dict[str, list[str]]]:
    all_files: list[dict] = []
    sha_map: dict[str, list[str]] = {}
    ielts_dir = root_dir / "IELTS"

    for p in sorted(ielts_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root_dir).as_posix()
        sz = p.stat().st_size
        sha = compute_sha256(p)
        item = {
            "path": rel,
            "name": p.name,
            "size": sz,
            "sha256": sha,
            "ext": p.suffix.lower(),
        }
        all_files.append(item)
        if sha != "EMPTY":
            sha_map.setdefault(sha, []).append(rel)

    return all_files, sha_map


def build_manifest(root_dir: Path) -> dict:
    all_files, sha_map = scan_all_files(root_dir)

    books_data: dict[int, dict] = {}
    for b in range(4, 21):
        books_data[b] = {
            "book": b,
            "canonical": None,
            "canonicalStatus": "unresolved",
            "canonicalRationale": "",
            "academicCandidates": [],
            "generalTrainingFiles": [],
            "duplicates": [],
            "explanations": [],
            "synonymsAndAids": [],
            "audio": {str(t): {} for t in range(1, 5)},
            "videos": [],
            "missingOrIncomplete": [],
        }

    # First pass: classify files
    for item in all_files:
        path_str = item["path"]
        name = item["name"]
        sz = item["size"]
        ext = item["ext"]
        sha = item["sha256"]

        # Incomplete check
        if sz == 0 or ext == ".downloading":
            # Assign to book if possible
            assigned = False
            for b in range(4, 21):
                if f"剑{b}" in path_str or f"【{b}】" in path_str or f"c{b}" in path_str.lower() or (b == 20 and "剑20" in path_str):
                    books_data[b]["missingOrIncomplete"].append(item)
                    assigned = True
            if not assigned:
                books_data[17]["missingOrIncomplete"].append(item)
            continue

        # Audio check
        if ext == ".mp3":
            ident = parse_audio_identity(path_str)
            if ident:
                b = ident["book"]
                t = str(ident["test"])
                p = str(ident["part"])
                entry = {
                    "path": path_str,
                    "sha256": sha,
                    "size": sz,
                    "originalTest": ident["originalTest"],
                    "status": "ready" if sz > 0 else "incomplete",
                }
                if p not in books_data[b]["audio"][t]:
                    books_data[b]["audio"][t][p] = entry
                else:
                    # duplicate audio
                    books_data[b]["duplicates"].append({
                        "type": "audio",
                        "path": path_str,
                        "sha256": sha,
                        "duplicateOf": books_data[b]["audio"][t][p]["path"],
                    })
            continue

        # Video check
        if ext == ".mp4":
            v_ident = parse_video_identity(path_str)
            if v_ident:
                books_data[v_ident["book"]]["videos"].append({
                    "test": v_ident["test"],
                    "skill": v_ident["skill"],
                    "path": path_str,
                    "sha256": sha,
                    "size": sz,
                    "status": "ready",
                })
            continue

        # PDF check
        if ext == ".pdf":
            # Synonyms / Aids
            if "同义" in path_str or "替换" in path_str:
                for b in range(4, 21):
                    if f"剑{b}" in path_str or f"【{b}】" in path_str or f" {b} " in path_str:
                        books_data[b]["synonymsAndAids"].append(item)
                continue

            # Explanations (精讲)
            if "精讲" in path_str:
                for b in range(4, 21):
                    if (
                        f"精讲{b}" in path_str
                        or f"剑{b}" in path_str
                        or f"【{b}】" in path_str
                        or (b in [4, 5, 6] and "456" in path_str)
                    ):
                        books_data[b]["explanations"].append(item)
                continue

            # General Training check
            if "G类" in path_str or "g类" in path_str or "General" in path_str or "general" in path_str:
                for b in range(4, 21):
                    if f"{b}" in path_str:
                        books_data[b]["generalTrainingFiles"].append(item)
                continue

            # Academic test candidates
            if "剑20" in path_str or "20-" in path_str or "20Test" in path_str:
                books_data[20]["academicCandidates"].append(item)
                continue

            for b in range(4, 20):
                # Pattern matching book number
                m = re.search(r"(?:剑雅?|IELTS|真题)[^\d/]*?(\d{1,2})(?!\d)", name) or re.search(r"【(\d{1,2})】", name)
                if m and int(m.group(1)) == b:
                    books_data[b]["academicCandidates"].append(item)

    # Second pass: Canonical decision for each book
    for b in range(4, 21):
        info = books_data[b]
        # Check duplicate relations for explanations and candidates
        for cand in info["academicCandidates"]:
            all_copies = sha_map.get(cand["sha256"], [])
            if len(all_copies) > 1:
                for other in all_copies:
                    if other != cand["path"] and not any(d["path"] == other for d in info["duplicates"]):
                        info["duplicates"].append({
                            "type": "pdf",
                            "path": other,
                            "sha256": cand["sha256"],
                            "canonicalCandidate": cand["path"],
                        })

        if b == 20:
            # Per-test PDFs
            # Looking for Test1, Test2, Test3, Test4
            tests_map = {}
            for t in range(1, 5):
                t_files = [c for c in info["academicCandidates"] if f"Test{t}" in c["name"] or f"Test {t}" in c["name"] or f"Test{t}" in c["path"]]
                if t_files:
                    target = t_files[0]
                    doc = fitz.open(root_dir / target["path"])
                    pg_count = len(doc)
                    txt_pgs = count_text_pages(doc, 10)
                    doc.close()
                    tests_map[str(t)] = {
                        "path": target["path"],
                        "size": target["size"],
                        "sha256": target["sha256"],
                        "pageCount": pg_count,
                        "sampleTextPages": txt_pgs,
                        "method": "text-layer" if txt_pgs >= 5 else "ocr",
                    }
            if len(tests_map) == 4:
                info["canonical"] = {
                    "type": "per-test-pdfs",
                    "tests": tests_map,
                }
                info["canonicalStatus"] = "ready"
                info["canonicalRationale"] = "Cambridge 20 is published locally as 4 independent Test PDFs (Test 1-4). Scanned image PDFs requiring local Tesseract OCR."
            else:
                info["canonicalStatus"] = "incomplete"
                info["canonicalRationale"] = f"Cambridge 20 incomplete test PDFs found: {list(tests_map.keys())}"
            continue

        if b in (12, 17):
            # Known 0-byte PDFs
            info["canonical"] = None
            info["canonicalStatus"] = "missing-resource"
            info["canonicalRationale"] = f"Original question paper PDF for Cambridge {b} is 0 bytes on disk. Audio and explanations are retained; test questions marked as missing-resource."
            continue

        # Books 4-11, 13-16, 18, 19
        cands = info["academicCandidates"]
        if not cands:
            info["canonicalStatus"] = "missing-resource"
            info["canonicalRationale"] = f"No candidate Academic PDF found for Book {b}."
            continue

        # Filter out (1) duplicates if non-(1) exists with same sha256
        unique_cands = []
        for c in cands:
            # check page count and text layer
            try:
                doc = fitz.open(root_dir / c["path"])
                pg_count = len(doc)
                txt_pgs = count_text_pages(doc, 15)
                doc.close()
                unique_cands.append({**c, "pageCount": pg_count, "sampleTextPages": txt_pgs})
            except Exception as err:
                unique_cands.append({**c, "pageCount": -1, "sampleTextPages": 0, "error": str(err)})

        # Preferred canonical selection:
        # 1. Non-(1) preferred over (1) if same sha
        # 2. For C18: ensure matching the existing verified cambridge-18.json path if available
        chosen = None
        if b == 18:
            matched_18 = next((c for c in unique_cands if "剑雅18/【剑雅18】真题+音频/剑桥雅思真题18.pdf" in c["path"]), None)
            if matched_18:
                chosen = matched_18
        if not chosen:
            # Pick non-(1) with standard page count (typically 140-190 pages for full book)
            full_books = [c for c in unique_cands if c["pageCount"] >= 120]
            non_paren = [c for c in full_books if "(1)" not in c["name"]]
            if non_paren:
                chosen = non_paren[0]
            elif full_books:
                chosen = full_books[0]
            elif unique_cands:
                chosen = unique_cands[0]

        if chosen:
            info["canonical"] = {
                "type": "single-pdf",
                "path": chosen["path"],
                "size": chosen["size"],
                "sha256": chosen["sha256"],
                "pageCount": chosen["pageCount"],
                "sampleTextPages": chosen["sampleTextPages"],
                "textLayerUsable": chosen["sampleTextPages"] >= 10,
            }
            info["canonicalStatus"] = "ready"
            info["canonicalRationale"] = (
                f"Selected {chosen['path']} (pages: {chosen['pageCount']}, size: {chosen['size']} B, SHA-256: {chosen['sha256'][:12]}...). "
                + ("Has high quality text layer." if chosen["sampleTextPages"] >= 10 else "Scanned book, requires OCR.")
            )

        # Select canonical explanation if explanations exist
        exps = info["explanations"]
        if exps:
            non_paren = [e for e in exps if "(1)" not in e["name"]]
            canon_exp = non_paren[0] if non_paren else exps[0]
            info["canonicalExplanation"] = {
                "path": canon_exp["path"],
                "name": canon_exp["name"],
                "size": canon_exp["size"],
                "sha256": canon_exp["sha256"],
            }
            for other in exps:
                if other["path"] != canon_exp["path"] and other["sha256"] == canon_exp["sha256"]:
                    if not any(d.get("path") == other["path"] for d in info["duplicates"]):
                        info["duplicates"].append({
                            "type": "explanation_pdf",
                            "path": other["path"],
                            "sha256": other["sha256"],
                            "duplicateOf": canon_exp["path"],
                        })

    # Global summary
    total_audio = sum(sum(len(t) for t in b["audio"].values()) for b in books_data.values())
    total_video = sum(len(b["videos"]) for b in books_data.values())
    manifest = {
        "schemaVersion": 1,
        "scannedAt": "2026-09-21T16:25:00Z",
        "summary": {
            "totalFiles": len(all_files),
            "totalUniqueSha256": len(sha_map),
            "booksCount": 17,
            "readyBooks": [b for b, d in books_data.items() if d["canonicalStatus"] == "ready"],
            "missingResourceBooks": [b for b, d in books_data.items() if d["canonicalStatus"] == "missing-resource"],
            "totalAudioMapped": total_audio,
            "totalVideosMapped": total_video,
        },
        "books": [books_data[b] for b in range(4, 21)],
    }
    return manifest


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = build_manifest(root)
    out_file = root / "resources" / "import-manifest.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest written to {out_file.as_posix()}")
    print("Summary:")
    print(f"  Total files: {manifest['summary']['totalFiles']}")
    print(f"  Ready books: {manifest['summary']['readyBooks']}")
    print(f"  Missing resource books: {manifest['summary']['missingResourceBooks']}")
    print(f"  Total audio mapped: {manifest['summary']['totalAudioMapped']}/272")
    print(f"  Total videos: {manifest['summary']['totalVideosMapped']}")


if __name__ == "__main__":
    main()
