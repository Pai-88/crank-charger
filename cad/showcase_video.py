"""Showcase video of the crank charger: a 360 turntable, then a true exploded view, then back together.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python cad/showcase_video.py -- 9x16
    ...                                                                                        -- 16x9
    ...                                                                                        -- stills
    ...                                                                                        -- 9x16 --test

9x16 / 16x9: 570 frames at 30 fps (19 s) to video/_frames/<tag>/, then ffmpeg writes video/crank_<tag>.mp4
and video/crank_<tag>_thumb.png (frame 1: the thumbnail IS the first screen).
stills: six 4K pictures (three angles, assembled and exploded, both aspects) to video/stills/, the inputs
for Higgsfield or any other image-to-video tool.
--test: frames 1 and 390 only, quarter size, to video/_test/.

Every part comes from assembly/_build/meshes (cad/assembly_steps_export.py), already in its assembled
place in planetary.py's model frame (X right, Y up, Z toward you). Nothing in the CAD is touched.
The gears really turn: the wheel drives the ring (dogs in notches), the carrier is the spider bolted to the
wall, so the sun turns -R/S times the ring and each planet +R/P times the ring about its own pin.
Black studio: grey printed parts, steel bought parts, black motor, a black glossy floor. No text:
titles belong in Resolve.

Timeline (frames at 30 fps):
    1 .. 240   orbit: one full turn of the camera round the machine, the wheel turning slowly
  241 .. 330   explode: fourteen groups fly apart along the axle, the near ones last; the camera dollies out
  331 .. 440   hold exploded, gears still turning, the camera drifting on round
  441 .. 528   back together, the near groups first
  529 .. 570   hold assembled
"""
import json
import math
import os
import shutil
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "assembly", "_build")
MESH = os.path.join(BUILD, "meshes")
OUT = os.path.join(ROOT, "video")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAG = next((a for a in argv if a in ("9x16", "16x9", "stills", "elec9x16", "elec16x9", "report", "reportelec")), "9x16")
TEST = "--test" in argv
ACT = "elec" if TAG.startswith("elec") or TAG == "reportelec" else "main"   # elec: act 2, the electronics, the cover and the phone
ASPECT = "16x9" if (TAG.endswith("16x9") or TAG.startswith("report")) else "9x16"
# report / reportelec: 16:9 stills for the design report plus, for each, a JSON of where every part's centre
# lands in the picture (0..1 from the left and from the bottom), so the report's labels can point at the parts.
FPS = 30
# "--long": the cut timed to the Higgsfield voice-over (video/commentary.wav, 46.1 s). Its act 1 narration ends
# at 25.66 s, so act 1 runs 770 frames (every camera and explode key stretched by 770/570, the wheel at the same
# speed) and act 2 runs 700 frames: the inside shot while the diodes, capacitor and converter are described
# (to 43.1 s), the cover-and-phone finale for the last 6 s. Files get a _46s suffix.
LONG = "--long" in argv
STRETCH = (770 / 570) if (LONG and ACT == "main") else 1.0
LAST = (700 if LONG else 360) if ACT == "elec" else (770 if LONG else 570)
SUFFIX = "_46s" if LONG else ""
# Act 2 (frames at 30 fps): two shots with a hard cut between them, no part moves except the wheel
#     1 .. 180   inside: the cover cut open, the card with its diode ladder and capacitor, the module and the
#                USB tester in their sled, the motor leads; the camera on the open side, drifting
#   181 .. 360   the product: cover on, the phone on the table charging from the tester's lead
CUT = 523 if LONG else 181
SHOTS = [dict(f0=1, f1=CUT - 1, phi=(-148.0, -196.0 if LONG else -186.0), elev=27.0, target="card", fit=0.62),
         dict(f0=CUT, f1=LAST, phi=(-290.0, -322.0), elev=15.0, target="scene", fit=1.0)]
S = 0.001                                   # the meshes are in millimetres, the scene in metres (lights, camera)

cfg = json.load(open(os.path.join(BUILD, "showcase_cfg.json")))
AY, PINS = cfg["AXLE_Y"], cfg["PINS"]
ZR, ZS, ZP = cfg["R"], cfg["S"], cfg["P"]
assert ZS + 2 * ZP == ZR, "the three gears do not mesh"
WHEEL_DEG_PER_S = 0.12 * 360.0              # the wheel: a turn every 8 s, so the sun stays under half a tooth per frame

# ---------------------------------------------------------------- what moves where
SKIP = {"mug", "table", "shaft_stub", "clamp1", "clamp2"}        # bench props and the cut-away pictures' halves


def wanted(n):
    return n not in SKIP and not n.startswith("tape") and "_half" not in n


PINB = [f"pin_bolt{i}" for i in (1, 2, 3)]
PINW = [f"pin_w{i}{s}" for i in (1, 2, 3) for s in "ab"]
# explode groups: names, how far along the axle (mm, + is toward the viewer, the wheel side)
GROUPS = [
    (["m5_1", "m5_2", "m5_3", "m5_4"], -125.0),
    (["motor"], -85.0),
    ([f"rear_nut{i}" for i in (1, 2, 3)], -80.0),
    ([f"rear_w{i}" for i in (1, 2, 3)], -48.0),
    (["frame"], 0.0),
    (["spider", "axle_bolt"] + PINB + PINW, 50.0),
    (["ring", "sun", "planet1", "planet2", "planet3", "brg_p1", "brg_p2", "brg_p3"], 100.0),
    ([f"pin_spacer{i}" for i in (1, 2, 3)], 135.0),
    (["axle_w1"], 168.0),
    (["wheel", "brg_a", "hub_spacer", "brg_b", "m6_nut"], 210.0),
    (["axle_w2"], 250.0),
    (["axle_nut"], 282.0),
    (["grip"], 270.0),
    (["m6_washer"], 305.0),
    (["m6_bolt"], 340.0),
]
NG = len(GROUPS)
RANK = {g: r for r, g in enumerate(sorted(range(NG), key=lambda g: abs(GROUPS[g][1])))}   # the wall's neighbours move first
GROUP_OF = {n: g for g, (names, _) in enumerate(GROUPS) for n in names}
AXLE = {"ring", "wheel", "grip", "m6_nut", "m6_washer", "m6_bolt", "hub_spacer"}            # turn with the wheel
PLANET_IDX = {"planet1": 0, "planet2": 1, "planet3": 2}


EXTRA = os.path.join(BUILD, "meshes_extra")
CARD_GROUP = {"card", "cardparts", "diodes"}                       # act 2: the ladder card and what stands on it
SLED_GROUP = {"sled", "pcb", "socket", "modparts", "tester", "plug", "screen", "phone_lead"}
CARD_C = SLED_C = np.zeros(3)
if ACT == "elec":
    CARD_C = np.array(json.load(open(os.path.join(EXTRA, "_extra.json")))["card_centre"])
    _sv = np.load(os.path.join(EXTRA, "sled.npz"))["v"]
    SLED_C = (_sv.min(axis=0) + _sv.max(axis=0)) / 2
CARD_OUT = np.array([0.0, 40.0, -130.0])                           # shot 1: the card floats up and back, turned to face the camera
SLED_OUT = np.array([0.0, 22.0, -130.0])                           # the sled with the module and tester comes out under it


def origin_of(n):
    """Where the part turns about, model frame. Planets about their pin, the axle set about the axle."""
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


# ---------------------------------------------------------------- the scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, LAST
ev = sc.eevee
ev.taa_render_samples = 16 if TEST else 64
for attr, val in (("use_raytracing", True), ("use_shadows", True)):
    if hasattr(ev, attr):
        setattr(ev, attr, val)
sc.render.use_motion_blur = (not TEST) and ACT == "main"   # act 2 has a hard cut: blur would smear across the camera jump
sc.render.motion_blur_shutter = 0.5
FRAMES = next((a for a in argv if a.startswith("--frames=")), None)      # --frames=A-B: re-render only these, then re-encode
if ASPECT == "16x9":
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
else:
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.resolution_percentage = 50 if TEST else 100
sc.render.film_transparent = True             # the studio HDRI lights and reflects but is never seen: black behind everything
sc.render.use_file_extension = True
im = sc.render.image_settings
if hasattr(im, "media_type"):
    im.media_type = "IMAGE"
im.file_format = "PNG"
im.color_mode = "RGBA"
im.color_depth = "8"
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

# ---- the studio: Blender's own soft-box HDRI (datafiles/studiolights/world/studio.exr), as Fusion's "Photobooth" does
HDRI = next(iter(sorted(__import__("glob").glob(os.path.join(os.path.dirname(bpy.app.binary_path), "..", "Resources", "*",
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
    # Black out the HDRI's floor and horizon: at grazing angles the glossy floor reflects the horizon at
    # full strength whatever its material says (Fresnel), and that was the grey band under the black sky.
    sep = wn.nodes.new("ShaderNodeSeparateXYZ")
    wn.links.new(wn.nodes.new("ShaderNodeTexCoord").outputs["Generated"], sep.inputs[0])
    sky = wn.nodes.new("ShaderNodeMapRange")
    sky.interpolation_type, sky.clamp = "SMOOTHSTEP", True
    sky.inputs["From Min"].default_value, sky.inputs["From Max"].default_value = 0.12, 0.45
    wn.links.new(sep.outputs["Z"], sky.inputs["Value"])
    gate = wn.nodes.new("ShaderNodeMix")
    gate.data_type, gate.blend_type = "RGBA", "MULTIPLY"
    gate.inputs["Factor"].default_value = 1.0
    wn.links.new(env.outputs["Color"], gate.inputs[6])         # A (RGBA sockets are 6 and 7 on the Mix node)
    wn.links.new(sky.outputs["Result"], gate.inputs[7])        # B
    wn.links.new(gate.outputs[2], bg.inputs["Color"])          # Result (RGBA)
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


# Fusion-style appearances: graphite PETG for the structure, orange PETG for the mechanism, satin steel
# hardware, anodised black motor. Change the two colour triples here for other rolls.
PETG_GRAPHITE = (0.085, 0.090, 0.095)
PETG_ORANGE = (0.86, 0.30, 0.035)
MAT = {
    "printed": material("petg_graphite", PETG_GRAPHITE, 0.0, 0.36, coat=0.35),
    "gear": material("petg_orange", PETG_ORANGE, 0.0, 0.40, coat=0.25),
    "grip": material("grip", (0.03, 0.03, 0.03), 0.0, 0.65),                 # rubbery hand grip
    "bought": material("steel_satin", (0.70, 0.70, 0.71), 1.0, 0.30),
    "motor": material("anodised_black", (0.030, 0.030, 0.032), 0.55, 0.38),
    # act 2
    "card": material("card", (0.58, 0.46, 0.30), 0.0, 0.9),                 # the stiff card the ladder is built on
    "diode": material("diode", (0.025, 0.025, 0.028), 0.0, 0.45),           # SB560 bodies and leads
    "pcb": material("pcb", (0.02, 0.10, 0.32), 0.0, 0.45),                  # the buck module's solder mask
    "dark": material("dark", (0.06, 0.06, 0.065), 0.0, 0.5),
    "tester": material("tester", (0.05, 0.09, 0.18), 0.0, 0.4),
    "screen": material("screen", (0.01, 0.012, 0.02), 0.0, 0.12),
    "cable": material("cable", (0.02, 0.02, 0.022), 0.0, 0.6),
    "wire": material("wire", (0.10, 0.10, 0.11), 0.0, 0.6),                 # the motor's four leads and their bundle
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

floor_mat = bpy.data.materials.new("floor")            # a dark glossy pool under the machine, fading to nothing
floor_mat.use_nodes = True
fn = floor_mat.node_tree
fb = fn.nodes["Principled BSDF"]
fb.inputs["Roughness"].default_value = 0.33
# Fade by distance from the floor's centre, written out in maths (the Gradient node's "spherical" falloff
# is not 1 - r). The fade darkens instead of using alpha: far from the machine the floor goes to true
# black and stops reflecting, so there is no horizon line against the black backdrop.
length = fn.nodes.new("ShaderNodeVectorMath")
length.operation = "LENGTH"
fn.links.new(fn.nodes.new("ShaderNodeTexCoord").outputs["Object"], length.inputs[0])    # the mesh runs -1..1
fade = fn.nodes.new("ShaderNodeMapRange")
fade.interpolation_type = "SMOOTHSTEP"
fade.clamp = True
fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = 0.10, 0.42     # with the 5 m floor: 0.5 to 2.1 m
# AgX lifts near-black into visible grey, so the fade must reach EXACTLY zero well inside the frame; the
# plane's own edge then lies in true black and never shows.
fade.inputs["To Min"].default_value, fade.inputs["To Max"].default_value = 1.0, 0.0
fn.links.new(length.outputs["Value"], fade.inputs["Value"])
for socket, gain in (("Base Color", 0.012), ("Specular IOR Level", 0.32)):
    mul = fn.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = gain
    fn.links.new(fade.outputs["Result"], mul.inputs[0])
    fn.links.new(mul.outputs[0], fb.inputs[socket])

rig = bpy.data.objects.new("rig", None)             # model frame -> world: X right, model Y up becomes world Z
rig.rotation_euler = (math.pi / 2, 0.0, 0.0)
sc.collection.objects.link(rig)

kinds = json.load(open(os.path.join(MESH, "_kinds.json")))
objs, origin, pts_assembled, pts_exploded = {}, {}, [], []
extra = json.load(open(os.path.join(EXTRA, "_extra.json"))) if ACT == "elec" else dict(roles={})
loads = [(n, k, MESH) for n, k in kinds.items() if wanted(n)] + [(n, r, EXTRA) for n, r in extra["roles"].items()]
for name, kind, folder in loads:
    d = np.load(os.path.join(folder, f"{name}.npz"))
    v, f = d["v"].astype(np.float64), d["f"].astype(np.int32)
    org = origin_of(name)
    off = np.array([0.0, 0.0, GROUPS[GROUP_OF[name]][1]]) if name in GROUP_OF else np.zeros(3)
    if folder == MESH or name in ("shell", "phone", "lead"):      # the scene's extent: machine, cover, phone
        pts_assembled.append(v[::7])
        pts_exploded.append(v[::7] + off)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", ((v - org) * S).ravel())
    me.loops.add(3 * len(f))
    me.loops.foreach_set("vertex_index", f.ravel())
    me.polygons.add(len(f))
    me.polygons.foreach_set("loop_start", np.arange(0, 3 * len(f), 3, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(f), 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(f), dtype=bool))
    me.materials.append(MAT["gear" if name in ACCENT else "grip" if name == "grip" else kind])
    ob = bpy.data.objects.new(name, me)
    ob.parent = rig
    ob.location = Vector(org * S)
    sc.collection.objects.link(ob)
    objs[name], origin[name] = ob, org

floor_me = bpy.data.meshes.new("floor")                # object coordinates run -1..1 across it, so the fade is in its own frame
floor_me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
floor_me.materials.append(floor_mat)
floor = bpy.data.objects.new("floor", floor_me)
floor.scale = (5.0, 5.0, 1.0)
sc.collection.objects.link(floor)


def to_world(p):                                   # model mm -> world metres
    return Vector((p[0] * S, -p[2] * S, p[1] * S))


def centre_radius(pts):
    pts = np.vstack(pts)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    c = (lo + hi) / 2
    return c, float(np.linalg.norm(pts - c, axis=1).max())


C1, R1 = centre_radius(pts_assembled)
C2, R2 = centre_radius(pts_exploded)
C1[1] += 8.0                                       # a little headroom: the wheel is the hero, not the base
C2[1] += 8.0

pivot = bpy.data.objects.new("pivot", None)
sc.collection.objects.link(pivot)
cam_data = bpy.data.cameras.new("cam")
cam_data.lens, cam_data.sensor_width, cam_data.sensor_fit = 50.0, 36.0, "HORIZONTAL"
cam_data.clip_start, cam_data.clip_end = 0.01, 50.0
cam = bpy.data.objects.new("cam", cam_data)
cam.parent = pivot
sc.collection.objects.link(cam)
sc.camera = cam
ELEV = math.radians(16.0)
AZ0 = -56.0                                        # the step pictures' view: front, a little from the left

half_h = math.atan(18.0 / cam_data.lens)
half_v = math.atan(18.0 / cam_data.lens * sc.render.resolution_y / sc.render.resolution_x)
MARGIN = {"16x9": 1.1}.get(TAG, 1.0)              # portrait: the machine fills the width, the bounding sphere is generous
FIT = MARGIN / math.sin(min(half_h, half_v))
D1, D2 = R1 * S * FIT, R2 * S * FIT


def light(name, loc, size, power, specular=1.0):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size, ld.shape = power, size, "SQUARE"
    if hasattr(ld, "specular_factor"):
        ld.specular_factor = specular                 # how much of the lamp shows as a reflection (the floor hot spots)
    lo = bpy.data.objects.new(name, ld)
    lo.parent = pivot                                # the studio turns with the camera: a turntable, lit once
    lo.location = loc
    sc.collection.objects.link(lo)
    for target_ob in (lo,):
        c = target_ob.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"
    return lo


light("key", (-1.3, -1.1, 1.5), 1.2, 62.0, specular=0.6)    # watts: one softbox for a defined highlight; the HDRI does the rest
light("rim", (1.0, 1.5, 1.6), 1.2, 60.0, specular=0.2)      # its reflection was the white blob on the floor
light("fill", (0.3, -1.7, 0.7), 1.6, 32.0, specular=0.3)    # from beside the camera, so the faces toward you are never mud
con = cam.constraints.new("TRACK_TO")
con.target, con.track_axis, con.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"


# ---------------------------------------------------------------- the motion, evaluated per (sub)frame
def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def hermite(f, keys):
    """Piecewise cubic through (frame, value, slope) keys: a camera move with no kink in its speed."""
    for (f0, v0, m0), (f1, v1, m1) in zip(keys, keys[1:]):
        if f <= f1:
            h = f1 - f0
            t = (f - f0) / h
            return ((2 * t ** 3 - 3 * t ** 2 + 1) * v0 + (t ** 3 - 2 * t ** 2 + t) * h * m0
                    + (-2 * t ** 3 + 3 * t ** 2) * v1 + (t ** 3 - t ** 2) * h * m1)
    return keys[-1][1]


AZ_KEYS = [(1, 0.0, 0.0), (240, 360.0, 1.2), (570, 720.0, 0.0)]         # two orbits: one assembled, one round the exploded
                                                                          # machine; slow in, no kink, slow out on the start view.
                                                                          # Keys live in the 570-frame cut's time (see STRETCH), never LAST.


def group_t(g, f):
    w = RANK[g]
    s1, s2 = 241 + 3 * w, 441 + 3 * (NG - 1 - w)
    if f < s1:
        return 0.0
    if f < s2:
        return smooth((f - s1) / 48.0)
    return 1.0 - smooth((f - s2) / 48.0)


def dolly_t(f):
    if f < 241:
        return 0.0
    if f < 441:
        return smooth((f - 241) / 89.0)
    return 1.0 - smooth((f - 441) / 87.0)


OVERRIDE = {}                                        # the stills set az / explode / theta by hand


def pose(f):
    theta = OVERRIDE.get("theta", WHEEL_DEG_PER_S * (f - 1) / FPS)
    f = 1 + (f - 1) / STRETCH                            # the keys below are in the 570-frame cut's time
    az = OVERRIDE.get("az", hermite(f, AZ_KEYS))
    for g, (names, off) in enumerate(GROUPS):
        t = OVERRIDE.get("explode", group_t(g, f))
        for n in names:
            objs[n].location = Vector((origin[n] + np.array([0.0, 0.0, off * t])) * S)
    for n in AXLE:
        objs[n].rotation_euler = (0.0, 0.0, math.radians(theta))
    objs["sun"].rotation_euler = (0.0, 0.0, math.radians(-ZR / ZS * theta))
    for n in PLANET_IDX:
        objs[n].rotation_euler = (0.0, 0.0, math.radians(ZR / ZP * theta))
    k = OVERRIDE.get("explode", dolly_t(f))
    pivot.location = to_world(C1 + (C2 - C1) * k)
    pivot.rotation_euler = (0.0, 0.0, math.radians(AZ0 - az))
    d = D1 + (D2 - D1) * k
    cam.location = (0.0, -d * math.cos(ELEV), d * math.sin(ELEV))


def pose_elec(f):
    """Act 2: nothing moves but the wheel and the camera; a hard cut between the two shots."""
    theta = WHEEL_DEG_PER_S * (f - 1) / FPS
    for n in AXLE:
        objs[n].rotation_euler = (0.0, 0.0, math.radians(theta))
    objs["sun"].rotation_euler = (0.0, 0.0, math.radians(-ZR / ZS * theta))
    for n in PLANET_IDX:
        objs[n].rotation_euler = (0.0, 0.0, math.radians(ZR / ZP * theta))
    shot = SHOTS[0] if f <= SHOTS[0]["f1"] else SHOTS[1]
    inside = shot is SHOTS[0]
    for n, hidden in ELEC_HIDE.items():
        objs[n].hide_render = hidden[0] if inside else hidden[1]
    for n in CARD_GROUP:                                 # shot 1: out, turned round to show the ladder; shot 2: home
        objs[n].location = Vector((origin[n] + (CARD_OUT if inside else 0.0)) * S)
        objs[n].rotation_euler = (0.0, math.pi if inside else 0.0, 0.0)
    for n in SLED_GROUP:
        objs[n].location = Vector((origin[n] + (SLED_OUT if inside else 0.0)) * S)
    t = smooth((f - shot["f0"]) / (shot["f1"] - shot["f0"]))
    phi = shot["phi"][0] + (shot["phi"][1] - shot["phi"][0]) * t
    if shot["target"] == "card":
        target = (CARD_C + CARD_OUT + SLED_C + SLED_OUT) / 2 + np.array([0.0, 0.0, 10.0])
        d = 0.21 * FIT * shot["fit"]                                                  # the floating card and module, about 210 mm across
    else:
        target, d = C1, D1 * shot["fit"]
    el = math.radians(shot["elev"])
    pivot.location = to_world(target)
    pivot.rotation_euler = (0.0, 0.0, math.radians(phi))
    cam.location = (0.0, -d * math.cos(el), d * math.sin(el))


def on_frame(scene):
    (pose_elec if ACT == "elec" else pose)(scene.frame_current_final)


bpy.app.handlers.frame_change_pre.append(on_frame)
# act 2 visibility: name -> (hidden in shot 1, hidden in shot 2). Shot 1 shows the parts out in the open, so the
# cover and the wires (which run to where the card sits when home) stay out of it.
ELEC_HIDE = {}
if ACT == "elec":
    ELEC_HIDE = {"shell": (True, False), "shell_open": (True, True),
                 "phone": (True, False), "phone_glyph": (True, False), "phone_fill": (True, False), "lead": (True, False)}
    ELEC_HIDE.update({n: (True, False) for n in objs if n.startswith("wire_")})
    for n, (h1, h2) in ELEC_HIDE.items():                # keyed too, so the render never trusts the handler alone
        for f, hidden in ((1, h1), (SHOTS[1]["f0"], h2)):
            objs[n].hide_render = hidden
            objs[n].keyframe_insert("hide_render", frame=f)


def flatten(path, w, h):
    """The film is transparent (the HDRI must not show); lay the picture on black so it is a normal opaque PNG."""
    tmp = path + ".rgba.png"
    os.replace(path, tmp)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}",
                    "-filter_complex", "[1:v][0:v]overlay=shortest=1,format=rgb24", "-frames:v", "1", path], check=True)
    os.remove(tmp)


def render_still(path, f):
    sc.frame_set(f)
    pose(f)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    flatten(path, sc.render.resolution_x * sc.render.resolution_percentage // 100,
            sc.render.resolution_y * sc.render.resolution_percentage // 100)
    print("wrote", path)


# ---------------------------------------------------------------- go
print(f"{len(objs)} parts; assembled radius {R1:.0f} mm, exploded {R2:.0f} mm; camera {D1:.2f} -> {D2:.2f} m")
if TEST:
    os.makedirs(os.path.join(OUT, "_test"), exist_ok=True)
    for f in ((60, 270) if ACT == "elec" else (1, 390)):
        render_still(os.path.join(OUT, "_test", f"{TAG}_f{f:04d}.png"), f)
elif TAG in ("report", "reportelec"):
    import bpy_extras
    rep = os.path.join(ROOT, "video", "report")
    os.makedirs(rep, exist_ok=True)
    ev.taa_render_samples = 128
    sc.render.use_motion_blur = False
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1350
    half_v = math.atan(18.0 / cam_data.lens * 1350 / 2400)
    FIT = 1.1 / math.sin(min(half_h, half_v))
    D1, D2 = R1 * S * FIT, R2 * S * FIT

    def anchors(path):
        """Where each part's centre lands in the picture, 0..1 from the left and from the bottom; off-screen parts dropped."""
        bpy.context.view_layer.update()
        out = {}
        for n, ob in objs.items():
            if ob.hide_render:
                continue
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            c = sum(bb, Vector((0, 0, 0))) / 8
            uv = bpy_extras.object_utils.world_to_camera_view(sc, cam, c)
            if 0.0 <= uv.x <= 1.0 and 0.0 <= uv.y <= 1.0 and uv.z > 0:
                out[n] = [round(uv.x, 4), round(uv.y, 4)]
        json.dump(out, open(path, "w"), indent=1)

    if ACT == "main":
        for label, az, explode in (("assembled", 8.0, 0.0), ("exploded", 22.0, 1.0)):
            OVERRIDE.update(az=az, explode=explode, theta=0.0)
            pose(1)
            anchors(os.path.join(rep, f"{label}_anchors.json"))
            render_still(os.path.join(rep, f"{label}.png"), 1)
    else:
        SHOTS[0]["phi"] = (-160.0, -160.0)
        pose_elec(60)
        anchors(os.path.join(rep, "electronics_anchors.json"))
        render_still(os.path.join(rep, "electronics.png"), 60)
elif TAG == "stills":
    os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
    ev.taa_render_samples = 128
    sc.render.use_motion_blur = False
    for aspect, (w, h) in (("9x16", (2160, 3840)), ("16x9", (3840, 2160))):
        sc.render.resolution_x, sc.render.resolution_y = w, h
        half_v = math.atan(18.0 / cam_data.lens * h / w)
        FIT = (1.1 if aspect == "16x9" else 1.0) / math.sin(min(half_h, half_v))
        D1, D2 = R1 * S * FIT, R2 * S * FIT
        for label, az, explode in (("front", 0.0, 0.0), ("left", 110.0, 0.0), ("back", 215.0, 0.0), ("exploded", 25.0, 1.0)):
            OVERRIDE.update(az=az, explode=explode, theta=0.0)
            render_still(os.path.join(OUT, "stills", f"crank_{label}_{aspect}.png"), 1)
else:
    frames = os.path.join(OUT, "_frames", TAG + SUFFIX)
    if FRAMES:
        a, b = (int(v) for v in FRAMES.split("=")[1].split("-"))
        sc.frame_start, sc.frame_end = a, b
        print(f"re-rendering frames {a} to {b} only")
    else:
        shutil.rmtree(frames, ignore_errors=True)
    os.makedirs(frames, exist_ok=True)
    sc.render.filepath = os.path.join(frames, "f_")
    bpy.ops.render.render(animation=True)
    mp4 = os.path.join(OUT, f"crank_{TAG}{SUFFIX}.mp4")
    w, h = sc.render.resolution_x, sc.render.resolution_y
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(frames, "f_%04d.png"),
                    "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={FPS}",
                    "-filter_complex", "[1:v][0:v]overlay=shortest=1,format=yuv420p",
                    "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-movflags", "+faststart", mp4], check=True)
    thumb = os.path.join(OUT, f"crank_{TAG}{SUFFIX}_thumb.png")
    shutil.copy(os.path.join(frames, "f_0001.png"), thumb)
    flatten(thumb, w, h)
    print("wrote", mp4)
