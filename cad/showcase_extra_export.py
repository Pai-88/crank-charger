"""Showcase video, act 2 geometry: the electronics, the cover, a phone on its lead.

    .venv/bin/python cad/showcase_extra_export.py

Writes assembly/_build/meshes_extra/<name>.npz in the same form as the machine's meshes (vertices split
at sharp edges, model frame, millimetres), plus _extra.json with the phone's lead end and the camera's
points of interest. The cover parts are the view meshes cad/wire_cover_render.py already exports
(cad/stl/cover/_view_NOT_FOR_PRINTING/), untouched. New here: a generic phone lying on the table on the
USB side, its charging glyph, and the lead from the tester's stub to the phone, swept along a spline.
Nothing in the CAD is changed.
"""
import json
import math
import os
import sys

import cadquery as cq
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VIEW = os.path.join(HERE, "stl", "cover", "_view_NOT_FOR_PRINTING")
OUT = os.path.join(ROOT, "assembly", "_build", "meshes_extra")
sys.path.insert(0, HERE)
import wire_cover as wc                    # read only: the constants and the USB side

SIDE = wc.USB_SIDE
VIEW_PARTS = {                                # view mesh -> material role in the video
    "shell": "printed", "shell_open": "printed", "sled": "printed", "card": "card", "cardparts": "bought", "diodes": "diode",
    "pcb": "pcb", "socket": "bought", "modparts": "dark", "tester": "tester", "plug": "bought", "screen": "screen",
    "phone_lead": "cable", "wire_bundle": "wire", "wire_lead1": "wire", "wire_lead2": "wire", "wire_lead3": "wire",
    "wire_lead4": "wire", "wire_out_plus": "red", "wire_out_minus": "cable",
}
PHONE = (147.0, 72.0, 8.0)                    # a generic phone: long, wide, thick (mm)
PHONE_AT = (SIDE * 205.0, -30.0)              # where it lies on the table (model x, z), long axis turned toward the machine
PHONE_TURN = -SIDE * 28.0                     # degrees about the vertical
LEAD_D = 3.4                                  # the phone lead's diameter


def save(name, m):
    sm = trimesh.graph.smooth_shade(m, angle=math.radians(30.0))
    np.savez_compressed(os.path.join(OUT, f"{name}.npz"), v=np.asarray(sm.vertices, np.float32), f=np.asarray(sm.faces, np.int32))
    print(f"  {name:16s} {len(sm.faces):6d} triangles")


def solid_mesh(solid, tol=0.05, ang=0.2):
    comp = cq.Compound.makeCompound(list(solid.vals()))
    vs, ts = comp.tessellate(tol, ang)
    return trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(ts), process=True)


def rot_y(p, deg):
    a = math.radians(deg)
    x, y, z = p
    return np.array([x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a)])


def main():
    os.makedirs(OUT, exist_ok=True)
    roles = {}
    lead_end = None
    for name, role in VIEW_PARTS.items():
        m = trimesh.load(os.path.join(VIEW, name + ".stl"), force="mesh")
        if name == "phone_lead":                          # the stub leaves the tester along +-X: its far end
            far = m.vertices[:, 0].argmax() if SIDE > 0 else m.vertices[:, 0].argmin()
            xs = m.vertices[:, 0]
            end_pts = m.vertices[np.abs(xs - xs[far]) < 0.5]
            lead_end = end_pts.mean(axis=0)
        save(name, m)
        roles[name] = role

    # ---- the phone, lying flat, screen up, port end toward the machine
    L, W, T = PHONE
    body = (cq.Workplane("XZ").rect(L, W).extrude(-T)             # along +Y: y from 0 to T
            .edges("|Y").fillet(10.0).edges(">Y or <Y").fillet(1.6))
    screen = cq.Workplane("XZ").workplane(offset=-T).rect(L - 7.0, W - 5.0).extrude(-0.25).edges("|Y").fillet(7.0)
    body = body.cut(screen)
    glyph_box = cq.Workplane("XZ").workplane(offset=-T + 0.25).rect(26.0, 12.5).extrude(-0.5)
    glyph_hole = cq.Workplane("XZ").workplane(offset=-T + 0.25).rect(22.6, 9.1).extrude(-0.6)
    outline = glyph_box.cut(glyph_hole).edges("|Y").fillet(1.2)
    nub = cq.Workplane("XZ").workplane(offset=-T + 0.25).center(14.5, 0).rect(3.0, 5.0).extrude(-0.5)
    fill = cq.Workplane("XZ").workplane(offset=-T + 0.25).center(-6.0, 0).rect(9.5, 8.0).extrude(-0.5)
    port = cq.Workplane("YZ").workplane(offset=-L / 2 - 1).center(T / 2, 0).rect(3.0, 9.0).extrude(8.0)
    body = body.cut(port)
    # place: port end toward the machine, i.e. -X for the +X side
    turn = PHONE_TURN
    px, pz = PHONE_AT
    place = lambda s: s.rotate((0, 0, 0), (0, 1, 0), turn).translate((px, 0.0, pz))
    for name, solid, role in (("phone", place(body), "phone"), ("phone_glyph", place(outline.union(nub)), "glyph_dim"),
                              ("phone_fill", place(fill), "glyph")):
        save(name, solid_mesh(solid, 0.03, 0.15))
        roles[name] = role

    # ---- the lead: from the tester stub's end, down to the table and into the port
    port_pt = rot_y(np.array([-SIDE * (L / 2 - 1.0), T / 2, 0.0]), turn) + np.array([px, 0.0, pz])
    port_dir = rot_y(np.array([-SIDE, 0.0, 0.0]), turn)                     # pointing out of the port
    p0 = np.array(lead_end)
    d0 = np.array([SIDE, 0.0, 0.0])
    pts = [p0, p0 + d0 * 28.0 + np.array([0, -8.0, 6.0]), p0 + d0 * 60.0 + np.array([0, -30.0, 30.0]),
           (p0 + port_pt) / 2 + np.array([SIDE * 25.0, 0.0, 15.0]) * 0 + np.array([0.0, 0.0, 0.0]),
           port_pt + port_dir * 30.0 + np.array([0.0, 2.0, 0.0]), port_pt + port_dir * 6.0]
    pts[3][1] = max(pts[3][1], LEAD_D / 2 + 1.0)                            # never below the table
    path = cq.Workplane("XY").spline([tuple(map(float, p)) for p in pts], includeCurrent=False)
    tangent = pts[1] - pts[0]
    prof = cq.Workplane(cq.Plane(origin=tuple(map(float, pts[0])), normal=tuple(map(float, tangent / np.linalg.norm(tangent))))).circle(LEAD_D / 2)
    lead = prof.sweep(path, isFrenet=True)
    plug = cq.Workplane(cq.Plane(origin=tuple(map(float, port_pt + port_dir * 7.0)), normal=tuple(map(float, -port_dir)))).rect(6.0, 10.0).extrude(9.0).edges().fillet(1.2)
    save("lead", solid_mesh(lead.union(plug), 0.05, 0.25))
    roles["lead"] = "cable"

    card_centre = trimesh.load(os.path.join(VIEW, "card.stl"), force="mesh").bounds.mean(axis=0)
    phone_centre = np.array([px, T / 2, pz])
    json.dump(dict(side=SIDE, roles=roles, lead_end=[float(v) for v in lead_end], card_centre=[float(v) for v in card_centre],
                   phone_centre=[float(v) for v in phone_centre]), open(os.path.join(OUT, "_extra.json"), "w"), indent=1)
    print(f"{len(roles)} meshes -> {OUT}")


if __name__ == "__main__":
    main()
