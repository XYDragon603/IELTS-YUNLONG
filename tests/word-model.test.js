import test from 'node:test';
import assert from 'node:assert/strict';
import {rateWord,studyQueue,DAY} from '../frontend/lib/word-model.js';
import {spellingMatches,recordWordError} from '../frontend/lib/word-model.js';
test('spelling preserves punctuation distinctions and errors retain existing progress',()=>{assert.equal(spellingMatches('  New   York ','new york'),true);assert.equal(spellingMatches('landlord','landlord / landlady'),false);const p=recordWordError({starred:true,stage:3},123);assert.equal(p.needsPractice,true);assert.equal(p.starred,true);assert.equal(p.stage,3);assert.equal(recordWordError(p).mistakes,2);});
test('larger and custom groups are not capped at 100',()=>{const words=Array.from({length:1200},(_,i)=>({id:String(i)}));for(const limit of [200,300,500,125,1000])assert.equal(studyQueue(words,{}, {limit}).length,limit);assert.equal(studyQueue(words,{}, {limit:2000}).length,1000);assert.equal(studyQueue(words.slice(0,3),{}, {limit:500}).length,3);});
test('ratings preserve favorites and schedule distinct review intervals',()=>{const p=rateWord({starred:true},'known',100);assert.equal(p.due,100+DAY);assert.equal(p.starred,true);assert.equal(rateWord(p,'again',100).due,600100);assert.equal(rateWord(p,'known',100).due,100+3*DAY);});
test('queue separates new, due and future words without modifying source',()=>{const words=[{id:'a'},{id:'b'},{id:'c'}],p={b:{reviews:1,due:5},c:{reviews:1,due:20}};assert.deepEqual(studyQueue(words,p,{now:10}),['a']);assert.deepEqual(studyQueue(words,p,{review:true,now:10}),['b']);assert.equal(words[0].id,'a');});
