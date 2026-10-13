"""Step-by-step assembly pictures, the drawing half of stage 2 (project venv, run by assembly_steps.py).

    .venv/bin/python cad/assembly_steps_compose.py           every step, then the two PDFs
    .venv/bin/python cad/assembly_steps_compose.py 4 6a      only these steps (no PDF)
    .venv/bin/python cad/assembly_steps_compose.py --grid 4  layout aid: a 100 px grid over the wide picture, in _build/

Turns the render passes in assembly/_build/passes/ into two sets of pictures from the same panels:

    assembly/phone/step_01_phone.png ...   1250 px wide, portrait: the move on top, the result under it.
    assembly/assembly_steps_phone.pdf      This is the set to read at the bench on a phone.
    assembly/step_01.png ...               2000 x 1250, landscape: the two panels side by side.
    assembly/assembly_steps.pdf            For a laptop or a print.

Per panel: flat colour by role (printed light grey, bought parts darker, the parts being added in
the one accent colour), soft shading from the surface normal, dark outlines wherever the part,
the depth or the surface direction changes, then the motion arrows and the Avenir call-outs on top.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assembly")
BUILD = os.path.join(OUT, "_build")
PASSES = os.path.join(BUILD, "passes")
SS = 2

AVENIR = "/System/Library/Fonts/Avenir.ttc"
HEAVY, MEDIUM, ROMAN = 4, 8, 11                      # faces inside Avenir.ttc
PX_STEP, PX_LINE, PX_CALL = 76, 46, 42               # final pixels; Avenir's cap height is 0.71 of the size
INK = (20, 20, 22)
ROLE = {                                             # linear-ish RGB, 0..1
    "printed": (0.90, 0.90, 0.91),
    "bought": (0.56, 0.58, 0.62),
    "motor": (0.40, 0.42, 0.46),
    "table": (0.97, 0.955, 0.93),
    "tape": (0.97, 0.87, 0.50),
    "cut": (0.70, 0.71, 0.73),
    "accent": (0.97, 0.47, 0.10),
    "cut_accent": (0.78, 0.33, 0.04),
}
LINE = np.array([0.10, 0.10, 0.12])
ARROW = (176, 62, 0)
LIGHT = np.array([-0.38, 0.52, 0.76])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
GRID = "--grid" in sys.argv
PHONE_W = 1250                                       # final width of a phone picture
PHONE_HEAD = 250                                     # its title strip, in the plan's own pixels (1000 wide)


def font(index, px):
    return ImageFont.truetype(AVENIR, int(round(px * SS)), index=index)


def render_view(view):
    """The shaded, outlined panel as float RGB plus its coverage mask, at SS times the final size."""
    d = np.load(os.path.join(PASSES, view["name"] + ".npz"))
    part = d["part"]
    hit = part > 0
    nx, ny, depth = d["nx"].astype(np.float32), d["ny"].astype(np.float32), d["depth"]
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 0.0, 1.0))
    lam = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
    shade = 0.60 + 0.40 * np.clip(0.5 + 0.5 * lam, 0.0, 1.0) ** 1.3
    lut = np.ones((256, 3), np.float32)
    for k, inst in enumerate(view["inst"]):
        lut[k + 1] = ROLE[inst["role"]]
    rgb = lut[part] * shade[..., None]

    # a soft contact shadow: darker where the surface lies deeper than its surroundings
    far = np.where(hit, depth, 0.0)
    cover = ndi.gaussian_filter(hit.astype(np.float32), 9.0 * SS) + 1e-6
    mean = ndi.gaussian_filter(far, 9.0 * SS) / cover
    sink = np.clip((mean - depth) / 30.0, 0.0, 1.0) * hit
    rgb *= (1.0 - 0.30 * sink)[..., None]
    rgb[~hit] = 1.0

    # outlines
    strong = np.zeros(part.shape, bool)
    weak = np.zeros(part.shape, bool)
    for ax in (0, 1):
        a = np.swapaxes(part, 0, ax)
        s = np.swapaxes(strong, 0, ax)
        wk = np.swapaxes(weak, 0, ax)
        dp = np.swapaxes(depth, 0, ax)
        n3 = [np.swapaxes(t, 0, ax) for t in (nx, ny, nz)]
        edge = a[1:] != a[:-1]                                   # a different part
        s[1:] |= edge
        s[:-1] |= edge
        same3 = (a[2:] == a[1:-1]) & (a[:-2] == a[1:-1]) & (a[1:-1] > 0)
        d1, d2 = dp[2:] - dp[1:-1], dp[1:-1] - dp[:-2]
        step = same3 & (np.abs(d1 - d2) > 0.5 + 0.5 * np.maximum(np.abs(d1), np.abs(d2)))   # a step in depth
        s[1:-1] |= step
        same2 = (a[1:] == a[:-1]) & (a[1:] > 0)
        turn = same2 & ((n3[0][1:] * n3[0][:-1] + n3[1][1:] * n3[1][:-1] + n3[2][1:] * n3[2][:-1]) < 0.80)  # a crease
        wk[1:] |= turn
        wk[:-1] |= turn
    strong = ndi.binary_dilation(strong, structure=np.ones((3, 3), bool))
    alpha = np.maximum(strong * 1.0, weak * 0.72)[..., None]
    rgb = rgb * (1 - alpha) + LINE * alpha
    return rgb, hit | strong


def project(view, p):
    """Model point to final-pixel coordinates inside the whole picture."""
    cam = view["cam"]
    q = np.asarray(p, float) - np.array(cam["target"])
    x, y, w, h = view["rect"]
    return (x + w / 2 + float(q @ np.array(cam["right"])) * view["ppm"],
            y + h / 2 - float(q @ np.array(cam["up"])) * view["ppm"])


def check_projection(view, hit):
    """The mask Blender drew and the box this file predicts must agree, or the arrows would lie.
    A zoomed view that crops its parts is skipped: there the outline is set by edges that cross
    the frame, not by corner points, and the uncropped views already prove the same projection."""
    pts = []
    for inst in view["inst"]:
        v = np.load(os.path.join(BUILD, "meshes", inst["mesh"] + ".npz"))["v"].astype(float) + np.array(inst["off"])
        pts.append(v)
    pts = np.vstack(pts) - np.array(view["cam"]["target"])
    w, h = view["rect"][2], view["rect"][3]
    u = w / 2 + pts @ np.array(view["cam"]["right"]) * view["ppm"]
    v = h / 2 - pts @ np.array(view["cam"]["up"]) * view["ppm"]
    if u.min() < 2 or u.max() > w - 2 or v.min() < 2 or v.max() > h - 2:
        return
    ys, xs = np.nonzero(hit)
    got = np.array([xs.min(), xs.max(), ys.min(), ys.max()]) / SS
    err = np.abs(got - np.array([u.min(), u.max(), v.min(), v.max()])).max()
    if err > 3.0:
        print(f"  WARNING {view['name']}: render and projection disagree by {err:.1f} px")


def draw_head(dr, b, v, colour, grow):
    perp = np.array([-v[1], v[0]])
    head, half = 17.0 * SS, 7.0 * SS
    base = b - v * head
    dr.polygon([tuple(b + v * grow), tuple(base + perp * (half + grow) - v * grow), tuple(base - perp * (half + grow) - v * grow)], fill=colour)


def draw_line(dr, pts, heads="end", dash=False):
    """A motion arrow (straight or curved, a head at the end or at both ends) or a dashed guide line.
    pts: final-pixel points."""
    pts = [np.array(p, float) * SS for p in pts]
    if np.linalg.norm(pts[-1] - pts[0]) < 1:
        return
    head = 17.0 * SS
    v_end = (pts[-1] - pts[-2]) / np.linalg.norm(pts[-1] - pts[-2])
    v_start = (pts[0] - pts[1]) / np.linalg.norm(pts[0] - pts[1])
    body = list(pts)
    if heads in ("end", "both"):
        body[-1] = pts[-1] - v_end * (head - SS)
    if heads == "both":
        body[0] = pts[0] - v_start * (head - SS)
    if dash:                                               # cut the line into 12 px dashes with 9 px gaps
        seg, out, on, left = [], [], True, 12.0 * SS
        for a, b in zip(body[:-1], body[1:]):
            d = np.linalg.norm(b - a)
            u, t = (b - a) / max(d, 1e-9), 0.0
            while t < d:
                step = min(left, d - t)
                if on:
                    out.append((a + u * t, a + u * (t + step)))
                t, left = t + step, left - step
                if left <= 1e-6:
                    on = not on
                    left = (12.0 if on else 9.0) * SS
        for colour, w in (((255, 255, 255), 6.5 * SS), (INK, 2.2 * SS)):
            for a, b in out:
                dr.line([tuple(a), tuple(b)], fill=colour, width=int(w))
        return
    for colour, grow in (((255, 255, 255), 2.0 * SS), (ARROW, 0.0)):
        dr.line([tuple(p) for p in body], fill=colour, width=int(2.5 * SS + 2 * grow), joint="curve")
        if heads in ("end", "both"):
            draw_head(dr, pts[-1], v_end, colour, grow)
        if heads == "both":
            draw_head(dr, pts[0], v_start, colour, grow)


def draw_callout(dr, view, call, f):
    x0, y0 = view["rect"][0] + call["xy"][0], view["rect"][1] + call["xy"][1]
    spacing = int(0.22 * PX_CALL * SS)
    box = dr.multiline_textbbox((x0 * SS, y0 * SS), call["text"], font=f, spacing=spacing)
    pad = 9 * SS
    bx0, by0, bx1, by1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
    # the leader starts at the lettering: either end of any line, above the first line or under the last
    rows = call["text"].split("\n")
    pitch = (box[3] - box[1]) / max(len(rows), 1)
    cands = []
    for k, row in enumerate(rows):
        wide = dr.textlength(row, font=f)
        yy = box[1] + pitch * (k + 0.5)
        cands += [(bx0, yy), (box[0] + wide + pad, yy)]
    cands += [(box[0] + dr.textlength(rows[0], font=f) / 2, by0), (box[0] + dr.textlength(rows[-1], font=f) / 2, by1)]
    px, py = [t * SS for t in project(view, call["at"])] if call["at"] else (mx, my)
    sx, sy = min(cands, key=lambda c: (c[0] - px) ** 2 + (c[1] - py) ** 2)
    if not (bx0 <= px <= bx1 and by0 <= py <= by1):
        dr.line([(sx, sy), (px, py)], fill=(255, 255, 255), width=int(5 * SS))
        dr.line([(sx, sy), (px, py)], fill=INK, width=int(1.6 * SS))
        r = 5.5 * SS
        dr.ellipse([px - r - SS, py - r - SS, px + r + SS, py + r + SS], fill=(255, 255, 255))
        dr.ellipse([px - r, py - r, px + r, py + r], fill=INK)
    dr.multiline_text((x0 * SS, y0 * SS), call["text"], font=f, fill=INK, spacing=spacing,
                      stroke_width=int(3 * SS), stroke_fill=(255, 255, 255))


def wrap(dr, text, f, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if cur and dr.textlength(trial, font=f) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


def compose(plan, step, phone=False):
    """phone=False: the two panels side by side. phone=True: the same two panels stacked, at 1000 px wide."""
    W, H = plan["size"]
    PW, PH = plan["panel"]
    head = plan["head"]
    views = []
    for view in sorted(step["views"], key=lambda v: v["inset"]):
        if phone:                                              # move every view from its place in the wide picture
            x, y, w, h = view["rect"]
            col = 0 if view["panel"] == "L" else 1
            view = dict(view, rect=[x - col * PW, y - head + PHONE_HEAD + col * PH, w, h])
        views.append(view)
    if phone:
        W, H = PW, PHONE_HEAD + 2 * PH
    canvas = np.ones((H * SS, W * SS, 3), np.float32)
    for view in views:
        rgb, hit = render_view(view)
        check_projection(view, hit)
        x, y, w, h = (t * SS for t in view["rect"])
        if view["inset"]:                                      # an inset is opaque: it covers what is under it
            card = Image.new("L", (w, h), 0)
            ImageDraw.Draw(card).rounded_rectangle([0, 0, w - 1, h - 1], radius=14 * SS, fill=255)
            keep = (np.asarray(card) > 127)[..., None]
            canvas[y:y + h, x:x + w] = np.where(keep, rgb, canvas[y:y + h, x:x + w])
        else:
            m = hit[..., None]
            canvas[y:y + h, x:x + w] = np.where(m, rgb, canvas[y:y + h, x:x + w])
    img = Image.fromarray((np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    for view in views:
        if view["inset"]:
            x, y, w, h = (t * SS for t in view["rect"])
            dr.rounded_rectangle([x, y, x + w, y + h], radius=14 * SS, outline=(60, 60, 64), width=int(2 * SS))
    if phone:
        yy = (PHONE_HEAD + PH) * SS
        dr.line([(30 * SS, yy), ((W - 30) * SS, yy)], fill=(205, 205, 208), width=SS)
    else:
        dr.line([(W * SS // 2, (head + 30) * SS), (W * SS // 2, (H - 30) * SS)], fill=(205, 205, 208), width=SS)
    for view in views:
        for line in view["arrows"]:
            draw_line(dr, [project(view, p) for p in line["pts"]], line["heads"], line["dash"])
    f_call = font(MEDIUM, PX_CALL)
    for view in views:
        for call in view["callouts"]:
            draw_callout(dr, view, call, f_call)
    f_step, f_line = font(HEAVY, PX_STEP), font(MEDIUM, PX_LINE)
    base = 104 * SS
    label = f"Step {step['n']}"
    dr.text((40 * SS, base), label, font=f_step, fill=INK, anchor="ls")
    if phone:
        for k, row in enumerate(wrap(dr, step["title"], f_line, (W - 80) * SS)):
            dr.text((40 * SS, (168 + 58 * k) * SS), row, font=f_line, fill=INK, anchor="ls")
        return img.resize((PHONE_W, round(H * PHONE_W / W)), Image.LANCZOS)
    dr.text((40 * SS + dr.textlength(label, font=f_step) + 36 * SS, base), step["title"], font=f_line, fill=INK, anchor="ls")
    img = img.resize((W, H), Image.LANCZOS)
    if GRID:                                           # layout aid only: never part of a delivered picture
        g = ImageDraw.Draw(img)
        small = ImageFont.truetype(AVENIR, 16, index=ROMAN)
        for x in range(0, W, 100):
            g.line([(x, 0), (x, H)], fill=(120, 170, 255), width=1)
            g.text((x + 3, plan["head"] + 2), str(x % 1000), font=small, fill=(0, 60, 200))
        for y in range(0, H, 100):
            g.line([(0, y), (W, y)], fill=(120, 170, 255), width=1)
            g.text((3, y + 2), str(y - plan["head"]), font=small, fill=(0, 60, 200))
    return img


def tag(step):
    n = step["n"]
    return n.zfill(2) if n.isdigit() else n.zfill(3)           # 01 .. 09, 06a, 06b


def main():
    with open(os.path.join(BUILD, "placements.json")) as fh:
        plan = json.load(fh)
    want = [a for a in sys.argv[1:] if not a.startswith("--")]
    phone_dir = os.path.join(OUT, "phone")
    os.makedirs(phone_dir, exist_ok=True)
    wide, tall = [], []
    for step in plan["steps"]:
        if want and step["n"] not in want:
            continue
        if len(step["title"].split()) > 10:
            sys.exit(f"step {step['n']}: the title is longer than ten words")
        img = compose(plan, step)
        path = os.path.join(BUILD if GRID else OUT, f"step_{tag(step)}{'_grid' if GRID else ''}.png")
        img.save(path, optimize=True)
        wide.append(img)
        print(f"wrote {path}")
        if not GRID:
            img = compose(plan, step, phone=True)
            path = os.path.join(phone_dir, f"step_{tag(step)}_phone.png")
            img.save(path, optimize=True)
            tall.append(img)
            print(f"wrote {path}")
    if not want and not GRID:
        for pages, name in ((wide, "assembly_steps.pdf"), (tall, "assembly_steps_phone.pdf")):
            pdf = os.path.join(OUT, name)
            pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=200.0, quality=95)
            print(f"wrote {pdf} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
