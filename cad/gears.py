"""Involute gears for the crank charger: spur or herringbone, 20 degree teeth.

One function, gear(), builds any gear in the train. pair_checks() is the part
that matters: it rolls two profiles through a full tooth pitch and measures
whether they collide, so a gear that renders fine but cannot turn is caught
here and not on the printer.

Print orientation: flat on the bed, axis vertical. No supports: the herringbone
flank leans by the helix angle, well inside 45 degrees.
"""
import math

import cadquery as cq
from shapely.affinity import rotate, translate
from shapely.geometry import Point, Polygon

PRESSURE_ANGLE = math.radians(20.0)
ADDENDUM = 1.0             # x module
DEDENDUM = 1.25            # x module, leaves 0.25 m root clearance
BACKLASH = 0.15            # mm at the pitch circle, total for a pair. Printed teeth
                           # come out fat; the mesh coupon tells you if this is enough.
HELIX = math.radians(20.0) # herringbone half-angle; 0 gives a plain spur gear
NOZZLE = 0.4
FOOT_RELIEF = 0.25         # mm shaved off every flank and tip over the first FOOT_H of height:
FOOT_H = 0.6               # the first layers squash outward, and on a print-in-place set that
                           # squash is what welds neighbours together

def _inv(a):
    return math.tan(a) - a

class Tooth:
    """The 2D geometry of one gear, all in mm and radians."""
    def __init__(self, z, module, backlash=BACKLASH, add=ADDENDUM, ded=DEDENDUM):
        self.z, self.m = z, module
        self.r = module * z / 2                         # pitch radius
        self.rb = self.r * math.cos(PRESSURE_ANGLE)     # base circle
        self.ra = self.r + add * module                 # tip
        self.rf = self.r - ded * module                 # root
        # each gear gives up half the pair's backlash
        self.half_pitch_angle = (math.pi * module / 2 - backlash / 2) / (2 * self.r)
        self.pitch = 2 * math.pi / z

    def half_angle(self, rho):
        """Half the tooth's angular thickness at radius rho (involute above the base
        circle, a radial line below it)."""
        phi = math.acos(min(1.0, self.rb / rho))
        return self.half_pitch_angle + _inv(PRESSURE_ANGLE) - _inv(phi)

    def tip_land(self):
        return 2 * self.half_angle(self.ra) * self.ra

    def flank(self, n):
        """n+1 (radius, half angle) samples from where the involute starts up to the tip."""
        r0 = max(self.rb, self.rf)
        # square-root spacing puts more samples near the base circle, where it curves most
        return [(rho, self.half_angle(rho)) for rho in
                (r0 + (self.ra - r0) * (i / n) ** 2 for i in range(n + 1))]

    def outline(self, n=24):
        """Closed polyline of the whole gear, tooth 0 centred on +X, counter-clockwise."""
        fl = self.flank(n)
        root_half = self.half_angle(max(self.rb, self.rf))
        pts = []
        for k in range(self.z):
            t = k * self.pitch
            pol = [(self.rf, t - root_half)] if self.rf < self.rb else []
            pol += [(rho, t - a) for rho, a in fl]
            pol += [(rho, t + a) for rho, a in reversed(fl)]
            if self.rf < self.rb:
                pol.append((self.rf, t + root_half))
            gap0, gap1 = t + root_half, t + self.pitch - root_half
            pol += [(self.rf, gap0 + (gap1 - gap0) * j / 4) for j in (1, 2, 3)]
            pts += [(rho * math.cos(a), rho * math.sin(a)) for rho, a in pol]
        return pts

def centre_distance(z1, z2, module):
    return module * (z1 + z2) / 2

def mesh_angle(z):
    """Rotation (degrees) that turns a gear built by gear() so a tooth GAP faces -X,
    ready to mesh with a gear at the origin whose tooth 0 faces +X."""
    return 180.0 + 180.0 / z

def _wire(t, spline_pts=7):
    """The closed 2D outline of Tooth t as one CadQuery wire: spline flanks, arc roots."""
    fl = t.flank(spline_pts)
    root_half = t.half_angle(max(t.rb, t.rf))

    def xy(rho, a):
        return (rho * math.cos(a), rho * math.sin(a))

    wp = cq.Workplane("XY").moveTo(*xy(t.rf, -root_half) if t.rf < t.rb else xy(fl[0][0], -fl[0][1]))
    for k in range(t.z):
        c = k * t.pitch
        if t.rf < t.rb:
            wp = wp.lineTo(*xy(t.rb, c - root_half))
        wp = wp.spline([xy(rho, c - a) for rho, a in fl[1:]], includeCurrent=True)
        wp = wp.lineTo(*xy(t.ra, c + fl[-1][1]))
        wp = wp.spline([xy(rho, c + a) for rho, a in reversed(fl[:-1])], includeCurrent=True)
        if t.rf < t.rb:
            wp = wp.lineTo(*xy(t.rf, c + root_half))
        wp = wp.threePointArc(xy(t.rf, c + t.pitch / 2), xy(t.rf, c + t.pitch - root_half))
    return wp.close()

def _herringbone(wp, t, width, hand, helix):
    if helix == 0:
        return wp.extrude(width)
    twist = hand * math.degrees(math.tan(helix) * (width / 2) / t.r)
    lower = wp.twistExtrude(width / 2, twist)
    return lower.union(lower.mirror("XY", (0, 0, width / 2)))

def _foot_cut(t_slim, t, width, hand, helix, spline_pts):
    """The bottom FOOT_H of a gear, shaved to the slimmer tooth t_slim, keeping the
    same helix so the relief follows the flank."""
    if helix == 0:
        return _wire(t_slim, spline_pts).extrude(FOOT_H + 0.5).translate((0, 0, -0.5))
    rate = hand * math.degrees(math.tan(helix) / t.r)            # degrees of twist per mm of height
    wp = _wire(t_slim, spline_pts)
    return wp.rotate((0, 0, 0), (0, 0, 1), -rate * 0.5).twistExtrude(FOOT_H + 0.5, rate * (FOOT_H + 0.5)).translate((0, 0, -0.5))

def gear(z, module, width, bore, hand=1, helix=HELIX, backlash=BACKLASH, spline_pts=7, relief=FOOT_RELIEF):
    """One external gear, bottom face on Z=0, tooth 0 centred on +X at Z=0.

    hand = +1 or -1. An external pair needs OPPOSITE hands. helix=0 gives a spur gear."""
    t = Tooth(z, module, backlash)
    body = _herringbone(_wire(t, spline_pts), t, width, hand, helix)
    if relief:
        slim = Tooth(z, module, backlash + 2 * relief, add=ADDENDUM - relief / module, ded=DEDENDUM + relief / module)
        keep = _foot_cut(slim, t, width, hand, helix, spline_pts)
        body = body.cut(cq.Workplane("XY").circle(t.ra + 2).extrude(FOOT_H + 0.5).translate((0, 0, -0.5)).cut(keep))
    if bore:
        body = body.cut(cq.Workplane("XY").circle(bore / 2).extrude(width))
    return body

def ring_cutter(z, module, backlash=BACKLASH):
    """The Tooth whose solid is the HOLE in a ring gear: an external gear turned inside
    out. Its tip cuts the ring's roots (so 1.25 m), its root leaves the ring's tips (1.0 m),
    and it is FATTER by the backlash, because the ring's spaces are what get widened."""
    return Tooth(z, module, -backlash, add=DEDENDUM, ded=ADDENDUM)

def ring(z, module, width, r_out, hand=1, helix=HELIX, backlash=BACKLASH, spline_pts=7, relief=FOOT_RELIEF):
    """Internal ring gear, bottom face on Z=0, a tooth SPACE centred on +X at Z=0.

    A ring and the planet inside it need the SAME hand (the opposite of an external pair)."""
    t = ring_cutter(z, module, backlash)
    hole = _herringbone(_wire(t, spline_pts), t, width, hand, helix)
    body = cq.Workplane("XY").circle(r_out).extrude(width).cut(hole)
    if relief:
        fat = Tooth(z, module, -backlash - 2 * relief, add=DEDENDUM + relief / module, ded=ADDENDUM - relief / module)
        body = body.cut(_foot_cut(fat, t, width, hand, helix, spline_pts))
    return body

def pair_checks(z1, z2, module, backlash=BACKLASH, steps=40):
    """Roll the pair through one tooth pitch in 2D. Returns a list of (text, ok)."""
    out = []
    a = centre_distance(z1, z2, module)

    def roll(bl):
        t1, t2 = Tooth(z1, module, bl), Tooth(z2, module, bl)
        g1, g2 = Polygon(t1.outline()), Polygon(t2.outline())
        worst_overlap, min_gap = 0.0, float("inf")
        for i in range(steps):
            phi = math.degrees(t1.pitch) * i / steps
            p1 = rotate(g1, phi, origin=(0, 0))
            p2 = translate(rotate(g2, mesh_angle(z2) - phi * z1 / z2, origin=(0, 0)), a, 0)
            worst_overlap = max(worst_overlap, p1.intersection(p2).area)
            min_gap = min(min_gap, p1.distance(p2))
        return worst_overlap, min_gap, t1, t2

    # with zero backlash a correct involute pair touches everywhere and overlaps nowhere.
    # Whatever overlap is left is the polyline's own chord error, so it must be tiny.
    overlap0, gap0, _, _ = roll(0.0)
    out.append((f"zero-backlash pair is conjugate: overlap {overlap0:.5f} mm2, gap {gap0:.4f} mm",
                overlap0 < 2e-3 and gap0 < 5e-3))
    overlap, gap, t1, t2 = roll(backlash)
    expect = backlash / 2 * math.cos(PRESSURE_ANGLE)
    out.append((f"{z1}:{z2} rolls one pitch with no collision (overlap {overlap:.6f} mm2)", overlap < 1e-6))
    out.append((f"flank gap {gap:.3f} mm (expected about {expect:.3f})", 0.6 * expect < gap < 1.4 * expect))
    for t in (t1, t2):
        out.append((f"{t.z}T tip land {t.tip_land():.2f} mm (at least one {NOZZLE} mm line)", t.tip_land() >= NOZZLE))
        out.append((f"{t.z}T has {t.z} teeth (17 or more, no undercut)", t.z >= 17))
    contact_ratio = (math.sqrt(t1.ra ** 2 - t1.rb ** 2) + math.sqrt(t2.ra ** 2 - t2.rb ** 2)
                     - a * math.sin(PRESSURE_ANGLE)) / (math.pi * module * math.cos(PRESSURE_ANGLE))
    out.append((f"contact ratio {contact_ratio:.2f} (above 1.2: a tooth is always engaged)", contact_ratio > 1.2))
    return out

def ring_half(z, module, width, r_out, hand=1, helix=HELIX, backlash=BACKLASH, spline_pts=7, relief=FOOT_RELIEF):
    """HALF a herringbone ring: a single helix of the given hand, `width` tall, bottom on Z=0,
    with the foot relief on that bottom. Two of these of opposite hand, stacked, make the
    herringbone ring that ring() makes in one piece, and unlike that one they can be
    screwed onto planets that already exist."""
    t = ring_cutter(z, module, backlash)
    twist = hand * math.degrees(math.tan(helix) * width / t.r)
    hole = _wire(t, spline_pts).twistExtrude(width, twist)
    body = cq.Workplane("XY").circle(r_out).extrude(width).cut(hole)
    if relief:
        fat = Tooth(z, module, -backlash - 2 * relief, add=DEDENDUM + relief / module, ded=ADDENDUM - relief / module)
        body = body.cut(_foot_cut(fat, t, width, hand, helix, spline_pts))
    return body

def half_twist(z, module, width, helix=HELIX):
    """Degrees a single helix of this ring turns through over `width` of height."""
    return math.degrees(math.tan(helix) * width / (module * z / 2))

def planet_angle(theta_deg, S, P):
    """Rotation (degrees) of a planet sitting at angle theta round the sun, for a sun
    whose tooth 0 faces +X. It is the angle the planet would reach by ROLLING round a
    fixed sun from theta=0, which is why it stays in mesh at every position."""
    return 180.0 + 180.0 / P + theta_deg * (1 + S / P)

def set_checks(S, P, R, n, module, backlash, steps=24):
    """Roll a whole star set (carrier fixed) through one sun tooth pitch in 2D."""
    out = []
    a = centre_distance(S, P, module)
    thetas = [360.0 * i / n for i in range(n)]

    def roll(bl):
        ts, tp, tc = Tooth(S, module, bl), Tooth(P, module, bl), ring_cutter(R, module, bl)
        sun, planet = Polygon(ts.outline()), Polygon(tp.outline())
        ringp = Point(0, 0).buffer(tc.ra + 6, 64).difference(Polygon(tc.outline()))
        worst, gap_s, gap_r = 0.0, float("inf"), float("inf")
        for i in range(steps):
            phi = 360.0 / S * i / steps
            sun_i, ring_i = rotate(sun, phi, origin=(0, 0)), rotate(ringp, -phi * S / R, origin=(0, 0))
            for th in thetas:
                p = translate(rotate(planet, planet_angle(th, S, P) - phi * S / P, origin=(0, 0)),
                              a * math.cos(math.radians(th)), a * math.sin(math.radians(th)))
                worst = max(worst, sun_i.intersection(p).area, ring_i.intersection(p).area)
                gap_s, gap_r = min(gap_s, sun_i.distance(p)), min(gap_r, ring_i.distance(p))
        return worst, gap_s, gap_r, ts, tp, tc

    o0, gs0, gr0, _, _, _ = roll(0.0)
    out.append((f"zero-backlash set is conjugate: overlap {o0:.5f} mm2, gaps {gs0:.4f} / {gr0:.4f} mm",
                o0 < 2e-3 and gs0 < 5e-3 and gr0 < 5e-3))
    o, gs, gr, ts, tp, tc = roll(backlash)
    expect = backlash / 2 * math.cos(PRESSURE_ANGLE)
    out.append((f"sun, {n} planets and ring roll one pitch with no collision (overlap {o:.6f} mm2)", o < 1e-6))
    out.append((f"sun-planet flank gap {gs:.3f} mm, planet-ring {gr:.3f} mm (expected about {expect:.3f})",
                0.6 * expect < gs < 1.4 * expect and 0.6 * expect < gr < 1.4 * expect))
    out.append((f"printed in place: no flank closer than {min(gs, gr):.2f} mm (0.15 or the parts fuse)", min(gs, gr) >= 0.15))
    for t, name in ((ts, "sun"), (tp, "planet")):
        out.append((f"{name} {t.z}T tip land {t.tip_land():.2f} mm", t.tip_land() >= 2 * NOZZLE))
    ring_tip = 2 * (math.pi / R - tc.half_angle(tc.rf)) * tc.rf
    out.append((f"ring {R}T tip land {ring_tip:.2f} mm", ring_tip >= 2 * NOZZLE))
    out.append((f"ring has {R - P} more teeth than a planet (12 or more, or the tips foul)", R - P >= 12))
    return out
