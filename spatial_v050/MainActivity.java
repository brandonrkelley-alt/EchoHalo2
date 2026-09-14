package org.neocities.bk26.echohalospatial;

import android.Manifest;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.EnumMap;
import java.util.Locale;
import java.util.Map;

public class MainActivity extends Activity implements SpatialAudioEngine.Listener, SensorEventListener {
    private static final String VERSION = "0.5.0";
    private static final int REQ_MIC = 81;

    private SpatialAudioEngine engine;
    private CompassView compassView;
    private TextView statusView;
    private TextView poseView;
    private TextView directionView;
    private TextView confidenceView;
    private TextView calibrationSummary;
    private TextView featureView;
    private TextView blindSummary;
    private TextView lastTrialView;
    private LinearLayout calibrationPanel;
    private LinearLayout diagnosticsPanel;
    private Button startButton;
    private Button diagnosticsButton;
    private final Map<SpatialAudioEngine.Direction, Button> calButtons = new EnumMap<>(SpatialAudioEngine.Direction.class);
    private final Map<SpatialAudioEngine.Direction, Button> truthButtons = new EnumMap<>(SpatialAudioEngine.Direction.class);

    private SensorManager sensorManager;
    private Sensor accelerometer;
    private float uprightDeviationDeg = 90f;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        engine = new SpatialAudioEngine(this, this);
        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        accelerometer = sensorManager == null ? null : sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);

        buildUi();
        refreshCalibrationSummary();
        refreshBlindSummary();
        updateCalibrationVisibility();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (sensorManager != null && accelerometer != null) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_UI);
        }
    }

    @Override
    protected void onPause() {
        if (sensorManager != null) sensorManager.unregisterListener(this);
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (engine != null) engine.stop();
        super.onDestroy();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.BLACK);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(14), dp(16), dp(28));
        root.setBackgroundColor(Color.BLACK);
        scroll.addView(root);

        root.addView(text("EchoHalo", 30, Color.WHITE, true));
        TextView sub = text("Spatial Compass prototype · v" + VERSION, 14, 0xFF8C969D, false);
        sub.setPadding(0, dp(2), 0, dp(10));
        root.addView(sub);

        poseView = text("POSE · hold phone portrait and nearly vertical", 12, 0xFFFFD17A, true);
        poseView.setPadding(0, 0, 0, dp(10));
        root.addView(poseView);

        compassView = new CompassView(this);
        compassView.setBackground(makeCardBackground(0xFF050505, 0xFF1C2226, 28));
        root.addView(compassView, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(360)));

        directionView = text("WAITING", 24, Color.WHITE, true);
        directionView.setGravity(Gravity.CENTER);
        directionView.setPadding(0, dp(12), 0, 0);
        root.addView(directionView);

        confidenceView = text("direction — · confidence —", 13, 0xFF96A0A7, false);
        confidenceView.setGravity(Gravity.CENTER);
        confidenceView.setPadding(0, dp(2), 0, dp(8));
        root.addView(confidenceView);

        statusView = text(engine.hasAllProfiles()
                ? "Saved upright calibration found. Start the mic and EchoHalo will listen continuously."
                : "First setup: start the mic, keep the phone in your normal upright hold, then teach the four directions with finger snaps.",
                14, 0xFFB8C1C7, false);
        statusView.setPadding(dp(4), dp(8), dp(4), dp(8));
        root.addView(statusView);

        startButton = button("START ECHOHALO MIC");
        startButton.setOnClickListener(v -> toggleMic());
        root.addView(startButton, fullButtonLp(56, 4));

        calibrationPanel = new LinearLayout(this);
        calibrationPanel.setOrientation(LinearLayout.VERTICAL);
        calibrationPanel.setPadding(dp(12), dp(12), dp(12), dp(12));
        calibrationPanel.setBackground(makeCardBackground(0xFF080A0B, 0xFF2A3338, 18));
        root.addView(calibrationPanel, fullWrapLp(12));

        TextView calTitle = text("SPATIAL SETUP", 16, 0xFFA9E8FF, true);
        calibrationPanel.addView(calTitle);
        TextView calHelp = text(
                "Hold the phone the way David will normally use it: portrait, screen facing you, nearly vertical. Keep the phone still. Tap a direction, then make 3 clear finger snaps from that direction. FRONT means in front of you; BEHIND means behind you. EchoHalo listens only for the snap bursts and learns the delivered stereo fingerprint.",
                13, 0xFFC2CBD1, false);
        calHelp.setPadding(0, dp(6), 0, dp(10));
        calibrationPanel.addView(calHelp);

        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        row1.addView(calButton(SpatialAudioEngine.Direction.LEFT, "←  TEACH LEFT"), weighted());
        row1.addView(space(dp(8)));
        row1.addView(calButton(SpatialAudioEngine.Direction.FRONT, "↑  TEACH FRONT"), weighted());
        calibrationPanel.addView(row1, fullWrapLp(2));

        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        row2.addView(calButton(SpatialAudioEngine.Direction.RIGHT, "TEACH RIGHT  →"), weighted());
        row2.addView(space(dp(8)));
        row2.addView(calButton(SpatialAudioEngine.Direction.BEHIND, "TEACH BEHIND  ↓"), weighted());
        calibrationPanel.addView(row2, fullWrapLp(8));

        calibrationSummary = text("", 11, 0xFFB8C0C8, false);
        calibrationSummary.setTypeface(Typeface.MONOSPACE);
        calibrationSummary.setPadding(0, dp(10), 0, 0);
        calibrationPanel.addView(calibrationSummary);

        Button recalibrate = button("RECALIBRATE UPRIGHT COMPASS");
        recalibrate.setOnClickListener(v -> {
            engine.clearCalibration();
            engine.setLiveEnabled(false);
            compassView.clearDirection();
            directionView.setText("SETUP NEEDED");
            confidenceView.setText("teach LEFT · FRONT · RIGHT · BEHIND");
            refreshCalibrationSummary();
            updateCalibrationVisibility();
            statusView.setText("Upright calibration cleared. Teach the four directions again.");
        });
        root.addView(recalibrate, fullButtonLp(50, 10));

        diagnosticsButton = button("SPATIAL DIAGNOSTICS ▾");
        diagnosticsButton.setOnClickListener(v -> toggleDiagnostics());
        root.addView(diagnosticsButton, fullButtonLp(50, 8));

        diagnosticsPanel = new LinearLayout(this);
        diagnosticsPanel.setOrientation(LinearLayout.VERTICAL);
        diagnosticsPanel.setVisibility(View.GONE);
        diagnosticsPanel.setPadding(dp(10), dp(10), dp(10), dp(10));
        diagnosticsPanel.setBackground(makeCardBackground(0xFF080808, 0xFF262626, 16));
        root.addView(diagnosticsPanel, fullWrapLp(8));

        featureView = text("Live features: —", 11, 0xFFBFC7CF, false);
        featureView.setTypeface(Typeface.MONOSPACE);
        diagnosticsPanel.addView(featureView);

        TextView scoreHelp = text("OPTIONAL GROUND TRUTH\nIf the dot is wrong during normal use, tap where the sound really was. This records evidence; it does not automatically train on its own guesses.", 12, 0xFF9EB5C0, false);
        scoreHelp.setPadding(0, dp(12), 0, dp(8));
        diagnosticsPanel.addView(scoreHelp);

        LinearLayout truth1 = new LinearLayout(this);
        truth1.setOrientation(LinearLayout.HORIZONTAL);
        truth1.addView(truthButton(SpatialAudioEngine.Direction.LEFT, "ACTUAL LEFT"), weighted());
        truth1.addView(space(dp(8)));
        truth1.addView(truthButton(SpatialAudioEngine.Direction.FRONT, "ACTUAL FRONT"), weighted());
        diagnosticsPanel.addView(truth1);

        LinearLayout truth2 = new LinearLayout(this);
        truth2.setOrientation(LinearLayout.HORIZONTAL);
        truth2.addView(truthButton(SpatialAudioEngine.Direction.RIGHT, "ACTUAL RIGHT"), weighted());
        truth2.addView(space(dp(8)));
        truth2.addView(truthButton(SpatialAudioEngine.Direction.BEHIND, "ACTUAL BEHIND"), weighted());
        diagnosticsPanel.addView(truth2, fullWrapLp(8));

        lastTrialView = text("No ground-truth marks yet.", 12, 0xFFBFC7CF, true);
        lastTrialView.setPadding(0, dp(10), 0, 0);
        diagnosticsPanel.addView(lastTrialView);

        blindSummary = text("", 11, 0xFFCDD4DB, false);
        blindSummary.setTypeface(Typeface.MONOSPACE);
        blindSummary.setPadding(0, dp(8), 0, 0);
        diagnosticsPanel.addView(blindSummary);

        Button copy = button("COPY SPATIAL REPORT");
        copy.setOnClickListener(v -> copyReport());
        diagnosticsPanel.addView(copy, fullButtonLp(48, 10));

        Button clearTrials = button("CLEAR GROUND-TRUTH MARKS");
        clearTrials.setOnClickListener(v -> {
            engine.clearBlindTrials();
            lastTrialView.setText("No ground-truth marks yet.");
            refreshBlindSummary();
        });
        diagnosticsPanel.addView(clearTrials, fullButtonLp(48, 8));

        Button pwa = button("OPEN ECHOHALO PWA");
        pwa.setOnClickListener(v -> startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://bk26.neocities.org/EchoHalo/"))));
        root.addView(pwa, fullButtonLp(52, 12));

        TextView foot = text("Prototype accessibility R&D. Spatial estimates come from the phone microphone stream and are not cochlear-implant programming or medical advice.", 11, 0xFF596168, false);
        foot.setGravity(Gravity.CENTER);
        foot.setPadding(dp(8), dp(18), dp(8), 0);
        root.addView(foot);

        setContentView(scroll);
        updateTruthControls();
    }

    private Button calButton(SpatialAudioEngine.Direction d, String label) {
        Button b = button(label);
        b.setOnClickListener(v -> {
            if (!engine.isRunning()) {
                Toast.makeText(this, "Start the EchoHalo mic first.", Toast.LENGTH_SHORT).show();
                return;
            }
            if (uprightDeviationDeg > 28f) {
                Toast.makeText(this, "Hold the phone more upright before teaching this direction.", Toast.LENGTH_LONG).show();
                return;
            }
            engine.beginCalibration(d);
        });
        calButtons.put(d, b);
        return b;
    }

    private Button truthButton(SpatialAudioEngine.Direction d, String label) {
        Button b = button(label);
        b.setTextSize(11);
        b.setOnClickListener(v -> recordTruth(d));
        truthButtons.put(d, b);
        return b;
    }

    private void toggleMic() {
        if (engine.isRunning()) {
            engine.stop();
            startButton.setText("START ECHOHALO MIC");
            statusView.setText("EchoHalo microphone stopped.");
            engine.setLiveEnabled(false);
            compassView.clearDirection();
            directionView.setText("STOPPED");
            confidenceView.setText("direction — · confidence —");
            updateTruthControls();
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_MIC);
        } else {
            startEngine();
        }
    }

    private void startEngine() {
        engine.start();
        startButton.setText("STOP ECHOHALO MIC");
        statusView.setText("Starting stereo spatial stream…");
        if (engine.hasAllProfiles()) {
            engine.setLiveEnabled(true);
            directionView.setText("LISTENING");
        }
        updateTruthControls();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_MIC && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startEngine();
        } else if (requestCode == REQ_MIC) {
            statusView.setText("Microphone permission is required for EchoHalo spatial direction.");
        }
    }

    @Override
    public void onEngineStatus(String text, boolean error) {
        statusView.setText(text);
        statusView.setTextColor(error ? 0xFFFF7C7C : 0xFFB8C1C7);
        startButton.setText(engine.isRunning() ? "STOP ECHOHALO MIC" : "START ECHOHALO MIC");
        if (!error && engine.isRunning() && engine.hasAllProfiles() && !engine.isLiveEnabled()) {
            engine.setLiveEnabled(true);
        }
        updateTruthControls();
    }

    @Override
    public void onFeature(SpatialAudioEngine.Feature f) {
        compassView.setSoundLevel(f.rmsDb);
        if (featureView != null) featureView.setText("Live features\n" + f.reportLine());
    }

    @Override
    public void onCalibrationProgress(SpatialAudioEngine.Direction d, long millisRemaining, int capturedSnaps) {
        statusView.setText(String.format(Locale.US,
                "TEACHING %s · %d/3 snaps captured · %.1f s left",
                d.label, Math.min(3, capturedSnaps), millisRemaining / 1000.0));
        for (Button b : calButtons.values()) b.setEnabled(false);
        directionView.setText("SNAP " + d.label);
        confidenceView.setText("make 3 clear finger snaps");
    }

    @Override
    public void onCalibrationComplete(SpatialAudioEngine.Direction d, SpatialAudioEngine.CalibrationProfile p) {
        for (Button b : calButtons.values()) b.setEnabled(true);
        statusView.setText("Learned " + d.label + ". " + (engine.hasAllProfiles() ? "Spatial Compass is ready." : "Teach the next direction."));
        refreshCalibrationSummary();
        updateCalibrationVisibility();
        if (engine.hasAllProfiles()) {
            engine.setLiveEnabled(true);
            directionView.setText("LISTENING");
            confidenceView.setText("upright spatial model active");
        }
        updateTruthControls();
    }

    @Override
    public void onClassification(SpatialAudioEngine.ClassificationResult r) {
        if (!engine.isLiveEnabled()) return;
        compassView.setClassification(r);
        if (!r.accepted || r.best == null) {
            directionView.setText("LISTENING");
            confidenceView.setText(r.detail == null ? "waiting for a clear sound" : r.detail);
            return;
        }
        directionView.setText(r.best.label);
        confidenceView.setText(String.format(Locale.US,
                "%.0f%% · runner-up %s %.0f%%",
                r.bestPosterior * 100.0,
                r.runnerUp == null ? "—" : r.runnerUp.label,
                r.runnerUpPosterior * 100.0));
    }

    private void recordTruth(SpatialAudioEngine.Direction actual) {
        SpatialAudioEngine.BlindTrial t = engine.recordGroundTruth(actual);
        if (t == null) {
            lastTrialView.setText("NOT RECORDED · wait for a fresh visible dot, then tap again.");
            lastTrialView.setTextColor(0xFFFFD17A);
            return;
        }
        lastTrialView.setText(String.format(Locale.US,
                "%s · actual %s · predicted %s · %.0f%%",
                t.isCorrect() ? "✓ CORRECT" : "✕ MISS",
                t.actual.label, t.predicted.label, t.bestPosterior * 100.0));
        lastTrialView.setTextColor(t.isCorrect() ? 0xFF9BE7B0 : 0xFFFF9B9B);
        refreshBlindSummary();
    }

    private void updateCalibrationVisibility() {
        if (calibrationPanel != null) calibrationPanel.setVisibility(engine.hasAllProfiles() ? View.GONE : View.VISIBLE);
    }

    private void updateTruthControls() {
        boolean enabled = engine.isRunning() && engine.isLiveEnabled() && engine.hasAllProfiles();
        for (Button b : truthButtons.values()) b.setEnabled(enabled);
    }

    private void toggleDiagnostics() {
        boolean opening = diagnosticsPanel.getVisibility() != View.VISIBLE;
        diagnosticsPanel.setVisibility(opening ? View.VISIBLE : View.GONE);
        diagnosticsButton.setText(opening ? "SPATIAL DIAGNOSTICS ▴" : "SPATIAL DIAGNOSTICS ▾");
    }

    private void refreshCalibrationSummary() {
        if (calibrationSummary == null) return;
        StringBuilder b = new StringBuilder();
        b.append("UPRIGHT CALIBRATION  ").append(engine.profileCount()).append("/4\n");
        for (SpatialAudioEngine.Direction d : SpatialAudioEngine.Direction.values()) {
            SpatialAudioEngine.CalibrationProfile p = engine.getProfile(d);
            b.append(String.format(Locale.US, "%-7s  ", d.label));
            if (p == null) b.append("—\n");
            else b.append(String.format(Locale.US, "lag=%+.1f  low=%+.1f  mid=%+.1f  high=%+.1f  n=%d\n",
                    p.center[0], p.center[1], p.center[2], p.center[3], p.frames));
        }
        calibrationSummary.setText(b.toString());
    }

    private void refreshBlindSummary() {
        if (blindSummary == null) return;
        int total = engine.getBlindTrialCount();
        int correct = engine.getBlindCorrectCount();
        int[][] m = engine.getConfusionMatrixCopy();
        StringBuilder b = new StringBuilder();
        b.append("GROUND TRUTH  ").append(correct).append('/').append(total);
        if (total > 0) b.append(String.format(Locale.US, "  %.1f%%", correct * 100.0 / total));
        b.append("\n          L    F    R    B\n");
        for (SpatialAudioEngine.Direction a : SpatialAudioEngine.Direction.values()) {
            b.append(String.format(Locale.US, "%-7s", a.label));
            for (SpatialAudioEngine.Direction p : SpatialAudioEngine.Direction.values()) {
                b.append(String.format(Locale.US, "%5d", m[a.ordinal()][p.ordinal()]));
            }
            b.append('\n');
        }
        blindSummary.setText(b.toString());
    }

    private void copyReport() {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("EchoHalo Spatial Report", engine.buildReport()));
        Toast.makeText(this, "Spatial report copied.", Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() != Sensor.TYPE_ACCELEROMETER) return;
        float x = event.values[0];
        float y = event.values[1];
        float z = event.values[2];
        double g = Math.sqrt(x * x + y * y + z * z);
        if (g < 0.1) return;
        double q = Math.min(1.0, Math.abs(z) / g);
        uprightDeviationDeg = (float) Math.toDegrees(Math.asin(q));
        if (uprightDeviationDeg <= 18f) {
            poseView.setText(String.format(Locale.US, "POSE OK · %.0f° from vertical", uprightDeviationDeg));
            poseView.setTextColor(0xFF8FE7A5);
        } else if (uprightDeviationDeg <= 30f) {
            poseView.setText(String.format(Locale.US, "POSE OK-ish · %.0f° from vertical", uprightDeviationDeg));
            poseView.setTextColor(0xFFFFD17A);
        } else {
            poseView.setText(String.format(Locale.US, "HOLD MORE UPRIGHT · %.0f° from vertical", uprightDeviationDeg));
            poseView.setTextColor(0xFFFF8D8D);
        }
    }

    @Override public void onAccuracyChanged(Sensor sensor, int accuracy) {}

    private TextView text(String s, int sp, int color, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        if (bold) t.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return t;
    }

    private Button button(String s) {
        Button b = new Button(this);
        b.setText(s);
        b.setTextColor(Color.WHITE);
        b.setTextSize(13);
        b.setAllCaps(false);
        b.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        b.setBackground(makeCardBackground(0xFF15191C, 0xFF3C464D, 14));
        b.setPadding(dp(8), 0, dp(8), 0);
        return b;
    }

    private LinearLayout.LayoutParams weighted() {
        return new LinearLayout.LayoutParams(0, dp(52), 1f);
    }

    private View space(int w) {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(w, 1));
        return v;
    }

    private LinearLayout.LayoutParams fullButtonLp(int h, int top) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(h));
        lp.setMargins(0, dp(top), 0, 0);
        return lp;
    }

    private LinearLayout.LayoutParams fullWrapLp(int top) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, dp(top), 0, 0);
        return lp;
    }

    private android.graphics.drawable.GradientDrawable makeCardBackground(int fill, int stroke, int radiusDp) {
        android.graphics.drawable.GradientDrawable g = new android.graphics.drawable.GradientDrawable();
        g.setColor(fill);
        g.setCornerRadius(dp(radiusDp));
        g.setStroke(dp(1), stroke);
        return g;
    }

    private int dp(int x) {
        return (int) (x * getResources().getDisplayMetrics().density + 0.5f);
    }
}
