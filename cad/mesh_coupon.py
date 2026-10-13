"""Mesh coupon: the FIRST print of this project, about an hour.

Two small herringbone gears printed ALREADY IN MESH, exactly as the real
gearset is, plus a plate with two pegs at the centre distance. Pull the gears
apart sideways, drop them on the pegs, spin one. It tells you three things
about YOUR printer before a 15 hour gearset depends on them:

  - do gears printed in mesh come apart, or do the flanks fuse?
  - does the smallest tooth count allowed (17) print cleanly at this module?
  - is the bore clearance a free-spinning fit?

    .venv/bin/python cad/mesh_coupon.py [module]

With no argument it uses the module from design.transmission() once that is
filled in, and 2.0 until then.
"""
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gears
from planetary import PIP_BACKLASH

# ============================================================
# PARAMETERS (mm)
# ============================================================
Z_SMALL, Z_LARGE = 17, 25      # 17 is the smallest the train may use
WIDTH = 8.0                    # face width
BORE = 8.3                     # gear bore, runs on the peg
PEG = 8.0                      # peg diameter: 0.3 diametral clearance
PEG_EXTRA = 1.0                # peg stands this far above the gear
PLATE_T = 3.0
PLATE_MARGIN = 6.0             # plate edge beyond the gear tips
SHOULDER_D, SHOULDER_H = 13.0, 0.6   # gears ride on these, not on the plate
CORNER_R = 4.0

def _module():
    if len(sys.argv) > 1:
        return float(sys.argv[1])
    try:
        import design
        return float(design.transmission()["module"])
    except NotImplementedError:
        return 2.0

MODULE = _module()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

def build():
    a = gears.centre_distance(Z_SMALL, Z_LARGE, MODULE)
    small = gears.gear(Z_SMALL, MODULE, WIDTH, BORE, hand=+1, backlash=PIP_BACKLASH)
    large = gears.gear(Z_LARGE, MODULE, WIDTH, BORE, hand=-1, backlash=PIP_BACKLASH)

    tip_s, tip_l = MODULE * (Z_SMALL + 2) / 2, MODULE * (Z_LARGE + 2) / 2
    x0, x1 = -tip_s - PLATE_MARGIN, a + tip_l + PLATE_MARGIN
    half_w = tip_l + PLATE_MARGIN
    plate = (cq.Workplane("XY").center((x0 + x1) / 2, 0)
             .rect(x1 - x0, 2 * half_w).extrude(PLATE_T)
             .edges("|Z").fillet(CORNER_R))
    for x in (0.0, a):
        plate = plate.union(cq.Workplane("XY").workplane(offset=PLATE_T).center(x, 0)
                            .circle(SHOULDER_D / 2).extrude(SHOULDER_H))
        plate = plate.union(cq.Workplane("XY").workplane(offset=PLATE_T).center(x, 0)
                            .circle(PEG / 2).extrude(SHOULDER_H + WIDTH + PEG_EXTRA))
    return a, small, large, plate

def check(a, small, large, plate):
    res = gears.pair_checks(Z_SMALL, Z_LARGE, MODULE, PIP_BACKLASH)
    z_seat = PLATE_T + SHOULDER_H
    s = small.translate((0, 0, z_seat))
    l = large.rotate((0, 0, 0), (0, 0, 1), gears.mesh_angle(Z_LARGE)).translate((a, 0, z_seat))
    for name, body in (("small gear", small), ("large gear", large), ("plate", plate)):
        res.append((f"{name} is one solid", body.solids().size() == 1))
    v = s.intersect(l).val().Volume() if s.intersect(l).solids().size() else 0.0
    res.append((f"assembled gears do not intersect in 3D ({v:.4f} mm3): hands are opposite", v < 1e-3))
    for name, g in (("small", s), ("large", l)):
        hit = g.intersect(plate)
        v = hit.val().Volume() if hit.solids().size() else 0.0
        res.append((f"{name} gear clears its peg and the plate ({v:.4f} mm3)", v < 1e-3))
    res.append((f"bore clearance {BORE - PEG:.2f} mm on diameter", 0.2 <= BORE - PEG <= 0.5))
    bb = plate.val().BoundingBox()
    res.append((f"plate {bb.xlen:.0f} x {bb.ylen:.0f} mm fits the bed", max(bb.xlen, bb.ylen) <= 240))
    return res, s, l

if __name__ == "__main__":
    a, small, large, plate = build()
    res, s, l = check(a, small, large, plate)
    for text, ok in res:
        print(f"[{'ok' if ok else 'NO'}] {text}")
    if not all(ok for _, ok in res):
        sys.exit("checks failed: nothing exported")
    os.makedirs(OUT, exist_ok=True)
    kw = dict(tolerance=0.01, angularTolerance=0.1)
    z_seat = PLATE_T + SHOULDER_H
    pair = cq.Compound.makeCompound([s.translate((0, 0, -z_seat)).val(), l.translate((0, 0, -z_seat)).val()])
    cq.exporters.export(cq.Workplane("XY").newObject([pair]), os.path.join(OUT, "coupon_pair_print_in_place.stl"), **kw)
    cq.exporters.export(plate, os.path.join(OUT, "coupon_plate.stl"), **kw)
    # assembled view, for the preview render only. Not a print file.
    cq.exporters.export(plate.union(s).union(l), os.path.join(OUT, "_coupon_assembled_VIEW_ONLY.stl"), **kw)
    print(f"module {MODULE}, centre distance {a:.2f} mm -> {OUT}")
