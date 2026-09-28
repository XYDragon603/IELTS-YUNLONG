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

  await send('Page.navigate',{url:'http://127.0.0.1:4173/words.html'});
  await waitFor('document.querySelectorAll(".word-book").length>=6');
  await evaluate('localStorage.removeItem("ielts-vocabulary-v1")');
  await reload('.word-book');
  await screenshot('words-home.png');
  await click('[data-book="ielts-1"][data-mode="learn"]');
  await waitFor('Boolean(document.querySelector(".word-card"))');
  await click('[data-action="reveal"]');
  await click('[data-rating="known"]');
  assert.equal(await evaluate('JSON.parse(localStorage.getItem("ielts-vocabulary-v1")).session.index'),1);
  await click('[data-action="spell"]');
  await evaluate('document.querySelector("#spelling-input").value="incorrect";document.querySelector("#spelling-form").requestSubmit()');
  assert.ok(await evaluate('Boolean(document.querySelector("[data-rating]"))'));
  await screenshot('words-card.png');
  await reload('.word-book');
  await click('[data-action="resume"]');
  await waitFor('Boolean(document.querySelector(".word-card"))');
  assert.equal(await evaluate('JSON.parse(localStorage.getItem("ielts-vocabulary-v1")).session.index'),1);
  await click('[data-action="home"]');
  await waitFor('Boolean(document.querySelector(".word-book"))');
  await click('[data-book="ielts-1"][data-mode="list"]');
  await waitFor('Boolean(document.querySelector("#word-search"))');
  await evaluate('const input=document.querySelector("#word-search");input.value="abandon";input.dispatchEvent(new Event("input",{bubbles:true}));');
  assert.ok(await evaluate('document.querySelectorAll(".word-row").length>0'));
  await click('[data-star-id]');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  await screenshot('words-mobile.png');
  await click('[data-action="home"]');
  await waitFor('document.querySelectorAll(".word-book").length>=6');
  assert.ok(await evaluate('Boolean(document.querySelector(".word-reader"))'));
  await click('[data-book="ielts-reading"][data-mode="list"]');
  await waitFor('Boolean(document.querySelector("#word-category"))');
  await evaluate('const el=document.querySelector("#word-category");el.selectedIndex=1;el.dispatchEvent(new Event("change",{bubbles:true}));');
  await evaluate('localStorage.setItem("ielts-vocabulary-v1",JSON.stringify({version:1,progress:{},limit:1,random:false,session:null}))');
  await reload('.word-book');
  await click('[data-book="ielts-1"][data-mode="dictation"]');
  await waitFor('Boolean(document.querySelector("#spelling-form"))');
  assert.equal(await evaluate('document.querySelector(".word-card").textContent.includes("abandon")'),false);
  await evaluate('window.spoken=[];Object.defineProperty(window,"speechSynthesis",{configurable:true,value:{getVoices:()=>[{lang:"en-GB"}],cancel:()=>{},speak:u=>window.spoken.push({text:u.text,rate:u.rate})}});window.SpeechSynthesisUtterance=function(text){this.text=text};');
  await click('[data-action="pronounce"]');
  await click('[data-action="slow"]');
  assert.equal(await evaluate('window.spoken[0].text'),'abandon');
  assert.ok(await evaluate('window.spoken[1].rate<window.spoken[0].rate'));
  await evaluate('document.querySelector("#spelling-input").value="wrong";document.querySelector("#spelling-form").requestSubmit()');
  assert.equal(await evaluate('Object.values(JSON.parse(localStorage.getItem("ielts-vocabulary-v1")).progress)[0].needsPractice'),true);
  await click('[data-rating="hard"]');
  await click('[data-action="reinforce"]');
  await evaluate('document.querySelector("#spelling-input").value="abandon";document.querySelector("#spelling-form").requestSubmit()');
  assert.equal(await evaluate('Object.values(JSON.parse(localStorage.getItem("ielts-vocabulary-v1")).progress)[0].needsPractice'),false);
  await click('[data-rating="known"]');
  assert.equal(await evaluate('Boolean(document.querySelector("[data-action=reinforce]"))'),false);
  assert.deepEqual(errors,[]);
  console.log('PASS: imported books, reveal, rating persistence, spelling, resume, search, favorites, mobile layout.');
  await send('Browser.close');
} finally {ws?.close();child.kill();}
