"""Hand-crank phone charger: the numbers, before any plastic.

    python3 design.py          score the transmission you chose
    python3 design.py lock     write the predicted USB watts to prediction.json

The generator side is not guessed: sim/alternator_sweep.py ran the stepper as
an alternator through SPICE and this file interpolates that table. What the
sweep showed, and what drives everything below:

  A stepper used as an alternator has a TORQUE CEILING. Its winding inductance
  limits the current no matter how fast it turns, so past a few hundred rpm it
  absorbs a fixed torque (about 0.084 N m for the NEMA17, 0.335 N m for the
  NEMA23) and the only way to more watts is more rpm. Power = torque x speed,
  the torque is capped, so the transmission's whole job is speed.

  That torque comes back to your hand multiplied by the ratio. A big ratio is
  exactly what makes the crank heavy.
"""
import json
import math
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SWEEP = os.path.join(HERE, "sim", "alternator_sweep.json")
LOCK = os.path.join(HERE, "prediction.json")

# ---- the hand (estimates from general ergonomics, not measured on you) ----
HAND_RPM = 90.0            # comfortable one-arm cadence
CRANK_ARM_MM = 100.0      # the handle sits ON the big gear (cad/charger.py reads this)
SUSTAINED_W = 20.0         # one arm, a few minutes; brief bursts go well above
OVERSPEED = 1.5            # somebody WILL spin it as fast as they can, unloaded

# ---- the electrical end (check against the label of the module you buy) ----
BUCK_VIN_MIN = 7.0         # V, a 5 V buck needs headroom
BUCK_VIN_MAX = 30.0        # V, above this the module dies
BUCK_EFF = 0.88            # assumed
USB_MAX_W = 10.0           # 5 V 2 A port; the phone decides what it takes
PHONE_WH = 15.0            # typical phone battery

# ---- the printed gears ----
MESH_EFF = 0.90            # per stage, bearings included. A GUESS: the drivetrain
                           # rig in ~/Documents/drivetrain_rig exists to measure it.
PLA_ALLOW_MPA = 12.5       # 50 MPa in-plane tensile / safety factor 4
BED_MM = 240.0             # P1S plate is 256, keep a margin
MIN_TEETH = 17             # 20 degree teeth undercut below 17; gears.py has no profile shift
RING_RIM = 6.0             # solid wall outside a ring gear's tooth roots (cad/planetary.py reads this)

def transmission():
    """Paing's calls, 2026-09-30, in order: the NEMA23, module 2.4 ("i want it
    bigger"), then planetary ("i want it advanced").

    One planetary stage run as a STAR drive: the three planets turn on pins
    fixed to the frame, the ring gear is the wheel you crank, the sun sits on
    the motor shaft. Ratio = ring / sun = 91 / 17 = 5.35.

    Why these teeth: 17 is the smallest sun that does not undercut. 91 - 17 =
    2 x 37, so the planets fit between. (91 + 17) / 3 = 36, a whole number, so
    three planets sit at equal angles. 17, 37 and 91 share no factors pairwise
    where they mesh, so wear is even. The ring comes out 236 mm across.

    The 12 mm face is my default."""
    return dict(motor="nema23", module=2.4, face_width=12.0,
                stages=[dict(kind="star", sun=17, planet=37, ring=91, planets=3)])

# --------------------------------------------------------------------------

def _generator(motor, rpm):
    """(dc watts available, shaft watts, bus volts) at this speed, bus held in the buck's window."""
    with open(SWEEP) as fh:
        rows = json.load(fh)[motor]["rows"]
    pts = []
    for r in sorted({x["rpm"] for x in rows}):
        ok = [x for x in rows if x["rpm"] == r and BUCK_VIN_MIN <= x["vbus"] <= BUCK_VIN_MAX]
        b = max(ok, key=lambda x: x["p_bus"])
        pts.append((r, max(b["p_bus"], 0.0), max(b["p_shaft"], 0.0), b["vbus"]))
    if rpm < pts[0][0]:
        return 0.0, 0.0, pts[0][3]
    if rpm > pts[-1][0]:
        raise ValueError(f"{rpm:.0f} rpm is beyond the sweep ({pts[-1][0]} rpm). Extend RPMS in sim/alternator_sweep.py.")
    for (r0, p0, s0, v0), (r1, p1, s1, v1) in zip(pts, pts[1:]):
        if r0 <= rpm <= r1:
            t = (rpm - r0) / (r1 - r0)
            return p0 + t * (p1 - p0), s0 + t * (s1 - s0), v0 if t < 0.5 else v1

def _lewis_y(z):
    return 0.484 - 2.865 / z           # 20 degree full-depth form factor, standard fit

def evaluate(tx):
    with open(SWEEP) as fh:
        ke = json.load(fh)[tx["motor"]]["params"]["ke"]
    m, b, stages = float(tx["module"]), float(tx["face_width"]), list(tx["stages"])
    ratio = math.prod(st["ring"] / st["sun"] if isinstance(st, dict) else st[0] / st[1] for st in stages)
    # a planetary stage passes the power through two meshes in series
    eff = math.prod(MESH_EFF ** 2 if isinstance(st, dict) else MESH_EFF for st in stages)
    gen_rpm = HAND_RPM * ratio
    p_dc, p_shaft, vbus = _generator(tx["motor"], gen_rpm)
    p_usb = min(p_dc * BUCK_EFF, USB_MAX_W)
    # if the phone takes less than the generator offers, the generator is loaded less
    load = p_usb / (p_dc * BUCK_EFF) if p_dc > 0 else 0.0
    p_crank = load * p_shaft / eff
    w_hand = HAND_RPM * 2 * math.pi / 60
    t_crank = p_crank / w_hand
    v_open = ke * gen_rpm * OVERSPEED * 2 * math.pi / 60       # unloaded, rectified peak

    checks, torque = [], t_crank
    for i, st in enumerate(stages, 1):
        if isinstance(st, dict):                                # star planetary: ring in, sun out
            S, P, R, n = st["sun"], st["planet"], st["ring"], st["planets"]
            ft = torque / (m * R / 2000) / n                    # N per planet; the planet is an idler,
            sigma = ft / (b * m * _lewis_y(S))                  # so the sun tooth sees the same force
            gap = (S + P) * math.sin(math.pi / n) - (P + 2)     # between neighbouring planets, in modules
            across = m * (R + 2.5) + 2 * RING_RIM
            checks += [(f"stage {i} sun has {S} teeth (min {MIN_TEETH})", S >= MIN_TEETH),
                       (f"stage {i} planets fit: {R} - {S} = 2 x {P}", R - S == 2 * P),
                       (f"stage {i} {n} planets sit at equal angles: ({R} + {S}) / {n} is whole", (R + S) % n == 0),
                       (f"stage {i} neighbouring planets clear by {gap * m:.1f} mm", gap * m >= 2.0),
                       (f"stage {i} teeth {S}:{P}:{R} share no factor where they mesh", math.gcd(S, P) == 1 and math.gcd(P, R) == 1),
                       (f"stage {i} tooth root {sigma:.2f} MPa (allow {PLA_ALLOW_MPA})", sigma <= PLA_ALLOW_MPA),
                       (f"stage {i} ring gear {across:.0f} mm across (bed {BED_MM:.0f})", across <= BED_MM)]
            torque *= S / R * MESH_EFF ** 2
            continue
        zb, zs = st
        ft = torque / (m * zb / 2000)                           # N at the pitch circle
        sigma = ft / (b * m * _lewis_y(zs))                     # MPa on the pinion tooth root
        checks.append((f"stage {i} pinion has {zs} teeth (min {MIN_TEETH})", zs >= MIN_TEETH))
        checks.append((f"stage {i} tooth root {sigma:.2f} MPa (allow {PLA_ALLOW_MPA})", sigma <= PLA_ALLOW_MPA))
        checks.append((f"stage {i} big gear {m * (zb + 2):.0f} mm across (bed {BED_MM:.0f})", m * (zb + 2) <= BED_MM))
        checks.append((f"stage {i} teeth {zb}:{zs} share no factor", math.gcd(zb, zs) == 1))
        torque *= zs / zb * MESH_EFF
    checks.append((f"module {m} mm (min 1.0 on a 0.4 nozzle)", m >= 1.0))
    checks.append((f"unloaded at {OVERSPEED}x speed the bus reaches {v_open:.0f} V (buck max {BUCK_VIN_MAX:.0f})",
                   v_open <= BUCK_VIN_MAX))
    checks.append((f"crank power {p_crank:.1f} W (sustainable {SUSTAINED_W:.0f})", p_crank <= SUSTAINED_W))
    checks.append((f"at most 3 stages (you have {len(stages)})", len(stages) <= 3))
    return dict(ratio=ratio, gen_rpm=gen_rpm, vbus=vbus, p_dc=p_dc, p_usb=p_usb, p_crank=p_crank,
                t_crank=t_crank, hand_force=t_crank / (CRANK_ARM_MM / 1000),
                mesh_hz=gen_rpm / 60 * (stages[-1]["sun"] if isinstance(stages[-1], dict) else stages[-1][1]), checks=checks,
                min_per_percent=(PHONE_WH / 100) / p_usb * 60 if p_usb > 0 else float("inf"))

def report(tx, r):
    print(f"{tx['motor']}, module {tx['module']}, stages " + " x ".join(
        f"star {st['sun']}/{st['planet']}/{st['ring']}" if isinstance(st, dict) else f"{st[0]}:{st[1]}" for st in tx["stages"]))
    print(f"  ratio            {r['ratio']:.2f} : 1   ->  generator at {r['gen_rpm']:.0f} rpm")
    print(f"  at the phone     {r['p_usb']:.1f} W      (generator offers {r['p_dc']:.1f} W dc at a {r['vbus']} V bus)")
    print(f"  at your hand     {r['p_crank']:.1f} W = {r['t_crank']:.2f} N m = {r['hand_force']:.0f} N on a {CRANK_ARM_MM:.0f} mm arm")
    print(f"  system           {100 * r['p_usb'] / r['p_crank'] if r['p_crank'] else 0:.0f} % hand to phone")
    print(f"  last mesh        {r['mesh_hz']:.0f} Hz (that is the pitch of the whine)")
    print(f"  1 % of a phone   {r['min_per_percent']:.1f} min of cranking")
    for text, ok in r["checks"]:
        print(f"  [{'ok' if ok else 'NO'}] {text}")
    print("  not modelled: iron loss in the stepper (grows with rpm), so high-rpm watts are optimistic.")

def lock(tx, r):
    if os.path.exists(LOCK):
        print(f"{os.path.basename(LOCK)} already exists - not overwriting. A prediction made twice is not one.")
        return 1
    failed = [t for t, ok in r["checks"] if not ok]
    if failed:
        print("not locking a design with failed checks:\n  " + "\n  ".join(failed))
        return 1
    with open(LOCK, "w") as fh:
        json.dump(dict(locked_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       transmission=tx, predicted_usb_w=round(r["p_usb"], 2),
                       predicted_crank_w=round(r["p_crank"], 2)), fh, indent=2)
    print(f"locked: {r['p_usb']:.1f} W at the phone. The USB meter now gets to disagree.")
    return 0

if __name__ == "__main__":
    try:
        tx = transmission()
    except NotImplementedError:
        print("transmission() is still a stub. Nothing to score, and the frame cannot be")
        print("drawn until it is filled in: every centre distance follows from it.")
        sys.exit(1)
    r = evaluate(tx)
    report(tx, r)
    sys.exit(lock(tx, r) if "lock" in sys.argv[1:] else 0)
