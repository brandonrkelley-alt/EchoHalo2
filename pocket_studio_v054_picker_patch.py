#!/usr/bin/env python3
"""Pocket Studio 0.5.4: photo gallery picker and one fullscreen button per screen."""
from pathlib import Path

root=Path("pocket-studio-build")
activity=root/"app/src/main/java/com/pocketstudio/app/MainActivity.java"
gradle=root/"app/build.gradle"
s=activity.read_text(encoding="utf-8")
old='    private void pick(int target){if(state.busy)return;importTarget=target;Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*").addCategory(Intent.CATEGORY_OPENABLE);intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);try{startActivityForResult(intent,100);}catch(Exception e){notice("No Android image picker is available.");}}'
new='''    /** Android Photo Picker displays Photos / Albums instead of a file browser. */
    private void pick(int target) {
        if (state.busy) return;
        importTarget = target;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            Intent photoPicker = new Intent(MediaStore.ACTION_PICK_IMAGES);
            photoPicker.setType("image/*");
            photoPicker.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            try {
                startActivityForResult(photoPicker, 100);
                return;
            } catch (android.content.ActivityNotFoundException | SecurityException unsupported) {
                // Fallback for phones lacking Photo Picker.
            }
        }
        Intent fallback = new Intent(Intent.ACTION_GET_CONTENT);
        fallback.setType("image/*");
        fallback.addCategory(Intent.CATEGORY_OPENABLE);
        fallback.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            startActivityForResult(fallback, 100);
        } catch (Exception error) {
            notice("Could not open photos: " + error.getMessage());
        }
    }'''
assert s.count(old)==1,"Old picker method not found exactly once"
s=s.replace(old,new)
oldResult='if(request==100&&resultCode==RESULT_OK&&data!=null&&data.getData()!=null){Uri uri=data.getData();try{getContentResolver().takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(Exception ignored){}state.importImage(uri,importTarget);}'
newResult='if(request==100&&resultCode==RESULT_OK&&data!=null&&data.getData()!=null){Uri uri=data.getData();state.importImage(uri,importTarget);}'
assert s.count(oldResult)==1,"Image selection callback not found"
s=s.replace(oldResult,newResult)
s=s.replace('button("Import photo",()->pick(0),true)','button("Choose from gallery",()->pick(0),true)')
s=s.replace('button("Import subject",()->pick(1),true)','button("Subject photo",()->pick(1),true)')
s=s.replace('button("Import background",()->pick(2),false)','button("Background photo",()->pick(2),false)')
# Edit already has an image viewer button; don't show a second one in result actions.
oldFull='        c.addView(button("⛶ View image full screen · Pinch to zoom",this::fullScreenResult,false));'
newFull='        if(tab!=1)c.addView(button("⛶ View image full screen · Pinch to zoom",this::fullScreenResult,false));'
assert s.count(oldFull)==1,"Result fullscreen action not found"
s=s.replace(oldFull,newFull)
assert 'MediaStore.ACTION_PICK_IMAGES' in s and 'ACTION_OPEN_DOCUMENT' not in s
activity.write_text(s,encoding="utf-8")
b=gradle.read_text(encoding="utf-8")
assert "versionCode 8" in b and "versionName '0.5.3'" in b,"Unexpected starting version"
b=b.replace("versionCode 8","versionCode 9").replace("versionName '0.5.3'","versionName '0.5.4'")
gradle.write_text(b,encoding="utf-8")
print("Pocket Studio 0.5.4: gallery picker, one full screen control, version updated.")
