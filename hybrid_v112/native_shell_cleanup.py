from pathlib import Path
import re
import sys

project = Path(sys.argv[1])
build = project / 'app/build.gradle'
asset = project / 'app/src/main/assets/spatial_inject.js'

text = build.read_text()
text = re.sub(r"versionCode\s+\d+", "versionCode 11", text, count=1)
text = re.sub(r"versionName\s+'[^']+'", "versionName '1.1.2'", text, count=1)
build.write_text(text)

js = asset.read_text()
js = js.replace(
    'EchoHalo v1.1.1 • Native Spatial Compass integrated',
    'EchoHalo v1.1.2 • Native Spatial Compass integrated',
    1,
)

anchor = "  native.startSpatial();\n"
if anchor not in js:
    raise SystemExit('native start anchor not found')

cleanup = r'''  // Native-shell cleanup. The hosted EchoHalo UI also supports standalone
  // browsers, but its browser microphone picker and raw-browser hardware
  // diagnostics are misleading inside this Android shell. Keep the DOM nodes
  // needed by the existing Voice Mirror code, but present one Android-managed
  // microphone path to the user.
  const nativeMicSelect = document.getElementById('micSelect');
  if (nativeMicSelect) {
    nativeMicSelect.innerHTML = '<option value="">Android managed microphone</option>';
    nativeMicSelect.value = '';
    nativeMicSelect.disabled = true;
    const micLabel = nativeMicSelect.previousElementSibling;
    if (micLabel) micLabel.textContent = 'EchoHalo microphone';
  }

  const refreshMics = document.getElementById('refreshMics');
  if (refreshMics) refreshMics.style.display = 'none';

  if (nativeMicSelect && nativeMicSelect.parentElement && !document.getElementById('ehNativeMicNote')) {
    const note = document.createElement('div');
    note.id = 'ehNativeMicNote';
    note.className = 'okbox';
    note.style.marginTop = '8px';
    note.textContent = 'Android manages the handset microphone automatically. EchoHalo pauses Spatial Compass while captions or Voice Mirror need the mic, then resumes it afterward.';
    nativeMicSelect.parentElement.insertAdjacentElement('afterend', note);
  }

  const diagCard = document.querySelector('.diag-card');
  if (diagCard) diagCard.style.display = 'none';

  const nativeSpatialCard = document.getElementById('nativeSpatialSettings');
  if (nativeSpatialCard) {
    const stale = nativeSpatialCard.querySelector('.native-only-note');
    if (stale) stale.textContent = 'Native Spatial Report replaces the old browser-only hardware probes in this Android app.';
  }

  native.startSpatial();
'''
js = js.replace(anchor, cleanup, 1)
asset.write_text(js)
print('Applied EchoHalo v1.1.2 native-shell cleanup')
