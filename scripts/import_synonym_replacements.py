#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import and structure all Cambridge IELTS Synonym Replacement (Paraphrase) collections
from authentic digital PDF files located in:
IELTS/剑雅真题【4-19】/真题/剑1-剑16同义词替换PDF/

Generates:
1. resources/words/ielts-synonyms.json (Vocabulary Studio book)
2. resources/synonyms/cambridge-synonyms.json (Hierarchical dataset & by-question map)
3. Enriches resources/cambridge/ test questions with explanation.paraphrase
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path

try:
    import fitz
except ImportError:
    print("Error: PyMuPDF (fitz) is required.")
    sys.exit(1)

WORKSPACE = Path(__file__).resolve().parent.parent

def sha20(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:20]


def review_flags(rec):
    """Flag likely extraction errors; never silently rewrite source wording."""
    term, para = rec['term'].strip(), rec['paraphrase'].strip()
    flags = []
    if len(term) > 80 or len(term.split()) > 8 or len(para) > 160:
        flags.append('long-extraction')
    if re.search(r'\bhap\s+piness\b', term + ' ' + para, re.I):
        flags.append('possible-split-word')
    if not rec.get('sourcePages'):
        flags.append('source-page-unresolved')
    if rec.get('sourceTermMatched') is False:
        flags.append('source-term-not-exact')
    return flags


def add_source_metadata(records, base_dir):
    """Resolve each entry to its own PDF and a 1-based PDF page when unambiguous."""
    paths = {p.name: p for p in base_dir.rglob('*.pdf')}
    page_texts = {}
    for name, path in paths.items():
        with fitz.open(path) as doc:
            page_texts[name] = [clean_text(page.get_text()).casefold() for page in doc]
    for rec in records:
        path = paths.get(rec.get('pdf'))
        rec['sourcePath'] = path.relative_to(WORKSPACE).as_posix() if path else None
        rec['sourcePages'] = []
        if not path:
            continue
        pages = page_texts[path.name]
        term = clean_text(rec['term']).casefold()
        candidates = [i + 1 for i, text in enumerate(pages) if term and term in text]
        reported = rec.get('page')
        # All parsers retain the actual PDF page where the entry begins.
        trusted_page = reported if isinstance(reported, int) and 1 <= reported <= len(pages) else None
        if trusted_page and (trusted_page in candidates or not candidates):
            rec['sourcePages'] = [trusted_page]
        elif len(candidates) == 1:
            rec['sourcePages'] = candidates
        rec['sourceTermMatched'] = bool(rec['sourcePages'] and rec['sourcePages'][0] in candidates)
        rec['needsReview'] = review_flags(rec)

def clean_text(s: str) -> str:
    if not s:
        return ""
    # Normalize unicode spaces and quotes
    s = s.replace('\xa0', ' ').replace('\u3000', ' ').replace('’', "'").replace('‘', "'")
    s = s.replace('“', '"').replace('”', '"')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def split_en_cn(text: str):
    """Separates English terms from Chinese annotations."""
    cn = ''.join(re.findall(r'[\u4e00-\u9fff\uff00-\uffef\u3000-\u303f]+', text)).strip()
    en = re.sub(r'[\u4e00-\u9fff\uff00-\uffef\u3000-\u303f]+', ' ', text).strip()
    en = re.sub(r'\s+', ' ', en).strip(' ,;:-=—_()（）')
    cn = cn.strip(' ,;:-=—_()（）')
    return en, cn

def parse_c10(pdf_path: Path):
    doc = fitz.open(pdf_path)
    entries = []
    current_test = 1
    
    for p_idx in range(len(doc)):
        page_text = doc[p_idx].get_text()
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        
        buf = []
        for line in lines:
            tm = re.search(r'test\s*(\d+)', line, re.I)
            if tm and ('剑' in line or len(line) < 25):
                if buf:
                    entries.append((current_test, p_idx + 1, ' '.join(buf)))
                    buf = []
                current_test = int(tm.group(1))
                continue
                
            m = re.match(r'^(\d+)\.\s*(.*)', line)
            if m:
                if buf:
                    entries.append((current_test, p_idx + 1, ' '.join(buf)))
                    buf = []
                buf.append(line)
            elif buf:
                buf.append(line)
        if buf:
            entries.append((current_test, p_idx + 1, ' '.join(buf)))
            
    results = []
    for test, page_num, raw in entries:
        raw_clean = clean_text(raw)
        nm = re.match(r'^(\d+)\.\s*(.*)', raw_clean)
        num = int(nm.group(1)) if nm else None
        body = nm.group(2) if nm else raw_clean
        
        parts = [p.strip() for p in body.split('=') if p.strip()]
        if len(parts) >= 2:
            term1, cn1 = split_en_cn(parts[0])
            term2, cn2 = split_en_cn(' = '.join(parts[1:]))
            cn = cn1 or cn2
            if term1 and term2:
                results.append({
                    'book': 10,
                    'test': test,
                    'skill': 'reading',
                    'item_num': num,
                    'term': term1,
                    'paraphrase': term2,
                    'meaning': cn,
                    'raw': raw_clean,
                    'page': page_num,
                    'pdf': pdf_path.name
                })
    return results

def parse_c11(pdf_path: Path):
    doc = fitz.open(pdf_path)
    entries = []
    current_test = 1
    
    for p_idx in range(len(doc)):
        page_text = doc[p_idx].get_text()
        lines = [l.strip() for l in page_text.splitlines() if l.strip()]
        
        buf = []
        for line in lines:
            tm = re.search(r'test\s*(\d+)', line, re.I)
            if tm and ('剑' in line or len(line) < 25):
                if buf:
                    entries.append((current_test, p_idx + 1, ' '.join(buf)))
                    buf = []
                current_test = int(tm.group(1))
                continue
                
            m = re.match(r'^(\d+)\.\s*(.*)', line)
            if m:
                if buf:
                    entries.append((current_test, p_idx + 1, ' '.join(buf)))
                    buf = []
                buf.append(line)
            elif buf:
                buf.append(line)
        if buf:
            entries.append((current_test, p_idx + 1, ' '.join(buf)))
            
    results = []
    for test, page_num, raw in entries:
        raw_clean = clean_text(raw)
        nm = re.match(r'^(\d+)\.\s*(.*)', raw_clean)
        num = int(nm.group(1)) if nm else None
        body = nm.group(2) if nm else raw_clean
        
        parts = [p.strip() for p in body.split('=') if p.strip()]
        if len(parts) >= 2:
            term1, cn1 = split_en_cn(parts[0])
            term2, cn2 = split_en_cn(' = '.join(parts[1:]))
            cn = cn1 or cn2
            if term1 and term2:
                results.append({
                    'book': 11,
                    'test': test,
                    'skill': 'reading',
                    'item_num': num,
                    'term': term1,
                    'paraphrase': term2,
                    'meaning': cn,
                    'raw': raw_clean,
                    'page': page_num,
                    'pdf': pdf_path.name
                })
    return results

def parse_c12(pdf_path: Path):
    doc = fitz.open(pdf_path)
    lines = [(p_idx + 1, l.strip()) for p_idx in range(len(doc)) for l in doc[p_idx].get_text().splitlines() if l.strip()]
    
    items = []
    current_item = None
    for page_num, line in lines:
        if '步剑' in line:
            continue
        m = re.match(r'^(\d+)\.\s*(.*)', line)
        if m:
            if current_item:
                items.append(current_item)
            current_item = {'num': int(m.group(1)), 'page': page_num, 'lines': [m.group(2).strip()] if m.group(2).strip() else []}
        elif current_item:
            current_item['lines'].append(line)
    if current_item:
        items.append(current_item)
        
    results = []
    for it in items:
        num = it['num']
        # Map item number to test (based on authentic passage distribution)
        if num <= 23:
            test = 1
        elif num <= 48:
            test = 2
        elif num <= 73:
            test = 3
        else:
            test = 4
            
        l_arr = it['lines']
        if len(l_arr) >= 2:
            term1 = clean_text(l_arr[0])
            term2 = clean_text(l_arr[1])
            cn = clean_text(' '.join(l_arr[2:])) if len(l_arr) > 2 else ""
            results.append({
                'book': 12,
                'test': test,
                'skill': 'reading',
                'item_num': num,
                'term': term1,
                'paraphrase': term2,
                'meaning': cn,
                'raw': f"{num}. {term1} = {term2} ({cn})",
                'page': it['page'],
                'pdf': pdf_path.name
            })
    return results

def parse_c13(pdf_path: Path):
    doc = fitz.open(pdf_path)
    lines = [(p_idx + 1, l.strip()) for p_idx in range(len(doc)) for l in doc[p_idx].get_text().splitlines() if l.strip()]
    
    current_test = 1
    items = []
    current_item = None
    
    for page_num, line in lines:
        tm = re.search(r'test\s*(\d+)', line, re.I)
        if tm:
            if current_item:
                items.append(current_item)
                current_item = None
            current_test = int(tm.group(1))
            continue
            
        m = re.match(r'^(\d+)\.\s*(.*)', line)
        if m:
            if current_item:
                items.append(current_item)
            current_item = {'test': current_test, 'num': int(m.group(1)), 'page': page_num, 'text': m.group(2).strip()}
        elif current_item:
            current_item['text'] += ' ' + line
    if current_item:
        items.append(current_item)
        
    results = []
    for it in items:
        raw_clean = clean_text(it['text'])
        parts = [p.strip() for p in raw_clean.split('/') if p.strip()]
        if len(parts) >= 2:
            term1, cn1 = split_en_cn(parts[0])
            term2, cn2 = split_en_cn(' / '.join(parts[1:]))
            cn = cn1 or cn2
            results.append({
                'book': 13,
                'test': it['test'],
                'skill': 'reading',
                'item_num': it['num'],
                'term': term1,
                'paraphrase': term2,
                'meaning': cn,
                'raw': f"{it['num']}. {raw_clean}",
                'page': it['page'],
                'pdf': pdf_path.name
            })
    return results

def parse_c14(pdf_path: Path):
    doc = fitz.open(pdf_path)
    lines = [(p_idx + 1, l.strip()) for p_idx in range(len(doc)) for l in doc[p_idx].get_text().splitlines() if l.strip()]
    
    current_skill = 'listening'
    current_test = 1
    val_map = {'1': 1, 'one': 1, '2': 2, 'two': 2, '3': 3, 'three': 3, '4': 4, 'four': 4}
    
    results = []
    for page_num, line in lines:
        if line.startswith('听力'):
            current_skill = 'listening'; continue
        elif line.startswith('口语'):
            current_skill = 'speaking'; continue
        elif line.startswith('写作'):
            current_skill = 'writing'; continue
        elif line.startswith('阅读'):
            current_skill = 'reading'; continue
            
        tm = re.match(r'^(?:Test|test)\s*(\d+|one|two|three|four)', line, re.I)
        if tm:
            val = tm.group(1).lower()
            if val in val_map:
                current_test = val_map[val]
            continue
            
        if any(h in line for h in ['剑14 替换词', 'Writing task', 'Task 1', 'Task 2', '词汇拓展', '【同义表达】', '【经典搭配】']):
            continue
            
        # Extract question number
        qm = re.search(r'（?第\s*(\d+(?:[，、.&与和\s]+\d+)*)\s*题）?', line)
        q_num = None
        if qm:
            try:
                first_num = re.findall(r'\d+', qm.group(1))[0]
                q_num = int(first_num)
            except Exception:
                pass
                
        clean_l = re.sub(r'（?第\s*(\d+(?:[，、.&与和\s]+\d+)*)\s*题）?', '', line).strip()
        num_m = re.match(r'^(\d+)[,，.、:\s]\s*(.*)', clean_l)
        body = num_m.group(2).strip() if num_m else clean_l
        
        # Split delimiters: '------', '-----', '----', '---', '--', '=', ':', '-', '<->', '<>'
        delims = ['------', '-----', '----', '---', '--', '<->', '<>', '=', ':', '：', '/']
        parts = []
        for d in delims:
            if d in body:
                parts = [p.strip() for p in body.split(d) if p.strip()]
                break
        if not parts and ' - ' in body:
            parts = [p.strip() for p in body.split(' - ') if p.strip()]
            
        if len(parts) >= 2:
            term1, cn1 = split_en_cn(parts[0])
            term2, cn2 = split_en_cn(' ⇋ '.join(parts[1:]))
            cn = cn1 or cn2
            if term1 and term2:
                results.append({
                    'book': 14,
                    'test': current_test,
                    'skill': current_skill,
                    'question': q_num,
                    'term': term1,
                    'paraphrase': term2,
                    'meaning': cn,
                    'raw': clean_text(line),
                    'page': page_num,
                    'pdf': pdf_path.name
                })
        elif len(parts) == 1 or not parts:
            # Check Chinese meaning embedded between English terms: e.g. "typical meals 有代表性的餐食 usual meals"
            m_embed = re.search(r'^([a-zA-Z\s\',.-]+)\s+([\u4e00-\u9fff\uff00-\uffef\u3000-\u303f\s，、；]+)\s+([a-zA-Z\s\',.-]+)$', body)
            if m_embed:
                term1 = clean_text(m_embed.group(1))
                cn = clean_text(m_embed.group(2))
                term2 = clean_text(m_embed.group(3))
                if term1 and term2:
                    results.append({
                        'book': 14,
                        'test': current_test,
                        'skill': current_skill,
                        'question': q_num,
                        'term': term1,
                        'paraphrase': term2,
                        'meaning': cn,
                        'raw': clean_text(line),
                        'page': page_num,
                        'pdf': pdf_path.name
                    })
    return results

def parse_c15(pdf_path: Path):
    doc = fitz.open(pdf_path)
    results = []
    
    for p_idx in range(len(doc)):
        test_num = p_idx + 1
        lines = [l.strip() for l in doc[p_idx].get_text().splitlines() if l.strip()]
        
        current_p = 1
        buf = []
        entries = []
        for line in lines:
            pm = re.search(r'passage\s*(\d+)', line, re.I)
            if pm:
                if buf:
                    entries.append((current_p, ' '.join(buf)))
                    buf = []
                current_p = int(pm.group(1))
                continue
            if re.match(r'^\d+\.', line):
                if buf:
                    entries.append((current_p, ' '.join(buf)))
                    buf = []
                buf.append(line)
            elif buf:
                buf.append(line)
        if buf:
            entries.append((current_p, ' '.join(buf)))
            
        for passage, raw in entries:
            raw_clean = clean_text(raw)
            # Question number
            qm = re.search(r'（?第\s*(\d+(?:[，、.&与和\s]+\d+)*)\s*题）?', raw_clean)
            q_num = None
            if qm:
                try:
                    q_num = int(re.findall(r'\d+', qm.group(1))[0])
                except Exception:
                    pass
                    
            clean_l = re.sub(r'（?第\s*(\d+(?:[，、.&与和\s]+\d+)*)\s*题）?', '', raw_clean).strip()
            clean_l = re.sub(r'^\d+\.\s*', '', clean_l).strip()
            
            # Format: '包住、环绕: be encased = surrounds' or 'objective ---- aim 目标'
            cn = ""
            if ':' in clean_l or '：' in clean_l:
                split_colon = re.split(r'[:：]', clean_l, maxsplit=1)
                cn_part, en_part = split_colon[0].strip(), split_colon[1].strip()
                _, cn = split_en_cn(cn_part)
                eq_parts = [p.strip() for p in re.split(r'=|----|---|--', en_part) if p.strip()]
                if len(eq_parts) >= 2:
                    t1, _ = split_en_cn(eq_parts[0])
                    t2, extra_cn = split_en_cn(' = '.join(eq_parts[1:]))
                    cn = cn or extra_cn
                    results.append({
                        'book': 15,
                        'test': test_num,
                        'passage': passage,
                        'skill': 'reading',
                        'question': q_num,
                        'term': t1,
                        'paraphrase': t2,
                        'meaning': cn,
                        'raw': raw_clean,
                        'page': p_idx + 1,
                        'pdf': pdf_path.name
                    })
            else:
                eq_parts = [p.strip() for p in re.split(r'=|----|---|--', clean_l) if p.strip()]
                if len(eq_parts) >= 2:
                    t1, cn1 = split_en_cn(eq_parts[0])
                    t2, cn2 = split_en_cn(' = '.join(eq_parts[1:]))
                    cn = cn1 or cn2
                    results.append({
                        'book': 15,
                        'test': test_num,
                        'passage': passage,
                        'skill': 'reading',
                        'question': q_num,
                        'term': t1,
                        'paraphrase': t2,
                        'meaning': cn,
                        'raw': raw_clean,
                        'page': p_idx + 1,
                        'pdf': pdf_path.name
                    })
    return results

def parse_c16(pdf_path: Path):
    doc = fitz.open(pdf_path)
    lines = [(p_idx + 1, l.strip()) for p_idx in range(len(doc)) for l in doc[p_idx].get_text().splitlines() if l.strip()]
    
    current_skill = 'reading'
    current_test = 1
    items = []
    
    buf = ''
    buf_page = None
    for page_num, line in lines:
        if line == '阅读':
            current_skill = 'reading'; continue
        if line == '听力':
            current_skill = 'listening'; continue
        tm = re.match(r'^Test\s*(\d+)', line, re.I)
        if tm:
            if buf:
                items.append((current_skill, current_test, buf_page, buf))
                buf = ''
            current_test = int(tm.group(1))
            continue
        if any(h in line for h in ['剑桥雅思16', '替换词', '注：部分为非同义替换']):
            continue
            
        if '/' in line:
            if buf:
                items.append((current_skill, current_test, buf_page, buf))
            buf = line
            buf_page = page_num
        else:
            if buf:
                buf += ' ' + line
            else:
                buf = line
                buf_page = page_num
    if buf:
        items.append((current_skill, current_test, buf_page, buf))
        
    results = []
    for skill, test, page_num, raw in items:
        raw_clean = clean_text(raw)
        parts = [p.strip() for p in raw_clean.split('/') if p.strip()]
        if len(parts) >= 2:
            term1, cn1 = split_en_cn(parts[0])
            term2, cn2 = split_en_cn(' / '.join(parts[1:]))
            cn = cn1 or cn2
            if term1 and term2:
                results.append({
                    'book': 16,
                    'test': test,
                    'skill': skill,
                    'term': term1,
                    'paraphrase': term2,
                    'meaning': cn,
                    'raw': raw_clean,
                    'page': page_num,
                    'pdf': pdf_path.name
                })
    return results

def parse_c1_c9(pdf_path: Path):
    doc = fitz.open(pdf_path)
    lines = [(p_idx + 1, l.strip()) for p_idx in range(len(doc)) for l in doc[p_idx].get_text().splitlines() if l.strip()]
    
    current_book = 9
    current_test = 1
    current_label = '剑9 第一篇'
    items = []
    
    p_map = {'一': 1, '二': 2, '三': 3, '四': 4, '1': 1, '2': 2, '3': 3, '4': 4}
    
    for page_num, line in lines:
        if '雅思阅读同义词替换' in line:
            continue
            
        bm = re.search(r'^(?:剑\s*([1-9])|Cambridge\s*([1-9]))', line, re.I)
        if bm:
            current_book = int(bm.group(1) or bm.group(2))
            tm = re.search(r'TEST\s*(\d+)', line, re.I)
            if tm:
                current_test = int(tm.group(1))
                current_label = f"剑{current_book} Test {current_test}"
            pm = re.search(r'第([一二三四\d]+)篇', line)
            if pm:
                current_test = p_map.get(pm.group(1), 1)
                current_label = f"剑{current_book} 第{pm.group(1)}篇"
            elif '其他' in line:
                current_label = f"剑{current_book} 补充词汇"
            continue
            
        tm = re.search(r'^(?:Cambridge\s*\d+\s*)?TEST\s*(\d+)', line, re.I)
        if tm:
            current_test = int(tm.group(1))
            current_label = f"剑{current_book} Test {current_test}"
            continue
            
        parts = re.split(r'(?:^|\s+)(?=\d+\.\s*)', line)
        for part in parts:
            part = part.strip()
            if not part: continue
            nm = re.match(r'^(\d+)\.\s*(.*)', part)
            if nm:
                num = int(nm.group(1))
                text = nm.group(2).strip()
                items.append({
                    'book': current_book,
                    'test': current_test,
                    'label': current_label,
                    'num': num,
                    'text': text,
                    'page': page_num
                })
            else:
                if items:
                    items[-1]['text'] += ' ' + part
                    
    results = []
    for it in items:
        raw_clean = clean_text(it['text'])
        # Can be split by '/' or '='
        delim = '/' if '/' in raw_clean else '=' if '=' in raw_clean else None
        if delim:
            parts = [p.strip() for p in raw_clean.split(delim) if p.strip()]
            if len(parts) >= 2:
                term1, cn1 = split_en_cn(parts[0])
                term2, cn2 = split_en_cn(f' {delim} '.join(parts[1:]))
                cn = cn1 or cn2
                if term1 and term2:
                    results.append({
                        'book': it['book'],
                        'test': it['test'],
                        'label': it['label'],
                        'skill': 'reading',
                        'item_num': it['num'],
                        'term': term1,
                        'paraphrase': term2,
                        'meaning': cn,
                        'raw': f"{it['num']}. {raw_clean}",
                        'page': it['page'],
                        'pdf': pdf_path.name
                    })
    return results

def main():
    base_dir = WORKSPACE / "IELTS/剑雅真题【4-19】/真题/剑1-剑16同义词替换PDF"
    if not base_dir.is_dir():
        print(f"Directory not found: {base_dir}")
        return
        
    all_records = []
    
    # 1. C10
    c10_path = base_dir / "剑10同义替换PDF/剑10同义词替换.pdf"
    if c10_path.is_file():
        r = parse_c10(c10_path)
        print(f"Parsed C10: {len(r)} records")
        all_records.extend(r)
        
    # 2. C11
    c11_path = base_dir / "剑11同义替换PDF/剑11同义词替换.pdf"
    if c11_path.is_file():
        r = parse_c11(c11_path)
        print(f"Parsed C11: {len(r)} records")
        all_records.extend(r)
        
    # 3. C12
    c12_path = base_dir / "剑12同义替换PDF/剑12同义词替换.pdf"
    if c12_path.is_file():
        r = parse_c12(c12_path)
        print(f"Parsed C12: {len(r)} records")
        all_records.extend(r)
        
    # 4. C13
    c13_path = base_dir / "剑13同义替换PDF/剑13同义词替换合集.pdf"
    if c13_path.is_file():
        r = parse_c13(c13_path)
        print(f"Parsed C13: {len(r)} records")
        all_records.extend(r)
        
    # 5. C14
    c14_path = base_dir / "剑14同义替换PDF/剑 14 替换词.pdf"
    if c14_path.is_file():
        r = parse_c14(c14_path)
        print(f"Parsed C14: {len(r)} records")
        all_records.extend(r)
        
    # 6. C15
    c15_path = base_dir / "剑15同义替换PDF/剑15同义词转换.pdf"
    if c15_path.is_file():
        r = parse_c15(c15_path)
        print(f"Parsed C15: {len(r)} records")
        all_records.extend(r)
        
    # 7. C16
    c16_path = base_dir / "剑16同义替换PDF/剑16替换词合集.pdf"
    if c16_path.is_file():
        r = parse_c16(c16_path)
        print(f"Parsed C16: {len(r)} records")
        all_records.extend(r)
        
    # 8. C1-C9
    c1_c9_path = base_dir / "剑1—剑9同义替换PDF/剑1到剑9同义词替换_1040.pdf"
    if c1_c9_path.is_file():
        r = parse_c1_c9(c1_c9_path)
        print(f"Parsed C1-C9: {len(r)} records")
        all_records.extend(r)
        
    print(f"\nTOTAL EXTRACTED RECORDS: {len(all_records)}")
    add_source_metadata(all_records, base_dir)
    
    # -------------------------------------------------------------
    # Build Vocabulary Book: resources/words/ielts-synonyms.json
    # -------------------------------------------------------------
    word_entries = []
    seen_hashes = set()
    
    skill_names = {
        'listening': '听力',
        'reading': '阅读',
        'writing': '写作',
        'speaking': '口语'
    }
    
    for rec in all_records:
        book_num = rec['book']
        test_num = rec.get('test', 1)
        skill = rec.get('skill', 'reading')
        skill_cn = skill_names.get(skill, '阅读')
        
        category = f"剑{book_num} Test {test_num} {skill_cn}"
        categories = [category, f"剑{book_num}", skill_cn]
        
        term = rec['term']
        para = rec['paraphrase']
        cn = rec.get('meaning', '').strip()
        q = rec.get('question')
        
        # Build clean meaning text
        meaning_parts = [f"⇋ {para}"]
        if cn:
            meaning_parts.append(f"({cn})")
        if q:
            meaning_parts.append(f"[Q{q}]")
        meaning_str = " ".join(meaning_parts)
        
        entry_id = sha20(f"synonym-{book_num}-{test_num}-{skill}-{term}-{para}")
        if entry_id in seen_hashes:
            continue
        seen_hashes.add(entry_id)
        
        word_entries.append({
            'id': entry_id,
            'word': term,
            'meaning': meaning_str,
            'category': category,
            'categories': categories,
            'book': book_num,
            'test': test_num,
            'skill': skill,
            'question': q,
            'sourcePath': rec['sourcePath'],
            'sourcePages': rec['sourcePages'],
            'needsReview': rec['needsReview'],
            'meaningStatus': 'provided' if cn else 'missing-in-source',
            'sourceText': rec.get('raw', ''),
            'method': 'text-layer'
        })
        
    print(f"Unique vocabulary words generated: {len(word_entries)}")
    
    words_dir = WORKSPACE / "resources/words"
    words_dir.mkdir(parents=True, exist_ok=True)
    
    vocab_book = {
        "schemaVersion": 1,
        "id": "ielts-synonyms",
        "title": "剑桥雅思真题同义替换",
        "count": len(word_entries),
        "verified": False,
        "source": {
            "title": "剑桥雅思真题1-16同义词替换合集",
            "path": "IELTS/剑雅真题【4-19】/真题/剑1-剑16同义词替换PDF",
            "pdfCount": 8
        },
        "words": word_entries
    }
    
    vocab_file = words_dir / "ielts-synonyms.json"
    vocab_file.write_text(json.dumps(vocab_book, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Saved vocabulary book: {vocab_file.relative_to(WORKSPACE)}")
    
    # Update manifest.json if not present
    manifest_path = words_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        books = manifest.get('books', [])
        found = False
        for b in books:
            if b.get('id') == 'ielts-synonyms':
                b['count'] = len(word_entries)
                found = True
                break
        if not found:
            books.append({
                "id": "ielts-synonyms",
                "title": "剑桥雅思真题同义替换",
                "count": len(word_entries),
                "path": "ielts-synonyms.json"
            })
        manifest['books'] = books
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Updated {manifest_path.relative_to(WORKSPACE)}")
        
    # -------------------------------------------------------------
    # Build Structured Dataset: resources/synonyms/cambridge-synonyms.json
    # -------------------------------------------------------------
    synonyms_dir = WORKSPACE / "resources/synonyms"
    synonyms_dir.mkdir(parents=True, exist_ok=True)
    
    by_book = {}
    by_question = {}
    
    for rec in all_records:
        b = str(rec['book'])
        t = f"test-{rec.get('test', 1)}"
        s = rec.get('skill', 'reading')
        
        if b not in by_book:
            by_book[b] = {}
        if t not in by_book[b]:
            by_book[b][t] = {}
        if s not in by_book[b][t]:
            by_book[b][t][s] = []
            
        item_entry = {
            'term': rec['term'],
            'paraphrase': rec['paraphrase'],
            'meaning': rec.get('meaning', ''),
            'raw': rec.get('raw', ''),
            'pdf': rec.get('pdf', ''),
            'sourcePath': rec['sourcePath'],
            'sourcePages': rec['sourcePages'],
            'needsReview': rec['needsReview'],
            'wordId': sha20(f"synonym-{rec['book']}-{rec.get('test', 1)}-{rec.get('skill', 'reading')}-{rec['term']}-{rec['paraphrase']}")
        }
        if rec.get('question'):
            item_entry['question'] = rec['question']
            q_key = f"c{b}-{t}-{s}-q{rec['question']}"
            if q_key not in by_question:
                by_question[q_key] = []
            by_question[q_key].append(item_entry)
            
        by_book[b][t][s].append(item_entry)
        
    structured_data = {
        "schemaVersion": 1,
        "totalCount": len(all_records),
        "uniqueVocabCount": len(word_entries),
        "byBook": by_book,
        "byQuestion": by_question
    }
    
    syn_file = synonyms_dir / "cambridge-synonyms.json"
    syn_file.write_text(json.dumps(structured_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Saved structured synonyms dataset: {syn_file.relative_to(WORKSPACE)}")
    review_queue = [{key: entry[key] for key in ('id', 'word', 'meaning', 'sourcePath', 'sourcePages', 'needsReview', 'sourceText')} for entry in word_entries if entry['needsReview']]
    (synonyms_dir / 'review-queue.json').write_text(json.dumps({'schemaVersion': 1, 'count': len(review_queue), 'items': review_queue}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Flagged {len(review_queue)} cards for source review; {sum(not rec.get('meaning') for rec in all_records)} raw records have no Chinese meaning.")
    
    # -------------------------------------------------------------
    # Enrich existing Cambridge questions with explanation.paraphrase
    # -------------------------------------------------------------
    enriched_count = 0
    cambridge_dir = WORKSPACE / "resources/cambridge"
    if cambridge_dir.is_dir():
        for q_key, syn_items in by_question.items():
            # q_key format: c14-test-1-listening-q1
            m = re.match(r'^c(\d+)-test-(\d+)-([a-z]+)-q(\d+)$', q_key)
            if not m:
                continue
            b_num, t_num, skill, q_num = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
            target_json = cambridge_dir / f"c{b_num}/test-{t_num}/{skill}.json"
            if not target_json.is_file():
                continue
                
            try:
                data = json.loads(target_json.read_text(encoding='utf-8'))
                modified = False
                
                # Find matching question
                questions_to_search = []
                if skill == 'listening':
                    for part in data.get('parts', []):
                        questions_to_search.extend(part.get('questions', []))
                elif skill == 'reading':
                    for passage in data.get('passages', []):
                        for group in passage.get('groups', []):
                            questions_to_search.extend(group.get('questions', []))
                            
                for q_obj in questions_to_search:
                    if q_obj.get('number') == q_num:
                        expl = q_obj.setdefault('explanation', {})
                        existing_para = expl.get('paraphrase', [])
                        if not isinstance(existing_para, list):
                            existing_para = []
                        sources = [{key: item[key] for key in ('term', 'paraphrase', 'meaning', 'sourcePath', 'sourcePages', 'needsReview', 'wordId')} for item in syn_items]
                        if expl.get('paraphraseSources') != sources:
                            expl['paraphraseSources'] = sources
                            modified = True
                        
                        for item in syn_items:
                            para_str = f"{item['term']} ⇋ {item['paraphrase']}"
                            if item.get('meaning'):
                                para_str += f" ({item['meaning']})"
                            if para_str not in existing_para:
                                existing_para.append(para_str)
                                modified = True
                                
                        if existing_para:
                            expl['paraphrase'] = existing_para
                            
                if modified:
                    target_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                    enriched_count += 1
            except Exception as e:
                print(f"Error enriching {target_json}: {e}")
                
    print(f"Enriched {enriched_count} test files with source-attributed synonym notes.")

if __name__ == '__main__':
    main()
