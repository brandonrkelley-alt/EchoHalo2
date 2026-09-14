from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
build = root / 'app/build.gradle'
manifest = root / 'app/src/main/AndroidManifest.xml'
asset = root / 'app/src/main/assets/spatial_inject.js'

# Version bump.
s = build.read_text()
s = re.sub(r"versionCode\s+\d+", "versionCode 13", s, count=1)
s = re.sub(r"versionName\s+'[^']+'", "versionName '1.2.1'", s, count=1)
build.write_text(s)

# Keep the Activity/WebView alive across Scout rotations. Recreating the Activity was
# throwing away JS/native Scout state and showing the hosted PWA launch screen again.
s = manifest.read_text()
if 'android:configChanges=' not in s:
    s = s.replace(
        'android:exported="true"',
        'android:exported="true"\n            android:configChanges="orientation|screenSize|smallestScreenSize|screenLayout|keyboardHidden|uiMode"',
        1,
    )
else:
    s = re.sub(
        r'android:configChanges="[^"]*"',
        'android:configChanges="orientation|screenSize|smallestScreenSize|screenLayout|keyboardHidden|uiMode"',
        s,
        count=1,
    )
# Scout must be allowed to rotate the display. The activity now survives that rotation.
s = re.sub(r'android:screenOrientation="[^"]*"', 'android:screenOrientation="unspecified"', s, count=1)
manifest.write_text(s)

js = asset.read_text()
js = js.replace(
    'EchoHalo v1.2.0 • Unified Spatial Captions • Accessibility prototype • Not a medical device.',
    'EchoHalo v1.2.1 • Unified Spatial Captions • Accessibility prototype • Not a medical device.',
    1,
)

addon = r'''

// EchoHalo v1.2.1 — rotation-safe Orientation Scout + compact landscape UI.
(() => {
  if (window.__echoHaloRotationLayoutV121) return;
  window.__echoHaloRotationLayoutV121 = true;
  if (!window.EchoHaloNative) return;

  const $ = s => document.querySelector(s);

  // The Android shell is already an app. Never show the browser/PWA entry screen here,
  // including after an orientation/configuration change.
  const dismissNativeLaunch = () => {
    const launch = $('#launchScreen');
    if (launch) {
      launch.classList.add('hidden');
      launch.style.display = 'none';
      launch.setAttribute('aria-hidden', 'true');
    }
    const fs = $('#fullscreenBtn');
    if (fs) fs.style.display = 'none';
    const install = $('#installBtn');
    if (install) install.style.display = 'none';
  };
  dismissNativeLaunch();
  window.addEventListener('orientationchange', () => {
    dismissNativeLaunch();
    setTimeout(dismissNativeLaunch, 50);
    setTimeout(dismissNativeLaunch, 300);
  });
  window.addEventListener('resize', dismissNativeLaunch);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') dismissNativeLaunch();
  });

  // Remember the active tab as a belt-and-suspenders fallback. configChanges should keep
  // the WebView alive, but a process/WebView reload during Scout should at least return
  // the user to Settings instead of dumping them on Listen/title.
  document.querySelectorAll('.tab[data-screen]').forEach(tab => {
    tab.addEventListener('click', () => {
      try { localStorage.setItem('echohalo-native-active-screen', tab.dataset.screen || 'listen'); } catch (_) {}
    });
  });
  try {
    const wanted = localStorage.getItem('echohalo-native-active-screen');
    const tab = wanted && document.querySelector('.tab[data-screen="' + wanted + '"]');
    if (tab && !tab.classList.contains('active')) setTimeout(() => tab.click(), 0);
  } catch (_) {}

  // Make it explicit that rotation during Scout is expected and no progress is lost.
  const scoutHelp = $('#scoutInstruction');
  const scoutStart = $('#scoutStart');
  if (scoutStart) {
    scoutStart.addEventListener('click', () => {
      try { localStorage.setItem('echohalo-native-active-screen', 'settings'); } catch (_) {}
    }, true);
  }

  const style = document.createElement('style');
  style.id = 'eh-v121-landscape-style';
  style.textContent = `
    /* Native app does not need the browser launch/fullscreen/install furniture. */
    body .launch-screen{display:none!important}
    body #fullscreenBtn,body #installBtn{display:none!important}

    /* Scout/status copy should stay readable when the device rotates. */
    #scoutInstruction{min-height:54px}

    @media (orientation:landscape) and (max-height:620px){
      html,body{min-height:100%;height:auto}
      body{padding-top:max(2px,env(safe-area-inset-top));padding-bottom:max(2px,env(safe-area-inset-bottom))}
      .app{max-width:none!important;padding:3px 8px 14px!important}
      .topbar{min-height:36px!important;margin:0 0 2px!important;padding:2px 4px!important}
      .brand-icon{width:30px!important;height:30px!important;border-radius:9px!important}
      .brand h1{font-size:1rem!important}.brand p{display:none!important}
      .status-pill{min-height:28px!important;padding:3px 8px!important}
      .tabs{position:sticky!important;top:0!important;z-index:25!important;padding:3px 0 6px!important;margin-bottom:5px!important;gap:5px!important}
      .tab{min-height:34px!important;padding:5px 7px!important;font-size:.75rem!important;border-radius:9px!important}

      #screen-listen>.grid.two{grid-template-columns:minmax(0,1.72fr) minmax(220px,.78fr)!important;gap:8px!important;align-items:start!important}
      #screen-listen>.grid.two>.card{padding:9px!important;border-radius:13px!important}
      #screen-listen>.grid.two>.card:first-child>.row.between{align-items:center!important;gap:8px!important}
      #screen-listen>.grid.two>.card:first-child>.row.between .sub{display:none!important}
      #screen-listen h2{font-size:.96rem!important;margin:0!important}
      #captionToggle{min-height:34px!important;padding:5px 10px!important;font-size:.8rem!important}
      #captionStatus{margin-top:6px!important;min-height:34px!important;padding:5px 8px!important;gap:6px!important}
      #captionStateDetail{font-size:.72rem!important;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      #captionReset{min-height:28px!important;padding:3px 8px!important}

      .hero-caption.eh-spatial-caption{min-height:190px!important;height:min(52vh,240px)!important;margin-top:6px!important;padding:28px 22px 22px!important;border-radius:24px!important}
      .hero-caption.eh-spatial-caption .caption-text{font-size:calc(1.36rem * var(--caption-scale))!important;line-height:1.16!important}
      .hero-caption.eh-spatial-caption .caption-interim{font-size:calc(1.0rem * var(--caption-scale))!important;line-height:1.15!important;margin-top:6px!important}
      .eh-cap-axis{font-size:.52rem!important}.eh-cap-pill{top:6px!important;right:7px!important;font-size:.56rem!important;padding:3px 6px!important}
      #spatialNotice{display:none!important}

      #screen-listen>.grid.two>.card:nth-child(2){max-height:calc(100vh - 88px)!important;overflow:auto!important}
      #screen-listen>.grid.two>.card:nth-child(2) .row.between .sub{display:none!important}
      #captionHistory{margin-top:6px!important}
      .history-item{padding:7px 8px!important;margin-bottom:5px!important;font-size:.78rem!important}

      /* Settings remains usable during Scout instead of becoming a tall narrow phone page. */
      #screen-settings .grid.two{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}
      #screen-settings .card{padding:10px!important;border-radius:13px!important}
      #screen-settings .card h2{font-size:.95rem!important}
      #screen-settings .sub{font-size:.75rem!important;line-height:1.28!important}
      .spatial-setup-grid{gap:5px!important}.spatial-setup-grid .btn{min-height:38px!important;padding:5px 7px!important;font-size:.74rem!important}
      .spatial-wizard{padding:8px!important}.spatial-score{font-size:.65rem!important;max-height:100px;overflow:auto}
    }

    @media (orientation:landscape) and (max-height:430px){
      .topbar{display:none!important}
      .tabs{padding-top:2px!important}
      #screen-listen>.grid.two{grid-template-columns:minmax(0,1.9fr) minmax(190px,.7fr)!important}
      .hero-caption.eh-spatial-caption{height:min(55vh,200px)!important;min-height:160px!important}
      #screen-listen>.grid.two>.card:nth-child(2){max-height:calc(100vh - 48px)!important}
    }
  `;
  document.head.appendChild(style);
})();
'''
js += addon
asset.write_text(js)

assert "versionName '1.2.1'" in build.read_text()
assert 'android:configChanges=' in manifest.read_text()
assert 'android:screenOrientation="unspecified"' in manifest.read_text()
assert '__echoHaloRotationLayoutV121' in asset.read_text()
print('EchoHalo v1.2.1 rotation/layout patch complete')
