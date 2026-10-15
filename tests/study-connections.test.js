import test from 'node:test';
import assert from 'node:assert/strict';
import {personalBook,savePersonalWord} from '../frontend/lib/personal-words.js';
import {validLoop,precisionTools} from '../frontend/lib/listening-tools.js';
import {audioPlayer} from '../frontend/ui/audio-player.js';
test('personal words deduplicate with stable dictionary ID and retain entered meaning',async()=>{const map=new Map(),storage={getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v)};const first=await savePersonalWord({word:'Abandon',meaning:'放弃',context:'example'},storage);await savePersonalWord({word:'abandon',meaning:'',context:'new'},storage);assert.equal(personalBook(storage).words.length,1);assert.equal(personalBook(storage).words[0].meaning,'放弃');assert.match(first.id,/^[a-f0-9]{20}$/);await assert.rejects(()=>savePersonalWord({word:'<script>'},storage));});
test('loop bounds are valid and mock mode omits learning controls',()=>{assert.ok(validLoop({a:1,b:2},10));assert.ok(!validLoop({a:2,b:1},10));assert.ok(!validLoop({a:0,b:20},10));assert.match(precisionTools(),/listening-rate/);assert.doesNotMatch(audioPlayer('/a.mp3','mock'),/loop-a/);assert.match(audioPlayer('/a.mp3','study'),/loop-a/);});
