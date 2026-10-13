"""Exploded and assembled pictures of the crank charger, from its own CAD meshes, with an anchor file per picture.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python cad/exploded_figures.py -- [name ...] [--test] [--lines]

Pictures (names): assembled, machine, cartridge, hub, electronics, inside, plates. No name: all seven.
Writes exploded/_raw/<name>.png and exploded/_raw/<name>_anchors.json: where every visible part lands in the
picture (0..1 from the left and from the TOP, with its box) plus named points on parts. cad/exploded_labels.py
then draws the labels. --test: 40 percent size, 16 samples. --lines: Freestyle edge lines on top.

Same black studio, materials and meshes as cad/showcase_video.py (assembly/_build/meshes and meshes_extra, in
planetary.py's model frame: X right, Y up, Z toward the viewer, millimetres). Nothing in the CAD is touched. The
flat lay ("plates") loads the print files from cad/stl exactly as exported, so each part lies in its print orientation.
Each picture is framed twice: a first guess from the parts' bounding sphere, then the camera backs off or comes in
until the parts fill the fraction of the frame the labels leave free ("fill"), centred.
"""
import glob
import json
import math
import os
import subprocess
import sys

import bpy
import bpy_extras
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "assembly", "_build")
MESH = os.path.join(BUILD, "meshes")
EXTRA = os.path.join(BUILD, "meshes_extra")
STL = os.path.join(HERE, "stl")
OUT = os.path.join(ROOT, "exploded", "_raw")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEST = "--test" in argv
LINES = "--lines" in argv
WEB = "--web" in argv                       # no floor, transparent film, no labels: a part that floats on the website's black
NAMES = [a for a in argv if not a.startswith("--")]
S = 0.001                                   # meshes in millimetres, the scene in metres
W, H = 3200, 2260                           # A4 landscape proportions: room for labels above and below
if WEB:
    OUT = os.path.join(ROOT, "exploded", "web")

cfg = json.load(open(os.path.join(BUILD, "showcase_cfg.json")))
AY, PINS = cfg["AXLE_Y"], cfg["PINS"]

# ---------------------------------------------------------------- the scene (as the showcase video's)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
ev = sc.eevee
ev.taa_render_samples = 16 if TEST else 160
for attr, val in (("use_raytracing", True), ("use_shadows", True)):
    if hasattr(ev, attr):
        setattr(ev, attr, val)
sc.render.use_motion_blur = False
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 40 if TEST else 100
sc.render.film_transparent = True
sc.render.use_file_extension = True
im = sc.render.image_settings
if hasattr(im, "media_type"):
    im.media_type = "IMAGE"
im.file_format, im.color_mode, im.color_depth = "PNG", "RGBA", "8"
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

HDRI = next(iter(sorted(glob.glob(os.path.join(os.path.dirname(bpy.app.binary_path), "..", "Resources", "*",
                                               "datafiles", "studiolights", "world", "studio.exr")))), None)
world = bpy.data.worlds.new("studio")
world.use_nodes = True
wn = world.node_tree
bg = wn.nodes["Background"]
if HDRI:
    env = wn.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(HDRI)
    mapping = wn.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(35.0))
    wn.links.new(wn.nodes.new("ShaderNodeTexCoord").outputs["Generated"], mapping.inputs["Vector"])
    wn.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    sep = wn.nodes.new("ShaderNodeSeparateXYZ")                 # black out the HDRI's floor and horizon
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
    bg.inputs["Strength"].default_value = 1.15
else:
    bg.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1)
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


PETG_GRAPHITE = (0.085, 0.090, 0.095)
PETG_ORANGE = (0.86, 0.30, 0.035)
MAT = {
    "printed": material("petg_graphite", PETG_GRAPHITE, 0.0, 0.36, coat=0.35),
    "gear": material("petg_orange", PETG_ORANGE, 0.0, 0.40, coat=0.25),
    "grip": material("grip", (0.03, 0.03, 0.03), 0.0, 0.65),
    "bought": material("steel_satin", (0.70, 0.70, 0.71), 1.0, 0.30),
    "motor": material("anodised_black", (0.030, 0.030, 0.032), 0.55, 0.38),
    "card": material("card", (0.58, 0.46, 0.30), 0.0, 0.9),
    "diode": material("diode", (0.025, 0.025, 0.028), 0.0, 0.45),
    "pcb": material("pcb", (0.02, 0.10, 0.32), 0.0, 0.45),
    "dark": material("dark", (0.06, 0.06, 0.065), 0.0, 0.5),
    "tester": material("tester", (0.05, 0.09, 0.18), 0.0, 0.4),
    "screen": material("screen", (0.01, 0.012, 0.02), 0.0, 0.12),
    "cable": material("cable", (0.02, 0.02, 0.022), 0.0, 0.6),
    "wire": material("wire", (0.10, 0.10, 0.11), 0.0, 0.6),
    "red": material("red", (0.60, 0.05, 0.03), 0.0, 0.55),
    "phone": material("phone", (0.035, 0.035, 0.04), 0.6, 0.28),
}
for name, colour, strength in (("glyph", (0.12, 0.95, 0.35), 4.0), ("glyph_dim", (0.85, 0.85, 0.85), 1.6)):
    m = material(name, (0, 0, 0), 0.0, 1.0)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (*colour, 1.0)
    b.inputs["Emission Strength"].default_value = strength
    MAT[name] = m
ACCENT = {"ring", "sun", "planet1", "planet2", "planet3", "spider"}

floor_mat = bpy.data.materials.new("floor")
floor_mat.use_nodes = True
fn = floor_mat.node_tree
fb = fn.nodes["Principled BSDF"]
fb.inputs["Roughness"].default_value = 0.33
length = fn.nodes.new("ShaderNodeVectorMath")
length.operation = "LENGTH"
fn.links.new(fn.nodes.new("ShaderNodeTexCoord").outputs["Object"], length.inputs[0])
fade = fn.nodes.new("ShaderNodeMapRange")
fade.interpolation_type = "SMOOTHSTEP"
fade.clamp = True
fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = 0.10, 0.42
fade.inputs["To Min"].default_value, fade.inputs["To Max"].default_value = 1.0, 0.0
fn.links.new(length.outputs["Value"], fade.inputs["Value"])
for socket, gain in (("Base Color", 0.012), ("Specular IOR Level", 0.17)):     # 0.32 in the video: here the far floor stays darker, so the labels on it read
    mul = fn.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = gain
    fn.links.new(fade.outputs["Result"], mul.inputs[0])
    fn.links.new(mul.outputs[0], fb.inputs[socket])
floor_me = bpy.data.meshes.new("floor")
floor_me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
floor_me.materials.append(floor_mat)
floor = bpy.data.objects.new("floor", floor_me)
floor.scale = (5.0, 5.0, 1.0)
sc.collection.objects.link(floor)

rig = bpy.data.objects.new("rig", None)             # model frame -> world: X right, model Y up becomes world Z
rig.rotation_euler = (math.pi / 2, 0.0, 0.0)
sc.collection.objects.link(rig)

# ---------------------------------------------------------------- the parts
SKIP = {"mug", "table", "shaft_stub", "clamp1", "clamp2"}      # bench props
PINB = [f"pin_bolt{i}" for i in (1, 2, 3)]
PINW = [f"pin_w{i}{s}" for i in (1, 2, 3) for s in "ab"]
GROUPS = [                                           # the showcase's explode: how far along the axle, + toward the wheel side
    (["m5_1", "m5_2", "m5_3", "m5_4"], -125.0), (["motor"], -85.0),
    ([f"rear_nut{i}" for i in (1, 2, 3)], -80.0), ([f"rear_w{i}" for i in (1, 2, 3)], -48.0),
    (["frame"], 0.0), (["spider", "axle_bolt"] + PINB + PINW, 50.0),
    (["ring", "sun", "planet1", "planet2", "planet3", "brg_p1", "brg_p2", "brg_p3"], 100.0),
    ([f"pin_spacer{i}" for i in (1, 2, 3)], 135.0), (["axle_w1"], 168.0),
    (["wheel", "brg_a", "hub_spacer", "brg_b", "m6_nut"], 210.0), (["axle_w2"], 250.0), (["axle_nut"], 282.0),
    (["grip"], 270.0), (["m6_washer"], 305.0), (["m6_bolt"], 340.0),
]
GROUP_OFF = {n: off for names, off in GROUPS for n in names}
PLANET_IDX = {"planet1": 0, "planet2": 1, "planet3": 2}
AXLE = {"ring", "wheel", "grip", "m6_nut", "m6_washer", "m6_bolt", "hub_spacer"}
extra = json.load(open(os.path.join(EXTRA, "_extra.json")))
CARD_GROUP = {"card", "cardparts", "diodes"}
CARD_C = np.array(extra["card_centre"])
_sv = np.load(os.path.join(EXTRA, "sled.npz"))["v"]
SLED_C = (_sv.min(axis=0) + _sv.max(axis=0)) / 2
SLED_GROUP = {"sled", "pcb", "socket", "modparts", "tester", "plug", "screen", "phone_lead"}


def origin_of(n):
    if n in CARD_GROUP:
        return CARD_C.copy()
    if n in SLED_GROUP:
        return SLED_C.copy()
    if n in PLANET_IDX:
        x, y = PINS[PLANET_IDX[n]]
        return np.array([x, AY + y, 0.0])
    if n in AXLE or n == "sun":
        return np.array([0.0, AY, 0.0])
    return np.zeros(3)


def add_mesh(name, v, f, mat, parent, loc):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", v.ravel())
    me.loops.add(3 * len(f))
    me.loops.foreach_set("vertex_index", f.ravel())
    me.polygons.add(len(f))
    me.polygons.foreach_set("loop_start", np.arange(0, 3 * len(f), 3, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(f), 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(f), dtype=bool))
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.parent = parent
    ob.location = loc
    sc.collection.objects.link(ob)
    return ob


kinds = json.load(open(os.path.join(MESH, "_kinds.json")))
objs, origin, samples = {}, {}, {}
MACHINE = [n for n, k in kinds.items() if n not in SKIP and k not in ("table", "tape", "cut") and "_half" not in n]
ELEC = list(extra["roles"])
for name, kind, folder in [(n, kinds[n], MESH) for n in MACHINE] + [(n, extra["roles"][n], EXTRA) for n in ELEC]:
    d = np.load(os.path.join(folder, f"{name}.npz"))
    v, f = d["v"].astype(np.float64), d["f"].astype(np.int32)
    org = origin_of(name)
    vl = (v - org) * S
    objs[name] = add_mesh(name, vl, f, MAT["gear" if name in ACCENT else "grip" if name == "grip" else kind], rig, Vector(org * S))
    origin[name], samples[name] = org, vl[::5]

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


def light(name, loc, size, power, specular=1.0):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size, ld.shape = power, size, "SQUARE"
    if hasattr(ld, "specular_factor"):
        ld.specular_factor = specular
    lo = bpy.data.objects.new(name, ld)
    lo.parent = pivot
    lo.location = loc
    sc.collection.objects.link(lo)
    c = lo.constraints.new("TRACK_TO")
    c.target, c.track_axis, c.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"
    return lo


light("key", (-1.3, -1.1, 1.5), 1.2, 62.0, specular=0.6)
light("rim", (1.0, 1.5, 1.6), 1.2, 60.0, specular=0.2)
light("fill", (0.3, -1.7, 0.7), 1.6, 32.0, specular=0.3)

if LINES:                                            # thin edge lines: the technical-illustration look
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = 1.0
    vl = bpy.context.view_layer
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(140.0)
    ls = fs.linesets.new("edges")
    ls.select_silhouette, ls.select_crease, ls.select_border, ls.select_contour = True, True, True, False
    ls.linestyle.color = (0.72, 0.72, 0.72)
    ls.linestyle.thickness = 1.0
    ls.linestyle.alpha = 0.85

HALF_H = math.atan(18.0 / cam_data.lens)
HALF_V = math.atan(18.0 / cam_data.lens * H / W)


# ---------------------------------------------------------------- one picture
def world_points(obs):
    bpy.context.view_layer.update()
    pts = []
    for n, ob in obs.items():
        M = np.array(ob.matrix_world)
        v = samples[n]
        pts.append((np.c_[v, np.ones(len(v))] @ M.T)[:, :3])
    return np.vstack(pts)


def uv_of(p):
    uv = bpy_extras.object_utils.world_to_camera_view(sc, cam, p)
    return [round(uv.x, 4), round(1.0 - uv.y, 4)]


def aim(c, d, rot, elev):
    pivot.location = Vector(c)
    pivot.rotation_euler = (0.0, 0.0, math.radians(rot))
    el = math.radians(elev)
    cam.location = (0.0, -d * math.cos(el), d * math.sin(el))
    bpy.context.view_layer.update()


def part_boxes(obs, names):
    out = {}
    for n in names:
        ob = obs[n]
        bb = [ob.matrix_world @ Vector(cn) for cn in ob.bound_box]
        uvs = [uv_of(b) for b in bb]
        cuv = uv_of(sum(bb, Vector()) / 8)
        out[n] = dict(c=cuv, box=[round(min(u for u, _ in uvs), 4), round(min(v for _, v in uvs), 4),
                                  round(max(u for u, _ in uvs), 4), round(max(v for _, v in uvs), 4)])
    return out


def flatten(path):
    """The film is transparent (the HDRI must not show); lay the picture on black so it is a normal opaque PNG."""
    w, h = sc.render.resolution_x * sc.render.resolution_percentage // 100, sc.render.resolution_y * sc.render.resolution_percentage // 100
    tmp = path + ".rgba.png"
    os.replace(path, tmp)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}",
                    "-filter_complex", "[1:v][0:v]overlay=shortest=1,format=rgb24", "-frames:v", "1", path], check=True)
    os.remove(tmp)


def shoot(name, rot, elev, visible, moves=None, flips=None, fill=(0.66, 0.64), points=None, obs=None):
    """Pose the parts, frame them, write the anchors and the picture.

    rot: the turntable angle (0 = camera in front of the machine, 180 = behind, negative = the camera walks to
    the left). moves: part -> (dx, dy, dz) in model mm. flips: part -> degrees about its own vertical axis.
    fill: the fraction of the frame's width and height the parts may take; the rest is for the labels.
    points: key -> (part, [x, y, z] model mm on that part), followed through the part's move and flip."""
    obs = obs if obs is not None else objs
    moves, flips, points = moves or {}, flips or {}, points or {}
    for n, ob in obs.items():
        ob.hide_render = n not in visible
        if obs is objs:
            ob.location = Vector((origin[n] + np.array(moves.get(n, (0.0, 0.0, 0.0)), float)) * S)
            ob.rotation_euler = (0.0, math.radians(flips.get(n, 0.0)), 0.0)
    pts = world_points({n: obs[n] for n in visible})
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    c = (lo + hi) / 2
    r = float(np.linalg.norm(pts - c, axis=1).max())
    d = r / math.sin(min(HALF_H, HALF_V))
    aim(c, d, rot, elev)
    for _ in range(3):                                   # back off or come in, and centre, until the parts fill `fill`
        boxes = part_boxes(obs, visible)
        u0, v0 = min(b["box"][0] for b in boxes.values()), min(b["box"][1] for b in boxes.values())
        u1, v1 = max(b["box"][2] for b in boxes.values()), max(b["box"][3] for b in boxes.values())
        k = max((u1 - u0) / fill[0], (v1 - v0) / fill[1])
        M = cam.matrix_world
        right, up = Vector(M.col[0][:3]).normalized(), Vector(M.col[1][:3]).normalized()
        c = Vector(c) + right * ((u0 + u1) / 2 - 0.5) * 2 * d * math.tan(HALF_H) - up * ((v0 + v1) / 2 - 0.5) * 2 * d * math.tan(HALF_V)
        d *= k
        aim(c, d, rot, elev)
    floor.location = (c[0], c[1], 0.0)                 # the lit pool on the floor sits under the parts, not the model origin
    floor.hide_render = WEB
    parts = part_boxes(obs, visible)
    named = {}
    for key, (part, p) in points.items():
        named[key] = uv_of(obs[part].matrix_world @ Vector((np.array(p, float) - origin.get(part, np.zeros(3))) * S))
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(size=[W, H], rot=rot, elev=elev, parts=parts, points=named),
              open(os.path.join(OUT, f"{name}_anchors.json"), "w"), indent=1)
    path = os.path.join(OUT, f"{name}.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if not WEB:
        flatten(path)
    u0, v0 = min(b["box"][0] for b in parts.values()), min(b["box"][1] for b in parts.values())
    u1, v1 = max(b["box"][2] for b in parts.values()), max(b["box"][3] for b in parts.values())
    print(f"wrote {path}  ({len(parts)} parts, {len(named)} points; parts fill {u0:.2f}..{u1:.2f} x {v0:.2f}..{v1:.2f}, camera {d:.2f} m)")


def Z(z):
    return (0.0, 0.0, z)


def XYZ(x, y, z):
    return (x, y, z)


MACH = set(MACHINE)
CART = {"spider", "axle_bolt", *PINB, *PINW, "ring", "sun", "planet1", "planet2", "planet3", "brg_p1", "brg_p2", "brg_p3",
        "pin_spacer1", "pin_spacer2", "pin_spacer3"}
HUB = {"spider", "axle_bolt", "axle_w1", "brg_a", "hub_spacer", "brg_b", "wheel", "axle_w2", "axle_nut", "m6_nut", "grip",
       "m6_washer", "m6_bolt"}
WIRES = {n for n in ELEC if n.startswith("wire_")}
PHONE = {"phone", "phone_glyph", "phone_fill", "lead"}
SLED_IN = {"sled", "pcb", "socket", "modparts", "tester", "plug", "screen", "phone_lead"}
CAP = ("cardparts", [27.2, 94.8, -87.5])                     # the 1000 uF capacitor, standing on the card's low end
BASE_IN = ("frame", [-85.0, 8.0, -60.0])                     # the base's top, behind the wall, on the far side from the sled
STRETCH = 1.4                                                # the machine explode, opened up a little more than the video's

PICS = {
    "assembled": dict(rot=52.0, elev=17.0, fill=(0.60, 0.62), visible=MACH | {"shell"} | SLED_IN | PHONE | CARD_GROUP,
                      points=dict(ring_rim=("ring", [112.0, AY - 20.0, 20.0]), base=("frame", [92.0, 8.0, -30.0]),
                                  cover_side=("shell", [105.0, 95.0, -55.0]), cover_top=("shell", [60.0, 196.0, -50.0]))),
    "machine": dict(rot=-78.0, elev=16.0, fill=(0.74, 0.60), visible=MACH, moves={n: Z(o * STRETCH) for n, o in GROUP_OFF.items()}),
    "cartridge": dict(rot=-70.0, elev=22.0, fill=(0.66, 0.64), visible=CART,
                      moves={**{n: Z(60.0) for n in PINB}, **{f"pin_w{i}a": Z(-40.0) for i in (1, 2, 3)},
                             **{f"pin_w{i}b": Z(-58.0) for i in (1, 2, 3)},
                             **{n: Z(-135.0) for n in ("ring", "planet1", "planet2", "planet3")},
                             **{n: Z(-92.0) for n in ("brg_p1", "brg_p2", "brg_p3")}, "sun": Z(-215.0),
                             **{f"pin_spacer{i}": Z(-265.0) for i in (1, 2, 3)}}),
    "hub": dict(rot=-70.0, elev=20.0, fill=(0.70, 0.60), visible=HUB,
                moves=dict(axle_bolt=Z(-45.0), axle_w1=Z(35.0), brg_a=Z(65.0), hub_spacer=Z(92.0), brg_b=Z(118.0), wheel=Z(195.0),
                           axle_w2=Z(258.0), axle_nut=Z(288.0), m6_nut=Z(165.0), grip=Z(255.0), m6_washer=Z(305.0), m6_bolt=Z(345.0))),
    "electronics": dict(rot=158.0, elev=26.0, fill=(0.56, 0.70), visible=MACH | {"shell"} | CARD_GROUP | SLED_IN,
                        moves={"shell": XYZ(0.0, 215.0, -90.0), **{n: XYZ(-92.0, 20.0, -120.0) for n in CARD_GROUP},
                               "sled": XYZ(40.0, -4.0, -110.0), **{n: XYZ(40.0, 62.0, -110.0) for n in ("pcb", "socket", "modparts")},
                               **{n: XYZ(112.0, 62.0, -110.0) for n in ("tester", "plug", "screen", "phone_lead")}},
                        flips={n: 180.0 for n in CARD_GROUP}, points=dict(cap=CAP, base=BASE_IN)),
    "inside": dict(rot=150.0, elev=28.0, fill=(0.56, 0.74), visible=MACH | CARD_GROUP | SLED_IN | PHONE | WIRES,
                   points=dict(cap=CAP, base=BASE_IN)),
}

# the print files of the machine as built, as exported: (key, file under cad/stl, material)
PLATE_FILES = [
    ("frame", "frame.stl", "printed"), ("wheel", "wheel.stl", "printed"), ("gearset", "gearset_print_in_place.stl", "gear"),
    ("shell", "cover/2_cover_shell.stl", "printed"), ("spider", "spider.stl", "gear"), ("grip", "grip.stl", "printed"),
    ("hub_spacer", "hub_spacer.stl", "printed"), ("pin_spacers", "pin_spacer_x3.stl", "printed"), ("washers", "batches/plate5_washers.stl", "printed"),
]
# spare designs, test coupons and placeholders: only with --spares (he asked to see the parts he uses, nothing else)
SPARE_FILES = [
    ("ring_rear", "ring_rear_half.stl", "gear"), ("ring_front", "ring_front_half.stl", "gear"),
    ("bayonet", "spares/wheel_bayonet.stl", "printed"), ("frame_click", "spares/frame_click.stl", "printed"),
    ("clip_rear", "spares/2_ring_rear_half_clip.stl", "gear"), ("clip_front", "spares/3_ring_front_half_clip.stl", "gear"),
    ("coupon_pair", "coupon_pair_print_in_place.stl", "gear"), ("coupon_plate", "coupon_plate.stl", "printed"),
    ("cover_coupons", "cover/1_cover_coupons.stl", "printed"), ("sled", "cover/3_module_sled_PLACEHOLDER_do_not_print_yet.stl", "printed"),
    ("ring_clips", "spares/4_ring_clips.stl", "gear"), ("clip_coupon", "spares/1_ring_clip_coupon.stl", "gear"),
    ("keeper", "spares/wheel_keeper_band.stl", "printed"), ("pin_spacer_1", "spares/pin_spacer_x1.stl", "printed"),
]


def plates():
    """Every print file laid out on the floor in its print orientation, big ones at the back."""
    for ob in objs.values():
        ob.hide_render = True
    pobs, dims = {}, {}
    for key, rel, mat in PLATE_FILES + (SPARE_FILES if "--spares" in argv else []):
        path = os.path.join(STL, rel)
        if not os.path.exists(path):
            print("missing", path)
            continue
        bpy.ops.wm.stl_import(filepath=path, global_scale=S)
        ob = bpy.context.selected_objects[0]
        ob.name = key
        ob.data.transform(Matrix.Scale(S, 4))            # the importer scales the OBJECT; bake it so the mesh is in metres
        ob.scale = (1.0, 1.0, 1.0)
        ob.data.materials.clear()
        ob.data.materials.append(MAT[mat])
        for p in ob.data.polygons:
            p.use_smooth = True
        try:
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35.0))
        except Exception:
            pass
        v = np.array([vt.co for vt in ob.data.vertices])
        pobs[key], dims[key] = ob, (v.min(axis=0), v.max(axis=0))
        samples[key] = v[::5]
    gap, row_gap = 0.075, 0.19                        # room under every part for its label
    order = sorted(pobs, key=lambda k: -(dims[k][1][0] - dims[k][0][0]) * (dims[k][1][1] - dims[k][0][1]))
    rows, row, width = [], [], 0.0
    for k in order:
        w = dims[k][1][0] - dims[k][0][0]
        if row and width + w > 1.45:
            rows.append(row)
            row, width = [], 0.0
        row.append(k)
        width += w + gap
    rows.append(row)
    y = 0.0
    placed = []
    for row in rows:                                   # the first (largest) row at the back, the camera in front
        depth = max(dims[k][1][1] - dims[k][0][1] for k in row)
        width = sum(dims[k][1][0] - dims[k][0][0] for k in row) + gap * (len(row) - 1)
        x = -width / 2
        for k in row:
            lo, hi = dims[k]
            pobs[k].location = (x - lo[0], y - depth / 2 - lo[1] + (depth - (hi[1] - lo[1])) / 2, -lo[2])
            x += hi[0] - lo[0] + gap
        placed.append((y, depth))
        y -= depth + row_gap
    span = placed[0][0] - (placed[-1][0] - placed[-1][1])
    for ob in pobs.values():                          # centre the whole lay on the floor's fade
        ob.location.y += span / 2 - placed[0][0]
    floor.scale = (8.0, 8.0, 1.0)
    shoot("plates", 0.0, 52.0, set(pobs), fill=(0.72, 0.68), obs=pobs)
    floor.scale = (5.0, 5.0, 1.0)
    for ob in pobs.values():
        ob.hide_render = True


# ---------------------------------------------------------------- go
todo = NAMES or list(PICS) + ["plates"]
for name in todo:
    if name == "plates":
        plates()
    elif name in PICS:
        shoot(name, **PICS[name])
    else:
        print("no such picture:", name)
