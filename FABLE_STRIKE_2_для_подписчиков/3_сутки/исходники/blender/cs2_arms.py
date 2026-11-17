"""FABLE STRIKE 2 — руки от первого лица. Сетка, кости и веса приходят из arms/<name>_parts.json
(обводка листа Codex), здесь собирается пара рук (правая + зеркальная левая), материал, glb.
A.build("arms_ct") — сразу; A.go("arms_ct") — по шагам с записью кадров."""
import bpy, bmesh, os, sys, json, math, time
from mathutils import Vector, Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
NS = bpy.app.driver_namespace
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "arms")
GAP = 0.13            # в исходной позе руки лежат параллельно: правая на +X, левая на -X
FING = ("thumb", "index", "middle", "ring", "pinky")


def _mesh(d, side):
    sx = 1.0 if side == "r" else -1.0
    off = GAP * sx
    me = bpy.data.meshes.new(f"{d['name']}_{side}")
    verts = [(v[0] * sx + off, v[1], v[2]) for v in d["verts"]]
    faces = d["faces"] if side == "r" else [f[::-1] for f in d["faces"]]
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    uv = d["uv"]
    for lp in me.loops:
        uvl.data[lp.index].uv = uv[lp.vertex_index]
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(f"{d['name']}_{side}", me)
    for bn, lst in d["weights"].items():
        vg = ob.vertex_groups.new(name=f"{bn}_{side}")
        for i, w in lst:
            vg.add([i], w, 'REPLACE')
    # шов верх/низ: склеить совпадающие вершины контура
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    return ob


def _armature(d, name):
    ad = bpy.data.armatures.new(name + "_rig")
    arm = bpy.data.objects.new("Armature", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.update()
    for o in [o_ for o_ in bpy.context.view_layer.objects if o_]:
        o.select_set(o == arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    for side in ("r", "l"):
        sx = 1.0 if side == "r" else -1.0
        for b in d["bones"]:
            e = eb.new(f"{b['name']}_{side}")
            e.head = (b["head"][0] * sx + GAP * sx, b["head"][1], b["head"][2])
            e.tail = (b["tail"][0] * sx + GAP * sx, b["tail"][1], b["tail"][2])
            e.align_roll(Vector((0, 0, 1)))
            if b["parent"]:
                e.parent = eb[f"{b['parent']}_{side}"]
                e.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm


def _material(name, tex_dir):
    m = bpy.data.materials.new(name + "_mat")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    base = nt.nodes.new("ShaderNodeTexImage")
    base.image = bpy.data.images.load(os.path.join(tex_dir, name + "_base.png"), check_existing=True)
    base.location = (-520, 260)
    nt.links.new(base.outputs["Color"], p.inputs["Base Color"])
    nrm_p = os.path.join(tex_dir, name + "_normal.png")
    if os.path.exists(nrm_p):
        nimg = nt.nodes.new("ShaderNodeTexImage")
        nimg.image = bpy.data.images.load(nrm_p, check_existing=True)
        nimg.image.colorspace_settings.name = 'Non-Color'
        nimg.location = (-760, -140)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.9
        nm.location = (-420, -140)
        nt.links.new(nimg.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    p.inputs["Roughness"].default_value = 0.74
    p.inputs["Metallic"].default_value = 0.0
    try:
        p.inputs["Specular IOR Level"].default_value = 0.32
    except Exception:
        pass
    return m


def build(name, src=None, tex_dir=None):
    src = src or SRC
    tex_dir = tex_dir or src
    d = json.load(open(os.path.join(src, name + "_parts.json"), encoding="utf-8"))
    arm = _armature(d, name)
    mat = _material(name, tex_dir)
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.get(name + "_root") or bpy.data.objects.new(name + "_root", None)
    root.empty_display_size = 0.04
    meshes = []
    for side in ("r", "l"):
        ob = _mesh(d, side)
        ob.data.materials.append(mat)
        col.objects.link(ob)
        ob.parent = arm
        md = ob.modifiers.new("Armature", 'ARMATURE')
        md.object = arm
        meshes.append(ob)
    for o in (root, arm):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    arm.parent = root
    bpy.context.view_layer.update()
    return arm, meshes, d


def curl(arm, side, fingers=1.0, thumb=0.6, spread=0.0):
    """сжать пальцы (0..1): проверка весов и демонстрация"""
    for f in FING:
        amt = thumb if f == "thumb" else fingers
        ang = (0.55, 0.75, 0.6) if f == "thumb" else (1.25, 1.55, 1.0)
        for k in (1, 2, 3):
            pb = arm.pose.bones.get(f"{f}{k}_{side}")
            if not pb:
                continue
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = Quaternion((1, 0, 0), -ang[k - 1] * amt)


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
                              export_yup=True, export_image_format='AUTO', export_tangents=True, export_def_bones=False)
    arm.parent = keep
    return round(os.path.getsize(out) / 2 ** 20, 2)


def go(name, seg=75, tick=0.04):
    """запись: сетка -> каркас -> кости -> текстура -> пальцы сжимаются -> glb + blend"""
    import cs2_tools as T
    T.new_scene()
    st = {"name": name, "n": 0, "step": 0, "k": 0, "done": False, "err": None, "state": "mesh", "t0": time.time(), "yaw": 200.0, "pending": False}
    NS["cs2_arms"] = st
    st["mode"] = T.shot_mode_detect()
    out = os.path.join(T.FOOTAGE, "build", name + ("_hd" if st["mode"] == "view" else ""))
    os.makedirs(out, exist_ok=True)
    arm, meshes, d = build(name)
    mat = meshes[0].data.materials[0]
    clay = bpy.data.materials.new("clay")
    clay.diffuse_color = (0.42, 0.40, 0.38, 1)
    for o in meshes:
        o.data.materials.clear()
        o.data.materials.append(clay)
    arm.hide_set(True)
    T.setup_viewport('SOLID')
    sp = T.view3d()[1].spaces.active
    center, distv = Vector((0, -0.06, 0)), 1.25

    def stage(i):
        if i == 1:
            sp.overlay.show_wireframes = True
            st["state"] = "wire"
        elif i == 2:
            sp.overlay.show_wireframes = False
            arm.hide_set(False)
            arm.show_in_front = True
            arm.data.display_type = 'STICK'
            st["state"] = "rig"
        elif i == 3:
            arm.hide_set(True)
            for o in meshes:
                o.data.materials.clear()
                o.data.materials.append(mat)
            sp.shading.type = 'MATERIAL'
            st["state"] = "material"
        elif i == 4:
            st["state"] = "fingers"
        elif i == 5:
            for pb in arm.pose.bones:
                pb.rotation_quaternion = (1, 0, 0, 0)
            sp.shading.type = 'SOLID'
            st["glb_mb"] = export(name, os.path.join(T.MODELS, "chars", name + ".glb"))
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
            if st["k"] >= seg * (2.0 if st["step"] == 4 else 1.0):
                st["k"] = 0
                st["step"] += 1
                stage(st["step"])
                if st["done"]:
                    return None
            if st["step"] == 4:
                a = 0.5 - 0.5 * math.cos(st["k"] / (seg * 2.0) * 4 * math.pi)
                curl(arm, "r", a, a * 0.7)
                curl(arm, "l", a, a * 0.7)
            st["yaw"] += 1.0
            T.set_view(center, distv, st["yaw"], 28.0)
            st["pending"] = True
        except Exception:
            import traceback
            st["err"] = traceback.format_exc()
            st["done"] = True
            return None
        return tick

    bpy.app.timers.register(_tick, first_interval=0.4)
    return {"name": name, "frames_dir": out, "verts": len(d["verts"]), "mode": st["mode"]}


def status():
    st = NS.get("cs2_arms")
    if not st:
        return None
    return {k: st.get(k) for k in ("name", "state", "step", "n", "done", "err", "sec", "glb_mb", "mode")}
