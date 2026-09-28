import test from 'node:test';
import assert from 'node:assert/strict';
import {publicPathAllowed} from '../lib/public-path.js';

test('website serves only its pages and required assets',()=>{
 for(const pathname of ['/','/mock.html','/features/mock.js','/lib/imported-listening.js','/resources/cambridge/c18/test-1/listening.json','/resources/cambridge/c18/test-1/assets/chart.png','/IELTS/剑桥雅思真题18.pdf','/IELTS/18-1-1.mp3'])assert.equal(publicPathAllowed(pathname),true,pathname);
 for(const pathname of ['/scripts/export-review-items.mjs','/artifacts/pending-review-items.csv','/docs/DATA_AGENT_HANDOFF.md','/WORD/words.docx','/package.json','/IELTS/archive.zip','/resources/secret.md'])assert.equal(publicPathAllowed(pathname),false,pathname);
});
