import test from 'node:test';
import assert from 'node:assert/strict';
import { usableLayouts, layoutHTML, layoutBlanks } from '../frontend/lib/listening-layouts.js';

const part = { number: 1, questions: [1, 2, 3].map(n => ({ id: `q${n}`, number: n, numbers: [n], type: 'text' })) };
const table = { part: 1, kind: 'table', questionNumbers: [1, 2], columns: ['Name', 'Note'], rows: [[['The {{1}}'], ['<b>£{{2}}</b> per person', 'Quite expensive']]] };

test('layouts are used only when their blanks match their declared text questions', () => {
  assert.deepEqual(layoutBlanks(table), [1, 2]);
  assert.equal(usableLayouts([table], part).length, 1);
  assert.equal(usableLayouts([{ ...table, part: 2 }], part).length, 0);
  assert.equal(usableLayouts([{ ...table, questionNumbers: [1, 2, 3] }], part).length, 0);
  assert.equal(usableLayouts([{ ...table, rows: [[['{{1}} {{1}}'], ['{{2}}']]] }], part).length, 0);
  const choice = { ...part, questions: part.questions.map(q => q.number === 2 ? { ...q, type: 'single' } : q) };
  assert.equal(usableLayouts([table], choice).length, 0);
});

test('layout text is escaped and each blank becomes an answer input bound to its question', () => {
  const html = layoutHTML(table, part, { q2: '"30"' });
  assert.ok(html.includes('&lt;b&gt;£'));
  assert.ok(!html.includes('<b>'));
  assert.equal((html.match(/data-response="q\d"/g) || []).length, 2);
  assert.ok(html.includes('id="study-q-q1"'));
  assert.ok(html.includes('value="&quot;30&quot;"'));
  assert.ok(html.includes('Questions 1–2'));
  const notes = layoutHTML({ part: 1, kind: 'notes', questionNumbers: [1, 2, 3], title: 'Notes', lines: [{ text: 'Topic', heading: true }, { text: 'size: {{1}}', level: 1, bullet: true }, 'cost {{2}} and {{3}}'] }, part);
  assert.ok(notes.includes('class="is-heading"'));
  assert.ok(notes.includes('level-1 is-bullet'));
  assert.ok(!notes.includes('Questions 1–3'));
});

test('form layouts render label/value rows and section headings with their blanks', () => {
  const form = { part: 1, kind: 'form', questionNumbers: [1, 2], rows: ['Details', ['Name:', 'Sophie Bird'], ['Place:', ['the {{1}}', '{{2}} Street']]] };
  assert.deepEqual(layoutBlanks(form), [1, 2]);
  assert.equal(usableLayouts([form], part).length, 1);
  const html = layoutHTML(form, part);
  assert.ok(html.includes('class="form-heading"'));
  assert.ok(html.includes('<th scope="row"><div>Name:</div></th>'));
  assert.equal((html.match(/data-response=/g) || []).length, 2);
});
