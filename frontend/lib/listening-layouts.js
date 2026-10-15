import { escapeHTML as esc } from '../core.js';

// Original-paper layouts (table, notes, form, flow-chart) for listening completion groups.
// Text is transcribed from the paper; {{n}} marks the blank for question n.
const BLANK = /\{\{(\d+)\}\}/g;
const numberOf = q => q.numbers?.[0] ?? q.number;

function texts(layout) {
  if (layout.kind === 'table') return [...(layout.columns || []), ...(layout.rows || []).flat(2)];
  if (layout.kind === 'form') return (layout.rows || []).flat(2);
  if (layout.kind === 'flow-chart') return (layout.steps || []).flat();
  return (layout.lines || []).map(l => typeof l === 'string' ? l : l.text);
}
export function layoutBlanks(layout) {
  return texts(layout).flatMap(t => [...String(t ?? '').matchAll(BLANK)].map(m => Number(m[1])));
}
// A short source-text excerpt for review cards when an inline completion
// question has no standalone OCR prompt. Mark the requested blank when a
// sentence contains more than one answer field.
export function layoutPrompt(layout, number) {
  if (!layout || !Number.isInteger(Number(number))) return null;
  const token = `{{${Number(number)}}}`;
  const source = texts(layout).map(value => String(value ?? '')).find(value => value.includes(token));
  if (!source) return null;
  const index = source.indexOf(token);
  let start = 0, end = source.length;
  if (source.length > 170) {
    const before = source.slice(0, index);
    const prior = [...before.matchAll(/[.!?]\s+/g)].at(-1);
    if (prior) start = prior.index + prior[0].length;
    const following = /[.!?](?:\s|$)/.exec(source.slice(index + token.length));
    if (following) end = index + token.length + following.index + 1;
    if (end - start > 170) {
      start = Math.max(start, index - 70);
      end = Math.min(end, index + token.length + 80);
      if (start > 0) { const nextSpace = source.indexOf(' ', start); if (nextSpace >= 0) start = nextSpace + 1; }
      if (end < source.length) { const priorSpace = source.lastIndexOf(' ', end); if (priorSpace >= start) end = priorSpace; }
    }
  }
  const excerpt = source.slice(start, end).replace(new RegExp(`\\{\\{${Number(number)}\\}\\}`, 'g'), `【${number}】____`)
    .replace(BLANK, '____').replace(/\s+/g, ' ').trim();
  return `${start ? '…' : ''}${excerpt}${end < source.length ? '…' : ''}`;
}
// A layout is used only when its blanks are exactly its declared questions and each is a single text question
// in this part; otherwise the questions fall back to the plain list so nothing becomes unanswerable.
export function usableLayouts(layouts, part) {
  const byNumber = new Map(part.questions.map(q => [numberOf(q), q]));
  return (layouts || []).filter(layout => {
    if (layout?.part !== part.number || !['table', 'notes', 'form', 'flow-chart'].includes(layout.kind)) return false;
    const blanks = layoutBlanks(layout), declared = layout.questionNumbers || [];
    if (!blanks.length || blanks.length !== new Set(blanks).size || blanks.length !== declared.length) return false;
    return declared.every(n => blanks.includes(n) && byNumber.get(n)?.type === 'text' && (byNumber.get(n).numbers?.length ?? 1) === 1);
  });
}
export function layoutHTML(layout, part, answers = {}) {
  const byNumber = new Map(part.questions.map(q => [numberOf(q), q]));
  const blank = n => {
    const q = byNumber.get(n), id = `study-${q.id}`;
    return `<span class="layout-blank" id="study-q-${esc(q.id)}"><label class="sr-only" for="${esc(id)}">第 ${n} 题</label><input id="${esc(id)}" type="text" data-response="${esc(q.id)}" value="${esc(answers[q.id] || '')}" placeholder="${n}" autocomplete="off" spellcheck="false"></span>`;
  };
  // The range is shown only when the layout covers part of the section; the section heading already names a full one.
  return renderLayout(layout, { blank, showRange: layout.questionNumbers.length !== part.questions.length });
}
// Shared renderer: `blank(n)` returns the answer control for question n (listening and reading bind answers differently).
export function renderLayout(layout, { blank, showRange = false }) {
  const line = text => esc(String(text ?? '')).replace(BLANK, (_, n) => blank(Number(n)));
  const range = `Questions ${Math.min(...layout.questionNumbers)}–${Math.max(...layout.questionNumbers)}`;
  const head = `${showRange ? `<p class="layout-range">${range}</p>` : ''}${layout.title ? `<h3 class="layout-title">${line(layout.title)}</h3>` : ''}`;
  if (layout.kind === 'table') {
    return `<section class="listening-layout-block">${head}<div class="layout-table-wrap"><table class="layout-table">${layout.columns.some(c => String(c).trim()) ? `<thead><tr>${layout.columns.map(c => `<th scope="col">${line(c)}</th>`).join('')}</tr></thead>` : ''}<tbody>${layout.rows.map(row => `<tr>${row.map(cell => `<td>${[cell].flat().map(l => `<div>${line(l)}</div>`).join('')}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section>`;
  }
  // A form is a two-column label/value grid; a plain string row is a section heading across both columns.
  if (layout.kind === 'form') {
    return `<section class="listening-layout-block layout-form">${head}<div class="layout-table-wrap"><table class="layout-table layout-form-table"><tbody>${layout.rows.map(row => typeof row === 'string' ? `<tr class="form-heading"><th colspan="2" scope="colgroup">${line(row)}</th></tr>` : `<tr><th scope="row">${[row[0]].flat().map(l => `<div>${line(l)}</div>`).join('')}</th><td>${[row[1]].flat().map(l => `<div>${line(l)}</div>`).join('')}</td></tr>`).join('')}</tbody></table></div></section>`;
  }
  if (layout.kind === 'flow-chart') {
    return `<section class="listening-layout-block">${head}<ol class="layout-flow">${layout.steps.map(step => `<li>${[step].flat().map(l => `<div>${line(l)}</div>`).join('')}</li>`).join('')}</ol></section>`;
  }
  const lines = layout.lines.map(l => typeof l === 'string' ? { text: l } : l);
  return `<section class="listening-layout-block layout-${layout.kind}">${head}<div class="layout-lines">${lines.map(l => `<p class="${l.heading ? 'is-heading' : ''}${l.level ? ` level-${Math.min(3, l.level)}` : ''}${l.bullet ? ' is-bullet' : ''}">${line(l.text)}</p>`).join('')}</div></section>`;
}
