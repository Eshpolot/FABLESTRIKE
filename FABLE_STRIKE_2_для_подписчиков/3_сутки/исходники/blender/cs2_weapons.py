"""Рецепты материалов по стволам и конвейер после сборки: материалы -> проверка -> запекание -> glb -> облёт."""
import bpy, os, json
import cs2_tools as T, cs2_mat as M

TMP = os.path.join(T.DL, "cs2_bridge", "tmp")
WOOD_AK = dict(dark=(0.030, 0.009, 0.004), mid=(0.150, 0.043, 0.013), light=(0.285, 0.098, 0.030), raw=(0.40, 0.23, 0.11), ring_scale=5.0)


def _common(n):
    return {
        "steel": M.steel(n + "_steel", base_a=(0.034, 0.036, 0.041), base_b=(0.072, 0.074, 0.080), wear_amt=1.5),
        "steel_bright": M.steel(n + "_steel_bright", base_a=(0.20, 0.20, 0.205), base_b=(0.33, 0.33, 0.335), worn=(0.62, 0.61, 0.60),
                                rough0=0.30, dirt=(0.05, 0.045, 0.04)),
        "alu": M.steel(n + "_alu", base_a=(0.026, 0.027, 0.030), base_b=(0.050, 0.051, 0.055), worn=(0.50, 0.50, 0.51), rough0=0.52, wear_amt=1.25),
        "polymer": M.polymer(n + "_polymer", col=(0.014, 0.0145, 0.016), rough0=0.62),
        "nickel": M.steel(n + "_nickel", base_a=(0.30, 0.30, 0.31), base_b=(0.46, 0.46, 0.47), worn=(0.78, 0.77, 0.75), rough0=0.36,
                          wear_amt=0.9, dirt=(0.06, 0.055, 0.05)),
        "rubber": M.rubber(n + "_rubber"),
        "green": M.polymer(n + "_green", col=(0.070, 0.090, 0.040), rough0=0.62),
        "glass": M.flat(n + "_glass", (0.012, 0.028, 0.05), 0.06, 0.85),
        "black": M.flat(n + "_black", (0.004, 0.004, 0.004), 1.0),
        "paint_olive": M.steel(n + "_paint_olive", base_a=(0.075, 0.090, 0.040), base_b=(0.110, 0.125, 0.055), worn=(0.20, 0.19, 0.17), rough0=0.60,
                               wear_amt=1.3, dirt=(0.10, 0.075, 0.045), metal0=0.0, scratch=0.5),
        "paint_white": M.steel(n + "_paint_white", base_a=(0.50, 0.50, 0.46), base_b=(0.66, 0.66, 0.61), worn=(0.16, 0.15, 0.14), rough0=0.55,
                               wear_amt=1.3, dirt=(0.26, 0.15, 0.07), metal0=0.0, scratch=0.5),
        "paint_grey": M.steel(n + "_paint_grey", base_a=(0.040, 0.042, 0.045), base_b=(0.075, 0.077, 0.080), worn=(0.36, 0.35, 0.34), rough0=0.55,
                              wear_amt=1.4, dirt=(0.09, 0.075, 0.06), metal0=0.3, scratch=0.6),
        "paint_green": M.steel(n + "_paint_green", base_a=(0.11, 0.15, 0.05), base_b=(0.16, 0.20, 0.07), worn=(0.45, 0.45, 0.42), rough0=0.6,
                               wear_amt=1.0, dirt=(0.12, 0.09, 0.05), metal0=0.0, scratch=0.4),
        "paint_red": M.steel(n + "_paint_red", base_a=(0.30, 0.025, 0.015), base_b=(0.45, 0.04, 0.02), worn=(0.30, 0.29, 0.28), rough0=0.5,
                             wear_amt=1.2, metal0=0.0, scratch=0.5),
        "paint_tan": M.steel(n + "_paint_tan", base_a=(0.30, 0.24, 0.15), base_b=(0.42, 0.34, 0.22), worn=(0.30, 0.29, 0.28), rough0=0.6,
                             wear_amt=1.2, dirt=(0.12, 0.09, 0.05), metal0=0.0, scratch=0.5),
        "amber": M.flat(n + "_amber", (0.20, 0.075, 0.012), 0.08, 0.35),
        "brass": M.steel(n + "_brass", base_a=(0.42, 0.27, 0.07), base_b=(0.60, 0.42, 0.13), worn=(0.85, 0.66, 0.30), rough0=0.36,
                         wear_amt=1.0, dirt=(0.10, 0.07, 0.03)),
        "cloth": M.polymer(n + "_cloth", col=(0.36, 0.33, 0.27), rough0=0.92),
        "blade": M.steel(n + "_blade", base_a=(0.22, 0.22, 0.225), base_b=(0.36, 0.36, 0.365), worn=(0.70, 0.70, 0.69), rough0=0.32,
                         wear_amt=1.2, dirt=(0.05, 0.045, 0.04)),
    }


def mats(name):
    tb = _common(name)
    used = {o.get("cs2_mat") for o in T.asset_objects(name) if o.type == 'MESH'}
    if "wood" in used:
        tb["wood"] = M.wood(name + "_wood", **WOOD_AK)
    for kind in used:
        if kind and kind not in tb:          # неизвестный вид материала — ровный цвет из палитры вьюпорта
            col, metal, rough = T.VIEW_COL.get(kind, ((0.5, 0.5, 0.5), 0.0, 0.6))
            tb[kind] = M.flat(name + "_" + kind, col, rough, metal)
    n = M.assign(name, tb)
    if name == "ak":
        wdir = os.path.join(T.BLENDS, "weapons")
        img = bpy.data.images.load(os.path.join(wdir, "ak_checker.png"), check_existing=True)
        img.colorspace_settings.name = 'Non-Color'
        mp = json.load(open(os.path.join(wdir, "ak_checker.json")))
        wg = M.wood("ak_wood_grip", checker_img=img, checker_map=(mp["y0"], mp["y1"], mp["z0"], mp["z1"]), **WOOD_AK)
        g = bpy.data.objects["grip"]
        g.data.materials.clear()
        g.data.materials.append(wg)
    # неиспользуемые процедурные материалы убрать
    for m in list(bpy.data.materials):
        if m.users == 0 and m.name.startswith(name + "_"):
            bpy.data.materials.remove(m)
    return n


def preview(name, tag="p", views=((10, 10, 1.0, None), (25, 14, 2.2, None)), spp=64):
    d = os.path.join(TMP, name)
    os.makedirs(d, exist_ok=True)
    T.studio(name)
    out = []
    for i, (yaw, pitch, zoom, look) in enumerate(views):
        T.cam_set(yaw=yaw, pitch=pitch, zoom=zoom, look=look)
        out.append(T.still(os.path.join(d, f"{tag}{i}.jpg"), 'CYCLES', spp=spp, res=(1600, 900)))
    return out


def finish(name, res=2048, spp=48, turntable=True):
    made = M.finalize(name)
    M.unwrap(name)
    log = M.bake(name, res=res, spp=spp)
    M.pbr_material(name)
    exp = M.export_glb(name, "weapons")
    blend = T.save_blend("weapon_" + name)
    tt = T.turntable_queue([(blend, name)], frames=360, fps=60, spp=32) if turntable else None
    return {"made": made, "bake_s": log["total"], "export": exp, "blend": blend, "tt": tt}


def auto(name, res=2048, spp=48, views=((10, 10, 1.0, None), (28, 14, 1.9, None)), turntable=True, fix=None):
    """после сборки: материалы -> (правки fix(name)) -> запекание -> glb -> blend -> облёт в очередь -> два кадра запечённой модели"""
    bs = T.build_status()
    if not bs or bs.get("name") != name or not bs.get("done"):
        return {"wait": bs}
    if bs.get("err"):
        return {"build_err": bs["err"]}
    n = mats(name)
    if fix:
        fix(name)
    st = T.stats(name)
    r = finish(name, res=res, spp=spp, turntable=turntable)
    T.setup_viewport('MATERIAL')
    d = os.path.join(TMP, name)
    os.makedirs(d, exist_ok=True)
    T.studio(name)
    shots = []
    for i, (yaw, pitch, zoom, look) in enumerate(views):
        T.cam_set(yaw=yaw, pitch=pitch, zoom=zoom, look=look)
        shots.append(T.still(os.path.join(d, f"b{i}.jpg"), 'CYCLES', spp=64, res=(1600, 900))["path"])
    return {"parts": n, "stats": st, "made": r["made"], "bake_s": r["bake_s"], "glb_mb": r["export"]["mb"], "shots": shots,
            "frames": bs.get("n"), "tt": T.turntable_status()}


def start(name, fpp=5, tail=110, zoom=1.05):
    """чистая сцена + сборка по деталям с записью"""
    T.new_scene()
    T.setup_viewport('SOLID')
    return T.build_staged(os.path.join(T.BLENDS, "weapons", name + "_parts.json"), fpp=fpp, orbit=1.1, tail=tail, yaw0=20.0, pitch=13.0, zoom=zoom)


def auto_bg(name, **kw):
    """то же, что auto(), но в фоне по таймеру: вызов возвращается сразу; итог — auto_status()"""
    NS = bpy.app.driver_namespace
    NS["cs2_auto"] = {"name": name, "state": "wait"}

    def _run():
        st = NS["cs2_auto"]
        bs = T.build_status()
        if not bs or bs.get("name") != name or not bs.get("done"):
            return 1.0
        try:
            st["state"] = "run"
            st["result"] = auto(name, **kw)
            st["state"] = "done"
        except Exception:
            import traceback
            st["state"] = "error"
            st["err"] = traceback.format_exc()
        return None

    bpy.app.timers.register(_run, first_interval=0.5)
    return NS["cs2_auto"]


def go(name, fpp=5, tail=110, zoom=1.05, **kw):
    """всё одним вызовом: чистая сцена, сборка с записью, материалы, запекание, glb, blend, облёт, кадры"""
    d = os.path.join(TMP, name)
    if os.path.isdir(d):
        for f in ("b0.jpg", "b1.jpg"):
            p = os.path.join(d, f)
            if os.path.exists(p):
                os.remove(p)
    b = start(name, fpp=fpp, tail=tail, zoom=zoom)
    auto_bg(name, **kw)
    return b


def auto_status():
    st = bpy.app.driver_namespace.get("cs2_auto")
    if not st:
        return None
    out = {k: st.get(k) for k in ("name", "state", "err")}
    r = st.get("result")
    if r:
        out["result"] = {k: r[k] for k in r if k != "tt"}
    return out


def batch(items):
    """items: [(name, dict(fpp=..., tail=..., zoom=..., views=...))] — по очереди, без участия; итог — batch_status()"""
    NS = bpy.app.driver_namespace
    q = NS.setdefault("cs2_batch_q", [])
    q.extend(items)
    NS.setdefault("cs2_batch_done", {})
    if NS.get("cs2_batch_on"):
        return {"queued": [i[0] for i in q]}
    NS["cs2_batch_on"] = True
    NS["cs2_batch_cur"] = None

    def _tick():
        try:
            cur = NS.get("cs2_batch_cur")
            if cur is not None:
                st = NS.get("cs2_auto") or {}
                if st.get("name") == cur and st.get("state") in ("done", "error"):
                    r = st.get("result") or {}
                    NS["cs2_batch_done"][cur] = {"state": st.get("state"), "err": st.get("err"),
                                                 "glb_mb": r.get("glb_mb"), "tris": (r.get("stats") or {}).get("tris"),
                                                 "size": (r.get("stats") or {}).get("size_m"), "made": r.get("made")}
                    NS["cs2_batch_cur"] = None
                return 1.0
            if not q:
                NS["cs2_batch_on"] = False
                return None
            name, kw = q.pop(0)
            NS["cs2_batch_cur"] = name
            go(name, **kw)
        except Exception:
            import traceback
            NS["cs2_batch_err"] = traceback.format_exc()
            NS["cs2_batch_on"] = False
            return None
        return 1.0

    bpy.app.timers.register(_tick, first_interval=0.3)
    return {"queued": [i[0] for i in q]}


def batch_status():
    NS = bpy.app.driver_namespace
    return {"on": NS.get("cs2_batch_on"), "cur": NS.get("cs2_batch_cur"), "queue": [i[0] for i in NS.get("cs2_batch_q", [])],
            "done": NS.get("cs2_batch_done"), "err": NS.get("cs2_batch_err")}
