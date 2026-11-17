"""FABLE STRIKE 2 — сборка бойца: риг Mixamo + 4K-материал Tripo + очки + полный набор костей -> glb.
В окне Blender: F.go("ct_1") — сборка по шагам с записью кадров. В фоне/облаке: F.assemble(...); F.export(...)."""
import bpy, os, sys, json, math, time
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cs2_chars as C

NS = bpy.app.driver_namespace
HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "chars_ref_skel.json")
STYLE = {"ct_1": ("goggles", True), "ct_2": ("sport", False), "t_1": ("sport", False), "t_2": (None, False)}


def _paths(name):
    import cs2_tools as T
    ch = os.path.join(T.DL, "cs2_chars")
    return (os.path.join(ch, "mixamo_out", name, name + ".fbx"), os.path.join(ch, name, name + ".glb"),
            os.path.join(T.MODELS, "chars", name + ".glb"))


def _active(ob):
    for o in [o_ for o_ in bpy.context.view_layer.objects if o_]:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob


def import_rig(fbx):
    """FBX Mixamo -> (arm, body) в метрах, без масштаба 0.01 и поворотов на объектах."""
    before = set(bpy.data.objects)
    acts = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before]
    arm = [o for o in new if o.type == 'ARMATURE'][0]
    body = max((o for o in new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    for o in new:
        if o not in (arm, body):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    mw = body.matrix_world.copy()
    body.parent = None
    body.data.transform(mw)
    body.matrix_world = Matrix.Identity(4)
    if arm.animation_data:
        arm.animation_data_clear()
    for a in [a for a in bpy.data.actions if a not in acts]:
        bpy.data.actions.remove(a)
    arm.data.transform(arm.matrix_world.copy())
    arm.matrix_world = Matrix.Identity(4)
    body.parent = arm
    body.matrix_parent_inverse = Matrix.Identity(4)
    arm.name = "Armature"
    arm.data.name = "Armature"
    bpy.context.view_layer.update()
    return arm, body


def save_ref(arm, path=REF):
    """эталонный скелет (ct_1): кость -> родитель, матрица относительно родителя, длина"""
    d = {}
    for b in arm.data.bones:
        rel = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local
        d[b.name] = {"parent": b.parent.name if b.parent else None, "rel": [list(r) for r in rel], "len": b.length}
    json.dump({"order": [b.name for b in arm.data.bones], "bones": d}, open(path, "w"))
    return len(d)


def add_missing_bones(arm, path=REF):
    """досоздать кости, которых нет в урезанном скелете (пальцы): без весов, чтобы имена совпадали у всех бойцов"""
    ref = json.load(open(path))
    have = {b.name for b in arm.data.bones}
    todo = [n for n in ref["order"] if n not in have]
    if not todo:
        return 0
    # масштаб кисти: длина предплечья бойца / эталона
    _active(arm)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    for n in todo:
        r = ref["bones"][n]
        par = eb.get(r["parent"])
        if par is None:
            continue
        k = 1.0
        hand = "LeftHand" if "Left" in n else "RightHand"
        fa = eb.get("mixamorig:" + hand.replace("Hand", "ForeArm"))
        rf = ref["bones"].get("mixamorig:" + hand.replace("Hand", "ForeArm"))
        if fa and rf:
            k = fa.length / rf["len"]
        rel = Matrix(r["rel"])
        rel.translation *= k
        m = par.matrix @ rel
        b = eb.new(n)
        b.head = m.translation
        b.tail = m.translation + m.to_3x3().col[1].normalized() * max(0.004, r["len"] * k)
        b.matrix = m
        b.length = max(0.004, r["len"] * k)
        b.parent = par
        b.use_connect = False
        b.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return len(todo)


def tripo_material(glb, name):
    """материал 4K (цвет/ORM/нормаль) из исходного glb Tripo"""
    before = set(bpy.data.objects)
    mats = set(bpy.data.materials)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in bpy.data.objects if o not in before]
    mat = [m for m in bpy.data.materials if m not in mats][0]
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    mat.name = name + "_mat"
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            kind = "base" if n.image.name.startswith("Color") else "orm" if n.image.name.startswith("ORM") else "normal"
            n.image.name = f"{name}_{kind}"
    p = mat.node_tree.nodes.get("Principled BSDF")
    if p:
        try:
            p.inputs["Specular IOR Level"].default_value = 0.35
        except Exception:
            pass
    return mat


def assemble(name, fbx, glb, style=None, strap=False, ref=REF):
    arm, body = import_rig(fbx)
    body.name = name + "_body"
    body.data.name = name + "_body"
    n_add = add_missing_bones(arm, ref) if os.path.exists(ref) else 0
    mat = tripo_material(glb, name)
    old = list(body.data.materials)
    body.data.materials.clear()
    body.data.materials.append(mat)
    for m in old:
        if m.users == 0:
            bpy.data.materials.remove(m)
    for p in body.data.polygons:
        p.use_smooth = True
    ew = None
    if style:
        ew = C.add_eyewear(arm, body, C.measure_head(arm, body), style=style, strap=strap, name=name + "_eyewear")
    link(name, arm, [body] + ([ew] if ew else []))
    return arm, body, ew, n_add


def link(name, arm, meshes):
    """коллекция <name> + <name>_root (для студии/облёта)"""
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.get(name + "_root") or bpy.data.objects.new(name + "_root", None)
    root.empty_display_size = 0.05
    for o in [root, arm] + meshes:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    arm.parent = root
    return col, root


def export(name, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    arm = bpy.data.objects["Armature"]
    arm.hide_set(False)
    arm.hide_viewport = False
    bpy.context.view_layer.update()
    sel = [arm] + [o for o in arm.children if o.type == 'MESH']
    for o in [o_ for o_ in bpy.context.view_layer.objects if o_]:
        o.select_set(o in sel)
    bpy.context.view_layer.objects.active = arm
    keep = arm.parent
    arm.parent = None
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_animations=False, export_skins=True,
                              export_yup=True, export_image_format='JPEG', export_jpeg_quality=92, export_tangents=True,
                              export_all_influences=False, export_def_bones=False)
    arm.parent = keep
    return round(os.path.getsize(out) / 2 ** 20, 2)


def load_action(fbx, name, loop_fix=True):
    """клип Mixamo (FBX без скина, 0.01) -> действие для скелета в метрах"""
    before = set(bpy.data.objects)
    acts = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new_acts = [a for a in bpy.data.actions if a not in acts]
    for o in [o for o in bpy.data.objects if o not in before]:
        bpy.data.objects.remove(o, do_unlink=True)
    act = max(new_acts, key=lambda a: a.frame_range[1] - a.frame_range[0])
    for a in new_acts:
        if a != act:
            bpy.data.actions.remove(a)
    act.name = name
    fix_action(act, detrend=loop_fix)
    return act


def fcurves(act):
    try:
        return list(act.fcurves)
    except Exception:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out += list(cb.fcurves)
        return out


def fix_action(act, detrend=False, k=0.01):
    """сантиметры -> метры; detrend: убрать уход таза по горизонтали (бег «на месте»), покачивание остаётся"""
    travel = 0.0
    for fc in fcurves(act):
        if not fc.data_path.endswith(".location"):
            continue
        kp = fc.keyframe_points
        for p in kp:
            p.co[1] *= k
            p.handle_left[1] *= k
            p.handle_right[1] *= k
        if 'Hips"]' in fc.data_path and fc.array_index in (0, 2) and len(kp) > 1:
            t0, t1 = kp[0].co[0], kp[-1].co[0]
            dv = kp[-1].co[1] - kp[0].co[1]
            travel = max(travel, abs(dv))
            if detrend and abs(dv) > 0.20:
                for p in kp:
                    off = dv * (p.co[0] - t0) / (t1 - t0)
                    p.co[1] -= off
                    p.handle_left[1] -= off
                    p.handle_right[1] -= off
        fc.update()
    return travel


# ------------------------------------------------------------------ окно Blender: сборка с записью
def go(name, style="auto", clip="rifle/Rifle Run.fbx", seg=70, tick=0.04):
    """шаги: сетка -> скелет -> материал 4K -> очки (крупно) -> пробежка -> glb + blend. Кадры: footage/build/char_<name>."""
    import cs2_tools as T
    fbx, glb, out_glb = _paths(name)
    if style == "auto":
        style, strap = STYLE.get(name, (None, False))
    else:
        strap = style == "goggles"
    T.new_scene()
    st = {"name": name, "n": 0, "step": 0, "k": 0, "done": False, "err": None, "state": "import", "t0": time.time(), "yaw": 150.0, "pending": False}
    NS["cs2_fighter"] = st
    st["mode"] = T.shot_mode_detect()
    out = os.path.join(T.FOOTAGE, "build", "char_" + name + ("_hd" if st["mode"] == "view" else ""))
    os.makedirs(out, exist_ok=True)
    arm, body = import_rig(fbx)
    body.name = name + "_body"
    link(name, arm, [body])
    grey = bpy.data.materials.new("clay")
    grey.diffuse_color = (0.42, 0.40, 0.38, 1)
    orig = list(body.data.materials)
    body.data.materials.clear()
    body.data.materials.append(grey)
    arm.hide_set(True)
    T.setup_viewport('SOLID')
    full = (Vector((0, 0, 0.92)), 3.3)
    st["view"] = full
    sp = T.view3d()[1].spaces.active

    def stage(i):
        if i == 1:                       # скелет
            arm.hide_set(False)
            arm.show_in_front = True
            arm.data.display_type = 'STICK'
            st["added"] = add_missing_bones(arm) if os.path.exists(REF) else 0
            st["state"] = "rig"
        elif i == 2:                     # материал 4K
            arm.hide_set(True)
            mat = tripo_material(glb, name)
            body.data.materials.clear()
            body.data.materials.append(mat)
            for m in orig + [grey]:
                if m.users == 0:
                    bpy.data.materials.remove(m)
            sp.shading.type = 'MATERIAL'
            st["state"] = "material"
        elif i == 3:                     # лицо крупно
            m = C.measure_head(arm, body)
            st["m"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in m.items()}
            st["view"] = (Vector((0, m["cy"], m["ze"] - 0.02)), 0.95)
            st["yaw"] = 150.0
            st["state"] = "face"
        elif i == 4:                     # очки
            if style:
                ew = C.add_eyewear(arm, body, C.measure_head(arm, body), style=style, strap=strap, name=name + "_eyewear")
                link(name, arm, [body, ew])
            st["state"] = "eyewear"
        elif i == 5:                     # пробежка
            st["view"] = full
            p = os.path.join(T.DL, "cs2_chars", "mixamo_out", "anims", *clip.split("/"))
            if os.path.exists(p):
                act = load_action(p, "preview_run")
                arm.animation_data_create().action = act
                try:
                    arm.animation_data.action_slot = act.slots[0]
                except Exception:
                    pass
                st["act"] = (act.frame_range[0], act.frame_range[1])
            st["state"] = "anim"
        elif i == 6:                     # сдача
            if arm.animation_data:
                a = arm.animation_data.action
                arm.animation_data_clear()
                if a:
                    bpy.data.actions.remove(a)
            for pb in arm.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.rotation_euler = (0, 0, 0)
                pb.scale = (1, 1, 1)
            bpy.context.scene.frame_set(1)
            sp.shading.type = 'SOLID'
            arm.hide_set(False)             # скрытый скелет не попадает в выделение -> glb без костей
            arm.show_in_front = False
            st["glb_mb"] = export(name, out_glb)
            st["blend"] = T.save_blend("char_" + name)
            st["state"] = "done"
            st["sec"] = round(time.time() - st["t0"], 1)
            st["done"] = True

    def _tick():
        try:
            if st["pending"]:
                T._shot(os.path.join(out, f"f_{st['n']:06d}.png"))
                st["n"] += 1
                st["pending"] = False
            st["k"] += 1
            if st["k"] >= seg * (1.6 if st["step"] == 5 else 1.0):
                st["k"] = 0
                st["step"] += 1
                stage(st["step"])
                if st["done"]:
                    return None
            if st["step"] == 5 and "act" in st:
                f0, f1 = st["act"]
                bpy.context.scene.frame_set(int(f0 + (st["k"] % max(1, int(f1 - f0)))))
            st["yaw"] += 1.1 if st["step"] not in (3, 4) else 0.75
            c, d = st["view"]
            T.set_view(c, d, st["yaw"], 8.0 if st["step"] not in (3, 4) else 4.0)
            st["pending"] = True
        except Exception:
            import traceback
            st["err"] = traceback.format_exc()
            st["done"] = True
            return None
        return tick

    bpy.app.timers.register(_tick, first_interval=0.4)
    return {"name": name, "frames_dir": out, "style": style}


def status():
    st = NS.get("cs2_fighter")
    if not st:
        return None
    return {k: st.get(k) for k in ("name", "state", "step", "n", "done", "err", "sec", "glb_mb", "added", "mode")}
