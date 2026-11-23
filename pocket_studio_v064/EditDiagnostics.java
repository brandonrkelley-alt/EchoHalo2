package com.pocketstudio.app.core;

/** Lightweight, sampled edit diagnostics; never logs prompts or image contents. */
public final class EditDiagnostics {
    private EditDiagnostics() {}

    /** Mean absolute RGB channel delta (0..255) at evenly spaced image pixels. */
    public static double meanRgbDelta(int[] original, int[] generated) {
        if(original == null || generated == null || original.length == 0 || original.length != generated.length)
            throw new IllegalArgumentException("Comparison images must have matching pixel arrays");
        int stride=Math.max(1,(int)Math.ceil(original.length/16384.0));
        long error=0;
        int count=0;
        for(int i=0;i<original.length;i+=stride) {
            int a=original[i],b=generated[i];
            error+=Math.abs(((a>>>16)&255)-((b>>>16)&255));
            error+=Math.abs(((a>>>8)&255)-((b>>>8)&255));
            error+=Math.abs((a&255)-(b&255));
            count++;
        }
        return error/(3.0*count);
    }

    /** Approximate selected coverage; null mask denotes an entire-frame edit. */
    public static double maskCoveragePercent(int[] alpha) {
        if(alpha==null)return 100.0;
        if(alpha.length==0)throw new IllegalArgumentException("Mask is empty");
        int stride=Math.max(1,(int)Math.ceil(alpha.length/16384.0));
        double total=0;
        int count=0;
        for(int i=0;i<alpha.length;i+=stride) {
            int a=alpha[i];
            if(a<0 || a>255)throw new IllegalArgumentException("Mask alpha must be 0..255");
            total+=a/255.0;
            count++;
        }
        return 100.0*total/count;
    }
}
