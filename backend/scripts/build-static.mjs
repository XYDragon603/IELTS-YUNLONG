// Build a static copy of the site in dist/ for Cloudflare Pages (or any static host).
// - frontend/ becomes the site root
// - question data and images from resources/ are copied as-is (audit/OCR files are left out)
// - /api/catalog.json is generated once from the same code the local server uses
// - IELTS/ media (papers, audio, video) is NOT copied: it is served from R2 by functions/IELTS/[[path]].js
//   and uploaded separately with backend/scripts/upload-media.mjs.
// dist/ holds copyrighted paper content: it is git-ignored and must only be deployed behind Cloudflare Access.
import { cp, mkdir, readdir, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildCatalog } from '../lib/catalog-server.js';
import { publicPathAllowed } from '../lib/public-path.js';

const root = fileURLToPath(new URL('../..', import.meta.url));
const dist = path.join(root, 'dist');
const PAGES_FILE_LIMIT = 25 * 1024 * 1024;
const SKIP = /(^|\/)(validation-report|curations|ocr-cleanup|import-manifest|import-report)\.json$|(^|\/)page-maps\//;

async function* walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.')) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full); else if (entry.isFile()) yield full;
  }
}

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(path.join(root, 'frontend'), dist, { recursive: true });

let files = 0, bytes = 0;
const tooBig = [];
for await (const file of walk(path.join(root, 'resources'))) {
  const rel = path.relative(root, file).split(path.sep).join('/');
  if (SKIP.test(rel) || !publicPathAllowed('/' + rel)) continue;
  const size = (await stat(file)).size;
  if (size > PAGES_FILE_LIMIT) { tooBig.push(rel); continue; }
  await mkdir(path.dirname(path.join(dist, rel)), { recursive: true });
  await cp(file, path.join(dist, rel));
  files++; bytes += size;
}

const catalog = await buildCatalog(root);
await mkdir(path.join(dist, 'api'), { recursive: true });
await writeFile(path.join(dist, 'api', 'catalog.json'), JSON.stringify(catalog));

// Cloudflare Pages response headers: keep the private site out of search engines; question data revalidates quickly.
await writeFile(path.join(dist, '_headers'), [
  '/*',
  '  X-Robots-Tag: noindex, nofollow',
  '  Referrer-Policy: same-origin',
  '/resources/*',
  '  Cache-Control: private, max-age=300',
  '/api/*',
  '  Cache-Control: private, no-cache',
  ''
].join('\n'));

let total = 0;
for await (const file of walk(dist)) { total++; if ((await stat(file)).size > PAGES_FILE_LIMIT) tooBig.push(path.relative(dist, file)); }
console.log(`dist/ ready: ${total} files (resources: ${files}, ${(bytes / 2 ** 20).toFixed(1)} MiB); catalog entries: ${catalog.entries.length}`);
if (tooBig.length) { console.error('Files over the 25 MiB Pages limit:', tooBig); process.exitCode = 1; }
if (total > 20000) { console.error('More than 20,000 files: over the Cloudflare Pages limit.'); process.exitCode = 1; }
