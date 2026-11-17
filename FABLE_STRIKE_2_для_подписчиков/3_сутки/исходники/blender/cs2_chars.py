"""FABLE STRIKE 2 — бойцы: замеры головы, очки (закрывают глаза Tripo), сборка glb.
Работает и в окне Blender, и в фоне. Персонаж стоит лицом в -Y, Z вверх."""
import bpy, bmesh, math, os
from mathutils import Vector


def char_objects():
    arm = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE'][0]
    body = max((o for o in bpy.context.scene.objects if o.type == 'MESH' and o.find_armature() == arm), key=lambda o: len(o.data.vertices))
    return arm, body


def bone(arm, short):
    for b in arm.data.bones:
        if b.name.split(":")[-1] == short:
            return b
    return None


def measure_head(arm, body):
    """Замеры по сетке: нос (самая передняя точка лица), уровень глаз, полуширина на уровне глаз, перед лба."""
    mw = body.matrix_world
    hb = bone(arm, "Head")
    ht = bone(arm, "HeadTop_End")
    z0 = (arm.matrix_world @ hb.head_local).z
    z1 = (arm.matrix_world @ (ht.head_local if ht else hb.tail_local)).z
    vs = [mw @ v.co for v in body.data.vertices]
    head = [p for p in vs if p.z > z0 + 0.02 and abs(p.x) < 0.14]
    cy = sum(p.y for p in head) / len(head)
    # нос: самая передняя точка в средней полосе лица
    band = [p for p in head if abs(p.x) < 0.015 and z0 + 0.03 < p.z < z0 + 0.11]
    nose = min(band, key=lambda p: p.y)
    ze = nose.z + 0.040
    lvl = [p for p in head if abs(p.z - ze) < 0.008]
    w = max(abs(p.x) for p in lvl if p.y < cy + 0.02)
    bridge = min((p for p in lvl if abs(p.x) < 0.012), key=lambda p: p.y)
    side = [p for p in lvl if abs(abs(p.x) - 0.045) < 0.01 and p.y < cy]
    y_eye = min(p.y for p in side) if side else bridge.y + 0.01
    return {"z0": z0, "z1": z1, "cy": cy, "nose": tuple(nose), "ze": ze, "w": w, "bridge_y": bridge.y, "eye_y": y_eye}


def _mat(name, col, rough, metal):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*col, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*col, 1)
    return m


def add_eyewear(arm, body, m, style="sport", name="eyewear", frame_col=(0.012, 0.012, 0.014), lens_col=(0.015, 0.018, 0.022),
                gap=0.011, h_up=0.021, h_dn=0.024, strap=False):
    """Очки-щиток по дуге вокруг лица. style: sport (дужки) | goggles (толстая рама + ремень)."""
    ze, w = m["ze"], min(m["w"], 0.070 if style == "sport" else 0.074)
    R = w + (0.016 if style == "goggles" else 0.011)
    y_front = min(m["bridge_y"], m["eye_y"] - 0.004) - gap
    yc = y_front + R
    a_end = math.asin(min(0.999, (w + 0.006) / R))
    n = 28
    bm = bmesh.new()
    th = 0.0022 if style == "sport" else 0.004

    def pt(a, z, r):
        return Vector((r * math.sin(a), yc - r * math.cos(a), z))

    def zb(a):          # нижний край: вырез под нос и скос к вискам
        t = abs(a) / a_end
        notch = 0.015 * math.exp(-(a / 0.15) ** 2)
        return ze - h_dn * (1 - 0.62 * t ** 2.2) + notch

    def zt(a):
        t = abs(a) / a_end
        return ze + h_up * (1 - 0.38 * t ** 2.2)

    cols = []
    for i in range(n + 1):
        a = -a_end + 2 * a_end * i / n
        cols.append([bm.verts.new(pt(a, zb(a), R)), bm.verts.new(pt(a, zt(a), R)),
                     bm.verts.new(pt(a, zt(a), R - th)), bm.verts.new(pt(a, zb(a), R - th))])
    lens_faces = []
    for i in range(n):
        a, b = cols[i], cols[i + 1]
        lens_faces.append(bm.faces.new((a[0], b[0], b[1], a[1])))      # наружная
        bm.faces.new((a[2], b[2], b[3], a[3]))                          # внутренняя
        bm.faces.new((a[1], b[1], b[2], a[2]))                          # верх
        bm.faces.new((a[3], b[3], b[0], a[0]))                          # низ
    bm.faces.new(cols[0])
    bm.faces.new(list(reversed(cols[-1])))
    # рама: полоса по верхнему краю (и по всему контуру у маски)
    fr = 0.0045 if style == "sport" else 0.009
    fo = 0.0016
    frame_faces = []

    def bar(z_in, z_out, sgn):
        prev = None
        for i in range(n + 1):
            a = -a_end + 2 * a_end * i / n
            zi, zo = z_in(a), z_out(a)
            q = [bm.verts.new(pt(a, zi, R + fo)), bm.verts.new(pt(a, zo, R + fo)), bm.verts.new(pt(a, zo, R - th - 0.001)), bm.verts.new(pt(a, zi, R - th - 0.001))]
            if prev:
                for k in range(4):
                    frame_faces.append(bm.faces.new((prev[k], q[k], q[(k + 1) % 4], prev[(k + 1) % 4])))
            else:
                frame_faces.append(bm.faces.new(q))
            prev = q
        frame_faces.append(bm.faces.new(list(reversed(prev))))

    bar(lambda a: zt(a) - fr, lambda a: zt(a) + 0.0015, 1)
    if style == "goggles":
        bar(lambda a: zb(a) - 0.0015, lambda a: zb(a) + fr, -1)
    # дужки / ремень
    for sgn in (-1, 1):
        a = sgn * a_end
        p0 = pt(a, ze + h_up * 0.55, R)
        y_back = m["cy"] + (0.105 if strap else 0.035)
        hh = 0.004 if not strap else 0.014
        tk = 0.0025
        x0 = p0.x
        pts = [Vector((x0, p0.y, p0.z)), Vector((x0 + sgn * 0.004, (p0.y + y_back) / 2, p0.z + 0.002)), Vector((x0 - sgn * (0.002 if not strap else 0.02), y_back, p0.z - (0.006 if not strap else -0.004)))]
        prev = None
        for p in pts:
            q = [bm.verts.new(p + Vector((sgn * tk, 0, -hh))), bm.verts.new(p + Vector((sgn * tk, 0, hh))), bm.verts.new(p + Vector((-sgn * tk, 0, hh))), bm.verts.new(p + Vector((-sgn * tk, 0, -hh)))]
            if prev:
                for k in range(4):
                    frame_faces.append(bm.faces.new((prev[k], q[k], q[(k + 1) % 4], prev[(k + 1) % 4])))
            else:
                frame_faces.append(bm.faces.new(q))
            prev = q
        frame_faces.append(bm.faces.new(list(reversed(prev))))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    lens_idx = {f.index for f in lens_faces}
    bm.faces.index_update()
    lens_set = set(lens_faces)
    mats = [_mat(name + "_frame", frame_col, 0.45, 0.0), _mat(name + "_lens", lens_col, 0.06, 0.9)]
    for f in bm.faces:
        f.material_index = 1 if f in lens_set else 0
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    try:
        me.set_sharp_from_angle(angle=math.radians(40))
    except Exception:
        pass
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    hb = bone(arm, "Head")
    vg = ob.vertex_groups.new(name=hb.name)
    vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    md = ob.modifiers.new("Armature", 'ARMATURE')
    md.object = arm
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    return ob
