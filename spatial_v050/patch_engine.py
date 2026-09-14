from pathlib import Path
import sys

root = Path(sys.argv[1])
engine = root / 'app/src/main/java/org/neocities/bk26/echohalospatial/SpatialAudioEngine.java'
manifest = root / 'app/src/main/AndroidManifest.xml'
build = root / 'app/build.gradle'


def replace_once(path, old, new, label):
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 match, found {count}')
    path.write_text(text.replace(old, new, 1))
    print('Applied:', label)

replace_once(build,
             "        versionCode 6\n        versionName '0.4.1'",
             "        versionCode 8\n        versionName '0.5.0'",
             'version')

replace_once(manifest, 'android:label="EchoHalo Spatial Lab"', 'android:label="EchoHalo"', 'app label')
replace_once(manifest, 'android:screenOrientation="unspecified"', 'android:screenOrientation="portrait"', 'portrait orientation')

replace_once(engine, 'private static final long CALIBRATION_MS = 4500;', 'private static final long CALIBRATION_MS = 10000;', 'calibration timeout')
replace_once(engine, 'private static final int MIN_CALIBRATION_FRAMES = 45;', 'private static final int MIN_CALIBRATION_FRAMES = 9;', 'calibration frames')
replace_once(engine, 'private static final double ACTIVE_RMS_DB = -52.0;', 'private static final double ACTIVE_RMS_DB = -56.0;', 'active threshold')

replace_once(engine,
'''    private long calibrationEndNanos;\n    private final List<Feature> calibrationFrames = new ArrayList<>();\n    private volatile Feature latestFeature;\n    private volatile ClassificationResult latestClassification;''',
'''    private long calibrationEndNanos;\n    private final List<Feature> calibrationFrames = new ArrayList<>();\n    private int calibrationSnapCount = 0;\n    private int calibrationCaptureFramesRemaining = 0;\n    private long calibrationLastSnapNanos = Long.MIN_VALUE;\n    private double calibrationNoiseDb = -68.0;\n    private volatile Feature latestFeature;\n    private volatile ClassificationResult latestClassification;\n    private volatile ClassificationResult latestAcceptedClassification;''',
'calibration + accepted state')

replace_once(engine,
'''        liveEnabled = enabled;\n        latestClassification = null;\n        synchronized (smoothedPosteriors) { smoothedPosteriors.clear(); }''',
'''        liveEnabled = enabled;\n        latestClassification = null;\n        latestAcceptedClassification = null;\n        synchronized (smoothedPosteriors) { smoothedPosteriors.clear(); }''',
'live reset')

replace_once(engine,
'''        running = false;\n        liveEnabled = false;\n        latestClassification = null;\n        synchronized (stateLock) {''',
'''        running = false;\n        liveEnabled = false;\n        latestClassification = null;\n        latestAcceptedClassification = null;\n        synchronized (stateLock) {''',
'stop reset')

replace_once(engine,
'''            calibrationTarget = d;\n            calibrationFrames.clear();\n            calibrationEndNanos = System.nanoTime() + CALIBRATION_MS * 1_000_000L;''',
'''            calibrationTarget = d;\n            calibrationFrames.clear();\n            calibrationSnapCount = 0;\n            calibrationCaptureFramesRemaining = 0;\n            calibrationLastSnapNanos = Long.MIN_VALUE;\n            calibrationNoiseDb = -68.0;\n            calibrationEndNanos = System.nanoTime() + CALIBRATION_MS * 1_000_000L;''',
'calibration start')

replace_once(engine,
'''        synchronized (smoothedPosteriors) { smoothedPosteriors.clear(); }\n        latestClassification = null;\n        log("CALIBRATION CLEARED");''',
'''        synchronized (smoothedPosteriors) { smoothedPosteriors.clear(); }\n        latestClassification = null;\n        latestAcceptedClassification = null;\n        log("CALIBRATION CLEARED");''',
'calibration clear')

replace_once(engine,
'''    public BlindTrial recordGroundTruth(Direction actual) {\n        ClassificationResult r = latestClassification;''',
'''    public BlindTrial recordGroundTruth(Direction actual) {\n        ClassificationResult r = latestAcceptedClassification;''',
'truth source')

old = '''        synchronized (stateLock) {\n            target = calibrationTarget;\n            if (target != null) {\n                if (f.rmsDb > ACTIVE_RMS_DB && f.peakCorr > 0.05) calibrationFrames.add(f);\n                remainMs = Math.max(0, (calibrationEndNanos - System.nanoTime()) / 1_000_000L);\n                count = calibrationFrames.size();\n                if (remainMs <= 0) finish = true;\n            } else {\n                remainMs = 0;\n                count = 0;\n            }\n        }'''
new = '''        synchronized (stateLock) {\n            target = calibrationTarget;\n            if (target != null) {\n                long now = System.nanoTime();\n                if (calibrationCaptureFramesRemaining <= 0) {\n                    if (f.rmsDb < calibrationNoiseDb + 5.0) {\n                        calibrationNoiseDb = calibrationNoiseDb * 0.96 + f.rmsDb * 0.04;\n                    }\n                    double triggerDb = Math.max(-50.0, calibrationNoiseDb + 8.0);\n                    if (f.rmsDb >= triggerDb && f.peakCorr > 0.04 &&\n                            (calibrationLastSnapNanos == Long.MIN_VALUE || now - calibrationLastSnapNanos > 320_000_000L)) {\n                        calibrationSnapCount++;\n                        calibrationLastSnapNanos = now;\n                        calibrationCaptureFramesRemaining = 7;\n                        log(String.format(Locale.US, "CAL SNAP %s #%d rms=%.1f noise=%.1f",\n                                target.label, calibrationSnapCount, f.rmsDb, calibrationNoiseDb));\n                    }\n                }\n                if (calibrationCaptureFramesRemaining > 0) {\n                    if (f.rmsDb > Math.max(-62.0, calibrationNoiseDb + 2.0) && f.peakCorr > 0.03) {\n                        calibrationFrames.add(f);\n                    }\n                    calibrationCaptureFramesRemaining--;\n                }\n                remainMs = Math.max(0, (calibrationEndNanos - now) / 1_000_000L);\n                count = calibrationSnapCount;\n                if (calibrationSnapCount >= 3 && calibrationFrames.size() >= MIN_CALIBRATION_FRAMES && calibrationCaptureFramesRemaining <= 0) {\n                    finish = true;\n                } else if (remainMs <= 0) {\n                    finish = true;\n                }\n            } else {\n                remainMs = 0;\n                count = 0;\n            }\n        }'''
replace_once(engine, old, new, 'snap calibration')

replace_once(engine,
'''        if (frames.size() < MIN_CALIBRATION_FRAMES) {\n            postStatus("Calibration " + d.label + " failed: only " + frames.size() +\n                    " usable frames. Turn the external calibration noise up slightly and retry.", true);\n            log("CAL FAIL " + d.label + " frames=" + frames.size());\n            return;\n        }''',
'''        if (frames.size() < MIN_CALIBRATION_FRAMES) {\n            postStatus("Teaching " + d.label + " failed: I did not catch 3 clear snap bursts. Hold the phone upright, stay quiet between snaps, and retry.", true);\n            log("CAL FAIL " + d.label + " frames=" + frames.size());\n            return;\n        }''',
'calibration failure text')

replace_once(engine,
'''        latestClassification = result;\n        main.post(() -> listener.onClassification(result));\n    }\n\n    private double distanceSquared''',
'''        latestClassification = result;\n        latestAcceptedClassification = result;\n        main.post(() -> listener.onClassification(result));\n    }\n\n    private double distanceSquared''',
'accepted result store')

replace_once(engine,
'return context.getSharedPreferences("echohalo_spatial_calibration_v1", Context.MODE_PRIVATE);',
'return context.getSharedPreferences("echohalo_spatial_calibration_upright_v2", Context.MODE_PRIVATE);',
'upright prefs')

replace_once(engine, 'b.append("EchoHalo Spatial Calibration Lab v0.4.1\\n");', 'b.append("EchoHalo Spatial Compass v0.5.0\\n");', 'report version')
replace_once(engine,
'b.append("Blind truth rule: latest accepted classification must be <1.5 s old; one ground-truth tap = one trial\\n");',
'b.append("Ground-truth rule: most recent accepted classification must be <1.5 s old; rejected audio frames do not erase it; one mark = one trial\\n");',
'report truth rule')
replace_once(engine,
'b.append("Orientation: phone flat, screen up; top edge=FRONT, right edge=RIGHT, bottom edge=BEHIND, left edge=LEFT\\n\\n");',
'b.append("Orientation: normal-use portrait hold, screen facing user, nearly vertical; UI top=FRONT, right=RIGHT, bottom=BEHIND, left=LEFT\\n\\n");',
'report orientation')

print('EchoHalo v0.5.0 patch complete')
