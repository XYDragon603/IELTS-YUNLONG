"""Recover multiple-choice stems from the paper. Dry run prints proposals; --write applies them."""
import json, glob, re, sys, subprocess, tempfile, os
from pathlib import Path
import fitz

WRITE = '--write' in sys.argv
TESS = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
INSTR = re.compile(r'^(write the correct|choose (the correct|two|three)|in boxes|nb\b)', re.I)
_cache = {}
FIXES = {'Inthe ': 'In the ', 'accept Al?': 'accept AI?', 'Thewriter': 'The writer', 'howtravel': 'how travel'}


def page_text(pdf, n):
    key = (pdf, n)
    if key in _cache:
        return _cache[key]
    page = fitz.open(pdf)[n - 1]
    txt = page.get_text('text')
    if len(txt.split()) < 40:
        pix = page.get_pixmap(dpi=300)
        with tempfile.TemporaryDirectory(dir='E:/tmp-claude') as d:
            img = os.path.join(d, 'p.png'); pix.save(img)
            txt = subprocess.run([TESS, img, 'stdout', '--psm', '4'], capture_output=True, text=True, encoding='utf-8').stdout
    _cache[key] = txt
    return txt


def norm(s):
    return re.sub(r'[^a-z0-9]+', '', str(s).lower())


def find_stem(text, number, option_a):
    lines = [l.strip() for l in text.split('\n')]
    a = norm(option_a)[:18]
    for i, line in enumerate(lines):
        m = re.match(rf'^{number}[.\s]+(.*)$', line)
        if not m:
            continue
        stem = [m.group(1)]
        for nxt in lines[i + 1:i + 8]:
            if re.match(r'^A[.\s]', nxt) or (a and norm(nxt).startswith(a[:10])):
                full = ' '.join(s for s in stem if s).strip()
                rest = norm(nxt[1:])
                if a and not (rest.startswith(a[:10]) or norm(nxt).startswith(a[:10])):
                    break
                return re.sub(r'\s+', ' ', full)
            if nxt:
                stem.append(nxt)
    return None


def clean_instr(prompt):
    lines = [l for l in str(prompt).split('\n') if l.strip()]
    for i, l in enumerate(lines):  # options copied into the stem start at an "A." line
        if i and re.match(r'^A[.\s]', l.strip()):
            lines = lines[:i]; break
    while lines and INSTR.match(lines[0].strip()):
        lines.pop(0)
    return re.sub(r'\s+', ' ', ' '.join(lines)).strip()


def bad(p):
    p = str(p or '').strip()
    return not p or bool(re.search(r'answer sheet|^Choose (the correct|TWO)|^Write the correct', p, re.I)) or bool(re.match(r'^\d+\s*-\s*\d+\n', p)) or bool(re.search(r'\nA[.\s]', p))


report, fixed, failed = [], 0, []
for f in sorted(glob.glob('resources/cambridge/c*/test-*/reading.json'), key=lambda f: [int(x) for x in re.findall(r'\d+', f)]):
    path = Path(f); d = json.loads(path.read_text(encoding='utf-8')); b, t = d['book'], d['test']
    if b == 12:
        continue
    pdf = d['sources']['paper']['path']; dirty = False
    for g in (g for p in d['passages'] for g in p['groups']):
        if g['type'] not in ('multiple-choice', 'single-choice'):
            continue
        for q in g['questions']:
            if not bad(q.get('prompt')):
                continue
            new, method = None, None
            cleaned = clean_instr(q.get('prompt') or '')
            cleaned = re.sub(r'^\d+\s*-\s*\d+\s*', '', cleaned)
            if cleaned and not bad(cleaned) and len(cleaned) > 15:
                new, method = cleaned, 'strip-instruction-lines'
            else:
                opts = q.get('options') or g.get('options') or []
                if opts:
                    stem = find_stem(page_text(pdf, q['source']['pdfPage']), q['number'], opts[0].get('label', ''))
                    if not stem:
                        for n in (q['source']['pdfPage'] - 1, q['source']['pdfPage'] + 1):
                            stem = find_stem(page_text(pdf, n), q['number'], opts[0].get('label', ''))
                            if stem: break
                    if stem:
                        new, method = stem, 'paper-text-matched-to-option-A'
            if not new:
                failed.append(f'C{b}T{t} Q{q["number"]}'); continue
            new = re.sub(r'^\d{1,2}[.\s]+', '', new)
            new = re.sub(r'\s+A$', '', new)
            for wrong, right in FIXES.items():
                new = new.replace(wrong, right)
            report.append(f'C{b}T{t} Q{q["number"]} [{method}] {new[:120]}')
            fixed += 1
            if WRITE:
                q.setdefault('promptRepairs', []).append({'date': '2026-10-15', 'method': method, 'previous': q.get('prompt'), 'note': '多选/单选题干缺失或混入作答说明；从原卷文字取题干，并以紧随其后的 A 选项与数据中 A 选项一致为准。'})
                q['prompt'] = new; dirty = True
    if dirty and WRITE:
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('\n'.join(report)); print('FAILED', failed); print(f'fixed {fixed} failed {len(failed)} write={WRITE}')
