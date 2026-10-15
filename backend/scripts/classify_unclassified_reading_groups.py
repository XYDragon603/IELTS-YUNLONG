"""Classify imported Cambridge 13–20 reading groups checked against paper pages.

The import left several otherwise usable groups as ``unclassified``.  Keep this
repair explicit so future imports can be compared with the original PDFs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / 'resources' / 'cambridge'

# (book, test, first question): paper question type
TYPES = {
    (13, 1, 8): 'true-false-not-given',
    (13, 1, 32): 'matching-sentence-endings',
    (13, 2, 14): 'matching-information',
    (13, 2, 27): 'multiple-choice',
    (13, 2, 32): 'matching-features',
    (13, 2, 38): 'matching-sentence-endings',
    (13, 3, 14): 'matching-features',
    (13, 3, 27): 'matching-information',
    (13, 4, 30): 'summary-completion',
    (16, 2, 21): 'yes-no-not-given',
    (16, 4, 1): 'diagram-label-completion',
    (16, 4, 11): 'short-answer',
    (16, 4, 23): 'yes-no-not-given',
    (16, 4, 36): 'yes-no-not-given',
    (18, 2, 1): 'notes-completion',
    (18, 2, 14): 'multiple-choice',
    (18, 2, 20): 'yes-no-not-given',
    (18, 4, 23): 'yes-no-not-given',
    (18, 4, 27): 'yes-no-not-given',
    (19, 1, 8): 'notes-completion',
    (19, 1, 37): 'yes-no-not-given',
    (19, 2, 1): 'notes-completion',
    (19, 2, 33): 'yes-no-not-given',
    (19, 3, 8): 'notes-completion',
    (19, 3, 31): 'matching-sentence-endings',
    (19, 3, 35): 'yes-no-not-given',
    (19, 4, 7): 'notes-completion',
    (19, 4, 36): 'yes-no-not-given',
}

CONTEXT = {
    (13, 1, 8): ('Do the following statements agree with the information given in Reading Passage 1?\n'
                  'Write TRUE, FALSE or NOT GIVEN in boxes 8–13.'),
    (13, 1, 32): ('Complete each sentence with the correct ending, A–G below.\n'
                    'Write the correct letter, A–G, in boxes 32–37.'),
    (13, 2, 14): ('Reading Passage 2 has six paragraphs, A–F.\n'
                    'Which paragraph contains the following information?\n'
                    'Write the correct letter, A–F, in boxes 14–17. You may use any letter more than once.'),
    (13, 2, 38): ('Complete each sentence with the correct ending, A–D below.\n'
                    'Write the correct letter, A–D, in boxes 38–40.'),
    (13, 3, 27): ('Reading Passage 3 has eight paragraphs, A–H.\n'
                    'Which paragraph contains the following information?\n'
                    'Write the correct letter, A–H, in boxes 27–31. You may use any letter more than once.'),
    (13, 4, 30): ('Complete the summary using the list of words A–G below.\n'
                    'Write the correct letter, A–G, in boxes 30–34.'),
    (19, 3, 31): ('Complete each sentence with the correct ending, A–F, below.\n'
                    'Write the correct letter, A–F, in boxes 31–34.'),
}

PARAGRAPH_OPTIONS = {
    (13, 2, 14): 'ABCDEF',
    (13, 3, 27): 'ABCDEFGH',
}


def main() -> None:
    changed = 0
    found = set()
    for book in range(13, 21):
        for test in range(1, 5):
            path = ROOT / f'c{book}' / f'test-{test}' / 'reading.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            for passage in data['passages']:
                for group in passage['groups']:
                    first = group['questionRange'][0]
                    key = book, test, first
                    if key not in TYPES:
                        assert group['type'] != 'unclassified', f'Unmapped group: {key}'
                        continue
                    found.add(key)
                    if group['type'] not in ('unclassified', TYPES[key]):
                        raise AssertionError(f'Unexpected existing type for {key}: {group["type"]}')
                    if group['type'] != TYPES[key]:
                        group['type'] = TYPES[key]
                        changed += 1
                    if key in CONTEXT:
                        group['context'] = CONTEXT[key]
                    if key in PARAGRAPH_OPTIONS:
                        group['options'] = [
                            {'value': letter, 'label': f'Paragraph {letter}'}
                            for letter in PARAGRAPH_OPTIONS[key]
                        ]
                    if key == (13, 3, 14):
                        for question in group['questions']:
                            question['prompt'] = re.sub(
                                rf'^\s*{question["number"]}\s+', '', question['prompt']
                            )
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8')
    assert found == set(TYPES), f'Missing expected groups: {set(TYPES) - found}'
    print(f'Classified {changed} groups; {len(found)} groups checked')


if __name__ == '__main__':
    main()
