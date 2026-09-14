package org.neocities.bk26.echohalospatial;

import android.content.Context;
import android.content.Intent;
import android.media.AudioFormat;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.ParcelFileDescriptor;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;

import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * Native caption engine that consumes the SAME PCM stream as SpatialAudioEngine.
 * On API 33+ Android can pass an already-opened audio source to SpeechRecognizer,
 * so the recognizer does not need to open the handset microphone a second time.
 */
public final class NativeCaptionEngine implements SpatialAudioEngine.PcmTap {
    public interface Listener {
        void onCaptionStatus(String state, String detail, boolean error);
        void onCaptionText(String text, boolean isFinal, long speechStartNanos, long speechEndNanos);
    }

    private static final int SAMPLE_RATE = SpatialAudioEngine.SAMPLE_RATE;
    private static final int QUEUE_CAPACITY = 18;

    private final Context context;
    private final Listener listener;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ArrayBlockingQueue<byte[]> audioQueue = new ArrayBlockingQueue<>(QUEUE_CAPACITY);

    private SpeechRecognizer recognizer;
    private ParcelFileDescriptor pipeRead;
    private ParcelFileDescriptor pipeWrite;
    private OutputStream pipeOut;
    private Thread writerThread;
    private volatile boolean wanted = false;
    private volatile boolean feeding = false;
    private volatile long speechStartNanos = -1L;
    private String languageTag = "en-US";

    public NativeCaptionEngine(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
    }

    public static boolean isSupported(Context context) {
        return Build.VERSION.SDK_INT >= 33 && SpeechRecognizer.isRecognitionAvailable(context);
    }

    public boolean isRunning() { return wanted; }

    public void start(String language) {
        main.post(() -> startOnMain(language));
    }

    public void stop() {
        main.post(() -> stopOnMain("Captions stopped."));
    }

    private void startOnMain(String language) {
        if (wanted) return;
        if (!isSupported(context)) {
            listener.onCaptionStatus("unavailable", "Native shared-audio captions require Android 13+ and a speech recognition service.", true);
            return;
        }
        languageTag = (language == null || language.trim().isEmpty()) ? "en-US" : language.trim();
        wanted = true;
        speechStartNanos = -1L;
        listener.onCaptionStatus("starting", "Starting native captions from the Spatial Compass audio stream…", false);
        openRecognizerSession();
    }

    private void openRecognizerSession() {
        if (!wanted) return;
        closeSession(false);
        try {
            ParcelFileDescriptor[] pipe = ParcelFileDescriptor.createPipe();
            pipeRead = pipe[0];
            pipeWrite = pipe[1];
            pipeOut = new ParcelFileDescriptor.AutoCloseOutputStream(pipeWrite);
            audioQueue.clear();
            feeding = true;
            writerThread = new Thread(this::writerLoop, "EchoHaloCaptionPipe");
            writerThread.start();

            recognizer = SpeechRecognizer.createSpeechRecognizer(context);
            recognizer.setRecognitionListener(new RecognitionListener() {
                @Override public void onReadyForSpeech(Bundle params) {
                    listener.onCaptionStatus("listening", "Spatial Compass + captions are sharing one microphone stream.", false);
                }
                @Override public void onBeginningOfSpeech() {
                    speechStartNanos = System.nanoTime();
                    listener.onCaptionStatus("hearing", "Hearing speech…", false);
                }
                @Override public void onRmsChanged(float rmsdB) { }
                @Override public void onBufferReceived(byte[] buffer) { }
                @Override public void onEndOfSpeech() { }
                @Override public void onError(int error) {
                    if (!wanted) return;
                    listener.onCaptionStatus("error", errorText(error), true);
                    main.postDelayed(() -> { if (wanted) openRecognizerSession(); }, 900);
                }
                @Override public void onResults(Bundle results) {
                    emitBundle(results, true);
                    if (wanted) main.postDelayed(() -> openRecognizerSession(), 180);
                }
                @Override public void onPartialResults(Bundle partialResults) {
                    emitBundle(partialResults, false);
                }
                @Override public void onEvent(int eventType, Bundle params) { }
                @Override public void onSegmentResults(Bundle segmentResults) {
                    emitBundle(segmentResults, true);
                }
                @Override public void onEndOfSegmentedSession() {
                    if (wanted) main.postDelayed(() -> openRecognizerSession(), 180);
                }
                @Override public void onLanguageDetection(Bundle results) { }
            });

            Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, languageTag);
            intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE, pipeRead);
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_CHANNEL_COUNT, 1);
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_ENCODING, AudioFormat.ENCODING_PCM_16BIT);
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_SAMPLING_RATE, SAMPLE_RATE);
            intent.putExtra(RecognizerIntent.EXTRA_SEGMENTED_SESSION, RecognizerIntent.EXTRA_AUDIO_SOURCE);
            recognizer.startListening(intent);
        } catch (Throwable t) {
            listener.onCaptionStatus("error", "Native caption audio injection failed: " + t.getClass().getSimpleName() + ": " + safe(t.getMessage()), true);
            closeSession(false);
            if (wanted) main.postDelayed(() -> openRecognizerSession(), 1200);
        }
    }

    private void emitBundle(Bundle b, boolean isFinal) {
        if (b == null) return;
        ArrayList<String> results = b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (results == null || results.isEmpty()) return;
        String text = results.get(0) == null ? "" : results.get(0).trim();
        if (text.isEmpty()) return;
        long end = System.nanoTime();
        long start = speechStartNanos > 0 ? speechStartNanos : Math.max(0L, end - 2_000_000_000L);
        listener.onCaptionText(text, isFinal, start, end);
        if (isFinal) speechStartNanos = -1L;
    }

    @Override
    public void onStereoPcm(short[] interleaved, int frameCount) {
        if (!feeding || !wanted || interleaved == null || frameCount <= 0) return;
        int frames = Math.min(frameCount, interleaved.length / 2);
        byte[] mono = new byte[frames * 2];
        for (int i = 0; i < frames; i++) {
            int l = interleaved[i * 2];
            int r = interleaved[i * 2 + 1];
            short m = (short)((l + r) / 2);
            mono[i * 2] = (byte)(m & 0xff);
            mono[i * 2 + 1] = (byte)((m >>> 8) & 0xff);
        }
        if (!audioQueue.offer(mono)) {
            audioQueue.poll();
            audioQueue.offer(mono);
        }
    }

    private void writerLoop() {
        try {
            while (feeding) {
                byte[] data = audioQueue.poll(250, TimeUnit.MILLISECONDS);
                if (data == null) continue;
                OutputStream out = pipeOut;
                if (out == null) break;
                out.write(data);
            }
        } catch (Throwable ignored) {
        }
    }

    private void stopOnMain(String detail) {
        wanted = false;
        speechStartNanos = -1L;
        closeSession(true);
        listener.onCaptionStatus("stopped", detail, false);
    }

    private void closeSession(boolean destroyRecognizer) {
        feeding = false;
        Thread wt = writerThread;
        writerThread = null;
        if (wt != null) wt.interrupt();
        audioQueue.clear();
        try { if (pipeOut != null) pipeOut.close(); } catch (Exception ignored) {}
        pipeOut = null;
        try { if (pipeRead != null) pipeRead.close(); } catch (Exception ignored) {}
        pipeRead = null;
        pipeWrite = null;
        SpeechRecognizer sr = recognizer;
        recognizer = null;
        if (sr != null) {
            try { sr.cancel(); } catch (Throwable ignored) {}
            try { sr.destroy(); } catch (Throwable ignored) {}
        }
    }

    private static String errorText(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO: return "Speech recognizer reported an audio error. Retrying…";
            case SpeechRecognizer.ERROR_CLIENT: return "Speech recognizer client reset. Retrying…";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: return "Speech recognition permission was denied.";
            case SpeechRecognizer.ERROR_NETWORK: return "Speech recognition network error. Retrying…";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: return "Speech recognition network timeout. Retrying…";
            case SpeechRecognizer.ERROR_NO_MATCH: return "Listening — no recognizable speech in that segment.";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY: return "Speech recognizer was busy. Retrying…";
            case SpeechRecognizer.ERROR_SERVER: return "Speech recognition service error. Retrying…";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: return "Listening — no speech yet.";
            default: return String.format(Locale.US, "Speech recognition error %d. Retrying…", error);
        }
    }

    private static String safe(String s) { return s == null ? "" : s; }
}
