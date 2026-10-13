"""A replacement ring for planets and a sun that are already printed: two halves that CLIP together.

No screws, no nuts, no glue. Printed parts only.

    .venv/bin/python cad/ring_spare.py            check, then export to cad/stl/spares/
    .venv/bin/python cad/ring_spare.py --check    check only

Why two halves: a one-piece herringbone ring cannot go round planets that exist. Each half is a
plain helix half the face width (planetary.ring_halves(), teeth, skirt and dogs untouched) and
screws onto the planets from its own side. What is new here is only the join:

    lugs     N_LUG of them, where planetary.py has six. N_LUG divides the ring's tooth count, so
             the lugs line up every time the teeth do, and never "nearly".
    ears     two low walls on each rear lug. The front lug drops between them. One ear is upright:
             the hard stop. The other leans back at the angle the lug swings in at, so it stands just
             as close at its foot, and the halves share the drive whichever way the crank is turned.
    clips    one printed C per lug pair, printed on its side so the layers run round the C.
             Its rear arm slides into a channel under the rear lug (nothing stands proud toward
             the wall), its front arm rides over the front lug and a barb drops into a groove.
             The rear arm is narrower than the rest and the channel is cut to it, so the thick
             arm cannot enter the channel: a clip cannot go on back to front.
    key      a flat three-armed gauge with three pegs. It holds the planets 120 degrees apart
             while the first half goes on (they also mesh 3.3 degrees out, and then no pin fits).
    coupon   plate 1: the lug pair, six teeth of each half and one clip, to try before the long prints.

Every number that is not about the clip comes from planetary.py, gears.py, design.py or
batches.py. Frame for the halves: axis at the origin, rear face Z=0, split Z=HALF, as
planetary.ring_halves() returns them.
"""
import math
import os
import subprocess
import sys

import cadquery as cq
import numpy as np
import trimesh
from scipy.optimize import minimize
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.spatial import Delaunay
from shapely import contains_xy
from shapely.affinity import rotate as srot
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import batches
import design
import gears
import planetary as P

OUT = os.path.join(P.OUT, "spares")
GATE = os.path.expanduser("~/.claude/skills/print-export-check/scripts/mesh_check.py")

# ============================================================ what comes from the other files
HALF = P.FACE_W / 2
R_OUT, REACH, LUG_W = P.R_OUT, P.LUG_REACH, P.LUG_W
R_PITCH = P.MODULE * P.R / 2
TAN_B = math.tan(gears.HELIX)
RATE = gears.half_twist(P.R, P.MODULE, HALF) / HALF          # degrees the ring's helix turns per mm of height
TOP = P.RING_H + P.DOG_H
NOZZLE = gears.NOZZLE
LAYER = 0.2                                                  # PRINT.md's layer height

# ============================================================ the join (mm). These are the only new numbers.
N_LUG = next(n for n in range(P.LUGS, P.R + 1) if P.R % n == 0)   # 7: the smallest count of at least six that divides 91
SPARE_CLIPS = 2
LUG_ANGLES = [P.DOG_ANGLES[0] + 180.0 / P.DOGS + 360.0 * i / N_LUG for i in range(N_LUG)]

EAR_H = 1.6                # ears stand this far above the split face
EAR_T = 3.0                # least ear thickness, along the rim
EAR_CLR = 0.25             # front lug to the stop ear
EAR_IN = 0.5               # ears start this far outside the front half's wall
EAR_STEP = 0.3             # and stop this far inside the rear lug's edges, so no two faces of ear and lug lie in one plane
FOOT = 0.4                 # 45 degree chamfer on the front lug's two bed edges: a squashed first layer cannot prop it

CLIP_W = 8.0               # front arm and spine, along the rim
ARM_W = 6.0                # rear arm, along the rim: narrower, and the only part that fits the channel
CH_W = ARM_W + 0.5         # channel under the rear lug: its roof is a bridge this wide
ARM_R = 2.4                # rear arm
CH_D = 3.2                 # channel depth: 16 layers
ARM_F = 3.0                # front arm
SPINE_T = 2.2
PLAY = 0.3                 # the C is this much wider than the stack it holds: the stack's rear seat is a bridge, and bridges sag
PRY = 1.5                  # gap left between the spine and the lug tips, to lever the clip off
TIP_GAP = 0.3              # arm tips to the ring's wall
BARB_H = 0.7
RAMP_L = 1.6               # the barb's leading ramp
BARB_FLAT = 0.5
CATCH = 45.0               # degrees between the barb's catch face and the arm
CATCH_PLAY = 0.2
G_D = BARB_H + 0.3         # groove across the front lug's top
LEAD = 0.8                 # chamfer on the front lug's outer top edge, where the ramp starts (and where a clip slid in along a board meets the lug)
FILLET = 1.5               # inside corners of the C
SAG = 0.3                  # ASSUMED worst droop of the channel roof (a 6.5 mm bridge); the coupon measures the real one
SHRINK = 0.15              # ASSUMED worst closing-up of the clip's mouth as printed

COUPON_LUG = 4             # the lug pair the test piece is cut round: the one a planet meshes beside
COUPON_TEETH = 6           # teeth of each half on the test piece
COUPON_SKIRT = 5.0         # of the front half's skirt kept on it
CUT_AT = 318.0             # where the old ring is cut, in the gearset's printed pose: between two dogs, 48 degrees from the nearest planet

PEG_R = P.LAND_R - 0.4     # the key's pegs, in the 15 mm bore at the BACK of each planet
PEG_H = P.PLANET_BRG_Z - 1.0
KEY_T = 2.4
KEY_ARM_W = 16.0
KEY_HOLE_R = 11.0          # a finger hole in the middle, to lift it off

# what the plastic and the hand can do (the two hand numbers are estimates, not measured on him)
E_MPA = {"PLA": 3300.0, "PETG": 2100.0}                      # tensile modulus along the layers
STRAIN_MAX = {"PLA": 0.02, "PETG": 0.04}
YIELD_MPA = 50.0                                             # design.py: "50 MPa in-plane tensile"
MU = 0.3                                                     # plastic on plastic
NU = 0.35                                                    # Poisson's ratio, PLA and PETG near enough
KT = 1.4                                                     # stress raiser at an inside corner of a 2.2 to 3 mm section (the hand formula only)
THUMB_MAX = 60.0                                             # N a thumb pushes comfortably (estimate)
YANK_N = 200.0                                               # a hard one-arm yank on the grip
BRIDGE_MAX = 10.0                                            # a flat bridge the P1S lays cleanly in PLA or PETG
SHAKE_G = 3.0                                                # picked up by one half and jerked
DENSITY = 1.25e-6                                            # kg per mm3, PLA or PETG, taken as solid


def tan_g(r):
    """Slope of the screwing path at radius r: mm along the rim per mm of height."""
    return TAN_B * r / R_PITCH


GUARD_GAP = math.ceil((EAR_H * tan_g(R_OUT + REACH) + EAR_CLR) * 20) / 20     # the front lug swings in past the TOP of the leaning ear
GUARD_SLOPE = (GUARD_GAP - EAR_CLR) / EAR_H                                   # mm along the rim per mm of height; the lug's own path is tan_g()
WR = LUG_W + 2 * (GUARD_GAP + EAR_T + EAR_STEP)                               # rear lug, along the rim

# the clip's outline in (radius, z), seated
RI = R_OUT + TIP_GAP
RS0 = R_OUT + REACH + PRY
RS1 = RS0 + SPINE_T
ZR1 = CH_D - PLAY / 2
ZR0 = ZR1 - ARM_R
ZF0 = P.FACE_W + PLAY / 2
ZF1 = ZF0 + ARM_F
COT = 1.0 / math.tan(math.radians(CATCH))
R_CATCH = RI + RAMP_L + BARB_FLAT + BARB_H * COT             # where the catch face meets the arm
G_OUT = R_CATCH + CATCH_PLAY                                 # top of the groove's outer wall
LAND = R_OUT + REACH - LEAD - G_OUT                          # flat left on the front lug for the arm to bear on


# ============================================================ small builders
def _rz(profile, half_w, ang):
    """A (radius, z) outline, half_w each side of the radial line at angle ang."""
    return cq.Workplane("XZ").polyline(profile).close().extrude(half_w, both=True).rotate((0, 0, 0), (0, 0, 1), ang)


def _tz(profile, r0, r1, ang):
    """An (along the rim, z) outline, from radius r0 to r1 on the radial line at angle ang."""
    return (cq.Workplane("YZ").polyline(profile).close().extrude(r1 - r0).translate((r0, 0, 0))
            .rotate((0, 0, 0), (0, 0, 1), ang))


def _slab(r0, t0, r1, t1, ang, z0, z1):
    return P._prism(srot(box(r0, min(t0, t1), r1, max(t0, t1)), ang, origin=(0, 0)), z0, z1)


def _join(parts):
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    return out


def _arc(cx, cy, r, a0, a1, n=6):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def screw(part, d, sense):
    """Move a half d mm along the axis the only way its teeth allow: turning as it goes."""
    return part.rotate((0, 0, 0), (0, 0, 1), sense * RATE * d).translate((0, 0, d))


def screw_senses(planets, bare=None):
    """Which way each half turns as it is lifted off the planets: found on the solids, not assumed.
    Returns (front, rear) as lists of the senses (+1 or -1) that do NOT collide; each should hold exactly one."""
    rear, front = bare or bare_halves()
    free = lambda part: max(P._vol(part, p) for p in planets) < 1e-3
    return [s for s in (1, -1) if free(screw(front, 3.0, s))], [s for s in (1, -1) if free(screw(rear, -3.0, s))]


# ============================================================ the parts
def bare_halves():
    """The two halves with no lugs: teeth, skirt and dogs exactly as planetary.py makes them.
    The front one IS planetary's, its screw lugs cut away. The rear one is the gears.ring_half() call planetary
    starts from, because planetary's own rear half has six screw counterbores that bite 0.25 mm into the rim."""
    rear = gears.ring_half(P.R, P.MODULE, HALF, R_OUT, hand=-P.SUN_HAND, backlash=P.PIP_BACKLASH)
    front = P.ring_halves()[1].intersect(P._cyl(0, 0, R_OUT, -1, TOP + 1))
    return rear, front


def rear_lug(ang, stop):
    """stop = +1 or -1: the side (counter-clockwise or clockwise, seen from the front) the stop ear stands on."""
    r1 = R_OUT + REACH
    lug = _slab(R_OUT - 1, -WR / 2, r1, WR / 2, ang, 0, HALF)
    edge = WR / 2 - EAR_STEP
    lug = lug.union(_slab(R_OUT + EAR_IN, stop * (LUG_W / 2 + EAR_CLR), r1 - EAR_STEP, stop * edge, ang, HALF - 0.5, HALF + EAR_H))
    # the other ear leans back from the lug: EAR_CLR at its foot, GUARD_GAP at its top. It narrows upward: no overhang
    g = -stop
    lean = [(g * (LUG_W / 2 + EAR_CLR), HALF - 0.5), (g * edge, HALF - 0.5), (g * edge, HALF + EAR_H),
            (g * (LUG_W / 2 + GUARD_GAP), HALF + EAR_H), (g * (LUG_W / 2 + EAR_CLR), HALF)]
    lug = lug.union(_tz(lean, R_OUT + EAR_IN, r1 - EAR_STEP, ang))
    return lug.cut(_slab(R_OUT - 2, -CH_W / 2, r1 + 1, CH_W / 2, ang, -1, CH_D))


def front_lug(ang):
    r1, zt, zg = R_OUT + REACH, P.FACE_W, P.FACE_W - G_D
    lug = _slab(R_OUT - 1, -LUG_W / 2, r1, LUG_W / 2, ang, HALF, zt)
    # every cutter runs on past the faces it meets: a cutter that ends ON an edge leaves sliver triangles
    groove = [(R_OUT - 2, zg), (G_OUT - G_D * COT, zg), (G_OUT, zt), (G_OUT + COT, zt + 1), (R_OUT - 2, zt + 1)]
    lead = [(r1 - LEAD - 1, zt + 1), (r1 + 1, zt - LEAD - 1), (r1 + 1, zt + 1)]
    lug = lug.cut(_rz(groove, LUG_W / 2 + 1, ang)).cut(_rz(lead, LUG_W / 2 + 1, ang))
    for s in (1, -1):
        foot = [(s * (LUG_W / 2 - FOOT - 0.5), HALF - 0.5), (s * (LUG_W / 2 + 0.5), HALF - 0.5), (s * (LUG_W / 2 + 0.5), HALF + FOOT + 0.5)]
        lug = lug.cut(_tz(foot, R_OUT - 2, r1 + 1, ang))
    return lug


def halves(stop):
    rear, front = bare_halves()
    rear = rear.union(_join([rear_lug(a, stop) for a in LUG_ANGLES]))
    front = front.union(_join([front_lug(a) for a in LUG_ANGLES]))
    return rear, front


R_ARM = R_OUT + REACH + 0.5                                  # the narrow rear arm runs to here: 0.5 mm outside the lug's tip, so the step never touches it


def clip_outline(split=False):
    """(radius, z) outline of one clip where it sits, counter-clockwise from the rear arm's tip.
    It carries two extra points, where the line radius = R_ARM crosses it: split=True also returns their places
    in the list, so the narrow rear arm and the rest are cut from the SAME points (no sliver between them)."""
    c = 0.8
    pts = [(RI + 0.5, ZR0), (R_ARM, ZR0), (RS1 - c, ZR0), (RS1, ZR0 + c), (RS1, ZF1 - c), (RS1 - c, ZF1), (RI + 0.5, ZF1), (RI, ZF1 - 0.5),
           (RI, ZF0), (RI + RAMP_L, ZF0 - BARB_H), (RI + RAMP_L + BARB_FLAT, ZF0 - BARB_H), (R_CATCH, ZF0)]
    pts += _arc(RS0 - FILLET, ZF0 - FILLET, FILLET, 90, 0, 12)      # front inside corner
    for a, b in zip(_arc(RS0 - FILLET, ZR1 + FILLET, FILLET, 0, -90, 12), _arc(RS0 - FILLET, ZR1 + FILLET, FILLET, 0, -90, 12)[1:] + [None]):
        pts.append(a)                                               # rear inside corner
        if b is not None and b[0] < R_ARM < a[0]:
            pts.append((R_ARM, a[1] + (b[1] - a[1]) * (R_ARM - a[0]) / (b[0] - a[0])))
    pts += [(RI + 0.6, ZR1), (RI, ZR1 - 0.6), (RI, ZR0 + 0.5)]
    pts = [(round(r, 4), round(z, 4)) for r, z in pts]
    if not split:
        return pts
    at = [i for i, q in enumerate(pts) if abs(q[0] - round(R_ARM, 4)) < 1e-9]
    return pts, at[0], at[1]


def clip(ang=None, back_to_front=False):
    """One clip: in place on the lug pair at ang, or (ang None) lying on its side as it prints.
    On its side the whole outline is ARM_W tall, then everything but the rear arm goes on up to CLIP_W: no overhang.
    back_to_front: seated the wrong way up, thick arm at the back (for the check that this cannot be done)."""
    pts, i0, i1 = clip_outline(split=True)
    r0, z0 = min(q[0] for q in pts), min(q[1] for q in pts)
    move = lambda qs: Polygon([(q[0] - r0, q[1] - z0) for q in qs])
    flat = P._prism(move(pts), 0, ARM_W).union(P._prism(move(pts[i0:i1 + 1]), 0, CLIP_W))
    if ang is None:
        return flat
    # stood up: the outline's own (radius, z), the rear arm centred on the lug's radial line
    seated = flat.rotate((0, 0, 0), (1, 0, 0), 90).translate((r0, ARM_W / 2, z0))
    if back_to_front:
        mid = (ZR1 + ZF0) / 2
        seated = seated.rotate((0, 0, mid), (1, 0, mid), 180)
    return seated.rotate((0, 0, 0), (0, 0, 1), ang)


def key():
    """The planet key as it prints: flat, pegs up. Turned over, its pegs sit in the backs of the three planets."""
    shape = [Point(0, 0).buffer(KEY_HOLE_R + 7.0, 32)]
    for ang, (x, y) in zip(P.PIN_ANGLES, P.PINS):
        shape.append(srot(box(0, -KEY_ARM_W / 2, P.A_C, KEY_ARM_W / 2), ang, origin=(0, 0)))
        shape.append(Point(x, y).buffer(PEG_R + 4.0, 32))
    plate = unary_union(shape).buffer(5, 12).buffer(-5, 12)
    body = P._prism(plate, 0, KEY_T).cut(P._cyl(0, 0, KEY_HOLE_R, -1, KEY_T + 1))
    top = KEY_T + PEG_H
    peg = (cq.Workplane("XZ").polyline([(0, KEY_T - 0.5), (PEG_R, KEY_T - 0.5), (PEG_R, top - 1.0), (PEG_R - 1.0, top), (0, top)])
           .close().revolve(360, (0, 0, 0), (0, 1, 0)))
    for x, y in P.PINS:
        body = body.union(peg.translate((x, y, 0)))
    return body


def coupon_parts(rear, front):
    """One lug pair with COUPON_TEETH teeth of each half, cut out of the real halves and still where the ring has them."""
    a = LUG_ANGLES[COUPON_LUG]
    r_in, r_out = P.R_RING_TIP - 1.0, R_OUT + REACH + 10
    span = 180.0 * COUPON_TEETH / P.R
    arc = lambda r, a0, a1: [(r * math.cos(math.radians(a + t)), r * math.sin(math.radians(a + t))) for t in np.linspace(a0, a1, 13)]
    sector = Polygon(arc(r_in, -span, span) + arc(r_out, span, -span))
    return (rear.intersect(P._prism(sector, -1, HALF + EAR_H + 1)),
            front.intersect(P._prism(sector, HALF - 1, P.FACE_W + COUPON_SKIRT)))


def coupon(rear, front):
    """The test plate: both pieces as they print (the front one split face down) and one clip on its side,
    batches.GAP apart. Three bodies."""
    a = LUG_ANGLES[COUPON_LUG]
    r, f = coupon_parts(rear, front)
    turn = lambda p: p.rotate((0, 0, 0), (0, 0, 1), -a)
    out, x = [], 0.0
    for part in (turn(r), turn(f).translate((0, 0, -HALF)), clip()):
        bb = part.val().BoundingBox()
        out.append(part.translate((x - bb.xmin, -(bb.ymin + bb.ymax) / 2, 0)))
        x += bb.xlen + batches.GAP
    return out


# ============================================================ the numbers behind the clip
def clip_fe(load_r, z_up, z_down, h=0.12):
    """The clip's outline as a plane-stress sheet of constant-strain triangles: ARM_W thick in the rear arm, CLIP_W
    in the rest. One newton pushes the front arm forward along z_up over the radii load_r, one pushes the rear arm
    back along z_down over the same radii (equal, opposite, in line: no support carries anything).
    Returns, per newton and for E = 1 MPa: mm the two loaded faces part, and the peak strain (largest principal,
    averaged at each node, nodes within 0.6 mm of a load left out) with where it is. Divide both by E."""
    outline = clip_outline()
    poly = Polygon(outline)
    edge = poly.exterior
    n = int(edge.length / h)
    pts = [edge.interpolate(i * edge.length / n).coords[0] for i in range(n)] + list(outline)
    x0, y0, x1, y1 = poly.bounds
    gx, gy = np.meshgrid(np.arange(x0, x1, h), np.arange(y0, y1, h))
    keep = contains_xy(poly.buffer(-0.5 * h), gx.ravel(), gy.ravel())
    pts = np.unique(np.round(np.vstack([np.array(pts), np.c_[gx.ravel()[keep], gy.ravel()[keep]]]), 6), axis=0)
    tri = Delaunay(pts).simplices
    cen = pts[tri].mean(axis=1)
    tri = tri[contains_xy(poly, cen[:, 0], cen[:, 1])]
    q = pts[tri]
    area = 0.5 * ((q[:, 1, 0] - q[:, 0, 0]) * (q[:, 2, 1] - q[:, 0, 1]) - (q[:, 2, 0] - q[:, 0, 0]) * (q[:, 1, 1] - q[:, 0, 1]))
    tri[area < 0] = tri[area < 0][:, [0, 2, 1]]
    tri = tri[np.abs(area) > 1e-9]
    q = pts[tri]
    area = 0.5 * ((q[:, 1, 0] - q[:, 0, 0]) * (q[:, 2, 1] - q[:, 0, 1]) - (q[:, 2, 0] - q[:, 0, 0]) * (q[:, 1, 1] - q[:, 0, 1]))
    cen = q.mean(axis=1)
    bb = np.stack([q[:, 1, 1] - q[:, 2, 1], q[:, 2, 1] - q[:, 0, 1], q[:, 0, 1] - q[:, 1, 1]], 1)
    cc = np.stack([q[:, 2, 0] - q[:, 1, 0], q[:, 0, 0] - q[:, 2, 0], q[:, 1, 0] - q[:, 0, 0]], 1)
    B = np.zeros((len(tri), 3, 6))
    B[:, 0, 0::2], B[:, 1, 1::2], B[:, 2, 0::2], B[:, 2, 1::2] = bb, cc, cc, bb
    B /= (2 * area)[:, None, None]
    D = 1.0 / (1 - NU * NU) * np.array([[1, NU, 0], [NU, 1, 0], [0, 0, (1 - NU) / 2]])
    thick = np.where((cen[:, 1] < ZR1 + 0.01) & (cen[:, 0] < R_ARM), ARM_W, CLIP_W)
    ke = np.einsum("eji,jk,ekl->eil", B, D, B) * (area * thick)[:, None, None]
    dof = np.stack([2 * tri, 2 * tri + 1], 2).reshape(len(tri), 6)
    K = coo_matrix((ke.ravel(), (np.repeat(dof, 6, 1).ravel(), np.tile(dof, (1, 6)).ravel())), shape=(2 * len(pts),) * 2).tocsr()
    on = lambda z: np.nonzero((np.abs(pts[:, 1] - z) < 1e-4) & (pts[:, 0] >= load_r[0] - 1e-6) & (pts[:, 0] <= load_r[1] + 1e-6))[0]
    up, down = on(z_up), on(z_down)
    f = np.zeros(2 * len(pts))
    f[2 * up + 1] += 1.0 / len(up)
    f[2 * down + 1] -= 1.0 / len(down)
    spine = np.nonzero(pts[:, 0] > RS1 - 1e-6)[0]                       # hold the spine's outer face: two points, three freedoms
    lo, hi = spine[np.argmin(pts[spine, 1])], spine[np.argmax(pts[spine, 1])]
    free = np.setdiff1d(np.arange(2 * len(pts)), [2 * lo, 2 * lo + 1, 2 * hi])
    u = np.zeros(2 * len(pts))
    u[free] = spsolve(K[free][:, free], f[free])
    part = u[2 * up + 1].mean() - u[2 * down + 1].mean()
    eps = np.einsum("eij,ej->ei", B, u[dof])
    rad = np.sqrt(((eps[:, 0] - eps[:, 1]) / 2) ** 2 + (eps[:, 2] / 2) ** 2)
    peak = np.abs((eps[:, 0] + eps[:, 1]) / 2) + rad
    loaded = pts[np.r_[up, down]]
    far = np.min(np.hypot(cen[:, None, 0] - loaded[None, :, 0], cen[:, None, 1] - loaded[None, :, 1]), axis=1) > 0.6
    good = far & (area > 0.15 * h * h)
    w, acc = np.zeros(len(pts)), np.zeros(len(pts))
    for j in range(3):
        np.add.at(w, tri[good, j], area[good])
        np.add.at(acc, tri[good, j], (peak * area)[good])
    node = np.where(w > 0, acc / np.maximum(w, 1e-12), 0.0)
    k = int(np.argmax(node))
    return dict(part=float(part), strain=float(node[k]), at=(float(pts[k, 0]), float(pts[k, 1])), triangles=len(tri))


def clip_numbers():
    barb = (RI + RAMP_L, RI + RAMP_L + BARB_FLAT)
    snap = clip_fe(barb, ZF0 - BARB_H, ZR1)                           # snapping on: the barb rides the lug's land
    seat = (G_OUT, R_OUT + REACH - LEAD)                              # holding: the land under the front arm, the roof over the rear
    hold = clip_fe(seat, ZF0, ZR1)
    opens = dict(nominal=BARB_H - PLAY, tight=BARB_H - PLAY + SAG + SHRINK)   # mm the C must open to pass the barb
    ramp = math.atan2(BARB_H, RAMP_L)
    thumb = (math.tan(ramp) + MU) / (1 - MU * math.tan(ramp)) + MU    # push on the spine per N of opening force
    catch = math.radians(CATCH)
    out = dict(opens=opens, snap=snap, hold=hold, thumb=thumb,
               strain_per_mm=snap["strain"] / snap["part"],          # the same in any plastic
               mpa_per_n=hold["strain"],                              # stress = E x strain; E cancels
               hold_n=YIELD_MPA / hold["strain"])                     # N on one clip before its worst corner yields
    out["stiff"] = E_MPA["PLA"] / hold["part"]                        # N per mm, parting
    # the hand formula it replaced, kept as a cross-check: three beams on their centre lines
    i_f, i_r, i_s = CLIP_W * ARM_F ** 3 / 12, ARM_W * ARM_R ** 3 / 12, CLIP_W * SPINE_T ** 3 / 12
    a = RS0 + SPINE_T / 2 - (barb[0] + barb[1]) / 2
    hh = (ZF0 + ARM_F / 2) - (ZR1 - ARM_R / 2)
    out["beam_n_per_mm"] = E_MPA["PLA"] / (a ** 3 / (3 * i_f) + a ** 3 / (3 * i_r) + a * a * hh / i_s)
    for mat, e in E_MPA.items():
        k = e / snap["part"]                                          # N per mm of opening
        out[mat] = dict(k=k)
        for case, d in opens.items():
            out[mat][case] = dict(open_n=k * d, strain=out["strain_per_mm"] * d, push_n=k * d * thumb,
                                  off_n=k * d * math.tan(catch),      # no friction: the least it takes to drag one off
                                  off_mu_n=k * d * math.tan(catch + math.atan(MU)))
    return out


def loads():
    t = design.evaluate(design.transmission())["t_crank"]                 # N m on the ring at design.HAND_RPM
    t_yank = YANK_N * design.CRANK_ARM_MM / 1000
    thrust = lambda tq: tq / (R_PITCH / 1000) * TAN_B                     # N along the axle if ONE half carries all of it
    r_ear = (R_OUT + EAR_IN + R_OUT + REACH - EAR_STEP) / 2 / 1000
    # the planet's tooth root, Lewis as design.py has it, when ONE half of its face carries that planet's whole share
    root = lambda tq: tq / (R_PITCH / 1000) / P.N / ((HALF - gears.FOOT_H) * P.MODULE * design._lewis_y(P.P))
    return dict(t=t, part=thrust(t), clip=thrust(t) / P.N, t_yank=t_yank, part_yank=thrust(t_yank), clip_yank=thrust(t_yank) / P.N,
                ear_yank=t_yank / 2 / r_ear / P.N, root=root(t), root_yank=root(t_yank))


def sharing(stop):
    """How the two halves come to share the drive, each way round. Worked out from the helix, the backlash and the
    ear gaps: no solids. A half that takes drive is pushed along the axle by tan(helix) x its tooth load; the two
    halves are opposite hands, so they are pushed opposite ways. Until a lug meets an ear only the front half
    (the wheel's dogs are on it) carries anything.
    Returns the turning direction that closes the halves, and mm the ring travels along the axle before sharing."""
    r_c = R_OUT + REACH - EAR_STEP                                        # the ears' outer end meets the lug first
    at_pitch = R_PITCH / r_c
    closing = "counter-clockwise" if stop > 0 else "clockwise"            # seen from the front (Z toward you)
    back = EAR_CLR * at_pitch / (2 * TAN_B)                               # both halves together, toward the wall
    def forward(play):                                                    # front half leads by the clips' play, lug that much higher on the leaning ear
        gap = (EAR_CLR + GUARD_SLOPE * (FOOT + play)) * at_pitch
        return (gap / TAN_B + play) / 2
    upright = ((GUARD_GAP * at_pitch) / TAN_B + PLAY) / 2                 # the same with an upright ear GUARD_GAP away (round 0)
    return dict(closing=closing, opening="clockwise" if stop > 0 else "counter-clockwise", back=back,
                fwd_tight=forward(0.0), fwd_loose=forward(PLAY), fwd_upright=upright,
                wedge=P.PIP_BACKLASH / 2 / TAN_B)


def open_ring(gap_force, n=1441):
    """The old ring cut through in ONE place and its two ends pulled apart by gap_force newtons each (along the rim):
    a thin curved beam of the rim's section, M = P R (1 - cos t) at angle t from the cut, integrated exactly
    (no small-deflection formula). The side opposite the cut is taken as held.
    Returns t, the centre line (cut on +X), its outward normals, the gap between the ends, and the peak bending stress."""
    r = R_OUT - P.RING_RIM / 2
    inertia = P.RING_H * P.RING_RIM ** 3 / 12                             # rim and skirt wall; teeth and dogs do not carry hoop bending
    c = gap_force * r * r / (E_MPA["PLA"] * inertia)
    t = np.linspace(0.0, 2 * math.pi, n)
    phi = t + math.pi / 2 - c * ((t - math.pi) - np.sin(t))               # direction of the centre line
    step = lambda v: np.concatenate([[0.0], np.cumsum((v[1:] + v[:-1]) / 2 * np.diff(t))]) * r
    x, y = step(np.cos(phi)), step(np.sin(phi))
    mid = n // 2
    x, y = x - x[mid] - r, y - y[mid]                                      # the far side stays where it was
    nrm = np.c_[np.sin(phi), -np.cos(phi)]
    gap = float(np.hypot(x[-1] - x[0], y[-1] - y[0]))
    sigma = gap_force * 2 * r * (P.RING_RIM / 2) / inertia
    return dict(t=t, xy=np.c_[x, y], n=nrm, gap=gap, sigma=sigma, r=r)


def ring_comes_off(need=1.5):
    """Least pull that lets the cut ring lift clear of all three planets (they are herringbone: it must clear their
    teeth all round, it cannot be lifted off them). Tooth tips of the opened ring against the planets' tip circles,
    the ring slid sideways to wherever suits it best. Returns the open_ring() result plus force, clearance and slide."""
    r_tip_planet = P.MODULE * (P.P + 2) / 2
    turn = math.radians(CUT_AT)
    rot = np.array([[math.cos(turn), -math.sin(turn)], [math.sin(turn), math.cos(turn)]])
    pins = np.array(P.PINS)
    grid = [(dx, dy) for dx in np.arange(-24.0, 24.1, 3.0) for dy in np.arange(-24.0, 24.1, 3.0)]
    for force in np.arange(1.0, 20.5, 0.5):
        o = open_ring(force)
        tips = (o["xy"] - (o["r"] - P.R_RING_TIP) * o["n"]) @ rot.T
        clear = lambda d: min(float(np.hypot(tips[:, 0] + d[0] - px, tips[:, 1] + d[1] - py).min()) - r_tip_planet for px, py in pins)
        start = max(grid, key=clear)                                      # the least of three distances has corners: start near the top
        best = minimize(lambda d: -clear(d), start, method="Nelder-Mead", options=dict(xatol=0.05, fatol=0.01))
        if -best.fun >= need:
            return dict(o, force=float(force), clear=float(-best.fun), slide=(float(best.x[0]), float(best.x[1])), rot=rot)
    return None


def compare(num, ld, masses):
    """The joins that were weighed, with numbers. (a) is what this file builds."""
    need = ld["clip_yank"]
    rows = []
    rows.append(("(a) separate C-clips, on their side", f"{num['hold_n']:.0f} N each, x{num['hold_n'] / need:.1f}",
                 f"{100 * num['PLA']['nominal']['strain']:.1f} to {100 * num['PLA']['tight']['strain']:.1f} % PLA, along layers",
                 f"yes: one {CH_W} mm bridge", f"{2 * (R_OUT + REACH):.0f} mm, unchanged",
                 "a clip only clicks where a lug sits between its ears", "yes: a scissor blade in the gap behind it, twist"))
    # (b) a snap arm that is part of the rear half. It has to rise past the front lug, so either it stands up
    # (bends across its layers: ruled out) or it lies along the rim with a 45 degree hook, which is the most a hook
    # can overhang with no support. A 45 degree hook lets go at the arm's own bending force.
    L, t, bb, y = 22.0, 3.0, HALF - 1.0, 1.5
    p = E_MPA["PLA"] * bb * t ** 3 * y / (4 * L ** 3)
    rows.append(("(b) snap arms on the rear half, along the rim", f"{p:.0f} N each, x{p / need:.1f}",
                 f"{100 * 1.5 * t * y / L ** 2:.1f} % PLA, along layers", "only with a 45 degree hook", f"{2 * (R_OUT + t + y + 1.0):.0f} mm",
                 f"all {N_LUG} must snap at once: {N_LUG * 1.06 * p:.0f} N", "no: seven hooks to hold open"))
    # (c) a bow-tie key slid through both lugs. Strong in the key; the lug walls beside the slot bend across layers.
    neck, wide, wall_h = 4.0, 7.0, 3.0
    wall = (LUG_W - wide) / 2
    sig = 6 * (need / 2) * wall_h / (REACH * wall ** 2)
    rows.append(("(c) sliding dovetail key through the lugs", f"wall {sig:.0f} MPa at {need:.0f} N, ACROSS layers",
                 "none (a sliding fit)", "yes: 45 degree slot walls", f"{2 * (R_OUT + REACH):.0f} mm, unchanged",
                 "no click; 0.1 mm decides loose or stuck", "yes if it was not jammed in"))
    # (d) a band twisted on round the outside, tabs under and over the lugs
    od = 2 * (R_OUT + REACH + 0.3 + SPINE_T)
    rows.append(("(d) twist-on outer band", "tabs, strong", "none", "no: inward tabs need supports",
                 f"{od:.0f} mm, over the {batches.PLATE - 2 * batches.EDGE:.0f} usable", "a third 3 hour print", "yes"))
    head = ("join", "holds (per lug, x over a yank)", "strain snapping on", "prints with no supports", "across", "beginner", "comes off")
    return head, rows


# ============================================================ printing checks on the meshes themselves
def mesh_of(part, tol=0.01, ang=0.1):
    comp = cq.Compound.makeCompound(list(part.vals()))
    vs, ts = comp.tessellate(tol, ang)
    return trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(ts), process=True)


def overhang(mesh, where=None):
    """mm2 of surface that faces down flatter than 45 degrees and is not on the bed. where: an (N,3)->bool filter."""
    c = mesh.triangles_center
    down = (mesh.face_normals[:, 2] < -0.72) & (c[:, 2] > 0.05)
    if where is not None:
        down &= where(c)
    return float(mesh.area_faces[down].sum())


def bed_fit(mesh, turn):
    """Edge margin on the P1S plate and whether any of it is in the reserved corner, turned and centred as the slicer will."""
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(turn), [0, 0, 1]))
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    half = batches.PLATE / 2
    v = m.vertices
    margin = half - np.abs(v[:, :2]).max()
    corner = bool(((v[:, 0] < -half + batches.NO_GO[0]) & (v[:, 1] < -half + batches.NO_GO[1])).any())
    return float(margin), corner, m


def best_turn(mesh):
    return max(np.arange(0.0, 360.0 / N_LUG, 0.5), key=lambda t: bed_fit(mesh, t)[0])


def plate_of_clips(clip_mesh, key_mesh):
    """Nine clips and the key on one plate, batches.py's rules: GAP between boxes, EDGE to the plate, clear of the corner."""
    n = N_LUG + SPARE_CLIPS
    kx, ky = key_mesh.bounds[1][:2] - key_mesh.bounds[0][:2]
    cx, cy = clip_mesh.bounds[1][:2] - clip_mesh.bounds[0][:2]
    placed = []
    k = key_mesh.copy()
    k.apply_translation([-(key_mesh.bounds[0][0] + key_mesh.bounds[1][0]) / 2, -key_mesh.bounds[0][1], 0])
    placed.append(k)
    pitch = cx + batches.GAP
    for i in range(n):
        c = clip_mesh.copy()
        c.apply_translation([(i - (n - 1) / 2) * pitch - (clip_mesh.bounds[0][0] + clip_mesh.bounds[1][0]) / 2,
                             -batches.GAP - clip_mesh.bounds[1][1], 0])
        placed.append(c)
    return trimesh.util.concatenate(placed), dict(pitch=pitch, clip=(cx, cy), key=(kx, ky))


# ============================================================ printing checks
def print_checks(add, rear, front, bare_r, bare_f, k):
    """Orientation, overhangs, walls and the bed, judged on the meshes that are exported. Returns {name: (mesh, bodies)}."""
    exports = {}
    m_r, m_f = mesh_of(rear), mesh_of(front.translate((0, 0, -HALF)))
    m_br, m_bf = mesh_of(bare_r), mesh_of(bare_f.translate((0, 0, -HALF)))
    m_c, m_k = mesh_of(clip()), mesh_of(k)
    roofs = N_LUG * CH_W * REACH
    lugs_only = lambda c: np.hypot(c[:, 0], c[:, 1]) > R_OUT - 0.2
    o_r, o_f = overhang(m_r, lugs_only), overhang(m_f, lugs_only)
    add(f"rear half, back on the bed: the only surface with nothing under it is the {N_LUG} channel roofs, a {CH_W} mm bridge each "
        f"({o_r:.0f} mm2 found, {roofs:.0f} drawn; bridges up to {BRIDGE_MAX:.0f} mm are fine)", abs(o_r - roofs) < 0.1 * roofs and CH_W <= BRIDGE_MAX)
    add(f"front half, split face on the bed: its lugs have no overhang past 45 degrees ({o_f:.1f} mm2)", o_f < 1.0)
    add(f"the teeth are planetary's and overhang as they always did (rear {overhang(m_r) - o_r:.0f} against {overhang(m_br):.0f} mm2, "
        f"front {overhang(m_f) - o_f:.0f} against {overhang(m_bf):.0f}: the {gears.FOOT_RELIEF} mm relief step)",
        abs(overhang(m_r) - o_r - overhang(m_br)) < 5 and abs(overhang(m_f) - o_f - overhang(m_bf)) < 5)
    add(f"clip on its side and key pegs up: no overhang at all ({overhang(m_c):.2f} and {overhang(m_k):.2f} mm2); "
        f"the clip's layers run round the C", overhang(m_c) < 0.01 and overhang(m_k) < 0.01)
    thin = {"clip rear arm": ARM_R, "clip front arm": ARM_F, "clip spine": SPINE_T, "channel roof": HALF - CH_D, "channel side rails": (WR - CH_W) / 2,
            "ears": EAR_T, "land under the front arm": LAND, "lug left under the groove": HALF - G_D, "key plate": KEY_T,
            "step beside the rear arm": CLIP_W - ARM_W}
    worst = min(thin, key=thin.get)
    add(f"walls: thinnest is the {worst}, {thin[worst]:.1f} mm ({thin[worst] / NOZZLE:.1f} lines of a {NOZZLE} nozzle; at least 3)", thin[worst] >= 3 * NOZZLE)
    barb_l = RAMP_L + BARB_FLAT + BARB_H * COT
    add(f"details: the barb is {BARB_H} mm high on a {barb_l:.1f} mm base, drawn in the plane of the bed (at least 1.5 and 4 lines of a "
        f"{NOZZLE} nozzle); ears {EAR_H / LAYER:.0f} layers tall, channel {CH_D / LAYER:.0f}, groove {G_D / LAYER:.0f}",
        BARB_H >= 1.5 * NOZZLE and barb_l >= 4 * NOZZLE and all(abs(x / LAYER - round(x / LAYER)) < 1e-6 for x in (EAR_H, CH_D, G_D)))
    add(f"fits: rear arm {(CH_W - ARM_W) / 2:.2f} mm a side in its channel, a {ARM_R} mm arm in a {CH_D} mm slot; the C's mouth is "
        f"{ZF0 - ZR1:.2f} mm over a {P.FACE_W - CH_D:.2f} mm stack ({PLAY} mm of play); front lug {EAR_CLR} mm off the stop ear, and off the "
        f"leaning ear {EAR_CLR} at its foot, {GUARD_GAP} at its top; {FOOT} mm chamfer on the lug's bed edges",
        (CH_W - ARM_W) / 2 >= 0.2 and CH_D - ARM_R >= 0.4 and EAR_CLR >= 0.2 and abs(ZF0 - ZR1 - (P.FACE_W - CH_D) - PLAY) < 1e-9)
    add(f"the leaning ear leans {GUARD_SLOPE:.3f} mm per mm, the lug swings in at {tan_g(R_OUT + REACH):.3f} at its tip and less further in: "
        f"it never closes on the lug; it leans back, so it has no overhang", GUARD_SLOPE >= tan_g(R_OUT + REACH))
    for name, mesh in (("2_ring_rear_half_clip", m_r), ("3_ring_front_half_clip", m_f)):
        turn = best_turn(mesh)
        margin, corner, placed = bed_fit(mesh, turn)
        ext = placed.bounds[1] - placed.bounds[0]
        add(f"{name}: turned {turn:.1f} degrees it is {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm, {margin:.1f} mm inside the "
            f"{batches.PLATE:.0f} mm plate (need {batches.EDGE}), clear of the reserved corner", margin >= batches.EDGE and not corner)
        exports[name] = (placed, 1)
    plate, lay = plate_of_clips(m_c, m_k)
    margin, corner, placed = bed_fit(plate, 0.0)
    ext = placed.bounds[1] - placed.bounds[0]
    add(f"4_ring_clips: {N_LUG} clips + {SPARE_CLIPS} spare + the key, {batches.GAP:.0f} mm apart, {ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.1f} mm, "
        f"{margin:.0f} mm inside the plate, clear of the corner", margin >= batches.EDGE and not corner)
    exports["4_ring_clips"] = (placed, N_LUG + SPARE_CLIPS + 1)
    bodies = [mesh_of(p) for p in coupon(rear, front)]
    apart = min(max(a.bounds[0][0] - b.bounds[1][0], b.bounds[0][0] - a.bounds[1][0], a.bounds[0][1] - b.bounds[1][1],
                    b.bounds[0][1] - a.bounds[1][1]) for i, a in enumerate(bodies) for b in bodies[:i])
    cp = trimesh.util.concatenate(bodies)
    margin, corner, placed = bed_fit(cp, 0.0)
    ext = placed.bounds[1] - placed.bounds[0]
    add(f"1_ring_clip_coupon: one lug pair with {COUPON_TEETH} teeth of each half, cut from the real halves, and one clip: "
        f"{ext[0]:.0f} x {ext[1]:.0f} x {ext[2]:.1f} mm, {placed.volume / 1000:.1f} cm3 ({placed.volume * DENSITY * 1000:.0f} g solid), "
        f"bodies {apart:.1f} mm apart (batches.GAP {batches.GAP:.0f})",
        margin >= batches.EDGE and not corner and placed.volume < 12000 and apart >= batches.GAP - 1e-6)
    exports["1_ring_clip_coupon"] = (placed, 3)
    def single(mesh, bodies):
        """What the slicer will read: an STL keeps 7 digits, and a sliver edge shorter than that opens the skin."""
        m = trimesh.Trimesh(mesh.vertices.astype(np.float32).astype(float), mesh.faces, process=True)
        m.merge_vertices()
        return m.is_watertight and len(m.split(only_watertight=False)) == bodies

    bad = [n for n, (m, b) in exports.items() if not single(m, b)]
    short = min(float(m.edges_unique_length.min()) for m, _ in exports.values())
    add(f"all {len(exports)} meshes stay closed, with the right number of bodies, when cut to an STL's single precision"
        + (f" (NOT: {', '.join(bad)})" if bad else "") + f"; shortest edge anywhere {short:.3f} mm (no slivers)", not bad and short >= 1e-3)
    return exports


# ============================================================ checks
def check():
    res = []
    add = lambda text, ok: res.append((text, bool(ok)))
    note = lambda text: res.append((text, None))              # said, not judged: nothing here can fail it
    num, ld = clip_numbers(), loads()

    # ---- the gears he has, and the ring they were printed inside
    gs = P.gearset()
    planets = [gs[k] for k in gs if k.startswith("planet")]
    stl = trimesh.load(os.path.join(P.OUT, "gearset_print_in_place.stl"), force="mesh")
    stl_ring = max(stl.split(only_watertight=False), key=lambda m: m.volume)
    v_ring = gs["ring"].val().Volume()
    add(f"the ring in gearset_print_in_place.stl is planetary.ring_gear() ({stl_ring.volume / 1000:.2f} against {v_ring / 1000:.2f} cm3), "
        f"PIP_BACKLASH {P.PIP_BACKLASH}", abs(stl_ring.volume - v_ring) < 2e-3 * v_ring)

    # ---- teeth, skirt, dogs: planetary's own, untouched
    bare_r, bare_f = bare_halves()
    p_rear = P.ring_halves()[0].intersect(P._cyl(0, 0, R_OUT, -1, TOP + 1))
    bores = 0.0
    for a in P.DOG_ANGLES:
        t = math.radians(a + 180.0 / P.DOGS)
        hx, hy = (R_OUT + REACH / 2) * math.cos(t), (R_OUT + REACH / 2) * math.sin(t)
        bores += P._vol(P._cyl(hx, hy, P.M3_HEAD_D / 2, 0, P.M3_HEAD_H), P._cyl(0, 0, R_OUT, 0, HALF))
    d_in = sum(x.Volume() for x in bare_r.cut(p_rear).solids().vals())
    d_out = sum(x.Volume() for x in p_rear.cut(bare_r).solids().vals())
    add(f"rear half: planetary's own, lugs off, is this one less its six screw counterbores ({d_in:.2f} mm3 missing, {bores:.2f} expected; "
        f"{d_out:.3f} added); both halves are one solid",
        abs(d_in - bores) < 0.05 and d_out < 0.01 and bare_r.solids().size() == 1 and bare_f.solids().size() == 1)
    both = bare_r.union(bare_f)
    relief = (gears.ring_half(P.R, P.MODULE, HALF, R_OUT, hand=P.SUN_HAND, backlash=P.PIP_BACKLASH, relief=0).val().Volume()
              - gears.ring_half(P.R, P.MODULE, HALF, R_OUT, hand=P.SUN_HAND, backlash=P.PIP_BACKLASH).val().Volume())
    miss = sum(s.Volume() for s in gs["ring"].cut(both).solids().vals())
    extra = sum(s.Volume() for s in both.cut(gs["ring"]).solids().vals())
    add(f"teeth, skirt and dogs are the printed ring's: the two halves add {extra:.3f} mm3 to it and leave out {miss:.1f} mm3, "
        f"the front half's own first-layer relief ({relief:.1f} mm3)", extra < 0.5 and abs(miss - relief) < 0.02 * relief + 0.5)

    # ---- which way the halves screw: found on the solids, not assumed
    def clear(part, others):
        return max(P._vol(part, o) for o in others)

    f_sense, r_sense = screw_senses(planets, (bare_r, bare_f))
    add(f"each half screws onto the planets one way only (front {f_sense}, rear {r_sense}); the other way it hits them",
        len(f_sense) == 1 and len(r_sense) == 1)
    if len(f_sense) != 1 or len(r_sense) != 1:
        return res, None
    fs, rs = f_sense[0], r_sense[0]
    stop = -fs                                                # coming down, the front lug swings toward this side
    rear, front = halves(stop)
    clips = [clip(a) for a in LUG_ANGLES]
    clips_all = _join(clips)
    arc = 2 * math.pi * (R_OUT + REACH / 2) / 360.0                       # mm at the lugs per degree
    off = lambda n, k: abs((k * 360.0 / P.R + 180.0 / n) % (360.0 / n) - 180.0 / n) * arc      # mm the lugs are out, k teeth round
    miss = lambda n: min((off(n, k), k) for k in range(1, P.R) if off(n, k) > 1e-6)
    add(f"{N_LUG} lugs: {P.R} teeth / {N_LUG} = {P.R // N_LUG}, so the lugs line up at every {P.R // N_LUG}th tooth and are a whole tooth "
        f"({miss(N_LUG)[0]:.1f} mm) out at any other. planetary's {P.LUGS} would line up at one tooth in {P.R} and sit only "
        f"{miss(P.LUGS)[0]:.1f} mm out at tooth {miss(P.LUGS)[1]}", P.R % N_LUG == 0 and miss(N_LUG)[0] > LUG_W / 2)
    for name, part in (("rear half", rear), ("front half", front), ("one clip", clips[0])):
        add(f"{name} is one solid", part.solids().size() == 1)

    # ---- the halves on the planets and on each other
    add(f"rear half meshes the three planets without touching ({clear(rear, planets):.4f} mm3)", clear(rear, planets) < 1e-3)
    add(f"front half meshes the three planets without touching ({clear(front, planets):.4f} mm3)", clear(front, planets) < 1e-3)
    v = clear(rear.rotate((0, 0, 0), (0, 0, 1), 180.0 / P.R), planets)
    add(f"and half a tooth out the rear half would hit them ({v:.0f} mm3)", v > 10)
    v = P._vol(rear, front)
    touch = P._vol(rear, front.translate((0, 0, -0.02))) / 0.02
    ann = math.pi * (R_OUT ** 2 - P.R_RING_ROOT ** 2)
    add(f"teeth in phase, the halves meet flat: {v:.4f} mm3 of overlap, and 0.02 mm closer they touch over {touch:.0f} mm2 "
        f"(the rim alone is {ann:.0f})", v < 1e-3 and touch > 0.9 * ann)
    steps = [0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, EAR_H, 2.0, 2.4, 4.0, HALF]
    v = max(P._vol(screw(front, d, fs), rear) for d in steps)
    add(f"the front half screws down past the ears, the leaning one too ({len(steps)} heights from {HALF:.0f} mm to 0.1, worst {v:.4f} mm3)", v < 1e-3)
    v = max(clear(screw(front, d, fs), planets) for d in (1.5, HALF)) + max(clear(screw(rear, -d, rs), planets) for d in (1.5, HALF))
    add(f"both halves screw onto the planets with no collision on the way ({v:.4f} mm3)", v < 1e-3)
    tooth = 360.0 / P.R
    v1, v2 = (P._vol(front.rotate((0, 0, 0), (0, 0, 1), s * tooth), rear) for s in (1, -1))
    add(f"one tooth out either way the front lugs land on an ear ({v1:.0f} and {v2:.0f} mm3): it cannot sit flat there", v1 > 5 and v2 > 5)
    # further out the lugs miss the rear lugs altogether. Lugs alone are enough to show it: nothing else of the two
    # halves can meet (the rest of each is a body of revolution outside its teeth, and the teeth are at different heights)
    lugs_r, lugs_f = _join([rear_lug(a, stop) for a in LUG_ANGLES]), _join([front_lug(a) for a in LUG_ANGLES])
    per = P.R // N_LUG
    out = {k: P._vol(lugs_f.rotate((0, 0, 0), (0, 0, 1), k * tooth), lugs_r) for k in range(-(per // 2), per // 2 + 1) if abs(k) > 1}
    miss = [abs(k) * tooth * arc - (LUG_W + WR) / 2 for k in out]
    add(f"BUT 2 to {per // 2} teeth out either way it DOES drop flat ({max(out.values()):.4f} mm3 in all {len(out)} places), every lug "
        f"{min(miss):.0f} to {max(miss):.0f} mm clear of the nearest ears: {len(out)} wrong places in {per}, against 1 right. So the picture says "
        f"lugs over ears FIRST, and nothing here claims the teeth alone find the place", max(out.values()) < 1e-3 and min(miss) > 0)
    v = P._vol(clips_all, rear.union(front))
    add(f"{N_LUG} clips sit on the lug pairs without overlap ({v:.4f} mm3)", v < 1e-3)
    pulled = P._vol(clips[0].translate(((CATCH_PLAY + 0.3) * math.cos(math.radians(LUG_ANGLES[0])),
                                        (CATCH_PLAY + 0.3) * math.sin(math.radians(LUG_ANGLES[0])), 0)), front)
    add(f"pull a clip straight out {CATCH_PLAY + 0.3:.1f} mm and its barb is into the groove wall ({pulled:.2f} mm3): it is caught", pulled > 0.05)
    # back to front: on the solids, at every height it could be offered up at (it may hang lower: the lug can be over a table edge)
    wrong = clip(LUG_ANGLES[0], back_to_front=True)
    drops = [0.0, 0.35, 0.7, 1.0, 1.5, 2.5]
    v = min(P._vol(wrong.translate((0, 0, -d)), rear) for d in drops)
    add(f"a clip cannot go on back to front: its thick arm is {CLIP_W:.0f} mm wide and the channel {CH_W}, so it is into the rear half by at "
        f"least {v:.1f} mm3 at every one of {len(drops)} heights from in place to {drops[-1]} mm low", v > 1.0)
    # on a board: the clip lies on the board the ring lies on, and is pushed in along it
    flat = [REACH + 4.0, REACH + 1.0, REACH - TIP_GAP + 0.05, REACH - TIP_GAP - 0.2]      # the last: arm tips 0.2 mm in past the lug's tip
    slid = lambda e: clips[0].translate((e * math.cos(math.radians(LUG_ANGLES[0])), e * math.sin(math.radians(LUG_ANGLES[0])), -ZR0))
    v = max(P._vol(slid(e), rear.union(front)) for e in flat)
    over = ZF0 - ZR0 - (P.FACE_W - LEAD)
    add(f"ring flat on a big book or board: a clip pushed in along the board ({ZR0:.2f} mm low) gets its thin arm into the slot and its "
        f"thick arm onto the lug's lead-in chamfer, {over:.2f} mm above the chamfer's foot, catching on nothing ({v:.4f} mm3 at "
        f"{len(flat)} places); then it rides up", v < 1e-3 and over >= 0.2)
    loose = ZF0 - ZR1 - HALF
    add(f"a clip only stays where a lug sits between its ears: on a front lug with no rear lug under it the C is {loose:.1f} mm too wide "
        f"(barb {BARB_H}); and halves a tooth out stand {EAR_H} mm apart, {EAR_H - PLAY:.1f} more than the C opens to", loose > 2 * BARB_H and EAR_H - PLAY >= 1.0)

    # ---- the machine: nothing new may touch anything old
    fr, sp, wh = P.frame(), P.spider(), P.wheel()
    spider_p, wheel_p = P.place(sp, P.SPIDER_Z0), P.place(wh, P.WHEEL_Z0)
    fixed = fr.union(P.motor_dummy()).union(spider_p).union(P.pins_dummy())
    table = cq.Workplane("XY").box(600, 60, 400, centered=(True, False, True)).translate((0, -60, 0))
    back = P.PIP_BACKLASH / 2 / TAN_B                         # how far the teeth let the ring drift along the axle
    r_max = max(math.hypot(RS1, CLIP_W - ARM_W / 2), math.hypot(R_OUT + REACH, WR / 2))
    sweep = (cq.Workplane("XZ").polyline([(R_OUT - 0.5, -back), (r_max, -back), (r_max, ZF1 + P.RING_FLOAT), (R_OUT - 0.5, ZF1 + P.RING_FLOAT)])
             .close().revolve(360, (0, 0, 0), (0, 1, 0)).translate((0, P.AXLE_Y, P.GEAR_GAP)))
    v = P._vol(sweep, fixed) + P._vol(sweep, table) + P._vol(sweep, wheel_p)
    add(f"lugs, ears and clips swept through a FULL turn, with the ring {back:.2f} mm back and {P.RING_FLOAT} mm forward: "
        f"{v:.4f} mm3 against frame, motor, pin spacers, spider, wheel and table", v < 1e-3)
    ring3 = [rear, front, clips_all]
    v = max(sum(P._vol(P.place(p, P.GEAR_GAP, a), fixed) for p in ring3) + P._vol(P.place(wh, P.WHEEL_Z0, a), fixed) for a in range(0, 360, 30))
    add(f"both halves, clips and the wheel turning together clear everything fixed at 12 positions (worst {v:.4f} mm3)", v < 1e-3)
    v = max(sum(P._vol(wheel_p, P.place(p, P.GEAR_GAP, 360.0 * k / P.DOGS)) for p in ring3) for k in range(P.DOGS))
    add(f"the six dogs sit in the wheel's notches at all {P.DOGS} ways round, lugs and clips clear the rim ({v:.4f} mm3)", v < 1e-3)
    v = P._vol(wheel_p, P.place(front, P.GEAR_GAP, 360.0 / P.DOGS / 2))
    add(f"and the dogs still drive: half a dog round, the front half hits the wheel ({v:.0f} mm3)", v > 100)
    add(f"clips are {ZF1 + P.GEAR_GAP:.1f} mm from the wall at their front, the wheel's back is at {P.WHEEL_Z0:.1f}: "
        f"{P.WHEEL_Z0 - P.GEAR_GAP - ZF1 - P.RING_FLOAT:.1f} mm apart with the ring fully forward", P.WHEEL_Z0 - P.GEAR_GAP - ZF1 - P.RING_FLOAT >= 5)
    add(f"nothing stands proud toward the wall: the clip's rear arm is {ZR0:.2f} mm inside the ring's back face, "
        f"which is {P.GEAR_GAP - back:.1f} mm off the wall at worst", ZR0 >= 0.3 and P.GEAR_GAP - back >= 1.5)
    add(f"clips pass {P.AXLE_Y - r_max:.1f} mm above the table (the bare ring: {P.AXLE_Y - R_OUT:.1f})", P.AXLE_Y - r_max >= 5)

    # ---- loads on the join, and what a clip holds
    sh = sharing(stop)
    add(f"drive: {ld['t']:.2f} N m at the hand ({design.HAND_RPM:.0f} rpm) is {ld['t'] / (R_PITCH / 1000):.1f} N at the {R_PITCH:.1f} mm pitch circle. "
        f"A half that carries it is pushed along the axle by tan({math.degrees(gears.HELIX):.0f}) of that: {ld['part']:.1f} N if one half "
        f"carries it all; {ld['part_yank']:.0f} N in a {YANK_N:.0f} N yank on the grip ({ld['t_yank']:.0f} N m)", True)
    add(f"cranked {sh['closing']} (seen from the front) the front half is pushed BACK onto the rear half: split face in compression, "
        f"clips carry nothing. The pair moves {sh['back']:.2f} mm toward the wall, the lugs meet the stop ears, both halves drive "
        f"(teeth would bind at {sh['wedge']:.2f} mm, the wall is {P.GEAR_GAP:.1f} away)", sh["back"] < sh["wedge"] and sh["back"] < P.GEAR_GAP - 1.5)
    ear_area = (WR / 2 - EAR_STEP - LUG_W / 2 - EAR_CLR) * (REACH - EAR_IN - EAR_STEP)
    add(f"the stop ears then carry half the drive: {ld['ear_yank']:.0f} N on one ear in a yank (taking one planet's share on one ear) over "
        f"{ear_area:.0f} mm2 = {ld['ear_yank'] / ear_area:.1f} MPa between layers (allow {design.PLA_ALLOW_MPA})",
        ld["ear_yank"] / ear_area <= design.PLA_ALLOW_MPA)
    add(f"cranked {sh['opening']} the front half is pushed FORWARD. The leaning ear is met after {sh['fwd_tight']:.2f} mm (clips with no "
        f"play) to {sh['fwd_loose']:.2f} mm (the full {PLAY}); the wheel stops the ring at {P.RING_FLOAT}. So the halves share, except "
        f"with clips at their very loosest, {sh['fwd_loose'] - P.RING_FLOAT:.2f} mm short. An upright ear {GUARD_GAP} mm off, as first "
        f"drawn, needed {sh['fwd_upright']:.2f} mm: never", sh["fwd_tight"] < P.RING_FLOAT and sh["fwd_loose"] < P.RING_FLOAT + 0.1)
    add(f"sharing that way, the rear half's thrust parts the halves and the clips carry it: at most {ld['part'] / 2:.1f} N in all "
        f"({ld['part_yank'] / 2:.0f} N in a yank). Checked at TWICE that, as if the clips took one half's whole thrust: worst clip "
        f"{ld['clip']:.1f} N of the {num['hold_n']:.0f} N it holds: x{num['hold_n'] / ld['clip']:.0f}", num["hold_n"] >= 10 * ld["clip"])
    add(f"yank, same doubled load: {ld['part_yank']:.0f} N parting, a whole planet's share on ONE clip is {ld['clip_yank']:.0f} N: "
        f"x{num['hold_n'] / ld['clip_yank']:.1f} to first yield ({YIELD_MPA:.0f} MPa at {num['mpa_per_n']:.2f} MPa per N, at the "
        f"inside corner r {num['hold']['at'][0]:.1f} z {num['hold']['at'][1]:.1f}); all {N_LUG} clips hold {N_LUG * num['hold_n']:.0f} N: "
        f"x{N_LUG * num['hold_n'] / ld['part_yank']:.1f}", num["hold_n"] >= 1.5 * ld["clip_yank"] and N_LUG * num["hold_n"] >= 3 * ld["part_yank"])
    add(f"not sharing (loosest clips, or a wheel with more float): the front half drives alone and its thrust goes into the wheel's back, "
        f"{ld['part']:.1f} N ({ld['part_yank']:.0f} in a yank), where the old ring's skirt already bore. The planets' teeth then carry it on "
        f"{HALF - gears.FOOT_H:.1f} mm of face: {ld['root']:.2f} MPa at the root, {ld['root_yank']:.1f} in a yank (allow {design.PLA_ALLOW_MPA})",
        ld["root_yank"] <= design.PLA_ALLOW_MPA)
    m_front = front.val().Volume() * DENSITY
    m_gears = (3 * planets[0].val().Volume() + gs["sun"].val().Volume()) * DENSITY + 3 * 0.012
    hang = (m_front + m_gears) * 9.81 * SHAKE_G
    add(f"handling: lifted by the rear half and jerked at {SHAKE_G:.0f} g, the front half and gears ({1000 * (m_front + m_gears):.0f} g, taken solid) "
        f"pull {hang:.0f} N; two clips nearest the hand hold {2 * num['hold_n']:.0f} N", 2 * num["hold_n"] >= 2 * hang)
    e_clips = N_LUG * num["hold_n"] ** 2 / (2 * num["stiff"])
    h_drop = e_clips / ((m_front + m_gears) * 9.81)
    note(f"dropped on the bench: flat, the halves are pushed together and the clips carry nothing. Edge-first is NOT covered: the clips "
         f"are now the outermost thing ({RS1:.1f} mm against the lugs' {math.hypot(R_OUT + REACH, WR / 2):.1f}) and all {N_LUG} soak up only "
         f"{e_clips:.0f} N mm before one yields, a {h_drop:.0f} mm fall of the front half and gears. A clip hit on its spine breaks. "
         f"RING.md: build over a towel, push every clip again after a knock, keep the two spares")
    snap = num["snap"]
    add(f"clip model: {snap['triangles']} triangles, plane stress, rear arm {ARM_W:.0f} mm thick and the rest {CLIP_W:.0f}: "
        f"{num['PLA']['k']:.1f} N per mm of opening in PLA ({num['beam_n_per_mm']:.1f} by three beams on their centre lines, which is "
        f"softer than the real corners), peak strain {100 * num['strain_per_mm']:.2f} % per mm at the inside corner "
        f"r {snap['at'][0]:.1f} z {snap['at'][1]:.1f}", 0.6 < num["beam_n_per_mm"] / num["PLA"]["k"] < 1.2)
    o = num["opens"]
    add(f"the C opens {o['nominal']:.1f} mm to pass its {BARB_H} mm barb as drawn ({PLAY} play), {o['tight']:.2f} mm if the bridged roof "
        f"sags {SAG} and the mouth prints {SHRINK} small (both ASSUMED: the coupon is the measurement)", o["nominal"] >= 0.3)
    for mat in E_MPA:
        n, t = num[mat]["nominal"], num[mat]["tight"]
        add(f"{mat} clip, as drawn / printed tight: {n['open_n']:.0f} / {t['open_n']:.0f} N to open, strain {100 * n['strain']:.2f} / "
            f"{100 * t['strain']:.2f} % along the layers (limit {100 * STRAIN_MAX[mat]:.0f} %), thumb {n['push_n']:.0f} / {t['push_n']:.0f} N "
            f"(x{num['thumb']:.2f} up the ramp; limit {THUMB_MAX:.0f}), {n['off_n']:.0f} to {t['off_mu_n']:.0f} N to drag off over a "
            f"{CATCH:.0f} degree catch; it weighs a gram and nothing in use pulls it outward, 10 N is plenty",
            t["strain"] <= STRAIN_MAX[mat] and t["push_n"] <= THUMB_MAX and n["off_n"] >= 10)

    # ---- the test plate, and getting the old ring off
    c_r, c_f = coupon_parts(rear, front)
    near = min(planets, key=lambda pl: abs((math.degrees(math.atan2(pl.val().Center().y, pl.val().Center().x)) - LUG_ANGLES[COUPON_LUG] + 180) % 360 - 180))
    cx, cy = near.val().Center().x, near.val().Center().y
    inward = lambda d: near.translate((-d * cx / math.hypot(cx, cy), -d * cy / math.hypot(cx, cy), 0))
    depths = [0.0, 1.5, 3.0, 4.5, 6.0]
    v = max(P._vol(c_r, inward(d)) + P._vol(c_f, inward(d)) for d in depths)
    add(f"test piece: clipped together it is {COUPON_TEETH} teeth of the real ring, and a real planet pushes straight into them from the "
        f"side ({v:.4f} mm3 at {len(depths)} depths from out of mesh to fully in): his own planet tries the tooth fit before the long prints",
        v < 1e-3)
    off = ring_comes_off()
    r_dog = min(abs((CUT_AT - a + 180) % 360 - 180) for a in P.DOG_ANGLES) - math.degrees(P.DOG_W / 2 / R_OUT)
    r_pl = min(abs((CUT_AT - a + 180) % 360 - 180) for a in P.PIN_ANGLES)
    add(f"old ring: ONE cut at {CUT_AT:.0f} degrees, {r_dog:.0f} degrees clear of a dog and {r_pl:.0f} from the nearest planet, through "
        f"{P.RING_H:.1f} mm of wall (through a dog it would be {TOP:.1f}). Ends pulled {off['gap']:.0f} mm apart ({off['force']:.1f} N each, "
        f"{off['sigma']:.0f} MPa in the rim) it clears all three planets' teeth by {off['clear']:.1f} mm, slid {math.hypot(*off['slide']):.0f} mm "
        f"sideways, and lifts off. The picture says 5 cm", off is not None and off["gap"] <= 50 and off["sigma"] < YIELD_MPA / 2 and r_dog > 5)

    # ---- the key
    k = key()
    k_on = k.translate((0, 0, -KEY_T))                         # in the halves' frame: plate against the gears' backs, pegs into the planets
    v = clear(k_on, planets + [gs["sun"]])
    rk = max(math.hypot(x, y) for x, y in P.PINS) + PEG_R + 4.0
    add(f"key: three {2 * PEG_R:.1f} mm pegs drop {PEG_H:.0f} mm into the {2 * P.LAND_R:.0f} mm bores in the planets' backs, lying on the gears "
        f"({v:.4f} mm3), and a ring half passes round it ({rk:.0f} against {P.R_RING_TIP:.1f} mm)",
        v < 1e-3 and rk < P.R_RING_TIP - 5 and PEG_H < P.PLANET_BRG_Z)
    step = 360.0 / (P.R + P.S)
    slack = math.degrees((P.LAND_R - PEG_R) / P.A_C)
    add(f"key: planets also mesh every {step:.2f} degrees round the sun; the pegs hold each within {slack:.2f}, so only 120 apart is possible",
        slack < step / 3)

    exports = print_checks(add, rear, front, bare_r, bare_f, k)
    solids = dict(rear=rear, front=front, clips=clips, key=k, gs=gs, fs=fs, rs=rs, stop=stop, num=num, ld=ld,
                  masses=dict(front=m_front, gears=m_gears))
    return res, dict(exports=exports, solids=solids)


def gate(path, bodies):
    run = subprocess.run([sys.executable, GATE, path, "--bodies", str(bodies)], capture_output=True, text=True)
    return run.returncode == 0, run.stdout.strip().replace(os.path.dirname(path) + os.sep, "")


if __name__ == "__main__":
    res, built = check()
    for text, ok in res:
        print(f"[{'note' if ok is None else 'ok' if ok else 'NO'}] {text}")
    bad = [t for t, ok in res if ok is False]
    if bad or built is None:
        sys.exit(f"{len(bad)} checks failed: nothing exported")
    head, rows = compare(built["solids"]["num"], built["solids"]["ld"], built["solids"]["masses"])
    print("\nthe joins that were weighed:")
    for row in [head] + rows:
        print("  " + " | ".join(row))
    if "--check" in sys.argv:
        sys.exit(0)
    os.makedirs(OUT, exist_ok=True)
    failed = 0
    for name, (mesh, bodies) in sorted(built["exports"].items()):
        path = os.path.join(OUT, name + ".stl")
        mesh.export(path)
        ok, line = gate(path, bodies)
        failed += not ok
        print(f"[{'ok' if ok else 'NO'}] mesh gate: {line}")
        if not ok:
            os.remove(path)
    if failed:
        sys.exit(f"{failed} files failed the mesh gate and were removed")
    print(f"exported to {OUT}, in print order and print orientation")
