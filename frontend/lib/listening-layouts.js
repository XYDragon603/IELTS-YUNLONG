import { escapeHTML as esc } from '../core.js';

// Original-paper layouts (table, notes, form, flow-chart) for listening completion groups.
// Text is transcribed from the paper; {{n}} marks the blank for question n.
const BLANK = /\{\{(\d+)\}\}/g;
const numberOf = q => q.numbers?.[0] ?? q.number;

function texts(layout) {
  if (layout.kind === 'table') return [...(layout.columns || []), ...(layout.rows || []).flat(2)];
  if (layout.kind === 'flow-chart') return (layout.steps || []).flat();
  return (layout.lines || []).map(l => typeof l === 'string' ? l : l.text);
}
export function layoutBlanks(layout) {
  return texts(layout).flatMap(t => [...String(t ?? '').matchAll(BLANK)].map(m => Number(m[1])));
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
  const line = text => esc(String(text ?? '')).replace(BLANK, (_, n) => blank(Number(n)));
  const range = `Questions ${Math.min(...layout.questionNumbers)}–${Math.max(...layout.questionNumbers)}`;
  // The range is shown only when the layout covers part of the section; the section heading already names a full one.
  const whole = layout.questionNumbers.length === part.questions.length;
  const head = `${whole ? '' : `<p class="layout-range">${range}</p>`}${layout.title ? `<h3 class="layout-title">${line(layout.title)}</h3>` : ''}`;
  if (layout.kind === 'table') {
    return `<section class="listening-layout-block">${head}<div class="layout-table-wrap"><table class="layout-table"><thead><tr>${layout.columns.map(c => `<th scope="col">${line(c)}</th>`).join('')}</tr></thead><tbody>${layout.rows.map(row => `<tr>${row.map(cell => `<td>${[cell].flat().map(l => `<div>${line(l)}</div>`).join('')}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section>`;
  }
  if (layout.kind === 'flow-chart') {
    return `<section class="listening-layout-block">${head}<ol class="layout-flow">${layout.steps.map(step => `<li>${[step].flat().map(l => `<div>${line(l)}</div>`).join('')}</li>`).join('')}</ol></section>`;
  }
  const lines = layout.lines.map(l => typeof l === 'string' ? { text: l } : l);
  return `<section class="listening-layout-block layout-${layout.kind}">${head}<div class="layout-lines">${lines.map(l => `<p class="${l.heading ? 'is-heading' : ''}${l.level ? ` level-${Math.min(3, l.level)}` : ''}${l.bullet ? ' is-bullet' : ''}">${line(l.text)}</p>`).join('')}</div></section>`;
}
