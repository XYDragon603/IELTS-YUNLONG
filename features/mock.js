import {createMockRun,mockRuns,mockProgress,mockPaperOptions} from '../lib/mock-run.js';
import {escapeHTML as esc} from '../core.js';

const root=document.querySelector('#mock-main');
const names={listening:'听力',reading:'阅读',writing:'写作',speaking:'口语'};

async function render(){
 try{
  const response=await fetch('/api/catalog');
  if(!response.ok)throw Error('无法读取题库，请确认本地服务器已启动。');
  const catalog=await response.json();
  const papers=mockPaperOptions(catalog.entries);
  const available=papers.filter(paper=>paper.available);
  const runs=mockRuns();
  root.innerHTML=`<div class="word-heading"><div><span class="eyebrow">FULL PRACTICE</span><h1>一套试卷，四次专注。</h1><p>选择试卷，依次完成听力、阅读、写作与口语。</p></div></div>
   <section class="word-book"><h2>选择整套试卷</h2><p class="word-muted">已导入 ${available.length} / ${papers.length} 套完整四科资源。练习记录仅供个人复习，不换算官方总分或写作、口语分数。</p>
   <div class="mock-picker"><label for="mock-paper">试卷</label><select id="mock-paper" ${available.length?'':'disabled'}>${papers.map(paper=>`<option value="${paper.book}-${paper.test}" ${paper.available?'':'disabled'}>Cambridge ${paper.book} · Test ${paper.test}${paper.available?'':' · 未导入完整'}</option>`).join('')}</select><button id="new-mock" class="btn primary" ${available.length?'':'disabled'}>开始新的一套</button></div>
   <p class="word-muted">每科分别保存，可以分次完成；交卷后解锁下一科。这是连续练习流程，未启用严格计时的正式机考规则。</p></section>
   <h2>我的整套记录</h2>${runs.map(run=>{const rows=mockProgress(run),next=rows.findIndex(row=>!row.finished);return `<section class="word-book" style="margin:20px 0"><h3>Cambridge ${run.book} · Test ${run.test}</h3><p class="word-muted">${esc(new Date(run.created).toLocaleString('zh-CN'))} · 已交卷 ${rows.filter(row=>row.finished).length} / 4</p>${rows.map((row,i)=>`<div class="catalog-row"><span>${i+1}. ${names[row.skill]}<small>${row.finished?'已交卷':row.started?'进行中':'未开始'}</small></span>${row.finished||i===next?`<a class="btn ${i===next?'primary':''}" href="${esc(row.href)}">${row.finished?'查看复盘':row.started?'继续本阶段':'开始本阶段'}</a>`:'<span class="word-muted">完成上一科后解锁</span>'}</div>`).join('')}${next===-1?'<p>四科已完成。可分别查看答题与复盘，记录保存在当前浏览器。</p>':''}</section>`;}).join('')||'<p class="word-muted">还没有整套练习记录。</p>'}`;
  const select=root.querySelector('#mock-paper');
  if(available.length)select.value=`${available[0].book}-${available[0].test}`;
  root.querySelector('#new-mock').onclick=()=>{try{const [book,test]=select.value.split('-').map(Number);if(!available.some(paper=>paper.book===book&&paper.test===test))throw Error('这套试卷尚未导入完整。');createMockRun(localStorage,{book,test});render();}catch(error){alert('创建失败：'+error.message);}};
 }catch(error){root.innerHTML=`<h1>无法打开整套练习</h1><p>${esc(error.message)}</p><a class="btn" href="/#library">返回题库</a>`;}
}
render();
