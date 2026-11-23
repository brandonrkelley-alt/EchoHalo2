#!/usr/bin/env python3
"""Pocket Studio v0.6.4: make FLUX whole-photo editing explicit and diagnose no-change results."""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
base=root/"app/src/main/java/com/pocketstudio/app"
def change(file,old,new):
    s=file.read_text(encoding="utf-8")
    n=s.count(old)
    if n!=1: raise RuntimeError(f"Expected one anchor in {file}: {old[:110]!r}; found {n}")
    file.write_text(s.replace(old,new),encoding="utf-8")

diag=Path(__file__).resolve().parent/"pocket_studio_v064"
(base/"core/EditDiagnostics.java").write_text((diag/"EditDiagnostics.java").read_text(encoding="utf-8"),encoding="utf-8")
(root/"tests/EditDiagnosticsTests.java").write_text((diag/"EditDiagnosticsTests.java").read_text(encoding="utf-8"),encoding="utf-8")

state=base/"StudioState.java"
change(state,"import com.pocketstudio.app.core.PixelOps;","import com.pocketstudio.app.core.PixelOps;\nimport com.pocketstudio.app.core.EditDiagnostics;")
change(state,"    public boolean confirmed = false, useMask = true, regionOnly = true, hints = false;",
"""    public boolean confirmed = false, useMask = false, regionOnly = true, hints = false;""")
change(state,'        strength = p.getFloat("strength",.5f); cfg = p.getFloat("cfg",7f);',
'''        strength = p.getFloat("strength",.5f); cfg = p.getFloat("cfg",7f);
        useMask=p.getBoolean("use_mask",false);regionOnly=p.getBoolean("region_only",true);''')
change(state,'.putFloat("strength",strength).putFloat("cfg",cfg).apply();',
'''.putFloat("strength",strength).putFloat("cfg",cfg)
            .putBoolean("use_mask",useMask).putBoolean("region_only",regionOnly).apply();''')
change(state,"    public void selectHostResolution(int width,int height) {",
'''    /** One-tap, reversible settings for true whole-photo FLUX reference editing. */
    public void prepareFluxEdit() {
        if(busy||checking)return;
        if(selectedKind()!=ModelCapabilities.Kind.FLUX_KLEIN){
            message="Select FLUX Klein in Settings first.";changed(true);return;
        }
        useMask=false;regionOnly=false;strength=1f;
        Map<String,Object> model=hostModel(hostModelId);
        steps=ModelCapabilities.defaultSteps(model);
        cfg=ModelCapabilities.defaultCfg(model);
        scheduler=ModelCapabilities.defaultScheduler(model);
        message="FLUX whole-photo edit ready: no mask, 100% reference strength, model defaults.";
        persistSettings();changed(true);
    }

    public void selectHostResolution(int width,int height) {''')
change(state,
'''        if(editing && useMask && (mask==null || !mask.hasPaint())) {message="Paint an area to edit, or switch off ‘Edit only the painted area’.";changed(false);return;}''',
'''        if(editing && useMask && (mask==null || !mask.hasPaint())) {message="Paint an area to edit, or switch off ‘Edit only the painted area’.";changed(false);return;}''')
change(state,
'''                Map<String,Object> base=new LinkedHashMap<>();
                base.put("prompt",actualPrompt);''',
'''                Map<String,Object> base=new LinkedHashMap<>();
                base.put("prompt",actualPrompt);''')
change(state,
'''                ImageGeometry.FramePlan plan=null;
                int[] pixels=null;''',
'''                ImageGeometry.FramePlan plan=null;
                int[] pixels=null;
                int[] rawSourcePixels=null;''')
change(state,
'''                    Bitmap prepared=ImageFiles.fromPixels(PixelOps.prepare(pixels,original.getWidth(),original.getHeight(),plan),tw,th);''',
'''                    rawSourcePixels=PixelOps.prepare(pixels,original.getWidth(),original.getHeight(),plan);
                    Bitmap prepared=ImageFiles.fromPixels(rawSourcePixels,tw,th);''')
change(state,
'''                    Bitmap finalImage=generated;
                    if(original!=null) {''',
'''                    if(original!=null && rawSourcePixels!=null){
                        double rawDelta=EditDiagnostics.meanRgbDelta(rawSourcePixels,ImageFiles.pixels(generated));
                        ledger.put("raw_model_rgb_delta",rawDelta);
                        ledger.put("edit_mask_coverage_percent",EditDiagnostics.maskCoveragePercent(alpha));
                    }
                    Bitmap finalImage=generated;
                    if(original!=null) {''')
change(state,
'''                        finalImage=ImageFiles.fromPixels(merged,original.getWidth(),original.getHeight());generated.recycle();''',
'''                        double finalDelta=EditDiagnostics.meanRgbDelta(pixels,merged);
                        ledger.put("final_rgb_delta",finalDelta);
                        ledger.put("masked_edit_hid_changes",alpha!=null && finalDelta<1.5 &&
                            ((Number)ledger.get("raw_model_rgb_delta")).doubleValue()>8.0);
                        finalImage=ImageFiles.fromPixels(merged,original.getWidth(),original.getHeight());generated.recycle();''')
change(state,
'''                        message="Preview "+position+" of "+count+(preview.savedId.isEmpty()?" · not saved to Library.":" · saved to Library.");''',
'''                        double raw=preview.metadata.get("raw_model_rgb_delta") instanceof Number
                            ?((Number)preview.metadata.get("raw_model_rgb_delta")).doubleValue():-1;
                        double fin=preview.metadata.get("final_rgb_delta") instanceof Number
                            ?((Number)preview.metadata.get("final_rgb_delta")).doubleValue():-1;
                        if(Boolean.TRUE.equals(preview.metadata.get("masked_edit_hid_changes")))
                            message="Mask restricted the edit: model changed image, but most changes were excluded. Use whole-photo mode.";
                        else if(raw>=0 && raw<1.5)
                            message="Local Dream returned nearly unchanged pixels. Try FLUX whole-photo edit, 100% strength, CFG 1 and 4 steps.";
                        else if(fin>=0 && fin<1.5 && raw>8)
                            message="The model changed pixels, but compositing kept the output similar. Inspect edit settings.";
                        else
                            message="Preview "+position+" of "+count+(preview.savedId.isEmpty()?" · not saved to Library.":" · saved in Library.");''')

activity=base/"MainActivity.java"
change(activity,
'''        check(controls,"Edit only the painted area",state.useMask,b->state.useMask=b);
        check(controls,"Focus model detail on the selected region",state.regionOnly,b->state.regionOnly=b);''',
'''        if(state.hostManaged&&state.selectedKind()==ModelCapabilities.Kind.FLUX_KLEIN) {
            controls.addView(button("FLUX whole-photo edit · use model defaults",()->state.prepareFluxEdit(),false));
            note(controls,"Whole-photo mode is recommended for ordinary FLUX image instructions. Masked mode intentionally preserves all unpainted pixels, so it may appear to ignore your prompt. Tap the button to disable masking and use 100% strength.");
        }
        check(controls,"Edit only the painted area",state.useMask,b->{state.useMask=b;state.persistSettings();});
        check(controls,"Focus model detail on the selected region",state.regionOnly,b->{state.regionOnly=b;state.persistSettings();});''')
change(activity,
'''            StudioState.Preview current=state.previews.get(state.previewIndex);
            double totalMs=''',
'''            StudioState.Preview current=state.previews.get(state.previewIndex);
            if(current.metadata.get("raw_model_rgb_delta") instanceof Number) {
                double raw=((Number)current.metadata.get("raw_model_rgb_delta")).doubleValue();
                double fin=current.metadata.get("final_rgb_delta") instanceof Number
                    ?((Number)current.metadata.get("final_rgb_delta")).doubleValue():-1;
                double coverage=current.metadata.get("edit_mask_coverage_percent") instanceof Number
                    ?((Number)current.metadata.get("edit_mask_coverage_percent")).doubleValue():100;
                String diff=String.format(Locale.US,"Edit diagnostic: model %.1f / 255 RGB delta; final %.1f / 255; mask coverage %.0f%%.",
                    raw,fin,coverage);
                note(c,diff);
                if(Boolean.TRUE.equals(current.metadata.get("masked_edit_hid_changes")))
                    note(c,"Model produced changes, but the painted mask kept most of the original. Choose whole-photo edit to test.");
                else if(raw<1.5)
                    note(c,"The model returned nearly unchanged pixels. This is not caused by Pocket Studio compositing.");
            }
            double totalMs=''')

gradle=root/"app/build.gradle"
change(gradle,"versionCode 14","versionCode 15")
change(gradle,"versionName '0.6.3'","versionName '0.6.4'")
builder=root/"scripts/build_with_sdk.py"
for old,new in [
    ('node.set(ANDROID + "versionCode", "14")','node.set(ANDROID + "versionCode", "15")'),
    ('node.set(ANDROID + "versionName", "0.6.3")','node.set(ANDROID + "versionName", "0.6.4")'),
    ('public static final int VERSION_CODE = 14;','public static final int VERSION_CODE = 15;'),
    ('public static final String VERSION_NAME = "0.6.3";','public static final String VERSION_NAME = "0.6.4";'),
    ('Pocket_Studio_v0_6_3_debug.apk','Pocket_Studio_v0_6_4_debug.apk'),
]: change(builder,old,new)
print("Applied Pocket Studio v0.6.4 FLUX editing and diagnostics patch.")
