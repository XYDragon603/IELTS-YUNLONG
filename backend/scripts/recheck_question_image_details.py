"""Read-only image/source and printed-question-number audit. Writes evidence only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv, io, json, re, hashlib, subprocess, sys
import fitz
from PIL import Image, ImageChops, ImageStat, ImageDraw
from ocr_extractor import get_tesseract_cmd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/question-images-deep-recheck'
if '--after' in sys.argv:OUT=OUT/'after'
OUT.mkdir(parents=True,exist_ok=True)
TESS=get_tesseract_cmd()

def task(row):
    image=ROOT/row['image']
    result=dict(row)
    with fitz.open(ROOT/row['sourcePdf']) as doc:
        page=doc[row['sourcePdfPage']-1]
        y0,x0,y1,x1=row['boundingBox']
        with Image.open(image) as im:
            gray=im.convert('L')
            dpi=round(im.width/(page.rect.width*(x1-x0))*72)
            pix=page.get_pixmap(dpi=dpi,clip=fitz.Rect(page.rect.width*x0,page.rect.height*y0,page.rect.width*x1,page.rect.height*y1),alpha=False)
            reference=Image.open(io.BytesIO(pix.tobytes('png'))).convert('L').resize(gray.size)
            result['sourceCropMeanError']=round(ImageStat.Stat(ImageChops.difference(gray,reference)).mean[0],3)
            result['imageSize']=list(im.size)
            result['edgeInk']={name:round(sum(n for v,n in enumerate(gray.crop(box).histogram()) if v<150)/max(1,(box[2]-box[0])*(box[3]-box[1])),4) for name,box in {'top':(0,0,gray.width,3),'bottom':(0,gray.height-3,gray.width,gray.height),'left':(0,0,3,gray.height),'right':(gray.width-3,0,gray.width,gray.height)}.items()}
        if row['skill']!='writing':
            proc=subprocess.run([TESS,str(image),'stdout','-l','eng','--psm','3','tsv'],capture_output=True,check=True)
            words=list(csv.DictReader(io.StringIO(proc.stdout.decode('utf-8')),delimiter='\t'))
            tokens=[w['text'].strip() for w in words if w.get('text','').strip()]
            result['ocrText']=' '.join(tokens)
            numbers=set()
            for token in tokens:
                if re.fullmatch(r'\D*\d{1,2}\D*',token):numbers.update(map(int,re.findall(r'\d+',token)))
            result['printedNumbers']=sorted(numbers)
            result['numbersNotSeen']=sorted(set(row['questions'] or [])-numbers)
        else:result['numbersNotSeen']=[]
    result['needsVisualAttention']=bool(result['numbersNotSeen']) or result['sourceCropMeanError']>12 or any(v>.04 for v in result['edgeInk'].values())
    return result

def main():
    original=json.loads((ROOT/'artifacts/question-images-check/mapping.json').read_text(encoding='utf-8'))
    rows=[r for r in original['images'] if r['skill'] in ('listening','reading','writing')]
    cache_file=OUT/'automatic-check.json'
    cached=json.loads(cache_file.read_text(encoding='utf-8'))['images'] if cache_file.exists() and '--after' in sys.argv else []
    cached_by_image={r['image']:r for r in cached}
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending=[]
        for row in rows:
            old=cached_by_image.get(row['image'])
            if old and old['sha256']==row['sha256']:results.append(old)
            else:pending.append(row)
        futures=[pool.submit(task,row) for row in pending]
        for future in as_completed(futures):
            results.append(future.result())
            if len(results)%20==0:print('Checked',len(results),'/',len(rows),flush=True)
    results.sort(key=lambda r:(r['book'],r['test'],r['skill'],r['sourcePdfPage']))
    hashes={}
    for row in results:
        if row['sourcePdf'] not in hashes:hashes[row['sourcePdf']]=hashlib.sha256((ROOT/row['sourcePdf']).read_bytes()).hexdigest()
    output=dict(count=len(results),attentionCount=sum(r['needsVisualAttention'] for r in results),sourceHashes=hashes,images=results)
    (OUT/'automatic-check.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    for i,r in enumerate(results):
        r['auditId']=i+1
    # Every image is paired with its original page; red rectangle shows the crop.
    for start in range(0,len(results),8):
        sheet=Image.new('RGB',(2000,4*700),'#e8e4dc');draw=ImageDraw.Draw(sheet)
        for i,r in enumerate(results[start:start+8]):
            x=i%2*1000;y=i//2*700
            label=f'#{r["auditId"]} C{r["book"]} T{r["test"]} {r["skill"]} Q{r["questions"]} PDF{r["sourcePdfPage"]}'
            draw.text((x+8,y+5),label,fill='black')
            with fitz.open(ROOT/r['sourcePdf']) as doc:
                pix=doc[r['sourcePdfPage']-1].get_pixmap(dpi=100,alpha=False)
                source=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
                sy0,sx0,sy1,sx1=r['boundingBox']
                ImageDraw.Draw(source).rectangle((sx0*source.width,sy0*source.height,sx1*source.width,sy1*source.height),outline='#d62828',width=4)
                source.thumbnail((485,650));sheet.paste(source,(x+(500-source.width)//2,y+30))
            with Image.open(ROOT/r['image']) as crop:
                crop=crop.convert('RGB');crop.thumbnail((485,650));sheet.paste(crop,(x+500+(500-crop.width)//2,y+30))
        sheet.save(OUT/f'source-pairs-{start//8+1:02}.jpg',quality=93)
    html='<!doctype html><meta charset="utf-8"><title>原页与裁剪图逐张对照</title><style>body{font:16px/1.7 system-ui;background:#f6f3ee;color:#252c43;margin:24px}img{display:block;max-width:100%;height:auto;margin:18px 0}a{color:#b94f30}</style><h1>原页与裁剪图逐张对照</h1><p>左侧为原 PDF 页面，红框为截取区域；右侧为实际题目图片。共 '+str(len(results))+' 张图题图片，剑雅 12 排除。OCR 未识别到数字只用于筛查，不能直接判为题目缺失；跨页图的题号需结合该题组的全部图片检查。</p>'
    html+=''.join(f'<h2>第 {i+1} 组对照图</h2><a href="source-pairs-{i+1:02}.jpg"><img loading="lazy" src="source-pairs-{i+1:02}.jpg" alt="原页与截图对照 {i+1}"></a>' for i in range((len(results)+7)//8))
    (OUT/'index.html').write_text(html,encoding='utf-8')
    (OUT/'automatic-check.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'count':output['count'],'attentionCount':output['attentionCount']},ensure_ascii=False))
    for r in results:
        if r['needsVisualAttention']:print(r['auditId'],r['book'],r['test'],r['skill'],r['questions'],'missing',r['numbersNotSeen'],'error',r['sourceCropMeanError'],'edges',r['edgeInk'])

if __name__=='__main__':main()
