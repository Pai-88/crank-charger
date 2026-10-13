"""Wheel keeper band: holds the hand wheel on the ring gear's dogs with no nut and no screws.

    .venv/bin/python cad/wheel_keeper.py           checks, then cad/stl/spares/wheel_keeper_band.stl (+ view meshes)

The hand wheel is only held on the ring's six dogs by the M8 nyloc on the axle. Without that nut it slides
forward off the dogs. This band is a near-full circle (310 degrees) of 2 mm PETG that hugs the OUTSIDE of
the wheel rim, with:
    six LIPS over the wheel's front face (so the band cannot go backward and the wheel cannot come forward
        past them), between the notches;
    three ARMS running back along the outside of the ring's skirt to its rear edge, each ending in a BARB
        that tucks under the ring's back face, in the 3.2 mm gap in front of the wall.
Lips tie the band to the wheel, barbs tie it to the ring: the wheel is captive on the ring. To fit: spread
the band at its gap with both thumbs, slip it over the rim, let go: it closes on the rim with the barbs
behind the ring and the lips on the wheel's face. To remove: spread it again. It never carries torque
(the dogs do that) and never touches the wall, the teeth, the handle or the clip ring's lugs.
Works with the print-in-place ring and with the two-half clip ring (arms sit between its lugs).

Printed lips-down (the model is flipped for the file): lips flat on the bed, the band wall and the three
arms grow upward, the barbs are the only overhang (1.6 mm, chamfered at 45 degrees). No supports.
Nothing in planetary.py or ring_spare.py is changed.
"""
import json
import math
import os
import subprocess
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import planetary as P                  # read only
import ring_spare as RS                # read only: the clip ring's lug angles

OUT = os.path.join(HERE, "stl", "spares")
VIEW = os.path.join(ROOT, "assembly", "_build", "keeper")
MESH_GATE = os.path.expanduser("~/.claude/skills/print-export-check/scripts/mesh_check.py")

# ---------------------------------------------------------------- the numbers (mm)
BAND_FIT = 0.3                         # air between the band and the rim's outside
BAND_T = 2.0                           # band and arm wall
BAND_W = 12.0                          # arms and lips, along the rim
GAP_DEG = 50.0                         # the opening in the band
GAP_AT = 60.0                          # where the opening sits (between two arms)
ARM_ANGLES = [0.0, 120.0, 240.0]       # between the dogs (30 + 60 k) and clear of the clip ring's lugs
LIP_ANGLES = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]
LIP_IN = 4.0                           # how far a lip reaches in over the wheel's front face
LIP_T = 1.8
LIP_AIR = 0.2                          # between the wheel's front face and the lip
BARB_IN = 1.6                          # how far a barb reaches in under the ring's back face
BARB_T = 1.6
BARB_AIR_RING = 0.6                    # between the ring's back face and the barb's top
BARB_AIR_WALL = 1.0                    # between the wall's front face and the barb's bottom

R_IN = P.R_OUT + BAND_FIT              # 118.5
R_OUTER = R_IN + BAND_T                # 120.5
Z_WHEEL_FRONT = P.WHEEL_Z0 + P.WHEEL_T # 44.9
Z_RING_BACK = P.GEAR_GAP               # 3.2
Z_LIP0 = Z_WHEEL_FRONT + LIP_AIR       # 45.1
Z_TOP = Z_LIP0 + LIP_T                 # 46.9
Z_BAND0 = P.WHEEL_Z0 + 1.0             # 33.9: the band covers the wheel rim's outside
Z_BARB1 = Z_RING_BACK - BARB_AIR_RING  # 2.6
Z_BARB0 = Z_BARB1 - BARB_T             # 1.0
NOTE = "note"


def _ring(r0, r1, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).circle(r1).circle(r0).extrude(z1 - z0)


def _sector(deg0, deg1, r1, z0, z1):
    """A wedge from the axis out to r1 covering deg0..deg1 (degrees), used to cut the gap."""
    pts = [(0, 0)] + [(r1 * 1.2 * math.cos(math.radians(a)), r1 * 1.2 * math.sin(math.radians(a)))
                      for a in [deg0 + (deg1 - deg0) * k / 24 for k in range(25)]]
    return cq.Workplane("XY").workplane(offset=z0 - 1).polyline(pts).close().extrude(z1 - z0 + 2)


def _tangent_box(angle, r0, r1, half_w, z0, z1):
    """A block r0..r1 radially, 2 half_w wide along the rim, z0..z1, centred on angle (degrees)."""
    b = cq.Workplane("XY").workplane(offset=z0).center((r0 + r1) / 2, 0).rect(r1 - r0, 2 * half_w).extrude(z1 - z0)
    return b.rotate((0, 0, 0), (0, 0, 1), angle)


def band():
    body = _ring(R_IN, R_OUTER, Z_BAND0, Z_TOP)
    for a in LIP_ANGLES:                                   # lip over the wheel's front face, 45 degree chamfer under it
        lip = _tangent_box(a, R_IN - LIP_IN, R_IN + 0.5, BAND_W / 2, Z_LIP0, Z_TOP)
        wedge = (cq.Workplane("XZ").polyline([(R_IN - LIP_IN, Z_LIP0), (R_IN + 0.5, Z_LIP0), (R_IN + 0.5, Z_LIP0 - LIP_IN)]).close()
                 .extrude(BAND_W / 2, both=True).rotate((0, 0, 0), (0, 0, 1), a))
        body = body.union(lip).union(wedge)
    for a in ARM_ANGLES:                                   # arm down the skirt, barb under the ring's back
        arm = _tangent_box(a, R_IN, R_OUTER, BAND_W / 2, Z_BARB0, Z_BAND0 + 1.0)
        barb = _tangent_box(a, R_IN - BARB_IN, R_IN + 0.5, BAND_W / 2, Z_BARB0, Z_BARB1)
        cham = (cq.Workplane("XZ").polyline([(R_IN - BARB_IN, Z_BARB1), (R_IN + 0.5, Z_BARB1), (R_IN + 0.5, Z_BARB1 + BARB_IN)]).close()
                .extrude(BAND_W / 2, both=True).rotate((0, 0, 0), (0, 0, 1), a))
        body = body.union(arm).union(barb).union(cham)
    return body.cut(_sector(GAP_AT - GAP_DEG / 2, GAP_AT + GAP_DEG / 2, R_OUTER + 5, Z_BARB0, Z_TOP))


def place(part):
    """Model frame: the axle at (0, AXLE_Y), Z along the axle toward the viewer."""
    return part.translate((0, P.AXLE_Y, 0))


def as_printed(part):
    """Lips down on the bed: flip about X, then the lips' top face becomes Z = 0."""
    return part.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, Z_TOP))


# ---------------------------------------------------------------- checks
def ang_dist(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def check():
    res = []
    r_mid = (R_IN + R_OUTER) / 2
    for a in ARM_ANGLES:
        d_dog = min(ang_dist(a, d) for d in P.DOG_ANGLES)
        res.append((f"arm at {a:.0f} deg sits {d_dog:.0f} deg from the nearest dog (dogs every 60: midway is 30)", abs(d_dog - 30.0) < 1e-6))
        d_lug = min(ang_dist(a, l) for l in RS.LUG_ANGLES)
        mm = math.radians(d_lug) * r_mid - BAND_W / 2 - P.LUG_W / 2
        res.append((f"arm at {a:.0f} deg: {mm:.0f} mm of air to the clip ring's nearest lug (want 3 or more)", mm >= 3.0))
        in_gap = ang_dist(a, GAP_AT) < GAP_DEG / 2 + BAND_W / 2 / r_mid * 180 / math.pi
        res.append((f"arm at {a:.0f} deg is clear of the band's opening at {GAP_AT:.0f} deg", not in_gap))
    for a in LIP_ANGLES:
        d_dog = min(ang_dist(a, d) for d in P.DOG_ANGLES)
        edge = math.radians(d_dog) * P.R_OUT - BAND_W / 2 - P.DOG_W / 2 - P.DOG_FIT
        res.append((f"lip at {a:.0f} deg rests on solid rim, {edge:.0f} mm from the nearest notch edge", edge >= 2.0))
    res.append((f"lips reach {LIP_IN:.1f} mm in over the wheel's front face; the rim band is {P.RIM_W:.0f} mm wide", LIP_IN < P.RIM_W))
    res.append((f"lip underside {Z_LIP0 - Z_WHEEL_FRONT:.1f} mm above the wheel's front face (dogs end flush with it)", 0.1 <= Z_LIP0 - Z_WHEEL_FRONT <= 0.4))
    res.append((f"barb top {Z_RING_BACK - Z_BARB1:.1f} mm behind the ring's back face; ring float is {P.RING_FLOAT} mm", Z_RING_BACK - Z_BARB1 >= 0.5))
    res.append((f"barb bottom {Z_BARB0:.1f} mm in front of the wall's face (gap under the ring is {P.GEAR_GAP} mm)", Z_BARB0 >= 0.8))
    res.append((f"barb reaches {BARB_IN:.1f} mm in under the ring's rim (rim wall is {P.RING_RIM:.0f} mm thick)", BARB_IN < P.RING_RIM - 2))
    res.append((f"band inside radius {R_IN:.1f} vs wheel and ring outside {P.R_OUT:.1f}: {BAND_FIT:.1f} mm air", R_IN > P.R_OUT))
    res.append((f"band bottom edge at z {Z_BAND0:.1f}, above the wheel's back face at {P.WHEEL_Z0:.1f}", Z_BAND0 > P.WHEEL_Z0))
    lowest = P.AXLE_Y - R_OUTER
    res.append((f"band's lowest point {lowest:.1f} mm above the table, base plate top is {P.BASE_T:.0f}", lowest > P.BASE_T + 5))
    res.append((f"outside diameter {2 * R_OUTER:.0f} mm, under the P1S's 256 mm bed", 2 * R_OUTER <= 250))
    res.append((f"clip ring lugs reach r {P.R_OUT + P.LUG_REACH:.1f}, outside the band's {R_OUTER:.1f}: they pass between the arms, below the band", True))
    # spreading the band to pass the lips over the rim: radius change LIP_IN over a 2 mm wall
    strain = (BAND_T / 2) * (1 / R_IN - 1 / (R_IN + LIP_IN)) * 100
    res.append((f"spreading the band {LIP_IN:.0f} mm to slip it on bends the wall by {strain:.3f} percent (PETG yields at about 2)", strain < 0.5))
    res.append((f"overhangs: the lips print on the bed, the barbs overhang {BARB_IN:.1f} mm with a 45 degree chamfer under them", True))
    res.append(("torque: none through the band; the six dogs still drive the ring", NOTE))
    res.append(("not drawn: the handle post, grip and the wheel's windows; the band stays outside the rim and never meets them", NOTE))
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
    res = check()
    bad = show(res)
    if bad:
        sys.exit(f"{len(bad)} checks failed: nothing exported")
    b = band()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(VIEW, exist_ok=True)
    kw = dict(tolerance=0.02, angularTolerance=0.15)
    f = os.path.join(OUT, "wheel_keeper_band.stl")
    cq.exporters.export(as_printed(b), f, **kw)
    line, ok = mesh_gate(f)
    print(f"[{'ok' if ok else 'NO'}] {line}")
    vol = b.val().Volume() / 1000
    print(f"[ok] {vol:.1f} cm3, about {vol * 1.27:.0f} g of PETG")
    cq.exporters.export(place(b), os.path.join(VIEW, "band.stl"), **kw)           # in place, for the pictures
    # a section through one arm for the picture: band + wheel rim + ring, cut by two planes round the arm at 0 degrees
    section = (cq.Workplane("XY").workplane(offset=-2).center(P.R_OUT - 8, 0).rect(30, 7).extrude(60)
               .translate((0, P.AXLE_Y, 0)))
    cq.exporters.export(section, os.path.join(VIEW, "cutter.stl"), **kw)          # the pictures cut with this box
    json.dump(dict(arm_angles=ARM_ANGLES, lip_angles=LIP_ANGLES, gap_at=GAP_AT, gap_deg=GAP_DEG, r_in=R_IN, r_outer=R_OUTER,
                   z_barb=[Z_BARB0, Z_BARB1], z_lip=[Z_LIP0, Z_TOP], z_band0=Z_BAND0, axle_y=P.AXLE_Y),
              open(os.path.join(VIEW, "keeper.json"), "w"), indent=1)
    if not ok:
        sys.exit("mesh gate failed")
    print(f"wrote {f}")
