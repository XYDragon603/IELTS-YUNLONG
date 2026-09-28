export function stopWordAudio(){window.speechSynthesis?.cancel();}
export function speakWord(word,{slow=false,message=()=>{}}={}){
  if(!window.speechSynthesis||!window.SpeechSynthesisUtterance){message('当前浏览器不支持发音，请使用 Chrome 或 Edge。');return;}
  stopWordAudio();
  const voices=window.speechSynthesis.getVoices().filter(v=>/^en[-_]/i.test(v.lang));
  const voice=voices.find(v=>/^en[-_]GB/i.test(v.lang))||voices[0];
  if(!voice){message('尚未找到英文语音。请安装系统英文语音后重试，或改用拼写自测。');return;}
  const utterance=new SpeechSynthesisUtterance(word);utterance.voice=voice;utterance.lang=voice.lang;utterance.rate=slow?0.65:0.9;
  utterance.onerror=e=>{if(!['canceled','interrupted'].includes(e.error))message('发音失败，请重试或检查系统语音设置。');};
  window.speechSynthesis.speak(utterance);
}
window.addEventListener('pagehide',stopWordAudio);
