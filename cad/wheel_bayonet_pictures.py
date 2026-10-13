"""Pictures for the bayonet wheel (Blender, headless):

    /Applications/Blender.app/Contents/MacOS/Blender --background --python cad/wheel_bayonet_pictures.py

Writes cad/stl/spares/bayonet_1.png (the wheel on the machine, from the front) and bayonet_2.png (close
on one pocket: the dog home under its roof, the spring finger behind it). The ring is turned by the
pocket travel so the dogs sit in the locked position. Same studio as the keeper pictures.
"""
import glob
import math
import os
import subprocess
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEEP = os.path.join(ROOT, "assembly", "_build", "keeper")
OUT = os.path.join(HERE, "stl", "spares")
S = 0.001
sys.path.insert(0, HERE)
AY, R_OUT, TRAVEL_DEG, Z_WHEEL = 144.0, 118.2, 4.36, 32.9      # from planetary.py and wheel_bayonet.py

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.eevee.taa_render_samples = 96
if hasattr(sc.eevee, "use_raytracing"):
    sc.eevee.use_raytracing = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 1050
im = sc.render.image_settings
if hasattr(im, "media_type"):
    im.media_type = "IMAGE"
im.file_format, im.color_mode = "PNG", "RGBA"
sc.render.use_file_extension = False
sc.render.film_transparent = True
sc.view_settings.view_transform = "AgX"
world = bpy.data.worlds.new("w")
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes["Background"]
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
           new=material("new", (0.10, 0.62, 0.72), 0.0, 0.38, 0.3), motor=material("motor", (0.03, 0.03, 0.032), 0.55, 0.38),
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
for n, m in (("frame", "printed"), ("ring", "gear"), ("sun", "gear"), ("planet1", "gear"), ("planet2", "gear"), ("planet3", "gear"),
             ("spider", "gear"), ("motor", "motor")):
    objs[n] = load(os.path.join(HERE, "stl", f"_view_{n}.stl"), n, MAT[m])
objs["wheel"] = load(os.path.join(KEEP, "wheel_bayonet_view.stl"), "wheel", MAT["new"])
# the ring turned by the travel: the dogs sit in the locked position (the gears' teeth are not re-meshed: a picture only)
objs["ring"].location = Vector((0, AY * S, 0))
objs["ring"].data.transform(__import__("mathutils").Matrix.Translation((0, -AY, 0)))   # mesh units are mm: the importer scales the OBJECT
objs["ring"].rotation_euler = (0.0, 0.0, math.radians(TRAVEL_DEG))

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


def shot(path, target, phi, elev, dist, hidden=()):
    for n, ob in objs.items():
        ob.hide_render = n in hidden
    pivot.location = to_world(target)
    pivot.rotation_euler = (0.0, 0.0, math.radians(phi))
    el = math.radians(elev)
    cam.location = (0.0, -dist * math.cos(el), dist * math.sin(el))
    sc.render.filepath = path + ".rgba.png"
    bpy.ops.render.render(write_still=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path + ".rgba.png", "-f", "lavfi", "-i", "color=c=black:s=1400x1050",
                    "-filter_complex", "[1:v][0:v]overlay=shortest=1,format=rgb24", "-frames:v", "1", path + ".png"], check=True)
    os.remove(path + ".rgba.png")
    print("wrote", path + ".png")


# 1: the new wheel on the machine, from the front and a little left, the pockets visible at the rim
shot(os.path.join(OUT, "bayonet_1"), (0, AY, 30), -35, 14, 0.62)
# 2: close on the pocket at 90 degrees (the top): the dog home under its roof, the finger behind it
top = (R_OUT * math.cos(math.radians(90 + TRAVEL_DEG / 2)), AY + R_OUT * math.sin(math.radians(90 + TRAVEL_DEG / 2)), Z_WHEEL + 8)
shot(os.path.join(OUT, "bayonet_2"), top, -25, 42, 0.17, hidden=("motor", "spider", "sun", "planet1", "planet2", "planet3"))

# 3: the lettering on the rim, seen from the front and a little above, the wheel's top
shot(os.path.join(OUT, "bayonet_3"), (-98, AY + 4, Z_WHEEL + 14), -30, 18, 0.26, hidden=("motor",))
