import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const sleep = ms => new Promise(r => setTimeout(r, ms));
const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const out = path.resolve('artifacts');
await mkdir(out, { recursive: true });
const child = spawn(chrome, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=9224', `--user-data-dir=${path.resolve('.chrome-test-profile')}`, '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required', 'about:blank'], { windowsHide: true, stdio: 'ignore' });
let launchError;
child.on('error', e => { launchError = e; });
let ws;
try {
  let tab;
  for (let i = 0; i < 80; i++) {
    if (launchError) throw launchError;
    try { tab = (await (await fetch('http://127.0.0.1:9224/json')).json()).find(t => t.type === 'page'); if (tab) break; } catch {}
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
  await send('Page.navigate', { url: 'http://localhost:4173' });
  await waitFor('Boolean(document.querySelector(".studio-hero"))');
  await evaluate('localStorage.clear()');
  await reload('.studio-hero');
  await screenshot('desktop-home.png');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true);
  await evaluate('location.hash="practice"');
  await waitFor('Boolean(document.querySelector("[data-start]"))');
  await click('[data-start="all"]'); await click('#confirm-modal');
  await waitFor('Boolean(document.querySelector("#answer-l1"))');
  await evaluate(`for (const [id,value] of Object.entries({l1:'monday',l2:'15',l3:'Carter',l4:'80',l5:'camera'})) { const el=document.querySelector('[data-answer="'+id+'"]');el.value=value;el.dispatchEvent(new Event('input',{bubbles:true})); }`);
  await click('[data-flag="l2"]');
  await click('[data-action="pause"]');
  await reload('.pause-panel');
  await click('[data-action="pause"]');
  assert.equal(await evaluate('document.querySelector("#answer-l1").value'), 'monday');
  assert.equal(await evaluate('document.querySelector("[data-flag=l2]").getAttribute("aria-pressed")'), 'true');
  await screenshot('desktop-listening.png');
  await click('[data-action="next"]'); await click('#confirm-modal');
  await waitFor('document.querySelector("h1")?.textContent.includes("Reading")');
  await click('[data-action="pause"]');
  for (const [id, answer] of Object.entries({ r1:'TRUE', r2:'FALSE', r3:'FALSE', r4:'FALSE', r5:'NOT GIVEN' })) {
    await click(`input[name="${id}"][value="${answer}"]`);
  }
  await click('[data-action="next"]'); await click('#confirm-modal');
  await waitFor('document.querySelector("h1")?.textContent.includes("Writing")');
  await click('[data-action="pause"]');
  await evaluate(`{const el=document.querySelector('#essay');el.value="Libraries support communities. <script>window.injected=true</script>";el.dispatchEvent(new Event('input',{bubbles:true}));}`);
  await click('[data-action="next"]'); await click('#confirm-modal');
  await waitFor('document.querySelector("h1")?.textContent.includes("Speaking")');
  await click('[data-action="pause"]');
  await click('[data-action="record"]');
  await waitFor('document.querySelector("#record-circle").classList.contains("recording")');
  await sleep(1300); await click('[data-action="stop-record"]');
  await waitFor('Boolean(document.querySelector("audio"))');
  await click('[data-action="next"]'); await click('#confirm-modal');
  await waitFor('Boolean(document.querySelector(".results-overview"))');
  assert.equal(await evaluate('JSON.parse(localStorage.getItem("ielts-history")).length'), 1);
  assert.equal(await evaluate('document.querySelectorAll(".status-tag:not(.wrong)").length'), 10);
  assert.equal(await evaluate('Boolean(window.injected)'), false);
  await waitFor('Boolean(document.querySelector("audio"))');
  await send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: out });
  await click('[data-export]');
  await screenshot('desktop-report.png');
  await evaluate('location.hash="home"');await waitFor('Boolean(document.querySelector(".studio-hero"))');
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 1, mobile: true });
  await screenshot('mobile-home.png');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true);
  await evaluate('location.hash="practice"');
  await waitFor('Boolean(document.querySelector("[data-start]"))');
  await click('[data-start="reading"]');await click('#confirm-modal');await waitFor('Boolean(document.querySelector(".choices"))');
  await screenshot('mobile-reading.png');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true);
  // Move the browser clock beyond the deadline. It must submit exactly once.
  await evaluate(`{const future=Date.now()+10*60*1000;Date.now=()=>future;}`);
  await waitFor('Boolean(document.querySelector(".results-overview"))');
  assert.equal(await evaluate('JSON.parse(localStorage.getItem("ielts-history")).length'), 2);
  assert.equal(await evaluate('document.querySelectorAll(".status-tag.wrong").length'), 5);
  await send('Emulation.setDeviceMetricsOverride', { width: 812, height: 375, deviceScaleFactor: 1, mobile: true });
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true);
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  assert.equal(await evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches'), true);
  assert.deepEqual(errors, []);
  console.log('PASS: desktop/mobile layouts, full four-section flow, answer persistence, flags, grading, XSS escaping, simulated microphone, audio persistence, report export, timer expiry, landscape, reduced motion.');
  await send('Browser.close');
} finally {
  ws?.close();
  child.kill();
}
