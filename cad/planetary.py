"""The crank charger's mechanism, planetary version: a herringbone STAR drive.

    ring gear (91T)  = the wheel you crank. It floats on the planets and is
                       driven through six dogs by the spoked wheel in front.
    3 planets (37T)  = idlers on 608 bearings, on M8 pins FIXED to the frame.
    sun (17T)        = on the NEMA23's shaft. Turns 5.35x faster than your hand.

The three pins run from the wall, through the planets, into a fixed spider in
front of the gears. The spider carries the axle the spoked wheel turns on, so
your hand's side load goes wheel -> axle -> spider -> pins -> wall and never
touches a gear tooth. The teeth carry torque only.

Herringbone teeth cannot be slid together, so the ring, the planets and the
sun are PRINTED IN PLACE, already meshed, as one job (gearset.stl, 5 bodies).

Model frame (mm): X right, Y UP, Z toward you. Wall front face is Z=0, the
wall runs to -Z, the table is Y=0.

    .venv/bin/python cad/planetary.py        check, then export to cad/stl/
"""
import math
import os
import sys

import cadquery as cq
from shapely.affinity import rotate as srot
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
_st = _tx["stages"][0]
MODULE, FACE_W = _tx["module"], _tx["face_width"]
S, P, R, N = _st["sun"], _st["planet"], _st["ring"], _st["planets"]
R_HANDLE = design.CRANK_ARM_MM
RING_RIM = design.RING_RIM

PIP_BACKLASH = 0.6         # at the pitch circle, per mesh. Wide on purpose: the set is
                           # printed already meshed and 0.28 mm is what keeps flanks apart.
                           # Was 0.4 (0.19 mm) for the first print, which came out as spaghetti.
SUN_HAND = +1              # planets are the opposite hand; the ring matches the planets

# NEMA23, StepperOnline 23HS22-2804S datasheet drawing
MOTOR_SQ = 57.0
MOTOR_LEN = 56.0
MOTOR_HOLE_PITCH = 47.14
MOTOR_PILOT_D, MOTOR_PILOT_H = 38.1, 1.6
MOTOR_SHAFT_D = 6.35
MOTOR_SHAFT_LEN = 21.0     # +/- 1
MOTOR_FLAT = 5.85          # across the D-cut, +/- 0.15. MEASURE YOURS
MOTOR_FLAT_LEN = 15.0
MOTOR_FLANGE_T = 5.0       # not on the drawing: an assumption

# wall and base
WALL_T = 8.0
BASE_T = 8.0
BASE_DEPTH = 85.0
BASE_HALF_W = 105.0
TABLE_CLEAR = 8.0
FINGER_ROOM = 30.0         # under the grip at the bottom of the stroke
PIN_BOSS_R, PIN_BOSS_H = 10.0, 8.0     # behind the wall, under each pin's nut
WALL_MARGIN = 6.0
GUSSET_T = 5.0
WINDOW_RIM = 9.0
POCKET_D = 2.0             # motor flange let into the back of the wall
POCKET_SQ = MOTOR_SQ + 0.6
M5_CLEAR = 5.5             # base holes, for screws into the table
M5_TAP = 4.3               # motor holes: the M5 bolts cut their own thread in the 6 mm wall, no nuts
M5_BOLT_LEN = 12.0
NUT_FIT = 0.3

# M8 hardware
M8_HOLE = 8.4
M8_HEAD_AF, M8_HEAD_T = 13.0, 5.3
HEAD_POCKET = 5.5
WASHER_M8 = 1.6
NYLOC_M8 = 8.0
PIN_BOLT_LEN = 50.0        # 3 pins, heads let into the spider, nylocs behind the wall
AXLE_BOLT_LEN = 40.0       # head let into the back of the spider, nyloc in front of the wheel
THREAD_SPARE = 1.5

# 608 bearings: planets and wheel hub
BRG_OD, BRG_W = 22.0, 7.0
BRG_FIT = 0.15
LAND_R = 7.5               # through-bore beside a bearing; clears a 12 mm spacer
SPACER_OD = 12.0           # spacers touch inner rings only
PIN_FLANGE_R, PIN_FLANGE_T = 11.0, 2.2   # foot of each pin spacer, against the wall: a wide seat
                                          # for the clamp load, and a stop behind each planet

GEAR_GAP = 2 * WASHER_M8   # gear backs stand this far off the wall
SPIDER_GAP = 2 * WASHER_M8 # two washers between each planet bearing and the spider
SPIDER_T = 10.0
SPIDER_ARM_W = 24.0
SPIDER_HUB_R = 18.0
SPIDER_BOSS_R = 11.0
PLANET_HOLES, PLANET_HOLE_R = 6, 8.0   # lightening holes

# wheel
WHEEL_T = 12.0
RIM_W = 20.0
HUB_R = 19.0
POCKET_A = 7.3             # back bearing pocket, 0.3 deep so the bearing floats
LAND_H = 2.0
SPOKES, SPOKE_W = 6, 16.0
WINDOW_FILLET = 4.0
DOGS = 6
DOG_W = 14.0               # along the rim
DOG_FIT = 0.3              # per side
RING_FLOAT = 0.8           # ring is free to move this far along the axle: the teeth centre it

# split ring: the same ring as two single-helix halves, for planets and a sun that already exist
LUGS = 6
LUG_W, LUG_REACH = 10.0, 6.0          # along the rim, and how far it sticks out
M3_HOLE, M3_PILOT = 3.4, 2.7
M3_HEAD_D, M3_HEAD_H = 6.5, 3.2       # counterbore in the rear half's lugs, so nothing stands proud toward the wall

# handle
POST_R = 7.0
PED_R, PED_H, PED_CONE = 12.0, 8.0, 4.0
HANDLE_BOLT_LEN = 90.0     # M6 x 90
M6_HOLE = 6.5
M6_NUT_AF, M6_NUT_T = 10.0, 5.0
WASHER_M6 = 1.6
BOLT_END_RECESS = 0.8
GRIP_OD = 28.0
GRIP_FLANGE_R, GRIP_FLANGE_T = 20.0, 4.0
GRIP_CLEAR = 0.6
GRIP_END_FLOAT = 0.5

SHAFT_FIT = 0.2
BED = 240.0
OUT = os.path.join(HERE, "stl")

# ---- derived ----
A_C = gears.centre_distance(S, P, MODULE)                 # sun to planet, = pin circle radius
R_RING_ROOT = MODULE * (R + 2.5) / 2
R_RING_TIP = MODULE * (R - 2) / 2
R_OUT = R_RING_ROOT + RING_RIM
AXLE_Y = max(R_OUT + TABLE_CLEAR, R_HANDLE + GRIP_OD / 2 + FINGER_ROOM)
PIN_ANGLES = [30.0 + 360.0 * i / N for i in range(N)]     # one pin straight below the motor when N=3
PINS = [(A_C * math.cos(math.radians(a)), A_C * math.sin(math.radians(a))) for a in PIN_ANGLES]
WALL_LOCAL = WALL_T - POCKET_D
SHAFT_TIP_Z = MOTOR_SHAFT_LEN - WALL_LOCAL
BRG_R = (BRG_OD + BRG_FIT) / 2
PLANET_BRG_Z = FACE_W - BRG_W                             # bearing sits at the FRONT of each planet
PIN_SPACER = GEAR_GAP + PLANET_BRG_Z                      # wall face to the back of the bearing
SPIDER_Z0 = GEAR_GAP + FACE_W + SPIDER_GAP
# the axle bolt's length decides how thick the middle of the spider is
HUB_STACK = WASHER_M8 + BRG_W + 0.0 + BRG_W + WASHER_M8   # spacer added below
CONE_H = BRG_R - LAND_R
POCKET_B_Z = POCKET_A + CONE_H + LAND_H
HUB_LEN = POCKET_B_Z + BRG_W
HUB_SPACER = round(POCKET_B_Z - BRG_W, 1)
SPIDER_MID = AXLE_BOLT_LEN - THREAD_SPARE - NYLOC_M8 - HUB_STACK - HUB_SPACER + HEAD_POCKET
SPIDER_BOSS_H = SPIDER_MID - SPIDER_T
WHEEL_Z0 = SPIDER_Z0 + SPIDER_MID + WASHER_M8
RING_H = WHEEL_Z0 - GEAR_GAP - RING_FLOAT                 # teeth plus skirt, without the dogs
DOG_H = WHEEL_T + RING_FLOAT
RIM_IN = R_OUT - RIM_W
POST_H = HANDLE_BOLT_LEN - WASHER_M6 - WHEEL_T + BOLT_END_RECESS
GRIP_LEN = POST_H - PED_H - GRIP_END_FLOAT
WALL_R = A_C + PIN_BOSS_R + WALL_MARGIN
X0, X1 = -BASE_HALF_W, BASE_HALF_W
GUSSETS = [(X0 + GUSSET_T / 2, 60.0), (-45.0, 155.0), (0.0, 55.0), (45.0, 155.0), (X1 - GUSSET_T / 2, 60.0)]
BASE_HOLES = [(-72.0, 70.0), (0.0, 74.0), (72.0, 70.0)]
DOG_ANGLES = [30.0 + 360.0 * i / DOGS for i in range(DOGS)]

def _pts(poly):
    return [(round(x, 4), round(y, 4)) for x, y in list(poly.exterior.coords)[:-1]]

def _prism(poly, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(_pts(poly)).close().extrude(z1 - z0)

def _cyl(x, y, r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)

def _hex(cx, cy, af):
    rc = af / math.sqrt(3)
    return Polygon([(cx + rc * math.cos(math.radians(60 * k)), cy + rc * math.sin(math.radians(60 * k))) for k in range(6)])

def _pieces(geom, min_area):
    return [p for p in (geom.geoms if hasattr(geom, "geoms") else [geom]) if p.area > min_area]

def _vol(a, b):
    return sum(s.Volume() for s in a.intersect(b).solids().vals())

def _bearing_bore(z_top):
    """Revolved cutter for a hub carrying two 608s: pocket, 45 degree cone (prints with
    no support), land, pocket."""
    return (cq.Workplane("XZ").polyline([(0, -1), (BRG_R, -1), (BRG_R, POCKET_A), (LAND_R, POCKET_A + CONE_H),
                                         (LAND_R, POCKET_B_Z), (BRG_R, POCKET_B_Z), (BRG_R, z_top + 1), (0, z_top + 1)])
            .close().revolve(360, (0, 0, 0), (0, 1, 0)))

# ------------------------------------------------------------ the gearset (local: axis at origin, back face Z=0)

def sun():
    g = gears.gear(S, MODULE, FACE_W, bore=0, hand=SUN_HAND, backlash=PIP_BACKLASH)
    r = (MOTOR_SHAFT_D + SHAFT_FIT) / 2
    flat = MOTOR_FLAT - MOTOR_SHAFT_D / 2 + SHAFT_FIT / 2
    d = Point(0, 0).buffer(r, 32).intersection(box(-r - 1, -r - 1, flat, r + 1))
    return g.cut(_prism(d, -1, FACE_W + 1))

def planet():
    g = gears.gear(P, MODULE, FACE_W, bore=0, hand=-SUN_HAND, backlash=PIP_BACKLASH)
    g = g.cut(_cyl(0, 0, LAND_R, -1, FACE_W + 1)).cut(_cyl(0, 0, BRG_R, PLANET_BRG_Z, FACE_W + 1))
    ring_r = (BRG_R + MODULE * (P - 2.5) / 2) / 2                   # midway between bearing seat and tooth roots
    for k in range(PLANET_HOLES):
        a = 2 * math.pi * k / PLANET_HOLES
        g = g.cut(_cyl(ring_r * math.cos(a), ring_r * math.sin(a), PLANET_HOLE_R, -1, FACE_W + 1))
    return g

def ring_gear():
    g = gears.ring(R, MODULE, FACE_W, R_OUT, hand=-SUN_HAND, backlash=PIP_BACKLASH)
    top = RING_H + DOG_H
    # skirt and dogs start as one tall shell; the gaps between the dogs are then cut out of
    # its top with straight-sided cutters, so no two curved faces ever have to coincide
    g = g.union(_cyl(0, 0, R_OUT, FACE_W - 0.5, top).cut(_cyl(0, 0, R_RING_ROOT, FACE_W - 1, top + 1)))
    dogs = unary_union([srot(box(0, -DOG_W / 2, R_OUT + 10, DOG_W / 2), a, origin=(0, 0)) for a in DOG_ANGLES])
    gaps = Point(0, 0).buffer(R_OUT + 3, 96).difference(Point(0, 0).buffer(R_RING_ROOT - 3, 96)).difference(dogs)
    for gap in _pieces(gaps, 1.0):
        g = g.cut(_prism(gap, RING_H, top + 1))
    return g

def ring_halves():
    """The ring as two halves in the ASSEMBLY frame (axis at origin, rear face Z=0):
    rear = teeth 0..6 with the planets' hand, front = teeth 6..12 with the other hand plus
    the skirt and dogs. Each half is built with its printed bottom on its own Z=0, so
    the front half is rotated to meet the rear one's helix at the split."""
    half = FACE_W / 2
    r_lug = R_OUT + LUG_REACH
    rear = gears.ring_half(R, MODULE, half, R_OUT, hand=-SUN_HAND, backlash=PIP_BACKLASH)
    front = gears.ring_half(R, MODULE, half, R_OUT, hand=SUN_HAND, backlash=PIP_BACKLASH)
    front = front.rotate((0, 0, 0), (0, 0, 1), -SUN_HAND * gears.half_twist(R, MODULE, half)).translate((0, 0, half))
    top = RING_H + DOG_H
    front = front.union(_cyl(0, 0, R_OUT, FACE_W - 0.5, top).cut(_cyl(0, 0, R_RING_ROOT, FACE_W - 1, top + 1)))
    dogs = unary_union([srot(box(0, -DOG_W / 2, R_OUT + 10, DOG_W / 2), a, origin=(0, 0)) for a in DOG_ANGLES])
    gaps = Point(0, 0).buffer(R_OUT + 3, 96).difference(Point(0, 0).buffer(R_RING_ROOT - 3, 96)).difference(dogs)
    for gap in _pieces(gaps, 1.0):
        front = front.cut(_prism(gap, RING_H, top + 1))
    for a in DOG_ANGLES:                                   # lugs sit between the dogs
        lug = srot(box(R_OUT - 1, -LUG_W / 2, r_lug, LUG_W / 2), a + 180.0 / DOGS, origin=(0, 0))
        hx, hy = (R_OUT + LUG_REACH / 2) * math.cos(math.radians(a + 180.0 / DOGS)), (R_OUT + LUG_REACH / 2) * math.sin(math.radians(a + 180.0 / DOGS))
        rear = rear.union(_prism(lug, 0, half)).cut(_cyl(hx, hy, M3_HOLE / 2, -1, half + 1)).cut(_cyl(hx, hy, M3_HEAD_D / 2, -1, M3_HEAD_H))
        front = front.union(_prism(lug, half, FACE_W)).cut(_cyl(hx, hy, M3_PILOT / 2, half - 1, FACE_W + 1))
    return rear, front

def gearset():
    """ring, planets, sun: five separate bodies, already in mesh, all backs on Z=0."""
    parts = {"ring": ring_gear(), "sun": sun()}
    pl = planet()
    for i, (ang, (x, y)) in enumerate(zip(PIN_ANGLES, PINS)):
        parts[f"planet{i + 1}"] = pl.rotate((0, 0, 0), (0, 0, 1), gears.planet_angle(ang, S, P)).translate((x, y, 0))
    return parts

# ------------------------------------------------------------ fixed parts

def spider():
    """Fixed carrier in front of the gears (local: back face Z=0). Three arms to the pins,
    the wheel's axle in the middle. Prints back face down."""
    hw = SPIDER_ARM_W / 2
    shape = [Point(0, 0).buffer(SPIDER_HUB_R, 32)]
    for ang, (x, y) in zip(PIN_ANGLES, PINS):
        shape.append(srot(box(0, -hw, A_C, hw), ang, origin=(0, 0)))
        shape.append(Point(x, y).buffer(hw + 2, 32))
    outline = unary_union(shape).buffer(6, 12).buffer(-6, 12)             # round the inside corners
    body = _prism(outline, 0, SPIDER_T).union(_cyl(0, 0, SPIDER_BOSS_R, SPIDER_T - 1, SPIDER_MID))
    body = body.cut(_cyl(0, 0, M8_HOLE / 2, -1, SPIDER_MID + 1))
    body = body.cut(_prism(_hex(0, 0, M8_HEAD_AF + NUT_FIT), -1, HEAD_POCKET))          # axle head, from the back
    for x, y in PINS:
        body = body.cut(_cyl(x, y, M8_HOLE / 2, -1, SPIDER_T + 1))
        body = body.cut(_prism(_hex(x, y, M8_HEAD_AF + NUT_FIT), SPIDER_T - HEAD_POCKET, SPIDER_T + 1))   # pin heads, from the front
    return body

def wall_outline():
    return MultiPoint([(X0, 0), (X1, 0)]).union(Point(0, AXLE_Y).buffer(WALL_R, 64)).convex_hull

def wall_windows(outline):
    hp = POCKET_SQ / 2
    keep = [box(-hp, AXLE_Y - hp, hp, AXLE_Y + hp).buffer(WINDOW_RIM), box(X0, 0, X1, BASE_T + WINDOW_RIM)]
    keep += [Point(x, AXLE_Y + y).buffer(PIN_BOSS_R + WINDOW_RIM) for x, y in PINS]
    keep += [box(x - GUSSET_T / 2 - 5, 0, x + GUSSET_T / 2 + 5, h + 5) for x, h in GUSSETS]
    inner = max(abs(x) for x, _ in GUSSETS[1:-1]) + GUSSET_T / 2 + 5
    keep.append(box(-inner, 0, inner, AXLE_Y + WALL_R))        # motor and pins sit in one solid column
    free = outline.buffer(-WINDOW_RIM).difference(unary_union(keep)).buffer(-6).buffer(6, 12)
    return _pieces(free, 600)

def frame():
    outline = wall_outline()
    body = _prism(outline, -WALL_T, 0)
    body = body.union(cq.Workplane("XY").workplane(offset=-WALL_T + 1).moveTo(0, BASE_T / 2)
                      .rect(X1 - X0, BASE_T).extrude(-(BASE_DEPTH + 1)))
    for gx, h in GUSSETS:
        d = min(h - BASE_T, BASE_DEPTH)
        tri = [(BASE_T - 1, -WALL_T + 1), (h, -WALL_T + 1), (h, -WALL_T), (BASE_T, -WALL_T - d), (BASE_T - 1, -WALL_T - d)]
        body = body.union(cq.Workplane("YZ").workplane(offset=gx - GUSSET_T / 2).polyline(tri).close().extrude(GUSSET_T))
    for x, y in PINS:
        body = body.union(_cyl(x, AXLE_Y + y, PIN_BOSS_R, -WALL_T + 1, -WALL_T - PIN_BOSS_H))
    for x, y in PINS:
        body = body.cut(_cyl(x, AXLE_Y + y, M8_HOLE / 2, 1, -WALL_T - PIN_BOSS_H - 1))
    for w in wall_windows(outline):
        body = body.cut(_prism(w, -WALL_T - 0.5, 0.5))
    body = body.cut(cq.Workplane("XY").workplane(offset=-WALL_T - 0.5).center(0, AXLE_Y)
                    .rect(POCKET_SQ, POCKET_SQ).extrude(POCKET_D + 0.5))
    body = body.cut(_cyl(0, AXLE_Y, (MOTOR_PILOT_D + 0.5) / 2, 1, -WALL_T - 1))
    for sx in (-1, 1):
        for sy in (-1, 1):
            hx, hy = sx * MOTOR_HOLE_PITCH / 2, AXLE_Y + sy * MOTOR_HOLE_PITCH / 2
            body = body.cut(_cyl(hx, hy, M5_TAP / 2, 1, -WALL_T - 1))
    for bx, bz in BASE_HOLES:
        body = body.cut(cq.Workplane("XZ").workplane(offset=1).center(bx, -WALL_T - bz)
                        .circle(M5_CLEAR / 2).extrude(-(BASE_T + 2)))
    return body

# ------------------------------------------------------------ the wheel you crank (local: back face Z=0)

def wheel():
    disc = Point(0, 0).buffer(R_OUT, 128)
    web = Point(0, 0).buffer(RIM_IN, 96).difference(Point(0, 0).buffer(HUB_R + 5, 48))
    solid = [Point(R_HANDLE, 0).buffer(PED_R + 3, 32)]
    for k in range(SPOKES):
        solid.append(srot(box(0, -SPOKE_W / 2, R_OUT, SPOKE_W / 2), 360.0 * k / SPOKES, origin=(0, 0)))
    holes = web.difference(unary_union(solid)).buffer(-WINDOW_FILLET).buffer(WINDOW_FILLET, 12)
    notches = [srot(box(R_RING_ROOT - DOG_FIT, -DOG_W / 2 - DOG_FIT, R_OUT + 2, DOG_W / 2 + DOG_FIT), a, origin=(0, 0))
               for a in DOG_ANGLES]
    plan = disc.difference(unary_union(_pieces(holes, 100) + notches))
    t = cq.Workplane("XY").polyline(_pts(plan)).close().extrude(WHEEL_T)
    for ring_ in plan.interiors:
        t = t.cut(_prism(Polygon(ring_), -0.5, WHEEL_T + 0.5))
    t = t.union(_cyl(0, 0, HUB_R, WHEEL_T - 1, HUB_LEN))
    top, ped_top = WHEEL_T + POST_H, WHEEL_T + PED_H
    post = (cq.Workplane("XZ").polyline([(0, WHEEL_T - 1), (PED_R, WHEEL_T - 1), (PED_R, ped_top - PED_CONE),
                                         (POST_R + 2, ped_top), (POST_R, ped_top), (POST_R, top), (0, top)]).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)).translate((R_HANDLE, 0, 0)))
    t = t.union(post).cut(_bearing_bore(HUB_LEN)).cut(_cyl(R_HANDLE, 0, M6_HOLE / 2, -1, top + 1))
    return t.cut(_prism(_hex(R_HANDLE, 0, M6_NUT_AF + NUT_FIT), -1, M6_NUT_T + BOLT_END_RECESS))

def grip():
    r, f = GRIP_OD / 2, GRIP_FLANGE_R
    prof = [(0, 0), (f - 1, 0), (f, 1), (f, GRIP_FLANGE_T - 1), (f - 1, GRIP_FLANGE_T),
            (r + 3, GRIP_FLANGE_T), (r, GRIP_FLANGE_T + 3), (r, GRIP_LEN - 2), (r - 2, GRIP_LEN), (0, GRIP_LEN)]
    g = cq.Workplane("XZ").polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return g.cut(_cyl(0, 0, POST_R + GRIP_CLEAR / 2, -1, GRIP_LEN + 1))

def spacer(length, flange=False):
    body = _cyl(0, 0, SPACER_OD / 2, 0, length)
    if flange:
        body = body.union(_cyl(0, 0, PIN_FLANGE_R, 0, PIN_FLANGE_T))
    return body.cut(_cyl(0, 0, M8_HOLE / 2, -1, length + 1))

def washer(hole, od, t):
    """Printed washer, flat on the bed. Replaces the bought M8 (16 OD) and M6 penny (18 OD) washers."""
    return _cyl(0, 0, od / 2, 0, t).cut(_cyl(0, 0, hole / 2, -1, t + 1))

def motor_dummy():
    seat = -WALL_LOCAL
    m = cq.Workplane("XY").workplane(offset=seat).center(0, AXLE_Y).rect(MOTOR_SQ, MOTOR_SQ).extrude(-MOTOR_LEN)
    m = m.union(_cyl(0, AXLE_Y, MOTOR_PILOT_D / 2, seat - 1, seat + MOTOR_PILOT_H))
    return m.union(_cyl(0, AXLE_Y, MOTOR_SHAFT_D / 2, seat - 1, seat + MOTOR_SHAFT_LEN))

def pins_dummy():
    """The three M8 pins with their spacers and washers, for collision checks only."""
    d = None
    for x, y in PINS:
        rod = _cyl(x, AXLE_Y + y, 4.0, -WALL_T - PIN_BOSS_H - 10, SPIDER_Z0 + SPIDER_T)
        rod = rod.union(_cyl(x, AXLE_Y + y, SPACER_OD / 2, 0.01, PIN_SPACER))
        rod = rod.union(_cyl(x, AXLE_Y + y, PIN_FLANGE_R, 0.01, PIN_FLANGE_T))
        d = rod if d is None else d.union(rod)
    return d

# ------------------------------------------------------------ checks

def place(part, z, deg=0.0):
    return part.rotate((0, 0, 0), (0, 0, 1), deg).translate((0, AXLE_Y, z))

def check(fr, gs, sp, wh, gr):
    res = list(gears.set_checks(S, P, R, N, MODULE, PIP_BACKLASH))
    placed = {k: place(v, GEAR_GAP) for k, v in gs.items()}
    planets = [placed[k] for k in placed if k.startswith("planet")]
    spider_p, wheel_p, motor, pins = place(sp, SPIDER_Z0), place(wh, WHEEL_Z0), motor_dummy(), pins_dummy()
    for name, part in [("frame", fr), ("spider", sp), ("wheel", wh), ("grip", gr)] + list(gs.items()):
        res.append((f"{name} is one solid", part.solids().size() == 1))
    # the gearset is born assembled: every pair of bodies must be separate
    worst = max([_vol(placed["sun"], p) for p in planets] + [_vol(placed["ring"], p) for p in planets]
                + [_vol(planets[i], planets[j]) for i in range(N) for j in range(i)] + [_vol(placed["sun"], placed["ring"])])
    res.append((f"sun, planets and ring are separate bodies in 3D (worst overlap {worst:.4f} mm3)", worst < 1e-3))
    fixed = fr.union(motor).union(spider_p).union(pins)
    v = sum(_vol(placed[k], fr.union(spider_p)) for k in placed)
    res.append((f"gearset clears the wall and the spider ({v:.4f} mm3)", v < 1e-3))
    v = sum(_vol(p, pins) for p in planets)
    res.append((f"planets clear their pins and spacers ({v:.4f} mm3)", v < 1e-3))
    v = _vol(placed["sun"].union(placed["ring"]), pins)
    res.append((f"sun and ring clear the pins ({v:.4f} mm3)", v < 1e-3))
    # the wheel and the ring turn together: sweep them through a revolution in 12 steps
    v = max(_vol(place(wh, WHEEL_Z0, a), fixed) + _vol(place(gs["ring"], GEAR_GAP, a), fixed) for a in range(0, 360, 30))
    res.append((f"wheel and ring clear everything fixed at 12 positions (worst {v:.4f} mm3)", v < 1e-3))
    v = _vol(wheel_p, placed["ring"])
    res.append((f"ring dogs sit in the wheel's notches without touching ({v:.4f} mm3)", v < 1e-3))
    v = _vol(wheel_p, place(gs["ring"], GEAR_GAP, 360 / DOGS / 2))
    res.append((f"and they DO drive: turn the ring half a dog and it hits the wheel ({v:.0f} mm3)", v > 100))
    res.append((f"ring floats {RING_FLOAT} mm under the wheel rim; dogs end flush with its front",
                abs(GEAR_GAP + RING_H + DOG_H - WHEEL_Z0 - WHEEL_T) < 1e-6))
    res.append((f"wheel back is {WHEEL_Z0 - SPIDER_Z0 - SPIDER_T:.1f} mm in front of the spider arms",
                WHEEL_Z0 - SPIDER_Z0 - SPIDER_T >= 3.0))
    # hand room
    res.append((f"ring {AXLE_Y - R_OUT:.0f} mm above the table", AXLE_Y - R_OUT >= 5))
    res.append((f"{AXLE_Y - R_HANDLE - GRIP_OD / 2:.0f} mm under the grip at the bottom of the stroke (knuckles need about 30)",
                AXLE_Y - R_HANDLE - GRIP_OD / 2 >= 28))
    res.append((f"pedestal inside the wheel ({R_HANDLE + PED_R:.0f} <= {R_OUT - 1:.0f} mm) and clear of the dogs' radius "
                f"at its own angle", R_HANDLE + PED_R <= R_OUT - 1 and min(abs((a + 180) % 360 - 180) for a in DOG_ANGLES) >= 20))
    res.append((f"handle nut pocket at {R_HANDLE:.0f} mm opens inside the ring skirt ({R_RING_ROOT:.0f} mm), "
                f"outside the spider ({A_C + SPIDER_ARM_W / 2 + 2:.0f} mm)",
                A_C + SPIDER_ARM_W / 2 + 2 < R_HANDLE - 6 and R_HANDLE + 6 < R_RING_ROOT))
    # motor shaft and sun
    engage = min(SHAFT_TIP_Z, GEAR_GAP + FACE_W) - GEAR_GAP
    res.append((f"sun sits on {engage:.1f} mm of shaft (tip at {SHAFT_TIP_Z:.1f}, even if the shaft is 1 mm short)",
                engage - 1.0 >= 0.75 * FACE_W))
    res.append((f"D-cut covers the sun (flat starts {SHAFT_TIP_Z - MOTOR_FLAT_LEN:.1f} mm from the wall face)",
                SHAFT_TIP_Z - MOTOR_FLAT_LEN <= GEAR_GAP))
    res.append((f"shaft tip at {SHAFT_TIP_Z + 1:.1f} mm worst, axle bolt head starts at {SPIDER_Z0:.1f}", SHAFT_TIP_Z + 1 + 1.5 <= SPIDER_Z0))
    sun_root = MODULE * (S - 2.5) / 2
    res.append((f"sun wall {sun_root - MOTOR_SHAFT_D / 2:.1f} mm between bore and tooth roots", sun_root - MOTOR_SHAFT_D / 2 >= 6))
    res.append((f"sun tips ({MODULE * (S + 2) / 2:.1f} mm) cover the motor pilot hole ({(MOTOR_PILOT_D + 0.5) / 2:.1f} mm)",
                MODULE * (S + 2) / 2 > (MOTOR_PILOT_D + 0.5) / 2))
    # planets
    hole_ring = (BRG_R + MODULE * (P - 2.5) / 2) / 2
    res.append((f"planet: {hole_ring - PLANET_HOLE_R - BRG_R:.1f} mm round the bearing, "
                f"{MODULE * (P - 2.5) / 2 - hole_ring - PLANET_HOLE_R:.1f} mm under the tooth roots",
                hole_ring - PLANET_HOLE_R - BRG_R >= 4 and MODULE * (P - 2.5) / 2 - hole_ring - PLANET_HOLE_R >= 4))
    res.append((f"pins at {A_C:.1f} mm clear the motor flange corner ({MOTOR_SQ / math.sqrt(2):.1f} mm) by "
                f"{A_C - MOTOR_SQ / math.sqrt(2) - 8:.1f} mm for a nut", A_C - MOTOR_SQ / math.sqrt(2) - 8 >= 8))
    # fasteners
    bolt_end = M5_BOLT_LEN - MOTOR_FLANGE_T - WALL_LOCAL
    res.append((f"M5 x {M5_BOLT_LEN:.0f} ends {bolt_end:+.1f} mm past the wall face, gears are {GEAR_GAP:.1f} away",
                0 <= bolt_end <= GEAR_GAP - 1.5))
    # self-tapped M5 in printed PETG: about 1.2 x d of thread is plenty for a motor that only reacts 0.34 N m
    res.append((f"M5 bolts cut {WALL_LOCAL:.1f} mm of thread in the wall ({WALL_LOCAL / 5:.1f} x d), pilot {M5_TAP} mm",
                WALL_LOCAL >= 1.2 * 5 and 4.1 <= M5_TAP <= 4.4))
    pin_grip = (SPIDER_T - HEAD_POCKET) + SPIDER_GAP + BRG_W + PIN_SPACER + WALL_T + PIN_BOSS_H + WASHER_M8
    spare = PIN_BOLT_LEN - pin_grip - NYLOC_M8
    res.append((f"M8 x {PIN_BOLT_LEN:.0f} pins: stack {pin_grip:.1f} + nyloc {NYLOC_M8:.0f}, {spare:.1f} mm of thread spare", 0.5 <= spare <= 6))
    ax_grip = (SPIDER_MID - HEAD_POCKET) + HUB_STACK + HUB_SPACER
    spare = AXLE_BOLT_LEN - ax_grip - NYLOC_M8
    res.append((f"M8 x {AXLE_BOLT_LEN:.0f} axle: stack {ax_grip:.1f} + nyloc {NYLOC_M8:.0f}, {spare:.1f} mm spare, "
                f"{SPIDER_MID - HEAD_POCKET:.1f} mm of spider under its head", 0.5 <= spare <= 6 and SPIDER_MID - HEAD_POCKET >= 6))
    res.append((f"{SPIDER_T - HEAD_POCKET:.1f} mm of spider under each pin head", SPIDER_T - HEAD_POCKET >= 4))
    # bought M8 washers run from 1.6 to 1.8 mm thick (Accu lists 1.8): three on each pin, two on the axle
    thick = 1.8 - WASHER_M8
    pin_worst = PIN_BOLT_LEN - pin_grip - NYLOC_M8 - 3 * thick
    ax_worst = AXLE_BOLT_LEN - ax_grip - NYLOC_M8 - 2 * thick
    res.append((f"with 1.8 mm washers the nylocs still bite: {pin_worst:.1f} mm spare on the pins, {ax_worst:.1f} on the axle, "
                f"ring float {RING_FLOAT + 3 * thick:.1f} mm", pin_worst >= 0.5 and ax_worst >= 0.5 and RING_FLOAT + 3 * thick <= 2.0))
    res.append((f"hub spacer {HUB_SPACER} mm against a {POCKET_B_Z - POCKET_A:.2f} mm land: back bearing floats "
                f"{POCKET_A - BRG_W:.1f} mm", HUB_SPACER >= POCKET_B_Z - BRG_W - 0.05 and POCKET_A > BRG_W))
    res.append((f"pin spacer {PIN_SPACER:.1f} mm, OD {SPACER_OD}, passes the planet bore (dia {2 * LAND_R})", SPACER_OD + 1 <= 2 * LAND_R))
    res.append((f"a planet can slide back {GEAR_GAP - PIN_FLANGE_T:.1f} mm before its spacer's foot stops it, "
                f"M5 bolt ends are {GEAR_GAP - bolt_end:.1f} mm back", 0.5 <= GEAR_GAP - PIN_FLANGE_T < GEAR_GAP - bolt_end
                and PIN_FLANGE_R > LAND_R + 2))
    res.append((f"M6 x {HANDLE_BOLT_LEN:.0f} handle bolt: pedestal {PED_H:.0f} + post {POST_H - PED_H:.1f} mm, grip {GRIP_LEN:.1f} mm "
                f"({GRIP_LEN - GRIP_FLANGE_T:.0f} to hold)", GRIP_LEN - GRIP_FLANGE_T >= 60 and BOLT_END_RECESS < M6_NUT_T))
    # the printer
    for name, part in (("frame", fr), ("wheel", wh), ("gearset", gs["ring"]), ("spider", sp)):
        bb = part.val().BoundingBox()
        dims = sorted((bb.xlen, bb.ylen, bb.zlen))
        res.append((f"{name} {dims[2]:.0f} x {dims[1]:.0f} x {dims[0]:.0f} mm fits the bed", dims[2] <= BED))
    # the split ring: same teeth, two parts, screwed together on the planets
    rear, front = ring_halves()
    rear_p, front_p = place(rear, GEAR_GAP), place(front, GEAR_GAP)
    for name, part in (("ring rear half", rear), ("ring front half", front)):
        res.append((f"{name} is one solid", part.solids().size() == 1))
    v = max(_vol(rear_p, p) for p in planets)
    res.append((f"rear half ring meshes the planets without touching ({v:.4f} mm3)", v < 1e-3))
    v = max(_vol(front_p, p) for p in planets)
    res.append((f"front half ring meets the rear one's helix and clears the planets ({v:.4f} mm3)", v < 1e-3))
    v = max(_vol(place(rear, GEAR_GAP, 180.0 / R), p) for p in planets)
    res.append((f"and half a tooth out it would hit them ({v:.0f} mm3)", v > 10))
    v = _vol(rear_p.union(front_p), fixed) + _vol(rear_p, front_p)
    res.append((f"both halves and their lugs clear frame, motor, spider, pins and each other ({v:.4f} mm3)", v < 1e-3))
    v = max(_vol(place(wh, WHEEL_Z0, a), fixed) + _vol(place(front, GEAR_GAP, a), fixed) for a in range(0, 360, 30))
    res.append((f"wheel and front half turning together clear everything fixed at 12 positions (worst {v:.4f} mm3)", v < 1e-3))
    res.append((f"split ring {2 * (R_OUT + LUG_REACH):.0f} mm across the lugs fits the 256 mm plate with 3 mm to spare",
                2 * (R_OUT + LUG_REACH) <= 250))
    res.append((f"lugs bottom out {AXLE_Y - R_OUT - LUG_REACH:.0f} mm above the table", AXLE_Y - R_OUT - LUG_REACH >= 5))
    res.append((f"M3 x 10 screws: {M3_HEAD_H:.1f} counterbore + {FACE_W / 2 - M3_HEAD_H:.1f} through + {FACE_W / 2:.0f} tapped, "
                f"{10 - (FACE_W - M3_HEAD_H):.1f} mm short of the far face", 0 < 10 - (FACE_W - M3_HEAD_H) < FACE_W / 2))
    view = dict(frame=fr, motor=motor, spider=spider_p, wheel=wheel_p, **placed)
    view["ring_rear_half"], view["ring_front_half"] = rear_p, front_p
    return res, view

if __name__ == "__main__":
    fr, gs, sp, wh, gr = frame(), gearset(), spider(), wheel(), grip()
    res, view = check(fr, gs, sp, wh, gr)
    for text, ok in res:
        print(f"[{'ok' if ok else 'NO'}] {text}")
    bad = [t for t, ok in res if not ok]
    if bad and "--force-view" not in sys.argv:
        sys.exit(f"{len(bad)} checks failed: nothing exported")
    os.makedirs(OUT, exist_ok=True)
    kw = dict(tolerance=0.01, angularTolerance=0.1)
    if not bad:
        fr_print = fr.rotate((0, 0, 0), (1, 0, 0), 180)                  # front face down on the bed
        fr_print = fr_print.translate((0, 0, -fr_print.val().BoundingBox().zmin))
        born = cq.Workplane("XY").newObject([cq.Compound.makeCompound([v.val() for v in gs.values()])])
        rear, front = ring_halves()
        parts = {"frame": fr_print, "gearset_print_in_place": born, "spider": sp, "wheel": wh, "grip": gr,
                 "pin_spacer_x3": spacer(PIN_SPACER, flange=True), "hub_spacer": spacer(HUB_SPACER),
                 "ring_rear_half": rear, "ring_front_half": front.translate((0, 0, -FACE_W / 2)),
                 "washer_m8": washer(M8_HOLE, 16.0, WASHER_M8), "washer_m6_penny": washer(M6_HOLE, 18.0, WASHER_M6)}
        for name, part in parts.items():
            cq.exporters.export(part, os.path.join(OUT, f"{name}.stl"), **kw)
    turn = 120.0
    view["wheel"] = place(wh, WHEEL_Z0, turn)
    view["ring"] = place(gs["ring"], GEAR_GAP, turn)      # a whole number of dogs: 120 deg is not a whole tooth, view only
    view["grip"] = (gr.translate((R_HANDLE, 0, WHEEL_T + PED_H + 0.2)).rotate((0, 0, 0), (0, 0, 1), turn)
                    .translate((0, AXLE_Y, WHEEL_Z0)))
    for name, part in view.items():
        cq.exporters.export(part, os.path.join(OUT, f"_view_{name}.stl"), tolerance=0.05, angularTolerance=0.2)
    print(f"star {S}/{P}/{R}, module {MODULE}: ring {2 * R_OUT:.1f} mm, pins on a {A_C:.1f} mm circle, axle {AXLE_Y:.0f} mm up")
    print(f"exported to {OUT}" if not bad else "VIEW ONLY: checks failed")
