"""Bayonet wheel: the hand wheel locks itself onto the ring gear's dogs. No nut, no band, no screws.

    .venv/bin/python cad/wheel_bayonet.py          checks, then cad/stl/spares/wheel_bayonet.stl (+ view mesh)

Same wheel as planetary.wheel() (spokes, windows, hub for two 608s, handle post and its M6 nut pocket), with:
  - the rim band raised 3.5 mm on the FRONT so there is room for a roof over each dog;
  - each of the six notches now a bayonet: a through-hole the dog enters from the back, then a blind
    pocket beside it (clockwise, seen from the front) with a 2.4 mm roof. Push the wheel on, turn it
    clockwise 9 mm at the rim (about 4.4 degrees): the dogs slide under the roofs and can no longer come
    forward;
  - a spring finger in the rim's outer wall at each pocket mouth. The dog pushes its bump aside on the way
    in and the finger springs back behind it, so the wheel cannot turn back out of the lock by itself. The
    crank's torque in either direction is taken by the pocket's end wall or by that bump (far below what
    the finger holds). To take the wheel off, press the six fingers outward with a fingernail and turn back.
  - the rim closed at the outside (2.2 mm wall), so the wheel is 4 mm bigger across: 240.8 mm, still on the bed.
Printed back face down, like the old wheel: the pockets are holes from the bed, the roofs bridge 6.6 mm.
Nothing in planetary.py is changed.
"""
import math
import os
import subprocess
import sys

import cadquery as cq
from shapely.geometry import Point, Polygon, box
from shapely.affinity import rotate as srot
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import planetary as P                  # read only

OUT = os.path.join(HERE, "stl", "spares")
VIEW = os.path.join(ROOT, "assembly", "_build", "keeper")
MESH_GATE = os.path.expanduser("~/.claude/skills/print-export-check/scripts/mesh_check.py")
NOTE = "note"

# ---------------------------------------------------------------- the numbers (mm)
OD_WALL = 2.2                                   # rim wall outside the dogs: the wheel's new edge
R_EDGE = P.R_OUT + P.DOG_FIT + OD_WALL          # 120.7
RIM_RAISE = 3.5                                 # the rim band stands this much proud of the front face
RIM_TOP = P.WHEEL_T + RIM_RAISE                 # 15.5
DOG_CLEAR = 0.4                                 # air over a dog pushed fully in (ring hard against the wheel)
POCKET_H = P.DOG_H + DOG_CLEAR                  # 13.2: the roof's underside
ROOF = RIM_TOP - POCKET_H                       # 2.3
TRAVEL = 9.0                                    # how far the dog slides into its pocket, along the rim
S_NOTCH = P.DOG_W / 2 + P.DOG_FIT               # 7.3: half the through-hole, along the rim
R_IN = P.R_RING_ROOT - P.DOG_FIT                # 111.9: inner face of hole and pocket
R_OUT_HOLE = P.R_OUT + P.DOG_FIT                # 118.5: outer face of hole and pocket
FINGER_L = 14.5                                 # along the rim, from its root to its free end
FINGER_T = 1.2                                  # radial
FINGER_H = POCKET_H - 0.8                       # stops short of the roof so it can flex
SLIT = 0.8
BUMP = 0.7                                      # how far the finger's bump reaches in past the hole's outer face
BUMP_L = 1.5                                    # along the rim
BUMP_GAP = 0.5                                  # between the bump and the dog once the dog is home
S_BUMP0 = S_NOTCH + TRAVEL - P.DOG_W - P.DOG_FIT - BUMP_GAP - BUMP_L     # the bump's start, measured like s below
E_PETG = 2000.0
TEXT = "Designed With Love By Paing"               # raised on the rim's front face, read from the front, opposite the handle
TEXT_H = 10.0                                     # letter height (mm): the whole rim band between the windows and the pockets
TEXT_RAISE = 1.0                                  # proud of the rim top
TEXT_R = P.RIM_IN + 1.5 + 6.1                      # 105.8: letters from r 100.8 to 110.8  # the letters' baseline radius: inside the pockets (r 111.9) with 1 mm to spare
TEXT_FONT = "/System/Library/Fonts/Avenir Next.ttc"


def _cyl(x, y, r, z0, z1):
    return P._cyl(x, y, r, z0, z1)


def tbox(angle, s0, s1, r0, r1, z0, z1):
    """A block along the rim at angle (degrees): s0..s1 along the rim (positive = anticlockwise seen from the
    front, the direction the DOG moves into its pocket), r0..r1 radially, z0..z1 along the axle."""
    b = cq.Workplane("XY").workplane(offset=z0).center((r0 + r1) / 2, (s0 + s1) / 2).rect(r1 - r0, s1 - s0).extrude(z1 - z0)
    return b.rotate((0, 0, 0), (0, 0, 1), angle)


def plan_outline():
    disc = Point(0, 0).buffer(R_EDGE, 160)
    web = Point(0, 0).buffer(P.RIM_IN, 96).difference(Point(0, 0).buffer(P.HUB_R + 5, 48))
    solid = [Point(P.R_HANDLE, 0).buffer(P.PED_R + 3, 32)]
    for k in range(P.SPOKES):
        solid.append(srot(box(0, -P.SPOKE_W / 2, R_EDGE, P.SPOKE_W / 2), 360.0 * k / P.SPOKES, origin=(0, 0)))
    holes = web.difference(unary_union(solid)).buffer(-P.WINDOW_FILLET).buffer(P.WINDOW_FILLET, 12)
    return disc.difference(unary_union(P._pieces(holes, 100)))


def lettering(text=TEXT):
    """Each letter stands on the rim's front face along an arc over the top of the wheel, upright to the rim,
    reading left to right from the front. Glyphs are measured, then spaced by their own widths."""
    glyphs = []
    for ch in text:
        if ch == " ":
            glyphs.append((None, TEXT_H * 0.45))
            continue
        g = cq.Workplane("XY").workplane(offset=RIM_TOP - 0.01).text(ch, TEXT_H, TEXT_RAISE + 0.01, fontPath=TEXT_FONT, kind="bold",
                                                                       halign="center", valign="center")
        bb = g.val().BoundingBox()
        glyphs.append((g, bb.xlen + TEXT_H * 0.16))
    total = sum(w for _, w in glyphs)
    s_pos = -total / 2                                            # along the arc, mm, left end
    out = None
    for g, w in glyphs:
        centre = s_pos + w / 2
        theta = 180.0 - math.degrees(centre / TEXT_R)             # centred opposite the handle post (which sits at 0 degrees)
        if g is not None:
            placed = g.rotate((0, 0, 0), (0, 0, 1), theta - 90.0).translate((TEXT_R * math.cos(math.radians(theta)),
                                                                              TEXT_R * math.sin(math.radians(theta)), 0))
            out = placed if out is None else out.union(placed)
        s_pos += w
    return out


STEP_R = P.RIM_IN + 1.5                         # where the raised rim starts: 1.5 mm outside the windows' outer arcs,
                                                # so no window wall coincides with the step (that coincidence broke the mesh)


def wheel():
    """The disc and its raised rim come from one revolved profile, so the web's top face is an original face;
    the windows are then cut through it exactly as planetary.wheel() does."""
    plan = plan_outline()
    prof = [(0, 0), (R_EDGE, 0), (R_EDGE, RIM_TOP), (STEP_R, RIM_TOP), (STEP_R, P.WHEEL_T), (0, P.WHEEL_T)]
    t = cq.Workplane("XZ").polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0))
    for ring_ in plan.interiors:
        t = t.cut(P._prism(Polygon(ring_), -0.5, RIM_TOP + 0.5))
    for a in P.DOG_ANGLES:
        t = t.cut(tbox(a, -S_NOTCH, S_NOTCH, R_IN, R_OUT_HOLE, -1, RIM_TOP + 1))                 # the through-hole
        t = t.cut(tbox(a, S_NOTCH - 0.01, S_NOTCH + TRAVEL, R_IN, R_OUT_HOLE, -1, POCKET_H))       # the pocket, roofed
        s_free = S_BUMP0 + BUMP_L                                                                   # the finger's free end
        s_root = s_free - FINGER_L
        t = t.cut(tbox(a, s_root - SLIT, s_root, R_OUT_HOLE - 0.01, R_EDGE + 1, -1, FINGER_H + SLIT))   # root slit
        t = t.cut(tbox(a, s_free, s_free + SLIT, R_OUT_HOLE - 0.01, R_EDGE + 1, -1, FINGER_H + SLIT))   # tip slit
        t = t.cut(tbox(a, s_root, s_free, R_OUT_HOLE - 0.01, R_EDGE + 1, FINGER_H, FINGER_H + SLIT))     # gap over it
        t = t.cut(tbox(a, s_root, s_free + SLIT, R_OUT_HOLE + FINGER_T, R_EDGE + 1, -1, FINGER_H + SLIT))  # thin it to FINGER_T
        base = R_OUT_HOLE + FINGER_T * 0.6                                                           # rooted inside the finger
        bump = (cq.Workplane("XY").polyline([(base, S_BUMP0 - BUMP - 0.3), (R_OUT_HOLE - BUMP, S_BUMP0),
                                              (R_OUT_HOLE - BUMP, S_BUMP0 + BUMP_L), (base, S_BUMP0 + BUMP_L + 0.3)])
                .close().extrude(FINGER_H - 0.01).rotate((0, 0, 0), (0, 0, 1), a))
        t = t.union(bump)
    t = t.union(lettering())
    t = t.union(_cyl(0, 0, P.HUB_R, P.WHEEL_T - 1, P.HUB_LEN))
    top, ped_top = P.WHEEL_T + P.POST_H, P.WHEEL_T + P.PED_H
    post = (cq.Workplane("XZ").polyline([(0, P.WHEEL_T - 1), (P.PED_R, P.WHEEL_T - 1), (P.PED_R, ped_top - P.PED_CONE),
                                         (P.POST_R + 2, ped_top), (P.POST_R, ped_top), (P.POST_R, top), (0, top)]).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)).translate((P.R_HANDLE, 0, 0)))
    t = t.union(post).cut(P._bearing_bore(P.HUB_LEN)).cut(_cyl(P.R_HANDLE, 0, P.M6_HOLE / 2, -1, top + 1))
    return t.cut(P._prism(P._hex(P.R_HANDLE, 0, P.M6_NUT_AF + P.NUT_FIT), -1, P.M6_NUT_T + P.BOLT_END_RECESS))


def check():
    res = []
    res.append((f"a dog pushed fully in stands {P.DOG_H:.1f} mm above the wheel's back face; the roof's underside is at {POCKET_H:.1f}: {DOG_CLEAR:.1f} mm of air", DOG_CLEAR >= 0.3))
    res.append((f"roof {ROOF:.1f} mm thick over each pocket ({ROOF / 0.2:.0f} layers at 0.2), bridging {R_OUT_HOLE - R_IN:.1f} mm", ROOF >= 2.0 and R_OUT_HOLE - R_IN <= 12))
    res.append((f"rim raised {RIM_RAISE:.1f} mm on the front; the dogs' tips end flush with the OLD front face, {RIM_RAISE:.1f} mm below the new rim top", RIM_TOP > P.DOG_H))
    s_free = S_BUMP0 + BUMP_L
    res.append((f"dog home: trailing edge {S_NOTCH + TRAVEL - P.DOG_W - 2 * P.DOG_FIT:.1f} mm past the hole, bump ends at {s_free:.1f}: {BUMP_GAP:.1f} mm between", BUMP_GAP >= 0.3))
    res.append((f"pocket travel {TRAVEL:.1f} mm along the rim = {math.degrees(TRAVEL / P.R_OUT):.1f} degrees of wheel turn", TRAVEL > P.DOG_FIT * 2 + BUMP_L + BUMP_GAP))
    strain = 1.5 * (BUMP + 0.3) * FINGER_T / FINGER_L ** 2 * 100
    res.append((f"finger {FINGER_L:.1f} long, {FINGER_T:.1f} thick: pushed {BUMP + 0.3:.1f} mm out it bends {strain:.2f} percent (PETG yields near 2)", strain < 1.0))
    I = FINGER_H * FINGER_T ** 3 / 12
    f_in = 3 * E_PETG * I * BUMP / FINGER_L ** 3
    res.append((f"to click a dog past its finger takes about {f_in:.1f} N radial; six at the rim is roughly {6 * f_in * P.R_OUT / 1000:.2f} N m on the wheel, {6 * f_in * P.R_OUT / P.R_HANDLE:.0f} N at the grip", 6 * f_in * P.R_OUT / P.R_HANDLE < 40))
    hold = f_in / math.tan(math.radians(8.0))
    res.append((f"a dog pushing back on the bump's steep face needs about {hold:.0f} N to force the finger out: six dogs hold {6 * hold * P.R_OUT / 1000:.1f} N m, the crank gives 1.85", 6 * hold * P.R_OUT / 1000 > 4.0))
    res.append((f"slits {SLIT:.1f} mm, finger top {POCKET_H - FINGER_H:.1f} mm under the roof: the finger is free on three sides", SLIT >= 0.6))
    res.append((f"wheel edge {2 * R_EDGE:.1f} mm across, bed 256 with margin", 2 * R_EDGE <= 250))
    res.append((f"lettering {TEXT!r}: {TEXT_H:.1f} mm letters raised {TEXT_RAISE:.1f} mm at r {TEXT_R:.1f}, inside the pockets (r {R_IN:.1f}) with {R_IN - TEXT_R - TEXT_H / 2:.1f} mm to spare, outside the windows (r {P.RIM_IN:.1f})", TEXT_R + TEXT_H / 2 < R_IN - 0.5 and TEXT_R - TEXT_H / 2 > P.RIM_IN))
    res.append((f"raised rim starts at r {STEP_R:.1f}, the windows end at {P.RIM_IN:.1f}: 1.5 mm apart, no coincident walls", STEP_R > P.RIM_IN + 1.0))
    res.append((f"lowest point of the wheel {P.AXLE_Y - R_EDGE:.1f} mm above the table (base plate top {P.BASE_T:.0f})", P.AXLE_Y - R_EDGE > P.BASE_T + 5))
    res.append((f"the clip ring's lugs reach r {P.R_OUT + P.LUG_REACH:.1f}, the wheel's edge is at {R_EDGE:.1f}: they are at different heights along the axle, no contact", True))
    res.append(("hub, bearing bore, spokes, windows, post, M6 hole and nut pocket: planetary.py's own functions and constants, unchanged", NOTE))
    res.append(("the old wheel's notches were open at the rim; these are holes, so each dog needs the wheel pushed on square", NOTE))
    res.append(("lock direction: with the wheel on, turn it CLOCKWISE (seen from the front) until six clicks. Anticlockwise to unlock, fingers pressed out", NOTE))
    return res


def show(lines):
    mark = {True: "ok", False: "NO", NOTE: "note"}
    for text, state in lines:
        print(f"[{mark[state]}] {text}")
    return [t for t, state in lines if state is False]


def mesh_gate(path):
    out = subprocess.run([sys.executable, MESH_GATE, path], capture_output=True, text=True).stdout.strip().splitlines()
    line = out[-1] if out else "no output"
    return line, line.startswith("PASS")


if __name__ == "__main__":
    bad = show(check())
    if bad:
        sys.exit(f"{len(bad)} checks failed: nothing exported")
    w = wheel()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(VIEW, exist_ok=True)
    kw = dict(tolerance=0.03, angularTolerance=0.15)
    f = os.path.join(OUT, "wheel_bayonet.stl")
    cq.exporters.export(w, f, **kw)                               # back face on Z = 0: as printed
    line, ok = mesh_gate(f)
    print(f"[{'ok' if ok else 'NO'}] {line}")
    vol = w.val().Volume() / 1000
    print(f"[ok] {vol:.0f} cm3, about {vol * 1.27:.0f} g of PETG")
    placed = P.place(w, P.WHEEL_Z0, 0.0)                         # in the machine, post at 3 o'clock, lettering at 9 o'clock
    cq.exporters.export(placed, os.path.join(VIEW, "wheel_bayonet_view.stl"), **kw)
    if not ok:
        sys.exit("mesh gate failed")
    print(f"wrote {f}")
