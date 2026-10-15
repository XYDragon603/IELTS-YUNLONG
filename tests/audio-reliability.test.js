import test from 'node:test';
import assert from 'node:assert/strict';
import { byteRange } from '../backend/lib/http-range.js';
import { getListeningTest } from '../frontend/lib/cambridge.js';
import { resultsFor } from '../frontend/lib/study-model.js';

test('media ranges support seeking, open ends, suffixes and invalid bounds',()=>{
  assert.deepEqual(byteRange('bytes=20-39',100),{start:20,end:39});
  assert.deepEqual(byteRange('bytes=80-',100),{start:80,end:99});
  assert.deepEqual(byteRange('bytes=-10',100),{start:90,end:99});
  assert.deepEqual(byteRange('bytes=90-200',100),{start:90,end:99});
  for(const range of ['bytes=100-','bytes=30-20','bytes=-0'])assert.equal(byteRange(range,100),false);
  assert.equal(byteRange('bytes=0-',0),false);
  assert.equal(byteRange('bytes=0-1,3-4',100),null);
  assert.equal(byteRange(undefined,100),null);
});
test('legacy listening never inherits verification from its old fixture flag',()=>{
  const paper=getListeningTest('c18-t1-listening');
  assert.equal(paper.verified,false);
  assert.equal(paper.verification.audio,'content-not-reviewed');
  assert.ok(resultsFor(paper,{answers:{q1:'DW30 7YZ'}}).every(q=>q.score===null));
  assert.equal(paper.parts.length,4);
});
