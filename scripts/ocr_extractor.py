#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract and cache genuine OCR word- and line-level data from Cambridge PDFs.

Produces rich OCR cache files containing:
- pdfPage, printedPage, method, rawText
- word-level and line-level genuine bounding boxes [ymin, xmin, ymax, xmax]
- word-level and line-level genuine OCR confidences
- original PDF SHA-256 and cache SHA-256
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import fitz


def get_tesseract_cmd() -> str:
    cmd = shutil.which("tesseract")
    if cmd:
        return cmd
    for candidate in [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("Tesseract executable not found.")


def compute_sha256(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        return "EMPTY"
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_string_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_page_ocr(doc: fitz.Document, page_idx: int, tesseract_cmd: str, dpi: int = 120) -> dict[str, Any]:
    """Extract complete OCR word and line data for a page using Tesseract TSV."""
    page = doc[page_idx]
    scale = dpi / 72.0
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csGRAY, alpha=False)
    w, h = pixmap.width, pixmap.height

    # Run Tesseract TSV
    process = subprocess.run(
        [tesseract_cmd, "stdin", "stdout", "-l", "eng", "--psm", "6", "tsv"],
        input=pixmap.tobytes("png"),
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        process = subprocess.run(
            [tesseract_cmd, "stdin", "stdout", "-l", "eng", "tsv"],
            input=pixmap.tobytes("png"),
            capture_output=True,
            check=False,
        )
    if process.returncode != 0:
        raise RuntimeError(f"Tesseract failed on page {page_idx + 1}: {process.stderr.decode('utf-8', errors='replace')}")

    tsv_output = process.stdout.decode("utf-8", errors="replace")
    tsv_lines = tsv_output.splitlines()

    lines: list[dict[str, Any]] = []
    current_line: dict[str, Any] | None = None

    for row in tsv_lines[1:]:
        cols = row.split("\t")
        if len(cols) < 12:
            continue
        level = cols[0]
        left, top, width, height = int(cols[6]), int(cols[7]), int(cols[8]), int(cols[9])
        raw_conf = float(cols[10])
        text = cols[11].strip()

        ymin = round(top / h, 4)
        xmin = round(left / w, 4)
        ymax = round((top + height) / h, 4)
        xmax = round((left + width) / w, 4)

        if level == "4":  # Line
            current_line = {
                "text": "",
                "boundingBox": [ymin, xmin, ymax, xmax],
                "confidence": 0.0,
                "words": [],
            }
            lines.append(current_line)
        elif level == "5" and text:  # Word
            norm_conf = max(0.0, min(1.0, raw_conf / 100.0))
            word_obj = {
                "text": text,
                "confidence": round(norm_conf, 4),
                "boundingBox": [ymin, xmin, ymax, xmax],
            }
            if current_line is None:
                current_line = {
                    "text": "",
                    "boundingBox": [ymin, xmin, ymax, xmax],
                    "confidence": 0.0,
                    "words": [],
                }
                lines.append(current_line)

            current_line["words"].append(word_obj)
            current_line["text"] = " ".join(w["text"] for w in current_line["words"])
            avg_line_conf = sum(w["confidence"] for w in current_line["words"]) / len(current_line["words"])
            current_line["confidence"] = round(avg_line_conf, 4)

    # Filter out empty lines
    non_empty_lines = [line for line in lines if line["words"]]

    # Overall page rawText and confidence
    all_words = [w for line in non_empty_lines for w in line["words"]]
    page_conf = round(sum(w["confidence"] for w in all_words) / len(all_words), 4) if all_words else 0.0
    raw_text = "\n".join(line["text"] for line in non_empty_lines)

    # Detect printed page number from bottom 15% of page
    printed_page: int | None = None
    bottom_candidates = [
        line["text"]
        for line in non_empty_lines
        if line["boundingBox"][0] >= 0.85
    ]
    for c_line in reversed(bottom_candidates):
        match = re.search(r"\b(\d{1,3})\b", c_line)
        if match and 1 <= int(match.group(1)) <= 300:
            printed_page = int(match.group(1))
            break

    return {
        "pdfPage": page_idx + 1,
        "printedPage": printed_page,
        "method": "ocr",
        "dimensions": {"width": w, "height": h, "dpi": dpi},
        "rawText": raw_text,
        "confidence": page_conf,
        "wordCount": len(all_words),
        "lineCount": len(non_empty_lines),
        "lines": non_empty_lines,
    }


def extract_and_cache_group(
    pdf_path: Path,
    pages: list[int],
    output_file: Path,
    category: str,
    book: int = 18,
    test: int = 1,
    skill: str = "listening",
    dpi: int = 120,
) -> dict[str, Any]:
    """Extract OCR data for a list of pages and write out the structured cache file."""
    tesseract = get_tesseract_cmd()
    doc = fitz.open(pdf_path)
    pdf_sha = compute_sha256(pdf_path)

    page_records = []
    for p_num in pages:
        p_data = extract_page_ocr(doc, p_num - 1, tesseract, dpi=dpi)
        p_data["sourcePdfSha256"] = pdf_sha
        page_records.append(p_data)

    payload = {
        "schemaVersion": 1,
        "book": book,
        "test": test,
        "skill": skill,
        "category": category,
        "source": {
            "pdfPath": pdf_path.as_posix(),
            "pdfSha256": pdf_sha,
            "pageCount": len(pages),
            "pages": pages,
        },
        "pages": page_records,
        "summary": {
            "pageCount": len(page_records),
            "totalWords": sum(p["wordCount"] for p in page_records),
            "totalLines": sum(p["lineCount"] for p in page_records),
            "avgConfidence": round(sum(p["confidence"] for p in page_records) / max(len(page_records), 1), 4),
        },
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    text_content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output_file.write_text(text_content, encoding="utf-8")

    # Compute cache file hash
    cache_sha = compute_sha256(output_file)
    payload["cacheSha256"] = cache_sha
    # rewrite with cacheSha256 embedded
    text_content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output_file.write_text(text_content, encoding="utf-8")
    final_sha = compute_sha256(output_file)

    return {
        "output": output_file.as_posix(),
        "category": category,
        "pages": pages,
        "sha256": final_sha,
        "pdfSha256": pdf_sha,
        "avgConfidence": payload["summary"]["avgConfidence"],
        "words": payload["summary"]["totalWords"],
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Extract and cache genuine OCR word- and line-level data.")
    parser.add_argument("--book", type=int, default=18)
    parser.add_argument("--test", type=int, default=1)
    args = parser.parse_args()

    workspace = Path(__file__).resolve().parent.parent
    page_map_path = workspace / "resources" / "page-maps" / f"cambridge-{args.book}.json"
    if not page_map_path.exists():
        page_map_path = workspace / "resources" / "page-maps" / f"cambridge-{args.book:02d}.json"
    if not page_map_path.exists():
        raise FileNotFoundError(f"Page map not found for book {args.book}")

    page_map = json.loads(page_map_path.read_text(encoding="utf-8"))
    source = page_map["source"]
    if source.get("type") == "per-test-pdfs":
        test_source = source["tests"][str(args.test)]
        pdf_path = workspace / test_source["path"]
        fingerprint = test_source.get("fingerprint") or compute_sha256(pdf_path)[:16]
    else:
        pdf_path = workspace / source["path"]
        fingerprint = source.get("fingerprint") or compute_sha256(pdf_path)[:16]
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    cache_base = workspace / ".cache" / "cambridge-importer" / fingerprint

    all_book_configs = {
        12: {
            1: {"questions": list(range(10, 16)), "answers": [116], "audioscripts": list(range(95, 100))},
            2: {"questions": list(range(30, 36)), "answers": [118], "audioscripts": list(range(100, 105))},
            3: {"questions": list(range(53, 59)), "answers": [120], "audioscripts": list(range(105, 110))},
            4: {"questions": list(range(74, 80)), "answers": [122], "audioscripts": list(range(110, 116))},
        },
        13: {
            1: {"questions": list(range(11, 17)), "answers": [121], "audioscripts": list(range(100, 105))},
            2: {"questions": list(range(35, 41)), "answers": [123], "audioscripts": list(range(105, 111))},
            3: {"questions": list(range(57, 63)), "answers": [125], "audioscripts": list(range(111, 116))},
            4: {"questions": list(range(79, 85)), "answers": [127], "audioscripts": list(range(116, 121))},
        },
        14: {
            1: {"questions": list(range(11, 17)), "answers": [122], "audioscripts": list(range(100, 105))},
            2: {"questions": list(range(35, 41)), "answers": [124], "audioscripts": list(range(105, 111))},
            3: {"questions": list(range(56, 62)), "answers": [126], "audioscripts": list(range(111, 116))},
            4: {"questions": list(range(78, 85)), "answers": [128], "audioscripts": list(range(116, 122))},
        },
        15: {
            1: {"questions": list(range(12, 18)), "answers": [123], "audioscripts": list(range(100, 105))},
            2: {"questions": list(range(35, 41)), "answers": [125], "audioscripts": list(range(105, 111))},
            3: {"questions": list(range(56, 62)), "answers": [127], "audioscripts": list(range(111, 117))},
            4: {"questions": list(range(78, 84)), "answers": [129], "audioscripts": list(range(117, 123))},
        },
        16: {
            1: {"questions": list(range(11, 17)), "answers": [123], "audioscripts": list(range(100, 105))},
            2: {"questions": list(range(33, 39)), "answers": [125], "audioscripts": list(range(105, 110))},
            3: {"questions": list(range(55, 61)), "answers": [127], "audioscripts": list(range(110, 115))},
            4: {"questions": list(range(77, 83)), "answers": [129], "audioscripts": list(range(115, 120))},
        },
        17: {
            1: {"questions": list(range(10, 16)), "answers": [119], "audioscripts": list(range(96, 101))},
            2: {"questions": list(range(31, 37)), "answers": [121], "audioscripts": list(range(101, 107))},
            3: {"questions": list(range(53, 59)), "answers": [123], "audioscripts": list(range(107, 113))},
            4: {"questions": list(range(75, 81)), "answers": [125], "audioscripts": list(range(113, 119))},
        },
        18: {
            1: {"questions": list(range(12, 18)), "answers": [123], "audioscripts": list(range(103, 108))},
            2: {"questions": list(range(36, 43)), "answers": [125], "audioscripts": list(range(108, 113))},
            3: {"questions": list(range(59, 65)), "answers": [127], "audioscripts": list(range(113, 118))},
            4: {"questions": list(range(82, 88)), "answers": [129], "audioscripts": list(range(118, 123))},
        },
        19: {
            1: {"questions": list(range(11, 17)), "answers": [123], "audioscripts": list(range(102, 107))},
            2: {"questions": list(range(36, 43)), "answers": [125], "audioscripts": list(range(106, 112))},
            3: {"questions": list(range(58, 65)), "answers": [127], "audioscripts": list(range(111, 117))},
            4: {"questions": list(range(81, 87)), "answers": [129], "audioscripts": list(range(117, 123))},
        },
        20: {
            1: {"questions": list(range(2, 6)), "answers": [5], "audioscripts": list(range(2, 6))},
            2: {"questions": list(range(2, 7)), "answers": [7], "audioscripts": list(range(2, 7))},
            3: {"questions": list(range(2, 7)), "answers": [6], "audioscripts": list(range(2, 7))},
            4: {"questions": list(range(2, 7)), "answers": [6], "audioscripts": list(range(2, 7))},
        },
    }
    book_cfg = all_book_configs.get(args.book)
    if not book_cfg:
        raise ValueError(f"Unsupported book {args.book}")
    cfg = book_cfg.get(args.test)
    if not cfg:
        raise ValueError(f"Unsupported test {args.test} for book {args.book}")

    print(f"=== Extracting Genuine OCR Data for Cambridge {args.book} Test {args.test} Listening ===")

    # 1. Questions
    q_file = cache_base / "questions" / f"test-{args.test}-listening.json"
    res_q = extract_and_cache_group(pdf_path, cfg["questions"], q_file, "questions", book=args.book, test=args.test)
    print(f"Questions: {res_q['output']} ({res_q['words']} words, conf={res_q['avgConfidence']}, SHA={res_q['sha256'][:16]}...)")

    # 2. Answers
    a_file = cache_base / "answers" / f"test-{args.test}-listening.json"
    res_a = extract_and_cache_group(pdf_path, cfg["answers"], a_file, "answers", book=args.book, test=args.test)
    print(f"Answers: {res_a['output']} ({res_a['words']} words, conf={res_a['avgConfidence']}, SHA={res_a['sha256'][:16]}...)")

    # 3. Audioscripts
    s_file = cache_base / "audioscripts" / f"test-{args.test}-listening.json"
    res_s = extract_and_cache_group(pdf_path, cfg["audioscripts"], s_file, "audioscripts", book=args.book, test=args.test)
    print(f"Audioscripts: {res_s['output']} ({res_s['words']} words, conf={res_s['avgConfidence']}, SHA={res_s['sha256'][:16]}...)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

