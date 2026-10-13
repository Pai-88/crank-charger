"""Draws the electronics picture guide: wire_01.png .. wire_10.png and electronics.pdf.

    ../.venv/bin/python wiring_pictures.py            all pictures and the PDF
    ../.venv/bin/python wiring_pictures.py 3 6        only pictures 3 and 6 (no PDF)
    ../.venv/bin/python wiring_pictures.py template   only the full-size card template

Same look as the mechanical guide in ../assembly: white page, Avenir, black
outlines, one orange accent for what is added in that picture, "Step E1" top
left with one line of at most ten words, call-outs on thin leader lines.
Parts are drawn as they look, not as circuit symbols. The only other colour is
red, and only on the things that are red in real life and where polarity
depends on it: the red meter lead, the red supply lead, the red output wire.

Everything is drawn in final pixels (2000 x 1250) and rendered at twice that.
The ladder is drawn in millimetres from one table, so every picture shows the
same layout: four legs 12 mm apart, each leg two diodes end to end, every band
pointing at the plus rail.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, SS = 2000, 1250, 2
AVENIR = "/System/Library/Fonts/Avenir.ttc"
HEAVY, MEDIUM, ROMAN = 4, 8, 11
PX_STEP, PX_LINE, PX_CALL = 76, 46, 42

INK = (20, 20, 22)
WHITE = (255, 255, 255)
PAPER = (230, 230, 232)          # light grey parts
STEEL = (143, 148, 158)          # bought metal
SLATE = (102, 107, 117)          # the motor, diode bodies
LEAD = (206, 208, 214)           # tinned leads
CARD = (247, 244, 237)
TAPE = (247, 222, 128)
ORANGE = (247, 120, 26)
ORANGE_D = (199, 84, 10)
ORANGE_L = (252, 178, 110)
ARROW = (176, 62, 0)
RED = (200, 40, 34)
LCD = (214, 223, 208)
RULE = (205, 205, 208)
MINUS, OHM = chr(0x2212), chr(0x3A9)          # the real minus sign and the ohm sign, for labels in the pictures

_fonts = {}


def font(face, px):
    key = (face, int(round(px * SS)))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(AVENIR, key[1], index=face)
    return _fonts[key]


def bezier(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def spline(pts, n=14):
    """Catmull-Rom through the points."""
    if len(pts) < 3:
        return list(pts)
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(p) - 2):
        a, b, c, d = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * b[j]) + (-a[j] + c[j]) * t + (2 * a[j] - 5 * b[j] + 4 * c[j] - d[j]) * t * t
                                    + (-a[j] + 3 * b[j] - 3 * c[j] + d[j]) * t ** 3) for j in (0, 1)))
    out.append(pts[-1])
    return out


class Page:
    def __init__(self, n, title, size=(W, H)):
        if len(title.split()) > 10:
            sys.exit(f"E{n}: the title is longer than ten words")
        self.n, self.title = n, title
        self.w, self.h = size
        self.img = Image.new("RGB", (self.w * SS, self.h * SS), WHITE)
        self.d = ImageDraw.Draw(self.img)

    # ---- primitives, all in final pixels ----
    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def line(self, pts, w=3.0, fill=INK, caps=True):
        ww = max(1, int(round(w * SS)))
        self.d.line(self._p(pts), fill=fill, width=ww, joint="curve")
        if caps and w >= 3:
            r = ww / 2
            for x, y in (pts[0], pts[-1]):
                self.d.ellipse([x * SS - r, y * SS - r, x * SS + r, y * SS + r], fill=fill)

    def wire(self, pts, w, fill, edge=INK, ew=2.0):
        """A round wire: dark edge, lighter core."""
        self.line(pts, w + 2 * ew, edge)
        self.line(pts, w, fill)

    def rect(self, x0, y0, x1, y1, fill=None, edge=INK, ew=3.0, r=0):
        box = [x0 * SS, y0 * SS, x1 * SS, y1 * SS]
        if r:
            self.d.rounded_rectangle(box, radius=r * SS, fill=fill, outline=edge, width=int(round(ew * SS)) if edge else 0)
        else:
            self.d.rectangle(box, fill=fill, outline=edge, width=int(round(ew * SS)) if edge else 0)

    def oval(self, x0, y0, x1, y1, fill=None, edge=INK, ew=3.0):
        self.d.ellipse([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill, outline=edge, width=int(round(ew * SS)) if edge else 0)

    def circle(self, x, y, r, fill=None, edge=INK, ew=3.0):
        self.oval(x - r, y - r, x + r, y + r, fill, edge, ew)

    def poly(self, pts, fill=None, edge=INK, ew=3.0):
        self.d.polygon(self._p(pts), fill=fill)
        if edge:
            self.line(list(pts) + [pts[0]], ew, edge, caps=False)

    def text(self, x, y, s, px=PX_CALL, face=MEDIUM, fill=INK, anchor="la", halo=3.0, spacing=12):
        f = font(face, px)
        kw = dict(font=f, fill=fill, spacing=spacing * SS, stroke_width=int(halo * SS), stroke_fill=WHITE)
        if "\n" in s:
            self.d.multiline_text((x * SS, y * SS), s, anchor=anchor if anchor[1] == "a" else anchor[0] + "a",
                                  align={"l": "left", "m": "center", "r": "right"}[anchor[0]], **kw)
        else:
            self.d.text((x * SS, y * SS), s, anchor=anchor, **kw)

    def box_of(self, x, y, s, px, face, anchor="la", spacing=12):
        f = font(face, px)
        b = self.d.multiline_textbbox((x * SS, y * SS), s, font=f, anchor=anchor, spacing=spacing * SS,
                                      align={"l": "left", "m": "center", "r": "right"}[anchor[0]])
        return [v / SS for v in b]

    def call(self, s, x, y, target=None, px=PX_CALL, face=MEDIUM, anchor="la", fill=INK, start=None):
        """A call-out: text at (x, y), a thin leader to the target, a dot on the target."""
        b = self.box_of(x, y, s, px, face, anchor)
        targets = [] if target is None else (target if isinstance(target, list) else [target])
        for tx, ty in targets:
            my = (b[1] + b[3]) / 2
            cands = [(b[0] - 8, my), (b[2] + 8, my), ((b[0] + b[2]) / 2, b[1] - 4), ((b[0] + b[2]) / 2, b[3] + 6),
                     (b[0] + 20, b[3] + 6), (b[2] - 20, b[3] + 6), (b[0] + 20, b[1] - 4), (b[2] - 20, b[1] - 4)]
            sx, sy = start or min(cands, key=lambda q: (q[0] - tx) ** 2 + (q[1] - ty) ** 2)
            self.line([(sx, sy), (tx, ty)], 5.0, WHITE, caps=False)
            self.line([(sx, sy), (tx, ty)], 1.7, INK, caps=False)
            self.circle(tx, ty, 8.5, WHITE, None)
            self.circle(tx, ty, 6.0, INK, None)
        self.text(x, y, s, px, face, fill, anchor)

    def arrow(self, pts, fill=ARROW, w=4.0, head=22):
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        a = math.atan2(y1 - y0, x1 - x0)
        bx, by = x1 - head * math.cos(a), y1 - head * math.sin(a)
        self.line(list(pts[:-1]) + [(bx, by)], w, fill)
        hw = head * 0.42
        self.d.polygon(self._p([(x1, y1), (bx - hw * math.sin(a), by + hw * math.cos(a)), (bx + hw * math.sin(a), by - hw * math.cos(a))]), fill=fill)

    def inset(self, x0, y0, x1, y1):
        self.rect(x0, y0, x1, y1, WHITE, (60, 60, 64), 2.0, r=14)

    def divider(self, x, y0=180, y1=H - 30):
        self.line([(x, y0), (x, y1)], 1.0, RULE, caps=False)

    def finish(self, header=True):
        if not header:
            return self.img.resize((self.w, self.h), Image.LANCZOS)
        d, base = self.d, 104 * SS
        label = f"Step E{self.n}"
        f_step, f_line = font(HEAVY, PX_STEP), font(MEDIUM, PX_LINE)
        d.text((40 * SS, base), label, font=f_step, fill=INK, anchor="ls")
        d.text((40 * SS + d.textlength(label, font=f_step) + 36 * SS, base), self.title, font=f_line, fill=INK, anchor="ls")
        return self.img.resize((W, H), Image.LANCZOS)


# --------------------------------------------------------------------------
# parts, drawn as they look
# --------------------------------------------------------------------------

SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
       "8": "abcdefg", "9": "abfgcd", "-": "g", " ": ""}


def seven(pg, x, y, w, h, ch, fill=INK):
    t = w * 0.19
    segs = dict(a=(x + t, y, x + w - t, y + t), d=(x + t, y + h - t, x + w - t, y + h), g=(x + t, y + h / 2 - t / 2, x + w - t, y + h / 2 + t / 2),
                f=(x, y + t * 0.6, x + t, y + h / 2 - t * 0.3), b=(x + w - t, y + t * 0.6, x + w, y + h / 2 - t * 0.3),
                e=(x, y + h / 2 + t * 0.3, x + t, y + h - t * 0.6), c=(x + w - t, y + h / 2 + t * 0.3, x + w, y + h - t * 0.6))
    for k in SEG[ch]:
        a, b, c, d = segs[k]
        pg.rect(a, b, c, d, fill, None, 0, r=t * 0.3)


def lcd(pg, x0, y0, x1, y1, reading, unit=None):
    """A 3 1/2 digit display. reading is a string such as '01.2', '8.4', '-8.4' or 'OL' (the lone 1)."""
    pg.rect(x0, y0, x1, y1, LCD, INK, 2.5, r=6)
    h = (y1 - y0) * 0.62
    w = h * 0.52
    gap = w * 0.42
    top = y0 + (y1 - y0 - h) / 2
    right = x1 - (x1 - x0) * (0.20 if unit else 0.10)
    if unit:
        pg.text(x1 - (x1 - x0) * 0.04, y1 - (y1 - y0) * 0.16, unit, px=(y1 - y0) * 0.34, face=HEAVY, anchor="rs", halo=0)
    if reading == "OL":
        seven(pg, right - 4 * w - 3 * gap, top, w, h, "1")
        return
    neg = reading.startswith("-")
    chars = reading.lstrip("-")
    x = right
    for ch in reversed(chars):
        if ch == ".":
            pg.rect(x + gap * 0.22, top + h - gap * 0.56, x + gap * 0.78, top + h, INK, None, 0)
            continue
        seven(pg, x - w, top, w, h, ch)
        x -= w + gap
    if neg:
        pg.rect(x - w * 0.8, top + h / 2 - w * 0.1, x - w * 0.1, top + h / 2 + w * 0.1, INK, None, 0)


DIAL = {"OFF": 0, "V~500": 18, "V~200": 36, "A2000u": 54, "A20m": 72, "A200m": 90, "A10": 108, "OUT": 126, "DIODE": 144,
        "R200": 162, "R2000": 180, "R20K": 198, "R200K": 216, "R20M": 234, "R200M": 252, "V200m": 270, "V2000m": 288,
        "V20": 306, "V200": 324, "V500": 342}


def meter(pg, x, y, m, reading, dial):
    """The AstroAI 2000-count meter. Returns the two socket points (red = middle, black = COM on the right)."""
    w, h = 300 * m, 500 * m
    pg.rect(x, y, x + w, y + h, PAPER, INK, 3.5, r=38 * m)
    pg.rect(x + 14 * m, y + 14 * m, x + w - 14 * m, y + h - 14 * m, None, STEEL, 1.5, r=28 * m)
    lcd(pg, x + 36 * m, y + 34 * m, x + w - 36 * m, y + 132 * m, reading)
    cx, cy, r = x + w / 2, y + 268 * m, 74 * m
    for name, deg in DIAL.items():
        a = math.radians(deg - 90)
        pg.circle(cx + (r + 16 * m) * math.cos(a), cy + (r + 16 * m) * math.sin(a), 3.2 * m, INK, None)
    for label, deg in (("V=", 306), ("V~", 27), ("A", 81), (OHM, 207)):
        a = math.radians(deg - 90)
        pg.text(cx + (r + 44 * m) * math.cos(a), cy + (r + 44 * m) * math.sin(a), label, px=27 * m, face=HEAVY, anchor="mm", halo=0)
    a = math.radians(144 - 90)                     # the diode / beeper position gets its own little mark
    dx, dy = cx + (r + 42 * m) * math.cos(a), cy + (r + 42 * m) * math.sin(a)
    pg.poly([(dx - 10 * m, dy - 9 * m), (dx - 10 * m, dy + 9 * m), (dx + 6 * m, dy)], INK, None)
    pg.line([(dx + 7 * m, dy - 10 * m), (dx + 7 * m, dy + 10 * m)], 3 * m, INK, caps=False)
    pg.circle(cx, cy, r, WHITE, INK, 3)
    a = math.radians(DIAL[dial] - 90)
    ux, uy = math.cos(a), math.sin(a)
    bar = [(cx + ux * r * 0.96 - uy * 15 * m, cy + uy * r * 0.96 + ux * 15 * m), (cx + ux * r * 0.96 + uy * 15 * m, cy + uy * r * 0.96 - ux * 15 * m),
           (cx - ux * r * 0.96 + uy * 15 * m, cy - uy * r * 0.96 - ux * 15 * m), (cx - ux * r * 0.96 - uy * 15 * m, cy - uy * r * 0.96 + ux * 15 * m)]
    pg.poly(bar, SLATE, INK, 2.5)
    pg.line([(cx + ux * r * 0.45, cy + uy * r * 0.45), (cx + ux * r * 0.92, cy + uy * r * 0.92)], 6 * m, WHITE)
    pg.circle(cx + (r + 16 * m) * ux, cy + (r + 16 * m) * uy, 8 * m, ORANGE, INK, 2)
    jy = y + 440 * m
    for jx, col in ((x + 70 * m, PAPER), (x + 150 * m, RED), (x + 230 * m, INK)):
        pg.circle(jx, jy, 19 * m, WHITE, INK, 2.5)
        pg.circle(jx, jy, 10 * m, col, INK, 1.5)
    return dict(red=(x + 150 * m, jy), black=(x + 230 * m, jy), dial=(cx + (r + 16 * m) * ux, cy + (r + 16 * m) * uy),
                lcd=(x + w / 2, y + 83 * m), box=(x, y, x + w, y + h))


def probe(pg, tip, deg, colour, size=1.0):
    """A meter probe touching `tip`, its handle pointing away at `deg` (0 = right, 90 = down). Returns the cable end."""
    a = math.radians(deg)
    ux, uy = math.cos(a), math.sin(a)
    t1 = (tip[0] + ux * 46 * size, tip[1] + uy * 46 * size)
    t2 = (tip[0] + ux * 190 * size, tip[1] + uy * 190 * size)
    pg.wire([tip, t1], 4 * size, LEAD, INK, 1.5)
    pg.wire([t1, t2], 17 * size, colour, INK, 2)
    g = (tip[0] + ux * 62 * size, tip[1] + uy * 62 * size)
    pg.line([(g[0] - uy * 15 * size, g[1] + ux * 15 * size), (g[0] + uy * 15 * size, g[1] - ux * 15 * size)], 7 * size, INK)
    return t2


def cable(pg, a, b, colour, w=7.0, sag=None, via=None):
    """A flexible lead from a to b."""
    if via:
        pts = spline([a] + list(via) + [b])
    else:
        sag = sag if sag is not None else 0.25 * abs(b[0] - a[0]) + 60
        pts = bezier(a, (a[0], a[1] + sag), (b[0], b[1] + sag), b)
    pg.wire(pts, w, colour, INK, 1.6)


def stub(pg, a, deg, colour, length=110, w=7.0, bend=0.25):
    """A short piece of cable that leaves the picture: it ends in a break mark. The other end is on the instrument."""
    r = math.radians(deg)
    ux, uy = math.cos(r), math.sin(r)
    b = (a[0] + ux * length, a[1] + uy * length)
    c1 = (a[0] + ux * length * 0.35 - uy * length * bend, a[1] + uy * length * 0.35 + ux * length * bend)
    c2 = (a[0] + ux * length * 0.70 - uy * length * bend, a[1] + uy * length * 0.70 + ux * length * bend)
    pts = bezier(a, c1, c2, b, 24)
    pg.wire(pts, w, colour, INK, 1.6)
    (x0, y0), (x1, y1) = pts[-3], pts[-1]
    t = math.atan2(y1 - y0, x1 - x0)
    for k in (12, 24):
        cx, cy = x1 + math.cos(t) * k, y1 + math.sin(t) * k
        pg.line([(cx - math.sin(t) * 13 - math.cos(t) * 5, cy + math.cos(t) * 13 - math.sin(t) * 5),
                 (cx + math.sin(t) * 13 + math.cos(t) * 5, cy - math.cos(t) * 13 + math.sin(t) * 5)], 3.0, INK)
    return b


def croc(pg, tip, deg, colour, size=1.0):
    """A crocodile clip biting at `tip`, body pointing away at `deg`. Returns the cable end."""
    a = math.radians(deg)
    ux, uy = math.cos(a), math.sin(a)

    def at(along, across):
        return (tip[0] + ux * along * size - uy * across * size, tip[1] + uy * along * size + ux * across * size)
    pg.poly([at(-6, 0), at(34, -13), at(96, -15), at(96, 15), at(34, 13)], colour, INK, 2.2)
    pg.line([at(-4, 0), at(40, 0)], 2.0, WHITE if colour == INK else INK, caps=False)
    pg.poly([at(52, -15), at(84, -24), at(96, -15)], colour, INK, 2.2)
    return at(96, 0)


def supply(pg, x, y, m, volts, amps):
    """The bench supply front. Returns the + and - terminal points."""
    w, h = 400 * m, 300 * m
    pg.rect(x, y, x + w, y + h, PAPER, INK, 3.5, r=14 * m)
    lcd(pg, x + 24 * m, y + 24 * m, x + 196 * m, y + 104 * m, volts, "V")
    lcd(pg, x + 204 * m, y + 24 * m, x + 376 * m, y + 104 * m, amps, "A")
    for kx in (x + 78 * m, x + 188 * m):
        pg.circle(kx, y + 170 * m, 34 * m, WHITE, INK, 3)
        pg.line([(kx, y + 170 * m), (kx + 18 * m, y + 146 * m)], 5 * m, INK)
    pg.rect(x + 264 * m, y + 142 * m, x + 372 * m, y + 196 * m, WHITE, INK, 2.5, r=8 * m)
    pg.text(x + 318 * m, y + 169 * m, "OUTPUT", px=22 * m, face=HEAVY, anchor="mm", halo=0)
    ty = y + 256 * m
    neg, pos = (x + 250 * m, ty), (x + 340 * m, ty)
    for (jx, jy), col in ((neg, INK), (pos, RED)):
        pg.circle(jx, jy, 22 * m, col, INK, 2.5)
        pg.circle(jx, jy, 8 * m, WHITE, INK, 1.5)
    pg.text(neg[0] - 34 * m, ty, MINUS, px=40 * m, face=HEAVY, anchor="rm", halo=0)
    pg.text(pos[0] - 30 * m, ty, "+", px=40 * m, face=HEAVY, anchor="rm", halo=0, fill=RED)
    return dict(pos=pos, neg=neg, out=(x + 318 * m, y + 169 * m), volts=(x + 110 * m, y + 64 * m), amps=(x + 290 * m, y + 64 * m),
                knob=(x + 188 * m, y + 170 * m))


def diode(pg, cx, y0, y1, dia, accent=False, band_top=True):
    """A fat axial diode standing on end: a cylinder with one pale ring. The ring is the band."""
    body = ORANGE if accent else SLATE
    r = dia * 0.22
    pg.rect(cx - dia / 2, y0, cx + dia / 2, y1, body, INK, 2.5, r=r)
    pg.rect(cx - dia * 0.30, y0 + r, cx - dia * 0.14, y1 - r, ORANGE_L if accent else STEEL, None, 0)       # the shine on a cylinder
    L = y1 - y0
    b0, b1 = (y0 + 0.11 * L, y0 + 0.36 * L) if band_top else (y1 - 0.36 * L, y1 - 0.11 * L)
    pg.rect(cx - dia / 2, b0, cx + dia / 2, b1, WHITE, INK, 2.5)
    return (cx, (b0 + b1) / 2)


def blob(pg, cx, cy, rx, ry, accent=False):
    """A solder joint."""
    pg.oval(cx - rx, cy - ry, cx + rx, cy + ry, ORANGE_D if accent else STEEL, INK, 2.2)
    pg.oval(cx - rx * 0.45, cy - ry * 0.55, cx + rx * 0.1, cy - ry * 0.1, ORANGE_L if accent else WHITE, None, 0)


def resistor(pg, cx, y0, y1, dia, accent=False):
    pg.rect(cx - dia / 2, y0, cx + dia / 2, y1, ORANGE_L if accent else PAPER, INK, 2.2, r=dia * 0.3)
    L = y1 - y0
    for f in (0.22, 0.40, 0.58, 0.80):
        pg.line([(cx - dia / 2 + 2, y0 + f * L), (cx + dia / 2 - 2, y0 + f * L)], max(2.0, L * 0.06), ORANGE_D if accent else SLATE, caps=False)


class Ladder:
    """The rectifier on its card, in millimetres. (ox, oy) is where leg 1 meets the plus rail; s is pixels per mm."""
    COL = (0.0, 12.0, 24.0, 36.0)
    OFF = 1.6                                      # the lower diode sits one lead-width to the right of the upper one

    def __init__(self, pg, ox, oy, s):
        self.pg, self.ox, self.oy, self.s = pg, ox, oy, s

    def xy(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def pts(self, mm):
        return [self.xy(x, y) for x, y in mm]

    def card(self, labels=True, x0=-18, y0=-15, x1=93, y1=75, lx=None, minus_x=None):
        pg, s = self.pg, self.s
        a, b = self.xy(x0, y0), self.xy(x1, y1)
        pg.rect(a[0], a[1], b[0], b[1], CARD, INK, 2.5, r=10)
        if labels:
            px = max(32, 4.4 * s)
            lx = x0 + 3 if lx is None else lx
            pg.text(*self.xy(lx, -9.3), "+  PLUS", px=px, face=HEAVY, anchor="lm", halo=0)
            pg.text(*self.xy(lx if minus_x is None else minus_x, 69.6), MINUS + "  MINUS", px=px, face=HEAVY, anchor="lm", halo=0)
        return (a[0], a[1], b[0], b[1])

    def jlabels(self, which=(1, 2, 3, 4), px=None):
        for k in which:
            x, y = self.xy(self.COL[k - 1] - 2.3, 30)
            self.pg.text(x, y, f"J{k}", px=px or max(30, 3.6 * self.s), face=HEAVY, anchor="rm", halo=2)

    # the two rails are the bent outer leads lying against each other
    def _top(self, k):
        return 0.0 if k % 2 == 0 else -1.5

    def _bot(self, k):
        return 60.0 if k % 2 == 0 else 61.5

    def legs(self, have, new=(), tape=True):
        pg, s = self.pg, self.s
        lw = max(4.0, 1.3 * s)
        for k in range(4):
            x = self.COL[k]
            for name, path in ((f"D{2 * k + 1}", [(x, 6.5), (x, self._top(k)), (x + 19, self._top(k))]),
                               (f"D{2 * k + 1}", [(x, 14.5), (x, 40)]),
                               (f"D{2 * k + 2}", [(x + self.OFF, 45.5), (x + self.OFF, 20)]),
                               (f"D{2 * k + 2}", [(x + self.OFF, 53.5), (x + self.OFF, self._bot(k)), (x + self.OFF + 19, self._bot(k))])):
                if name in have:
                    pg.wire(self.pts(path), lw, ORANGE_L if name in new else LEAD, INK, 1.8)
        if tape:
            for names, (y0, y1) in (((1, 3, 5, 7), (10.4, 14.0)), ((2, 4, 6, 8), (49.4, 53.0))):
                ks = [i for i, n in enumerate(names) if f"D{n}" in have]
                if ks:
                    a, b = self.xy(self.COL[ks[0]] - 6, y0), self.xy(self.COL[ks[-1]] + 8, y1)
                    pg.rect(a[0], a[1], b[0], b[1], TAPE, STEEL, 1.5)
        for k in range(4):
            x = self.COL[k]
            for name, cx, (y0, y1) in ((f"D{2 * k + 1}", x, (6, 15)), (f"D{2 * k + 2}", x + self.OFF, (45, 54))):
                if name in have:
                    (px_, py0), (_, py1) = self.xy(cx, y0), self.xy(cx, y1)
                    diode(pg, px_, py0, py1, 5.3 * s, name in new)
        if tape:                                    # the tape lies over the bodies, under the band
            for names, (y0, y1) in (((1, 3, 5, 7), (10.4, 14.0)), ((2, 4, 6, 8), (49.4, 53.0))):
                for i, n in enumerate(names):
                    if f"D{n}" in have:
                        cx = self.COL[i] + (self.OFF if n % 2 == 0 else 0)
                        a, b = self.xy(cx - 2.65, y0), self.xy(cx + 2.65, y1)
                        pg.rect(a[0] + 1.5, a[1], b[0] - 1.5, b[1], TAPE, None, 0)
                        pg.line([(a[0] + 1.5, a[1]), (b[0] - 1.5, a[1])], 1.5, STEEL, caps=False)
                        pg.line([(a[0] + 1.5, b[1]), (b[0] - 1.5, b[1])], 1.5, STEEL, caps=False)

    def joints(self, have, new=()):
        s = self.s
        for k in range(4):
            if f"J{k + 1}" in have:
                x, y = self.xy(self.COL[k] + self.OFF / 2, 28)
                blob(self.pg, x, y, 2.3 * s, 4.6 * s, f"J{k + 1}" in new)
        for k in range(3):
            for name, y in ((f"P{k + 1}", -0.75), (f"M{k + 1}", 60.75)):
                if name in have:
                    x, yy = self.xy(self.COL[k + 1] + (3.6 if name[0] == "P" else 3.6 + self.OFF), y)
                    blob(self.pg, x, yy, 3.6 * s, 2.2 * s, name in new)

    def light(self, accent=False, lit=False):
        """Two 1 k resistors and the LED in one string down the left side: resistor end on plus, LED short leg on minus."""
        pg, s = self.pg, self.s
        lw = max(2.4, 0.6 * s)
        col = ORANGE if accent else STEEL
        x = -8.0
        pg.wire(self.pts([(7.5, 1.4), (x + 2, 1.4), (x, 3), (x, 45.2)]), lw, col, INK, 1.3)
        pg.wire(self.pts([(x, 48.8), (x, 58.6), (x + 2, 60 - 1.4), (7.5, 60 - 1.4)]), lw, col, INK, 1.3)
        for y0 in (6.5, 23.5):
            (cx, a), (_, b) = self.xy(x, y0), self.xy(x, y0 + 6.5)
            resistor(pg, cx, a, b, 2.5 * s, accent)
        for y in (18.2, 35.8):
            bx, by = self.xy(x, y)
            blob(pg, bx, by, 1.5 * s, 1.7 * s, accent)
        lx, ly = self.xy(x - 5.2, 47)
        if lit:
            for deg in range(100, 261, 32):
                a = math.radians(deg)
                pg.line([(lx + 3.9 * s * math.cos(a) - 1.2 * s, ly + 3.9 * s * math.sin(a)), (lx + 6.4 * s * math.cos(a) - 1.2 * s, ly + 6.4 * s * math.sin(a))], 4, ORANGE)
        a, b = self.xy(x - 5.4, 44.4), self.xy(x - 0.6, 49.6)
        pg.rect(a[0], a[1], b[0], b[1], ORANGE if (accent or lit) else PAPER, INK, 2.2, r=2)
        pg.oval(lx - 3.6 * s, ly - 2.6 * s, lx + 1.6 * s, ly + 2.6 * s, ORANGE if (accent or lit) else PAPER, INK, 2.2)
        a, b = self.xy(x - 1.2, 43.8), self.xy(x - 0.2, 50.2)
        pg.rect(a[0], a[1], b[0], b[1], ORANGE_D if (accent or lit) else STEEL, INK, 1.8)
        for name, y in (("P", 1.0), ("M", 59.2)):
            bx, by = self.xy(5.6, y)
            blob(pg, bx, by, 2.6 * s, 1.7 * s, accent)
        return dict(led=self.xy(x - 3.4, 47), r1=self.xy(x, 9.7), r2=self.xy(x, 26.7), top=self.xy(5.6, 1.0), bottom=self.xy(5.6, 59.2))

    def cap(self, accent=False, link=True, link_accent=None):
        """C1 lying on its side at the right: long leg along the plus tab, stripe side down, a link wire to the minus tab."""
        pg, s = self.pg, self.s
        col = ORANGE if accent else SLATE
        lw = max(2.4, 0.7 * s)
        la = accent if link_accent is None else link_accent
        if link:
            pg.wire(self.pts(bezier((60.5, 13), (60.5, 40), (62, 61.5), (50, 60.2), 30)), max(5.0, 2.3 * s), ORANGE if la else INK, INK, 1.5)
            bx, by = self.xy(51, 60.2)
            blob(pg, bx, by, 3.4 * s, 2.0 * s, la)
        pg.wire(self.pts([(64, 0.2), (46.5, 0.2)]), lw, ORANGE_L if accent else LEAD, INK, 1.3)
        pg.wire(self.pts([(64, 5.4), (61.5, 5.4), (60.5, 6.6), (60.5, 14)]), lw, ORANGE_L if accent else LEAD, INK, 1.3)
        a, b = self.xy(63.5, -3.7), self.xy(89, 9.3)
        pg.rect(a[0], a[1], b[0], b[1], col, INK, 2.8, r=1.4 * s)
        st0, st1 = self.xy(66.5, 5.2), self.xy(88, 9.3)
        pg.rect(st0[0], st0[1], st1[0], st1[1] - 2.8, WHITE, INK, 2.0)
        for i in range(4):
            mx, my = self.xy(69.5 + i * 5.2, 7.0)
            pg.line([(mx - 1.1 * s, my), (mx + 1.1 * s, my)], max(3.0, 0.5 * s), INK, caps=False)
        pg.line([self.xy(66.5, -3.7), self.xy(66.5, 9.3)], 2.2, INK, caps=False)
        pg.rect(self.xy(63.5, -3.7)[0], self.xy(0, -1.4)[1], self.xy(64.6, 0)[0], self.xy(0, 7.0)[1], INK, None, 0)
        bx, by = self.xy(50.5, -0.6)
        blob(pg, bx, by, 3.6 * s, 2.3 * s, accent)
        if link:
            bx, by = self.xy(60.5, 11.5)
            blob(pg, bx, by, 1.9 * s, 2.6 * s, la)
        return dict(can=self.xy(78, 0.5), stripe=self.xy(80, 7.2), long=self.xy(57, 0.2), short=self.xy(60.5, 8.2), link=self.xy(61.3, 38),
                    plus=self.xy(50.5, -0.6), minus=self.xy(51, 60.2))

    def out_wires(self, red_to, black_to, accent=False, red_via=None, black_via=None):
        """The two output wires: three jumper wires twisted together each. Red from the plus tab, black from the minus tab."""
        pg, s = self.pg, self.s
        w = max(5.0, 2.3 * s)
        a = self.xy(54.5, -1.5)
        b = self.xy(55.5, 61.5)
        pg.wire(spline([a, self.xy(60, -9), self.xy(84, -11.5)] + list(red_via or []) + [red_to]), w, RED, INK, 1.5)
        pg.wire(spline([b, self.xy(66, 62.6), self.xy(84, 62.2)] + list(black_via or []) + [black_to]), w, INK, INK, 1.0)
        for (x, y) in (self.xy(54.3, -1.6), self.xy(55.3, 61.6)):
            blob(pg, x, y, 2.4 * s, 2.0 * s, accent)
        return dict(red=self.xy(72, -11.2), black=self.xy(76, 62.3), plus=a, minus=b)

    def motor_wires(self, ends, accent=False):
        """Four motor wires coming up from below, each wrapped round its J joint."""
        pg, s = self.pg, self.s
        for k, end in enumerate(ends):
            x = self.COL[k] - 3.6
            path = [end, self.xy(x, 72), self.xy(x, 46), self.xy(x + 1.2, 41.5), self.xy(x + 3.0, 38.6)]
            pg.wire(spline(path), max(4.5, 1.7 * s), ORANGE if accent else STEEL, INK, 1.5)
            bx, by = self.xy(self.COL[k] + self.OFF / 2, 36.6)
            blob(pg, bx, by, 2.5 * s, 2.3 * s, accent)

    def at(self, name):
        k = int(name[1]) - 1 if name[1:].isdigit() else 0
        table = {"J": (self.COL[k] + self.OFF / 2, 22.3), "j": (self.COL[k] + self.OFF / 2, 34.5),
                 "B": (self.COL[k % 4], 8.4)}
        if name in ("plus", "tab+"):
            return self.xy(46.8 if name == "tab+" else 21.5, -1.5 if name == "tab+" else -1.5)
        if name in ("minus", "tab-"):
            return self.xy(48.5 if name == "tab-" else 22.8, 61.5)
        if name[0] == "D":                                   # band of diode n
            n = int(name[1:])
            kk = (n - 1) // 2
            return self.xy(self.COL[kk] + (self.OFF if n % 2 == 0 else 0), 8.2 if n % 2 else 47.2)
        return self.xy(*table[name[0]])


ALL_D = {f"D{i}" for i in range(1, 9)}
ALL_J = {"J1", "J2", "J3", "J4", "P1", "P2", "P3", "M1", "M2", "M3"}


def motor(pg, x, y, m, accent_flags=False, flags=True):
    """The NEMA23 from the side, shaft to the left, four leads out of the back. Returns the four lead ends."""
    pg.rect(x - 46 * m, y + 58 * m, x + 4 * m, y + 82 * m, LEAD, INK, 2.5, r=3)                # shaft
    pg.rect(x, y + 22 * m, x + 16 * m, y + 118 * m, STEEL, INK, 2.5, r=3)                        # the round boss
    pg.rect(x + 14 * m, y, x + 54 * m, y + 140 * m, SLATE, INK, 3, r=6 * m)                     # front bell
    pg.rect(x + 54 * m, y + 4 * m, x + 150 * m, y + 136 * m, (70, 74, 82), INK, 3)             # the laminations
    for i in range(1, 8):
        pg.line([(x + 54 * m + i * 12 * m, y + 6 * m), (x + 54 * m + i * 12 * m, y + 134 * m)], 1.3, SLATE, caps=False)
    pg.rect(x + 150 * m, y, x + 190 * m, y + 140 * m, SLATE, INK, 3, r=6 * m)                   # back bell
    return (x + 190 * m, y + 70 * m)


def flag(pg, x, y, letter, accent=True, size=1.0):
    pg.rect(x - 24 * size, y - 20 * size, x + 24 * size, y + 20 * size, ORANGE if accent else TAPE, INK, 2.2, r=3)
    pg.text(x, y, letter, px=32 * size, face=HEAVY, anchor="mm", halo=0, fill=WHITE if accent else INK)


def module(pg, x, y, m, accent=False):
    """The 5 V USB module: a small board, IN+ and IN- at one end, a USB-A socket at the other."""
    w, h = 250 * m, 130 * m
    pg.rect(x, y, x + w, y + h, ORANGE_L if accent else PAPER, INK, 3, r=6)
    pg.rect(x + 78 * m, y + 26 * m, x + 150 * m, y + 104 * m, SLATE, INK, 2.5, r=8 * m)         # the coil
    pg.circle(x + 114 * m, y + 65 * m, 18 * m, STEEL, INK, 2)
    pads = dict(pos=(x + 26 * m, y + 34 * m), neg=(x + 26 * m, y + 96 * m))
    for (px_, py_) in pads.values():
        pg.rect(px_ - 15 * m, py_ - 15 * m, px_ + 15 * m, py_ + 15 * m, LEAD, INK, 2.2, r=3)
    pg.rect(x + w - 72 * m, y + 22 * m, x + w + 44 * m, y + 108 * m, LEAD, INK, 3, r=4)        # USB-A shell
    pg.rect(x + w - 30 * m, y + 34 * m, x + w + 44 * m, y + 96 * m, WHITE, INK, 2)
    pg.rect(x + w - 30 * m, y + 66 * m, x + w + 30 * m, y + 86 * m, SLATE, INK, 1.5)
    pads.update(usb=(x + w + 44 * m, y + 65 * m), body=(x + w / 2, y + h), top=(x + 114 * m, y))
    return pads


def usb_tester(pg, x, y, m, volts="5.10", amps="1.96"):
    """The USB meter: plug on the left, socket on the right, volts and amps on its face."""
    pg.rect(x - 52 * m, y + 28 * m, x + 6 * m, y + 92 * m, LEAD, INK, 3, r=3)                   # its plug
    pg.rect(x, y, x + 250 * m, y + 120 * m, PAPER, INK, 3, r=12 * m)
    pg.rect(x + 22 * m, y + 16 * m, x + 204 * m, y + 104 * m, INK, INK, 2, r=6)
    pg.text(x + 113 * m, y + 40 * m, f"{volts} V", px=34 * m, face=HEAVY, anchor="mm", halo=0, fill=WHITE)
    pg.text(x + 113 * m, y + 80 * m, f"{amps} A", px=34 * m, face=HEAVY, anchor="mm", halo=0, fill=WHITE)
    pg.rect(x + 214 * m, y + 26 * m, x + 250 * m, y + 94 * m, WHITE, INK, 2)
    return dict(plug=(x - 52 * m, y + 60 * m), socket=(x + 250 * m, y + 60 * m), face=(x + 113 * m, y + 16 * m))


def phone(pg, x, y, m, charging=True):
    w, h = 190 * m, 380 * m
    pg.rect(x, y, x + w, y + h, SLATE, INK, 3.5, r=28 * m)
    pg.rect(x + 12 * m, y + 14 * m, x + w - 12 * m, y + h - 14 * m, WHITE, INK, 2, r=18 * m)
    bx, by = x + w / 2, y + h * 0.42
    pg.rect(bx - 48 * m, by - 26 * m, bx + 48 * m, by + 26 * m, WHITE, INK, 3.5, r=8 * m)
    pg.rect(bx + 48 * m, by - 10 * m, bx + 57 * m, by + 10 * m, INK, None, 0)
    pg.rect(bx - 40 * m, by - 18 * m, bx - 4 * m, by + 18 * m, ORANGE if charging else STEEL, None, 0, r=3)
    if charging:
        pg.poly([(bx + 8 * m, by - 46 * m), (bx - 16 * m, by + 6 * m), (bx + 2 * m, by + 6 * m), (bx - 8 * m, by + 48 * m),
                 (bx + 20 * m, by - 8 * m), (bx + 2 * m, by - 8 * m)], ORANGE, INK, 2.2)
    return dict(port=(x + w / 2, y + h), icon=(bx + 22 * m, by - 20 * m))


def crank(pg, cx, cy, r, turns=True):
    """The big wheel with its grip, and an arrow for the direction of cranking."""
    pg.circle(cx, cy, r, PAPER, INK, 3.5)
    pg.circle(cx, cy, r * 0.84, WHITE, INK, 2.5)
    for k in range(6):
        a = math.radians(60 * k + 15)
        pg.wire([(cx + r * 0.16 * math.cos(a), cy + r * 0.16 * math.sin(a)), (cx + r * 0.84 * math.cos(a), cy + r * 0.84 * math.sin(a))], r * 0.09, PAPER, INK, 1.8)
    pg.circle(cx, cy, r * 0.18, STEEL, INK, 2.5)
    a = math.radians(-38)
    gx, gy = cx + r * 0.66 * math.cos(a), cy + r * 0.66 * math.sin(a)
    pg.circle(gx, gy, r * 0.15, SLATE, INK, 2.5)
    pg.circle(gx, gy, r * 0.07, STEEL, INK, 1.5)
    if turns:
        arc = [(cx + r * 1.16 * math.cos(math.radians(d)), cy + r * 1.16 * math.sin(math.radians(d))) for d in range(-150, -59, 6)]
        pg.arrow(arc, ARROW, 5, 26)
    return dict(grip=(gx, gy), hub=(cx, cy))


def kit_load(pg, x, y, m, accent=True):
    """Thirty kit resistors twisted together at both ends, lying on a plate."""
    pg.oval(x - 40 * m, y - 34 * m, x + 400 * m, y + 174 * m, WHITE, INK, 3)
    pg.oval(x + 12 * m, y - 6 * m, x + 348 * m, y + 146 * m, WHITE, STEEL, 1.5)
    col = ORANGE_L if accent else PAPER
    for i in range(9):
        yy = y + 14 * m + i * 14 * m
        pg.wire(bezier((x + 62 * m, y + 70 * m), (x + 100 * m, yy), (x + 120 * m, yy), (x + 140 * m, yy), 12)
                + bezier((x + 220 * m, yy), (x + 240 * m, yy), (x + 262 * m, yy), (x + 298 * m, y + 70 * m), 12), 2.6, STEEL, INK, 1.0)
        pg.rect(x + 138 * m, yy - 6 * m, x + 222 * m, yy + 6 * m, col, INK, 1.8, r=4)
        for f in (0.2, 0.4, 0.6, 0.82):
            pg.line([(x + 138 * m + 84 * m * f, yy - 5 * m), (x + 138 * m + 84 * m * f, yy + 5 * m)], 3, ORANGE_D if accent else SLATE, caps=False)
    for ex in (x + 56 * m, x + 304 * m):
        blob(pg, ex, y + 70 * m, 13 * m, 11 * m, accent)
    return dict(left=(x + 46 * m, y + 70 * m), right=(x + 314 * m, y + 70 * m), top=(x + 180 * m, y + 14 * m), plate=(x + 340 * m, y + 140 * m),
                lump_l=(x + 56 * m, y + 70 * m), lump_r=(x + 304 * m, y + 70 * m))


# --------------------------------------------------------------------------
# the ten pictures
# --------------------------------------------------------------------------

def e1():
    pg = Page(1, "Find the two coil pairs with the meter.")
    back = motor(pg, 150, 420, 1.9)
    ends = [(760, 330), (790, 520), (760, 700), (700, 880)]
    for i, e in enumerate(ends):
        start = (back[0], back[1] - 36 + 24 * i)
        pts = bezier(start, (start[0] + 150, start[1]), (e[0] - 190, e[1]), (e[0] - 34, e[1]))
        pg.wire(pts, 11, STEEL, INK, 1.8)
        pg.wire([(e[0] - 36, e[1]), e], 5, LEAD, INK, 1.5)
    flag(pg, 600, 338, "A")
    flag(pg, 618, 700, "A")
    mt = meter(pg, 1180, 250, 1.5, "01.2", "R200")
    r_end = probe(pg, ends[0], -14, RED)
    b_end = probe(pg, ends[2], 14, INK)
    cable(pg, r_end, mt["red"], RED, via=[(1040, 250), (1110, 420), (1120, 900), (1230, 1090), (1360, 1080)])
    cable(pg, b_end, mt["black"], INK, via=[(1040, 800), (1090, 1050), (1250, 1180), (1470, 1160)])
    pg.call("dial on 200,\nin the " + OHM + " zone", 1680, 500, mt["dial"])
    pg.call("a pair shows a\nsmall number", 1680, 250, (mt["lcd"][0] + 150, mt["lcd"][1]))
    pg.call("tape a flag\non each pair", 330, 190, (592, 316))
    pg.call("four wires,\nany colours", 230, 800, (560, 600))
    pg.call("red probe", 800, 190, (ends[0][0] + 110, ends[0][1] - 30))
    pg.call("black probe", 830, 580, (ends[2][0] + 100, ends[2][1] + 24))
    pg.inset(1660, 780, 1975, 1215)
    lcd(pg, 1700, 815, 1935, 925, "OL")
    pg.text(1700, 950, "a lone 1 =\nnot a pair.\nTry the next\nwire.", px=40)
    pg.text(60, 1070, "The other two wires are pair B.", px=PX_CALL)
    pg.text(60, 1135, "Black lead in COM. Red in the middle socket.", px=PX_CALL)
    return pg.finish()


def e2():
    pg = Page(2, "Build bridge A. Four diodes, every band up.")
    pg.text(40, 180, "1. this ring is the band", px=PX_CALL)
    pg.wire([(230, 290), (230, 760)], 16, LEAD, INK, 2)
    diode(pg, 230, 400, 600, 110, False)
    pg.call("band", 380, 425, (285, 450), face=HEAVY)
    pg.call("lead", 380, 665, (238, 700))
    pg.text(40, 830, "2. two leads side by side,\n    2 cm. Solder the middle.", px=PX_CALL)
    pg.wire([(90, 1040), (440, 1040)], 16, LEAD, INK, 2)
    pg.wire([(260, 1062), (640, 1062)], 16, LEAD, INK, 2)
    blob(pg, 350, 1051, 78, 30, True)
    pg.call("solder", 420, 1150, (365, 1078))
    pg.divider(700)
    lad = Ladder(pg, 1040, 400, 10)
    lad.card(x1=46)
    have = {"D1", "D2", "D3", "D4"}
    lad.legs(have, new=have)
    lad.joints({"J1", "J2", "P1", "M1"}, new={"J1", "J2", "P1", "M1"})
    lad.jlabels((1, 2))
    pg.text(720, 180, "3. tape them on the card, bands toward PLUS", px=PX_CALL)
    pg.call("band\nup", 722, 400, lad.at("D1"), face=HEAVY)
    pg.call("band\nup", 722, 800, lad.at("D2"), face=HEAVY)
    pg.call("4. solder\nfour joints", 1540, 480, [lad.xy(15.6, -0.75), lad.xy(13.0, 28)])
    pg.call("tape", 1540, 760, lad.xy(19.3, 51.2))
    pg.call("bend each end lead\nover a screwdriver", 1540, 960, lad.xy(25, 61.5))
    return pg.finish()


def e3():
    pg = Page(3, "Add bridge B. Join plus to plus, minus to minus.")
    lad = Ladder(pg, 510, 390, 10)
    lad.card(x1=66)
    new = {"D5", "D6", "D7", "D8"}
    lad.legs(ALL_D, new=new)
    lad.joints(ALL_J, new={"J3", "J4", "P2", "P3", "M2", "M3"})
    lad.jlabels()
    pg.text(*lad.xy(57.2, -1.6), "tab", px=36, face=HEAVY, anchor="lm", halo=0)
    pg.text(*lad.xy(58.8, 61.4), "tab", px=36, face=HEAVY, anchor="lm", halo=0)
    pg.call("8 bands,\nall pointing\nat PLUS", 40, 290, lad.at("D1"), face=HEAVY)
    pg.call("the top row of bent\nleads is the PLUS rail", 1210, 215, lad.xy(30, -1.5))
    pg.call("six new joints", 1210, 520, [lad.xy(37.4, 28), lad.xy(40.6, -0.75)])
    pg.call("leave the two\ntabs bare", 1210, 690, None)
    pg.call("the bottom row is\nthe MINUS rail", 1210, 930, lad.xy(32, 61.5))
    pg.inset(40, 690, 312, 1140)
    pg.wire([(176, 712), (176, 930)], 9, LEAD, INK, 1.8)
    diode(pg, 176, 762, 882, 66, False, band_top=False)
    pg.line([(110, 732), (242, 912)], 9, RED)
    pg.line([(242, 732), (110, 912)], 9, RED)
    pg.text(58, 950, "a band\npointing down\nis wrong", px=38)
    return pg.finish()


def e4():
    pg = Page(4, "Meter check: red on J, black on plus.")
    lad = Ladder(pg, 412, 425, 9)
    lad.card(x1=62)
    lad.legs(ALL_D)
    lad.joints(ALL_J)
    lad.jlabels()
    mt = meter(pg, 1130, 230, 1.3, "230", "DIODE")
    jr, pr = lad.at("j1"), lad.xy(6, 0)
    r_end = probe(pg, jr, 25, RED)
    b_end = probe(pg, pr, -60, INK)
    stub(pg, r_end, 14, RED, 400, bend=0.06)
    stub(pg, b_end, -12, INK, 130)
    pg.circle(jr[0], jr[1], 30, None, ORANGE, 6)
    pg.circle(pr[0], pr[1], 30, None, ORANGE, 6)
    stub(pg, mt["red"], 100, RED, 90)
    stub(pg, mt["black"], 80, INK, 90, bend=-0.25)
    pg.call("black probe\non PLUS", 40, 170, (b_end[0] - 50, b_end[1] + 78))
    pg.call("red probe\non J1", 40, 690, (jr[0] - 30, jr[1]))
    pg.call("70 to 350\n= good", 1560, 250, (mt["lcd"][0] + 130, mt["lcd"][1]), face=HEAVY)
    pg.call("dial on the\ndiode mark", 1560, 560, mt["dial"])
    pg.text(250, 1122, "Then J2, J3 and J4 the same way.", px=PX_CALL)
    pg.text(250, 1182, "Then black on each J, red on the MINUS rail.", px=PX_CALL)
    pg.inset(1600, 900, 1975, 1228)
    lcd(pg, 1630, 925, 1945, 1022, "OL")
    pg.text(1630, 1040, "a lone 1 here: that\ndiode is backwards", px=36)
    return pg.finish()


def e5():
    pg = Page(5, "Add the light. First power through one 1 k.")
    lad = Ladder(pg, 191, 330, 8.4)
    lad.card(x1=70)
    lad.legs(ALL_D)
    lad.joints(ALL_J)
    lad.light(accent=True, lit=True)
    lad.jlabels()
    s = lad.s
    # the extra 1 k: one leg hooked on J4, the red clip on its other leg
    hook = lad.xy(37.6, 42.3)
    pg.wire([lad.xy(38.2, 42.3), lad.xy(69, 42.3)], 4, ORANGE_L, INK, 1.3)
    pg.circle(hook[0], hook[1], 1.5 * s, None, INK, 5.5)
    pg.circle(hook[0], hook[1], 1.5 * s, None, ORANGE_L, 2.8)
    a, b = lad.xy(46, 40.5), lad.xy(56, 44.1)
    pg.rect(a[0], a[1], b[0], b[1], ORANGE_L, INK, 2.4, r=10)
    for f in (0.2, 0.4, 0.6, 0.82):
        x = a[0] + (b[0] - a[0]) * f
        pg.line([(x, a[1] + 3), (x, b[1] - 3)], 6, ORANGE_D, caps=False)
    c_red = croc(pg, lad.xy(64.5, 42.3), 0, RED, 0.9)
    stub(pg, c_red, 25, RED, 100)
    c_blk = croc(pg, lad.xy(25.6, 42.6), 120, INK, 0.8)
    stub(pg, c_blk, 95, INK, 235, bend=0.04)
    # the meter on the two tabs
    r_end = probe(pg, lad.xy(47.5, -1.5), -35, RED, 0.9)
    b_end = probe(pg, lad.xy(49, 61.5), 30, INK, 0.9)
    stub(pg, r_end, -8, RED, 100)
    stub(pg, b_end, 8, INK, 100)
    mt = meter(pg, 1560, 170, 1.05, "8.4", "V20")
    stub(pg, mt["red"], 100, RED, 70)
    stub(pg, mt["black"], 80, INK, 70, bend=-0.25)
    sp = supply(pg, 1050, 820, 1.15, "12.0", "0.00")
    stub(pg, sp["pos"], 75, RED, 50, w=6)
    stub(pg, sp["neg"], 105, INK, 50, w=6, bend=-0.25)
    pg.call("8 to 9 V = good", 1000, 250, (mt["lcd"][0] - 110, mt["lcd"][1]), face=HEAVY)
    pg.call("dial on 20,\nin the V= zone", 1090, 400, mt["dial"])
    pg.call("one more 1 k,\nhooked on J4", 860, 520, ((a[0] + b[0]) / 2, a[1] - 2))
    pg.text(400, 985, "black clip on J3", px=PX_CALL)
    pg.call("12.0 V", 1060, 740, (sp["volts"][0] - 62, sp["volts"][1] - 30), face=HEAVY)
    pg.text(40, 1085, "The light: two 1 k and the LED in one string.", px=PX_CALL)
    pg.text(40, 1145, "Resistor end on PLUS. LED short leg on MINUS.", px=PX_CALL)
    pg.text(1560, 760, "Under 3 V, or a\nminus sign: stop.", px=PX_CALL, face=HEAVY)
    pg.text(1560, 940, "Then swap the\ntwo clips. Then\ndo J1 and J2.", px=PX_CALL)
    return pg.finish()


def e6():
    pg = Page(6, "Add the capacitor. Stripe side to minus.")
    pg.wire([(180, 720), (180, 1010)], 9, LEAD, INK, 1.8)
    pg.wire([(280, 720), (280, 930)], 9, LEAD, INK, 1.8)
    pg.rect(110, 300, 350, 730, SLATE, INK, 3.5, r=16)
    pg.rect(262, 318, 350, 712, WHITE, INK, 2.5)
    for i in range(5):
        pg.line([(292, 372 + i * 72), (322, 372 + i * 72)], 8, INK, caps=False)
    pg.line([(110, 690), (350, 690)], 2.5, INK, caps=False)
    pg.text(40, 180, "1000 uF 50 V", px=PX_CALL)
    pg.call("minus signs\non the stripe", 400, 330, (330, 420), face=HEAVY)
    pg.call("short leg\n= MINUS", 400, 820, (286, 900))
    pg.call("long leg\n= PLUS", 40, 1070, (176, 990), face=HEAVY)
    pg.divider(660)
    lad = Ladder(pg, 851, 401, 8.4)
    lad.card(minus_x=63)
    lad.legs(ALL_D)
    lad.joints(ALL_J)
    lad.light()
    c = lad.cap(accent=True)
    lad.jlabels()
    pg.call("long leg on the PLUS tab", 1060, 168, c["plus"])
    pg.call("stripe faces\nthe MINUS\nrail", 1662, 520, (c["stripe"][0] + 40, c["stripe"][1] + 6), face=HEAVY)
    pg.call("three jumper\nwires twisted:\nstripe leg to\nthe MINUS tab", 1662, 760, lad.xy(61.4, 44))
    # the test that belongs to this step: a backwards capacitor must be found at 12 mA, before any cranking
    pg.text(700, 1052, "Then first power again through the 1 k (picture E5).", px=PX_CALL)
    pg.text(700, 1106, "Climbs to 8 to 9 V in 3 seconds = good.\nStays under 3 V = capacitor backwards. Fit a new one.", px=PX_CALL, face=HEAVY)
    return pg.finish()


def _loose_ends(pg, lad, y=75.0):
    """Motor wires that run off the bottom of the card."""
    ends = [lad.xy(c - 3.6, y) for c in lad.COL]
    lad.motor_wires(ends)
    return ends


def e7():
    pg = Page(7, "Solder the motor wires on. Crank with no load.")
    lad = Ladder(pg, 177, 304, 7.6)
    lad.card(minus_x=63)
    lad.legs(ALL_D)
    lad.joints(ALL_J)
    lad.light(lit=True)
    lad.cap()
    lad.jlabels()
    ends = [lad.xy(c - 3.6, 75) for c in lad.COL]
    back = motor(pg, 70, 1060, 0.95)
    for k, e in enumerate(ends):
        st = (back[0], back[1] - 27 + 18 * k)
        pg.wire(bezier(st, (st[0] + 90 + 40 * k, st[1]), (e[0], e[1] + 150), (e[0], e[1] + 2), 30), max(4.5, 1.7 * lad.s), ORANGE, INK, 1.5)
    lad.motor_wires(ends, accent=True)
    for k, e in enumerate(ends):
        flag(pg, e[0], e[1] + 42, "AABB"[k], accent=False, size=0.8)
    c_red = croc(pg, lad.at("plus"), -90, RED, 0.8)
    stub(pg, c_red, -25, RED, 60)
    c_blk = croc(pg, lad.xy(26.3, 61.5), 100, INK, 0.75)
    stub(pg, c_blk, 80, INK, 28, bend=0.0)
    mt = meter(pg, 1190, 190, 1.1, "10.3", "V20")
    stub(pg, mt["red"], 100, RED, 70)
    stub(pg, mt["black"], 80, INK, 70, bend=-0.25)
    crank(pg, 1080, 1040, 140)
    pg.text(1262, 985, "one turn a second\n= 60 turns a minute", px=PX_CALL)
    pg.call("dial on 20,\nin the V=\nzone", 905, 330, mt["dial"])
    pg.text(470, 960, "pair A on J1 and J2,\npair B on J3 and J4", px=PX_CALL)
    pg.text(1555, 200, "30 turns a minute:\n4 to 6 V", px=PX_CALL)
    pg.text(1555, 340, "60 turns a minute:\n9 to 13 V", px=PX_CALL, face=HEAVY)
    pg.text(1555, 480, "90 turns a minute:\n13 to 20 V\n(dial on 200)", px=PX_CALL)
    pg.text(1555, 700, "Nothing plugged\nin? Never faster\nthan 2 turns a\nsecond.", px=PX_CALL, face=HEAVY)
    return pg.finish()


def e8():
    pg = Page(8, "Crank into thirty kit resistors. Ten seconds only.")
    lad = Ladder(pg, 177, 304, 7.6)
    lad.card(minus_x=63)
    lad.legs(ALL_D)
    lad.joints(ALL_J)
    lad.light(lit=True)
    lad.cap()
    _loose_ends(pg, lad)
    k = kit_load(pg, 1170, 900, 1.2, accent=True)
    # each output wire runs across the plate and ends on a lump; the lump is drawn last, on top of the wire end
    lad.out_wires(k["lump_r"], k["lump_l"], accent=True,
                  red_via=[(985, 300), (1010, 690), (1300, 765), (1640, 800), (1672, 905), (1618, 978)],
                  black_via=[(1000, 950), (1150, 986)])
    for q in (k["lump_l"], k["lump_r"]):
        blob(pg, q[0], q[1], 24, 20, True)
    c_red = croc(pg, lad.at("plus"), -90, RED, 0.8)
    stub(pg, c_red, -25, RED, 60)
    c_blk = croc(pg, lad.xy(26.3, 61.5), 100, INK, 0.75)
    stub(pg, c_blk, 80, INK, 28, bend=0.0)
    mt = meter(pg, 1090, 180, 1.0, "8.1", "V20")
    stub(pg, mt["red"], 100, RED, 45)
    stub(pg, mt["black"], 80, INK, 45, bend=-0.25)
    pg.text(1440, 200, "75 turns a minute:\n7.0 V", px=PX_CALL)
    pg.text(1440, 340, "90 turns a minute:\n8.1 V", px=PX_CALL, face=HEAVY)
    pg.text(1440, 480, "Write yours down.", px=PX_CALL)
    pg.call("ten 100, ten 220, ten 330 ohm,\ntwisted together at each end", 1090, 1130, (k["top"][0], k["top"][1] + 118))
    pg.call("on a plate.\nDo not touch.", 1700, 640, (1566, 896), face=HEAVY)
    pg.call("two output wires,\nthree jumpers each", 40, 1010, lad.xy(70, 62.8))
    pg.call("one wire on each lump,\neither way round", 520, 1130, (k["lump_l"][0] - 6, k["lump_l"][1] + 12), face=HEAVY)
    return pg.finish()


def e9():
    pg = Page(9, "Wire the module in. Test it on the supply.")
    lad = Ladder(pg, 170, 358, 7.2)
    lad.card(minus_x=63)
    lad.legs(ALL_D)
    lad.joints(ALL_J)
    lad.light(lit=True)
    lad.cap()
    _loose_ends(pg, lad)
    md = module(pg, 1000, 440, 1.15, accent=True)
    lad.out_wires(md["pos"], md["neg"], red_via=[(900, 330)], black_via=[(900, 720)])
    for q in (md["pos"], md["neg"]):
        blob(pg, q[0], q[1], 17, 15, True)
    ut = usb_tester(pg, 1332, 449, 1.1)
    ph = phone(pg, 1720, 620, 1.15)
    pg.wire(spline([ut["socket"], (1690, 500), (1960, 545), (1978, 1000), (1905, 1125), (ph["port"][0], ph["port"][1] + 4)]), 9, PAPER, INK, 1.8)
    phone(pg, 1720, 620, 1.15)
    c_red = croc(pg, lad.at("plus"), -90, RED, 0.75)
    stub(pg, c_red, -30, RED, 50)
    c_blk = croc(pg, lad.xy(26.3, 61.5), 100, INK, 0.75)
    stub(pg, c_blk, 80, INK, 26, bend=0.0)
    sp = supply(pg, 900, 860, 1.1, "12.0", "0.95")
    stub(pg, sp["pos"], 75, RED, 44, w=6)
    stub(pg, sp["neg"], 105, INK, 44, w=6, bend=-0.25)
    pg.call("red wire to IN+", 1010, 300, (md["pos"][0], md["pos"][1] - 14), face=HEAVY)
    pg.call("black wire to IN" + MINUS, 1010, 650, (md["neg"][0], md["neg"][1] + 14), face=HEAVY)
    pg.call("5.0 to 5.3 V", 1420, 320, ut["face"], face=HEAVY)
    pg.call("write down\nvolts x amps", 1400, 660, (ut["face"][0], ut["face"][1] + 116))
    pg.text(40, 975, "The supply clips go on the two rails.", px=PX_CALL)
    pg.text(40, 1070, "No cranking while the\nsupply is clipped on.", px=PX_CALL, face=HEAVY)
    pg.call("10 W phone:\nabout 0.95 A", 1385, 836, (sp["amps"][0] + 94, sp["amps"][1] - 20), face=HEAVY)
    pg.text(1378, 1040, "12.0 V.\nLimit 0.30 A first.\nPhone in: limit 2.0 A.", px=PX_CALL)
    return pg.finish()


def e10():
    pg = Page(10, "The film: crank, tester in shot, sixty seconds.")
    back = motor(pg, 318, 575, 0.95)
    cr = crank(pg, 240, 640, 185)
    lad = Ladder(pg, 675, 296, 6.4)
    lad.card(minus_x=63)
    lad.legs(ALL_D)
    lad.joints(ALL_J)
    lad.light(lit=True)
    lad.cap()
    ends = [lad.xy(c - 3.6, 75) for c in lad.COL]
    for k, e in enumerate(ends):
        st = (back[0], back[1] - 27 + 18 * k)
        pg.wire(bezier(st, (st[0] + 70 + 20 * k, st[1] + 30), (e[0], e[1] + 150), (e[0], e[1] + 2), 30), max(4.5, 1.7 * lad.s), STEEL, INK, 1.5)
    lad.motor_wires(ends)
    md = module(pg, 1330, 400, 0.95)
    lad.out_wires(md["pos"], md["neg"], red_via=[(1290, 300)], black_via=[(1300, 610)])
    ut = usb_tester(pg, 1609, 402, 1.0)
    pg.rect(1594, 384, 1876, 540, None, ORANGE, 7, r=22)
    ph = phone(pg, 1730, 690, 1.1)
    pg.wire(spline([ut["socket"], (1930, 472), (1978, 600), (1978, 1100), (1905, 1195), (ph["port"][0], ph["port"][1] + 4)]), 9, PAPER, INK, 1.8)
    phone(pg, 1730, 690, 1.1)
    c_red = croc(pg, lad.at("plus"), -90, RED, 0.7)
    stub(pg, c_red, -20, RED, 46)
    c_blk = croc(pg, lad.xy(26.3, 61.5), 100, INK, 0.7)
    stub(pg, c_blk, 80, INK, 16, bend=0.0)
    mt = meter(pg, 1050, 790, 0.82, "8.5", "V20")
    stub(pg, mt["red"], 110, RED, 26, w=6, bend=0.0)
    stub(pg, mt["black"], 70, INK, 26, w=6, bend=0.0)
    pg.call("your pace,\nfrom your own table", 40, 190, (cr["hub"][0] + 20, cr["hub"][1] - 212))
    pg.call("tester in shot.\nWatts = volts x amps", 1400, 180, (1735, 384), face=HEAVY)
    pg.call("icon on for the\nwhole minute", 1370, 900, ph["icon"])
    pg.call("bus 8 V or more: keep going.\nUnder 7.5 V: speed up now.", 40, 1090, (mt["lcd"][0] - 70, mt["lcd"][1]))
    return pg.finish()


def template():
    """The card at full size on A4 (300 dots per inch), to print at 100 % and tape onto the card."""
    dpi = 300
    mm = dpi / 25.4
    pg = Page(0, "", size=(int(297 * mm), int(210 * mm)))
    lad = Ladder(pg, 62 * mm, 72 * mm, mm)
    lad.card(minus_x=63)
    lad.legs(ALL_D, tape=False)
    lad.joints(ALL_J)
    lad.light()
    lad.cap()
    lad.jlabels(px=40)
    big, mid = 96, 62
    pg.text(30 * mm, 14 * mm, "Card template", px=big, face=HEAVY)
    pg.text(30 * mm, 26 * mm, "Print at 100 %, not \"fit to page\". This bar must measure 50 mm:", px=mid)
    pg.rect(30 * mm, 36 * mm, 80 * mm, 39 * mm, INK, None, 0)
    for x in (30, 80):
        pg.line([(x * mm, 33 * mm), (x * mm, 42 * mm)], 4, INK, caps=False)
    pg.text(84 * mm, 37.5 * mm, "50 mm", px=mid, anchor="lm")
    x = 165
    for i, row in enumerate(("Cut round the outline. Tape it onto stiff card.",
                             "Lay each part on its picture.",
                             "Every band toward PLUS.",
                             "Capacitor: stripe toward MINUS.",
                             "LED: long leg toward the resistors.",
                             "Grey lumps: solder here.",
                             "Legs are 12 mm apart. Rails are 60 mm apart.")):
        pg.text(x * mm, (62 + 13 * i) * mm, row, px=mid, face=HEAVY if "band" in row or "stripe" in row else MEDIUM)
    return pg.finish(header=False)


PICTURES = [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10]


def main():
    want = [int(a) for a in sys.argv[1:] if a.isdigit()]
    if not want or "template" in sys.argv[1:]:
        img = template()
        img.save(os.path.join(HERE, "card_template.png"), optimize=True, dpi=(300, 300))
        img.save(os.path.join(HERE, "card_template.pdf"), resolution=300.0, quality=95)
        print("wrote card_template.png and card_template.pdf (A4, full size)")
        if "template" in sys.argv[1:] and not want:
            return
    pages = []
    for i, fn in enumerate(PICTURES, 1):
        if want and i not in want:
            continue
        img = fn()
        path = os.path.join(HERE, f"wire_{i:02d}.png")
        img.save(path, optimize=True)
        pages.append(img)
        print(f"wrote {path}")
    if not want:
        pdf = os.path.join(HERE, "electronics.pdf")
        pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=200.0, quality=95)
        print(f"wrote {pdf} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
