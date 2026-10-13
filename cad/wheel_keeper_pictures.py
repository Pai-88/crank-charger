"""Pictures for the wheel keeper band (Blender, headless):

    /Applications/Blender.app/Contents/MacOS/Blender --background --python cad/wheel_keeper_pictures.py

Writes cad/stl/spares/keeper_1.png .. keeper_4.png (the band alone; on the machine; a cutaway through one
arm showing lip and barb; the fitting move), from the real meshes: the machine's view STLs in cad/stl/,
the band from assembly/_build/keeper/band.stl (in place). Same black studio as the showcase video.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEEP = os.path.join(ROOT, "assembly", "_build", "keeper")
OUT = os.path.join(HERE, "stl", "spares")
S = 0.001
cfg = json.load(open(os.path.join(KEEP, "keeper.json")))
AY = cfg["axle_y"]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.eevee.taa_render_samples = 96
if hasattr(sc.eevee, "use_raytracing"):
    sc.eevee.use_raytracing = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 1050
sc.render.film_transparent = False
im = sc.render.image_settings
if hasattr(im, "media_type"):
    im.media_type = "IMAGE"
im.file_format, im.color_mode = "PNG", "RGBA"
sc.render.use_file_extension = False                   # the path below carries its own .png
sc.view_settings.view_transform = "AgX"
world = bpy.data.worlds.new("w")
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes["Background"]
hdri = os.path.join(os.path.dirname(bpy.app.binary_path), "..", "Resources", bpy.app.version_string.split()[0][:3], "datafiles", "studiolights", "world", "studio.exr")
import glob
hits = glob.glob(os.path.join(os.path.dirname(bpy.app.binary_path), "..", "Resources", "*", "datafiles", "studiolights", "world", "studio.exr"))
if hits:
    env = wn.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(hits[0])
    sep = wn.nodes.new("ShaderNodeSeparateXYZ")
    wn.links.new(wn.nodes.new("ShaderNodeTexCoord").outputs["Generated"], sep.inputs[0])
    sky = wn.nodes.new("ShaderNodeMapRange")
    sky.interpolation_type, sky.clamp = "SMOOTHSTEP", True
    sky.inputs["From Min"].default_value, sky.inputs["From Max"].default_value = 0.12, 0.45
    wn.links.new(sep.outputs["Z"], sky.inputs["Value"])
    gate = wn.nodes.new("ShaderNodeMix")
    gate.data_type, gate.blend_type = "RGBA", "MULTIPLY"
    gate.inputs["Factor"].default_value = 1.0
    wn.links.new(env.outputs["Color"], gate.inputs[6])
    wn.links.new(sky.outputs["Result"], gate.inputs[7])
    wn.links.new(gate.outputs[2], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.1
sc.world = world
# a black backdrop: the camera must never see the HDRI
sc.render.film_transparent = True


def material(name, base, metallic, rough, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    return m


MAT = dict(printed=material("graphite", (0.085, 0.09, 0.095), 0.0, 0.36, 0.35), gear=material("orange", (0.86, 0.30, 0.035), 0.0, 0.4, 0.25),
           band=material("band", (0.10, 0.62, 0.72), 0.0, 0.38, 0.3), motor=material("motor", (0.03, 0.03, 0.032), 0.55, 0.38),
           grip=material("grip", (0.03, 0.03, 0.03), 0.0, 0.65))

rig = bpy.data.objects.new("rig", None)
rig.rotation_euler = (math.pi / 2, 0.0, 0.0)
sc.collection.objects.link(rig)


def load(path, name, mat):
    bpy.ops.wm.stl_import(filepath=path, global_scale=S)
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    try:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35.0))
    except Exception:
        pass
    ob.parent = rig
    return ob


objs = {}
for n, m in (("frame", "printed"), ("wheel", "printed"), ("ring", "gear"), ("sun", "gear"), ("planet1", "gear"), ("planet2", "gear"),
             ("planet3", "gear"), ("spider", "gear"), ("grip", "grip"), ("motor", "motor")):
    objs[n] = load(os.path.join(HERE, "stl", f"_view_{n}.stl"), n, MAT[m])
objs["band"] = load(os.path.join(KEEP, "band.stl"), "band", MAT["band"])
objs["cutter"] = load(os.path.join(KEEP, "cutter.stl"), "cutter", MAT["band"])
objs["cutter"].hide_render = True

floor_me = bpy.data.meshes.new("floor")
floor_me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
fb = fm.node_tree.nodes["Principled BSDF"]
fb.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
fb.inputs["Roughness"].default_value = 0.33
floor_me.materials.append(fm)
floor = bpy.data.objects.new("floor", floor_me)
floor.scale = (5, 5, 1)
sc.collection.objects.link(floor)

pivot = bpy.data.objects.new("pivot", None)
sc.collection.objects.link(pivot)
cam_data = bpy.data.cameras.new("cam")
cam_data.lens, cam_data.sensor_width, cam_data.sensor_fit = 50.0, 36.0, "HORIZONTAL"
cam_data.clip_start, cam_data.clip_end = 0.01, 50.0
cam = bpy.data.objects.new("cam", cam_data)
cam.parent = pivot
sc.collection.objects.link(cam)
sc.camera = cam
con = cam.constraints.new("TRACK_TO")
con.target, con.track_axis, con.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"


def light(name, loc, size, power, specular=0.6):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size = power, size
    if hasattr(ld, "specular_factor"):
        ld.specular_factor = specular
    lo = bpy.data.objects.new(name, ld)
    lo.parent = pivot
    lo.location = loc
    sc.collection.objects.link(lo)
    c = lo.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"


light("key", (-1.3, -1.1, 1.5), 1.2, 62.0)
light("rim", (1.0, 1.5, 1.6), 1.2, 60.0, 0.2)
light("fill", (0.3, -1.7, 0.7), 1.6, 32.0, 0.3)


def to_world(p):
    return Vector((p[0] * S, -p[2] * S, p[1] * S))


def shot(path, target, phi, elev, dist, hidden=(), cut=None):
    for n, ob in objs.items():
        ob.hide_render = (n in hidden) or n == "cutter"
    if cut:
        for n in cut:
            mod = objs[n].modifiers.new("cut", "BOOLEAN")
            mod.operation, mod.object = "INTERSECT", objs["cutter"]
            mod.solver = "EXACT"
    pivot.location = to_world(target)
    pivot.rotation_euler = (0.0, 0.0, math.radians(phi))
    el = math.radians(elev)
    cam.location = (0.0, -dist * math.cos(el), dist * math.sin(el))
    sc.render.filepath = path + ".rgba.png"
    bpy.ops.render.render(write_still=True)
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path + ".rgba.png", "-f", "lavfi", "-i", "color=c=black:s=1400x1050",
                    "-filter_complex", "[1:v][0:v]overlay=shortest=1,format=rgb24", "-frames:v", "1", path + ".png"], check=True)
    os.remove(path + ".rgba.png")
    if cut:
        for n in cut:
            objs[n].modifiers.clear()
    print("wrote", path + ".png")


machine = ["frame", "wheel", "ring", "sun", "planet1", "planet2", "planet3", "spider", "grip", "motor"]
only = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else []
want = lambda k: not only or str(k) in only
# 1: the band alone, lips up as it comes off the printer (shown in place but everything else hidden)
if want(1):
    shot(os.path.join(OUT, "keeper_1"), (0, AY, 25), -40, 28, 0.62, hidden=machine)
# 2: on the machine, front-left, the gap at the upper left
if want(2):
    shot(os.path.join(OUT, "keeper_2"), (0, AY, 20), -50, 16, 0.78)
# 3: a 7 mm slice through the arm at 0 degrees, seen straight down onto the cut: the lip over the wheel's front face,
#    the band down the outside of the rim and skirt, the barb tucked under the ring's back, the wall behind it all
if want(3):
    shot(os.path.join(OUT, "keeper_3"), (cfg["r_in"] - 6, AY, 22), 0, 89, 0.15, hidden=["grip", "motor", "spider", "sun", "planet1", "planet2", "planet3"], cut=["band", "wheel", "ring", "frame"])
# 4: from behind-right, the three arms running down the skirt into the gap in front of the wall
if want(4):
    shot(os.path.join(OUT, "keeper_4"), (0, AY, 10), -215, 22, 0.74, hidden=["motor"])
