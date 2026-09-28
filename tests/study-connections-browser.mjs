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

  await send('Page.navigate',{url:'http://127.0.0.1:4173/practice.html?skill=reading'});
  await waitFor('Boolean(document.querySelector("#reading-word"))');
  await evaluate('const p=document.querySelector("[data-reading-block]");const node=p.firstChild;const r=document.createRange();r.setStart(node,0);r.setEnd(node,2);getSelection().removeAllRanges();getSelection().addRange(r);document.dispatchEvent(new Event("selectionchange"));window.prompt=()=>"test meaning";');
  await click('#reading-word');
  await waitFor('Boolean(localStorage.getItem("ielts-personal-words-v1"))');
  assert.ok(await evaluate('JSON.parse(localStorage.getItem("ielts-personal-words-v1"))[0].context.length>2'));
  await send('Page.navigate',{url:'http://127.0.0.1:4173/words.html'});
  await waitFor('Boolean(document.querySelector("[data-book=personal]"))');
  await click('[data-book="personal"][data-mode="list"]');
  await waitFor('Boolean(document.querySelector(".word-row"))');
  await evaluate(`(async()=>{const {audioPlayer,mountAudioPlayer}=await import('/ui/audio-player.js');document.body.innerHTML=audioPlayer('/missing-test.mp3','study');const a=document.querySelector('audio');Object.defineProperty(a,'duration',{value:30});Object.defineProperty(a,'readyState',{value:1});window.audioSaved=null;window.player=mountAudioPlayer({saved:{},onSave:s=>window.audioSaved=s,notify:()=>{}});})()`);
  await evaluate('document.querySelector("audio").currentTime=2');await click('#loop-a');
  await evaluate('document.querySelector("audio").currentTime=5');await click('#loop-b');
  assert.equal(await evaluate('window.audioSaved.loop.b'),5);
  await evaluate('document.querySelector("audio").currentTime=6;document.querySelector("audio").dispatchEvent(new Event("timeupdate"))');
  assert.equal(await evaluate('document.querySelector("audio").currentTime'),2);
  await evaluate('const rate=document.querySelector("#listening-rate");rate.value="0.75";rate.dispatchEvent(new Event("change"))');
  assert.equal(await evaluate('window.audioSaved.rate'),0.75);
  await click('#loop-clear');assert.equal(await evaluate('window.audioSaved.loop'),null);
  assert.deepEqual(errors,[]);
  console.log('PASS: reading selection to personal vocabulary, personal list, AB loop rewind, speed and persistence (simulated audio metadata).');
  await send('Browser.close');
} finally {ws?.close();child.kill();}
