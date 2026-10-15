"""Inventory existing figure-to-question links and verify local images, excluding C12."""
import hashlib
import json
import html
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/question-images-check'


def audit():
    rows = []
    for file in sorted((ROOT / 'resources/cambridge').glob('c*/test-*/*.json')):
        if file.stem not in ('listening', 'reading', 'writing', 'speaking'):
            continue
        data = json.loads(file.read_text(encoding='utf-8-sig'))
        if data['book'] == 12:
            continue

        def walk(node, location='', numbers=None):
            if isinstance(node, dict):
                if isinstance(node.get('questions'), list):
                    numbers = sorted({n for q in node['questions'] if isinstance(q,dict) for n in (q.get('numbers') or [q.get('number')]) if n is not None}) or numbers
                if node.get('type', '').startswith('writing-task'):
                    numbers = [node['number']]
                if isinstance(node.get('asset'), str):
                    numbers=node.get('questionNumbers') or numbers
                    # Part/group objects sometimes own an asset object instead.
                    image = file.parent / node['asset']
                    sha = hashlib.sha256(image.read_bytes()).hexdigest() if image.is_file() else None
                    rows.append(dict(book=data['book'], test=data['test'], skill=data['skill'],
                                     location=location, questions=numbers, image=str(image.relative_to(ROOT)),
                                     sourcePdf=data['sources']['paper']['path'],
                                     sourcePdfPage=node.get('sourcePdfPage'),
                                     boundingBox=node.get('boundingBox'), sha256=sha,
                                     valid=bool(sha) and (not node.get('sha256') or sha == node['sha256'])))
                for name, value in node.items():
                    walk(value, location + '/' + name, numbers)
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, location + '/' + str(i), numbers)
        walk(data)
    OUT.mkdir(parents=True, exist_ok=True)
    result = dict(boundBooks=sorted({r['book'] for r in rows}), archivedOnlyBooks=list(range(4,12)), excludedBooks=[12], totalImages=len(rows), skillCounts=dict(Counter(r['skill'] for r in rows)), invalidImages=sum(not r['valid'] for r in rows), images=rows)
    (OUT / 'mapping.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    cards=[]
    for row in rows:
        src='../../'+row['image'].replace('\\','/')
        pdf='../../'+row['sourcePdf']+'#page='+str(row['sourcePdfPage'])
        title=f'C{row["book"]} · Test {row["test"]} · {row["skill"]} · '+('题号 '+', '.join(map(str,row['questions'])) if row['questions'] else row['location'])
        cards.append(f'<figure><figcaption>{html.escape(title)}<br><a href="{html.escape(pdf,quote=True)}">原卷 PDF {row["sourcePdfPage"]} 页</a></figcaption><a href="{html.escape(src,quote=True)}"><img loading="lazy" src="{html.escape(src,quote=True)}" alt="{html.escape(title,quote=True)}"></a></figure>')
    page='<!doctype html><meta charset="utf-8"><title>图片与题号对应检查</title><style>body{font:16px/1.6 system-ui;margin:24px;background:#f6f3ee;color:#252c43}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px}figure{margin:0;padding:16px;background:white;border-radius:12px}img{width:100%;height:420px;object-fit:contain;background:white}figcaption{margin-bottom:12px}a{color:#b94f30}</style><h1>图片与题号对应检查</h1><p>本次绑定范围：现有在线题库剑雅 13–20。剑雅 12 暂留空；4–11 仅归档了原页截图，尚无在线题目可绑定。当前共 '+str(len(rows))+' 个图片引用，其中 101 个听力、阅读、写作图片已复看，另 32 个口语卡片本轮仅检查文件引用。点击图片查看完整尺寸，点击页码对照原卷。此清单不代表 OCR 正文、答案及音频内容已全部人工校准。</p><main>'+''.join(cards)+'</main>'
    page=page.replace('其中 101 个听力',f"其中 {sum(r['skill']!='speaking' for r in rows)} 个听力")
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'images'}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    audit()
