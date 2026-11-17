"""Библиотека анимаций Mixamo -> один glb (полный скелет ct_1 в метрах + все клипы дорожками NLA).
blender -b --python cs2_anims.py -- <rig.fbx> <папка anims> <out.glb>"""
import bpy, sys, os, re, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cs2_fighter as F

rig, adir, out = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
arm, body = F.import_rig(rig)
bpy.data.objects.remove(body, do_unlink=True)


def clean(folder, fn):
    s = os.path.splitext(fn)[0].lower()
    s = s.replace("(2)", "b")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if folder == "pistol":
        s = s if s.startswith("pistol") else "pistol_" + s
    elif folder == "rifle":
        s = "rifle_" + s
    return s


LOCO = ("walk", "run", "sprint", "strafe", "jump")
LOOP = ("walk", "run", "sprint", "strafe", "idle", "jump_loop", "breathing")
report = {}
for folder in ("rifle", "pistol", "misc"):
    d = os.path.join(adir, folder)
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".fbx"):
            continue
        name = clean(folder, fn)
        loco = any(w in name for w in LOCO) and "death" not in name and "turn" not in name
        act = F.load_action(os.path.join(d, fn), name, loop_fix=loco)
        act.use_fake_user = True
        fr = act.frame_range
        report[name] = {"frames": int(fr[1] - fr[0]), "loop": any(w in name for w in LOOP) and not any(w in name for w in ("death", "_to_", "turn")),
                        "loco": loco}

ad = arm.animation_data_create()
ad.action = None
for act in sorted(bpy.data.actions, key=lambda a: a.name):
    tr = ad.nla_tracks.new()
    tr.name = act.name
    st = tr.strips.new(act.name, int(act.frame_range[0]), act)
    st.name = act.name
bpy.context.scene.render.fps = 30
for o in bpy.context.scene.objects:
    o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_animations=True,
                          export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_optimize_animation_size=True,
                          export_skins=True, export_yup=True, export_frame_range=False, export_anim_single_armature=True)
json.dump(report, open(os.path.splitext(out)[0] + "_report.json", "w"), indent=1)
print("ANIMS", len(bpy.data.actions), "->", out, round(os.path.getsize(out) / 2 ** 20, 2), "MB")
