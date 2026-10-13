# Crank charger: the electronics

Version of 2026-10-05. It replaces the draft of 2026-10-04.

**Open `electronics.pdf` first.** Ten pictures, one per page,
Step E1 to Step E10. This file is the words behind them.

**Nothing here is built or measured.** Every "expect" number is
a model prediction. `python3 electronics/verify.py` prints all
of them again. Three things in the model are soft:

- Ke (volts per speed) comes from the listing, not a meter.
  I band it from 15 % under to 25 % over.
- Coil inductance L is banded 20 % each way.
- Iron loss is not modelled. Real watts will be a bit lower.

## The pictures

| File | Step | Shows |
|---|---|---|
| wire_01 | E1 | find the two coil pairs |
| wire_02 | E2 | bridge A, bands up |
| wire_03 | E3 | bridge B, the two rails |
| wire_04 | E4 | meter check by position |
| wire_05 | E5 | the light, first power |
| wire_06 | E6 | the capacitor |
| wire_07 | E7 | motor wires, crank unloaded |
| wire_08 | E8 | crank into the kit load |
| wire_09 | E9 | module on the supply |
| wire_10 | E10 | the film |

`card_template.pdf` is the card at full size, to print.
`wiring_pictures.py` redraws all of it.

## The chain

    motor -> 8 diodes -> capacitor -> module -> USB -> phone
    (AC)     AC to DC    smooths      makes     tester
                                      5 V

Three facts explain everything below.

1. Faster cranking means more volts. With nothing plugged in
   the bus gets about 0.18 V for every turn a minute (model).
2. The motor cannot push much current: 3 to 5 A even into a
   dead short (model). So no diode, wire or coil can burn from
   cranking. Small test resistors can. A reversed capacitor can.
3. The module takes what the phone asks for. Crank too slowly
   and the bus collapses and the phone stops. Speed is the game.

## Words

- **band**: the pale ring on one end of a diode.
- **Schottky**: a kind of diode that wastes less voltage.
- **bus**: the two DC rails, PLUS and MINUS.
- **rail**: one row of joined diode leads.
- **tab**: the bare end of a rail that sticks out to the right.
- **J1 to J4**: the four middle joints. One motor wire on each.
- **lone 1**: a single 1 at the far left of the meter screen.
  It means "open, nothing connected". It does not mean 1 ohm.
- **limit**: the current limit knob on the bench supply.
- **kit load**: thirty kit resistors twisted together (5.7 ohm).

---

# Card 1. TODAY, with what is on the desk

No new parts needed. Tick each one.

**[ ] 0. Lock the prediction.** `PROJECT.md` says lock it before
anything turns. There is no `prediction.json` yet.

    python3 design.py lock

That is your click. I did not run it.

**[ ] 1. Find the two coil pairs.** Picture E1.

- Dial on 200 in the ohm zone. Black lead in COM, red lead in
  the middle socket.
- Touch one wire with red. Try the other three with black.
- One of them shows a small number such as 01.2. That is its
  partner. The other two show the lone 1.
- Tape a flag on that pair: A. The two left over are pair B.
- No-meter cross-check: hold two bare ends together and twirl
  the shaft. A pair makes the shaft feel stiff. A non-pair
  changes nothing.
- Write the colours here: A = ____ + ____   B = ____ + ____

**[ ] 2. Coil to body.** Dial on 20M. One probe on a bare wire
end, one on bare metal of the motor body. Expect the lone 1 on
all four wires. Do not touch the probe tips: skin reads about
1 M. Any other reading: do not use the motor. Tell me.

**[ ] 3. Coil resistance, with the bench supply.** The meter's
ohm range is too coarse for this (it is good to 0.5 ohm only).

- Output OFF. Volts to about 1 V. Clip the two clips together.
  Output ON. Turn the current knob to 1.00 A. Output OFF.
  Unclip. Volts to 3.0 V.
- Clip onto pair A. Output ON. The shaft locks. That is normal.
- Meter dial on 2000m in the V= zone. Probes on the two bare
  wire ends, not on the clips.
- Expect **800 to 1050**. That is millivolts. Divide by 1000
  for ohms. (Listing: 0.95 ohm. Model: 0.9 ohm.)
- Output OFF before you unclip. Then pair B.
- A = ______ mV    B = ______ mV
- The two should be within 10 % of each other. If not, or if
  both are above 1500: tell me, the model changes.

**[ ] 4. See AC.** On the breadboard: two LEDs side by side,
facing opposite ways, one 1 k in series with the pair. Join it
across pair A. Twirl the shaft. Both LEDs light: one on each
half of the wave. Milliamps only, so the breadboard is fine.

**[ ] 5. Optional: a first rectifier.** The kit has two small
1 A diodes.

- One wire of A and one wire of B into the same row. MINUS.
- The other wire of A to the plain end of diode 1.
- The other wire of B to the plain end of diode 2.
- Both band ends into one row. That row is PLUS.
- LED and one 1 k from PLUS to MINUS. Long LED leg to PLUS.
- Twirl. The LED lights. AC has become DC.

**[ ] 6. Phone cable.** The module and the USB tester are USB-A.
If your iPhone cable has USB-C at the charger end it will not
plug in. Then you need a USB-A cable for the phone.

**[ ] 7. Tester label.** `SHOPPING.md` wrote "3 to 7 V, up to
3.5 A". Read the label on yours. Rating: ______ V.

**[ ] 8. What the phone draws.** Only if your normal charger has
a USB-A socket: put the tester between it and the phone, at
20 to 60 % battery. ______ V x ______ A = ______ W.

**[ ] 9. Make the kit load.** Count ten 100 ohm, ten 220 ohm and
ten 330 ohm resistors. Twist all thirty together at one end,
then at the other. Solder each twist into one lump. Meter on
200: expect 5 to 7 ohm. Mine reads: ______

**[ ] 10. Decide about a spare module. By Sat 10 Oct.** The one
module arrives 20 to 24 Oct. The film is due 25 Oct. If it is
late or dead there is no time. `SHOPPING.md` names a 5-pack of
the same kind that came in days for GBP 9.99 (read on 30 Sep,
not re-checked). Buy it, or write your fallback here:
"no working module by Thu 22 Oct means the film moves". ______

**[ ] 11. Pay the two basket lines** when you are ready (next
card). Your click.

---

# Card 2. BUY

**Plan A needs only two lines that are already in the basket.**

| Line | GBP | For |
|---|---|---|
| SR560 Schottky, 20 | 5.99 | the 8 diodes |
| 1000 uF 50 V, 25 | 6.69 | the capacitor |
| **Total** | **12.68** | |

Prices are from `ORDER_2026-10-03.md`. Both packs are shared
with the arm. Everything else comes from the ELEGOO kit.

**From the kit:** three 1 k resistors, one LED, nine jumper
wires, the thirty resistors of the kit load.

**Tools you must own.** Check now:

- soldering iron and solder (you have the YIHUA 926)
- any tape, a pen, stiff card about 13 x 10 cm
- a screwdriver (to bend leads over)
- something to cut THIN leads: side cutters or nail clippers.
  The fat diode leads are never cut in this build.
- glasses, for first power and for clipping leads
- an old plate or a tile (the kit load gets hot)

**Optional, not price-checked** (I was told not to shop):

- the spare module 5-pack: see Today, item 10
- one 4.7 ohm 50 W resistor: lets you run the load test for a
  minute instead of ten seconds (appendix C)

**In the basket but not used here:** the fuse holder (the
generator tops out at 3 to 5 A, a 5 A fuse would not blow),
the DC jack adapters, the PCB screw terminals, the AMS1117
modules. The P6KE18A is optional: appendix D.

---

# Card 3. BUILD

The rectifier is a ladder of eight diodes, soldered lead to
lead, taped on a card. No holes, so the fat leads do not matter.

**One rule: every band points at PLUS.**

### Step 0. The card comes first

- Cut stiff card, about 13 x 10 cm.
- Print `card_template.pdf` at 100 % (check the 50 mm bar with
  a ruler) and tape it on. No printer: copy it with a pen.
- PLUS is written along the top. MINUS along the bottom.
  Write them BEFORE any diode goes on. The card decides which
  way is up. The diodes follow the card.

### Step E2. Bridge A (picture E2)

1. Do not trim any diode lead.
2. Top diode of leg 1: lay it on its outline, band toward PLUS.
3. Bottom diode of leg 1: below it, band toward PLUS too. Its
   upper lead lies beside the top diode's lower lead for 2 cm.
4. Tape across each body, below the band. The band must stay
   in view.
5. Bend the outer leads to the right, over a screwdriver blade,
   about 6 mm from the body. Top lead of the top diode. Bottom
   lead of the bottom diode.
6. Leg 2 the same, 12 mm to the right. Its bent leads now lie
   against leg 1's.
7. Solder four joints: J1, J2, one on the top row, one on the
   bottom row. Iron at 350 to 380 C, widest tip. Heat both
   leads for 3 seconds, feed solder into the joint, hold still
   until it sets. Shiny and wetting both leads = good.

### Step E3. Bridge B (picture E3)

8. Legs 3 and 4 the same way. Six more joints.
9. The top row of bent leads is now the PLUS rail. The bottom
   row is the MINUS rail. The two ends sticking out to the
   right are the tabs. Leave them bare.
10. **LOOK.** Eight bands. All eight toward PLUS. Take a photo.

### Step E4. Meter check, by position (picture E4)

Nothing else is connected yet. Dial on the diode mark (same
position as the beeper).

| Red probe | Black probe | Expect |
|---|---|---|
| J1 | PLUS rail | 70 to 350 |
| J2 | PLUS rail | 70 to 350 |
| J3 | PLUS rail | 70 to 350 |
| J4 | PLUS rail | 70 to 350 |
| MINUS rail | J1 | 70 to 350 |
| MINUS rail | J2 | 70 to 350 |
| MINUS rail | J3 | 70 to 350 |
| MINUS rail | J4 | 70 to 350 |
| PLUS rail | MINUS rail | lone 1 |

The number is millivolts. All eight should be within about 50
of each other.

- Lone 1 on a row: that diode is backwards, or a joint is open.
  Swap the probes on it. A good number now = backwards.
- 500 to 700 on every row: these are not Schottky. Wrong part.
- 000 and a beep: that diode is shorted, or solder bridges it.
- Never "fix" a row by swapping the probes. The probes follow
  the card. That is the whole point of this check.

### Step E5. The light, then first power (picture E5)

**The light.** Solder two 1 k resistors end to end. Solder the
LED's LONG leg to the free end of the second one. This string
is now one part.

- Resistor end onto the PLUS rail, at its left end.
- LED SHORT leg onto the MINUS rail, at its left end.
- Why two 1 k: one alone would run hot at 24 V. Two share it.
- The light shows the bus is live, and it drains the capacitor
  when you stop.

**First power, through one more 1 k.** With 1 k in the way, at
most 12 mA can flow whatever the supply's knobs say. Nothing
can get warm.

- Glasses on. Output OFF. Supply to 12.0 V.
- Hook one leg of a 1 k round J4. Red clip on its other leg.
  The red clip must touch nothing else.
- Black clip on J3.
- Meter dial on 20 in the V= zone. Red probe on the PLUS tab,
  black probe on the MINUS tab.
- Output ON.

| Row | 1 k hooked on | Black clip on | Expect |
|---|---|---|---|
| 1 | J4 | J3 | 8 to 9 V, LED glows |
| 2 | J3 | J4 | the same |
| 3 | J2 | J1 | the same |
| 4 | J1 | J2 | the same |

Arithmetic: (12 - 0.3 - 1.9) V across 3 k is 3.3 mA. The bus
is 1.9 + 2 k x 3.3 mA = 8.4 V.

- Under 3 V and the LED dark: a fault in that bridge. Output
  OFF. Redo E4 on those two legs. E4 names the diode.
- About 11.5 V and the LED dark: the LED is in backwards.
- **A minus sign: STOP.** With the red probe on the PLUS tab a
  minus sign means the rails are swapped. Go back to E4.
  Do not swap the probes to make it go away.

### Step E6. The capacitor (picture E6)

The stripe with the minus signs marks the MINUS leg. It is the
shorter leg. The longer leg is PLUS.

1. Wait for the LED to go out.
2. Lay C1 on its side to the right of the ladder. Stripe
   toward the MINUS rail.
3. Long leg along the PLUS tab. Solder.
4. The link: cut the pins off three jumper wires, strip 1 cm
   at each end, twist the three together. Solder one end to
   the stripe leg, the other to the MINUS tab.
5. Tape C1 down. **LOOK:** stripe toward MINUS. Photo.

**Then repeat row 1 of E5, still through the 1 k.**

- The reading now CLIMBS for about 3 seconds to the same
  8 to 9 V.
- Output OFF: it falls slowly. About 4 seconds to get under
  3 V. Then it rests near 1.7 to 1.9 V for minutes, LED dark.
  That is normal and harmless.
- It jumps up and drops to zero at once: C1 is not connected.
- It stays under 3 V with the supply on, and it was fine in
  E5: **C1 is backwards**, or the link is on the wrong rail.
  Output OFF. Nothing was harmed at 12 mA. Fit a NEW
  capacitor the right way round. There are 24 spares.

**Then once without the 1 k.**

- Output OFF. Set the limit to 0.10 A (clips together at about
  1 V, output on, turn the current knob, output off). 12.0 V.
- First put the meter on the two supply clips. Note it: ____ V.
- Red clip on J4, black clip on J3. Output ON.
- The limit light may blink once as C1 fills. Then it must
  go out. Supply amps: 0.00 to 0.01.
- Tabs: 0.2 to 0.7 V under what you noted (about 11.5 V).
- **Limit light stays on: output OFF first. Then think.**
  Bus between 1 and 10 V with the light on: suspect C1 first.

### Step E7. Motor wires (picture E7)

After this step the rows of E5 no longer work, because each
coil joins its two J points. So finish E5 and E6 first.

1. LED out. Strip 1 cm of each motor wire. Twist. Tin it.
2. Pair A on J1 and J2. Pair B on J3 and J4. Either way round.
3. Wrap each wire once round its J leads, just below the J
   joint. Solder.
4. Tape the four wires to the edge of the card, so a tug on
   the motor does not reach the joints.
5. Long motor leads: coil the spare. Cutting them is your call.

### Output wires (picture E8)

Two wires, each three jumper wires twisted, about 10 cm.
Pins cut off, 1 cm stripped at each end.

- Warm colours (red, orange, yellow) for PLUS. Solder to the
  PLUS tab.
- Dark colours for MINUS. Solder to the MINUS tab.
- Their free ends go to the kit load first (E8), and to the
  module later (E9).
- Never one jumper alone for power. Never the breadboard.

### Hands-free meter leads

You cannot crank and hold probes. Two ways:

- The bench supply's two clip leads usually have 4 mm plugs
  that fit the meter: red in the middle socket, black in COM.
  Try it. (Not checked on your supply.)
- Or solder one jumper wire to each rail, wind its other end
  round the probe tip and tape it.

Clip on the rails, as in pictures E7, E8 and E10.

### Where it lives

Tape or screw the card to the base, away from the wheel. Bare
metal everywhere: keep screwdrivers and clips off it while you
crank.

---

# Card 4. TESTS

Bench habits, every time:

- **Output OFF. Clip on. Check PLUS and MINUS once more.
  Output ON.**
- Output OFF before you unclip.
- Set the limit with the volts near 1 V, not at 12 V.
- LED out before you solder or change anything.
- Never crank with the supply clipped on.

## E7 test. Crank, nothing plugged in

Meter on the rails. Dial on 20 in the V= zone. Above 19 V the
screen shows the lone 1: go to 200.

**By finger, before the gearset.** One flick of the bare shaft:
expect only 1 to 3 V. The rotor does not hold enough energy to
fill C1 in one go. Flick it 5 to 10 times: the reading climbs
in steps toward 3 to 6 V, and the LED comes on above about 2 V.

**With the gearset.** Metronome app, one turn per beat.

| Turns a minute | Model | Expect | Yours |
|---|---|---|---|
| 30 | 5.0 V | 4.1 to 6.3 | ____ |
| 60 | 10.3 V | 8.7 to 13.0 | ____ |
| 90 | 15.7 V | 13.2 to 19.7 | ____ |

Arithmetic: 0.178 V per turn a minute, minus 0.4 V of diodes.

**Your Ke.** This is the first real check on the model.

    Ke = (your volts at 60 + 0.4) / 33.6 = ______

The model says 0.318.

**Your speed limit with nothing plugged in.** The module dies
above 30 to 32 V.

    volts per turn = your volts at 60 / 60 = ______
    limit = 30 / that number = ______ turns a minute

Model: 170. Rule until you have your own number: **never
faster than 2 turns a second with nothing plugged in.**

**Both coils alive.** Dial on 200 in the V~ zone. This range is
coarse (1 V either way), so it is a yes or no check only.

- Clips on J1 and J2, crank at 60: anything from 5.5 to 10.5.
- Clips on J3 and J4: within 1 V of the first.
- One pair near zero: that coil's wire is off, or broken.

Wrong readings:

- About half the expected volts: the sun gear is slipping on
  the shaft, or the count is off.
- Heavy crank and the bus under 1 V (gearset only): a short.
  Stop. LED out, then look for metal touching both rails.
- The reading jumps about: a cold solder joint. Wiggle each
  joint with the LED lit and watch the meter.

## E8 test. Crank into the kit load

The kit load is the thirty resistors from Today, item 9:
5.7 ohm. Solder the two output wires to its two lumps. Lay it
on the plate.

- **Up to 5.0 V it can stay on as long as you like.**
- **Above 5 V: ten seconds, then a minute's rest. Do not
  touch it.** At 90 turns each 100 ohm part carries 0.65 W,
  2.6 times its rating. Ten seconds is fine. A minute is not.
- Above 11 V on any row: stop at 5 seconds. Your generator is
  stronger than the model. Good news, hot resistors.

| Turns a minute | Model | Expect | Yours | Watts |
|---|---|---|---|---|
| 60 | 5.8 V | 4.6 to 7.6 | ____ | ____ |
| 75 | 7.0 V | 5.6 to 9.2 | ____ | ____ |
| 90 | 8.1 V | 6.5 to 10.7 | ____ | ____ |
| 100 | 8.8 V | 7.0 to 11.7 | ____ | ____ |
| 110 | 9.5 V | 7.5 to 12.6 | ____ | ____ |

    watts = volts x volts / 5.7

The model's 8.1 V at 90 is 11.4 W, at about 17 W from your
hand. That is the full-power proof of everything upstream of
the module, done before the module arrives.

**Both coils pulling.** While someone cranks at 75: V~ 200,
J1 to J2, then J3 to J4. The two should match within 1 V. If
one coil is dead the model says 6.2 V at 90 instead of 8.1 V.

Wrong readings:

- Under the band on every row, both coils matching: Ke is low
  or the gears lose more than guessed. A result, not a fault.
  The pace table below still works: it uses YOUR numbers.
- A diode too hot to touch: it should be barely warm (about
  0.15 W). A cold joint on that diode.

## Your pace for the film

The module is a constant-power load. If the phone asks for
more than the generator has at that pace, the bus does not
settle lower. It collapses. So pick the pace from your own E8
table, before film day.

**Phone watts you can HOLD at a pace = 0.8 x your E8 watts.
Only rows where you read 7.0 V or more count.**

| Your E8 volts | You can hold |
|---|---|
| 7.0 | 6.9 W |
| 7.5 | 7.9 W |
| 8.0 | 9.0 W |
| 8.5 | 10.1 W |
| 9.0 | 11.4 W |
| 9.5 | 12.7 W |
| 10.0 | 14.0 W |

So a phone that takes 10 W needs the slowest pace where you
read **8.5 V** or more. A 12 W phone needs 9.3 V. A 7.5 W
phone needs 7.3 V.

The 0.8 is a safety factor. In the model the true figure runs
from 0.88 to 1.16 across the whole band on every row that
reads 7.0 V or more, so 0.8 is on the safe side everywhere.
Cranking faster than you need costs nothing: the phone takes
the same watts, so your hand does about the same work at a
lighter push.

**An early guess, from E7 alone:**

| Your bus at 60, no load | Pace for 10 W | Pace for 12 W |
|---|---|---|
| 8.7 V | 106 to 120 | 122 to 141 |
| 10.3 V | 84 to 91 | 93 to 106 |
| 13.0 V | 59 to 63 | 63 to 68 |

(The range is the unknown inductance.)

**If the pace you need is past your arm:** start the film at a
higher battery level, where the phone asks for less. Find that
level in the E9 test. I do not know where your phone tapers.

Write it here before film day:

    phone takes ______ W.  Pace: ______ turns a minute.

## E9 test. The module, on the bench supply (picture E9)

The module is wired to the ladder for this. The supply clips go
on the two RAILS. The diodes stop the supply reaching the motor.

1. LED out. Unsolder the output wires from the kit load.
2. Red wire to the pad marked IN+ (or VIN+, or +). Black wire
   to IN- (or GND, or -). Follow each wire with a finger from
   tab to pad. Twice.
3. Output OFF. 12.0 V. Limit 0.30 A. Red clip on the PLUS
   rail, black clip on the MINUS rail. Check. Output ON.
   - Expect: the limit light blinks once, then off. LED lit.
     Supply amps 0.01 to 0.05. (No datasheet for this module.)
   - Limit light stays on: output OFF. Module backwards or dead.
4. Plug in the USB tester, no phone. Expect **5.0 to 5.3 V**.
   Above 5.5 V: stop. Do not connect the phone to this module.
5. Turn the supply slowly from 6 V up to 24 V and back. The
   tester stays at 5.0 to 5.3 V all the way. Never above 30 V.
6. Back to 12.0 V. Limit up to 2.0 A. Plug the phone into the
   tester, at 20 to 60 % battery.

       ______ V x ______ A = ______ W   at ______ % battery

7. **Where it drops out.** With the phone charging, turn the
   supply down slowly from 12 V.

       charging stops at ______ V.  Back up: restarts at ____ V.

   `design.py` assumes 7 V. The label says 6 V.
8. **Rehearse the collapse.** At 9 V, turn the current knob
   down until the supply's volts sag. Watch the phone.

       circle one:   BLINKS      SLOWS

   Slows = the film is safer than the model says. Blinks =
   hold the pace you chose.

What the supply should show while the phone charges:

| Phone takes | at 12 V | at 8 V |
|---|---|---|
| 5 W | 0.47 A | 0.71 A |
| 10 W | 0.95 A | 1.42 A |
| 12 W | 1.14 A | 1.70 A |

    efficiency = (tester V x A) / (supply V x A) = ______

Expect 0.80 to 0.92. `design.py` assumes 0.88. Under 0.75:
the film comes in under the prediction by that much.

- Phone takes only 0.5 or 1 A: not a fault. The phone chose
  that rate from what the port announces.
- Tester shows 9 or 12 V: something asked for fast charge.
  An iPhone does not. Unplug it.

## E10. The film (picture E10)

1. `prediction.json` exists. The locked number: ______ W.
2. Phone at the battery level you chose. Tester in the module.
   Phone in the tester. Meter clipped on the rails. All of it
   plugged in BEFORE you start, so the generator is never
   spun up unloaded.
3. Metronome at your pace. Crank. The icon may blink while
   you get up to speed. That is before the minute starts.
4. Bus steady at 8 V or more: start the 60 seconds.
5. Bus 8 V or more: keep going. Under 7.5 V: speed up now.
6. After: tester ______ V x ______ A = ______ W, written next
   to the locked number.

The model's own answer at 90 turns: about 5.1 V, 2.0 A, 10 W,
bus near 8 V, 17.5 W from your hand.

- Icon blinks: the bus is collapsing. Faster, or the phone
  wants more than you tested. Compare with E9.
- Steady but about 1 A: the phone chose that.
- Tester dark: bus under the module's minimum, or an output
  wire is off.
- Watts fine, then falling: the phone is tapering. Start lower.

---

# Card 5. HAZARDS

1. **Capacitor backwards.** It conducts, heats and can burst.
   Stripe to MINUS. Photo. E5 and E6 find it at 12 mA, where
   it cannot hurt. Never crank an untested board. Glasses.
2. **A diode backwards.** A short through two diodes. The
   crank goes heavy, the bus stays near zero. Nothing burns:
   3 to 5 A through 5 A diodes. E4 finds it before any power.
3. **Too many volts with nothing plugged in.** 0.18 V per turn
   a minute. About 180 turns a minute reaches the module's
   32 V. C1 (50 V) and the diodes (60 V) are out of reach of
   an arm. Rule: never faster than 2 turns a second unloaded.
   No drill in high gear.
4. **The kit load gets hot.** Plate. Ten seconds above 5 V.
   Do not touch it for a minute after.
5. **Fast charge raising the USB volts.** The module can go to
   9 or 12 V if the device asks. The tester is rated to about
   7 V (read its label).
   An iPhone never asks. Never put an Android phone or a
   fast-charge power bank through the tester.
6. **Thin wire carrying amps.** Every power wire is three
   jumpers twisted. No breadboard in the power path, ever.
7. **A short on the bare ladder while cranking.** The generator
   limits itself. The snap comes from C1: nothing at 8 V, a
   spark that pits metal at 24 V. Keep metal off the card.
8. **The icon dropping out.** Harmless to the phone, fatal to
   the film. C1 cannot help: it holds two thousandths of a
   second. The heavy wheel and a steady arm do the smoothing.
   Pick the pace from your own table.
9. **The meter dial on an A position.** The mA ranges use the
   same socket as volts. Turn the dial to 2000u, 20m, 200m or
   10 with the probes on the bus and the meter is nearly a
   short: it blows its fuse. Never use the A zone here. The
   red lead stays in the middle socket. The USB tester gives
   amps.
10. **Supply and crank together.** The generator pushes
    current back into the supply. Unclip before you crank.
11. **The iron.** 350 C. Park it in its stand. Clip thin leads
    with a finger on the off-cut, glasses on.

---

# Appendix A. The numbers

    Ke    = holding torque / (1.414 x rated current)
          = 1.26 / (1.414 x 2.8)     = 0.3182 V per rad/s
    ratio = 91 / 17                  = 5.353
    rad/s = hand turns a minute x 5.353 x 0.10472
    peak volts per turn a minute = 0.3182 x 0.5606 = 0.178
    60 turns a minute = 33.6 rad/s at the motor
    hertz = motor rpm x 50 / 60      (401 Hz at 90 turns)

From `verify.py` (model):

- Short circuit: 3.2 A. With Ke 25 % high: 4.0 A. With L 20 %
  low as well: 4.9 A, 2.7 A in each coil (rated 2.8 A).
- Slowest pace for a 10 W phone, bus at 7 V or more: 84
  nominal, 91 if L is 20 % high, 106 if Ke is 15 % low, 120
  with both, 63 if Ke is 25 % high. For 12 W: 93 nominal, 122
  with Ke 15 % low.
- At 90 turns with Ke 15 % low the generator has 7.8 W dc at
  most, 6.8 W at the phone.
- At 90 turns nominal: 12.9 W dc at a 7.0 V bus, 12.0 W at
  7.7 V, 11.3 W at 8.1 V. `design.py` reads 12.4 W off the
  coarser sweep table.
- One flick of the bare shaft at 2, 3, 4, 8 turns a second
  leaves 1.2, 2.1, 3.0, 5.8 V on C1. Rotor inertia
  (300 g cm2) and friction (0.02 N m) are assumed.
- Each diode at the design point: about 0.4 A average, 0.15 W.

Meter facts, read from the AstroAI manual for this meter
family (AM33D / DT33). That yours is this model is assumed:
check the dial matches picture E1.

- V~ has only 200 and 500. Accuracy 2 % + 10 digits: 1.15 V
  either way at 7.6 V. Good from 45 to 450 Hz.
- V= 20 range: 0.8 % + 2 digits: 0.1 V either way at 10 V.
- Ohm 200 range: 1.5 % + 5 digits: 0.5 ohm either way.
- Ohm ranges: 200, 2000, 20K, 200K, 20M, 200M.
- Diode test shows millivolts. Open shows "1".
- mA shares the middle socket with volts. 10 A has its own.

Diode facts (SB560 data sheet, Diodes Inc.): body up to
9.5 x 5.3 mm, leads 1.2 to 1.3 mm thick and at least 25.4 mm
long, 0.67 V at 5 A, about 0.3 V at 10 mA. Other makers' SR560
curves run lower, which is why the E4 band is wide.

Ladder sizes: legs 12 mm apart. Rails 60 mm apart. Lead
overlap at each J: 20 mm. Each bent lead reaches 19 mm, so it
overlaps its neighbour by 7 mm. C1's legs cannot span 60 mm,
hence the link.

# Appendix B. Plan B: no soldering, screw strips

Same ladder, same pictures, same tests. Screws instead of
solder. It needs a shop trip: two 12-way 15 A screw connector
strips and 1 m of two-core 0.75 mm2 cable. I did not check
prices.

- Cut three 4-way pieces: T (plus rail), M (J1 to J4), B
  (minus rail). Fix them to the card and write the labels
  BEFORE any diode goes in.
- Top diodes from M up to T, bottom diodes from B up to M.
  Every band toward T. Trim leads to 12 mm.
- Join the four ways of T with links, and the four of B. Make
  the links from 35 mm cable off-cuts, 10 mm stripped at each
  end, strands folded double.
- Tighten every screw as each lead goes in. Tug each one.
- A fourth 4-way piece, MOTOR: motor wire in one side, a 6 cm
  cable tail out of the other, into its M way. Fit the tails
  once. All later connecting and disconnecting happens at the
  MOTOR piece, never at M.
- Thin leads (C1, the light): fold double or triple before
  they go under a screw. Solder the light string as in E5.
  Lay C1 flat and tape it.
- Use red and black speaker cable. Do not use a lead that
  still has a mains plug on it.
- Then E4 to E10 exactly as above. Screw heads are the test
  points.

# Appendix C. If you buy the 4.7 ohm 50 W resistor

- It can stay on for a minute. Model at 90 turns: 7.6 V,
  12.3 W (band 6.1 to 10.1 V). Lay it on the tile.
- Rehearsal sitting down, the day the module arrives: supply
  PLUS through the resistor to the PLUS rail. Set the supply
  to 0.17 x the pace you are pretending (15.3 V for 90).
  Phone charging. Turn the volts down until charging stops.
  That is your collapse pace. Between 5 and 8 V on the bus the
  supply behind 4.7 ohm matches the generator model within
  about 10 %. The resistor makes up to 23 W: tile.

# Appendix D. The optional clamp, Z1 (P6KE18A)

Leave it out for the film. It is for a demo where other
people crank.

- It starts to conduct at 17.1 to 18.9 V and holds the bus
  there. It is a one-shot guard. Overheated, it fails as a
  dead short: the crank goes heavy and nothing charges until
  you clip it out. That failure is what saves the module.
- In free air it is good for about 1.5 W, not the 5 W on its
  data sheet (that needs the leads held at 75 C).
- Model, nothing plugged in: up to 1.2 W at 110 turns, 1.1
  to 3.6 W at 120, 5 to 8 W at 135. So with Z1 fitted the
  unloaded limit is about 100 turns a minute.
- Fit it only if your bus at 60 turns, no load, was 11 V or
  less. A stronger generator cooks it at normal pace.
- Solder it across C1's two legs. Band end to the long leg.
  Leave 10 mm of lead each side and stand it clear of the
  card and the tape.

# Appendix E. Other things worth knowing

- **Why the order of the motor wires does not matter.** Each
  wire has its own diode up to PLUS and its own diode up from
  MINUS. Four identical legs. Swap the two wires of a pair, or
  swap the pairs: the bus is the same. A on J1 and J2 is only
  so that the pictures and the coil checks make sense.
- **No gearset yet?** A cordless drill on the motor shaft,
  LOW gear, gentle trigger, motor held in a G-clamp. Stop at
  20 V. A drill in high gear can reach 50 V and kill C1.
- **A car USB charger** (12 to 24 V in, USB-A out) is the same
  kind of converter. If someone at home has one, the E9 steps
  can be practised on it today from the bench supply: tip is
  plus, side spring is minus. Many need 8 to 9 V to start.
- **Build methods I looked at.** Perfboard: the 1.3 mm leads
  do not fit the holes and you have no drill. Screw strip:
  good, but it is a purchase (appendix B). Breadboard: never
  for power, the clips are good for about 1 A. Lead to lead
  on a card: needs only the basket. Chosen.

# What I could not check

- The module: pads, screws or wires on its input, its real
  minimum input, its idle current. E9 measures them.
- What your iPhone draws from this port. E9, step 6.
- Ke and L. E7 and E8 measure what matters.
- That the kit has ten each of 100, 220 and 330 ohm.
- That your meter is the AM33D family.
- That your supply has an output button and clip leads whose
  plugs fit the meter.
- How a reversed capacitor of this brand behaves at 12 mA. The
  "under 3 V" figure is general knowledge. To see it for
  yourself: reverse one spare on purpose behind the 1 k.
- The length of the capacitor's legs and of the motor leads.

---

# Review

Two reviewers criticised the draft. I re-traced each circuit
claim and re-ran each number (`verify.py`) before changing
anything.

**Confirmed and fixed**

- **F1** (a swapped ladder passed every check). Traced: true.
  The old diode check followed each band, so it could not see
  which rail the bands faced. Now: labels go on the card first
  (step 0 and the template), the check is by position (E4),
  and E5 passes only on a plus sign with the red probe on the
  PLUS tab.
- **F2** (first power had one knob between a reversed capacitor
  and 10 A). True. Now: first power through a 1 k resistor
  (8.4 V, 12 mA at most), the bridges before C1 is fitted,
  then C1, then once at 0.10 A. New rule for the limit light.
- **F3, R2-01, R2-02** (the meter is not what the draft
  assumed). I read the manual: confirmed. Diode readings are
  now in millivolts, open is the lone 1, the AC range is a yes
  or no check, Ke comes from the DC reading in E7, coil
  resistance uses the supply and the 2000m range, the body
  check uses 20M.
- **F4, R2-04** (the film can fail on pace with nothing
  wrong). My runs agree: 84, 91, 106, 120 turns a minute for
  10 W across the band. Now there is a pace rule built on his
  own E8 readings, an early lookup from E7, and the pace is
  written down before film day.
- **F5, R2-13** (one module, no spare, no date). True from the
  repo notes. Now a decision with a date and a fallback line.
  I did not re-check the price.
- **F7** (text only). True. Ten pictures, a PDF, a printable
  card template, and this file cut into five cards with short
  lines.
- **R2-03** (one flick cannot give 3 to 8 V). My time-step run
  gives 1.2 to 3.0 V. Fixed, and the false "short" alarm is
  now for the gearset only.
- **R2-05** (the build could not start from owned and basket
  parts). True, and I went further than asked: the soldered
  ladder is now plan A and the screw strip is plan B.
- **R2-06** (no full-power proof without a resistor he does
  not own). True. The thirty-resistor kit load (5.69 ohm) is
  now the load test. My bands: 6.5 to 10.7 V at 90.
- **F6** (motor wire sharing a screw). It cannot be tested
  from here. Plan A removes the cause: the motor wires are
  soldered once and never opened. Plan B uses the MOTOR piece.
- Minor points applied: F8, R2-07, F19, F13 (plan B), F9,
  R2-10 (Z1), F10 (drop-out with the phone on, collapse
  rehearsal compulsory), F11 (the opening now says test loads
  can burn), F12, R2-09 (the light is one soldered string, C1
  taped flat), F14 (20M), F15 (budget line), F16 (bench
  habits), F17 (lock first, relative reading, the slow fall),
  F18 (appendix C), R2-08 (hands-free leads), R2-11 (looser
  bands), R2-12 (Today first, word list, 3 to 5 A).

**Refuted, or changed before use**

- **R2-05, "solder C1 across the two rails".** It does not
  reach. The rails are 60 mm apart and a capacitor's legs are
  about 15 to 20 mm. Hence the three-jumper link. Also two
  untrimmed diodes end to end with a 10 mm overlap would be
  109 mm long: I use a 20 mm overlap.
- **R2-06, test (d2), supply on J1 and J2 with the module
  on.** Not usable once the motor is soldered on: the coil
  (0.9 ohm) sits across those two points. E9 feeds the rails
  instead, and E8 is the full-current proof of the bridges.
- **F3, "use the 2 M or 20 M range".** This meter has no 2 M.
  20M it is.
- **F3 against R2-02 on the diode reading** (near 80 against
  200 to 260). Both are fair readings of two makers' curves.
  I do not know who made the basket parts, so the band is 70
  to 350 and the real test is that all eight agree.
- **F17 against R2-11 on the 12 V reading** (up to 11.8
  against 11.4). Same cause. Now a relative reading: 0.2 to
  0.7 V under the supply clips.
- **R2-01, "the 400 Hz line can go".** Half right. The meter
  is specified to 450 Hz and 90 turns is 401 Hz, but 101
  turns is already past it. The AC check is now at 60 and 75
  only.
- **R2-12, the 35 to 54 band for the 10 ohm test.** The band
  is right. The test is gone: the kit load at 5 V or less
  does the same job with no new bundle.

**Changed beyond what was asked**

- Plan A is soldered, not screwed. Cost: GBP 0 beyond the two
  basket lines. It also removes every loose-screw failure.
- The meter in the cranking pictures is on clip leads.
- The phone is plugged in before spin-up for the film, so the
  generator never runs unloaded on camera.
