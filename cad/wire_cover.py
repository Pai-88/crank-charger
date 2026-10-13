"""Wire cover for the crank charger: one plain shell behind the wall, plus a small module sled.

Nothing in cad/planetary.py is changed: its frame, motor, pins, gears and wheel are imported
and used as the real solids for every fit check. Nothing here is printed or test-fitted yet.

Model frame (planetary.py's): X right seen from the front, Y UP, Z toward the person cranking.
Wall back face Z = -8, base top Y = 8, base back edge (= the table edge in step 9) Z = -93.

What it is
  * SHELL: a box with no bottom and no front. It slides over the motor from behind until four
    small stops touch the wall, drops 3 mm onto two pegs in the base's own outer holes, and is
    pinned by the SAME two G-clamps, which now sit on two feet of the shell.
  * The card (trimmed to the paper template, 111 x 90) stands on end on the inside of the back
    panel, held by a ledge and two corner clips. No bolts.
  * The DC-DC module rides on a SLED that goes into the corner low on one side and slides down
    onto a rail, its USB socket behind a plain window. Only the sled knows the module's size.
  * Two 45 degree baffles behind the wall's windows hide the inside from the front. Air comes
    in under the back panel (6 mm gap behind the base) and round the baffles, and leaves by a
    slot where the lid stops short of the wall.
  * No screws, no nuts, no inserts, no glue.

    .venv/bin/python cad/wire_cover.py            check; export only if no line is [NO]
    .venv/bin/python cad/wire_cover.py --quick    skip the gears and wheel (never exports)
    .venv/bin/python cad/wire_cover_render.py     the step pictures in cover/

Lines printed [note] are things no script can test (placeholders, heat, what he must measure).
"""
import math
import os
import subprocess
import sys

import cadquery as cq
import numpy as np
from shapely.geometry import box as sbox

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import batches as plate_rules          # read only: the P1S plate size, edge margin and reserved corner
import planetary as pl                 # read only: importing it exports nothing

OUT = os.path.join(HERE, "stl", "cover")
MESH_GATE = os.path.expanduser("~/.claude/skills/print-export-check/scripts/mesh_check.py")

# ============================================================ FROM THE FRAME (imported, never typed)
WALL_BACK = -pl.WALL_T                                    # -8
BASE_TOP = pl.BASE_T                                      # 8
BASE_BACK = -pl.WALL_T - pl.BASE_DEPTH                    # -93
AY = pl.AXLE_Y
MOTOR_BACK = -pl.WALL_LOCAL - pl.MOTOR_LEN                # -62
MOTOR_TOP = AY + pl.MOTOR_SQ / 2                          # 172.5
BOSSES = [(x, AY + y) for x, y in pl.PINS]
BOSS_XMAX = max(x for x, _ in BOSSES) + pl.PIN_BOSS_R     # 66.1
BOSS_TOP = max(y for _, y in BOSSES) + pl.PIN_BOSS_R      # 186.4
BOSS_UNDER = max(y for _, y in BOSSES) - pl.PIN_BOSS_R    # 166.4, underside of the two top bosses
PIN_TIP_Z = pl.SPIDER_Z0 + pl.SPIDER_T - pl.HEAD_POCKET - pl.PIN_BOLT_LEN      # -27.1
TALL_GUSSETS = [(gx, gh) for gx, gh in pl.GUSSETS if gh > 100]                 # x = -45 and +45
TALL_X = max(gx for gx, _ in TALL_GUSSETS)
TALL_H = TALL_GUSSETS[0][1]
OUTER_IN = pl.BASE_HALF_W - pl.GUSSET_T                   # 100, inner face of each outer gusset
OUTER_END_Z = WALL_BACK - min(pl.GUSSETS[-1][1] - pl.BASE_T, pl.BASE_DEPTH)    # -60, where it runs out
PEG_HOLES = [(bx, -pl.WALL_T - bz) for bx, bz in pl.BASE_HOLES if abs(bx) > 1]  # (+-72, -78)
_WINDOWS = pl.wall_windows(pl.wall_outline())
WIN_X_IN = min(abs(w.bounds[0]) if w.bounds[0] > 0 else abs(w.bounds[2]) for w in _WINDOWS)   # 52.5
WIN_Y0 = min(w.bounds[1] for w in _WINDOWS)               # 17
WIN_Y1 = max(w.bounds[3] for w in _WINDOWS)               # 159.1


def tall_gusset_top(z):
    """Height of a tall gusset's sloping edge at model Z (planetary.frame()'s triangle)."""
    d = min(TALL_H - pl.BASE_T, pl.BASE_DEPTH)
    return pl.BASE_T + (TALL_H - pl.BASE_T) * (1 - (WALL_BACK - z) / d)


# ============================================================ THE SHELL (mm)
T = 2.0                    # every wall of the shell
BOSS_CLEAR = 2.5           # least air between the inside of a side wall and a pin boss
IN_HW = math.ceil(BOSS_XMAX + BOSS_CLEAR)                 # 69, inside half width
HW = IN_HW + T                                            # 71, outside half width
GAP_WALL = 1.0             # side walls stop this far short of the wall's back face
WALL_STOP_GAP = 0.25       # four small stops on the side walls' front edges end this far from the wall:
                           # push the shell until they touch and the pegs are over their holes
STOP_BUMP_Y = ((BASE_TOP, BASE_TOP + 6.0), (163.0, 170.0))   # where the stops are: solid wall below and above the windows
GAP_BACK = 6.0             # back panel hangs this far behind the base's back edge: the low air inlet,
                           # right under the card and the module, and the way out for two meter tails
Z_FRONT = WALL_BACK - GAP_WALL                            # -9
IN_Z = BASE_BACK - GAP_BACK                               # -99, inside face of the back panel
Z_BACK = IN_Z - T                                         # -101, the filmed face; the bed face
CORNER_R = 22.0            # top corners, outside. Big, so nothing shows round the wall from the front
TOP_GAP = 13.0             # the lid stops this far short of the wall: the warm-air slot
BED_CHAMFER = 0.6          # on the bed edge of the filmed face

# feet under the G-clamps
FOOT_T = 4.0
FOOT_X1 = OUTER_IN - 1.0                                  # 99, 1 mm off the outer gusset
FOOT_Z1 = -20.0            # front end: the step-9 clamp's pad (Z -68 to -46) lands wholly on the foot
FOOT_X_WIDE = pl.BASE_HALF_W                              # 105: behind the outer gusset's tail the foot runs to the base's edge
FOOT_WIDE_Z1 = OUTER_END_Z - 2.0                          # -62
FOOT_TIE = 3.0             # 45 degree tie between foot and side wall, in front of the clamp only
FOOT_TIE_Z0 = -42.0

# pegs into the base's two outer 5.5 mm holes: they stop the shell sliding back. Slim in X on
# purpose: left-right is the forks' job, so two pegs 144 mm apart never fight each other.
# NO fillet at the root: the root is level with the base's top face, so any fillet would sit
# in the mouth of the hole (a 1 mm one makes the root 5.0 x 6.4 in a 5.5 hole).
PEG_X, PEG_Z = 3.0, 4.4    # across X and across Z. Pointed at the end that prints first, so no support
PEG_LEN = 3.0
PEG_TAPER = 8.0            # degrees per side

# forks that hug the two tall gussets: they fix the shell left to right
FORK_CLEAR = 0.5           # per side. COUPON C1
FORK_T = 2.0
FORK_H = 20.0              # top, above the table (under the sled's rail)
FORK_Z1 = -79.0            # front end

# baffles behind the wall's two windows
BAFFLE_T = 3.4             # measured along Z; 2.4 mm through the 45 degree slab
BAFFLE_FLAT = 0.8          # the slab ends in a flat this wide, not a feather. COUPON C5
BAFFLE_ROOT = 2.0          # wedge under the slab where it leaves the side wall
BAFFLE_X_TIP = WIN_X_IN - 1.5                             # 51: inside the wall's solid middle column
BAFFLE_SLIT = 4.0          # air slit between a baffle's tip and the wall's back face
BAFFLE_Y0 = WIN_Y0 - 2.0
BAFFLE_Y1 = math.ceil(WIN_Y1) + 0.0                       # 160

# ============================================================ THE CARD (real mm from electronics/wiring_pictures.py)
# Ladder.card(): template x -18..93, y -15..75, origin where leg 1 meets the PLUS rail.
# The pocket takes the PAPER TEMPLATE's outline. ELECTRONICS.md step 0 says to cut the card
# "about 13 x 10 cm" and tape the paper on: that card does NOT fit. cover/cover_01 shows the
# trim: cut the card flush with the paper, all four sides.
TPL_U0, TPL_U1, TPL_V0, TPL_V1 = -18.0, 93.0, -15.0, 75.0
TPL_COL = (0.0, 12.0, 24.0, 36.0)      # Ladder.COL
TPL_OFF = 1.6                          # Ladder.OFF
CARD_W = TPL_V1 - TPL_V0               # 90: the card stands ON END, capacitor end DOWN
CARD_H = TPL_U1 - TPL_U0               # 111
CARD_AS_TOLD = (130.0, 100.0)          # what ELECTRONICS.md step 0 says to cut. ASSUMED he followed it: measure
CARD_CUT_TOL = 1.0         # how far off the printed outline a scissor cut may be, each way
CARD_T_NOM = 2.0           # PLACEHOLDER: thickness of HIS stiff card. Measure it with a ruler.
CARD_T_MAX = 3.0           # the pocket takes anything up to this
RIB_H = 3.0                # air behind the card
RIB_XS = (-34.0, -9.0, 9.0, 34.0)       # between the diode rows, never behind a diode; the outer two back the clips
LEDGE_T = 3.0
LEDGE_LIP = 3.0            # how much of the card's bottom edge the ledge's lip covers
LEDGE_XS = ((-36.0, 16.0), (36.0, 44.0))   # two pieces: the gap between them is the capacitor
CARD_LIFT = 5.0            # the card goes this far up under the clips before it drops into the ledge
STOP_T = 2.0               # side stops, low on both edges, below where the motor leads cross
STOP_Y = (0.0, 40.0)       # measured up from the card's bottom edge
CLIP_LID = (24.5, 36.0)    # where each clip meets the lid, |x|
CLIP_POST_W = 4.0          # corner post beside the card, the clip's other anchor
CLIP_POST_DY = (19.5, 8.0)  # the post's bottom and top, below the inside of the lid
CLIP_T = 2.4               # a flat printed bridge from the lid to the post. COUPON C2
CLIP_PLAY = 0.5            # above the thickest card
CLIP_MIN_AREA = 60.0       # mm2 of the smallest allowed card under each clip
GLOW_SKIN = 0.8            # two 0.4 mm lines: the bus light shows through, no hole. COUPON C2
GLOW_X = 12.0              # width of the thin spot
GLOW_Z = 11.0

# ============================================================ THE MODULE, ALL PLACEHOLDERS (Amazon B0DF4KSN95, not arrived)
USB_SIDE = +1              # +1: socket on the +X side (left, seen from behind; the table side in step 9).
                           # For the other side set -1 and run again. Do NOT mirror in the slicer:
                           # the card's pocket is not symmetric. The shell fixes the SIDE only; which
                           # way the tester's screen faces is decided by the sled, printed later.
MOD_L = 45.0               # PLACEHOLDER: board length, socket end to far end. Measure.
MOD_W = 22.0               # PLACEHOLDER: board width. Measure. The seat takes up to SEAT_W.
MOD_PCB_T = 1.6            # PLACEHOLDER: board thickness
MOD_H = 12.0               # PLACEHOLDER: tallest part above the board
MOD_UNDER = 2.0            # PLACEHOLDER: tallest part UNDER the board; the board stands on two ribs this high
USB_W, USB_H, USB_L = 13.2, 7.0, 14.0   # USB-A socket shell: the one standard size on the module
USB_Y_OFF = 0.0            # PLACEHOLDER: socket centre off the board's centre line. Measure.
USB_Z_OFF = 0.0            # PLACEHOLDER: socket underside above the board's top face. Measure.
TESTER = (62.0, 24.0, 12.0)             # PLACEHOLDER: USB tester body, long x wide x thick
PLUG_W, PLUG_T = 12.0, 4.5             # USB-A plug shell, the standard section
PLUG_LEN = 12.0            # ASSUMED (from memory, not a datasheet): metal plug showing beyond the tester's body. Measure.
USB_SEAT = 10.3            # ASSUMED (from memory): how far a USB-A plug goes into its socket. The pen-line test settles it.

# what the SHELL fixes for good
SEAT_W = 36.0              # widest board the sled's seat can take
SLED_Y0 = 26.0             # the sled's bottom edge, above the table
SLED_W = 44.0              # the sled's whole height on the panel
SLED_DROP = 4.0            # the sled goes on this far above its seat, then slides down
SLED_SIDE = 1.5            # ... and this far inboard of its seat, then into the corner
WIN_H = 25.0               # plain window in the side wall, across the bridge
PLUG_HEAD = 1.0            # the window's top edge is this far above a plugged-in plug: the plug is the sled's lock
WIN_Z = (1.0, 23.0)        # above the inside of the back panel
WIN_RECESS = 1.0           # round the window the side wall is thinned this much from the inside:
WIN_WALL = T - WIN_RECESS  # ... 1.0 mm left, so the socket's mouth is 1.3 mm from the outside, not 2.3
RAIL_T = 4.0               # rail under the sled
RAIL_H = 4.2
RAIL_LIP = 3.0             # 45 degree lip over the sled's keel
RAIL_FIT = 0.4             # play between keel and lip. COUPONS C3 and C4
RAIL_X0 = 8.0              # the rail's inboard end
KEY_X = (45.0, 55.0)       # gap in the rail for the sled's key: takes the push of plugging in
KEY_DEPTH = 3.5
KEY_FIT = 0.3

# the sled itself (reprinted once the module is measured)
SLED_FLOOR = 2.0
SLED_NOSE_GAP = 0.3        # between the sled's face plate and the thinned side wall
FACE_T = 2.1
FACE_H = 25.0
KEEL_FLAT = 1.0
KEEL_BAND = RAIL_LIP + 0.4  # the strip along the sled's bottom edge that belongs to the rail's lip
RAIL_LIP_Z0 = KEEL_FLAT + RAIL_FIT
TRAY_WALL = 1.6
PCB_FIT = 0.4              # per side
PCB_LIFT = 0.3             # play under the two short lips at the socket end
NOSE_LIP_L = 5.0           # those lips are only this long, so the board can tilt in over the tail stop
TAIL_STOP = 0.8            # the tail stop stands this far ABOVE the board's top face
COMB_L = 3.0               # the tail stop is a comb of three posts: the two output wires lie in its slots
COMB_SLOT = 4.2
PAD_DY = 4.5               # PLACEHOLDER: the module's two input pads, each side of its centre line
TAIL_LAND = 8.0            # floor beyond the comb: tape the two wires down here
USB_HOLE_FIT = 0.8         # per side, round the socket shell

# ============================================================ CLAMPS, WIRES, PRINTER
G_OPEN = 100.0             # 4 inch G-clamp, as cad/assembly_steps_export.py draws it for step 9:
G_FRAME_W = 12.0           # frame section, across
G_FRAME_T = 14.0           # PLACEHOLDER: D, how high HIS clamp's frame stands above the face that presses. Copied from the
                           # step 9 illustration, NEVER measured (a cast clamp "with reinforced shoulders": 20 or more is
                           # likely). The tester hangs straight above this arm. Measure, and put the number here.
TESTER_ARM_AIR = 5.0       # least air between the tester and the clamp's arm under it
G_SPINE_BACK = 12.0        # spine this far behind the table edge
G_REACH = 58.0             # arm tip this far past the spine's front
G_PAD_IN = 10.0            # pad centre this far back from the arm tip
G_PAD_R = 11.0
G_JAW_W = 22.0             # PLACEHOLDER: widest part of HIS clamp at the jaw (Blue Spot 4 inch, no drawing found). Measure.
TABLE_T = 28.0             # as the step pictures draw it
CLAMP_X = (HW + FOOT_X1) / 2                              # 85: middle of each foot

LEAD_LEN = 300.0           # PLACEHOLDER: motor lead length (maker's page says 30 cm, the twin's says 500). Measure.
LEAD_D = 1.8               # PLACEHOLDER: one motor lead over its insulation
LEAD_BUNDLE_D = 2.42 * LEAD_D          # four leads side by side, as one round bundle
LEAD_EXIT = (-6.0, MOTOR_TOP, MOTOR_BACK + 8.0)           # PLACEHOLDER: where the four leads leave the motor (wires up, step 3)
COIL_R, COIL_PITCH = 11.0, 4.4      # the spare, looped round two fingers, laid on the BACK half of the motor's top and taped
COIL_CHOICES = (0.625, 1.625)       # loops the drawing can show: n + 0.625. Which one is NOT typed: fit_coil() picks the
                                    # most that the lead length allows in the coil pose and sets COIL_TURNS
COIL_RISE = 10.0           # the leads come up out of the motor in a bend this big
LEAD_OVER = 6.0            # the leads are drawn this far off the card (over the MINUS rail's solder lumps)
LEAD_EDGE_Y1 = 165.4       # lead 1 crosses the card's edge here, beside lead 2: the clip owns the corner above
OUT_WIRE_LEN = 170.0       # cut the two output wires THIS long. ELECTRONICS.md says about 10 cm: too short here
OUT_WIRE_D = 3.4           # three jumper wires twisted
TAIL_D = 1.6               # one thin jumper: the meter tails
TAIL_Y = 128.0             # where each tail's 1 k resistor leaves its rail
MIN_BEND = 8.0             # smallest bend radius drawn for a motor lead
OUT_BEND = 10.0            # ... and for a three-jumper output wire
TAIL_BEND = 5.0            # ... and for a thin meter tail
WIRE_AIR = 1.0             # least air between two wires that are not one bundle

NOZZLE = 0.4
MIN_FEATURE = 2 * NOZZLE   # nothing thinner than two lines
MAX_BRIDGE = 30.0
MIN_AIR = 1.0              # least air between the shell and anything of the machine, locators aside
DIODE_AIR = 5.0            # least air between a diode and any plastic
VENT_MIN = 1250.0          # mm2, each of inlet and outlet (judge's figure for about 6 W inside)
POWER_W = 6.0              # motor copper about 2, diodes 1.2 to 1.7, module 1 to 2.5: an ESTIMATE
NOTE = "note"              # a line that says something no script can test

# ---- derived
CARD_Y0 = SLED_Y0 + SLED_W + SLED_DROP + 1.0 + LEDGE_T    # 78: card's bottom edge
CARD_TOP = CARD_Y0 + CARD_H                               # 189
LID_IN = CARD_TOP + CARD_LIFT                             # 194: inside of the lid
Y_TOP = LID_IN + T                                        # 196
CARD_BACK = IN_Z + RIB_H                                  # -96
CLIP_Z0 = CARD_BACK + CARD_T_MAX + CLIP_PLAY              # underside of the two clips
LEDGE_Z0 = CARD_BACK + CARD_T_MAX + 0.3
SLED_YC = SLED_Y0 + KEEL_BAND + TRAY_WALL + PCB_FIT + SEAT_W / 2      # 49.4: the socket's centre line
WIN_Y = (SLED_YC + PLUG_W / 2 + PLUG_HEAD - WIN_H, SLED_YC + PLUG_W / 2 + PLUG_HEAD)   # 31.4 to 56.4
LIFT_ON = PEG_LEN                                         # the shell rides on its peg tips until it drops
LIFT_MAX = BOSS_UNDER - BAFFLE_Y1                         # 6.4: lifted more, the baffle tops meet the top pin bosses
LIE_GAP = BASE_BACK - MOTOR_BACK    # -31. Fitting pose: the shell on its back, pushed FORWARD until its foot end
                           # meets the motor's back. The books stand against the base's back edge; the shell overhangs them
LIE_BOX = 150.0            # ... on a stack of books this high, so 30 cm motor leads reach the card with slack
LIE_BOX_RANGE = (120.0, 170.0)      # a real stack is never exactly 15 cm: the reach is tested at both ends of this too
TIE_X = -39.5              # the four motor leads are tied to the card along this line (picture cover_01, the blue twist)
LEAD_ENDS = 15.0           # lead used up at its two ends: 5 for the bend out of the motor, 10 for the wrap at the joint
LEAD_SPARE_MIN = 50.0      # least spare lead in the fitting pose (holding the card a hand above the pocket takes 10 to 20)
COIL_BACK = Z_FRONT - MOTOR_BACK    # 53. Coil pose: the shell UPRIGHT, short of home by this much, so its front edge is LEVEL
                           # WITH THE MOTOR'S BACK (he can see that, no ruler). Its front stands on the base, a thin book
                           # under its back edge. The ONLY pose in which the spare lead can be looped: see the checks
COIL_KEEP = 20.0           # lead left over in the coil pose, at least


# ============================================================ helpers
def _box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _prism_xy(pts, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)


def _prism_yz(pts, x0, x1):
    """pts are (Y, Z); extruded along X."""
    x0, x1 = sorted((x0, x1))
    return cq.Workplane("YZ").workplane(offset=x0).polyline(pts).close().extrude(x1 - x0)


def _prism_xz(pts, y0, y1):
    """pts are (X, Z); extruded along Y."""
    y0, y1 = sorted((y0, y1))
    return cq.Workplane("XZ").workplane(offset=-y1).polyline(pts).close().extrude(y1 - y0)


def _cyl_z(x, y, r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def _cyl_x(y, z, r, x0, x1):
    x0, x1 = sorted((x0, x1))
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(r).extrude(x1 - x0)


def _cyl_y(x, z, r, y0, y1):
    y0, y1 = sorted((y0, y1))
    return cq.Workplane("XZ").workplane(offset=-y1).center(x, z).circle(r).extrude(y1 - y0)


def _profile(hw, y_top, r):
    """Closed XY outline: straight sides up from the base, two rounded top corners."""
    return (cq.Workplane("XY").moveTo(-hw, BASE_TOP).lineTo(-hw, y_top - r)
            .radiusArc((-hw + r, y_top), r).lineTo(hw - r, y_top)
            .radiusArc((hw, y_top - r), r).lineTo(hw, BASE_TOP).close())


def _vol(a, b):
    """Overlap volume, solid by solid (one boolean on a many-body compound can come back null)."""
    total = 0.0
    for sa in a.solids().vals():
        ba = sa.BoundingBox()
        for sb in b.solids().vals():
            bb = sb.BoundingBox()
            if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
                    or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
                continue
            try:
                total += sum(s.Volume() for s in sa.intersect(sb).Solids())
            except ValueError:
                pass                                   # null result = no overlap
    return total


def _dist(a, b):
    """Least distance between two workplane objects (exact, OCC)."""
    return min(sa.distance(sb) for sa in a.solids().vals() for sb in b.solids().vals())


def _many(solids):
    return cq.Workplane("XY").newObject([cq.Compound.makeCompound([s.val() for s in solids])])


# ============================================================ the shell
def _clip_poly(sx):
    """One card clip, seen from behind: a flat plate bridging from the lid to a post beside the
    card's top corner. Returns its outline and the post's box (x0, x1, y0, y1)."""
    half = CARD_W / 2 + CARD_CUT_TOL
    y0, y1 = LID_IN - CLIP_POST_DY[0], LID_IN - CLIP_POST_DY[1]
    poly = [(sx * CLIP_LID[0], LID_IN + 0.5), (sx * CLIP_LID[1], LID_IN + 0.5), (sx * (half + CLIP_POST_W), y1),
            (sx * (half + CLIP_POST_W), y0), (sx * half, y0)]
    return poly, (half, half + CLIP_POST_W, y0, y1)


def _peg_outline(bx=0.0, bz=0.0):
    hx, hz = PEG_X / 2, PEG_Z / 2
    return [(bx, bz - hz), (bx + hx, bz - hz + hx), (bx + hx, bz + hz - 0.6), (bx + hx - 0.6, bz + hz),
            (bx - hx + 0.6, bz + hz), (bx - hx, bz + hz - 0.6), (bx - hx, bz - hz + hx)]


def pegs():
    """The two pegs alone (also used for the travel test)."""
    out = []
    for bx, bz in PEG_HOLES:
        out.append(cq.Workplane("XZ").workplane(offset=-(BASE_TOP + 0.5)).polyline(_peg_outline(bx, bz)).close()
                   .extrude(PEG_LEN + 0.5, taper=PEG_TAPER))
    return out


def peg_travel(hole_d, depth):
    """Free travel (back, forward) of the peg's section `depth` mm below the base's top face in a
    round hole of that diameter: the real diamond outline, not half the difference of two sizes."""
    from shapely import affinity
    from shapely.geometry import Point, Polygon
    sec = Polygon(_peg_outline()).buffer(-(depth + 0.5) * math.tan(math.radians(PEG_TAPER)), join_style=2)
    hole = Point(0, 0).buffer(hole_d / 2, 256)
    if not hole.contains(sec):
        return None

    def lim(sign):
        s = 0.0
        while s < 3.0 and hole.contains(affinity.translate(sec, 0, sign * (s + 0.01))):
            s += 0.01
        return s
    return lim(-1), lim(+1)


def shell(locators=True, side=None):
    """The one big print. Prints back panel down, no support. locators=False leaves the pegs,
    forks and wall stops off, for the clearance check."""
    S = USB_SIDE if side is None else side
    outer = _profile(HW, Y_TOP, CORNER_R).extrude(Z_FRONT - Z_BACK).translate((0, 0, Z_BACK))
    outer = outer.faces("<Z").edges().chamfer(BED_CHAMFER)
    inner = _profile(IN_HW, LID_IN, CORNER_R - T).extrude(Z_FRONT - IN_Z + 1).translate((0, 0, IN_Z))
    s = outer.cut(inner)
    # warm-air slot: the lid stops short of the wall (the rounded corners run on, for stiffness)
    flat = HW - CORNER_R
    s = s.cut(_box(-flat, flat, LID_IN - 1, Y_TOP + 1, WALL_BACK - TOP_GAP, Z_FRONT + 1))

    for sx in (-1, 1):
        # feet: the G-clamps press here
        s = s.union(_box(sx * (HW - 0.5), sx * FOOT_X1, BASE_TOP, BASE_TOP + FOOT_T, Z_BACK, FOOT_Z1))
        s = s.union(_box(sx * (HW - 0.5), sx * FOOT_X_WIDE, BASE_TOP, BASE_TOP + FOOT_T, Z_BACK, FOOT_WIDE_Z1))
        y0 = BASE_TOP + FOOT_T
        tri = [(sx * (HW - 0.5), y0 - 0.5), (sx * (HW + FOOT_TIE), y0 - 0.5), (sx * (HW + FOOT_TIE), y0),
               (sx * HW, y0 + FOOT_TIE), (sx * (HW - 0.5), y0 + FOOT_TIE)]
        tip = [(sx * (HW - 0.5), y0 - 0.5), (sx * (HW + 0.2), y0 - 0.5), (sx * (HW + 0.2), y0), (sx * HW, y0 + 0.2),
               (sx * (HW - 0.5), y0 + 0.2)]
        s = s.union(_prism_xy(tri, FOOT_TIE_Z0, FOOT_Z1))
        ramp = (cq.Workplane("XY").workplane(offset=FOOT_TIE_Z0 - FOOT_TIE).polyline(tip).close()
                .workplane(offset=FOOT_TIE).polyline(tri).close().loft(combine=True))
        s = s.union(ramp)
        # baffle: a 45 degree slab from the side wall in to the wall's solid column. It ends in a
        # flat, not a feather, and a wedge backs its root (it is the natural handhold)
        xw = IN_HW + 0.5
        z_top = WALL_BACK - BAFFLE_SLIT
        zw = z_top - (xw - BAFFLE_X_TIP - BAFFLE_FLAT)
        slab = [(sx * xw, zw - BAFFLE_T), (sx * xw, zw), (sx * (BAFFLE_X_TIP + BAFFLE_FLAT), z_top),
                (sx * BAFFLE_X_TIP, z_top), (sx * BAFFLE_X_TIP, z_top - BAFFLE_T + BAFFLE_FLAT)]
        s = s.union(_prism_xz(slab, BAFFLE_Y0, BAFFLE_Y1))
        d = BAFFLE_ROOT + 0.5
        wedge = [(sx * xw, zw - BAFFLE_T - 1.5 * BAFFLE_ROOT), (sx * xw, zw - BAFFLE_T + 0.2), (sx * (xw - d), zw - BAFFLE_T + d)]
        s = s.union(_prism_xz(wedge, BAFFLE_Y0, BAFFLE_Y1))
        # card: low side stop, corner post and the clip that bridges from the lid to the post
        half = CARD_W / 2 + CARD_CUT_TOL
        s = s.union(_box(sx * half, sx * (half + STOP_T), CARD_Y0 + STOP_Y[0], CARD_Y0 + STOP_Y[1], IN_Z - 0.5, CLIP_Z0 + 0.5))
        poly, (px0, px1, y_lo, y_hi) = _clip_poly(sx)
        s = s.union(_box(sx * px0, sx * px1, y_lo, y_hi, IN_Z - 0.5, CLIP_Z0 + CLIP_T))
        s = s.union(_prism_xy(poly, CLIP_Z0, CLIP_Z0 + CLIP_T))

    if locators:
        for peg in pegs():
            s = s.union(peg)
        for gx, _ in TALL_GUSSETS:
            for side_ in (-1, 1):
                a = gx + side_ * (pl.GUSSET_T / 2 + FORK_CLEAR)          # the face toward the gusset
                b = a + side_ * FORK_T
                rib = [(a, IN_Z - 0.5), (b, IN_Z - 0.5), (b, FORK_Z1), (a + side_ * 1.0, FORK_Z1), (a, FORK_Z1 - 1.0)]
                s = s.union(_prism_xz(rib, BASE_TOP, FORK_H))
        for sx in (-1, 1):                                 # wall stops: four small nubs on the side walls' front edges
            for y0, y1 in STOP_BUMP_Y:
                s = s.union(_box(sx * IN_HW, sx * HW, y0, y1, Z_FRONT - 0.5, WALL_BACK - WALL_STOP_GAP))

    # card: ribs behind it, ledge under it with a 45 degree lip
    for x in RIB_XS:
        s = s.union(_box(x - 1, x + 1, CARD_Y0, CARD_TOP, IN_Z - 0.5, CARD_BACK))
    ledge = [(CARD_Y0 - LEDGE_T, IN_Z - 0.5), (CARD_Y0, IN_Z - 0.5), (CARD_Y0, LEDGE_Z0),
             (CARD_Y0 + LEDGE_LIP, LEDGE_Z0 + LEDGE_LIP), (CARD_Y0 - LEDGE_T, LEDGE_Z0 + LEDGE_LIP)]
    for x0, x1 in LEDGE_XS:
        s = s.union(_prism_yz(ledge, x0, x1))
    # the bus light glows through a thin spot in the lid, straight above the LED
    gx = led_x()
    gz = CARD_BACK + (CARD_T_NOM + CARD_T_MAX) / 2 + 2.6
    s = s.cut(_box(gx - GLOW_X / 2, gx + GLOW_X / 2, LID_IN - 0.5, Y_TOP - GLOW_SKIN, gz - GLOW_Z / 2, gz + GLOW_Z / 2))

    # module side: the rail with its lip and key gap, the plain window, and the thinned wall round it
    top = RAIL_H
    for x0, x1 in ((RAIL_X0, KEY_X[0] - KEY_FIT), (KEY_X[1] + KEY_FIT, IN_HW + 0.5)):
        s = s.union(_box(S * x0, S * x1, SLED_Y0 - RAIL_T, SLED_Y0, IN_Z - 0.5, IN_Z + top))
        lip = [(SLED_Y0 - 0.5, IN_Z + RAIL_LIP_Z0 - 0.5), (SLED_Y0, IN_Z + RAIL_LIP_Z0),
               (SLED_Y0 + top - RAIL_LIP_Z0, IN_Z + top), (SLED_Y0 - 0.5, IN_Z + top)]
        s = s.union(_prism_yz(lip, S * x0, S * x1))
    s = s.cut(_box(S * (IN_HW - 1), S * (HW + 1), WIN_Y[0], WIN_Y[1], IN_Z + WIN_Z[0], IN_Z + WIN_Z[1]))
    ry0, ry1 = recess_y()
    zr = IN_Z + FACE_H + 0.6
    s = s.cut(_box(S * (IN_HW - 0.01), S * (IN_HW + WIN_RECESS), ry0, ry1, IN_Z, zr))
    roof = [(S * (IN_HW - 0.01), zr - 0.01), (S * (IN_HW + WIN_RECESS + 0.01), zr - 0.01), (S * (IN_HW - 0.01), zr + WIN_RECESS + 0.01)]
    s = s.cut(_prism_xz(roof, ry0, ry1))
    return s


def recess_y():
    """The thinned patch of side wall: the sled's face plate, where it sits and where it goes on."""
    return SLED_Y0 + KEEL_BAND - 0.6, SLED_Y0 + SLED_W + SLED_DROP + 0.6


# ============================================================ the card and what is on it (dummies, NOT printed)
def tpl(u, v):
    """Template millimetres (u right, v down, as printed) to model X, Y. Card on end, capacitor end
    down, parts facing the motor: template right is DOWN, template down is toward -X."""
    return (-(v - (TPL_V0 + TPL_V1) / 2), CARD_TOP - (u - TPL_U0))


def untpl(x, y):
    """Model X, Y on the card back to template u, v."""
    return (CARD_TOP - y + TPL_U0, (TPL_V0 + TPL_V1) / 2 - x)


def led_x():
    return tpl(0, 47.0)[0]                                 # Ladder.light(): the LED sits at template y = 47


def _tbox(u0, u1, v0, v1, h, t, z0=0.0, lift=0.0):
    (xa, ya), (xb, yb) = tpl(u0, v0), tpl(u1, v1)
    zf = CARD_BACK + t
    return _box(xa, xb, ya + lift, yb + lift, zf + z0, zf + z0 + h)


def card_dummy(t=CARD_T_NOM, lift=0.0, wide=0.0, tall=0.0):
    """wide, tall: cut that much too big (or, negative, too small). It always stands on the ledge."""
    return _box(-CARD_W / 2 - wide / 2, CARD_W / 2 + wide / 2, CARD_Y0 + lift, CARD_TOP + lift + tall, CARD_BACK, CARD_BACK + t)


def card_as_told_dummy(on_end=True, t=CARD_T_NOM):
    """The card ELECTRONICS.md step 0 tells him to cut, about 130 x 100, standing on the ledge."""
    w, h = (CARD_AS_TOLD[1], CARD_AS_TOLD[0]) if on_end else CARD_AS_TOLD
    return _box(-w / 2, w / 2, CARD_Y0, CARD_Y0 + h, CARD_BACK, CARD_BACK + t)


def diodes_dummy(t=CARD_T_NOM, lift=0.0):
    """Eight DO-201AD bodies, 5.3 mm round, where Ladder.legs() draws them."""
    out = []
    for k, c in enumerate(TPL_COL):
        for cu, (v0, v1) in ((c, (6.0, 15.0)), (c + TPL_OFF, (45.0, 54.0))):
            (x0, y), (x1, _) = tpl(cu, v0), tpl(cu, v1)
            out.append(_cyl_x(y + lift, CARD_BACK + t + 2.65, 2.65, x0, x1))
    return _many(out)


def card_parts_dummy(t=CARD_T_NOM, lift=0.0):
    """Everything else that stands on the card: rails and joints, capacitor, light, wire stubs."""
    b = lambda *a, **k: _tbox(*a, t=t, lift=lift, **k)
    out = [b(-0.7, 55.7, -2.4, 0.9, 3.0), b(0.9, 57.3, 59.1, 62.4, 3.0)]            # PLUS and MINUS rails with their lumps
    for c in TPL_COL:
        out += [b(c - 0.7, c + 0.7, 0.0, 40.0, 1.4), b(c + TPL_OFF - 0.7, c + TPL_OFF + 0.7, 20.0, 61.5, 1.4),
                b(c - 0.4, c + 2.0, 25.7, 30.3, 4.0), b(c - 0.4, c + 2.0, 34.3, 38.9, 4.5)]   # J joint, motor-wire wrap
    (x0, y0), (x1, y1) = tpl(63.5, 2.8), tpl(89.0, 2.8)
    out.append(_cyl_y(x0, CARD_BACK + t + 6.5, 6.5, y0 + lift, y1 + lift))               # C1: 13 x 25.5, lying down
    out += [b(46.5, 64.0, -0.3, 0.7, 1.2), b(59.9, 64.0, 4.9, 5.9, 1.2), b(59.3, 62.6, 5.9, 61.5, 2.6)]   # its legs and the link
    out += [b(-16.8, -8.6, 44.4, 49.6, 5.2), b(-9.25, -6.75, 6.5, 13.0, 2.5), b(-9.25, -6.75, 23.5, 30.0, 2.5),
            b(-8.4, -7.6, 1.4, 58.6, 1.0), b(-8.4, 7.5, 0.9, 1.9, 1.0), b(-8.4, 7.5, 58.1, 59.1, 1.0)]    # LED, two 1 k, their wire
    return _many(out)


def led_dummy(t=CARD_T_NOM):
    return _tbox(-16.8, -8.6, 44.4, 49.6, 5.2, t)


# ============================================================ the sled and the module
def _sled_x():
    """Along X for USB_SIDE = +1: nose face, inside of the face plate, board tail, front of the
    comb, the sled's own tail."""
    nose = IN_HW + WIN_RECESS - SLED_NOSE_GAP
    plate_in = nose - FACE_T
    tail_pcb = plate_in - MOD_L
    comb0 = tail_pcb - PCB_FIT - COMB_L
    return nose, plate_in, tail_pcb, comb0, comb0 - TAIL_LAND


def _pcb_z():
    return IN_Z + SLED_FLOOR + MOD_UNDER


def _mirror(part, side):
    return part if side > 0 else part.mirror("YZ")


def sled(side=None, drop=0.0, shift=0.0):
    """Module sled, in its seat on the panel (drop > 0: that far above its seat; shift > 0: that
    far inboard of it). Prints floor down. EVERY module number in here is a placeholder."""
    S = USB_SIDE if side is None else side
    nose, plate_in, tail_pcb, comb0, tail = _sled_x()
    y0, y1, z = SLED_Y0, SLED_Y0 + SLED_W, IN_Z
    yb = y0 + KEEL_BAND                                   # floor, tray and face plate start above the lip's strip
    s = _box(tail, nose, yb, y1, z, z + SLED_FLOOR)
    keel = [(y0, z), (y0, z + KEEL_FLAT), (y0 + RAIL_LIP, z + KEEL_FLAT + RAIL_LIP), (y0 + 4.5, z + KEEL_FLAT + RAIL_LIP),
            (y0 + 4.5, z)]
    s = s.union(_prism_yz(keel, tail, IN_HW - SLED_NOSE_GAP))             # the keel stops at the full-thickness wall
    kz = KEEL_FLAT + RAIL_LIP                              # the key: chamfered like the keel, so it passes under the rail's lip on the way in
    key = [(y0 - KEY_DEPTH, z), (y0 - KEY_DEPTH, z + KEEL_FLAT + 0.5), (y0 - KEY_DEPTH + RAIL_LIP - 0.5, z + kz), (y0 + 1.0, z + kz), (y0 + 1.0, z)]
    s = s.union(_prism_yz(key, KEY_X[0], KEY_X[1]))
    s = s.union(_box(plate_in, nose, yb, y1, z, z + FACE_H))                                            # face plate
    pcb_z = _pcb_z()
    yc = SLED_YC - USB_Y_OFF                              # the BOARD's centre line: the socket stays on SLED_YC
    top_z = pcb_z + MOD_PCB_T
    lip_z = top_z + PCB_LIFT
    half = MOD_W / 2 + PCB_FIT
    for sy in (-1, 1):                                    # tray walls; a short 45 degree lip over the board at the socket end only
        yi = yc + sy * half
        yo = yi + sy * TRAY_WALL
        s = s.union(_box(comb0, plate_in + 0.5, yi, yo, z, lip_z + 1.6))
        lip = [(yi + sy * 0.1, lip_z - 0.1), (yi - sy * 1.0, lip_z + 1.0), (yi - sy * 1.0, lip_z + 1.6), (yi + sy * 0.1, lip_z + 1.6)]
        s = s.union(_prism_yz(lip, plate_in - NOSE_LIP_L, plate_in + 0.5))
    for x in (tail_pcb + 6.0, plate_in - USB_L - 4.0):   # two ribs the board stands on, clear of the socket's solder tabs
        s = s.union(_box(x - 1, x + 1, yc - half - 0.2, yc + half + 0.2, z, pcb_z))
    # tail stop = wire comb: three posts taller than the board; the two output wires lie in the slots
    for ya, yb_ in comb_posts(yc):
        s = s.union(_box(comb0, comb0 + COMB_L, ya, yb_, z, top_z + TAIL_STOP))
    hy, hz = SLED_YC, top_z + USB_Z_OFF
    s = s.cut(_box(plate_in - 1, nose + 1, hy - USB_W / 2 - USB_HOLE_FIT, hy + USB_W / 2 + USB_HOLE_FIT,
                   hz - 0.3, hz + USB_H + USB_HOLE_FIT))
    return _mirror(s, S).translate((-S * shift, drop, 0))


def comb_posts(yc):
    half = MOD_W / 2 + PCB_FIT + 0.2
    a, b = PAD_DY - COMB_SLOT / 2, PAD_DY + COMB_SLOT / 2
    return [(yc - half, yc - b), (yc - a, yc + a), (yc + b, yc + half)]


def module_dummy(side=None, drop=0.0):
    S = USB_SIDE if side is None else side
    nose, plate_in, tail_pcb, _, _ = _sled_x()
    pcb_z = _pcb_z()
    yc = SLED_YC - USB_Y_OFF
    pcb = _box(tail_pcb, plate_in, yc - MOD_W / 2, yc + MOD_W / 2, pcb_z, pcb_z + MOD_PCB_T)
    hy, hz = SLED_YC, pcb_z + MOD_PCB_T + USB_Z_OFF
    sock = _box(nose - USB_L, nose, hy - USB_W / 2, hy + USB_W / 2, hz, hz + USB_H)
    lump = _box(tail_pcb + 8, plate_in - USB_L - 3, yc - MOD_W / 2 + 3, yc + MOD_W / 2 - 3, pcb_z + MOD_PCB_T, pcb_z + MOD_PCB_T + MOD_H)
    return {k: _mirror(v, S).translate((0, drop, 0)) for k, v in (("pcb", pcb), ("socket", sock), ("parts", lump))}


def _usb_centre():
    return SLED_YC, _pcb_z() + MOD_PCB_T + USB_Z_OFF + USB_H / 2


def tester_face_x():
    """Where the tester's body ends up: its plug bottoms in the socket, or its body meets the wall first."""
    nose = _sled_x()[0]
    return max(HW, nose - USB_SEAT + PLUG_LEN)


def tester_dummy(side=None, drop=0.0):
    """A real-length plug (PLUG_LEN), not one drawn long enough to hide a standoff."""
    S = USB_SIDE if side is None else side
    yc, zc = _usb_centre()
    x0 = tester_face_x()
    body = _box(x0, x0 + TESTER[0], yc - TESTER[1] / 2, yc + TESTER[1] / 2, zc - TESTER[2] / 2, zc + TESTER[2] / 2)
    plug = _box(x0 - PLUG_LEN, x0 + 1, yc - PLUG_W / 2, yc + PLUG_W / 2, zc - PLUG_T / 2, zc + PLUG_T / 2)
    return {k: _mirror(v, S).translate((0, drop, 0)) for k, v in (("body", body), ("plug", plug))}


# ============================================================ clamps (the step-9 ghost, moved onto the feet)
def clamp_dummy(sx, jaw=None, pad_z=None):
    """cad/assembly_steps_export.py's 4 inch G-clamp, same numbers, with two changes: it stands on
    the cover's foot, and its jaw is drawn as wide as a real one (G_JAW_W, a placeholder).
    pad_z moves the whole clamp so its pad's centre is at that Z."""
    jaw = G_JAW_W if jaw is None else jaw
    x, w, t = sx * CLAMP_X, G_FRAME_W, G_FRAME_T
    top = BASE_TOP + FOOT_T
    low = top - G_OPEN
    z_sp = BASE_BACK - G_SPINE_BACK
    z_tip = z_sp + G_REACH
    zs = z_tip - G_PAD_IN
    c = _box(x - w / 2, x + w / 2, top, top + t, z_sp - t, z_tip)
    c = c.union(_box(x - w / 2, x + w / 2, low - t, top + t, z_sp - t, z_sp))
    c = c.union(_box(x - w / 2, x + w / 2, low - t, low, z_sp - t, z_tip))
    c = c.union(_box(x - jaw / 2, x + jaw / 2, top, top + t, zs - G_PAD_R, z_tip))        # the jaw
    c = c.union(_cyl_y(x, zs, 5.0, low - t - 34.0, -TABLE_T - 4.0))
    c = c.union(_cyl_y(x, zs, G_PAD_R, -TABLE_T - 5.0, -TABLE_T))
    c = c.union(_cyl_x(low - t - 28.0, zs, 2.6, x - 32.0, x + 32.0))
    return c if pad_z is None else c.translate((0, 0, pad_z - zs))


def jaw_footprint(sx, jaw=None):
    """Where the jaw presses: x0, x1, z0, z1."""
    jaw = G_JAW_W if jaw is None else jaw
    zs = BASE_BACK - G_SPINE_BACK + G_REACH - G_PAD_IN
    return sx * CLAMP_X - jaw / 2, sx * CLAMP_X + jaw / 2, zs - G_PAD_R, zs + G_PAD_R


def rear_hardware_dummy():
    """Washer and nyloc behind each pin boss, out to the bolt's tip: a 16 mm cylinder."""
    return _many([_cyl_z(x, y, 8.0, PIN_TIP_Z, WALL_BACK - pl.PIN_BOSS_H + 0.01) for x, y in BOSSES])


# ============================================================ wires (dummies: for the pictures and the room check)
def _round_path(pts, r, step=1.0, arc_deg=20.0):
    """A polyline with every corner replaced by an arc of radius r, tangent to both legs: the
    way a hand lays a wire. Returns (fine, coarse): samples about `step` apart for lengths and
    bends, and a short list (leg ends, arcs in arc_deg pieces) for the solid."""
    p = [np.array(q, float) for q in pts]
    fine, coarse = [p[0]], [p[0]]
    start, prev_t = p[0], 0.0

    def line(a, b):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for k in range(1, n + 1):
            fine.append(a + (b - a) * k / n)

    for i in range(1, len(p) - 1):
        a, b, c = p[i - 1], p[i], p[i + 1]
        lu, lv = np.linalg.norm(b - a), np.linalg.norm(c - b)
        u, v = (b - a) / lu, (c - b) / lv
        cosang = float(np.clip(u @ v, -1.0, 1.0))
        phi = math.acos(cosang)
        if phi < 1e-3:
            continue
        t = r * math.tan(phi / 2)
        if prev_t + t > lu + 1e-6:
            raise ValueError(f"no room for a {r} mm bend at corner {i}: leg {lu:.1f}, needs {prev_t + t:.1f}")
        p0 = b - u * t
        nrm = v - u * cosang
        nrm /= np.linalg.norm(nrm)
        centre = p0 + nrm * r
        line(start, p0)
        coarse.append(p0)
        for th in np.linspace(0, phi, max(2, int(math.ceil(phi * r / step))) + 1)[1:]:
            fine.append(centre + r * (-nrm * math.cos(th) + u * math.sin(th)))
        for th in np.linspace(0, phi, max(1, int(math.ceil(math.degrees(phi) / arc_deg))) + 1)[1:]:
            coarse.append(centre + r * (-nrm * math.cos(th) + u * math.sin(th)))
        start, prev_t = b + v * t, t
    if prev_t > np.linalg.norm(p[-1] - p[-2]) + 1e-6:
        raise ValueError(f"no room for a {r} mm bend before the last point")
    line(start, p[-1])
    coarse.append(p[-1])
    return np.array(fine), np.array(coarse)


def _length(path):
    return float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())


def _min_bend(path, span=3):
    """Smallest radius of the circle through three samples `span` apart (samples are about 1 mm)."""
    best = 1e9
    for i in range(span, len(path) - span):
        a, b, c = path[i - span], path[i], path[i + span]
        la, lb, lc = np.linalg.norm(b - c), np.linalg.norm(a - c), np.linalg.norm(a - b)
        area = np.linalg.norm(np.cross(b - a, c - a)) / 2
        if area > 1e-6:
            best = min(best, la * lb * lc / (4 * area))
    return best


def _trim(path, head=0.0, tail=0.0):
    """Drop that many mm from each end (where a wire is soldered ONTO the part it is tested against)."""
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    keep = (s >= head - 1e-9) & (s <= s[-1] - tail + 1e-9)
    return path[keep]


def coil_pitch(turns):
    """The loop comes down from the top of the leads' bend onto the motor: never tighter than COIL_PITCH a turn."""
    return max(COIL_PITCH, (COIL_RISE - LEAD_BUNDLE_D / 2 - 1.3) / turns)


def coil_length(turns):
    return turns * math.hypot(2 * math.pi * COIL_R, coil_pitch(turns))


def wire_paths(t=CARD_T_NOM, side=None, back=0.0, turns=None):
    """Every wire inside the shell, as a hand can lay it:
      bundle       the four motor leads as ONE bundle: up out of the motor, the spare coiled and
                   taped on the back half of the motor's top, then down behind the motor
      lead1..4     the four leads from where the bundle fans out, over the card's MINUS edge to
                   J1..J4 (Ladder.motor_wires()'s lines; lead 1 crosses the edge beside lead 2)
      out_plus, out_minus   three-jumper output wires: down the card's two free margins, round to
                   the module's TAIL and in through the comb, never down onto the pads from above
      tail_plus, tail_minus  thin meter tails, each through a 1 k resistor at its rail, down the
                   inside of a side wall and out under the back panel
    Each entry: fine (samples), coarse (for the solid), d (diameter), bend (the radius it was laid with).
    back: the MOTOR LEADS only, drawn with the shell (and the card in it) that far short of home."""
    S = USB_SIDE if side is None else side
    turns = COIL_TURNS if turns is None else turns
    zf = CARD_BACK + t
    zl = zf + LEAD_OVER
    zL, zJ = zl - back, zf + 2.4 - back                    # the leads' height off the card, and at their joints
    ex, ey, ez = LEAD_EXIT
    out = {}

    # ---- motor leads: the common bundle
    th = np.linspace(0, math.pi / 2, 12)
    rise = np.array([(ex + COIL_RISE * (1 - math.cos(a)), ey + COIL_RISE * math.sin(a), ez) for a in th])
    cx, cz, y0 = ex + COIL_RISE, ez + COIL_R, ey + COIL_RISE
    a_end = turns * 2 * math.pi
    pitch = coil_pitch(turns)
    helix = lambda a: np.array([cx + COIL_R * math.sin(a), y0 - pitch * a / (2 * math.pi), cz - COIL_R * math.cos(a)])
    n = int(math.ceil(a_end * COIL_R))
    coil_f = np.array([helix(a) for a in np.linspace(0, a_end, n + 1)])
    coil_c = np.array([helix(a) for a in np.linspace(0, a_end, int(math.ceil(math.degrees(a_end) / 20.0)) + 1)])
    end = helix(a_end)
    heading = np.array([math.cos(a_end), 0.0, math.sin(a_end)])
    b_a = end + heading * ((-(IN_HW - 39.0) - end[0]) / heading[0])        # along the coil's own tangent, to the motor's back left corner
    b_a[1] = MOTOR_TOP + LEAD_BUNDLE_D / 2 + 1.3
    b_c = np.array([-(IN_HW - 8.0), MOTOR_TOP - 6.5, MOTOR_BACK - 4.0])
    b_d = np.array([-(IN_HW - 8.0), LEAD_EDGE_Y1 - 5.4, zL])
    b_mid = b_c + (b_d - b_c) * 0.45
    run_f, run_c = _round_path([end, b_a, b_c, b_mid], MIN_BEND)
    common_f = np.vstack([rise[:-1], coil_f[:-1], run_f])
    common_c = np.vstack([rise[::3][:-1], coil_c[:-1], run_c])
    out["bundle"] = dict(fine=common_f, coarse=common_c, d=LEAD_BUNDLE_D, bend=MIN_BEND)

    # ---- the four leads, from the fan-out to J1..J4
    edge = -CARD_W / 2 - 5.0
    for k, c in enumerate(TPL_COL):
        jx, jy = tpl(c - 0.4, 36.6)                        # Ladder.motor_wires(): wrapped just under each J joint
        line_y = tpl(c - 3.6, 0)[1]                        # ... and it runs 3.6 mm beside its leg
        pts = [b_mid, b_d]
        if k == 0:                                         # lead 1: over the edge beside lead 2, then up to its own line
            pts += [(edge, LEAD_EDGE_Y1, zL), (-39.2, LEAD_EDGE_Y1, zL), (-25.0, line_y, zL)]
        else:
            pts += [(edge, line_y, zL)]
        pts += [(jx - 7.4, line_y, zL), (jx, jy, zJ)]
        f, cr = _round_path(pts, MIN_BEND)
        out[f"lead{k + 1}"] = dict(fine=f, coarse=cr, d=LEAD_D, bend=MIN_BEND, full=np.vstack([common_f[:-1], f]))

    # ---- output wires. X is written for the module on +X and mirrored for the other side
    _, _, tail_pcb, comb0, _ = _sled_x()
    z_card = zf + OUT_WIRE_D / 2 + 0.5
    z_front = LEDGE_Z0 + LEDGE_LIP + OUT_WIRE_D / 2 + WIRE_AIR         # in front of the ledge's lip
    z_pad = _pcb_z() + MOD_PCB_T + OUT_WIRE_D / 2
    yc = SLED_YC - USB_Y_OFF
    xm = CARD_W / 2 - OUT_WIRE_D / 2 - 1.6                            # down the card's free margin
    tabs = {"out_plus": tpl(54.5, -1.5), "out_minus": tpl(55.5, 61.5)}
    for name, (tx, ty) in tabs.items():
        X = S * tx                                         # the tab, in the module-side-positive frame
        if X > 0:                                          # the NEAR tab: round the top of the sled and in from the tail
            y_run = SLED_Y0 + SLED_W + OUT_WIRE_D / 2 + 2.7
            pts = [(X, ty, zf + 2.0), (xm, ty, z_card), (xm, y_run, z_front), (comb0 - 17.4, y_run, z_front),
                   (comb0 - 17.4, yc + PAD_DY, z_pad + 1.5), (tail_pcb + 4.0, yc + PAD_DY, z_pad)]
        else:                                              # the FAR tab: down its own margin, across under the card
            pts = [(X, ty, zf + 2.0), (-xm, ty, z_card), (-xm, CARD_Y0 + 6.0, z_front), (-xm, yc - PAD_DY, z_front),
                   (tail_pcb + 4.0, yc - PAD_DY, z_pad)]
        f, cr = _round_path([(S * x, y, z) for x, y, z in pts], OUT_BEND)
        out[name] = dict(fine=f, coarse=cr, d=OUT_WIRE_D, bend=OUT_BEND)

    # ---- meter tails: 1 k at the rail, over the card's edge, down the inside of the side wall, out under the panel
    xs = IN_HW - TAIL_D / 2 - 1.0
    for name, sx in (("tail_plus", +1), ("tail_minus", -1)):
        pts = [(31.0, TAIL_Y, zf + 2.5), (60.0, TAIL_Y, zf + 2.5), (xs, TAIL_Y - 10.0, MOTOR_BACK), (xs, 30.0, MOTOR_BACK),
               (65.0, 10.0, IN_Z + GAP_BACK / 2), (65.0, -8.0, IN_Z + GAP_BACK / 2)]
        f, cr = _round_path([(sx * x, y, z) for x, y, z in pts], TAIL_BEND)
        out[name] = dict(fine=f, coarse=cr, d=TAIL_D, bend=TAIL_BEND)
    return out


def lie_point(p, up=0.0, gap=None):
    """A model point when the shell lies on its back behind the machine (open front up, feet toward the machine)."""
    x, y, z = p
    return (x, z - Z_BACK + up, BASE_BACK - (LIE_GAP if gap is None else gap) + BASE_TOP - y)


def lie_solid(part, up=LIE_BOX, gap=None):
    """A solid in that same pose (the matrix wire_cover_render.lie() uses)."""
    return part.rotate((0, 0, 0), (1, 0, 0), -90).translate((0, -Z_BACK + up, BASE_BACK - (LIE_GAP if gap is None else gap) + BASE_TOP))


def lead_ties(W):
    """Per motor lead: the point where it passes under the tie (card seated, model frame) and the
    length of lead from there to its joint, both read off the drawn path."""
    out = []
    for k in (1, 2, 3, 4):
        f = W[f"lead{k}"]["fine"]
        i = [n for n in range(1, len(f)) if (f[n - 1][0] - TIE_X) * (f[n][0] - TIE_X) <= 0][-1]
        out.append((tuple(f[i]), _length(f[i:])))
    return out


def lead_need(ties, place):
    """Lead needed by the worst of the four with the card in some pose: straight from where the
    leads leave the motor to the tie (place() moves a seated point to the pose), the drawn run
    from the tie to the joint, and the two ends. The card is TIED: a straight line from the motor
    to the joint (the old check) forgets that every lead must go round by the tie."""
    return max(math.dist(LEAD_EXIT, place(tp)) + run + LEAD_ENDS for tp, run in ties)


def lead_drawn(back=0.0, turns=None):
    """The longest of the four motor leads as DRAWN (bend out of the motor, coil, hand-laid route, joint)."""
    W = wire_paths(back=back, turns=turns)
    return max(_length(W[f"lead{k}"]["full"]) for k in (1, 2, 3, 4))


def fit_coil():
    """How much spare can really be wound up. The coil is made in the coil pose (the shell COIL_BACK short of
    home), so the lead as drawn THERE, coil included, must leave COIL_KEEP. Loops come as n + COIL_FRAC, because
    the coil has to leave toward the motor's back left corner. None: not even the part loop fits."""
    best = None
    for t in COIL_CHOICES:
        if lead_drawn(COIL_BACK, t) <= LEAD_LEN - COIL_KEEP:
            best = t
    return best


COIL_FIT = fit_coil()
COIL_TURNS = COIL_FIT if COIL_FIT is not None else COIL_CHOICES[0]


def wire_solid(coarse, d):
    """A wire as a row of cylinders with a ball at each joint: enough for an overlap test."""
    parts = []
    for a, b in zip(coarse[:-1], coarse[1:]):
        v = b - a
        L = float(np.linalg.norm(v))
        if L < 1e-6:
            continue
        parts.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(d / 2, L, cq.Vector(*a), cq.Vector(*(v / L)))))
        parts.append(cq.Workplane("XY").add(cq.Solid.makeSphere(d / 2).translate(cq.Vector(*b))))
    return _many(parts)


def wire_air(pa, da, pb, db):
    """Least air between two wires, from their sampled centre lines."""
    from scipy.spatial import cKDTree
    d, _ = cKDTree(pa).query(pb)
    return float(d.min()) - da / 2 - db / 2


# ============================================================ print orientation, coupons, plates
def as_printed(part, z_bed):
    return part.translate((0, 0, -z_bed))


def coupons(sh):
    """Slices of the real shell, so every printer-dependent fit can be tried in under an hour."""
    c1 = sh.intersect(_box(37.0, FOOT_X_WIDE + 1, BASE_TOP - 6, FORK_H + 1.0, Z_BACK, OUTER_END_Z))        # foot, peg, forks
    lx = led_x()
    c2 = sh.intersect(_box(-HW - 1, min(lx + GLOW_X / 2 + 3, -8.0), LID_IN - 28.0, Y_TOP + 1, Z_BACK, IN_Z + 15.0))   # clip, thin spot
    S = USB_SIDE
    c3 = sh.intersect(_box(S * 36.0, S * (HW + 1), FORK_H + 0.5, recess_y()[1] + 0.2, Z_BACK, IN_Z + FACE_H + 4.0))   # rail, key, window
    c5 = sh.intersect(_box(-S * 48.0, -S * 84.0, BASE_TOP, 40.0, -46.0, Z_FRONT + 1))                    # baffle, wall stop, a bit of foot
    return {"C1_foot_peg_forks": c1, "C2_card_clip_and_light": c2, "C3_rail_and_window": c3,
            "C4_sled_PLACEHOLDER": sled(), "C5_baffle": c5}


def overhang_census(mesh):
    """Downward faces steeper than 46 degrees off vertical and not on the bed, grouped into
    patches. Returns (patches, worst span): each patch is (area, short side, long side, z)."""
    import trimesh
    n = mesh.face_normals
    cz = mesh.triangles_center[:, 2]
    flag = (n[:, 2] < -math.sin(math.radians(46.0))) & (cz > 0.05)
    idx = np.nonzero(flag)[0]
    if len(idx) == 0:
        return [], 0.0
    adj = mesh.face_adjacency
    keep = flag[adj[:, 0]] & flag[adj[:, 1]]
    groups = trimesh.graph.connected_components(adj[keep], nodes=idx)
    out = []
    for g in groups:
        if mesh.area_faces[g].sum() < 0.05:                # a facet edge of the mesher, not a face
            continue
        v = mesh.triangles[g].reshape(-1, 3)
        ex = v.max(axis=0) - v.min(axis=0)
        out.append((float(mesh.area_faces[g].sum()), float(min(ex[0], ex[1])), float(max(ex[0], ex[1])), float(v[:, 2].mean())))
    return out, max((p[1] for p in out), default=0.0)


def pack(items, path):
    """items: (stl path, x, y, quarter turns). Centres at x, y; writes one STL; returns the meshes."""
    import trimesh
    placed = []
    for src, x, y, turn in items:
        m = trimesh.load(src, force="mesh")
        if turn:
            m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(90 * turn), [0, 0, 1]))
        lo, hi = m.bounds
        m.apply_translation([x - (lo[0] + hi[0]) / 2, y - (lo[1] + hi[1]) / 2, -lo[2]])
        placed.append(m)
    lo = np.min([m.bounds[0] for m in placed], axis=0)
    hi = np.max([m.bounds[1] for m in placed], axis=0)
    for m in placed:
        m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, 0])
    whole = trimesh.util.concatenate(placed)
    whole.export(path)
    return placed


def pack_rows(srcs, path, gap, width=200.0):
    """Lay the pieces out in rows, `gap` apart, bounding box to bounding box."""
    import trimesh
    x = y = row_h = 0.0
    items = []
    for src in srcs:
        ext = trimesh.load(src, force="mesh").bounding_box.extents
        if x > 0 and x + ext[0] > width:
            x, y, row_h = 0.0, y + row_h + gap, 0.0
        items.append((src, x + ext[0] / 2, y + ext[1] / 2, 0))
        x += ext[0] + gap
        row_h = max(row_h, ext[1])
    return pack(items, path)


def plate_ok(placed, gap):
    """batches.py's rules: edge margin, the P1S's reserved front-left corner, and a least gap
    between parts' bounding boxes."""
    half = plate_rules.PLATE / 2
    worst = 1e9
    for i, m in enumerate(placed):
        v = m.vertices
        if np.abs(v[:, :2]).max() > half - plate_rules.EDGE:
            return False, 0.0
        if ((v[:, 0] < -half + plate_rules.NO_GO[0]) & (v[:, 1] < -half + plate_rules.NO_GO[1])).any():
            return False, 0.0
        a = m.bounds
        for other in placed[:i]:
            b = other.bounds
            worst = min(worst, float(max(a[0][0] - b[1][0], b[0][0] - a[1][0], a[0][1] - b[1][1], b[0][1] - a[1][1])))
    return worst >= gap or len(placed) == 1, worst


# ============================================================ checks
def check(sh, sl, quick=False):
    """Returns (lines, solids). A line is (text, True | False | NOTE): NOTE lines say what no
    script can test and are never counted as passed."""
    from shapely.geometry import Point, Polygon
    res = []
    S = USB_SIDE
    ok = lambda text, good: res.append((text, bool(good)))
    note = lambda text: res.append((text, NOTE))
    fr, motor, pins, nuts = pl.frame(), pl.motor_dummy(), pl.pins_dummy(), rear_hardware_dummy()
    fixed = [("frame", fr), ("motor", motor), ("pin bolts", pins), ("pin washers and nyloc nuts", nuts)]
    machine = _many([p for _, p in fixed])
    metal = _many([motor, pins, nuts])
    bare = shell(locators=False)

    # ---- 1. the machine
    ok("shell is one solid", sh.solids().size() == 1)
    for name, other in fixed:
        v = _vol(sh, other)
        ok(f"shell against the {name}: {v:.3f} mm3 of overlap", v < 1e-3)
    worst = 0.0
    for dx, dz in ((MIN_AIR, 0), (-MIN_AIR, 0), (0, MIN_AIR), (0, -MIN_AIR)):
        worst = max(worst, _vol(bare.translate((dx, 0, dz)), machine))
    ok(f"pegs, forks and wall stops aside, the shell can move {MIN_AIR:.1f} mm left, right, forward or back and still touch "
       f"nothing ({worst:.3f} mm3): least clearance {MIN_AIR:.1f} mm", worst < 1e-3)
    d = _dist(bare, metal)
    ok(f"nearest the shell comes to the motor, a pin bolt or a nut: {d:.1f} mm", d >= BOSS_CLEAR - 0.01)
    side_bite = _vol(sh.translate((FORK_CLEAR + 0.4, 0, 0)), fr)
    side_free = _vol(sh.translate((FORK_CLEAR - 0.15, 0, 0)), fr)
    ok(f"left-right it is held by the four forks on the two tall gussets: free at {FORK_CLEAR - 0.15:.2f} mm "
       f"({side_free:.3f} mm3), stopped at {FORK_CLEAR + 0.4:.1f} mm ({side_bite:.1f} mm3)", side_free < 1e-3 and side_bite > 1.0)

    # front-back: FREE TRAVEL of the real diamond section in the hole, not a bite volume
    hole = pl.M5_CLEAR
    back, fwd = peg_travel(hole, 0.0)
    pg = _many(pegs())
    occ = [_vol(pg.translate((0, 0, dz)), fr) for dz in (-(back - 0.05), -(back + 0.10), fwd - 0.05, fwd + 0.10)]
    ok(f"front-back it is held by two pegs ({PEG_X} x {PEG_Z} mm) in the base's {hole} mm holes: free travel {-back:+.2f} to "
       f"{fwd:+.2f} mm (the real solids agree: {occ[0]:.3f} and {occ[2]:.3f} mm3 just inside, {occ[1]:.2f} and {occ[3]:.2f} just outside). "
       f"COUPON C1", 0.2 <= back <= 0.9 and fwd >= 0.2 and occ[0] < 1e-3 and occ[2] < 1e-3 and occ[1] > 1e-3 and occ[3] > 1e-3)
    small = {dd: peg_travel(dd, 0.0) for dd in (5.2, 5.0, 4.8)}
    txt = ", ".join(f"{dd} hole {-tr[0]:+.2f} to {tr[1]:+.2f}" if tr else f"{dd} hole: does NOT seat" for dd, tr in small.items())
    ok(f"the frame printed front face down, so these holes lay on their side and may be small front to back. Seated travel in a "
       f"smaller hole: {txt}. It still seats in a hole printed {hole - 5.0:.1f} mm small. COUPON C1 on the REAL frame first",
       small[5.0] is not None and small[5.0][0] >= 0.1)
    tip5 = peg_travel(5.0, PEG_LEN)
    push = _vol(sh.translate((0, 0, WALL_STOP_GAP + 0.10)), fr)
    hold = _vol(sh.translate((0, 0, WALL_STOP_GAP - 0.05)), fr)
    ok(f"blind fitting: four stops on the side walls' front edges meet the wall {WALL_STOP_GAP} mm past the seat ({hold:.3f} mm3 just "
       f"before, {push:.2f} just after). Pushed hard on the wall the pegs are over their holes: {WALL_STOP_GAP} is inside the "
       f"{fwd:+.2f} travel, and a peg TIP still enters a {5.0} hole there (tip travel {tip5[1]:+.2f}) and centres itself as it drops",
       hold < 1e-3 and push > 1e-3 and WALL_STOP_GAP < fwd - 0.1 and tip5 is not None and tip5[1] >= WALL_STOP_GAP + 0.2)
    tipw = PEG_LEN * math.tan(math.radians(PEG_TAPER))
    ok(f"peg tips are {PEG_Z - 2 * tipw:.1f} x {PEG_X - 2 * tipw:.1f} mm. No fillet at the root: the root is level with the base's "
       f"top, so a 1 mm fillet would make it {PEG_X + 2:.1f} x {PEG_Z + 2:.1f} in the mouth of a {hole} hole", PEG_Z + 2 > hole)

    # the way on: lowered behind the motor, slid forward riding on the peg tips, then it drops
    path = [(0, 30.0, -25.0), (0, 12.0, -25.0), (0, LIFT_ON + 1.5, -20.0)] + [(0, LIFT_ON, -z) for z in (60, 40, 25, 15, 10, 6, 3, 1, 0.2)]
    path += [(0, LIFT_ON * f, 0) for f in (0.75, 0.5, 0.25)]
    worst = max(_vol(sh.translate(p), machine) for p in path)
    ok(f"the way on is clear at {len(path)} positions: down behind the motor, forward on its peg tips "
       f"({LIFT_ON:.0f} mm up), drop ({worst:.3f} mm3)", worst < 1e-3)
    lifts = (LIFT_ON + 0.5, 5.0, LIFT_MAX - 0.4)
    worst = max(_vol(sh.translate((0, h, -z)), machine) for h in lifts for z in (25, 6, 0.5))
    over = _vol(sh.translate((0, LIFT_MAX + 0.6, -0.5)), machine)
    ok(f"it need not be held at exactly {LIFT_ON:.0f} mm: clear at {', '.join(f'{h:.1f}' for h in lifts)} mm up as well ({worst:.3f} mm3). "
       f"The window is {LIFT_ON:.0f} to {LIFT_MAX:.1f} mm: at {LIFT_MAX + 0.6:.1f} the baffle tops meet the two top pin bosses ({over:.1f} mm3)",
       worst < 1e-3 and over > 1e-3 and LIFT_MAX - LIFT_ON >= 3.0)
    # riding on two peg tips it wants to tip forward: what touches first must be the wall, never the motor or a nut
    tilt = 1.5
    piv = (BASE_TOP, PEG_HOLES[0][1])
    first, worst_metal = None, 0.0
    for zb in (25, 12, 8, 6, 4, 2, 0.5):
        t = sh.translate((0, LIFT_ON + 0.1, -zb)).rotate((0, piv[0], piv[1] - zb), (1, piv[0], piv[1] - zb), tilt)
        worst_metal = max(worst_metal, _vol(t, metal))
        if first is None and _vol(t, fr) > 1e-3:
            first = zb
    lead = (STOP_BUMP_Y[1][1] - BASE_TOP) * math.sin(math.radians(tilt))
    ok(f"tipped {tilt} degrees forward on its peg tips it touches the wall {first} mm early (its top leads by {lead:.1f} mm) and "
       f"nothing else: {worst_metal:.3f} mm3 against motor, bolts and nuts all the way in. Level it and it goes home",
       worst_metal < 1e-3 and first is not None and first <= 8)
    bb = sh.val().BoundingBox()
    ok(f"all of the shell is behind the wall: it ends at Z = {bb.zmax:.2f}, the wall's back face is {WALL_BACK:.0f}", bb.zmax <= WALL_BACK - 0.2)
    if quick:
        ok("gears and wheel: SKIPPED (--quick). Run without it before printing", False)
    else:
        gs = pl.gearset()
        turning = {k: pl.place(v, pl.GEAR_GAP) for k, v in gs.items()}
        turning["wheel"] = pl.place(pl.wheel(), pl.WHEEL_Z0)
        turning["spider"] = pl.place(pl.spider(), pl.SPIDER_Z0)
        grip = (pl.grip().translate((pl.R_HANDLE, 0, pl.WHEEL_T + pl.PED_H + 0.2)).translate((0, AY, pl.WHEEL_Z0)))
        turning["grip"] = grip
        zmin = min(p.val().BoundingBox().zmin for p in turning.values())
        cover = _many([sh, sl] + list(tester_dummy().values()) + [clamp_dummy(-1), clamp_dummy(1)])
        v = sum(_vol(cover, p) for p in turning.values())
        ok(f"shell, sled, tester and clamps against sun, planets, ring, spider, wheel and grip: {v:.3f} mm3; the nearest "
           f"turning face is at Z = {zmin:+.1f}, {zmin - bb.zmax:.1f} mm in front of the shell with the whole wall between",
           v < 1e-3 and zmin - bb.zmax >= 8)

    # ---- 2. what the camera sees
    sil = sbox(-HW, BASE_TOP, HW, Y_TOP - CORNER_R).union(sbox(-(HW - CORNER_R), BASE_TOP, HW - CORNER_R, Y_TOP))
    for sx in (-1, 1):
        sil = sil.union(Point(sx * (HW - CORNER_R), Y_TOP - CORNER_R).buffer(CORNER_R, 64))
    feet = sbox(-FOOT_X_WIDE, BASE_TOP, FOOT_X_WIDE, BASE_TOP + FOOT_T)
    g_out = pl.GUSSETS[-1]                                 # the frame's own front outline: wall, base, and the two outer gussets behind the wall
    seen = pl.wall_outline().union(sbox(-pl.BASE_HALF_W, 0, pl.BASE_HALF_W, BASE_TOP))
    for sx in (-1, 1):
        x0, x1 = sorted((sx * OUTER_IN, sx * pl.BASE_HALF_W))
        seen = seen.union(sbox(x0, BASE_TOP, x1, g_out[1]))
    out = sil.union(feet).difference(seen).area
    out_wall = sil.union(feet).difference(pl.wall_outline()).area
    ok(f"from dead ahead nothing of the shell shows round the frame: {out:.1f} mm2 outside its outline ({out_wall:.1f} mm2 of the "
       f"feet's wide rear ends are outside the WALL's outline, straight behind the outer gussets)", out < 1.0)
    covered = sbox(BAFFLE_X_TIP, BAFFLE_Y0, HW, BAFFLE_Y1).union(sbox(-HW, BAFFLE_Y0, -BAFFLE_X_TIP, BAFFLE_Y1))
    total = sum(w.area for w in _WINDOWS)
    behind = sum(w.intersection(sbox(-HW, 0, HW, 400)).area for w in _WINDOWS)
    peek = sum(w.intersection(sbox(-HW, 0, HW, 400)).difference(covered).area for w in _WINDOWS)
    ok(f"through the wall's two windows ({total:.0f} mm2 in all): the {behind:.0f} mm2 in front of the shell is closed by the two baffles "
       f"and the side walls' edges ({peek:.1f} mm2 left open). The other {total - behind:.0f} mm2 is OUTBOARD of the shell: through it "
       f"the camera sees the shell's plain side wall, a foot and a clamp, no wire. The air slit is {BAFFLE_SLIT:.0f} mm, too narrow for a finger",
       peek < 1.0 and BAFFLE_SLIT <= 6.0)
    sbb = sl.val().BoundingBox()
    inside = (max(abs(sbb.xmin), abs(sbb.xmax)) <= HW and CARD_W / 2 < IN_HW)
    ok(f"everything the shell holds is inboard of its side walls: card to {CARD_W / 2:.0f} mm, sled to {max(abs(sbb.xmin), abs(sbb.xmax)):.1f}, "
       f"walls at {IN_HW} to {HW}", inside)
    note(f"the filmed back is one plain face: no hole, no notch, no screw head. One opening in all: a {WIN_Y[1] - WIN_Y[0]:.0f} x "
         f"{WIN_Z[1] - WIN_Z[0]:.0f} mm window in one side, filled by the sled's face plate. Two things may GHOST through thin plastic in "
         f"a pale filament: the {GLOW_X:.0f} x {GLOW_Z:.0f} mm light spot on the lid (wanted) and the {WIN_WALL:.0f} mm patch round the window")
    note("from high in front (over 30 degrees up, over the wall's top) a camera can look down the 13 mm warm-air slot. The spare "
         "lead is drawn looped on the BACK half of the motor's top, under the lid. Tape it there")

    # ---- 3. clamps
    for sx, name in ((-1, "left"), (1, "right")):
        cl = clamp_dummy(sx)
        v = _vol(cl, _many([sh, fr, sl] + list(tester_dummy().values())))
        x0, x1, z0, z1 = jaw_footprint(sx)
        fx0, fx1 = sorted((sx * HW, sx * FOOT_X1))
        mx, mz = min(x0 - fx0, fx1 - x1), min(z0 - Z_BACK, FOOT_Z1 - z1)
        ok(f"{name} G-clamp (step 9's, PLACEHOLDER jaw {G_JAW_W:.0f} mm wide) at x = {sx * CLAMP_X:+.0f}: jaw wholly on the foot with "
           f"{mx:.1f} mm each side and {mz:.1f} mm front and back, touching nothing else ({v:.3f} mm3). COUPON C1",
           v < 1e-3 and mx >= 2.0 and mz >= 2.0)
    grip_mm = BASE_TOP + FOOT_T + TABLE_T
    ok(f"clamp opening needed: table {TABLE_T:.0f} + base {BASE_TOP:.0f} + foot {FOOT_T:.0f} = {grip_mm:.0f} mm of {G_OPEN:.0f}", grip_mm <= G_OPEN - 20)
    bay_f, bay_r = FOOT_X1 - HW, FOOT_X_WIDE - HW
    wide = bay_r - 4.0
    zs_r = FOOT_WIDE_Z1 - G_PAD_R - 1.0                   # pad centre with the whole pad behind the outer gusset's tail
    v = _vol(clamp_dummy(1, jaw=wide, pad_z=zs_r).translate(((HW + FOOT_X_WIDE) / 2 - CLAMP_X, 0, 0)), _many([sh, fr]))
    ok(f"the bay between side wall and outer gusset is {bay_f:.0f} mm (it was 52.5 before the cover): a jaw up to {bay_f - 4.0:.0f} mm "
       f"goes anywhere on the foot with 2 mm each side. Behind the gusset's tail the foot runs to the base's edge, a {bay_r:.0f} mm bay: "
       f"a jaw up to {wide:.0f} mm fits there, hooked {zs_r + G_PAD_R - BASE_BACK:.0f} mm onto the table ({v:.3f} mm3)",
       bay_f - 4.0 >= G_JAW_W and v < 1e-3)
    note(f"his clamp is NOT measured (Blue Spot 4 inch, no drawing found). Measure the widest part of the jaw: {bay_f - 4.0:.0f} mm or "
         f"less, anywhere; {bay_f - 4.0:.0f} to {wide:.0f}, behind the short gusset; more, tell me. Put the number in G_JAW_W")
    # the tester ALWAYS hangs straight above a clamp's arm (the spine must be behind the foot, the pad on it), and
    # the shell's window freezes its height. So the clamp's frame depth D and the tester's size decide, before the shell is printed
    yc, zc = _usb_centre()
    seat_top = BASE_TOP + FOOT_T
    arm_top = seat_top + G_FRAME_T
    flat = (yc - TESTER[1] / 2) - arm_top                 # this sled: tester on edge, its WIDTH is up and down
    shelf_yc = WIN_Y[1] - PLUG_HEAD - PLUG_T / 2          # a shelf sled: board level, tester flat, its THICKNESS is up and down
    shelf = (shelf_yc - TESTER[2] / 2) - arm_top
    shelf_under = shelf_yc - USB_H / 2 - USB_Z_OFF - MOD_PCB_T - MOD_UNDER - SLED_FLOOR - MIN_AIR     # the tall gusset must stay below this
    shelf_z = WALL_BACK - min(TALL_H - pl.BASE_T, pl.BASE_DEPTH) * (1 - (shelf_under - pl.BASE_T) / (TALL_H - pl.BASE_T))
    shelf_w = math.floor(shelf_z - (IN_Z + WIN_Z[0]))
    shelf_ok = shelf >= TESTER_ARM_AIR and MOD_W <= shelf_w    # N1 (2026-10-05): a shelf sled only counts if the board fits beside the tall gusset
    how = ("print as drawn" if flat >= TESTER_ARM_AIR else
           "the sled MUST be redrawn as a shelf BEFORE the shell is printed (it is not drawn yet, so this line stays [NO] until it is)" if shelf_ok else
           "NEITHER sled clears: move the window, in the file, before the shell is printed")
    ok(f"the USB tester always hangs straight above a G-clamp's arm, and the shell's window freezes its height. RULE: "
       f"{yc - seat_top:.1f} - W/2 - D must be {TESTER_ARM_AIR:.0f} mm or more (W = tester body width, D = height of the clamp's frame above "
       f"the face that presses). PLACEHOLDERS W = {TESTER[1]:.0f}, D = {G_FRAME_T:.0f}: {flat:.1f} mm. If the real numbers give less, the sled "
       f"becomes a shelf (board level, tester flat, screen up) behind the SAME window: {shelf_yc - seat_top:.2f} - thickness/2 - D, "
       f"{shelf:.1f} mm with thickness {TESTER[2]:.0f}. Verdict on today's numbers: {how}", flat >= TESTER_ARM_AIR)    # N1: only the DRAWN sled may pass
    note(f"D is NOT measured: {G_FRAME_T:.0f} mm is copied from the step 9 drawing. Examples on this sled: W 24, D 22 leaves 3.4 mm; "
         f"W 30, D 25 CLASHES by 2.6. This sled is good up to D = {yc - seat_top - TESTER[1] / 2 - TESTER_ARM_AIR:.1f} (W {TESTER[1]:.0f}); a shelf "
         f"sled up to D = {shelf_yc - seat_top - TESTER[2] / 2 - TESTER_ARM_AIR:.1f} (thickness {TESTER[2]:.0f}), but it is NOT drawn yet and takes a "
         f"board only up to about {shelf_w:.0f} mm wide (a tall gusset is under it). Do NOT print the shell before D, the tester's width "
         f"and thickness and the module's width are in this file: a wrong guess is a second 7 hour shell")

    # ---- 4. the card
    for told, name in ((card_as_told_dummy(True), "on end"), (card_as_told_dummy(False), "on its side")):
        v = _vol(sh, told)
        ok(f"the card ELECTRONICS.md step 0 says to cut ({CARD_AS_TOLD[0]:.0f} x {CARD_AS_TOLD[1]:.0f}) does NOT go in {name}: "
           f"{v:.0f} mm3 into the shell. It must be trimmed to the paper template's outline: picture cover_01", v > 100)
    for t in (CARD_T_NOM, CARD_T_MAX):
        card, parts, dio = card_dummy(t), card_parts_dummy(t), diodes_dummy(t)
        v = _vol(sh, card) + _vol(sh, parts) + _vol(sh, dio)
        ok(f"card {CARD_W:.0f} x {CARD_H:.0f} x {t:.1f} (template size, on end, capacitor down) and every part on it sit in "
           f"the pocket: {v:.3f} mm3", v < 1e-3)
    tol = CARD_CUT_TOL
    v = _vol(sh, card_dummy(CARD_T_NOM, wide=2 * tol - 0.02, tall=tol))
    over_lip = CARD_LIFT - tol - LEDGE_LIP
    small = sbox(-CARD_W / 2 + tol, CARD_Y0, CARD_W / 2 - tol, CARD_TOP - tol)
    under = min(Polygon(_clip_poly(sx)[0]).intersection(small).area for sx in (-1, 1))
    under_nom = min(Polygon(_clip_poly(sx)[0]).intersection(sbox(-CARD_W / 2, CARD_Y0, CARD_W / 2, CARD_TOP)).area for sx in (-1, 1))
    ok(f"a scissor-cut card may be {CARD_W - 2 * tol:.0f} to {CARD_W + 2 * tol:.0f} wide and {CARD_H - tol:.0f} to {CARD_H + tol:.0f} tall: the biggest "
       f"still seats ({v:.3f} mm3) and lifts {over_lip:.1f} mm clear of the ledge's lip; under each clip the smallest has {under:.0f} mm2 "
       f"and the template size {under_nom:.0f} (limit {CLIP_MIN_AREA:.0f})", v < 1e-3 and over_lip >= 0.4 and under >= CLIP_MIN_AREA)
    lifted = [card_dummy(CARD_T_MAX, CARD_LIFT - 0.01), card_parts_dummy(CARD_T_MAX, CARD_LIFT - 0.01), diodes_dummy(CARD_T_MAX, CARD_LIFT - 0.01)]
    v = sum(_vol(sh, p) for p in lifted)
    ok(f"going in: slid {CARD_LIFT:.0f} mm up under the two clips, no clip or lip touches a part ({v:.3f} mm3), and its bottom "
       f"edge is {CARD_LIFT - LEDGE_LIP:.1f} mm clear of the ledge's lip", v < 1e-3 and CARD_LIFT - LEDGE_LIP >= 1.0)
    # plastic on the parts' side of the card: everything in front of the card's back face (the ribs touch its back only)
    front = sh.intersect(_box(-200, 200, -50, 400, CARD_BACK + 0.05, 50))
    d = min(_dist(front, diodes_dummy(t)) for t in (CARD_T_NOM, CARD_T_MAX))
    ok(f"diodes: the nearest plastic on their side of the card is {d:.1f} mm away. Behind them is the card, then {RIB_H:.0f} mm of air; "
       f"no rib is behind a diode", d >= DIODE_AIR and all(not (abs(tpl(0, 15.0)[0]) - 2 <= abs(x) <= abs(tpl(0, 6.0)[0]) + 2) for x in RIB_XS))
    d_all = min(_dist(front, card_parts_dummy(t)) for t in (CARD_T_NOM, CARD_T_MAX))
    ok(f"clips, lips and stops bear on bare card only: the nearest any part comes to them is {d_all:.1f} mm", d_all >= 1.0)
    v = _vol(_many([card_dummy(CARD_T_MAX), card_parts_dummy(CARD_T_MAX), diodes_dummy(CARD_T_MAX)]), machine)
    cap_gap = MOTOR_BACK - (CARD_BACK + CARD_T_MAX + 13.0)
    ok(f"card and parts against frame, gussets, motor and nuts: {v:.3f} mm3; capacitor to the motor's back {cap_gap:.1f} mm", v < 1e-3 and cap_gap >= 8)
    # could a card that left its clips reach the motor? It pivots on the ledge; the J joints are its highest live metal
    j_y, j_h = tpl(TPL_COL[0], 28.0)[1], 4.5
    depth = MOTOR_BACK - (CARD_BACK + CARD_T_NOM + j_h)
    tip_deg = math.degrees(math.atan2(depth, j_y - CARD_Y0))
    slot = CLIP_Z0 - CARD_BACK
    ok(f"the card is held at both ends: {LEDGE_LIP:.0f} mm of its bottom edge behind the ledge's lip, both top corners behind a "
       f"{CLIP_T} mm clip. To reach the motor's back its J joints would have to tip {tip_deg:.0f} degrees ({depth:.0f} mm). Under the "
       f"clips it has {slot - CARD_T_NOM:.1f} mm of play at {CARD_T_NOM:.0f} mm thick (PLACEHOLDER): two folds of tape on its back take it up",
       tip_deg >= 15 and slot - CARD_T_MAX <= 0.6)
    note("belt and braces for a bare 24 V ladder facing a metal motor: two layers of masking tape across the motor's BACK face before "
         "the cover goes on. Then even a loose card meets paper. Picture cover_04")
    card_edge = CARD_W / 2
    ok(f"the card is inside the wall's solid middle column: edge at {card_edge:.0f} mm, column to {WIN_X_IN:.1f} mm", card_edge < WIN_X_IN)
    led_tip_gap = LID_IN - tpl(-16.8, 47)[1]
    zs = [CARD_BACK + t + 2.6 for t in (1.0, CARD_T_MAX)]
    gz = CARD_BACK + (CARD_T_NOM + CARD_T_MAX) / 2 + 2.6
    ok(f"bus light: the LED's tip is {led_tip_gap:.1f} mm under a {GLOW_X:.0f} x {GLOW_Z:.0f} mm spot where the lid is "
       f"{GLOW_SKIN} mm thin, for any card 1 to {CARD_T_MAX} mm thick; lifted {CARD_LIFT:.0f} mm on the way in the tip is "
       f"{led_tip_gap - CARD_LIFT:.1f} mm under the lid, so NOTHING may stick out past the card's edge",
       led_tip_gap <= 8 and led_tip_gap - CARD_LIFT >= 1.0 and gz - GLOW_Z / 2 <= min(zs) - 2 and gz + GLOW_Z / 2 >= max(zs) + 2)
    note(f"whether a {GLOW_SKIN} mm skin lets the light through depends on the filament: at film pace the LED runs at about 3 mA. "
         f"COUPON C2 over a lit LED decides. No glow in black: that is fine for the film, but then count to ten after the wheel "
         f"stops before touching anything inside")
    top_room = LID_IN - BOSS_TOP
    ok(f"lid is {top_room:.1f} mm above the top pin bosses and {LID_IN - MOTOR_TOP:.1f} mm above the motor (room for the looped spare lead)",
       top_room >= 5 and LID_IN - MOTOR_TOP >= 15)

    # ---- 5. the module and its sled
    mod = module_dummy()
    modc = _many(list(mod.values()))
    v = _vol(sl, sh) + _vol(sl, machine) + _vol(modc, sh) + _vol(modc, machine) + _vol(modc, sl)
    ok(f"PLACEHOLDER module {MOD_L:.0f} x {MOD_W:.0f} on its sled, seated: {v:.3f} mm3 against shell, frame, gussets and motor", v < 1e-3)
    held = [card_dummy(CARD_T_MAX), card_parts_dummy(CARD_T_MAX)]
    v = 0.0
    for shift, drop, dz in ((SLED_SIDE, SLED_DROP, 30.0), (SLED_SIDE, SLED_DROP, 0.0), (0.0, SLED_DROP, 0.0), (0.0, SLED_DROP / 2, 0.0)):
        up = sled(drop=drop, shift=shift).translate((0, 0, dz))
        v += _vol(up, sh) + _vol(up, _many(held))
    ok(f"the sled goes on flat, {SLED_DROP:.0f} mm high and {SLED_SIDE} mm inboard, into the corner, then down: 4 positions, {v:.3f} mm3. "
       f"Its key drops {KEY_DEPTH:.1f} mm into the rail's gap", v < 1e-3 and SLED_DROP >= KEY_DEPTH + 0.4)
    push = _vol(sl.translate((-S * (KEY_FIT + 0.5), 0, 0)), sh)
    pull = _vol(sl.translate((S * (SLED_NOSE_GAP + 0.5), 0, 0)), sh)
    tipz = _vol(sl.translate((0, 0, RAIL_FIT + 0.4)), sh)
    ok(f"plugging in pushes the key against the rail ({push:.1f} mm3 at {KEY_FIT + 0.5:.1f} mm), unplugging pulls the face plate "
       f"against the side wall ({pull:.1f} mm3), the rail's lip holds the keel down ({tipz:.1f} mm3 at {RAIL_FIT + 0.4:.1f} mm). "
       f"Fit {RAIL_FIT} mm: COUPONS C3 + C4", push > 1 and pull > 1 and tipz > 0.2)
    free = _vol(sl.translate((0, 0, RAIL_FIT - 0.1)), sh) + _vol(sl.translate((-S * (KEY_FIT - 0.1), 0, 0)), sh)
    ok(f"and inside those fits it is free ({free:.3f} mm3)", free < 1e-3)
    # LIFT: gravity alone held the old sled. Now the plugged-in tester is the lock
    def lifted_sled(h):
        both = _many([sled(drop=h)] + list(module_dummy(drop=h).values()) + list(tester_dummy(drop=h).values()))
        return _vol(both, sh)
    f_lo, f_hi = lifted_sled(PLUG_HEAD - 0.2), lifted_sled(PLUG_HEAD + 0.5)
    bare_lift = _vol(sled(drop=RAIL_LIP), sh) + _vol(sled(drop=KEY_DEPTH), sh)
    ok(f"LIFT with the tester in: the sled, module and tester rise {PLUG_HEAD - 0.2:.1f} mm free ({f_lo:.3f} mm3), then the plug meets the "
       f"window's top edge ({f_hi:.1f} mm3 at {PLUG_HEAD + 0.5:.1f} mm). The rail's lip holds for {RAIL_LIP:.0f} mm and the key for "
       f"{KEY_DEPTH:.1f}, so a tug on the phone lead cannot unseat it. COUPONS C3 + C4: tug the tester up, the sled must stay",
       f_lo < 1e-3 and f_hi > 1e-3 and PLUG_HEAD + 0.5 < min(RAIL_LIP, KEY_DEPTH) - 1.0)
    note(f"with the tester OUT the sled is held down by its own weight only ({bare_lift:.3f} mm3 in its way up, by design: that is "
         f"how it comes out). Plug the tester in before the shell goes on the machine, or put one strip of tape over the sled's top edge")
    tst = tester_dummy()
    v = _vol(_many(list(tst.values())), _many([sh, fr])) + _vol(tst["body"], sl)
    ok(f"PLACEHOLDER tester {TESTER[0]:.0f} x {TESTER[1]:.0f} x {TESTER[2]:.0f} plugs in from outside through the window, drawn with a "
       f"real-length plug ({PLUG_LEN:.0f} mm): {v:.3f} mm3", v < 1e-3)
    nose = _sled_x()[0]
    standoff = HW - nose
    ok(f"the socket's mouth is {standoff:.1f} mm inside the shell's outer face (it was 2.3): the side wall is {WIN_WALL:.0f} mm thick round "
       f"the window and the sled's nose sits in that recess. A {PLUG_LEN:.0f} mm plug goes in {PLUG_LEN - standoff:.1f} mm before the "
       f"tester's body meets the wall", standoff <= 1.5 and WIN_WALL >= MIN_FEATURE)
    note(f"plug length {PLUG_LEN:.0f} mm and full-seat depth {USB_SEAT} mm are from MEMORY, not a datasheet, and the module's socket may "
         f"sit back from its board's edge. The test that settles it: mark the plug with a pen where it stops in the BARE module; in the "
         f"cover it must go in to the same line")
    fy0, fy1 = SLED_Y0 + KEEL_BAND, SLED_Y0 + SLED_W
    cover_y = min(WIN_Y[0] - fy0, fy1 - WIN_Y[1])
    cover_z = FACE_H - WIN_Z[1]
    ok(f"the face plate covers the window with {cover_y:.0f} mm to spare above and below and {cover_z:.0f} mm beyond its far edge", cover_y >= 2 - 1e-6 and cover_z >= 2)
    ok(f"the window is {WIN_Y[1] - WIN_Y[0]:.0f} x {WIN_Z[1] - WIN_Z[0]:.0f} mm. Flat on the panel (this sled) the plug is "
       f"{PLUG_W:.0f} x {PLUG_T} in it; on a shelf sled (board level, tester's screen UP) it would be {PLUG_T} x {PLUG_W:.0f}: both pass. "
       f"The SHELL fixes only which side the socket is on", WIN_Y[1] - WIN_Y[0] >= PLUG_W + 2 and WIN_Z[1] - WIN_Z[0] >= PLUG_W + 2)
    rows = []
    for tall in (12.0, 15.0):
        z_g = _pcb_z() + MOD_PCB_T + tall
        wide_ok = 2 * (SLED_YC - (tall_gusset_top(z_g) + 2.0))
        rows.append((tall, min(SEAT_W, math.floor(wide_ok))))
    long_ok = IN_HW - RAIL_X0 - FACE_T - COMB_L - TAIL_LAND - 1.0
    ok(f"the seat takes a board up to {rows[0][1]:.0f} mm wide if its parts stand {rows[0][0]:.0f} mm tall, {rows[1][1]:.0f} wide if "
       f"{rows[1][0]:.0f} tall (it crosses a tall gusset), and {long_ok:.0f} long. It was 26 wide", rows[0][1] >= 34 and rows[1][1] >= 28 and long_ok >= 45)
    note("module size, socket position, pad position and tester size are PLACEHOLDERS. The sled is designed again from the real "
         "module (and may become a shelf, so the tester's screen faces up): 20 minutes of printing. Do not print file 3 as it is")
    note("the shell fixes the SIDE the socket is on (USB_SIDE). Hold the tester in any USB charger first: see which face the "
         "screen is on, then choose the side the camera will stand on")

    # ---- 6. wires
    W = wire_paths()
    leads = [W[f"lead{k}"] for k in (1, 2, 3, 4)]
    outs = [W["out_plus"], W["out_minus"]]
    tails = [W["tail_plus"], W["tail_minus"]]
    solid = lambda w, head=0.0, tail=0.0: wire_solid(_trim(w["coarse"], head, tail), w["d"])
    everything = _many([solid(W["bundle"], head=3.0)] + [solid(w) for w in leads + outs + tails])   # the bundle starts IN the motor
    v = _vol(everything, sh) + _vol(everything, _many([fr, pins, nuts, motor])) + _vol(everything, sl)
    ok(f"every wire, drawn as a hand lays it (4 motor leads as one bundle, then fanned out; 2 output wires; 2 meter tails), "
       f"lies wholly inside: {v:.3f} mm3 against shell, frame, motor, bolts, nuts and sled", v < 1e-3)
    card, parts, dio = card_dummy(), card_parts_dummy(), diodes_dummy()
    onto = _many([solid(w, tail=10.0) for w in leads] + [solid(w, head=8.0, tail=6.0) for w in outs] + [solid(w, head=8.0) for w in tails]
                 + [solid(W["bundle"])])
    v = _vol(onto, card) + _vol(onto, parts) + _vol(onto, dio) + _vol(onto, modc)
    ok(f"the same wires against the card, the rails and joints, the capacitor, the eight diodes and the module (each wire's "
       f"own soldered end left out): {v:.3f} mm3. The old check never looked: its wires ran through the capacitor", v < 1e-3)
    airs = []
    on_card = lambda w: w["fine"][w["fine"][:, 0] > -CARD_W / 2 - 2.0]
    for i in range(4):
        for j in range(i):
            airs.append((wire_air(on_card(leads[i]), LEAD_D, on_card(leads[j]), LEAD_D), f"lead{j + 1}/lead{i + 1} on the card"))
    lead_all = [("bundle", W["bundle"])] + [(f"lead{k + 1}", w) for k, w in enumerate(leads)]
    others = [("out_plus", outs[0]), ("out_minus", outs[1]), ("tail_plus", tails[0]), ("tail_minus", tails[1])]
    for i, (na, a) in enumerate(others):
        for nb, b in others[:i] + lead_all:
            airs.append((wire_air(a["fine"], a["d"], b["fine"], b["d"]), f"{nb}/{na}"))
    worst_air, where = min(airs)
    ok(f"air between wires that are not one bundle: least {worst_air:.1f} mm ({where}), limit {WIRE_AIR}", worst_air >= WIRE_AIR - 0.02)
    longest = max(_length(w["full"]) for w in leads)
    direct = math.dist(LEAD_EXIT, (*tpl(TPL_COL[-1], 36.6), CARD_BACK + CARD_T_NOM)) + 30.0
    ok(f"motor leads: {longest:.0f} mm drawn with {COIL_TURNS} of a loop of spare taped on the motor, PLACEHOLDER length {LEAD_LEN:.0f}; the "
       f"shortest route with the shell in place is about {direct:.0f}", longest <= LEAD_LEN and LEAD_LEN - direct >= 100)
    # the lead budget, pose by pose, in the order the work is done. Every lead goes round by the TIE on the card's edge
    ties = lead_ties(W)
    coil_len = coil_length(COIL_TURNS)
    lying = lead_need(ties, lambda p: lie_point(p, LIE_BOX))
    ends = [lead_need(ties, lambda p, u=u: lie_point(p, u)) for u in LIE_BOX_RANGE]
    was = lead_need(ties, lambda p: lie_point(p, LIE_BOX, gap=15.0))
    bare = lead_need(ties, lambda p: lie_point(p, 0.0, gap=0.0))
    v = sum(_vol(lie_solid(part).translate((0, 0, -0.2)), machine) for part in (sh, sl))
    stop = _vol(lie_solid(sh).translate((0, 0, 1.0)), motor)       # the motor's back IS the stop: no measuring
    ok(f"pose 1, sled and card go in (picture cover_03): books against the base's back edge, the shell on its BACK on them, pushed "
       f"forward until it meets the motor's back ({-LIE_GAP:.0f} mm over the books' edge, {v:.3f} mm3 against the machine, {stop:.0f} mm3 "
       f"into the motor if pushed 1 mm more: the motor is the stop). Through the "
       f"tie the worst lead needs {lying:.0f} mm of {LEAD_LEN:.0f}: {LEAD_LEN - lying:.0f} to spare (limit {LEAD_SPARE_MIN:.0f}; a stack "
       f"{LIE_BOX_RANGE[0] / 10:.0f} to {LIE_BOX_RANGE[1] / 10:.0f} cm high leaves {LEAD_LEN - max(ends):.0f} or more). It was drawn 15 mm BEHIND the "
       f"base: that needs {was:.0f}, only {LEAD_LEN - was:.0f} to spare, and the old check's 57 forgot the tie. On the bare table: {bare:.0f}, too short",
       v < 1e-3 and stop > 1.0 and LEAD_LEN - lying >= LEAD_SPARE_MIN and LEAD_LEN - max(ends) >= LEAD_SPARE_MIN)
    stand = lead_need(ties, lambda p: (p[0], p[1], p[2] - COIL_BACK))
    drawn_c = lead_drawn(COIL_BACK)
    lid_edge = WALL_BACK - TOP_GAP - COIL_BACK
    peg_z = max(bz for _, bz in PEG_HOLES) + PEG_Z / 2 - COIL_BACK
    v = _vol(sh.translate((0, 0, -COIL_BACK)), machine)
    ok(f"pose 2, the spare lead is looped and taped (picture cover_05, steps 1 and 2): the shell UPRIGHT with its front edge level "
       f"with the motor's back, {COIL_BACK:.0f} mm short of home, its front {Z_FRONT - COIL_BACK - BASE_BACK:.0f} mm standing on the base, a thin "
       f"book under its back edge ({v:.3f} mm3; the pegs hang {BASE_BACK - peg_z:.0f} mm behind the base). The lid's front edge is "
       f"{MOTOR_BACK - lid_edge:.0f} mm BEHIND the motor's back: its whole top is open to two hands. Drawn there with {COIL_TURNS} of a loop "
       f"({coil_len:.0f} mm) on the motor, the worst lead is {drawn_c:.0f} mm of {LEAD_LEN:.0f}: {LEAD_LEN - drawn_c:.0f} left (limit {COIL_KEEP:.0f}; "
       f"the straight-line floor through the tie is {stand:.0f} + {coil_len:.0f})",
       v < 1e-3 and MOTOR_BACK - lid_edge >= 10 and peg_z < BASE_BACK - 5 and COIL_FIT is not None and drawn_c <= LEAD_LEN - COIL_KEEP)
    big = max(COIL_CHOICES)
    big_len = coil_length(big)
    ok(f"how much spare can be looped is decided THERE, not in the finished drawing. A loop and a half ({big} turns, {big_len:.0f} mm) fits "
       f"the finished drawing ({lead_drawn(0.0, big):.0f} mm) but would need {lead_drawn(COIL_BACK, big):.0f} mm in the pose where it is wound"
       + (f": more than a {LEAD_LEN:.0f} mm lead. So {COIL_TURNS} of a loop is drawn and no more" if COIL_TURNS < big else ": it fits, and is drawn"),
       COIL_FIT is not None)
    on_books = LEAD_LEN - lying - coil_len
    ok(f"the order of work is fixed. NOT on the books: with the loop already taped the card would go in with {on_books:.0f} mm to spare"
       + (f", under the limit of {LEAD_SPARE_MIN:.0f}" if on_books < LEAD_SPARE_MIN else f" (enough with this lead, but the loop would be smaller)")
       + f". NOT once the shell is home: the one opening over the motor is the {TOP_GAP:.0f} x {2 * (HW - CORNER_R):.0f} mm slot under a lid "
       f"{LID_IN - MOTOR_TOP:.1f} mm up, and no hand loops and tapes through that. So: books (sled, card), stand up, loop and tape, push home",
       TOP_GAP < 25)
    drawn_h = lead_drawn(0.0)
    loose = LEAD_LEN - drawn_h
    note(f"once home there is {loose:.0f} mm more lead inside than the finished drawing shows ({drawn_c - drawn_h:.0f} freed by the last push, "
         f"{LEAD_LEN - drawn_c:.0f} left slack in the coil pose). It bows behind the motor, where the taped back face is: press it DOWN "
         f"behind the motor with a finger as the shell goes home. Lead length ({LEAD_LEN:.0f}), where the leads leave the motor and where he "
         f"ties them are PLACEHOLDERS: his ruler settles them")
    note("measure the motor leads. 30 cm: as drawn. 50 cm: every pose passes with 20 cm more; while the shell is still on the books "
         "fold that 20 cm flat and tape it to the inside of the back panel, below the card, on the side away from the module "
         "(or cut the leads to 30 and tin the ends again)")
    lo = max(_length(w["fine"]) for w in outs)
    ok(f"output wires: {_length(outs[0]['fine']):.0f} mm (PLUS) and {_length(outs[1]['fine']):.0f} mm (MINUS) as drawn. CUT BOTH "
       f"{OUT_WIRE_LEN:.0f} mm, not the 'about 10 cm' in ELECTRONICS.md: the MINUS tab is on the far side of the card from the module, "
       f"and both go in at the module's tail, through the sled's comb", lo <= OUT_WIRE_LEN - 20)
    bends = [(_min_bend(w["full"]), MIN_BEND, "motor leads") for w in leads] + [(_min_bend(w["fine"]), OUT_BEND, "output wires") for w in outs] \
        + [(_min_bend(w["fine"]), TAIL_BEND, "meter tails") for w in tails]
    b_txt = ", ".join(f"{name} {min(b for b, _, n in bends if n == name):.1f} (limit {lim:.0f})"
                      for name, lim in (("motor leads", MIN_BEND), ("output wires", OUT_BEND), ("meter tails", TAIL_BEND)))
    ok(f"tightest bend drawn, mm radius: {b_txt}", all(b >= lim - 0.3 for b, lim, _ in bends))
    gap = MOTOR_BACK - (CARD_BACK + CARD_T_NOM + 5.3)
    ok(f"{gap:.0f} mm of free depth between the diodes and the motor's back for the leads to cross", gap >= 15)
    slit = IN_Z + GAP_BACK - IN_Z
    ok(f"meter tails: each leaves its rail through a 1 k resistor, so a slipped tail end on a clamp passes 24 V / 2 k = 12 mA, "
       f"not the generator's 3 to 5 A. They run down the inside of the side walls and out under the back panel, a {slit:.0f} mm gap "
       f"against a {TAIL_D} mm wire, hidden from the front and the back", slit >= 2 * TAIL_D)
    note("NO crocodile clips inside the cover (film step E10 as drawn clips the meter on the rails): between card and motor there is "
         f"{MOTOR_BACK - (CARD_BACK + CARD_T_NOM):.0f} mm, a clip is 30 mm or more, and both rails sit 3 mm outside the motor's metal sides. "
         "Use the two tails, for the METER only, never the bench supply; or film without the meter and read the tester")
    note("strain relief is HIS to build: the four motor leads tied to the card with a twist of jumper wire through two pencil "
         "holes and taped over; the two output wires taped into the sled's comb; a finger of slack at every solder joint. Picture cover_01, cover_04")

    # ---- 7. air
    slit_a = 2 * BAFFLE_SLIT * (BAFFLE_Y1 - BAFFLE_Y0)
    rear = GAP_BACK * 2 * IN_HW
    outlet = TOP_GAP * 2 * (HW - CORNER_R)
    ok(f"air in: {rear:.0f} mm2 under the back panel, right below the card and the module (it was 207), plus two baffle slits "
       f"{slit_a:.0f} mm2 at the front: {slit_a + rear:.0f} in all", rear >= 800 and slit_a + rear >= VENT_MIN)
    ok(f"air out: slot along the top {outlet:.0f} mm2, {Y_TOP - BASE_TOP:.0f} mm higher, hidden {pl.AXLE_Y + pl.WALL_R - Y_TOP:.0f} mm below the wall's top",
       outlet >= VENT_MIN)
    note(f"heat is an ESTIMATE, not a measurement: {POWER_W:.0f} W inside (3.4 to 9.5), air at the top rear judged 10 to 25 C above the "
         f"room. PLA lets go at 57 C, PETG at 69 C: print the sled in PETG (it cradles the module), and the shell too if you have "
         f"the filament. Rehearse 10 minutes of real charging with a hand on the top rear of the shell and on the sled's face plate")

    # ---- 8. the printer
    feats = {"shell wall": T, "wall round the window": WIN_WALL, "baffle (through the slab)": BAFFLE_T / math.sqrt(2), "baffle tip": BAFFLE_FLAT,
             "fork": FORK_T, "card rib": 2.0, "side stop": STOP_T, "clip": CLIP_T, "thin spot over the light": GLOW_SKIN, "ledge": LEDGE_T,
             "rail": RAIL_T, "foot": FOOT_T, "sled floor": SLED_FLOOR, "tray wall": TRAY_WALL, "face plate": FACE_T, "tray lip": 1.0,
             "peg tip": PEG_X - 2 * tipw}
    thin = min(feats, key=feats.get)
    ok(f"0.4 mm nozzle: shell wall {T} mm, thinnest feature is the {thin} at {feats[thin]:.1f} mm (two lines = {MIN_FEATURE})", feats[thin] >= MIN_FEATURE - 1e-6 and T >= 1.6)
    note("lay the shell on its BACK when it is off the machine. Stood upright on a desk it stands on its two pegs. A snapped "
         "peg may be glued back: it only locates")
    return res, dict(fr=fr, motor=motor, pins=pins, nuts=nuts)


def printer_checks(files):
    """Run on the exported meshes, in the orientation they will be printed in."""
    import trimesh
    res = []
    half = plate_rules.PLATE / 2 - plate_rules.EDGE
    for name, path, patches_allowed in files:
        m = trimesh.load(path, force="mesh")
        ext = m.bounding_box.extents
        res.append((f"{name}: {ext[0]:.0f} x {ext[1]:.0f} on the plate, {ext[2]:.0f} tall, fits {plate_rules.PLATE:.0f} with {plate_rules.EDGE:.0f} mm at the edge",
                    ext[0] <= 2 * half and ext[1] <= 2 * half and ext[2] <= 250))
        patches, span = overhang_census(m)
        area = sum(p[0] for p in patches)
        res.append((f"{name}: no supports. Every face leans 45 degrees or less except {len(patches)} flat bridges "
                    f"({area:.0f} mm2 in all, longest span {span:.0f} mm, limit {MAX_BRIDGE:.0f})",
                    len(patches) <= patches_allowed and span <= MAX_BRIDGE))
    return res


def mesh_gate(path, bodies=1):
    cmd = [sys.executable, MESH_GATE, path] + (["--bodies", str(bodies)] if bodies != 1 else [])
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()
    line = out[-1] if out else "no output"
    return line, line.startswith("PASS")


FILES = {"coupons": "1_cover_coupons.stl", "shell": "2_cover_shell.stl", "sled": "3_module_sled_PLACEHOLDER_do_not_print_yet.stl"}


def show(lines):
    mark = {True: "ok", False: "NO", NOTE: "note"}
    for text, state in lines:
        print(f"[{mark[state]}] {text}")
    return [t for t, state in lines if state is False]


# ============================================================ main
if __name__ == "__main__":
    quick = "--quick" in sys.argv
    sh, sl = shell(), sled()
    res, _ = check(sh, sl, quick)
    bad = show(res)
    n_ok = sum(1 for _, s in res if s is True)
    n_note = sum(1 for _, s in res if s == NOTE)
    print(f"-- {n_ok} checks ok, {len(bad)} failed, {n_note} notes (a note is NOT a pass)")
    if bad:
        sys.exit(f"{len(bad)} checks failed: nothing exported")

    os.makedirs(OUT, exist_ok=True)
    kw = dict(tolerance=0.02, angularTolerance=0.15)
    f_shell, f_sled, f_coup = (os.path.join(OUT, FILES[k]) for k in ("shell", "sled", "coupons"))
    cq.exporters.export(as_printed(sh, Z_BACK), f_shell, **kw)
    cq.exporters.export(as_printed(sl, IN_Z), f_sled, **kw)
    placed_s = pack([(f_shell, 0, 0, 0)], f_shell)          # the slicer centres it: judge it as it will land
    cps = coupons(sh)
    tmp = []
    for name, part in cps.items():
        p = os.path.join(OUT, f"_tmp_{name}.stl")
        bbz = part.val().BoundingBox().zmin
        cq.exporters.export(part.translate((0, 0, -bbz)), p, **kw)
        tmp.append(p)
    placed_c = pack_rows(tmp, f_coup, plate_rules.GAP)
    c_vol = sum(part.val().Volume() for part in cps.values()) / 1000
    for p in tmp:
        os.remove(p)

    late = printer_checks([("shell", f_shell, 4), ("sled", f_sled, 1)])     # shell: two clips, the light spot, the window. Sled: the socket hole
    good, _ = plate_ok(placed_s, plate_rules.GAP)
    late.append((f"job 2 is the shell ALONE on the plate (no placeholder sled packed with it any more): inside the edge margin and "
                 f"clear of the P1S's reserved corner", good))
    good, gap = plate_ok(placed_c, plate_rules.GAP)
    late.append((f"job 1, the coupons: {len(cps)} test pieces ({c_vol:.0f} cm3), {gap:.1f} mm apart at the nearest (rule {plate_rules.GAP:.0f})", good))
    for path, n in ((f_coup, len(cps)), (f_shell, 1), (f_sled, 1)):
        line, good = mesh_gate(path, n)
        late.append((f"mesh gate: {line.replace(OUT + os.sep, '')}", good))
    vol = sh.val().Volume() / 1000
    late.append((f"shell {vol:.0f} cm3: about {vol * 1.24:.0f} g of PLA or {vol * 1.27:.0f} g of PETG; sled {sl.val().Volume() / 1000:.1f} cm3", vol < 260))
    late.append((f"print time is NOT sliced. My guess: 7 to 8 hours for the shell at 0.2 mm, 1 hour for the coupons, 20 minutes for a sled", NOTE))
    bad = show(late)
    if bad:
        for f in (f_shell, f_sled, f_coup):
            os.remove(f)
        sys.exit(f"{len(bad)} print checks failed: the STL files were removed again")
    print(f"exported to {OUT}: " + ", ".join(FILES[k] for k in ("coupons", "shell", "sled")))
