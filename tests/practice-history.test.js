import test from 'node:test';
import assert from 'node:assert/strict';
import { identifyPractice, newPractice, archivePractice, historyEntries } from '../frontend/lib/practice-history.js';
const memory=()=>{const values=new Map();return {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v)};};
test('redo isolates answers, flags and recordings while preserving a submitted snapshot',()=>{
 const store=memory(),key='test';const old=newPractice('reading',key);old.answers.q1='yes';old.submitted='2026-09-23T00:00:00Z';
 const paper={skill:'reading',verified:false,passages:[{groups:[{questions:[{id:'q1',number:1,answer:{accepted:['yes']}}]}]}]};
 archivePractice(key,old,paper,store);archivePractice(key,old,paper,store);
 old.answers.q1='no';paper.passages[0].groups[0].questions[0].answer.accepted=['no'];
 const entries=historyEntries(key,store);assert.equal(entries.length,1);assert.equal(entries[0].session.answers.q1,'yes');assert.equal(entries[0].readingResults[0].correct,true);
 const next=newPractice('reading',key);assert.notEqual(next.attemptId,old.attemptId);assert.notEqual(next.recordingNamespace,old.recordingNamespace);assert.deepEqual(next.answers,{});assert.equal(next.remaining,3600);
});
test('legacy sessions keep access to old recording keys and corrupt histories are not overwritten',()=>{
 const s=identifyPractice({skill:'speaking',answers:{}},'old-key');assert.equal(s.recordingNamespace,'old-key');assert.equal(identifyPractice(s,'old-key').attemptId,s.attemptId);
 const bad={getItem:()=>'{broken',setItem:()=>assert.fail('must not overwrite')};
 assert.throws(()=>archivePractice('test',{...s,submitted:'date'},{skill:'speaking'},bad));
 const full={getItem:()=>null,setItem:()=>{throw new Error('quota');}};assert.throws(()=>archivePractice('test',{...s,submitted:'date'},{skill:'speaking'},full),/quota/);
});
