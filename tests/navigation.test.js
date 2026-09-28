import test from 'node:test';
import assert from 'node:assert/strict';
import {shell} from '../ui/layout.js';

test('main navigation highlights the route being shown',()=>{
 const oldDocument=globalThis.document;
 let html='';
 globalThis.document={querySelector:()=>({set innerHTML(value){html=value;}})};
 try{
  for(const [page,href] of [['home','/#home'],['library','/#library'],['history','/#history'],['review','/review.html'],['explanation','/#library']]){
   shell('<p>Content</p>',page);
   const current=[...html.matchAll(/<a\b[^>]*aria-current="page"[^>]*>/g)].map(match=>match[0]);
   assert.equal(current.length,1,`Expected one active menu item for ${page}`);
   assert.ok(current[0].includes(`href="${href}"`),`Wrong active menu item for ${page}`);
  }
 }finally{globalThis.document=oldDocument;}
});
