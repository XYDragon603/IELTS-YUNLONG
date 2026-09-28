"""Local text-layer import; uncertain lines remain in a review report."""
from pathlib import Path
import hashlib, json, re, unicodedata
import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'resources/words'
HAN=r'[\u3400-\u9fff]'

def parse_entry(raw):
    raw=unicodedata.normalize('NFKC',raw).strip()
    first=re.search(HAN,raw)
    if not first:return None
    english=raw[:first.start()].strip()
    # Keep complex alternatives together instead of inventing separate meanings.
    english=re.sub(r'\[[^\]]*\]','',english)
    english=re.sub(r'\(?\b(?:advp|prep|pron|conj|adj|adv|vt|vi|np|vp|pl|n|v)\b\.?\)?','',english)
    english=re.sub(r'\s+',' ',english).strip(' .;,，;（(')
    if not re.fullmatch(r"[A-Za-z][A-Za-z '\-/,().&=]*",english) or len(english)>100:return None
    return english,raw[first.start():].strip()

def run():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    reports=[]
    for kind,title in [('listening','雅思听力分类词汇'),('reading','雅思阅读分类词汇')]:
        source=ROOT/'WORD'/f'{title}.pdf';doc=fitz.open(source)
        entries=[];review=[];category='未分类';pending=None
        def flush():
            nonlocal pending
            if pending:
                result=parse_entry(pending['raw'])
                if result:
                    word,meaning=result
                    entries.append(dict(id=hashlib.sha256(word.casefold().encode()).hexdigest()[:20],word=word,meaning=meaning,category=pending['category'],sourcePages=pending['pages'],sourceText=pending['raw'],method='text-layer'))
                else:review.append(pending)
            pending=None
        for n,page in enumerate(doc,1):
            text=unicodedata.normalize('NFKC',page.get_text())
            # Listening numbers can sit on a separate line from their entry.
            if kind=='listening':text=re.sub(r'(?m)^(\d+\.)\s*\n',r'\1 ',text)
            for line in text.splitlines():
                line=line.strip()
                if not line:continue
                if re.match(r'^(?:第\s*\d+\s*类|[★☆]*场景[一二三四五六七八九十\d]|\d+\.\s*\d+\s)',line):
                    flush();category=line;continue
                if line.startswith('考点') or line=='场景词汇':flush();continue
                if re.fullmatch(r'\d+',line) or 'www.' in line:continue
                numbered=re.match(r'^\d+\.\s*([A-Za-z].*)',line)
                start=numbered if kind=='listening' else re.match(r'^[A-Za-z]',line)
                if start:
                    flush();pending=dict(raw=numbered.group(1) if kind=='listening' else line,category=category,pages=[n])
                elif pending:
                    pending['raw']+=' '+line
                    if n not in pending['pages']:pending['pages'].append(n)
                else:review.append(dict(raw=line,pages=[n],category=category))
        flush()
        # Merge only identical words, retaining all categories and source locations.
        merged={}
        for entry in entries:
            if entry['id'] in merged:
                old=merged[entry['id']]
                if entry['meaning'] not in old['meaning']:old['meaning']+='\n'+entry['meaning']
                old['categories']=list(dict.fromkeys(old['categories']+[entry['category']]))
                old['sources'].append(dict(pages=entry['sourcePages'],text=entry['sourceText']))
            else:
                entry['categories']=[entry['category']];entry['sources']=[dict(pages=entry['sourcePages'],text=entry['sourceText'])];merged[entry['id']]=entry
        book_id='ielts-'+kind
        data=dict(schemaVersion=1,id=book_id,title=title,verified=False,source=dict(path=source.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),pageCount=len(doc)),words=list(merged.values()))
        (OUT/f'{book_id}.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        manifest['books']=[b for b in manifest['books'] if b['id']!=book_id]
        manifest['books'].append(dict(id=book_id,title=title,count=len(merged),path=f'{book_id}.json',needsReview=len(review)))
        reports.append(dict(id=book_id,entries=len(merged),needsReview=review))
    memory=ROOT/'WORD/雅思记忆法.pdf'
    manifest['readers']=[dict(id='memory',title='雅思记忆法',path=memory.relative_to(ROOT).as_posix(),pageCount=len(fitz.open(memory)),kind='scanned-book')]
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'pdf-import-report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([dict(id=r['id'],entries=r['entries'],review=len(r['needsReview'])) for r in reports]))

if __name__=='__main__':run()
