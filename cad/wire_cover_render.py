"""Step pictures for the wire cover, in the style of assembly/step_*.png: flat shading, dark
outlines, orange for the part in hand, Avenir call-outs.

Everything drawn is the real solid from cad/wire_cover.py (shell, sled, card and its parts,
wires, clamps) and the machine's own view meshes in cad/stl/. No picture is edited by hand.

    .venv/bin/python cad/wire_cover_render.py            all pictures into cover/ (cover_00 to cover_06)
    .venv/bin/python cad/wire_cover_render.py 3 5        only cover_03 and cover_05
"""
import math
import os
import sys

import cadquery as cq
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wire_cover as wc

ROOT = os.path.dirname(HERE)
PICS = os.path.join(ROOT, "cover")
VIEW = os.path.join(wc.OUT, "_view_NOT_FOR_PRINTING")
SS = 2
AVENIR = "/System/Library/Fonts/Avenir.ttc"
HEAVY, MEDIUM, ROMAN = 4, 8, 11
PX_STEP, PX_LINE, PX_CALL = 76, 46, 40
INK = (20, 20, 22)
ROLE = {
    "printed": (0.90, 0.90, 0.91), "bought": (0.56, 0.58, 0.62), "motor": (0.40, 0.42, 0.46), "table": (0.97, 0.955, 0.93),
    "tape": (0.97, 0.87, 0.50), "accent": (0.97, 0.47, 0.10), "accent2": (0.99, 0.72, 0.42), "card": (0.95, 0.93, 0.86),
    "metal": (0.62, 0.64, 0.68), "dark": (0.25, 0.26, 0.29), "red": (0.80, 0.16, 0.13), "black": (0.16, 0.16, 0.18),
    "blue": (0.24, 0.47, 0.76), "green": (0.20, 0.50, 0.33), "screen": (0.10, 0.12, 0.16), "shell": (0.33, 0.35, 0.39),
    "wire": (0.93, 0.62, 0.15), "book": (0.78, 0.83, 0.90),
}
LINE = np.array([0.10, 0.10, 0.12])
ARROW = (176, 62, 0)
LIGHT = np.array([-0.38, 0.52, 0.76])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
W = 2000


def font(index, px):
    return ImageFont.truetype(AVENIR, int(round(px * SS)), index=index)


# ============================================================ meshes
_cache = {}


def mesh(name, build, tol=0.05):
    """A cadquery solid as a trimesh, through an STL in the view folder (never a print file)."""
    if name not in _cache:
        os.makedirs(VIEW, exist_ok=True)
        path = os.path.join(VIEW, name + ".stl")
        cq.exporters.export(build(), path, tolerance=tol, angularTolerance=0.3)
        _cache[name] = trimesh.load(path, force="mesh")
    return _cache[name]


def machine(name):
    if name not in _cache:
        _cache[name] = trimesh.load(os.path.join(HERE, "stl", f"_view_{name}.stl"), force="mesh")
    return _cache[name]


TURNING = ("wheel", "ring", "planet1", "planet2", "planet3", "sun", "spider", "grip")


def moved(m, mat):
    m = m.copy()
    m.apply_transform(mat)
    return m


def shift(dx=0.0, dy=0.0, dz=0.0):
    return trimesh.transformations.translation_matrix([dx, dy, dz])


def lie():
    """wire_cover.lie_point() as a matrix: the shell on its back on the books behind the machine."""
    r = trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0])      # y' = z, z' = -y
    return shift(0, -wc.Z_BACK + wc.LIE_BOX, wc.BASE_BACK - wc.LIE_GAP + wc.BASE_TOP) @ r


def box(x0, x1, y0, y1, z0, z1):
    return wc._box(x0, x1, y0, y1, z0, z1)


def parts():
    """name -> (trimesh, role), everything in its seated place in the model frame."""
    S = wc.USB_SIDE
    sh = wc.shell()
    P = {}
    P["shell"] = (mesh("shell", lambda: sh), "accent")
    P["shell_open"] = (mesh("shell_open", lambda: sh.cut(box(-200, -47.5, -50, 400, -200, 50)).cut(box(-200, 200, 183, 400, -200, 50))), "accent")
    P["shell_back"] = (mesh("shell_back", lambda: sh.cut(box(-200, 200, -50, 400, -40, 50))), "accent")
    P["shell_corner"] = (mesh("shell_corner", lambda: sh.cut(box(-200, 200, -50, 400, -52, 50)).cut(box(-S * 400, -S * 6, -50, 400, -200, 50))
                              .cut(box(-200, 200, 104, 400, -200, 50))), "accent")
    P["shell_pocket"] = (mesh("shell_pocket", lambda: sh.cut(box(-200, 200, -50, 400, -52, 50)).cut(box(52, 400, -50, 400, -200, 50))), "accent")
    P["sled"] = (mesh("sled", wc.sled), "accent2")
    mod = wc.module_dummy()
    P["pcb"] = (mesh("pcb", lambda: mod["pcb"]), "green")
    P["socket"] = (mesh("socket", lambda: mod["socket"]), "metal")
    P["modparts"] = (mesh("modparts", lambda: mod["parts"]), "dark")
    tst = wc.tester_dummy()
    P["tester"] = (mesh("tester", lambda: tst["body"]), "blue")
    P["plug"] = (mesh("plug", lambda: tst["plug"]), "metal")
    yc, zc = wc._usb_centre()
    x0 = wc.tester_face_x()
    P["screen"] = (mesh("screen", lambda: wc._mirror(box(x0 + 14, x0 + 44, yc - 8, yc + 8, zc - wc.TESTER[2] / 2 - 0.4, zc - wc.TESTER[2] / 2 + 0.2), S)), "screen")
    P["phone_lead"] = (mesh("phone_lead", lambda: wc._mirror(wc._cyl_x(yc, zc, 2.2, x0 + wc.TESTER[0], x0 + wc.TESTER[0] + 60), S)), "black")
    P["card"] = (mesh("card", wc.card_dummy), "card")
    P["cardparts"] = (mesh("cardparts", wc.card_parts_dummy), "metal")
    P["diodes"] = (mesh("diodes", wc.diodes_dummy), "dark")
    P["clamp_l"] = (mesh("clamp_l", lambda: wc.clamp_dummy(-1)), "bought")
    P["clamp_r"] = (mesh("clamp_r", lambda: wc.clamp_dummy(1)), "bought")
    Wp = wc.wire_paths()
    for k, role in (("bundle", "wire"), ("lead1", "wire"), ("lead2", "wire"), ("lead3", "wire"), ("lead4", "wire"),
                    ("out_plus", "red"), ("out_minus", "black"), ("tail_plus", "red"), ("tail_minus", "black")):
        P[k] = (mesh("wire_" + k, lambda k=k: wc.wire_solid(Wp[k]["coarse"], Wp[k]["d"]), tol=0.1), role)
    mt = wc.MOTOR_TOP
    P["tape"] = (mesh("tape", lambda: box(-pl_half(), pl_half(), mt - wc.pl.MOTOR_SQ, mt, wc.MOTOR_BACK - 0.6, wc.MOTOR_BACK)), "tape")
    for n in ("frame",) + TURNING:
        P[n] = (machine(n), "printed")
    P["motor"] = (machine("motor"), "motor")
    return P


def pl_half():
    return wc.pl.MOTOR_SQ / 2


def table(z0, z1, x0=-260, x1=260):
    return (mesh(f"table_{z0}_{z1}_{x0}_{x1}", lambda: box(x0, x1, -wc.TABLE_T, 0, z0, z1)), "table")


# ============================================================ one shaded, outlined panel
class Panel:
    def __init__(self, rect, eye, target, ppm, up=(0, 1, 0)):
        self.rect, self.target, self.ppm = rect, np.array(target, float), ppm
        e = np.array(eye, float)
        self.back = e / np.linalg.norm(e)                  # from the target toward the camera
        r = np.cross(np.array(up, float), self.back)
        self.right = r / np.linalg.norm(r)
        self.up = np.cross(self.back, self.right)
        self.items, self.calls, self.arrows, self.dashes = [], [], [], []

    def add(self, item, mat=None, role=None):
        m, r = item
        self.items.append((m if mat is None else moved(m, mat), role or r))
        return self

    def call(self, text, at, xy):
        self.calls.append((text, at, xy))
        return self

    def arrow(self, pts, heads="end"):
        self.arrows.append((pts, heads))
        return self

    def dash(self, pts):
        self.dashes.append(pts)
        return self

    def project(self, p):
        q = np.asarray(p, float) - self.target
        x, y, w, h = self.rect
        return (x + w / 2 + float(q @ self.right) * self.ppm, y + h / 2 - float(q @ self.up) * self.ppm)

    def render(self):
        import pyrender
        from pyrender import RenderFlags
        x, y, w, h = self.rect
        ws, hs = int(w * SS), int(h * SS)
        sc = pyrender.Scene(bg_color=[0, 0, 0, 1], ambient_light=[1, 1, 1])
        for k, (m, _) in enumerate(self.items):
            mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[((k + 1) * 6) / 255.0, 0, 0, 1])
            sc.add(pyrender.Mesh.from_trimesh(m, material=mat, smooth=False))
        pose = np.eye(4)
        pose[:3, 0], pose[:3, 1], pose[:3, 2] = self.right, self.up, self.back
        pose[:3, 3] = self.target + self.back * 1500.0
        near, far = 10.0, 4000.0
        sc.add(pyrender.OrthographicCamera(xmag=w / (2 * self.ppm), ymag=h / (2 * self.ppm), znear=near, zfar=far), pose=pose)
        r = pyrender.OffscreenRenderer(ws, hs)
        col, d = r.render(sc, flags=RenderFlags.FLAT | RenderFlags.SKIP_CULL_FACES)
        r.delete()
        hit = d > 0
        part = np.where(hit, np.rint(col[..., 0].astype(np.float32) / 6.0).astype(np.int32), 0)
        part = np.clip(part, 0, len(self.items))
        depth = np.where(hit, (far + near) - near * far / np.maximum(d, 1e-9), 0.0).astype(np.float32)   # pyrender hands back a perspective-style number
        mm = 1.0 / (self.ppm * SS)
        gx = ndi.sobel(depth, axis=1) / (8.0 * mm)
        gy = -ndi.sobel(depth, axis=0) / (8.0 * mm)
        nrm = np.sqrt(gx * gx + gy * gy + 1.0)
        nx, ny, nz = gx / nrm, gy / nrm, 1.0 / nrm
        lam = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
        shade = 0.60 + 0.40 * np.clip(0.5 + 0.5 * lam, 0.0, 1.0) ** 1.3
        lut = np.ones((len(self.items) + 1, 3), np.float32)
        for k, (_, role) in enumerate(self.items):
            lut[k + 1] = ROLE[role]
        rgb = lut[part] * shade[..., None]
        far_ = np.where(hit, depth, 0.0)
        cover = ndi.gaussian_filter(hit.astype(np.float32), 9.0 * SS) + 1e-6
        mean = ndi.gaussian_filter(far_, 9.0 * SS) / cover
        sink = np.clip((depth - mean) / 30.0, 0.0, 1.0) * hit
        rgb *= (1.0 - 0.30 * sink)[..., None]
        rgb[~hit] = 1.0
        strong = np.zeros(part.shape, bool)
        weak = np.zeros(part.shape, bool)
        for ax in (0, 1):
            a = np.swapaxes(part, 0, ax)
            s = np.swapaxes(strong, 0, ax)
            wk = np.swapaxes(weak, 0, ax)
            dp = np.swapaxes(depth, 0, ax)
            n3 = [np.swapaxes(t, 0, ax) for t in (nx, ny, nz)]
            edge = a[1:] != a[:-1]
            s[1:] |= edge
            s[:-1] |= edge
            same3 = (a[2:] == a[1:-1]) & (a[:-2] == a[1:-1]) & (a[1:-1] > 0)
            d1, d2 = dp[2:] - dp[1:-1], dp[1:-1] - dp[:-2]
            step = same3 & (np.abs(d1 - d2) > 0.5 + 0.5 * np.maximum(np.abs(d1), np.abs(d2)))
            s[1:-1] |= step
            same2 = (a[1:] == a[:-1]) & (a[1:] > 0)
            turn = same2 & ((n3[0][1:] * n3[0][:-1] + n3[1][1:] * n3[1][:-1] + n3[2][1:] * n3[2][:-1]) < 0.80)
            wk[1:] |= turn
            wk[:-1] |= turn
        strong = ndi.binary_dilation(strong, structure=np.ones((3, 3), bool))
        weak &= ~ndi.binary_dilation(strong, iterations=3)
        alpha = np.maximum(strong * 1.0, weak * 0.55)[..., None]
        rgb = rgb * (1 - alpha) + LINE * alpha
        return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))


# ============================================================ arrows and call-outs (assembly_steps_compose.py's look)
def draw_head(dr, b, v, colour, grow):
    perp = np.array([-v[1], v[0]])
    head, half = 17.0 * SS, 7.0 * SS
    base = b - v * head
    dr.polygon([tuple(b + v * grow), tuple(base + perp * (half + grow) - v * grow), tuple(base - perp * (half + grow) - v * grow)], fill=colour)


def draw_arrow(dr, pts, heads="end"):
    pts = [np.array(p, float) * SS for p in pts]
    if np.linalg.norm(pts[-1] - pts[0]) < 1:
        return
    head = 17.0 * SS
    v_end = (pts[-1] - pts[-2]) / np.linalg.norm(pts[-1] - pts[-2])
    v_start = (pts[0] - pts[1]) / np.linalg.norm(pts[0] - pts[1])
    body = list(pts)
    body[-1] = pts[-1] - v_end * (head - SS)
    if heads == "both":
        body[0] = pts[0] - v_start * (head - SS)
    for colour, grow in (((255, 255, 255), 2.0 * SS), (ARROW, 0.0)):
        dr.line([tuple(p) for p in body], fill=colour, width=int(2.5 * SS + 2 * grow), joint="curve")
        draw_head(dr, pts[-1], v_end, colour, grow)
        if heads == "both":
            draw_head(dr, pts[0], v_start, colour, grow)


def draw_dash(dr, pts):
    pts = [np.array(p, float) * SS for p in pts]
    for a, b in zip(pts[:-1], pts[1:]):
        d = np.linalg.norm(b - a)
        u, t = (b - a) / max(d, 1e-9), 0.0
        while t < d:
            e = min(t + 12.0 * SS, d)
            for colour, wd in (((255, 255, 255), 6.5 * SS), (INK, 2.2 * SS)):
                dr.line([tuple(a + u * t), tuple(a + u * e)], fill=colour, width=int(wd))
            t = e + 9.0 * SS


def draw_callout(dr, xy, text, at, f):
    x0, y0 = xy
    spacing = int(0.22 * PX_CALL * SS)
    bx = dr.multiline_textbbox((x0 * SS, y0 * SS), text, font=f, spacing=spacing)
    pad = 9 * SS
    bx0, by0, bx1, by1 = bx[0] - pad, bx[1] - pad, bx[2] + pad, bx[3] + pad
    rows = text.split("\n")
    pitch = (bx[3] - bx[1]) / max(len(rows), 1)
    cands = []
    for k, row in enumerate(rows):
        wide = dr.textlength(row, font=f)
        yy = bx[1] + pitch * (k + 0.5)
        cands += [(bx0, yy), (bx[0] + wide + pad, yy)]
    cands += [(bx[0] + dr.textlength(rows[0], font=f) / 2, by0), (bx[0] + dr.textlength(rows[-1], font=f) / 2, by1)]
    if at is not None:
        px, py = at[0] * SS, at[1] * SS
        sx, sy = min(cands, key=lambda c: (c[0] - px) ** 2 + (c[1] - py) ** 2)
        if not (bx0 <= px <= bx1 and by0 <= py <= by1):
            dr.line([(sx, sy), (px, py)], fill=(255, 255, 255), width=int(5 * SS))
            dr.line([(sx, sy), (px, py)], fill=INK, width=int(1.6 * SS))
            r = 5.5 * SS
            dr.ellipse([px - r - SS, py - r - SS, px + r + SS, py + r + SS], fill=(255, 255, 255))
            dr.ellipse([px - r, py - r, px + r, py + r], fill=INK)
    dr.multiline_text((x0 * SS, y0 * SS), text, font=f, fill=INK, spacing=spacing, stroke_width=int(3 * SS), stroke_fill=(255, 255, 255))


def sheet(num, title, height, panels, notes=(), rules=(), rule_end=None):
    """One picture: 'Cover N  title' across the top, the panels, flat notes (text, x, y)."""
    img = Image.new("RGB", (W * SS, height * SS), "white")
    for p in panels:
        x, y, w, h = p.rect
        img.paste(p.render(), (x * SS, y * SS))
    dr = ImageDraw.Draw(img)
    for x in rules:
        dr.line([(x * SS, 180 * SS), (x * SS, ((rule_end or height - 30)) * SS)], fill=(205, 205, 210), width=SS)
    f_call = font(MEDIUM, PX_CALL)
    for p in panels:
        for pts in p.dashes:
            draw_dash(dr, [p.project(q) for q in pts])
        for pts, heads in p.arrows:
            draw_arrow(dr, [p.project(q) for q in pts], heads)
        for text, at, xy in p.calls:
            draw_callout(dr, (p.rect[0] + xy[0], p.rect[1] + xy[1]), text, None if at is None else p.project(at), f_call)
    dr.text((40 * SS, 38 * SS), f"Cover {num}", font=font(HEAVY, PX_STEP), fill=INK)
    off = dr.textlength(f"Cover {num}", font=font(HEAVY, PX_STEP)) / SS + 76
    dr.text((off * SS, 66 * SS), title, font=font(MEDIUM, PX_LINE), fill=INK)
    for text, x, y in notes:
        dr.multiline_text((x * SS, y * SS), text, font=f_call, fill=INK, spacing=int(0.22 * PX_CALL * SS))
    out = img.resize((W, height), Image.LANCZOS)
    path = os.path.join(PICS, f"cover_{num:02d}.png")
    out.save(path, optimize=True)
    print("wrote", path)
    return path


# ============================================================ picture 1: the card (a flat drawing, real template mm)
def picture_card():
    from shapely.geometry import MultiPoint, box as sbox
    H = 1500
    img = Image.new("RGB", (W * SS, H * SS), "white")
    dr = ImageDraw.Draw(img)
    k = 9.2                                                # final px per mm
    u0, u1, v0, v1 = wc.TPL_U0, wc.TPL_U1, wc.TPL_V0, wc.TPL_V1
    bw, bh = wc.CARD_AS_TOLD
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    ox, oy = 350 - (cu - bw / 2) * k, 330 - (cv - bh / 2) * k      # where template (0, 0) lands
    P = lambda u, v: ((ox + u * k) * SS, (oy + v * k) * SS)
    rect = lambda a0, b0, a1, b1, **kw: dr.rectangle([P(min(a0, a1), min(b0, b1)), P(max(a0, a1), max(b0, b1))], **kw)
    rect(cu - bw / 2, cv - bh / 2, cu + bw / 2, cv + bh / 2, fill=(234, 234, 237), outline=(150, 150, 156), width=2 * SS)   # the card as ELECTRONICS.md says
    rect(u0, v0, u1, v1, fill=(246, 243, 233))                                                                         # the paper template

    def hatched(poly):
        m = Image.new("L", img.size, 0)
        ImageDraw.Draw(m).polygon(poly, fill=255)
        lay = Image.new("RGB", img.size, (255, 228, 200))
        dl = ImageDraw.Draw(lay)
        for t in range(-img.size[1], img.size[0], 12 * SS):
            dl.line([(t, 0), (t + img.size[1], img.size[1])], fill=(232, 120, 30), width=2 * SS)
        img.paste(lay, (0, 0), m)
    for sx in (-1, 1):                                     # the two clips, plus the 5 mm the card rises on its way in
        poly, _ = wc._clip_poly(sx)
        pts = [wc.untpl(x, y - wc.CARD_LIFT) for x, y in poly] + [wc.untpl(x, y) for x, y in poly]
        shape = MultiPoint(pts).convex_hull.intersection(sbox(u0, v0, u1, v1))
        hatched([P(u, v) for u, v in shape.exterior.coords])
    for x0, x1 in wc.LEDGE_XS:                             # the ledge's lip
        (ua, va), (ub, vb) = wc.untpl(x0, wc.CARD_Y0 + wc.LEDGE_LIP + 1.0), wc.untpl(x1, wc.CARD_Y0)
        hatched([P(ua, va), P(ub, va), P(ub, vb), P(ua, vb)])
    dr = ImageDraw.Draw(img)
    # the parts, where Ladder draws them (the same numbers wire_cover.card_parts_dummy() uses)
    steel, dark, ink = (150, 153, 160), (88, 91, 99), INK
    rect(-0.7, -2.4, 55.7, 0.9, fill=steel)
    rect(0.9, 59.1, 57.3, 62.4, fill=steel)
    for c in wc.TPL_COL:
        rect(c - 0.7, 0.0, c + 0.7, 40.0, fill=steel)
        rect(c + wc.TPL_OFF - 0.7, 20.0, c + wc.TPL_OFF + 0.7, 61.5, fill=steel)
        rect(c - 2.65, 6.0, c + 2.65, 15.0, fill=dark)
        rect(c + wc.TPL_OFF - 2.65, 45.0, c + wc.TPL_OFF + 2.65, 54.0, fill=dark)
        rect(c - 2.65, 6.0, c + 2.65, 8.0, fill=(240, 240, 240))
        rect(c + wc.TPL_OFF - 2.65, 45.0, c + wc.TPL_OFF + 2.65, 47.0, fill=(240, 240, 240))
    rect(63.5, -3.7, 89.0, 9.3, fill=dark)
    rect(59.3, 5.9, 62.6, 61.5, fill=(40, 40, 44))
    rect(-16.8, 44.4, -8.6, 49.6, fill=(205, 60, 50))
    rect(-9.25, 6.5, -6.75, 13.0, fill=(196, 170, 120))
    rect(-9.25, 23.5, -6.75, 30.0, fill=(196, 170, 120))
    dr.line([P(-8.0, 1.4), P(-8.0, 58.6)], fill=steel, width=3 * SS)
    f_s = font(MEDIUM, 28)
    for i, c in enumerate(wc.TPL_COL):
        dr.text(P(c + 3.4, 26.0), f"J{i + 1}", font=f_s, fill=ink)
    dr.text(P(6.0, -12.0), "+  PLUS", font=f_s, fill=ink)
    dr.text(P(64.5, 55.0), "-  MINUS", font=f_s, fill=ink)
    # motor wires as wire_cover draws them, and the tie
    Wp = wc.wire_paths()
    for n in ("lead1", "lead2", "lead3", "lead4"):
        pts = [wc.untpl(x, y) for x, y, _ in Wp[n]["fine"] if x > -wc.CARD_W / 2 - 4.5]
        dr.line([P(u, v) for u, v in pts], fill=(232, 150, 30), width=int(wc.LEAD_D * k * SS), joint="curve")
    hu = [wc.untpl(wc.TIE_X, y)[0] for y in (169.5, 134.5)]
    hv = wc.untpl(wc.TIE_X, 0)[1]
    dr.line([P(hu[0], hv), P(hu[1], hv)], fill=(40, 90, 200), width=4 * SS)
    for u in hu:
        dr.ellipse([P(u - 1.6, hv - 1.6), P(u + 1.6, hv + 1.6)], fill="white", outline=ink, width=2 * SS)
    for n, colr in (("out_plus", (200, 40, 34)), ("out_minus", (40, 40, 44))):      # output wires, as far as the card's end
        pts = [wc.untpl(x, y) for x, y, _ in Wp[n]["fine"] if y > wc.CARD_Y0 - 2]
        dr.line([P(u, v) for u, v in pts], fill=colr, width=int(wc.OUT_WIRE_D * k * SS), joint="curve")
    dr.rectangle([P(u0, v0), P(u1, v1)], outline=(200, 30, 30), width=5 * SS)        # the cut line
    f = font(MEDIUM, PX_CALL)
    call = lambda text, at, xy: draw_callout(dr, xy, text, None if at is None else (ox + at[0] * k, oy + at[1] * k), f)
    call("cut the card HERE, on the edge of the paper: 111 x 90 mm", (30.0, v0), (520, 200))
    call("a card cut\n13 x 10 cm\ndoes not go in", (cu + bw / 2 - 1.5, cv - bh / 2 + 6), (1590, 250))
    call("keep the orange\nplaces bare:\ntwo clips hold\nthese corners", (u0 + 4.0, v0 + 5.0), (30, 330))
    call("the LED must\nnot stick out\npast the edge", (-16.8, 47.0), (30, 700))
    call("motor wire 1 leaves\nbeside wire 2", wc.untpl(-46.5, wc.LEAD_EDGE_Y1), (60, 1290))
    call("two pencil holes, a twist of jumper wire over\nthe four motor wires, then tape on top", (hu[1], hv), (560, 1290))
    call("a ledge holds\nthis edge:\nkeep it bare", (u1 - 1.5, 46.0), (1590, 620))
    pm = [wc.untpl(x, y) for x, y, _ in Wp["out_minus"]["fine"] if y > wc.CARD_Y0 + 8][-1]
    call(f"output wires:\ncut BOTH {wc.OUT_WIRE_LEN / 10:.0f} cm,\nnot 10 cm", pm, (1590, 930))
    dr.multiline_text((1590 * SS, 480 * SS), f"card no thicker\nthan {wc.CARD_T_MAX:.0f} mm", font=f, fill=INK, spacing=int(0.22 * PX_CALL * SS))
    dr.text((40 * SS, 38 * SS), "Cover 1", font=font(HEAVY, PX_STEP), fill=INK)
    dr.text((390 * SS, 66 * SS), "Before you build the card: cut it to the paper.", font=font(MEDIUM, PX_LINE), fill=INK)
    out = img.resize((W, H), Image.LANCZOS)
    path = os.path.join(PICS, "cover_01.png")
    out.save(path, optimize=True)
    print("wrote", path)


# ============================================================ pictures 2 to 6
def picture_print(P):
    S = wc.USB_SIDE
    a = Panel((0, 190, 1040, 1060), (-0.46 * S, 0.50, 0.73), (-4 * S, 100, -55), 4.2)
    a.add(P["shell"])
    cz = wc.CLIP_Z0
    a.call("clip, x2: the\ncard's top corners", (S * 40, wc.LID_IN - 10, cz + 2.4), (640, 30))
    a.call("ledge: the card\nstands in it", (-S * 20, wc.CARD_Y0, wc.LEDGE_Z0 + 3), (30, 500))
    a.call("rail for\nthe sled", (S * 22, wc.SLED_Y0, wc.IN_Z + 4), (30, 760))
    a.call("window: the\nUSB socket", (S * wc.IN_HW, sum(wc.WIN_Y) / 2, wc.IN_Z + 12), (760, 560))
    a.call("baffle, x2: hides the\ninside from the front", (S * 58, 150, -20), (640, 200))
    a.call("peg, x2", (-S * 72, wc.BASE_TOP - 2, -78), (40, 980))
    a.call("foot, x2: a G-clamp\nsits on each", (S * 88, wc.BASE_TOP + 4, -34), (640, 960))
    a.call("wall stop, x4", (-S * 70, 166, wc.Z_FRONT + 0.6), (30, 60))
    b = Panel((1040, 190, 960, 1060), (0.30, 0.74, 0.60), (0, 20, 0), 4.3)
    cm = trimesh.load(os.path.join(wc.OUT, wc.FILES["coupons"]), force="mesh")
    cm.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))     # plate up
    b.target = np.array(cm.bounding_box.centroid)
    bodies = list(cm.split(only_watertight=False))
    for m in bodies:
        b.add((m, "accent"))
    want = wc.coupons(wc.shell())
    text = {"C1_foot_peg_forks": "C1  foot, peg, forks:\non the real base,\nwith the real clamp", "C2_card_clip_and_light": "C2  clip and light:\na card corner under it,\na lit LED behind it",
            "C3_rail_and_window": "C3  rail and window", "C4_sled_PLACEHOLDER": "C4  sled (placeholder):\nit must slide into C3",
            "C5_baffle": "C5  baffle: does the\nthin slab print clean?"}
    spots = {"C1_foot_peg_forks": (30, 60), "C2_card_clip_and_light": (500, 30), "C3_rail_and_window": (30, 900),
             "C4_sled_PLACEHOLDER": (430, 900), "C5_baffle": (540, 330)}
    for name, part in want.items():
        vol = part.val().Volume()
        m = min(bodies, key=lambda mm: abs(mm.volume - vol))
        top = m.bounding_box.centroid + np.array([0, m.bounding_box.extents[1] / 2, 0])
        b.call(text[name], tuple(top), spots[name])
    sheet(2, "What you print. The five test pieces first: one hour.", 1330, [a, b],
          notes=[("job 2: the shell. Back face on the plate, no supports.", 60, 1262), ("job 1: five test pieces", 1090, 1262)], rules=(1040,))


def lead_slack(P):
    """The motor leads, slack, from the motor to the card while the shell lies on its back."""
    edge = wc.lie_point((-50.0, 158.0, wc.CARD_BACK + 8.0), wc.LIE_BOX)
    ex, ey, ez = wc.LEAD_EXIT
    z1 = wc.BASE_BACK - wc.LIE_GAP                         # the shell's foot end = the motor's back
    pts = [(ex, ey, ez), (ex, ey + 20, ez - 6), (-20, ey + 30, z1 - 34), (-44, ey + 24, z1 - 92),
           (edge[0] - 4, edge[1] + 14, edge[2] + 30), edge]
    f, c = wc._round_path(pts, 9.0)
    run = max(r for _, r in wc.lead_ties(wc.wire_paths()))
    drawn = wc._length(f) + run + 12.0
    assert drawn <= wc.LEAD_LEN - 20.0, f"the slack lead drawn in cover_03 is {drawn:.0f} mm: longer than the lead allows"
    return (mesh("wire_slack", lambda: wc.wire_solid(c, wc.LEAD_BUNDLE_D), tol=0.1), "wire")


def picture_inside(P):
    S = wc.USB_SIDE
    L = lie()
    inner = ("card", "cardparts", "diodes")
    mod = ("sled", "pcb", "socket", "modparts")
    # A: the fitting pose
    a = Panel((0, 190, 720, 1040), (-0.80, 0.56, 0.20), (0, 104, -112), 1.85)
    for n in ("frame", "motor") + TURNING:
        a.add(P[n])
    a.add(table(-420, 170, -230, 230))
    z1 = wc.BASE_BACK - wc.LIE_GAP                         # the motor's back
    a.add((mesh("books", lambda: box(-118, 118, 0, wc.LIE_BOX, wc.BASE_BACK - 200, wc.BASE_BACK)), "book"))
    for n in ("shell",) + mod + inner:
        a.add(P[n], L)
    a.add(lead_slack(P))
    a.call("pull the machine in\nfrom the table edge", (-230, 0, -330), (30, 900))
    a.call("1  books against the\nback of the base,\n15 cm high", (-118, wc.LIE_BOX - 60, wc.BASE_BACK - 110), (30, 640))
    a.call("2  shell on its BACK. Push it\nforward till it touches\nthe motor's back", (-wc.HW, wc.LIE_BOX + 60, z1 - 4), (30, 30))
    a.call("motor wires:\nslack, not tight", (-17, wc.MOTOR_TOP + 29, z1 - 30), (400, 215))
    # B: the sled, in one corner of the shell
    b = Panel((720, 190, 640, 1040), (-0.66 * S, 0.50, 0.56), (S * 36, 52, wc.IN_Z + 14), 5.6)
    b.add(P["shell_corner"])
    hi = shift(-S * (wc.SLED_SIDE + 10), wc.SLED_DROP + 6, 14)
    for n in mod:
        b.add(P[n], hi)
    b.arrow([(-S * 2, 62, wc.IN_Z + 26), (-S * 2, 62, wc.IN_Z + 4)])
    b.arrow([(S * 40, 84, wc.IN_Z + 2.5), (S * 60, 84, wc.IN_Z + 2.5)])
    b.arrow([(S * 20, 98, wc.IN_Z + 2.5), (S * 20, 82, wc.IN_Z + 2.5)])
    b.call("3  sled: flat\non the panel", (-S * 2, 62, wc.IN_Z + 16), (30, 470))
    b.call("4  into the corner", (S * 50, 84, wc.IN_Z + 2.5), (270, 40))
    b.call("5  down,\nonto the rail", (S * 20, 90, wc.IN_Z + 2.5), (30, 120))
    b.call("socket end toward\nthe side wall", (S * 56, 60, wc.IN_Z + 26), (300, 800))
    b.call("rail", (S * 12, wc.SLED_Y0 - 1.5, wc.IN_Z + 4.2), (40, 800))
    b.call("(one corner of the shell)", None, (30, 985))
    # C: the card, caught half way in
    c = Panel((1360, 190, 640, 1040), (0.72, 0.24, 0.65), (-2, 128, wc.IN_Z + 22), 4.3)
    c.add(P["shell_pocket"])
    for n in mod:
        c.add(P[n])
    piv = [0, wc.LID_IN - 12.0, wc.CARD_BACK + 1.0]
    tip = shift(*piv) @ trimesh.transformations.rotation_matrix(math.radians(-8.0), [1, 0, 0]) @ shift(-piv[0], -piv[1], -piv[2]) @ shift(0, wc.CARD_LIFT - 0.5, 0)
    for n in inner:
        c.add(P[n], tip)
    c.arrow([(44, wc.CARD_TOP - 22, wc.CARD_BACK + 9), (44, wc.CARD_TOP + 2, wc.CARD_BACK + 5)])
    c.arrow([(44, wc.CARD_Y0 + 14, wc.CARD_BACK + 26), (44, wc.CARD_Y0 + 3, wc.CARD_BACK + 5)])
    c.call("6  card: top edge up,\nunder the two clips", (44, wc.CARD_TOP - 10, wc.CARD_BACK + 7), (30, 30))
    c.call("7  then the bottom\nedge in, and down\ninto the ledge", (44, wc.CARD_Y0 + 9, wc.CARD_BACK + 16), (30, 770))
    c.call("(near side wall not drawn)", None, (100, 985))
    sheet(3, "Sled first, then the card. Do it with the shell lying on its back.", 1250, [a, b, c], rules=(720, 1360))


def picture_wires(P):
    S = wc.USB_SIDE
    wires = ("bundle", "lead1", "lead2", "lead3", "lead4", "out_plus", "out_minus", "tail_plus", "tail_minus")
    held = ("sled", "pcb", "socket", "modparts", "card", "cardparts", "diodes")
    a = Panel((0, 190, 1000, 1110), (-0.66, 0.42, 0.62), (-4, 108, -58), 4.5)
    a.add(P["shell_open"])
    a.add(P["motor"]).add(P["tape"])
    for n in held + wires:
        a.add(P[n])
    ex, ey, ez = wc.LEAD_EXIT
    loop_at = wc.wire_paths()["bundle"]["fine"][20]
    a.call("spare motor wire: one loop on the\nmotor's BACK half (Cover 5, step 2)", tuple(loop_at), (330, 8))
    a.call("tape across the motor's\nBACK face (hidden here)", (-wc.pl.MOTOR_SQ / 2, wc.MOTOR_TOP - 44, wc.MOTOR_BACK), (20, 400))
    a.call("down behind the motor,\nonto the card's edge", (-(wc.IN_HW - 8.0), wc.MOTOR_TOP - 10, wc.MOTOR_BACK - 12), (20, 150))
    a.call("meter tail (thin):\ndown the side wall,\nout under the back", (-(wc.IN_HW - 1.8), 70, wc.MOTOR_BACK), (20, 640))
    a.call("(side wall and lid\ncut away to show)", None, (30, 990))
    b = Panel((1000, 190, 1000, 1110), (0.10, 0.20, 0.97), (0, 100, -80), 5.2)
    b.add(P["shell_back"])
    for n in held + wires[1:]:
        b.add(P[n])
    Wp = wc.wire_paths()
    pm = Wp["out_minus"]["fine"]
    pp = Wp["out_plus"]["fine"]
    b.call("MINUS: down its edge,\nacross, in at the tail", tuple(pm[len(pm) // 2]), (30, 870))
    b.call("PLUS: round the top\nof the sled, in at the tail", tuple(pp[int(len(pp) * 0.55)]), (500, 500))
    b.call("both wires lie in\nthe comb: tape them", (S * (wc._sled_x()[3] + 1.5), wc.SLED_YC, wc.IN_Z + 8), (560, 960))
    b.call("1 k resistor\non each\nmeter tail", (36, wc.TAIL_Y, wc.CARD_BACK + 5), (775, 290))
    b.call("no crocodile\nclips in here", None, (30, 90))
    sheet(4, "Where every wire runs.", 1320, [a, b],
          notes=[("seen from the front, motor and baffles taken away", 1040, 196)], rules=(1000,))


def picture_on(P):
    S = wc.USB_SIDE
    held = ("sled", "pcb", "socket", "modparts", "card", "cardparts", "diodes", "tester", "plug", "screen")
    eye = (-0.80, 0.34, -0.50)
    tgt = (0, 96, -70)
    # A: the coil pose. Shell upright, its front edge level with the motor's back, a thin book under its back edge
    cb = wc.COIL_BACK
    stand = shift(0, 0, -cb)
    a = Panel((0, 190, 720, 1060), (-0.72, 0.58, -0.38), (-12, 156, -92), 2.5)
    for n in ("frame", "motor") + TURNING:
        a.add(P[n])
    a.add(P["tape"])
    a.add(table(-330, 160))
    zb = wc.Z_BACK - cb                                    # the shell's back face in this pose
    a.add((mesh("thin_book", lambda: box(-95, 95, 0, wc.BASE_TOP, zb - 70, zb + 12)), "book"))
    a.add(P["shell"], stand)
    for n in held:
        a.add(P[n], stand)
    Wc = wc.wire_paths(back=cb)
    for k in ("bundle", "lead1", "lead2", "lead3", "lead4"):
        a.add((mesh("coilpose_" + k, lambda k=k: wc.wire_solid(Wc[k]["coarse"], Wc[k]["d"]), tol=0.1), "wire"))
    loop_at = Wc["bundle"]["fine"][30]
    a.call("1  stand it up, tester in.\nFront edge LEVEL with\nthe motor's back", (-wc.HW, wc.Y_TOP - wc.CORNER_R - 30, wc.Z_FRONT - cb), (30, 20))
    a.call("2  loop the spare wire round\ntwo fingers, lay it on the\nmotor, one strip of tape", tuple(loop_at), (30, 190))
    a.call("a thin book under\nthe back edge", (-95, wc.BASE_TOP, zb - 30), (30, 940))
    # B: the last push
    b = Panel((720, 190, 640, 1060), eye, tgt, 2.25)
    for n in ("frame", "motor") + TURNING:
        b.add(P[n])
    b.add(table(-330, 160))
    back = shift(0, wc.LIFT_ON, -30)
    b.add(P["shell"], back)
    for n in held[:4] + held[7:]:
        b.add(P[n], back)
    b.arrow([(-wc.HW - 4, 110, -122), (-wc.HW - 4, 110, -62)])
    b.call("3  slide it on LEVEL. A finger\npresses the slack wire DOWN\nbehind the motor", (-wc.HW - 4, 110, -92), (20, 30))
    b.call("4  the pegs bump the base:\nlift the back a finger\n(3 mm), keep pushing", (-72, wc.BASE_TOP + 2, -78 - 30), (20, 800))
    b.call("5  it stops at the wall,\ndrops with a clunk", (-wc.HW, 166, wc.WALL_BACK), (250, 250))
    # C: clamped
    c = Panel((1360, 190, 640, 1060), eye, tgt, 2.25)
    for n in ("frame", "motor") + TURNING:
        c.add(P[n])
    c.add(table(wc.BASE_BACK, 160))
    c.add(P["shell"], role="shell")
    for n in held[7:]:
        c.add(P[n])
    c.add(P["clamp_l"]).add(P["clamp_r"])
    c.call("6  push the machine back to\nthe table edge BY THE BASE,\nnot by the shell", (-100, 4, wc.BASE_BACK + 30), (20, 30))
    c.call("7  a G-clamp on\neach FOOT", (-wc.CLAMP_X, wc.BASE_TOP + wc.FOOT_T + 14, -57), (20, 560))
    c.call("the back panel hangs 8 mm\nbehind the table edge", (-20, 30, wc.Z_BACK), (110, 930))
    sheet(5, "Loop the spare wire. Slide it on. Clamp. To open it: the same, backwards.", 1280, [a, b, c], rules=(720, 1360))


def picture_done(P):
    S = wc.USB_SIDE
    a = Panel((0, 190, 1000, 1060), (0.74 * S, 0.34, -0.58), (0, 96, -40), 3.1)
    for n in ("frame", "motor") + TURNING:
        a.add(P[n])
    a.add(table(wc.BASE_BACK, 200))
    a.add(P["shell"], role="shell")
    for n in ("sled", "socket", "tester", "plug", "screen", "phone_lead", "clamp_l", "clamp_r"):
        a.add(P[n])
    yc, zc = wc._usb_centre()
    a.call("USB tester, and the\nphone lead from it", (S * (wc.tester_face_x() + 30), yc, zc), (40, 60))
    a.call("one plain panel:\nno hole, no screw", (0, 130, wc.Z_BACK), (620, 60))
    a.call("pull the tester UP:\nthe sled must stay", (S * (wc.tester_face_x() + 8), yc + 6, zc), (30, 860))
    arm_top = wc.BASE_TOP + wc.FOOT_T + wc.G_FRAME_T
    a.call(f"air between tester and\nclamp: {wc.TESTER_ARM_AIR:.0f} mm or more", (S * wc.CLAMP_X, (yc - wc.TESTER[1] / 2 + arm_top) / 2, zc - wc.TESTER[2] / 2), (30, 620))
    b = Panel((1000, 190, 1000, 1060), (0.20 * S, 0.16, 0.97), (12 * S, 122, 0), 2.9)
    for n in ("frame", "motor") + TURNING:
        b.add(P[n])
    b.add(table(wc.BASE_BACK, 200))
    b.add(P["shell"], role="shell")
    for n in ("sled", "socket", "tester", "plug", "screen", "phone_lead", "clamp_l", "clamp_r"):
        b.add(P[n])
    b.call("square from the front the\nshell is behind the wall", (S * 40, 190, 0), (40, 40))
    b.call("a baffle behind\neach window", (S * 66, 70, -14), (640, 930))
    sheet(6, "Done. Tester in the side, the phone lead from the tester.", 1280, [a, b], rules=(1000,))


def picture_measure(P):
    """Cover 0: where the ruler goes. Every number here is a PLACEHOLDER in wire_cover.py until he sends it."""
    S = wc.USB_SIDE
    # A: the G-clamp's top arm, seen from a little below so the pressing face shows
    x, top, t = wc.CLAMP_X, wc.BASE_TOP + wc.FOOT_T, wc.G_FRAME_T
    z_tip = wc.BASE_BACK - wc.G_SPINE_BACK + wc.G_REACH
    a = Panel((0, 190, 700, 1010), (0.38, -0.16, 0.91), (x, top - 40, z_tip - 30), 4.6)
    a.add(P["clamp_r"])
    xj = x + wc.G_JAW_W / 2
    a.arrow([(xj + 5, top, z_tip + 1), (xj + 5, top + t, z_tip + 1)], heads="both")
    a.arrow([(x - wc.G_JAW_W / 2, top + t + 6, z_tip + 1), (xj, top + t + 6, z_tip + 1)], heads="both")
    a.call("2  jaw: its widest\npart  ____ mm", (x, top + t + 6, z_tip + 1), (30, 30))
    a.call("3  frame: from the\nface that presses\nUP to its top  ____ mm", (xj + 5, top + t / 2, z_tip + 1), (30, 600))
    a.call("the face\nthat presses", (x + 2, top, z_tip - 6), (440, 330))
    a.call("your G-clamp", None, (450, 870))
    # B: the tester
    yc, zc = wc._usb_centre()
    x0, (tl, tw, tt) = wc.tester_face_x(), wc.TESTER
    b = Panel((700, 190, 700, 1010), (0.50 * S, 0.42, -0.76), (S * (x0 + tl / 2 - 6), yc - 2, zc), 7.4)
    for n in ("tester", "plug", "screen"):
        b.add(P[n])
    xe = S * (x0 + tl + 4)
    b.arrow([(xe, yc - tw / 2, zc - tt / 2), (xe, yc + tw / 2, zc - tt / 2)], heads="both")
    b.arrow([(S * (x0 + 6), yc + tw / 2 + 3, zc - tt / 2), (S * (x0 + 6), yc + tw / 2 + 3, zc + tt / 2)], heads="both")
    b.arrow([(S * (x0 - wc.PLUG_LEN), yc - 8, zc), (S * x0, yc - 8, zc)], heads="both")
    b.call("5  body, wide\n____ mm", (xe, yc, zc - tt / 2), (30, 150))
    b.call("6  body, thick\n____ mm", (S * (x0 + 6), yc + tw / 2 + 3, zc), (410, 30))
    b.call("7  metal plug,\nsticking out\n____ mm", (S * (x0 - wc.PLUG_LEN / 2), yc - 8, zc), (430, 640))
    b.call("8  the screen: on this\nface, or the other?", (S * (x0 + 29), yc - 4, zc - tt / 2), (30, 720))
    b.call("the USB tester", None, (30, 930))
    # C: the motor wires
    ex, ey, ez = wc.LEAD_EXIT
    c = Panel((1400, 190, 600, 1010), (-0.62, 0.40, -0.68), (-10, wc.MOTOR_TOP - 40, wc.MOTOR_BACK - 40), 3.3)
    c.add(P["motor"])
    pts = [(ex, ey, ez), (ex, ey + 22, ez - 4), (ex - 16, ey + 26, ez - 60), (ex - 22, ey - 30, ez - 110), (ex + 6, ey - 96, ez - 126)]
    f, cr = wc._round_path(pts, 12.0)
    c.add((mesh("wire_measure", lambda: wc.wire_solid(cr, wc.LEAD_BUNDLE_D), tol=0.1), "accent"))
    c.call("4  motor wires: from the\nmotor to the bare tip\n____ cm", tuple(f[len(f) // 2]), (30, 30))
    c.call("do they come out\nHERE, on top, near\nthe back?  yes / no", (ex, ey, ez), (210, 610))
    c.call("the motor, from behind", None, (30, 930))
    sheet(0, "Measure these with a ruler. Send me the numbers.", 1330, [a, b, c],
          notes=[("1  the card: how thick?  ____ mm", 60, 1215),
                 ("9  the module, when it comes: board long x wide x tallest part  ____ x ____ x ____ mm", 60, 1268)],
          rules=(700, 1400), rule_end=1180)


if __name__ == "__main__":
    os.makedirs(PICS, exist_ok=True)
    want = {int(a) for a in sys.argv[1:] if a.isdigit()} or {0, 1, 2, 3, 4, 5, 6}
    if 1 in want:
        picture_card()
    if want - {1}:
        P = parts()
        for n, fn in ((0, picture_measure), (2, picture_print), (3, picture_inside), (4, picture_wires), (5, picture_on), (6, picture_done)):
            if n in want:
                fn(P)
