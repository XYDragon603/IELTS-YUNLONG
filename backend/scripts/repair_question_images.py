"""Re-render complete Task 1 figures from original PDFs; preserve original data backups."""
import hashlib
import json
import re
from pathlib import Path
import fitz
from PIL import Image, ImageDraw
from audit_question_images import audit

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/question-images-check'
BACKUP=ROOT/'backups/question-images-2026-10-15'
DEEP_BACKUP=ROOT/'backups/question-images-deep-recheck-2026-10-15'


def save_data(file,data):
    current_backup=DEEP_BACKUP/file.relative_to(ROOT)
    if not current_backup.exists():
        current_backup.parent.mkdir(parents=True,exist_ok=True)
        current_backup.write_bytes(file.read_bytes())
    backup=BACKUP/file.relative_to(ROOT)
    if not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(file.read_bytes())
    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def render(doc,file,page,bbox,name,alt):
    p=doc[page-1];y0,x0,y1,x1=bbox
    image=file.parent/'assets'/name
    p.get_pixmap(dpi=180,clip=fitz.Rect(p.rect.width*x0,p.rect.height*y0,p.rect.width*x1,p.rect.height*y1),alpha=False).save(image)
    with Image.open(image) as im:width,height=im.size
    return dict(asset='./assets/'+name,sourcePdfPage=page,boundingBox=bbox,
                boundingBoxFormat='ymin,xmin,ymax,xmax',width=width,height=height,
                sha256=hashlib.sha256(image.read_bytes()).hexdigest(),alt=alt)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    changed=[]
    for file in sorted((ROOT/'resources/cambridge').glob('c*/test-*/writing.json')):
        data=json.loads(file.read_text(encoding='utf-8-sig'))
        if data['book']==12:continue
        task=next(t for t in data['tasks'] if t['number']==1)
        original=BACKUP/file.relative_to(ROOT)
        original_data=json.loads(original.read_text(encoding='utf-8-sig')) if original.exists() else data
        old=next(t for t in original_data['tasks'] if t['number']==1).get('assets',[])
        if not old:continue
        with fitz.open(ROOT/data['sources']['paper']['path']) as doc:
            page=task['source']['pdfPage']
            # Keep complete instructions rather than a clipped line above the chart.
            box=[0,.02,.98,.98]
            if data['book']==20 and data['test']==4:box=[.18,.02,.92,.98]
            assets=[render(doc,file,page,box,
                           'writing-task-1-complete.png',f'Cambridge {data["book"]} Test {data["test"]} Writing Task 1 完整原图')]
            if data['book']==20 and data['test']==3:
                assets=[render(doc,file,23,[0,.02,.66,.98],'writing-task-1-complete.png','Little Chalfont Library：饼图、分类表和借阅数量柱状图')]
            if data['book']==20 and data['test'] in (1,2):
                bottom=.50 if data['test']==1 else .55
                assets.append(render(doc,file,page+1,[0,.02,bottom,.98],
                                     'writing-task-1-continuation.png','Task 1 续图：'+('Manhattan 与其他地区人口表' if data['test']==1 else 'Today 地图')))
        task['assets']=assets
        save_data(file,data);changed.append(str(file.relative_to(ROOT)))
    # Record the map's exact question range as printed on the original figure.
    for file in sorted((ROOT/'resources/cambridge').glob('c*/test-*/listening.json')):
        data=json.loads(file.read_text(encoding='utf-8-sig'))
        if data['book']==12:continue
        modified=False
        for part in data['parts']:
            asset=part.get('asset')
            if not isinstance(asset,dict):continue
            match=re.search(r'Questions?\s+(\d+)\s*(?:to|[-–])\s*(\d+)',asset.get('alt',''),re.I)
            if match:
                asset['questionNumbers']=list(range(int(match[1]),int(match[2])+1));modified=True
            corrections={(15,2):(37,[.10,.07,.86,.94],list(range(15,21)),'Minster Park 地图 · Questions 15–20'),
                         (17,2):(33,[.10,.06,.84,.94],list(range(15,21)),'Oniton Hall 活动选项和地点 · Questions 15–20（原题无地图）'),
                         (19,2):(39,[.07,.06,.52,.94],list(range(17,21)),'Lifeboat volunteer 选项 · Questions 17–20（原题无地图）')}
            correction=corrections.get((data['book'],data['test'])) if part['number']==2 else None
            if correction:
                page,bbox,numbers,alt=correction
                with fitz.open(ROOT/data['sources']['paper']['path']) as doc:
                    part['asset']=render(doc,file,page,bbox,'listening-part-2-correct-source.png',alt)
                part['asset']['questionNumbers']=numbers;modified=True
            if data['book']==16 and data['test']==4:
                asset['questionNumbers']=list(range(15,21));modified=True
            if not correction and isinstance(part.get('asset'),dict):
                # Keep map labels at the edges, including the C20 castle walls.
                asset=part['asset'];y0,_,y1,_=asset['boundingBox']
                original=BACKUP/file.relative_to(ROOT)
                if original.exists():
                    old_part=json.loads(original.read_text(encoding='utf-8-sig'))['parts'][part['number']-1]
                    old_asset=old_part.get('asset')
                    if isinstance(old_asset,dict):y0,_,y1,_=old_asset['boundingBox']
                with fitz.open(ROOT/data['sources']['paper']['path']) as doc:
                    replacement=render(doc,file,asset['sourcePdfPage'],[0,0,1,1],'listening-part-2-complete-source.png',asset.get('alt','原卷图题'))
                replacement['questionNumbers']=asset.get('questionNumbers') or list(range(11,21))
                part['asset']=replacement;modified=True
            if data['book']==20 and data['test']==3 and part['number']==2:
                with fitz.open(ROOT/data['sources']['paper']['path']) as doc:
                    map_image=render(doc,file,3,[.37,.02,.98,.98],'listening-part-2-complete-source.png','Bidcaster Archaeological Dig 地图 · Questions 17–20')
                    names=render(doc,file,4,[.03,.02,.38,.98],'listening-part-2-question-names.png','Questions 17–20 的地点名称及答题表')
                map_image['questionNumbers']=names['questionNumbers']=list(range(17,21))
                part['assets']=[map_image,names];part.pop('asset',None);modified=True
        if modified:save_data(file,data)
    reading_corrections=[(13,1,[1,7],19,[.08,.04,.73,.96]),
                         (13,3,[1,8],65,[.08,.04,.88,.97]),
                         (15,4,[6,8],86,[.50,.07,.87,.97]),
                         (20,1,[24,26],16,[0,.02,.35,.98]),
                         (20,2,[17,22],17,[0,.02,.80,.98]),
                         (20,2,[33,37],22,[.22,.02,.86,.98]),
                         (20,4,[37,40],21,[.38,.02,.82,.98]),
                         (13,4,[27,29],94,[.08,.04,.65,.96])]
    reading_corrections.extend([(16,2,[17,20],47,[.07,.02,.80,.98]),
                                (16,2,[31,35],52,[.07,.02,.76,.98]),
                                (17,1,[27,31],26,[.09,.02,.595,.98]),
                                (17,2,[37,40],49,[.09,.02,.63,.98]),
                                (17,3,[36,40],71,[.09,.02,.66,.98])])
    reading_corrections.append((18,4,[31,36],98,[.44,.02,.96,.98]))
    reading_corrections.extend([(16,1,[8,13],19,[.07,.05,.63,.94]),
                                (17,4,[7,13],84,[.08,.08,.74,.93])])
    for book,test,question_range,page,bbox in reading_corrections:
        file=ROOT/f'resources/cambridge/c{book}/test-{test}/reading.json'
        data=json.loads(file.read_text(encoding='utf-8-sig'))
        group=next(g for p in data['passages'] for g in p['groups'] if g['questionRange']==question_range)
        with fitz.open(ROOT/data['sources']['paper']['path']) as doc:
            group['asset']=render(doc,file,page,bbox,f'reading-q{question_range[0]}-{question_range[1]}-correct-source.png',f'Questions {question_range[0]}–{question_range[1]} 原卷题组')
        save_data(file,data)
    # Re-open the clipped right-hand frames without changing which group is shown.
    evidence=ROOT/'artifacts/question-images-deep-recheck/automatic-check.json'
    edge_rows=json.loads(evidence.read_text(encoding='utf-8'))['images'] if evidence.exists() else []
    edges={(r['book'],r['test'],r['location']):r['edgeInk'] for r in edge_rows}
    for file in sorted((ROOT/'resources/cambridge').glob('c*/test-*/reading.json')):
        data=json.loads(file.read_text(encoding='utf-8-sig'))
        if data['book']==12:continue
        modified=False
        with fitz.open(ROOT/data['sources']['paper']['path']) as doc:
            for pi,passage in enumerate(data['passages']):
                for gi,group in enumerate(passage['groups']):
                    asset=group.get('asset')
                    if not asset:continue
                    edge=edges.get((data['book'],data['test'],f'/passages/{pi}/groups/{gi}/asset'),{})
                    if data['book']<20 and any(edge.get(side,0)>.02 for side in ('left','right','bottom')):
                        y0,x0,y1,x1=asset['boundingBox']
                        # Use the pre-recheck crop for repeatable margins on later runs.
                        previous=DEEP_BACKUP/file.relative_to(ROOT)
                        if previous.exists():
                            old_group=json.loads(previous.read_text(encoding='utf-8-sig'))['passages'][pi]['groups'][gi]
                            if old_group.get('asset'):y0,x0,y1,x1=old_group['asset']['boundingBox']
                        if (data['book'],data['test'],group['questionRange']) in [(b,t,q) for b,t,q,_,_ in reading_corrections]:continue
                        box=[y0,.02,min(.97,y1+(.02 if edge.get('bottom',0)>.02 else 0)),.98]
                        first,last=group['questionRange']
                        group['asset']=render(doc,file,asset['sourcePdfPage'],box,f'reading-q{first}-{last}-complete-source.png',f'Questions {first}–{last} 完整原卷题组')
                        modified=True
                    if data['book']==20 and data['test']==2 and group['questionRange']==[33,37]:
                        options=render(doc,file,23,[0,.04,.38,.98],'reading-q33-37-options.png','Questions 33–37 的 A–H 完整选项')
                        group['assets']=[group['asset'],options];group.pop('asset',None);modified=True
        if modified:save_data(file,data)
    result=audit()
    # Contact sheets let the full set be inspected without replacing the original PNGs.
    rows=[r for r in result['images'] if r['skill'] in ('writing','reading','listening')]
    for start in range(0,len(rows),24):
        batch=rows[start:start+24]
        sheet=Image.new('RGB',(1600,6*330),'#e9e6df');draw=ImageDraw.Draw(sheet)
        for i,row in enumerate(batch):
            x=(i%4)*400;y=(i//4)*330
            with Image.open(ROOT/row['image']) as im:
                im=im.convert('RGB');im.thumbnail((386,290));sheet.paste(im,(x+(400-im.width)//2,y+30))
            label=f'C{row["book"]} T{row["test"]} {row["skill"]} Q{row["questions"]} p{row["sourcePdfPage"]}'
            draw.text((x+8,y+5),label,fill='black')
        sheet.save(OUT/f'contact-{start//24+1}.jpg',quality=90)
    print('Writing figures repaired:',len(changed))


if __name__=='__main__':main()
