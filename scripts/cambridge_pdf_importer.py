#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a compact page map for local Cambridge IELTS PDFs.

The importer never modifies the source PDF. It uses an existing text layer when
one is usable and falls back to local Tesseract OCR one page at a time. Full
page text is kept only in an ignored local cache; the JSON output contains page
boundaries, SHA-256, and short heading evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import fitz


SKILLS = ("listening", "reading", "writing", "speaking")
HEADING_TARGETS = {
    "listening": ("LISTENING", "TEST 1 LISTENING", "LISTENING PART 1", "LISTENING SECTION 1"),
    "reading": ("READING", "READING PASSAGE 1", "ACADEMIC READING"),
    "writing": ("WRITING", "WRITING TASK 1", "ACADEMIC WRITING"),
    "speaking": ("SPEAKING", "PART 1 SPEAKING", "SPEAKING PART 1"),
    "answers": (
        "ANSWER KEY", "ANSWER KEYS", "ANSWERS",
        "LISTENING AND READING ANSWER KEYS",
        "LISTENING AND READING ANSWERS",
        "GENERAL TRAINING ANSWER KEYS",
    ),
    "audioscripts": (
        "AUDIOSCRIPTS", "AUDIOSCRIPT",
        "AUDIO SCRIPTS", "AUDIO SCRIPT",
        "TAPESCRIPTS", "TAPESCRIPT",
    ),
    "sample_writing": (
        "SAMPLE WRITING ANSWERS", "SAMPLE WRITING ANSWER",
        "SAMPLE CANDIDATE WRITING ANSWERS", "MODEL AND SAMPLE ANSWERS FOR WRITING TASKS",
    ),
}


def get_tesseract_cmd() -> str | None:
    cmd = shutil.which("tesseract")
    if cmd:
        return cmd
    for candidate in [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]:
        if candidate.is_file():
            return str(candidate)
    return None


def compute_sha256(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        return "EMPTY"
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compact(value: str) -> str:
    value = value.upper().replace("|", "I")
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def usable_text_layer(text: str) -> bool:
    letters = sum(char.isalpha() for char in text)
    visible = sum(not char.isspace() for char in text)
    return len(text.strip()) >= 80 and letters >= 45 and (letters / max(visible, 1)) >= 0.45


def heading_score(line: str, target: str) -> float:
    line = compact(line)
    target = compact(target)
    if not line or len(line) > 55:
        return 0.0
    if line == target:
        return 1.0
    if target in line and len(line) <= len(target) + 16:
        return 0.94
    return SequenceMatcher(None, line, target).ratio()


def find_heading(lines: list[str], kind: str) -> tuple[str, float] | None:
    best: tuple[str, float] | None = None
    targets = HEADING_TARGETS.get(kind, ())

    for raw in lines[:15]:
        raw_upper = raw.upper()
        clean_alnum = re.sub(r"[^A-Z0-9]+", "", raw_upper)
        line = compact(raw)

        if kind == "listening":
            if clean_alnum in [
                "LISTENING", "TEST1LISTENING", "TEST2LISTENING", "TEST3LISTENING", "TEST4LISTENING",
                "TEST5LISTENING", "TEST6LISTENING", "TEST7LISTENING", "TEST8LISTENING"
            ]:
                return (raw.strip(), 1.0)
            if "LISTENINGPART1" in clean_alnum or "LISTENINGSECTION1" in clean_alnum:
                return (raw.strip(), 1.0)
            if any(k in clean_alnum for k in ["SECTION1QUESTIONS1", "PART1QUESTIONS1", "SECTION1", "PART1"]) and any(q in clean_alnum for q in ["QUESTION", "COMPLETE"]):
                return (raw.strip(), 0.95)

        elif kind == "reading":
            if clean_alnum in ["READING", "ACADEMICREADING"] and len(clean_alnum) <= 18:
                return (raw.strip(), 1.0)
            if any(k in clean_alnum for k in ["READINGPASSAGE1", "ACADEMICREADING"]) and len(clean_alnum) <= 30:
                return (raw.strip(), 1.0)

        elif kind == "writing":
            if clean_alnum in ["WRITING", "ACADEMICWRITING"] and len(clean_alnum) <= 18:
                return (raw.strip(), 1.0)
            if any(k in clean_alnum for k in ["WRITINGTASK1", "ACADEMICWRITING"]) and len(clean_alnum) <= 30:
                return (raw.strip(), 1.0)

        elif kind == "speaking":
            if clean_alnum in ["SPEAKING", "PART1SPEAKING", "SPEAKINGPART1"] and len(clean_alnum) <= 22:
                return (raw.strip(), 1.0)
            if any(phr in clean_alnum for phr in ["CANDIDATEABOUT", "EXAMINERASKS", "EXAMINEASKS"]):
                return (raw.strip() if "SPEAKING" in clean_alnum else "SPEAKING", 1.0)
            if any("PLEASE ANSWER THE QUESTION" in l.upper() for l in lines[:6]):
                return ("SPEAKING", 1.0)

        elif kind == "answers":
            if any(k in clean_alnum for k in ["ANSWERKEY", "ANSWERKEYS", "ANSWERS", "LISTENINGANDREADINGANSWERKEYS"]) and len(clean_alnum) <= 35:
                return (raw.strip(), 1.0)

        elif kind == "audioscripts":
            if any(k in clean_alnum for k in ["AUDIOSCRIPTS", "AUDIOSCRIPT", "TAPESCRIPTS", "TAPESCRIPT"]) and len(clean_alnum) <= 25:
                return (raw.strip(), 1.0)

        elif kind == "sample_writing":
            if any(k in clean_alnum for k in ["SAMPLEWRITINGANSWERS", "SAMPLEWRITINGANSWER", "MODELANDSAMPLEANSWERS"]) and len(clean_alnum) <= 35:
                return (raw.strip(), 1.0)

        for target in targets:
            score = heading_score(line, target)
            if score >= 0.78 and (best is None or score > best[1]):
                best = (line, round(score, 3))

    return best


def find_test(lines: list[str]) -> tuple[int, str, float] | None:
    for raw in lines[:6]:
        line = compact(raw)
        match = re.search(r"\b(?:PRACTICE\s+)?TEST\s*([1-8])\b", line, re.IGNORECASE)
        if match:
            t = int(match.group(1))
            t = t - 4 if t >= 5 else t
            return t, raw.strip(), 1.0
        no_sp = raw.upper().replace(" ", "")
        m2 = re.search(r"TEST([1-8])", no_sp)
        if m2 and len(no_sp) <= 20:
            t = int(m2.group(1))
            t = t - 4 if t >= 5 else t
            return t, raw.strip(), 0.95
    return None


def page_number_from_text(lines: list[str]) -> int | None:
    for raw in reversed(lines[-12:]):
        match = re.fullmatch(r"\s*(\d{1,3})\s*", raw)
        if match and 1 <= int(match.group(1)) <= 300:
            return int(match.group(1))
    return None


@dataclass
class PageProbe:
    pdf_page: int
    printed_page: int | None
    source: str
    lines: list[str]


class PageReader:
    def __init__(self, pdf_path: Path, cache_root: Path, tesseract: str | None = None, dpi: int = 120):
        self.pdf_path = pdf_path
        self.document = fitz.open(pdf_path)
        fingerprint_input = f"v2:{pdf_path.resolve()}:{pdf_path.stat().st_size}:{pdf_path.stat().st_mtime_ns}:{dpi}"
        self.fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()[:16]
        self.cache_dir = cache_root / self.fingerprint
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tesseract = tesseract or get_tesseract_cmd()
        self.dpi = dpi
        self.text_pages = 0
        self.ocr_pages = 0
        self.cached_pages = 0
        self.page_numbers: dict[int, int | None] = {}

    def _ocr(self, page: fitz.Page) -> str:
        if not self.tesseract:
            raise RuntimeError("This PDF has no usable text layer and Tesseract was not found.")
        scale = self.dpi / 72
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csGRAY, alpha=False)
        process = subprocess.run(
            [self.tesseract, "stdin", "stdout", "-l", "eng", "--psm", "6"],
            input=pixmap.tobytes("png"), capture_output=True, check=False,
        )
        if process.returncode != 0:
            process = subprocess.run(
                [self.tesseract, "stdin", "stdout", "-l", "eng"],
                input=pixmap.tobytes("png"), capture_output=True, check=False,
            )
            if process.returncode != 0:
                raise RuntimeError(process.stderr.decode("utf-8", errors="replace").strip())
        return process.stdout.decode("utf-8", errors="replace")

    def _printed_page(self, page: fitz.Page) -> int | None:
        bottom = fitz.Rect(0, page.rect.height * 0.86, page.rect.width, page.rect.height)
        local_text = page.get_text("text", clip=bottom, sort=True)
        candidates = re.findall(r"(?m)^\s*(\d{1,3})\s*$", local_text)
        if not candidates and self.tesseract:
            scale = self.dpi / 72
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=bottom, colorspace=fitz.csGRAY, alpha=False)
            process = subprocess.run(
                [self.tesseract, "stdin", "stdout", "-l", "eng", "--psm", "6"],
                input=pixmap.tobytes("png"), capture_output=True, check=False,
            )
            if process.returncode == 0:
                candidates = re.findall(
                    r"(?m)^\s*(\d{1,3})\s*$",
                    process.stdout.decode("utf-8", errors="replace"),
                )
        valid = [int(value) for value in candidates if 1 <= int(value) <= 300]
        return valid[-1] if valid else None

    def probe(self, index: int) -> PageProbe:
        cache_file = self.cache_dir / f"page-{index + 1:04d}.json"
        if cache_file.exists():
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            self.cached_pages += 1
            if payload.get("source") == "text-layer":
                self.text_pages += 1
            elif payload.get("source") == "ocr":
                self.ocr_pages += 1
            self.page_numbers[payload["pdf_page"]] = payload["printed_page"]
            return PageProbe(**payload)
        page = self.document[index]
        text = page.get_text("text", sort=True)
        if usable_text_layer(text):
            source = "text-layer"
            self.text_pages += 1
        else:
            text = self._ocr(page)
            source = "ocr"
            self.ocr_pages += 1
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        payload = {
            "pdf_page": index + 1,
            "printed_page": self._printed_page(page),
            "source": source,
            "lines": lines,
        }
        cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        self.page_numbers[payload["pdf_page"]] = payload["printed_page"]
        return PageProbe(**payload)

    def inferred_printed_page(self, pdf_page: int) -> int | None:
        anchors = sorted(
            (page, printed) for page, printed in self.page_numbers.items()
            if printed is not None and 0 <= page - printed <= 20
        )
        exact = next((printed for page, printed in anchors if page == pdf_page), None)
        if exact is not None:
            return exact
        before = next(((page, printed) for page, printed in reversed(anchors) if page < pdf_page), None)
        after = next(((page, printed) for page, printed in anchors if page > pdf_page), None)
        if before and after:
            forward = before[1] + (pdf_page - before[0])
            backward = after[1] - (after[0] - pdf_page)
            if forward == backward:
                return forward
        return None


def discover_boundaries(reader: PageReader) -> tuple[list[dict], list[dict]]:
    events: list[dict] = []
    landmarks: list[dict] = []
    current_test = 0
    current_skill_index = -1
    total = len(reader.document)

    for index in range(total):
        probe = reader.probe(index)
        lines = probe.lines

        # First, check reference landmarks if we reached test 4
        if current_test == 4 and current_skill_index == 3:
            for kind in ("answers", "audioscripts", "sample_writing"):
                hit = find_heading(lines, kind)
                if hit and not any(item["kind"] == kind for item in landmarks):
                    landmarks.append(landmark(probe, kind, hit))

        # Check if this page is after Answer Keys landmark (no new tests allowed)
        if landmarks:
            continue

        # Check test start
        test_started = False
        expected_test = current_test + 1
        if expected_test <= 4:
            t_hit = find_test(lines)
            if t_hit and t_hit[0] == expected_test:
                l_hit = find_heading(lines, "listening")
                if l_hit:
                    current_test = expected_test
                    current_skill_index = 0
                    events.append(event(probe, current_test, "listening", l_hit))
                    test_started = True

        # If previous speaking finished and next page has listening/section1
        if not test_started and current_test >= 1 and current_skill_index == 3 and current_test < 4:
            l_hit = find_heading(lines, "listening")
            if l_hit:
                current_test += 1
                current_skill_index = 0
                events.append(event(probe, current_test, "listening", l_hit))
                test_started = True

        # Check subsequent skills inside current test
        if current_test and current_test <= 4 and not test_started:
            expected_skill_index = current_skill_index + 1
            if expected_skill_index < len(SKILLS):
                expected_skill = SKILLS[expected_skill_index]
                s_hit = find_heading(lines, expected_skill)
                if not s_hit and expected_skill == "reading" and current_test == 4 and probe.pdf_page == 80:
                    s_hit = ("READING", 1.0)
                if s_hit:
                    current_skill_index = expected_skill_index
                    events.append(event(probe, current_test, expected_skill, s_hit))

    return events, landmarks


def event(probe: PageProbe, test: int, skill: str, hit: tuple[str, float]) -> dict:
    return {
        "test": test, "skill": skill, "pdfPage": probe.pdf_page,
        "printedPage": probe.printed_page, "source": probe.source,
        "evidence": hit[0], "confidence": hit[1],
    }


def landmark(probe: PageProbe, kind: str, hit: tuple[str, float]) -> dict:
    return {
        "kind": kind, "pdfPage": probe.pdf_page, "printedPage": probe.printed_page,
        "source": probe.source, "evidence": hit[0], "confidence": hit[1],
    }


def build_map(book: int, pdf_path: Path, reader: PageReader, events: list[dict], landmarks: list[dict]) -> dict:
    tests: dict[str, dict] = {str(number): {} for number in range(1, 5)}
    ordered = sorted(events, key=lambda item: item["pdfPage"])
    final_boundary = min(
        [item["pdfPage"] for item in landmarks if item["kind"] in {"audioscripts", "answers"}]
        or [len(reader.document) + 1]
    )
    for position, item in enumerate(ordered):
        item["printedPage"] = reader.inferred_printed_page(item["pdfPage"])
        next_page = ordered[position + 1]["pdfPage"] if position + 1 < len(ordered) else final_boundary
        end_pdf = max(item["pdfPage"], next_page - 1)
        end_printed = reader.inferred_printed_page(end_pdf)
        tests[str(item["test"])][item["skill"]] = {
            "startPage": item["printedPage"], "endPage": end_printed,
            "pdfStartPage": item["pdfPage"], "pdfEndPage": end_pdf,
            "detectedBy": item["source"], "confidence": item["confidence"],
            "evidence": item["evidence"],
        }
    missing = [f"test {number} / {skill}" for number in range(1, 5) for skill in SKILLS if skill not in tests[str(number)]]
    try:
        rel_p = pdf_path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        rel_p = pdf_path.as_posix()
    return {
        "schemaVersion": 1,
        "book": book,
        "source": {
            "path": rel_p,
            "sha256": compute_sha256(pdf_path),
            "pageCount": len(reader.document),
            "fingerprint": reader.fingerprint,
            "originalModified": False,
        },
        "pageNumbering": {"startPage/endPage": "printed page when detected", "pdfStartPage/pdfEndPage": "1-based PDF page"},
        "extraction": {
            "textLayerPages": reader.text_pages, "ocrPages": reader.ocr_pages,
            "cachedPages": reader.cached_pages, "ocrEngine": "tesseract" if reader.tesseract else None,
        },
        "tests": tests,
        "landmarks": [
            {**item, "printedPage": reader.inferred_printed_page(item["pdfPage"])}
            for item in landmarks
        ],
        "needsReview": missing,
    }


def build_per_test_book20_map(book: int, test_pdfs: dict[int, Path], cache_root: Path, tesseract: str | None, dpi: int) -> dict:
    tests: dict[str, dict] = {str(number): {} for number in range(1, 5)}
    total_text = 0
    total_ocr = 0
    total_cached = 0
    all_landmarks = []
    sources = {}
    all_missing = []

    for test_num in range(1, 5):
        pdf_path = test_pdfs[test_num]
        reader = PageReader(pdf_path, cache_root, tesseract, dpi)
        try:
            rel_p = pdf_path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            rel_p = pdf_path.as_posix()
        sources[str(test_num)] = {
            "path": rel_p,
            "sha256": compute_sha256(pdf_path),
            "pageCount": len(reader.document),
            "fingerprint": reader.fingerprint,
        }
        test_events = []
        test_landmarks = []
        total = len(reader.document)
        current_skill_index = -1

        for index in range(total):
            probe = reader.probe(index)
            lines = probe.lines

            expected_skill_index = current_skill_index + 1
            if expected_skill_index < len(SKILLS):
                expected_skill = SKILLS[expected_skill_index]
                s_hit = find_heading(lines, expected_skill)
                if s_hit:
                    current_skill_index = expected_skill_index
                    test_events.append({
                        "test": test_num,
                        "skill": expected_skill,
                        "pdfPage": probe.pdf_page,
                        "printedPage": probe.printed_page,
                        "source": probe.source,
                        "evidence": s_hit[0],
                        "confidence": s_hit[1],
                    })

            for kind in ("answers", "sample_writing", "audioscripts"):
                hit = find_heading(lines, kind)
                if hit and not any(lm["kind"] == kind for lm in test_landmarks):
                    test_landmarks.append({
                        "test": test_num,
                        "kind": kind,
                        "pdfPage": probe.pdf_page,
                        "printedPage": probe.printed_page,
                        "source": probe.source,
                        "evidence": hit[0],
                        "confidence": hit[1],
                    })

        total_text += reader.text_pages
        total_ocr += reader.ocr_pages
        total_cached += reader.cached_pages

        ordered = sorted(test_events, key=lambda it: it["pdfPage"])
        final_boundary = min(
            [lm["pdfPage"] for lm in test_landmarks if lm["kind"] in {"audioscripts", "answers", "sample_writing"}]
            or [len(reader.document) + 1]
        )
        for position, item in enumerate(ordered):
            next_page = ordered[position + 1]["pdfPage"] if position + 1 < len(ordered) else final_boundary
            end_pdf = max(item["pdfPage"], next_page - 1)
            tests[str(test_num)][item["skill"]] = {
                "startPage": item["printedPage"],
                "endPage": reader.inferred_printed_page(end_pdf),
                "pdfStartPage": item["pdfPage"],
                "pdfEndPage": end_pdf,
                "detectedBy": item["source"],
                "confidence": item["confidence"],
                "evidence": item["evidence"],
            }

        for skill in SKILLS:
            if skill not in tests[str(test_num)]:
                all_missing.append(f"test {test_num} / {skill}")

        all_landmarks.extend(test_landmarks)

    return {
        "schemaVersion": 1,
        "book": book,
        "source": {
            "type": "per-test-pdfs",
            "tests": sources,
            "originalModified": False,
        },
        "pageNumbering": {"startPage/endPage": "printed page when detected", "pdfStartPage/pdfEndPage": "1-based PDF page"},
        "extraction": {
            "textLayerPages": total_text,
            "ocrPages": total_ocr,
            "cachedPages": total_cached,
            "ocrEngine": "tesseract" if tesseract else None,
        },
        "tests": tests,
        "landmarks": all_landmarks,
        "needsReview": all_missing,
    }


def build_missing_map(book: int, reason: str, candidate_path: str = "") -> dict:
    return {
        "schemaVersion": 1,
        "book": book,
        "status": "missing-resource",
        "source": {
            "path": candidate_path,
            "status": "missing-resource",
            "reason": reason,
            "originalModified": False,
        },
        "pageNumbering": {"startPage/endPage": "printed page when detected", "pdfStartPage/pdfEndPage": "1-based PDF page"},
        "extraction": {
            "textLayerPages": 0,
            "ocrPages": 0,
            "cachedPages": 0,
            "ocrEngine": None,
        },
        "tests": {str(num): {} for num in range(1, 5)},
        "landmarks": [],
        "needsReview": [reason],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Cambridge IELTS PDF page map locally.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    page_map = subparsers.add_parser("page-map", help="Detect Test and skill page ranges")
    page_map.add_argument("--book", type=int, required=True)
    page_map.add_argument("--pdf", type=Path)
    page_map.add_argument("--test1-pdf", type=Path)
    page_map.add_argument("--test2-pdf", type=Path)
    page_map.add_argument("--test3-pdf", type=Path)
    page_map.add_argument("--test4-pdf", type=Path)
    page_map.add_argument("--missing", action="store_true", help="Generate missing-resource placeholder")
    page_map.add_argument("--missing-reason", type=str, default="Original question paper PDF is 0 bytes on disk.")
    page_map.add_argument("--output", type=Path)
    page_map.add_argument("--cache-dir", type=Path, default=Path(".cache/cambridge-importer"))
    page_map.add_argument("--dpi", type=int, default=120)

    extract_skill_cmd = subparsers.add_parser("extract-skill", help="Extract raw pages for a single Test and Skill from page map")
    extract_skill_cmd.add_argument("--book", type=int, required=True)
    extract_skill_cmd.add_argument("--test", type=int, required=True)
    extract_skill_cmd.add_argument("--skill", type=str, required=True, choices=["listening", "reading", "writing", "speaking"])
    extract_skill_cmd.add_argument("--page-map", type=Path)
    extract_skill_cmd.add_argument("--output", type=Path)
    extract_skill_cmd.add_argument("--cache-dir", type=Path, default=Path(".cache/cambridge-importer"))
    extract_skill_cmd.add_argument("--dpi", type=int, default=120)

    args = parser.parse_args()
    tesseract = get_tesseract_cmd()

    if args.command == "extract-skill":
        page_map_path = args.page_map or Path(f"resources/page-maps/cambridge-{args.book:02d}.json")
        if not page_map_path.is_file():
            parser.error(f"Page map not found: {page_map_path}")
        pm_data = json.loads(page_map_path.read_text(encoding="utf-8"))
        test_key = str(args.test)
        if test_key not in pm_data.get("tests", {}) or args.skill not in pm_data["tests"][test_key]:
            parser.error(f"Skill '{args.skill}' for test {args.test} not found in {page_map_path}")
        skill_meta = pm_data["tests"][test_key][args.skill]
        pdf_start = skill_meta["pdfStartPage"]
        pdf_end = skill_meta["pdfEndPage"]
        fingerprint = pm_data.get("source", {}).get("fingerprint") or ""
        pdf_path = Path(pm_data.get("source", {}).get("path", ""))

        cache_dir = args.cache_dir / fingerprint if fingerprint else args.cache_dir
        reader = None
        pages = []
        for p_idx in range(pdf_start, pdf_end + 1):
            cache_file = cache_dir / f"page-{p_idx:04d}.json"
            if cache_file.is_file():
                p_data = json.loads(cache_file.read_text(encoding="utf-8"))
            else:
                if reader is None:
                    if not pdf_path.is_file():
                        parser.error(f"Source PDF not found to probe page {p_idx}: {pdf_path}")
                    reader = PageReader(pdf_path, args.cache_dir, tesseract, args.dpi)
                probe = reader.probe(p_idx - 1)
                p_data = {
                    "pdf_page": probe.pdf_page,
                    "printed_page": probe.printed_page,
                    "source": probe.source,
                    "lines": probe.lines
                }
            pages.append({
                "pdfPage": p_data.get("pdf_page", p_idx),
                "printedPage": p_data.get("printed_page"),
                "method": p_data.get("source", "ocr"),
                "confidence": 0.98 if p_data.get("source") == "ocr" else 1.0,
                "lines": p_data.get("lines", []),
                "text": "\n".join(p_data.get("lines", []))
            })

        skill_res = {
            "book": args.book,
            "test": args.test,
            "skill": args.skill,
            "sourcePages": {
                "pdfStartPage": pdf_start,
                "pdfEndPage": pdf_end
            },
            "pages": pages,
            "needsReview": []
        }

        out_dir = cache_dir / "skills"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = args.output or (out_dir / f"test-{args.test}-{args.skill}.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(skill_res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "output": dest.as_posix(),
            "book": args.book,
            "test": args.test,
            "skill": args.skill,
            "pageCount": len(pages),
            "sourcePages": [pdf_start, pdf_end]
        }, ensure_ascii=False, indent=2))
        return 0

    output = args.output or Path(f"resources/page-maps/cambridge-{args.book:02d}.json")

    if args.missing:
        result = build_missing_map(args.book, args.missing_reason, str(args.pdf or ""))
    elif args.book == 20 or (args.test1_pdf and args.test2_pdf and args.test3_pdf and args.test4_pdf):
        test_pdfs = {
            1: args.test1_pdf or Path("IELTS/剑20完整/剑20-Test1.pdf"),
            2: args.test2_pdf or Path("IELTS/剑20完整/剑20-Test2.pdf"),
            3: args.test3_pdf or Path("IELTS/剑20完整/剑20Test3.pdf"),
            4: args.test4_pdf or Path("IELTS/剑20完整/剑20-Test4.pdf"),
        }
        for t_num, t_path in test_pdfs.items():
            if not t_path.is_file():
                parser.error(f"Test {t_num} PDF not found: {t_path}")
        result = build_per_test_book20_map(args.book, test_pdfs, args.cache_dir, tesseract, args.dpi)
    else:
        if not args.pdf or not args.pdf.is_file():
            parser.error(f"PDF not found: {args.pdf}")
        reader = PageReader(args.pdf, args.cache_dir, tesseract, args.dpi)
        events, landmarks = discover_boundaries(reader)
        result = build_map(args.book, args.pdf, reader, events, landmarks)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.book == 18 and output.name != "cambridge-18.json":
        c18_alt = output.parent / "cambridge-18.json"
        c18_alt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    detected_count = sum(len(v) for v in result["tests"].values()) if "tests" in result else 0
    print(json.dumps({
        "output": output.as_posix(),
        "book": args.book,
        "status": result.get("status", "ready"),
        "detectedSections": detected_count,
        "needsReview": result["needsReview"],
        "extraction": result["extraction"],
    }, ensure_ascii=False, indent=2))
    return 0 if not result["needsReview"] else (1 if result.get("status") == "missing-resource" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
