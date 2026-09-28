import { escapeHTML as esc } from '../core.js';
const labels={listening:'听力',reading:'阅读',writing:'写作',speaking:'口语'};
const statuses={ready:'可练习','needs-review':'可练习','missing-resource':'资料缺失','not-imported':'尚未导入'};
export function catalogPlaceholder(book=null,test=null){return `<section class="import-catalog" data-catalog ${book?`data-book-number="${book}" data-test-number="${test}"`:''}><h2>四科在线练习</h2><p role="status">正在检查本地题库…</p></section>`;}
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
    host.innerHTML=`<h2>${book?`Test ${test} · 四科状态`:'导入题库 · 四科在线练习'}</h2><p class="hint">可练习的试卷会自动出现在这里；资料新增后点击刷新即可发现。</p><div class="catalog-filters">${book?'':`<label>册次<select data-filter="book"><option value="">全部册次</option>${Array.from({length:17},(_,i)=>20-i).map(b=>`<option>${b}</option>`).join('')}</select></label><label>Test<select data-filter="test"><option value="">全部</option>${[1,2,3,4].map(t=>`<option>${t}</option>`).join('')}</select></label>`}<label>科目<select data-filter="skill"><option value="">全部科目</option>${Object.entries(labels).map(([id,label])=>`<option value="${id}">${label}</option>`).join('')}</select></label><label>状态<select data-filter="status"><option value="imported">已导入</option><option value="">全部状态</option><option value="missing-resource">资料缺失</option><option value="not-imported">尚未导入</option></select></label><button class="btn" data-refresh>刷新题库</button></div><div data-catalog-list></div>`;
    if(book)host.querySelector('[data-filter=status]').value='';
    const draw=()=>{
      const filters=[...host.querySelectorAll('[data-filter]')];
      const visible=entries.filter(e=>filters.every(f=>!f.value||(f.value==='imported'?e.status!=='not-imported':String(e[f.dataset.filter])===f.value)));
      host.querySelector('[data-catalog-list]').innerHTML=visible.map(e=>{
        const key=`ielts-practice-v1-c${e.book}-t${e.test}-${e.skill}`;
        const s=read(e.skill==='listening'?`ielts-c${e.book}-t${e.test}-import-preview-v1`:key);
        const history=read(key+'-history');const count=Array.isArray(history)?history.length:0;
        const answered=s?.answers?Object.values(s.answers).filter(v=>Array.isArray(v)?v.length:String(v||'').trim()).length:0;
        const action=s?.submitted?'查看本次记录':answered?'继续练习':'进入练习';
        return `<article class="catalog-row" data-entry="${e.book}-${e.test}-${e.skill}"><div><strong>Cambridge ${e.book} · Test ${e.test} · ${labels[e.skill]}</strong><small>${statuses[e.status]}${answered?` · 已保存 ${answered} 项作答`:''}</small>${e.issues.length?`<small>${esc([...new Set(e.issues)].join('；'))}</small>`:''}</div><div class="catalog-actions">${e.available?`<a class="btn primary" href="${esc(e.href)}">${action}</a>`:'<span class="hint">暂不可进入</span>'}${count?`<a class="text-btn" href="/practice.html?book=${e.book}&test=${e.test}&skill=${e.skill}&attempt=${encodeURIComponent(history[0].id)}">历史 ${count} 次 ↗</a>`:''}</div></article>`;
      }).join('')||'<p class="hint">没有符合筛选条件的试卷。</p>';
    };
    host.querySelectorAll('select').forEach(el=>el.addEventListener('change',draw));
    host.querySelector('[data-refresh]').onclick=()=>mountCatalog();draw();
  }catch{if(host.isConnected)host.innerHTML='<h2>导入题库</h2><p role="status">无法读取题库索引，请重启本地服务器后刷新页面。</p>';}
}
