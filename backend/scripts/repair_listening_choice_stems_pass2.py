"""Second pass for listening choice placeholders.
(a) Option-A anchor: the stem is the text right before the paper line holding this question's option A
    (used only when option A is unique to the question).
(b) Shared option box (e.g. A–C ways for several hotels): the item is the "n text" line.
Searches the listening question pages of the book (OCR cache page list). Dry run unless --write."""
import json, glob, re, sys
from pathlib import Path
src = open(__import__('os').path.join(__import__('os').path.dirname(__file__), 'repair_listening_choice_stems.py'), encoding='utf-8').read(); src = src[:src.index('out, todo')]
ns = {}; exec(src, ns)
page_text, norm, placeholder = ns['page_text'], ns['norm'], ns['placeholder']
WRITE = '--write' in sys.argv
NOISE = re.compile(r'^(\d{1,2}|Questions?\b.*|Choose\b.*|Write\b.*|SECTION\b.*|PART\b.*|Test \d|Listening|[A-H])$')


def anchor_stem(text, opt_a):
    lines = [l.strip() for l in text.split('\n')]
    a = norm(opt_a)[:14]
    for i, line in enumerate(lines):
        body = re.sub(r'^[A-H]\s*[_.\-—]*\s*', '', line)
        if not a or norm(body)[:len(a)] != a:
            continue
        if not re.match(r'^[A-H]\b', line) and not (i and re.fullmatch(r'[A-H]', lines[i - 1])):
            continue
        stem = []
        j = i - 1 if not (i and re.fullmatch(r'[A-H]', lines[i - 1])) else i - 2
        while j >= 0 and len(stem) < 3:
            l = lines[j]
            if not l:
                if stem: break
                j -= 1; continue
            if NOISE.match(l) or re.match(r'^[A-H]\s', l):
                break
            stem.insert(0, re.sub(r'^\d{1,2}\s+', '', l)); j -= 1
        s = re.sub(r'\s+', ' ', ' '.join(stem)).strip()
        if len(s) > 8:
            return s
    return None


def item_line(text, n):
    for l in text.split('\n'):
        m = re.match(rf'^\s*{n}[\s.]+([A-Za-z’\'][^\n]{{1,60}}?)\s*[.…_]*\s*$', l.replace('\t', ' '))
        if m:
            return m.group(1).strip()
    return None


out, todo = [], []
for f in sorted(glob.glob('resources/cambridge/c*/test-*/listening.json'), key=lambda f: [int(x) for x in re.findall(r'\d+', f)]):
    path = Path(f); d = json.loads(path.read_text(encoding='utf-8')); b, t = d['book'], d['test']
    if b == 12:
        continue
    pdf = d['sources']['paper']['path']
    cache = json.load(open(d['importProvenance']['artifacts']['questions']['path'], encoding='utf-8'))
    pages = [p['pdfPage'] for p in cache['pages']]
    texts = {n: page_text(pdf, n) for n in pages}
    dirty = False
    for p in d['parts']:
        qs = [q for q in p['questions'] if q['type'] in ('single', 'multiple')]
        firsts = [norm((q.get('options') or [{}])[0].get('label', ''))[:14] for q in qs]
        for q in qs:
            if not placeholder(q['prompt']):
                continue
            a = (q.get('options') or [{}])[0].get('label', '')
            shared = firsts.count(norm(a)[:14]) > 1
            stem = method = None
            for n in pages:
                stem = item_line(texts[n], q['number']) if shared else anchor_stem(texts[n], a)
                if stem:
                    method = 'item-line' if shared else 'option-A-anchor'; break
            if not stem:
                todo.append(f'C{b}T{t}Q{q["number"]}'); continue
            out.append(f'C{b}T{t} Q{q["number"]} [{q["type"]}{" shared" if shared else ""}] {stem}')
            if WRITE:
                q.setdefault('promptRepairs', []).append({'date': '2026-10-15', 'method': method, 'previous': q['prompt'], 'note': '听力选择题题干原为占位“Question N”；按原卷文字补入（以本题 A 选项或题号行定位）。'})
                q['prompt'] = stem; dirty = True
    if dirty and WRITE:
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('\n'.join(out)); print('TODO', len(todo), todo); print('found', len(out), 'write', WRITE)
