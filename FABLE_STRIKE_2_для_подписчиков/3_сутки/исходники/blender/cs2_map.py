"""FABLE STRIKE 2 — карта «КАСБА» в Blender. Куски сетки приходят из maps/kasbah_parts.json (генератор map_gen.py),
здесь: материалы из текстур assets/tex, сборка по кускам (с записью), склейка по участкам, экспорт glb.
MP.build() — сразу; MP.go() — по шагам с записью кадров; MP.status()."""
import bpy, os, sys, json, math, time
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
NS = bpy.app.driver_namespace
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "maps")
TEX = os.path.join(ROOT, "assets", "tex")
OUT = os.path.join(ROOT, "assets", "maps")

TEXMATS = {"plaster_white": 0.9, "plaster_ochre": 0.9, "plaster_damaged": 0.92, "mud_brick": 0.95, "sandstone_blocks": 0.88, "cobblestone": 0.85, "concrete": 0.9,
           "dirt_road": 0.97, "sand": 0.97, "floor_tiles": 0.55, "wood_planks": 0.8, "wood_dark": 0.75, "metal_sheet": 0.6, "fabric_stripes": 0.95}
FLAT = {"terracotta": ((0.46, 0.17, 0.10), 0.85, 0), "roof": ((0.56, 0.47, 0.36), 0.95, 0), "dark": ((0.012, 0.012, 0.015), 0.6, 0),
        "metal_dark": ((0.06, 0.06, 0.065), 0.5, 0.8), "metal_light": ((0.55, 0.56, 0.58), 0.45, 0.7),
        "paint_teal": ((0.07, 0.30, 0.30), 0.7, 0), "paint_green": ((0.12, 0.28, 0.13), 0.7, 0), "paint_blue": ((0.08, 0.19, 0.38), 0.7, 0),
        "paint_red": ((0.38, 0.09, 0.06), 0.7, 0), "barrel_red": ((0.40, 0.08, 0.05), 0.55, 0.3), "barrel_blue": ((0.07, 0.17, 0.36), 0.55, 0.3),
        "fruit_orange": ((0.85, 0.38, 0.05), 0.6, 0), "fruit_red": ((0.6, 0.06, 0.05), 0.5, 0), "fruit_green": ((0.25, 0.45, 0.08), 0.6, 0),
        "spice": ((0.7, 0.42, 0.05), 0.9, 0), "palm_trunk": ((0.24, 0.17, 0.11), 0.95, 0), "palm_leaf": ((0.10, 0.24, 0.06), 0.7, 0),
        "flower": ((0.62, 0.04, 0.28), 0.7, 0), "rope": ((0.4, 0.35, 0.27), 0.9, 0), "cloth_white": ((0.78, 0.76, 0.70), 0.95, 0),
        "carpet": ((0.36, 0.06, 0.06), 0.97, 0), "carpet_blue": ((0.08, 0.14, 0.30), 0.97, 0), "lamp_glow": ((1.0, 0.72, 0.38), 0.4, 0)}


def material(name):
    m = bpy.data.materials.get("map_" + name)
    if m:
        return m
    m = bpy.data.materials.new("map_" + name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    if name in TEXMATS:
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(os.path.join(TEX, name + "_base.jpg"), check_existing=True)
        img.location = (-520, 260)
        nt.links.new(img.outputs["Color"], p.inputs["Base Color"])
        np_ = os.path.join(TEX, name + "_normal.jpg")
        if os.path.exists(np_):
            ni = nt.nodes.new("ShaderNodeTexImage")
            ni.image = bpy.data.images.load(np_, check_existing=True)
            ni.image.colorspace_settings.name = 'Non-Color'
            ni.location = (-760, -140)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (-420, -140)
            nt.links.new(ni.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
        p.inputs["Roughness"].default_value = TEXMATS[name]
        if name == "metal_sheet":
            p.inputs["Metallic"].default_value = 0.5
        m.diffuse_color = (0.6, 0.5, 0.38, 1)
    else:
        col, rough, metal = FLAT.get(name, ((0.5, 0.5, 0.5), 0.8, 0))
        p.inputs["Base Color"].default_value = (*col, 1)
        p.inputs["Roughness"].default_value = rough
        p.inputs["Metallic"].default_value = metal
        m.diffuse_color = (*col, 1)
        if name == "lamp_glow":
            p.inputs["Emission Color"].default_value = (1.0, 0.62, 0.28, 1)
            p.inputs["Emission Strength"].default_value = 6.0
    try:
        p.inputs["Specular IOR Level"].default_value = 0.25
    except Exception:
        pass
    return m


def make_piece(pc, col):
    me = bpy.data.meshes.new(pc["name"])
    me.from_pydata(pc["v"], [], pc["f"])
    names = sorted(set(pc["m"]))
    idx = {n: i for i, n in enumerate(names)}
    for n in names:
        me.materials.append(material(n))
    uvl = me.uv_layers.new(name="UVMap")
    k = 0
    for fi, poly in enumerate(me.polygons):
        poly.material_index = idx[pc["m"][fi]]
        uv = pc["uv"][fi]
        for j in range(poly.loop_total):
            uvl.data[poly.loop_start + j].uv = uv[j]
    me.update()
    ob = bpy.data.objects.new(pc["name"], me)
    ob["cs2_stage"] = pc["stage"]
    col.objects.link(ob)
    return ob


def load():
    return json.load(open(os.path.join(SRC, "kasbah_parts.json"), encoding="utf-8"))


def collection(name="kasbah"):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(col)
    return col


def build():
    d = load()
    col = collection()
    return [make_piece(pc, col) for pc in d["pieces"]]


def join_chunks(cell=24.0):
    """склеить куски по участкам (меньше объектов в игре)"""
    col = collection()
    groups = {}
    for o in list(col.objects):
        if o.type != 'MESH':
            continue
        if o.name.startswith("ground"):
            key = "ground"
        else:
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            cx = sum(p.x for p in bb) / 8
            cy = sum(p.y for p in bb) / 8
            key = f"chunk_{int(cx // cell)}_{int(cy // cell)}"
        groups.setdefault(key, []).append(o)
    out = []
    for key, obs in groups.items():
        for o in [o_ for o_ in bpy.context.view_layer.objects if o_]:
            o.select_set(False)
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            with bpy.context.temp_override(active_object=obs[0], selected_editable_objects=obs, selected_objects=obs):
                bpy.ops.object.join()
        obs[0].name = key
        obs[0].data.name = key
        out.append(obs[0])
    return out


def export(path=None):
    path = path or os.path.join(OUT, "kasbah.glb")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    col = collection()
    for o in [o_ for o_ in bpy.context.view_layer.objects if o_]:
        o.select_set(o.name in col.objects and o.type == 'MESH')
    bpy.context.view_layer.objects.active = [o for o in col.objects if o.type == 'MESH'][0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_animations=False, export_yup=True,
                              export_image_format='JPEG', export_jpeg_quality=90, export_tangents=True, export_apply=True)
    return round(os.path.getsize(path) / 2 ** 20, 2)


def go(per_tick=2, tick=0.04, orbit=0.35):
    """запись: земля -> дома растут волной от базы атаки -> проходы, арки -> пропсы -> материалы -> glb"""
    import cs2_tools as T
    T.new_scene()
    st = {"n": 0, "i": 0, "done": False, "err": None, "state": "build", "t0": time.time(), "yaw": 215.0, "pending": False, "tail": 0}
    NS["cs2_map"] = st
    st["mode"] = T.shot_mode_detect()
    out = os.path.join(T.FOOTAGE, "build", "map_kasbah" + ("_hd" if st["mode"] == "view" else ""))
    os.makedirs(out, exist_ok=True)
    d = load()
    col = collection()
    order = {"земля": 0, "дома": 1, "крытые проходы": 2, "арки": 3, "пропсы": 4}

    def key(pc):
        if pc["stage"] == "дома" and pc["v"]:
            x = sum(v[0] for v in pc["v"][:8]) / 8
            y = sum(v[1] for v in pc["v"][:8]) / 8
            return (1, math.hypot(x - 14, y - 11))
        return (order.get(pc["stage"], 5), 0)
    pcs = sorted(d["pieces"], key=key)
    st["total"] = len(pcs)
    T.setup_viewport('SOLID')
    sp = T.view3d()[1].spaces.active
    try:
        sp.shading.color_type = 'TEXTURE'
        sp.shading.light = 'STUDIO'
        sp.shading.show_shadows = True
        sp.shading.show_cavity = True
    except Exception:
        pass
    center, dist = Vector((48, 40, 0)), 150.0

    def _tick():
        try:
            if st["pending"]:
                T._shot(os.path.join(out, f"f_{st['n']:06d}.png"))
                st["n"] += 1
                st["pending"] = False
            if st["i"] < len(pcs):
                for _ in range(per_tick if pcs[st["i"]]["stage"] == "дома" else 1):
                    if st["i"] < len(pcs):
                        make_piece(pcs[st["i"]], col)
                        st["i"] += 1
            else:
                st["tail"] += 1
                if st["tail"] == 60:
                    sp.shading.type = 'MATERIAL'
                    st["state"] = "material"
                if st["tail"] > 240:
                    sp.shading.type = 'SOLID'
                    join_chunks()
                    st["glb_mb"] = export()
                    st["blend"] = T.save_blend("map_kasbah")
                    st["state"] = "done"
                    st["sec"] = round(time.time() - st["t0"], 1)
                    st["done"] = True
                    return None
            st["yaw"] += orbit
            T.set_view(center, dist, st["yaw"], 38.0)
            st["pending"] = True
        except Exception:
            import traceback
            st["err"] = traceback.format_exc()
            st["done"] = True
            return None
        return tick

    bpy.app.timers.register(_tick, first_interval=0.4)
    return {"pieces": len(pcs), "frames_dir": out, "mode": st["mode"]}


def status():
    st = NS.get("cs2_map")
    if not st:
        return None
    return {k: st.get(k) for k in ("state", "i", "total", "n", "done", "err", "sec", "glb_mb", "mode")}
