import {createMockRun,mockRuns,mockProgress,mockPaperOptions} from '../lib/mock-run.js';
import {escapeHTML as esc} from '../core.js';
import {icon} from '../ui/icons.js';

const root=document.querySelector('#mock-main');
const names={listening:'听力',reading:'阅读',writing:'写作',speaking:'口语'};
const skillIcons={listening:'headphones',reading:'book',writing:'pen',speaking:'mic'};
const when=iso=>{const d=new Date(iso);return Number.isNaN(d.getTime())?'':`${d.getFullYear()}/${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;};

// Stage states for one run: finished, current (next to do), locked.
function stages(run){
 const rows=mockProgress(run),next=rows.findIndex(row=>!row.finished);
 return rows.map((row,i)=>({...row,state:row.finished?'done':i===next?'current':'locked'}));
}

function stageStrip(rows){
 return `<ol class="mock-stages">${rows.map((row,i)=>{
  const status=row.state==='done'?`${icon('check')}已交卷`:row.state==='current'?(row.started?'<i class="spin" aria-hidden="true"></i>进行中':`${icon('play')}可以开始`):`${icon('lock')}待解锁`;
  const body=`<span class="mock-stage-no">0${i+1}</span><span class="mock-stage-icon">${icon(skillIcons[row.skill])}</span><span class="mock-stage-name">${names[row.skill]}<small>${row.skill.toUpperCase()}</small></span><span class="mock-stage-status">${status}</span>`;
  return `<li class="mock-stage is-${row.state}">${row.state==='locked'||!row.href?`<div>${body}</div>`:`<a href="${esc(row.href)}" aria-label="${names[row.skill]} · ${row.state==='done'?'查看复盘':row.started?'继续':'开始'}">${body}</a>`}</li>`;}).join('')}</ol>`;
}

function currentCard(run,rows){
 const done=rows.filter(r=>r.finished).length,current=rows.find(r=>r.state==='current'),last=[...rows].reverse().find(r=>r.finished);
 const summary=[['已交卷',rows.filter(r=>r.state==='done')],['进行中',rows.filter(r=>r.state==='current'&&r.started)],['待解锁',rows.filter(r=>r.state==='locked'||(r.state==='current'&&!r.started))]].filter(([,list])=>list.length).map(([label,list])=>`<span>${label}：${list.map(r=>names[r.skill]).join('、')}</span>`).join('');
 return `<section class="mock-current"><div class="studio-cover"><small>CAMBRIDGE</small><span>${run.book}</span><small>ACADEMIC</small></div><div class="mock-current-body"><h2>Cambridge ${run.book} · Test ${run.test}</h2><p class="mock-current-sub">Academic · 本地原卷 · ${esc(when(run.created))} 开始</p><p class="mock-current-count">已完成 ${done} / 4 科</p><div class="home-progress" role="progressbar" aria-label="整套进度" aria-valuemin="0" aria-valuemax="4" aria-valuenow="${done}"><i style="width:${Math.max(3,done/4*100)}%"></i></div><p class="mock-current-summary">${summary}</p><div class="mock-current-actions">${current?`<a class="btn primary" href="${esc(current.href)}">${current.started?'继续':'开始'}${names[current.skill]}练习 ${icon('arrow')}</a>`:'<span class="mock-complete">四科已完成，可分别查看答题与复盘。</span>'}${last?`<a class="btn outline" href="${esc(last.href)}">查看${names[last.skill]}复盘 ${icon('arrow')}</a>`:''}</div></div></section>`;
}

const tips=`<aside class="mock-tips"><h2>按你的节奏完成</h2><ul><li>${icon('doc')}<span>每科独立保存<small>随时中断，进度自动保存在本机。</small></span></li><li>${icon('lock')}<span>完成上一科后解锁下一科<small>按考试顺序，逐步完成四个部分。</small></span></li><li>${icon('bars')}<span>结果仅供个人复习<small>不换算官方总分或写作、口语分数；未启用严格计时的机考规则。</small></span></li></ul></aside>`;

async function render(){
 try{
  const response=await fetch('/api/catalog.json');
  if(!response.ok)throw Error('无法读取题库，请确认本地服务器已启动。');
  const catalog=await response.json();
  const papers=mockPaperOptions(catalog.entries);
  const available=papers.filter(paper=>paper.available);
  const runs=mockRuns();
  const active=runs.find(run=>mockProgress(run).some(row=>!row.finished))||runs[0];
  const books=[...new Set(papers.map(p=>p.book))];
  const first=available[0];
  const activeRows=active&&stages(active);
  root.innerHTML=`<div class="mock-intro"><span class="eyebrow">Full practice</span><h1>一套试卷，<em>四次专注。</em></h1><p>按真实考试的顺序完成四个部分，在专注练习中稳步提升。</p></div>
   <section class="mock-picker" aria-label="选择整套试卷"><label for="mock-book">选择试卷</label><select id="mock-book" ${available.length?'':'disabled'}>${books.map(b=>`<option value="${b}" ${papers.some(p=>p.book===b&&p.available)?'':'disabled'}>Cambridge ${b}</option>`).join('')}</select>
    <div class="mock-tests" role="group" aria-label="选择 Test">${[1,2,3,4].map(t=>`<button type="button" data-mock-test="${t}">Test ${t}</button>`).join('')}</div>
    <select id="mock-paper" hidden ${available.length?'':'disabled'}>${papers.map(paper=>`<option value="${paper.book}-${paper.test}" ${paper.available?'':'disabled'}>Cambridge ${paper.book} · Test ${paper.test}${paper.available?'':' · 未导入完整'}</option>`).join('')}</select>
    <span class="mock-picker-meta">Academic · 本地原卷 · 已导入 ${available.length} / ${papers.length} 套</span><button id="new-mock" class="btn primary" ${available.length?'':'disabled'}>开始新的一套 ${icon('arrow')}</button></section>
   ${active?`${stageStrip(activeRows)}<div class="mock-grid">${currentCard(active,activeRows)}${tips}</div>`:`<div class="mock-grid"><section class="mock-current mock-empty"><div class="studio-cover"><small>CAMBRIDGE</small><span>${first?.book??'—'}</span><small>ACADEMIC</small></div><div class="mock-current-body"><h2>还没有进行中的整套练习</h2><p class="mock-current-sub">在上方选择册次和 Test，点击“开始新的一套”。听力交卷后解锁阅读，依次完成四科。</p></div></section>${tips}</div>`}
   <section class="mock-records"><div class="section-heading"><h2>我的整套记录</h2><span class="mock-records-note">连续练习流程 · 非正式考试成绩</span></div>${runs.length?`<ul>${runs.map(run=>{const rows=stages(run),done=rows.filter(r=>r.finished).length,current=rows.find(r=>r.state==='current'),last=[...rows].reverse().find(r=>r.finished);const action=current||last;return `<li><span class="recent-icon">${icon('book')}</span><span class="mock-record-paper">Cambridge ${run.book} · Test ${run.test}</span><span class="mock-pill ${done===4?'is-done':''}">${done===4?'已完成':'进行中'}</span><time datetime="${esc(run.created)}">${esc(when(run.created))}</time><span class="mock-record-count">已完成 ${done} / 4 科</span><span class="mock-record-bar ${done===4?'is-done':''}"><i style="width:${Math.max(3,done/4*100)}%"></i></span>${run===active?'<span class="mock-record-hint">见上方进度</span>':action?`<a class="btn small outline" href="${esc(action.href)}">${current?'继续练习':'查看复盘'} ${icon('arrow')}</a>`:''}</li>`;}).join('')}</ul>`:'<p class="recent-empty">还没有整套练习记录。</p>'}</section>`;
  const paper=root.querySelector('#mock-paper'),bookSelect=root.querySelector('#mock-book');
  const sync=()=>{const [book,test]=paper.value.split('-').map(Number);bookSelect.value=String(book);root.querySelectorAll('[data-mock-test]').forEach(button=>{const t=Number(button.dataset.mockTest);const ok=available.some(p=>p.book===book&&p.test===t);button.disabled=!ok;button.setAttribute('aria-pressed',String(t===test));});};
  if(available.length){paper.value=`${first.book}-${first.test}`;sync();}
  bookSelect.onchange=()=>{const book=Number(bookSelect.value);const p=available.find(x=>x.book===book);if(p){paper.value=`${p.book}-${p.test}`;sync();}};
  root.querySelectorAll('[data-mock-test]').forEach(button=>button.onclick=()=>{paper.value=`${bookSelect.value}-${button.dataset.mockTest}`;sync();});
  paper.onchange=sync;
  root.querySelector('#new-mock').onclick=()=>{try{const [book,test]=paper.value.split('-').map(Number);if(!available.some(p=>p.book===book&&p.test===test))throw Error('这套试卷尚未导入完整。');createMockRun(localStorage,{book,test});render();}catch(error){alert('创建失败：'+error.message);}};
 }catch(error){root.innerHTML=`<h1>无法打开整套练习</h1><p>${esc(error.message)}</p><a class="btn" href="/#library">返回题库</a>`;}
}
render();
