// Upload local IELTS/ media to the private R2 bucket used by functions/IELTS/[[path]].js.
//   node backend/scripts/upload-media.mjs            # papers + audio used by the online question bank (default)
//   node backend/scripts/upload-media.mjs --all      # also explanation PDFs / videos listed in frontend/data/manifest.js
//   node backend/scripts/upload-media.mjs --dry-run  # list what would be uploaded
// Requires `npx wrangler login` first. Progress is kept in .cache/r2-uploaded.json so a rerun skips finished files.
import { readFile, readdir, stat, writeFile, mkdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../..', import.meta.url));
const BUCKET = process.env.R2_BUCKET || 'ielts-media';
const WRANGLER_LIMIT = 300 * 1024 * 1024; // larger objects need an S3-compatible client (e.g. rclone)
const all = process.argv.includes('--all'), dryRun = process.argv.includes('--dry-run');
const logFile = path.join(root, '.cache', 'r2-uploaded.json');

const keys = new Set();
for (let book = 4; book <= 20; book++) for (let test = 1; test <= 4; test++) for (const skill of ['listening', 'reading', 'writing', 'speaking']) {
  let data;
  try { data = JSON.parse(await readFile(path.join(root, `resources/cambridge/c${book}/test-${test}/${skill}.json`), 'utf8')); } catch { continue; }
  if (data.sources?.paper?.path) keys.add(data.sources.paper.path);
  for (const audio of Object.values(data.audio || {})) keys.add(typeof audio === 'string' ? audio : audio.path);
}
if (all) {
  const manifest = await readFile(path.join(root, 'frontend/data/manifest.js'), 'utf8');
  for (const [, p] of manifest.matchAll(/"(IELTS\/[^"]+\.(?:pdf|mp3|m4a|wav|ogg|mp4))"/g)) keys.add(p);
}

let done = {};
try { done = JSON.parse(await readFile(logFile, 'utf8')); } catch {}
const todo = [], skipped = [];
for (const key of [...keys].sort()) {
  const file = path.join(root, key);
  let size;
  try { size = (await stat(file)).size; } catch { skipped.push(`${key} (missing locally)`); continue; }
  if (size > WRANGLER_LIMIT) { skipped.push(`${key} (${(size / 2 ** 20).toFixed(0)} MiB, use rclone)`); continue; }
  if (done[key] === size) continue;
  todo.push({ key, file, size });
}
const gib = todo.reduce((n, f) => n + f.size, 0) / 2 ** 30;
console.log(`${keys.size} media files referenced; ${todo.length} to upload (${gib.toFixed(2)} GiB); ${Object.keys(done).length} already uploaded.`);
for (const s of skipped) console.log('  skip:', s);
if (dryRun) { for (const f of todo) console.log('  ', f.key); process.exit(0); }

await mkdir(path.dirname(logFile), { recursive: true });
let i = 0;
for (const f of todo) {
  i++;
  process.stdout.write(`[${i}/${todo.length}] ${f.key} ... `);
  const r = spawnSync('npx', ['wrangler', 'r2', 'object', 'put', `${BUCKET}/${f.key}`, '--file', f.file, '--remote'], { stdio: ['ignore', 'pipe', 'pipe'], shell: process.platform === 'win32', encoding: 'utf8' });
  if (r.status !== 0) { console.log('failed'); console.error(r.stderr || r.stdout); process.exitCode = 1; break; }
  done[f.key] = f.size;
  await writeFile(logFile, JSON.stringify(done, null, 1));
  console.log('ok');
}
