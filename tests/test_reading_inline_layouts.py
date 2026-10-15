"""Structural regression checks for Cambridge 13–20 inline reading groups."""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'resources' / 'cambridge'
COMPLETION = {'notes-completion', 'summary-completion', 'table-completion',
              'sentence-completion', 'flow-chart-completion'}


class ReadingInlineLayoutsTest(unittest.TestCase):
    @staticmethod
    def layout_text(layout):
        def flatten(value):
            if isinstance(value, str):
                return [value]
            if isinstance(value, list):
                return [text for item in value for text in flatten(item)]
            return [value['text']] if isinstance(value, dict) and 'text' in value else []
        fields = ['columns', 'rows'] if layout['kind'] == 'table' else ['steps'] if layout['kind'] == 'flow-chart' else ['rows'] if layout['kind'] == 'form' else ['lines']
        return '\n'.join(text for field in fields for text in flatten(layout.get(field, [])))

    def test_every_completion_group_has_one_numbered_inline_blank(self):
        for book in range(13, 21):
            for test in range(1, 5):
                folder = ROOT / f'c{book}' / f'test-{test}'
                reading = json.loads((folder / 'reading.json').read_text(encoding='utf-8'))
                layouts_path = folder / 'reading-layouts.json'
                layouts = json.loads(layouts_path.read_text(encoding='utf-8'))
                self.assertEqual(layouts['source']['sha256'], reading['sources']['paper']['sha256'])
                groups = {tuple(q['number'] for q in group['questions']): group
                          for passage in reading['passages'] for group in passage['groups']}
                seen = set()
                for layout in layouts['layouts']:
                    numbers = tuple(layout['questionNumbers'])
                    with self.subTest(book=book, test=test, numbers=numbers):
                        self.assertNotIn(numbers, seen)
                        self.assertIn(numbers, groups)
                        text = self.layout_text(layout)
                        tokens = [int(n) for n in re.findall(r'\{\{(\d+)\}\}', text)]
                        self.assertEqual(sorted(tokens), sorted(numbers))
                        self.assertNotRegex(text, r'[\ufffd\x07]')
                        self.assertEqual(layout['review']['method'], 'assistant-visual')
                        if 'options' in layout:
                            self.assertEqual(len({o['value'] for o in layout['options']}),
                                             len(layout['options']))
                    seen.add(numbers)
                for numbers, group in groups.items():
                    with self.subTest(book=book, test=test, classified=numbers):
                        self.assertNotEqual(group['type'], 'unclassified')
                    if group['type'] in COMPLETION:
                        with self.subTest(book=book, test=test, completion=numbers):
                            self.assertIn(numbers, seen)
                    if group['type'] in {'matching-information', 'matching-features',
                                         'matching-sentence-endings'}:
                        with self.subTest(book=book, test=test, choices=numbers):
                            self.assertTrue(group.get('options') or all(
                                question.get('options') for question in group['questions']))
                    if group['type'] == 'matching-headings':
                        with self.subTest(book=book, test=test, headings=numbers):
                            self.assertGreaterEqual(len(group.get('options', [])), len(numbers))
                            self.assertEqual([q['prompt'] for q in group['questions']], [
                                f'{"Section" if "sections" in group["context"] else "Paragraph"} '
                                f'{chr(ord("A") + index)}'
                                for index in range(len(numbers))])

    def test_corrected_multi_select_is_not_a_sentence_completion(self):
        reading = json.loads((ROOT / 'c20' / 'test-3' / 'reading.json').read_text(encoding='utf-8'))
        group = next(group for passage in reading['passages'] for group in passage['groups']
                     if group['questionRange'] == [22, 23])
        self.assertEqual(group['type'], 'multiple-choice')
        self.assertEqual([o['value'] for o in group['options']], list('ABCDE'))

    def test_bentham_summary_keeps_five_blanks_and_word_bank(self):
        folder = ROOT / 'c13' / 'test-4'
        reading = json.loads((folder / 'reading.json').read_text(encoding='utf-8'))
        layouts = json.loads((folder / 'reading-layouts.json').read_text(encoding='utf-8'))['layouts']
        group = next(group for passage in reading['passages'] for group in passage['groups']
                     if group['questionRange'] == [30, 34])
        layout = next(layout for layout in layouts if layout['questionNumbers'] == list(range(30, 35)))
        self.assertEqual(group['type'], 'summary-completion')
        self.assertEqual([o['value'] for o in group['options']], list('ABCDEFG'))
        self.assertEqual(sorted(int(n) for n in re.findall(r'\{\{(\d+)\}\}',
                                                    self.layout_text(layout))), list(range(30, 35)))

    def test_two_letter_questions_keep_complete_shared_prompt(self):
        reading = json.loads((ROOT / 'c20' / 'test-2' / 'reading.json').read_text(encoding='utf-8'))
        group = next(group for passage in reading['passages'] for group in passage['groups']
                     if group['questionRange'] == [23, 24])
        self.assertEqual(group['questions'][0]['prompt'], group['questions'][1]['prompt'])


if __name__ == '__main__':
    unittest.main()
