import {savePersonalWord} from './personal-words.js';
import { escapeHTML as esc } from '../core.js';

export function highlightHTML(text,marks=[]){
  text=String(text||'');
  const ranges=marks.filter(m=>m.text===text&&Number.isInteger(m.start)&&Number.isInteger(m.end)&&m.start>=0&&m.end<=text.length&&m.start<m.end).sort((a,b)=>a.start-b.start);
  const merged=[];
  for(const range of ranges){const last=merged.at(-1);if(last&&range.start<=last.end)last.end=Math.max(last.end,range.end);else merged.push({start:range.start,end:range.end});}
  let position=0,result='';
  for(const range of merged){result+=esc(text.slice(position,range.start))+`<mark>${esc(text.slice(range.start,range.end))}</mark>`;position=range.end;}
  return result+esc(text.slice(position));
}
export function readingToolbar(passage){
  return `<div class="reading-tools"><div class="reading-mobile-tabs" role="group" aria-label="阅读面板"><button class="btn" data-reading-panel="article" aria-pressed="true">文章</button><button class="btn" data-reading-panel="questions" aria-pressed="false">题目</button></div><label>文章字号 <select id="reading-font">${[16,18,20,22].map(n=>`<option value="${n}">${n}px</option>`).join('')}</select></label><label>定位原文 <select id="reading-block-jump"><option value="">选择文本段</option>${(passage.blocks||[]).map((b,i)=>`<option value="${i}">文本段 ${i+1}${b.source?.pdfPage?` · PDF ${b.source.pdfPage} 页`:''}</option>`).join('')}</select></label><button class="btn" id="reading-highlight">高亮选中文字</button><button class="btn" id="reading-word">收藏选中生词</button><a class="btn" href="/words.html">我的生词本</a><button class="btn" id="reading-clear">清除本篇高亮</button><span class="practice-muted">选中同一文本段内的内容后点击高亮；导入文本更新后，旧高亮不会套用到新文本。</span></div>`;
}
export function readingBlock(block,index,passageIndex,marks=[]){
  return `<p class="practice-prose" data-reading-block="${index}" id="reading-block-${index}" tabindex="-1">${highlightHTML(block.text,marks.filter(m=>m.passage===passageIndex&&m.block===index))}</p>`;
}
export function mountReadingTools({passage,index,state,save,message}){
  const abort=new AbortController(),options={signal:abort.signal};
  const root=document.querySelector('.practice-reading');if(!root)return ()=>abort.abort();
  const prefKey='ielts-reading-preferences-v1';let prefs={font:18,panel:'article'},selection=null;
  try{const p=JSON.parse(localStorage.getItem(prefKey));if([16,18,20,22].includes(p?.font))prefs.font=p.font;if(['article','questions'].includes(p?.panel))prefs.panel=p.panel;}catch{}
  const persist=()=>{try{localStorage.setItem(prefKey,JSON.stringify(prefs));}catch{message('阅读偏好暂时无法保存。');}};
  const setPanel=panel=>{
    prefs.panel=panel;root.dataset.panel=panel;
    document.querySelectorAll('[data-reading-panel]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.readingPanel===panel)));
    persist();
  };
  const font=document.querySelector('#reading-font');font.value=String(prefs.font);root.style.setProperty('--reading-font',prefs.font+'px');setPanel(prefs.panel);
  font.addEventListener('change',()=>{prefs.font=Number(font.value);root.style.setProperty('--reading-font',prefs.font+'px');persist();},options);
  document.querySelectorAll('[data-reading-panel]').forEach(button=>button.addEventListener('click',()=>setPanel(button.dataset.readingPanel),options));
  document.querySelector('#reading-block-jump').addEventListener('change',e=>{
    if(e.target.value==='')return;setPanel('article');const target=document.querySelector(`#reading-block-${Number(e.target.value)}`);target?.focus({preventScroll:true});target?.scrollIntoView({block:'center',behavior:'auto'});
  },options);
  const selectedBlock=node=>{const el=node?.nodeType===Node.ELEMENT_NODE?node:node?.parentElement;return el?.closest('[data-reading-block]');};
  document.addEventListener('selectionchange',()=>{
    const selected=window.getSelection();if(!selected?.rangeCount||selected.isCollapsed)return;
    const range=selected.getRangeAt(0),p=selectedBlock(range.startContainer);
    if(!p||p!==selectedBlock(range.endContainer)||!root.contains(p)){selection=null;return;}
    const prefix=range.cloneRange();prefix.selectNodeContents(p);prefix.setEnd(range.startContainer,range.startOffset);
    const start=prefix.toString().length;
    selection={passage:index,block:Number(p.dataset.readingBlock),text:p.textContent,start,end:start+range.toString().length};
  },options);
  const collect=document.querySelector('#reading-word');
  collect.addEventListener('pointerdown',e=>e.preventDefault(),options);
  collect.addEventListener('click',async()=>{
    if(!selection){message('请先选中英文单词或短语。');return;}
    const selected={...selection},word=selected.text.slice(selected.start,selected.end).trim();
    if(!/^[A-Za-z][A-Za-z '\-]*$/.test(word)||word.length>80||word.split(/\s+/).length>8){message('请选择一个单词或不超过 8 个词的短语。');return;}
    const meaning=window.prompt('为 '+word+' 填写释义（可留空）','');if(meaning===null)return;
    try{await savePersonalWord({word,meaning,context:selected.text.slice(Math.max(0,selected.start-250),selected.end+350),source:{title:passage.title||'',url:location.pathname+location.search,pdfPage:passage.blocks[selected.block]?.source?.pdfPage||null}});message('已收藏到阅读生词本，可在记单词页复习。');}catch(e){message(e.message);}
  },options);
  const repaint=()=>{for(const p of root.querySelectorAll('[data-reading-block]')){const i=Number(p.dataset.readingBlock);p.innerHTML=highlightHTML(passage.blocks[i].text,(state.readingMarks||[]).filter(m=>m.passage===index&&m.block===i));}};
  const add=document.querySelector('#reading-highlight'),clear=document.querySelector('#reading-clear');
  add.disabled=clear.disabled=Boolean(state.submitted);
  add.addEventListener('pointerdown',e=>e.preventDefault(),options);
  add.addEventListener('click',()=>{
    if(state.submitted)return;
    if(!selection){message('请先选中同一文本段内的文字。');return;}
    const current=selection;selection=null;
    state.readingMarks=[...(state.readingMarks||[]),current];
    const saved=save();window.getSelection()?.removeAllRanges();repaint();if(saved)message('高亮已添加，随本次练习保存。');
  },options);
  clear.addEventListener('click',()=>{if(state.submitted)return;state.readingMarks=(state.readingMarks||[]).filter(m=>m.passage!==index);selection=null;const saved=save();repaint();if(saved)message('已清除本篇高亮。');},options);
  return ()=>abort.abort();
}
