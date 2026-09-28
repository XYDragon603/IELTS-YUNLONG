import test from 'node:test';
import assert from 'node:assert/strict';
import {listeningSummary} from '../lib/listening-summary.js';
import {resultsFor} from '../lib/study-model.js';
const paper={verified:false,parts:[{number:1,questions:[{id:'q1',accepted:['A']},{id:'q2',numbers:[2,3],type:'multiple',accepted:['B','C'],maxChoices:2}]}]};
test('submission summary counts multiple-choice points and finds partial answers',()=>{const summary=listeningSummary(paper,{answers:{q1:'A',q2:['B']},flags:['q2']});assert.deepEqual(summary,[{part:1,total:3,answered:2,missing:1,flagged:1,firstMissing:'q2'}]);});
test('unverified listening never produces definitive question scores',()=>{assert.ok(resultsFor(paper,{answers:{q1:'A'}}).every(q=>q.score===null));assert.equal(resultsFor({...paper,verified:true},{answers:{q1:'A'}})[0].score,1);});
