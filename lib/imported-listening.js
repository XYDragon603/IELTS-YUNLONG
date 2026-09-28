// Adapt independent scoring points to the existing grouped question controls.
export function adaptImportedListening(data, transcript) {
  if (!Number.isInteger(data.book) || ![1,2,3,4].includes(data.test) || data.skill !== 'listening') throw new Error('试卷身份不匹配');
  const seen = new Set();
  const segments = new Map(transcript.parts.flatMap(p => p.segments).map(s => [s.id, s]));
  const parts = data.parts.map(part => {
    const questions = [];
    for (const original of part.questions) {
      const numbers = original.type === 'multiple' ? original.numbers : [original.number];
      if (!Array.isArray(numbers) || !numbers.length) throw new Error('缺少题组编号');
      if (numbers.every(n => seen.has(n))) continue;
      if (numbers.some(n => seen.has(n))) throw new Error('计分点重叠');
      numbers.forEach(n => seen.add(n));
      questions.push({...original, numbers, options: original.options || [],
        evidence: (original.transcriptEvidence?.segmentIds || []).map(id => segments.get(id)).filter(Boolean)});
    }
    return {...part, questions};
  });
  if (seen.size !== 40 || Array.from({length:40}, (_, i) => i + 1).some(n => !seen.has(n))) throw new Error('计分点必须完整覆盖 1–40');
  return {...data, parts};
}

export function localResourceURL(path) {
  if (typeof path !== 'string' || !path.startsWith('IELTS/') || path.split('/').some(p => p === '..') || path.includes('\\')) throw new Error('无效的本地资源路径');
  return '/' + path.split('/').map(encodeURIComponent).join('/');
}
