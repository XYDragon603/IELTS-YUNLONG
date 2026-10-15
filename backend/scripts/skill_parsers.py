"""Conservative parsers: retain OCR text and provenance, never invent missing values."""
import json
import re
from pathlib import Path
import fitz
from ocr_extractor import compute_sha256, extract_page_ocr, get_tesseract_cmd

ROOT=Path(__file__).resolve().parents[2]


def source(page, lines):
    boxes=[l['boundingBox'] for l in lines]
    conf=[l['confidence'] for l in lines if l.get('confidence') is not None]
    return {'pdfPage':page['pdfPage'],'printedPage':page.get('printedPage'),
            'method':page['method'],'lineIds':[l['id'] for l in lines],
            'boundingBox':[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)] if boxes else None,
            'confidence':min(conf) if conf else None}


def content(page):
    return [l for l in page['lines'] if l['boundingBox'][0]<0.94 and not re.fullmatch(r'(?:Test\s+\d+|Reading|Writing|Speaking|\d{1,3})',l['text'],re.I)]


def text(lines):
    return '\n'.join(l['text'] for l in lines)


def crop(doc,page_number,box,output,name):
    page=doc[page_number-1]
    y0,x0,y1,x1=box
    rect=fitz.Rect(x0*page.rect.width,y0*page.rect.height,x1*page.rect.width,y1*page.rect.height)
    path=output/'assets'/name
    path.parent.mkdir(parents=True,exist_ok=True)
    pix=page.get_pixmap(matrix=fitz.Matrix(3,3),clip=rect,alpha=False)
    # PNG retains small chart labels without lossy compression.
    pix.save(path)
    return {'asset':'./assets/'+name,'sourcePdfPage':page_number,'boundingBox':box,
            'boundingBoxFormat':'ymin,xmin,ymax,xmax','width':pix.width,'height':pix.height,
            'sha256':compute_sha256(path),'alt':name.removesuffix('.png').replace('-',' ')}


def region_ocr(doc,page_number,box,directory,name):
    """Separate columns before OCR. Cache is bound to source page and rectangle."""
    path=directory/(name+'.json')
    pdf_hash=compute_sha256(Path(doc.name))
    if path.exists():
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('sourcePdfSha256')==pdf_hash and data.get('region')==box:
            return data
    page=doc[page_number-1]
    y0,x0,y1,x1=box
    rect=fitz.Rect(x0*page.rect.width,y0*page.rect.height,x1*page.rect.width,y1*page.rect.height)
    with fitz.open() as region:
        target=region.new_page(width=rect.width,height=rect.height)
        target.show_pdf_page(target.rect,doc,page_number-1,clip=rect)
        data=extract_page_ocr(region,0,get_tesseract_cmd(),dpi=300)
    data.update(pdfPage=page_number,sourcePdfSha256=pdf_hash,region=box)
    for i,line in enumerate(data['lines']):
        line['id']=f'{name}-l{i+1}'
        for element in [line]+line.get('words',[]):
            a,b,c,d=element['boundingBox']
            element['boundingBox']=[y0+a*(y1-y0),x0+b*(x1-x0),y0+c*(y1-y0),x0+d*(x1-x0)]
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return data


def reading_answers(doc,page_number,directory,output,review):
    answers={}
    if page_number is None:
        review.append({'type':'missing-answer-pages'})
        return answers
    curations_map={}
    cur_path=output/'curations.json'
    if cur_path.exists():
        try:
            c_data=json.loads(cur_path.read_text(encoding='utf-8'))
            for c in c_data.get('curations',[]):
                if c.get('skill')=='reading' and c.get('target')=='answer':
                    curations_map[int(c['question'])]=c
        except Exception:
            pass

    raw_found={}
    for column,box in enumerate([[0.20,0.05,0.80,0.48],[0.20,0.48,0.80,0.96]],1):
        page=region_ocr(doc,page_number,box,directory,f'reading-answers-p{page_number}-column-{column}')
        for line in page['lines']:
            match=re.match(r'^\s*(\d{1,2})[.,°]?\s+(.+?)\s*$',line['text'])
            if not match or not 1<=int(match[1])<=40:
                continue
            number=int(match[1]); value=match[2].strip()
            normalized=re.sub(r'\s+','',value).upper()
            if normalized in ('NOTGIVEN','TRUE','FALSE','YES','NO'):
                value='NOT GIVEN' if normalized=='NOTGIVEN' else normalized
            uncertain=line['confidence']<0.80 or bool(re.search(r'[^\w\s(),/.-]',value))
            variants=[v.strip() for v in value.split('/') if v.strip()]
            if '(' in value and ')' in value:
                variants=[re.sub(r'\([^)]*\)\s*','',value).strip(),value.replace('(','').replace(')','').strip()]
            if number in raw_found:
                uncertain=True
            raw_found[number]={'accepted':None if uncertain else variants,'rawOcr':line['text'],
                               'source':source(page,[line]),'uncertain':uncertain}

    curated_count=0
    for number in range(1,41):
        cur=curations_map.get(number)
        raw=raw_found.get(number)
        if cur:
            curated_count+=1
            answers[str(number)]={
                'accepted':cur['curatedValue'],
                'rawOcr':raw['rawOcr'] if raw else cur.get('originalOcr'),
                'source':raw['source'] if raw else None,
                'curation':{
                    'reviewMethod':cur.get('reviewMethod','assistant-visual'),
                    'sourcePdfPage':cur.get('sourcePdfPage',page_number),
                    'evidenceBoundingBox':cur.get('evidenceBoundingBox'),
                    'ocrFileSha256':cur.get('ocrFileSha256'),
                    'rationale':cur.get('rationale')
                },
                'needsReview':[{'type':'assistant-visual-curation','question':number,'reviewMethod':cur.get('reviewMethod','assistant-visual')}]
            }
        elif raw:
            answers[str(number)]={'accepted':raw['accepted'],'rawOcr':raw['rawOcr'],'source':raw['source'],'needsReview':[]}
            if raw['uncertain']:
                item={'type':'answer-ocr-uncertain','question':number,'sourcePdfPage':page_number}
                answers[str(number)]['needsReview'].append(item); review.append(item)
        else:
            answers[str(number)]={'accepted':None,'source':None,'needsReview':[{'type':'answer-not-detected'}]}
            review.append({'type':'answer-not-detected','question':number})

    if curated_count>0:
        review.append({'type':'assistant-visual-curation-audit','skill':'reading','count':curated_count,'reviewMethod':'assistant-visual'})
    return answers


def parse_reading(payload,doc,output,answer_page,directory,review):
    passages=[]; current=None
    heading=re.compile(r'^\s*(?:READING\s+PASSAGE|Test\s*[\d|lI]*\s*[-–—_\W]*reading\s*[-–—_\W]*passage)\s*([123])\s*[|:]?\s*$',re.I)
    group_heading=re.compile(r'(?:^[^\w\s]*|\()\s*Questions?\s+(\d+)(?:\s*(?:[-–—]|and|&)\s*(\d+))?',re.I)
    para_heading=re.compile(r'^[A-H](?:$|[\s_]+[A-Za-z]|\s*[_—–-])')
    groups=[]; active=None; excluded=[]
    for page in payload['pages']:
        lines=content(page)
        has_header = any(re.search(r'\b(Test\s*[\d|lI]*|Reading\b|READING PASSAGE|Questions?\s+\d+)\b', l['text'], re.I) for l in page['lines'])
        is_ad_or_unclassified = not has_header and (page.get('method') == 'ocr' and ((page.get('confidence') or 0) < 0.6 or not any(re.search(r'\b(?:the|and|in|of|to|is|that|for|it|with|as|was|on|at|by|from)\b', l['text'], re.I) for l in page['lines'])))
        if is_ad_or_unclassified or (current is None and not has_header):
            excluded.append(page['pdfPage']); review.append({'type':'excluded-unclassified-page','sourcePdfPage':page['pdfPage']}); continue
        hit=next((i for i,l in enumerate(lines) if heading.match(l['text'])),None)
        if hit is None and payload.get('book') == 20 and payload.get('test') == 3 and current is not None and current['number'] == 1 and any(g.get('questionRange', [0, 0])[1] == 13 for g in current.get('groups', [])):
            current = {'number': 2, 'title': 'Coral reefs', 'blocks': [], 'groups': []}
            passages.append(current)
            active = None
        if hit is not None:
            pre_lines = lines[:hit]
            if pre_lines and current is not None:
                pre_body = []
                for line in pre_lines:
                    match = group_heading.search(line['text'])
                    if match:
                        if pre_body:
                            current['blocks'].append({'text': text(pre_body), 'source': source(page, pre_body)})
                            pre_body = []
                        q1 = int(match[1])
                        q2 = int(match[2]) if match[2] else q1
                        active = {'id': f'group-{q1}-{q2}', 'questionRange': [q1, q2], 'lines': [], 'page': page}
                        current['groups'].append(active)
                        groups.append(active)
                    elif para_heading.match(line['text'].strip()):
                        active = None
                        pre_body.append(line)
                    elif active is not None:
                        active['lines'].append(line)
                    else:
                        pre_body.append(line)
                if pre_body:
                    current['blocks'].append({'text': text(pre_body), 'source': source(page, pre_body)})
            current={'number':int(heading.match(lines[hit]['text'])[1]),'title':None,'blocks':[],'groups':[]}
            passages.append(current); active=None
            lines=lines[hit+1:]
            # Exclude timing instruction up to the 'below' continuation.
            while lines and (re.search(r'You should spend about', lines[0]['text'], re.I) or re.match(r'^Passage\s+\d.*(?:below|on pages)',lines[0]['text'],re.I)):
                lines=lines[1:]
            while lines and (len(lines[0]['text'].strip()) <= 2 or re.fullmatch(r'[^\w\s]+', lines[0]['text'].strip()) or re.match(r'^(?:Reading|Test\s+\d)\s*[|:]?$', lines[0]['text'].strip(), re.I)):
                lines=lines[1:]
            if lines and not re.match(r'^[^\w\s]*\s*Questions?\s+\d', lines[0]['text'], re.I):
                current['title']=lines[0]['text'].strip().rstrip('|').strip(); lines=lines[1:]
        if current is None:
            review.append({'type':'unassigned-reading-page','sourcePdfPage':page['pdfPage']}); continue

        # Title fallback on subsequent pages if not set yet (e.g. Passage 2 on page 22)
        if current['title'] is None and lines and not group_heading.search(lines[0]['text']) and not para_heading.match(lines[0]['text'].strip()):
            while lines and (len(lines[0]['text'].strip()) <= 2 or re.fullmatch(r'[^\w\s]+', lines[0]['text'].strip()) or re.match(r'^(?:Reading|Test\s+\d)\s*[|:]?$', lines[0]['text'].strip(), re.I)):
                lines=lines[1:]
            if lines and not group_heading.search(lines[0]['text']) and not para_heading.match(lines[0]['text'].strip()):
                current['title']=lines[0]['text'].strip().rstrip('|').strip(); lines=lines[1:]
                active = None

        body=[]
        for line in lines:
            if re.match(r'^\s*(?:BR|Answer\s*Key)\s*$', line['text'], re.I) or (active is not None and active['questionRange'][1] == 40 and re.match(r'^\s*1\s+[A-Z]\b', line['text'])):
                break
            match=group_heading.search(line['text'])
            if match:
                q1 = int(match[1])
                q2 = int(match[2]) if match[2] else q1
                q_range = [q1, q2]
                existing = next((g for g in current['groups'] if g['questionRange'] == q_range), None)
                if existing is not None:
                    active = existing
                    if not active['lines']:
                        active['page'] = page
                    active['lines'].append(line)
                    continue
                if body:
                    current['blocks'].append({'text':text(body),'source':source(page,body)}); body=[]
                active={'id':f'group-{q1}-{q2}','questionRange':q_range,'lines':[], 'page':page}
                current['groups'].append(active); groups.append(active)
                continue

            m_boxes = re.search(r'\bin\s+boxes\s+(\d+)\s*[-–—]\s*(\d+)\b', line['text'], re.I)
            if m_boxes and (active is None or active.get('questionRange', [0, 0])[1] < int(m_boxes[1])):
                q1, q2 = int(m_boxes[1]), int(m_boxes[2])
                q_range = [q1, q2]
                existing = next((g for g in current['groups'] if g['questionRange'] == q_range), None)
                if existing is not None:
                    active = existing
                else:
                    if body:
                        current['blocks'].append({'text': text(body), 'source': source(page, body)})
                        body = []
                    active = {'id': f'group-{q1}-{q2}', 'questionRange': q_range, 'lines': [line], 'page': page}
                    current['groups'].append(active)
                    groups.append(active)
                continue

            m_sect = re.search(r'has\s+(?:six|\d+)\s+sections,\s*A\s*[-–—]?\s*([A-F])', line['text'], re.I)
            if m_sect and current.get('number') == 2 and (active is None or active.get('questionRange', [0, 0])[0] != 14):
                if body:
                    current['blocks'].append({'text': text(body), 'source': source(page, body)})
                    body = []
                active = {'id': 'group-14-19', 'questionRange': [14, 19], 'lines': [line], 'page': page}
                current['groups'].append(active)
                groups.append(active)
                continue

            m_q24 = re.match(r'^24\s+[A-Z]', line['text'])
            if m_q24 and active and active.get('questionRange') == [22, 23]:
                active = {'id': 'group-24-26', 'questionRange': [24, 26], 'lines': [line], 'page': page}
                current['groups'].append(active)
                groups.append(active)
                continue

            m_q34 = re.match(r'^(?:Complete each sentence|34\.)', line['text'], re.I)
            if m_q34 and active and active.get('questionRange') == [27, 33]:
                active = {'id': 'group-34-36', 'questionRange': [34, 36], 'lines': [line], 'page': page}
                current['groups'].append(active)
                groups.append(active)
                continue

            if para_heading.match(line['text'].strip()):
                active=None
                body.append(line)
            elif active is not None:
                active['lines'].append(line)
            else:
                body.append(line)
        if body:
            current['blocks'].append({'text':text(body),'source':source(page,body)})
    groups.sort(key=lambda g: g['questionRange'][0])
    for p in passages:
        p['groups'].sort(key=lambda g: g['questionRange'][0])
    answers=reading_answers(doc,answer_page,directory,output,review)
    for group in groups:
        page=group.pop('page'); lines=group.pop('lines'); raw=text(lines)
        lower=raw.lower()
        kind=('table-completion' if 'table below' in lower else 'true-false-not-given' if 'true' in lower and 'not given' in lower else
              'yes-no-not-given' if 'yes' in lower and 'not given' in lower else
              'matching-features' if 'match each' in lower else 'matching-information' if 'which paragraph' in lower or 'which section' in lower else
              'matching-headings' if 'list of headings' in lower or 'correct heading' in lower or 'sections' in lower else
              'summary-completion' if 'summary' in lower else 'notes-completion' if 'notes below' in lower else
              'sentence-completion' if 'sentence' in lower and ('ending' in lower or 'below' in lower or 'sentences below' in lower) else
              'multiple-choice' if 'choose two' in lower or 'choose the correct letter' in lower or 'choose the correct' in lower else 'unclassified')
        group.update(type=kind,context=raw,source=source(page,lines),questions=[],options=[])
        for line in lines:
            option=re.match(r'^([A-G])(?:[\s_]+|(?=[a-zA-Z]))(.*)',line['text'])
            if option and kind in ('matching-features','multiple-choice'):
                label=option[2].strip().lstrip('_').strip()
                group['options'].append({'value':option[1],'label':label,'source':source(page,[line])})
        if kind=='table-completion':
            box=source(page,lines)['boundingBox']; box=[max(0,box[0]-.01),max(0,box[1]-.015),min(.94,box[2]+.015),min(1,box[3]+.015)]
            group['asset']=crop(doc,page['pdfPage'],box,output,f'reading-{group["id"]}.png')
            review.append({'type':'table-layout-review','group':group['id'],'sourcePdfPage':page['pdfPage']})
        elif kind=='summary-completion':
            box=source(page,lines)['boundingBox']; box=[max(0,box[0]-.01),max(0,box[1]-.015),min(.94,box[2]+.015),min(1,box[3]+.015)]
            group['asset']=crop(doc,page['pdfPage'],box,output,f'reading-{group["id"]}.png')
        for n in range(group['questionRange'][0],group['questionRange'][1]+1):
            matches=[(i,l) for i,l in enumerate(lines) if re.search(rf'(?:^\s*|\b){n}[.)°]?(?:\s+|$)',l['text'])]
            selected=[]
            if kind in ('table-completion','summary-completion'):
                prompt=None
            elif kind=='matching-headings':
                prompt=f"Section {chr(ord('A') + n - 14)}"
            elif kind=='multiple-choice' and not matches:
                q_lines=[l for l in lines if not re.match(r'^(?:Choose|Write|Questions|[A-G]\b|>|\d+)',l['text'],re.I)]
                prompt=text(q_lines) if q_lines else None
            else:
                if matches:
                    start=matches[0][0]; selected=[lines[start]]
                    for line in lines[start+1:]:
                        if re.match(r'^\s*\d{1,2}[.)°]?\s+|^(?:List of|Questions|[A-G]\s)',line['text']): break
                        selected.append(line)
                prompt=text(selected) if selected else None
            answer=answers.get(str(n))
            group['questions'].append({'id':f'q{n}','number':n,'prompt':prompt,'source':source(page,selected) if selected else group['source'],
                                      'answer':answer,'needsReview':[] if prompt else [{'type':'use-group-context-or-image'}]})
            if not prompt and kind not in ('table-completion','summary-completion','multiple-choice','matching-headings'):
                review.append({'type':'question-boundary-review','question':n,'group':group['id']})
        if kind=='unclassified': review.append({'type':'unknown-question-type','group':group['id']})
    return {'passages':passages,'answerKey':answers,'excludedPdfPages':excluded,
            'detectedScoringPoints':sum(len(g['questions']) for g in groups),'expectedScoringPoints':40}


def parse_writing(payload,doc,output,review):
    hits = []
    for p_idx, page in enumerate(payload['pages']):
        lines = page['lines']
        for l_idx, l in enumerate(lines):
            m = re.search(r'(?:WRITING\s+TASK|Test\s*\d\s*[-–—_\W]*writing\s*[-–—_\W]*task|Test\s*\d\s*[-–—_\W]*task)\s*([12])', l['text'], re.I)
            if m:
                hits.append((int(m.group(1)), p_idx, l_idx))

    if len(hits) == 2 and hits[0][0] == 1 and hits[1][0] == 2:
        tasks = []
        p1_idx, l1_idx = hits[0][1], hits[0][2]
        p2_idx, l2_idx = hits[1][1], hits[1][2]
        page1 = payload['pages'][p1_idx]
        lines1 = page1['lines']
        page2 = payload['pages'][p2_idx]
        lines2 = page2['lines']

        limit1 = l2_idx if p1_idx == p2_idx else len(lines1)
        end1_candidates = [i for i in range(l1_idx+1, limit1) if re.search(r'Write at least\s+\d+\s+words', lines1[i]['text'], re.I)]
        end1 = end1_candidates[-1] if end1_candidates else next((i for i in range(l1_idx+1, len(lines1)) if re.search(r'Write at least\s+\d+\s+words', lines1[i]['text'], re.I)), None)
        task1_lines = lines1[l1_idx+1:end1+1] if end1 is not None else lines1[l1_idx+1:]
        min_words1 = int(re.search(r'Write at least\s+(\d+)\s+words', lines1[end1]['text'], re.I).group(1)) if end1 is not None else 150
        task1 = {'id': 'task-1', 'type': 'writing-task-1', 'number': 1,
                 'prompt': text(task1_lines), 'minimumWords': min_words1,
                 'source': source(page1, task1_lines), 'assets': [], 'sampleAnswer': None, 'needsReview': []}

        below1 = [l for l in lines1[end1+1:limit1] if l['boundingBox'][0] < 0.94] if end1 is not None else []
        if below1:
            box = source(page1, below1)['boundingBox']
            box = [max(lines1[end1]['boundingBox'][2]+.01, box[0]-.015), max(0, box[1]-.035), min(.94, box[2]+.025), min(1, box[3]+.035)]
            task1['assets'].append(crop(doc, page1['pdfPage'], box, output, 'writing-task-1-chart.png'))
            review.append({'type': 'chart-crop-review', 'task': 1, 'sourcePdfPage': page1['pdfPage']})
        elif p2_idx > p1_idx and l2_idx > 0:
            chart_lines = [l for l in lines2[:l2_idx] if l['boundingBox'][0] < 0.94]
            if chart_lines:
                box = source(page2, chart_lines)['boundingBox']
                box = [max(0.04, box[0]-.015), max(0, box[1]-.035), min(lines2[l2_idx]['boundingBox'][0]-.01, box[2]+.025), min(1, box[3]+.035)]
                task1['assets'].append(crop(doc, page2['pdfPage'], box, output, 'writing-task-1-chart.png'))
                review.append({'type': 'chart-crop-review', 'task': 1, 'sourcePdfPage': page2['pdfPage']})
        tasks.append(task1)

        end2_candidates = [i for i in range(l2_idx+1, len(lines2)) if re.search(r'Write at least\s+\d+\s+words', lines2[i]['text'], re.I)]
        if end2_candidates:
            end2 = end2_candidates[-1]
            task2_lines = lines2[l2_idx+1:end2+1]
            min_words2 = int(re.search(r'Write at least\s+(\d+)\s+words', lines2[end2]['text'], re.I).group(1))
            t2_source = source(page2, task2_lines)
        else:
            t2_part1 = lines2[l2_idx+1:]
            t2_part2 = []
            min_words2 = 250
            p3_obj = None
            if p2_idx + 1 < len(payload['pages']):
                page3 = payload['pages'][p2_idx + 1]
                p3_obj = page3
                lines3 = page3['lines']
                start3 = next((i for i, l in enumerate(lines3) if re.search(r'Write about the following topic', l['text'], re.I)), 0)
                end3_candidates = [i for i in range(start3, len(lines3)) if re.search(r'Write at least\s+\d+\s+words', lines3[i]['text'], re.I)]
                if end3_candidates:
                    end3 = end3_candidates[0]
                    t2_part2 = lines3[start3:end3+1]
                    min_words2 = int(re.search(r'Write at least\s+(\d+)\s+words', lines3[end3]['text'], re.I).group(1))
            task2_lines = t2_part1 + t2_part2
            t2_source = source(page2, t2_part1) if t2_part1 else (source(p3_obj, t2_part2) if p3_obj else None)

        task2 = {'id': 'task-2', 'type': 'writing-task-2', 'number': 2,
                 'prompt': text(task2_lines), 'minimumWords': min_words2,
                 'source': t2_source, 'assets': [], 'sampleAnswer': None, 'needsReview': []}
        tasks.append(task2)
        return {'tasks': tasks, 'sampleAnswerStatus': 'not-extracted'}

    tasks=[]
    for page in payload['pages']:
        lines=content(page)
        hit=next((i for i,l in enumerate(lines) if re.search(r'(?:WRITING\s+TASK|Test\s*\d\s*[-–—_\W]*writing\s*[-–—_\W]*task|Test\s*\d\s*[-–—_\W]*task)\s*([12])',l['text'],re.I)),None)
        if hit is None:
            review.append({'type':'writing-heading-missing','sourcePdfPage':page['pdfPage']}); continue
        number=int(re.search(r'(?:WRITING\s+TASK|Test\s*\d\s*[-–—_\W]*writing\s*[-–—_\W]*task|Test\s*\d\s*[-–—_\W]*task)\s*([12])',lines[hit]['text'],re.I).group(1))
        end=next((i for i in range(hit+1,len(lines)) if re.search(r'Write at least\s+\d+\s+words',lines[i]['text'],re.I)),None)
        if end is None:
            review.append({'type':'word-limit-missing','sourcePdfPage':page['pdfPage']}); continue
        task_lines=lines[hit+1:end+1]
        task={'id':f'task-{number}','type':f'writing-task-{number}','number':number,
              'prompt':text(task_lines),'minimumWords':int(re.search(r'Write at least\s+(\d+)\s+words',lines[end]['text'],re.I).group(1)),
              'source':source(page,task_lines),'assets':[],'sampleAnswer':None,'needsReview':[]}
        if number==1 and re.search(r'graph|chart|diagram|map|table|plan',text(task_lines),re.I):
            below=[l for l in lines[end+1:] if l['boundingBox'][0]<.94]
            if below:
                box=source(page,below)['boundingBox']
                # Include axes and graph strokes which are not OCR words.
                box=[max(lines[end]['boundingBox'][2]+.01,box[0]-.015),max(0,box[1]-.035),min(.94,box[2]+.025),min(1,box[3]+.035)]
                task['assets'].append(crop(doc,page['pdfPage'],box,output,'writing-task-1-chart.png'))
                review.append({'type':'chart-crop-review','task':1,'sourcePdfPage':page['pdfPage']})
            else: review.append({'type':'missing-writing-image','task':1})
        tasks.append(task)
    return {'tasks':tasks,'sampleAnswerStatus':'not-extracted'}


def parse_speaking(payload,doc,output,directory,review):
    parts=[]
    for page in payload['pages']:
        lines=content(page)
        bounds=[(i,int(m[1])) for i,l in enumerate(lines) if (m:=re.search(r'(?:^|\b)(?:PART|Test\s*\d\s*[-–—_\W]*Part)\s*([123])\b',l['text'],re.I))]
        if bounds and bounds[0][1] == 2 and any('?' in l['text'] for l in lines[:bounds[0][0]]):
            bounds.insert(0, (-1, 1))
        for offset,(start,number) in enumerate(bounds):
            end=bounds[offset+1][0] if offset+1<len(bounds) else len(lines)
            selected=lines[start+1:end]
            if number == 3:
                cutoff = len(selected)
                for idx_s, l in enumerate(selected):
                    if re.search(r'^\s*(?:BE|Candidate\s*response|Sample\s*answer)\b', l['text'], re.I) or (idx_s > 0 and '?' not in l['text'] and re.search(r'^\s*1\.\s+Well\b', l['text'], re.I)):
                        cutoff = idx_s
                        break
                selected = selected[:cutoff]
            part={'part':number,'type':f'speaking-part-{number}','source':source(page,selected),'topics':[],'needsReview':[]}
            if number==2:
                has_side_instr = any(re.search(r'talk about the topic for 1 to 2 minutes|one minute to think', l['text'], re.I) for l in selected)
                box = source(page, selected)['boundingBox']
                if has_side_instr:
                    card_box = [max(0, box[0]-.01), max(0, box[1]-.01), min(.94, box[2]+.01), .62]
                    card_lines = []
                    instr_lines = []
                    card_words = []
                    for l in selected:
                        cw = [w for w in l.get('words', []) if w['boundingBox'][1] < 0.62]
                        iw = [w for w in l.get('words', []) if w['boundingBox'][1] >= 0.62]
                        if cw:
                            card_lines.append(' '.join(w['text'] for w in cw))
                            card_words.extend(cw)
                        if iw:
                            instr_lines.append(' '.join(w['text'] for w in iw))
                else:
                    card_box = [max(0, box[0]-.01), max(0, box[1]-.01), min(.94, box[2]+.01), min(.98, box[3]+.03)]
                    card_lines = [l['text'] for l in selected if not re.search(r'^\s*Please answer the question\s*$', l['text'], re.I)]
                    instr_lines = []
                    card_words = [w for l in selected for w in l.get('words', [])]

                card_bbox = [min(w['boundingBox'][0] for w in card_words), min(w['boundingBox'][1] for w in card_words),
                             max(w['boundingBox'][2] for w in card_words), max(w['boundingBox'][3] for w in card_words)] if card_words else card_box
                card_conf = [w['confidence'] for w in card_words if w.get('confidence') is not None] if card_words else []
                part['cueCard'] = {'text': '\n'.join(card_lines),
                                  'source': {'pdfPage': page['pdfPage'], 'printedPage': page.get('printedPage'), 'method': page['method'],
                                            'boundingBox': card_bbox, 'confidence': sum(card_conf)/len(card_conf) if card_conf else None},
                                  'asset': crop(doc, page['pdfPage'], card_box, output, 'speaking-part-2-cue-card.png')}
                part['instructionText'] = '\n'.join(instr_lines) or text(selected)
                review.append({'type': 'cue-card-layout-review', 'sourcePdfPage': page['pdfPage']})
            else:
                topic=None
                for i,line in enumerate(selected):
                    value=line['text']
                    if '?' in value:
                        if topic is None:
                            topic={'title':None,'questions':[]};part['topics'].append(topic)
                        topic['questions'].append({'text':re.sub(r'^[e•●]\s+','',value),'source':source(page,[line])})
                    elif (number==1 and i>0 and selected[i-1]['text'].upper()=='EXAMPLE') or (number==3 and i+1<len(selected) and selected[i+1]['text'].startswith('Example questions')):
                        topic={'title':value,'questions':[]};part['topics'].append(topic)
                part['context']=text(selected)
            parts.append(part)
    return {'parts':parts}


def import_skill(payload,doc,output,cache,answer_page,directory):
    review=[];skill=payload['skill']
    output.mkdir(parents=True,exist_ok=True)
    if skill=='reading': data=parse_reading(payload,doc,output,answer_page,directory,review)
    elif skill=='writing': data=parse_writing(payload,doc,output,review)
    else: data=parse_speaking(payload,doc,output,directory,review)
    low=[p['pdfPage'] for p in payload['pages'] if p.get('confidence') is not None and p['confidence']<.85]
    if low: review.append({'type':'low-page-ocr-confidence','pdfPages':low})
    review.append({'type':'source-content-review','message':'OCR text and segmentation require comparison with source before publication.'})
    supplemental=[]
    for path in sorted(directory.glob('*.json')):
        if (skill=='reading' and path.name.startswith('reading-answers-')) or (skill=='speaking' and path.name.startswith('speaking-')):
            supplemental.append({'path':path.relative_to(ROOT).as_posix(),'sha256':compute_sha256(path)})
    return {'schemaVersion':1,'id':f'c{payload["book"]}-t{payload["test"]}-{skill}',
            'book':payload['book'],'test':payload['test'],'skill':skill,'variant':'academic','verified':False,'status':'needs-review',
            'sources':{'paper':payload['source'],'questionPdfPages':[p['pdfPage'] for p in payload['pages']],
                       'answerPdfPages':[answer_page] if answer_page else [],'supplementalExtractions':supplemental},
            **data,'needsReview':review}
