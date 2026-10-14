import { catalogPlaceholder } from './import-catalog.js';
import { manifest,getTestResources } from '../lib/cambridge.js';
import { statusBadge } from './components.js';
import { icon } from './icons.js';
import { escapeHTML as esc } from '../core.js';

function testStatus(book,test,state){
  const sessions=state.sessions.filter(s=>s.book===book&&s.test===test);
  return sessions.some(s=>!s.finished)?'progress':sessions.some(s=>s.finished)?'completed':'new';
}
export function cambridgeBookRow(book,state){
  const audio=book.tests.reduce((n,t)=>n+Object.keys(t.audio).length,0);
  return `<details class="book-row" data-book="${book.number}" ${[18,19,20].includes(book.number)?'open':''}><summary><span class="book-index">${book.number}</span><span><strong>Cambridge IELTS ${book.number}</strong><small>ACADEMIC · 4 TESTS</small></span><span class="book-availability">${book.documents.length?'原卷已找到':'原卷待补充'} · ${audio}/16 段音频</span><span class="expand-symbol">+</span></summary><div class="book-tests">${book.tests.map(t=>`<a href="#library/${book.number}/${t.number}" class="test-cell"><span>Test ${t.number} ${icon('arrow')}</span>${statusBadge(testStatus(book.number,t.number,state))}<small>${book.number===18&&t.number===1?'听力在线答题 · 逐题解析':`${Object.keys(t.audio).length}/4 段音频 · 原卷练习`}</small></a>`).join('')}</div></details>`;
}
export function libraryView(state){
  return `<div class="intro journal-intro"><div><span class="eyebrow">THE CAMBRIDGE COLLECTION</span><h1>你的题库，也是你的书架。</h1><p>从一套题开始，沿着理解、复盘和重做，走得更远。</p></div><span class="collection-count">04 <span>—</span> 20</span></div>${catalogPlaceholder()}<details class="resource-shelf"><summary><strong>原卷与音频</strong><span>17 册 PDF 与听力音频，未导入在线题目的册次可在这里练习</span></summary><div class="library-toolbar"><label for="book-filter">查找册次 <input id="book-filter" type="search" placeholder="例如 18 或 Cambridge 18" autocomplete="off"></label><span>17 册 / 原始文件保持原位</span></div><div id="book-list">${[...manifest.books].reverse().map(b=>cambridgeBookRow(b,state)).join('')}</div><p id="book-empty" class="empty-journal" hidden>没有匹配的册次，请输入 4–20 之间的数字。</p><p class="source-note">资源索引更新时间：${new Date(manifest.scannedAt).toLocaleString('zh-CN')}。新增文件后运行 npm run scan:resources 刷新索引。</p></details>`;
}
const links=(items,label)=>items.length?items.map(d=>`<a class="resource-link" href="${d.url}" target="_blank" rel="noopener">${icon('book')}<span>${esc(d.name||label)}</span>↗</a>`).join(''):'<p class="hint">本地尚未发现此资源。</p>';
export function testDetailView(book,test,state){
  const r=getTestResources(book,test);if(!r)return '<h1>没有找到这套试卷</h1><a class="btn" href="#library">回到题库</a>';
  const pilot=Number(book)===18&&Number(test)===1;
  const audioCount=Object.keys(r.audio).length;
  return `<a class="text-btn" href="#library">← Cambridge Library</a><div class="intro journal-intro"><div><span class="eyebrow">CAMBRIDGE IELTS ${book} / ACADEMIC</span><h1>Test ${test}<span class="heading-divider"> / </span>一次专注的练习。</h1><p>在下方查看四科资料状态，开始或继续练习。</p></div>${statusBadge(testStatus(Number(book),Number(test),state))}</div>${catalogPlaceholder(book,test)}<p><button class="btn" data-study="start" data-test="c${book}-t${test}-listening">听力计时练习 · 开始 / 继续</button></p><details class="resource-fold"><summary>原卷、精讲与音频资源</summary><div class="resource-columns"><section><div class="section-heading"><h2>Original paper <span>本地原卷</span></h2></div>${links(r.documents)}</section><section><div class="section-heading"><h2>Explanations <span>精讲与视频</span></h2></div>${links(r.explanations)}${links(r.videos.map(v=>({...v,name:`Test ${test} · ${v.skill==='listening'?'听力':'阅读'}精讲视频`})),'讲解视频')}</section></div><section><div class="section-heading"><h2>Listening audio <span>资源映射状态</span></h2></div><div class="audio-resource-list">${[1,2,3,4].map(p=>`<div><strong>Part ${p}</strong><span>${r.audio[p]?'音频已就绪':'音频待补充'}</span>${r.audio[p]?`<a class="text-btn" href="${r.audio[p].url}" target="_blank" rel="noopener">打开音频 ↗</a>`:'<span class="hint">未找到完整文件</span>'}</div>`).join('')}</div></section></details>`;
}
