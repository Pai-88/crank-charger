"""Wire cover, concept "base-tray": a LOW TRAY beside the base plate. MASSING MODEL ONLY.

Why beside and not on top: the card is 111 x 90 mm (wiring_pictures.py, Ladder.card) and
the free floor of the base plate is cut into bays 52, 40, 40 and 52 mm wide by the five
gussets (the two tall ones run the whole 85 mm depth). No flat place on the base takes the
card. So the tray sits on the table, tight against the base's side edge, level with it,
and is tied to the base through the base hole at (72, 70) by a printed FOOT that lies in
the outer bay. The G-clamp for that side lands on the foot, exactly where step 9 puts it.

Four printed parts, all support-free:
    foot     lies on the base in the outer bay. One M4 x 16 dropped through it into the
             base hole as a pin (head sunk, no nut: a nut under the flat base would lift it
             off the table). A groove underneath carries the four motor leads. Its top is
             the clamp pad.
    tray     drops over the foot's hooked end. Card on ribs, capacitor, module bay.
    lid      a plain slab. Stands 1.5 mm proud all round: that shadow gap is the vent.
    channel  a cap that presses onto the sloping edge of the tall gusset; the four motor
             leads lie on the gusset's edge underneath it.
    (+ plate a small slide-in face plate for the USB socket, re-printed to the module's
             real size when it arrives. Every MODULE_* number below is a PLACEHOLDER.)

Model frame as planetary.py: X right, Y up, Z toward you, wall front Z=0, table Y=0.

    .venv/bin/python cad/wire_cover_concept_base-tray.py     check, export to cad/stl/cover/
"""
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import planetary as P

OUT = os.path.join(HERE, "stl", "cover")
NAME = "base-tray"

# ------------------------------------------------------------ what exists (from planetary.py)
BASE_X = P.BASE_HALF_W                     # 105: the base's side edge
BASE_TOP = P.BASE_T                        # 8
BASE_REAR = -P.WALL_T + 1 - (P.BASE_DEPTH + 1)   # -93
HOLE_X, HOLE_Z = P.BASE_HOLES[2][0], -P.WALL_T - P.BASE_HOLES[2][1]      # (72, -78)
G_X, G_H = P.GUSSETS[3]                    # the tall gusset on this side: x 45, 155 high at the wall
G_SLOPE = (G_H - BASE_TOP) / P.BASE_DEPTH  # 1.73: its edge drops this much per mm toward the back
OUTER_G_END = -P.WALL_T - (P.GUSSETS[4][1] - BASE_TOP)                   # -60: the short outer gusset stops here

# ------------------------------------------------------------ what goes inside
CARD_L, CARD_W, CARD_T = 111.0, 90.0, 1.5  # the template's outline. TRIM the stiff card to it
CAP_D, CAP_L = 13.0, 25.0
MODULE_L, MODULE_W, MODULE_H = 45.0, 22.0, 12.0     # PLACEHOLDER: measure on arrival
USB_W, USB_H = 14.0, 7.5                             # PLACEHOLDER opening in the face plate
TESTER = (26.0, 14.0, 65.0)                          # PLACEHOLDER, view only

# ------------------------------------------------------------ foot
FOOT_H = 14.0
FOOT_X0 = 52.0                 # clear of the tall gusset (47.5) and the channel's leg
FOOT_FRONT = -50.0             # clamp pad runs this far forward, beside the outer gusset
FOOT_GATE = OUTER_G_END - 2.0  # -62: behind the outer gusset the foot can reach the edge
GROOVE_Z0, GROOVE_Z1, GROOVE_H = -90.0, -84.0, 10.0
PIN_D, PIN_HEAD_D, PIN_HEAD_H = 4.5, 8.0, 5.0        # M4 x 16 socket cap, head 1 mm under the pad
HEAD_T, HEAD_HOOK = 4.0, 6.0   # the hooked end inside the tray

# ------------------------------------------------------------ tray
GAP_BASE = 0.4
WALL, FLOOR = 2.0, 2.4
TRAY_WALL_H = 27.0
CORRIDOR = 5.5                 # between the inboard wall and the card: the foot's hook lives here
CARD_FIT = 1.5
DIVIDER = 1.6
BAY_W = 36.0                   # module bay, outboard of the card
RIB_H = 4.0                    # card stands this far off the floor: spare lead goes under it
SLOT_FIT = 0.3
PLATE_W, PLATE_T = 26.0, 3.0   # the slide-in USB face plate

TRAY_X0 = BASE_X + GAP_BASE
TRAY_Z0 = BASE_REAR - 0.5 - WALL            # rear wall just behind the foot: 2.5 mm past the base's back edge
IN_X0 = TRAY_X0 + WALL
CARD_X0 = IN_X0 + CORRIDOR
CARD_X1 = CARD_X0 + CARD_W + CARD_FIT
BAY_X0 = CARD_X1 + DIVIDER
BAY_X1 = BAY_X0 + BAY_W
TRAY_X1 = BAY_X1 + WALL
IN_Z0 = TRAY_Z0 + WALL
IN_Z1 = IN_Z0 + CARD_L + 2.0
TRAY_Z1 = IN_Z1 + WALL

# ------------------------------------------------------------ lid
LID_GAP, LID_T, SKIRT_H, SKIRT_IN = 1.5, 2.4, 4.0, 2.0   # the lid rests on five posts inside the tray

# ------------------------------------------------------------ channel on the tall gusset
CH_TOP_Y = 125.0               # where the leads leave the motor's lower corner and meet the gusset edge
CH_HALF = 6.0
CH_ROOF = 9.0                  # roof stands this far off the gusset's edge
CH_LEG = 10.0                  # legs reach this far down the gusset's faces
CH_SLOT = 5.2                  # gusset is 5.0
CH_MOUTH = 22.0                # inboard leg cut away here: the leads come in from the motor


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def vcyl(x, z, r, y0, y1):
    """A cylinder standing up (axis along Y)."""
    return cq.Workplane("XZ").workplane(offset=-y1).center(x, z).circle(r).extrude(y1 - y0)


def foot():
    top = BASE_TOP + FOOT_H
    body = box(FOOT_X0, 99.0, BASE_TOP, top, BASE_REAR, FOOT_FRONT)                  # the clamp pad
    body = body.union(box(99.0 - 1, IN_X0 + SLOT_FIT, BASE_TOP, top, BASE_REAR, FOOT_GATE))       # through the gate and the tray wall
    body = body.union(box(IN_X0 + SLOT_FIT, IN_X0 + SLOT_FIT + HEAD_T, BASE_TOP, top, BASE_REAR, FOOT_GATE + HEAD_HOOK))   # the hook
    body = body.cut(box(FOOT_X0 - 1, IN_X0 + HEAD_T + 2, BASE_TOP - 1, BASE_TOP + GROOVE_H, GROOVE_Z0, GROOVE_Z1))       # lead groove
    body = body.cut(vcyl(HOLE_X, HOLE_Z, PIN_D / 2, BASE_TOP - 1, top + 1))
    return body.cut(vcyl(HOLE_X, HOLE_Z, PIN_HEAD_D / 2, top - PIN_HEAD_H, top + 1))


def tray():
    body = box(TRAY_X0, TRAY_X1, 0, TRAY_WALL_H, TRAY_Z0, TRAY_Z1)
    body = body.cut(box(IN_X0, BAY_X1, FLOOR, TRAY_WALL_H + 1, IN_Z0, IN_Z1))
    # low divider between the card and the module bay: the two output wires cross over it
    body = body.union(box(CARD_X1, BAY_X0, FLOOR - 0.5, 12.0, IN_Z0 - 0.5, IN_Z1 + 0.5))
    # ribs the card lies on, each ending in a stop that keeps the card out of the corridor
    for z in (IN_Z0 + 14, (IN_Z0 + IN_Z1) / 2, IN_Z1 - 14):
        body = body.union(box(CARD_X0, CARD_X1 + 0.5, FLOOR - 0.5, FLOOR + RIB_H, z - 0.8, z + 0.8))
        if z > FOOT_GATE + HEAD_HOOK + 6:
            body = body.union(box(CARD_X0 - 1.6, CARD_X0, FLOOR - 0.5, FLOOR + RIB_H + 6, z - 3, z + 3))
    # the slot and floor notch that let the tray drop over the foot's hook
    body = body.cut(box(TRAY_X0 - 1, IN_X0 + 1, -1, BASE_TOP + FOOT_H + SLOT_FIT, BASE_REAR - SLOT_FIT, FOOT_GATE + SLOT_FIT))
    body = body.cut(box(TRAY_X0 - 1, IN_X0 + SLOT_FIT + HEAD_T + 0.6, -1, FLOOR + 1, BASE_REAR - SLOT_FIT, FOOT_GATE + HEAD_HOOK + 0.6))
    # USB notch in the front wall, open to the rim, with two cheeks that make the groove for the face plate
    cx = (BAY_X0 + BAY_X1) / 2
    body = body.cut(box(cx - PLATE_W / 2 + 2, cx + PLATE_W / 2 - 2, FLOOR + 2, TRAY_WALL_H + 1, IN_Z1 - 1, TRAY_Z1 + 1))
    for s in (-1, 1):
        x0 = cx + s * (PLATE_W / 2 + 0.3)
        body = body.union(box(min(x0, x0 + s * 3), max(x0, x0 + s * 3), FLOOR - 0.5, TRAY_WALL_H, IN_Z1 - PLATE_T - 0.4 - 2, IN_Z1 + 0.5))
        body = body.union(box(min(x0, x0 - s * 2.3), max(x0, x0 - s * 2.3), FLOOR - 0.5, TRAY_WALL_H, IN_Z1 - PLATE_T - 0.4 - 2, IN_Z1 - PLATE_T - 0.4))
    # five posts inside the tray carry the lid 1.5 mm above the rim: nothing shows in the gap
    top = TRAY_WALL_H + LID_GAP
    for x, z in ((IN_X0 + 6.5, FOOT_GATE + HEAD_HOOK + 14), (IN_X0 + 6.5, IN_Z1 - 30), (CARD_X1 - 4.5, IN_Z0 + 30), (CARD_X1 - 4.5, IN_Z1 - 45),
                 (BAY_X1 - 9, IN_Z0 + 9)):
        body = body.union(box(x - 2.2, x + 2.2, FLOOR - 0.5, top, z - 3, z + 3))
    # a notch in the back rim for the two meter leads (step E10 clips a meter on the rails)
    return body.cut(box(CARD_X0 + 40, CARD_X0 + 48, TRAY_WALL_H - 5, TRAY_WALL_H + 1, TRAY_Z0 - 1, IN_Z0 + 1))


def face_plate():
    cx = (BAY_X0 + BAY_X1) / 2
    p = box(cx - PLATE_W / 2, cx + PLATE_W / 2, FLOOR, TRAY_WALL_H, IN_Z1 - PLATE_T - 0.2, IN_Z1 - 0.2)
    y = FLOOR + 5.0 + 1.6 + 0.5                       # PLACEHOLDER: board on a 5 mm cradle
    return p.cut(box(cx - USB_W / 2, cx + USB_W / 2, y, y + USB_H, IN_Z1 - PLATE_T - 1, IN_Z1 + 1))


def lid():
    y0 = TRAY_WALL_H + LID_GAP
    body = box(TRAY_X0, TRAY_X1, y0, y0 + LID_T, TRAY_Z0, TRAY_Z1)
    a = SKIRT_IN
    ring = box(IN_X0 + a, BAY_X1 - a, y0 - SKIRT_H, y0 + 0.5, IN_Z0 + a, IN_Z1 - a)
    ring = ring.cut(box(IN_X0 + a + 1.6, BAY_X1 - a - 1.6, y0 - SKIRT_H - 1, y0 + 1, IN_Z0 + a + 1.6, IN_Z1 - a - 1.6))
    body = body.union(ring)
    cx = (BAY_X0 + BAY_X1) / 2
    body = body.cut(box(cx - PLATE_W / 2 - 5, cx + PLATE_W / 2 + 5, y0 - SKIRT_H - 1, y0, IN_Z1 - PLATE_T - 4, IN_Z1))   # the skirt steps round the USB plate
    # eight fins centre the lid in the tray. They stop below the rim, so the shadow gap is unbroken
    for x in (IN_X0 + 25, BAY_X0 - 25):
        body = body.union(box(x - 1, x + 1, y0 - SKIRT_H, TRAY_WALL_H, IN_Z0 + 0.3, IN_Z0 + a + 0.5))
        body = body.union(box(x - 1, x + 1, y0 - SKIRT_H, TRAY_WALL_H, IN_Z1 - a - 0.5, IN_Z1 - 0.3))
    for z in (IN_Z0 + 50, IN_Z1 - 25):
        body = body.union(box(IN_X0 + 0.3, IN_X0 + a + 0.5, y0 - SKIRT_H, TRAY_WALL_H, z - 1, z + 1))
        body = body.union(box(BAY_X1 - a - 0.5, BAY_X1 - 0.3, y0 - SKIRT_H, TRAY_WALL_H, z - 1, z + 1))
    return body


def channel():
    """Built along its own length (local z = down the slope, local y = into the gusset),
    then swung onto the gusset's edge."""
    h = CH_HALF
    prof = [(-h, -CH_ROOF), (h, -CH_ROOF), (h, CH_LEG), (CH_SLOT / 2, CH_LEG), (CH_SLOT / 2, 0), (4.0, -1.4), (4.0, -CH_ROOF + 1.6),
            (-4.0, -CH_ROOF + 1.6), (-4.0, -1.4), (-CH_SLOT / 2, 0), (-CH_SLOT / 2, CH_LEG), (-h, CH_LEG)]
    length = (CH_TOP_Y - BASE_TOP) * math.hypot(1, 1 / G_SLOPE) + 25
    c = cq.Workplane("XY").polyline(prof).close().extrude(length)
    c = c.cut(cq.Workplane("XY").box(h - CH_SLOT / 2 + 0.2, CH_ROOF + CH_LEG, CH_MOUTH + 1, centered=False)
              .translate((-h - 0.1, -CH_ROOF + 1.6, -1)))                                  # the mouth, on the motor's side
    theta = math.degrees(math.atan2(G_SLOPE, -1.0))                                        # 120 deg: local z points down the slope
    z_top = -P.WALL_T - (G_H - CH_TOP_Y) / G_SLOPE
    c = c.rotate((0, 0, 0), (1, 0, 0), theta).translate((G_X, CH_TOP_Y, z_top))
    keep = box(G_X - 20, G_X + 20, BASE_TOP + 0.2, 400, BASE_REAR, 50)                     # stands on the base, flush with its back edge
    c = c.intersect(keep)
    c = c.union(box(G_X - h, G_X + h, BASE_TOP + 0.2, BASE_TOP + 17.0, BASE_REAR, BASE_REAR + 1.6)       # closes the back
                .cut(box(G_X - CH_SLOT / 2, G_X + CH_SLOT / 2, 0, BASE_TOP + 3.5, BASE_REAR - 1, BASE_REAR + 3)))
    # the leads turn sideways here, into the foot's groove
    return c.cut(box(G_X + CH_SLOT / 2, G_X + h + 1, BASE_TOP - 1, BASE_TOP + GROOVE_H + 1, GROOVE_Z0 - 1.2, GROOVE_Z1 + 6))


# ------------------------------------------------------------ view-only dummies

def dummies():
    d = {}
    y = FLOOR + RIB_H
    d["card"] = box(CARD_X0 + 0.5, CARD_X0 + 0.5 + CARD_W, y, y + CARD_T, IN_Z0 + 1, IN_Z0 + 1 + CARD_L)
    # card frame (mm, wiring_pictures.Ladder): card x runs toward the front, card y runs toward the machine;
    # card corner (x0=-18, y0=-15) is at the rear, outboard.
    def cxz(cx_, cy_):
        return (CARD_X0 + 0.5 + CARD_W - (cy_ + 15.0), IN_Z0 + 1 + (cx_ + 18.0))
    yt = y + CARD_T
    parts = None
    for k in range(4):
        for cx_, (a, b) in ((P_COL[k], (6, 15)), (P_COL[k] + 1.6, (45, 54))):
            (x1, z), (x0, _) = cxz(cx_, a), cxz(cx_, b)
            body = cq.Workplane("YZ").workplane(offset=x0).center(yt + 2.65, z).circle(2.65).extrude(x1 - x0)
            parts = body if parts is None else parts.union(body)
        for row in (-0.75, 60.75):                                                         # the two rails
            (x, z0), (_, z1) = cxz(P_COL[0], row), cxz(P_COL[3] + 19, row)
            parts = parts.union(box(x - 0.65, x + 0.65, yt, yt + 1.3, z0, z1))
        (x1, z), (x0, _) = cxz(P_COL[k], -1), cxz(P_COL[k], 61)
        parts = parts.union(box(x0, x1, yt + 2, yt + 3.3, z - 0.65 + 0.8, z + 0.65 + 0.8))  # the leg's leads
    (x1, z0), (x0, z1) = cxz(63.5, -3.7), cxz(89, 9.3)
    cap = cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, yt + CAP_D / 2).circle(CAP_D / 2).extrude(z1 - z0)
    d["card_parts"] = parts.union(cap)
    cx = (BAY_X0 + BAY_X1) / 2
    mz1 = IN_Z1 - PLATE_T - 0.6
    mod = box(cx - MODULE_W / 2, cx + MODULE_W / 2, FLOOR + 5, FLOOR + 5 + 1.6, mz1 - MODULE_L, mz1)
    mod = mod.union(box(cx - 6, cx + 6, FLOOR + 6.6, FLOOR + 6.6 + MODULE_H - 4, mz1 - MODULE_L + 12, mz1 - 20))
    mod = mod.union(box(cx - 6.6, cx + 6.6, FLOOR + 7.2, FLOOR + 7.2 + 5.8, mz1 - 14, TRAY_Z1 + 1))
    d["module"] = mod
    tw, th, tl = TESTER
    ty = FLOOR + 7.2 + 2.9
    t = box(cx - 6, cx + 6, ty - 2.25, ty + 2.25, TRAY_Z1 + 1, TRAY_Z1 + 12)
    d["tester"] = t.union(box(cx - tw / 2, cx + tw / 2, ty - th / 2, ty + th / 2, TRAY_Z1 + 10, TRAY_Z1 + 10 + tl))
    d["tester_screen"] = box(cx - tw / 2 + 3, cx + tw / 2 - 3, ty + th / 2, ty + th / 2 + 0.4, TRAY_Z1 + 18, TRAY_Z1 + 10 + tl - 16)
    d["pin"] = vcyl(HOLE_X, HOLE_Z, 3.5, BASE_TOP + FOOT_H - PIN_HEAD_H, BASE_TOP + FOOT_H - 1).union(
        vcyl(HOLE_X, HOLE_Z, 2.0, BASE_TOP + FOOT_H - 16 - 1, BASE_TOP + FOOT_H - 1))
    # the four leads: motor corner -> channel -> groove -> under the card
    d["leads_exposed"] = _tube([(P.MOTOR_SQ / 2, P.AXLE_Y - 14, -52.0), (P.MOTOR_SQ / 2 + 6, P.AXLE_Y - 20, -46.0),
                                (G_X - 3, CH_TOP_Y + 1, -27.0), (G_X, CH_TOP_Y - 6, -27.5 - 6 / G_SLOPE - 3)], 2.2)
    for sx, name in ((1, "clamp_r"), (-1, "clamp_l")):
        d[name] = _clamp(sx * 76.0, BASE_TOP + (FOOT_H if sx > 0 else 0))
    d["table"] = box(-330, 330, -30, -0.05, BASE_REAR, 260)
    return d


P_COL = (0.0, 12.0, 24.0, 36.0)


def _tube(pts, r):
    path = cq.Workplane("XY").polyline(pts)
    out = None
    for a, b in zip(pts, pts[1:]):
        v = cq.Vector(*b) - cq.Vector(*a)
        seg = cq.Solid.makeCylinder(r, v.Length, cq.Vector(*a), v)
        out = cq.Workplane("XY").newObject([seg]) if out is None else out.union(cq.Workplane("XY").newObject([seg]))
        out = out.union(cq.Workplane("XY").sphere(r).translate(b))
    return out


def _clamp(x, y_jaw, table_t=30.0):
    """A 100 mm G-clamp, fixed jaw on top, as in assembly/step_09.png. View only, sizes guessed."""
    w, z_in, z_out = 9.0, -68.0, BASE_REAR - 22.0
    c = box(x - w, x + w, y_jaw, y_jaw + 14, z_out, z_in)                                   # top arm, ends in the jaw
    c = c.union(box(x - w, x + w, -table_t - 62, y_jaw + 14, z_out - 14, z_out))            # spine
    c = c.union(box(x - w, x + w, -table_t - 62, -table_t - 48, z_out, z_in + 4))           # bottom arm
    c = c.union(vcyl(x, z_in - 8, 4.5, -table_t - 90, -table_t - 4))                        # screw
    return c.union(vcyl(x, z_in - 8, 10.0, -table_t - 4, -table_t - 0.1))                   # swivel pad under the table


# ------------------------------------------------------------ checks

def _vol(a, b):
    return sum(s.Volume() for s in a.intersect(b).solids().vals())


def check(parts):
    res = []
    fr, motor = P.frame(), P.motor_dummy()
    for name, part in parts.items():
        res.append((f"{name} is one solid", part.solids().size() == 1))
        v = _vol(part, fr) + _vol(part, motor)
        res.append((f"{name} clears the frame and the motor ({v:.3f} mm3)", v < 1e-3))
    names = list(parts)
    worst, pair = max((_vol(parts[a], parts[b]), f"{a}/{b}") for i, a in enumerate(names) for b in names[:i])
    res.append((f"cover parts do not overlap each other (worst {worst:.3f} mm3, {pair})", worst < 1e-3))
    # the turning parts: nothing of the cover may be inside the cylinder the ring, wheel, grip and a hand sweep
    top = TRAY_WALL_H + LID_GAP + LID_T
    r_ring = P.R_OUT + P.LUG_REACH
    low_ring = P.AXLE_Y - math.sqrt(r_ring ** 2 - TRAY_X0 ** 2)
    res.append((f"lid top {top:.1f} mm; the ring's lugs pass {low_ring - top:.0f} mm above it at the tray's inboard edge", low_ring - top >= 25))
    res.append((f"tray ends {P.WHEEL_Z0 - TRAY_Z1:.0f} mm behind the wheel's back face and {P.WHEEL_Z0 + P.WHEEL_T + P.PED_H - TRAY_Z1:.0f} mm "
                f"behind the grip", P.WHEEL_Z0 - TRAY_Z1 >= 8))
    cx = (BAY_X0 + BAY_X1) / 2
    r_hand = P.R_HANDLE + P.GRIP_FLANGE_R + 30.0
    res.append((f"USB tester at x = {cx:.0f}: {cx - TESTER[0] / 2 - r_hand:.0f} mm outside a hand on the grip ({r_hand:.0f} mm from the axle)",
                cx - TESTER[0] / 2 - r_hand >= 20))
    # clamps
    res.append((f"clamp pad on the foot {99 - FOOT_X0:.0f} x {FOOT_FRONT - GROOVE_Z1:.0f} mm, {FOOT_H:.0f} mm of solid plastic over the base",
                99 - FOOT_X0 >= 40 and FOOT_FRONT - GROOVE_Z1 >= 25))
    res.append((f"the other outer bay (x -100 to -47.5) is untouched: second clamp as in step 9", True))
    res.append((f"pin: M4 x 16, head {PIN_HEAD_H - 4:.0f} mm under the pad, {16 - (FOOT_H - PIN_HEAD_H) - 0:.0f} mm into the 8 mm base, "
                f"{BASE_TOP - (16 - (FOOT_H - PIN_HEAD_H)):.0f} mm short of the table", 0 < 16 - (FOOT_H - PIN_HEAD_H) < BASE_TOP))
    # what fits
    clear = (TRAY_WALL_H + LID_GAP) - (FLOOR + RIB_H + CARD_T + CAP_D)
    res.append((f"card pocket {CARD_X1 - CARD_X0:.1f} x {IN_Z1 - IN_Z0:.1f} mm for the {CARD_W:.0f} x {CARD_L:.0f} card; "
                f"{clear:.1f} mm of air between the capacitor and the lid (the lid's skirt is over the card's empty margin)", clear >= 6))
    air = (TRAY_WALL_H + LID_GAP) - (FLOOR + RIB_H + CARD_T + 5.3)
    res.append((f"diodes lie on the card, {RIB_H:.0f} mm off the floor and {air:.0f} mm under the lid: no diode touches plastic", air >= 10))
    vent = LID_GAP * 2 * ((TRAY_X1 - TRAY_X0) + (TRAY_Z1 - TRAY_Z0) - 60)
    res.append((f"vent: {LID_GAP} mm shadow gap all round, {vent:.0f} mm2 open", vent >= 500))
    res.append((f"module bay {BAY_W:.0f} x {IN_Z1 - IN_Z0:.0f} x {TRAY_WALL_H - FLOOR:.0f} mm for a module of UNKNOWN size "
                f"(placeholder {MODULE_L:.0f} x {MODULE_W:.0f} x {MODULE_H:.0f})", BAY_W >= MODULE_W + 10))
    # the motor leads
    run = (40.0, (CH_TOP_Y - BASE_TOP) * math.hypot(1, 1 / G_SLOPE), IN_X0 + HEAD_T - G_X, 75.0)
    res.append((f"lead run: {run[0]:.0f} motor to channel + {run[1]:.0f} channel + {run[2]:.0f} groove + up to {run[3]:.0f} to J4 "
                f"= {sum(run):.0f} mm. MEASURE the motor's leads: they must be at least {sum(run) + 20:.0f} mm", True))
    for name, part in parts.items():
        bb = part.val().BoundingBox()
        dims = sorted((bb.xlen, bb.ylen, bb.zlen))
        res.append((f"{name} {dims[2]:.0f} x {dims[1]:.0f} x {dims[0]:.0f} mm fits the 256 mm plate", dims[2] <= 250))
    return res


if __name__ == "__main__":
    parts = {"foot": foot(), "tray": tray(), "lid": lid(), "channel": channel(), "face_plate": face_plate()}
    res = check(parts)
    for text, ok in res:
        print(f"[{'ok' if ok else 'NO'}] {text}")
    os.makedirs(OUT, exist_ok=True)
    kw = dict(tolerance=0.02, angularTolerance=0.2)
    comp = cq.Workplane("XY").newObject([cq.Compound.makeCompound([p.val() for p in parts.values()])])
    cq.exporters.export(comp, os.path.join(OUT, f"concept_{NAME}.stl"), **kw)
    for name, part in parts.items():
        cq.exporters.export(part, os.path.join(OUT, f"_view_{NAME}_{name}.stl"), **kw)
    for name, part in dummies().items():
        cq.exporters.export(part, os.path.join(OUT, f"_view_{NAME}_{name}.stl"), tolerance=0.05, angularTolerance=0.3)
    print(f"tray outside {TRAY_X1 - TRAY_X0:.1f} x {TRAY_Z1 - TRAY_Z0:.1f} x {TRAY_WALL_H + LID_GAP + LID_T:.1f} mm, "
          f"x {TRAY_X0:.1f} to {TRAY_X1:.1f}, z {TRAY_Z0:.1f} to {TRAY_Z1:.1f}")
    bad = [t for t, ok in res if not ok]
    print(f"MASSING MODEL exported to {OUT}" + (f"  ({len(bad)} checks FAILED)" if bad else ""))
