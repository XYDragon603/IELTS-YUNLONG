import {requireMockStage,practiceRunKey} from '../lib/mock-run.js';
import {openSubmissionCheck} from '../lib/practice-submit.js';
import { mountExamWorkspace } from '../lib/exam-workspace.js';
import { mountExamHeader } from '../ui/exam-header.js';
import { icon } from '../ui/icons.js';
import { readingToolbar, readingBlock, mountReadingTools } from '../lib/reading-tools.js';
import { identifyPractice, newPractice, archivePractice, historyEntries } from '../lib/practice-history.js';
import { escapeHTML as esc, wordCount, formatTime } from '../core.js';
import { practiceRemaining, pausePractice, readingItems, readingReport, loadPractice, assetURL } from '../lib/practice-model.js';
import { recordingStore } from '../lib/practice-recordings.js';
import { localResourceURL } from '../lib/imported-listening.js';
import { exactReadingExcerpt, renderSynonymNotes, saveSynonymWord } from '../lib/synonym-notes.js';
import { addReviewItem, createReadingReviewItem } from '../lib/review-queue.js';

const params=new URLSearchParams(location.search);
const skill=['reading','writing','speaking'].includes(params.get('skill'))?params.get('skill'):'reading';
const book=/^\d+$/.test(params.get('book')||'')?Number(params.get('book')):18;
const test=/^[1-4]$/.test(params.get('test')||'')?Number(params.get('test')):1;
const base=`/resources/cambridge/c${book}/test-${test}/`;
const mockId=params.get('mockRun');
let mockRun=null,mockError=null;
try{if(mockId){mockRun=requireMockStage(mockId,skill);if(mockRun.book!==book||mockRun.test!==test)throw Error('Mock paper mismatch');}}catch(e){mockError=e;}
const key=mockRun?practiceRunKey(mockRun,skill):`ielts-practice-v1-c${book}-t${test}-${skill}`;
const historyId=params.get('attempt');
let archiveEntry=null, disposeReadingTools=()=>{};
const names={reading:'阅读',writing:'写作',speaking:'口语'};
const main=document.querySelector('#practice-main');
const notice=document.querySelector('#practice-notice');
let data,state=identifyPractice(loadPractice(key,skill),key),recorder,stream,pendingMic=false,finishingRecording=false,stopPromise,recordURL,recordBlob,renderToken=0;
const message=text=>{notice.textContent=text;};
function save(){if(historyId)return true;try{state.savedAt=Date.now();localStorage.setItem(key,JSON.stringify(state));document.querySelector('#save-status')?.replaceChildren(document.createTextNode('已保存至本机'));return true;}catch{message('本地保存失败，请导出记录并保持页面打开。');return false;}}
function promptText(q){const text=String(q.prompt||'').replace(new RegExp(`^\\s*${Number(q.number)}[.)]?\\s+`),'');return text||'请对照上方题组或原图填写对应空格。';}
// PDF line breaks inside a sentence (next line starts lower-case or with a digit) are shown as spaces.
function flowText(text){return String(text||'').replace(/([^.!?:\n])\n(?=[a-z0-9(])/g,'$1 ');}
function groups(){return skill==='reading'?data.passages:skill==='writing'?data.tasks:data.parts;}
function img(asset){return asset?`<img class="practice-asset" src="${esc(assetURL(base,asset.asset))}" alt="${esc(asset.alt||'原卷图片')}" loading="lazy">`:'';}
function sourceLink(source){return source?.pdfPage&&data.sources?.paper?.path?`<a class="text-btn" href="${esc(localResourceURL(data.sources.paper.path))}#page=${source.pdfPage}" target="_blank" rel="noopener">原卷第 ${source.pdfPage} 页 ↗</a>`:'';}
const JUDGEMENTS={'true-false-not-given':['TRUE','FALSE','NOT GIVEN'],'yes-no-not-given':['YES','NO','NOT GIVEN']};
function input(q,group){
  const flag=`<button class="btn flag" data-flag="${esc(q.id)}" aria-label="标记第 ${q.number} 题" aria-pressed="${state.flags.includes(q.id)}">☆</button>`;
  const number=`<strong><span class="sr-only">第 </span>${q.number}<span class="sr-only"> 题</span></strong>`;
  const judgement=JUDGEMENTS[group.type];
  if(judgement){ // one-tap segmented choice; radios fire the same input event as other answer fields
    return `<section class="practice-q" id="question-${esc(q.id)}">${flag}<label id="prompt-${esc(q.id)}">${number} ${esc(promptText(q))}</label><div class="choice-segment" role="radiogroup" aria-labelledby="prompt-${esc(q.id)}">${judgement.map((value,i)=>`<label class="choice-segment-item"><input type="radio" ${i===0?`id="answer-${esc(q.id)}"`:''} name="answer-${esc(q.id)}" data-answer="${esc(q.id)}" value="${value}" ${String(state.answers[q.id]||'').trim().toUpperCase()===value?'checked':''} ${state.submitted?'disabled':''}><span>${value}</span></label>`).join('')}</div></section>`;
  }
  const options=q.options||group.options||[];
  return `<section class="practice-q" id="question-${esc(q.id)}">${flag}<label for="answer-${esc(q.id)}"><strong><span class="sr-only">第 </span>${q.number}<span class="sr-only"> 题</span></strong> ${esc(promptText(q))}</label>${options.length?`<select id="answer-${esc(q.id)}" data-answer="${esc(q.id)}" ${state.submitted?'disabled':''}><option value="">选择答案</option>${options.map(o=>`<option value="${esc(o.value)}" ${state.answers[q.id]===o.value?'selected':''}>${esc(o.value)} · ${esc(o.label)}</option>`).join('')}</select>`:`<input id="answer-${esc(q.id)}" data-answer="${esc(q.id)}" value="${esc(state.answers[q.id]||'')}" ${state.submitted?'disabled':''} autocomplete="off" spellcheck="false">`}</section>`;
}
function questionRange(passage){const n=(passage.groups||[]).flatMap(g=>g.questions||[]).map(q=>Number(q.number)).filter(Number.isFinite);return n.length?`Questions ${Math.min(...n)}–${Math.max(...n)}`:'Questions';}
function reading(passage){
  return `${readingToolbar(passage)}<div class="practice-grid practice-reading"><article class="practice-paper" tabindex="0" aria-label="阅读文章，可滚动"><h2>${esc(passage.title||'文章标题待整理')}</h2>${(passage.blocks||[]).map((b,i)=>readingBlock(b,i,state.index,state.readingMarks||[])).join('')}${sourceLink(passage.blocks?.[0]?.source)}</article><section class="practice-editor"><h2>${questionRange(passage)}</h2><nav class="practice-map" aria-label="本篇题号">${(passage.groups||[]).flatMap(g=>g.questions||[]).map(q=>`<a href="#question-${esc(q.id)}" data-map="${esc(q.id)}">${q.number}</a>`).join('')}</nav>${(passage.groups||[]).map(g=>`<section><h3>Questions ${g.questionRange.join('–')}</h3>${g.asset?`<figure class="practice-group-asset">${img(g.asset)}${sourceLink(g.source)}</figure>`:`<details ${(g.questions||[]).some(q=>!q.prompt)?'open':''}><summary>题组说明与上下文</summary><p class="practice-prose">${esc(g.context||g.instruction||'')}</p>${sourceLink(g.source)}</details>`}${(g.questions||[]).map(q=>input(q,g)).join('')}</section>`).join('')||'<p>本篇题目尚待整理，请对照原卷。</p>'}</section></div>`;
}
const SELF_CHECKS={
  task1:['概述了主要趋势或特征','选取了关键数据并做比较','没有加入个人观点或原因推测','达到至少 150 词'],
  task2:['回应了题目的每一个部分','每段有清晰的中心句','用具体例子或理由支撑观点','达到至少 250 词'],
  speaking:['回答完整，并有展开','用了具体的例子或经历','表达连贯，用了衔接词']
};
// Optional self-check, saved per task/part in state.selfCheck (kept out of state.answers, so it never looks like an answer).
function selfCheck(id,kind,title){
  const done=(state.selfCheck||{})[id]||[];
  return `<fieldset class="self-check"><legend>${title} <small>（可选）</small></legend>${SELF_CHECKS[kind].map((label,i)=>`<label><input type="checkbox" data-self-check="${esc(id)}" value="${i}" ${done.includes(i)?'checked':''} ${historyId?'disabled':''}> ${label}</label>`).join('')}</fieldset>`;
}
function writing(task){
  return `<div class="practice-grid"><article class="practice-paper"><h2>Writing Task ${task.number}</h2><p class="practice-prose">${esc(flowText(task.prompt))}</p>${(task.assets||[]).map(img).join('')}${sourceLink(task.source)}</article><section class="practice-editor"><label for="essay"><h2>Your response</h2></label><div class="practice-metrics"><span>建议至少 ${task.minimumWords||'—'} 词</span><output id="word-count">0 词</output></div><textarea id="essay" data-answer="${esc(task.id)}" ${state.submitted?'readonly':''} placeholder="Write your response here…">${esc(state.answers[task.id]||'')}</textarea>${selfCheck(task.id,Number(task.number)===1?'task1':'task2','写作自查')}<div class="essay-foot"><p class="practice-muted">草稿自动保存。提交后保留全文，不生成虚构评分。</p><button class="btn" type="button" id="export-essay">${icon('download')} 导出作文</button></div></section></div>`;
}
function cueCard(card){
  if(card.asset)return img(card.asset);
  const lines=String(card.text||'').split('\n').map(l=>l.replace(/^[•\-–]\s*/,'').trim()).filter(Boolean);
  const say=lines.findIndex(l=>/^you should say:?$/i.test(l));
  const title=lines[0]||'',points=say>=0?lines.slice(say+1):lines.slice(1);
  return `<h2 class="cue-title">${esc(title)}</h2>${say>=0?'<p class="cue-say">You should say:</p>':''}<ul class="cue-points">${points.map(l=>`<li>${esc(l)}</li>`).join('')}</ul>`;
}
function speaking(part){
  const disabled=state.submitted?'disabled':'';
  return `<div class="practice-grid practice-speaking"><article class="practice-paper"><span class="eyebrow">SPEAKING · PART ${part.part}</span>${part.cueCard?`${cueCard(part.cueCard)}<div class="speaking-tip">${icon('clock')}<p><strong>准备 1 分钟 · 作答 1–2 分钟</strong>练习建议：准备 1 分钟，再尝试连续表达 1–2 分钟。</p></div>`:`<h2>Let’s talk.</h2>${(part.topics||[]).map(t=>`<section class="practice-topic"><h3>${esc(t.title||'Discussion')}</h3><ol>${t.questions.map(q=>`<li>${esc(q.text)}</li>`).join('')}</ol></section>`).join('')}`}${sourceLink(part.source)}</article><section class="practice-editor"><div class="speaking-head"><h2>录音与作答</h2><span class="practice-muted">录音保存在当前浏览器</span></div><div class="practice-recording"><p id="record-status" role="status">录音仅保存在本机浏览器，可下载备份。</p><div class="practice-actions"><button class="btn primary" id="record" ${disabled}>${icon('mic')} 开始录音</button><button class="btn" id="stop-record" disabled>停止录音</button></div><div class="record-meter" aria-hidden="true"><span>音量</span><div id="record-meter"><i></i></div></div><div id="record-player"></div></div><div class="speaking-timers"><button class="speaking-timer" data-duration="60" ${disabled}>${icon('clock')}<span>准备计时<strong>01:00</strong></span></button><button class="speaking-timer" data-duration="120" ${disabled}>${icon('play')}<span>作答计时<strong>02:00</strong></span></button></div><label for="speaking-notes" class="speaking-notes-label">关键词与复盘笔记</label><textarea id="speaking-notes" style="min-height:180px" data-answer="notes-${part.part}" ${state.submitted?'readonly':''} placeholder="记下关键词，避免写完整稿件…">${esc(state.answers[`notes-${part.part}`]||'')}</textarea>${selfCheck(`speaking-${part.part}`,'speaking','回听自查')}</section></div>`;
}
function refreshCounters(){
  for(const a of document.querySelectorAll('[data-map]')){a.classList.toggle('answered',Boolean(state.answers[a.dataset.map]?.trim()));a.classList.toggle('flagged',state.flags.includes(a.dataset.map));}
  const output=document.querySelector('#word-count');if(output)output.textContent=`${wordCount(state.answers[groups()[state.index].id])} 词`;
}
function review(){
  if(!state.submitted)return '';
  if(skill==='reading'){
    const rows=archiveEntry?.readingResults||readingReport(data,state.answers),known=rows.filter(r=>r.correct!==null),correct=known.filter(r=>r.correct).length;
    const questions=new Map(readingItems(data).map(q=>[q.number,q]));
    const passages=new Map((data.passages||[]).flatMap(p=>(p.groups||[]).flatMap(g=>(g.questions||[]).map(q=>[q.number,p]))));
    return `<section class="practice-review"><h2>本次答题记录</h2><p>${data.verified?'已录入答案的题目':'暂定参考结果'}：${correct} / ${known.length}；${rows.length-known.length} 题答案待核对。未导入或未确认的题目不计为错误，不换算 Band。</p><p><a class="text-btn" href="/review.html">打开复盘清单 ↗</a></p>${rows.map(r=>{const q=questions.get(r.number),notes=(q?.explanation?.paraphraseSources||[]).map(item=>({...item,paperExcerpt:exactReadingExcerpt(passages.get(r.number)?.blocks,item.paraphrase)}));return `<details><summary>Q${r.number} · ${r.correct===null?'待核对':r.correct?'匹配参考答案':'需复盘'}</summary>${q?.prompt?`<p>题干：${esc(q.prompt)}</p>`:''}<p>你的答案：${esc(r.given||'未填写')}</p><p>参考答案：${esc(r.accepted?.join(' / ')||'尚未确认')}</p>${sourceLink(q?.source)}${renderSynonymNotes(notes)}${q?`<p><button class="btn" data-add-review="${r.number}">加入复盘清单</button></p>`:''}</details>`;}).join('')}</section>`;
  }
  return `<section class="practice-review"><h2>已保存 · 待自查</h2><p>${skill==='writing'?'检查任务回应、段落逻辑与表达。当前没有自动评分。':'回听录音，检查内容是否完整、表达是否连贯。当前没有自动评分。'}</p>${Object.entries(state.answers).map(([id,value])=>`<details><summary>${esc(id)}${skill==='writing'?` · ${wordCount(value)} 词`:''}</summary><pre>${esc(value)}</pre></details>`).join('')}</section>`;
}
function historyView(){
  try{
    const entries=historyEntries(key);
    return `<section class="practice-history"><h2>练习历史 <small>${entries.length}</small></h2>${entries.length?entries.map(e=>`<a class="history-row" href="/practice.html?book=${book}&test=${test}&skill=${skill}${mockRun?'&mockRun='+encodeURIComponent(mockRun.id):''}&attempt=${encodeURIComponent(e.id)}"><span>${esc(new Date(e.submitted).toLocaleString('zh-CN'))}</span><span>${e.paper?.verified?'已核验资料':'当时资料待核对'} · 查看记录 ↗</span></a>`).join(''):'<p>提交后的记录会保存在这里。</p>'}</section>`;
  }catch(error){return `<p class="practice-warning">${esc(error.message)}</p>`;}
}
async function render(){
  disposeReadingTools();
  const token=++renderToken;
  const items=groups(); if(!items?.length)throw new Error('本技能暂无可用内容');
  state.index=Math.max(0,Math.min(state.index,items.length-1));
  const item=items[state.index];
  main.innerHTML=`<div class="practice-intro"><div><span class="eyebrow">CAMBRIDGE ${book} / TEST ${test}</span><h1>${names[skill]} · ${skill[0].toUpperCase()+skill.slice(1)}</h1><span id="save-status" class="practice-muted">本机草稿 · ${state.submitted?'已提交':'未提交'}</span></div><div class="practice-clock">${icon('clock')}<output id="practice-clock" aria-label="剩余时间">${formatTime(practiceRemaining(state))}</output><button class="btn" id="clock-toggle" ${state.submitted?'disabled':''}>${state.deadline?'暂停计时':'开始计时'}</button></div></div>
    ${!data.verified?'<p class="practice-warning" data-unverified>本卷由 OCR 自动整理，尚未人工核对。遇到缺失题干或识别异常时，请对照原卷继续练习；答案待核对的题不计为错误。</p>':''}
    ${state.legacySnapshot?'<p class="practice-warning">这是旧版练习记录。旧答案已保留，题目与参考结果在本次迁移时保存，无法还原首次提交时的题库版本。</p>':''}
    ${skill==='reading'&&readingItems(data).length!==40?`<p class="practice-warning">当前导入 ${readingItems(data).length} 个题目记录，完整卷应有 40 个计分点；资料补齐后刷新即可加载。</p>`:''}
    <nav class="practice-tabs" aria-label="练习分段">${items.map((p,i)=>`<button class="btn" data-index="${i}" aria-pressed="${i===state.index}">${skill==='reading'?'Passage':skill==='writing'?'Task':'Part'} ${p.number||p.part||i+1}</button>`).join('')}</nav>
    ${skill==='reading'?reading(item):skill==='writing'?writing(item):speaking(item)}
    <div class="practice-actions"><button class="btn primary" id="submit-practice" ${state.submitted?'disabled':''}>${state.submitted?'本次已提交':'提交本次练习'}</button><button class="btn" id="export-practice">导出记录</button></div>${review()}${mockRun?'<p><a class="btn primary" href="/mock.html">返回整套进度 / 继续下一科</a></p>':''}
    <div class="practice-actions">${historyId?`<a class="btn primary" href="/practice.html?book=${book}&test=${test}&skill=${skill}">返回当前练习</a>`:state.submitted&&!mockRun?'<button class="btn" id="restart-practice">重新练习（保留旧记录）</button>':''}</div>${historyView()}`;
  refreshCounters();
  if(skill==='reading')disposeReadingTools=mountReadingTools({passage:item,index:state.index,state,save,message});
  mountExamWorkspace({skill,book,test,state,items,onNavigate:async index=>{state.index=index;save();await render();}});
  if(state.submitted)document.querySelectorAll('[data-flag]').forEach(button=>button.disabled=true);
  if(skill==='speaking'){
    try{const blob=await recordingStore(`${state.recordingNamespace}-part-${item.part}`);if(token===renderToken){recordBlob=blob||null;showRecording(blob);}}catch{if(token===renderToken)message('浏览器无法读取本地录音。新录音仍可下载备份。');}
  }
}
function showRecording(blob){
  if(recordURL)URL.revokeObjectURL(recordURL);recordURL=null;
  const target=document.querySelector('#record-player');if(!target)return;
  target.replaceChildren();if(!blob)return;
  recordURL=URL.createObjectURL(blob);const audio=document.createElement('audio');audio.controls=true;audio.src=recordURL;
  const download=document.createElement('a');download.href=recordURL;download.download=`c${book}-t${test}-speaking-part-${groups()[state.index].part}.${blob.type.includes('mp4')?'m4a':'webm'}`;download.textContent='下载本段录音';download.className='text-btn';
  target.append(audio,download);
}
// Live input level while recording, so it is clear the microphone is picking up sound.
let meter=null;
function startMeter(source){
  try{
    const ctx=new AudioContext(),analyser=ctx.createAnalyser();analyser.fftSize=512;
    ctx.createMediaStreamSource(source).connect(analyser);
    const data=new Uint8Array(analyser.fftSize),bar=document.querySelector('#record-meter i');
    meter={ctx,raf:0};document.querySelector('#record-meter')?.classList.add('is-live');
    const tick=()=>{analyser.getByteTimeDomainData(data);let peak=0;for(const v of data)peak=Math.max(peak,Math.abs(v-128));if(bar)bar.style.width=`${Math.min(100,peak/128*180)}%`;meter.raf=requestAnimationFrame(tick);};
    tick();
  }catch{meter=null;}
}
function stopMeter(){
  if(!meter)return;cancelAnimationFrame(meter.raf);meter.ctx.close().catch(()=>{});meter=null;
  const wrap=document.querySelector('#record-meter');wrap?.classList.remove('is-live');const bar=wrap?.querySelector('i');if(bar)bar.style.width='0';
}
async function startRecording(){
  if(pendingMic||finishingRecording||recorder?.state==='recording'||state.submitted)return;
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){message('当前浏览器不支持录音，请使用本机 Chrome 或 Edge。');return;}
  pendingMic=true;document.querySelector('#record').disabled=true;
  try{
    stream=await navigator.mediaDevices.getUserMedia({audio:true});
    const chunks=[];const part=groups()[state.index].part;
    recorder=new MediaRecorder(stream);
    stopPromise=new Promise(resolve=>{
      recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      recorder.onstop=async()=>{
        finishingRecording=true;
        stopMeter();stream?.getTracks().forEach(t=>t.stop());
        const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});
        recordBlob=blob;showRecording(blob);
        try{await recordingStore(`${state.recordingNamespace}-part-${part}`,blob);message('录音已保存至本机，可回听或下载。');}catch{message('录音保存失败，请立即点击下载本段录音。');}
        document.querySelector('#record').disabled=Boolean(state.submitted);document.querySelector('#stop-record').disabled=true;
        document.querySelector('#record-status').textContent='录音已结束';finishingRecording=false;resolve();
      };
    });
    recorder.onerror=()=>{message('录音中断，请检查麦克风。');if(recorder.state==='recording')recorder.stop();};
    recorder.start(1000);startMeter(stream);document.querySelector('#stop-record').disabled=false;document.querySelector('#record-status').textContent='正在录音 · 请完成后停止并保存';
  }catch{stopMeter();stream?.getTracks().forEach(t=>t.stop());message('未获得麦克风权限，仍可填写笔记。请在浏览器设置中允许麦克风后重试。');document.querySelector('#record').disabled=false;}
  finally{pendingMic=false;}
}
async function stopRecording(){if(recorder?.state==='recording'){finishingRecording=true;recorder.stop();await stopPromise;}else if(finishingRecording)await stopPromise;}
main.addEventListener('change',e=>{
  const id=e.target.dataset.selfCheck;if(!id||historyId)return;
  const value=Number(e.target.value),list=new Set((state.selfCheck||={})[id]||[]);
  e.target.checked?list.add(value):list.delete(value);state.selfCheck[id]=[...list].sort();save();
});
main.addEventListener('input',e=>{if(!e.target.dataset.answer||state.submitted)return;state.answers[e.target.dataset.answer]=e.target.value;save();refreshCounters();});
main.addEventListener('click',async e=>{
  const el=e.target.closest('button');if(!el||el.disabled)return;
  if(el.dataset.saveSynonym){try{saveSynonymWord(el.dataset.saveSynonym);el.textContent='已收藏到词书';el.disabled=true;message('已加入词书收藏，可在记单词页面复习。');}catch(error){message(error.message);}return;}
  if(el.dataset.addReview!==undefined){try{if(!state.submitted)throw Error('交卷后才能加入复盘');const number=Number(el.dataset.addReview);let found;for(const passage of data.passages||[])for(const group of passage.groups||[])for(const q of group.questions||[])if(q.number===number&&!found)found={q,group,passage};if(!found)throw Error('未找到原题');const entry=createReadingReviewItem(data,found.q,found.group,found.passage,state.answers[found.q.id]);const result=addReviewItem(entry);el.textContent='已在复盘清单';el.disabled=true;message(result.added?'已加入复盘清单，可随时复做。':'这道题已在复盘清单。');}catch(error){message(error.message);}return;}
  if(el.dataset.index!==undefined){if(pendingMic||finishingRecording||recorder?.state==='recording'){message('请先停止并保存录音，再切换 Part。');return;}state.index=Number(el.dataset.index);save();await render();}
  if(el.dataset.flag&&!state.submitted){const id=el.dataset.flag;state.flags=state.flags.includes(id)?state.flags.filter(v=>v!==id):[...state.flags,id];el.setAttribute('aria-pressed',String(state.flags.includes(id)));save();refreshCounters();}
  if(el.id==='clock-toggle'){if(state.deadline)pausePractice(state);else if(state.remaining>0)state.deadline=Date.now()+state.remaining*1000;save();el.textContent=state.deadline?'暂停计时':'开始计时';}
  if(el.dataset.duration){state.remaining=Number(el.dataset.duration);state.deadline=Date.now()+state.remaining*1000;save();document.querySelector('#clock-toggle').textContent='暂停计时';}
  if(el.id==='record')await startRecording();
  if(el.id==='stop-record')await stopRecording();
  if(el.id==='submit-practice'){if(pendingMic){message('请先完成麦克风授权。');return;}el.disabled=true;try{await stopRecording();await openSubmissionCheck({skill,paper:data,state,recordingStore,onNavigate:async(index,target)=>{state.index=index;save();await render();if(skill==='reading')document.querySelector('[data-reading-panel="questions"]')?.click();const input=target?document.getElementById('answer-'+target):document.querySelector(skill==='writing'?'#essay':'#record');input?.focus({preventScroll:true});input?.scrollIntoView({block:'center'});}});}finally{el.disabled=Boolean(state.submitted);}}
  if(el.id==='restart-practice'&&!historyId&&state.submitted){
    try{archivePractice(key,state,data);const response=await fetch(base+skill+'.json');if(!response.ok)throw new Error('Unable to load current paper');const latest=await response.json();if(latest.skill!==skill||latest.book!==book||latest.test!==test)throw new Error('Paper identity mismatch');const next=newPractice(skill,key);localStorage.setItem(key,JSON.stringify(next));state=next;data=latest;archiveEntry=null;await render();message('已开始新练习，旧记录已保留。');}catch(error){message('无法保存新练习，旧记录未替换。'+error.message);}return;
  }
  if(el.id==='export-essay'){
    const task=groups()[state.index],text=String(state.answers[task.id]||'');
    if(!text.trim()){message('这篇还没有内容，写一点再导出。');return;}
    const body=`Cambridge ${book} · Test ${test} · Writing Task ${task.number}
${wordCount(text)} words · ${new Date().toLocaleString('zh-CN')}

${text}
`;
    const url=URL.createObjectURL(new Blob([body],{type:'text/plain;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`c${book}-t${test}-writing-task${task.number}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    message('作文已导出为文本文件。');return;
  }
  if(el.id==='export-practice'){
    const url=URL.createObjectURL(new Blob([JSON.stringify({book,test,skill,sourceVerified:data.verified,session:state,readingResults:skill==='reading'?(archiveEntry?.readingResults||readingReport(data,state.answers)):undefined},null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download=`c${book}-t${test}-${skill}-practice.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
});
document.querySelector('#practice-submit').addEventListener('close',async e=>{
  if(e.target.returnValue!=='submit'||historyId||state.submitted)return;
  pausePractice(state);state.submitted=new Date().toISOString();
  try{archivePractice(key,state,data);if(!save())throw new Error('Current session save failed');await render();message('练习已提交，答案和当时的题目已保存。');}
  catch(error){state.submitted=null;message('提交保存失败，请导出记录后重试。'+error.message);}
});
setInterval(()=>{if(!data)return;const left=practiceRemaining(state);const clock=document.querySelector('#practice-clock');if(clock)clock.textContent=formatTime(left);if(state.deadline&&left===0){pausePractice(state);save();document.querySelector('#clock-toggle').textContent='计时结束';message('练习计时已结束，答案已保存。可继续检查后提交。');}},500);
window.addEventListener('beforeunload',e=>{if(pendingMic||recorder?.state==='recording'){e.preventDefault();e.returnValue='';}if(data){pausePractice(state);save();}});
window.addEventListener('pagehide',()=>{if(recorder?.state==='recording')recorder.stop();stream?.getTracks().forEach(t=>t.stop());if(data){pausePractice(state);save();}});
mountExamHeader({book,test,skill,mockRunId:mockRun?.id});
try{
  if(mockError)throw mockError;
  if(historyId){
    archiveEntry=historyEntries(key).find(e=>e.id===historyId);
    if(!archiveEntry)throw new Error('未找到这次练习记录');
    data=archiveEntry.paper;state=structuredClone(archiveEntry.session);
  }else{
    const response=await fetch(base+skill+'.json');if(!response.ok)throw new Error('本套资料尚未导入');data=await response.json();
    if(data.book!==book||data.test!==test||data.skill!==skill)throw new Error('试卷信息不匹配');
    if(state.submitted){archivePractice(key,state,data);archiveEntry=historyEntries(key).find(e=>e.id===state.attemptId);data=archiveEntry.paper;}
    save();
  }
  await render();
}catch(error){main.innerHTML=`<section class="practice-paper"><h1>暂时无法打开练习</h1><p>${esc(error.message)}</p><a class="btn" href="/#library/${book}/${test}">返回题库</a></section>`;}
