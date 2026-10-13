"""Expected readings for the electronics bench tests.

    python3 electronics/checks.py

Reads sim/alternator_sweep.json and design.py (never writes to them) and runs
a few extra ngspice cases: the same two-phase, two-bridge model as
sim/alternator_sweep.py, but with a real capacitor and a resistor on the bus
instead of an ideal fixed-voltage bus. Every number printed here is a MODEL
PREDICTION. Iron loss is not modelled and Ke is derived from the holding
torque, so treat the outputs as plus or minus 15 to 25 %.
"""
import json
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
import design  # noqa: E402  (read only: evaluate() and constants)

SWEEP = json.load(open(os.path.join(ROOT, "sim", "alternator_sweep.json")))["nema23"]
KE = SWEEP["params"]["ke"]
R_PH, L_PH, POLES = SWEEP["params"]["r"], SWEEP["params"]["l"], SWEEP["params"]["pole_pairs"]
tx = design.transmission()
st = tx["stages"][0]
RATIO = st["ring"] / st["sun"]

NET = """* stepper alternator into C and R, motor rpm={rpm}
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
VS bus busc 0
C1 busc 0 {c} ic=0
RL bus 0 {rl}
.tran {dt:.4e} {tstop:.5e} {tstart:.5e} {dt:.4e} uic
.meas tran vavg AVG v(bus)
.meas tran vmax MAX v(bus)
.meas tran vmin MIN v(bus)
.meas tran icap RMS i(VS)
.meas tran ia RMS i(VA)
.meas tran pemf AVG par('-(v(ea,0a)*i(VA) + v(eb,0b)*i(VB))')
.end
"""

def spice(motor_rpm, rl, c=1000e-6):
    w = motor_rpm * 2 * math.pi / 60
    f = POLES * motor_rpm / 60
    settle = max(8 * rl * c, 0.05)
    text = NET.format(rpm=motor_rpm, e=KE * w, f=f, r=R_PH, l=L_PH, c=c, rl=rl,
                      dt=1 / (f * 200), tstop=settle + 30 / f, tstart=settle)
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as fh:
        fh.write(text)
        path = fh.name
    out = subprocess.run(["ngspice", "-b", path], capture_output=True, text=True, timeout=300)
    os.unlink(path)
    got = dict(re.findall(r"^(vavg|vmax|vmin|icap|ia|pemf)\s*=\s*([-+0-9.eE]+)", out.stdout, re.M))
    if len(got) != 6:
        raise RuntimeError(out.stdout[-600:])
    return {k: float(v) for k, v in got.items()}

def p_fixed_bus(motor_rpm, vbus):
    """DC watts from the sweep table at a fixed bus voltage, linear in rpm and in volts."""
    rows = SWEEP["rows"]
    rpms = sorted({x["rpm"] for x in rows})
    vs = sorted({x["vbus"] for x in rows})
    tab = {(x["rpm"], x["vbus"]): max(x["p_bus"], 0.0) for x in rows}
    if motor_rpm < rpms[0]:
        return 0.0
    r0 = max(r for r in rpms if r <= motor_rpm)
    r1 = min(r for r in rpms if r >= motor_rpm)
    v0 = max(v for v in vs if v <= vbus)
    v1 = min(v for v in vs if v >= vbus)
    tr = 0 if r1 == r0 else (motor_rpm - r0) / (r1 - r0)
    tv = 0 if v1 == v0 else (vbus - v0) / (v1 - v0)
    a = tab[r0, v0] + tv * (tab[r0, v1] - tab[r0, v0])
    b = tab[r1, v0] + tv * (tab[r1, v1] - tab[r1, v0])
    return a + tr * (b - a)

def bus_for_power(motor_rpm, p_dc):
    """Bus voltage on the STABLE (falling) side of the P-V curve where the generator gives p_dc."""
    best = None
    v = 30.0
    while v >= 5.0:
        if p_fixed_bus(motor_rpm, v) >= p_dc:
            best = v
            break
        v -= 0.05
    return best

def hand(motor_rpm):
    return motor_rpm / RATIO

if __name__ == "__main__":
    r = design.evaluate(tx)
    print(f"ratio {RATIO:.3f}, Ke {KE} V s/rad peak per phase, R {R_PH} ohm, L {L_PH * 1000} mH")
    print(f"design.py: {r['p_usb']:.1f} W usb, {r['p_dc']:.1f} W dc at {r['vbus']} V, {r['p_crank']:.1f} W hand, gen {r['gen_rpm']:.0f} rpm")

    print("\n(b) open-circuit AC volts per phase = Ke * w / sqrt(2)")
    print("    per motor rpm: %.5f V rms, per hand rpm: %.4f V rms, frequency %.3f Hz per motor rpm" % (
        KE * 2 * math.pi / 60 / math.sqrt(2), KE * 2 * math.pi / 60 / math.sqrt(2) * RATIO, POLES / 60))
    for h in (30, 60, 90):
        m = h * RATIO
        print(f"    hand {h:>3} rpm -> motor {m:5.0f} rpm -> {KE * m * 2 * math.pi / 60 / math.sqrt(2):5.2f} V rms at {POLES * m / 60:4.0f} Hz")
    for m in (60, 120, 180, 300):
        print(f"    bare shaft {m:>3} rpm -> {KE * m * 2 * math.pi / 60 / math.sqrt(2):5.2f} V rms at {POLES * m / 60:4.0f} Hz")

    print("\n(c) no-load DC bus = Ke * w - two light-load diode drops (about 0.4 V)")
    print("    peak volts per hand rpm: %.4f" % (KE * 2 * math.pi / 60 * RATIO))
    for h in (30, 60, 90, 120, 135, 150, 180):
        print(f"    hand {h:>3} rpm -> peak {KE * h * RATIO * 2 * math.pi / 60:5.1f} V -> bus about {KE * h * RATIO * 2 * math.pi / 60 - 0.4:5.1f} V")
    for lim in (25, 30, 32, 50):
        print(f"    bus {lim} V needs hand {(lim + 0.4) / (KE * 2 * math.pi / 60 * RATIO):.0f} rpm")

    print("\nshort circuit on the bus (0.01 ohm), model:")
    for h in (60, 90, 135):
        s = spice(h * RATIO, 0.01)
        print(f"    hand {h:>3} rpm: bus {s['vavg'] / 0.01:4.2f} A dc, phase {s['ia']:.2f} A rms, shaft {s['pemf']:.1f} W, "
              f"motor torque {s['pemf'] / (h * RATIO * 2 * math.pi / 60):.3f} N m, hand torque {s['pemf'] / (h * 2 * math.pi / 60) / design.MESH_EFF ** 2:.2f} N m")
    print("    analytic limit Ke / (pole pairs * L) = %.2f A peak per phase" % (KE / (POLES * L_PH)))

    print("\n(e) resistor on the bus, 1000 uF, model:")
    for rl, name in ((10.0, "10 ohm (ten 100 ohm 1/4 W in parallel, 2.5 W)"), (6.8, "6.8 ohm power resistor"),
                     (4.7, "4.7 ohm power resistor"), (33.0, "33 ohm (ten 330 ohm 1/4 W in parallel, 2.5 W)")):
        print(f"  {name}")
        for h in (30, 40, 45, 50, 60, 75, 90, 105):
            s = spice(h * RATIO, rl)
            print(f"    hand {h:>3} rpm: bus {s['vavg']:5.2f} V  {s['vavg'] / rl:4.2f} A  {s['vavg'] ** 2 / rl:5.2f} W  "
                  f"ripple {s['vmax'] - s['vmin']:.2f} V p-p  cap {s['icap']:.2f} A rms  phase {s['ia']:.2f} A rms  hand {s['pemf'] / design.MESH_EFF ** 2:5.1f} W")

    print("\n(f) the module is a constant-power load. Bus voltage where the sweep table gives that power")
    print("    (stable side of the curve), and the slowest hand speed that can supply it at 7 V or more:")
    for p_usb in (2.5, 5.0, 7.5, 10.0, 12.0):
        p_dc = p_usb / design.BUCK_EFF
        line = f"    phone takes {p_usb:4.1f} W -> bus needs {p_dc:5.2f} W dc:"
        for h in (75, 90, 105):
            v = bus_for_power(h * RATIO, p_dc)
            line += f"  {h} rpm: " + (f"{v:4.1f} V {p_dc / v:4.2f} A" if v else " cannot ")
        hmin = next((h / 2 for h in range(60, 400) if max(p_fixed_bus(h / 2 * RATIO, v / 10) for v in range(70, 301, 5)) >= p_dc), None)
        print(line + f"   min hand {hmin} rpm")
    print("    sweep at design speed (%.0f motor rpm):" % (design.HAND_RPM * RATIO), "  ".join(
        f"{v} V: {p_fixed_bus(design.HAND_RPM * RATIO, v):.1f} W" for v in (5, 7, 9, 12, 15)))

    print("\nbus capacitor at the design point (load 5.2 ohm stands in for 11.4 W at 7.7 V):")
    for c in (1000e-6, 2000e-6):
        s = spice(design.HAND_RPM * RATIO, 5.2, c)
        print(f"    {c * 1e6:.0f} uF: bus {s['vavg']:.2f} V, ripple {s['vmax'] - s['vmin']:.3f} V p-p, cap current {s['icap']:.2f} A rms, phase {s['ia']:.2f} A rms")
    for v in (8, 16, 24, 32):
        print(f"    energy in 1000 uF at {v} V: {0.5 * 1e-3 * v * v:.3f} J")
    print("    ride-through of 1000 uF from 9 V down to 6 V at 11.4 W: %.1f ms" % (0.5e-3 * (81 - 36) / 11.4 * 1000))
