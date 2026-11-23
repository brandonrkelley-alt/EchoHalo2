#!/usr/bin/env python3
"""Restore reliable Original / Edited comparison in Pocket Studio v0.6.3."""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
base=root/"app/src/main/java/com/pocketstudio/app"

def replace_once(file, old, new):
    content=file.read_text(encoding="utf-8")
    occurrences=content.count(old)
    if occurrences != 1:
        raise RuntimeError(f"Expected exactly one match in {file}: {old[:100]!r}; found {occurrences}")
    file.write_text(content.replace(old,new),encoding="utf-8")

state=base/"StudioState.java"
# Keep original and mask with rotated output so the comparison remains usable.
replace_once(state,
    '''        final Bitmap before=result;
        final int selected=previewIndex;
        final Preview previous=selected>=0 && selected<previews.size()?previews.get(selected):null;''',
    '''        final Bitmap before=result;
        final int selected=previewIndex;
        final Preview previous=selected>=0 && selected<previews.size()?previews.get(selected):null;
        final Bitmap beforeOriginal=resultOriginal!=null?resultOriginal:(previous==null?null:previous.original);
        final Bitmap beforeMask=previous==null?null:previous.mask;''')
replace_once(state,
    '''                Bitmap rotated=ImageFiles.rotateQuarter(before,degrees);
                main.post(()->{
                    if(previous!=null && selected<previews.size() && previews.get(selected)==previous){''',
    '''                Bitmap rotated=ImageFiles.rotateQuarter(before,degrees);
                Bitmap rotatedOriginal=beforeOriginal==null?null:ImageFiles.rotateQuarter(beforeOriginal,degrees);
                Bitmap rotatedMask=beforeMask==null?null:ImageFiles.rotateQuarter(beforeMask,degrees);
                main.post(()->{
                    if(previous!=null && selected<previews.size() && previews.get(selected)==previous){''')
replace_once(state,
    '''                        meta.put("rotation_correction_degrees",degrees);
                        previews.set(selected,new Preview(rotated,null,null,meta));''',
    '''                        int prevDegrees=meta.get("rotation_correction_degrees") instanceof Number
                            ?((Number)meta.get("rotation_correction_degrees")).intValue():0;
                        meta.put("rotation_correction_degrees",(prevDegrees+degrees+720)%360);
                        previews.set(selected,new Preview(rotated,rotatedOriginal,rotatedMask,meta));''')
replace_once(state,
    '''                    result=rotated;resultOriginal=null;resultId="";showResult=true;busy=false;''',
    '''                    result=rotated;resultOriginal=rotatedOriginal;resultId="";showResult=true;busy=false;''')

activity=base/"MainActivity.java"
replace_once(activity,
    '''    private MaskEditorView editor;
    private ComposeView composer;''',
    '''    private MaskEditorView editor;
    private Bitmap comparedResult;
    private boolean showingOriginal=false;
    private ComposeView composer;''')
replace_once(activity,
    '''        editor=new MaskEditorView(this);editor.mode=state.mode;editor.brushDp=state.brush;
        Bitmap displayed=state.showResult&&state.result!=null?state.result:state.source;
        editor.bind(displayed,state.showResult?null:state.mask,state.showResult?state.resultOriginal:null);
        editor.readOnly=state.showResult||state.busy;''',
    '''        editor=new MaskEditorView(this);editor.mode=state.mode;editor.brushDp=state.brush;
        Bitmap displayed=state.showResult&&state.result!=null?state.result:state.source;
        if(!state.showResult || state.result==null){
            comparedResult=null;showingOriginal=false;
        }else if(comparedResult!=state.result){
            comparedResult=state.result;showingOriginal=false;
        }
        editor.bind(displayed,state.showResult?null:state.mask,state.showResult?state.resultOriginal:null);
        editor.showComparison=state.showResult&&showingOriginal&&state.resultOriginal!=null;
        editor.readOnly=state.showResult||state.busy;''')
replace_once(activity,
    '''            LinearLayout compare=row();addEqual(compare,button("Edit original",()->{state.showResult=false;render();},false));
            Button before=button("Show original",()->{},false);locked.remove(before);before.setEnabled(state.resultOriginal!=null);before.setOnClickListener(v->{editor.showComparison=!editor.showComparison;before.setText(editor.showComparison?"Show result":"Show original");editor.invalidate();});addEqual(compare,before);canvasColumn.addView(compare);''',
    '''            LinearLayout compare=row();addEqual(compare,button("Edit original",()->{showingOriginal=false;state.showResult=false;render();},false));
            Button before=button(showingOriginal?"Show edited":"Show original",()->{},false);
            locked.remove(before);
            before.setEnabled(state.resultOriginal!=null);
            before.setOnClickListener(v->{
                showingOriginal=!showingOriginal;
                editor.showComparison=showingOriginal&&state.resultOriginal!=null;
                before.setText(showingOriginal?"Show edited":"Show original");
                editor.invalidate();
            });
            addEqual(compare,before);canvasColumn.addView(compare);''')

# Keep the comparison fix isolated from working inference, model selection, and timing.
gradle=root/"app/build.gradle"
replace_once(gradle,"versionCode 13","versionCode 14")
replace_once(gradle,"versionName '0.6.2'","versionName '0.6.3'")
builder=root/"scripts/build_with_sdk.py"
for old,new in [
    ('node.set(ANDROID + "versionCode", "13")','node.set(ANDROID + "versionCode", "14")'),
    ('node.set(ANDROID + "versionName", "0.6.2")','node.set(ANDROID + "versionName", "0.6.3")'),
    ('public static final int VERSION_CODE = 13;','public static final int VERSION_CODE = 14;'),
    ('public static final String VERSION_NAME = "0.6.2";','public static final String VERSION_NAME = "0.6.3";'),
    ('Pocket_Studio_v0_6_2_debug.apk','Pocket_Studio_v0_6_3_debug.apk'),
]:
    replace_once(builder,old,new)
print("Applied Pocket Studio v0.6.3 comparison fix.")
