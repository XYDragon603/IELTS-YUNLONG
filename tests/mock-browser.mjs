import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const sleep = ms => new Promise(r => setTimeout(r, ms));
const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const out = path.resolve('artifacts');
await mkdir(out, { recursive: true });
const child = spawn(chrome, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=9227', `--user-data-dir=${path.resolve('.chrome-practice-test-profile')}`, '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required', 'about:blank'], { windowsHide: true, stdio: 'ignore' });
let launchError;
child.on('error', e => { launchError = e; });
let ws;
try {
  let tab;
  for (let i = 0; i < 80; i++) {
    if (launchError) throw launchError;
    try { tab = (await (await fetch('http://127.0.0.1:9227/json')).json()).find(t => t.type === 'page'); if (tab) break; } catch {}
    await sleep(150);
  }
  if (!tab) throw new Error('Chrome did not start');
  ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let sequence = 0;
  const pending = new Map(), errors = [];
  ws.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (message.id) { const p = pending.get(message.id); if (p) { pending.delete(message.id); message.error ? p.reject(new Error(message.error.message)) : p.resolve(message.result); } }
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text + ': ' + (message.params.exceptionDetails.exception?.description || ''));
  };
  ws.onclose = event => { for (const p of pending.values()) p.reject(new Error(`Chrome connection closed: ${event.code} ${event.reason}`)); pending.clear(); };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, 12000);
    pending.set(id, { resolve: value => { clearTimeout(timer); resolve(value); }, reject: error => { clearTimeout(timer); reject(error); } });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  };
  const waitFor = async expression => { for (let i = 0; i < 80; i++) { if (await evaluate(expression)) return; await sleep(100); } throw new Error('Timed out: ' + expression); };
  const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const reload = async selector => {
    await evaluate('window.__reloadMarker=true');
    await send('Page.reload');
    await waitFor(`!window.__reloadMarker && document.readyState==='complete' && Boolean(document.querySelector(${JSON.stringify(selector)}))`);
  };
  const screenshot = async name => { const result = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }); await writeFile(path.join(out, name), Buffer.from(result.data, 'base64')); };
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });

  await send('Page.navigate',{url:'http://127.0.0.1:4173/mock.html'});
  await waitFor('Boolean(document.querySelector("#new-mock"))');
  await send('Emulation.setDeviceMetricsOverride',{width:1200,height:900,deviceScaleFactor:1,mobile:false});
  assert.ok(await evaluate('document.querySelector(".studio-nav nav").getBoundingClientRect().top < document.querySelector(".brand").getBoundingClientRect().bottom'));
  assert.ok(await evaluate('document.querySelector(".yunlong-signature").getBoundingClientRect().left > document.querySelector(".studio-nav nav").getBoundingClientRect().left'));
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  await screenshot('navigation-1200.png');
  await send('Emulation.setDeviceMetricsOverride',{width:977,height:900,deviceScaleFactor:1,mobile:false});
  assert.ok(await evaluate('document.querySelector(".studio-nav nav").getBoundingClientRect().top >= document.querySelector(".brand").getBoundingClientRect().bottom'));
  assert.ok(await evaluate('document.querySelector(".yunlong-signature").getBoundingClientRect().left > innerWidth/2'));
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  await screenshot('navigation-977.png');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  assert.equal(await evaluate('document.querySelector(".studio-nav [aria-current=page]")?.getAttribute("href")'),'/mock.html');
  await send('Page.navigate',{url:'http://127.0.0.1:4173/words.html'});
  await waitFor('document.querySelector(".studio-nav [aria-current=page]")?.getAttribute("href")==="/words.html"');
  await send('Page.navigate',{url:'http://127.0.0.1:4173/review.html'});
  await waitFor('document.querySelector(".studio-nav [aria-current=page]")?.getAttribute("href")==="/review.html"');
  await send('Page.navigate',{url:'http://127.0.0.1:4173/mock.html'});
  await waitFor('Boolean(document.querySelector("#new-mock"))');
  assert.ok(await evaluate('document.querySelector("#mock-main").textContent.includes("36 / 68")'));
  assert.ok(await evaluate('[...document.querySelector("#mock-paper").options].some(o=>o.value==="20-4"&&!o.disabled)'));
  assert.ok(await evaluate('[...document.querySelector("#mock-paper").options].some(o=>o.value==="4-1"&&o.disabled)'));
  await screenshot('mock-selector.png');
  await evaluate('document.querySelector("#mock-paper").value="18-1"');
  await click('#new-mock');
  await waitFor('Boolean(document.querySelector("a[href*=import-preview]"))');
  const listeningURL=await evaluate('document.querySelector("a[href*=import-preview]").href');
  await send('Page.navigate',{url:listeningURL});
  await waitFor('Boolean(document.querySelector("#submit-preview"))');
  assert.ok(await evaluate('location.search.includes("mockRun=")'));
  await screenshot('listening-workspace.png');
  await click('#submit-preview');
  await waitFor('Boolean(document.querySelector("#preview-results h2"))');
  assert.ok(await evaluate('document.querySelector("#preview-results").textContent.includes("暂定参考分")'));
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  await send('Page.navigate',{url:'http://127.0.0.1:4173/mock.html'});
  await waitFor('[...document.querySelectorAll("a")].some(a=>a.href.includes("skill=reading"))');
  const readingURL=await evaluate('[...document.querySelectorAll("a")].find(a=>a.href.includes("skill=reading")).href');
  await send('Page.navigate',{url:readingURL});
  await waitFor('Boolean(document.querySelector("#submit-practice"))');
  assert.ok(await evaluate('location.search.includes("mockRun=")'));
  await click('#submit-practice');
  await click('#practice-submit button[value="submit"]');
  await waitFor('Boolean(document.querySelector(".practice-review"))');
  await send('Page.navigate',{url:'http://127.0.0.1:4173/mock.html'});
  await waitFor('[...document.querySelectorAll("a")].some(a=>a.href.includes("skill=writing"))');
  for(const skill of ['writing','speaking']){
    const url=await evaluate(`[...document.querySelectorAll("a")].find(a=>a.href.includes("skill=${skill}")).href`);
    await send('Page.navigate',{url});
    await waitFor('Boolean(document.querySelector("#submit-practice"))');
    await click('#submit-practice');
    await click('#practice-submit button[value="submit"]');
    await waitFor('Boolean(document.querySelector(".practice-review"))');
    await send('Page.navigate',{url:'http://127.0.0.1:4173/mock.html'});
    await waitFor('Boolean(document.querySelector("#new-mock"))');
  }
  assert.ok(await evaluate('document.querySelector("#mock-main").textContent.includes("4 / 4")'));
  await evaluate('document.querySelector("#mock-paper").value="20-4"');
  await click('#new-mock');
  await waitFor('[...document.querySelectorAll("a")].some(a=>a.href.includes("import-preview.html?book=20&test=4"))');
  const anotherListeningURL=await evaluate('[...document.querySelectorAll("a")].find(a=>a.href.includes("import-preview.html?book=20&test=4")).href');
  await send('Page.navigate',{url:anotherListeningURL});
  await waitFor('Boolean(document.querySelector("#submit-preview"))');
  assert.ok(await evaluate('document.querySelector("h1").textContent.includes("Cambridge 20 · Test 4")'));
  assert.ok(await evaluate('Boolean(document.querySelector("audio[src]"))'));
  assert.deepEqual(errors,[]);
  console.log('PASS: all-paper selection, imported listening, four-stage submission and unlocking, completion.');
  await send('Browser.close');
} finally {ws?.close();child.kill();}
