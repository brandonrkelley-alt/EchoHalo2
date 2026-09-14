package org.neocities.bk26.echohalospatial;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;

public class CompassView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF border = new RectF();

    private float currentX = 0f;
    private float currentY = -1f;
    private float targetX = 0f;
    private float targetY = -1f;
    private float currentRadius = 8f;
    private float targetRadius = 8f;
    private float currentAlpha = 0.25f;
    private float targetAlpha = 0.25f;
    private boolean hasDirection = false;

    public CompassView(Context context) {
        super(context);
        setLayerType(View.LAYER_TYPE_SOFTWARE, null);
    }

    public void setClassification(SpatialAudioEngine.ClassificationResult r) {
        if (r == null || !r.accepted || r.posterior == null || r.posterior.length < 4) {
            hasDirection = false;
            targetAlpha = 0.18f;
            postInvalidateOnAnimation();
            return;
        }
        double pL = r.posterior[SpatialAudioEngine.Direction.LEFT.ordinal()];
        double pF = r.posterior[SpatialAudioEngine.Direction.FRONT.ordinal()];
        double pR = r.posterior[SpatialAudioEngine.Direction.RIGHT.ordinal()];
        double pB = r.posterior[SpatialAudioEngine.Direction.BEHIND.ordinal()];

        double vx = pR - pL;
        double vy = pB - pF;
        double mag = Math.sqrt(vx * vx + vy * vy);
        if (mag > 0.035) {
            targetX = (float) (vx / mag);
            targetY = (float) (vy / mag);
            hasDirection = true;
        }
        targetAlpha = (float) (0.22 + 0.78 * Math.max(0.0, Math.min(1.0, r.confidence)));
        postInvalidateOnAnimation();
    }

    public void setSoundLevel(double rmsDb) {
        double n = (rmsDb + 65.0) / 45.0;
        n = Math.max(0.0, Math.min(1.0, n));
        n = Math.sqrt(n);
        targetRadius = dp((float) (7.0 + 23.0 * n));
        if (rmsDb < -60.0) targetAlpha = Math.min(targetAlpha, 0.18f);
        postInvalidateOnAnimation();
    }

    public void clearDirection() {
        hasDirection = false;
        targetAlpha = 0.18f;
        postInvalidateOnAnimation();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float w = getWidth();
        float h = getHeight();
        if (w <= 0 || h <= 0) return;

        float inset = dp(26);
        border.set(inset, inset, w - inset, h - inset);

        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(dp(2));
        paint.setColor(0xFF2D3439);
        canvas.drawRoundRect(border, dp(32), dp(32), paint);

        paint.setStyle(Paint.Style.FILL);
        paint.setTextAlign(Paint.Align.CENTER);
        paint.setTextSize(dp(11));
        paint.setColor(0xFF69747C);
        canvas.drawText("FRONT", w / 2f, inset + dp(18), paint);
        canvas.drawText("BEHIND", w / 2f, h - inset - dp(10), paint);
        paint.setTextAlign(Paint.Align.LEFT);
        canvas.drawText("L", inset + dp(10), h / 2f + dp(4), paint);
        paint.setTextAlign(Paint.Align.RIGHT);
        canvas.drawText("R", w - inset - dp(10), h / 2f + dp(4), paint);

        float smoothing = 0.16f;
        currentX += (targetX - currentX) * smoothing;
        currentY += (targetY - currentY) * smoothing;
        float m = (float) Math.sqrt(currentX * currentX + currentY * currentY);
        if (m < 0.001f) {
            currentX = 0f;
            currentY = -1f;
        } else {
            currentX /= m;
            currentY /= m;
        }
        currentRadius += (targetRadius - currentRadius) * 0.18f;
        currentAlpha += (targetAlpha - currentAlpha) * 0.16f;

        float cx = w / 2f;
        float cy = h / 2f;
        float halfW = border.width() / 2f;
        float halfH = border.height() / 2f;
        float ax = Math.abs(currentX);
        float ay = Math.abs(currentY);
        float tx = ax < 0.0001f ? Float.POSITIVE_INFINITY : halfW / ax;
        float ty = ay < 0.0001f ? Float.POSITIVE_INFINITY : halfH / ay;
        float t = Math.min(tx, ty);
        float x = cx + currentX * t;
        float y = cy + currentY * t;

        int alpha = (int) (255 * Math.max(0f, Math.min(1f, currentAlpha)));
        paint.setStyle(Paint.Style.FILL);
        paint.setColor((alpha << 24) | 0x0042D7FF);
        paint.setShadowLayer(currentRadius * 1.4f, 0, 0, (Math.min(180, alpha) << 24) | 0x0042D7FF);
        canvas.drawCircle(x, y, currentRadius, paint);
        paint.clearShadowLayer();

        if (!hasDirection) {
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(0xFF56616A);
            canvas.drawCircle(cx, cy, dp(3), paint);
        }

        if (Math.abs(targetX - currentX) > 0.005f || Math.abs(targetY - currentY) > 0.005f ||
                Math.abs(targetRadius - currentRadius) > 0.3f || Math.abs(targetAlpha - currentAlpha) > 0.01f) {
            postInvalidateOnAnimation();
        }
    }

    private float dp(float x) {
        return x * getResources().getDisplayMetrics().density;
    }
}
