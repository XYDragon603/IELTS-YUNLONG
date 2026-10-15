"""Read-only checks for merged or corrupted Cambridge 13–20 reading prompts."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / 'resources' / 'cambridge'
COMPLETION = {'notes-completion', 'summary-completion', 'table-completion',
              'sentence-completion', 'flow-chart-completion'}


def main() -> None:
    counts = Counter()
    for path in sorted(ROOT.glob('c*/test-*/reading.json')):
        book = int(path.parent.parent.name[1:])
        if not 13 <= book <= 20:
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        layout_path = path.with_name('reading-layouts.json')
        layouts = json.loads(layout_path.read_text(encoding='utf-8'))['layouts'] if layout_path.exists() else []
        covered = {tuple(layout['questionNumbers']) for layout in layouts}
        for passage in data['passages']:
            for group in passage['groups']:
                numbers = tuple(question['number'] for question in group['questions'])
                if numbers in covered:
                    counts['layout_groups'] += 1
                    continue
                context = group.get('context', '')
                if group['type'] in COMPLETION and re.search(r'Choose the correct letter,\s*A,?\s*B', context, re.I):
                    print('TYPE_MISMATCH', book, data['test'], numbers, group['type'])
                    counts['type_mismatch'] += 1
                for index, question in enumerate(group['questions']):
                    counts['questions'] += 1
                    prompt = str(question.get('prompt') or '')
                    issues = []
                    if not prompt:
                        issues.append('missing')
                    if len(prompt) > 260:
                        issues.append(f'long:{len(prompt)}')
                    if len(prompt.splitlines()) > 3:
                        issues.append(f'lines:{len(prompt.splitlines())}')
                    if '\ufffd' in prompt or any(ord(char) < 32 and char not in '\n\r\t' for char in prompt):
                        issues.append('encoding')
                    embedded = [int(value) for value in re.findall(r'(?m)^\s*(\d{1,2})[.\t ]+', prompt)]
                    if any(value != question['number'] for value in embedded):
                        issues.append('other-question-number')
                    following = group['questions'][index + 1]['prompt'] if index + 1 < len(group['questions']) else ''
                    following = re.sub(r'^\s*\d{1,2}[.\t ]+', '', following).replace('\n', ' ').strip()
                    if group['type'] != 'multiple-choice' and len(following) > 35 and following[:35] in prompt.replace('\n', ' '):
                        issues.append('neighbour-question-text')
                    if re.search(r'(?m)^\s*[A-H][.\s]+\S', prompt) and group['type'] == 'multiple-choice':
                        issues.append('options-in-prompt')
                    if issues:
                        counts.update(issues)
                        print('PROMPT', book, data['test'], question['number'], group['type'], ','.join(issues), repr(prompt[:180]))
    print('COUNTS', dict(counts))


if __name__ == '__main__':
    main()
