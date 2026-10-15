"""Replace three incomplete Speaking Part 2 screenshots from their original PDF pages."""

import hashlib
import json
import shutil
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / 'backups/speaking-image-recheck-2026-10-15'

# Bounding boxes are [top, left, bottom, right] fractions of the source page.
CORRECTIONS = {
    (13, 1): {
        'box': [.418, .07, .619, .65],
        'alt': 'Speaking Part 2：Describe someone you know who has started a business',
        'text': ('Describe someone you know who has started a business.\n'
                 'You should say:\n'
                 'who this person is\n'
                 'what work this person does\n'
                 'why this person decided to start a business\n'
                 'and explain whether you would like to do the same kind of work as this person.'),
    },
    (18, 2): {
        'box': [.405, .085, .625, .685],
        'alt': 'Speaking Part 2：Describe a tourist attraction in your country',
        'text': ('Describe a tourist attraction in your country that you would recommend.\n'
                 'You should say:\n'
                 'what the tourist attraction is\n'
                 'where in your country this tourist attraction is\n'
                 'what visitors can see and do at this tourist attraction\n'
                 'and explain why you would recommend this tourist attraction.'),
    },
    (20, 1): {
        'box': [.445, .04, .82, .96],
        'alt': 'Speaking Part 2：Describe a play or film you would see again with friends',
        'text': ('Describe a play or a film you have seen that you would like to see again with friends.\n'
                 'You should say:\n'
                 'what play or film you would like to go to see again\n'
                 'who you would go with\n'
                 'what other people have said about this play or film\n'
                 'and explain why you would like to see this play or film again with friends.'),
    },
}


def main():
    for (book, test), change in CORRECTIONS.items():
        file = ROOT / f'resources/cambridge/c{book}/test-{test}/speaking.json'
        data = json.loads(file.read_text(encoding='utf-8-sig'))
        part = next(p for p in data['parts'] if p['part'] == 2)
        card = part['cueCard']
        asset = card['asset']
        image = file.parent / asset['asset']
        for original in (file, image):
            backup = BACKUP / original.relative_to(ROOT)
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, backup)

        pdf = ROOT / data['sources']['paper']['path']
        actual = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if actual != data['sources']['paper']['sha256']:
            raise ValueError(f'Original PDF changed: {pdf}')
        top, left, bottom, right = change['box']
        with fitz.open(pdf) as doc:
            page = doc[asset['sourcePdfPage'] - 1]
            clip = fitz.Rect(page.rect.width * left, page.rect.height * top,
                             page.rect.width * right, page.rect.height * bottom)
            pixmap = page.get_pixmap(dpi=180, clip=clip, alpha=False)
            pixmap.save(image)

        asset.update(boundingBox=change['box'], width=pixmap.width, height=pixmap.height,
                     sha256=hashlib.sha256(image.read_bytes()).hexdigest(), alt=change['alt'])
        card['text'] = change['text']
        card['source']['boundingBox'] = change['box']
        part['source']['boundingBox'] = change['box']
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'C{book} T{test}: page {asset["sourcePdfPage"]}, {pixmap.width}x{pixmap.height}')

    # In these two imports Part 3 preceded the Part 2 card in the tab order.
    for book, test in ((13, 3), (13, 4)):
        file = ROOT / f'resources/cambridge/c{book}/test-{test}/speaking.json'
        data = json.loads(file.read_text(encoding='utf-8-sig'))
        if [part['part'] for part in data['parts']] == [1, 2, 3]:
            continue
        backup = BACKUP / file.relative_to(ROOT)
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, backup)
        data['parts'].sort(key=lambda part: part['part'])
        file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'C{book} T{test}: Part 1, Part 2, Part 3 order restored')


if __name__ == '__main__':
    main()
