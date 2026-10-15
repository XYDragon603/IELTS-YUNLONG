import { escapeHTML as esc } from '../core.js';
import { mountExamHeader } from '../ui/exam-header.js';
import { adaptImportedListening, localResourceURL } from '../lib/imported-listening.js';
import { questionRenderer } from '../ui/components.js';
import { questionScore, questionWeight, answeredWeight } from '../lib/study-model.js';
import { renderSynonymNotes, saveSynonymWord } from '../lib/synonym-notes.js';
import { addReviewItem, createListeningReviewItem } from '../lib/review-queue.js';
import { listeningRunKey, requireMockStage } from '../lib/mock-run.js';

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
let test, state = {part:1, answers:{}, flags:[], audio:{}, submitted:false};
let storageError = false;
function save() {
  try { localStorage.setItem(key, JSON.stringify(state)); storageError = false; }
  catch { storageError = true; status.textContent = '保存失败，请保留页面并导出答题记录。'; }
}
function questions() { return test.parts.flatMap(p => p.questions); }
function updateStatus() {
  if (storageError) return;
  const count = questions().reduce((n,q) => n + answeredWeight(q, state.answers[q.id]), 0);
  status.textContent = `已作答 ${count} / 40 · ${mockRun?'整套练习':'预览'}进度自动保存`;
}
function saveAudio() {
  const audio = content.querySelector('audio');
  if (audio && Number.isFinite(audio.currentTime)) { state.audio[state.part] = audio.currentTime; save(); }
}
function render() {
  const part = test.parts.find(p => p.number === state.part);
  const navigation = test.parts.map(p => `<button class="btn" data-part="${p.number}" aria-pressed="${p.number===state.part}">Part ${p.number}</button>`).join('');
  const paper = localResourceURL(test.sources.paper.path);
  const notes = [...new Set([part.instruction, ...(part.groups || []).map(g => g.instruction), part.context].map(t => String(t || '').trim()).filter(Boolean))];
  content.innerHTML = `<div class="listening-bar"><nav class="practice-tabs listening-parts" aria-label="听力分段">${navigation}</nav>
    <audio controls preload="metadata" src="${esc(localResourceURL(test.audio[state.part].path))}"></audio>
    <a class="text-btn" target="_blank" rel="noopener" href="${esc(paper)}#page=${part.questions[0].source.pdfPage}">对照原卷 ↗</a></div>
    <section class="listening-sheet"><h2>Part ${state.part} · ${esc(part.title)}</h2>${notes.map(t => `<p class="listening-instruction">${esc(t)}</p>`).join('')}
    ${part.questions.map(q => questionRenderer(q, state.answers, state.flags)).join('')}</section>
    <div class="preview-actions"><button class="btn primary" id="submit-preview">提交并查看暂定结果</button><button class="btn" id="export-preview">导出答题记录</button></div>
    <section id="preview-results" aria-live="polite"></section>`;
  const audio = content.querySelector('audio');
  audio.addEventListener('loadedmetadata', () => { audio.currentTime = Math.min(state.audio[state.part] || 0, Number.isFinite(audio.duration) ? audio.duration : Infinity); });
  audio.addEventListener('pause', saveAudio);
  audio.addEventListener('seeked', saveAudio);
  audio.addEventListener('error', () => { status.textContent = '音频加载失败，请检查本地 MP3。已保存的答案仍可继续填写。'; });
  updateStatus();
  if (state.submitted) renderResults();
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
  if (!id) return;
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
  state.submitted = false;
  document.querySelector('#preview-results').innerHTML = '';
  save(); updateStatus();
});
content.addEventListener('click', e => {
  const el = e.target.closest('button');
  if (!el) return;
  if (el.dataset.saveSynonym) { try { saveSynonymWord(el.dataset.saveSynonym); el.textContent='已收藏到词书'; el.disabled=true; status.textContent='已加入词书收藏，可在记单词页面复习。'; } catch (error) { status.textContent=error.message; } return; }
  if (el.dataset.addReview) { try { if(!state.submitted)throw Error('交卷后才能加入复盘'); const q=questions().find(item=>item.id===el.dataset.addReview),part=test.parts.find(item=>item.questions.some(question=>question.id===q?.id));if(!q||!part)throw Error('未找到原题');const result=addReviewItem(createListeningReviewItem(test,q,part,state.answers[q.id]));el.textContent='已在复盘清单';el.disabled=true;status.textContent=result.added?'已加入复盘清单，可随时复做。':'这道题已在复盘清单。'; } catch(error){status.textContent=error.message;} return; }
  if (el.dataset.part) { saveAudio(); content.querySelector('audio')?.pause(); state.part = Number(el.dataset.part); save(); render(); }
  if (el.dataset.study === 'flag') {
    const id = el.dataset.q;
    state.flags = state.flags.includes(id) ? state.flags.filter(v=>v!==id) : [...state.flags,id];
    el.setAttribute('aria-pressed', String(state.flags.includes(id))); el.classList.toggle('selected',state.flags.includes(id)); save();
  }
  if (el.id === 'submit-preview') { state.submitted = true; save(); renderResults(); document.querySelector('#preview-results').scrollIntoView(); }
  if (el.id === 'export-preview') {
    const url = URL.createObjectURL(new Blob([JSON.stringify({testId:test.id,verified:false,...state},null,2)],{type:'application/json'}));
    const a = document.createElement('a'); a.href=url; a.download=`c${book}-t${testNumber}-listening-preview.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
});
window.addEventListener('pagehide', saveAudio);
document.addEventListener('visibilitychange', () => { if (document.hidden) saveAudio(); });
try {
  if(mockError)throw mockError;
  const base = `/resources/cambridge/c${book}/test-${testNumber}/`;
  const load = async file => { const r=await fetch(base+file); if(!r.ok) throw new Error(`${file}: HTTP ${r.status}`); return r.json(); };
  const [data,transcript] = await Promise.all([load('listening.json'),load('audioscript.json')]);
  if(data.book!==book||data.test!==testNumber)throw new Error('Paper identity mismatch');
  test=adaptImportedListening(data,transcript);
  try { const saved=JSON.parse(localStorage.getItem(key)); if(saved && [1,2,3,4].includes(saved.part) && saved.answers && Array.isArray(saved.flags) && saved.audio) state=saved; } catch {}
  render();
} catch(e) { status.textContent=`无法载入导入预览：${e.message}`; }
