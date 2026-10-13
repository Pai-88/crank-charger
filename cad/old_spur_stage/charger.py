"""The crank charger's mechanism: frame, 97T wheel, 20T pinion, grip, spacer.

Layout is the hand drill's: the big herringbone wheel turns on a fixed M8 axle
cantilevered from an upright wall, and the handle is bolted to the wheel
itself. Hand torque goes handle -> wheel -> teeth, never through the axle, so
nothing printed has to grip a round steel shaft. The NEMA23 bolts to the back
of the wall, its shaft pokes through, and the pinion slides onto the D-cut.

Model frame (mm): X right, Y UP, Z toward you. The wall's front face is Z=0 and
the wall runs to -Z; the table is Y=0. Gears sit in front of the wall in the
same orientation they print in (back face down).

    .venv/bin/python cad/charger.py          check, then export to cad/stl/

Tooth counts, module and face width come from design.transmission(); the
handle radius from design.CRANK_ARM_MM. Change them there, not here.
"""
import math
import os
import sys

import cadquery as cq
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import design
import gears

# ============================================================
# PARAMETERS (mm)
# ============================================================
_tx = design.transmission()
MODULE = _tx["module"]
FACE_W = _tx["face_width"]
Z_BIG, Z_PIN = _tx["stages"][0]
R_HANDLE = design.CRANK_ARM_MM

# NEMA23, StepperOnline 23HS22-2804S datasheet drawing (oyostepper.com PDF)
MOTOR_SQ = 57.0            # flange, "57 MAX"
MOTOR_LEN = 56.0
MOTOR_HOLE_PITCH = 47.14   # NEMA standard; the drawing says 47 +/- 0.1
MOTOR_HOLE_D = 5.0
MOTOR_PILOT_D, MOTOR_PILOT_H = 38.1, 1.6
MOTOR_SHAFT_D = 6.35
MOTOR_SHAFT_LEN = 21.0     # from the mounting face, +/- 1
MOTOR_FLAT = 5.85          # across the D-cut, +/- 0.15. MEASURE YOURS before printing the pinion
MOTOR_FLAT_LEN = 15.0      # the flat runs this far back from the shaft tip
MOTOR_FLANGE_T = 5.0       # not dimensioned on the drawing: an assumption, check it

# wall and base
WALL_T = 8.0
BASE_T = 8.0
BASE_DEPTH = 85.0          # behind the wall; the motor is 56 long
TABLE_CLEAR = 8.0          # wheel tip above the table, at least
FINGER_ROOM = 30.0         # under the grip at the bottom of the stroke, for your knuckles
LEFT_REACH = 75.0          # wall extends this far left of the axle
AXLE_PAD_R = 26.0          # wall outline radius round the axle
MOTOR_MARGIN = 8.0         # wall beyond the motor flange
PINION_Y = 44.0            # pinion axis height: low, the motor weighs 0.7 kg
GUSSET_T = 5.0
WINDOW_RIM = 9.0           # solid band left round every window

# axle: M8 x 60, head at the back, nyloc at the front
AXLE_D = 8.0
AXLE_HOLE = 8.4
AXLE_BOLT_LEN = 60.0
AXLE_BOSS_R, AXLE_BOSS_H = 17.0, 16.0
WASHER_M8 = 1.6
GEAR_GAP = 2 * WASHER_M8   # two steel washers space the wheel off the wall
NYLOC_M8 = 8.0

# motor mount: slotted so the centre distance can be set on assembly
SLOT = 1.0                 # +/- travel along the line of centres
POCKET_D = 2.0             # flange is let into the back of the wall
POCKET_SQ = MOTOR_SQ + 0.6 + 2 * SLOT
M5_CLEAR = 5.5
M5_NUT_AF, M5_NUT_T = 8.0, 4.0
M5_BOLT_LEN = 12.0
NUT_FIT = 0.3

# wheel
BRG_OD, BRG_ID, BRG_W = 22.0, 8.0, 7.0      # 608
BRG_FIT = 0.15             # on diameter: a firm push fit
POCKET_A = 7.3             # back bearing pocket, 0.3 deeper than the bearing so it floats
LAND_R, LAND_H = 7.5, 2.0
HUB_R = 19.0
RIM = 7.0                  # solid ring under the tooth roots
SPOKES, SPOKE_W = 6, 16.0
WINDOW_FILLET = 4.0
POST_R = 7.0               # handle post, printed with the wheel
PED_R, PED_H = 12.0, 16.0  # pedestal under the post: lifts your hand clear of the pinion
PED_CONE = 5.0             # pedestal necks down to the post over this height
HANDLE_BOLT_LEN = 100.0    # M6 x 100 down the middle of the post
M6_HOLE = 6.5
M6_NUT_AF, M6_NUT_T = 10.0, 5.0
WASHER_M6 = 1.6
BOLT_END_RECESS = 0.8      # handle bolt stops this far short of the wheel's back face

# grip: a sleeve that spins on the post
GRIP_OD = 28.0
GRIP_FLANGE_R, GRIP_FLANGE_T = 24.0, 4.0    # guard disc between your hand and the teeth
GRIP_CLEAR = 0.6           # on diameter
GRIP_END_FLOAT = 0.5

SHAFT_FIT = 0.2            # pinion bore over the motor shaft, on diameter
SPACER_OD = 12.0           # touches the bearings' inner rings only

BED = 240.0
OUT = os.path.join(HERE, "stl")

# ---- derived ----
A = gears.centre_distance(Z_BIG, Z_PIN, MODULE)
R_TIP = MODULE * (Z_BIG + 2) / 2
R_ROOT = MODULE * (Z_BIG - 2.5) / 2
AXLE_Y = max(R_TIP + TABLE_CLEAR, R_HANDLE + GRIP_OD / 2 + FINGER_ROOM)
THETA = math.asin((AXLE_Y - PINION_Y) / A)          # line of centres, below horizontal
PIN = (A * math.cos(THETA), PINION_Y)
U = (math.cos(THETA), -math.sin(THETA))             # unit vector axle -> pinion
X0, X1 = -LEFT_REACH, PIN[0] + MOTOR_SQ / 2 + MOTOR_MARGIN
WALL_LOCAL = WALL_T - POCKET_D                      # wall thickness under the motor flange
SHAFT_TIP_Z = MOTOR_SHAFT_LEN - WALL_LOCAL
BRG_R = (BRG_OD + BRG_FIT) / 2
CONE_H = BRG_R - LAND_R                             # 45 degrees: prints with no support
POCKET_B_Z = POCKET_A + CONE_H + LAND_H
HUB_LEN = POCKET_B_Z + BRG_W
SPACER_LEN = round(POCKET_B_Z - BRG_W, 1)           # holds the inner rings apart
# the handle bolt's length fixes the post: head, washer, post, wheel, stop short of the back
POST_H = HANDLE_BOLT_LEN - WASHER_M6 - FACE_W + BOLT_END_RECESS      # pedestal + post, above the wheel face
GRIP_LEN = POST_H - PED_H - GRIP_END_FLOAT
GRIP_Z0 = GEAR_GAP + FACE_W + PED_H                                 # where your hand starts, from the wall face
G3_X = PIN[0] - POCKET_SQ / 2 - GUSSET_T / 2 - 5.0                  # last gusset left of the motor
GUSSETS = [(-55.0, 45.0), (0.0, AXLE_Y - 12.0), (G3_X, 55.0), (X1 - GUSSET_T / 2, 70.0)]   # (x, height)
BASE_HOLES = [(-66.0, 70.0), (28.0, 70.0), (X1 - 14.0, 74.0)]                               # (x, behind wall)

def _pts(poly):
    return [(round(x, 4), round(y, 4)) for x, y in list(poly.exterior.coords)[:-1]]

def _prism(poly, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(_pts(poly)).close().extrude(z1 - z0)

def _cyl(x, y, r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)

def _hex_slot(cx, cy, af, travel):
    """Hexagon with two flats parallel to U, stretched +/- travel along U: holds a nut
    against turning while letting it slide with the motor."""
    rc, ang = af / math.sqrt(3), math.atan2(U[1], U[0])
    out = []
    for k in range(6):
        t = ang + math.radians(60 * k)
        sgn = 1 if math.cos(math.radians(60 * k)) > 0 else -1
        out.append((cx + rc * math.cos(t) + sgn * travel * U[0], cy + rc * math.sin(t) + sgn * travel * U[1]))
    return Polygon(out)

def wall_outline():
    h = MOTOR_SQ / 2 + MOTOR_MARGIN
    r = 6.0
    return MultiPoint([(X0, 0), (X1, 0)]).union(Point(0, AXLE_Y).buffer(AXLE_PAD_R, 48)).union(
        Point(X1 - r, PIN[1] + h - r).buffer(r, 16)).union(Point(X0 + r, 14).buffer(r, 16)).convex_hull

def wall_windows(outline):
    keep = [Point(0, AXLE_Y).buffer(AXLE_BOSS_R + WINDOW_RIM),
            box(PIN[0] - POCKET_SQ / 2, PIN[1] - POCKET_SQ / 2, PIN[0] + POCKET_SQ / 2, PIN[1] + POCKET_SQ / 2).buffer(WINDOW_RIM),
            box(X0, 0, X1, BASE_T + WINDOW_RIM)]
    keep += [box(x - GUSSET_T / 2 - 5, 0, x + GUSSET_T / 2 + 5, h + 5) for x, h in GUSSETS]
    keep.append(box(G3_X - GUSSET_T / 2 - 5, 0, X1, AXLE_Y + AXLE_PAD_R))      # solid from the last gusset to the motor
    free = outline.buffer(-WINDOW_RIM).difference(unary_union(keep)).buffer(-5).buffer(5, 12)
    polys = list(free.geoms) if hasattr(free, "geoms") else [free]
    return [p for p in polys if p.area > 500]

def frame():
    outline = wall_outline()
    body = _prism(outline, -WALL_T, 0)
    body = body.union(cq.Workplane("XY").workplane(offset=-WALL_T + 1).moveTo((X0 + X1) / 2, BASE_T / 2)
                      .rect(X1 - X0, BASE_T).extrude(-(BASE_DEPTH + 1)))
    for gx, h in GUSSETS:
        d = min(h - BASE_T, BASE_DEPTH)
        tri = [(BASE_T - 1, -WALL_T + 1), (h, -WALL_T + 1), (h, -WALL_T), (BASE_T, -WALL_T - d), (BASE_T - 1, -WALL_T - d)]
        body = body.union(cq.Workplane("YZ").workplane(offset=gx - GUSSET_T / 2).polyline(tri).close().extrude(GUSSET_T))
    body = body.union(_cyl(0, AXLE_Y, AXLE_BOSS_R, -WALL_T + 1, -WALL_T - AXLE_BOSS_H))
    # everything added; now cut
    body = body.cut(_cyl(0, AXLE_Y, AXLE_HOLE / 2, 1, -WALL_T - AXLE_BOSS_H - 1))
    for w in wall_windows(outline):
        body = body.cut(_prism(w, -WALL_T - 0.5, 0.5))
    px, py = PIN
    deg = math.degrees(math.atan2(U[1], U[0]))
    body = body.cut(cq.Workplane("XY").workplane(offset=-WALL_T - 0.5).center(px, py)
                    .rect(POCKET_SQ, POCKET_SQ).extrude(POCKET_D + 0.5))
    pilot = MOTOR_PILOT_D + 0.5
    body = body.cut(cq.Workplane("XY").workplane(offset=-WALL_T - 1).center(px, py)
                    .slot2D(pilot + 2 * SLOT, pilot, deg).extrude(WALL_T + 2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            hx, hy = px + sx * MOTOR_HOLE_PITCH / 2, py + sy * MOTOR_HOLE_PITCH / 2
            body = body.cut(cq.Workplane("XY").workplane(offset=-WALL_T - 1).center(hx, hy)
                            .slot2D(M5_CLEAR + 2 * SLOT, M5_CLEAR, deg).extrude(WALL_T + 2))
            body = body.cut(_prism(_hex_slot(hx, hy, M5_NUT_AF + NUT_FIT, SLOT), -(M5_NUT_T + NUT_FIT), 0.5))
    for bx, bz in BASE_HOLES:
        body = body.cut(cq.Workplane("XZ").workplane(offset=1).center(bx, -WALL_T - bz)
                        .circle(M5_CLEAR / 2).extrude(-(BASE_T + 2)))
    return body

def wheel():
    t = gears.gear(Z_BIG, MODULE, FACE_W, bore=0, hand=+1)
    rim_in = R_ROOT - RIM
    web = Point(0, 0).buffer(rim_in, 96).difference(Point(0, 0).buffer(HUB_R + 5, 48))
    solid = [Point(R_HANDLE, 0).buffer(PED_R + 3, 32)]
    for k in range(SPOKES):
        a = 2 * math.pi * k / SPOKES
        c, s = math.cos(a), math.sin(a)
        hw = SPOKE_W / 2
        solid.append(Polygon([(-hw * -s, -hw * c), (R_TIP * c - hw * -s, R_TIP * s - hw * c),
                              (R_TIP * c + hw * -s, R_TIP * s + hw * c), (hw * -s, hw * c)]))
    holes = web.difference(unary_union(solid)).buffer(-WINDOW_FILLET).buffer(WINDOW_FILLET, 12)
    for p in (holes.geoms if hasattr(holes, "geoms") else [holes]):
        if p.area > 100:
            t = t.cut(_prism(p, -0.5, FACE_W + 0.5))
    t = t.union(_cyl(0, 0, HUB_R, FACE_W - 1, HUB_LEN))
    # pedestal and handle post, printed upright with the wheel
    top = FACE_W + POST_H
    ped_top = FACE_W + PED_H
    foot = (cq.Workplane("XZ").polyline([(0, FACE_W - 1), (PED_R, FACE_W - 1), (PED_R, ped_top - PED_CONE),
                                         (POST_R + 2, ped_top), (POST_R, ped_top), (POST_R, top), (0, top)]).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)).translate((R_HANDLE, 0, 0)))
    t = t.union(foot)
    # bearing bore: pocket, 45 degree cone, land, pocket
    bore = (cq.Workplane("XZ").polyline([(0, -1), (BRG_R, -1), (BRG_R, POCKET_A), (LAND_R, POCKET_A + CONE_H),
                                         (LAND_R, POCKET_B_Z), (BRG_R, POCKET_B_Z), (BRG_R, HUB_LEN + 1), (0, HUB_LEN + 1)])
            .close().revolve(360, (0, 0, 0), (0, 1, 0)))
    t = t.cut(bore)
    t = t.cut(_cyl(R_HANDLE, 0, M6_HOLE / 2, -1, top + 1))
    rc = (M6_NUT_AF + NUT_FIT) / math.sqrt(3)
    nut = Polygon([(R_HANDLE + rc * math.cos(math.radians(60 * k)), rc * math.sin(math.radians(60 * k))) for k in range(6)])
    t = t.cut(_prism(nut, -1, M6_NUT_T + BOLT_END_RECESS))
    return t

def pinion():
    p = gears.gear(Z_PIN, MODULE, FACE_W, bore=0, hand=-1)
    r = (MOTOR_SHAFT_D + SHAFT_FIT) / 2
    flat = MOTOR_FLAT - MOTOR_SHAFT_D / 2 + SHAFT_FIT / 2          # centre to flat
    d = Point(0, 0).buffer(r, 32).intersection(box(-r - 1, -r - 1, flat, r + 1))
    return p.cut(_prism(d, -1, FACE_W + 1))

def grip():
    """Sleeve with a guard disc at the wheel end. Prints disc-down, no supports."""
    r, f = GRIP_OD / 2, GRIP_FLANGE_R
    prof = [(0, 0), (f - 1, 0), (f, 1), (f, GRIP_FLANGE_T - 1), (f - 1, GRIP_FLANGE_T),
            (r + 3, GRIP_FLANGE_T), (r, GRIP_FLANGE_T + 3), (r, GRIP_LEN - 2), (r - 2, GRIP_LEN), (0, GRIP_LEN)]
    g = cq.Workplane("XZ").polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return g.cut(_cyl(0, 0, POST_R + GRIP_CLEAR / 2, -1, GRIP_LEN + 1))

def spacer():
    return _cyl(0, 0, SPACER_OD / 2, 0, SPACER_LEN).cut(_cyl(0, 0, AXLE_HOLE / 2, -1, SPACER_LEN + 1))

def motor_dummy(shift=0.0):
    """The motor as bought, for collision checks only. shift slides it along the slots."""
    px, py = PIN[0] + shift * U[0], PIN[1] + shift * U[1]
    seat = -WALL_LOCAL
    m = (cq.Workplane("XY").workplane(offset=seat).center(px, py).rect(MOTOR_SQ, MOTOR_SQ).extrude(-MOTOR_LEN))
    m = m.union(_cyl(px, py, MOTOR_PILOT_D / 2, seat - 1, seat + MOTOR_PILOT_H))
    return m.union(_cyl(px, py, MOTOR_SHAFT_D / 2, seat - 1, seat + MOTOR_SHAFT_LEN))

def _vol(a, b):
    hit = a.intersect(b)
    return sum(s.Volume() for s in hit.solids().vals())

def _place_wheel(part, deg):
    return part.rotate((0, 0, 0), (0, 0, 1), deg).translate((0, AXLE_Y, GEAR_GAP))

def check(fr, wh, pn, gr, sp):
    res = list(gears.pair_checks(Z_BIG, Z_PIN, MODULE))
    line = math.degrees(math.atan2(U[1], U[0]))
    wheel_placed = _place_wheel(wh, line)                                  # tooth 0 on the line of centres
    pin_placed = (pn.rotate((0, 0, 0), (0, 0, 1), gears.mesh_angle(Z_PIN) + line)
                  .translate((PIN[0], PIN[1], GEAR_GAP)))
    motor = motor_dummy()
    for name, part in (("frame", fr), ("wheel", wh), ("pinion", pn), ("grip", gr), ("spacer", sp)):
        res.append((f"{name} is one solid", part.solids().size() == 1))
    res.append((f"wheel and pinion in mesh do not intersect ({_vol(wheel_placed, pin_placed):.4f} mm3)",
                _vol(wheel_placed, pin_placed) < 1e-3))
    res.append((f"wheel clears the frame ({_vol(wheel_placed, fr):.4f} mm3)", _vol(wheel_placed, fr) < 1e-3))
    res.append((f"pinion clears the frame ({_vol(pin_placed, fr):.4f} mm3)", _vol(pin_placed, fr) < 1e-3))
    for shift in (-SLOT, 0.0, SLOT):
        v = _vol(motor_dummy(shift), fr)
        res.append((f"motor at slot {shift:+.1f} mm clears the frame ({v:.4f} mm3)", v < 1e-3))
    # sweep everything that turns with the wheel through a full revolution
    z_top = GEAR_GAP + FACE_W + POST_H + WASHER_M6 + 6
    swept = (_cyl(0, AXLE_Y, R_HANDLE + PED_R + 0.5, GEAR_GAP + 0.01, GRIP_Z0)
             .union(_cyl(0, AXLE_Y, R_HANDLE + GRIP_FLANGE_R + 0.5, GRIP_Z0 - 0.01, z_top)))
    ring = _cyl(0, AXLE_Y, R_TIP + 0.5, GEAR_GAP, GEAR_GAP + FACE_W)
    fixed = fr.union(motor)
    res.append((f"handle sweep clears frame, motor and shaft ({_vol(swept, fixed):.4f} mm3)", _vol(swept, fixed) < 1e-3))
    res.append((f"tooth ring sweep clears frame and motor body ({_vol(ring, fr):.4f} mm3)", _vol(ring, fr) < 1e-3))
    pin_tip = A - MODULE * (Z_PIN + 2) / 2
    res.append((f"pedestal sweeps to {R_HANDLE + PED_R:.0f} mm, pinion tips start at {pin_tip:.0f} mm from the axle",
                R_HANDLE + PED_R + 2 <= pin_tip))
    res.append((f"pedestal stays inside the rim ({R_HANDLE + PED_R:.0f} <= {R_ROOT - 1:.0f} mm)", R_HANDLE + PED_R <= R_ROOT - 1))
    res.append((f"your hand starts {GRIP_Z0 + GRIP_FLANGE_T:.1f} mm from the wall, shaft tip is at {SHAFT_TIP_Z + 1:.1f} at worst: "
                f"{GRIP_Z0 - SHAFT_TIP_Z - 1:.1f} mm of air under the guard disc", GRIP_Z0 - SHAFT_TIP_Z - 1 >= 12))
    fingers = R_HANDLE + GRIP_OD / 2 + 20            # knuckles wrapped round the grip
    res.append((f"fingers reach {fingers:.0f} mm from the axle, teeth start at {R_ROOT:.0f}: the guard disc reaches {R_HANDLE + GRIP_FLANGE_R:.0f}",
                fingers <= min(R_ROOT, pin_tip) - 2 or R_HANDLE + GRIP_FLANGE_R >= R_ROOT + 2))
    res.append((f"wheel tip {AXLE_Y - R_TIP:.0f} mm above the table", AXLE_Y - R_TIP >= 5))
    res.append((f"{AXLE_Y - R_HANDLE - GRIP_OD / 2:.0f} mm under the grip at the bottom of the stroke (knuckles need about 30)",
                AXLE_Y - R_HANDLE - GRIP_OD / 2 >= 28))
    res.append((f"guard disc {AXLE_Y - R_HANDLE - GRIP_FLANGE_R:.0f} mm above the table", AXLE_Y - R_HANDLE - GRIP_FLANGE_R >= 5))
    # the motor shaft and the pinion
    engage = min(SHAFT_TIP_Z, GEAR_GAP + FACE_W) - GEAR_GAP
    res.append((f"pinion sits on {engage:.1f} mm of shaft (tip at {SHAFT_TIP_Z:.1f}, even if the shaft is 1 mm short)",
                engage - 1.0 >= 0.75 * FACE_W))
    res.append((f"D-cut covers the pinion (flat starts {SHAFT_TIP_Z - MOTOR_FLAT_LEN:.1f} mm from the wall face)",
                SHAFT_TIP_Z - MOTOR_FLAT_LEN <= GEAR_GAP))
    # fasteners
    bolt_end = M5_BOLT_LEN - MOTOR_FLANGE_T - WALL_LOCAL
    res.append((f"M5 x {M5_BOLT_LEN:.0f} ends {bolt_end:+.1f} mm past the wall face, wheel is {GEAR_GAP:.1f} away", bolt_end <= GEAR_GAP - 1.5))
    res.append((f"M5 bolt passes right through its nut", bolt_end >= 0))
    res.append((f"{WALL_LOCAL - M5_NUT_T - NUT_FIT:.1f} mm of wall left under each M5 nut", WALL_LOCAL - M5_NUT_T - NUT_FIT >= 1.2))
    stack = WASHER_M8 + AXLE_BOSS_H + WALL_T + GEAR_GAP + BRG_W + SPACER_LEN + BRG_W + WASHER_M8
    spare = AXLE_BOLT_LEN - stack - NYLOC_M8
    res.append((f"M8 x {AXLE_BOLT_LEN:.0f} axle: stack {stack:.1f} + nyloc {NYLOC_M8:.0f}, {spare:.1f} mm of thread spare", 0.5 <= spare <= 6))
    res.append((f"inner-ring spacer {SPACER_LEN} mm, hub land {POCKET_B_Z - POCKET_A:.2f} mm: back bearing floats "
                f"{POCKET_A - BRG_W:.1f} mm", SPACER_LEN >= POCKET_B_Z - BRG_W - 0.05 and POCKET_A > BRG_W))
    res.append((f"spacer OD {SPACER_OD} passes the hub land (dia {2 * LAND_R})", SPACER_OD + 1 <= 2 * LAND_R))
    res.append((f"M6 x {HANDLE_BOLT_LEN:.0f} handle bolt: pedestal {PED_H:.0f} + post {POST_H - PED_H:.1f} mm, grip {GRIP_LEN:.1f} mm "
                f"({GRIP_LEN - GRIP_FLANGE_T:.0f} to hold), ends {BOLT_END_RECESS} mm inside the back face",
                GRIP_LEN - GRIP_FLANGE_T >= 60 and BOLT_END_RECESS < M6_NUT_T))
    res.append((f"grip bore {2 * POST_R + GRIP_CLEAR:.1f} rides a {2 * POST_R:.0f} mm post and cannot drop over the {2 * (POST_R + 2):.0f} mm pedestal top",
                POST_R + GRIP_CLEAR / 2 < POST_R + 2))
    res.append((f"hub wall {HUB_R - BRG_R:.1f} mm round the bearings", HUB_R - BRG_R >= 4))
    # the printer
    for name, part in (("frame", fr), ("wheel", wh)):
        bb = part.val().BoundingBox()
        dims = sorted((bb.xlen, bb.ylen, bb.zlen))
        res.append((f"{name} {dims[2]:.0f} x {dims[1]:.0f} x {dims[0]:.0f} mm fits the bed", dims[2] <= BED))
    return res, wheel_placed, pin_placed, motor

if __name__ == "__main__":
    fr, wh, pn, gr, sp = frame(), wheel(), pinion(), grip(), spacer()
    res, wheel_placed, pin_placed, motor = check(fr, wh, pn, gr, sp)
    for text, ok in res:
        print(f"[{'ok' if ok else 'NO'}] {text}")
    bad = [t for t, ok in res if not ok]
    os.makedirs(OUT, exist_ok=True)
    kw = dict(tolerance=0.01, angularTolerance=0.1)
    # frame prints FRONT FACE DOWN: flip it so the wall face is on the bed
    fr_print = fr.rotate((0, 0, 0), (1, 0, 0), 180)
    fr_print = fr_print.translate((0, 0, -fr_print.val().BoundingBox().zmin))
    parts = {"frame": fr_print, "wheel_97T": wh, "pinion_20T": pn, "grip": gr, "axle_spacer": sp}
    if bad and "--force-view" not in sys.argv:
        sys.exit(f"{len(bad)} checks failed: nothing exported")
    if not bad:
        for name, part in parts.items():
            cq.exporters.export(part, os.path.join(OUT, f"{name}.stl"), **kw)
    # assembled view, for the preview render only
    line = math.degrees(math.atan2(U[1], U[0]))
    turn = line + round((125 - line) / (360 / Z_BIG)) * 360 / Z_BIG       # whole teeth, so the mesh stays true
    gr_placed = gr.translate((R_HANDLE, 0, FACE_W + PED_H + 0.2)).rotate((0, 0, 0), (0, 0, 1), turn).translate((0, AXLE_Y, GEAR_GAP))
    view = {"frame": fr, "wheel": _place_wheel(wh, turn), "pinion": pin_placed, "motor": motor, "grip": gr_placed}
    for name, part in view.items():
        cq.exporters.export(part, os.path.join(OUT, f"_view_{name}.stl"), tolerance=0.05, angularTolerance=0.2)
    print(f"centre distance {A:.2f} mm, axle {AXLE_Y:.0f} mm up, line of centres {math.degrees(THETA):.1f} deg below horizontal")
    print(f"exported to {OUT}" if not bad else "VIEW ONLY: checks failed")
