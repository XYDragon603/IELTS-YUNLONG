import test from 'node:test';
import assert from 'node:assert/strict';
import {saveClip,loadClips,deleteClip,CLIPS_KEY} from '../frontend/lib/listening-clips.js';
const memory=()=>{const map=new Map();return {getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v)};};
const input={testId:'c18-t1-listening',part:1,loop:{a:2,b:5},rate:.85,question:'2',note:'Listen for a contrast'};
test('clips preserve part identity, deduplicate the same range and delete only selected clip',()=>{
  const storage=memory(),first=saveClip(input,storage);
  assert.equal(saveClip({...input,note:'Updated'},storage).id,first.id);
  saveClip({...input,part:2,question:'12'},storage);
  assert.equal(loadClips(storage).length,2);
  deleteClip(first.id,storage);
  assert.equal(loadClips(storage)[0].part,2);
});
test('invalid ranges and out-of-part questions are rejected without changing records',()=>{
  const storage=memory();saveClip(input,storage);const raw=storage.getItem(CLIPS_KEY);
  for(const update of [{question:'12'},{loop:{a:4,b:3}},{rate:9},{testId:'javascript:evil'},{note:'x'.repeat(1001)}])assert.throws(()=>saveClip({...input,...update},storage));
  assert.equal(storage.getItem(CLIPS_KEY),raw);
  storage.setItem(CLIPS_KEY,'broken');assert.throws(()=>saveClip(input,storage));assert.equal(storage.getItem(CLIPS_KEY),'broken');
});
