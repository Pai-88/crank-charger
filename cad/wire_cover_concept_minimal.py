"""Wire cover, concept MINIMAL: the HOOD. A MASSING model, not a print file yet.

Question asked: does this need a box at all? Answer here: no. The printed wall is
already the front of the box and the base is already its floor. What is missing is
a back and two sides. So the cover is ONE open-fronted hood (back panel, two side
walls, a round top that copies the wall's own arc) that stands on the base behind
the motor. Nothing is screwed, glued or tapped.

How it stays on (all three are features that already exist on the frame):
    1. a HOOK on a strap over the top of the wall (the strap sits on the wall's top
       edge, a 1.4 mm lip hangs in front of it),
    2. a PEG that drops into the middle 5.5 mm base hole (the one no clamp covers),
    3. two ribs that sit against the outside faces of the two tall gussets.
Fit: hold it 1 cm up, push it forward until the strap meets the wall, let it drop.
Take off: lift 1 cm, pull back.

Everything about the DC-DC module is a PLACEHOLDER (it has not arrived). The hood
only has a plain window; the module lives on a small separate SLED that is sized
and printed the day the module is measured.

Model frame as planetary.py: X right, Y up, Z toward you, wall front face Z=0.
Print: back panel on the bed, Z up. Every wall is a straight extrusion.

    .venv/bin/python cad/wire_cover_concept_minimal.py           build, check, export, picture
    .venv/bin/python cad/wire_cover_concept_minimal.py --no-png  skip the picture
"""
import math
import os
import sys

import cadquery as cq
from shapely.geometry import Point, Polygon, box

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import planetary as P

OUT = os.path.join(HERE, "stl", "cover")
PNG = os.path.join(os.path.dirname(HERE), "cover", "concept_minimal.png")

# ============================================================ numbers (mm)
AY = P.AXLE_Y
Z_BASE_REAR = -P.WALL_T + 1 - (P.BASE_DEPTH + 1)      # -93: back edge of the base = the table edge

# ---- the card (ELECTRONICS.md: "about 13 x 10 cm"; the template outline is 111 x 90). Stood on end.
CARD_W, CARD_H, CARD_T = 100.0, 130.0, 2.0            # PLACEHOLDER until he gives two ruler numbers
PART_H = 15.0                                         # tallest thing on the card: the 13 mm capacitor, taped flat

# ---- the hood
PANEL_T = 1.6
SIDE_T = 1.6                                          # four 0.4 mm lines: prints solid
HALF_W = CARD_W / 2 + 0.7 + SIDE_T                    # 52.3: both side walls stay behind the wall's solid middle
                                                      # column (the wall windows start at x = 52.5)
Z_PANEL0 = Z_BASE_REAR - PANEL_T                      # panel hangs just behind the base, so it never meets a gusset
Z_FRONT = -38.0                                       # side walls stop here: 11 mm short of the upper pin nuts,
                                                      # 30 mm short of the wall. That gap is the air path.
Y_FOOT = P.BASE_T + 0.2                               # side walls stand on the base
R_TOP = P.WALL_R - 0.8                                # round top, hidden behind the wall from the front
CARD_Y0 = 72.0                                        # card's bottom edge

# ---- hook over the top of the wall
STRAP_HALF = 14.0                                     # narrow: keeps the lip 15 mm from the planets' tooth tips
STRAP_T = 2.4
WALL_TOP_GAP = 0.4
R_STRAP_IN = P.WALL_R + WALL_TOP_GAP
R_STRAP_OUT = R_STRAP_IN + STRAP_T
LIP_BITE = 1.4                                        # a flat overhang this small prints without support
LIP_Z0, LIP_Z1 = 0.8, 4.0                             # in front of the wall face
SHOULDER_GAP = 0.6                                    # behind the wall's back face

# ---- peg in the middle base hole
HOLE_X, HOLE_Z = P.BASE_HOLES[1][0], -P.WALL_T - P.BASE_HOLES[1][1]
PEG_HALF_DIAG = 2.4                                   # a diamond: prints lying down with no support, 4.8 across
PEG_LEN = 6.0
FOOT_HALF_W, FOOT_H = 9.0, 8.0

# ---- ribs against the tall gussets
GUSSET_X = P.GUSSETS[3][0]                            # 45
RIB_GAP = 0.3

# ---- USB window and the sled. EVERY module number is a PLACEHOLDER.
MOD_L, MOD_W, MOD_T = 43.0, 21.0, 1.6                 # PLACEHOLDER board
USB_W, USB_H, USB_LEN = 13.2, 5.8, 14.0               # USB-A socket shell: this one is the USB standard
USB_Y = 57.0                                          # socket centre height: tester bottom edge clears a clamp arm
WIN_Y0, WIN_Y1 = USB_Y - 12.0, USB_Y + 12.0
WIN_Z0, WIN_Z1 = Z_BASE_REAR + 1.5, Z_BASE_REAR + 21.5
SLED_FLOOR = 1.5
TESTER = (62.0, 25.0, 13.0)                           # PLACEHOLDER: long, wide, thick

CLAMP_X, CLAMP_PAD, CLAMP_TOP = 74.0, 24.0, 38.0      # G-clamp: from assembly_steps_export.py, made fatter

DENSITY_PETG = 1.27e-3                                # g / mm3


def circ(r, n=160):
    return Point(0, AY).buffer(r, n)


def dome(r):
    """Everything below the axle, and a round top of radius r above it: the wall's own shape."""
    return circ(r).union(box(-300, -50, 300, AY))


def sector(r_in, r_out, half):
    return circ(r_out).difference(circ(r_in)).intersection(box(-half, AY, half, AY + r_out + 5))


def cbox(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def yz_wedge(pts_yz, x0, x1):
    """A profile drawn in (y, z), extruded along X."""
    return cq.Workplane("YZ").workplane(offset=x0).polyline(pts_yz).close().extrude(x1 - x0)


# ============================================================ the hood
def hood():
    outline = box(-HALF_W, Y_FOOT, HALF_W, AY + 200).intersection(dome(R_TOP))
    inner = box(-HALF_W + SIDE_T, Y_FOOT - 5, HALF_W - SIDE_T, AY + 200).intersection(dome(R_TOP - SIDE_T))
    body = P._prism(outline, Z_PANEL0, Z_BASE_REAR)                       # the plain back
    for piece in P._pieces(outline.difference(inner), 5.0):               # two sides and the round top, one wall
        body = body.union(P._prism(piece, Z_PANEL0, Z_FRONT))

    # hook: a strap that grows out of the round top, runs over the wall's top edge, and ends in a lip
    # in front of the wall. Two fins under it stiffen it and stop against the wall's back face.
    body = body.union(P._prism(sector(R_TOP - 0.2, R_STRAP_OUT, STRAP_HALF), Z_PANEL0, Z_FRONT))
    body = body.union(P._prism(sector(R_STRAP_IN, R_STRAP_OUT, STRAP_HALF), Z_PANEL0, LIP_Z1))
    for s in (-1, 1):
        a, b = sorted((s * (STRAP_HALF - 2.4), s * STRAP_HALF))
        fin = sector(R_TOP - SIDE_T, R_STRAP_IN + 0.2, STRAP_HALF).intersection(box(a, AY, b, AY + 200))
        body = body.union(P._prism(fin, Z_FRONT - 1, -P.WALL_T - SHOULDER_GAP))
    body = body.union(P._prism(sector(R_STRAP_IN - LIP_BITE, R_STRAP_IN + 0.5, STRAP_HALF), LIP_Z0, LIP_Z1))

    # foot and peg for the middle base hole
    body = body.union(cbox(HOLE_X - FOOT_HALF_W, HOLE_X + FOOT_HALF_W, Y_FOOT, Y_FOOT + FOOT_H, Z_PANEL0, HOLE_Z + 8))
    d = PEG_HALF_DIAG
    peg = (cq.Workplane("XZ").workplane(offset=-(Y_FOOT + 1))
           .polyline([(HOLE_X - d, HOLE_Z), (HOLE_X, HOLE_Z + d), (HOLE_X + d, HOLE_Z), (HOLE_X, HOLE_Z - d)]).close()
           .extrude(PEG_LEN + 1, taper=8))
    body = body.union(peg)

    # ribs against the outside of each tall gusset
    xr0 = GUSSET_X + P.GUSSET_T / 2 + RIB_GAP
    for s in (-1, 1):
        a, b = sorted((s * xr0, s * (HALF_W - SIDE_T + 0.5)))
        body = body.union(cbox(a, b, Y_FOOT + 2, Y_FOOT + 16, Z_PANEL0, Z_FRONT))

    # the card: a ledge with two hooks under it, two spring fingers over it
    zc = Z_BASE_REAR + CARD_T + 1.0                                       # room for card plus a taped paper template
    y1 = CARD_Y0 + CARD_H + 0.3
    for s in (-1, 1):
        a, b = sorted((s * 18.0, s * 32.0))
        body = body.union(cbox(a, b, CARD_Y0 - 2.5, CARD_Y0, Z_PANEL0, zc + 4))
        body = body.union(yz_wedge([(CARD_Y0 - 0.1, zc), (CARD_Y0 + 1.4, zc + 1.5), (CARD_Y0 + 1.4, zc + 4), (CARD_Y0 - 0.1, zc + 4)], a, b))
        body = body.union(cbox(a, b, y1, y1 + 1.8, Z_PANEL0, zc + 4))
        body = body.union(yz_wedge([(y1 + 0.1, zc), (y1 - 1.2, zc + 1.3), (y1 - 1.2, zc + 4), (y1 + 0.1, zc + 4)], a, b))

    # the sled's end stop, and the plain window for the USB socket (right-hand side wall)
    body = body.union(cbox(HALF_W - SIDE_T - MOD_L - 8.0, HALF_W - SIDE_T - MOD_L - 6.0, WIN_Y0, WIN_Y1, Z_PANEL0, Z_BASE_REAR + 8))
    body = body.cut(cbox(HALF_W - SIDE_T - 1, HALF_W + 1, WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1))
    return body


def sled():
    """PLACEHOLDER. The only part that knows the module's size: a floor, a flange behind the side
    wall, a face plate that fills the hood's window, and the socket's exact opening."""
    xi = HALF_W - SIDE_T                                                   # inside face of the side wall
    x_stop = xi - MOD_L - 6.0
    z_pcb = Z_BASE_REAR + SLED_FLOOR
    s = cbox(x_stop + 0.2, xi - 0.2, WIN_Y0 + 0.3, WIN_Y1 - 0.3, Z_BASE_REAR, z_pcb)                       # floor
    s = s.union(cbox(xi - 2.0, xi - 0.2, WIN_Y0 - 3, WIN_Y1 + 1.5, Z_BASE_REAR, WIN_Z1 + 2))               # flange
    s = s.union(cbox(xi - 0.3, HALF_W, WIN_Y0 + 0.3, WIN_Y1 - 0.3, WIN_Z0 + 0.3, WIN_Z1 - 0.3))            # face plate
    s = s.union(cbox(x_stop + 0.2, x_stop + 2.0, WIN_Y0 + 0.3, WIN_Y1 - 0.3, Z_BASE_REAR, z_pcb + 5))      # board's end stop
    for y in (USB_Y - MOD_W / 2 - 1.2, USB_Y + MOD_W / 2 + 0.2):                                           # two rails
        s = s.union(cbox(x_stop + 0.2, xi - 2.0, y, y + 1.0, Z_BASE_REAR, z_pcb + 4))
    zs = z_pcb + MOD_T
    return s.cut(cbox(xi - 3, HALF_W + 1, USB_Y - USB_W / 2 - 0.4, USB_Y + USB_W / 2 + 0.4, zs - 0.3, zs + USB_H + 0.4))


# ============================================================ things that are not printed (view and checks only)
def dummies():
    xi = HALF_W - SIDE_T
    z_pcb = Z_BASE_REAR + SLED_FLOOR
    zs = z_pcb + MOD_T
    d = {}
    d["card"] = cbox(-CARD_W / 2, CARD_W / 2, CARD_Y0, CARD_Y0 + CARD_H, Z_BASE_REAR, Z_BASE_REAR + CARD_T)
    zt = Z_BASE_REAR + CARD_T
    parts = None
    for i in range(4):                                                    # four legs, 12 mm apart, now running across
        y = CARD_Y0 + 62 + 12 * i
        for x in (-28.0, 12.0):
            dio = cq.Workplane("YZ").workplane(offset=x).center(y, zt + 2.7).circle(2.65).extrude(9.5)
            lead = cq.Workplane("YZ").workplane(offset=x - 14).center(y, zt + 2.7).circle(0.65).extrude(37.5)
            parts = dio.union(lead) if parts is None else parts.union(dio).union(lead)
    cap = cq.Workplane("YZ").workplane(offset=14).center(CARD_Y0 + 20, zt + 6.5).circle(6.5).extrude(25)
    d["card_parts"] = parts.union(cap)
    mod = cbox(xi - 2.2 - MOD_L, xi - 2.2, USB_Y - MOD_W / 2, USB_Y + MOD_W / 2, z_pcb, zs)
    mod = mod.union(cbox(xi - 2.2 - MOD_L + 4, xi - 2.2 - MOD_L + 16, USB_Y - 6, USB_Y + 6, zs, zs + 7))   # its coil
    mod = mod.union(cbox(xi - USB_LEN + 1.0, HALF_W - 0.4, USB_Y - USB_W / 2, USB_Y + USB_W / 2, zs, zs + USB_H))
    d["module"] = mod
    tl, tw, tt = TESTER
    zc = zs + USB_H / 2
    t = cbox(HALF_W + 0.6, HALF_W + 11, USB_Y - 6, USB_Y + 6, zc - 2.2, zc + 2.2)                           # the plug's metal
    d["tester"] = t.union(cbox(HALF_W + 11, HALF_W + 11 + tl, USB_Y - tw / 2, USB_Y + tw / 2, zc - tt / 2, zc + tt / 2))
    d["tester_screen"] = cbox(HALF_W + 19, HALF_W + 51, USB_Y - 8, USB_Y + 8, zc + tt / 2, zc + tt / 2 + 0.6)
    for name, sx in (("clamp_l", -1), ("clamp_r", 1)):
        x0, x1 = sx * CLAMP_X - CLAMP_PAD / 2, sx * CLAMP_X + CLAMP_PAD / 2
        c = cbox(x0, x1, P.BASE_T, CLAMP_TOP, Z_BASE_REAR - 26, Z_BASE_REAR + 46)                           # arm on the base
        c = c.union(cbox(x0, x1, -75, CLAMP_TOP, Z_BASE_REAR - 26, Z_BASE_REAR - 12))                       # spine
        c = c.union(cbox(x0, x1, -75, -61, Z_BASE_REAR - 26, Z_BASE_REAR + 46))                             # lower arm
        c = c.union(cq.Workplane("XZ").workplane(offset=20).center(sx * CLAMP_X, Z_BASE_REAR + 36).circle(5).extrude(55))
        d[name] = c
    d["table"] = cbox(-260, 260, -20, 0, Z_BASE_REAR, 260)
    nuts = None                                                           # washer, nyloc and bolt end behind each boss
    for x, y in P.PINS:
        n = P._cyl(x, AY + y, 8.0, -P.WALL_T - P.PIN_BOSS_H - 12, -P.WALL_T - P.PIN_BOSS_H + 0.5)
        nuts = n if nuts is None else nuts.union(n)
    d["pin_nuts"] = nuts
    return d


# ============================================================ checks
def vol(a, b):
    return P._vol(a, b)


def gap(a, b):
    return a.val().distance(b.val())


def check(h, sl, d):
    res = []
    fr, motor = P.frame(), P.motor_dummy()
    res.append(("hood is one solid", h.solids().size() == 1))
    res.append(("sled is one solid", sl.solids().size() == 1))
    fixed = fr.union(motor).union(d["pin_nuts"]).union(P.pins_dummy())
    v = vol(h, fixed)
    res.append((f"hood clears frame, motor, pins and nuts ({v:.3f} mm3)", v < 1e-3))
    v = vol(h, sl) + vol(sl, fixed)
    res.append((f"sled clears the hood and everything fixed ({v:.3f} mm3)", v < 1e-3))
    # Everything that turns, as plain ENVELOPES (the real herringbone solids take minutes to
    # measure against, and an envelope is the safer test: it is bigger than the part).
    #   ring + split-ring lugs + wheel rim: all of r >= ring tooth tips, from 1 mm behind the gears forward
    #   planets and sun: full tip cylinders, same depth.   spider, spokes, hub: a full disc from the spider forward
    z_gear = P.GEAR_GAP - 1.0
    z_end = P.WHEEL_Z0 + P.WHEEL_T + P.POST_H
    geartrain = P._cyl(0, AY, P.R_OUT + P.LUG_REACH + 2, z_gear, z_end).cut(P._cyl(0, AY, P.R_RING_TIP - 0.5, z_gear - 1, z_end + 1))
    for x, y in P.PINS:
        geartrain = geartrain.union(P._cyl(x, AY + y, P.MODULE * (P.P + 2) / 2 + 0.5, z_gear, P.SPIDER_Z0))
    geartrain = geartrain.union(P._cyl(0, AY, P.MODULE * (P.S + 2) / 2 + 0.5, z_gear, P.SPIDER_Z0))
    geartrain = geartrain.union(P._cyl(0, AY, P.R_OUT + P.LUG_REACH + 2, P.SPIDER_Z0, z_end))
    v = vol(h, geartrain)
    g = gap(h, geartrain)
    res.append((f"hood clears the envelope of everything that turns (ring, lugs, planets, sun, spider, wheel): nearest {g:.1f} mm", v < 1e-3 and g >= 12))
    # the way on: 10 mm up, slide forward, drop. Nothing may be hit on the way.
    worst, near = 0.0, 1e9
    for dz in (-60, -40, -20, -10, -5, 0):
        hh = h.translate((0, 10, dz))
        worst = max(worst, vol(hh, fixed) + vol(hh, geartrain))
        near = min(near, gap(hh, geartrain))
    for dy in (10, 7, 4, 2):
        hh = h.translate((0, dy, 0))
        worst = max(worst, vol(hh, fixed) + vol(hh, geartrain))
    res.append((f"the way on (10 up, forward, down) hits nothing ({worst:.3f} mm3); gears never nearer than {near:.1f} mm", worst < 1e-3 and near >= 8))
    # it cannot leave without being lifted
    back = vol(h.translate((0, 0, -3)), fr)
    res.append((f"pulled straight back 3 mm it bites the frame: hook and peg hold ({back:.1f} mm3)", back > 5))
    side = min(vol(h.translate((s * 2, 0, 0)), fr) for s in (-1, 1))
    res.append((f"pushed 2 mm sideways it bites the frame: gusset ribs and peg hold ({side:.1f} mm3)", side > 5))
    fwd = vol(h.translate((0, 0, 2)), fr)
    res.append((f"pushed 2 mm forward it bites the frame: the strap's shoulder is on the wall's back ({fwd:.1f} mm3)", fwd > 5))
    lift = vol(h.translate((0, PEG_LEN + 2.5, 0)), fixed)
    res.append((f"lifted {PEG_LEN + 2.5:.1f} mm it is free ({lift:.3f} mm3)", lift < 1e-3))
    # clamps
    for name in ("clamp_l", "clamp_r"):
        g = gap(h, d[name])
        gt = gap(d["tester"], d[name])
        res.append((f"{name}: {g:.1f} mm from the hood, {gt:.1f} mm under the USB tester (clamp drawn {CLAMP_PAD:.0f} wide, {CLAMP_TOP - P.BASE_T:.0f} tall)",
                    g >= 6 and gt >= 4))
    # what is inside
    inside = d["card"].union(d["card_parts"]).union(d["module"])
    v = vol(inside, h) + vol(inside, fixed) + vol(d["card"].union(d["card_parts"]), sl)
    res.append((f"card, its parts and the module clear hood, sled, frame and motor ({v:.3f} mm3)", v < 1e-3))
    g = gap(d["card_parts"], motor)
    res.append((f"bare ladder and capacitor are {g:.1f} mm from the motor's metal back", g >= 10))
    g = gap(d["card_parts"], h)
    res.append((f"diodes and capacitor touch only the card and air: the nearest hood plastic is {g:.1f} mm away, behind the card", g >= 1.5))
    motor_back = P.WALL_LOCAL + P.MOTOR_LEN
    res.append((f"motor: its last {motor_back + Z_FRONT:.0f} mm (where the leads come out) are inside the hood; "
                f"side walls are {HALF_W - SIDE_T - P.MOTOR_SQ / 2:.0f} mm off its sides", motor_back + Z_FRONT >= 15))
    res.append((f"open air gap between the wall and the hood: {abs(Z_FRONT) - P.WALL_T:.0f} mm all the way up both sides; the whole front is open",
                abs(Z_FRONT) - P.WALL_T >= 20))
    # hidden from the front: the hood's outline lies inside the wall's solid column
    out = box(-HALF_W, Y_FOOT, HALF_W, AY + 200).intersection(dome(R_TOP))
    wall = P.wall_outline()
    for w in P.wall_windows(wall):
        wall = wall.difference(w)
    seen = out.difference(wall).area
    res.append((f"seen from dead ahead the hood body is behind solid wall, except {seen:.0f} mm2 (the hook's lip is the only thing in front)", seen < 60))
    bb = h.val().BoundingBox()
    res.append((f"hood {bb.xlen:.0f} x {bb.ylen:.0f} on the plate, {bb.zlen:.0f} mm tall: fits the P1S", max(bb.xlen, bb.ylen) <= 250 and bb.zlen <= 250))
    res.append((f"lip is a {LIP_BITE:.1f} mm flat overhang ({LIP_BITE / 0.42:.1f} lines): no support needed", LIP_BITE <= 1.5))
    return res


# ============================================================ picture
def picture(h, sl, d):
    import numpy as np
    import pyrender
    import trimesh
    from PIL import Image, ImageDraw, ImageFont

    def tm(name):
        return trimesh.load(os.path.join(OUT, f"_view_minimal_{name}.stl"), force="mesh")

    def frame_part(name):
        return trimesh.load(os.path.join(HERE, "stl", f"_view_{name}.stl"), force="mesh")

    GREY, DARK, ACC = (0.66, 0.68, 0.71), (0.26, 0.28, 0.32), (0.93, 0.45, 0.10)
    items = {"frame": (frame_part("frame"), GREY), "motor": (frame_part("motor"), DARK)}
    for n in ("wheel", "ring", "planet1", "planet2", "planet3", "sun", "spider", "grip"):
        items[n] = (frame_part(n), (0.76, 0.78, 0.81))
    items["hood"] = (tm("hood"), ACC)
    items["sled"] = (tm("sled"), (0.75, 0.33, 0.05))
    items["card"] = (tm("card"), (0.93, 0.89, 0.78))
    items["card_parts"] = (tm("card_parts"), (0.35, 0.37, 0.42))
    items["module"] = (tm("module"), (0.10, 0.35, 0.55))
    items["tester"] = (tm("tester"), (0.55, 0.75, 0.95))
    items["tester_screen"] = (tm("tester_screen"), (0.05, 0.05, 0.07))
    items["clamp_l"] = (tm("clamp_l"), (0.45, 0.47, 0.50))
    items["clamp_r"] = (tm("clamp_r"), (0.45, 0.47, 0.50))
    items["table"] = (tm("table"), (0.80, 0.76, 0.68))

    def look_at(eye, target, up=(0, 1, 0)):
        eye, target, up = np.array(eye, float), np.array(target, float), np.array(up, float)
        f = target - eye
        f /= np.linalg.norm(f)
        r = np.cross(f, up)
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        m = np.eye(4)
        m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = r, u, -f, eye
        return m

    def render(skip, eye, target, size, mag, ghost=()):
        sc = pyrender.Scene(bg_color=[1.0, 1.0, 1.0, 1.0], ambient_light=[0.34, 0.34, 0.34])
        for name, (mesh, col) in items.items():
            if name in skip:
                continue
            a = 0.22 if name in ghost else 1.0
            mat = pyrender.MetallicRoughnessMaterial(baseColorFactor=[*col, a], metallicFactor=0.0, roughnessFactor=0.9,
                                                     doubleSided=True, alphaMode="BLEND" if a < 1 else "OPAQUE")
            sc.add(pyrender.Mesh.from_trimesh(mesh, material=mat, smooth=False))
        pose = look_at(eye, target)
        cam = pyrender.OrthographicCamera(xmag=mag * size[0] / size[1], ymag=mag, znear=1, zfar=4000)
        sc.add(cam, pose=pose)
        for dvec, k in (((0.3, 1.0, -0.6), 1.5), ((-0.8, 0.5, -0.7), 1.0), ((0.6, 0.4, 1.0), 1.2), ((-0.5, 0.6, 0.9), 0.6), ((1.0, 0.2, -0.1), 0.7)):
            sc.add(pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=k), pose=look_at(np.array(dvec) * 1000, (0, 0, 0)))
        r = pyrender.OffscreenRenderer(*size)
        col, _ = r.render(sc)
        r.delete()

        def project(pt):
            v = np.linalg.inv(pose) @ np.array([*pt, 1.0])
            return (size[0] / 2 + v[0] / (mag * size[0] / size[1]) * size[0] / 2, size[1] / 2 - v[1] / mag * size[1] / 2)
        return Image.fromarray(col), project

    W, Hh = 1000, 900
    tgt = (0, 105, -45)
    turning = {"wheel", "ring", "planet1", "planet2", "planet3", "sun", "spider", "grip"}
    views = [
        ("1. from behind: one plain panel", set(), (-330, 290, -640), tgt, 165, ()),
        ("2. the hood alone, from the front: what is inside", turning | {"frame", "table", "clamp_l", "clamp_r"},
         (300, 200, 620), (10, 118, -60), 135, ("motor",)),
        ("3. from the front right: a plain side wall and the tester", set(), (520, 250, 560), tgt, 190, ()),
        ("4. from the side (wheel taken away)", turning | {"clamp_r"}, (900, 118, -45), (0, 118, -45), 135, ()),
    ]
    fonts = ["/System/Library/Fonts/Avenir Next.ttc", "/System/Library/Fonts/Avenir.ttc", "/System/Library/Fonts/Helvetica.ttc"]
    fpath = next((f for f in fonts if os.path.exists(f)), None)
    font = lambda px: ImageFont.truetype(fpath, px) if fpath else ImageFont.load_default()
    INK = (25, 25, 28)
    sheet = Image.new("RGB", (2 * W, 2 * Hh + 110), "white")
    dr = ImageDraw.Draw(sheet)
    dr.text((30, 22), "Concept MINIMAL: the hood", font=font(46), fill=INK)
    dr.text((30, 76), "one printed part, no screws: a hook over the wall top, a peg in the middle base hole", font=font(26), fill=(90, 90, 96))

    xi = HALF_W - SIDE_T
    notes = {
        0: [("plain back, nothing through it", (0, 150, Z_PANEL0), (40, 200)),
            ("both G-clamps: untouched", (-CLAMP_X, 30, Z_BASE_REAR - 20), (500, 830)),
            ("USB tester", (HALF_W + 45, USB_Y, Z_BASE_REAR + 8), (40, 560))],
        1: [("hook over the wall top", (0, AY + R_STRAP_IN, 0), (40, 80)),
            ("card on end, parts facing the motor", (-30, 185, Z_BASE_REAR + 2), (40, 150)),
            ("8 diodes", (-28, CARD_Y0 + 74, Z_BASE_REAR + 5), (40, 420)),
            ("motor (ghost): leads go straight back", (-20, AY - 20, -62), (40, 330)),
            ("capacitor", (30, CARD_Y0 + 20, Z_BASE_REAR + 12), (40, 640)),
            ("module on its sled (PLACEHOLDER size)", (xi - 25, USB_Y, Z_BASE_REAR + 4), (40, 720)),
            ("peg for the middle base hole", (HOLE_X, 5, HOLE_Z), (60, 850)),
            ("rib against the tall gusset", (xi - 1, 17, -60), (620, 850)),
            ("USB tester", (HALF_W + 45, USB_Y, Z_BASE_REAR + 14), (800, 560))],
        2: [("hook: the only thing in front of the wall", (0, AY + P.WALL_R, 3), (330, 60)),
            ("tester and phone lead, in shot", (HALF_W + 45, USB_Y, Z_BASE_REAR + 14), (560, 800))],
        3: [("hook", (HALF_W, AY + P.WALL_R + 2, 2), (150, 110)),
            ("30 mm open gap: air", (HALF_W, 200, -23), (60, 200)),
            ("motor", (HALF_W, AY, -25), (60, 300)),
            ("plain side", (HALF_W, 150, -70), (760, 300)),
            ("stands on the base", (HALF_W, 9, -60), (640, 840)),
            ("G-clamp", (HALF_W, 0, Z_BASE_REAR - 19), (800, 700))],
    }
    for i, (title, skip, eye, target, mag, ghost) in enumerate(views):
        img, proj = render(skip, eye, target, (W, Hh), mag, ghost)
        ox, oy = (i % 2) * W, 110 + (i // 2) * Hh
        sheet.paste(img, (ox, oy))
        dr.text((ox + 30, oy + 14), title, font=font(30), fill=INK)
        for text, pt, at in notes[i]:
            px, py = proj(pt)
            tx, ty = ox + at[0], oy + at[1]
            dr.text((tx, ty), text, font=font(24), fill=INK)
            bbox = dr.textbbox((tx, ty), text, font=font(24))
            sx = bbox[2] + 8 if px > bbox[2] - ox else bbox[0] - 8
            dr.line([(sx, (bbox[1] + bbox[3]) / 2), (ox + px, oy + py)], fill=INK, width=2)
            dr.ellipse([ox + px - 5, oy + py - 5, ox + px + 5, oy + py + 5], fill=INK)
    dr.line([(W, 110), (W, 110 + 2 * Hh)], fill=(215, 215, 220), width=2)
    dr.line([(0, 110 + Hh), (2 * W, 110 + Hh)], fill=(215, 215, 220), width=2)
    os.makedirs(os.path.dirname(PNG), exist_ok=True)
    sheet.save(PNG, optimize=True)
    print("wrote", PNG)


if __name__ == "__main__":
    h, sl, d = hood(), sled(), dummies()
    res = check(h, sl, d)
    for text, ok in res:
        print(f"[{'ok' if ok else 'NO'}] {text}")
    bad = [t for t, ok in res if not ok]
    v = h.val().Volume()
    vs = sl.val().Volume()
    print(f"hood {v / 1000:.0f} cm3 solid = {v * DENSITY_PETG:.0f} g if printed solid (4 walls make these thin walls solid); sled {vs / 1000:.1f} cm3")
    os.makedirs(OUT, exist_ok=True)
    kw = dict(tolerance=0.02, angularTolerance=0.15)
    to_bed = lambda part: part.translate((0, 0, -part.val().BoundingBox().zmin))
    cq.exporters.export(to_bed(h), os.path.join(OUT, "concept_minimal.stl"), **kw)           # back panel on the bed
    cq.exporters.export(to_bed(sl), os.path.join(OUT, "concept_minimal_sled.stl"), **kw)
    cq.exporters.export(h, os.path.join(OUT, "_view_minimal_hood.stl"), **kw)
    cq.exporters.export(sl, os.path.join(OUT, "_view_minimal_sled.stl"), **kw)
    for name, part in d.items():
        cq.exporters.export(part, os.path.join(OUT, f"_view_minimal_{name}.stl"), tolerance=0.05, angularTolerance=0.3)
    print("exported to", OUT, "(MASSING ONLY)" if not bad else "(CHECKS FAILED)")
    if "--no-png" not in sys.argv:
        picture(h, sl, d)
    if bad:
        sys.exit(f"{len(bad)} checks failed")
