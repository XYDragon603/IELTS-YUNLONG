#!/usr/bin/env python3
"""Restore C13 T1 Reading Q27–31 from the text layer of PDF page 29."""
import json
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "resources/cambridge/c13/test-1/reading.json"
QUESTIONS = {
    27: ("What is the writer suggesting about computer-produced works in the first paragraph?", [
        "People’s acceptance of them can vary considerably.",
        "A great deal of progress has already been attained in this field.",
        "They have had more success in some artistic genres than in others.",
        "The advances are not as significant as the public believes them to be."]),
    28: ("According to Geraint Wiggins, why are many people worried by computer art?", [
        "It is aesthetically inferior to human art.",
        "It may ultimately supersede human art.",
        "It undermines a fundamental human quality.",
        "It will lead to a deterioration in human ability."]),
    29: ("What is a key difference between Aaron and the Painting Fool?", [
        "its programmer’s background", "public response to its work",
        "the source of its subject matter", "the technical standard of its output"]),
    30: ("What point does Simon Colton make in the fourth paragraph?", [
        "Software-produced art is often dismissed as childish and simplistic.",
        "The same concepts of creativity should not be applied to all forms of art.",
        "It is unreasonable to expect a machine to be as imaginative as a human being.",
        "People tend to judge computer art and human art according to different criteria."]),
    31: ("The writer refers to the paintings of a chair as an example of computer art which", [
        "achieves a particularly striking effect.",
        "exhibits a certain level of genuine artistic skill.",
        "closely resembles that of a well-known artist.",
        "highlights the technical limitations of the software."]),
}


def main():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    group = next(g for p in data["passages"] for g in p["groups"] if g["questionRange"] == [27, 31])
    if all(q.get("prompt") and len(q.get("options", [])) == 4 for q in group["questions"]):
        print("C13 T1 Reading Q27–31 already restored")
        return
    if len(group["questions"]) != 5 or any(q.get("prompt") for q in group["questions"]):
        raise ValueError("Current group differs from expected missing import")
    with fitz.open(ROOT / data["sources"]["paper"]["path"]) as pdf:
        page = pdf[28]
        full_text = page.get_text()
        for n, (prompt, _) in QUESTIONS.items():
            if prompt.split("?")[0][:28] not in full_text:
                raise ValueError(f"Q{n} prompt not found on original page 29")
        number_words = {n: next(w for w in page.get_text("words") if w[4].rstrip(".,") == str(n)) for n in QUESTIONS}
        width, height = page.rect.width, page.rect.height
    backup = ROOT / ".cache/cambridge-importer/c13-t1-reading-before-mc-repair.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_bytes(FILE.read_bytes())
    group["type"] = "single-choice"
    group["context"] = "Choose the correct letter, A, B, C or D. Write the correct letter in boxes 27–31 on your answer sheet."
    for q in group["questions"]:
        n = q["number"]
        prompt, choices = QUESTIONS[n]
        q["prompt"] = prompt
        q["options"] = [{"value": letter, "label": label} for letter, label in zip("ABCD", choices)]
        word = number_words[n]
        q["source"] = {"pdfPage": 29, "printedPage": 26, "method": "text-layer",
                       "lineIds": [], "boundingBox": [round(word[1] / height, 4), round(word[0] / width, 4),
                                                      round(word[3] / height, 4), round(word[2] / width, 4)],
                       "confidence": 1.0}
        q["needsReview"] = [{"type": "assistant-visual-curation", "question": n,
                             "sourcePdfPage": 29, "reviewMethod": "assistant-visual"}]
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("C13 T1 Reading Q27–31 restored from PDF page 29")


if __name__ == "__main__":
    main()
