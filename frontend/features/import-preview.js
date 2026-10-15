import { escapeHTML as esc } from '../core.js';
import { mountExamHeader } from '../ui/exam-header.js';
import { adaptImportedListening, localResourceURL } from '../lib/imported-listening.js';
import { questionRenderer } from '../ui/components.js';
import { questionScore, questionWeight, answeredWeight } from '../lib/study-model.js';
import { renderSynonymNotes, saveSynonymWord } from '../lib/synonym-notes.js';
import { addReviewItem, createListeningReviewItem } from '../lib/review-queue.js';
import { listeningRunKey, requireMockStage } from '../lib/mock-run.js';
import { assetURL } from '../lib/practice-model.js';
import { usableLayouts, layoutHTML } from '../lib/listening-layouts.js';

const params=new URLSearchParams(location.search);
const book=/^\d+$/.test(params.get('book')||'')?Number(params.get('book')):18;
const testNumber=/^[1-4]$/.test(params.get('test')||'')?Number(params.get('test')):1;
const mockRunId=params.get('mockRun');
let mockRun=null;
let mockError=null;
try {if(mockRunId){mockRun=requireMockStage(mockRunId,'listening');if(mockRun.book!==book||mockRun.test!==testNumber)throw Error('整套练习与试卷不匹配');}} catch(error){mockError=error;}
const key = mockRun?listeningRunKey(mockRun):`ielts-c${book}-t${testNumber}-import-preview-v1`;
document.querySelector('h1').textContent=`Cambridge ${book} · Test ${testNumber} · Listening`;
document.title=`IELTS Studio · Cambridge ${book} Test ${testNumber} 听力`;
mountExamHeader({book,test:testNumber,skill:'listening',mockRunId:mockRun?.id,showSkills:!mockRun});
if(mockRun)document.querySelector('.note-box').textContent='整套练习 · 本科进度与单科练习分别保存。提交后可查看参考答案，返回整套进度可继续阅读。';
const status = document.querySelector('#preview-status');
const content = document.querySelector('#preview-content');
const historyKey = key + '-history';
const attemptParam = params.get('attempt');
const fresh = () => ({part:1, answers:{}, flags:[], audio:{}, submitted:false});
let test, layouts = [], state = fresh(), viewOnly = false;
function history() { try { const v = JSON.parse(localStorage.getItem(historyKey) || '[]'); return Array.isArray(v) ? v : []; } catch { return []; } }
// Each submission is kept in the history so a new attempt never overwrites it.
function archive() {
  if (!state.submitted || mockRun) return;
  state.attemptId ||= crypto.randomUUID();
  if (typeof state.submitted !== 'string') state.submitted = new Date().toISOString();
  const entries = history().filter(e => e.id !== state.attemptId);
  localStorage.setItem(historyKey, JSON.stringify([{id:state.attemptId, submitted:state.submitted, session:structuredClone(state)}, ...entries]));
}
function restart() {
  try { archive(); content.querySelector('audio')?.pause(); state = fresh(); save(); render(); window.scrollTo(0, 0); status.textContent = '已开始新练习，旧记录保留在练习历史中。'; }
  catch (error) { status.textContent = '无法开始新练习，旧记录未替换。' + error.message; }
}
let storageError = false;
function save() {
  if (viewOnly) return;
  try { localStorage.setItem(key, JSON.stringify(state)); storageError = false; }
  catch { storageError = true; status.textContent = '保存失败，请保留页面并导出答题记录。'; }
}
function questions() { return test.parts.flatMap(p => p.questions); }
function updateStatus() {
  if (storageError) return;
  const count = questions().reduce((n,q) => n + answeredWeight(q, state.answers[q.id]), 0);
  status.textContent = `已作答 ${count} / 40 · ${mockRun?'整套练习':'预览'}进度自动保存`;
}
// Right-hand answer progress: question numbers grouped by part; answered and flagged states.
function progressPanel() {
  const done = q => answeredWeight(q, state.answers[q.id]) > 0;
  const total = questions().reduce((n,q) => n + answeredWeight(q, state.answers[q.id]), 0);
  return `<h2>答题进度 <strong>${total} / 40</strong></h2>${test.parts.map(p => `<section class="progress-part${p.number===state.part?' is-current':''}"><h3>Part ${p.number}<span>${p.questions.filter(done).length} / ${p.questions.length}</span></h3><div class="progress-grid">${p.questions.map(q => { const label = q.numbers?.join('–') || q.number; return `<button type="button" class="${done(q)?'answered':''}${state.flags.includes(q.id)?' flagged':''}" data-jump-q="${esc(q.id)}" data-jump-part="${p.number}" aria-label="第 ${label} 题，${done(q)?'已作答':'未作答'}${state.flags.includes(q.id)?'，已标记':''}">${label}</button>`; }).join('')}</div></section>`).join('')}<p class="progress-legend"><span><i class="is-answered"></i>已作答</span><span><i></i>未作答</span><span><i class="is-flagged"></i>标记</span></p>`;
}
function updateProgress() { const panel = document.querySelector('#listening-progress'); if (panel) panel.innerHTML = progressPanel(); }
function saveAudio() {
  const audio = content.querySelector('audio');
  if (audio && Number.isFinite(audio.currentTime)) { state.audio[state.part] = audio.currentTime; save(); }
}
function render() {
  const part = test.parts.find(p => p.number === state.part);
  const navigation = test.parts.map(p => `<button class="btn" data-part="${p.number}" aria-pressed="${p.number===state.part}">Part ${p.number}</button>`).join('');
  const paper = localResourceURL(test.sources.paper.path);
  const notes = [...new Set([part.instruction, ...(part.groups || []).map(g => g.instruction), part.context].map(t => String(t || '').trim()).filter(Boolean))];
  const assets=book===12?[]:(part.assets||[part.asset].filter(Boolean));
  // An image whose questions are all answered inside a transcribed layout stays available, folded, for checking against the paper.
  const laidOut=new Set(usableLayouts(layouts,part).flatMap(l=>l.questionNumbers));
  const covered=asset=>asset.questionNumbers?.length&&asset.questionNumbers.every(n=>laidOut.has(n));
  const figures=assets.map(asset=>{const q=part.questions.find(q=>q.numbers?.includes(asset.questionNumbers?.[0]));const html=`<figure class="practice-group-asset"><img class="practice-asset" src="${esc(assetURL(`/resources/cambridge/c${book}/test-${testNumber}/`,asset.asset))}" alt="${esc(asset.alt||'本段原卷图题')}" loading="lazy"><figcaption>${esc(asset.alt||'原卷图题')} · <a href="${esc(paper)}#page=${asset.sourcePdfPage}" target="_blank" rel="noopener">原卷第 ${asset.sourcePdfPage} 页 ↗</a>${q?` <button class="text-btn" data-jump-q="${esc(q.id)}" data-jump-part="${state.part}">跳至图题 ${q.number}</button>`:''}</figcaption></figure>`;;return covered(asset)?`<details class="layout-source-image"><summary>原卷图片（对照）</summary>${html}</details>`:html}).join('');
  content.innerHTML = `<div class="listening-bar"><nav class="practice-tabs listening-parts" aria-label="听力分段">${navigation}</nav>
    <audio controls preload="metadata" src="${esc(localResourceURL(test.audio[state.part].path))}"></audio>
    <a class="text-btn" target="_blank" rel="noopener" href="${esc(paper)}#page=${part.questions[0].source.pdfPage}">对照原卷 ↗</a>${state.submitted&&!viewOnly&&!mockRun?'<button class="btn primary" id="restart-preview" title="旧记录会保留在练习历史中">重新练习</button>':''}</div>
    <div class="listening-layout"><section class="listening-sheet"><h2>Part ${state.part} · ${esc(part.title)}</h2>${notes.map(t => `<p class="listening-instruction">${esc(t)}</p>`).join('')}
    ${figures}${questionsHTML(part)}</section><aside class="listening-progress" id="listening-progress" aria-label="答题进度">${progressPanel()}</aside></div>
    <div class="preview-actions">${viewOnly?`<a class="btn primary" href="/import-preview.html?book=${book}&test=${testNumber}">返回当前练习</a>`:state.submitted?'':'<button class="btn primary" id="submit-preview">提交并查看暂定结果</button>'}<button class="btn" id="export-preview">导出答题记录</button>${historyView()}</div>
    <section id="preview-results" aria-live="polite"></section>`;
  const audio = content.querySelector('audio');
  audio.addEventListener('loadedmetadata', () => { audio.currentTime = Math.min(state.audio[state.part] || 0, Number.isFinite(audio.duration) ? audio.duration : Infinity); });
  audio.addEventListener('pause', saveAudio);
  audio.addEventListener('seeked', saveAudio);
  audio.addEventListener('error', () => { status.textContent = '音频加载失败，请检查本地 MP3。已保存的答案仍可继续填写。'; });
  updateStatus();
  if (viewOnly || state.submitted) content.querySelectorAll('.listening-sheet input, .listening-sheet select, .listening-sheet textarea, .listening-sheet [data-study=flag]').forEach(el => el.disabled = true);
  if (viewOnly) { status.textContent = `历史记录 · ${new Date(state.submitted).toLocaleString('zh-CN')} · 只读`; }
  if (state.submitted) renderResults();
}
function historyView() {
  if (mockRun) return '';
  const entries = history();
  return entries.length ? `<details class="listening-history"><summary>练习历史 · ${entries.length} 次</summary>${entries.map(e => `<a class="history-row" href="/import-preview.html?book=${book}&test=${testNumber}&attempt=${encodeURIComponent(e.id)}"><span>${esc(new Date(e.submitted).toLocaleString('zh-CN'))}</span><span>查看记录 ↗</span></a>`).join('')}</details>` : '';
}
// Questions covered by an original-paper layout are answered inside that table or notes block.
function questionsHTML(part) {
  const used = usableLayouts(layouts, part);
  const owner = new Map(used.flatMap(l => l.questionNumbers.map(n => [n, l])));
  const done = new Set();
  return part.questions.map(q => {
    const layout = owner.get(q.numbers?.[0] ?? q.number);
    if (!layout) return questionRenderer(q, state.answers, state.flags);
    if (done.has(layout)) return '';
    done.add(layout); return layoutHTML(layout, part, state.answers);
  }).join('');
}
function renderResults() {
  const score = questions().reduce((n,q) => n + (questionScore(q,state.answers[q.id]) || 0),0);
  document.querySelector('#preview-results').innerHTML = `<h2>暂定参考分：${score} / 40</h2><p>分数仅供个人复习参考，不换算 Band。</p><p>${mockRun?'<a class="btn primary" href="/mock.html">返回整套进度，继续阅读</a> ':''}<a class="text-btn" href="/review.html">打开复盘清单 ↗</a></p>` + questions().map(q => `<details><summary>Q${q.numbers.join('–')} · ${questionScore(q,state.answers[q.id]) ?? '待核对'} / ${questionWeight(q)}</summary>
    <p>你的答案：${esc([state.answers[q.id] || '未作答'].flat().join(', '))}</p><p>导入参考答案：${esc(q.accepted.join(' / '))}</p>
    <a target="_blank" rel="noopener" href="${esc(localResourceURL(test.sources.paper.path))}#page=${q.answer.sourcePdfPage}">核对原卷答案页 ↗</a>
    ${q.evidence.length ? q.evidence.map(s => `<blockquote>${esc(s.text)}</blockquote><small>OCR 听力稿 · PDF ${s.sourcePdfPage} 页</small>`).join('') : '<p>尚无听力证据。</p>'}${renderSynonymNotes(q.explanation?.paraphraseSources)}<p><button class="btn" data-add-review="${esc(q.id)}">加入复盘清单</button></p></details>`).join('');
}
content.addEventListener('input', e => {
  const id = e.target.dataset.response;
  if (!id || viewOnly || state.submitted) return;
  const q = questions().find(q => q.id === id);
  if (!q) return;
  if (q.type === 'multiple') {
    let values = Array.isArray(state.answers[id]) ? [...state.answers[id]] : [];
    if (e.target.checked) {
      if (values.length >= q.maxChoices) { e.target.checked = false; status.textContent = `本题最多选择 ${q.maxChoices} 项`; return; }
      values.push(e.target.value);
    } else values = values.filter(v => v !== e.target.value);
    state.answers[id] = values;
  } else state.answers[id] = e.target.value;
  document.querySelector('#preview-results').innerHTML = '';
  save(); updateStatus(); updateProgress();
});
content.addEventListener('click', e => {
  const el = e.target.closest('button');
  if (!el) return;
  if (el.dataset.saveSynonym) { try { saveSynonymWord(el.dataset.saveSynonym); el.textContent='已收藏到词书'; el.disabled=true; status.textContent='已加入词书收藏，可在记单词页面复习。'; } catch (error) { status.textContent=error.message; } return; }
  if (el.dataset.addReview) { try { if(!state.submitted)throw Error('交卷后才能加入复盘'); const q=questions().find(item=>item.id===el.dataset.addReview),part=test.parts.find(item=>item.questions.some(question=>question.id===q?.id));if(!q||!part)throw Error('未找到原题');const result=addReviewItem(createListeningReviewItem(test,q,part,state.answers[q.id]));el.textContent='已在复盘清单';el.disabled=true;status.textContent=result.added?'已加入复盘清单，可随时复做。':'这道题已在复盘清单。'; } catch(error){status.textContent=error.message;} return; }
  if (el.dataset.jumpQ) {
    const target = Number(el.dataset.jumpPart);
    if (target !== state.part) { saveAudio(); content.querySelector('audio')?.pause(); state.part = target; save(); render(); }
    const question = document.getElementById(`study-q-${el.dataset.jumpQ}`);
    question?.scrollIntoView({block:'center'});
    question?.querySelector('input,select,textarea')?.focus({preventScroll:true});
    return;
  }
  if (el.dataset.part) { saveAudio(); content.querySelector('audio')?.pause(); state.part = Number(el.dataset.part); save(); render(); }
  if (el.dataset.study === 'flag') {
    const id = el.dataset.q;
    state.flags = state.flags.includes(id) ? state.flags.filter(v=>v!==id) : [...state.flags,id];
    el.setAttribute('aria-pressed', String(state.flags.includes(id))); el.classList.toggle('selected',state.flags.includes(id)); save(); updateProgress();
  }
  if (el.id === 'restart-preview') { restart(); return; }
  if (el.id === 'submit-preview') { state.submitted = new Date().toISOString(); try { archive(); } catch {} save(); render(); document.querySelector('#preview-results').scrollIntoView(); }
  if (el.id === 'export-preview') {
    const url = URL.createObjectURL(new Blob([JSON.stringify({testId:test.id,verified:false,...state},null,2)],{type:'application/json'}));
    const a = document.createElement('a'); a.href=url; a.download=`c${book}-t${testNumber}-listening-preview.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
});
window.addEventListener('pagehide', saveAudio);
document.addEventListener('visibilitychange', () => { if (document.hidden) saveAudio(); });
try {
  if(book===12)throw new Error('剑雅 12 按要求暂留空，等待可靠原卷后再开放。');
  if(mockError)throw mockError;
  const base = `/resources/cambridge/c${book}/test-${testNumber}/`;
  const load = async file => { const r=await fetch(base+file); if(!r.ok) throw new Error(`${file}: HTTP ${r.status}`); return r.json(); };
  const [data,transcript,layoutFile] = await Promise.all([load('listening.json'),load('audioscript.json'),fetch(base+'listening-layouts.json').then(r=>r.ok?r.json():null).catch(()=>null)]);
  if(layoutFile?.book===book&&layoutFile?.test===testNumber&&layoutFile.source?.sha256===data.sources?.paper?.sha256&&Array.isArray(layoutFile.layouts))layouts=layoutFile.layouts;
  if(data.book!==book||data.test!==testNumber)throw new Error('Paper identity mismatch');
  test=adaptImportedListening(data,transcript);
  try { const saved=JSON.parse(localStorage.getItem(key)); if(saved && [1,2,3,4].includes(saved.part) && saved.answers && Array.isArray(saved.flags) && saved.audio) state=saved; } catch {}
  if (attemptParam) {
    const entry = history().find(e => e.id === attemptParam);
    if (!entry) throw new Error('未找到这次练习记录');
    state = structuredClone(entry.session); viewOnly = true;
  } else if (state.submitted) {
    archive(); save();
    if (params.get('new') === '1' && !mockRun) { state = fresh(); save(); }
  }
  if (params.has('new')) { params.delete('new'); window.history.replaceState(null, '', location.pathname + '?' + params); }
  render();
} catch(e) { status.textContent=`无法载入导入预览：${e.message}`; }
