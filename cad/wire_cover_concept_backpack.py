"""Wire cover, concept "backpack": ONE shell over everything behind the wall.

MASSING MODEL ONLY. Real geometry from cad/planetary.py is imported (never changed);
this file adds one printed shell, three small printed keepers, and dummies of the
electronics so the fit can be checked and drawn.

Model frame (same as planetary.py): X right, Y UP, Z toward the wheel. The wall's back
face is Z = -8, the base top is Y = 8, the base's back edge is Z = -93.

How it sits:
  * the shell is a box with NO bottom and NO front: it slides in from behind over the
    motor and the two tall gussets, until its side walls touch the back of the wall
  * two feet on its sides drop into the outer bays of the base (between the shell and
    the outer gussets); a short peg under each side wall drops into a base hole
  * the two G-clamps he already uses now press ON THE FEET: they hold the machine to
    the table and the cover to the machine in one go. No screws into plastic.
  * card, capacitor and module live on the inside of the shell's back panel. The motor
    leads go motor -> card and never leave. The only opening is one USB-A window in
    the right-hand side wall (seen from the front), high up at the back.
  * air: in through the wall's two existing windows, out through a slot along the top
    where the lid stops 5 mm short of the wall. No holes in any face you can film.

    .venv/bin/python cad/wire_cover_concept_backpack.py      check, export, list
"""
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import planetary as pl

OUT = os.path.join(HERE, "stl", "cover")

# ============================================================ numbers (mm)
T = 2.0                    # shell wall
WALL_BACK = -pl.WALL_T                         # -8
BASE_TOP = pl.BASE_T                           # 8
BASE_BACK = -pl.WALL_T - pl.BASE_DEPTH         # -93

HW = 72.4                  # outer half width. Inside 70.4: clears the top pin bosses (66.1) by 4
Y_TOP = 195.0              # outer top. The wall goes on up to 224.8; the wheel hides the corners
Z_BACK = BASE_BACK         # back panel flush with the base's back edge (= the table edge)
Z_FRONT = WALL_BACK - 0.4  # side walls stop 0.4 mm short of the wall
TOP_GAP = 5.0              # lid stops this far short of the wall: the hidden warm-air slot
CORNER_R = 10.0

IN_Z = Z_BACK + T          # inside face of the back panel, -91

# feet under the G-clamps, one in each outer bay
FOOT_X1 = 99.5             # outer gusset's inner face is 100
FOOT_T = 4.0
FOOT_Z1 = -58.0
PEG_AF, PEG_LEN = 4.4, 5.0          # octagon in the 5.5 mm base holes at x = +-72

# the card: stiff card "about 13 x 10 cm", template outline 111 x 90. Pocket takes both.
CARD_MAX_W, CARD_MAX_H, CARD_MAX_T = 138.0, 110.0, 4.0
CARD_Y0 = 32.0             # card's bottom edge
RIB_H = 3.0                # air behind the card
RIB_Z = IN_Z + RIB_H       # -88: the card's back
RIB_XS = (-50.0, -17.0, 17.0, 50.0)
LEDGE_T = 3.0
LEDGE_SEGS = ((-36.0, 36.0), (52.0, 64.0), (-64.0, -52.0))   # gaps at x = +-45: the tall gussets
LIP = 5.5
TOGGLE_POSTS = ((-40.0, 149.0), (40.0, 149.0))
POST_R = 6.0
CARD_POST_TOP = RIB_Z + 3.5
M4_HOLE = 4.4
NUT_AF, NUT_T = 7.2, 3.4   # slot for an M4 nut, pushed in from the side

# the module: SIZE UNKNOWN (Amazon B0DF4KSN95 has not arrived). Only the USB-A socket is a
# standard: 13.2 to 14.5 wide, 5.7 to 7.1 high. The bridge clamps the socket, nothing else.
MOD_Y = 171.0              # centre of the socket
MOD_PAD = 1.0              # the module rests 1 mm off the panel
BRIDGE_POSTS = ((58.0, 149.0), (58.0, 189.0))    # 28 mm clear between them
MOD_POST_TOP = IN_Z + 8.0
USB_W, USB_H = 15.0, 9.5   # window in the side wall: along Y, along Z
USB_Z0 = IN_Z + 0.7

# placeholders, for the picture and the clearance checks only
MOD_PCB = (45.0, 26.0, 1.6)
USB_SOCKET = (14.0, 13.2, 7.0)
TESTER = (62.0, 24.0, 12.0)


def _box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _cyl_z(x, y, r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def _profile(hw, y_top, r):
    """Closed XY outline: straight sides down to the base, two rounded top corners."""
    return (cq.Workplane("XY").moveTo(-hw, BASE_TOP).lineTo(-hw, y_top - r)
            .radiusArc((-hw + r, y_top), r).lineTo(hw - r, y_top)
            .radiusArc((hw, y_top - r), r).lineTo(hw, BASE_TOP).close())


def _post(x, y, z_top):
    """A post rising from the back panel with an M4 hole and a side slot for a nut."""
    p = _cyl_z(x, y, POST_R, IN_Z - 0.5, z_top)
    p = p.cut(_cyl_z(x, y, M4_HOLE / 2, IN_Z + 0.2, z_top + 1))
    side = 1 if x < 0 else -1                       # slots open toward the middle of the box
    slot = _box(x - NUT_AF / 2, x + NUT_AF / 2, y - NUT_AF / 2, y + NUT_AF / 2, IN_Z + 1.0, IN_Z + 1.0 + NUT_T)
    slot = slot.union(_box(min(x, x + side * (POST_R + 1)), max(x, x + side * (POST_R + 1)),
                           y - NUT_AF / 2, y + NUT_AF / 2, IN_Z + 1.0, IN_Z + 1.0 + NUT_T))
    return p.cut(slot)


def shell():
    """The one big print. Prints back panel down, no support."""
    outer = _profile(HW, Y_TOP, CORNER_R).extrude(Z_FRONT - Z_BACK).translate((0, 0, Z_BACK))
    inner = _profile(HW - T, Y_TOP - T, CORNER_R - T).extrude(Z_FRONT - IN_Z + 1).translate((0, 0, IN_Z))
    s = outer.cut(inner)
    # the warm-air slot: the lid stops short of the wall (the corner radii stay, for stiffness)
    s = s.cut(_box(-(HW - CORNER_R), HW - CORNER_R, Y_TOP - T - 1, Y_TOP + 1, WALL_BACK - TOP_GAP, Z_FRONT + 1))
    # the two tall gussets run right to the base's back edge: a small notch for each tail
    for gx, gh in pl.GUSSETS:
        if gh > 100:
            s = s.cut(_box(gx - pl.GUSSET_T / 2 - 0.4, gx + pl.GUSSET_T / 2 + 0.4, BASE_TOP - 1, BASE_TOP + 5.0, Z_BACK - 1, IN_Z + 1))
    # feet and pegs
    for sx in (-1, 1):
        a, b = sorted((sx * (HW - T), sx * FOOT_X1))
        s = s.union(_box(a, b, BASE_TOP, BASE_TOP + FOOT_T, Z_BACK, FOOT_Z1))
    for bx, bz in pl.BASE_HOLES:
        if abs(bx) < 1:
            continue                                # the middle hole is under nothing: left empty
        peg = (cq.Workplane("XZ").workplane(offset=-BASE_TOP - 0.5).center(bx, -pl.WALL_T - bz)
               .polygon(8, PEG_AF / math.cos(math.pi / 8)).extrude(PEG_LEN + 0.5))
        s = s.union(peg.rotate((bx, 0, -pl.WALL_T - bz), (bx, 1, -pl.WALL_T - bz), 22.5))
    # card: ribs behind it, a ledge under it with a 45 degree lip
    for x in RIB_XS:
        s = s.union(_box(x - 1, x + 1, CARD_Y0, CARD_Y0 + CARD_MAX_H - 2, IN_Z - 0.5, RIB_Z))
    for x0, x1 in LEDGE_SEGS:
        z_lip = RIB_Z + CARD_MAX_T
        prof = [(CARD_Y0 - LEDGE_T, IN_Z - 0.5), (CARD_Y0, IN_Z - 0.5), (CARD_Y0, z_lip),
                (CARD_Y0 + LIP, z_lip + LIP), (CARD_Y0 - LEDGE_T, z_lip + LIP)]
        s = s.union(cq.Workplane("YZ").workplane(offset=x0).polyline(prof).close().extrude(x1 - x0))
    for x, y in TOGGLE_POSTS:
        s = s.union(_post(x, y, CARD_POST_TOP))
    # module: two pads, two posts, one window
    for x in (20.0, 62.0):
        s = s.union(_box(x - 4, x + 4, MOD_Y - 12, MOD_Y + 12, IN_Z - 0.5, IN_Z + MOD_PAD))
    for x, y in BRIDGE_POSTS:
        s = s.union(_post(x, y, MOD_POST_TOP))
    s = s.cut(_box(HW - T - 1, HW + 1, MOD_Y - USB_W / 2, MOD_Y + USB_W / 2, USB_Z0, USB_Z0 + USB_H))
    return s


def toggle():
    """Card keeper: swings over the card's top edge. One M4 x 8 into the post's nut. Print two."""
    body = _box(-5, 39, -5, 5, 0, 3).edges("|Z").fillet(3)
    return body.cut(_cyl_z(0, 0, M4_HOLE / 2, -1, 4))


def bridge():
    """Module keeper: a bar across the USB socket. Two M4 x 12 into the posts' nuts. Print one."""
    span = BRIDGE_POSTS[1][1] - BRIDGE_POSTS[0][1]
    body = _box(-6, 6, -6, span + 6, 0, 4).edges("|Z").fillet(3)
    return body.cut(_cyl_z(0, 0, M4_HOLE / 2, -1, 5)).cut(_cyl_z(0, span, M4_HOLE / 2, -1, 5))


# ------------------------------------------------------------ dummies (NOT printed)

def card_dummy(w=130.0, h=100.0, t=2.0):
    return _box(-w / 2, w / 2, CARD_Y0, CARD_Y0 + h, RIB_Z, RIB_Z + t)


def card_parts_dummy(w=130.0, h=100.0, t=2.0):
    """Eight diodes, the capacitor and the tallest solder lumps, from the template's millimetres
    (legs 12 apart, rails 60 apart, capacitor 13 x 25 lying down at the top right)."""
    z = RIB_Z + t
    x_leg1, y_plus = -w / 2 + 30.0, CARD_Y0 + h - 20.0
    d = None
    for i in range(4):
        for yy in (y_plus - 14.0, y_plus - 46.0):
            b = _box(x_leg1 + 12 * i - 2.7, x_leg1 + 12 * i + 2.7, yy - 4.75, yy + 4.75, z, z + 5.3)
            d = b if d is None else d.union(b)
    d = d.union(_box(x_leg1 - 6, x_leg1 + 48, y_plus - 1, y_plus + 1, z, z + 4))           # plus rail
    d = d.union(_box(x_leg1 - 6, x_leg1 + 48, y_plus - 61, y_plus - 59, z, z + 4))         # minus rail
    cap = (cq.Workplane("YZ").workplane(offset=x_leg1 + 62).center(y_plus - 8, z + 6.5).circle(6.5).extrude(25))
    return d.union(cap)


def module_dummy():
    """PLACEHOLDER size. Socket against the side wall, board lying on the pads."""
    x1 = HW - 0.2
    z0 = IN_Z + MOD_PAD
    pcb = _box(x1 - MOD_PCB[0], x1 - 2.0, MOD_Y - MOD_PCB[1] / 2, MOD_Y + MOD_PCB[1] / 2, z0, z0 + MOD_PCB[2])
    sock = _box(x1 - USB_SOCKET[0], x1, MOD_Y - USB_SOCKET[1] / 2, MOD_Y + USB_SOCKET[1] / 2,
                z0 + MOD_PCB[2], z0 + MOD_PCB[2] + USB_SOCKET[2])
    return pcb.union(sock)


def tester_dummy():
    zc = IN_Z + MOD_PAD + MOD_PCB[2] + USB_SOCKET[2] / 2
    x0 = HW + 1.5
    body = _box(x0, x0 + TESTER[0], MOD_Y - TESTER[1] / 2, MOD_Y + TESTER[1] / 2, zc - TESTER[2] / 2, zc + TESTER[2] / 2)
    plug = _box(HW - 9, x0 + 1, MOD_Y - 6, MOD_Y + 6, zc - 2.25, zc + 2.25)
    return body.union(plug)


def clamp_dummy(sx):
    """A 100 mm G-clamp, jaw on the foot. Sizes guessed from a typical one: 22 mm wide, 60 throat."""
    xc = sx * 86.0
    w = 11.0
    top = BASE_TOP + FOOT_T
    g = _box(xc - w, xc + w, top, top + 16, BASE_BACK - 30, -66)                 # upper arm, pad on the foot
    g = g.union(_box(xc - w, xc + w, -95, top + 16, BASE_BACK - 30, BASE_BACK - 14))   # spine, beyond the table edge
    g = g.union(_box(xc - w, xc + w, -95, -79, BASE_BACK - 30, -66))             # lower arm
    g = g.union(cq.Workplane("XZ").workplane(offset=115).center(xc, -78).circle(5).extrude(85))   # screw, y -115..-30
    return g


def bolts_dummy():
    """Heads of the four M4 bolts, for the picture."""
    d = None
    pts = [(x, y, CARD_POST_TOP + 3) for x, y in TOGGLE_POSTS] + [(x, y, IN_Z + MOD_PAD + 8.6 + 4) for x, y in BRIDGE_POSTS]
    for x, y, z in pts:
        h = _cyl_z(x, y, 3.5, z, z + 4)
        d = h if d is None else d.union(h)
    return d


def placed_small_parts():
    out = {}
    for i, (x, y) in enumerate(TOGGLE_POSTS):
        # arm hangs straight down over the card's top edge
        out[f"toggle{i + 1}"] = toggle().rotate((0, 0, 0), (0, 0, 1), -90).translate((x, y, CARD_POST_TOP))
    x, y = BRIDGE_POSTS[0]
    out["bridge"] = bridge().translate((x, y, IN_Z + MOD_PAD + MOD_PCB[2] + USB_SOCKET[2]))
    return out


def _vol(a, b):
    """Overlap volume, solid by solid (one boolean on a many-body compound can come back null)."""
    total = 0.0
    for sa in a.solids().vals():
        for sb in b.solids().vals():
            if sa.BoundingBox().xmax < sb.BoundingBox().xmin or sb.BoundingBox().xmax < sa.BoundingBox().xmin:
                continue
            try:
                total += sum(s.Volume() for s in sa.intersect(sb).Solids())
            except ValueError:
                pass                                   # null result = no overlap
    return total


def check(sh):
    fr, motor, pins = pl.frame(), pl.motor_dummy(), pl.pins_dummy()
    card, parts, mod = card_dummy(CARD_MAX_W, CARD_MAX_H, 2.0), card_parts_dummy(), module_dummy()
    res = [("shell is one solid", sh.solids().size() == 1)]
    for name, other in (("frame", fr), ("motor", motor), ("pin bolts and nuts", pins)):
        v = _vol(sh, other)
        res.append((f"shell clears the {name} ({v:.3f} mm3)", v < 1e-3))
    v = _vol(sh, card) + _vol(sh, parts)
    res.append((f"biggest card {CARD_MAX_W:.0f} x {CARD_MAX_H:.0f} and its parts fit the pocket ({v:.3f} mm3)", v < 1e-3))
    v = _vol(card.union(parts), fr.union(motor).union(pins))
    res.append((f"card and parts clear frame, gussets, motor and nuts ({v:.3f} mm3)", v < 1e-3))
    gap = -pl.WALL_LOCAL - pl.MOTOR_LEN - (RIB_Z + 2.0 + 13.0)
    res.append((f"capacitor top to the motor's back: {gap:.1f} mm", gap >= 6))
    v = _vol(mod, fr.union(motor).union(pins).union(card)) + _vol(mod, sh) + _vol(tester_dummy(), sh)
    res.append((f"placeholder module and tester clear everything ({v:.3f} mm3)", v < 1e-3))
    v = sum(_vol(clamp_dummy(sx), sh.union(fr)) for sx in (-1, 1))
    res.append((f"both G-clamps sit on the feet and touch nothing else ({v:.3f} mm3)", v < 1e-3))
    bay = FOOT_X1 - (HW)
    res.append((f"clamp bay {bay:.1f} mm wide between shell and outer gusset (a 100 mm G-clamp is about 22)", bay >= 25))
    # nothing in front of the wall, so nothing near the wheel, ring or crank
    bb = sh.val().BoundingBox()
    res.append((f"shell ends at Z = {bb.zmax:.1f}: all of it is behind the wall (Z = {WALL_BACK:.0f})", bb.zmax < WALL_BACK))
    r_corner = math.hypot(HW, Y_TOP - pl.AXLE_Y)
    res.append((f"top corners {r_corner:.0f} mm from the axle: hidden behind the {pl.R_OUT:.0f} mm wheel from the front",
                r_corner < pl.R_OUT - 10))
    dims = sorted((bb.xlen, bb.ylen, bb.zlen))
    res.append((f"shell {bb.xlen:.0f} x {bb.ylen:.0f} on the plate, {bb.zlen:.0f} tall: fits 256", dims[2] <= 250))
    vol = sh.val().Volume() / 1000
    res.append((f"shell {vol:.0f} cm3 of plastic, about {vol * 1.24:.0f} g of PLA", vol < 260))
    return res


if __name__ == "__main__":
    sh = shell()
    res = check(sh)
    for text, ok in res:
        print(f"[{'ok' if ok else 'NO'}] {text}")
    os.makedirs(OUT, exist_ok=True)
    kw = dict(tolerance=0.02, angularTolerance=0.15)
    # as printed: back panel on the bed
    printed = sh.translate((0, 0, -Z_BACK))
    cq.exporters.export(printed, os.path.join(OUT, "concept_backpack.stl"), **kw)
    small = toggle().union(toggle().translate((0, 16, 0))).union(bridge().translate((-20, 0, 0)))
    cq.exporters.export(small, os.path.join(OUT, "concept_backpack_small_parts.stl"), **kw)
    # in place, for pictures
    view = {"shell": sh, "card": card_dummy(), "card_parts": card_parts_dummy(), "module": module_dummy(),
            "tester": tester_dummy(), "clamp_l": clamp_dummy(-1), "clamp_r": clamp_dummy(1), "bolts": bolts_dummy()}
    view.update(placed_small_parts())
    for name, part in view.items():
        cq.exporters.export(part, os.path.join(OUT, f"_view_backpack_{name}.stl"), tolerance=0.05, angularTolerance=0.2)
    bad = [t for t, ok in res if not ok]
    print(f"exported to {OUT}" + (f"; {len(bad)} CHECKS FAILED" if bad else ""))
