import test from 'node:test';
import assert from 'node:assert/strict';
import {createMockRun,mockProgress,mockPaperOptions,practiceRunKey,listeningRunKey,requireMockStage,MOCK_KEY} from '../frontend/lib/mock-run.js';

function memoryStorage(){const map=new Map();return {getItem:key=>map.get(key)||null,setItem:(key,value)=>map.set(key,value)};}

test('only complete four-skill papers are selectable',()=>{
 const complete=['listening','reading','writing','speaking'].map(skill=>({book:20,test:4,skill,available:true,status:'needs-review'}));
 const missing=[{book:4,test:1,skill:'reading',available:false,status:'not-imported'}];
 const papers=mockPaperOptions([...complete,...missing]);
 assert.equal(papers.length,2);
 assert.equal(papers[0].available,true);
 assert.equal(papers[0].verified,false);
 assert.equal(papers[1].available,false);
});

test('imported listening unlocks the following stages and isolates each run',()=>{
 const storage=memoryStorage();
 const run=createMockRun(storage,{book:20,test:4});
 const second=createMockRun(storage,{book:20,test:4});
 assert.equal(JSON.parse(storage.getItem(MOCK_KEY)).length,2);
 assert.match(mockProgress(run,storage)[0].href,/import-preview\.html\?book=20&test=4&mockRun=/);
 assert.notEqual(listeningRunKey(run),listeningRunKey(second));
 assert.throws(()=>requireMockStage(run.id,'reading',storage));
 storage.setItem(listeningRunKey(run),JSON.stringify({answers:{},submitted:true}));
 assert.equal(requireMockStage(run.id,'reading',storage).id,run.id);
 assert.throws(()=>requireMockStage(second.id,'reading',storage));
 storage.setItem(practiceRunKey(run,'reading'),JSON.stringify({submitted:true}));
 assert.equal(requireMockStage(run.id,'writing',storage).id,run.id);
 assert.throws(()=>requireMockStage(run.id,'speaking',storage));
});

test('older runs retain their existing listening route',()=>{
 const storage=memoryStorage();
 const run={id:'old',book:18,test:1};
 storage.setItem(MOCK_KEY,JSON.stringify([run]));
 assert.equal(mockProgress(run,storage)[0].href,'/#mock-listening/old');
 storage.setItem('ielts-study-v1',JSON.stringify({sessions:[{id:'s1',mockRun:'old',finished:123}]}));
 assert.equal(requireMockStage('old','reading',storage).id,'old');
});
