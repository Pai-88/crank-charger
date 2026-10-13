"""Click-on frame: the stand (wall, base, gussets) with the electronics cover held by clicks, not by clamps.

    .venv/bin/python cad/frame_click.py            checks, then cad/stl/spares/frame_click.stl (+ view mesh)

The frame is planetary.frame() untouched (same wall, motor pocket, pin bosses, gussets, base holes), plus:
  GROOVES  the cover's two pegs used to need the cover lifted 3 mm and dropped. Each peg now has a groove in
           the base's top face, open at the back edge, so the cover slides on FLAT from behind.
  LIPS     four rigid ledges over the cover's feet: two on the inside of the outer gussets (front), two on
           the outboard plates (rear). The feet slide under them; the cover cannot lift.
  LATCHES  each outboard plate runs on behind the base as a 30 mm spring blade with a hook at its end. The
           cover's feet push the two blades apart on the way in; at home the hooks spring in behind the feet:
           two clicks. The hook's catch is at 50 degrees (it must print without support), so it is a firm
           detent, not a dead lock: pull the cover straight back, or thumb the two blade tips apart, to take
           it off.
  FILLET   a 6 mm web in the corner where the base meets the wall, between and outside the cover's walls.
  TEXT     "Designed With Love By Paing" sunk 0.6 mm into the front face, along the bottom under the wheel.
Push the cover forward on the base until both sides click. The G-clamps still clamp the base to the table
(on the cover's feet, as before); they no longer have to hold the cover.

Fits the cover exactly as exported (cad/stl/cover/2_cover_shell.stl): nothing on the cover changes.
Printed like the old frame: front face on the bed, no supports. Every added shape starts with a 45 degree
underside. Nothing in planetary.py or wire_cover.py is changed.
"""
import math
import os
import subprocess
import sys

import cadquery as cq
from shapely.geometry import LineString

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import planetary as P                  # read only
import wire_cover as wc                # read only: the cover this frame has to fit

OUT = os.path.join(HERE, "stl", "spares")
VIEW = os.path.join(ROOT, "assembly", "_build", "frame_click")
MESH_GATE = os.path.expanduser("~/.claude/skills/print-export-check/scripts/mesh_check.py")
NOTE = "note"

# ---------------------------------------------------------------- the numbers (mm)
FOOT_TOP = wc.BASE_TOP + wc.FOOT_T              # 12: top face of the cover's feet
LIP_PLAY = 0.6                                  # air between a foot's top face and a lip
LIP_Y0 = FOOT_TOP + LIP_PLAY                    # 12.6
LIP_T = 2.6
LIP_Y1 = LIP_Y0 + LIP_T                         # 15.2
# front lips, on the inner faces of the two outer gussets
G_FACE = wc.OUTER_IN                            # 100
LIP_IN = 4.0                                    # reaches in to x 96; the foot's edge is at 99
LIP_ZS, LIP_Z1 = -18.0, -44.0                   # starts (45 degrees) at -18, full from -22; ends clear of the clamp's pad
# grooves for the cover's pegs
GROOVE_HW, GROOVE_D = 2.6, 3.8                  # half width, depth (the peg is 3.0 wide, 3.0 long)
# outboard plates on the base's two side faces
SIDE = P.BASE_HALF_W                            # 105
GAP = 0.8                                       # slit between plate and base side, and air beside the foot's edge
PX0 = SIDE + GAP                                # 105.8
PLATE_T = 2.4
PX1 = PX0 + PLATE_T                             # 108.2
PY0, PY1 = 1.0, LIP_Y1
ZS = -50.0                                      # where the plate starts to grow out of the base's side
LIP2_IN = 3.0                                   # rear lip reaches in to x 102.8; the foot's wide edge is at 105
LIP2_Z1 = -70.0
BLADE_Z0 = -71.0                                # behind this the plate is free of the base: the spring blade
BARB_IN = 1.9                                   # the hook reaches in to x 103.9
CATCH_DEG, RAMP_DEG = 50.0, 35.0                # catch face and lead-in, measured from the sliding direction
CATCH_GAP = 0.3                                 # the cover can move back this far before the hooks start to work
FILLET = 6.0
FILLET_X = ((-66.0, 66.0), (74.0, G_FACE + 0.5), (-G_FACE - 0.5, -74.0))
TEXT = "Designed With Love By Paing"
TEXT_DEPTH = 0.6
TEXT_W, TEXT_H, TEXT_YC = 176.0, 10.5, 8.0      # the band it has to fit in, and its centre height
FONT = "/System/Library/Fonts/Avenir Next.ttc"
E_PETG, MU = 2000.0, 0.3

_t = math.tan(math.radians(CATCH_DEG))
ZB = wc.Z_BACK - CATCH_GAP + (PX0 - SIDE) / _t                  # catch face where it leaves the blade
Z_TIP = ZB - BARB_IN / _t
Z_FLAT = Z_TIP - 0.4
Z_END = Z_FLAT - BARB_IN / math.tan(math.radians(RAMP_DEG))     # the blade's far end


def half(n, d, size=900.0):
    """The half-space {p : n . p <= d} as a big block (n need not be a unit vector)."""
    v = cq.Vector(*n)
    u = v.multiply(1.0 / v.Length)
    o = u.multiply(d / v.Length)
    return cq.Workplane(cq.Plane(origin=o.toTuple(), normal=u.toTuple())).rect(size, size).extrude(-size)


def front_lip():
    """+X side. A rib on the outer gusset's inner face, over the foot's outer edge."""
    lip = wc._box(G_FACE - LIP_IN, G_FACE + 0.5, LIP_Y0, LIP_Y1, LIP_Z1, LIP_ZS)
    lip = lip.intersect(half((-1, 0, 1), -G_FACE + LIP_ZS))                      # grows inward from the gusset at 45 degrees
    lead = [(LIP_Y0 - 0.05, LIP_Z1 - 0.05), (LIP_Y0 + 1.0, LIP_Z1 - 0.05), (LIP_Y0 - 0.05, LIP_Z1 + 1.0)]
    return lip.cut(wc._prism_yz(lead, G_FACE - LIP_IN - 0.1, G_FACE + 0.6))      # lead-in where the foot enters


def plate():
    """+X side, the rigid part: web onto the base's side, the plate itself, the rear lip."""
    h_a = half((1, 0, 1), SIDE + ZS)                                             # grows out of the base's side face
    h_b = half((1, 1, 1), SIDE + wc.BASE_TOP + ZS)                               # ... and, above the base, upward
    h_c = half((-1, 1, 1), SIDE + wc.BASE_TOP + ZS - 2 * PX0)                    # the lip grows inward from the plate
    web = wc._prism_xz([(SIDE - 0.5, ZS + 1), (PX0 + 0.2, ZS + 1), (PX0 + 0.2, BLADE_Z0 - GAP), (SIDE, BLADE_Z0),
                        (SIDE - 0.5, BLADE_Z0)], PY0, wc.BASE_TOP).intersect(h_a)
    low = wc._box(PX0, PX1, PY0, wc.BASE_TOP, Z_END, ZS + 1).intersect(h_a)
    up = wc._box(PX0, PX1, wc.BASE_TOP - 0.1, PY1, Z_END, ZS + 1).intersect(h_a).intersect(h_b)
    lip = wc._box(PX0 - LIP2_IN, PX0 + 0.2, LIP_Y0, LIP_Y1, LIP2_Z1, ZS + 1).intersect(h_b).intersect(h_c)
    lead = [(LIP_Y0 - 0.05, LIP2_Z1 - 0.05), (LIP_Y0 + 1.0, LIP2_Z1 - 0.05), (LIP_Y0 - 0.05, LIP2_Z1 + 1.0)]
    lip = lip.cut(wc._prism_yz(lead, PX0 - LIP2_IN - 0.1, PX0 + 0.3))
    return web.union(low).union(up), lip


def barb():
    """+X side: the hook at the end of the spring blade."""
    pts = [(PX0 + 0.2, ZB + 0.2 / _t), (PX0 - BARB_IN, Z_TIP), (PX0 - BARB_IN, Z_FLAT), (PX0 + 0.2, Z_END)]
    return wc._prism_xz(pts, PY0, PY1)


def fillets():
    tri = [(wc.BASE_TOP - 0.5, wc.WALL_BACK + 0.5), (wc.BASE_TOP + FILLET, wc.WALL_BACK + 0.5), (wc.BASE_TOP + FILLET, wc.WALL_BACK),
           (wc.BASE_TOP, wc.WALL_BACK - FILLET), (wc.BASE_TOP - 0.5, wc.WALL_BACK - FILLET)]
    return [wc._prism_yz(tri, x0, x1) for x0, x1 in FILLET_X]


def grooves():
    return [wc._box(bx - GROOVE_HW, bx + GROOVE_HW, wc.BASE_TOP - GROOVE_D, wc.BASE_TOP + 0.5, wc.BASE_BACK - 1.0, bz)
            for bx, bz in wc.PEG_HOLES]


def lettering():
    def make(size):
        return (cq.Workplane("XY").workplane(offset=-TEXT_DEPTH)
                .text(TEXT, size, TEXT_DEPTH + 0.5, fontPath=FONT, kind="bold", halign="center", valign="center"))
    bb = make(10.0).val().BoundingBox()
    size = 10.0 * min(TEXT_W / bb.xlen, TEXT_H / bb.ylen)
    t = make(size)
    bb = t.val().BoundingBox()
    return t.translate((-(bb.xmin + bb.xmax) / 2, TEXT_YC - (bb.ymin + bb.ymax) / 2, 0)), bb.xlen, bb.ylen


def parts():
    """name -> solid for every added piece, both sides."""
    out = {}
    fl, (pl, lip2), bb = front_lip(), plate(), barb()
    for tag, f in (("R", lambda s: s), ("L", lambda s: s.mirror("YZ"))):
        out["lip_front_" + tag], out["plate_" + tag], out["lip_rear_" + tag], out["barb_" + tag] = f(fl), f(pl), f(lip2), f(bb)
    for k, s in enumerate(fillets()):
        out[f"fillet_{k}"] = s
    return out


def frame(pc=None, text=True, barbs=True):
    pc = pc or parts()
    f = P.frame()
    for g in grooves():
        f = f.cut(g)
    for name, s in pc.items():
        if barbs or not name.startswith("barb"):
            f = f.union(s)
    if text:
        f = f.cut(lettering()[0])
    return f


# ---------------------------------------------------------------- checks
def moved(s, dx=0.0, dy=0.0, dz=0.0):
    return s.translate((dx, dy, dz))


def check(pc, rigid, shell):
    res = []
    vol = P._vol
    added = [s for n, s in pc.items()]
    lips = {n: s for n, s in pc.items() if n.startswith("lip")}
    hooks = {n: s for n, s in pc.items() if n.startswith("barb")}

    v = vol(rigid, shell)
    res.append((f"cover at home on the new frame (hooks left out): {v:.2f} mm3 of overlap", v < 0.5))
    for dx in (-wc.FORK_CLEAR, wc.FORK_CLEAR):
        v = vol(rigid, moved(shell, dx=dx))
        res.append((f"cover pushed {dx:+.1f} mm sideways (all its forks allow): {v:.2f} mm3 of overlap", v < 0.5))
    v = max(vol(h, shell) for h in hooks.values())
    res.append((f"hooks against the cover at home: {v:.2f} mm3 (they stand {CATCH_GAP:.1f} mm behind the feet)", v < 0.5))

    worst = 0.0
    for s_back in (3.0, 8.0, 15.0, 25.0, 40.0, 60.0):                      # the slide, flat on the base
        worst = max(worst, vol(rigid, moved(shell, dz=-s_back)))
    res.append((f"sliding the cover on flat, 60 mm to 3 mm from home, six places: worst overlap {worst:.2f} mm3 "
                f"(pegs in their grooves, feet under the lips)", worst < 0.5))

    v_old = vol(P.frame(), moved(shell, dz=-8.0))                           # negative control: the check must be able to fail
    res.append((f"control: the same slide on the OLD frame (no grooves) collides by {v_old:.0f} mm3 at 8 mm from home, so the slide check can see a clash",
                v_old > 5.0))

    up = moved(shell, dy=1.5)
    held = {n: vol(s, up) for n, s in lips.items()}
    res.append((f"cover lifted 1.5 mm: every lip bites (" + ", ".join(f"{n[4:]} {v:.0f}" for n, v in held.items()) + " mm3)",
                all(v > 3.0 for v in held.values())))
    back = moved(shell, dz=-(CATCH_GAP + 1.2))
    bite = {n: vol(s, back) for n, s in hooks.items()}
    res.append((f"cover pulled back {CATCH_GAP + 1.2:.1f} mm: both hooks bite (" + ", ".join(f"{n[5:]} {v:.1f}" for n, v in bite.items()) + " mm3)",
                all(v > 1.0 for v in bite.values())))

    other = {"sled": wc.sled(), "card": wc.card_dummy(), "clamp +": wc.clamp_dummy(1), "clamp -": wc.clamp_dummy(-1)}
    other.update({"module " + k: s for k, s in wc.module_dummy().items()})
    other.update({"tester " + k: s for k, s in wc.tester_dummy().items()})
    hit = {n: sum(vol(a, s) for a in added) for n, s in other.items()}
    res.append((f"nothing added touches the sled, card, module, USB tester or either G-clamp "
                f"(worst {max(hit.values()):.2f} mm3: {max(hit, key=hit.get)})", max(hit.values()) < 0.5))

    # ---- the numbers behind the click
    foot_edge = wc.FOOT_X_WIDE
    over_front = wc.FOOT_X1 - (G_FACE - LIP_IN)
    over_rear = foot_edge - (PX0 - LIP2_IN)
    res.append((f"front lips cover the feet's edges by {over_front:.1f} mm, rear lips by {over_rear:.1f} mm, {LIP_PLAY:.1f} mm of air above the foot",
                over_front >= 2.0 and over_rear >= 1.5))
    res.append((f"front lip ends at z {LIP_Z1:.0f}; the G-clamp's pad sits from z -68 to -46: {LIP_Z1 + 46:.0f} mm between them",
                LIP_Z1 + 46 >= 1.5))
    gus_top = 68.0 + LIP_Z1                                                  # outer gusset's edge at the lip's rear end (60 high, 52 deep)
    res.append((f"the outer gusset is {gus_top:.0f} mm high where the front lip ends, the lip tops out at {LIP_Y1:.1f}", gus_top > LIP_Y1 + 3))
    peg_half = wc.PEG_X / 2 + wc.FORK_CLEAR
    res.append((f"peg grooves {2 * GROOVE_HW:.1f} wide, {GROOVE_D:.1f} deep for a peg {wc.PEG_X:.1f} wide (plus {wc.FORK_CLEAR:.1f} side play), {wc.PEG_LEN:.1f} long",
                GROOVE_HW >= peg_half + 0.4 and GROOVE_D >= wc.PEG_LEN + 0.5))
    overlap = foot_edge - (PX0 - BARB_IN)
    arm = BLADE_Z0 - (wc.Z_BACK - CATCH_GAP)
    I = (PY1 - PY0) * PLATE_T ** 3 / 12
    k = 3 * E_PETG * I / arm ** 3
    strain = 3 * (PLATE_T / 2) * overlap / arm ** 2 * 100
    strain_max = 3 * (PLATE_T / 2) * (overlap + wc.FORK_CLEAR) / arm ** 2 * 100
    res.append((f"hooks reach {overlap:.1f} mm in behind each foot ({overlap - wc.FORK_CLEAR:.1f} to {overlap + wc.FORK_CLEAR:.1f} with the cover's side play)",
                overlap - wc.FORK_CLEAR >= 0.5))
    res.append((f"spring blade {arm:.0f} mm long, {PLATE_T:.1f} thick, {PY1 - PY0:.1f} high: {k:.1f} N per mm; bent {overlap:.1f} mm it strains "
                f"{strain:.2f} percent ({strain_max:.2f} at worst). It bends ACROSS the layers, so the limit used is 0.8", strain_max <= 0.8))
    p = k * overlap
    ta, tr = math.tan(math.radians(CATCH_DEG)), math.tan(math.radians(RAMP_DEG))
    hold = 2 * p * (MU + ta) / (1 - MU * ta)
    push = 2 * p * (MU + tr) / (1 - MU * tr)
    res.append((f"to click on: about {push:.0f} N of push. To pull off again: about {hold:.0f} N straight back (the cover weighs about 2.3 N)",
                hold >= 8.0 and push <= 25.0))
    res.append((f"hook's catch at {CATCH_DEG:.0f} degrees: that is its overhang on the printer, no support needed", CATCH_DEG <= 55.0))
    res.append((f"frame is now {2 * PX1:.1f} mm wide (was {2 * SIDE:.0f}) and {abs(Z_END):.1f} mm tall on the bed (was 93)", 2 * PX1 <= 240.0))
    line = LineString([(-200, TEXT_YC + TEXT_H / 2 + 1), (200, TEXT_YC + TEXT_H / 2 + 1)])
    wall_w = P.wall_outline().intersection(line).length
    _, tw, th = lettering()
    res.append((f"lettering {tw:.0f} x {th:.1f} mm, {TEXT_DEPTH:.1f} deep, on the front face under the wheel: the wall is {wall_w:.0f} mm wide there, "
                f"solid up to y {wc.WIN_Y0:.0f}", tw + 8 <= wall_w and TEXT_YC + th / 2 + 2 <= wc.WIN_Y0))
    res.append(("the wall, motor pocket, pin bosses, five gussets and three base holes are planetary.frame(), unchanged", NOTE))
    res.append(("not checked by geometry: the wires (they run inside the cover, nothing here is inside it except the corner web)", NOTE))
    res.append(("the hooks are a detent, not a dead lock: a hard pull straight back takes the cover off", NOTE))
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
    pc = parts()
    rigid = frame(pc, text=False, barbs=False)
    bad = show(check(pc, rigid, wc.shell()))
    if bad:
        sys.exit(f"{len(bad)} checks failed: nothing exported")
    full = frame(pc)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(VIEW, exist_ok=True)
    kw = dict(tolerance=0.03, angularTolerance=0.15)
    f = os.path.join(OUT, "frame_click.stl")
    cq.exporters.export(full.rotate((0, 0, 0), (1, 0, 0), 180), f, **kw)        # front face down on the bed, as the old frame
    line, ok = mesh_gate(f)
    print(f"[{'ok' if ok else 'NO'}] {line}")
    vol = full.val().Volume() / 1000
    print(f"[ok] {vol:.0f} cm3, about {vol * 1.27:.0f} g of PETG (the old frame: {P.frame().val().Volume() / 1000:.0f} cm3)")
    cq.exporters.export(full, os.path.join(VIEW, "frame_click_view.stl"), **kw)   # model frame, for the pictures
    body = P.frame()                                                             # the pictures colour the new pieces: body and pieces apart
    for g in grooves():
        body = body.cut(g)
    cq.exporters.export(body.cut(lettering()[0]), os.path.join(VIEW, "body_view.stl"), **kw)
    new = None
    for s_ in pc.values():
        new = s_ if new is None else new.union(s_)
    cq.exporters.export(new, os.path.join(VIEW, "new_view.stl"), **kw)
    if not ok:
        sys.exit("mesh gate failed")
    print(f"wrote {f}")
