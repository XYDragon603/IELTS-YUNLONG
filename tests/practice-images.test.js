import test from 'node:test';
import assert from 'node:assert/strict';
import {withCurrentPracticeImages} from '../frontend/lib/practice-images.js';

const asset=(name,page)=>({asset:`./assets/${name}.png`,sourcePdfPage:page,sha256:name});
const paper=(skill,sections)=>({book:20,test:1,skill,sources:{paper:{path:'IELTS/test1.pdf',sha256:'same-original'}},...sections});

test('a submitted writing snapshot displays the corrected chart and its continuation without changing the snapshot',()=>{
  const old=paper('writing',{tasks:[{id:'task-1',number:1,prompt:'Original prompt',assets:[asset('old-truncated-chart',23)]},{id:'task-2',number:2,prompt:'Original Task 2',assets:[]}]});
  const latest=paper('writing',{tasks:[{id:'task-1',number:1,prompt:'Changed current prompt',assets:[asset('complete-chart',23),asset('continuation',24)]},{id:'task-2',number:2,prompt:'Changed Task 2',assets:[]}]});
  const before=JSON.stringify(old);
  const result=withCurrentPracticeImages(old,latest);
  assert.equal(result.changed,true);
  assert.deepEqual(result.paper.tasks[0].assets.map(a=>a.sourcePdfPage),[23,24]);
  assert.equal(result.paper.tasks[0].prompt,'Original prompt');
  assert.equal(result.paper.tasks[1].prompt,'Original Task 2');
  assert.equal(JSON.stringify(old),before);
  assert.equal(latest.tasks[0].prompt,'Changed current prompt');
});

test('reading image repairs support multiple images and preserve the old questions and reference answers',()=>{
  const old=paper('reading',{passages:[{number:3,groups:[{id:'group-33-37',asset:asset('clipped',22),questions:[{id:'q33',number:33,prompt:'Old question',answer:{accepted:['A']}}]}]}]});
  const latest=structuredClone(old);
  const group=latest.passages[0].groups[0];delete group.asset;
  group.assets=[asset('body',22),asset('options',23)];group.questions[0].answer.accepted=['B'];
  const result=withCurrentPracticeImages(old,latest);
  assert.equal(result.changed,true);
  assert.equal(result.paper.passages[0].groups[0].asset,undefined);
  assert.equal(result.paper.passages[0].groups[0].assets.length,2);
  assert.deepEqual(result.paper.passages[0].groups[0].questions,old.passages[0].groups[0].questions);
});

test('a different original PDF or different test cannot replace saved images',()=>{
  const old=paper('writing',{tasks:[{id:'task-1',assets:[asset('old',23)]}]});
  for(const change of [{test:2},{book:19},{skill:'reading'},{sources:{paper:{path:'IELTS/test1.pdf',sha256:'different-original'}}},{sources:{paper:{path:'other.pdf',sha256:'same-original'}}}]){
    const latest={...structuredClone(old),...change};latest.tasks[0].assets=[asset('new',24)];
    const result=withCurrentPracticeImages(old,latest);
    assert.equal(result.changed,false);assert.equal(result.paper,old);
  }
});

test('failed latest loading and unchanged images keep the original paper object',()=>{
  const old=paper('writing',{tasks:[{id:'task-1',assets:[asset('same',23)]}]});
  assert.equal(withCurrentPracticeImages(old,undefined).paper,old);
  assert.deepEqual(withCurrentPracticeImages(old,structuredClone(old)),{paper:old,changed:false});
});
