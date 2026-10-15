"""Audit Cambridge 13–20 reading numbering, controls, assets and OCR outliers."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / 'resources' / 'cambridge'
SELECT_TYPES = {'multiple-choice', 'single-choice', 'matching-headings',
                'matching-information', 'matching-features',
                'matching-sentence-endings'}
SUSPICIOUS = re.compile(
    r'[\ufffd\x07]|\b(?:Awarm|Apossible|Aperiod|lron|itis)\b|'
    r'(?<![A-Za-z])(?:[=~@]|\{tis|\.\s*\.)', re.I)


def ocr_outlier(value: str) -> str | None:
    match = SUSPICIOUS.search(value)
    if match:
        return match.group()
    # OCR often mistakes capital I for lower-case l in the abbreviation AI.
    return 'Al' if re.search(r'\bAl\b', value) else None


def main() -> None:
    counts = Counter()
    for path in sorted(ROOT.glob('c*/test-*/reading.json')):
        book = int(path.parent.parent.name[1:])
        if not 13 <= book <= 20:
            continue
        counts['tests'] += 1
        data = json.loads(path.read_text(encoding='utf-8'))
        groups = [group for passage in data['passages']
                  for group in passage['groups']]
        numbers = [q['number'] for group in groups for q in group['questions']]
        if sorted(numbers) != list(range(1, 41)):
            print('NUMBERING', book, data['test'], numbers)
            counts['numbering_issues'] += 1
        for group in groups:
            counts['groups'] += 1
            key = (book, data['test'], group['questionRange'])
            values = [str(option['value']) for option in group.get('options', [])]
            if group['type'] in SELECT_TYPES and not values and not all(
                    q.get('options') for q in group['questions']):
                print('MISSING_OPTIONS', *key)
                counts['missing_options'] += 1
            if values and len(values) != len(set(values)):
                print('DUPLICATE_OPTIONS', *key, values)
                counts['duplicate_options'] += 1
            for q in group['questions']:
                counts['questions'] += 1
                prompt = q.get('prompt') or ''
                if match := ocr_outlier(prompt):
                    print('SUSPICIOUS_PROMPT', *key, q['number'],
                          repr(match), ascii(prompt[:180]))
                    counts['suspicious_prompts'] += 1
                options = q.get('options') or group.get('options') or []
                for option in options:
                    label = str(option.get('label') or '')
                    if match := ocr_outlier(label):
                        print('SUSPICIOUS_OPTION', *key, q['number'],
                              option['value'], repr(match), ascii(label))
                        counts['suspicious_options'] += 1
                asset = q.get('asset') or group.get('asset')
                if asset:
                    target = (path.parent / asset['asset']).resolve()
                    if not target.is_file():
                        print('MISSING_ASSET', *key, q['number'], target)
                        counts['missing_assets'] += 1
    print('COUNTS', dict(counts))


if __name__ == '__main__':
    main()
