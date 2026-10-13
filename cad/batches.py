"""Lay the print files out as full Bambu P1S plates: one STL per print job, in print order.

    .venv/bin/python cad/batches.py        reads cad/stl/, writes cad/stl/batches/

Run it after planetary.py and mesh_coupon.py. Every part keeps the orientation
it was exported in; this only slides parts around on the plate.
"""
import os
import sys

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "stl")
OUT = os.path.join(SRC, "batches")
PLATE = 256.0          # Bambu P1S
GAP = 8.0              # least distance between two parts' bounding boxes

EDGE = 3.0             # keep this far inside the plate edge
NO_GO = (18.0, 28.0)   # the P1S keeps the front-left corner for itself (x, y from that corner)

# (file, x, y, turn in degrees) with x, y the centre of the part, plate centre = (0, 0)
BATCHES = {
    "plate1_coupon_and_small_parts": [("spider", -50, 58, 0), ("coupon_pair_print_in_place", 85, 60, 90),
                                      ("coupon_plate", -48, -78, 0), ("grip", 40, -70, 0),
                                      ("pin_spacer_x3", 80, -52, 0), ("pin_spacer_x3", 112, -52, 0),
                                      ("pin_spacer_x3", 80, -84, 0), ("hub_spacer", 112, -84, 0)],
    "plate2_gearset": [("gearset_print_in_place", 0, 0, 0)],
    # the ring alone, as two halves, for planets and a sun that already exist (see PRINT.md)
    "plate2a_ring_rear_half": [("ring_rear_half", 0, 0, 0)],
    "plate2b_ring_front_half": [("ring_front_half", 0, 0, 0)],
    "plate3_wheel": [("wheel", 0, 0, 0)],
    "plate4_frame": [("frame", 0, 0, 0)],
    # the washers, printed instead of bought: twelve M8 (eleven used) and the M6 penny washer
    "plate5_washers": [("washer_m8", 26 * (i % 4), 26 * (i // 4), 0) for i in range(12)] + [("washer_m6_penny", 26 * 4, 0, 0)],
}

def build(items):
    import numpy as np
    placed = []
    for name, x, y, turn in items:
        m = trimesh.load(os.path.join(SRC, name + ".stl"), force="mesh")
        if turn:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(turn), [0, 0, 1]))
        lo, hi = m.bounds
        if abs(lo[2]) > 1e-6:
            sys.exit(f"{name} does not sit on the bed (z min {lo[2]:.3f})")
        m.apply_translation([x - (lo[0] + hi[0]) / 2, y - (lo[1] + hi[1]) / 2, 0])
        placed.append((name, m))
    # the slicer centres whatever it is given, so judge the layout the way it will land
    lo = np.min([m.bounds[0] for _, m in placed], axis=0)
    hi = np.max([m.bounds[1] for _, m in placed], axis=0)
    for _, m in placed:
        m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, 0])
    half = PLATE / 2
    for i, (na, ma) in enumerate(placed):
        a = ma.bounds
        if max(abs(a[0][0]), abs(a[1][0]), abs(a[0][1]), abs(a[1][1])) > half - EDGE:
            sys.exit(f"{na} is within {EDGE} mm of the plate edge")
        # corner test on the real outline, not the bounding box: a disc clears a corner its box covers
        v = ma.vertices
        if ((v[:, 0] < -half + NO_GO[0]) & (v[:, 1] < -half + NO_GO[1])).any():
            sys.exit(f"{na} sits in the P1S's reserved front-left corner")
        for nb, mb in placed[:i]:
            b = mb.bounds
            apart = max(a[0][0] - b[1][0], b[0][0] - a[1][0], a[0][1] - b[1][1], b[0][1] - a[1][1])
            if apart < GAP:
                sys.exit(f"{na} and {nb} are only {apart:.1f} mm apart")
    return trimesh.util.concatenate([m for _, m in placed])

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for batch, items in BATCHES.items():
        m = build(items)
        m.export(os.path.join(OUT, batch + ".stl"))
        ext = m.bounding_box.extents
        print(f"{batch}: {len(items)} parts, {ext[0]:.0f} x {ext[1]:.0f} mm of the {PLATE:.0f} x {PLATE:.0f} plate, {ext[2]:.0f} mm tall")
