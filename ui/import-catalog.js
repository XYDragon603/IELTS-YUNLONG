import { escapeHTML as esc } from '../core.js';
const labels={listening:'听力',reading:'阅读',writing:'写作',speaking:'口语'};
const statuses={ready:'已核对','needs-review':'待核对','missing-resource':'资料缺失','not-imported':'尚未导入'};
export function catalogPlaceholder(book=null,test=null){return `<section class="import-catalog" data-catalog ${book?`data-book-number="${book}" data-test-number="${test}"`:''}><h2>四科在线练习</h2><p role="status">正在检查本地题库…</p></section>`;}
function bookRanges(books){
  const sorted=[...books].sort((a,b)=>a-b),parts=[];
  for(let i=0;i<sorted.length;){let j=i;while(sorted[j+1]===sorted[j]+1)j++;parts.push(j-i>1?`${sorted[i]}–${sorted[j]}`:sorted.slice(i,j+1).join('、'));i=j+1;}
  return parts.join('、');
}
function read(key){try{return JSON.parse(localStorage.getItem(key));}catch{return null;}}
export function localPracticeLinks(){
  const drafts=[],history=[];
  try{for(let i=0;i<localStorage.length;i++){
    const key=localStorage.key(i);
    const listening=key.match(/^ielts-c(\d+)-t([1-4])-import-preview-v1$/);
    if(listening){const s=read(key);if(s?.answers&&!s.submitted&&Object.keys(s.answers).length)drafts.push({title:`Cambridge ${listening[1]} · Test ${listening[2]} · 听力预览`,href:`/import-preview.html?book=${listening[1]}&test=${listening[2]}`});continue;}
    const m=key.match(/^ielts-practice-v1-c(\d+)-t([1-4])-(reading|writing|speaking)(-history)?$/);if(!m)continue;
    const value=read(key);const url=`/practice.html?book=${m[1]}&test=${m[2]}&skill=${m[3]}`;
    const title=`Cambridge ${m[1]} · Test ${m[2]} · ${labels[m[3]]}`;
    if(m[4]){if(Array.isArray(value))for(const item of value)if(item?.id&&item.submitted)history.push({title,href:url+'&attempt='+encodeURIComponent(item.id),date:item.submitted});}
    else if(value?.version===1&&!value.submitted&&value.answers&&(Object.keys(value.answers).length||value.deadline))drafts.push({title,href:url});
  }}catch{}
  const links=(items,action)=>items.map(v=>`<a class="catalog-row" href="${esc(v.href)}"><span>${esc(v.title)}${v.date?`<small>${esc(new Date(v.date).toLocaleString('zh-CN'))}</small>`:''}</span><strong>${action} ↗</strong></a>`).join('');
  return `<section class="import-catalog"><h2>继续四科练习</h2>${links(drafts,'继续练习')||'<p class="hint">暂无阅读、写作或口语草稿。</p>'}<a class="text-btn" href="#library">选择题库 ↗</a></section><section class="import-catalog"><h2>三科练习历史</h2>${links(history.sort((a,b)=>String(b.date).localeCompare(String(a.date))),'查看记录')||'<p class="hint">提交后的练习记录会显示在这里。</p>'}</section>`;
}
export async function mountCatalog(){
  const host=document.querySelector('[data-catalog]');if(!host)return;
  const book=Number(host.dataset.bookNumber),test=Number(host.dataset.testNumber);
  try{
    const response=await fetch('/api/catalog');if(!response.ok)throw new Error();const result=await response.json();
    if(!host.isConnected)return;
    const entries=result.entries.filter(e=>!book||e.book===book&&e.test===test);
    const imported=result.entries.filter(e=>e.status!=='not-imported');
    const ready=imported.filter(e=>e.status==='ready').length;
    const missingBooks=Array.from({length:17},(_,i)=>20-i).filter(b=>!imported.some(e=>e.book===b));
    const legend=`<p class="catalog-legend"><span><i class="status-dot ready"></i>已核对</span><span><i class="status-dot needs-review"></i>待核对 · 由 OCR 自动整理，题干或答案可能有识别错误，可对照原卷练习</span><span><i class="status-dot missing-resource"></i>资料缺失</span></p>`;
    host.innerHTML=`<h2>${book?`Test ${test} · 四科状态`:'在线题库'}</h2><p class="hint">${book?'资料新增后点击刷新即可发现。':`已导入 ${imported.length} 项 · 已核对 ${ready} 项。资料新增后点击刷新即可发现。`}</p>${legend}<div class="catalog-filters">${book?'':`<label>册次<select data-filter="book"><option value="">全部册次</option>${Array.from({length:17},(_,i)=>20-i).map(b=>`<option>${b}</option>`).join('')}</select></label>`}<label>科目<select data-filter="skill"><option value="">全部科目</option>${Object.entries(labels).map(([id,label])=>`<option value="${id}">${label}</option>`).join('')}</select></label><label>状态<select data-filter="status"><option value="imported">已导入</option><option value="">全部状态</option><option value="needs-review">待核对</option><option value="ready">已核对</option><option value="missing-resource">资料缺失</option><option value="not-imported">尚未导入</option></select></label><button class="btn" data-refresh>刷新题库</button></div><div data-catalog-list></div>`;
    if(book)host.querySelector('[data-filter=status]').value='';
    const progress=e=>{
      const key=`ielts-practice-v1-c${e.book}-t${e.test}-${e.skill}`;
      const s=read(e.skill==='listening'?`ielts-c${e.book}-t${e.test}-import-preview-v1`:key);
      const history=read(key+'-history');const count=Array.isArray(history)?history.length:0;
      const answered=s?.answers?Object.values(s.answers).filter(v=>Array.isArray(v)?v.length:String(v||'').trim()).length:0;
      const historyHref=count?`/practice.html?book=${e.book}&test=${e.test}&skill=${e.skill}&attempt=${encodeURIComponent(history[0].id)}`:'';
      return {submitted:Boolean(s?.submitted),answered,count,historyHref};
    };
    const row=e=>{
      const p=progress(e);
      const action=p.submitted?'查看本次记录':p.answered?'继续练习':'进入练习';
      return `<article class="catalog-row" data-entry="${e.book}-${e.test}-${e.skill}"><div><strong>Cambridge ${e.book} · Test ${e.test} · ${labels[e.skill]}</strong><small><i class="status-dot ${e.status}"></i>${statuses[e.status]}${p.answered?` · 已保存 ${p.answered} 项作答`:''}</small>${e.issues.length?`<small>${esc([...new Set(e.issues)].join('；'))}</small>`:''}</div><div class="catalog-actions">${e.available?`<a class="btn primary" href="${esc(e.href)}">${action}</a>`:'<span class="hint">暂不可进入</span>'}${p.count?`<a class="text-btn" href="${p.historyHref}">历史 ${p.count} 次 ↗</a>`:''}</div></article>`;
    };
    const cell=e=>{
      if(!e)return '<span class="shelf-cell empty" aria-hidden="true">—</span>';
      const p=progress(e),title=`${labels[e.skill]} · ${statuses[e.status]}${e.issues.length?' · '+[...new Set(e.issues)].join('；'):''}`;
      if(!e.available)return `<span class="shelf-cell locked" data-entry="${e.book}-${e.test}-${e.skill}" title="${esc(title)}"><i class="status-dot ${e.status}"></i>${e.status==='not-imported'?'未导入':'暂不可用'}</span>`;
      const label=p.submitted?'已提交':p.answered?`继续 · ${p.answered}`:'开始';
      return `<span class="shelf-cell${p.submitted?' done':p.answered?' active':''}" data-entry="${e.book}-${e.test}-${e.skill}"><a href="${esc(e.href)}" title="${esc(title)}" aria-label="Test ${e.test} ${esc(title)} · ${label}"><i class="status-dot ${e.status}"></i>${label}</a>${p.count?`<a class="shelf-history" href="${p.historyHref}">历史 ${p.count}</a>`:''}</span>`;
    };
    const shelf=visible=>{
      const skillFilter=host.querySelector('[data-filter=skill]').value;
      const columns=skillFilter?[skillFilter]:Object.keys(labels);
      const books=[...new Set(visible.map(e=>e.book))].sort((a,b)=>b-a);
      const html=books.map(b=>{
        const own=visible.filter(e=>e.book===b);
        const all=result.entries.filter(e=>e.book===b&&e.status!=='not-imported');
        const pending=all.filter(e=>e.status==='needs-review').length;
        const tests=[1,2,3,4].filter(t=>own.some(e=>e.test===t));
        return `<section class="shelf-book" data-shelf-book="${b}"><header><span class="shelf-index">${b}</span><div><strong>Cambridge IELTS ${b}</strong><small>已导入 ${all.length} / 16 项${pending?` · 待核对 ${pending}`:''}</small></div></header><div class="shelf-grid" style="--shelf-cols:${columns.length}"><span class="shelf-head" aria-hidden="true"></span>${columns.map(s=>`<span class="shelf-head">${labels[s]}</span>`).join('')}${tests.map(t=>`<a class="shelf-test" href="#library/${b}/${t}">Test ${t}</a>${columns.map(s=>cell(own.find(e=>e.test===t&&e.skill===s))).join('')}`).join('')}</div></section>`;
      }).join('');
      return html?`<div class="shelf">${html}</div>${missingBooks.length&&!host.querySelector('[data-filter=book]').value?`<p class="hint shelf-missing">第 ${bookRanges(missingBooks)} 册尚未导入在线题目，可在下方“原卷与音频”中打开 PDF 练习。</p>`:''}`:'';
    };
    const draw=()=>{
      const filters=[...host.querySelectorAll('[data-filter]')];
      const visible=entries.filter(e=>filters.every(f=>!f.value||(f.value==='imported'?e.status!=='not-imported':String(e[f.dataset.filter])===f.value)));
      host.querySelector('[data-catalog-list]').innerHTML=(book?visible.map(row).join(''):shelf(visible))||'<p class="hint">没有符合筛选条件的试卷。</p>';
    };
    host.querySelectorAll('select').forEach(el=>el.addEventListener('change',draw));
    host.querySelector('[data-refresh]').onclick=()=>mountCatalog();draw();
  }catch{if(host.isConnected)host.innerHTML='<h2>导入题库</h2><p role="status">无法读取题库索引，请重启本地服务器后刷新页面。</p>';}
}
