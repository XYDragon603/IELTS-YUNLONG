"""Bind original table/form question images, leaving Cambridge 12 untouched.

The explicit page/crop inventory was reviewed against original listening pages,
including pages omitted by the old screenshot section classification. Only asset
fields are changed; prompts, answers, attempts and UI behavior are preserved.
"""
import copy
import base64
import hashlib
import html
import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageOps

from audit_question_images import audit
from repair_question_images import render

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/table-question-images'
BACKUP = ROOT / 'backups/table-question-images-2026-10-15'

# book, test, part, question range, title, (PDF page, normalized crop) list.
TABLES = [
    (13, 1, 1, (1, 10), 'Cookery classes 烹饪课程表', [(11, [0, 0, 1, 1])]),
    (14, 1, 1, (1, 10), 'Crime report form 报案表', [(11, [0, 0, 1, 1])]),
    (14, 2, 1, (1, 10), 'Total Health Clinic 病人登记表', [(35, [0, 0, 1, 1])]),
    (15, 1, 2, (15, 20), 'Timetable for Isle of Man holiday 行程表', [(14, [0, 0, 1, 1])]),
    (15, 2, 1, (1, 4), 'Festival information 活动日程表', [(35, [.28, .04, .58, .96])]),
    (17, 2, 1, (8, 10), 'Village social events 村庄活动表', [(31, [.69, .06, .935, .94])]),
    (17, 4, 4, (31, 40), 'Maple syrup 双栏分区笔记表', [(80, [0, 0, 1, 1])]),
    (18, 2, 1, (6, 10), 'Working at Milo’s Restaurants 岗位信息表', [(37, [0, 0, 1, 1])]),
    (18, 3, 1, (1, 10), 'Waydale Camera Club 会员登记表及摄影比赛表', [(59, [0, 0, 1, 1])]),
    (19, 2, 1, (7, 10), 'A typical 45-minute guitar lesson 吉他课程表', [(37, [0, 0, 1, 1])]),
    (19, 3, 1, (7, 10), 'Shopping 购物表', [(59, [0, 0, 1, 1])]),
    (19, 4, 1, (7, 10), 'Responsibilities 岗位职责表', [(81, [.58, .04, .91, .96])]),
    (20, 1, 1, (1, 10), 'Restaurant recommendations 餐厅推荐表', [(2, [.09, .03, .42, .97])]),
    # The supplied C20 T2 PDF says "table" but presents a two-page notes list.
    (20, 2, 1, (1, 10), 'Carers’ support 原卷标为表格的跨页笔记题', [(2, [0, .03, .98, .97]), (3, [0, .03, .50, .97])]),
    (20, 3, 1, (1, 10), 'Furniture Rental Companies 家具租赁表', [(2, [.04, .03, .55, .97])]),
    (20, 2, 3, (21, 25), '补充：Aspects of human geography 两栏表格式匹配题', [(5, [.04, .03, .34, .97])]),
    (20, 3, 3, (27, 30), '补充：Comments about programme 两栏表格式匹配题', [(5, [.27, .03, .58, .97])]),
    (20, 4, 2, (15, 20), '补充：Events in the history of football 两栏表格式匹配题', [(4, [0, .03, .38, .97])]),
]
MATCHING_TABLES = [
    (20, 1, 'group-14-18', 14, [.24, .04, .84, .96]),
    (20, 2, 'group-14-16', 16, [.17, .04, .64, .96]),
    (20, 4, 'group-14-17', 15, [.46, .04, .95, .96]),
    (20, 4, 'group-27-31', 20, [.37, .04, .90, .96]),
]


def without_assets(value):
    if isinstance(value, dict):
        return {k: without_assets(v) for k, v in value.items() if k not in ('asset', 'assets')}
    if isinstance(value, list):
        return [without_assets(v) for v in value]
    return value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    modified = []
    source_hashes = {}
    for book, test, part_number, numbers, title, pages in TABLES:
        file = ROOT / f'resources/cambridge/c{book}/test-{test}/listening.json'
        before = json.loads(file.read_text(encoding='utf-8-sig'))
        data = copy.deepcopy(before)
        part = next(p for p in data['parts'] if p['number'] == part_number)
        expected = list(range(numbers[0], numbers[1] + 1))
        actual = {n for q in part['questions'] for n in (q.get('numbers') or [q['number']])}
        assert set(expected) <= actual, (book, test, part_number, expected)
        source = ROOT / data['sources']['paper']['path']
        source_hashes[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
        assets = list(part.get('assets') or ([part['asset']] if part.get('asset') else []))
        # Replace only images owned by this script, preserving maps/other figures.
        prefix = f'./assets/listening-table-part-{part_number}-'
        assets = [a for a in assets if not a.get('asset', '').startswith(prefix)]
        with fitz.open(source) as doc:
            for index, (page, bbox) in enumerate(pages, 1):
                suffix = f'（第 {index}/{len(pages)} 张）' if len(pages) > 1 else ''
                asset = render(doc, file, page, bbox,
                               f'listening-table-part-{part_number}-{index}.png',
                               f'{title} · Questions {numbers[0]}–{numbers[1]}{suffix}')
                asset['questionNumbers'] = expected
                assets.append(asset)
                rows.append(dict(book=book, test=test, skill='listening', title=title,
                                 questions=expected, sourcePdf=data['sources']['paper']['path'],
                                 image=str((file.parent / asset['asset']).relative_to(ROOT)), **asset))
        part['assets'] = assets
        part.pop('asset', None)
        assert without_assets(before) == without_assets(data), 'Non-image data changed'
        if data != before:
            backup = BACKUP / file.relative_to(ROOT)
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(file.read_bytes())
            file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            modified.append(str(file.relative_to(ROOT)))
    # C20 T3 prints the map's question names in a matching grid on the next page.
    file = ROOT / 'resources/cambridge/c20/test-3/listening.json'
    data = json.loads(file.read_text(encoding='utf-8-sig'))
    part = next(p for p in data['parts'] if p['number'] == 2)
    for asset in part['assets']:
        rows.append(dict(book=20, test=3, skill='listening', title='地图及表格内匹配题：Bidcaster Archaeological Dig',
                         questions=list(range(17, 21)), sourcePdf=data['sources']['paper']['path'],
                         image=str((file.parent / asset['asset']).relative_to(ROOT)), **asset))
    # The table-only visual review found two additional clipped right borders.
    for book, test, group_id, page, box in [
        (16, 1, 'group-8-13', 19, [.07, .05, .63, .94]),
        (17, 4, 'group-7-13', 84, [.08, .08, .74, .93]),
    ] + MATCHING_TABLES:
        file = ROOT / f'resources/cambridge/c{book}/test-{test}/reading.json'
        before = json.loads(file.read_text(encoding='utf-8-sig'))
        data = copy.deepcopy(before)
        group = next(g for p in data['passages'] for g in p['groups'] if g['id'] == group_id)
        with fitz.open(ROOT / data['sources']['paper']['path']) as doc:
            kind = '表格内匹配题' if group['type'] == 'matching-information' else '表格填空题'
            group['asset'] = render(doc, file, page, box, f'reading-table-{group_id}-complete.png',
                                    f'Questions {group["questionRange"][0]}–{group["questionRange"][-1]} {kind} · 完整原题')
        assert without_assets(before) == without_assets(data)
        if data != before:
            backup = BACKUP / file.relative_to(ROOT)
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(file.read_bytes())
            file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            modified.append(str(file.relative_to(ROOT)))
    reading_groups = 0
    for file in sorted((ROOT / 'resources/cambridge').glob('c*/test-*/reading.json')):
        data = json.loads(file.read_text(encoding='utf-8-sig'))
        if not 13 <= data['book'] <= 20:
            continue
        for passage in data['passages']:
            for group in passage['groups']:
                matching = (data['book'], data['test'], group['id']) in {(b, t, g) for b, t, g, _, _ in MATCHING_TABLES}
                if group.get('type') != 'table-completion' and not matching:
                    continue
                reading_groups += 1
                numbers = sorted({n for q in group['questions'] for n in (q.get('numbers') or [q['number']])})
                for asset in group.get('assets') or [group.get('asset')]:
                    assert asset and (file.parent / asset['asset']).is_file(), (file, group['id'])
                    rows.append(dict(book=data['book'], test=data['test'], skill='reading',
                                     title=asset.get('alt', group['id']), questions=numbers,
                                     sourcePdf=data['sources']['paper']['path'],
                                     image=str((file.parent / asset['asset']).relative_to(ROOT)), **asset))
    for source, sha in source_hashes.items():
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == sha, 'Source PDF changed'
    listening_rows = [r for r in rows if r['skill'] == 'listening']
    listening_groups = len({(r['book'], r['test'], tuple(r['questions'])) for r in listening_rows})
    result = dict(listeningGroups=listening_groups, listeningImages=len(listening_rows),
                  readingGroups=reading_groups, images=rows, changedFiles=sorted(set(modified)),
                  sourceHashes=source_hashes, nonImageDataUnchanged=True, excludedBooks=[12])
    (OUT / 'mapping.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    cards = []
    for row in rows:
        label = f'C{row["book"]} · Test {row["test"]} · {row["skill"]} · Questions {row["questions"][0]}–{row["questions"][-1]}'
        src = '../../' + row['image'].replace('\\', '/')
        pdf = '../../' + row['sourcePdf'] + '#page=' + str(row['sourcePdfPage'])
        cards.append(f'<figure><figcaption>{html.escape(label)}<br>{html.escape(row["title"])} · <a href="{html.escape(pdf, quote=True)}">原卷第 {row["sourcePdfPage"]} 页</a></figcaption><a href="{html.escape(src, quote=True)}"><img loading="lazy" src="{html.escape(src, quote=True)}" alt="{html.escape(label, quote=True)}"></a></figure>')
    counts = f'听力 {listening_groups} 组、{len(listening_rows)} 张，阅读 {reading_groups} 组、{len(rows)-len(listening_rows)} 张，共 {listening_groups+reading_groups} 组、{len(rows)} 张。'
    page = '<!doctype html><meta charset="utf-8"><title>表格内含题号与填空的原题图片</title><style>body{font:16px/1.7 system-ui;margin:24px;background:#f6f3ee;color:#252c43}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:20px}figure{margin:0;padding:18px;background:white;border-radius:12px}img{width:100%;height:650px;object-fit:contain}a{color:#b94f30}</style><h1>表格内含题目的原题图片</h1><p>剑雅 13–20：' + counts + '含表格填空、表格内匹配题、表单及部分笔记框。剑雅 12 留空。保留题号、空格、表头及完整行列；点击图片查看原尺寸。C20 T2 原文件将题目称为 table，实际是跨页笔记；C16 T1 阅读原文件同样称为 table，实际为笔记框。C20 T3 听力 17–20 的地图与匹配表分处两页，均保留。原文件中的蓝色数字是题号，原文件自带的格式符号保持原样。</p><main>' + ''.join(cards) + '</main>'
    (OUT / 'index.html').write_text(page, encoding='utf-8')
    # A single portable file: images are embedded, so it needs no image folder.
    standalone = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>表格题清单 · 剑雅13–20</title><style>body{font:17px/1.75 system-ui;color:#252c43;background:#f6f3ee;max-width:1100px;margin:32px auto;padding:0 20px}table{width:100%;border-collapse:collapse;background:white}th,td{padding:10px;text-align:left;border-bottom:1px solid #ddd}details{background:white;border-radius:12px;padding:16px;margin:20px 0}summary{cursor:pointer;font-weight:600}img{width:100%;height:auto;margin-top:18px}a{color:#b94f30}</style><h1>表格题清单 · 剑雅13–20</h1><p>按册次、Test、科目、题号单独标注。' + counts + '图片已嵌入本文件，点击下方题组可展开完整原图。剑雅12按要求留空；剑雅4–11仅有原页归档，不在本在线题库清单中。写作数据表另属Task 1，本文件专列表格填空、表格内匹配题、表单和部分笔记框中的听力、阅读题。</p><p>保留原题的表头、行列、题号、空格及作答要求。剑雅20 Test 2原文件称为table，实际呈现为跨页笔记；剑雅16 Test 1阅读也是原文件称为table的笔记框。剑雅20 Test 3听力17–20题的地图与匹配表分处两页，均保留。原文件自带的水印、蓝色题号和格式符号保留。此清单不代表OCR题干或答案已经全部校准。</p><table><thead><tr><th>剑雅</th><th>Test</th><th>科目</th><th>题号</th><th>原卷PDF页</th><th>图片</th></tr></thead><tbody>']
    rows.sort(key=lambda r: (r['book'], r['test'], r['skill'], r['sourcePdfPage']))
    for i, row in enumerate(rows, 1):
        skill = '听力' if row['skill'] == 'listening' else '阅读'
        standalone.append(f'<tr><td>{row["book"]}</td><td>{row["test"]}</td><td>{skill}</td><td>{row["questions"][0]}–{row["questions"][-1]}</td><td>{row["sourcePdfPage"]}</td><td><a href="#table-{i}">查看第{i}张</a></td></tr>')
    standalone.append('</tbody></table>')
    for i, row in enumerate(rows, 1):
        skill = '听力' if row['skill'] == 'listening' else '阅读'
        label = f'剑雅{row["book"]} · Test {row["test"]} · {skill} · 第{row["questions"][0]}–{row["questions"][-1]}题 · PDF第{row["sourcePdfPage"]}页'
        encoded = base64.b64encode((ROOT / row['image']).read_bytes()).decode('ascii')
        pdf = (ROOT / row['sourcePdf']).as_uri() + '#page=' + str(row['sourcePdfPage'])
        standalone.append(f'<details id="table-{i}" open><summary>{html.escape(label)}</summary><p>{html.escape(row["title"])} · <a href="{html.escape(pdf, quote=True)}">对照原卷</a></p><img loading="lazy" src="data:image/png;base64,{encoded}" alt="{html.escape(label, quote=True)}"></details>')
    standalone.append('</html>')
    standalone_path = ROOT / 'artifacts/表格题清单_剑雅13-20.html'
    standalone_backup = BACKUP / 'artifacts/表格题清单_剑雅13-20.html'
    if standalone_path.exists() and not standalone_backup.exists():
        standalone_backup.parent.mkdir(parents=True, exist_ok=True)
        standalone_backup.write_bytes(standalone_path.read_bytes())
    standalone_path.write_text(''.join(standalone), encoding='utf-8')
    for start in range(0, len(rows), 6):
        sheet = Image.new('RGB', (1600, 2400), '#e8e4dc')
        draw = ImageDraw.Draw(sheet)
        for i, row in enumerate(rows[start:start+6]):
            x, y = i % 2 * 800, i // 2 * 800
            draw.text((x+10, y+8), f'C{row["book"]} T{row["test"]} {row["skill"]} Q{row["questions"]} PDF{row["sourcePdfPage"]}', fill='black')
            with Image.open(ROOT / row['image']) as im:
                thumb = ImageOps.contain(im.convert('RGB'), (780, 750))
                sheet.paste(thumb, (x+(800-thumb.width)//2, y+40))
        sheet.save(OUT / f'tables-{start//6+1:02d}.jpg', quality=94)
    audit()
    print(json.dumps({k: v for k, v in result.items() if k not in ('images', 'sourceHashes')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
