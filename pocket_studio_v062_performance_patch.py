#!/usr/bin/env python3
"""Pocket Studio v0.6.2: fast DiT editing controls and per-request timing."""
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
base=root/"app/src/main/java/com/pocketstudio/app"

def change(path,old,new):
    s=path.read_text(encoding="utf-8")
    count=s.count(old)
    if count!=1:
        raise RuntimeError(f"Expected exactly one anchor in {path}: {old[:90]!r}; found {count}")
    path.write_text(s.replace(old,new),encoding="utf-8")

state=base/"StudioState.java"
change(state,
    "    public void selectHostResolution(int width,int height) {",
    """    /** One-tap reset; keeps an intentionally chosen custom CFG until the user requests this. */
    public void restoreModelDefaults() {
        if(busy || checking)return;
        Map<String,Object> model=hostModel(hostModelId);
        if(model.isEmpty()) {
            message="Refresh models in Settings before applying defaults.";
            changed(false);return;
        }
        steps=ModelCapabilities.defaultSteps(model);
        cfg=ModelCapabilities.defaultCfg(model);
        scheduler=ModelCapabilities.defaultScheduler(model);
        if(ModelCapabilities.isDit(ModelCapabilities.classify(model)))strength=1.0f;
        message="Applied "+hostModelName+" defaults: "+steps+" steps, guidance "+cfg+", "+scheduler+".";
        persistSettings();changed(true);
    }

    public void selectHostResolution(int width,int height) {""")
change(state,
    "        busy=true;generating=true;cancelled=false;step=0;totalSteps=nsteps;batchIndex=1;showResult=false;",
    """        final long runStartedMs=android.os.SystemClock.elapsedRealtime();
        busy=true;generating=true;cancelled=false;step=0;totalSteps=nsteps;batchIndex=1;showResult=false;""")
change(state,
    "                    final int position=i+1;\n                    long nextSeed=",
    "                    final int position=i+1;\n                    final long imageStartedMs=position==1?runStartedMs:android.os.SystemClock.elapsedRealtime();\n                    long nextSeed=")
change(state,
    "                    imageRequested=true;\n                    Map<String,Object> response=client.generate(request,(s,t)->main.post(()->{step=s;totalSteps=t;changed(false);}),()->cancelled);",
    """                    imageRequested=true;
                    long requestStartedMs=android.os.SystemClock.elapsedRealtime();
                    Map<String,Object> response=client.generate(request,(s,t)->main.post(()->{step=s;totalSteps=t;changed(false);}),()->cancelled);
                    long requestFinishedMs=android.os.SystemClock.elapsedRealtime();""")
change(state,
    '                    ledger.put("generation_time_ms",response.get("generation_time_ms"));',
    '''                    ledger.put("generation_time_ms",response.get("generation_time_ms"));
                    ledger.put("total_wall_ms",android.os.SystemClock.elapsedRealtime()-imageStartedMs);
                    ledger.put("pre_request_ms",requestStartedMs-imageStartedMs);
                    ledger.put("request_wall_ms",requestFinishedMs-requestStartedMs);
                    ledger.put("post_request_ms",android.os.SystemClock.elapsedRealtime()-requestFinishedMs);''')

activity=base/"MainActivity.java"
change(activity,
    '        if(editing)slider(c,"Change strength",5,95,Math.round(state.strength*100),v->state.strength=v/100f,"%");',
    '''        if(editing){
            slider(c,"Change strength",5,100,Math.round(state.strength*100),v->state.strength=v/100f,"%");
            if(state.hostManaged && state.selectedKind()==ModelCapabilities.Kind.FLUX_KLEIN)
                note(c,"FLUX Klein: 100% without a mask uses your source as a reference only. Below 100%, or when masked, Local Dream also encodes a starting image. This may add work. Use a mask for targeted changes.");
        }''')
change(activity,
    '        slider(c,"Steps",1,60,state.steps,v->state.steps=v,"");',
    '''        if(state.hostManaged && state.selectedKind()!=ModelCapabilities.Kind.UNKNOWN) {
            c.addView(button("Use selected model defaults",()->state.restoreModelDefaults(),false));
            if(ModelCapabilities.isDit(state.selectedKind()) && Math.abs(state.cfg-1.0f)>0.05f)
                note(c,"This distilled model normally runs with guidance near 1.0. Current value is "+state.cfg+". Tap the model-defaults button to restore its recommended settings.");
        }
        slider(c,"Steps",1,60,state.steps,v->state.steps=v,"");''')
change(activity,
    '                    note(c,"Model defaults: "+state.steps+" steps, guidance "+state.cfg+", sampler "+state.scheduler+". You can change these in Create or Edit.");',
    '                    note(c,"Current settings: "+state.steps+" steps, guidance "+state.cfg+", sampler "+state.scheduler+". Restore defaults for this model in Create or Edit.");')
change(activity,
    '            StudioState.Preview current=state.previews.get(state.previewIndex);\n            if(current.savedId.isEmpty())',
    '''            StudioState.Preview current=state.previews.get(state.previewIndex);
            double totalMs=Json.number(current.metadata.get("total_wall_ms"),-1);
            double requestMs=Json.number(current.metadata.get("request_wall_ms"),-1);
            double backendMs=Json.number(current.metadata.get("generation_time_ms"),-1);
            if(totalMs>=0 && requestMs>=0) {
                String timing=String.format(Locale.US,"Time: %.1f s total | %.1f s Local Dream request | %.1f s outside request",
                    totalMs/1000.,requestMs/1000.,Math.max(0,totalMs-requestMs)/1000.);
                if(backendMs>=0)timing+=String.format(Locale.US," | %.1f s model engine",backendMs/1000.);
                note(c,timing);
            }
            if(current.savedId.isEmpty())''')

gradle=root/"app/build.gradle"
change(gradle,"versionCode 12","versionCode 13")
change(gradle,"versionName '0.6.1'","versionName '0.6.2'")
builder=root/"scripts/build_with_sdk.py"
for old,new in [
    ('node.set(ANDROID + "versionCode", "12")','node.set(ANDROID + "versionCode", "13")'),
    ('node.set(ANDROID + "versionName", "0.6.1")','node.set(ANDROID + "versionName", "0.6.2")'),
    ('public static final int VERSION_CODE = 12;','public static final int VERSION_CODE = 13;'),
    ('public static final String VERSION_NAME = "0.6.1";','public static final String VERSION_NAME = "0.6.2";'),
    ('Pocket_Studio_v0_6_1_debug.apk','Pocket_Studio_v0_6_2_debug.apk'),
]:
    change(builder,old,new)
print("Applied Pocket Studio v0.6.2 performance and usability fixes.")
