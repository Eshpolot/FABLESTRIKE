"""FABLE STRIKE 2 — инструменты Blender (оружие и окружение кодом, с записью).

Масштаб — метры, Z вверх, ствол смотрит в +Y (в Godot это -Z).
Ассет = коллекция <имя> + корневой Empty <имя>_root. Подвижные детали: mv_*.
Геометрия деталей приходит из json (трассировка листа-концепта), сборка идёт
по одной детали с записью кадров окна.
"""
import bpy, bmesh, math, os, time, json, subprocess
from mathutils import Vector, Euler, Matrix, Quaternion

DL = r"C:\Users\User\Downloads"
ROOT = os.path.join(DL, "CS2_FABLE", "сутки")
MODELS = os.path.join(ROOT, "assets", "models")
BLENDS = os.path.join(ROOT, "blender")
FOOTAGE = os.path.join(DL, "cs2_материалы", "footage")
NS = bpy.app.driver_namespace

VIEW_COL = {  # цвет в Solid-вьюпорте: (rgb, metallic, roughness)
    "steel": ((0.115, 0.12, 0.13), 0.9, 0.42),
    "steel_bright": ((0.36, 0.36, 0.37), 0.9, 0.3),
    "wood": ((0.36, 0.15, 0.06), 0.0, 0.5),
    "black": ((0.012, 0.012, 0.014), 0.0, 0.9),
    "rubber": ((0.035, 0.035, 0.038), 0.0, 0.85),
    "polymer": ((0.05, 0.052, 0.055), 0.0, 0.6),
    "alu": ((0.085, 0.088, 0.095), 0.8, 0.5),
    "nickel": ((0.55, 0.55, 0.56), 0.9, 0.35),
    "paint_olive": ((0.13, 0.15, 0.07), 0.1, 0.6),
    "paint_white": ((0.62, 0.62, 0.58), 0.1, 0.55),
    "paint_grey": ((0.10, 0.105, 0.11), 0.3, 0.55),
    "paint_green": ((0.22, 0.27, 0.10), 0.1, 0.6),
    "paint_red": ((0.45, 0.05, 0.03), 0.1, 0.5),
    "paint_tan": ((0.42, 0.34, 0.22), 0.1, 0.6),
    "amber": ((0.25, 0.10, 0.02), 0.3, 0.1),
    "cloth": ((0.55, 0.50, 0.42), 0.0, 0.9),
    "blade": ((0.42, 0.42, 0.43), 1.0, 0.3),
    "tan": ((0.45, 0.36, 0.24), 0.0, 0.6),
    "green": ((0.16, 0.2, 0.12), 0.0, 0.6),
    "brass": ((0.6, 0.45, 0.18), 1.0, 0.35),
    "glass": ((0.05, 0.12, 0.16), 0.2, 0.05),
    "red": ((0.6, 0.05, 0.03), 0.0, 0.5),
}


def vmat(kind, prefix=""):
    """простой материал для этапа сборки (цвет вьюпорта + Principled)"""
    name = prefix + kind
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        col, metal, rough = VIEW_COL.get(kind, ((0.5, 0.5, 0.5), 0.0, 0.5))
        p = m.node_tree.nodes.get("Principled BSDF")
        p.inputs["Base Color"].default_value = (*col, 1)
        p.inputs["Metallic"].default_value = metal
        p.inputs["Roughness"].default_value = rough
        m.diffuse_color = (*col, 1)
        m.metallic = metal
        m.roughness = rough
        m["cs2_kind"] = kind
    return m


# ---------------------------------------------------------------- коллекции
def new_asset(name, slot=(0, 0, 0), category=None):
    parent = bpy.context.scene.collection
    if category:
        cat = bpy.data.collections.get(category)
        if cat is None:
            cat = bpy.data.collections.new(category)
            bpy.context.scene.collection.children.link(cat)
        parent = cat
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        parent.children.link(col)
    root = bpy.data.objects.get(name + "_root")
    if root is None:
        root = bpy.data.objects.new(name + "_root", None)
        root.empty_display_type = 'PLAIN_AXES'
        root.empty_display_size = 0.05
        col.objects.link(root)
    root.location = slot
    return col, root


def asset_objects(name):
    col = bpy.data.collections.get(name)
    return list(col.all_objects) if col else []


def add_part(asset, pname, p, col, root, sharp=38.0):
    me = bpy.data.meshes.new(pname)
    me.from_pydata(p["v"], [], p["f"])
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    except Exception:
        pass
    me.materials.append(vmat(p["mat"]))
    ob = bpy.data.objects.new(pname, me)
    col.objects.link(ob)
    ob.parent = root
    cuts = []
    for i, c in enumerate(p.get("cut") or []):
        cme = bpy.data.meshes.new(pname + "_cut")
        cme.from_pydata(c["v"], [], c["f"])
        cbm = bmesh.new()
        cbm.from_mesh(cme)
        bmesh.ops.recalc_face_normals(cbm, faces=cbm.faces)
        cbm.to_mesh(cme)
        cbm.free()
        cob = bpy.data.objects.new(pname + "_cut%d" % i, cme)
        col.objects.link(cob)
        cob.parent = root
        md = ob.modifiers.new("cut%d" % i, 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.solver = 'EXACT'
        md.object = cob
        cuts.append(cob)
    if cuts:
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        ob.data = me2
        bpy.data.meshes.remove(me)
        me = me2
        me.name = pname
        for cob in cuts:
            cm = cob.data
            bpy.data.objects.remove(cob, do_unlink=True)
            bpy.data.meshes.remove(cm)
        me.shade_smooth()
        try:
            me.set_sharp_from_angle(angle=math.radians(sharp))
        except Exception:
            pass
    ob["cs2_mat"] = p["mat"]
    if p.get("mv"):
        ob["cs2_mv"] = p["mv"]
    if p.get("stage"):
        ob["cs2_stage"] = p["stage"]
    md = ob.modifiers.new("WN", 'WEIGHTED_NORMAL')
    md.keep_sharp = True
    md.weight = 60
    return ob


# ---------------------------------------------------------------- вьюпорт
def view3d():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D':
                return w, a
    return None, None


def setup_viewport(mode='SOLID'):
    w, a = view3d()
    if a is None:
        return False
    sp = a.spaces.active
    sh = sp.shading
    sh.type = mode
    if mode == 'SOLID':
        sh.light = 'STUDIO'
        sh.color_type = 'MATERIAL'
        sh.show_cavity = True
        sh.cavity_type = 'BOTH'
        sh.curvature_ridge_factor = 1.2
        sh.curvature_valley_factor = 1.0
        sh.show_shadows = True
        sh.shadow_intensity = 0.5
        sh.show_object_outline = False
        sh.background_type = 'VIEWPORT'
        sh.background_color = (0.014, 0.016, 0.021)
        sh.show_specular_highlight = True
    sp.overlay.show_relationship_lines = False
    sp.overlay.show_extras = False
    sp.overlay.show_floor = False
    sp.overlay.show_axis_x = False
    sp.overlay.show_axis_y = False
    sp.overlay.show_cursor = False
    sp.overlay.show_object_origins = False
    sp.clip_start = 0.005
    sp.clip_end = 500
    sp.lens = 70
    return True


def set_view(center, dist, yaw=40.0, pitch=18.0, persp=True):
    """камера вьюпорта: yaw — вокруг Z (0 = смотрим вдоль +Y), pitch — вверх"""
    w, a = view3d()
    if a is None:
        return
    r3d = a.spaces.active.region_3d
    q = Euler((math.radians(90 - pitch), 0, math.radians(yaw)), 'XYZ').to_quaternion()
    if NS.get("cs2_shot_mode") == 'view':
        # окно маленькое: снимаем через камеру 16:9, кадр не зависит от размера окна
        cam = bpy.data.objects.get("cs2_viewcam")
        if cam is None:
            cd = bpy.data.cameras.new("cs2_viewcam")
            cd.lens = 35
            cd.sensor_width = 36
            cd.clip_start = 0.005
            cd.clip_end = 500
            cd.passepartout_alpha = 1.0
            cam = bpy.data.objects.new("cs2_viewcam", cd)
            bpy.context.scene.collection.objects.link(cam)
        sc = bpy.context.scene
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 100
        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = q
        cam.location = Vector(center) + q @ Vector((0, 0, dist))
        a.spaces.active.overlay.show_extras = False
        if r3d.view_perspective != 'CAMERA':
            r3d.view_perspective = 'CAMERA'
        return
    r3d.view_rotation = q
    r3d.view_perspective = 'PERSP' if persp else 'ORTHO'
    r3d.view_location = Vector(center)
    r3d.view_distance = dist


def _win():
    wm = bpy.context.window_manager
    win = wm.windows[0]
    for w in wm.windows:
        if any(a.type == 'VIEW_3D' for a in w.screen.areas):
            win = w
            break
    return win


def _shot_window(path):
    win = _win()
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=path, check_existing=False)


def _shot_view(path):
    """вид вьюпорта без интерфейса (работает и при свёрнутом окне)"""
    w, a = view3d()
    reg = [r for r in a.regions if r.type == 'WINDOW'][0]
    sc = bpy.context.scene
    keep = (sc.render.filepath, sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 100
    st = sc.render.image_settings
    try:
        st.media_type = 'IMAGE'
    except Exception:
        pass
    st.file_format = 'JPEG'
    st.quality = 92
    try:
        sc.display.render_aa = '5'
    except Exception:
        pass
    sc.render.filepath = path
    with bpy.context.temp_override(window=w, screen=w.screen, area=a, region=reg):
        bpy.ops.render.opengl(write_still=True, view_context=True)
    sc.render.filepath, sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = keep


def shot_mode_detect():
    """'window' — кадр всего окна Blender; 'view' — только вьюпорт (если окно свёрнуто и кадр чёрный)."""
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "cs2_probe.png")
    mode = 'view'
    win = _win()
    NS["cs2_win_size"] = (win.width, win.height)
    if win.width < 1600 or win.height < 880:      # окно маленькое -> кадры вьюпорта 1920x1080 без интерфейса
        NS["cs2_shot_mode"] = mode
        return mode
    try:
        _shot_window(p)
        im = bpy.data.images.load(p, check_existing=False)
        px = list(im.pixels[0:400000])
        vals = [px[i] + px[i + 1] + px[i + 2] for i in range(0, len(px) - 3, 4 * 97)]
        mean = sum(vals) / max(1, len(vals)) / 3
        bpy.data.images.remove(im)
        NS["cs2_shot_mean"] = mean
        if mean > 0.01:
            mode = 'window'
    except Exception as e:
        NS["cs2_shot_err"] = repr(e)
    NS["cs2_shot_mode"] = mode
    return mode


def _shot(path):
    if NS.get("cs2_shot_mode", "window") == 'window':
        _shot_window(path)
    else:
        _shot_view(os.path.splitext(path)[0] + ".jpg")


# ---------------------------------------------------------------- фоновая запись (каждые N секунд)
def rec_start(interval=2.0, sub="blender_timelapse"):
    out = os.path.join(FOOTAGE, sub)
    os.makedirs(out, exist_ok=True)
    NS["cs2_rec_dir"] = out
    NS["cs2_rec_on"] = True
    NS["cs2_rec_interval"] = interval
    NS.setdefault("cs2_rec_n", 0)
    shot_mode_detect()

    def _cap():
        try:
            if not NS.get("cs2_build_busy"):
                n = NS.get("cs2_rec_n", 0)
                _shot(os.path.join(NS["cs2_rec_dir"], time.strftime("%Y%m%d_%H%M%S") + f"_{n:06d}.png"))
                NS["cs2_rec_n"] = n + 1
        except Exception as e:
            NS["cs2_rec_err"] = repr(e)
        return NS.get("cs2_rec_interval", 2.0) if NS.get("cs2_rec_on") else None

    old = NS.get("cs2_rec_fn")
    if old and bpy.app.timers.is_registered(old):
        bpy.app.timers.unregister(old)
    bpy.app.timers.register(_cap, first_interval=0.5, persistent=True)
    NS["cs2_rec_fn"] = _cap
    return out


def rec_status():
    fn = NS.get("cs2_rec_fn")
    return {"on": bool(NS.get("cs2_rec_on")), "registered": bool(fn and bpy.app.timers.is_registered(fn)),
            "frames": NS.get("cs2_rec_n", 0), "err": NS.get("cs2_rec_err")}


def rec_stop():
    NS["cs2_rec_on"] = False
    fn = NS.get("cs2_rec_fn")
    if fn and bpy.app.timers.is_registered(fn):
        bpy.app.timers.unregister(fn)


# ---------------------------------------------------------------- сборка по одной детали с записью
def build_staged(json_path, slot=(0, 0, 0), category="weapons", fpp=4, orbit=1.2, tail=90,
                 yaw0=35.0, pitch=14.0, zoom=1.15, sub=None, tick=0.04):
    """Собирает ассет из json по одной детали. На каждую деталь fpp кадров окна, камера
    медленно облетает модель. В конце tail кадров облёта готовой модели.
    Кадры: footage/build/<имя>/f_000001.png. Состояние: NS['cs2_build']."""
    d = json.load(open(json_path, encoding="utf-8"))
    name = d["name"]
    col, root = new_asset(name, slot, category)
    for o in list(col.objects):
        if o != root:
            bpy.data.objects.remove(o, do_unlink=True)
    out = os.path.join(FOOTAGE, "build", sub or name)
    os.makedirs(out, exist_ok=True)
    allv = [v for n in d["order"] for v in d["parts"][n]["v"]]
    mn = Vector((min(v[0] for v in allv), min(v[1] for v in allv), min(v[2] for v in allv)))
    mx = Vector((max(v[0] for v in allv), max(v[1] for v in allv), max(v[2] for v in allv)))
    center = (mn + mx) / 2 + Vector(slot)
    radius = (mx - mn).length / 2
    st = {"name": name, "i": 0, "j": 0, "n": 0, "tail": tail, "done": False, "err": None, "out": out,
          "yaw": yaw0, "total": len(d["order"]), "t0": time.time(), "pending": False}
    NS["cs2_build"] = st
    NS["cs2_build_busy"] = True
    st["mode"] = shot_mode_detect()
    setup_viewport('SOLID')
    set_view(center, radius * 2 * zoom, st["yaw"], pitch)

    def _tick():
        try:
            if st["pending"]:
                _shot(os.path.join(out, f"f_{st['n']:06d}.png"))
                st["n"] += 1
                st["pending"] = False
            if st["i"] < st["total"]:
                if st["j"] == 0:
                    pn = d["order"][st["i"]]
                    add_part(name, pn, d["parts"][pn], col, root)
                st["j"] += 1
                if st["j"] >= fpp:
                    st["j"] = 0
                    st["i"] += 1
            elif st["tail"] > 0:
                st["tail"] -= 1
            else:
                for en, loc in d.get("empties", {}).items():
                    e = bpy.data.objects.new(en, None)
                    e.empty_display_type = 'ARROWS'
                    e.empty_display_size = 0.02
                    e.location = loc
                    col.objects.link(e)
                    e.parent = root
                root["cs2_pivots"] = json.dumps(d.get("pivots", {}))
                st["done"] = True
                st["sec"] = round(time.time() - st["t0"], 1)
                NS["cs2_build_busy"] = False
                return None
            st["yaw"] += orbit
            set_view(center, radius * 2 * zoom, st["yaw"], pitch)
            st["pending"] = True
        except Exception as e:
            import traceback
            st["err"] = traceback.format_exc()
            st["done"] = True
            NS["cs2_build_busy"] = False
            return None
        return tick

    bpy.app.timers.register(_tick, first_interval=0.3)
    return {"name": name, "parts": st["total"], "frames_dir": out, "radius": round(radius, 3)}


def build_status():
    st = NS.get("cs2_build")
    if not st:
        return None
    return {k: st.get(k) for k in ("name", "i", "total", "n", "done", "err", "sec", "out", "mode")}


def stats(name):
    dg = bpy.context.evaluated_depsgraph_get()
    tris = parts = 0
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in asset_objects(name):
        if o.type == 'MESH':
            parts += 1
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            ev.to_mesh_clear()
            for c in o.bound_box:
                wc = o.matrix_world @ Vector(c)
                mn = Vector(map(min, mn, wc))
                mx = Vector(map(max, mx, wc))
    return {"tris": tris, "parts": parts, "size_m": tuple(round(v, 3) for v in (mx - mn)) if parts else None}


def save_blend(fname):
    os.makedirs(BLENDS, exist_ok=True)
    path = os.path.join(BLENDS, fname + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    return path


# ---------------------------------------------------------------- студия и кадры
def _bbox(name):
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    bpy.context.view_layer.update()
    for o in asset_objects(name):
        if o.type == 'MESH':
            for c in o.bound_box:
                wc = o.matrix_world @ Vector(c)
                mn = Vector(map(min, mn, wc))
                mx = Vector(map(max, mx, wc))
    return mn, mx


def studio(name, drop=0.30, backdrop=(0.012, 0.013, 0.016), power=0.16):
    """Студия вокруг ассета: циклорама, 4 источника, камера сбоку (+X, ствол вправо), пивот для вращения.
    Всё лежит в коллекции «studio» (в игру не уходит)."""
    sc = bpy.context.scene
    col = bpy.data.collections.get("studio")
    if col is not None:
        for o in list(col.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        col = bpy.data.collections.new("studio")
        sc.collection.children.link(col)
    mn, mx = _bbox(name)
    C = (mn + mx) / 2
    R = (mx - mn).length / 2
    zf = mn.z - drop * R * 2
    # циклорама: пол -> дуга -> стена (за моделью, со стороны -X)
    prof = []
    rad = R * 2.2
    xb = C.x - R * 2.6
    for i in range(0, 13):
        a = math.radians(90 * i / 12)
        prof.append((xb + rad - rad * math.sin(a), zf + rad - rad * math.cos(a)))
    pts = [(C.x + R * 9, zf)] + [(xb + rad, zf)] + prof[1:] + [(xb, zf + R * 9)]
    verts, faces = [], []
    for j, yy in enumerate((C.y - R * 9, C.y + R * 9)):
        for (x, z) in pts:
            verts.append((x, yy, z))
    n = len(pts)
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    me = bpy.data.meshes.new("studio_cyc")
    me.from_pydata(verts, [], faces)
    me.shade_smooth()
    cyc = bpy.data.objects.new("studio_cyc", me)
    col.objects.link(cyc)
    m = bpy.data.materials.get("studio_backdrop") or bpy.data.materials.new("studio_backdrop")
    try:
        m.use_nodes = True
    except Exception:
        pass
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*backdrop, 1)
    p.inputs["Roughness"].default_value = 0.55
    me.materials.append(m)
    w = bpy.data.worlds.get("studio_world") or bpy.data.worlds.new("studio_world")
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.02, 0.022, 0.028, 1)
    bg.inputs[1].default_value = 0.25
    sc.world = w

    tgt = bpy.data.objects.new("studio_target", None)
    col.objects.link(tgt)
    tgt.location = C

    def light(nm, energy, loc, size, size_y=None, color=(1, 1, 1)):
        ld = bpy.data.lights.new(nm, 'AREA')
        ld.energy = energy * power * (R / 0.46) ** 2
        ld.color = color
        ld.size = size * R
        if size_y:
            ld.shape = 'RECTANGLE'
            ld.size_y = size_y * R
        ob = bpy.data.objects.new(nm, ld)
        col.objects.link(ob)
        ob.location = C + Vector(loc) * R
        c = ob.constraints.new('TRACK_TO')
        c.target = tgt
        c.track_axis = 'TRACK_NEGATIVE_Z'
        c.up_axis = 'UP_Y'
        return ob
    light("studio_key", 420, (3.2, -2.2, 3.0), 3.0, 2.0, (1.0, 0.96, 0.90))
    light("studio_rim", 520, (-2.0, 2.6, 2.4), 2.4, 1.2, (0.72, 0.84, 1.0))
    light("studio_fill", 90, (3.0, 2.8, -0.6), 3.5, 2.5, (0.9, 0.95, 1.0))
    light("studio_strip", 260, (1.2, 0.0, 3.4), 5.0, 0.35, (1.0, 1.0, 1.0))

    piv = bpy.data.objects.new("studio_pivot", None)
    col.objects.link(piv)
    piv.location = C
    cd = bpy.data.cameras.get("studio_cam") or bpy.data.cameras.new("studio_cam")
    cd.lens = 85
    cd.clip_start = 0.01
    cam = bpy.data.objects.new("studio_cam", cd)
    col.objects.link(cam)
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    sc.camera = cam
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    NS["cs2_studio"] = {"C": tuple(C), "R": R}
    cam_set(8.0, 12.0, 1.0)
    return {"center": tuple(round(v, 3) for v in C), "radius": round(R, 3)}


def cam_set(yaw=8.0, pitch=12.0, zoom=1.0, look=None, lens=85):
    """камера студии: yaw 0 = строго сбоку (правый борт), + = заходим спереди; zoom>1 — ближе"""
    s = NS["cs2_studio"]
    C, R = Vector(s["C"]), s["R"]
    cam = bpy.data.objects["studio_cam"]
    cam.data.lens = lens
    sc = bpy.context.scene
    asp = sc.render.resolution_x / sc.render.resolution_y
    fov = 2 * math.atan(36 / (2 * lens))           # горизонтальный
    dist = (R * 1.08) / math.tan(fov / 2) / zoom
    y, p = math.radians(yaw), math.radians(pitch)
    cam.location = C + Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))) * dist
    bpy.data.objects["studio_target"].location = Vector(look) if look else C


def still(path, engine='CYCLES', spp=64, res=(1920, 1080), pct=100):
    sc = bpy.context.scene
    if engine == 'CYCLES':
        sc.render.engine = 'CYCLES'
        try:
            import cs2_mat
            cs2_mat._gpu()
        except Exception:
            pass
        sc.cycles.samples = spp
        sc.cycles.use_denoising = True
        try:
            sc.cycles.denoiser = 'OPTIX'
        except Exception:
            pass
    else:
        for eid in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try:
                sc.render.engine = eid
                break
            except Exception:
                pass
        try:
            sc.eevee.taa_render_samples = spp
            sc.eevee.use_raytracing = True
        except Exception:
            pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = pct
    st = sc.render.image_settings
    try:
        st.media_type = 'IMAGE'
    except Exception:
        pass
    st.file_format = 'PNG' if path.lower().endswith('.png') else 'JPEG'
    st.quality = 92
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return {"path": path, "sec": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- облёты (фоновый Blender, интерфейс не блокируется)
def turntable_queue(jobs, **opts):
    """jobs: [(blend_path, asset)]. Рендерит по очереди в фоновых Blender (по одному), кадры —
    footage/turntables/frames/<asset>_<режим>/f_0001.jpg; прерванный рендер продолжается с того же кадра."""
    import threading
    out_dir = os.path.join(FOOTAGE, "turntables")
    os.makedirs(out_dir, exist_ok=True)
    script = os.path.join(BLENDS, "cs2_turntable.py")
    exe = bpy.app.binary_path
    q = NS.setdefault("cs2_tt_q", [])
    q.extend(jobs)
    if NS.get("cs2_tt_running"):
        return {"queued": len(q)}

    def run():
        NS["cs2_tt_running"] = True
        try:
            while q:
                job = q.pop(0)
                blend, asset = job[0], job[1]
                NS["cs2_tt_now"] = asset
                args = dict(opts, asset=asset, out=out_dir)
                if len(job) > 2:
                    args.update(job[2])
                for attempt in range(3):
                    with open(os.path.join(out_dir, asset + "_log.txt"), "a", encoding="utf-8") as lf:
                        lf.write("\n==== start attempt %d ====\n" % attempt)
                        lf.flush()
                        rc = subprocess.call([exe, "-b", blend, "--python", script, "--", json.dumps(args)],
                                             stdout=lf, stderr=subprocess.STDOUT,
                                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                        lf.write("\n==== exit code %s ====\n" % rc)
                    if os.path.exists(os.path.join(out_dir, "frames", asset + ".done")):
                        break
        finally:
            NS["cs2_tt_running"] = False
            NS["cs2_tt_now"] = None

    threading.Thread(target=run, daemon=True).start()
    return {"queued": len(q), "started": True}


def turntable_status(asset=None):
    out_dir = os.path.join(FOOTAGE, "turntables")
    fr = os.path.join(out_dir, "frames")
    counts = {}
    if os.path.isdir(fr):
        for d in sorted(os.listdir(fr)):
            pth = os.path.join(fr, d)
            if os.path.isdir(pth):
                counts[d] = len(os.listdir(pth))
    return {"running": bool(NS.get("cs2_tt_running")), "now": NS.get("cs2_tt_now"), "queue": [j[1] for j in NS.get("cs2_tt_q", [])],
            "frames": counts}
