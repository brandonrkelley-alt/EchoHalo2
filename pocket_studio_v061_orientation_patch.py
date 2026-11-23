#!/usr/bin/env python3
"""Pocket Studio v0.6.1 non-destructive orientation correction."""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
base=root/"app/src/main/java/com/pocketstudio/app"
def change(path,old,new):
    s=path.read_text(encoding="utf-8")
    if s.count(old)!=1: raise RuntimeError(f"Expected one anchor in {path}: {old[:70]!r} got {s.count(old)}")
    path.write_text(s.replace(old,new),encoding="utf-8")
p=base/"ImageFiles.java"
change(p,"import android.graphics.ImageDecoder;","import android.graphics.ImageDecoder;\nimport android.graphics.Matrix;")
change(p,"    public static byte[] png(Bitmap bitmap) {",'''    /** Clockwise quarter-turn on decoded pixels: no duplicate EXIF transform. */
    public static Bitmap rotateQuarter(Bitmap source,int degrees) {
        requireBitmap(source);
        if(degrees!=-90 && degrees!=90 && degrees!=180)
            throw new IllegalArgumentException("Rotation must be -90, 90, or 180");
        Matrix matrix=new Matrix();
        matrix.setRotate(degrees);
        Bitmap rotated=Bitmap.createBitmap(source,0,0,source.getWidth(),source.getHeight(),matrix,false);
        if(rotated==null)throw new IllegalStateException("Could not rotate image");
        rotated.setDensity(Bitmap.DENSITY_NONE);
        return rotated;
    }

    public static byte[] png(Bitmap bitmap) {''')
p=base/"StudioState.java"
change(p,"    public String finalPrompt(boolean editing) {",'''    /** Correct a sideways imported photo and its painted mask together. */
    public void rotateSource(int degrees) {
        if(busy || checking || source==null)return;
        final Bitmap before=source;
        final MaskDocument oldMask=mask;
        busy=true;message="Rotating photo and mask…";changed(true);
        worker.execute(()->{
            try {
                Bitmap rotated=ImageFiles.rotateQuarter(before,degrees);
                Bitmap rotatedMask=oldMask==null?null:ImageFiles.rotateQuarter(oldMask.bitmap(),degrees);
                main.post(()->{
                    setSource(rotated,rotated.getWidth()+" × "+rotated.getHeight()+" working pixels · orientation adjusted");
                    if(rotatedMask!=null){mask.restoreFrom(rotatedMask);rotatedMask.recycle();}
                    busy=false;message="Photo and mask rotated. Original Gallery file unchanged.";changed(true);
                });
            }catch(Exception e){finishFailure("Could not rotate photo: "+safe(e),true);}
            catch(OutOfMemoryError e){finishFailure("Not enough memory to rotate photo.",true);}
        });
    }

    /** Rotate result into a separate unsaved preview; prior Library items remain unchanged. */
    public void rotateResult(int degrees) {
        if(busy || checking || result==null)return;
        final Bitmap before=result;
        final int selected=previewIndex;
        final Preview previous=selected>=0 && selected<previews.size()?previews.get(selected):null;
        busy=true;message="Rotating result…";changed(true);
        worker.execute(()->{
            try {
                Bitmap rotated=ImageFiles.rotateQuarter(before,degrees);
                main.post(()->{
                    if(previous!=null && selected<previews.size() && previews.get(selected)==previous){
                        Map<String,Object> meta=new LinkedHashMap<>(previous.metadata);
                        meta.put("result_width",rotated.getWidth());meta.put("result_height",rotated.getHeight());
                        meta.put("rotation_correction_degrees",degrees);
                        previews.set(selected,new Preview(rotated,null,null,meta));
                    }
                    result=rotated;resultOriginal=null;resultId="";showResult=true;busy=false;
                    message="Result rotated. Save corrected copy; earlier Library images remain unchanged.";
                    changed(true);
                });
            }catch(Exception e){finishFailure("Could not rotate result: "+safe(e),true);}
            catch(OutOfMemoryError e){finishFailure("Not enough memory to rotate result.",true);}
        });
    }

    public String finalPrompt(boolean editing) {''')
p=base/"MainActivity.java"
change(p,"        if(displayed!=null){\n            final Bitmap fullImage=displayed;",'''        if(displayed!=null){
            LinearLayout rotatePhoto=row();
            addEqual(rotatePhoto,button("↶ Rotate left 90°",()->{
                if(state.showResult&&state.result!=null)state.rotateResult(-90);
                else state.rotateSource(-90);
            },false));
            addEqual(rotatePhoto,button("↷ Rotate right 90°",()->{
                if(state.showResult&&state.result!=null)state.rotateResult(90);
                else state.rotateSource(90);
            },false));
            canvasColumn.addView(rotatePhoto);
            final Bitmap fullImage=displayed;''')
change(p,'        if(tab!=1)c.addView(button("⛶ View image full screen · Pinch to zoom",this::fullScreenResult,false));','''        if(tab!=1){
            c.addView(button("⛶ View image full screen · Pinch to zoom",this::fullScreenResult,false));
            LinearLayout rotateResultRow=row();
            addEqual(rotateResultRow,button("↶ Rotate result left",()->state.rotateResult(-90),false));
            addEqual(rotateResultRow,button("↷ Rotate result right",()->state.rotateResult(90),false));
            c.addView(rotateResultRow);
        }''')
p=root/"app/build.gradle"
change(p,"versionCode 11","versionCode 12")
change(p,"versionName '0.6.0'","versionName '0.6.1'")
p=root/"scripts/build_with_sdk.py"
for old,new in [
    ('node.set(ANDROID + "versionCode", "11")','node.set(ANDROID + "versionCode", "12")'),
    ('node.set(ANDROID + "versionName", "0.6.0")','node.set(ANDROID + "versionName", "0.6.1")'),
    ('public static final int VERSION_CODE = 11;','public static final int VERSION_CODE = 12;'),
    ('public static final String VERSION_NAME = "0.6.0";','public static final String VERSION_NAME = "0.6.1";'),
    ('Pocket_Studio_v0_6_0_debug.apk','Pocket_Studio_v0_6_1_debug.apk'),
]: change(p,old,new)
print("Applied Pocket Studio v0.6.1 orientation patch.")
