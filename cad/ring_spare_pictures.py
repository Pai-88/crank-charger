"""Pictures for the clip-together replacement ring: "Ring 0" to "Ring 6", in the style of assembly/step_*.png.

    .venv/bin/python cad/ring_spare_pictures.py              meshes, plan, Blender passes, pictures
    .venv/bin/python cad/ring_spare_pictures.py --reuse      keep the meshes (they take two minutes)
    .venv/bin/python cad/ring_spare_pictures.py --reuse 4 5  only these pictures
    .venv/bin/python cad/ring_spare_pictures.py --props      rebuild only the bench props, keep the rest
    add --grid for a 100 px layout grid (written to spares/_build/, never delivered)

Writes spares/ring_0.png ... (2000 x 1250, landscape) and spares/phone/ring_0_phone.png ... (portrait).
The drawing code is cad/assembly_steps_compose.py's own, imported and pointed at spares/_build/; the
Blender half is cad/ring_spare_render.py. Parts come from ring_spare.py and planetary.py; the gears,
bearings, spider and mug are the meshes cad/assembly_steps_export.py already made (read, not changed).
Two books, the side cutters, the cut mark, a butter knife and a bit of table are bench props. The old ring,
cut once and pulled open, is planetary's ring bent by ring_spare.open_ring(): the same sum the check line prints.
"""
import json
import math
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "spares")
BUILD = os.path.join(OUT, "_build")
MESH = os.path.join(BUILD, "meshes")
SRC = os.path.join(ROOT, "assembly", "_build", "meshes")
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
sys.path.insert(0, HERE)

import planetary as P
import ring_spare as RS

AY, GG = P.AXLE_Y, P.GEAR_GAP
PIN = [(x, AY + y) for x, y in P.PINS]
BORROWED = ["planet1", "planet2", "planet3", "sun", "ring", "brg_p1", "brg_p2", "brg_p3", "mug", "spider", "axle_bolt",
            "pin_bolt1", "pin_bolt2", "pin_bolt3"] + [f"pin_w{i}{s}" for i in (1, 2, 3) for s in "ab"]
R_MID = (P.R_RING_ROOT + P.R_OUT) / 2
CUT = RS.CUT_AT                # where the old ring is cut, ONCE: between two dogs, well away from a planet
BOOK = (150.0, 215.0, 22.0)    # the first book: any size, the gears only lie on it
BIG = (210.0, 297.0, 22.0)     # the second: A4. After the turn-over the rear half rests on it, so it must reach the rim
LIFT = 78.0                    # the opened old ring, drawn lifted this far off the gears
KIND = {}


def g(x, y, z):
    """A point given in the ring's own frame (axis at the origin, back face z=0), in the pictures' frame."""
    return (x, AY + y, GG + z)


def polar(r, deg, z):
    return g(r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), z)


# ============================================================ geometry
OPENED = RS.ring_comes_off(3.0)            # the cut ring pulled open far enough to clear every planet by 3 mm (about 5 cm at the cut)


def open_xy(xy):
    """Points of the old ring (its own frame) to where they are once it is cut at CUT and pulled open."""
    o = OPENED
    t = np.radians((np.degrees(np.arctan2(xy[:, 1], xy[:, 0])) - CUT) % 360.0)
    rho = np.hypot(xy[:, 0], xy[:, 1])
    line = np.c_[np.interp(t, o["t"], o["xy"][:, 0]), np.interp(t, o["t"], o["xy"][:, 1])]
    nrm = np.c_[np.interp(t, o["t"], o["n"][:, 0]), np.interp(t, o["t"], o["n"][:, 1])]
    return (line + (rho - o["r"])[:, None] * nrm) @ o["rot"].T + np.array(o["slide"])


def build_meshes(props_only=False):
    import cadquery as cq
    import trimesh
    from shapely.geometry import Polygon

    os.makedirs(MESH, exist_ok=True)
    kinds = json.load(open(os.path.join(SRC, "_kinds.json")))
    for n in BORROWED:
        shutil.copyfile(os.path.join(SRC, n + ".npz"), os.path.join(MESH, n + ".npz"))
        KIND[n] = kinds[n]
    solids = {}

    def add(name, solid, kind, tol=0.05, ang=0.2):
        solids[name] = (solid, tol, ang)
        KIND[name] = kind

    here = lambda part: part.translate((0, AY, GG))
    if not props_only:                        # the gears and the two halves: the slow part
        gs = P.gearset()
        planets = [gs[k] for k in gs if k.startswith("planet")]
        fs, _ = RS.screw_senses(planets)
        if len(fs) != 1:
            sys.exit("the front half's screwing direction is not unique: run cad/ring_spare.py")
        rear, front = RS.halves(-fs[0])
        add("rear", here(rear), "printed")
        add("front", here(front), "printed")
        for i, a in enumerate(RS.LUG_ANGLES):
            add(f"clip{i + 1}", here(RS.clip(a)), "printed", 0.02, 0.1)
        add("key", here(RS.key().translate((0, 0, -RS.KEY_T))), "printed")

        c_r, c_f = RS.coupon_parts(rear, front)                  # the test piece, still where the ring has it
        add("cp_rear", here(c_r), "printed", 0.02, 0.1)
        add("cp_front", here(c_f), "printed", 0.02, 0.1)

        # the old ring, cut through once. Its mesh is bent open after tessellating (see below)
        kerf = math.degrees(1.2 / R_MID)
        pts = [(0.0, 0.0)] + [(160 * math.cos(math.radians(t)), 160 * math.sin(math.radians(t))) for t in np.linspace(CUT - kerf, CUT + kerf, 5)]
        add("old_open", gs["ring"].cut(P._prism(Polygon(pts), -1, RS.TOP + 1)), "printed", 0.03, 0.08)
    add("cut1", here(RS._slab(P.R_RING_TIP - 1.5, -1.6, P.R_OUT + 1.5, 1.6, CUT, -0.4, P.RING_H + 0.6)), "printed")

    # side cutters: two levers on a pivot, jaws astride the ring's wall, part way down the cut
    lever = [(0.8, 0), (4.5, 0), (8.5, 20), (6.5, 30), (-4, 44), (-14, 120), (-22, 118), (-12, 44), (-6.5, 26), (0.8, 18)]
    piv = 26.0
    one = cq.Workplane("XZ").polyline(lever).close().extrude(3.5, both=True)
    two = cq.Workplane("XZ").polyline([(-x, z) for x, z in reversed(lever)]).close().extrude(3.5, both=True)
    tool = one.rotate((0, 0, piv), (0, 1, piv), -8).union(two.rotate((0, 0, piv), (0, 1, piv), 8))
    tool = tool.union(cq.Workplane("XZ").center(0, piv).circle(5.0).extrude(4.5, both=True))
    tool = tool.rotate((0, 0, 0), (0, 1, 0), 28)                       # handles lean outward, clear of the gears
    add("cutters", here(tool.translate((R_MID, 0, P.RING_H - 8.0)).rotate((0, 0, 0), (0, 0, 1), CUT)), "bought", 0.03, 0.15)

    # two books: one against the gears' front faces, one (bigger) against their backs
    def book(z0, size):
        bx, by, bt = size
        b = cq.Workplane("XY").box(bx, by, 2.0, centered=(True, True, False)).translate((0, 0, z0))
        b = b.union(cq.Workplane("XY").box(bx - 5, by - 7, bt - 3.0, centered=(True, True, False)).translate((-2.5, 0, z0 + 1.5)))
        return b.union(cq.Workplane("XY").box(bx, by, 2.0, centered=(True, True, False)).translate((0, 0, z0 + bt - 2.0)))

    add("book_f", here(book(P.FACE_W, BOOK)), "table")
    add("book_b", here(book(-BIG[2], BIG)), "table")

    # for the test picture: a bit of table under the test piece, and a butter knife in the gap behind its clip
    lug = RS.LUG_ANGLES[RS.COUPON_LUG]
    at_lug = lambda part: here(part.rotate((0, 0, 0), (0, 0, 1), lug))
    add("table", at_lug(cq.Workplane("XY").box(46, 76, 3.0, centered=(True, True, False)).translate((P.R_OUT + 1, 0, -3.0))), "table")
    r_gap = P.R_OUT + P.LUG_REACH + RS.PRY / 2
    knife = [(-2.0, 0), (60.0, 0), (60.0, 7.0), (8.0, 7.0), (2.0, 5.0), (-2.0, 2.0)]               # along the rim, up the axle
    blade = cq.Workplane("XY").polyline(knife).close().extrude(1.0).translate((0, 0, -0.5))
    blade = blade.union(cq.Workplane("XY").box(46, 9, 5.0, centered=(False, False, True)).translate((60, -1, 0)))
    blade = blade.rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 90)                # flat against the spine, point along the rim
    add("blade", at_lug(blade.translate((r_gap, -RS.CLIP_W + 1.0, (RS.ZR1 + RS.ZF0) / 2 - 3.5))), "bought", 0.03, 0.15)

    for name, (solid, tol, ang) in solids.items():
        comp = cq.Compound.makeCompound(list(solid.vals()))
        vs, ts = comp.tessellate(tol, ang)
        m = trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(ts), process=True)
        if len(m.faces) == 0:
            sys.exit(f"{name}: empty mesh")
        sm = trimesh.graph.smooth_shade(m, angle=math.radians(30.0))
        v = np.asarray(sm.vertices, float)
        if name == "old_open":                                         # bend it open, slide it clear, put it in the pictures' frame
            v = np.c_[open_xy(v[:, :2]), v[:, 2]] + np.array([0.0, AY, GG])
        np.savez_compressed(os.path.join(MESH, f"{name}.npz"), v=np.asarray(v, np.float32), f=np.asarray(sm.faces, np.int32))
        print(f"  {name:10s} {len(sm.faces):6d} triangles")
    if props_only:
        KIND.update({**json.load(open(os.path.join(MESH, "_kinds.json"))), **KIND})
    with open(os.path.join(MESH, "_kinds.json"), "w") as fh:
        json.dump(KIND, fh, indent=1)


# ============================================================ the plan
PW, PH, HEAD = 1000, 1100, 150
W, H = 2 * PW, PH + HEAD


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def cam_bench(az, el, up_is_front):
    """The gears lying on the bench, axis vertical. up_is_front: their FRONT (bearing side, dogs) faces up."""
    az, el, s = math.radians(az), math.radians(el), (1.0 if up_is_front else -1.0)
    return dict(c=(math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), s * math.sin(el)), up=(0, 0, s))


def make_plan():
    verts = {n: np.load(os.path.join(MESH, f"{n}.npz"))["v"].astype(float) for n in KIND}

    def view(name, side, cam, inst, fit=None, fit_pts=None, arrows=(), guides=(), curves=(), turns=(), callouts=(), inset=None, ppm_max=9.0):
        px = 0 if side == "L" else PW
        x, y, w, h = (px, HEAD, PW, PH) if inset is None else (px + inset[0], HEAD + inset[1], inset[2], inset[3])
        c, up0 = unit(cam["c"]), unit(cam["up"])
        right = unit(np.cross(up0, c))
        up = np.cross(c, right)
        pts = np.vstack([verts[m] + np.asarray(off, float) for m, _, off in inst]) if fit_pts is None else np.asarray(fit_pts, float)
        u, v = pts @ right, pts @ up
        fx0, fy0, fx1, fy1 = fit or (50, 50, w - 50, h - 50)
        ppm = min((fx1 - fx0) / (u.max() - u.min()), (fy1 - fy0) / (v.max() - v.min()), ppm_max)
        cu, cv = (u.max() + u.min()) / 2, (v.max() + v.min()) / 2
        du, dv = ((fx0 + fx1) / 2 - w / 2) / ppm, -((fy0 + fy1) / 2 - h / 2) / ppm
        target = right * (cu - du) + up * (cv - dv) + c * float((pts @ c).mean())
        f3 = lambda p: [float(t) for t in p]
        lines = [dict(pts=[f3(a), f3(b)], heads="end", dash=False) for a, b in arrows]
        lines += [dict(pts=[f3(a), f3(b)], heads="none", dash=True) for a, b in guides]
        lines += [dict(pts=[f3(p) for p in pl], heads="both", dash=False) for pl in curves]
        lines += [dict(pts=[f3(p) for p in pl], heads="end", dash=False) for pl in turns]
        return dict(name=name, panel=side, rect=[x, y, w, h], inset=inset is not None, ppm=ppm,
                    cam=dict(c=c.tolist(), up=up.tolist(), right=right.tolist(), target=target.tolist()),
                    inst=[dict(mesh=m, role=r, off=f3(off)) for m, r, off in inst], arrows=lines,
                    callouts=[dict(text=t, at=None if at is None else f3(at), xy=list(xy)) for t, at, xy in callouts])

    Z0 = (0.0, 0.0, 0.0)
    dz = lambda d: (0.0, 0.0, float(d))
    out = lambda r, deg: (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), 0.0)
    plain = lambda names, off=Z0: [(n, KIND[n], off) for n in names]
    hot = lambda names, off=Z0: [(n, KIND[n] if KIND[n] == "table" else "accent", off) for n in names]

    PLANETS, BRG = ["planet1", "planet2", "planet3"], ["brg_p1", "brg_p2", "brg_p3"]
    GEARS = ["sun"] + PLANETS + BRG
    CLIPS = [f"clip{i + 1}" for i in range(RS.N_LUG)]
    LUG = RS.LUG_ANGLES[RS.COUPON_LUG]           # the lug nearest the camera in the bench pictures (about 266 degrees); the test piece is cut round it
    R_L = P.R_OUT + P.LUG_REACH
    FW, HALF, TOP = P.FACE_W, RS.HALF, RS.TOP
    lug_n = f"clip{RS.COUPON_LUG + 1}"
    steps = []

    def twist(r, a0, a1, z):
        return [polar(r, a, z) for a in np.linspace(a0, a1, 30)]

    def lug_box(pad_r=10.0, pad_t=20.0, z0=-4.0, z1=22.0, lift=0.0):
        """Corner points round the near lug, for the close-ups."""
        a = math.radians(LUG)
        er, et = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
        pts = []
        for r in (P.R_OUT - pad_r, R_L + pad_r + 6):
            for t in (-pad_t, pad_t):
                for z in (z0, z1):
                    pts.append(g(r * er[0] + t * et[0], r * er[1] + t * et[1], z + lift))
        return pts

    def along(deg, t):
        """t mm along the rim from the radial line at deg (counter-clockwise positive), as an offset."""
        return (-t * math.sin(math.radians(deg)), t * math.cos(math.radians(deg)), 0.0)

    # ---------------------------------------------------------------- 0: the test piece
    near = cam_bench(LUG + 38, 24, True)
    e_f0, e_c0 = 17.0, 12.0
    card = lambda col, row: (20 + 490 * col, 20 + 535 * row, 470, 525)
    fit_c = (40, 200, 430, 505)
    whole = plain(["cp_rear", "cp_front"]) + [(lug_n, "accent", Z0)]
    edge_on = cam_bench(LUG + 90, 0, True)
    gap_at = tuple(a + b for a, b in zip(polar(R_L + RS.PRY / 2, LUG, 9.5), along(LUG, 14.0)))
    steps.append(dict(n="0", title="Test piece first: does the clip click?", views=[
        view("r0_move", "L", near, plain(["cp_rear"]) + hot(["cp_front"], dz(e_f0)) + [(lug_n, "accent", out(e_c0, LUG))],
             fit=(110, 330, PW - 140, 800), ppm_max=15.0,
             arrows=[(polar(P.R_OUT - 3, LUG + 7, HALF + e_f0 - 2), polar(P.R_OUT - 3, LUG + 7, HALF + 3)),
                     (polar(RS.RS1 + e_c0 + 9, LUG, 7.5), polar(RS.RS1 + e_c0 + 1.5, LUG, 7.5))], callouts=[
            ("plate 1 prints 3 pieces. Try them\nbefore the long prints.", None, (30, 20)),
            ("1. taller piece on the shorter:\nits lug drops between the 2 ears", polar(R_L - 2.5, LUG, FW + e_f0 - 1.2), (30, 170)),
            ("2. clip: THIN arm underneath, in its\nslot. Push until it CLICKS.", polar(RS.RS1 + e_c0 - 1.0, LUG, 3.0), (30, 840)),
            ("No click, or a crack? STOP and say so.\nWhite marks alone are fine.", None, (30, 975)),
        ]),
        view("r0_pull", "R", near, whole, inset=card(0, 0), fit=fit_c, ppm_max=11.0,
             arrows=[(polar(P.R_OUT - 3, LUG + 8, FW + 6), polar(P.R_OUT - 3, LUG + 8, FW + 17)),
                     (polar(P.R_OUT - 3, LUG + 8, -1), polar(P.R_OUT - 3, LUG + 8, -8))], callouts=[
            ("pull the pieces\napart by hand:\nthey hold", None, (18, 12)),
        ]),
        view("r0_gap", "R", edge_on, plain(["table"]) + whole, inset=card(1, 0), fit=(40, 225, 430, 505), fit_pts=lug_box(1.0, 6.0, -3.5, 13.5), ppm_max=24.0, callouts=[
            ("flat on a table:\nthe clip does not\ntouch the table", polar(RS.RS1 + 1.6, LUG, 0.3), (18, 12)),
        ]),
        view("r0_lever", "R", near, whole + plain(["blade"]), inset=card(0, 1), fit=fit_c, fit_pts=lug_box(8.0, 22.0, -2.0, 18.0), ppm_max=11.0, callouts=[
            ("off again: scissor\nblade or cutter tips\nin the gap, twist", gap_at, (18, 12)),
        ]),
        view("r0_teeth", "R", cam_bench(LUG + 30, 50, True), whole + plain(["planet3", "brg_p3"]), inset=card(1, 1), fit=(30, 250, 440, 515),
             fit_pts=[polar(r, LUG + t, z) for r in (52, P.R_OUT + 10) for t in (-22, 22) for z in (0, FW)], ppm_max=6.0,
             curves=[twist(P.A_C + 8, 256, 284, FW + 2)], callouts=[
            ("a planet (Ring 1):\nits teeth go in and\nrock, never stick", None, (18, 12)),
        ]),
    ]))

    # ---------------------------------------------------------------- 1: cut the old ring, once, and lift it off
    cam = cam_bench(-70, 42, True)
    fit1 = (70, 330, PW - 60, PH - 170)
    ends = [np.array(OPENED["xy"][k]) @ OPENED["rot"].T + np.array(OPENED["slide"]) for k in (0, -1)]
    apart = (ends[0] - ends[1]) / np.linalg.norm(ends[0] - ends[1])
    pull = [(g(*(e + s_ * 5 * apart), P.RING_H / 2 + LIFT), g(*(e + s_ * 40 * apart), P.RING_H / 2 + LIFT)) for e, s_ in zip(ends, (1, -1))]
    up = [(polar(P.R_OUT + 4, a, P.RING_H + 4), polar(P.R_OUT + 4, a, P.RING_H + LIFT - 6)) for a in (178, 2)]
    steps.append(dict(n="1", title="Cut the old ring in ONE place. Lift it off.", views=[
        view("r1_move", "L", cam, plain(["ring"] + GEARS) + hot(["cut1"]) + plain(["cutters"]), fit=(90, 350, PW - 90, 850), callouts=[
            ("cut in ONE place: between two dogs,\naway from the planets", polar(P.R_OUT, CUT, P.RING_H - 6), (30, 20)),
            ("side cutters, small bites (2 mm), top\nedge down. Glasses on and a cloth\nover the gears: chips fly.", polar(R_MID + 26, CUT, P.RING_H + 68), (30, 150)),
            ("Gears still on the machine? Undo Steps\n7, 6, 5. Will not bite? STOP, say so:\nscissors will NOT cut this. Cracked\nright through already? Start there.", None, (30, 860)),
        ]),
        view("r1_done", "R", cam, plain(["old_open"], dz(LIFT)) + [(n, "accent", Z0) for n in GEARS],
             fit=(90, 300, PW - 90, 850), arrows=pull + up, callouts=[
            ("1. pull the cut ends 5 cm apart\n2. lift the ring straight up, off the gears", g(*(ends[0] + 44 * apart), P.RING_H / 2 + LIFT), (30, 20)),
            ("The gears stay flat on the table:\nnever pull a gear up out of the ring.", None, (30, 150)),
            ("KEEP the sun and the 3 planets. Old ring:\nin the bin. No bearings in the planets?\nPress them into the BIG holes now:\nStep 1, part 2.", g(P.PINS[2][0] + 8, P.PINS[2][1], FW), (30, 860)),
        ]),
    ]))

    # ---------------------------------------------------------------- 2: gears face down on a book, key on top
    cam = cam_bench(-70, 40, False)
    fit2 = (90, 330, PW - 90, PH - 60)
    e_k = 95.0
    push = [(polar(P.A_C + 86, a, 6), polar(P.A_C + 52, a, 6)) for a in P.PIN_ANGLES]
    drop = [((x, y, GG - e_k + RS.PEG_H + 3), (x, y, GG - 2)) for x, y in PIN]
    base2 = plain(["book_f"] + GEARS)
    one = ["planet1", "brg_p1"]
    one_fit = [(PIN[0][0] + dx, PIN[0][1] + dy, GG + z) for dx in (-48, 48) for dy in (-48, 48) for z in (0, FW)]
    steps.append(dict(n="2", title="Gears face down on a book. Key on top.", views=[
        view("r2_move", "L", cam, base2 + hot(["key"], dz(-e_k)), fit=fit2, arrows=push + drop, callouts=[
            ("1. sun in the middle, 3 planets pushed\nagainst it. BIG hole DOWN, small hole UP.", polar(P.A_C + 30, P.PIN_ANGLES[0], 0), (30, 20)),
            ("2. planet key: 3 pegs\ninto the 3 small holes", (PIN[1][0] - 6, PIN[1][1], GG - e_k - RS.KEY_T), (560, 170)),
            ("any flat book", g(-60, -95, FW + 8), (30, 990)),
        ]),
        view("r2_done", "R", cam, base2 + hot(["key"]), fit=(330, 20, PW - 30, 400), callouts=[
            ("key down flat:\nnow the planets are\nevenly spaced", g(P.PINS[1][0] + 22, P.PINS[1][1] - 12, -RS.KEY_T), (30, 20)),
            ("Peg loose in a big hole? That planet\nis upside down. Peg will not drop in?\nRoll that planet round the sun a little.\nSun will not mesh? Turn the sun over.", None, (30, 430)),
        ]),
        view("r2_up", "R", cam_bench(-70, 50, False), plain(one), inset=(20, 690, 470, 390), fit=(120, 180, 420, 380), fit_pts=one_fit, callouts=[
            ("this side UP: the\nsmall hole. The peg\nfits it snugly.", None, (18, 12)),
        ]),
        view("r2_down", "R", cam_bench(-70, 50, True), plain(one), inset=(510, 690, 470, 390), fit=(120, 180, 420, 380), fit_pts=one_fit, callouts=[
            ("this side DOWN:\nthe big hole, or\nthe bearing in it", None, (18, 12)),
        ]),
    ]))

    # ---------------------------------------------------------------- 3: rear half on, then turn it all over
    e_r = 78.0
    tw = twist(P.R_OUT + 14, 262, 322, -e_r + 3)
    down = [(polar(P.R_OUT - 3, a, -e_r + HALF + 3), polar(P.R_OUT - 3, a, -3)) for a in (175, 5)]
    c3 = unit(cam["c"])
    right3 = unit(np.cross((0, 0, -1.0), c3))
    mid3 = np.array(g(0, 0, -12.0))
    flip = [tuple(mid3 + 168.0 * (math.cos(t) * right3 + math.sin(t) * np.array([0, 0, -1.0]))) for t in np.radians(np.linspace(-20, 195, 40))]
    under = cam_bench(LUG + 38, 26, False)
    steps.append(dict(n="3", title="Rear half on. Then turn it all over.", views=[
        view("r3_move", "L", cam, base2 + plain(["key"]) + hot(["rear"], dz(-e_r)), fit=(60, 430, PW - 60, PH - 30),
             arrows=down, curves=[tw], callouts=[
            ("rear half, the thin ring:\nslots UP, little ears\nDOWN at the book", None, (30, 20)),
            ("lower it and turn it: it\nscrews down and stops\nlevel with the gears", tw[22], (30, 215)),
        ]),
        view("r3_lug", "L", under, hot(["rear"], dz(-e_r)), inset=(520, 15, 460, 400), fit=(30, 30, 430, 370),
             fit_pts=lug_box(6.0, 16.0, -5.0, 10.0, -e_r), ppm_max=15.0, callouts=[
            ("slot: on top", polar(P.R_OUT + 3.5, LUG, -e_r - 0.2), (18, 12)),
            ("ear: underneath", polar(R_L - 2.5, LUG - 3.4, -e_r + HALF + RS.EAR_H), (150, 330)),
        ]),
        view("r3_book", "R", cam, base2 + hot(["rear"]) + plain(["book_b"], dz(-70)), fit=(250, 180, PW - 90, 560),
             arrows=[(g(0, -140, -70 + 2), g(0, -140, -8))], turns=[flip], callouts=[
            ("1. lift the key out. 2. BIG book on top:\nA4 or bigger, or a chopping board.", g(60, -140, -70 - 10), (30, 20)),
            ("3. SQUEEZE both\nbooks together,\nturn the lot over", flip[30], (30, 590)),
            ("4. lift off\nthe top book", None, (30, 800)),
        ]),
        view("r3_after", "R", cam_bench(-70, 40, True), plain(["book_b"] + GEARS) + hot(["rear"]), inset=(380, 590, 600, 490),
             fit=(30, 120, 570, 470), callouts=[
            ("after: bearings UP,\nlittle ears UP", polar(R_L - 2.5, LUG - 3.4, HALF + RS.EAR_H), (18, 12)),
        ]),
    ]))

    # ---------------------------------------------------------------- 4: front half on
    cam = cam_bench(-70, 38, True)
    e_f = 80.0
    base4 = plain(["book_b", "rear"] + GEARS)
    tw = twist(P.R_OUT + 16, 296, 350, e_f + FW)
    down = [(polar(P.R_OUT - 3, a, e_f + HALF - 3), polar(P.R_OUT - 3, a, HALF + 3)) for a in (175, 5)]
    plumb = [(polar(R_L - 1.5, a, e_f + HALF - 1), polar(R_L - 1.5, a, HALF + RS.EAR_H + 1)) for a in RS.LUG_ANGLES if 200 < a < 340 or a < 20]
    steps.append(dict(n="4", title="Front half: lugs over the ears, then down flat.", views=[
        view("r4_move", "L", cam, base4 + hot(["front"], dz(e_f)), fit=(60, 400, PW - 60, PH - 20), arrows=down, guides=plumb, curves=[tw], callouts=[
            ("front half:\ndogs UP", polar(P.R_OUT - 3, P.DOG_ANGLES[2], e_f + TOP), (30, 20)),
            ("FIRST hold each of the 7 lugs\njust above its pair of ears.\nTHEN lower it and turn it a\nlittle (2 mm): it drops flat.",
             polar(R_L - 1.5, LUG, e_f + HALF + 3), (250, 20)),
        ]),
        view("r4_done", "R", cam, base4 + hot(["front"]), fit=(60, 130, PW - 60, 600), callouts=[
            ("flat all the way round", polar(P.R_OUT, 338, HALF), (480, 20)),
        ]),
        view("r4_lug", "R", near, plain(["rear"]) + hot(["front"]), inset=(20, 610, 440, 470), fit=(30, 30, 410, 440),
             fit_pts=lug_box(), ppm_max=14.0, callouts=[
            ("right: every lug sits\ndown between its\ntwo ears", polar(R_L - 1, LUG, HALF + 3), (470, 10)),
            ("lug ON an ear, or a gap?\nIt is one tooth out.\nLugs nowhere near ears?\nLift, turn until they are\nover the ears, lower.", None, (470, 195)),
        ]),
    ]))

    # ---------------------------------------------------------------- 5: the clips
    e_c = 34.0
    base5 = plain(["book_b", "rear", "front"] + GEARS)
    offs = {f"clip{i + 1}": out(e_c, a) for i, a in enumerate(RS.LUG_ANGLES)}
    arrows = [(polar(RS.RS1 + e_c - 14, a, FW + 6), polar(RS.RS1 + 4, a, FW + 6)) for a in RS.LUG_ANGLES]
    side = cam_bench(LUG + 62, -9, True)
    e_s = 15.0
    card, fit5 = (20, 610, 960, 470), (440, 40, 900, 430)
    steps.append(dict(n="5", title="Seven clips: push each one on until it clicks.", views=[
        view("r5_move", "L", cam, base5 + [(n, "accent", offs[n]) for n in CLIPS], fit=(70, 200, PW - 70, 600), arrows=arrows, callouts=[
            ("clip, x7 (you printed 9: 2 are spare).\nPINCH each one on: fingers inside\nthe ring, thumb on the clip.", None, (30, 20)),
        ]),
        view("r5_how", "L", side, plain(["rear", "front"]) + [(lug_n, "accent", out(e_s, LUG))], inset=card,
             fit=fit5, fit_pts=lug_box(4.0, 12.0, -3.0, 17.0), ppm_max=22.0,
             arrows=[(polar(RS.RS1 + e_s + 11, LUG, 7.5), polar(RS.RS1 + e_s + 1.5, LUG, 7.5))], callouts=[
            ("thick arm with\nthe hook: on top", polar(RS.RS0 + e_s - 3, LUG, RS.ZF1), (30, 20)),
            ("push until\nit CLICKS", None, (30, 185)),
            ("thin arm: into the\nslot under the lug", polar(P.R_OUT + 4.5, LUG, 0.4), (30, 335)),
        ]),
        view("r5_done", "R", cam, base5 + hot(CLIPS), fit=(70, 160, PW - 70, 600), callouts=[
            ("all seven on. Push each one again: none moves.", None, (30, 20)),
        ]),
        view("r5_on", "R", side, plain(["rear", "front"]) + [(lug_n, "accent", Z0)], inset=card,
             fit=fit5, fit_pts=lug_box(4.0, 12.0, -3.0, 17.0), ppm_max=22.0, callouts=[
            ("clicked: the hook\nis in the groove", polar(RS.RI + RS.RAMP_L + 1.0, LUG, FW + 1.0), (30, 20)),
            ("to take one off:\nscissor blade or\nclosed cutter tips\nin this gap, twist.\nNo sharp knife.", polar(RS.RS0 - 0.7, LUG, 7.0), (30, 165)),
        ]),
    ]))

    # ---------------------------------------------------------------- 6: check, then back to the main guide
    ring_new = ["rear", "front"] + CLIPS
    tw = twist(P.R_OUT + 20, 196, 250, 10)
    cam5 = cam_bench(-90.0, 20, False)
    e_g = 72.0
    stand = plain(["mug", "spider", "axle_bolt", "pin_bolt1", "pin_bolt2", "pin_bolt3"] + [f"pin_w{i}{s}" for i in (1, 2, 3) for s in "ab"])
    Z_PIN_TIP = P.SPIDER_Z0 + P.SPIDER_T - P.HEAD_POCKET - P.PIN_BOLT_LEN
    pins = [((x, y, GG + FW - e_g + 1), (x, y, Z_PIN_TIP - 1)) for x, y in PIN]
    dog = polar(P.R_OUT, 330.0, TOP - 5)
    steps.append(dict(n="6", title="Check it turns. Then on to Step 5.", views=[
        view("r6_check", "L", cam, plain(["book_b"] + ring_new + GEARS), fit=(70, 300, PW - 70, PH - 150), curves=[tw], callouts=[
            ("finger on the sun, turn the ring: the\n3 planets roll round, nothing jams", tw[4], (30, 20)),
            ("pick it up by the front half:\nnothing comes apart", polar(P.R_OUT - 3, P.DOG_ANGLES[0], TOP), (470, 180)),
            ("bearings must be in the planets by now (Ring 1)", g(P.PINS[2][0] + 8, P.PINS[2][1], FW), (30, 1010)),
        ]),
        view("r6_next", "R", cam5, stand + [(n, "accent", dz(-e_g)) for n in ring_new + GEARS], fit=(50, 240, PW - 50, PH - 85), arrows=pins, callouts=[
            ("main guide, Step 5: new gearset FRONT\nface down, dogs DOWN, onto the pins", (dog[0], dog[1], dog[2] - e_g), (30, 20)),
            ("no spider yet?\nStep 4 first.", (PIN[0][0], PIN[0][1], Z_PIN_TIP + 12), (20, 880)),
        ]),
    ]))

    plan = dict(size=[W, H], head=HEAD, panel=[PW, PH], meshes={n: dict(file=f"meshes/{n}.npz", kind=k) for n, k in KIND.items()}, steps=steps)
    with open(os.path.join(BUILD, "placements.json"), "w") as fh:
        json.dump(plan, fh, indent=1)
    return plan


# ============================================================ drawing (assembly_steps_compose's code, with "Ring" for "Step")
def compose_all(plan, want, grid):
    from PIL import Image, ImageDraw, ImageFont
    import assembly_steps_compose as C

    C.BUILD, C.PASSES, C.OUT = BUILD, os.path.join(BUILD, "passes"), OUT
    SS = C.SS

    def compose(step, phone):
        Wd, Ht = plan["size"]
        views = []
        for view in sorted(step["views"], key=lambda v: v["inset"]):
            if phone:
                x, y, w, h = view["rect"]
                col = 0 if view["panel"] == "L" else 1
                view = dict(view, rect=[x - col * PW, y - HEAD + C.PHONE_HEAD + col * PH, w, h])
            views.append(view)
        if phone:
            Wd, Ht = PW, C.PHONE_HEAD + 2 * PH
        canvas = np.ones((Ht * SS, Wd * SS, 3), np.float32)
        for view in views:
            rgb, hit = C.render_view(view)
            C.check_projection(view, hit)
            x, y, w, h = (t * SS for t in view["rect"])
            if view["inset"]:
                card = Image.new("L", (w, h), 0)
                ImageDraw.Draw(card).rounded_rectangle([0, 0, w - 1, h - 1], radius=14 * SS, fill=255)
                keep = (np.asarray(card) > 127)[..., None]
                canvas[y:y + h, x:x + w] = np.where(keep, rgb, canvas[y:y + h, x:x + w])
            else:
                canvas[y:y + h, x:x + w] = np.where(hit[..., None], rgb, canvas[y:y + h, x:x + w])
        img = Image.fromarray((np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8))
        dr = ImageDraw.Draw(img)
        for view in views:
            if view["inset"]:
                x, y, w, h = (t * SS for t in view["rect"])
                dr.rounded_rectangle([x, y, x + w, y + h], radius=14 * SS, outline=(60, 60, 64), width=int(2 * SS))
        if phone:
            yy = (C.PHONE_HEAD + PH) * SS
            dr.line([(30 * SS, yy), ((Wd - 30) * SS, yy)], fill=(205, 205, 208), width=SS)
        else:
            dr.line([(Wd * SS // 2, (HEAD + 30) * SS), (Wd * SS // 2, (Ht - 30) * SS)], fill=(205, 205, 208), width=SS)
        for view in views:
            for line in view["arrows"]:
                C.draw_line(dr, [C.project(view, p) for p in line["pts"]], line["heads"], line["dash"])
        f_call = C.font(C.MEDIUM, C.PX_CALL)
        boxes = []
        for view in views:
            for call in view["callouts"]:
                C.draw_callout(dr, view, call, f_call)
                # lettering must stay inside its own panel or card, and off other lettering: said out loud, never silently
                x, y, w, h = view["rect"]
                if view["inset"] and call["xy"][0] >= w:
                    x, w = (x // PW) * PW if not phone else 0, PW      # beside its card: the panel is the frame
                    x, y, h = x, y, 10 ** 6
                b = dr.multiline_textbbox(((view["rect"][0] + call["xy"][0]) * SS, (view["rect"][1] + call["xy"][1]) * SS), call["text"], font=f_call,
                                          spacing=int(0.22 * C.PX_CALL * SS))
                b = [t / SS for t in b]
                first = call["text"].split("\n")[0]
                if b[2] > x + w - 6 or b[3] > y + h - 4 or b[0] < x + 4:
                    print(f"  LAYOUT ring {step['n']} {view['name']}: '{first}' runs out of its frame by {max(b[2] - x - w + 6, b[3] - y - h + 4):.0f} px")
                for other, name in boxes:
                    if b[0] < other[2] and other[0] < b[2] and b[1] < other[3] and other[1] < b[3]:
                        print(f"  LAYOUT ring {step['n']}: '{first}' overlaps '{name}'")
                boxes.append((b, first))
        f_step, f_line = C.font(C.HEAVY, C.PX_STEP), C.font(C.MEDIUM, C.PX_LINE)
        base = 104 * SS
        label = f"Ring {step['n']}"
        dr.text((40 * SS, base), label, font=f_step, fill=C.INK, anchor="ls")
        if phone:
            for k, row in enumerate(C.wrap(dr, step["title"], f_line, (Wd - 80) * SS)):
                dr.text((40 * SS, (168 + 58 * k) * SS), row, font=f_line, fill=C.INK, anchor="ls")
            return img.resize((C.PHONE_W, round(Ht * C.PHONE_W / Wd)), Image.LANCZOS)
        dr.text((40 * SS + dr.textlength(label, font=f_step) + 36 * SS, base), step["title"], font=f_line, fill=C.INK, anchor="ls")
        img = img.resize((Wd, Ht), Image.LANCZOS)
        if grid:
            gdr = ImageDraw.Draw(img)
            small = ImageFont.truetype(C.AVENIR, 16, index=C.ROMAN)
            for x in range(0, Wd, 100):
                gdr.line([(x, 0), (x, Ht)], fill=(120, 170, 255), width=1)
                gdr.text((x + 3, HEAD + 2), str(x % 1000), font=small, fill=(0, 60, 200))
            for y in range(0, Ht, 100):
                gdr.line([(0, y), (Wd, y)], fill=(120, 170, 255), width=1)
                gdr.text((3, y + 2), str(y - HEAD), font=small, fill=(0, 60, 200))
        return img

    os.makedirs(os.path.join(OUT, "phone"), exist_ok=True)
    for step in plan["steps"]:
        if want and step["n"] not in want:
            continue
        if len(step["title"].split()) > 10:
            sys.exit(f"ring {step['n']}: the title is longer than ten words")
        img = compose(step, False)
        path = os.path.join(BUILD if grid else OUT, f"ring_{step['n']}{'_grid' if grid else ''}.png")
        img.save(path, optimize=True)
        print(f"wrote {path}  {img.size}")
        if not grid:
            img = compose(step, True)
            path = os.path.join(OUT, "phone", f"ring_{step['n']}_phone.png")
            img.save(path, optimize=True)
            print(f"wrote {path}  {img.size}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    os.makedirs(BUILD, exist_ok=True)
    if "--props" in sys.argv and os.path.exists(os.path.join(MESH, "_kinds.json")):
        build_meshes(props_only=True)                 # only the cutters, the cut marks and the books again
    elif "--reuse" in sys.argv and os.path.exists(os.path.join(MESH, "_kinds.json")):
        KIND.update(json.load(open(os.path.join(MESH, "_kinds.json"))))
    else:
        print("building meshes (about two minutes)")
        build_meshes()
    plan = make_plan()
    if "--no-render" not in sys.argv:
        prefixes = [f"r{a}_" for a in args]
        subprocess.run([BLENDER, "--background", "--python", os.path.join(HERE, "ring_spare_render.py"), "--", BUILD] + prefixes,
                       check=True, stdout=subprocess.DEVNULL)
    compose_all(plan, args, "--grid" in sys.argv)
