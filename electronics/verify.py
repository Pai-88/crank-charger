"""Re-runs the numbers that ELECTRONICS.md quotes, with the two soft constants banded.

    python3 electronics/verify.py            everything (a few minutes)
    python3 electronics/verify.py pace       only the pace table for the film

Same two-phase, two-bridge ngspice model as sim/alternator_sweep.py and
electronics/checks.py. Reads those files, never writes to them. What this adds:

  * Ke scaled x0.85 / x1.00 / x1.25 and L scaled x0.8 / x1.0 / x1.2
  * the slowest hand pace that holds a constant-power load with the bus at 7 V or more
  * the kit load (ten 100 + ten 220 + ten 330 ohm in parallel = 5.69 ohm) and the 10 ohm load
  * a TVS held at its breakdown voltage with no other load
  * the short-circuit current at the edges of the band
  * one flick of the bare shaft into 1000 uF (a small time-step model, no ngspice)

Every number is a MODEL PREDICTION. Nothing here has been measured.
"""
import math
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import design  # noqa: E402  (read only)
import json  # noqa: E402

P = json.load(open(os.path.join(ROOT, "sim", "alternator_sweep.json")))["nema23"]["params"]
KE, R_PH, L_PH, POLES = P["ke"], P["r"], P["l"], P["pole_pairs"]
ST = design.transmission()["stages"][0]
RATIO = ST["ring"] / ST["sun"]
EFF = design.BUCK_EFF
R_KIT = 1 / (10 / 100 + 10 / 220 + 10 / 330)

HEAD = """* banded alternator model
.model SCH D(Is=2e-6 N=1.05 Rs=0.04 Cjo=200p)
VA ea 0a SIN(0 {e:.5f} {f:.4f})
RA ea ma {r}
LA ma ta1 {l}
VB eb 0b SIN(0 {e:.5f} {f:.4f} 0 0 90)
RB eb mb {r}
LB mb tb1 {l}
D1 ta1 bus SCH
D2 0a  bus SCH
D3 0 ta1 SCH
D4 0 0a  SCH
D5 tb1 bus SCH
D6 0b  bus SCH
D7 0 tb1 SCH
D8 0 0b  SCH
RfA 0a 0 10Meg
RfB 0b 0 10Meg
"""
FIXED = HEAD + """VBUS bus 0 DC {vbus}
.tran {dt:.4e} {tstop:.5e} {tstart:.5e} {dt:.4e}
.meas tran ibus AVG i(VBUS)
.meas tran ia RMS i(VA)
.meas tran pemf AVG par('-(v(ea,0a)*i(VA) + v(eb,0b)*i(VB))')
.end
"""
RLOAD = HEAD + """C1 bus 0 1000u ic=0
RL bus 0 {rl}
.tran {dt:.4e} {tstop:.5e} {tstart:.5e} {dt:.4e} uic
.meas tran vavg AVG v(bus)
.meas tran ia RMS i(VA)
.meas tran pemf AVG par('-(v(ea,0a)*i(VA) + v(eb,0b)*i(VB))')
.end
"""
_cache = {}


def _run(text, keys):
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as fh:
        fh.write(text)
        path = fh.name
    out = subprocess.run(["ngspice", "-b", path], capture_output=True, text=True, timeout=300)
    os.unlink(path)
    got = dict(re.findall(r"^(%s)\s*=\s*([-+0-9.eE]+)" % "|".join(keys), out.stdout, re.M))
    if len(got) != len(keys):
        raise RuntimeError(out.stdout[-600:])
    return {k: float(v) for k, v in got.items()}


def fixed(hand_rpm, vbus, ks=1.0, ls=1.0):
    """DC watts into a bus held at vbus, plus phase amps rms and shaft watts."""
    key = (round(hand_rpm, 3), round(vbus, 3), ks, ls)
    if key not in _cache:
        m = hand_rpm * RATIO
        w, f = m * 2 * math.pi / 60, POLES * m / 60
        g = _run(FIXED.format(e=KE * ks * w, f=f, r=R_PH, l=L_PH * ls, vbus=vbus,
                              dt=1 / (f * 300), tstop=50 / f, tstart=25 / f), ("ibus", "ia", "pemf"))
        _cache[key] = dict(p=max(vbus * g["ibus"], 0.0), ia=g["ia"], shaft=g["pemf"])
    return _cache[key]


def rload(hand_rpm, rl, ks=1.0, ls=1.0):
    m = hand_rpm * RATIO
    w, f = m * 2 * math.pi / 60, POLES * m / 60
    settle = max(8 * rl * 1e-3, 0.05)
    g = _run(RLOAD.format(e=KE * ks * w, f=f, r=R_PH, l=L_PH * ls, rl=rl,
                          dt=1 / (f * 200), tstop=settle + 30 / f, tstart=settle), ("vavg", "ia", "pemf"))
    return dict(v=g["vavg"], w=g["vavg"] ** 2 / rl, ia=g["ia"], hand=g["pemf"] / design.MESH_EFF ** 2)


GRID_RPM = [45 + 5 * k for k in range(21)]            # 45 .. 145 hand rpm
GRID_V = (7.0, 7.5, 8.0, 8.5, 9.0, 10.0, 11.0, 12.0)


def prefetch(jobs):
    """Run many fixed-bus cases at once (ngspice is one process per case)."""
    from concurrent.futures import ThreadPoolExecutor
    todo = [j for j in set(jobs) if (round(j[0], 3), round(j[1], 3), j[2], j[3]) not in _cache]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda j: fixed(*j), todo))


def best(hand_rpm, ks=1.0, ls=1.0):
    """Most DC watts the generator gives with the bus at 7 V or more."""
    prefetch([(hand_rpm, v, ks, ls) for v in GRID_V])
    return max(fixed(hand_rpm, v, ks, ls)["p"] for v in GRID_V)


def min_pace(p_phone, ks=1.0, ls=1.0):
    """Slowest grid pace that gives the watts, refined by a straight line between grid points."""
    need = p_phone / EFF
    prefetch([(h, v, ks, ls) for h in GRID_RPM for v in GRID_V])
    tab = [(h, best(h, ks, ls)) for h in GRID_RPM]
    if tab[0][1] >= need:
        return tab[0][0]
    for (h0, p0), (h1, p1) in zip(tab, tab[1:]):
        if p0 < need <= p1:
            return h0 + (need - p0) / (p1 - p0) * (h1 - h0)
    return float("nan")


def bus_at(hand_rpm, p_phone, ks=1.0, ls=1.0):
    """Bus volts on the stable (high) side where the generator gives exactly what the module takes."""
    need = p_phone / EFF
    vs = [30.0 - 0.5 * k for k in range(47)]              # 30 V down to 7 V
    prefetch([(hand_rpm, v, ks, ls) for v in vs])
    for v in vs:
        if fixed(hand_rpm, v, ks, ls)["p"] >= need:
            return v
    return None


BAND = ((0.85, 1.0, "Ke x0.85"), (1.0, 1.0, "nominal"), (1.25, 1.0, "Ke x1.25"),
        (1.0, 1.2, "L x1.2"), (0.85, 1.2, "Ke x0.85, L x1.2"), (1.25, 0.8, "Ke x1.25, L x0.8"))


def pace():
    print("\nSlowest hand pace (rpm) that holds the phone, bus at 7 V or more, module at %.0f %%" % (100 * EFF))
    print("  no-load bus at 60 rpm is the reading he will have from test C2: Ke * w - 0.4")
    print(f"  {'case':<18} {'bus@60':>7} {'5 W':>6} {'7.5 W':>6} {'10 W':>6} {'12 W':>6}")
    for ks, ls, name in BAND:
        v60 = KE * ks * 60 * RATIO * 2 * math.pi / 60 - 0.4
        print(f"  {name:<18} {v60:>7.1f} " + " ".join(f"{min_pace(p, ks, ls):>6.0f}" for p in (5, 7.5, 10, 12)))
    print("\nBus volts while charging (nominal model), stable side:")
    for p in (5, 7.5, 10, 12):
        print(f"  phone {p:>4} W: " + "  ".join(
            f"{h} rpm {('%.1f V' % v) if (v := bus_at(h, p)) else 'cannot'}" for h in (80, 90, 100, 110)))
    print("\nMost DC watts at 7 V or more, and at exactly 7.0 / 7.7 / 8.1 V, nominal, 90 rpm:")
    print("  best %.1f W;  7.0 V %.1f W;  7.7 V %.1f W;  8.1 V %.1f W" % (
        best(90), fixed(90, 7.0)["p"], fixed(90, 7.7)["p"], fixed(90, 8.1)["p"]))
    print("  at 90 rpm with Ke x0.85: best %.1f W dc = %.1f W at the phone" % (best(90, 0.85), best(90, 0.85) * EFF))


def loads():
    print(f"\nKit load: ten 100 + ten 220 + ten 330 ohm in parallel = {R_KIT:.2f} ohm")
    for h in (45, 60, 75, 90, 100, 110):
        row = [rload(h, R_KIT, ks, ls) for ks, ls in ((1, 1), (0.85, 1.2), (1.25, 0.8))]
        n = row[0]
        print(f"  {h:>3} rpm: {n['v']:.2f} V {n['w']:5.1f} W, hand {n['hand']:4.1f} W, each 100 ohm part {n['v'] ** 2 / 100:.2f} W"
              f"   band {row[1]['v']:.1f} to {row[2]['v']:.1f} V")
    print("\nThe rule 'phone watts you can HOLD = k x (V x V / 5.7)': k across the band")
    for h in (75, 90, 105):
        ks_ = []
        for ks, ls, name in BAND:
            ks_.append(best(h, ks, ls) * EFF / rload(h, R_KIT, ks, ls)["w"])
        print(f"  {h:>3} rpm: k = " + ", ".join(f"{k:.2f}" for k in ks_))
    print("\n10 ohm load (ten 100 ohm in parallel, 2.5 W): pace that gives 5.0 V")
    for ks, ls, name in ((1, 1, "nominal"), (0.85, 1, "Ke x0.85"), (1.25, 1, "Ke x1.25")):
        lo, hi = 20.0, 80.0
        while hi - lo > 0.5:
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if rload(mid, 10.0, ks, ls)["v"] >= 5.0 else (mid, hi)
        print(f"  {name:<10} {hi:.0f} rpm")
    print("  nominal at 60 rpm: %.2f V %.1f W; at 90 rpm: %.2f V %.1f W" % (
        rload(60, 10)["v"], rload(60, 10)["w"], rload(90, 10)["v"], rload(90, 10)["w"]))
    print("\n4.7 ohm power resistor, 90 rpm: nominal %.2f V %.1f W; band %.1f to %.1f V" % (
        rload(90, 4.7)["v"], rload(90, 4.7)["w"], rload(90, 4.7, 0.85, 1.2)["v"], rload(90, 4.7, 1.25, 0.8)["v"]))
    print("\nBench supply behind 4.7 ohm as a stand-in for the generator at 90 rpm (amps into the bus):")
    for v in (5, 6, 7, 8, 9):
        print(f"  bus {v} V: supply 15.3 V gives {(15.3 - v) / 4.7:.2f} A, generator model gives {fixed(90, v)['p'] / v:.2f} A")


def clamp():
    print("\nTVS holding the bus with no load: watts it must burn (model)")
    for ks, name in ((1.0, "nominal Ke"), (1.25, "Ke x1.25")):
        for h in (90, 100, 110, 120, 135, 150):
            print(f"  {name:<11} {h:>3} rpm: " + "  ".join(
                f"clamp {vc} V {fixed(h, vc, ks)['p']:5.1f} W" for vc in (17.1, 18.0, 18.9)))
    print("  P6KE in free air: (150 - 25) C / 75 C per W = %.1f W (the 5 W figure needs the leads held at 75 C)" % (125 / 75))


def short():
    print("\nShort circuit on the bus (bus held at 0.05 V):")
    for ks, ls, name in ((1, 1, "nominal"), (1.25, 1, "Ke x1.25"), (1.25, 0.8, "Ke x1.25, L x0.8")):
        g = fixed(90, 0.05, ks, ls)
        print(f"  {name:<18} 90 rpm: {g['p'] / 0.05:.1f} A dc, {g['ia']:.2f} A rms per phase")


def flick():
    """One flick of the bare shaft into 1000 uF with the LED string across it."""
    print("\nOne finger flick of the bare shaft (rotor 300 g cm2 ASSUMED, friction 0.02 N m ASSUMED):")
    J, C, VD, TF = 3.0e-5, 1.0e-3, 0.30, 0.02
    for rev_s in (2, 3, 4, 6, 8):
        w, th, ia, ib, v, dt = rev_s * 2 * math.pi, 0.0, 0.0, 0.0, 0.0, 2e-6
        while w > 0.05:
            ea, eb = KE * w * math.sin(POLES * th), KE * w * math.cos(POLES * th)
            new = []
            for e, i in ((ea, ia), (eb, ib)):
                back = v + 2 * VD
                if i == 0.0 and abs(e) <= back:
                    new.append(0.0)
                    continue
                s = math.copysign(1.0, i if i != 0.0 else e)
                n = i + dt * (e - R_PH * i - s * back) / L_PH
                new.append(0.0 if n * s < 0 else n)
            torque = KE * (ia * math.sin(POLES * th) + ib * math.cos(POLES * th)) + TF
            ia, ib = new
            led = max(v - 1.9, 0.0) / 2000
            v += dt * (abs(ia) + abs(ib) - led) / C
            w -= dt * torque / J
            th += dt * w
        e0 = 0.5 * J * (rev_s * 2 * math.pi) ** 2
        print(f"  {rev_s} rev/s: rotor holds {1000 * e0:5.1f} mJ, open-circuit peak {KE * rev_s * 2 * math.pi:4.1f} V, bus ends at {v:.1f} V")
    print("  energy in 1000 uF at 5.5 V: %.0f mJ" % (0.5 * 1e-3 * 5.5 ** 2 * 1000))


def bench():
    print("\nFirst power through one 1 k resistor (supply 12.0 V):")
    i = (12.0 - 0.3 - 1.9) / 3000
    print(f"  good board: {1000 * i:.1f} mA, bus {1.9 + 2000 * i:.1f} V. Most that can ever flow: {12.0 / 1000 * 1000:.0f} mA")
    print("  LED string at 32 V: %.1f mA, %.2f W in each 1 k" % ((32 - 1.9) / 2, ((32 - 1.9) / 2000) ** 2 * 1000))
    print("  LED string drains C1 with time constant 2 k x 1000 uF = 2 s, and stops near the LED's 1.7 to 1.9 V")
    print("\nMeter (AstroAI AM33D class, from its manual):")
    for rng, pct, dig, res, val in (("200 V AC", 2.0, 10, 0.1, 7.57), ("20 V DC", 0.8, 2, 0.01, 10.3), ("200 ohm", 1.5, 5, 0.1, 0.9),
                                    ("2000 mV DC", 0.8, 2, 0.001, 0.9)):
        err = val * pct / 100 + dig * res
        print(f"  {rng:<11} reading {val:>5}: +/- {err:.3f} = +/- {100 * err / val:.0f} %")
    print("  three 28 AWG jumpers in parallel: %.0f milliohm per metre, %.0f mW lost at 2 A over 16 cm" % (213 / 3, 4 * 0.213 / 3 * 0.16 * 1000))


if __name__ == "__main__":
    print(f"ratio {RATIO:.3f}, Ke {KE}, R {R_PH} ohm, L {1000 * L_PH} mH, module efficiency {EFF}")
    if sys.argv[1:] == ["pace"]:
        pace()
    else:
        bench()
        flick()
        short()
        loads()
        clamp()
        pace()
