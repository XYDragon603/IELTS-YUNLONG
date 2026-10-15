"""Recover listening choice stems that are placeholders ("Question N"). Accept a stem only when the
paper's next option line matches the stored option A. Dry run unless --write."""
import json, glob, re, sys, os, subprocess, tempfile
from pathlib import Path
import fitz

WRITE = '--write' in sys.argv
TESS = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
_cache = {}


def page_text(pdf, n):
    if (pdf, n) in _cache:
        return _cache[(pdf, n)]
    try:
        page = fitz.open(pdf)[n - 1]
    except Exception:
        return ''
    txt = page.get_text('text')
    if len(txt.split()) < 40:
        with tempfile.TemporaryDirectory(dir='E:/tmp-claude') as d:
            img = os.path.join(d, 'p.png'); page.get_pixmap(dpi=300).save(img)
            txt = subprocess.run([TESS, img, 'stdout', '--psm', '4'], capture_output=True, text=True, encoding='utf-8').stdout
    _cache[(pdf, n)] = txt
    return txt


norm = lambda s: re.sub(r'[^a-z0-9]', '', str(s).lower())
placeholder = lambda p: bool(re.fullmatch(r'Questions? \d+(\s*(and|-|–)\s*\d+)?', p.strip()))


def find_stem(text, nums, opt_a):
    lines = [l.strip() for l in text.split('\n')]
    a = norm(opt_a)[:12]
    head = rf'^({nums[0]}(\s*(and|-|–|&)\s*{nums[-1]})?)[.\s]+(.*\S.*)$' if len(nums) > 1 else rf'^{nums[0]}[.\s]+(.*\S.*)$'
    for i, line in enumerate(lines):
        m = re.match(head, line)
        bare = re.fullmatch(rf'{nums[0]}', line)
        # "Questions 15 and 16" / "...ns 17 and 18" header: the stem follows the "Choose TWO letters" line
        group = len(nums) > 1 and re.search(rf'{nums[0]}\s*(and|-|–)\s*{nums[-1]}\s*$', line)
        if not (m or bare or group):
            continue
        body = [m.groups()[-1]] if m and not group else []
        if group:
            j = i + 1
            while j < len(lines) and (not lines[j] or re.search(r'letters|^TWO', lines[j])):
                j += 1
            lines_after = lines[j:j + 6]
            for k, nxt in enumerate(lines_after):
                if re.fullmatch(r'[A-H]', nxt) or re.match(r'^[A-H][.\s]', nxt) or (a and norm(nxt).startswith(a)):
                    s = re.sub(r'\s+', ' ', ' '.join(body)).strip()
                    s = re.sub(r'^\S*\s*(?=(things|activities|features|types|points|of|reasons|aspects|benefits|problems|advantages|changes|ways|items|facilities|factors|skills|recommendations)\b)', 'Which TWO ', s) if not s.startswith('Which') else s
                    return s if len(s) > 8 else None
                if nxt:
                    body.append(nxt)
            continue
        for nxt in lines[i + 1:i + 6]:
            if not nxt:
                continue
            if re.fullmatch(r'[A-H]', nxt):
                s = re.sub(r'\s+', ' ', ' '.join(body)).strip()
                return s if len(s) > 8 else None
            if re.match(r'^[A-H][.\s]', nxt) or (a and norm(nxt).startswith(a)):
                rest = norm(re.sub(r'^[A-H][.\s]+', '', nxt))
                if a and rest[:len(a)] != a and norm(nxt)[:len(a)] != a:
                    break
                s = re.sub(r'\s+', ' ', ' '.join(body)).strip()
                return s if len(s) > 8 else None
            if re.match(r'^(Choose|Write|Questions?)\b', nxt):
                break
            body.append(nxt)
    return None


out, todo = [], []
for f in sorted(glob.glob('resources/cambridge/c*/test-*/listening.json'), key=lambda f: [int(x) for x in re.findall(r'\d+', f)]):
    path = Path(f); d = json.loads(path.read_text(encoding='utf-8')); b, t = d['book'], d['test']
    if b == 12:
        continue
    pdf = d['sources']['paper']['path']; dirty = False
    for p in d['parts']:
        for q in p['questions']:
            if q['type'] not in ('single', 'multiple') or not placeholder(q['prompt']):
                continue
            nums = q.get('numbers') or [q['number']]
            opts = q.get('options') or []
            if not opts:
                todo.append(f'C{b}T{t}Q{q["number"]} no-options'); continue
            pg = q['source'].get('pdfPage')
            stem = None
            for n in (pg, pg + 1, pg - 1):
                if n:
                    stem = find_stem(page_text(pdf, n), nums, opts[0].get('label', ''))
                    if stem: break
            if not stem:
                todo.append(f'C{b}T{t}Q{q["number"]}'); continue
            stem = re.sub(r'\s+[A-H]$', '', stem).replace(' wHI ', ' will ').strip()
            out.append(f'C{b}T{t} Q{"-".join(map(str, nums))} [{q["type"]}] {stem}')
            if WRITE:
                q.setdefault('promptRepairs', []).append({'date': '2026-10-15', 'method': 'paper-text-matched-to-option-A', 'previous': q['prompt'], 'note': '听力选择题题干原为占位“Question N”；从原卷文字取题干，且紧随其后的 A 选项与数据一致。'})
                q['prompt'] = stem; dirty = True
    if dirty and WRITE:
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('\n'.join(out)); print('TODO', len(todo), todo); print('found', len(out), 'write', WRITE)
