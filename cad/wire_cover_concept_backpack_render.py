"""Picture of the "backpack" wire cover concept: closed, and with the shell ghosted.

    .venv/bin/python cad/wire_cover_concept_backpack.py           first (writes the view STLs)
    .venv/bin/python cad/wire_cover_concept_backpack_render.py    then this -> cover/concept_backpack.png
"""
import os

import numpy as np
import pyrender
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "stl")
COVER = os.path.join(STL, "cover")
OUT = os.path.join(os.path.dirname(HERE), "cover", "concept_backpack.png")
AVENIR = "/System/Library/Fonts/Avenir.ttc"

GREY = (0.80, 0.80, 0.82, 1.0)
GREY_D = (0.66, 0.67, 0.70, 1.0)
SLATE = (0.36, 0.38, 0.43, 1.0)
ORANGE = (0.97, 0.47, 0.10, 1.0)
CARD = (0.95, 0.92, 0.84, 1.0)
STEEL = (0.56, 0.58, 0.62, 1.0)
GREEN = (0.16, 0.42, 0.30, 1.0)
BLACK = (0.10, 0.10, 0.11, 1.0)
TABLE = (0.91, 0.89, 0.85, 1.0)
CLAMP = (0.25, 0.30, 0.40, 1.0)

FIXED = [("_view_frame.stl", GREY), ("_view_motor.stl", SLATE), ("_view_wheel.stl", GREY), ("_view_ring.stl", GREY_D),
         ("_view_spider.stl", GREY_D), ("_view_grip.stl", GREY), ("_view_planet1.stl", GREY_D),
         ("_view_planet2.stl", GREY_D), ("_view_planet3.stl", GREY_D), ("_view_sun.stl", GREY_D)]
INSIDE = [("card", CARD), ("card_parts", SLATE), ("module", GREEN), ("toggle1", ORANGE), ("toggle2", ORANGE),
          ("bridge", ORANGE), ("bolts", BLACK)]
OUTSIDE = [("tester", BLACK), ("clamp_l", CLAMP), ("clamp_r", CLAMP)]


def _mesh(path, colour, smooth=False):
    tm = trimesh.load(path, force="mesh")
    mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=colour, metallicFactor=0.05, roughnessFactor=0.75,
                                             alphaMode="BLEND" if colour[3] < 1 else "OPAQUE", doubleSided=True)
    return pyrender.Mesh.from_trimesh(tm, material=mat, smooth=smooth)


def _tube(points, r, colour):
    parts = []
    for a, b in zip(points[:-1], points[1:]):
        parts.append(trimesh.creation.cylinder(radius=r, segment=[a, b], sections=12))
        parts.append(trimesh.creation.icosphere(subdivisions=1, radius=r).apply_translation(b))
    tm = trimesh.util.concatenate(parts)
    mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=colour, metallicFactor=0.0, roughnessFactor=0.8)
    return pyrender.Mesh.from_trimesh(tm, material=mat, smooth=True)


def _look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = (np.array(v, float) for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = r, u, -f, eye
    return pose


def scene(shell_colour, show_inside, eye, target, mag):
    sc = pyrender.Scene(bg_color=np.array([1.0, 1.0, 1.0, 1.0]), ambient_light=[0.55, 0.55, 0.55])
    for name, col in FIXED:
        sc.add(_mesh(os.path.join(STL, name), col))
    table = trimesh.creation.box(extents=[620, 30, 420], transform=trimesh.transformations.translation_matrix([40, -15, -93 + 210]))
    sc.add(pyrender.Mesh.from_trimesh(table, material=pyrender.MetallicRoughnessMaterial(baseColorFactor=TABLE, roughnessFactor=0.9),
                                      smooth=False))
    for name, col in OUTSIDE + (INSIDE if show_inside else []):
        sc.add(_mesh(os.path.join(COVER, f"_view_backpack_{name}.stl"), col))
    if show_inside:
        # four motor leads: out of the top of the motor's back end, a loop of spare, down to the card's four joints
        for i in range(4):
            x_j = -35.0 + 12 * i
            pts = [(-9 + 6 * i, 172.5, -52), (-9 + 6 * i, 184, -55), (-18 + 4 * i, 186, -70), (x_j, 172, -80),
                   (x_j, 140, -80), (x_j, 82, -81), (x_j, 82, -84)]
            sc.add(_tube(pts, 1.1, (0.55, 0.57, 0.62, 1.0)))
        # two output wires: card's right end up to the module
        for dy, col in ((0, (0.78, 0.16, 0.13, 1.0)), (4, BLACK)):
            pts = [(33, 110 + dy * 3, -83), (44, 132, -80), (40, 160 + dy, -80), (31, 168 + dy, -87)]
            sc.add(_tube(pts, 1.3, col))
    # phone cable out of the tester's far end
    sc.add(_tube([(136, 171, -84.9), (165, 171, -84.9), (190, 150, -70), (205, 60, -40), (210, 4, 0), (215, 4, 90)], 1.8,
                 (0.93, 0.93, 0.94, 1.0)))
    sc.add(_mesh(os.path.join(COVER, "_view_backpack_shell.stl"), shell_colour))
    cam = pyrender.OrthographicCamera(xmag=mag, ymag=mag, znear=1, zfar=3000)
    pose = _look_at(eye, target)
    sc.add(cam, pose=pose)
    for d, inten in (((0.2, 1.0, -0.35), 4.0), ((1.0, 0.35, -0.5), 2.2), ((-0.6, 0.3, -1.0), 2.6), ((0.6, 0.3, 0.8), 1.2)):
        lp = _look_at(np.array(d) * 1000, (0, 0, 0))
        sc.add(pyrender.DirectionalLight(color=[1, 1, 1], intensity=inten), pose=lp)
    return sc


def shot(shell_colour, show_inside, eye, target, mag, w, h):
    r = pyrender.OffscreenRenderer(w, h)
    colour, depth = r.render(scene(shell_colour, show_inside, eye, target, mag))
    r.delete()
    # thin dark outlines wherever the depth jumps, so grey parts do not melt into each other
    d = np.where(depth == 0, depth.max() + 50, depth)
    gx, gy = np.abs(np.diff(d, axis=1, prepend=d[:, :1])), np.abs(np.diff(d, axis=0, prepend=d[:1, :]))
    edge = (gx + gy) > 0.004
    edge = edge | np.roll(edge, 1, 0) | np.roll(edge, 1, 1)
    img = colour.copy()
    img[edge] = (img[edge] * 0.25).astype(np.uint8)
    return Image.fromarray(img)


def project(pt, eye, target, mag, w, h):
    """Model point -> pixel, for the orthographic camera above."""
    pose = _look_at(eye, target)
    v = np.linalg.inv(pose) @ np.array([pt[0], pt[1], pt[2], 1.0])
    aspect = w / h
    return (w / 2 + v[0] / (mag * aspect) * w / 2, h / 2 - v[1] / mag * h / 2)


if __name__ == "__main__":
    W, H = 1500, 1500
    eye, target, mag = (420, 330, -560), (25, 70, -20), 215
    closed = shot(ORANGE, False, eye, target, mag, W, H)
    ghost = shot((0.97, 0.47, 0.10, 0.20), True, eye, target, mag, W, H)
    # straight from behind, shell ghosted: where each thing sits on the back panel
    BW, BH = 1300, 1300
    b_eye, b_target, b_mag = (0, 105, -900), (0, 105, 0), 150
    back = shot((0.97, 0.47, 0.10, 0.14), True, b_eye, b_target, b_mag, BW, BH)
    TOP = 190
    sheet = Image.new("RGB", (W * 2 + BW, H + TOP + 110), (255, 255, 255))
    sheet.paste(closed, (0, TOP))
    sheet.paste(ghost, (W, TOP))
    sheet.paste(back, (2 * W, TOP + 100))
    d = ImageDraw.Draw(sheet)
    big, mid, small = (ImageFont.truetype(AVENIR, 80, index=5), ImageFont.truetype(AVENIR, 46, index=0),
                       ImageFont.truetype(AVENIR, 38, index=0))
    INK = (20, 20, 22)
    d.text((50, 30), "Concept: backpack", font=big, fill=INK)
    d.text((800, 62), "one shell behind the wall, held by the two G-clamps you already use", font=mid, fill=INK)
    d.text((60, H + TOP + 30), "closed: what the camera sees from behind", font=mid, fill=INK)
    d.text((W + 60, H + TOP + 30), "the same, shell made see-through", font=mid, fill=INK)
    d.text((2 * W + 60, H + TOP + 30), "straight from behind, see-through", font=mid, fill=INK)

    def call(panel_x, panel_y, cam, size, pt, text_xy, text):
        px, py = project(pt, cam[0], cam[1], cam[2], size[0], size[1])
        px, py = px + panel_x, py + panel_y
        tx, ty = text_xy
        box = d.textbbox((tx, ty), text, font=small)
        start = (tx + 20, box[3] + 8) if py > box[3] else (tx + 20, box[1] - 8)
        d.line([start, (px, py)], fill=INK, width=3)
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=INK)
        d.rectangle([box[0] - 8, box[1] - 6, box[2] + 8, box[3] + 6], fill=(255, 255, 255))
        d.text((tx, ty), text, font=small, fill=INK)

    c1 = (eye, target, mag)
    call(0, TOP, c1, (W, H), (105, 171, -85), (30, 300), "USB tester plugs in here")
    call(0, TOP, c1, (W, H), (-86, 12, -80), (900, 1440), "G-clamp sits on the cover's foot")
    call(0, TOP, c1, (W, H), (0, 195, -12), (700, 215), "air slot along the top, against the wall")
    cb = (b_eye, b_target, b_mag)
    ox, oy = 2 * W, TOP + 100
    call(ox, oy, cb, (BW, BH), (-20, 90, -88), (ox + 760, oy + 1130), "card: diodes, capacitor, light")
    call(ox, oy, cb, (BW, BH), (45, 171, -88), (ox + 30, oy + 60), "module (size not known yet)")
    call(ox, oy, cb, (BW, BH), (-17, 160, -80), (ox + 760, oy + 60), "four motor leads, all inside")
    sheet.save(OUT, optimize=True)
    print("wrote", OUT, sheet.size)
