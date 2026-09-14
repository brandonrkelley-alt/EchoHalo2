from pathlib import Path
import re
import sys

project = Path(sys.argv[1])
build = project / 'app/build.gradle'
asset = project / 'app/src/main/assets/spatial_inject.js'

# Bump Android package version from the reconstructed v1.1.0 overlay.
text = build.read_text()
text = re.sub(r"versionCode\s+\d+", "versionCode 10", text, count=1)
text = re.sub(r"versionName\s+'[^']+'", "versionName '1.1.1'", text, count=1)
build.write_text(text)

js = asset.read_text()
anchor = "  const native = window.EchoHaloNative;\n  if (!native) return;\n"
if anchor not in js:
    raise SystemExit('native bridge anchor not found')

arbiter = r'''  const native = window.EchoHaloNative;
  if (!native) return;

  // v1.1.1 microphone arbiter. Samsung/Android does not reliably allow the
  // native CAMCORDER AudioRecord and WebView getUserMedia/Web Speech to own
  // the handset microphone at the same time. Release native capture before a
  // browser microphone feature starts, then resume Spatial Compass when that
  // browser session is actually finished.
  const micArbiter = (() => {
    let browserTrackRefs = 0;
    let speechActive = false;
    let resumeTimer = 0;

    const clearResume = () => {
      if (resumeTimer) {
        clearTimeout(resumeTimer);
        resumeTimer = 0;
      }
    };

    const setPausedUi = label => {
      const d = document.querySelector('#ehDirection');
      const c = document.querySelector('#ehConfidence');
      if (d) d.textContent = 'SPATIAL PAUSED';
      if (c) c.textContent = label || 'Another EchoHalo feature is using the microphone.';
    };

    const pauseNative = label => {
      clearResume();
      try { native.stopSpatial(); } catch (_) {}
      setPausedUi(label);
    };

    const resumeNativeSoon = (delay = 450) => {
      clearResume();
      if (browserTrackRefs > 0 || speechActive) return;
      resumeTimer = setTimeout(() => {
        resumeTimer = 0;
        if (browserTrackRefs > 0 || speechActive) return;
        try { native.startSpatial(); } catch (_) {}
      }, delay);
    };

    const releaseTrack = track => {
      if (!track || track.__ehNativeWrapped) return;
      track.__ehNativeWrapped = true;
      browserTrackRefs++;
      let released = false;
      const release = () => {
        if (released) return;
        released = true;
        browserTrackRefs = Math.max(0, browserTrackRefs - 1);
        resumeNativeSoon();
      };
      const realStop = track.stop.bind(track);
      try {
        track.stop = function () {
          try { return realStop(); }
          finally { release(); }
        };
      } catch (_) {}
      try { track.addEventListener('ended', release, { once: true }); } catch (_) {}
    };

    const md = navigator.mediaDevices;
    if (md && md.getUserMedia && !md.__ehNativeMicArbiter) {
      md.__ehNativeMicArbiter = true;
      const realGum = md.getUserMedia.bind(md);
      md.getUserMedia = async constraints => {
        const wantsAudio = !!(constraints && constraints.audio);
        if (wantsAudio) {
          pauseNative('Voice Mirror / browser audio is using the microphone.');
          // stopSpatial is marshalled onto Android's main thread. Give the
          // AudioRecord a moment to release before WebView opens its stream.
          await new Promise(r => setTimeout(r, 220));
        }
        try {
          const stream = await realGum(constraints);
          if (wantsAudio) {
            const tracks = stream.getAudioTracks ? stream.getAudioTracks() : [];
            if (tracks.length) tracks.forEach(releaseTrack);
            else resumeNativeSoon();
          }
          return stream;
        } catch (err) {
          if (wantsAudio) resumeNativeSoon(600);
          throw err;
        }
      };
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR && SR.prototype && !SR.prototype.__ehNativeMicArbiter) {
      SR.prototype.__ehNativeMicArbiter = true;
      const realStart = SR.prototype.start;
      const realStop = SR.prototype.stop;
      const realAbort = SR.prototype.abort;

      SR.prototype.start = function () {
        clearResume();
        speechActive = true;
        pauseNative('Live captions are using the microphone.');
        const self = this;
        try {
          self.addEventListener('end', () => {
            speechActive = false;
            // EchoHalo normally restarts recognition after about 500 ms.
            // Waiting longer means that restart cancels this resume; a real
            // stop returns the mic to Spatial Compass automatically.
            resumeNativeSoon(950);
          }, { once: true });
        } catch (_) {}
        setTimeout(() => {
          try { realStart.call(self); }
          catch (e) {
            speechActive = false;
            resumeNativeSoon(600);
          }
        }, 220);
      };

      if (realStop) {
        SR.prototype.stop = function () {
          try { return realStop.call(this); }
          finally { speechActive = false; resumeNativeSoon(700); }
        };
      }
      if (realAbort) {
        SR.prototype.abort = function () {
          try { return realAbort.call(this); }
          finally { speechActive = false; resumeNativeSoon(700); }
        };
      }
    }

    return { pauseNative, resumeNativeSoon };
  })();
'''
js = js.replace(anchor, arbiter, 1)

js = js.replace(
    'EchoHalo v1.1.0 • Native Spatial Compass integrated',
    'EchoHalo v1.1.1 • Native Spatial Compass integrated',
    1,
)

end_anchor = "  $('#ehCopy')?.addEventListener('click',()=>native.copySpatialReport());\n  native.startSpatial();\n"
if end_anchor not in js:
    raise SystemExit('spatial footer anchor not found')

end_replacement = """  $('#ehCopy')?.addEventListener('click',()=>native.copySpatialReport());

  // Browser-only hardware probes are obsolete in the native shell and fight
  // the same microphone used by Spatial Compass. Keep the native spatial
  // report as the diagnostic surface instead of presenting buttons that fail.
  for (const id of ['runAudioDiag', 'runRouteProbe']) {
    const b = document.getElementById(id);
    if (b) {
      b.disabled = true;
      b.textContent = 'Use Native Spatial Report';
      b.title = 'Browser microphone hardware probes are disabled inside the native EchoHalo app.';
    }
  }

  native.startSpatial();
"""
js = js.replace(end_anchor, end_replacement, 1)
asset.write_text(js)

print('Applied EchoHalo v1.1.1 microphone arbitration patch')
