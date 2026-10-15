import test from 'node:test';
import assert from 'node:assert/strict';
import { onRequest, mediaKey } from '../functions/IELTS/[[path]].js';

const bytes = new TextEncoder().encode('0123456789');
// Minimal stand-in for an R2 bucket binding: parses a single "bytes=a-b" / "bytes=-n" range like R2 does.
const bucket = {
  objects: new Map([['IELTS/剑20完整/T1S1.mp3', bytes]]),
  async head(key) { const b = this.objects.get(key); return b ? this.meta(b) : null; },
  async get(key, { range } = {}) {
    const b = this.objects.get(key); if (!b) return null;
    const header = range?.get?.('Range'); let r;
    const m = header && /bytes=(\d*)-(\d*)/.exec(header);
    if (m) r = m[1] === '' ? { suffix: Number(m[2]) } : { offset: Number(m[1]), length: (m[2] === '' ? b.length - 1 : Number(m[2])) - Number(m[1]) + 1 };
    const slice = !r ? b : 'suffix' in r ? b.slice(b.length - r.suffix) : b.slice(r.offset, r.offset + r.length);
    return { ...this.meta(b), range: r, body: new Blob([slice]).stream() };
  },
  meta(b) { return { size: b.length, httpEtag: '"e1"', writeHttpMetadata() {} }; }
};
const call = (path, init = {}) => onRequest({ request: new Request('https://x.test' + path, init), env: { MEDIA: bucket } });
const url = '/IELTS/' + encodeURIComponent('剑20完整') + '/T1S1.mp3';

test('media keys stay inside IELTS/ and only allow media extensions', () => {
  assert.equal(mediaKey(url).key, 'IELTS/剑20完整/T1S1.mp3');
  assert.equal(mediaKey('/IELTS/a/../../secret.pdf'), null);
  assert.equal(mediaKey('/IELTS/a/b.json'), null);
  assert.equal(mediaKey('/resources/x.mp3'), null);
});

test('full, ranged, suffix and HEAD requests return the right bytes and headers', async () => {
  const full = await call(url);
  assert.equal(full.status, 200);
  assert.equal(await full.text(), '0123456789');
  assert.equal(full.headers.get('Content-Type'), 'audio/mpeg');
  assert.equal(full.headers.get('Accept-Ranges'), 'bytes');

  const part = await call(url, { headers: { Range: 'bytes=2-4' } });
  assert.equal(part.status, 206);
  assert.equal(await part.text(), '234');
  assert.equal(part.headers.get('Content-Range'), 'bytes 2-4/10');

  const tail = await call(url, { headers: { Range: 'bytes=-3' } });
  assert.equal(tail.status, 206);
  assert.equal(await tail.text(), '789');
  assert.equal(tail.headers.get('Content-Range'), 'bytes 7-9/10');

  const head = await call(url, { method: 'HEAD' });
  assert.equal(head.status, 200);
  assert.equal(head.headers.get('Content-Length'), '10');
});

test('missing objects, other methods and non-media paths are refused', async () => {
  assert.equal((await call('/IELTS/none.mp3')).status, 404);
  assert.equal((await call(url, { method: 'POST' })).status, 405);
  assert.equal((await call('/IELTS/x.exe')).status, 404);
});
