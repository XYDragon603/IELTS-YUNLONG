export function bookNumber(file) {
  const match = file.match(/(?:剑雅?|IELTS|剑桥雅思(?:真题)?)[^\d/]*?(\d{1,2})(?!\d)/i) || file.match(/【(\d{1,2})】/);
  const n = Number(match?.[1]);
  return n >= 4 && n <= 20 ? n : null;
}

export function audioIdentity(file) {
  if (!file.toLowerCase().endsWith('.mp3') || /G类/.test(file)) return null;
  const parts = file.split('/');
  const book = parts.map(p => p.match(/^剑(?:雅)?(\d+)(?:\D|$)/)?.[1]).find(Boolean);
  const name = parts.at(-1);
  let match = name.match(/(?:test|t)\s*(\d+)[\s._-]*(?:section|secton|part|audio|s|p)\s*(\d+)/i);
  if (!match) match = name.match(/^\d+-(\d+)-(\d+)\.mp3$/i);
  if (!book || !match) return null;
  // Cambridge 12's supplied audio uses the publisher's Test 5–8 numbering.
  const originalTest = Number(match[1]);
  const test = Number(book) === 12 && originalTest >= 5 ? originalTest - 4 : originalTest;
  const part = Number(match[2]);
  if (test < 1 || test > 4 || part < 1 || part > 4) return null;
  return { book: Number(book), test, part, originalTest };
}

export const resourceURL = file => '/' + file.split('/').map(encodeURIComponent).join('/');
