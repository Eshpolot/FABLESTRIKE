"""FABLE STRIKE 2 — материалы оружия: процедурные шейдеры (износ кромок, грязь в щелях,
волокна дерева), развёртка, запекание в текстуры (base / ORM / normal), финальный PBR-материал.
"""
import bpy, math, os, time, json
import numpy as np
from mathutils import Vector
import cs2_tools as T

NS = bpy.app.driver_namespace


# ---------------------------------------------------------------- конструктор узлов
class G:
    def __init__(self, nt):
        self.nt = nt
        self.col = 0
        self.row = 0

    def n(self, typ, **props):
        nd = self.nt.nodes.new(typ)
        nd.location = (-2200 + self.col * 190, 600 - self.row * 170)
        self.row += 1
        if self.row > 7:
            self.row = 0
            self.col += 1
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def put(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        elif v is not None:
            if isinstance(v, (tuple, list)) and len(v) == 3 and sock.type == 'RGBA':
                v = (*v, 1.0)
            sock.default_value = v

    def math(self, op, a, b=None, c=None, clamp=False):
        nd = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.put(nd.inputs[0], a)
        if b is not None:
            self.put(nd.inputs[1], b)
        if c is not None:
            self.put(nd.inputs[2], c)
        return nd.outputs[0]

    def mr(self, v, a, b, c=0.0, d=1.0):
        nd = self.n('ShaderNodeMapRange', clamp=True)
        self.put(nd.inputs[0], v)
        for i, x in enumerate((a, b, c, d)):
            nd.inputs[1 + i].default_value = x
        return nd.outputs[0]

    def mixc(self, fac, a, b, blend='MIX'):
        nd = self.n('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        self.put(nd.inputs[0], fac)
        self.put(nd.inputs[6], a)
        self.put(nd.inputs[7], b)
        return nd.outputs[2]

    def mixf(self, fac, a, b):
        nd = self.n('ShaderNodeMix', data_type='FLOAT')
        self.put(nd.inputs[0], fac)
        self.put(nd.inputs[2], a)
        self.put(nd.inputs[3], b)
        return nd.outputs[0]

    def ramp(self, fac, stops, interp='LINEAR'):
        nd = self.n('ShaderNodeValToRGB')
        cr = nd.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p
            e.color = (*c, 1.0) if len(c) == 3 else c
        self.put(nd.inputs[0], fac)
        return nd.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=0.55, dist=0.0):
        nd = self.n('ShaderNodeTexNoise')
        if vec is not None:
            self.nt.links.new(vec, nd.inputs["Vector"])
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        nd.inputs["Distortion"].default_value = dist
        return nd.outputs[0]

    def mapping(self, vec, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0)):
        nd = self.n('ShaderNodeMapping')
        self.nt.links.new(vec, nd.inputs["Vector"])
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Rotation"].default_value = rot
        nd.inputs["Location"].default_value = loc
        return nd.outputs[0]

    def rgb(self, c):
        nd = self.n('ShaderNodeRGB')
        nd.outputs[0].default_value = (*c, 1.0)
        return nd.outputs[0]


def _masks(g, bevel_r=0.003, ao_dist=0.012):
    """кромки (Edge), открытость (Open), щели (Cav) — работает в Cycles, запекается"""
    geo = g.n('ShaderNodeNewGeometry')
    bev = g.n('ShaderNodeBevel', samples=8)
    bev.inputs["Radius"].default_value = bevel_r
    dot = g.n('ShaderNodeVectorMath', operation='DOT_PRODUCT')
    g.nt.links.new(bev.outputs[0], dot.inputs[0])
    g.nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    inv = g.math('SUBTRACT', 1.0, dot.outputs["Value"])
    edge = g.mr(inv, 0.003, 0.085)
    ao = g.n('ShaderNodeAmbientOcclusion', samples=12)
    ao.inputs["Distance"].default_value = ao_dist
    open_ = g.mr(ao.outputs["AO"], 0.55, 0.95)
    cav = g.math('SUBTRACT', 1.0, g.mr(ao.outputs["AO"], 0.30, 0.88), clamp=True)
    return edge, open_, cav


def _finish(g, base, rough, metal, height, bump_strength=0.35, bump_dist=0.0003):
    nt = g.nt
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (700, 300)
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    p.location = (350, 300)
    for key, sock, y in (("OUT_BASE", base, 500), ("OUT_ROUGH", rough, 380), ("OUT_METAL", metal, 260)):
        r = nt.nodes.new('NodeReroute')
        r.name = key
        r.label = key
        r.location = (150, y)
        if isinstance(sock, bpy.types.NodeSocket):
            nt.links.new(sock, r.inputs[0])
        else:
            v = nt.nodes.new('ShaderNodeValue')
            v.outputs[0].default_value = sock
            v.location = (0, y)
            nt.links.new(v.outputs[0], r.inputs[0])
    nt.links.new(nt.nodes["OUT_BASE"].outputs[0], p.inputs["Base Color"])
    nt.links.new(nt.nodes["OUT_ROUGH"].outputs[0], p.inputs["Roughness"])
    nt.links.new(nt.nodes["OUT_METAL"].outputs[0], p.inputs["Metallic"])
    if height is not None:
        b = nt.nodes.new('ShaderNodeBump')
        b.location = (150, 80)
        b.inputs["Strength"].default_value = bump_strength
        b.inputs["Distance"].default_value = bump_dist
        nt.links.new(height, b.inputs["Height"])
        nt.links.new(b.outputs[0], p.inputs["Normal"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return p


def _new(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.node_tree.nodes.clear()
    return m, G(m.node_tree)


# ---------------------------------------------------------------- сталь (воронение, потёртости)
def steel(name="cs2_steel", base_a=(0.020, 0.022, 0.026), base_b=(0.050, 0.052, 0.057), worn=(0.40, 0.39, 0.375),
          rough0=0.47, wear_amt=1.0, dirt=(0.085, 0.07, 0.055), metal0=1.0, scratch=1.0):
    m, g = _new(name)
    tc = g.n('ShaderNodeTexCoord').outputs["Object"]
    n_big = g.noise(tc, 38, 5, 0.62)
    n_mid = g.noise(tc, 240, 4, 0.55)
    n_fine = g.noise(tc, 1700, 2, 0.5)
    scr_n = g.noise(g.mapping(tc, scale=(1, 0.012, 1)), 4200, 1, 0.5)
    scr = g.mr(scr_n, 0.745, 0.775)
    scr2_n = g.noise(g.mapping(tc, scale=(0.02, 1, 0.3), rot=(0, 0.5, 0.3)), 3000, 1, 0.5)
    scr2 = g.mr(scr2_n, 0.76, 0.79)
    scr_all = g.math('MAXIMUM', scr, g.math('MULTIPLY', scr2, 0.7))
    edge, open_, cav = _masks(g)
    w0 = g.math('MULTIPLY', g.math('MULTIPLY', edge, open_), g.math('ADD', 0.45, g.math('MULTIPLY', n_mid, 1.25)))
    wear = g.mr(g.math('MULTIPLY', w0, wear_amt), 0.22, 0.70)
    # пятна выцветшего воронения на плоскостях
    patch = g.mr(g.math('MULTIPLY', n_big, g.math('ADD', 0.6, g.math('MULTIPLY', n_mid, 0.8))), 0.55, 0.85)
    dirtm = g.math('MULTIPLY', cav, g.math('ADD', 0.35, n_big), clamp=True)
    c0 = g.mixc(n_big, base_a, base_b)
    c1 = g.mixc(g.math('MULTIPLY', patch, 0.35), c0, (0.11, 0.105, 0.10))
    c2 = g.mixc(wear, c1, worn)
    c3 = g.mixc(g.math('MULTIPLY', scr_all, 0.22 * scratch), c2, (0.17, 0.17, 0.175))
    c4 = g.mixc(g.math('MULTIPLY', dirtm, 0.75), c3, dirt)
    r0 = g.math('ADD', rough0, g.math('MULTIPLY', g.math('SUBTRACT', n_big, 0.5), 0.20))
    r1 = g.math('ADD', r0, g.math('MULTIPLY', g.math('SUBTRACT', n_fine, 0.5), 0.10))
    r2 = g.mixf(wear, r1, 0.26)
    r3 = g.mixf(g.math('MULTIPLY', scr_all, 0.5), r2, 0.30)
    r4 = g.mixf(g.math('MULTIPLY', dirtm, 0.85), r3, 0.88)
    metal = g.math('MULTIPLY', g.mixf(wear, metal0, 1.0), g.math('SUBTRACT', 1.0, g.math('MULTIPLY', dirtm, 0.6), clamp=True))
    h = g.math('ADD', g.math('MULTIPLY', n_fine, 0.35), g.math('MULTIPLY', n_mid, 0.25))
    h = g.math('SUBTRACT', h, g.math('MULTIPLY', scr_all, 0.8))
    h = g.math('SUBTRACT', h, g.math('MULTIPLY', wear, 0.25))
    _finish(g, c4, r4, metal, h, 0.30, 0.0003)
    m["cs2_proc"] = True
    return m


# ---------------------------------------------------------------- дерево (лакированное, с рисунком)
def wood(name="cs2_wood", dark=(0.070, 0.020, 0.007), mid=(0.255, 0.082, 0.026), light=(0.43, 0.175, 0.062),
         raw=(0.44, 0.27, 0.14), rough0=0.36, ring_scale=7.0, checker_img=None, checker_map=None):
    m, g = _new(name)
    tc = g.n('ShaderNodeTexCoord').outputs["Object"]
    tcw = g.mapping(tc, scale=(1, 0.10, 1))
    fig = g.noise(tcw, 24, 6, 0.6, 1.5)
    rings = g.math('FRACT', g.math('MULTIPLY', fig, ring_scale))
    ringc = g.ramp(rings, [(0.0, dark), (0.10, mid), (0.50, light), (0.86, mid), (1.0, dark)])
    fib = g.noise(g.mapping(tc, scale=(1, 0.018, 1)), 430, 3, 0.6)
    fibm = g.mr(fib, 0.42, 0.72)
    pores = g.noise(g.mapping(tc, scale=(1, 0.05, 1)), 1500, 2, 0.5)
    porem = g.mr(pores, 0.60, 0.72)
    var = g.noise(tc, 8, 2, 0.5)
    c0 = g.mixc(g.math('MULTIPLY', fibm, 0.55), ringc, dark)
    c1 = g.mixc(g.math('MULTIPLY', porem, 0.5), c0, (0.03, 0.01, 0.004))
    c2 = g.mixc(g.mr(var, 0.3, 0.75), c1, g.mixc(0.5, c1, light), )
    edge, open_, cav = _masks(g, 0.004, 0.014)
    n_mid = g.noise(tc, 200, 4, 0.55)
    wear = g.mr(g.math('MULTIPLY', g.math('MULTIPLY', edge, open_), g.math('ADD', 0.4, g.math('MULTIPLY', n_mid, 1.2))), 0.30, 0.85)
    dirtm = g.math('MULTIPLY', cav, g.math('ADD', 0.5, var), clamp=True)
    c3 = g.mixc(g.math('MULTIPLY', wear, 0.8), c2, raw)
    c4 = g.mixc(g.math('MULTIPLY', dirtm, 0.8), c3, (0.022, 0.012, 0.008))
    r0 = g.math('ADD', rough0, g.math('MULTIPLY', fibm, 0.10))
    r1 = g.math('ADD', r0, g.math('MULTIPLY', porem, 0.18))
    r2 = g.mixf(wear, r1, 0.72)
    r3 = g.mixf(g.math('MULTIPLY', dirtm, 0.7), r2, 0.85)
    h = g.math('SUBTRACT', g.math('MULTIPLY', fibm, -0.35), g.math('MULTIPLY', porem, 0.9))
    base, rough, height = c4, r3, h
    if checker_img is not None:
        # насечка: маска из чертежа (проекция сбоку), рисунок — ромбы
        y0, y1, z0, z1 = checker_map
        sep = g.n('ShaderNodeSeparateXYZ')
        g.nt.links.new(tc, sep.inputs[0])
        u = g.math('DIVIDE', g.math('SUBTRACT', sep.outputs["Y"], y0), (y1 - y0))
        v = g.math('DIVIDE', g.math('SUBTRACT', sep.outputs["Z"], z0), (z1 - z0))
        cmb = g.n('ShaderNodeCombineXYZ')
        g.nt.links.new(u, cmb.inputs[0])
        g.nt.links.new(v, cmb.inputs[1])
        im = g.n('ShaderNodeTexImage', image=checker_img, extension='CLIP', interpolation='Linear')
        g.nt.links.new(cmb.outputs[0], im.inputs["Vector"])
        geo = g.n('ShaderNodeNewGeometry')
        sn = g.n('ShaderNodeSeparateXYZ')
        g.nt.links.new(geo.outputs["Normal"], sn.inputs[0])
        facing = g.mr(g.math('ABSOLUTE', sn.outputs["X"]), 0.55, 0.8)
        mask = g.math('MULTIPLY', im.outputs[0], facing)
        k = 1 / 0.0019
        a1 = g.math('ADD', g.math('MULTIPLY', sep.outputs["Y"], k), g.math('MULTIPLY', sep.outputs["Z"], k * 0.62))
        a2 = g.math('SUBTRACT', g.math('MULTIPLY', sep.outputs["Y"], k), g.math('MULTIPLY', sep.outputs["Z"], k * 0.62))
        t1 = g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', a1), 0.5))
        t2 = g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', a2), 0.5))
        pyr = g.math('MULTIPLY', g.math('MINIMUM', t1, t2), 2.0)       # 0 в канавке, 1 на вершине
        groove = g.math('SUBTRACT', 1.0, g.mr(pyr, 0.0, 0.35))
        base = g.mixc(g.math('MULTIPLY', mask, g.math('ADD', 0.35, g.math('MULTIPLY', groove, 0.6))), base, (0.03, 0.012, 0.006))
        rough = g.mixf(mask, rough, 0.62)
        height = g.math('ADD', g.math('MULTIPLY', height, g.math('SUBTRACT', 1.0, mask)), g.math('MULTIPLY', g.math('MULTIPLY', pyr, mask), 3.0))
    _finish(g, base, rough, 0.0, height, 0.30, 0.0003)
    m["cs2_proc"] = True
    return m


def rubber(name="cs2_rubber", col=(0.016, 0.016, 0.018), rough0=0.72, cell=900.0):
    m, g = _new(name)
    tc = g.n('ShaderNodeTexCoord').outputs["Object"]
    vor = g.n('ShaderNodeTexVoronoi')
    g.nt.links.new(tc, vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = cell
    n = g.noise(tc, 60, 3, 0.5)
    edge, open_, cav = _masks(g)
    wear = g.mr(g.math('MULTIPLY', edge, open_), 0.3, 0.9)
    c = g.mixc(g.math('MULTIPLY', wear, 0.5), g.mixc(n, col, tuple(v * 2.2 for v in col)), (0.10, 0.10, 0.105))
    c = g.mixc(g.math('MULTIPLY', cav, 0.6), c, (0.07, 0.06, 0.05))
    r = g.mixf(wear, g.math('ADD', rough0, g.math('MULTIPLY', n, 0.1)), 0.5)
    _finish(g, c, r, 0.0, vor.outputs[0], 0.5, 0.0004)
    m["cs2_proc"] = True
    return m


def flat(name, col, rough=0.9, metal=0.0):
    m, g = _new(name)
    c = g.rgb(col)
    _finish(g, c, rough, metal, None)
    m["cs2_proc"] = True
    return m


def polymer(name="cs2_polymer", col=(0.022, 0.023, 0.025), rough0=0.58):
    m, g = _new(name)
    tc = g.n('ShaderNodeTexCoord').outputs["Object"]
    n_big = g.noise(tc, 30, 4, 0.6)
    n_fine = g.noise(tc, 2600, 2, 0.5)
    edge, open_, cav = _masks(g)
    n_mid = g.noise(tc, 220, 4, 0.55)
    wear = g.mr(g.math('MULTIPLY', g.math('MULTIPLY', edge, open_), g.math('ADD', 0.4, g.math('MULTIPLY', n_mid, 1.2))), 0.3, 0.85)
    dirtm = g.math('MULTIPLY', cav, g.math('ADD', 0.4, n_big), clamp=True)
    c = g.mixc(n_big, col, tuple(v * 1.9 for v in col))
    c = g.mixc(g.math('MULTIPLY', wear, 0.55), c, tuple(min(1.0, v * 6.5) for v in col))
    c = g.mixc(g.math('MULTIPLY', dirtm, 0.7), c, (0.09, 0.08, 0.065))
    r = g.math('ADD', rough0, g.math('MULTIPLY', g.math('SUBTRACT', n_big, 0.5), 0.15))
    r = g.mixf(wear, r, 0.38)
    r = g.mixf(g.math('MULTIPLY', dirtm, 0.8), r, 0.9)
    _finish(g, c, r, 0.0, n_fine, 0.35, 0.00025)
    m["cs2_proc"] = True
    return m


def assign(asset, table):
    """table: вид материала детали (cs2_mat) -> материал"""
    n = 0
    for o in T.asset_objects(asset):
        if o.type == 'MESH' and o.get("cs2_mat") in table:
            o.data.materials.clear()
            o.data.materials.append(table[o["cs2_mat"]])
            n += 1
    return n


# ---------------------------------------------------------------- объединение деталей
def _ctx():
    w, a = T.view3d()
    reg = [r for r in a.regions if r.type == 'WINDOW'][0]
    return dict(window=w, screen=w.screen, area=a, region=reg)


def finalize(asset):
    """Склеить детали: неподвижные -> <asset>_body, подвижные по группам -> mv_<группа>.
    Опорные точки подвижных — из pivots."""
    root = bpy.data.objects.get(asset + "_root")
    pivots = json.loads(root.get("cs2_pivots", "{}"))
    groups = {}
    for o in T.asset_objects(asset):
        if o.type == 'MESH':
            groups.setdefault(o.get("cs2_mv") or "", []).append(o)
    dg = bpy.context.evaluated_depsgraph_get()
    made = {}
    for gname, objs in groups.items():
        for o in objs:           # применить модификаторы (нормали)
            if o.modifiers:
                me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
                old = o.data
                o.modifiers.clear()
                o.data = me
                if old.users == 0:
                    bpy.data.meshes.remove(old)
        base = objs[0]
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = base
        with bpy.context.temp_override(**_ctx(), active_object=base, selected_editable_objects=objs, selected_objects=objs):
            bpy.ops.object.join()
        nm = (asset + "_body") if gname == "" else ("mv_" + gname)
        base.name = nm
        base.data.name = nm
        if gname and gname in pivots:
            pv = Vector(pivots[gname])
            from mathutils import Matrix
            base.data.transform(Matrix.Translation(-pv))
            base.location = pv
        made[nm] = len(base.data.polygons)
    return made


def unwrap(asset, margin=0.0022):
    objs = [o for o in T.asset_objects(asset) if o.type == 'MESH']
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
        if not o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(**_ctx(), active_object=objs[0], selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        try:
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(margin=margin, rotate=True)
        except Exception as e:
            NS["cs2_uv_err"] = repr(e)
        bpy.ops.object.mode_set(mode='OBJECT')
    return len(objs)


# ---------------------------------------------------------------- запекание
def _gpu():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        pr = bpy.context.preferences.addons['cycles'].preferences
        for dt in ('OPTIX', 'CUDA'):
            try:
                pr.compute_device_type = dt
                break
            except Exception:
                pass
        try:
            pr.refresh_devices()
        except Exception:
            pr.get_devices()
        for d in pr.devices:
            d.use = (d.type != 'CPU')
        sc.cycles.device = 'GPU'
        return pr.compute_device_type
    except Exception as e:
        return repr(e)


def bake(asset, res=2048, spp=48, out_dir=None):
    """Запечь процедурные материалы ассета в <asset>_base/_orm/_normal. Возвращает пути."""
    t0 = time.time()
    sc = bpy.context.scene
    dev = _gpu()
    sc.cycles.samples = spp
    sc.cycles.use_denoising = False
    bk = sc.render.bake
    bk.margin = max(4, res // 256)
    bk.use_clear = True
    bk.use_selected_to_active = False
    try:
        bk.target = 'IMAGE_TEXTURES'
    except Exception:
        pass
    objs = [o for o in T.asset_objects(asset) if o.type == 'MESH']
    mats = []
    for o in objs:
        for s in o.material_slots:
            if s.material and s.material not in mats:
                mats.append(s.material)
    imgs = {}
    for k in ("base", "rough", "metal", "ao", "normal"):
        nm = f"{asset}_{k}"
        im = bpy.data.images.get(nm)
        if im is not None:
            bpy.data.images.remove(im)
        im = bpy.data.images.new(nm, res, res, alpha=False, float_buffer=False, is_data=(k != "base"))
        imgs[k] = im
    for m in mats:
        nt = m.node_tree
        tgt = nt.nodes.get("BAKE_TGT") or nt.nodes.new('ShaderNodeTexImage')
        tgt.name = "BAKE_TGT"
        tgt.location = (900, -200)
        em = nt.nodes.get("BAKE_EM") or nt.nodes.new('ShaderNodeEmission')
        em.name = "BAKE_EM"
        em.location = (500, -200)

    def target(k):
        for m in mats:
            nt = m.node_tree
            for n in nt.nodes:
                n.select = False
            tg = nt.nodes["BAKE_TGT"]
            tg.image = imgs[k]
            tg.select = True
            nt.nodes.active = tg

    def out_node(nt):
        for n in nt.nodes:
            if n.type == 'OUTPUT_MATERIAL':
                return n

    def emit(key):
        for m in mats:
            nt = m.node_tree
            em = nt.nodes["BAKE_EM"]
            nt.links.new(nt.nodes[key].outputs[0], em.inputs["Color"])
            nt.links.new(em.outputs[0], out_node(nt).inputs["Surface"])

    def restore():
        for m in mats:
            nt = m.node_tree
            p = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
            nt.links.new(p.outputs[0], out_node(nt).inputs["Surface"])

    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    ctx = dict(_ctx(), active_object=objs[0], selected_objects=objs, selected_editable_objects=objs)
    log = {}
    with bpy.context.temp_override(**ctx):
        for k, key in (("base", "OUT_BASE"), ("rough", "OUT_ROUGH"), ("metal", "OUT_METAL")):
            t1 = time.time()
            target(k)
            emit(key)
            bpy.ops.object.bake(type='EMIT')
            log[k] = round(time.time() - t1, 1)
        restore()
        t1 = time.time()
        target("normal")
        bk.normal_space = 'TANGENT'
        bpy.ops.object.bake(type='NORMAL')
        log["normal"] = round(time.time() - t1, 1)
        t1 = time.time()
        target("ao")
        bpy.ops.object.bake(type='AO')
        log["ao"] = round(time.time() - t1, 1)
    # ORM
    n = res * res * 4
    def px(im):
        a = np.empty(n, np.float32)
        im.pixels.foreach_get(a)
        return a.reshape(-1, 4)
    ao, ro, me = px(imgs["ao"]), px(imgs["rough"]), px(imgs["metal"])
    orm = np.ones((res * res, 4), np.float32)
    orm[:, 0] = np.clip(ao[:, 0] * 1.15, 0, 1)
    orm[:, 1] = ro[:, 0]
    orm[:, 2] = me[:, 0]
    nm = f"{asset}_orm"
    old = bpy.data.images.get(nm)
    if old is not None:
        bpy.data.images.remove(old)
    im_orm = bpy.data.images.new(nm, res, res, alpha=False, float_buffer=False, is_data=True)
    im_orm.pixels.foreach_set(orm.ravel())
    out_dir = out_dir or os.path.join(T.MODELS, "weapons", "tex")
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for k, im in (("base", imgs["base"]), ("orm", im_orm), ("normal", imgs["normal"])):
        p = os.path.join(out_dir, f"{asset}_{k}.png")
        im.filepath_raw = p
        im.file_format = 'PNG'
        im.save()
        paths[k] = p
    for k in ("rough", "metal", "ao"):
        bpy.data.images.remove(imgs[k])
    log["total"] = round(time.time() - t0, 1)
    log["device"] = dev
    log["paths"] = paths
    return log


def _gltf_ao_group():
    ng = bpy.data.node_groups.get("glTF Material Output")
    if ng is None:
        ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        ng.interface.new_socket(name="Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
        ng.nodes.new('NodeGroupInput')
    return ng


def pbr_material(asset):
    """Финальный материал из запечённых текстур; назначается всем деталям."""
    m, g = _new(f"{asset}_pbr")
    nt = m.node_tree
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (500, 200)
    p = nt.nodes.new('ShaderNodeBsdfPrincipled'); p.location = (150, 200)
    tb = nt.nodes.new('ShaderNodeTexImage'); tb.location = (-500, 400); tb.image = bpy.data.images[f"{asset}_base"]
    to = nt.nodes.new('ShaderNodeTexImage'); to.location = (-800, 100); to.image = bpy.data.images[f"{asset}_orm"]
    to.image.colorspace_settings.name = 'Non-Color'
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.location = (-500, -250); tn.image = bpy.data.images[f"{asset}_normal"]
    tn.image.colorspace_settings.name = 'Non-Color'
    sp = nt.nodes.new('ShaderNodeSeparateColor'); sp.location = (-450, 100)
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.location = (-150, -250)
    gl = nt.nodes.new('ShaderNodeGroup'); gl.node_tree = _gltf_ao_group(); gl.location = (150, -250)
    L = nt.links.new
    L(tb.outputs["Color"], p.inputs["Base Color"])
    L(to.outputs["Color"], sp.inputs[0])
    L(sp.outputs[1], p.inputs["Roughness"])
    L(sp.outputs[2], p.inputs["Metallic"])
    L(sp.outputs[0], gl.inputs["Occlusion"])
    L(tn.outputs["Color"], nm.inputs["Color"])
    L(nm.outputs[0], p.inputs["Normal"])
    L(p.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (0.2, 0.2, 0.2, 1)
    n = 0
    for o in T.asset_objects(asset):
        if o.type == 'MESH':
            o.data.materials.clear()
            o.data.materials.append(m)
            n += 1
    return n


def export_glb(asset, category="weapons"):
    root = bpy.data.objects.get(asset + "_root")
    saved = tuple(root.location)
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    out_dir = os.path.join(T.MODELS, category)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, asset + ".glb")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    objs = T.asset_objects(asset)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    with bpy.context.temp_override(**_ctx(), active_object=root, selected_objects=objs):
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                                  export_yup=True, export_cameras=False, export_lights=False, export_extras=True)
    root.location = saved
    return {"path": path, "mb": round(os.path.getsize(path) / 2 ** 20, 2)}
