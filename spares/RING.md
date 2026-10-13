# Replacement ring: two halves that clip together (no screws, no glue)

Print ONLY the four files in `cad/stl/spares/` numbered 1 to 4. Do NOT print `ring_rear_half`, `ring_front_half`
(in `cad/stl/`) or `plate2a` / `plate2b`: those are the older version in PRINT.md and need screws.

    WHAT TO DO
    1. Print plate 1 (about half an hour). While it prints, do picture ring_1.png: cut the old ring off.
    2. Do picture ring_0.png: the test piece. If any part of it fails, STOP and say so. Print nothing else.
    3. Print plates 2, 3 and 4.
    4. Follow ring_2.png to ring_6.png (on a phone: phone/ring_2_phone.png ...).
    5. Then carry on with the main guide at Step 5 (Step 4 first if the spider is not ready).

You need: side cutters (scissors will NOT cut the old ring), any glasses, a cloth, one book of any size, and one BIG
flat thing: an A4 hardback or bigger, a chopping board or a baking tray. Nothing to buy. If the cutters will not
bite the old ring, stop and say so (a junior hacksaw blade, about GBP 2, is the fallback, and that is your call).

| plate | file in `cad/stl/spares/` | what | note |
|---|---|---|---|
| 1 | `1_ring_clip_coupon` | test piece: one lug pair with 6 teeth of each half, and one clip | 3 small bodies, 10 g |
| 2 | `2_ring_rear_half_clip` | rear half, 7.6 mm tall | as exported: back on the bed, already turned to fit |
| 3 | `3_ring_front_half_clip` | front half, skirt and dogs | as exported: split face on the bed |
| 4 | `4_ring_clips` | 9 clips (7 + 2 spare) and the planet key | clips lie on their side: do not stand them up |

Print settings: exactly PRINT.md's table (0.2 mm layers, 4 walls, 25 % gyroid, supports OFF, no brim, elephant foot
compensation 0.2, avoid crossing walls on, seam random). ONE filament for all four plates: the one your gears are in.
Check the AMS slot does not say "Support". Plate 4 only: seam position "Back", then look at the preview: the seam
line must be on the OUTSIDE of each clip's thick arm, never inside the C. If it is inside, say so.

Test piece (plate 1), all in ring_0.png:
- The taller piece sits on the shorter with its lug between the two ears. No gap, no rock.
- The clip, thin arm underneath in its slot, pushes on with a firm thumb and CLICKS.
- Pull the two pieces apart by hand: they hold. Lay it on the table: the clip does not touch the table.
- Twist it off with a scissor blade or the closed tips of the side cutters in the gap behind it. Never a sharp
  knife. Click it on again. White marks are fine if it still clicks; a crack is a fail.
- Press one of your own planets into the teeth: it goes fully in and rocks without sticking.
- If you have callipers: slot under the lug 2.9 to 3.3 mm deep, clip mouth 9.0 to 9.2 mm. Outside that, say so.
- PLA clip cracked? Print plate 4 in PETG and test one of those clips on the same test piece.

Looking after it: build it over a towel. After any knock, push every clip again and swap a marked one for a spare
(keep both spares). The clips pass a finger's width (16 mm) above the table: keep fingers and the phone lead out
from under the ring. It charges cranked either way; clockwise, seen from the front, is the smoother way.

Not PRINT.md's order: a planet cannot be lowered in beside the sun (herringbone), so the gears are laid flat first.
Seven lugs, not six: 7 divides the 91 teeth. Not tested in plastic. Rebuild: `cad/ring_spare.py`, then `cad/ring_spare_pictures.py`.
