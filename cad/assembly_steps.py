"""Step-by-step assembly pictures, stage 2 of 2: Blender renders every panel.

    .venv/bin/python cad/assembly_steps_export.py
    /Applications/Blender.app/Contents/MacOS/Blender --background --python cad/assembly_steps.py
    (optional, after "--":  s4 s5   render only the views whose name starts with these;
                            --no-compose   stop after the render passes)

Reads assembly/_build/placements.json and the meshes beside it. For each panel it places the
parts (seated, or pulled out along their insertion direction), sets an ORTHOGRAPHIC camera and
renders two unlit data passes with EEVEE: surface normal and which part owns each pixel, then depth.
The picture itself (soft shading, dark outlines, arrows, Avenir text, the PDF) is drawn from
those passes by cad/assembly_steps_compose.py, which this script runs at the end with the
project's own Python, because Blender's Python has no Pillow.

The camera is a true camera: nothing is ever mirrored.
"""
import json
import os
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "assembly", "_build")
PASSES = os.path.join(BUILD, "passes")
SS = 2                                    # supersampling: the passes are twice the picture's size
CAM_DIST = 3000.0
DEPTH_BIAS = 2000.0

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
only = [a for a in argv if not a.startswith("--")]
with open(os.path.join(BUILD, "placements.json")) as fh:
    plan = json.load(fh)
os.makedirs(PASSES, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
sc.eevee.taa_render_samples = 1           # one sample, no filtering: every pixel belongs to exactly one part
sc.render.filter_size = 0.01
sc.render.film_transparent = True
sc.render.use_file_extension = True
sc.render.resolution_percentage = 100
im = sc.render.image_settings
if hasattr(im, "media_type"):
    im.media_type = "IMAGE"
im.file_format = "OPEN_EXR"
im.color_mode = "RGBA"
im.color_depth = "32"
world = bpy.data.worlds.new("w")
sc.world = world

# ---- two unlit materials. EEVEE's film is half-float, so the numbers are packed to survive that:
#      pass A: R = normal.right + 1, G = normal.up + 1, B = part number (a whole number)
#      pass B: R = whole part of depth / 4 mm, G = the remainder + 1 (depth measured toward the camera)
def new_material(name):
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree


def dot(nt, sock):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = "DOT_PRODUCT"
    nt.links.new(sock, n.inputs[0])
    return n


def math_node(nt, op, a, b=0.0):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for k, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            n.inputs[k].default_value = v
        else:
            nt.links.new(v, n.inputs[k])
    return n


def emit(nt, channels):
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    for k, n in enumerate(channels):
        nt.links.new(n.outputs[0], comb.inputs[k])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(comb.outputs[0], em.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])


mat_a, nt = new_material("normal_and_part")
geo = nt.nodes.new("ShaderNodeNewGeometry")
info = nt.nodes.new("ShaderNodeObjectInfo")
n_right, n_up = dot(nt, geo.outputs["Normal"]), dot(nt, geo.outputs["Normal"])
emit(nt, (math_node(nt, "ADD", n_right.outputs["Value"], 1.0), math_node(nt, "ADD", n_up.outputs["Value"], 1.0),
          math_node(nt, "ADD", info.outputs["Object Index"], 0.0)))

mat_b, nt = new_material("depth")
geo = nt.nodes.new("ShaderNodeNewGeometry")
p_c = dot(nt, geo.outputs["Position"])
depth = math_node(nt, "ADD", p_c.outputs["Value"], DEPTH_BIAS)
quarter = math_node(nt, "DIVIDE", depth.outputs[0], 4.0)
emit(nt, (math_node(nt, "FLOOR", quarter.outputs[0]), math_node(nt, "ADD", math_node(nt, "FRACT", quarter.outputs[0]).outputs[0], 1.0)))


def render_pass(material, path, w, h):
    for ob in objs.values():
        ob.data.materials[0] = material
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    os.remove(path)
    return px.reshape(h, w, 4)[::-1]                      # Blender stores rows bottom up


# ---- the parts, each already in its assembled position (millimetres are Blender units here)
objs = {}
for name, meta in plan["meshes"].items():
    d = np.load(os.path.join(BUILD, meta["file"]))
    v, f = d["v"].astype(np.float32), d["f"].astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", v.ravel())
    me.loops.add(3 * len(f))
    me.loops.foreach_set("vertex_index", f.ravel())
    me.polygons.add(len(f))
    me.polygons.foreach_set("loop_start", np.arange(0, 3 * len(f), 3, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(f), 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(f), dtype=bool))      # the export split the sharp edges
    me.materials.append(mat_a)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    objs[name] = ob

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.clip_start, cam_data.clip_end = 10.0, 2 * CAM_DIST
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam

done = 0
for step in plan["steps"]:
    for view in step["views"]:
        if only and not any(view["name"].startswith(p) for p in only):
            continue
        for ob in objs.values():
            ob.hide_render = True
        for k, inst in enumerate(view["inst"]):
            ob = objs[inst["mesh"]]
            ob.hide_render = False
            ob.location = inst["off"]
            ob.pass_index = k + 1
        c, up, right, target = (np.array(view["cam"][k]) for k in ("c", "up", "right", "target"))
        loc = target + c * CAM_DIST
        cam.matrix_world = Matrix([[right[0], up[0], c[0], loc[0]], [right[1], up[1], c[1], loc[1]],
                                   [right[2], up[2], c[2], loc[2]], [0, 0, 0, 1]])
        w, h = view["rect"][2] * SS, view["rect"][3] * SS
        sc.render.resolution_x, sc.render.resolution_y = w, h
        cam_data.ortho_scale = max(view["rect"][2], view["rect"][3]) / view["ppm"]
        n_right.inputs[1].default_value = right
        n_up.inputs[1].default_value = up
        p_c.inputs[1].default_value = c
        depth.inputs[1].default_value = DEPTH_BIAS - float(target @ c)
        bpy.context.view_layer.update()
        path = os.path.join(PASSES, view["name"] + ".exr")
        pa = render_pass(mat_a, path, w, h)
        pb = render_pass(mat_b, path, w, h)
        hit = pa[..., 3] > 0.5
        np.savez_compressed(os.path.join(PASSES, view["name"] + ".npz"),
                            nx=(pa[..., 0] - 1.0).astype(np.float16), ny=(pa[..., 1] - 1.0).astype(np.float16),
                            part=np.where(hit, np.rint(pa[..., 2]), 0).astype(np.uint8),
                            depth=np.where(hit, 4.0 * (pb[..., 0] + pb[..., 1] - 1.0), 0).astype(np.float32))
        part = np.rint(pa[..., 2])
        done += 1
        print(f"pass {view['name']}: {w} x {h}, {int(part.max())} parts")

print(f"{done} passes in {PASSES}")
if "--no-compose" not in argv:
    py = os.path.join(ROOT, ".venv", "bin", "python")
    subprocess.run([py, os.path.join(HERE, "assembly_steps_compose.py")], check=True)
