import test from 'node:test';
import assert from 'node:assert/strict';
import {submissionRows} from '../lib/practice-submit.js';
test('reading check deduplicates records and prioritizes missing answers',()=>{const q={id:'q1'},paper={passages:[{groups:[{questions:[q,q,{id:'q2'}]}]}]};const [row]=submissionRows('reading',paper,{answers:{q1:'yes'},flags:['q1']});assert.equal(row.target,'q2');assert.match(row.detail,/1 \/ 2/);});
test('writing distinguishes empty and short responses using each task limit',()=>{const rows=submissionRows('writing',{tasks:[{id:'a',minimumWords:150},{id:'b',minimumWords:250}]},{answers:{b:'One short response'}});assert.match(rows[0].detail,/尚未作答/);assert.match(rows[1].detail,/3 词.*250.*字数不足/);});
