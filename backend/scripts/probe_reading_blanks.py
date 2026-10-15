"""Inspect OCR positions of numbered blanks in reading-group image assets."""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
TESSERACT = Path('C:/Program Files/Tesseract-OCR/tesseract.exe')


def words(image: Path, psm: int = 6) -> list[dict]:
    result = subprocess.run(
        [str(TESSERACT), str(image), 'stdout', '-l', 'eng', '--psm', str(psm), 'tsv'],
        capture_output=True, text=True, encoding='utf-8', errors='replace', check=True,
    )
    return [row for row in csv.DictReader(io.StringIO(result.stdout), delimiter='\t')
            if row['level'] == '5' and row['text'].strip()]


def main() -> None:
    counts = Counter()
    for book in range(13, 21):
        for test in range(1, 5):
            folder = ROOT / 'resources' / 'cambridge' / f'c{book}' / f'test-{test}'
            path = folder / 'reading.json'
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding='utf-8'))
            layouts_path = folder / 'reading-layouts.json'
            layouts = json.loads(layouts_path.read_text(encoding='utf-8'))['layouts'] if layouts_path.exists() else []
            covered = {tuple(layout['questionNumbers']) for layout in layouts}
            for passage in data['passages']:
                for group in passage['groups']:
                    numbers = tuple(q['number'] for q in group['questions'])
                    if numbers in covered or all(q.get('prompt') for q in group['questions']):
                        continue
                    asset = group.get('asset') or next(iter(group.get('assets', [])), None)
                    if not asset:
                        counts['no_asset'] += 1
                        continue
                    image = folder / asset['asset']
                    if not image.exists():
                        print('MISSING_IMAGE', book, test, numbers, image)
                        continue
                    ocr = words(image, 11)
                    size = Image.open(image).size
                    positions = {}
                    for number in numbers:
                        matches = [word for word in ocr if re.sub(r'^[^0-9]+|[^0-9]+$', '', word['text']) == str(number)]
                        positions[number] = [[round(int(w['left']) / size[0], 3), round(int(w['top']) / size[1], 3),
                                              round(int(w['width']) / size[0], 3), round(int(w['height']) / size[1], 3),
                                              round(float(w['conf']))] for w in matches]
                    unique = all(len(matches) == 1 for matches in positions.values())
                    counts['unique' if unique else 'ambiguous'] += 1
                    print(f'c{book} t{test} {numbers[0]}-{numbers[-1]} {group["type"]} {size} {"UNIQUE" if unique else "AMBIG"} {positions}')
    print('COUNTS', dict(counts))


if __name__ == '__main__':
    main()
