import test from 'node:test';
import assert from 'node:assert/strict';
import {exactReadingExcerpt,renderSynonymNotes,saveSynonymWord} from '../lib/synonym-notes.js';

test('reading excerpt is shown only when a phrase uniquely matches source text',()=>{
  const blocks=[{text:'The shell surrounds the fruit and protects it.',source:{pdfPage:10}}];
  assert.match(exactReadingExcerpt(blocks,'surrounds').text,/surrounds/);
  assert.equal(exactReadingExcerpt([...blocks,...blocks],'surrounds'),null);
  assert.equal(exactReadingExcerpt(blocks,'surrounds = covers'),null);
  assert.equal(exactReadingExcerpt(blocks,'missing'),null);
});

test('synonym notes preserve attribution and escape imported PDF text',()=>{
  const html=renderSynonymNotes([{term:'<term>',paraphrase:'another & phrase',meaning:'',sourcePath:'IELTS/book.pdf',sourcePages:[7],needsReview:['long-extraction'],wordId:'a'.repeat(20)}]);
  assert.match(html, /&lt;term&gt;/);
  assert.match(html, /another &amp; phrase/);
  assert.match(html, /book.pdf#page=7/);
  assert.match(html, /中文释义尚未提供/);
  assert.match(html, /资料待校对/);
  assert.doesNotMatch(renderSynonymNotes([{term:'x',paraphrase:'y',sourcePath:'IELTS/../bad.pdf',sourcePages:[1]}]), /href=/);
});

test('saving a synonym preserves existing vocabulary progress and protects invalid storage',()=>{
  let data=JSON.stringify({version:1,progress:{old:{starred:true},["a".repeat(20)]:{reviews:3}},limit:20});
  const storage={getItem:()=>data,setItem:(_,value)=>{data=value;}};
  saveSynonymWord('a'.repeat(20),storage);
  const state=JSON.parse(data);
  assert.equal(state.progress.old.starred,true);
  assert.deepEqual(state.progress['a'.repeat(20)],{reviews:3,starred:true});
  const before=data;
  assert.throws(()=>saveSynonymWord('../bad',storage));
  assert.equal(data,before);
  assert.throws(()=>saveSynonymWord('b'.repeat(20),{getItem:()=>'{',setItem:()=>assert.fail('must not overwrite')}));
});
