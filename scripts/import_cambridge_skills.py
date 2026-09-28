"""Local, resumable page-map extraction and conservative skill parsing.

No LLM calls. Full page OCR stays in .cache. Original PDFs are read-only.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import fitz
from cambridge_pdf_importer import usable_text_layer
from ocr_extractor import compute_sha256, extract_page_ocr, get_tesseract_cmd

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'skills-v1-240dpi'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def native_page(page):
    lines = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            text = ''.join(s['text'] for s in line['spans']).strip()
            if not text:
                continue
            x0,y0,x1,y1 = line['bbox']
            lines.append({'text': text, 'boundingBox': [y0/page.rect.height,x0/page.rect.width,y1/page.rect.height,x1/page.rect.width], 'confidence': None})
    return {'pdfPage': page.number+1, 'printedPage': None, 'method': 'text-layer', 'confidence': None,
            'rawText': '\n'.join(l['text'] for l in lines), 'lines': lines}


def extract_pages(doc, pages, cache_dir, source_hash):
    result = []
    for number in pages:
        if not 1 <= number <= len(doc):
            raise ValueError(f'PDF page outside source: {number}')
        target = cache_dir / f'page-{number:04}.json'
        record = json.loads(target.read_text(encoding='utf-8')) if target.exists() else None
        hit = bool(record and record.get('sourcePdfSha256') == source_hash and record.get('extractorVersion') == VERSION)
        if not hit:
            page = doc[number-1]
            record = native_page(page) if usable_text_layer(page.get_text()) else extract_page_ocr(doc,number-1,get_tesseract_cmd(),dpi=240)
            record.update(sourcePdfSha256=source_hash, extractorVersion=VERSION)
            write_json(target,record)
        for index,line in enumerate(record['lines']):
            line['id'] = f'p{number}-l{index+1}'
        result.append(record)
        print(f'page={number} method={record["method"]} cache={"hit" if hit else "miss"}',flush=True)
    return result


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--page-map',type=Path,default=ROOT/'resources/page-maps/cambridge-18.json')
    cli.add_argument('--test',type=int,default=1)
    cli.add_argument('--skill',choices=['reading','writing','speaking'],required=True)
    cli.add_argument('--extract-only',action='store_true')
    cli.add_argument('--answer-page',type=int)
    args=cli.parse_args()
    mapping=json.loads(args.page_map.read_text(encoding='utf-8'))
    section=mapping['tests'][str(args.test)][args.skill]
    source=mapping['source']
    if source.get('type') == 'per-test-pdfs':
        source = source['tests'][str(args.test)]
    pdf=ROOT/source['path']
    digest=compute_sha256(pdf)
    if digest != source['sha256']:
        raise ValueError('Source PDF hash differs from page map')
    fingerprint = source.get('fingerprint') or digest[:16]
    directory=ROOT/'.cache/cambridge-importer'/fingerprint/VERSION
    with fitz.open(pdf) as doc:
        pages=extract_pages(doc,range(section['pdfStartPage'],section['pdfEndPage']+1),directory,digest)
        cache=directory/f'test-{args.test}-{args.skill}.json'
        payload={'book':mapping['book'],'test':args.test,'skill':args.skill,'source':source,'pages':pages}
        write_json(cache,payload)
        if args.answer_page:
            answer_pages=extract_pages(doc,[args.answer_page],directory,digest)
            write_json(directory/f'test-{args.test}-{args.skill}-answers.json',{'source':source,'pages':answer_pages})
        if not args.extract_only:
            from skill_parsers import import_skill
            output=ROOT/f'resources/cambridge/c{mapping["book"]}/test-{args.test}'
            result=import_skill(payload,doc,output,cache,args.answer_page,directory)
            result['sources']['extraction']={'path':cache.relative_to(ROOT).as_posix(),'sha256':compute_sha256(cache)}
            write_json(output/f'{args.skill}.json',result)
            print(json.dumps({'skill':args.skill,'status':result['status'],'needsReview':len(result['needsReview'])}))
    if compute_sha256(pdf)!=digest:
        raise RuntimeError('Source changed during extraction')


if __name__=='__main__':
    main()
