"""Read-only inventory of Cambridge 13–20 reading completion group coverage."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / 'resources' / 'cambridge'


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
                if not any(not question.get('prompt') for question in group['questions']):
                    continue
                counts['with_missing_prompt'] += 1
                if numbers in covered:
                    counts['layout'] += 1
                    continue
                context = group.get('context', '')
                body = '\n'.join(line for line in context.splitlines()
                                 if not re.match(r'^(Complete|Choose|Write)', line.strip()))
                hits = {number: len(re.findall(r'(?<!\d)' + str(number) + r'\s*(?:[_\.]{2,}|(?=\n))', body))
                        for number in numbers}
                safe = all(count == 1 for count in hits.values())
                asset = bool(group.get('asset') or group.get('assets'))
                counts['asset' if asset else 'no_asset'] += 1
                counts['safe_context' if safe else 'unsafe_context'] += 1
                print(f'c{book} t{data["test"]} {numbers[0]}–{numbers[-1]} {group["type"]} '
                      f'asset={asset} safe={safe} hits={hits}')
    print('COUNTS', dict(counts))


if __name__ == '__main__':
    main()
