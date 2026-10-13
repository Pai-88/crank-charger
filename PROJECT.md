# Crank charger

A hand crank, a printed step-up gear train, a stepper motor run backwards as an
alternator, and a phone that shows the charging icon.

## Exit test (the only definition of done)

> **Filmed: 60 s of continuous cranking, your phone plugged in, the charging
> icon on for the whole minute, a USB power meter in shot, and the measured
> watts written next to the number `design.py lock` predicted BEFORE the first
> crank. By 2026-10-25.**

STLs are not done. A render is not done. A lit LED is not done. A multimeter
reading with no phone attached is not done.

## The three facts the design hangs on

**1. The generator has a torque ceiling.** `sim/alternator_sweep.py` ran both
candidate steppers through SPICE (two phases, two Schottky bridges, a DC bus).
Winding inductance caps the current whatever the speed, so each motor absorbs a
fixed torque and extra watts only come from extra rpm:

| motor | torque ceiling | dc watts at 450 rpm | at 1000 rpm |
|---|---|---|---|
| NEMA17 (17HS4401) | 0.084 N m | 2.5 (at a 3 V bus) | 7.1 |
| NEMA23 (23HS5628) | 0.335 N m | 11.6 | 30.8 |

The NEMA23 constants match the 23HS22-2804S datasheet; the NEMA17 ones are
quoted from memory. Iron loss is not modelled, so the high-rpm numbers are
optimistic.

**2. The transmission trades torque for speed, and the torque lands on you.**
The gear train speeds the shaft UP, so torque at the generator is SMALLER than
at the crank by the ratio. "Lots of torque" is what your hand feels: the
generator's ceiling multiplied back through the ratio. A big ratio or a big
motor makes a heavy crank and more watts. A reduction would make the generator
turn slower than your hand and produce nothing.

**3. A 5 V buck needs about 7 V in.** A NEMA17 behind one 5:1 stage turns at
450 rpm and peaks at 7.8 V, which after two diode drops leaves the buck nothing:
`design.py` scores that layout at 0 W. It needs more ratio, a bigger motor, or a
buck-boost module.

## The honest payoff

A phone battery is about 15 Wh. At 10 W into the phone, 1 % takes about a minute
of cranking at roughly 17 W of effort. This is a demonstrator of a drivetrain
and an energy chain, not a way to charge a phone.

## The mechanism (decided 2026-09-30, third and current layout)

NEMA23 behind one herringbone planetary stage run as a STAR drive, module 2.4:

- **ring gear, 91 teeth:** the 236 mm wheel you crank
- **three planets, 37 teeth:** idlers on 608 bearings, on M8 pins fixed to the frame
- **sun, 17 teeth:** on the motor shaft, turning 91 / 17 = 5.35 times faster than the hand

The three pins run from the wall, through the planets, into a fixed spider in
front of the gears. The spider carries the axle for a spoked wheel with the
handle on it, and that wheel drives the ring through six dogs. So the hand's
side load goes wheel, axle, spider, pins, wall, and the teeth carry torque only.
The ring floats and is centred by the planets, which is what shares the load
between them.

Herringbone teeth cannot be slid into each other, so ring, planets and sun are
printed in place as one job, already meshed.

`python3 design.py` scores it at 10.0 W into the phone for 17.5 W at the hand
(1.85 N m, 19 N on the grip at 90 rpm). The single spur stage it replaced
scored 9.2 W for 14.6 W: the planetary costs about a fifth more effort,
because the power crosses two meshes instead of one.

## Order of work

1. ~~`transmission()`~~ decided.
2. Print the coupon (`cad/stl/coupon_*.stl`, about an hour): two gears printed
   already in mesh. If they come apart and spin, the gearset will too.
3. `python3 design.py lock`. This is the prediction the exit test is judged
   against, so it happens before anything turns.
4. Print and build: `PRINT.md`.
5. Wire rectifiers, capacitor and buck module. Bench it with a resistor first.
6. The film. That film, with the meter in shot, is the LinkedIn post.

## Parts

| part | note |
|---|---|
| NEMA23 stepper, JoyNano 2.8 A 1.26 N m (datasheet twin of the 23HS22-2804S) | the generator; measure the shaft before printing the sun |
| 8 x diode, 3 A or more, from a parts kit | two bridges, one per phase; Schottky for full output, 1N5408 at about 10 % less |
| bus capacitor, 1000 uF or more, 35 V or more, from a parts kit | smooths the DC; 25 V parts are NOT enough, the bus reaches 24 V unloaded |
| buck module with USB-A socket, 6 to 32 V in, 5 V out | ready-made, nothing to solder but two wires |
| USB power meter | the instrument for the exit test |
| 5 x 608 bearings, M8 / M6 / M5 bolts, 2 clamps | full list in `PRINT.md` |

No surface-mount parts and no bare ICs.

## Files

- `design.py`: the scorer and the prediction lock. `transmission()` holds the decision.
- `sim/alternator_sweep.py`: SPICE sweep of the stepper as an alternator.
- `cad/gears.py`: involute spur, herringbone and ring-gear generator. `set_checks()`
  rolls the whole planetary set through a tooth pitch and measures every gap.
- `cad/mesh_coupon.py`: the first print.
- `cad/planetary.py`: frame, print-in-place gearset, spider, wheel, grip, spacers,
  and 50 checks on them.
- `cad/old_spur_stage/`: the single-stage layout this replaced. Complete, never printed.
- `PRINT.md`: print order, hardware, assembly sequence.
