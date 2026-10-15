"""Build draft inline answer layouts from complete, uniquely numbered source context.

Only deterministic OCR blanks (number followed by dots/underscores) are converted.
The output is a draft for visual comparison against the paper, not a claim of review.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAMBRIDGE = ROOT / 'resources' / 'cambridge'
OUTPUT = ROOT / 'artifacts' / 'reading-inline-drafts.json'
INSTRUCTION = re.compile(r'^(Complete|Choose|Write)\b', re.I)


def transcribe(group: dict) -> dict | None:
    numbers = [question['number'] for question in group['questions']]
    lines = [line.strip() for line in group.get('context', '').splitlines()]
    body = [line for line in lines if line and not INSTRUCTION.match(line)]
    if len(body) < 2:
        return None
    text = '\n'.join(body)
    for number in numbers:
        pattern = re.compile(r'(?<!\d)' + str(number) + r'\s*[_\.]{2,}')
        if len(pattern.findall(text)) != 1:
            return None
        text = pattern.sub('{{' + str(number) + '}}', text)
    text = text.replace('‘normal，language', '‘normal’ language')
    text = text.replace('，', ',').replace('��', '').replace('�', '')
    text = re.sub(r',(?=\S)', ', ', text)
    text = re.sub(r'(?<!\S)__\s*', '', text)
    text = re.sub(r'\s+!(?=\s|$)', '', text)
    text = re.sub(r'\bAl\b', 'AI', text) if 'Using Al in the UK health system' in text else text
    body = text.splitlines()
    title = body.pop(0).strip().rstrip(' .:')
    kind = 'notes' if group['type'] in ('notes-completion', 'unclassified') else 'summary'
    if kind == 'summary':
        content = ' '.join(body).replace('  ', ' ')
        content = re.sub(r'\s+([.,;:])', r'\1', content)
        rendered = [content]
    else:
        rendered = []
        for raw in body:
            raw = raw.strip()
            if not raw:
                continue
            bullet = bool(re.match(r'^[•·-]\s*', raw))
            raw = re.sub(r'^[•·-]\s*', '', raw)
            heading = (not bullet and '{{' not in raw and len(raw) < 60
                       and not raw.endswith(('.', ',', ';')) and raw[:1].isupper())
            if bullet or heading or not rendered:
                rendered.append({'text': raw, 'heading': heading, 'bullet': bullet})
            else:
                rendered[-1]['text'] += ' ' + raw
        for line in rendered:
            line['text'] = re.sub(r'\s+([.,;:])', r'\1', line['text'])
    layout = {'kind': kind, 'title': title, 'questionNumbers': numbers, 'lines': rendered}
    found = [int(number) for line in rendered for number in re.findall(r'\{\{(\d+)\}\}',
                                                                  line if isinstance(line, str) else line['text'])]
    return layout if sorted(found) == sorted(numbers) else None


def main() -> None:
    drafts = []
    for path in sorted(CAMBRIDGE.glob('c*/test-*/reading.json')):
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
                if numbers in covered or all(question.get('prompt') for question in group['questions']):
                    continue
                layout = transcribe(group)
                if layout:
                    drafts.append({'book': book, 'test': data['test'], 'group': list(numbers),
                                   'sourcePdfPage': group.get('asset', {}).get('sourcePdfPage') or group.get('source', {}).get('pdfPage'),
                                   'asset': group.get('asset', {}).get('asset'), 'layout': layout})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(drafts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(drafts)} drafts: {OUTPUT}')
    if '--apply' in sys.argv:
        grouped = {}
        for draft in drafts:
            grouped.setdefault((draft['book'], draft['test']), []).append(draft['layout'])
        for (book, test), additions in grouped.items():
            folder = CAMBRIDGE / f'c{book}' / f'test-{test}'
            path = folder / 'reading-layouts.json'
            reading = json.loads((folder / 'reading.json').read_text(encoding='utf-8'))
            if path.exists():
                document = json.loads(path.read_text(encoding='utf-8'))
                assert document['source']['sha256'] == reading['sources']['paper']['sha256']
            else:
                document = {'schemaVersion': 1, 'book': book, 'test': test, 'skill': 'reading',
                            'description': '阅读填空题按原卷上下文显示内嵌答题框；{{n}} 对应第 n 题。',
                            'source': {'path': reading['sources']['paper']['path'],
                                       'sha256': reading['sources']['paper']['sha256']},
                            'layouts': []}
            current = {tuple(layout['questionNumbers']) for layout in document['layouts']}
            for layout in additions:
                if tuple(layout['questionNumbers']) in current:
                    continue
                layout['review'] = {'method': 'source-context', 'status': 'needs-visual-check'}
                document['layouts'].append(layout)
            document['layouts'].sort(key=lambda layout: layout['questionNumbers'][0])
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Applied layouts in {len(grouped)} tests')


if __name__ == '__main__':
    main()
