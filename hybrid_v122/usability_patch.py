from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
build = root / 'app/build.gradle'
main = root / 'app/src/main/java/org/neocities/bk26/echohalospatial/MainActivity.java'
asset = root / 'app/src/main/assets/spatial_inject.js'

# EchoHalo v1.2.2 - daily-use polish layered on the v1.2.1 hybrid build.
s = build.read_text()
s = re.sub(r"versionCode\s+\d+", "versionCode 14", s, count=1)
s = re.sub(r"versionName\s+'[^']+'", "versionName '1.2.2'", s, count=1)
build.write_text(s)

s = main.read_text()
s = re.sub(r'private static final String VERSION = "[^"]+";',
           'private static final String VERSION = "1.2.2";', s, count=1)
main.write_text(s)

js = asset.read_text()
js = js.replace('EchoHalo v1.2.1 • Unified Spatial Captions • Accessibility prototype • Not a medical device.',
                'EchoHalo v1.2.2 • Caption-first Spatial Audio • Accessibility prototype • Not a medical device.')

addon = r'''

// EchoHalo v1.2.2 — caption-first daily-use UX, reliable history, browser-mic
// handoff, and visual Orientation Scout instructions.
(() => {
  if (window.__echoHaloDailyUseV122) return;
  window.__echoHaloDailyUseV122 = true;
  const native = window.EchoHaloNative;
  if (!native) return;
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));

  const listen = $('#screen-listen');
  const listenGrid = $('#screen-listen>.grid.two');
  const liveCard = listenGrid?.children?.[0] || null;
  const historyCard = listenGrid?.children?.[1] || null;
  if (liveCard) liveCard.id = 'ehLiveCaptionCard';
  if (historyCard) historyCard.id = 'ehHistoryCard';

  if (liveCard && !$('#ehHistoryToggle')) {
    const b = document.createElement('button');
    b.id = 'ehHistoryToggle';
    b.type = 'button';
    b.className = 'btn ghost';
    b.textContent = 'History';
    b.setAttribute('aria-expanded', 'false');
    const row = liveCard.querySelector('.row.between') || liveCard;
    row.appendChild(b);
    b.addEventListener('click', ev => {
      ev.preventDefault(); ev.stopPropagation();
      const open = !document.body.classList.contains('eh-history-open');
      document.body.classList.toggle('eh-history-open', open);
      b.textContent = open ? 'Hide History' : 'History';
      b.setAttribute('aria-expanded', String(open));
      wakeControls();
    });
  }

  const style = document.createElement('style');
  style.id = 'eh-v122-daily-style';
  style.textContent = `
    #screen-listen>.grid.two{grid-template-columns:minmax(0,1fr)!important;gap:8px!important}
    #ehHistoryCard{display:none!important}
    body.eh-history-open #ehHistoryCard{display:block!important}
    #ehLiveCaptionCard{min-width:0!important}
    #ehHistoryToggle{min-height:34px!important;padding:5px 10px!important;font-size:.78rem!important}
    .hero-caption.eh-spatial-caption{
      min-height:clamp(360px,58vh,680px)!important;
      display:flex!important;flex-direction:column!important;justify-content:center!important;
      transition:min-height .24s ease,height .24s ease,margin .24s ease!important;
    }
    .hero-caption.eh-spatial-caption .caption-text{
      font-size:calc(1.62rem * var(--caption-scale))!important;line-height:1.18!important;
    }
    .hero-caption.eh-spatial-caption .caption-interim{
      font-size:calc(1.14rem * var(--caption-scale))!important;line-height:1.2!important;
    }
    body.eh-listen-focus .topbar{max-height:8px!important;min-height:0!important;opacity:.08!important;overflow:hidden!important;padding:0!important;margin:0!important;transform:translateY(-5px)}
    body.eh-listen-focus .tabs{max-height:9px!important;min-height:0!important;opacity:.10!important;overflow:hidden!important;padding:0!important;margin:0 0 2px!important;transform:translateY(-4px)}
    body.eh-listen-focus #ehLiveCaptionCard>.row.between{max-height:7px!important;opacity:.08!important;overflow:hidden!important;margin:0!important}
    body.eh-listen-focus #captionStatus{max-height:8px!important;min-height:0!important;opacity:.12!important;overflow:hidden!important;padding:0!important;margin:0!important}
    body.eh-listen-focus #spatialNotice{display:none!important}
    body.eh-listen-focus .hero-caption.eh-spatial-caption{min-height:calc(100svh - 44px)!important;margin-top:2px!important}
    .topbar,.tabs,#ehLiveCaptionCard>.row.between,#captionStatus{transition:opacity .22s ease,max-height .25s ease,transform .22s ease!important}
    @media (orientation:landscape){
      .hero-caption.eh-spatial-caption{min-height:66vh!important;height:auto!important}
      body.eh-listen-focus .hero-caption.eh-spatial-caption{min-height:calc(100svh - 28px)!important;height:calc(100svh - 28px)!important}
      body.eh-history-open #screen-listen>.grid.two{grid-template-columns:minmax(0,3.5fr) minmax(210px,1fr)!important;align-items:stretch!important}
      body.eh-history-open #ehHistoryCard{display:block!important;max-height:calc(100svh - 55px)!important;overflow:auto!important}
      .hero-caption.eh-spatial-caption .caption-text{font-size:calc(1.75rem * var(--caption-scale))!important}
    }
    .eh-scout-visual{position:relative;min-height:176px;margin:9px 0;border:1px solid #28373e;border-radius:16px;background:radial-gradient(circle at 50% 45%,#10242e 0,#071014 54%,#030607 100%);overflow:hidden}
    .eh-scout-stage{position:absolute;inset:8px;display:flex;align-items:center;justify-content:center}
    .eh-scout-phone{position:relative;width:72px;height:132px;border:3px solid #9eb4bf;border-radius:15px;background:#020304;box-shadow:0 0 0 1px #ffffff10,0 8px 26px #000;transition:width .2s,height .2s}
    .eh-scout-phone.landscape{width:132px;height:72px}
    .eh-scout-screen{position:absolute;inset:7px;border:1px solid #2b454f;border-radius:9px;background:linear-gradient(150deg,#10232d,#05090b)}
    .eh-scout-camera{position:absolute;width:7px;height:7px;border-radius:50%;background:#42d7ff;box-shadow:0 0 9px #42d7ff;z-index:2}
    .eh-scout-phone.portrait .eh-scout-camera{top:4px;left:50%;transform:translateX(-50%)}
    .eh-scout-phone.landscape-left .eh-scout-camera{left:4px;top:50%;transform:translateY(-50%)}
    .eh-scout-phone.landscape-right .eh-scout-camera{right:4px;top:50%;transform:translateY(-50%)}
    .eh-scout-top{position:absolute;color:#a9e8ff;font-size:.58rem;font-weight:950;letter-spacing:.08em;z-index:3}
    .eh-scout-phone.portrait .eh-scout-top{top:-19px;left:50%;transform:translateX(-50%)}
    .eh-scout-phone.landscape-left .eh-scout-top{left:-42px;top:50%;transform:translateY(-50%) rotate(-90deg)}
    .eh-scout-phone.landscape-right .eh-scout-top{right:-42px;top:50%;transform:translateY(-50%) rotate(90deg)}
    .eh-scout-face{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);font-size:.64rem;color:#91a4ae;font-weight:850;white-space:nowrap}
    .eh-scout-sound{position:absolute;top:50%;transform:translateY(-50%);font-size:1.9rem;color:#ffd47d;text-shadow:0 0 15px #ffd47d88;opacity:.28}
    .eh-scout-sound.left{left:17px}.eh-scout-sound.right{right:17px}.eh-scout-sound.active{opacity:1;animation:ehScoutPulse .75s ease-in-out infinite alternate}
    .eh-scout-orientation{position:absolute;top:8px;left:10px;color:#d8e9f0;font-weight:900;font-size:.72rem}
    .eh-scout-note{position:absolute;right:10px;top:8px;color:#81949e;font-size:.63rem;text-align:right}
    @keyframes ehScoutPulse{from{transform:translateY(-50%) scale(.85)}to{transform:translateY(-50%) scale(1.15)}}
  `;
  document.head.appendChild(style);

  let idleTimer = 0;
  function captionsAppearRunning(){
    const t = ($('#captionToggle')?.textContent || '').toLowerCase();
    return t.includes('stop captions') || t.includes('starting');
  }
  function listenVisible(){ return !!listen?.classList.contains('active'); }
  function wakeControls(){
    document.body.classList.remove('eh-listen-focus');
    clearTimeout(idleTimer);
    if (!listenVisible() || !captionsAppearRunning()) return;
    idleTimer = setTimeout(() => {
      if (listenVisible() && captionsAppearRunning() && !document.body.classList.contains('eh-history-open')) document.body.classList.add('eh-listen-focus');
    }, 3400);
  }
  ['pointerdown','touchstart','keydown'].forEach(name => document.addEventListener(name, wakeControls, {passive:true}));
  $('#captionToggle')?.addEventListener('click', () => setTimeout(wakeControls, 150), true);
  $$('.tab[data-screen]').forEach(t => t.addEventListener('click', () => setTimeout(wakeControls, 80)));
  wakeControls();

  const HISTORY_KEY = 'echohalo-caption-history-v122';
  let savedHistory = [];
  let pendingPartial = null;
  let partialTimer = 0;
  let suppressObserver = false;
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    if (Array.isArray(parsed)) savedHistory = parsed.slice(0,30);
  } catch (_) {}

  function cleanText(v){ return String(v || '').replace(/\s+/g,' ').trim(); }
  function isPlaceholder(v){
    const t = cleanText(v).toLowerCase();
    return !t || /^(tap |caption history cleared|waiting|listening|start captions|ready)/.test(t);
  }
  function saveHistory(){ try { localStorage.setItem(HISTORY_KEY, JSON.stringify(savedHistory.slice(0,30))); } catch (_) {} }
  function directionGlyph(side){ return side==='left'?'←':side==='right'?'→':side==='behind'?'↓':side==='front'?'↑':''; }
  function renderSavedHistory(){
    const el = $('#captionHistory'); if (!el) return;
    suppressObserver = true;
    if (!savedHistory.length) el.innerHTML = '<div class="sub">No captions yet.</div>';
    else {
      el.innerHTML = '';
      for (const x of savedHistory) {
        const side = String(x.direction || 'unknown').toLowerCase();
        const d = document.createElement('div'); d.className='history-item'+(side!=='unknown'?' '+side:'');
        const tm = document.createElement('div'); tm.className='history-time';
        const dt = new Date(x.time || Date.now()); tm.textContent = dt.toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});
        const row = document.createElement('div'); row.className='history-caption-row';
        const glyph = directionGlyph(side);
        if (glyph) { const a=document.createElement('span');a.className='history-arrow '+side;a.textContent=glyph;row.appendChild(a); }
        const p=document.createElement('div');p.textContent=x.text;row.appendChild(p);d.append(tm,row);el.appendChild(d);
      }
    }
    queueMicrotask(() => { suppressObserver=false; });
  }
  function commitHistory(text, direction='unknown', source='final'){
    text = cleanText(text); if (isPlaceholder(text) || text.length < 2) return;
    const now = Date.now(); const first = savedHistory[0];
    if (first && now-(first.time||0)<6500 &&
        (text.toLowerCase().startsWith(String(first.text||'').toLowerCase()) || String(first.text||'').toLowerCase().startsWith(text.toLowerCase()))) {
      if (text.length >= String(first.text||'').length) { first.text=text; first.time=now; first.direction=direction||first.direction||'unknown'; first.source=source; }
    } else if (!first || String(first.text||'').toLowerCase() !== text.toLowerCase()) {
      savedHistory.unshift({text,time:now,direction:direction||'unknown',source});
      if (savedHistory.length>30) savedHistory.length=30;
    }
    saveHistory(); renderSavedHistory();
  }
  function schedulePartialRescue(){
    clearTimeout(partialTimer);
    partialTimer=setTimeout(()=>{ if (!pendingPartial) return; const p=pendingPartial; pendingPartial=null; commitHistory(p.text,p.direction,'rescued-partial'); },1900);
  }
  renderSavedHistory();

  $('#clearHistory')?.addEventListener('click', () => {
    savedHistory=[];pendingPartial=null;clearTimeout(partialTimer);saveHistory();setTimeout(renderSavedHistory,0);
  }, true);

  const finalCaption = $('#finalCaption');
  if (finalCaption) {
    let previousFinal = cleanText(finalCaption.textContent);
    new MutationObserver(() => {
      if (suppressObserver) return;
      const t=cleanText(finalCaption.textContent);
      if (t && t!==previousFinal && !isPlaceholder(t)) commitHistory(t,'unknown','dom-final');
      previousFinal=t;
    }).observe(finalCaption,{childList:true,subtree:true,characterData:true});
  }

  let resumeCaptionsAfterBrowserMic = false;
  let browserMicPause = false;
  function captionIntent(){ return captionsAppearRunning(); }
  function pauseForBrowserMic(label){
    if (browserMicPause) return;
    browserMicPause=true;
    resumeCaptionsAfterBrowserMic = resumeCaptionsAfterBrowserMic || captionIntent();
    try { native.stopNativeCaptions(); } catch (_) {}
    try { native.stopSpatial(); } catch (_) {}
    const detail=$('#captionStateDetail'); if(detail) detail.textContent=label || 'Microphone handed to Voice Mirror.';
  }
  function mirrorLooksRunning(){
    const a=($('#mirrorToggle')?.textContent||'').toLowerCase();
    const b=($('#worshipMicBtn')?.textContent||'').toLowerCase();
    return a.includes('stop microphone') || b.includes('stop voice mirror');
  }
  function resumeNativeAudio(forceCaptions=false){
    if (mirrorLooksRunning()) return;
    browserMicPause=false;
    try { native.startSpatial(); } catch (_) {}
    if (resumeCaptionsAfterBrowserMic && (forceCaptions || listenVisible())) {
      const lang=$('#speechLang')?.value||'en-US';
      setTimeout(()=>{ try{native.startNativeCaptions(lang);}catch(_){} },420);
      resumeCaptionsAfterBrowserMic=false;
    }
  }

  for (const id of ['mirrorToggle','worshipMicBtn']) {
    const b=$('#'+id); if(!b) continue;
    b.addEventListener('click', () => {
      const stopping = /stop/i.test(b.textContent||'');
      if (stopping) setTimeout(()=>resumeNativeAudio(false),650);
      else pauseForBrowserMic(id==='worshipMicBtn'?'Worship Voice Mirror is using the microphone.':'Voice Mirror is using the microphone.');
    }, true);
  }
  $$('.tab[data-screen]').forEach(tab => tab.addEventListener('click', () => {
    const screen=tab.dataset.screen||'';
    if (screen==='worship' || screen==='mirror') pauseForBrowserMic('Voice tools have temporary microphone control.');
    else if (screen==='listen') setTimeout(()=>resumeNativeAudio(true),420);
  }, true));

  const prior=window.echoHaloNativeEvent;
  window.echoHaloNativeEvent=e=>{
    if(prior) try{prior(e);}catch(err){console.warn(err);}
    if(!e||!e.type)return;
    if(e.type==='nativeCaption'){
      const text=cleanText(e.text);if(!text)return;
      const dir=String(e.direction||'unknown').toLowerCase();
      if(e.final){pendingPartial=null;clearTimeout(partialTimer);commitHistory(text,dir,'native-final');}
      else{pendingPartial={text,direction:dir};schedulePartialRescue();}
    }else if(e.type==='nativeCaptionStatus'){
      const state=String(e.state||'');
      if((state==='stopped'||state==='error')&&pendingPartial)schedulePartialRescue();
    }
  };

  const scoutInstruction=$('#ehScoutInstruction');
  if (scoutInstruction && !$('#ehScoutDiagram')) {
    const vis=document.createElement('div');
    vis.id='ehScoutDiagram';vis.className='eh-scout-visual';
    vis.innerHTML=`<div class="eh-scout-orientation" id="ehScoutOrientation">PORTRAIT</div><div class="eh-scout-note">screen faces you<br>phone stays upright</div><div class="eh-scout-stage"><span class="eh-scout-sound left" id="ehScoutSoundLeft">✦</span><div class="eh-scout-phone portrait" id="ehScoutPhone"><span class="eh-scout-top">TOP EDGE</span><span class="eh-scout-camera"></span><span class="eh-scout-screen"></span></div><span class="eh-scout-sound right" id="ehScoutSoundRight">✦</span><span class="eh-scout-face">SCREEN → YOU</span></div>`;
    scoutInstruction.parentElement.insertBefore(vis,scoutInstruction);
  }
  function updateScoutVisual(){
    const phone=$('#ehScoutPhone'),ori=$('#ehScoutOrientation'); if(!phone||!ori)return;
    const txt=((scoutInstruction?.textContent||'')+' '+($('#ehScoutCapture')?.textContent||'')).toUpperCase();
    let pose='portrait',label='PORTRAIT';
    if (txt.includes('TOP EDGE LEFT')) {pose='landscape landscape-left';label='LANDSCAPE · TOP EDGE LEFT';}
    else if (txt.includes('TOP EDGE RIGHT')) {pose='landscape landscape-right';label='LANDSCAPE · TOP EDGE RIGHT';}
    phone.className='eh-scout-phone '+pose;ori.textContent=label;
    $('#ehScoutSoundLeft')?.classList.toggle('active',txt.includes('LEFT'));
    $('#ehScoutSoundRight')?.classList.toggle('active',txt.includes('RIGHT'));
  }
  if (scoutInstruction) new MutationObserver(updateScoutVisual).observe(scoutInstruction,{childList:true,subtree:true,characterData:true});
  $('#ehScoutStart')?.addEventListener('click',()=>setTimeout(updateScoutVisual,0));
  $('#ehScoutCapture')?.addEventListener('click',()=>setTimeout(updateScoutVisual,0));
  updateScoutVisual();

  const footer=document.querySelector('.footer');
  if(footer) footer.textContent='EchoHalo v1.2.2 • Caption-first Spatial Audio • Accessibility prototype • Not a medical device.';
  const micNote=$('#ehNativeMicNote');
  if(micNote) micNote.textContent='EchoHalo coordinates microphone ownership automatically: native captions + Spatial Compass share one stream; Voice Mirror temporarily takes the mic and EchoHalo restores the native stream afterward.';
})();
'''

js += addon
asset.write_text(js)

assert "versionName '1.2.2'" in build.read_text()
assert 'private static final String VERSION = "1.2.2";' in main.read_text()
assert '__echoHaloDailyUseV122' in asset.read_text()
assert 'ehScoutDiagram' in asset.read_text()
assert 'echohalo-caption-history-v122' in asset.read_text()
assert 'pauseForBrowserMic' in asset.read_text()
print('EchoHalo v1.2.2 daily-use usability patch complete')
