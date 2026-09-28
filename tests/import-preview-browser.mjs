import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const sleep = ms => new Promise(r => setTimeout(r, ms));
const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const out = path.resolve('artifacts');
await mkdir(out, { recursive: true });
const child = spawn(chrome, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=9226', `--user-data-dir=${path.resolve('.chrome-import-preview-test-profile')}`, '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required', 'about:blank'], { windowsHide: true, stdio: 'ignore' });
let launchError;
child.on('error', e => { launchError = e; });
let ws;
try {
  let tab;
  for (let i = 0; i < 80; i++) {
    if (launchError) throw launchError;
    try { tab = (await (await fetch('http://127.0.0.1:9226/json')).json()).find(t => t.type === 'page'); if (tab) break; } catch {}
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
  await send('Page.navigate', {url:'http://127.0.0.1:4173/favicon.svg'});
  await waitFor('location.pathname==="/favicon.svg"');
  await evaluate('localStorage.removeItem("ielts-c18-t1-import-preview-v1");localStorage.removeItem("ielts-c14-t1-import-preview-v1");localStorage.removeItem("ielts-review-v1")');
  await send('Page.navigate', {url:'http://127.0.0.1:4173/import-preview.html'});
  await waitFor('Boolean(document.querySelector("#submit-preview"))');
  assert.equal(await evaluate('document.querySelectorAll(".study-question").length'),10);
  await waitFor('document.querySelector("audio").readyState >= 1');
  await evaluate('document.querySelector("audio").currentTime=12');
  await evaluate('const input=document.querySelector("[data-response=q1]"); input.value="example"; input.dispatchEvent(new Event("input",{bubbles:true}))');
  await reload('#submit-preview');
  assert.equal(await evaluate('document.querySelector("[data-response=q1]").value'),'example');
  await waitFor('document.querySelector("audio").readyState >= 1');
  assert.ok(await evaluate('document.querySelector("audio").currentTime >= 11'));
  await click('[data-part="2"]');
  assert.equal(await evaluate('document.querySelectorAll(".study-question").length'),9);
  await evaluate('for(const el of [...document.querySelectorAll("[data-response=q14]")].slice(0,3)){el.checked=true;el.dispatchEvent(new Event("input",{bubbles:true}));}');
  assert.equal(await evaluate('document.querySelectorAll("[data-response=q14]:checked").length'),2);
  await click('[data-part="3"]');
  assert.equal(await evaluate('document.querySelectorAll(".study-question").length'),8);
  await click('[data-part="4"]');
  await send('Emulation.setDeviceMetricsOverride', {width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
  await click('#submit-preview');
  assert.equal(await evaluate('document.querySelectorAll("#preview-results details").length'),37);
  assert.ok(await evaluate('document.querySelector("#preview-results h2").textContent.includes("/ 40")'));
  await send('Page.navigate', {url:'http://127.0.0.1:4173/import-preview.html?book=14&test=1'});
  await waitFor('Boolean(document.querySelector("#submit-preview"))');
  await click('#submit-preview');
  assert.ok(await evaluate('document.querySelectorAll("#preview-results .synonym-note").length > 0'));
  const synonymId=await evaluate('document.querySelector("[data-save-synonym]").dataset.saveSynonym');
  await click('[data-save-synonym]');
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem('ielts-vocabulary-v1')).progress[${JSON.stringify(synonymId)}].starred`),true);
  await click('[data-add-review="q1"]');
  assert.ok(await evaluate('JSON.parse(localStorage.getItem("ielts-review-v1")).items.some(item=>item.id==="c14-t1-listening-q1")'));
  assert.deepEqual(errors,[]);
  console.log('PASS: JSON loading, audio, answer persistence, mobile layout, C14 synonym and review collection.');
  await send('Browser.close');
} finally {
  ws?.close();
  child.kill();
}
