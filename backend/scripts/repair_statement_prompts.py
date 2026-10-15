"""Re-split statement-style reading groups whose per-question prompts were mis-assigned by OCR.

Only groups where the statements parsed from the group text number exactly the questions, and every
already-correct prompt matches its parsed statement, are changed. Usage: fix_prompts.py [--write]
"""
import json, glob, re, sys
from pathlib import Path

WRITE = '--write' in sys.argv
INSTR = re.compile(r'^(match each|write the correct|in boxes|write your answers?|nb\b|look at the following|reading passage \d has|which (section|paragraph) contains|choose |do the following statements|true\b|false\b|yes\b|no\b|not given\b|if the statement|if there is no|if it is impossible|complete |list of |test\s*\d|testl|questions? \d)', re.I)
STATEMENT_TYPES = {'true-false-not-given', 'yes-no-not-given', 'matching-information', 'matching-features', 'unclassified'}
JUDGE = re.compile(r'\bYES\b[\s\S]*\bNO\b[\s\S]*NOT GIVEN|\bTRUE\b[\s\S]*\bFALSE\b[\s\S]*NOT GIVEN')


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower()).strip()


def bad(prompt):
    p = str(prompt or '').strip()
    return not p or bool(re.search(r'In boxes \d|if the statement|answer sheet|^Write the correct', p))


STRICT = True
# Word-level OCR slips in the repaired stems, each checked against the printed page.
OCR_FIXES = {'areference': 'a reference', 'asuggestion': 'a suggestion', 'Inthe brain—activity study, siloadores': 'In the brain–activity study, silbadores', 'depictions of Al ': 'depictions of AI '}
def statements(text, numbers):
    lines = [l.strip() for l in str(text or '').replace('\t', ' ').split('\n')]
    out = []
    for line in lines:
        if re.match(r'^(you should spend|list of|reading passage \d below)', line, re.I):
            break  # the next passage or the option list begins
        line = line.replace('', '').strip()
        if not line or INSTR.match(line) or line in ('•',):
            continue
        line = re.sub(r'^[;:,·•\s]+', '', line)
        if re.match(r'^[A-J]\s+\S', line) and not re.match(r'^[AI]\s+[a-z]', line):
            continue  # an option row such as "A Peter Toohey" in matching groups
        m = re.match(r'^(\d{1,3})[.\s]+(.*)$', line)
        if m:
            n = int(m.group(1))
            out.append([n if n in numbers else None, m.group(2)])
            continue
        # A capitalised line after a finished sentence starts a new (unnumbered) statement.
        if out and (line[:1].islower() or (STRICT and not re.search(r'[.?!]$', out[-1][1]))):
            out[-1][1] += ' ' + line
        else:
            out.append([None, line])
    return out


def main():
    changed = skipped = 0
    report = []
    for f in sorted(glob.glob('resources/cambridge/c*/test-*/reading.json'), key=lambda f: [int(x) for x in re.findall(r'\d+', f)]):
        path = Path(f)
        data = json.loads(path.read_text(encoding='utf-8'))
        b, t = data['book'], data['test']
        if b == 12:
            continue
        dirty = False
        for g in (g for p in data['passages'] for g in p['groups']):
            qs = g['questions']
            text = f"{g.get('instruction') or ''}\n{g.get('context') or ''}"
            if g['type'] not in STATEMENT_TYPES or (g['type'] == 'unclassified' and not JUDGE.search(text)):
                continue
            if g.get('options') and g['type'] not in ('matching-information', 'matching-features'):
                continue
            if not any(bad(q.get('prompt')) for q in qs):
                continue
            nums = [q['number'] for q in qs]
            # The group text is the authoritative copy; question prompts often hold fragments of it.
            src = g.get('context') or ''
            sts = statements(src, set(nums))
            label = f"C{b}T{t} Q{nums[0]}-{nums[-1]} [{g['type']}]"
            if len(sts) != len(qs):
                skipped += 1; report.append(f"SKIP {label}: parsed {len(sts)} statements for {len(qs)} questions"); continue
            ok = True
            for q, (n, s) in zip(qs, sts):
                if n is not None and n != q['number']:
                    ok = False; break
                if not bad(q.get('prompt')):
                    own = re.sub(r'^\d{1,2}\s+', '', q['prompt'].replace('\t', ' ').strip())
                    if norm(s) not in norm(own):
                        ok = False; break
            if not ok:
                skipped += 1; report.append(f"SKIP {label}: order check failed"); continue
            for q, (n, s) in zip(qs, sts):
                if bad(q.get('prompt')):
                    q.setdefault('promptRepairs', []).append({'date': '2026-10-15', 'method': 'regroup-from-group-context', 'previous': q.get('prompt'), 'note': '题干由 OCR 错位，按题组原文顺序重新分配；条数与题数一致且已正确的题干逐条对上。'})
                    fixed = s.strip()
                    for wrong, right in OCR_FIXES.items():
                        fixed = fixed.replace(wrong, right)
                    q['prompt'] = fixed
                    q['needsReview'] = [r for r in (q.get('needsReview') or []) if r.get('type') != 'use-group-context-or-image']
                    changed += 1
                    report.append(f"  {label} Q{q['number']}: {s[:90]}")
            dirty = True
        if dirty and WRITE:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('\n'.join(report))
    print(f'changed prompts: {changed}, skipped groups: {skipped}, write={WRITE}')


main()
