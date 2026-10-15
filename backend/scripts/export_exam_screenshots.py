"""Export complete original question pages as local, lossless PNGs.

Includes listening/reading/writing pages to avoid missing diagrams, maps,
tables, or a continuation page. Never changes a PDF or imported test data.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import collections
import hashlib
import json
import re
import sys

import fitz

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts' / 'exam-screenshots'
DPI = 180
SKILLS = ['listening', 'reading', 'writing']
LABELS = {'listening': '听力', 'reading': '阅读', 'writing': '写作'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def plan():
    known = collections.defaultdict(set)
    for path in (ROOT / 'resources/cambridge').glob('c*/test-*/*.json'):
        if path.stem not in SKILLS:
            continue
        data = read(path)
        for node in walk(data):
            if isinstance(node.get('asset'), str) and node.get('sourcePdfPage'):
                known[(data['book'], data['test'], path.stem, node['sourcePdfPage'])].add('已有图题来源')
        if path.stem == 'listening':
            for part in data['parts']:
                asset = part.get('asset')
                if isinstance(asset, str):
                    match = re.search(r'-p(\d+)-', asset)
                    if match:
                        known[(data['book'], data['test'], path.stem, int(match[1]))].add('听力地图')

    jobs = collections.defaultdict(list)
    order = list(range(12, 21)) + list(range(4, 12))
    for book in order:
        mapping = read(ROOT / f'resources/page-maps/cambridge-{book:02}.json')
        for test_id, sections in mapping['tests'].items():
            test = int(test_id)
            source = mapping['source'].get('tests', {}).get(test_id, mapping['source'])
            for skill in SKILLS:
                section = sections[skill]
                for page in range(section['pdfStartPage'], section['pdfEndPage'] + 1):
                    jobs[source['path']].append(dict(
                        book=book, test=test, skill=skill, pdfPage=page,
                        source=source['path'], expectedSourceSha256=source['sha256'],
                        tags=sorted(known[(book, test, skill, page)]),
                    ))
    return list(jobs.items())


def render_source(job):
    source, requests = job
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    path = ROOT / source
    source_sha = digest(path)
    rows = []
    with fitz.open(path) as doc:
        for index, request in enumerate(requests, 1):
            item = {**request, 'sourceSha256': source_sha, 'dpi': DPI}
            item['sourceHashMatched'] = source_sha == request['expectedSourceSha256']
            relative = f"c{item['book']:02}/test-{item['test']}/{item['skill']}/pdf-page-{item['pdfPage']:03}.png"
            target = OUT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            fitz.TOOLS.mupdf_warnings(reset=True)
            try:
                page = doc[item['pdfPage'] - 1]
                original_text = page.get_text()
                tags = set(item['tags'])
                if item['skill'] == 'writing':
                    tags.add('写作原页')
                for label, pattern in [
                    ('地图/平面图线索', r'\b(?:map|plans?|layout)\b'),
                    ('图表/表格线索', r'\b(?:chart|graph|table|diagram|flow\s*chart|figure)\b'),
                ]:
                    if re.search(pattern, original_text, re.I):
                        tags.add(label)
                item['tags'] = sorted(tags)
                pix = page.get_pixmap(dpi=DPI, colorspace=fitz.csRGB, alpha=False)
                image_bytes = pix.tobytes('png')
                target.write_bytes(image_bytes)
                gray = fitz.Pixmap(fitz.csGRAY, pix)
                samples = gray.samples
                step = max(1, len(samples) // 80000)
                sampled = samples[::step]
                ink = sum(value < 235 for value in sampled) / max(1, len(sampled))
                warnings = fitz.TOOLS.mupdf_warnings(reset=True)
                # Warnings alone can be harmless. Only confirmed C12 corruption
                # and truly blank pages are marked unusable.
                damaged = item['book'] == 12 and 77 <= item['pdfPage'] <= 83
                status = 'source-damaged' if damaged else 'blank-page' if ink < 0.0001 else 'saved'
                item.update(image=relative, width=pix.width, height=pix.height,
                            bytes=len(image_bytes), sha256=hashlib.sha256(image_bytes).hexdigest(),
                            inkRatio=round(ink, 6), status=status, renderWarnings=warnings[:1400],
                            title=f"剑雅 {item['book']} · Test {item['test']} · {LABELS[item['skill']]} · PDF 第 {item['pdfPage']} 页")
            except Exception as error:
                item.update(status='render-failed', error=str(error))
            rows.append(item)
            if index % 25 == 0:
                print(f"C{request['book']} original pages {index}/{len(requests)}", flush=True)
    return rows


def gallery(rows, summary):
    payload = json.dumps(dict(summary=summary, pages=rows), ensure_ascii=False).replace('<', '\\u003c')
    html = r'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>剑雅原卷截图 · 地图与图表</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f5f2;color:#202923;font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}header,main{max-width:1440px;margin:auto;padding:24px}h1{font-size:30px;margin:0 0 8px}p{margin:8px 0}.muted{color:#59685f}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}select,input,button,a.open{font:inherit;padding:9px 12px;border:1px solid #c7d0c9;border-radius:7px;background:white;color:inherit}input{flex:1;min-width:180px}button,a{cursor:pointer}a{color:#226043}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:18px}.card{background:white;border:1px solid #d8dfd9;border-radius:10px;overflow:hidden}.preview{display:block;height:310px;background:#e9ede7;padding:10px}.preview img{width:100%;height:100%;object-fit:contain}.info{padding:14px}.info h2{font-size:15px;margin:0}.info p{font-size:13px}.warn{color:#a13b20}.actions{display:flex;gap:14px;font-size:13px}.pager{display:flex;gap:12px;align-items:center;justify-content:center;margin:24px}.tag{font-size:12px;background:#e9f0e7;border-radius:4px;padding:3px 6px;display:inline-block;margin:3px 3px 0 0}#count{margin-bottom:18px}details{background:#fff5e7;border-radius:7px;padding:10px 14px;margin-top:16px}footer{padding:18px 0;color:#5d6d62}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #549876;outline-offset:3px}
</style>
<header><h1>地图、图表与原题完整截图</h1><p id="summary"></p><p class="muted">PNG 原页截图 · 180 DPI · 保留原色与整页边界。为保留跨页题目，听力、阅读、写作原题页一起归档。关键词标签只帮助查找，全部原页均可查看。</p><details><summary>损坏页与原页内容说明</summary><p>剑雅 12 第 77–83 页的原 PDF 存在损坏或空白，相关截图已标注。截图保留原 PDF 同页的全部内容；部分剑雅 20 原页含答案或下一题题干。此目录是本地原页档案。</p></details>
<div class="toolbar"><label>册次 <select id="book"><option value="">全部册次</option></select></label><label>Test <select id="test"><option value="">全部</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label><label>科目 <select id="skill"><option value="">全部</option><option value="listening">听力</option><option value="reading">阅读</option><option value="writing">写作</option></select></label><label>显示 <select id="view"><option value="focus">图题线索与写作原页</option><option value="all">全部原题页</option><option value="bad">损坏或空白页</option></select></label><input id="search" aria-label="搜索页码、册次或标签" placeholder="搜索 PDF 页码、地图、表格…"></div></header>
<main><div id="count" role="status"></div><div class="grid" id="grid"></div><div class="pager"><button id="prev">上一页</button><span id="position"></span><button id="next">下一页</button></div><footer>每张图的具体 PDF 路径、物理页码、图片校验值均保存在 <a href="manifest.json">manifest.json</a>。截图路径按 c册次 / test序号 / 科目分类。</footer></main>
<script id="data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.querySelector('#data').textContent),pages=data.pages,byId=id=>document.getElementById(id);let current=0;const perPage=48;
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
byId('summary').textContent=`剑雅 4–20 · 68 个 Test · ${data.summary.totalPages.toLocaleString()} 张完整原页 · ${(data.summary.totalBytes/1024/1024).toFixed(1)} MB`;
for(let b=4;b<=20;b++)byId('book').insertAdjacentHTML('beforeend',`<option value="${b}">剑雅 ${b}</option>`);
function selected(){const q=byId('search').value.trim().toLowerCase();return pages.filter(p=>(!byId('book').value||p.book===Number(byId('book').value))&&(!byId('test').value||p.test===Number(byId('test').value))&&(!byId('skill').value||p.skill===byId('skill').value)&&(byId('view').value==='all'||byId('view').value==='bad'&&p.status!=='saved'||byId('view').value==='focus'&&p.tags.length>0)&&(!q||`${p.title} ${p.tags.join(' ')} ${p.pdfPage}`.toLowerCase().includes(q)));}
function render(){const list=selected(),max=Math.max(1,Math.ceil(list.length/perPage));current=Math.min(current,max-1);byId('count').textContent=`筛选到 ${list.length} 张原页。点击图片可打开原尺寸 PNG；跨页题目请连同相邻页一起查看。`;byId('grid').innerHTML=list.slice(current*perPage,(current+1)*perPage).map(p=>`<article class="card"><a class="preview" href="${escape(p.image||'')}" target="_blank" rel="noopener">${p.image?`<img src="${escape(p.image)}" loading="lazy" alt="${escape(p.title)}">`:'无法渲染'}</a><div class="info"><h2>${escape(p.title)}</h2><p>${p.width||0} × ${p.height||0}${p.status!=='saved'?` <strong class="warn">原页损坏或空白</strong>`:''}</p><p>${p.tags.map(t=>`<span class="tag">${escape(t)}</span>`).join('')}</p><div class="actions">${p.image?`<a href="${escape(p.image)}" download>保存 PNG</a>`:''}<a href="../../${p.source.split('/').map(encodeURIComponent).join('/')}#page=${p.pdfPage}" target="_blank" rel="noopener">查看原 PDF</a></div></div></article>`).join('');byId('position').textContent=`${current+1} / ${max}`;byId('prev').disabled=current===0;byId('next').disabled=current>=max-1;}
for(const id of ['book','test','skill','view','search'])byId(id).addEventListener(id==='search'?'input':'change',()=>{current=0;render()});byId('prev').onclick=()=>{current--;render();scrollTo(0,0)};byId('next').onclick=()=>{current++;render();scrollTo(0,0)};render();
</script></html>'''
    (OUT / 'index.html').write_text(html.replace('__DATA__', payload), encoding='utf-8')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = plan()
    total = sum(len(requests) for _, requests in jobs)
    (OUT / 'export-plan.json').write_text(json.dumps(dict(dpi=DPI, totalPages=total, sources=[dict(path=path, pages=len(rows)) for path, rows in jobs]), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Exporting {total} complete pages from {len(jobs)} original PDFs at {DPI} DPI', flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=2) as pool:
        pending = {pool.submit(render_source, job): job for job in jobs}
        for future in as_completed(pending):
            source, requests = pending[future]
            try:
                result = future.result()
            except Exception as error:
                result = [{**item, 'status': 'render-failed', 'error': str(error)} for item in requests]
            rows.extend(result)
            progress = dict(totalPages=total, completedPages=len(rows), latestSource=source)
            (OUT / 'progress.json').write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'Completed {len(rows)}/{total}: {Path(source).name}', flush=True)
    rows.sort(key=lambda item: (item['book'], item['test'], SKILLS.index(item['skill']), item['pdfPage']))
    summary = dict(totalPages=len(rows), dpi=DPI, totalBytes=sum(item.get('bytes', 0) for item in rows),
                   statusCounts=dict(collections.Counter(item['status'] for item in rows)),
                   sourceHashesMatched=all(item.get('sourceHashMatched', False) for item in rows))
    (OUT / 'manifest.json').write_text(json.dumps(dict(schemaVersion=1, summary=summary, pages=rows), ensure_ascii=False, indent=2), encoding='utf-8')
    gallery(rows, summary)
    (OUT / 'README.md').write_text(
        '# 地图与图表原页截图\n\n打开 index.html 可按册次、Test、科目筛选并查看完整 PNG。\n\n'
        f'- 剑雅 4–20，68 个 Test，共 {len(rows)} 张听力、阅读、写作完整原页。\n'
        f'- 180 DPI，无损 PNG，原色输出，共 {summary["totalBytes"]/1024/1024:.1f} MB。\n'
        '- 所有图片保留整页，跨页图题保留对应后续页；源 PDF 和现有题库未修改。\n'
        '- 剑雅 12 PDF 第 77–83 页的来源损坏，已标注，不能把空白截图视为完整题目。\n'
        '- 分类标签只是定位线索；“全部原题页”包含未识别出关键词的扫描页。\n'
        '- 图片页码均为从 1 开始的 PDF 物理页码，详见 manifest.json。\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
