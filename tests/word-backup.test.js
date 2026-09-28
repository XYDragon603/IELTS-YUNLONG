import test from 'node:test';
import assert from 'node:assert/strict';
import {parseWordBackup,replaceWordBackup} from '../lib/word-backup.js';
const id='a'.repeat(20),data={version:1,progress:{[id]:{reviews:3,starred:true,needsPractice:true,stage:2}},limit:125,random:true,session:{book:'ielts-1',ids:[id],index:0,mode:'dictation'}};
test('backup round trip retains progress and session',()=>{const restored=parseWordBackup(JSON.stringify(data));assert.deepEqual(restored.progress,data.progress);assert.equal(restored.session.mode,'dictation');assert.equal(restored.limit,125);});
test('malformed imports and duplicate queues are rejected',()=>{for(const invalid of [{...data,limit:0},{...data,progress:{__bad:{}}},{...data,session:{...data.session,ids:[id,id]}},{...data,progress:{[id]:{reviews:-1}}}])assert.throws(()=>parseWordBackup(JSON.stringify(invalid)));});
test('backup write failure leaves old progress untouched',()=>{let wrote=false;const storage={getItem:()=>'{old}',setItem:(key)=>{if(key.endsWith('before-import'))throw Error('quota');wrote=true;}};assert.throws(()=>replaceWordBackup(storage,'key',data));assert.equal(wrote,false);});
test('successful replacement preserves original raw backup',()=>{const map=new Map([['key','original']]);replaceWordBackup({getItem:k=>map.get(k),setItem:(k,v)=>map.set(k,v)},'key',data);assert.equal(map.get('key-before-import'),'original');assert.deepEqual(JSON.parse(map.get('key')),data);});
