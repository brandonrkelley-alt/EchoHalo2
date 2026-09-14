from pathlib import Path
import re, sys

root = Path(sys.argv[1])
repo = Path(sys.argv[2])
java_dir = root / 'app/src/main/java/org/neocities/bk26/echohalospatial'
main = java_dir / 'MainActivity.java'
engine = java_dir / 'SpatialAudioEngine.java'
manifest = root / 'app/src/main/AndroidManifest.xml'
build = root / 'app/build.gradle'
asset = root / 'app/src/main/assets/spatial_inject.js'

(java_dir / 'NativeCaptionEngine.java').write_text((repo / 'hybrid_v120/NativeCaptionEngine.java').read_text())

s = build.read_text()
s = re.sub(r"versionCode\s+\d+", "versionCode 12", s, count=1)
s = re.sub(r"versionName\s+'[^']+'", "versionName '1.2.0'", s, count=1)
build.write_text(s)

s = manifest.read_text()
if 'android.speech.RecognitionService' not in s:
    marker = '    <application\n'
    queries = '''    <queries>\n        <intent>\n            <action android:name="android.speech.RecognitionService" />\n        </intent>\n    </queries>\n\n'''
    if marker not in s:
        raise SystemExit('manifest application anchor not found')
    s = s.replace(marker, queries + marker, 1)
manifest.write_text(s)

s = engine.read_text()
listener_anchor = '''    public interface Listener {\n        void onEngineStatus(String text, boolean error);'''
if listener_anchor not in s:
    raise SystemExit('engine Listener anchor missing')
s = s.replace(listener_anchor, '''    public interface PcmTap {\n        void onStereoPcm(short[] interleaved, int frameCount);\n    }\n\n    public interface Listener {\n        void onEngineStatus(String text, boolean error);''', 1)

field_anchor = '''    private AudioRecord record;\n    private Direction calibrationTarget;'''
if field_anchor not in s:
    raise SystemExit('engine record field anchor missing')
s = s.replace(field_anchor, '''    private AudioRecord record;\n    private volatile PcmTap pcmTap;\n    private Direction calibrationTarget;''', 1)

getter_anchor = '''    public double getLiveNoiseDb() { return liveNoiseDb; }\n    public double getLiveThresholdDb() { return liveThresholdDb; }'''
if getter_anchor not in s:
    raise SystemExit('engine getter anchor missing')
s = s.replace(getter_anchor, getter_anchor + '''\n    public void setPcmTap(PcmTap tap) { pcmTap = tap; }''', 1)

read_anchor = '''                if (n <= 0) continue;\n                if (n < FRAME_SHORTS) continue;\n                Feature f = FeatureExtractor.extract(data, FRAME_SAMPLES, SAMPLE_RATE);'''
if read_anchor not in s:
    raise SystemExit('engine audio read anchor missing')
s = s.replace(read_anchor, '''                if (n <= 0) continue;\n                if (n < FRAME_SHORTS) continue;\n                PcmTap tap = pcmTap;\n                if (tap != null) {\n                    try { tap.onStereoPcm(data, n / 2); } catch (Throwable ignored) {}\n                }\n                Feature f = FeatureExtractor.extract(data, FRAME_SAMPLES, SAMPLE_RATE);''', 1)

s = s.replace('return context.getSharedPreferences("echohalo_native_spatial_v110", Context.MODE_PRIVATE);',
              'return context.getSharedPreferences("echohalo_native_spatial_v120_gccphat", Context.MODE_PRIVATE);')
s = s.replace('b.append("EchoHalo Native Spatial Engine v1.1.0\\n");',
              'b.append("EchoHalo Native Spatial Engine v1.2.0\\n");')
s = s.replace('b.append("Classifier features: GCC-style interchannel lag + low/mid/high interchannel level difference + peak correlation\\n");',
              'b.append("Classifier features: partial GCC-PHAT lag (SpeechCompass-style exponent -0.3) + low/mid/high ILD + lag correlation\\n");')

feature_start = s.index('    private static class FeatureExtractor {')
outer_close = s.rfind('\n}')
if feature_start < 0 or outer_close <= feature_start:
    raise SystemExit('FeatureExtractor bounds missing')
new_feature = r'''    private static class FeatureExtractor {
        private static final int MAX_LAG = 32;
        private static final double PHAT_EXPONENT = -0.3;

        static Feature extract(short[] interleaved, int frames, int sr) {
            int n = Math.min(frames, FRAME_SAMPLES);
            double[] l = new double[FRAME_SAMPLES];
            double[] r = new double[FRAME_SAMPLES];
            double sumSqL = 0, sumSqR = 0, meanL = 0, meanR = 0;
            for (int i = 0; i < n; i++) {
                l[i] = interleaved[i * 2] / 32768.0;
                r[i] = interleaved[i * 2 + 1] / 32768.0;
                meanL += l[i]; meanR += r[i];
                sumSqL += l[i] * l[i]; sumSqR += r[i] * r[i];
            }
            meanL /= n; meanR /= n;
            double rms = Math.sqrt((sumSqL + sumSqR) / (2.0 * n));
            double rmsDb = 20.0 * Math.log10(rms + 1e-12);

            double[] reL = new double[FRAME_SAMPLES];
            double[] imL = new double[FRAME_SAMPLES];
            double[] reR = new double[FRAME_SAMPLES];
            double[] imR = new double[FRAME_SAMPLES];
            for (int i = 0; i < FRAME_SAMPLES; i++) {
                double w = 0.5 - 0.5 * Math.cos(2.0 * Math.PI * i / (FRAME_SAMPLES - 1));
                reL[i] = (l[i] - meanL) * w;
                reR[i] = (r[i] - meanR) * w;
            }
            fft(reL, imL);
            fft(reR, imR);

            double[] gccRe = new double[FRAME_SAMPLES];
            double[] gccIm = new double[FRAME_SAMPLES];
            for (int k = 0; k < FRAME_SAMPLES; k++) {
                double cr = reL[k] * reR[k] + imL[k] * imR[k];
                double ci = imL[k] * reR[k] - reL[k] * imR[k];
                double magSq = cr * cr + ci * ci;
                if (magSq < 1e-24) {
                    gccRe[k] = 0; gccIm[k] = 0;
                } else {
                    double weight = Math.pow(magSq, PHAT_EXPONENT);
                    gccRe[k] = cr * weight;
                    gccIm[k] = ci * weight;
                }
            }
            ifft(gccRe, gccIm);

            int bestLag = 0;
            double bestPeak = -Double.MAX_VALUE;
            for (int lag = -MAX_LAG; lag <= MAX_LAG; lag++) {
                double v = gccRe[indexForLag(lag, FRAME_SAMPLES)];
                if (v > bestPeak) { bestPeak = v; bestLag = lag; }
            }
            int bi = indexForLag(bestLag, FRAME_SAMPLES);
            double ym = gccRe[(bi - 1 + FRAME_SAMPLES) % FRAME_SAMPLES];
            double y0 = gccRe[bi];
            double yp = gccRe[(bi + 1) % FRAME_SAMPLES];
            double denom = ym - 2.0 * y0 + yp;
            double frac = Math.abs(denom) < 1e-18 ? 0.0 : 0.5 * (ym - yp) / denom;
            frac = Math.max(-0.5, Math.min(0.5, frac));
            double lagSamples = bestLag + frac;

            double lagCorr = Math.abs(correlationAtLag(l, r, meanL, meanR, (int)Math.round(lagSamples), n));
            double[] eL = bandEnergy(reL, imL, sr);
            double[] eR = bandEnergy(reR, imR, sr);
            double ildLow = 10 * Math.log10((eR[0] + 1e-18) / (eL[0] + 1e-18));
            double ildMid = 10 * Math.log10((eR[1] + 1e-18) / (eL[1] + 1e-18));
            double ildHigh = 10 * Math.log10((eR[2] + 1e-18) / (eL[2] + 1e-18));
            return new Feature(lagSamples, ildLow, ildMid, ildHigh,
                    Math.max(0, Math.min(1, lagCorr)), rmsDb);
        }

        private static int indexForLag(int lag, int n) { return lag >= 0 ? lag : n + lag; }

        private static double correlationAtLag(double[] l, double[] r, double meanL, double meanR, int lag, int n) {
            double num = 0, a = 0, b = 0;
            int start = Math.max(0, -lag);
            int end = Math.min(n, n - lag);
            for (int i = start; i < end; i++) {
                double lv = l[i] - meanL;
                double rv = r[i + lag] - meanR;
                num += lv * rv;
                a += lv * lv;
                b += rv * rv;
            }
            return num / Math.sqrt(a * b + 1e-18);
        }

        private static double[] bandEnergy(double[] re, double[] im, int sr) {
            double[] e = new double[3];
            int ny = re.length / 2;
            for (int k = 1; k < ny; k++) {
                double hz = (double) k * sr / re.length;
                int band = hz >= 300 && hz < 1200 ? 0 : hz >= 1200 && hz < 3000 ? 1 : hz >= 3000 && hz < 8000 ? 2 : -1;
                if (band >= 0) e[band] += re[k] * re[k] + im[k] * im[k];
            }
            return e;
        }

        private static void ifft(double[] re, double[] im) {
            for (int i = 0; i < im.length; i++) im[i] = -im[i];
            fft(re, im);
            double inv = 1.0 / re.length;
            for (int i = 0; i < re.length; i++) {
                re[i] *= inv;
                im[i] = -im[i] * inv;
            }
        }

        private static void fft(double[] re, double[] im) {
            int n = re.length;
            for (int i = 1, j = 0; i < n; i++) {
                int bit = n >> 1;
                for (; (j & bit) != 0; bit >>= 1) j ^= bit;
                j ^= bit;
                if (i < j) {
                    double tr = re[i]; re[i] = re[j]; re[j] = tr;
                    double ti = im[i]; im[i] = im[j]; im[j] = ti;
                }
            }
            for (int len = 2; len <= n; len <<= 1) {
                double ang = -2 * Math.PI / len;
                double wLenR = Math.cos(ang), wLenI = Math.sin(ang);
                for (int i = 0; i < n; i += len) {
                    double wr = 1, wi = 0;
                    for (int j = 0; j < len / 2; j++) {
                        int u = i + j, v = i + j + len / 2;
                        double vr = re[v] * wr - im[v] * wi;
                        double vi = re[v] * wi + im[v] * wr;
                        double ur = re[u], ui = im[u];
                        re[u] = ur + vr; im[u] = ui + vi;
                        re[v] = ur - vr; im[v] = ui - vi;
                        double nwr = wr * wLenR - wi * wLenI;
                        wi = wr * wLenI + wi * wLenR;
                        wr = nwr;
                    }
                }
            }
        }
    }
'''
s = s[:feature_start] + new_feature + s[outer_close:]
engine.write_text(s)

s = main.read_text()
s = s.replace('import java.util.EnumMap;\n', 'import java.util.ArrayDeque;\nimport java.util.EnumMap;\n', 1)
s = s.replace('private static final String VERSION = "1.1.0";', 'private static final String VERSION = "1.2.0";', 1)
field_anchor = '''    private WebView web;\n    private SpatialAudioEngine engine;\n    private SensorManager sensorManager;'''
if field_anchor not in s:
    raise SystemExit('MainActivity field anchor missing')
s = s.replace(field_anchor, '''    private WebView web;\n    private SpatialAudioEngine engine;\n    private NativeCaptionEngine captionEngine;\n    private SensorManager sensorManager;''', 1)
history_anchor = '''    private String recommendedPose = "";\n\n    @Override'''
if history_anchor not in s:
    raise SystemExit('MainActivity history anchor missing')
s = s.replace(history_anchor, '''    private String recommendedPose = "";\n\n    private static final long DIRECTION_HISTORY_NS = 12_000_000_000L;\n    private final ArrayDeque<DirectionSample> directionHistory = new ArrayDeque<>();\n\n    private static class DirectionSample {\n        final long t;\n        final double[] posterior;\n        final double confidence;\n        DirectionSample(long t, double[] posterior, double confidence) {\n            this.t = t; this.posterior = posterior; this.confidence = confidence;\n        }\n    }\n\n    @Override''', 1)
create_anchor = '''        engine = new SpatialAudioEngine(this, this);\n        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);'''
if create_anchor not in s:
    raise SystemExit('MainActivity engine creation anchor missing')
s = s.replace(create_anchor, '''        engine = new SpatialAudioEngine(this, this);\n        captionEngine = new NativeCaptionEngine(this, new NativeCaptionEngine.Listener() {\n            @Override public void onCaptionStatus(String state, String detail, boolean error) {\n                sendNativeCaptionStatus(state, detail, error);\n            }\n            @Override public void onCaptionText(String text, boolean isFinal, long speechStartNanos, long speechEndNanos) {\n                sendNativeCaption(text, isFinal, speechStartNanos, speechEndNanos);\n            }\n        });\n        engine.setPcmTap(captionEngine);\n        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);''', 1)
s = s.replace('''    protected void onDestroy() {\n        if (engine != null) engine.stop();''', '''    protected void onDestroy() {\n        if (captionEngine != null) captionEngine.stop();\n        if (engine != null) engine.stop();''', 1)
class_anchor = '''    @Override\n    public void onClassification(SpatialAudioEngine.ClassificationResult r) {\n        long now = android.os.SystemClock.elapsedRealtime();'''
if class_anchor not in s:
    raise SystemExit('classification anchor missing')
s = s.replace(class_anchor, '''    @Override\n    public void onClassification(SpatialAudioEngine.ClassificationResult r) {\n        rememberDirection(r);\n        long now = android.os.SystemClock.elapsedRealtime();''', 1)
bridge_anchor = '''        @JavascriptInterface\n        public String getVersion() { return VERSION; }\n\n        @JavascriptInterface\n        public void startSpatial() {'''
if bridge_anchor not in s:
    raise SystemExit('bridge version anchor missing')
s = s.replace(bridge_anchor, '''        @JavascriptInterface\n        public String getVersion() { return VERSION; }\n\n        @JavascriptInterface\n        public boolean nativeCaptionsAvailable() {\n            return NativeCaptionEngine.isSupported(MainActivity.this);\n        }\n\n        @JavascriptInterface\n        public void startNativeCaptions(String languageTag) {\n            runOnUiThread(() -> {\n                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {\n                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC);\n                    sendNativeCaptionStatus("error", "Microphone permission is required for captions.", true);\n                    return;\n                }\n                startSpatialEngine();\n                if (engine.hasAllProfiles() && isCalibrationPoseMatch()) engine.setLiveEnabled(true);\n                captionEngine.start(languageTag);\n            });\n        }\n\n        @JavascriptInterface\n        public void stopNativeCaptions() {\n            runOnUiThread(() -> captionEngine.stop());\n        }\n\n        @JavascriptInterface\n        public void startSpatial() {''', 1)
helper_anchor = '''    @Override\n    public void onSensorChanged(SensorEvent event) {'''
if helper_anchor not in s:
    raise SystemExit('sensor helper anchor missing')
helpers = r'''    private void rememberDirection(SpatialAudioEngine.ClassificationResult r) {
        if (r == null || !r.accepted || r.posterior == null || r.posterior.length < 4) return;
        long t = r.timestampNanos;
        synchronized (directionHistory) {
            directionHistory.addLast(new DirectionSample(t, r.posterior.clone(), r.confidence));
            while (!directionHistory.isEmpty() && t - directionHistory.peekFirst().t > DIRECTION_HISTORY_NS) {
                directionHistory.removeFirst();
            }
        }
    }

    private JSONObject phraseDirection(long startNanos, long endNanos) {
        try {
            long duration = Math.max(0L, endNanos - startNanos);
            long tailTrim = Math.min(700_000_000L, duration / 3L);
            long from = Math.max(0L, startNanos - 250_000_000L);
            long to = Math.max(from, endNanos - tailTrim);
            double[] sum = new double[4];
            double total = 0;
            DirectionSample fallback = null;
            synchronized (directionHistory) {
                for (DirectionSample sample : directionHistory) {
                    if (sample.t <= endNanos) fallback = sample;
                    if (sample.t < from || sample.t > to) continue;
                    double w = Math.max(0.15, sample.confidence);
                    for (int i = 0; i < 4; i++) sum[i] += sample.posterior[i] * w;
                    total += w;
                }
            }
            if (total <= 1e-9 && fallback != null && endNanos - fallback.t < 1_500_000_000L) {
                for (int i = 0; i < 4; i++) sum[i] = fallback.posterior[i];
                total = 1.0;
            }
            JSONObject out = new JSONObject();
            if (total <= 1e-9) return out;
            for (int i = 0; i < 4; i++) sum[i] /= total;
            int best = 0, second = 1;
            for (int i = 1; i < 4; i++) if (sum[i] > sum[best]) best = i;
            second = best == 0 ? 1 : 0;
            for (int i = 0; i < 4; i++) if (i != best && sum[i] > sum[second]) second = i;
            SpatialAudioEngine.Direction[] dirs = SpatialAudioEngine.Direction.values();
            out.put("direction", dirs[best].label);
            out.put("directionPosterior", sum[best]);
            out.put("directionRunner", dirs[second].label);
            out.put("directionRunnerPosterior", sum[second]);
            JSONArray a = new JSONArray();
            for (double v : sum) a.put(v);
            out.put("posterior", a);
            return out;
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    private void sendNativeCaptionStatus(String state, String detail, boolean error) {
        try {
            JSONObject j = new JSONObject();
            j.put("type", "nativeCaptionStatus");
            j.put("state", state == null ? "" : state);
            j.put("detail", detail == null ? "" : detail);
            j.put("error", error);
            sendEvent(j);
        } catch (Exception ignored) {}
    }

    private void sendNativeCaption(String text, boolean isFinal, long speechStartNanos, long speechEndNanos) {
        try {
            JSONObject j = new JSONObject();
            j.put("type", "nativeCaption");
            j.put("text", text == null ? "" : text);
            j.put("final", isFinal);
            JSONObject d = phraseDirection(speechStartNanos, speechEndNanos);
            java.util.Iterator<String> keys = d.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                j.put(key, d.get(key));
            }
            sendEvent(j);
        } catch (Exception ignored) {}
    }

'''
s = s.replace(helper_anchor, helpers + helper_anchor, 1)
main.write_text(s)

js = asset.read_text()
addon = r'''

// EchoHalo v1.2.0 — unified Spatial Caption surface.
(() => {
  if (window.__echoHaloSpatialCaptionV120) return;
  window.__echoHaloSpatialCaptionV120 = true;
  const native = window.EchoHaloNative;
  if (!native) return;
  const $ = s => document.querySelector(s);

  const style = document.createElement('style');
  style.textContent = `
    .eh-native-spatial{display:none!important}
    .hero-caption.eh-spatial-caption{position:relative;overflow:hidden;border:2px solid #2b363c!important;min-height:310px!important;padding:46px 28px 36px!important}
    .eh-cap-axis{position:absolute;z-index:2;color:#5f6b71;font-size:.62rem;font-weight:900;letter-spacing:.08em;pointer-events:none}
    .eh-cap-axis.f{top:10px;left:50%;transform:translateX(-50%)}.eh-cap-axis.b{bottom:9px;left:50%;transform:translateX(-50%)}
    .eh-cap-axis.l{left:10px;top:50%;transform:translateY(-50%)}.eh-cap-axis.r{right:10px;top:50%;transform:translateY(-50%)}
    .eh-cap-dot{position:absolute;z-index:4;left:50%;top:100%;width:20px;height:20px;margin:-10px;border-radius:50%;background:#42d7ff;box-shadow:0 0 15px #42d7ffbb,0 0 34px #42d7ff66;opacity:.12;pointer-events:none;transition:left .09s linear,top .09s linear,width .08s linear,height .08s linear,margin .08s linear,opacity .15s ease,filter .15s ease}
    .eh-cap-dot.uncertain{filter:blur(2.5px)}
    .eh-cap-pill{position:absolute;z-index:3;right:11px;top:10px;border:1px solid #2b3b42;border-radius:999px;background:#081014dd;color:#a8bec8;padding:4px 8px;font-size:.65rem;font-weight:850;letter-spacing:.02em}
    .eh-cap-pill.live{color:#9be6b3;border-color:#28563a}.eh-cap-pill.warn{color:#ffd47d;border-color:#634b22}
    .hero-caption.eh-spatial-caption .caption-line,.hero-caption.eh-spatial-caption .caption-interim{position:relative;z-index:1}
  `;
  document.head.appendChild(style);

  const hero = $('.hero-caption');
  if (hero) {
    hero.classList.add('eh-spatial-caption');
    for (const [cls,txt] of [['f','FRONT'],['l','L'],['r','R'],['b','BEHIND']]) {
      const n=document.createElement('span'); n.className='eh-cap-axis '+cls; n.textContent=txt; hero.appendChild(n);
    }
    const dot=document.createElement('span'); dot.id='ehCaptionSpatialDot'; dot.className='eh-cap-dot'; hero.appendChild(dot);
    const pill=document.createElement('span'); pill.id='ehCaptionSpatialPill'; pill.className='eh-cap-pill'; pill.textContent='SPATIAL SETUP'; hero.appendChild(pill);
  }

  const notice=$('#spatialNotice');
  if(notice) notice.textContent='Spatial Compass is integrated directly around the live caption. The border dot follows the sound source while the words stay centered.';

  let lastRms=-70, lastThreshold=-56, lastSpatialHit=0;
  let nativeCaptionsWanted=false;

  function setCaptionStateNative(kind,label,detail){
    const dot=$('#captionStateDot');
    if(dot) dot.className='caption-state-dot'+(kind?' '+kind:'');
    const l=$('#captionStateLabel'); if(l) l.textContent=label;
    const d=$('#captionStateDetail'); if(d) d.textContent=detail||'';
  }

  function moveDot(p,r,c){
    const d=$('#ehCaptionSpatialDot'), box=hero;
    if(!d||!box||!p||p.length<4)return;
    let x=(+p[2]||0)-(+p[0]||0), y=(+p[3]||0)-(+p[1]||0), m=Math.hypot(x,y);
    if(m<.015)return;
    x/=m; y/=m;
    const w=box.clientWidth,h=box.clientHeight, hw=Math.max(8,w/2-13), hh=Math.max(8,h/2-13);
    const t=Math.min(Math.abs(x)<.001?1e9:hw/Math.abs(x),Math.abs(y)<.001?1e9:hh/Math.abs(y));
    const px=w/2+x*t, py=h/2+y*t;
    const above=Math.max(0,(Number(r??lastRms)-lastThreshold));
    const intensity=Math.max(0,Math.min(1,above/28));
    const size=13+34*Math.sqrt(intensity);
    d.style.left=px+'px';d.style.top=py+'px';d.style.width=size+'px';d.style.height=size+'px';d.style.margin=(-size/2)+'px';
    d.style.opacity=String(.28+.72*Math.max(.12,Math.min(1,Number(c)||0)));
    d.classList.toggle('uncertain',(Number(c)||0)<.48);
  }

  function updatePill(direction,confidence){
    const p=$('#ehCaptionSpatialPill'); if(!p)return;
    if(!direction){p.className='eh-cap-pill warn';p.textContent='SPATIAL SETUP';return;}
    p.className='eh-cap-pill live';p.textContent=direction+' · '+Math.round((confidence||0)*100)+'%';
  }

  function applyCaptionDirection(e){
    if(!e || !e.direction) return;
    const side=String(e.direction).toLowerCase();
    try { if(typeof window.setDirection==='function') window.setDirection(side,'Native phrase direction'); else if(typeof setDirection==='function') setDirection(side,'Native phrase direction'); } catch(_){}
  }

  const prior=window.echoHaloNativeEvent;
  window.echoHaloNativeEvent=e=>{
    if(prior) try{prior(e);}catch(err){console.warn(err);}
    if(!e||!e.type)return;
    if(e.type==='feature'){
      lastRms=Number(e.rmsDb??-70); lastThreshold=Number(e.thresholdDb??-56);
      const d=$('#ehCaptionSpatialDot');
      if(d && lastRms<lastThreshold && Date.now()-lastSpatialHit>650)d.style.opacity='.10';
    }else if(e.type==='spatial'&&e.accepted){
      lastSpatialHit=Date.now(); moveDot(e.posterior,e.rmsDb??lastRms,e.confidence||0); updatePill(e.best,e.confidence||0);
    }else if(e.type==='initial'){
      if(e.ready) updatePill('LISTENING',1); else updatePill('',0);
    }else if(e.type==='calibrationCleared'){
      updatePill('',0);
    }else if(e.type==='nativeCaptionStatus'){
      const state=String(e.state||'');
      if(state==='listening') setCaptionStateNative('live','Listening',e.detail||'Spatial Compass + captions share one audio stream.');
      else if(state==='hearing') setCaptionStateNative('hearing','Hearing speech',e.detail||'Transcribing…');
      else if(state==='starting') setCaptionStateNative('warn','Starting',e.detail||'Starting native captions…');
      else if(state==='stopped') setCaptionStateNative('','Ready',e.detail||'Captions stopped.');
      else if(state==='error') setCaptionStateNative('warn','Caption engine',e.detail||'Native caption issue.');
    }else if(e.type==='nativeCaption'){
      const text=String(e.text||'').trim(); if(!text)return;
      applyCaptionDirection(e);
      if(e.final){
        const f=$('#finalCaption'),i=$('#interimCaption'); if(f)f.textContent=text;if(i)i.textContent='';
        try { if(typeof window.addCaption==='function') window.addCaption(text); else if(typeof addCaption==='function') addCaption(text); } catch(_){}
        setCaptionStateNative('hearing','Captioned','Listening for the next phrase…');
      }else{
        const i=$('#interimCaption'); if(i)i.textContent=text;
      }
    }
  };

  const toggle=$('#captionToggle');
  if(toggle){
    toggle.addEventListener('click',ev=>{
      if(!native.nativeCaptionsAvailable || !native.nativeCaptionsAvailable()) return;
      ev.preventDefault();ev.stopImmediatePropagation();
      if(nativeCaptionsWanted){
        nativeCaptionsWanted=false;native.stopNativeCaptions();toggle.textContent='Start Captions';
      }else{
        nativeCaptionsWanted=true;toggle.textContent='Stop Captions';
        const lang=$('#speechLang')?.value||'en-US';
        native.startSpatial();native.startNativeCaptions(lang);
        setCaptionStateNative('warn','Starting','Opening native shared-audio captions…');
      }
    },true);
  }

  const reset=$('#captionReset');
  if(reset){
    reset.addEventListener('click',ev=>{
      if(!nativeCaptionsWanted)return;
      ev.preventDefault();ev.stopImmediatePropagation();
      native.stopNativeCaptions();
      const lang=$('#speechLang')?.value||'en-US';
      setTimeout(()=>native.startNativeCaptions(lang),300);
      setCaptionStateNative('warn','Resetting','Restarting native caption recognizer…');
    },true);
  }

  const footer=document.querySelector('.footer');
  if(footer) footer.textContent='EchoHalo v1.2.0 • Unified Spatial Captions • Accessibility prototype • Not a medical device.';
})();
'''
js += addon
asset.write_text(js)

assert "versionName '1.2.0'" in build.read_text()
assert 'EXTRA_AUDIO_SOURCE' in (java_dir / 'NativeCaptionEngine.java').read_text()
assert 'partial GCC-PHAT' in engine.read_text()
assert 'startNativeCaptions' in main.read_text()
assert '__echoHaloSpatialCaptionV120' in asset.read_text()
assert 'android.speech.RecognitionService' in manifest.read_text()
print('EchoHalo v1.2.0 SpeechCompass-inspired shared-audio patch complete')
