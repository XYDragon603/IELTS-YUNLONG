import test from 'node:test';
import assert from 'node:assert/strict';
import { createAttempt, secondsLeft, grade, wordCount, escapeHTML, formatTime } from '../frontend/core.js';
import { listeningQuestions, readingQuestions } from '../frontend/data.js';

test('full and single practice allocate the correct countdown', () => {
  const full = createAttempt(null, 1000);
  assert.deepEqual(full.sections, ['listening', 'reading', 'writing', 'speaking']);
  assert.equal(secondsLeft(full, 61000), 240);
  assert.equal(secondsLeft(full, 999999), 0);
  assert.equal(secondsLeft({ ...full, paused: true, remaining: 123 }, 999999), 123);
  assert.equal(secondsLeft(createAttempt('writing', 1000), 1000), 600);
  assert.throws(() => createAttempt('bad'));
});

test('grading handles whitespace, case, numeric variants, and unanswered questions', () => {
  const result = grade(listeningQuestions, { l1: '  monday ', l2: 'fifteen', l3: 'CARTER', l4: '80', l5: '' });
  assert.equal(result.filter(q => q.correct).length, 4);
  assert.equal(result[4].correct, false);
  assert.equal(grade(readingQuestions, { r1: 'true', r2: 'FALSE', r3: 'FALSE', r4: 'FALSE', r5: 'not   given' }).filter(q => q.correct).length, 5);
});

test('word counter handles contractions and excludes punctuation and Chinese-only notes', () => {
  assert.equal(wordCount("It's a well-known idea, isn't it?"), 6);
  assert.equal(wordCount('  \n 中文说明 ... '), 0);
  assert.equal(wordCount('One\ntwo\tthree'), 3);
});

test('user content is escaped and countdown has stable formatting', () => {
  assert.equal(escapeHTML('<script>"&\'</script>'), '&lt;script&gt;&quot;&amp;&#39;&lt;/script&gt;');
  assert.equal(formatTime(300), '05:00');
  assert.equal(formatTime(0), '00:00');
});
