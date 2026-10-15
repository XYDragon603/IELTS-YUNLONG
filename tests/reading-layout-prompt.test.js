import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {layoutPrompt} from '../frontend/lib/listening-layouts.js';

test('every Cambridge 13–20 inline blank has a usable review excerpt',()=>{
  let checked=0;
  for(let book=13;book<=20;book++)for(let paper=1;paper<=4;paper++){
    const path=join('resources','cambridge',`c${book}`,`test-${paper}`,'reading-layouts.json');
    const layouts=JSON.parse(readFileSync(path,'utf8')).layouts;
    for(const layout of layouts)for(const number of layout.questionNumbers){
      const prompt=layoutPrompt(layout,number);
      assert.ok(prompt?.includes(`【${number}】____`),`C${book} T${paper} Q${number}`);
      assert.equal(prompt.includes('{{'),false,`C${book} T${paper} Q${number}`);
      assert.ok(prompt.length<=200,`C${book} T${paper} Q${number}: ${prompt.length}`);
      checked++;
    }
  }
  assert.equal(checked,491);
});
