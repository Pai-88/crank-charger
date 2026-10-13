"""Preview picture for the "base-tray" wire cover concept: two views in one PNG.

    .venv/bin/python cad/wire_cover_concept_base-tray.py           first (writes the STLs)
    .venv/bin/python cad/wire_cover_concept_base-tray_render.py    then this -> cover/concept_base-tray.png
"""
import math
import os
import sys

import numpy as np
import pyrender
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from preview import _add_edges

STL = os.path.join(HERE, "stl")
COVER = os.path.join(STL, "cover")
OUT = os.path.join(os.path.dirname(HERE), "cover", "concept_base-tray.png")
N = "base-tray"

GREY, DARK, TABLE = (0.80, 0.80, 0.82), (0.30, 0.31, 0.35), (0.93, 0.92, 0.89)
ORANGE, ORANGE_D, STEEL = (0.90, 0.45, 0.12), (0.72, 0.33, 0.08), (0.45, 0.50, 0.58)
CARD, SLATE, WHITE, INK, GREEN = (0.96, 0.94, 0.88), (0.42, 0.44, 0.50), (0.95, 0.95, 0.95), (0.08, 0.08, 0.09), (0.20, 0.45, 0.32)

MACHINE = [("_view_frame", GREY), ("_view_motor", DARK), ("_view_wheel", GREY), ("_view_ring", GREY), ("_view_grip", GREY),
           ("_view_spider", GREY), ("_view_sun", GREY), ("_view_planet1", GREY), ("_view_planet2", GREY), ("_view_planet3", GREY)]
ALWAYS = [("table", TABLE), ("clamp_l", STEEL), ("clamp_r", STEEL), ("foot", ORANGE), ("tray", ORANGE), ("channel", ORANGE),
          ("face_plate", ORANGE_D), ("module", GREEN), ("tester", WHITE), ("tester_screen", INK), ("pin", DARK), ("leads_exposed", DARK)]
INSIDE = [("card", CARD), ("card_parts", SLATE)]

TO_WORLD = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)      # model (x, y up, z front) -> world z up


def w(p):
    return np.array([p[0], -p[2], p[1]], float)


def load(path, lift=0.0):
    m = trimesh.load(path)
    m.apply_transform(TO_WORLD)
    if lift:
        m.apply_translation([0, 0, lift])
    return m


def look_at(eye, target):
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = r, u, -f, eye
    return pose


def render(items, eye, target, size, yfov=28.0):
    scene = pyrender.Scene(bg_color=[1.0, 1.0, 1.0, 1.0], ambient_light=[0.42, 0.42, 0.42])
    for mesh, col in items:
        mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[*col, 1.0], metallicFactor=0.0, roughnessFactor=1.0, doubleSided=True)
        scene.add(pyrender.Mesh.from_trimesh(mesh, material=mat, smooth=False))
    cam = pyrender.PerspectiveCamera(yfov=math.radians(yfov), znear=10, zfar=5000)
    pose = look_at(w(eye), w(target))
    scene.add(cam, pose=pose)
    for d, k in (((0.4, -0.6, 1.0), 2.4), ((-0.8, -0.3, 0.5), 1.3), ((0.3, 0.9, 0.6), 1.6), ((0.08, -0.05, 1.0), 1.6)):
        lp = look_at(np.array(d, float) * 1000, np.zeros(3))
        scene.add(pyrender.DirectionalLight(color=[1, 1, 1], intensity=k), pose=lp)
    r = pyrender.OffscreenRenderer(*size)
    color, depth = r.render(scene)
    r.delete()
    img = Image.fromarray(_add_edges(color, depth, strength=0.75))
    view = np.linalg.inv(pose)
    proj = cam.get_projection_matrix(*size)

    def px(p):
        v = proj @ view @ np.append(w(p), 1.0)
        return ((v[0] / v[3] + 1) / 2 * size[0], (1 - v[1] / v[3]) / 2 * size[1])
    return img, px


def font(sz, heavy=False):
    for path, idx in (("/System/Library/Fonts/Avenir Next.ttc", 0 if heavy else 7), ("/System/Library/Fonts/Avenir.ttc", 0),
                      ("/System/Library/Fonts/Helvetica.ttc", 0)):
        try:
            return ImageFont.truetype(path, sz, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


def call(draw, text, at, tip, f, anchor="lm"):
    draw.line([at, tip], fill=(20, 20, 20), width=2)
    draw.ellipse([tip[0] - 5, tip[1] - 5, tip[0] + 5, tip[1] + 5], fill=(20, 20, 20))
    box = draw.multiline_textbbox(at, text, font=f, anchor=anchor, spacing=6)
    draw.rectangle([box[0] - 8, box[1] - 5, box[2] + 8, box[3] + 5], fill=(255, 255, 255))
    draw.multiline_text(at, text, font=f, fill=(20, 20, 20), anchor=anchor, spacing=6)


def main():
    machine = [(load(os.path.join(STL, f"{n}.stl")), c) for n, c in MACHINE]
    part = lambda n, lift=0.0: load(os.path.join(COVER, f"_view_{N}_{n}.stl"), lift)
    always = [(part(n), c) for n, c in ALWAYS]
    W, H = 1500, 1150
    f, fh = font(30), font(46, heavy=True)

    # view 1: as filmed, from the front, lid on
    a, pa = render(machine + always + [(part("lid"), ORANGE)], eye=(520, 330, 620), target=(75, 85, -20), size=(W, H))
    d = ImageDraw.Draw(a)
    call(d, "low tray, plain lid\n139 x 117 x 31 mm", (980, 150), pa((190, 31, -30)), f)
    call(d, "USB tester plugs in here,\nin shot, clear of the crank", (60, 1040), pa((224, 20, 60)), f)
    call(d, "the wheel, gears and crank\nare not touched", (60, 110), pa((-60, 230, 45)), f)

    # view 2: from behind, lid lifted
    b, pb = render(machine + always + [(part(n), c) for n, c in INSIDE] + [(part("lid", 80.0), ORANGE)],
                   eye=(560, 420, -520), target=(95, 55, -35), size=(W, H))
    d = ImageDraw.Draw(b)
    call(d, "channel pressed onto the\nsloping rib: the four motor\nleads lie under it", (1020, 250), pb((45, 80, -56)), f)
    call(d, "foot: pinned in the base hole.\nThe G-clamp sits on it", (1010, 1020), pb((70, 22, -62)), f)
    call(d, "card on ribs", (60, 560), pb((165, 9, -5)), f)
    call(d, "module bay\n(size not known yet)", (60, 760), pb((224, 14, -40)), f)
    call(d, "lid lifts off: no screws.\nThe gap under it is the vent", (60, 250), pb((160, 126, -40)), f)
    call(d, "second clamp:\nas in step 9", (1130, 600), pb((-76, 22, -80)), f)

    sheet = Image.new("RGB", (2 * W + 30, H + 110), "white")
    sheet.paste(a, (0, 110))
    sheet.paste(b, (W + 30, 110))
    d = ImageDraw.Draw(sheet)
    d.text((40, 30), "Concept: base tray", font=fh, fill=(20, 20, 20))
    d.text((520, 44), "massing model, not a print file.   Left: from the front, as filmed.   Right: from behind, lid lifted.", font=f, fill=(70, 70, 70))
    d.line([(W + 15, 130), (W + 15, H + 90)], fill=(200, 200, 200), width=2)
    sheet.save(OUT, optimize=True)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
