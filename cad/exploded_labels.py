"""Draw the labels on the exploded pictures.

    .venv/bin/python cad/exploded_labels.py [name ...]

Reads exploded/_raw/<name>.png and <name>_anchors.json (from cad/exploded_figures.py) and writes
exploded/<NN>_<name>.png, then exploded/crank_charger_pictures.pdf with all of them, in order. Labels sit in the
margins round the picture, set in Avenir Next, each with a leader to its part (the flat lay puts each label under
its part instead). A label names a part by the renderer's name, a named point, a (u, v) fraction, or a list of
names: the first gets the leader, every one a dot.
"""
import datetime
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "exploded", "_raw")
OUT = os.path.join(ROOT, "exploded")
FONT = "/System/Library/Fonts/Avenir Next.ttc"           # faces: 2 Demi Bold, 5 Medium, 7 Regular
PINB = [f"pin_bolt{i}" for i in (1, 2, 3)]
PINW = [f"pin_w{i}{s}" for i in (1, 2, 3) for s in "ab"]
PLANETS = ["planet1", "planet2", "planet3"]
BRG_P = ["brg_p1", "brg_p2", "brg_p3"]
SPACERS = ["pin_spacer1", "pin_spacer2", "pin_spacer3"]
REAR_N = ["rear_nut1", "rear_nut2", "rear_nut3"]
REAR_W = ["rear_w1", "rear_w2", "rear_w3"]
M5 = ["m5_3", "m5_1", "m5_4", "m5_2"]

ORDER = ["assembled", "machine", "cartridge", "hub", "electronics", "inside", "plates"]
GRID = {"plates"}                                         # labels under the parts, not round the edge
TITLES = {
    "assembled": ("The machine", "hand-crank phone charger, as built"),
    "machine": ("Every part, pulled apart", "along the axle, in the order they go on"),
    "cartridge": ("The gear cartridge", "one planetary stage, 91 : 17 = 5.35 to 1"),
    "hub": ("Hub and handle", "the wheel's bearings and the grip"),
    "electronics": ("The electronics", "lifted out of the cover"),
    "inside": ("Electronics in place", "cover off, everything wired"),
    "plates": ("The print files", "the machine's own parts, as exported, in print orientation"),
}
# (text, part or point or list or (u, v), small line underneath)
LABELS = {
    "assembled": [
        ("hand wheel", "wheel", "printed, 236 mm; the ring's six dogs sit in its notches"),
        ("grip", "grip", "printed; turns free on an M6 x 90 post"),
        ("ring gear", "ring_rim", "printed, 91 teeth, behind the wheel; its dogs drive it"),
        ("frame", "base", "printed; wall, base and five gussets in one piece"),
        ("wire cover", "cover_top", "printed; clicks on behind the wall"),
        ("inside the cover", "cover_side", "NEMA23 motor, 8 Schottkys, 1000 uF, 5 V converter"),
        ("USB meter", "tester", "volts and amps on the way to the phone"),
        ("phone lead", "lead", ""),
        ("phone", "phone", "charging at 5 V, up to 2 A"),
    ],
    "machine": [
        ("4 x M5 x 12", M5, "motor screws"),
        ("NEMA23 stepper", "motor", "the generator"),
        ("3 x M8 nyloc", REAR_N, "behind the wall"),
        ("3 x M8 washer", REAR_W, ""),
        ("frame", "frame", "printed, plate 4"),
        ("spider", "spider", "printed; fixed carrier"),
        ("M8 x 40 axle bolt", "axle_bolt", ""),
        ("3 x M8 x 50 pin", PINB, "one per planet"),
        ("6 x M8 washer", PINW, "two per pin"),
        ("ring gear, 91 teeth", "ring", "printed, plate 2; its dogs sit in the wheel"),
        ("3 x planet, 37 teeth", PLANETS, "printed with the ring"),
        ("sun, 17 teeth", "sun", "on the motor shaft"),
        ("3 x 608 bearing", BRG_P, "in the planets"),
        ("3 x pin spacer", SPACERS, "printed"),
        ("M8 washer", "axle_w1", ""),
        ("608 bearing", "brg_a", "hub, back"),
        ("hub spacer", "hub_spacer", "printed"),
        ("608 bearing", "brg_b", "hub, front"),
        ("hand wheel", "wheel", "printed, plate 3"),
        ("M8 washer", "axle_w2", ""),
        ("M8 nyloc", "axle_nut", "snug, not tight"),
        ("M6 nut", "m6_nut", "behind the post"),
        ("grip", "grip", "printed"),
        ("M6 penny washer", "m6_washer", "printed, plate 5"),
        ("M6 x 90 bolt", "m6_bolt", ""),
    ],
    "cartridge": [
        ("spider", "spider", "printed; carries the three pins, bolts to the wall"),
        ("M8 x 40 axle bolt", "axle_bolt", "the wheel's axle, fixed in the spider"),
        ("3 x M8 x 50 pin", PINB, "each planet turns on one"),
        ("6 x M8 washer", PINW, "two per pin, behind the spider"),
        ("ring gear, 91 teeth", "ring", "printed in one job with planets and sun"),
        ("3 x planet, 37 teeth", PLANETS, "idlers: they only pass the torque on"),
        ("3 x 608 bearing", BRG_P, "one pressed into each planet"),
        ("sun, 17 teeth", "sun", "D bore for the motor's 6.35 mm shaft"),
        ("3 x pin spacer", SPACERS, "printed; hold the planets off the wall"),
    ],
    "hub": [
        ("spider", "spider", "the axle is fixed in its centre"),
        ("M8 x 40 axle bolt", "axle_bolt", "in from the back of the spider"),
        ("M8 washer", "axle_w1", ""),
        ("608 bearing, back", "brg_a", "pressed into the hub from behind"),
        ("hub spacer", "hub_spacer", "printed, 5.9 mm; keeps the bearings apart"),
        ("608 bearing, front", "brg_b", ""),
        ("hand wheel", "wheel", "printed; the hub takes both bearings"),
        ("M8 washer", "axle_w2", ""),
        ("M8 nyloc", "axle_nut", "snug only; tight would load the bearings"),
        ("M6 nut", "m6_nut", "behind the post"),
        ("grip", "grip", "printed; spins on the post"),
        ("M6 penny washer", "m6_washer", "printed, plate 5"),
        ("M6 x 90 bolt", "m6_bolt", "through washer, grip and post, into the nut"),
    ],
    "electronics": [
        ("wire cover", "shell", "printed; lifts off the back of the frame"),
        ("rectifier card", "card", "stiff card; everything on it faces the motor"),
        ("8 x SB560 Schottky", "diodes", "two bridges, one per coil; every band toward PLUS"),
        ("1000 uF capacitor", "cap", "stripe to MINUS; smooths the bus"),
        ("module sled", "sled", "printed; holds the converter and its socket"),
        ("5 V converter", "pcb", "QC3.0 buck module, 6 to 32 V in"),
        ("USB-A socket", "socket", "on the converter"),
        ("USB meter", "tester", "plugs in through the cover's window"),
        ("phone lead", "phone_lead", ""),
        ("NEMA23 stepper", "motor", "its four leads go to the card"),
        ("frame", "base", ""),
        ("3 x M8 nyloc", REAR_N, "the planet pins' nuts, behind the wall"),
        ("4 x M5 x 12", M5, "motor screws"),
    ],
    "inside": [
        ("4 motor leads", "wire_bundle", "coil A to J1 and J2, coil B to J3 and J4"),
        ("rectifier card", "card", "seen from behind; diodes and capacitor face the motor"),
        ("PLUS wire", "wire_out_plus", "card's PLUS rail to the converter's IN+"),
        ("MINUS wire", "wire_out_minus", "card's MINUS rail to IN-"),
        ("module sled", "sled", "printed"),
        ("USB meter", "tester", ""),
        ("phone lead", "lead", ""),
        ("phone", "phone", ""),
        ("NEMA23 stepper", "motor", ""),
        ("frame", "base", ""),
    ],
    "plates": [
        ("frame", "frame", "plate 4: front face on the bed"),
        ("hand wheel", "wheel", "plate 3: back on the bed, post up"),
        ("gear set, print in place", "gearset", "plate 2: ring 91, three planets 37, sun 17, teeth on the bed"),
        ("wire cover shell", "shell", "cover file 2: open side up"),
        ("spider", "spider", "plate 1"),
        ("grip", "grip", "plate 1: stands on its disc"),
        ("hub spacer", "hub_spacer", "plate 1"),
        ("3 x pin spacer", "pin_spacers", "plate 1"),
        ("12 M8 + 1 M6 penny washer", "washers", "plate 5, 1.6 mm"),
    ],
}


def font(size, face=5):
    return ImageFont.truetype(FONT, max(6, int(round(size))), index=face)


def anchor(a, ref):
    if isinstance(ref, tuple):
        return list(ref)
    if isinstance(ref, list):
        return anchor(a, ref[0])
    if ref in a["points"]:
        return a["points"][ref]
    return a["parts"][ref]["c"]


def relax(desired, sizes, lo, hi):
    """1-D: keep the order of `desired`, separate neighbours by their sizes, stay inside [lo, hi], move as little as possible."""
    idx = sorted(range(len(desired)), key=lambda i: desired[i])
    p = [float(desired[i]) for i in idx]
    sz = [sizes[i] for i in idx]
    n = len(p)
    for _ in range(500):
        moved = False
        for k in range(n - 1):
            gap = (sz[k] + sz[k + 1]) / 2 - (p[k + 1] - p[k])
            if gap > 1e-6:
                p[k] -= gap / 2
                p[k + 1] += gap / 2
                moved = True
        if n and p[0] - sz[0] / 2 < lo:
            p[0] = lo + sz[0] / 2
            moved = True
        if n and p[-1] + sz[-1] / 2 > hi:
            p[-1] = hi - sz[-1] / 2
            moved = True
        if not moved:
            break
    out = [0.0] * n
    for k, i in enumerate(idx):
        out[i] = p[k]
    return out


def callouts(labels, kx0, ky0, kx1, ky1, W, H, s, gut, edge, tw, fw):
    """Labels round the edge: each on the side its part is nearest, in one column or row per side."""
    cx, cy, hw, hh = (kx0 + kx1) / 2, (ky0 + ky1) / 2, max(1.0, (kx1 - kx0) / 2), max(1.0, (ky1 - ky0) / 2)
    aspect = hw / hh
    w_tb, w_lr = (1.3, 0.75) if aspect > 1.25 else (0.75, 1.3) if aspect < 0.8 else (1.0, 1.0)
    room = dict(left=kx0 - edge, right=W - kx1 - edge, top=ky0 - edge, bottom=H - ky1 - edge)
    cap = dict(left=0.0, right=0.0, top=0.0, bottom=0.0)
    limit = dict(left=H - 2 * edge, right=H - 2 * edge, top=W - 2 * edge - tw - 60 * s, bottom=W - 2 * edge - fw - 60 * s)
    for L in labels:
        dx, dy = (L["ax"] - cx) / hw, (L["ay"] - cy) / hh
        L["score"] = dict(left=-dx * w_lr, right=dx * w_lr, top=-dy * w_tb, bottom=dy * w_tb)
        L["strength"] = max(L["score"].values())
    for L in sorted(labels, key=lambda L: -L["strength"]):    # the labels that clearly belong somewhere choose first
        prefs = sorted(L["score"], key=lambda k: -L["score"][k])
        for side in prefs:
            need = L["bw"] + gut + 24 * s if side in ("left", "right") else L["bh"] + gut
            size = L["bh"] + 18 * s if side in ("left", "right") else L["bw"] + 44 * s
            if room[side] >= need and cap[side] + size <= limit[side]:
                break
        else:
            side = max(room, key=lambda k: room[k] - (0 if k in ("left", "right") else 1e9) if L["bw"] > L["bh"] * 3 else room[k])
            size = L["bh"] + 18 * s if side in ("left", "right") else L["bw"] + 44 * s
        L["side"] = side
        cap[side] += size
    for side in ("left", "right", "top", "bottom"):
        group = [L for L in labels if L["side"] == side]
        if not group:
            continue
        # Order the labels as seen from a vantage point far out on their side (a leader is the line from that
        # point through the part, continued to the column), so leaders fan out instead of crossing.
        if side in ("left", "right"):
            X, V = (kx0 - gut, -0.35 * W) if side == "left" else (kx1 + gut, 1.35 * W)
            want = [cy + (L["ay"] - cy) * (V - X) / (V - L["ax"]) for L in group]
            pos = relax(want, [L["bh"] + 18 * s for L in group], edge + 110 * s, H - edge - 40 * s)
        else:
            Y, V = (ky0 - gut, -0.35 * H) if side == "top" else (ky1 + gut, 1.35 * H)
            want = [cx + (L["ax"] - cx) * (V - Y) / (V - L["ay"]) for L in group]
            lo = edge + (tw + 60 * s if side == "top" else 0.0)
            hi = W - edge - (fw + 60 * s if side == "bottom" else 0.0)
            pos = relax(want, [L["bw"] + 44 * s for L in group], lo, hi)
        for L, p in zip(group, pos):
            if side == "left":
                x1 = max(edge + L["bw"], min(kx0 - gut, L["ax"] - gut))
                L["tx"], L["ty"], L["align"] = x1 - L["bw"], p - L["bh"] / 2, "right"
                L["attach"] = (x1 + 10 * s, p - L["bh"] / 2 + 20 * s)
                L["path"] = [L["attach"], (x1 + 30 * s, L["attach"][1]), (L["ax"], L["ay"])]
            elif side == "right":
                x0 = min(W - edge - L["bw"], max(kx1 + gut, L["ax"] + gut))
                L["tx"], L["ty"], L["align"] = x0, p - L["bh"] / 2, "left"
                L["attach"] = (x0 - 10 * s, p - L["bh"] / 2 + 20 * s)
                L["path"] = [L["attach"], (x0 - 30 * s, L["attach"][1]), (L["ax"], L["ay"])]
            elif side == "top":
                y1 = max(edge + 100 * s + L["bh"], min(ky0 - gut, L["ay"] - gut))
                L["tx"], L["ty"], L["align"] = p - L["bw"] / 2, y1 - L["bh"], "centre"
                L["attach"] = (p, y1 + 6 * s)
                L["path"] = [L["attach"], (p, y1 + 26 * s), (L["ax"], L["ay"])]
            else:
                y0 = min(H - edge - L["bh"], max(ky1 + gut, L["ay"] + gut))
                L["tx"], L["ty"], L["align"] = p - L["bw"] / 2, y0, "centre"
                L["attach"] = (p, y0 - 6 * s)
                L["path"] = [L["attach"], (p, y0 - 26 * s), (L["ax"], L["ay"])]
            L["dot"] = True


def under_parts(labels, a, W, H, s, edge):
    """The flat lay: each label under its part; a crowded row alternates two tiers."""
    for L in labels:
        box = a["parts"][L["ref"]]["box"]
        L["px"], L["py"] = (box[0] + box[2]) / 2 * W, box[3] * H
    rows = []
    for L in sorted(labels, key=lambda L: L["py"]):
        if rows and abs(L["py"] - rows[-1][0]["py"]) < 0.09 * H:
            rows[-1].append(L)
        else:
            rows.append([L])
    for row in rows:
        row.sort(key=lambda L: L["px"])
        ybase = max(L["py"] for L in row) + 26 * s
        tiers = 1 if sum(L["bw"] + 40 * s for L in row) <= W - 2 * edge else 2
        for t in range(tiers):
            group = row[t::tiers]
            pos = relax([L["px"] for L in group], [L["bw"] + 40 * s for L in group], edge, W - edge)
            for L, p in zip(group, pos):
                L["tx"], L["ty"], L["align"] = p - L["bw"] / 2, ybase + t * 96 * s, "centre"
                L["path"] = [(L["px"], L["py"] + 6 * s), (p, L["ty"] - 8 * s)]
                L["dot"] = False


SCALE = float(next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--scale=")), 1.0))   # text size factor
OUT = os.path.join(ROOT, "exploded", "doc") if SCALE != 1.0 else OUT                              # a bigger-text set for print


def compose(name, number):
    a = json.load(open(os.path.join(RAW, f"{name}_anchors.json")))
    im = Image.open(os.path.join(RAW, f"{name}.png")).convert("RGB")
    W, H = im.size
    s = W / 3200.0 * SCALE
    f_main, f_sub, f_title, f_small = font(34 * s), font(25 * s, 7), font(46 * s, 2), font(23 * s, 7)
    draw = ImageDraw.Draw(im, "RGBA")
    edge, gut = 60 * s, 48 * s
    title, sub = TITLES[name]
    tw = draw.textlength(f"{number}   {title}", font=f_title)
    foot = f"Designed by Paing   ·   from the CAD files   ·   {datetime.date.today().isoformat()}"
    fw = draw.textlength(foot, font=f_small)

    labels = []
    for text, ref, small in LABELS[name]:
        try:
            u, v = anchor(a, ref)
        except KeyError:
            print(f"  {name}: no anchor for {ref!r} ({text}), skipped")
            continue
        mw = draw.textlength(text, font=f_main)
        sw = draw.textlength(small, font=f_sub) if small else 0.0
        dots = [anchor(a, r) for r in ref[1:]] if isinstance(ref, list) else []
        labels.append(dict(text=text, small=small, ref=ref, ax=u * W, ay=v * H, bw=max(mw, sw), mw=mw,
                           bh=40 * s + (30 * s if small else 0.0), dots=dots))

    if name in GRID:
        under_parts(labels, a, W, H, s, edge)
    else:
        boxes = [p["box"] for p in a["parts"].values()]
        kx0, ky0 = max(0.0, min(b[0] for b in boxes)) * W, max(0.0, min(b[1] for b in boxes)) * H
        kx1, ky1 = min(1.0, max(b[2] for b in boxes)) * W, min(1.0, max(b[3] for b in boxes)) * H
        callouts(labels, kx0, ky0, kx1, ky1, W, H, s, gut, edge, tw, fw)

    for L in labels:                                        # leaders first, with a dark halo, then dots, then text
        draw.line(L["path"], fill=(0, 0, 0, 170), width=max(1, int(6 * s)), joint="curve")
    for L in labels:
        draw.line(L["path"], fill=(196, 196, 196, 255), width=max(1, int(2.2 * s)), joint="curve")
    for L in labels:
        if not L["dot"]:
            continue
        for (x, y) in [(L["ax"], L["ay"])] + [(u * W, v * H) for u, v in L["dots"]]:
            r = 6.5 * s
            draw.ellipse((x - r - 1.6 * s, y - r - 1.6 * s, x + r + 1.6 * s, y + r + 1.6 * s), fill=(0, 0, 0, 200))
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(236, 236, 236, 255))
    texts = [((edge, edge - 8 * s), f"{number}   {title}", f_title, (240, 240, 240)), ((edge, edge + 50 * s), sub, f_sub, (150, 150, 150)),
             ((W - edge - fw, H - edge - 26 * s), foot, f_small, (120, 120, 120))]
    for L in labels:
        sw = draw.textlength(L["small"], font=f_sub) if L["small"] else 0.0
        if L["align"] == "right":
            x, sx = L["tx"] + L["bw"] - L["mw"], L["tx"] + L["bw"] - sw
        elif L["align"] == "centre":
            x, sx = L["tx"] + (L["bw"] - L["mw"]) / 2, L["tx"] + (L["bw"] - sw) / 2
        else:
            x, sx = L["tx"], L["tx"]
        texts.append(((x, L["ty"]), L["text"], f_main, (238, 238, 238)))
        if L["small"]:
            texts.append(((sx, L["ty"] + 40 * s), L["small"], f_sub, (156, 156, 156)))
    halo = Image.new("RGBA", im.size, (0, 0, 0, 0))     # a soft dark glow under every text: invisible on black, legible on the lit floor
    hd = ImageDraw.Draw(halo)
    for xy, text, f, _ in texts:
        hd.text(xy, text, font=f, fill=(0, 0, 0, 255), stroke_width=max(1, int(3 * s)), stroke_fill=(0, 0, 0, 255))
    halo = halo.filter(ImageFilter.GaussianBlur(5 * s))
    halo.putalpha(halo.split()[3].point(lambda a: int(a * 0.9)))
    im = Image.alpha_composite(im.convert("RGBA"), halo).convert("RGB")
    draw = ImageDraw.Draw(im, "RGBA")
    for xy, text, f, colour in texts:
        draw.text(xy, text, font=f, fill=colour)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{number:02d}_{name}.png")
    im.save(path)
    sides = ", ".join(f"{k} {sum(1 for L in labels if L.get('side') == k)}" for k in ("left", "right", "top", "bottom"))
    print(f"{os.path.basename(path)}: {len(labels)} labels; {sides if name not in GRID else 'under the parts'}")
    return path


def main():
    names = [n for n in sys.argv[1:] if n in ORDER] or [n for n in ORDER if os.path.exists(os.path.join(RAW, f"{n}_anchors.json"))]
    paths = [compose(n, ORDER.index(n) + 1) for n in names]
    if len(paths) > 1:
        ims = [Image.open(p).convert("RGB") for p in paths]
        pdf = os.path.join(OUT, "crank_charger_pictures.pdf")
        ims[0].save(pdf, save_all=True, append_images=ims[1:], resolution=300.0)
        print("wrote", pdf)


if __name__ == "__main__":
    main()
