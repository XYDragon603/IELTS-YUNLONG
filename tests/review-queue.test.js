import test from 'node:test';
import assert from 'node:assert/strict';
import {REVIEW_KEY,addReviewItem,createReadingReviewItem,createListeningReviewItem,loadReviewQueue,retryReviewItem,setReviewStatus} from '../frontend/lib/review-queue.js';

const memory=()=>{const data=new Map();return {getItem:key=>data.get(key)||null,setItem:(key,value)=>data.set(key,value),raw:()=>data.get(REVIEW_KEY)};};

test('unverified imported questions remain unscored when retried and duplicates keep progress',()=>{
  const store=memory();
  const item={id:'c15-t1-reading-q2',sourceVerified:false,accepted:['A'],prompt:'Question 2'};
  assert.equal(addReviewItem(item,store,100).added,true);
  assert.equal(addReviewItem(item,store,200).added,false);
  const result=retryReviewItem(item.id,'A',store,1000);
  assert.equal(result.attempts[0].match,null);
  assert.equal(result.status,'reviewing');
  assert.equal(loadReviewQueue(store).items.length,1);
  assert.equal(setReviewStatus(item.id,'mastered',store,2000).status,'mastered');
  assert.throws(()=>retryReviewItem(item.id,'',store,3000));
  assert.equal(loadReviewQueue(store).items[0].attempts.length,1);
});

test('verified answers score only after retry and corrupt queues are never overwritten',()=>{
  const store=memory(),id='c14-t1-listening-q1';
  addReviewItem({id,sourceVerified:true,accepted:['ABC']},store,0);
  assert.equal(retryReviewItem(id,'abc',store,10).status,'mastered');
  assert.equal(retryReviewItem(id,'xyz',store,20).attempts.at(-1).match,false);
  const multi='c14-t1-listening-q14';
  addReviewItem({id:multi,sourceVerified:true,accepted:['B','E'],multiple:true},store,0);
  assert.equal(retryReviewItem(multi,'E, B',store,30).attempts.at(-1).match,true);
  assert.equal(retryReviewItem(multi,'B, B',store,40).attempts.at(-1).match,false);
  const bad={getItem:()=>'{broken',setItem:()=>assert.fail('must preserve raw data')};
  assert.throws(()=>addReviewItem({id:'c14-t1-listening-q2'},bad));
});

test('reading review evidence requires exact source match; listening keeps audio and transcript evidence',()=>{
  const paper={book:15,test:1,verified:false,sources:{paper:{path:'IELTS/paper.pdf'}}};
  const q={id:'q2',number:2,prompt:'Which shell?',source:{pdfPage:8},answer:{accepted:['A']},explanation:{paraphraseSources:[{term:'encased',paraphrase:'surrounds'}]}};
  const group={context:'Choose one answer',options:[{value:'A',label:'shell'}]};
  const passage={blocks:[{text:'The shell surrounds the fruit.',source:{pdfPage:8}}]};
  const item=createReadingReviewItem(paper,q,group,passage,'B');
  assert.equal(item.evidence.length,1);
  assert.equal(item.sourceVerified,false);
  assert.equal(item.latestGiven,'B');
  const noisy=createReadingReviewItem(paper,{...q,prompt:'© '+q.prompt.repeat(90)},group,passage,'B');
  assert.match(noisy.prompt,/OCR 待核对/);
  assert.match(noisy.rawPrompt,/Which shell/);
  const layout={kind:'notes',lines:[{text:'The {{1}} surrounds the fruit.'},{text:'The {{2}} is used for nutmeg.'}]};
  const fromLayout=createReadingReviewItem(paper,{...q,id:'q1',number:1,prompt:null},group,passage,'',layout);
  assert.equal(fromLayout.prompt,'The 【1】____ surrounds the fruit.');
  const listening=createListeningReviewItem({book:14,test:1,verified:false,sources:paper.sources,audio:{1:{path:'IELTS/audio.mp3'}}},{id:'q1',numbers:[1],prompt:'Name?',accepted:['John'],evidence:[{text:'John said hello',sourcePdfPage:90}]},{number:1,instruction:'Write one word'},'Jack');
  assert.equal(listening.audioPath,'IELTS/audio.mp3');
  assert.equal(listening.evidence[0].sourcePdfPage,90);
});
