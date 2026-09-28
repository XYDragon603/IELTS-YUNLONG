import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { adaptImportedListening, localResourceURL } from '../lib/imported-listening.js';
import { questionScore, questionWeight, answeredWeight } from '../lib/study-model.js';
const load = name => JSON.parse(readFileSync(new URL(`../resources/cambridge/c18/test-1/${name}.json`,import.meta.url)));
test('import adapter preserves 40 points without duplicate multiple-choice controls', () => {
  const adapted=adaptImportedListening(load('listening'),load('audioscript'));
  const qs=adapted.parts.flatMap(p=>p.questions);
  assert.equal(qs.length,37);
  assert.equal(qs.reduce((n,q)=>n+questionWeight(q),0),40);
  assert.equal(qs.reduce((n,q)=>n+questionScore(q,q.type==='multiple'?q.accepted:q.accepted[0]),0),40);
  assert.equal(qs.reduce((n,q)=>n+answeredWeight(q,q.type==='multiple'?q.accepted:q.accepted[0]),0),40);
  const multiple=qs.find(q=>q.type==='multiple');
  assert.equal(questionScore(multiple,[multiple.accepted[0],multiple.accepted[0]]),1);
  assert.equal(questionScore(multiple,[...multiple.accepted].reverse()),2);
});
test('adapter rejects missing points and resource traversal', () => {
  const data=load('listening'); data.parts[0].questions.pop();
  assert.throws(()=>adaptImportedListening(data,load('audioscript')));
  assert.throws(()=>localResourceURL('IELTS/../secret'));
  assert.equal(localResourceURL('IELTS/a b.mp3'),'/IELTS/a%20b.mp3');
});
