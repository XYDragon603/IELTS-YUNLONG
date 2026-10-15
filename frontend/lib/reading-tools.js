import {savePersonalWord} from './personal-words.js';
import { escapeHTML as esc } from '../core.js';

export function highlightHTML(text,marks=[]){
  text=String(text||'');
  const ranges=marks.filter(m=>m.text===text&&Number.isInteger(m.start)&&Number.isInteger(m.end)&&m.start>=0&&m.end<=text.length&&m.start<m.end).sort((a,b)=>a.start-b.start);
  const merged=[];
  for(const range of ranges){const last=merged.at(-1);if(last&&range.start<=last.end)last.end=Math.max(last.end,range.end);else merged.push({start:range.start,end:range.end,id:range.id,note:range.note});}
  let position=0,result='';
  for(const range of merged){const attrs=range.id?` data-mark="${esc(range.id)}"${range.note?` class="has-note" title="${esc(range.note)}"`:''}`:'';result+=esc(text.slice(position,range.start))+`<mark${attrs}>${esc(text.slice(range.start,range.end))}</mark>`;position=range.end;}
  return result+esc(text.slice(position));
}
export function readingToolbar(passage){
  return `<div class="reading-tools"><div class="reading-mobile-tabs" role="group" aria-label="阅读面板"><button class="btn" data-reading-panel="article" aria-pressed="true">文章</button><button class="btn" data-reading-panel="questions" aria-pressed="false">题目</button></div><button class="btn reading-notes-toggle" id="reading-notes-toggle" type="button" aria-expanded="false">笔记 <span data-notes-count>0</span></button><label>文章字号 <select id="reading-font">${[16,18,20,22].map(n=>`<option value="${n}">${n}px</option>`).join('')}</select></label><label>定位原文 <select id="reading-block-jump"><option value="">选择文本段</option>${(passage.blocks||[]).map((b,i)=>`<option value="${i}">文本段 ${i+1}${b.source?.pdfPage?` · PDF ${b.source.pdfPage} 页`:''}</option>`).join('')}</select></label><button class="btn" id="reading-highlight">高亮选中文字</button><button class="btn" id="reading-word">收藏选中生词</button><a class="btn" href="/words.html">我的生词本</a><button class="btn" id="reading-clear">清除本篇高亮</button><span class="practice-muted">在文章中选中文字即可高亮、记笔记或收藏生词；点击已高亮的文字可编辑笔记或删除高亮。导入文本更新后，旧高亮不会套用到新文本。</span></div>`;
}
// A paragraph letter printed on its own line ("A\n...") is shown as a hanging letter. Only markup is added
// (<br>, <b>), never characters, so text offsets used by highlights stay identical to block.text.
const PARAGRAPH_LETTER=/(^|\n)([A-J])(?=\n)/g;
export function readingBlock(block,index,passageIndex,marks=[]){
  const text=String(block.text||'');
  const lettered=(text.match(PARAGRAPH_LETTER)||[]).length>=2;
  let html=highlightHTML(text,marks.filter(m=>m.passage===passageIndex&&m.block===index));
  if(lettered)html=html.replace(PARAGRAPH_LETTER,(_,lead,letter)=>`${lead}${lead?'<br class="para-break">':''}<b class="para-letter" aria-label="段落 ${letter}">${letter}</b>`);
  return `<p class="practice-prose${lettered?' has-paragraph-letters':''}" data-reading-block="${index}" id="reading-block-${index}" tabindex="-1">${html}</p>`;
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
  const collectWord=async selected=>{
    if(!selected){message('请先选中英文单词或短语。');return;}
    const word=selected.text.slice(selected.start,selected.end).trim();
    if(!/^[A-Za-z][A-Za-z '\-]*$/.test(word)||word.length>80||word.split(/\s+/).length>8){message('请选择一个单词或不超过 8 个词的短语。');return;}
    const meaning=window.prompt('为 '+word+' 填写释义（可留空）','');if(meaning===null)return;
    try{await savePersonalWord({word,meaning,context:selected.text.slice(Math.max(0,selected.start-250),selected.end+350),source:{title:passage.title||'',url:location.pathname+location.search,pdfPage:passage.blocks[selected.block]?.source?.pdfPage||null}});message('已收藏到阅读生词本，可在记单词页复习。');}catch(e){message(e.message);}
  };
  collect.addEventListener('click',()=>collectWord(selection&&{...selection}),options);
  // Older highlights have no id; give them one so they can carry a note or be deleted individually.
  if((state.readingMarks||[]).some(m=>!m.id)&&!state.submitted){state.readingMarks=state.readingMarks.map(m=>m.id?m:{...m,id:markId()});save();}
  const repaint=()=>{for(const p of root.querySelectorAll('[data-reading-block]')){const i=Number(p.dataset.readingBlock);p.outerHTML=readingBlock(passage.blocks[i],i,index,state.readingMarks||[]);}refreshNotes();};
  const add=document.querySelector('#reading-highlight'),clear=document.querySelector('#reading-clear');
  add.disabled=clear.disabled=Boolean(state.submitted);
  add.addEventListener('pointerdown',e=>e.preventDefault(),options);
  add.addEventListener('click',()=>{
    if(state.submitted)return;
    if(!selection){message('请先选中同一文本段内的文字。');return;}
    const current=selection;selection=null;
    addMark(current);window.getSelection()?.removeAllRanges();
  },options);
  clear.addEventListener('click',()=>{if(state.submitted)return;state.readingMarks=(state.readingMarks||[]).filter(m=>m.passage!==index);selection=null;const saved=save();repaint();if(saved)message('已清除本篇高亮。');},options);
  const {addMark,refreshNotes,dispose}=mountAnnotations({root,passage,index,state,save,message,collectWord,repaint:()=>repaint(),getSelection:()=>selection,clearSelection:()=>{selection=null;}});
  refreshNotes();
  return ()=>{dispose();abort.abort();};
}

const markId=()=>Math.random().toString(36).slice(2,10);
// Selection popup (highlight / note / save word), highlight popup (note / delete) and the notes panel.
function mountAnnotations({root,passage,index,state,save,message,collectWord,repaint,getSelection,clearSelection}){
  const abort=new AbortController(),options={signal:abort.signal};
  const pop=document.createElement('div');pop.className='reading-popover';pop.hidden=true;pop.setAttribute('role','dialog');pop.setAttribute('aria-label','文字操作');
  const panel=document.createElement('aside');panel.className='reading-notes-panel';panel.hidden=true;panel.setAttribute('aria-label','本篇笔记');
  document.body.append(pop,panel);
  const close=()=>{pop.hidden=true;pop.innerHTML='';};
  const place=rect=>{pop.hidden=false;const w=pop.offsetWidth,h=pop.offsetHeight;let top=rect.top-h-10;if(top<8)top=rect.bottom+10;pop.style.top=Math.max(8,Math.min(top,innerHeight-h-8))+'px';pop.style.left=Math.max(8,Math.min(rect.left+rect.width/2-w/2,innerWidth-w-8))+'px';};
  const find=id=>(state.readingMarks||[]).find(m=>m.id===id);
  const snippet=m=>{const t=String(m.text||'').slice(m.start,m.end).replace(/\s+/g,' ');return t.length>140?t.slice(0,140)+'…':t;};
  const commit=(text,done)=>{const saved=save();repaint();if(done)close();if(saved&&text)message(text);};
  function addMark(sel){
    if(state.submitted)return null;
    // Overlapping highlights in the same text block are merged into one, keeping any notes.
    const overlap=(state.readingMarks||[]).filter(m=>m.passage===sel.passage&&m.block===sel.block&&m.text===sel.text&&m.start<sel.end&&sel.start<m.end);
    const mark={...sel,id:overlap[0]?.id||markId(),start:Math.min(sel.start,...overlap.map(m=>m.start)),end:Math.max(sel.end,...overlap.map(m=>m.end))};
    const notes=overlap.map(m=>m.note).filter(Boolean);if(notes.length)mark.note=notes.join('\n');
    state.readingMarks=[...(state.readingMarks||[]).filter(m=>!overlap.includes(m)),mark];
    commit('高亮已添加，随本次练习保存。');return mark;
  }
  function editNote(mark,rect){
    const readonly=Boolean(state.submitted);
    pop.innerHTML=`<p class="reading-popover-quote">${esc(snippet(mark))}</p><label class="sr-only" for="reading-note-text">笔记</label><textarea id="reading-note-text" rows="4" placeholder="写下你的笔记…" ${readonly?'readonly':''}>${esc(mark.note||'')}</textarea><div class="reading-popover-actions">${readonly?'':'<button class="btn primary" data-note-save>保存</button>'}<button class="btn" data-pop-close>${readonly?'关闭':'取消'}</button>${mark.note&&!readonly?'<button class="btn reading-danger" data-note-delete>删除笔记</button>':''}</div>`;
    pop.dataset.mark=mark.id;place(rect);pop.querySelector('textarea').focus({preventScroll:true});
  }
  function markMenu(mark,rect){
    pop.innerHTML=`<div class="reading-popover-actions">${state.submitted?(mark.note?'<button class="btn" data-pop-note>查看笔记</button>':'<span class="practice-muted">交卷后高亮为只读</span>'):`<button class="btn" data-pop-note>${mark.note?'编辑笔记':'添加笔记'}</button><button class="btn reading-danger" data-mark-delete>删除高亮</button>`}</div>`;
    pop.dataset.mark=mark.id;place(rect);
  }
  function selectionMenu(rect){
    pop.innerHTML=`<div class="reading-popover-actions">${state.submitted?'':'<button class="btn" data-pop-highlight>高亮</button><button class="btn" data-pop-addnote>笔记</button>'}<button class="btn" data-pop-word>收藏生词</button></div>`;
    delete pop.dataset.mark;place(rect);
  }
  function refreshNotes(){
    const marks=(state.readingMarks||[]).filter(m=>m.passage===index).sort((a,b)=>a.block-b.block||a.start-b.start);
    document.querySelectorAll('[data-notes-count]').forEach(el=>el.textContent=String(marks.filter(m=>m.note).length));
    if(panel.hidden)return;
    panel.innerHTML=`<header><h2>笔记 · Passage ${esc(passage.number||index+1)}</h2><button class="btn" data-panel-close aria-label="关闭笔记">✕</button></header>${marks.length?marks.map(m=>`<article class="reading-note"><blockquote>${esc(snippet(m))}</blockquote>${m.note?`<p>${esc(m.note)}</p>`:'<p class="practice-muted">仅高亮</p>'}<div class="reading-popover-actions"><button class="btn" data-note-jump="${esc(m.id)}">定位</button>${state.submitted?'':`<button class="btn" data-note-edit="${esc(m.id)}">${m.note?'编辑':'添加笔记'}</button><button class="btn reading-danger" data-note-remove="${esc(m.id)}">删除</button>`}</div></article>`).join(''):'<p class="practice-muted">在文章中选中文字，即可高亮或记笔记。</p>'}`;
  }
  const toggle=document.querySelector('#reading-notes-toggle');
  toggle?.addEventListener('click',()=>{panel.hidden=!panel.hidden;toggle.setAttribute('aria-expanded',String(!panel.hidden));document.body.classList.toggle('reading-notes-open',!panel.hidden);refreshNotes();},options);
  const paper=root.querySelector('.practice-paper');
  const onRelease=()=>setTimeout(()=>{const sel=window.getSelection();if(sel?.rangeCount&&!sel.isCollapsed&&getSelection()&&paper.contains(sel.anchorNode))selectionMenu(sel.getRangeAt(0).getBoundingClientRect());},0);
  paper.addEventListener('mouseup',onRelease,options);
  paper.addEventListener('keyup',e=>{if(e.shiftKey)onRelease();},options);
  paper.addEventListener('click',e=>{
    const mark=e.target.closest('mark[data-mark]');if(!mark)return;
    const sel=window.getSelection();if(sel&&!sel.isCollapsed)return;
    const m=find(mark.dataset.mark);if(m)markMenu(m,mark.getBoundingClientRect());
  },options);
  pop.addEventListener('mousedown',e=>{if(e.target.closest('button'))e.preventDefault();},options);
  pop.addEventListener('click',async e=>{
    const b=e.target.closest('button');if(!b)return;
    const rect=pop.getBoundingClientRect(),current=find(pop.dataset.mark);
    if(b.matches('[data-pop-close]')){close();return;}
    if(b.matches('[data-pop-highlight]')){const sel=getSelection();clearSelection();window.getSelection()?.removeAllRanges();close();if(sel)addMark(sel);return;}
    if(b.matches('[data-pop-addnote]')){const sel=getSelection();clearSelection();window.getSelection()?.removeAllRanges();const mark=sel&&addMark(sel);if(mark)editNote(mark,rect);return;}
    if(b.matches('[data-pop-word]')){const sel=getSelection();close();await collectWord(sel&&{...sel});return;}
    if(b.matches('[data-pop-note]')&&current){editNote(current,rect);return;}
    if(b.matches('[data-mark-delete]')&&current){state.readingMarks=state.readingMarks.filter(m=>m!==current);commit('已删除这处高亮。',true);return;}
    if(b.matches('[data-note-save]')&&current){const text=pop.querySelector('textarea').value.trim();state.readingMarks=state.readingMarks.map(m=>m===current?{...m,note:text||undefined}:m);commit(text?'笔记已保存，随本次练习保存。':'笔记已清空。',true);return;}
    if(b.matches('[data-note-delete]')&&current){state.readingMarks=state.readingMarks.map(m=>m===current?{...m,note:undefined}:m);commit('笔记已删除，高亮保留。',true);}
  },options);
  panel.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;
    if(b.matches('[data-panel-close]')){toggle?.click();return;}
    const id=b.dataset.noteJump||b.dataset.noteEdit||b.dataset.noteRemove,m=find(id);if(!m)return;
    if(b.dataset.noteRemove){state.readingMarks=state.readingMarks.filter(x=>x!==m);commit('已删除。');return;}
    const el=root.querySelector(`mark[data-mark="${CSS.escape(id)}"]`);
    el?.scrollIntoView({block:'center'});el?.classList.add('is-flash');setTimeout(()=>el?.classList.remove('is-flash'),1200);
    if(b.dataset.noteEdit&&el)setTimeout(()=>editNote(m,el.getBoundingClientRect()),80);
  },options);
  document.addEventListener('mousedown',e=>{if(!pop.hidden&&!pop.contains(e.target)&&!e.target.closest('mark[data-mark]'))close();},options);
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close();},options);
  paper.addEventListener('scroll',close,options);window.addEventListener('scroll',close,options);
  return {addMark,refreshNotes,dispose:()=>{abort.abort();pop.remove();panel.remove();document.body.classList.remove('reading-notes-open');}};
}

