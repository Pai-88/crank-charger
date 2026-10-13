"""Step-by-step assembly pictures, stage 1 of 2: the geometry and the plan.

    .venv/bin/python cad/assembly_steps_export.py            build every mesh, then write the plan
    .venv/bin/python cad/assembly_steps_export.py --reuse    keep the meshes, rewrite the plan only

Writes into assembly/_build/:
    meshes/<name>.npz     every part as a triangle mesh, already in its ASSEMBLED position
                          (planetary.py's model frame: X right, Y up, Z toward you, wall front Z=0)
    placements.json       the steps (1 to 9, step 6 in two pictures): which parts are on the bench,
                          which are being added, how far each is pulled out along its insertion
                          direction, the camera of every panel, the motion arrows and the call-outs

Printed parts come straight from planetary.py's own functions. Bought parts are simple dummies
at their real sizes, placed from planetary.py's constants. Three things are bench props and not
parts of the machine: the mug the spider stands on, the masking tape over the pin heads, the table.
Nothing in planetary.py is changed and no STL is touched. Stage 2 is cad/assembly_steps.py (Blender).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assembly")
BUILD = os.path.join(OUT, "_build")
MESH = os.path.join(BUILD, "meshes")
sys.path.insert(0, HERE)

import planetary as P          # read only: importing it exports nothing

AY = P.AXLE_Y
TURN = 120.0                   # where the handle sits in the pictures: upper left, seen from the front
PIN = [(x, AY + y) for x, y in P.PINS]

# ---- where things sit along the axis (model Z), all from planetary.py's constants ----
Z_PLANET_FRONT = P.GEAR_GAP + P.FACE_W                       # 15.2
Z_PLANET_BRG = P.GEAR_GAP + P.PLANET_BRG_Z                   # 8.2, back face of each planet bearing
Z_SPIDER_BACK = P.SPIDER_Z0                                  # 18.4, the flat face
Z_SPIDER_FRONT = P.SPIDER_Z0 + P.SPIDER_T                    # 28.4, the arms
Z_BOSS_FRONT = P.SPIDER_Z0 + P.SPIDER_MID                    # 31.3, the middle boss
Z_PIN_HEAD = Z_SPIDER_FRONT - P.HEAD_POCKET                  # 22.9, under the pin heads
Z_PIN_TIP = Z_PIN_HEAD - P.PIN_BOLT_LEN                      # -27.1
Z_AXLE_HEAD = P.SPIDER_Z0 + P.HEAD_POCKET                    # 23.9, under the axle head
Z_AXLE_TIP = Z_AXLE_HEAD + P.AXLE_BOLT_LEN                   # 63.9
Z_BOSS_BACK = -P.WALL_T - P.PIN_BOSS_H                       # -16, behind the wall
Z_HUB_FRONT = P.WHEEL_Z0 + P.HUB_LEN                         # 52.8
Z_BRG_B = P.WHEEL_Z0 + P.POCKET_B_Z                          # front hub bearing, back face
Z_MOTOR_SEAT = -P.WALL_LOCAL                                 # -6, motor flange front
Z_M5_HEAD = Z_MOTOR_SEAT - P.MOTOR_FLANGE_T                  # -11, under the M5 heads
M5_XY = [(sx * P.MOTOR_HOLE_PITCH / 2, AY + sy * P.MOTOR_HOLE_PITCH / 2) for sx in (-1, 1) for sy in (1, -1)]
Z_POST_TOP = P.WHEEL_T + P.POST_H                            # wheel-local, 89.2
TABLE_T = 28.0
Z_BASE_REAR = -P.WALL_T + 1 - (P.BASE_DEPTH + 1)             # -93
CLAMP_X = 74.0                                               # between the gussets at 45 and 102.5

KIND = {}                      # mesh name -> printed | bought | motor | table | tape | cut
BENCH_AZ = -70.0               # where the camera stands in the bench pictures of steps 1 and 4 (degrees in model XY)
STEP5_AZ = -90.0               # step 5: one pin straight in front, the other two left and right, so no
                               # pin's path crosses another planet
MUG_R, MUG_H = 41.0, 85.0      # the mug the spider stands on: the arms rest on its rim, the axle bolt hangs inside.
                               # It has to be taller than the 36 mm the axle bolt hangs down, and narrower than the
                               # ring's skirt (radius 112), which comes down 16 mm past the arms in step 5.


# ============================================================ geometry (cadquery)
def build_meshes():
    import cadquery as cq
    import trimesh

    def rev(profile):
        return cq.Workplane("XZ").polyline(profile).close().revolve(360, (0, 0, 0), (0, 1, 0))

    def box(x0, x1, y0, y1, z0, z1):
        return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

    def flip(part):                                   # local +Z becomes -Z, the hex keeps its corner on X
        return part.rotate((0, 0, 0), (1, 0, 0), 180)

    def hex_bolt(d, length, af, k, thread):
        """Head on z = -k..0, shank along +Z to z = length. The threaded end is drawn ribbed."""
        rc = af / math.sqrt(3)
        ch = (rc + 0.9 - af / 2) * 0.58
        head = P._prism(P._hex(0, 0, af), -k, 0).intersect(
            rev([(0, -k), (af / 2 - 0.4, -k), (rc + 0.5, -k + ch), (rc + 0.5, 0), (0, 0)]))
        r, rt, z = d / 2, d / 2 - 0.35, length - thread
        prof = [(0, -0.5), (r, -0.5), (r, z), (rt, z + 0.35)]
        zz, pitch, g = z + 0.35, 2.5, 0.45
        while zz + pitch < length - 1.2:
            prof += [(rt, zz + pitch - 0.9), (rt - g, zz + pitch - 0.45), (rt, zz + pitch)]
            zz += pitch
        prof += [(rt, length - 0.9), (rt - 0.9, length), (0, length)]
        return head.union(rev(prof))

    def socket_cap(d, length, hd, hk):
        head = rev([(0, -hk), (hd / 2 - 0.5, -hk), (hd / 2, -hk + 0.5), (hd / 2, 0), (0, 0)])
        head = head.cut(P._prism(P._hex(0, 0, 4.0), -hk - 1, -hk + 3.0))
        return head.union(rev([(0, -0.5), (d / 2, -0.5), (d / 2, length - 0.6), (d / 2 - 0.6, length), (0, length)]))

    def nyloc(af, h, bore):
        """Seat face on z=0, hex first, the round nylon collar last."""
        rc = af / math.sqrt(3)
        hx = P._prism(P._hex(0, 0, af), 0, h * 0.66).intersect(
            rev([(0, 0), (af / 2 - 0.3, 0), (rc + 0.5, 0.9), (rc + 0.5, h), (0, h)]))
        collar = rev([(0, h * 0.66 - 0.2), (af * 0.45, h * 0.66 - 0.2), (af * 0.45, h - 0.9), (af * 0.45 - 0.9, h), (0, h)])
        return hx.union(collar).cut(P._cyl(0, 0, bore / 2, -1, h + 1))

    def plain_nut(af, h, bore):
        return P._prism(P._hex(0, 0, af), 0, h).cut(P._cyl(0, 0, bore / 2, -1, h + 1))

    def bearing():
        """608: 8 x 22 x 7, back face on z=0."""
        w, ro, ri = P.BRG_W, P.BRG_OD / 2, 4.0
        outer = rev([(ro - 1.7, 0), (ro - 0.3, 0), (ro, 0.3), (ro, w - 0.3), (ro - 0.3, w), (ro - 1.7, w)])
        inner = rev([(ri, 0), (ri + 1.7, 0), (ri + 1.7, w), (ri, w)])
        shield = rev([(ri + 1.6, 0.8), (ro - 1.6, 0.8), (ro - 1.6, w - 0.8), (ri + 1.6, w - 0.8)])
        return outer.union(inner).union(shield)

    def motor():
        """NEMA23 from the constants planetary.py's motor_dummy() uses, plus what a picture needs:
        the flange, the corner channels the M5 bolts run down, and the D-flat on the shaft."""
        seat, sq, ln, ft = Z_MOTOR_SEAT, P.MOTOR_SQ, P.MOTOR_LEN, P.MOTOR_FLANGE_T

        def slab(side, z0, z1):
            return cq.Workplane("XY").workplane(offset=z0).center(0, AY).rect(side, side).extrude(z1 - z0)

        body = slab(sq, seat - ln, seat - ft + 0.01)
        body = body.cut(slab(sq + 2, seat - ln + 13, seat - 18).cut(slab(sq - 1.6, seat - ln + 12, seat - 17)))
        m = slab(sq, seat - ft, seat)
        for hx, hy in M5_XY:
            body = body.cut(P._cyl(hx, hy, 7.2, seat - ln - 1, seat - ft))
            m = m.cut(P._cyl(hx, hy, 2.6, seat - ft - 1, seat + 1))
        m = m.union(body).union(P._cyl(0, AY, P.MOTOR_PILOT_D / 2, seat - 1, seat + P.MOTOR_PILOT_H))
        r = P.MOTOR_SHAFT_D / 2
        shaft = P._cyl(0, AY, r, seat - 1, seat + P.MOTOR_SHAFT_LEN)
        flat_x = P.MOTOR_FLAT - r                     # same side as the flat in planetary.sun()
        z0 = seat + P.MOTOR_SHAFT_LEN - P.MOTOR_FLAT_LEN
        shaft = shaft.cut(box(flat_x, flat_x + 10, AY - 10, AY + 10, z0, z0 + P.MOTOR_FLAT_LEN + 1))
        return m.union(shaft)

    def clamp(x):
        """A 4 inch G-clamp: jaw on the base plate, screw pad under the table."""
        w, t = 12.0, 14.0
        top, low = P.BASE_T, P.BASE_T - 100.0
        z_sp = Z_BASE_REAR - 12.0
        z_tip = z_sp + 58.0
        c = box(x - w / 2, x + w / 2, top, top + t, z_sp - t, z_tip)
        c = c.union(box(x - w / 2, x + w / 2, low - t, top + t, z_sp - t, z_sp))
        c = c.union(box(x - w / 2, x + w / 2, low - t, low, z_sp - t, z_tip))
        zs = z_tip - 10.0
        up = lambda part: part.rotate((0, 0, 0), (1, 0, 0), -90)          # local +Z becomes +Y
        screw = up(P._cyl(0, 0, 5.0, low - t - 34.0, -TABLE_T - 4.0)).translate((x, 0, zs))
        pad = up(P._cyl(0, 0, 11.0, -TABLE_T - 5.0, -TABLE_T)).translate((x, 0, zs))
        bar = P._cyl(0, 0, 2.6, -32.0, 32.0).rotate((0, 0, 0), (0, 1, 0), 90).translate((x, low - t - 28.0, zs))
        return c.union(screw).union(pad).union(bar)

    def mug():
        """Bench prop for steps 4 and 5: rim against the spider's arms, opening toward the wall side."""
        z0, z1 = Z_SPIDER_FRONT, Z_SPIDER_FRONT + MUG_H
        m = P._cyl(0, 0, MUG_R, z0, z1).cut(P._cyl(0, 0, MUG_R - 4.0, z0 - 1, z1 - 6.0))
        loop = box(MUG_R - 3, MUG_R + 27, -6, 6, z0 + 14, z0 + 66).cut(box(MUG_R - 4, MUG_R + 17, -7, 7, z0 + 24, z0 + 56))
        return m.union(loop).rotate((0, 0, 0), (0, 0, 1), 215.0).translate((0, AY, 0))      # handle between two arms

    def tape(ang, x, y):
        """A strip of masking tape across one pin head, on the spider's front face."""
        strip = box(-4.0, 4.0, -13.0, 13.0, Z_SPIDER_FRONT, Z_SPIDER_FRONT + 0.5)
        return strip.rotate((0, 0, 0), (0, 0, 1), ang).translate((x, y, 0))

    solids = {}

    def add(name, solid, kind, tol=0.04, ang=0.15):
        solids[name] = (solid, tol, ang)
        KIND[name] = kind

    # ---- printed
    gs = P.gearset()
    for k, v in gs.items():
        add(k, P.place(v, P.GEAR_GAP), "printed", 0.05, 0.2)
    add("frame", P.frame(), "printed")
    add("spider", P.place(P.spider(), P.SPIDER_Z0), "printed")
    wh = P.wheel()
    add("wheel", P.place(wh, P.WHEEL_Z0, TURN), "printed")
    half = P.place(wh, P.WHEEL_Z0, 30.0)              # step 2: cut through two spokes, the post on the far half
    big = 400.0
    add("wheel_half", half.intersect(box(0.25, big, -big, big, -big, big)), "printed")
    add("wheel_half_cap", half.intersect(box(0.0, 0.25, -big, big, -big, big)), "cut")

    def on_wheel(part):                               # wheel-local to the model frame
        return part.rotate((0, 0, 0), (0, 0, 1), TURN).translate((0, AY, P.WHEEL_Z0))

    add("grip", on_wheel(P.grip().translate((P.R_HANDLE, 0, P.WHEEL_T + P.PED_H + 0.2))), "printed")
    for i, (x, y) in enumerate(PIN):
        add(f"pin_spacer{i + 1}", P.spacer(P.PIN_SPACER, flange=True).translate((x, y, 0)), "printed")
    add("hub_spacer", P.spacer(P.HUB_SPACER).translate((0, AY, P.WHEEL_Z0 + P.BRG_W)), "printed")

    def halved(name, solid, kind):                    # the far half and its cut face, for the step 2 section
        add(name + "_half", solid.intersect(box(0.25, big, -big, big, -big, big)), kind)
        add(name + "_half_cap", solid.intersect(box(0.0, 0.25, -big, big, -big, big)), "cut")

    halved("hub_spacer", P.spacer(P.HUB_SPACER).translate((0, AY, P.WHEEL_Z0 + P.BRG_W)), "printed")

    # ---- bench props
    add("mug", mug(), "table")
    for i, ((x, y), ang) in enumerate(zip(PIN, P.PIN_ANGLES)):
        add(f"tape{i + 1}", tape(ang, x, y), "tape")
    r = P.MOTOR_SHAFT_D / 2                           # the D-shaped end of the motor shaft on its own, for the step 6 detail
    stub = P._cyl(0, AY, r, 0.0, P.SHAFT_TIP_Z).cut(box(P.MOTOR_FLAT - r, P.MOTOR_FLAT - r + 10, AY - 10, AY + 10, -1, P.SHAFT_TIP_Z + 1))
    add("shaft_stub", stub, "motor", 0.02, 0.1)

    # ---- bought (washers are drawn as bought parts; the printed ones are the same size)
    w8 = P.washer(P.M8_HOLE, 16.0, P.WASHER_M8)
    brg = bearing()
    pin_bolt = flip(hex_bolt(8.0, P.PIN_BOLT_LEN, P.M8_HEAD_AF, P.M8_HEAD_T, 22.0))
    nut8 = nyloc(P.M8_HEAD_AF, P.NYLOC_M8, 6.6)
    for i, (x, y) in enumerate(PIN):
        n = i + 1
        add(f"brg_p{n}", brg.translate((x, y, Z_PLANET_BRG)), "bought")
        add(f"pin_bolt{n}", pin_bolt.translate((x, y, Z_PIN_HEAD)), "bought")
        add(f"pin_w{n}a", w8.translate((x, y, Z_SPIDER_BACK - P.WASHER_M8)), "bought")
        add(f"pin_w{n}b", w8.translate((x, y, Z_SPIDER_BACK - 2 * P.WASHER_M8)), "bought")
        add(f"rear_w{n}", w8.translate((x, y, Z_BOSS_BACK - P.WASHER_M8)), "bought")
        add(f"rear_nut{n}", flip(nut8).translate((x, y, Z_BOSS_BACK - P.WASHER_M8)), "bought")
    add("axle_bolt", hex_bolt(8.0, P.AXLE_BOLT_LEN, P.M8_HEAD_AF, P.M8_HEAD_T, 22.0).translate((0, AY, Z_AXLE_HEAD)), "bought")
    add("axle_w1", w8.translate((0, AY, Z_BOSS_FRONT)), "bought")
    add("brg_a", brg.translate((0, AY, P.WHEEL_Z0)), "bought")
    add("brg_b", brg.translate((0, AY, Z_BRG_B)), "bought")
    halved("brg_a", brg.translate((0, AY, P.WHEEL_Z0)), "bought")
    halved("brg_b", brg.translate((0, AY, Z_BRG_B)), "bought")
    add("axle_w2", w8.translate((0, AY, Z_HUB_FRONT)), "bought")
    add("axle_nut", nut8.translate((0, AY, Z_HUB_FRONT + P.WASHER_M8)), "bought")
    add("motor", motor(), "motor")
    for i, (hx, hy) in enumerate(M5_XY):
        add(f"m5_{i + 1}", socket_cap(5.0, P.M5_BOLT_LEN, 8.5, 5.0).translate((hx, hy, Z_M5_HEAD)), "bought")
    add("m6_nut", on_wheel(plain_nut(P.M6_NUT_AF, P.M6_NUT_T, 5.0).translate((P.R_HANDLE, 0, P.BOLT_END_RECESS))), "bought")
    add("m6_washer", on_wheel(P.washer(P.M6_HOLE, 18.0, P.WASHER_M6).translate((P.R_HANDLE, 0, Z_POST_TOP))), "bought")
    add("m6_bolt", on_wheel(flip(hex_bolt(6.0, P.HANDLE_BOLT_LEN, 10.0, 4.0, 24.0))
                            .translate((P.R_HANDLE, 0, Z_POST_TOP + P.WASHER_M6))), "bought")
    add("clamp1", clamp(-CLAMP_X), "bought")
    add("clamp2", clamp(CLAMP_X), "bought")
    add("table", box(-235.0, 235.0, -TABLE_T, 0.0, Z_BASE_REAR - 2.0, 175.0), "table")

    os.makedirs(MESH, exist_ok=True)
    for name, (solid, tol, ang) in solids.items():
        comp = cq.Compound.makeCompound(list(solid.vals()))
        vs, ts = comp.tessellate(tol, ang)
        m = trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(ts), process=True)
        if len(m.faces) == 0:
            sys.exit(f"{name}: empty mesh")
        sm = trimesh.graph.smooth_shade(m, angle=math.radians(30.0))     # split at edges sharper than 30 degrees
        np.savez_compressed(os.path.join(MESH, f"{name}.npz"), v=np.asarray(sm.vertices, np.float32),
                            f=np.asarray(sm.faces, np.int32))
        print(f"  {name:16s} {len(sm.faces):6d} triangles")
    with open(os.path.join(MESH, "_kinds.json"), "w") as fh:
        json.dump(KIND, fh, indent=1)


# ============================================================ the plan
PW, PH, HEAD = 1000, 1100, 150               # one panel, and the strip the title sits in (wide picture)
W, H = 2 * PW, PH + HEAD                     # the wide picture: the two panels side by side
# The phone picture stacks the same two panels (the move on top, the result under it), so every
# call-out is twice the size on a portrait screen. cad/assembly_steps_compose.py lays out both.


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def cam_front(a, el):
    """Standing in front of the machine, a degrees round to the right (negative: to the left), el up."""
    a, el = math.radians(a), math.radians(el)
    return dict(c=(math.sin(a) * math.cos(el), math.sin(el), math.cos(a) * math.cos(el)), up=(0, 1, 0))


def cam_back(a, el):
    """Standing behind the wall."""
    a, el = math.radians(a), math.radians(el)
    return dict(c=(math.sin(a) * math.cos(el), math.sin(el), -math.cos(a) * math.cos(el)), up=(0, 1, 0))


def cam_bench(az, el, up_is_front):
    """The part lying on the bench with the model's axis vertical. up_is_front: its FRONT faces up.
    A negative el looks up at it from underneath; up stays up."""
    az, el, s = math.radians(az), math.radians(el), (1.0 if up_is_front else -1.0)
    return dict(c=(math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), s * math.sin(el)), up=(0, 0, s))


def main():
    reuse = "--reuse" in sys.argv
    if reuse and os.path.exists(os.path.join(MESH, "_kinds.json")):
        KIND.update(json.load(open(os.path.join(MESH, "_kinds.json"))))
    else:
        print("building meshes (the gearset takes about half a minute)")
        build_meshes()
    verts = {n: np.load(os.path.join(MESH, f"{n}.npz"))["v"].astype(float) for n in KIND}

    def view(name, side, cam, inst, fit=None, fit_pts=None, arrows=(), guides=(), curves=(), callouts=(),
             inset=None, ppm_max=9.0):
        """side: "L" (the move) or "R" (the result). inset: x, y, w, h inside that panel, or None for
        the whole panel. fit: the box inside the view the parts must stay in. Arrows are straight and
        end in a head; guides are dashed with no head; curves are polylines with a head at both ends."""
        px = 0 if side == "L" else PW
        x, y, w, h = (px, HEAD, PW, PH) if inset is None else (px + inset[0], HEAD + inset[1], inset[2], inset[3])
        c, up0 = unit(cam["c"]), unit(cam["up"])
        right = unit(np.cross(up0, c))
        up = np.cross(c, right)
        if fit_pts is None:
            pts = np.vstack([verts[m] + np.asarray(off, float) for m, _, off in inst])
        else:
            pts = np.asarray(fit_pts, float)
        u, v = pts @ right, pts @ up
        fx0, fy0, fx1, fy1 = fit or (50, 50, w - 50, h - 50)
        ppm = min((fx1 - fx0) / (u.max() - u.min()), (fy1 - fy0) / (v.max() - v.min()), ppm_max)
        # the middle of the parts lands on the middle of the fit box
        cu, cv = (u.max() + u.min()) / 2, (v.max() + v.min()) / 2
        du = ((fx0 + fx1) / 2 - w / 2) / ppm
        dv = -((fy0 + fy1) / 2 - h / 2) / ppm
        target = right * (cu - du) + up * (cv - dv) + c * float((pts @ c).mean())
        f3 = lambda p: [float(t) for t in p]
        lines = [dict(pts=[f3(a), f3(b)], heads="end", dash=False) for a, b in arrows]
        lines += [dict(pts=[f3(a), f3(b)], heads="none", dash=True) for a, b in guides]
        lines += [dict(pts=[f3(p) for p in pl], heads="both", dash=False) for pl in curves]
        return dict(name=name, panel=side, rect=[x, y, w, h], inset=inset is not None, ppm=ppm,
                    cam=dict(c=c.tolist(), up=up.tolist(), right=right.tolist(), target=target.tolist()),
                    inst=[dict(mesh=m, role=r, off=f3(off)) for m, r, off in inst], arrows=lines,
                    callouts=[dict(text=t, at=None if at is None else f3(at), xy=list(xy)) for t, at, xy in callouts])

    Z0 = (0.0, 0.0, 0.0)
    PROP = ("table", "tape")                 # bench props keep their own colour even while they move with a part

    def fitted(names):
        return [(n, KIND[n], Z0) for n in names]

    def moved(offs, seated=False):
        role = lambda n: KIND[n] if KIND[n] in PROP else ("cut_accent" if KIND[n] == "cut" else "accent")
        return [(n, role(n), Z0 if seated else off) for n, off in offs.items()]

    def dz(d):
        return (0.0, 0.0, float(d))

    def polar(r, deg, z):
        return (r * math.cos(math.radians(deg)), AY + r * math.sin(math.radians(deg)), z)

    GEARS = ["ring", "sun", "planet1", "planet2", "planet3"]
    PBRG = ["brg_p1", "brg_p2", "brg_p3"]
    PIN_BOLTS = [f"pin_bolt{i}" for i in (1, 2, 3)]
    SPIDER_SUB = ["spider", "axle_bolt"] + PIN_BOLTS + [f"pin_w{i}{s}" for i in (1, 2, 3) for s in "ab"]
    SPACERS = [f"pin_spacer{i}" for i in (1, 2, 3)]
    TAPES = ["tape1", "tape2", "tape3"]
    CART = SPIDER_SUB + GEARS + PBRG + SPACERS
    MOTORED = ["frame", "motor", "m5_1", "m5_2", "m5_3", "m5_4"]
    REAR_W = [f"rear_w{i}" for i in (1, 2, 3)]
    REAR_N = [f"rear_nut{i}" for i in (1, 2, 3)]
    REAR = REAR_W + REAR_N
    WHEEL_SUB = ["wheel", "brg_a", "hub_spacer", "brg_b"]
    AXLE_STACK = ["axle_w1"] + WHEEL_SUB + ["axle_w2", "axle_nut"]
    HANDLE = ["m6_nut", "grip", "m6_washer", "m6_bolt"]
    dogs = [polar(P.R_OUT, a, 0.0)[:2] for a in P.DOG_ANGLES]
    Z_DOG_TIP = P.GEAR_GAP + P.RING_H + P.DOG_H                    # 44.9, the front end of the dogs
    steps = []

    # ---------------------------------------------------------------- 1: free the gears, bearings into the planets
    cam = cam_bench(BENCH_AZ, 42, True)
    new = {n: dz(62) for n in PBRG}
    arrows = [((x, y, Z_PLANET_BRG + 62 - 2), (x, y, Z_PLANET_FRONT + 1)) for x, y in PIN]
    twist = [polar(P.R_OUT + 13, a, P.GEAR_GAP + 9) for a in np.linspace(168, 236, 30)]     # round the ring's left side
    fit1 = (70, 250, PW - 60, PH - 200)
    steps.append(dict(n="1", title="Free the gears, then a 608 bearing into each planet.", views=[
        view("s1_move", "L", cam, fitted(GEARS) + moved(new), fit=fit1, arrows=arrows, curves=[twist], callouts=[
            ("1. FIRST twist the ring\nagainst the sun until all\n5 gears turn. Do not\npull them apart.", twist[2], (30, 20)),
            ("2. 608 bearing, x3:\npress one into the\nfront of each planet", (PIN[0][0], PIN[0][1], Z_PLANET_FRONT + 62 + 5), (560, 20)),
            ("front of the planet: the face\nthat was up on the printer", (PIN[2][0] - 34, PIN[2][1], Z_PLANET_FRONT), (30, 960)),
        ]),
        view("s1_done", "R", cam, fitted(GEARS) + moved(new, True), fit=fit1, callouts=[
            ("pressed in flush", (PIN[0][0] + 8, PIN[0][1], Z_PLANET_FRONT), (560, 110)),
            ("all five gears still turn", None, (30, 990)),
        ]),
    ]))

    # ---------------------------------------------------------------- 2: bearings and spacer into the wheel hub
    cam = cam_front(-66, 16)
    new = {"brg_a": dz(-50), "hub_spacer": dz(40), "brg_b": dz(70)}
    half = fitted(["wheel_half", "wheel_half_cap"])
    cut = {n + s: dz(0) for n in ("brg_a", "hub_spacer", "brg_b") for s in ("_half", "_half_cap")}
    arrows = [((0, AY, P.WHEEL_Z0 + P.BRG_W - 50 + 2), (0, AY, P.WHEEL_Z0 - 1)),
              ((0, AY, P.WHEEL_Z0 + P.BRG_W + 40 - 2), (0, AY, Z_HUB_FRONT + 1)),
              ((0, AY, Z_BRG_B + 70 - 2), (0, AY, P.WHEEL_Z0 + P.BRG_W + P.HUB_SPACER + 40 + 2))]
    post = (P.R_HANDLE * math.cos(math.radians(30)), AY + P.R_HANDLE * math.sin(math.radians(30)) + 7, P.WHEEL_Z0 + 60)
    fit2 = (60, 250, PW - 60, PH - 30)
    steps.append(dict(n="2", title="Wheel hub: bearing in the back, then spacer, then bearing.", views=[
        view("s2_move", "L", cam, half + moved(new), fit=fit2, arrows=arrows, callouts=[
            ("1. 608 bearing into the BACK (the\nface that was on the printer bed)", (0, AY + 11, P.WHEEL_Z0 - 50 + 3.5), (30, 20)),
            ("2. hub spacer", (0, AY + 6, P.WHEEL_Z0 + P.BRG_W + 40 + 3), (640, 560)),
            ("3. 608 bearing", (0, AY - 11, Z_BRG_B + 70 + 3.5), (680, 800)),
            ("handle post:\nthis side is\nthe FRONT", post, (720, 190)),
            ("cut view: the\nwheel is drawn\nsliced in half", (0, AY - 40, P.WHEEL_Z0 + 6), (30, 780)),
        ]),
        view("s2_done", "R", cam, half + moved(cut, True), fit=fit2, callouts=[
            ("to press bearing 1 in: lay the wheel front\ndown, the post hanging over the table edge", None, (30, 20)),
            ("spacer sits between\nthe two bearings", (0, AY - 4, P.WHEEL_Z0 + P.BRG_W + 3), (540, 820)),
        ]),
    ]))

    # ---------------------------------------------------------------- 3: motor onto the back of the wall
    cam = cam_back(-38, 24)
    e_m = 78.0
    top = AY + P.MOTOR_SQ / 2
    e_b = 104.0
    bolts = {f"m5_{i}": dz(-e_b) for i in (1, 2, 3, 4)}
    z_mouth = Z_MOTOR_SEAT - P.MOTOR_LEN                     # the back of the motor, where the corner channels open
    near = cam_back(-15, 17)                                 # nearly along the shaft: all four channels are in sight
    near_pts = [(sx * 44, AY + sy * 44, zz) for sx in (-1, 1) for sy in (-1, 1) for zz in (Z_M5_HEAD - e_b - 6, -8)]
    steps.append(dict(n="3", title="Bolt the motor onto the back of the wall.", views=[
        view("s3_move", "L", cam, fitted(["frame"]) + moved({"motor": dz(-e_m)}), fit=(150, 150, PW - 30, PH - 110),
             arrows=[((0, top, Z_MOTOR_SEAT - e_m + 2), (0, top, -P.WALL_T - 1))], callouts=[
            ("1. motor onto the BACK of the wall", (0, top, Z_MOTOR_SEAT - e_m - 20), (30, 20)),
            ("BACK of the wall", (-62, AY + 62, -P.WALL_T), (600, 110)),
        ]),
        view("s3_shaft", "L", cam_front(-38, 22), moved({"motor": Z0}), inset=(20, 640, 380, 445), fit=(40, 200, 340, 425), callouts=[
            ("this end goes in:\nthe shaft, through\nthe big hole", (0, AY + 2, Z_MOTOR_SEAT + P.MOTOR_SHAFT_LEN - 4), (18, 12)),
        ]),
        view("s3_bolts", "R", near, fitted(["frame", "motor"]) + moved(bolts), inset=(20, 150, 960, 640), fit=(150, 60, 810, 580), fit_pts=near_pts,
             arrows=[((hx, hy, Z_M5_HEAD + P.M5_BOLT_LEN - e_b + 2), (hx, hy, z_mouth + 1)) for hx, hy in M5_XY], callouts=[
            ("2. M5 x 12 socket cap, x4: one down\nthe channel in each corner of the motor", (M5_XY[0][0], M5_XY[0][1] + 3, Z_M5_HEAD - e_b - 4), (10, -130)),
            ("4 mm hex key. Drive slowly: the bolts cut their\nown thread. Stop when the flange is tight.\nThe wires can point any way round; up is\neasiest.", None, (10, 660)),
        ]),
    ]))

    # ---------------------------------------------------------------- 4: bolts and washers into the spider (bench)
    cam = cam_bench(BENCH_AZ, 22, False)
    new = {"axle_bolt": dz(-62)}
    new.update({n: dz(74) for n in PIN_BOLTS})
    new.update({f"pin_w{i}a": dz(-66) for i in (1, 2, 3)})
    new.update({f"pin_w{i}b": dz(-76) for i in (1, 2, 3)})
    arrows = [((0, AY, Z_AXLE_TIP - 62 + 1), (0, AY, Z_SPIDER_BACK - 1))]
    arrows += [((x, y, Z_PIN_TIP + 74 - 1), (x, y, Z_SPIDER_FRONT + 1)) for x, y in PIN]
    arrows += [((x, y, Z_SPIDER_BACK - 66 + 1), (x, y, Z_SPIDER_BACK - 1)) for x, y in PIN]
    steps.append(dict(n="4", title="Bolts into the spider, then two washers on each pin.", views=[
        view("s4_move", "L", cam, fitted(["spider"]) + moved(new), fit=(110, 230, PW - 270, PH - 30), arrows=arrows, callouts=[
            ("1. M8 x 40: head in the hex\npocket on the flat side", (0, AY, Z_AXLE_HEAD - P.M8_HEAD_T - 62), (30, 20)),
            ("3. two M8 washers\non each pin\n(printed or steel)", (PIN[1][0] - 8, PIN[1][1], Z_SPIDER_BACK - 72), (590, 20)),
            ("flat side\nup", (PIN[1][0] - 12, PIN[1][1] + 6, Z_SPIDER_BACK), (800, 500)),
            ("2. M8 x 50, x3:\nup from\nunderneath", (PIN[1][0] - 5, PIN[1][1], Z_PIN_HEAD + 74 - 22), (720, 800)),
        ]),
        view("s4_done", "R", cam, fitted(["mug", "spider"]) + moved(new, True), fit=(30, 60, 540, 640), callouts=[
            ("three pins\npoint up", (PIN[1][0] - 4, PIN[1][1], Z_PIN_TIP + 6), (720, 40)),
            ("stand it on a mug: the axle\nbolt hangs inside", polar(MUG_R, BENCH_AZ - 40, Z_SPIDER_FRONT + 62), (30, 690)),
        ]),
        view("s4_under", "R", cam_bench(BENCH_AZ, -36, False), fitted(["spider"]) + moved(new, True) + fitted(TAPES),
             inset=(560, 390, 420, 440), fit=(25, 25, 395, 415), callouts=[
            ("underneath: masking tape over each bolt\nhead stops the bolts dropping out. Peel it\noff after step 6.", (PIN[2][0], PIN[2][1], Z_SPIDER_FRONT + 0.5), (-530, 510)),
        ]),
    ]))

    # ---------------------------------------------------------------- 5: gearset and pin spacers onto the pins (bench)
    cam = cam_bench(STEP5_AZ, 20, False)                           # seen from here, pin 1 is on the left and pin 2 on the right
    e_g, e_s = 72.0, 108.0
    stand = fitted(["mug"] + SPIDER_SUB)
    new_l = {n: dz(-e_g) for n in GEARS + PBRG}
    new_l.update({n: dz(-e_s) for n in SPACERS})
    new_r = {n: dz(0) for n in GEARS + PBRG + SPACERS}
    arrows = [((x, y, Z_PLANET_FRONT - e_g + 1), (x, y, Z_PIN_TIP - 1)) for x, y in PIN]
    arrows += [((x, y, P.PIN_SPACER - e_s + 1), (x, y, P.GEAR_GAP - e_g - 1)) for x, y in PIN]
    dog_l, dog_r = polar(P.R_OUT, 330.0, Z_DOG_TIP - 5), polar(P.R_OUT, 210.0, Z_DOG_TIP - 5)
    steps.append(dict(n="5", title="Lower the gearset onto the pins, then the pin spacers.", views=[
        view("s5_move", "L", cam, stand + moved(new_l), fit=(50, 220, PW - 50, PH - 85), arrows=arrows, callouts=[
            ("1. gearset: FRONT face\ndown, dogs point DOWN", (dog_l[0], dog_l[1], dog_l[2] - e_g), (30, 20)),
            ("2. pin spacer, x3:\nwide foot on top", (PIN[1][0] - 11, PIN[1][1], -e_s), (620, 20)),
            ("each pin goes\nthrough a planet\nbearing", (PIN[0][0], PIN[0][1], Z_PIN_TIP + 12), (20, 770)),
            ("spider still on the mug", polar(MUG_R, STEP5_AZ + 30, Z_SPIDER_FRONT + 70), (30, 1030)),
        ]),
        view("s5_done", "R", cam, stand + moved(new_r, True), fit=(60, 200, PW - 60, PH - 120), callouts=[
            ("wide foot of each spacer on top", (PIN[1][0] - 11, PIN[1][1], 0), (60, 60)),
            ("the six dogs\npoint down", dog_r, (700, 900)),
        ]),
    ]))

    # ---------------------------------------------------------------- 6a: cartridge onto the wall
    cam = cam_front(-68, 18)
    e_c = 140.0
    cart = {n: dz(e_c) for n in CART + TAPES}
    arrows = [((x, y, Z_PIN_TIP + e_c - 1), (x, y, 1)) for x, y in PIN]
    arrows += [((0, AY, P.GEAR_GAP + e_c - 1), (0, AY, P.SHAFT_TIP_Z + 1))]
    hi = lambda n: "accent" if n in PIN_BOLTS + ["sun"] else KIND[n]          # the four things that have to line up
    behind = cam_back(34, 24)
    end_on = cam_back(20, 13)                                # nearly along the shaft, so both D shapes read as a D
    e_d = 44.0
    stub_off = dz(-e_d)
    flat_x = P.MOTOR_FLAT - P.MOTOR_SHAFT_D / 2
    flat_pts = [(sx * 23, AY + sy * 23, P.GEAR_GAP) for sx in (-1, 1) for sy in (-1, 1)]         # the back face of the sun
    steps.append(dict(n="6a", title="Cartridge onto the wall: pins in, sun onto the shaft.", views=[
        view("s6a_move", "L", cam, fitted(MOTORED) + moved(cart), fit=(330, 170, PW - 20, 610), arrows=arrows, callouts=[
            ("stand the cartridge up, pins toward the wall.\nThumbs on the taped bolt heads.", None, (30, 20)),
            ("1. three pins\ninto three\nholes", (PIN[1][0], PIN[1][1] + 5, 0), (30, 170)),
            ("2. sun onto\nthe motor\nshaft", (0, AY - 3, P.SHAFT_TIP_Z - 4), (30, 400)),
        ]),
        view("s6a_back", "L", behind, [(n, hi(n), Z0) for n in CART], inset=(20, 630, 445, 455), fit=(40, 140, 405, 440), callouts=[
            ("back of the cartridge:\n3 pins and the sun", None, (18, 12)),
        ]),
        view("s6a_flat", "L", end_on, [("sun", "accent", Z0), ("shaft_stub", "motor", stub_off)], inset=(480, 630, 500, 455),
             fit=(40, 180, 360, 465), fit_pts=flat_pts, ppm_max=6.0,
             guides=[((0, AY, P.GEAR_GAP - 1), (0, AY, P.SHAFT_TIP_Z - e_d + 1))], callouts=[
            ("turn the ring until the\nflat in the sun meets the\nflat on the shaft", None, (18, 12)),
            ("flat", (flat_x, AY + 1, 4.0 - e_d), (400, 230)),
            ("flat", (flat_x, AY - 1.5, P.GEAR_GAP), (30, 395)),
        ]),
        view("s6a_done", "R", cam, fitted(MOTORED) + moved(cart, True), fit=(60, 200, PW - 60, PH - 230), callouts=[
            ("pushed home: only a 3 mm gap\nbetween the ring and the wall", polar(P.R_OUT, 100.0, P.GEAR_GAP / 2), (30, 30)),
            ("keep a hand on it: nothing holds\nit until the nuts are on (next picture)", None, (30, 950)),
        ]),
    ]))

    # ---------------------------------------------------------------- 6b: washers and nylocs behind the wall
    back = cam_back(-40, 24)
    e_w, e_n = 34.0, 62.0
    rear = {n: dz(-e_w) for n in REAR_W}
    rear.update({n: dz(-e_n) for n in REAR_N})
    zw = Z_BOSS_BACK - P.WASHER_M8
    arrows = [((x, y, zw - e_w + 2.5), (x, y, Z_PIN_TIP - 1)) for x, y in PIN]
    arrows += [((x, y, zw - e_n + 1), (x, y, zw - e_w - 1.5)) for x, y in PIN]
    back_pts = [(sx * 72, yy, zz) for sx in (-1, 1) for yy in (AY - 80, AY + 48) for zz in (-70, 0)]    # the three bosses
    card, fit6 = (20, 205, 960, 745), (40, 25, 920, 720)
    steps.append(dict(n="6b", title="Behind the wall: washer and nyloc nut on each pin.", views=[
        view("s6b_move", "L", back, fitted(MOTORED + CART) + moved(rear), inset=card, fit=fit6, fit_pts=back_pts,
             arrows=arrows, callouts=[
            ("1. M8 washer, x3", (PIN[0][0], PIN[0][1] + 8, zw - e_w), (10, -185)),
            ("2. M8 nyloc nut, x3:\nnylon collar away\nfrom the wall", (PIN[1][0], PIN[1][1] + 6, zw - e_n - 5), (540, -185)),
            ("13 mm spanner. The hex pockets in the\nspider hold the bolt heads for you.", None, (10, 765)),
        ]),
        view("s6b_done", "R", back, fitted(MOTORED + CART) + moved(rear, True), inset=card, fit=fit6, fit_pts=back_pts, callouts=[
            ("all three firm", (PIN[1][0], PIN[1][1] + 6, zw - 9), (540, -130)),
            ("now peel the tape off the three\nbolt heads at the front", None, (10, 765)),
        ]),
    ]))

    # ---------------------------------------------------------------- 7: wheel onto the axle
    cam = cam_front(-70, 17)
    e1, e2, e3, e4 = 75.0, 150.0, 195.0, 225.0
    new = {"axle_w1": dz(e1)}
    new.update({n: dz(e2) for n in WHEEL_SUB})
    new.update({"axle_w2": dz(e3), "axle_nut": dz(e4)})
    zn = Z_HUB_FRONT + P.WASHER_M8
    arrows = [((0, AY, Z_BOSS_FRONT + e1 - 2), (0, AY, Z_AXLE_TIP + 2)),
              ((0, AY, P.WHEEL_Z0 + e2 - 2), (0, AY, Z_BOSS_FRONT + P.WASHER_M8 + e1 + 3)),
              ((0, AY, Z_HUB_FRONT + e3 - 2), (0, AY, Z_HUB_FRONT + e2 + 3)),
              ((0, AY, zn + e4 - 2), (0, AY, zn + e3 + 2))]
    top_dog = (dogs[1][0], dogs[1][1], Z_DOG_TIP)
    top_notch = (dogs[1][0], dogs[1][1], P.WHEEL_Z0 + e2)
    built = MOTORED + CART + REAR
    c1, c2, c3, c4 = 20.0, 46.0, 64.0, 78.0                       # the same four parts, pulled out less, for the close-up
    close = fitted(["spider", "axle_bolt"]) + [("axle_w1", "accent", dz(c1)), ("wheel_half", "accent", dz(c2)), ("wheel_half_cap", "cut_accent", dz(c2))]
    close += [(n + s, KIND[n + s], dz(c2)) for n in ("brg_a", "hub_spacer", "brg_b") for s in ("_half", "_half_cap")]
    close += [("axle_w2", "accent", dz(c3)), ("axle_nut", "accent", dz(c4))]
    close_pts = [(0, AY + sy * 21, zz) for sy in (-1, 1) for zz in (16, zn + c4 + P.NYLOC_M8 + 4)]
    steps.append(dict(n="7", title="Washer, wheel, washer, nyloc nut onto the axle. Snug only.", views=[
        view("s7_move", "L", cam, fitted(built) + moved(new), fit=(30, 230, PW - 30, 740), arrows=arrows,
             guides=[(top_dog, top_notch)], callouts=[
            ("turn the wheel until the 6 dogs\ndrop into the 6 notches", None, (30, 20)),
            ("dog", top_dog, (300, 150)),
            ("notch", (top_notch[0], top_notch[1] - 2, top_notch[2] + 6), (730, 150)),
            ("1", (0, AY - 8, Z_BOSS_FRONT + e1), (535, 480)),
            ("2", polar(P.R_OUT, 270.0, P.WHEEL_Z0 + e2 + 6), (700, 690)),
            ("3", (0, AY - 8, Z_HUB_FRONT + e3), (772, 500)),
            ("4", (0, AY - 7, zn + e4 + 4), (840, 500)),
        ]),
        view("s7_close", "L", cam_front(-80, 9), close, inset=(20, 765, 960, 320), fit=(30, 30, 930, 290), fit_pts=close_pts, ppm_max=6.2, callouts=[
            ("axle", (0, AY + 4, Z_BOSS_FRONT + 10), (40, 14)),
            ("1. washer", (0, AY + 8, Z_BOSS_FRONT + c1), (280, 14)),
            ("2. wheel (drawn cut)", (0, AY - 19, P.WHEEL_Z0 + c2 + 9), (40, 258)),
            ("3. washer", (0, AY + 8, Z_HUB_FRONT + c3), (690, 14)),
            ("4. nyloc nut", (0, AY - 7, zn + c4 + 4), (720, 258)),
        ]),
        view("s7_done", "R", cam_front(-56, 18), fitted(built) + moved(new, True), fit=(60, 190, PW - 60, PH - 230), callouts=[
            ("all 6 dogs sit in their notches", (dogs[1][0] - 3, dogs[1][1] - 2, P.WHEEL_Z0 + P.WHEEL_T), (60, 30)),
            ("13 mm spanner. Snug, not tight: the wheel must\nspin freely and the ring should rattle a little.", (0, AY - 5, zn + 6), (30, 890)),
            ("M8 washers used: 6 + 3 + 2 = 11. One is spare.", None, (30, 1020)),
        ]),
    ]))

    # ---------------------------------------------------------------- 8: the handle
    cam = cam_front(-56, 18)
    hx, hy = polar(P.R_HANDLE, TURN, 0.0)[:2]
    zp = P.WHEEL_Z0 + Z_POST_TOP                          # top of the post
    zg = P.WHEEL_Z0 + P.WHEEL_T + P.PED_H                 # where the grip's disc ends up
    g1, g2, g3 = 112.0, 142.0, 262.0
    new = {"m6_nut": dz(-26), "grip": dz(g1), "m6_washer": dz(g2), "m6_bolt": dz(g3)}
    front = {k: v for k, v in new.items() if k != "m6_nut"}
    arrows = [((hx, hy, zg + g1 - 2), (hx, hy, zp + 3)),
              ((hx, hy, zp + g2 - 2), (hx, hy, zg + P.GRIP_LEN + g1 + 3)),
              ((hx, hy, P.WHEEL_Z0 + P.BOLT_END_RECESS + g3 - 2), (hx, hy, zp + P.WASHER_M6 + g2 + 3))]
    built = MOTORED + CART + REAR + AXLE_STACK
    zoom = [(hx - 60, hy - 150, P.WHEEL_Z0), (hx + 30, hy + 45, P.WHEEL_Z0), (hx, hy + 14, zp + g3 + 6), (hx, hy - 14, zp + g3 + 6)]
    # The pictures keep the post at 120 degrees: the wheel's notches only meet the ring's dogs every 60 degrees,
    # so "post at the top" (where no planet is behind the nut pocket) is said in words, not drawn.
    wb = cam_back(28, 22)
    nut_pts = [(hx + dx, hy + dy, P.WHEEL_Z0 + dzz) for dx in (-52, 52) for dy in (-46, 46) for dzz in (-30, 12)]
    window = polar(72.0, TURN + 27.0, P.WHEEL_Z0 + P.WHEEL_T)      # the window beside the post's spoke
    steps.append(dict(n="8", title="Handle: M6 nut behind, then grip, penny washer, bolt.", views=[
        view("s8_nut", "L", wb, fitted(["wheel"]) + moved({"m6_nut": dz(-26)}), inset=(20, 20, 440, 400),
             fit=(20, 20, 420, 380), fit_pts=nut_pts,
             arrows=[((hx, hy, P.WHEEL_Z0 + P.BOLT_END_RECESS + P.M6_NUT_T - 26 + 1), (hx, hy, P.WHEEL_Z0 - 1))], callouts=[
            ("1. M6 nut into the hex\npocket behind the post.", (hx, hy, P.WHEEL_Z0 - 26), (475, 10)),
            ("Wheel drawn alone, seen\nfrom the wall side: yours\nstays on the machine.\nTurn the post to the top;\nfingertip on the nut.", None, (475, 130)),
        ]),
        view("s8_move", "L", cam, fitted(built + ["m6_nut"]) + moved(front), fit=(30, 580, PW - 40, PH - 20), fit_pts=zoom, arrows=arrows, callouts=[
            ("reach in here\nfor the nut", window, (30, 450)),
            ("2. grip: disc\ntoward the wheel", (hx, hy + 19, zg + g1 + 2), (350, 450)),
            ("3. M6 x 18 penny washer\n(printed or steel)", (hx, hy - 9, zp + g2), (450, 960)),
            ("4. M6 x 90 bolt", (hx, hy - 5, zp + g3 + 4), (690, 880)),
        ]),
        view("s8_done", "R", cam, fitted(built) + moved(new, True), fit=(60, 200, PW - 60, PH - 120), callouts=[
            ("10 mm spanner: bolt tight into the\nnut; the grip still turns", (hx, hy + 5, zp + P.WASHER_M6 + 4), (40, 30)),
        ]),
    ]))

    # ---------------------------------------------------------------- 9: clamp it down
    cam = cam_back(-40, 30)
    e_k = 140.0
    new = {"clamp1": dz(-e_k), "clamp2": dz(-e_k)}
    built = ["table"] + MOTORED + CART + REAR + AXLE_STACK + HANDLE
    z_tip = Z_BASE_REAR - 12.0 + 58.0
    arrows = [((sx * CLAMP_X, P.BASE_T + 7, z_tip - e_k + 2), (sx * CLAMP_X, P.BASE_T + 7, Z_BASE_REAR)) for sx in (-1, 1)]
    steps.append(dict(n="9", title="Clamp the base to the table with two G-clamps.", views=[
        view("s9_move", "L", cam, fitted(built) + moved(new), fit=(30, 260, PW - 30, PH - 130), arrows=arrows, callouts=[
            ("seen from behind (the motor side)", None, (30, 20)),
            ("G-clamp (100 mm), x2: jaw on the\nbase, between the gussets", (CLAMP_X, P.BASE_T + 14, Z_BASE_REAR - 20 - e_k), (30, 110)),
            ("back edge of the base\nat the table edge", (-20, 0, Z_BASE_REAR), (480, 980)),
        ]),
        view("s9_done", "R", cam, fitted(built) + moved(new, True), fit=(30, 260, PW - 30, PH - 130), callouts=[
            ("tighten both: it must not\nmove when you crank", (CLAMP_X, P.BASE_T + 14, Z_BASE_REAR - 20), (30, 30)),
            ("use a corner of the table, so you can\nstand beside the wheel to crank", None, (30, 980)),
        ]),
    ]))

    plan = dict(size=[W, H], head=HEAD, panel=[PW, PH],
                meshes={n: dict(file=f"meshes/{n}.npz", kind=k) for n, k in KIND.items()}, steps=steps)
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "placements.json"), "w") as fh:
        json.dump(plan, fh, indent=1)
    nv = sum(len(s["views"]) for s in steps)
    print(f"{len(KIND)} meshes, {len(steps)} pictures, {nv} views -> {os.path.join(BUILD, 'placements.json')}")


if __name__ == "__main__":
    main()
