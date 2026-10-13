# Superseded: single spur stage, 97:20 at module 2.4

Complete and checked on 2026-09-30 (41 checks, five watertight parts), then
replaced the same day by the planetary layout in `cad/planetary.py` at Paing's
call. Never printed. `charger.py` here expects `design.transmission()` to
return `stages=[(97, 20)]` and will not run against the current design.
It scored 9.2 W at the phone for 14.6 W at the hand.
