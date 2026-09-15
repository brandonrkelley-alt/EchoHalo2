from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
build = root / 'app/build.gradle'
main = root / 'app/src/main/java/org/neocities/bk26/echohalospatial/MainActivity.java'
manifest = root / 'app/src/main/AndroidManifest.xml'
asset = root / 'app/src/main/assets/spatial_inject.js'

# Version bump.
s = build.read_text()
s = re.sub(r"versionCode\s+\d+", "versionCode 15", s, count=1)
s = re.sub(r"versionName\s+'[^']+'", "versionName '1.2.3'", s, count=1)
build.write_text(s)

# Native haptics + live pose override bridge.
s = manifest.read_text()
if 'android.permission.VIBRATE' not in s:
    marker = '<uses-permission android:name="android.permission.RECORD_AUDIO" />'
    if marker in s:
        s = s.replace(marker, marker + '\n    <uses-permission android:name="android.permission.VIBRATE" />', 1)
    else:
        s = s.replace('<manifest', '<manifest', 1)
        pos = s.find('>')
        s = s[:pos+1] + '\n    <uses-permission android:name="android.permission.VIBRATE" />' + s[pos+1:]
manifest.write_text(s)

s = main.read_text()
s = re.sub(r'private static final String VERSION = "[^"]+";',
           'private static final String VERSION = "1.2.3";', s, count=1)
anchor = '''        @JavascriptInterface\n        public String getVersion() { return VERSION; }\n'''
if anchor not in s:
    raise SystemExit('MainActivity bridge version anchor missing')
extra = anchor + '''\n        @JavascriptInterface\n        public void hapticPulse(int milliseconds) {\n            final int ms = Math.max(8, Math.min(250, milliseconds));\n            runOnUiThread(() -> {\n                try {\n                    android.os.Vibrator v;\n                    if (android.os.Build.VERSION.SDK_INT >= 31) {\n                        android.os.VibratorManager vm = getSystemService(android.os.VibratorManager.class);\n                        v = vm == null ? null : vm.getDefaultVibrator();\n                    } else {\n                        v = (android.os.Vibrator) getSystemService(Context.VIBRATOR_SERVICE);\n                    }\n                    if (v == null || !v.hasVibrator()) return;\n                    if (android.os.Build.VERSION.SDK_INT >= 26)\n                        v.vibrate(android.os.VibrationEffect.createOneShot(ms, android.os.VibrationEffect.DEFAULT_AMPLITUDE));\n                    else\n                        v.vibrate(ms);\n                } catch (Throwable ignored) {}\n            });\n        }\n\n        @JavascriptInterface\n        public void forceLiveSpatial() {\n            runOnUiThread(() -> {\n                startSpatialEngine();\n                if (engine != null && engine.hasAllProfiles()) engine.setLiveEnabled(true);\n            });\n        }\n'''
s = s.replace(anchor, extra, 1)
main.write_text(s)

js = asset.read_text()
addon = r'''

// EchoHalo v1.2.3 — runtime recovery patch.
// v1.2.2's build-time assets were present, but its UI initializer could miss the
// hosted DOM lifecycle. This patch waits for the actual EchoHalo controls before
// applying the visible layout, Scout diagrams, history capture, and mic handoff.
(() => {
  const native = window.EchoHaloNative;
  if (!native) return;

  // Stronger browser-mic handoff. Native captions must stop too, not only the
  // spatial AudioRecord. Retry NotReadableError once after a longer release gap.
  try {
    const md = navigator.mediaDevices;
    if (md && md.getUserMedia && !md.__echoHaloV123MicWrapper) {
      md.__echoHaloV123MicWrapper = true;
      const previous = md.getUserMedia.bind(md);
      md.getUserMedia = async constraints => {
        const wantsAudio = !!(constraints && constraints.audio);
        if (!wantsAudio) return previous(constraints);
        const releaseNative = async wait => {
          try { native.stopNativeCaptions(); } catch (_) {}
          try { native.stopSpatial(); } catch (_) {}
          await new Promise(r => setTimeout(r, wait));
        };
        await releaseNative(850);
        try {
          const stream = await previous(constraints);
          const tracks = stream && stream.getAudioTracks ? stream.getAudioTracks() : [];
          tracks.forEach(t => t.addEventListener('ended', () => setTimeout(() => { try { native.startSpatial(); } catch (_) {} }, 650), {once:true}));
          return stream;
        } catch (err) {
          if (err && err.name === 'NotReadableError') {
            await releaseNative(1150);
            const stream = await previous(constraints);
            const tracks = stream && stream.getAudioTracks ? stream.getAudioTracks() : [];
            tracks.forEach(t => t.addEventListener('ended', () => setTimeout(() => { try { native.startSpatial(); } catch (_) {} }, 650), {once:true}));
            return stream;
          }
          throw err;
        }
      };
    }
  } catch (_) {}

  let eventWrapped = false;
  let history = [];
  let historyTimer = 0;
  let latestText = '';
  let latestDirection = 'unknown';
  const HISTORY_KEY = 'echohalo-caption-history-v123';

  const clean = v => String(v || '').replace(/\s+/g,' ').trim();
  const glyph = d => d==='left'?'←':d==='right'?'→':d==='behind'?'↓':d==='front'?'↑':'';
  try {
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    if (Array.isArray(saved)) history = saved.slice(0,30);
  } catch (_) {}

  function persist(){ try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0,30))); } catch (_) {} }
  function renderHistory(){
    const el=document.querySelector('#captionHistory'); if(!el)return;
    if(!history.length){el.innerHTML='<div class="sub">No captions yet.</div>';return;}
    el.innerHTML='';
    history.forEach(x=>{
      const d=document.createElement('div'); d.className='history-item'+(x.direction&&x.direction!=='unknown'?' '+x.direction:'');
      const t=document.createElement('div');t.className='history-time';t.textContent=new Date(x.time||Date.now()).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});
      const row=document.createElement('div');row.className='history-caption-row';
      const g=glyph(x.direction); if(g){const a=document.createElement('span');a.className='history-arrow '+x.direction;a.textContent=g;row.appendChild(a);}
      const p=document.createElement('div');p.textContent=x.text;row.appendChild(p);d.append(t,row);el.appendChild(d);
    });
  }
  function commitHistory(text, direction='unknown'){
    text=clean(text); if(!text || text.length<2 || /^(waiting|listening|caption history cleared|tap )/i.test(text))return;
    const now=Date.now(); const first=history[0];
    if(first && now-(first.time||0)<7000 && (text.toLowerCase().startsWith(String(first.text||'').toLowerCase()) || String(first.text||'').toLowerCase().startsWith(text.toLowerCase()))) {
      if(text.length>=String(first.text||'').length){first.text=text;first.time=now;first.direction=direction||first.direction||'unknown';}
    } else if(!first || String(first.text||'').toLowerCase()!==text.toLowerCase()) {
      history.unshift({text,time:now,direction:direction||'unknown'}); if(history.length>30)history.length=30;
    }
    persist();renderHistory();
  }
  function rescueLater(text, direction){
    latestText=clean(text); latestDirection=direction||latestDirection||'unknown'; clearTimeout(historyTimer);
    historyTimer=setTimeout(()=>{ if(latestText) commitHistory(latestText,latestDirection); },1400);
  }

  function wrapNativeEvents(){
    if(eventWrapped)return; eventWrapped=true;
    const prior=window.echoHaloNativeEvent;
    window.echoHaloNativeEvent=e=>{
      if(prior)try{prior(e);}catch(err){console.warn('prior native event',err);}
      if(!e||!e.type)return;
      if(e.type==='nativeCaption'){
        const txt=clean(e.text); if(!txt)return;
        const dir=String(e.direction||'unknown').toLowerCase();
        if(e.final){clearTimeout(historyTimer);latestText='';commitHistory(txt,dir);}else rescueLater(txt,dir);
      }
    };
  }
  wrapNativeEvents();

  function installUi(){
    const listen=document.querySelector('#screen-listen');
    const grid=document.querySelector('#screen-listen>.grid.two');
    const spatial=document.querySelector('#ehSpatialSettings');
    if(!listen || !grid || !spatial) return false;
    if(document.querySelector('#ehV123RuntimeBadge')) return true;

    const cards=Array.from(grid.children).filter(x=>x.classList&&x.classList.contains('card'));
    const live=cards[0]||null, historyCard=cards[1]||null;
    if(live)live.id='ehLiveCaptionCardV123';
    if(historyCard)historyCard.id='ehHistoryCardV123';

    const style=document.createElement('style');style.id='eh-v123-style';style.textContent=`
      #screen-listen>.grid.two{grid-template-columns:minmax(0,1fr)!important;gap:8px!important}
      #ehHistoryCardV123{display:none!important}
      body.eh-v123-history #ehHistoryCardV123{display:block!important}
      #ehLiveCaptionCardV123{width:100%!important;max-width:none!important}
      .hero-caption.eh-spatial-caption{min-height:58svh!important;height:auto!important;display:flex!important;flex-direction:column!important;justify-content:center!important}
      .hero-caption.eh-spatial-caption .caption-text{font-size:calc(1.7rem * var(--caption-scale))!important;line-height:1.16!important}
      #ehHistoryToggleV123{margin-left:8px}
      body.eh-v123-focus .topbar{display:none!important}
      body.eh-v123-focus .tabs{opacity:.12!important;max-height:8px!important;min-height:0!important;overflow:hidden!important;padding:0!important;margin:0 0 2px!important}
      body.eh-v123-focus #ehLiveCaptionCardV123>.row.between,body.eh-v123-focus #captionStatus{opacity:.10!important;max-height:8px!important;min-height:0!important;overflow:hidden!important;padding-top:0!important;padding-bottom:0!important;margin:0!important}
      body.eh-v123-focus .hero-caption.eh-spatial-caption{min-height:calc(100svh - 26px)!important}
      @media (orientation:landscape){.hero-caption.eh-spatial-caption{min-height:70svh!important}.hero-caption.eh-spatial-caption .caption-text{font-size:calc(1.9rem * var(--caption-scale))!important}body.eh-v123-history #screen-listen>.grid.two{grid-template-columns:minmax(0,3.8fr) minmax(230px,1fr)!important}body.eh-v123-history #ehHistoryCardV123{display:block!important;max-height:calc(100svh - 66px)!important;overflow:auto!important}}
      .eh-v123-badge{display:inline-flex;align-items:center;gap:5px;border:1px solid #286478;background:#07171e;color:#9cecff;border-radius:999px;padding:5px 9px;font-size:.68rem;font-weight:900;margin-bottom:8px}
      .eh-pose-picker{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:10px 0 12px}
      .eh-pose-choice{position:relative;border:1px solid #30414a;background:#080d10;color:#d7e4ea;border-radius:14px;padding:10px 7px;min-height:124px;text-align:center;font-weight:850}
      .eh-pose-choice.active{border-color:#4fd4e1;box-shadow:0 0 0 1px #4fd4e155 inset;background:#09171b}
      .eh-pose-choice.recommended::after{content:'SCOUT PICK';position:absolute;top:5px;right:5px;font-size:.48rem;background:#624b22;color:#ffd47d;border-radius:999px;padding:2px 5px}
      .eh-mini-phone{position:relative;margin:8px auto 7px;width:34px;height:62px;border:2px solid #a8bbc4;border-radius:8px;background:#010203}
      .eh-mini-phone.land{width:62px;height:34px;margin-top:20px;margin-bottom:23px}
      .eh-mini-phone::before{content:'';position:absolute;inset:4px;border:1px solid #2b4853;border-radius:5px;background:linear-gradient(145deg,#10242c,#030607)}
      .eh-mini-phone::after{content:'';position:absolute;width:5px;height:5px;border-radius:50%;background:#43d8ff;box-shadow:0 0 7px #43d8ff}
      .eh-mini-phone.portrait::after{top:2px;left:50%;transform:translateX(-50%)}
      .eh-mini-phone.land.left::after{left:2px;top:50%;transform:translateY(-50%)}
      .eh-mini-phone.land.right::after{right:2px;top:50%;transform:translateY(-50%)}
      .eh-pose-label{font-size:.73rem;line-height:1.15}.eh-pose-sub{font-size:.58rem;color:#83969f;margin-top:4px;line-height:1.2}
      .eh-pose-status{border:1px solid #2c3e46;border-radius:12px;background:#05090b;padding:8px 10px;color:#a8bac2;font-size:.72rem;margin-top:4px}
      .eh-scout-diagram-v123{position:relative;height:152px;border:1px solid #2a3a42;border-radius:15px;background:radial-gradient(circle,#10232b,#030607 66%);margin:8px 0;overflow:hidden}
      .eh-scout-diagram-v123 .phone{position:absolute;left:50%;top:50%;width:48px;height:88px;transform:translate(-50%,-50%);border:3px solid #adbec6;border-radius:10px;background:#020304}
      .eh-scout-diagram-v123 .phone.land{width:88px;height:48px}.eh-scout-diagram-v123 .screen{position:absolute;inset:6px;border:1px solid #28505f;border-radius:6px}.eh-scout-diagram-v123 .topmark{position:absolute;color:#78def4;font-size:.56rem;font-weight:950}
      .eh-scout-diagram-v123 .sound{position:absolute;top:50%;font-size:1.5rem;color:#ffd47d;transform:translateY(-50%);opacity:.28}.eh-scout-diagram-v123 .sound.left{left:18px}.eh-scout-diagram-v123 .sound.right{right:18px}.eh-scout-diagram-v123 .sound.hot{opacity:1;text-shadow:0 0 14px #ffd47d}
      @media(max-width:560px){.eh-pose-picker{grid-template-columns:1fr}.eh-pose-choice{min-height:96px}.eh-mini-phone{transform:scale(.8);margin-top:2px;margin-bottom:2px}}
    `;document.head.appendChild(style);

    const badge=document.createElement('div');badge.id='ehV123RuntimeBadge';badge.className='eh-v123-badge';badge.textContent='v1.2.3 runtime patch active';spatial.insertBefore(badge,spatial.firstChild);

    if(live&&!document.querySelector('#ehHistoryToggleV123')){
      const b=document.createElement('button');b.id='ehHistoryToggleV123';b.className='btn ghost';b.type='button';b.textContent='History';
      (live.querySelector('.row.between')||live).appendChild(b);
      b.addEventListener('click',()=>{const open=!document.body.classList.contains('eh-v123-history');document.body.classList.toggle('eh-v123-history',open);b.textContent=open?'Hide History':'History';});
    }

    // Persistent history rescue works even if the recognizer only emits partials.
    renderHistory();
    ['#finalCaption','#interimCaption'].forEach(sel=>{
      const n=document.querySelector(sel); if(!n)return; let last=clean(n.textContent);
      new MutationObserver(()=>{const t=clean(n.textContent);if(t&&t!==last){last=t;rescueLater(t,latestDirection);}}).observe(n,{childList:true,subtree:true,characterData:true});
    });
    document.querySelector('#clearHistory')?.addEventListener('click',()=>{history=[];latestText='';clearTimeout(historyTimer);persist();setTimeout(renderHistory,0);},true);

    // Orientation selection is now manual as well as Scout-driven.
    const firstWizard=spatial.querySelector('.eh-wizard');
    const picker=document.createElement('div');picker.id='ehPosePickerV123';
    picker.innerHTML=`<div style="font-weight:900;color:#d9f7ff">Choose the orientation you want to use</div><div class="sub" style="margin-top:4px">Scout is advice, not a lock. Tap any pose at any time. Re-teach the four directions in that pose for the best accuracy.</div><div class="eh-pose-picker"><button class="eh-pose-choice" data-pose="PORTRAIT"><div class="eh-mini-phone portrait"></div><div class="eh-pose-label">Portrait</div><div class="eh-pose-sub">top edge up</div></button><button class="eh-pose-choice" data-pose="LANDSCAPE_TOP_LEFT"><div class="eh-mini-phone land left"></div><div class="eh-pose-label">Landscape</div><div class="eh-pose-sub">top edge left</div></button><button class="eh-pose-choice" data-pose="LANDSCAPE_TOP_RIGHT"><div class="eh-mini-phone land right"></div><div class="eh-pose-label">Landscape</div><div class="eh-pose-sub">top edge right</div></button></div><div class="eh-pose-status" id="ehPoseStatusV123">AUTO · Scout recommendation is currently advisory.</div>`;
    spatial.insertBefore(picker,firstWizard||spatial.children[1]||null);
    const poseStatus=picker.querySelector('#ehPoseStatusV123');
    const posePretty=p=>p==='PORTRAIT'?'Portrait':p==='LANDSCAPE_TOP_LEFT'?'Landscape · top edge left':'Landscape · top edge right';
    let selected='';try{selected=localStorage.getItem('echohalo-manual-pose-v123')||'';}catch(_){}
    function paintPose(){picker.querySelectorAll('[data-pose]').forEach(b=>b.classList.toggle('active',b.dataset.pose===selected));poseStatus.textContent=selected?('MANUAL · '+posePretty(selected)+' · live pose override enabled. Recalibrate here if direction quality changes.'):'AUTO · Scout recommendation is currently advisory.';}
    picker.querySelectorAll('[data-pose]').forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.pose;try{localStorage.setItem('echohalo-manual-pose-v123',selected);}catch(_){}paintPose();try{native.forceLiveSpatial();}catch(_){};}));
    paintPose();

    // Always-visible Scout diagram, updated from the current step text.
    const instruction=document.querySelector('#ehScoutInstruction');
    if(instruction&&!document.querySelector('#ehScoutDiagramV123')){
      const d=document.createElement('div');d.id='ehScoutDiagramV123';d.className='eh-scout-diagram-v123';d.innerHTML='<span class="sound left">✦</span><div class="phone"><span class="screen"></span><span class="topmark">TOP</span></div><span class="sound right">✦</span>';instruction.parentElement.insertBefore(d,instruction);
      const update=()=>{const txt=((instruction.textContent||'')+' '+(document.querySelector('#ehScoutCapture')?.textContent||'')).toUpperCase();const p=d.querySelector('.phone'),m=d.querySelector('.topmark');p.className='phone';m.style='';if(txt.includes('TOP EDGE LEFT')){p.classList.add('land');m.style='left:-27px;top:50%;transform:translateY(-50%) rotate(-90deg)';}else if(txt.includes('TOP EDGE RIGHT')){p.classList.add('land');m.style='right:-29px;top:50%;transform:translateY(-50%) rotate(90deg)';}else{m.style='top:-16px;left:50%;transform:translateX(-50%)';}d.querySelector('.sound.left').classList.toggle('hot',txt.includes('LEFT'));d.querySelector('.sound.right').classList.toggle('hot',txt.includes('RIGHT'));};
      new MutationObserver(update).observe(instruction,{childList:true,subtree:true,characterData:true});document.querySelector('#ehScoutCapture')?.addEventListener('click',()=>setTimeout(update,0));document.querySelector('#ehScoutStart')?.addEventListener('click',()=>setTimeout(update,0));update();
    }

    // Native haptic pulses follow the visible Worship beat; no WebView vibrate dependency.
    const beat=document.querySelector('#beatRow');
    if(beat){let lastPulse=0;new MutationObserver(()=>{if(document.querySelector('#hapticToggle')?.value!=='on')return;if(!beat.querySelector('.beat-dot.on'))return;const now=Date.now();if(now-lastPulse<120)return;lastPulse=now;try{native.hapticPulse(28);}catch(_){}}).observe(beat,{subtree:true,attributes:true,attributeFilter:['class']});}

    let idle=0;const wake=()=>{document.body.classList.remove('eh-v123-focus');clearTimeout(idle);const active=document.querySelector('#screen-listen.active');const stop=/stop captions/i.test(document.querySelector('#captionToggle')?.textContent||'');if(active&&stop&&!document.body.classList.contains('eh-v123-history'))idle=setTimeout(()=>{if(document.querySelector('#screen-listen.active')&&!document.body.classList.contains('eh-v123-history'))document.body.classList.add('eh-v123-focus');},3000);};
    ['pointerdown','touchstart','keydown'].forEach(n=>document.addEventListener(n,wake,{passive:true}));document.querySelector('#captionToggle')?.addEventListener('click',()=>setTimeout(wake,200),true);wake();

    const footer=document.querySelector('.footer');if(footer)footer.textContent='EchoHalo v1.2.3 • Caption-first Spatial Audio • Accessibility prototype • Not a medical device.';
    return true;
  }

  // The hosted page can finish constructing after the native injection runs.
  // Retry until the actual controls exist instead of silently missing them.
  let attempts=0;
  const boot=()=>{attempts++;try{if(installUi())return;}catch(e){console.warn('EchoHalo v1.2.3 UI boot retry',e);}if(attempts<80)setTimeout(boot,200);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
'''
js += addon
asset.write_text(js)

assert "versionName '1.2.3'" in build.read_text()
assert 'android.permission.VIBRATE' in manifest.read_text()
assert 'public void hapticPulse' in main.read_text()
assert 'public void forceLiveSpatial' in main.read_text()
assert '__echoHaloV123MicWrapper' in asset.read_text()
assert 'ehV123RuntimeBadge' in asset.read_text()
assert 'ehPosePickerV123' in asset.read_text()
assert 'ehScoutDiagramV123' in asset.read_text()
print('EchoHalo v1.2.3 runtime recovery patch complete')
