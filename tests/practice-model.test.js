import test from 'node:test';
import assert from 'node:assert/strict';
import { readingReport, practiceRemaining, pausePractice, loadPractice, assetURL } from '../lib/practice-model.js';
test('unknown reading answers are not marked incorrect and duplicates do not add points',()=>{
 const data={passages:[{groups:[{questions:[{id:'q1',number:1,answer:{accepted:['TRUE']}},{id:'q2',number:2,answer:{accepted:null}},{id:'q1',number:1,answer:{accepted:['TRUE']}}]}]}]};
 const results=readingReport(data,{q1:' true '});assert.equal(results.length,2);assert.equal(results[0].correct,true);assert.equal(results[1].correct,null);
});
test('timer pause retains exact remaining time and expires at zero',()=>{
 const s={remaining:3600,deadline:11000};assert.equal(practiceRemaining(s,2000),9);pausePractice(s,2000);assert.equal(s.deadline,null);assert.equal(practiceRemaining(s,90000),9);assert.equal(practiceRemaining({deadline:1000},2000),0);
});
test('corrupt or mismatched saved state falls back without erasing other keys',()=>{
 assert.equal(loadPractice('x','writing',{getItem:()=>'{broken'}).remaining,3600);
 assert.equal(loadPractice('x','reading',{getItem:()=>JSON.stringify({version:1,skill:'writing'})}).skill,'reading');
 assert.throws(()=>assetURL('/resources/','../../secret'));assert.throws(()=>assetURL('/resources/','https://example.com/a.png'));
 assert.equal(assetURL('/resources/','./assets/chart.png'),'/resources/assets/chart.png');
});
