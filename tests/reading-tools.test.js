import test from 'node:test';
import assert from 'node:assert/strict';
import { highlightHTML } from '../frontend/lib/reading-tools.js';
test('highlights merge overlaps and always escape source text',()=>{
 const text='<script>abc</script>';
 assert.equal(highlightHTML(text,[{text,start:0,end:2},{text,start:1,end:8}]),'<mark>&lt;script&gt;</mark>abc&lt;/script&gt;');
});
test('updated source or invalid offsets cannot apply stale highlights',()=>{
 assert.equal(highlightHTML('new text',[{text:'old text',start:0,end:3}]),'new text');
 assert.equal(highlightHTML('abc',[{text:'abc',start:-1,end:2},{text:'abc',start:0,end:8}]),'abc');
});
