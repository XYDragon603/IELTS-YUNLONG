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

  const origin=process.env.CATALOG_ORIGIN||'http://127.0.0.1:4173';
  const reset=await send('Page.addScriptToEvaluateOnNewDocument',{source:'localStorage.removeItem("ielts-study-v1")'});
  await send('Page.navigate',{url:origin+'/#library/18/1'});
  await waitFor('Boolean(document.querySelector("[data-study=start]"))');
  // Dedicated headless profile only. Give each test run a fresh practice state.
  await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:reset.identifier});
  await waitFor('Boolean(document.querySelector("[data-study=start]"))');
  await click('[data-study="start"]');
  await waitFor('Boolean(document.querySelector("#confirm-modal"))');
  await click('#confirm-modal');
  await waitFor('Boolean(document.querySelector("[data-study=submit]"))');
  if(await evaluate('Boolean(document.querySelector(".focus-paused"))'))await click('[data-study="pause"]');
  const rows=[];
  for(let part=1;part<=4;part++){
    if(part>1)await click(`[data-study="part"][data-part="${part}"]`);
    await waitFor('Number.isFinite(document.querySelector("#study-audio")?.duration)');
    rows.push(await evaluate(`(()=>{const a=document.querySelector('#study-audio');return {part:${part},title:document.querySelector('.focus-part-heading h1').textContent,src:decodeURI(a.currentSrc),duration:a.duration,error:a.error?.code||null}})()`));
    assert.ok(rows.at(-1).src.endsWith(`18-1-${part}.mp3`));
    assert.ok(rows.at(-1).duration>60);
    assert.equal(rows.at(-1).error,null);
    const response=await fetch(rows.at(-1).src,{headers:{Range:'bytes=0-9'}});
    assert.equal(response.status,206);
    assert.equal(response.headers.get('content-type'),'audio/mpeg');
    assert.equal((await response.arrayBuffer()).byteLength,10);
    await evaluate(`document.querySelector('#audio-seek').value=10;document.querySelector('#audio-seek').dispatchEvent(new Event('input'));{const rate=document.querySelector('#listening-rate');rate.value='0.85';rate.dispatchEvent(new Event('change'));}`);
    await waitFor('!document.querySelector("#study-audio").seeking');
    assert.ok(Math.abs(await evaluate('document.querySelector("#study-audio").currentTime')-rows.at(-1).duration*.1)<1);
  }
  // Return through the actual Part controls, checking isolated saved positions.
  for(let part=3;part>=1;part--){
    await click(`[data-study="part"][data-part="${part}"]`);
    await waitFor('Number.isFinite(document.querySelector("#study-audio")?.duration)&&!document.querySelector("#study-audio").seeking');
    assert.ok(Math.abs(await evaluate('document.querySelector("#study-audio").currentTime')-rows[part-1].duration*.1)<1);
    assert.equal(await evaluate('document.querySelector("#study-audio").playbackRate'),.85);
  }
  await evaluate('document.querySelector("#study-audio").currentTime=2');
  await waitFor('!document.querySelector("#study-audio").seeking');await click('#loop-a');
  await evaluate('document.querySelector("#study-audio").currentTime=4');
  await waitFor('!document.querySelector("#study-audio").seeking');await click('#loop-b');
  await click('[data-player="play"]');
  await waitFor('!document.querySelector("#study-audio").paused');
  await sleep(3500);
  assert.ok(await evaluate('document.querySelector("#study-audio").currentTime>=2&&document.querySelector("#study-audio").currentTime<4.4'));
  await click('[data-player="play"]');
  await reload('[data-study=submit]');
  if(await evaluate('Boolean(document.querySelector(".focus-paused"))'))await click('[data-study="pause"]');
  await waitFor('Number.isFinite(document.querySelector("#study-audio")?.duration)');
  assert.equal(await evaluate('document.querySelector("#study-audio").playbackRate'),.85);
  assert.ok(await evaluate('document.querySelector("#loop-status").textContent.includes("2.0–4.0")'));
  await click('#loop-clear');
  // Real end-of-file loop: after ended fires, playback must resume at A.
  await evaluate('document.querySelector("#study-audio").currentTime=document.querySelector("#study-audio").duration-1');
  await waitFor('!document.querySelector("#study-audio").seeking');await click('#loop-a');
  await evaluate('document.querySelector("#study-audio").currentTime=document.querySelector("#study-audio").duration');
  await waitFor('!document.querySelector("#study-audio").seeking');await click('#loop-b');
  await click('[data-player="play"]');await sleep(2800);
  assert.equal(await evaluate('document.querySelector("#study-audio").paused'),false);
  assert.deepEqual(errors,[]);
  await writeFile(path.join(out,'listening-audio-audit.json'),JSON.stringify({scope:'C18 Test 1',contentListened:false,rows,errors},null,2));
  console.log(JSON.stringify({rows,errors},null,2));
  await send('Browser.close');
} finally {ws?.close();child.kill();}

