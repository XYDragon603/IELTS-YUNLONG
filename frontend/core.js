export const SECTIONS = [
  { id: 'listening', name: '听力', english: 'Listening', duration: 5 * 60, icon: 'headphones', detail: '5 道填空题', color: 'green' },
  { id: 'reading', name: '阅读', english: 'Reading', duration: 8 * 60, icon: 'book', detail: '5 道判断题', color: 'blue' },
  { id: 'writing', name: '写作', english: 'Writing', duration: 10 * 60, icon: 'pen', detail: '1 篇议论文', color: 'orange' },
  { id: 'speaking', name: '口语', english: 'Speaking', duration: 3 * 60, icon: 'mic', detail: '1 道话题卡', color: 'purple' },
];

export function createAttempt(section = null, now = Date.now()) {
  const sections = section ? [section] : SECTIONS.map(s => s.id);
  if (sections.some(id => !SECTIONS.some(s => s.id === id))) throw new Error('Unknown section');
  return { id: String(now), started: now, sections, index: 0, answers: {}, flags: [], completed: [], deadline: now + SECTIONS.find(s => s.id === sections[0]).duration * 1000, remaining: null, paused: false, elapsed: 0, lastResumed: now };
}
export function secondsLeft(attempt, now = Date.now()) {
  return attempt.paused ? attempt.remaining : Math.max(0, Math.ceil((attempt.deadline - now) / 1000));
}
export function normalizeAnswer(value) {
  return String(value || '').trim().toLowerCase().replace(/[.?!]+$/, '').replace(/\s+/g, ' ');
}
export function grade(questions, answers) {
  return questions.map(q => ({ ...q, given: answers[q.id] || '', correct: q.accepted.some(a => normalizeAnswer(a) === normalizeAnswer(answers[q.id])) }));
}
export function wordCount(value) {
  return (String(value || '').match(/[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*/g) || []).length;
}
export function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
export function formatTime(seconds) {
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}
