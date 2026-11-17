"""Фоновый рендер облёта 360°: сетка -> глина -> финал.
blender -b <file.blend> --python cs2_turntable.py -- '{"asset":"ak","out":"...","modes":["wire","clay","final"]}'
"""
import bpy, sys, json, math, os, glob, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cs2_tools as T

a = json.loads(sys.argv[sys.argv.index("--") + 1])
asset, out = a["asset"], a["out"]
modes = a.get("modes", ["wire", "clay", "final"])
frames, fps = a.get("frames", 360), a.get("fps", 60)
res = a.get("res", [1920, 1080])
engine, spp = a.get("engine", "EEVEE"), a.get("spp", 48)
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene

T.studio(asset, power=a.get("power", 0.16))
T.cam_set(yaw=a.get("yaw", 0.0), pitch=a.get("pitch", 9.0), zoom=a.get("zoom", 0.98), lens=a.get("lens", 85))

if engine == "CYCLES":
    import cs2_mat
    cs2_mat._gpu()
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
        sc.eevee.use_shadows = True
    except Exception as e:
        print("eevee opt", e)

sc.render.resolution_x, sc.render.resolution_y = res
sc.render.resolution_percentage = 100
sc.render.fps = fps
sc.frame_start, sc.frame_end = 1, frames
sc.render.use_motion_blur = False
st = sc.render.image_settings
try:
    st.media_type = 'IMAGE'
except Exception:
    pass
st.file_format = 'JPEG'
st.quality = 95
sc.render.use_overwrite = False      # дозапись: готовые кадры пропускаются
sc.render.use_placeholder = False

# вращение модели на пивоте (свет и камера неподвижны — блики бегут по металлу)
root = bpy.data.objects[asset + "_root"]
piv = bpy.data.objects["studio_pivot"]
bpy.context.view_layer.update()
root.parent = piv
root.matrix_parent_inverse = piv.matrix_world.inverted()
a0 = math.radians(a.get("start", -28.0))
piv.rotation_euler = (0, 0, a0)
piv.keyframe_insert("rotation_euler", index=2, frame=1)
piv.rotation_euler = (0, 0, a0 + 2 * math.pi)
piv.keyframe_insert("rotation_euler", index=2, frame=frames + 1)


def _linear(ob):
    ad = ob.animation_data
    try:
        for fc in ad.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'
        return
    except Exception:
        pass
    for layer in ad.action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    for k in fc.keyframe_points:
                        k.interpolation = 'LINEAR'


_linear(piv)

meshes = [o for o in T.asset_objects(asset) if o.type == 'MESH']
orig = {o.name: [s.material for s in o.material_slots] for o in meshes}


def mk(name, col, rough=0.6, metal=0.0, emit=None):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*col, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*emit[0], 1)
        p.inputs["Emission Strength"].default_value = emit[1]
    return m


clay = mk("tt_clay", (0.42, 0.40, 0.38), 0.62)
dark = mk("tt_dark", (0.035, 0.038, 0.045), 0.55)
wire = mk("tt_wire", (0.0, 0.0, 0.0), 0.5, emit=((0.55, 0.85, 1.0), 2.2))
wires = []


def set_mode(mode):
    global wires
    for w in wires:
        bpy.data.objects.remove(w, do_unlink=True)
    wires = []
    for o in meshes:
        if mode == "final":
            for s, m in zip(o.material_slots, orig[o.name]):
                s.material = m
        else:
            for s in o.material_slots:
                s.material = clay if mode == "clay" else dark
    if mode == "wire":
        col = bpy.data.collections[asset]
        for o in meshes:
            w = bpy.data.objects.new(o.name + "_wire", o.data.copy())
            col.objects.link(w)
            w.parent = o.parent
            w.matrix_local = o.matrix_local.copy()
            w.data.materials.clear()
            w.data.materials.append(wire)
            md = w.modifiers.new("wf", 'WIREFRAME')
            md.thickness = a.get("wire_mm", 0.55) * 0.001
            md.use_replace = True
            md.use_even_offset = False
            wires.append(w)


for mode in modes:
    t0 = time.time()
    fdir = os.path.join(out, "frames", f"{asset}_{mode}")
    os.makedirs(fdir, exist_ok=True)
    have = len([f for f in os.listdir(fdir) if f.endswith(".jpg")])
    if have >= frames:
        print("SKIP", mode, have, flush=True)
        continue
    set_mode(mode)
    sc.render.filepath = os.path.join(fdir, "f_")
    bpy.ops.render.render(animation=True)
    have = len([f for f in os.listdir(fdir) if f.endswith(".jpg")])
    print("DONE", mode, have, "frames", round(time.time() - t0, 1), "s", flush=True)
open(os.path.join(out, "frames", asset + ".done"), "w").write("ok")
print("ALL DONE", flush=True)
