"""For gap-fill questions whose prompt is a pasted block, take the single line holding blank n (strict blank marker)."""
import json, glob, re, sys
from pathlib import Path

WRITE = '--write' in sys.argv
INS = re.compile(r'In boxes \d|answer sheet|if the statement|if there is no information|Choose (the correct|TWO|THREE|NO MORE|ONE WORD)|Complete the (notes|table|summary|sentences|flow|diagram)|Look at the following|Match each|Reading Passage \d has|Which (paragraph|section) contains|You should spend|Write the correct', re.I)
MARK = r'(?:\s*(?:\.{2,}|_{2,}|…+))'


def broken(p):
    p = str(p or '').strip()
    return bool(INS.search(p)) or len(p) > 300 or bool(re.search(r'\nA[.\s]', p))


def line_for(text, n, others):
    lines = [l.replace('\x07', '').replace('\t', ' ').strip() for l in str(text).split('\n')]
    pat = re.compile(rf'(?<![\d£$.,])\b{n}{MARK}')
    for i, line in enumerate(lines):
        if not pat.search(line):
            continue
        s = line
        # a wrapped continuation (lower-case start) belongs to this line
        if i + 1 < len(lines) and lines[i + 1][:1].islower() and not re.search(r'\b\d{1,2}' + MARK, lines[i + 1]):
            s += ' ' + lines[i + 1]
        # a line that is only the blank continues the previous text ("... the making of" / "1 .....")
        if re.fullmatch(rf'{n}{MARK}\s*[.,]?', s) and i:
            s = lines[i - 1] + ' ' + s
        s = pat.sub(' ____', s, count=1)
        s = re.sub(r'(?:\.{3,}|…+)', '', s)
        s = re.sub(r'^[•·\-–—_;:\s]+(?=\S)', '', s).strip()
        s = re.sub(r'\s+', ' ', s).replace(' ____ ,', ' ____,').replace(' ____ .', ' ____.')
        if any(re.search(rf'(?<![\d£$.,])\b{o}{MARK}', s) for o in others):
            return None
        if '____' in s and len(s) >= 8:
            return s
    return None


out, todo = [], []
for f in sorted(glob.glob('resources/cambridge/c*/test-*/reading.json'), key=lambda f: [int(x) for x in re.findall(r'\d+', f)]):
    path = Path(f); d = json.loads(path.read_text(encoding='utf-8')); b, t = d['book'], d['test']
    if b == 12:
        continue
    dirty = False
    for g in (g for p in d['passages'] for g in p['groups']):
        if g.get('options') or any(q.get('options') for q in g['questions']):
            continue
        nums = [q['number'] for q in g['questions']]
        for q in g['questions']:
            if not broken(q.get('prompt')):
                continue
            src = f"{g.get('context') or ''}\n{q.get('prompt') or ''}"
            s = line_for(src, q['number'], [x for x in nums if x != q['number']])
            if not s:
                todo.append(f'C{b}T{t} Q{q["number"]}'); continue
            out.append(f'C{b}T{t} Q{q["number"]} [{g["type"]}] {s}')
            if WRITE:
                q.setdefault('promptRepairs', []).append({'date': '2026-10-15', 'method': 'line-from-group-context', 'previous': q.get('prompt'), 'note': '题干为整段粘贴或混入作答说明；改为本题所在的那一行（空格以 ____ 表示）。'})
                q['prompt'] = s; dirty = True
    if dirty and WRITE:
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('\n'.join(out)); print('TODO', todo); print('count', len(out), 'write', WRITE)
