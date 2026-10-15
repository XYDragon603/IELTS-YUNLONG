import {escapeHTML as esc} from '../core.js';
import {localResourceURL} from './imported-listening.js';

export function exactReadingExcerpt(blocks = [], phrase = '') {
  if (typeof phrase !== 'string' || !phrase.trim() || /[⇋=/]/.test(phrase)) return null;
  const needle=phrase.trim().replace(/\s+/g,' ').toLocaleLowerCase();
  if (needle.length < 4) return null;
  const matches=[];
  for(const block of blocks){
    const text=block.text?.replace(/\s+/g,' ');
    if(!text)continue;
    const at=text.toLocaleLowerCase().indexOf(needle);
    if(at>=0)matches.push({text:text.slice(Math.max(0,at-65),Math.min(text.length,at+needle.length+65)),source:block.source});
  }
  return matches.length===1?matches[0]:null;
}

export function renderSynonymNotes(items = []) {
  if (!Array.isArray(items) || !items.length) return '';
  return `<section class="synonym-notes"><h4>题目同义表达 · 资料待校对</h4><p class="practice-muted">以下摘自本地同义替换资料，请结合题干与原文判断具体语境。</p>${items.map(item => {
    const page = item.sourcePages?.[0];
    let link = '';
    try {
      if (Number.isInteger(page) && page > 0 && item.sourcePath) link = `<a class="text-btn" href="${esc(localResourceURL(item.sourcePath))}#page=${page}" target="_blank" rel="noopener">资料 PDF 第 ${page} 页 ↗</a>`;
    } catch {}
    return `<div class="synonym-note"><p><strong>${esc(item.term || '')}</strong> ⇋ ${esc(item.paraphrase || '')}</p>${item.meaning?`<small>${esc(item.meaning)}</small>`:'<small>中文释义尚未提供</small>'}${item.paperExcerpt?`<blockquote>原卷文章中逐字匹配：${esc(item.paperExcerpt.text)}</blockquote>`:''}<div class="synonym-actions">${link}${item.wordId?`<button class="text-btn" type="button" data-save-synonym="${esc(item.wordId)}">收藏到词书</button>`:''}</div>${item.needsReview?.length?'':''}</div>`;
  }).join('')}</section>`;
}

export function saveSynonymWord(id, storage = localStorage) {
  if (!/^[a-f0-9]{20}$/.test(id)) throw new Error('无效的词卡编号');
  const key = 'ielts-vocabulary-v1';
  const raw = storage.getItem(key);
  let state;
  try { state = raw ? JSON.parse(raw) : {version:1,progress:{},limit:20,random:true,session:null}; }
  catch { throw new Error('词书进度无法读取，已保留原记录'); }
  if (state.version !== 1 || !state.progress || typeof state.progress !== 'object' || Array.isArray(state.progress)) throw new Error('词书进度格式异常，已保留原记录');
  state.progress[id] = {...state.progress[id],starred:true};
  storage.setItem(key, JSON.stringify(state));
}
