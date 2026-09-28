"""Read local XLS vocabulary without modifying source files or using OCR."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache/word-import-deps'))
import xlrd

def main():
    source = next(p for p in (ROOT / 'WORD').glob('*.xls') if '顺序' in p.name)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    workbook = xlrd.open_workbook(str(source))
    output = ROOT / 'resources/words'
    output.mkdir(parents=True, exist_ok=True)
    previous = json.loads((output / "manifest.json").read_text(encoding="utf-8")) if (output / "manifest.json").exists() else {}
    books = [b for b in previous.get("books", []) if b["id"] not in ("ielts-1", "ielts-2")]
    for index, sheet in enumerate(workbook.sheets()):
        words, skipped, seen = [], [], set()
        for row in range(sheet.nrows):
            word, meaning = (str(sheet.cell_value(row, col)).strip() for col in (1, 2))
            if not word or not meaning:
                skipped.append(row + 1)
                continue
            identity = hashlib.sha256(word.casefold().encode()).hexdigest()[:20]
            pair = (word.casefold(), meaning)
            if pair in seen:
                continue
            seen.add(pair)
            existing = next((w for w in words if w['id'] == identity), None)
            if existing:
                existing['meaning'] += '\n' + meaning
                existing['sourceRows'].append(row + 1)
            else:
                words.append(dict(id=identity, word=word, meaning=meaning, sourceRows=[row+1]))
        book_id = f'ielts-{index+1}'
        title = '雅思常用词汇' if index == 0 else '雅思完整词汇'
        data = dict(schemaVersion=1, id=book_id, title=title, source=dict(path=source.relative_to(ROOT).as_posix(), sha256=digest, sheet=sheet.name), words=words)
        (output / f'{book_id}.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        books.append(dict(id=book_id, title=title, count=len(words), sourceRows=sheet.nrows, skippedRows=skipped, path=f'{book_id}.json'))
    (output / 'manifest.json').write_text(json.dumps(dict(schemaVersion=1, books=books, readers=previous.get("readers", [])), ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([dict(id=b['id'], count=b['count'], skipped=len(b.get('skippedRows', []))) for b in books]))

if __name__ == '__main__':
    main()
