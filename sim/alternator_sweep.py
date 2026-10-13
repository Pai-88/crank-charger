"""What does a NEMA17 stepper actually deliver as an alternator? Ask SPICE.

Two phases, each a back-EMF source behind its winding R and L, each into its
own Schottky bridge, both bridges onto one DC bus held at a fixed voltage (a
big capacitor feeding a buck converter looks like that). Sweep shaft speed and
bus voltage, record the DC power and the shaft torque.

    python3 alternator_sweep.py        writes alternator_sweep.json

The motor numbers are the common 17HS4401 (1.7 A, 1.5 ohm, 2.8 mH, 0.40 N m
holding) and the NEMA23 23HS5628 (2.8 A, 0.9 ohm, 2.5 mH, 1.26 N m), both
QUOTED FROM MEMORY. Replace them from the datasheet of the motor you
buy; everything downstream is recomputed from this file's output.
"""
import json
import math
import os
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

POLE_PAIRS = 50            # 1.8 degree stepper: 50 rotor teeth
# r_phase ohm, l_phase H, holding torque N m (both phases at rated current), rated A
MOTORS = {
    "nema17": dict(r=1.5, l=2.8e-3, hold=0.40, i=1.7),    # 17HS4401
    "nema23": dict(r=0.9, l=2.5e-3, hold=1.26, i=2.8),    # 23HS5628
}

def ke(m):
    """Back-EMF constant, V s/rad peak per phase. Two phases in quadrature at
    rated current give holding torque = sqrt(2) * Kt * I, and Ke = Kt in SI."""
    return m["hold"] / (math.sqrt(2) * m["i"])

RPMS = (200, 300, 450, 600, 800, 1000, 1300, 1700, 2200)
VBUS = (3, 5, 7, 9, 12, 15, 18, 24, 30, 40)

NETLIST = """* stepper as alternator, rpm={rpm}, bus={vbus} V
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
VBUS bus 0 DC {vbus}
.tran {dt:.4e} {tstop:.5e} {tstart:.5e} {dt:.4e}
.meas tran ibus AVG i(VBUS)
.meas tran pemf AVG par('-(v(ea,0a)*i(VA) + v(eb,0b)*i(VB))')
.end
"""

def run(name, rpm, vbus):
    m = MOTORS[name]
    KE, R_PHASE, L_PHASE = ke(m), m["r"], m["l"]
    w = rpm * 2 * math.pi / 60
    f = POLE_PAIRS * rpm / 60
    text = NETLIST.format(rpm=rpm, vbus=vbus, e=KE * w, f=f, r=R_PHASE, l=L_PHASE,
                          dt=1 / (f * 400), tstop=60 / f, tstart=30 / f)
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as fh:
        fh.write(text)
        path = fh.name
    out = subprocess.run(["ngspice", "-b", path], capture_output=True, text=True, timeout=120)
    os.unlink(path)
    got = dict(re.findall(r"^(ibus|pemf)\s*=\s*([-+0-9.eE]+)", out.stdout, re.M))
    if len(got) != 2:
        raise RuntimeError(f"ngspice gave no measurement at {rpm} rpm, {vbus} V:\n{out.stdout[-800:]}")
    p_bus = vbus * float(got["ibus"])          # current INTO the bus source is positive
    p_emf = float(got["pemf"])                 # power leaving the two EMF sources
    return dict(motor=name, rpm=rpm, vbus=vbus, e_peak=round(KE * w, 3), p_bus=round(p_bus, 4),
                p_shaft=round(p_emf, 4), torque=round(p_emf / w, 5))

if __name__ == "__main__":
    out = {}
    for name, m in MOTORS.items():
        rows = [run(name, rpm, v) for rpm in RPMS for v in VBUS]
        print(f"\n{name}: Ke = {ke(m):.4f} V s/rad per phase, short-circuit limit "
              f"Ke/(p L) = {ke(m) / (POLE_PAIRS * m['l']):.2f} A peak")
        print(f"{'rpm':>5} {'E pk':>6} {'best bus V':>10} {'P dc W':>7} {'P shaft W':>9} {'torque mNm':>10} {'eta':>5}")
        for rpm in RPMS:
            b = max((r for r in rows if r["rpm"] == rpm), key=lambda r: r["p_bus"])
            print(f"{rpm:>5} {b['e_peak']:>6.2f} {b['vbus']:>10} {b['p_bus']:>7.2f} {b['p_shaft']:>9.2f} "
                  f"{1000 * b['torque']:>10.1f} {b['p_bus'] / max(b['p_shaft'], 1e-9):>5.2f}")
        out[name] = dict(params=dict(m, pole_pairs=POLE_PAIRS, ke=round(ke(m), 5)), rows=rows)
    with open(os.path.join(HERE, "alternator_sweep.json"), "w") as fh:
        json.dump(out, fh, indent=1)
