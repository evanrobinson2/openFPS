# Grenades: game-level effects

What a grenade does to players in the game: damage by distance, blinding and deafening, and a smoke plume that blocks
sight lines. Each is anchored on a published effect figure and filled in with labelled game tuning. Nothing here
models how a device produces the effect. Credit: carpetshark. Simulation by Claude.

| File | What it is |
|---|---|
| `sim.py` | Reference implementation, parameters and Python checks. Writes `effects.json`. |
| `effects.json` | Every parameter with its tag in `sim.py` (PUB / GAME / EST), reference cases, checks. |
| `grenades-effects.js` | Browser and node runtime (`window.GrenadeEffects`). |
| `test.js`, `check.json` | The runtime against the Python reference and the published radii; results committed. |

Rebuild from `assets/grenades/`: `python3 effects/sim.py`, then `node effects/test.js`.

## Frag (and impact): damage against distance

Published (FM 3-23.30 Table A-1): killing radius 5 m, casualty radius 15 m. The game curve passes through those two
points: 100 damage (a full-health player) at 5 m and 25 (a wound) at 15 m, with straight lines in log damage between
anchors, 400 at the centre and zero from 20 m. Only the two radii are published; the damage values, the 20 m
cut-off, `prone` (x0.5 outside 5 m) and `cover` (x0) are game tuning. The manual warns fragments can travel 230 m;
the game ignores that tail.

`GrenadeEffects.fragDamage(r, { prone, cover })` returns `{ damage, lethal, casualty }`.

## Flash: blind and deafen by distance and view angle

Published (Table A-5): a flash of over one million candlepower, a bang of 170 to 180 dB at 5 ft, effects within 9 m.

- **Bang.** L(r) = 175 - 20 log10(r / 1.524 m): the middle of the published window, falling 6 dB per doubling.
  Deafen severity is 1 inside 9 m and falls in a straight line in dB to 0 where the bang reaches 140 dB peak (the
  unprotected impulse-noise limit of OSHA 29 CFR 1910.95 and MIL-STD-1474), 86 m in the open. Hearing protection
  and walls (15 dB, game) subtract. Duration 2 + 8 x severity seconds (game).
- **Flash.** Illuminance E = 1,000,000 cd / r^2, times a view factor: 1 within 30 deg of the view axis, tapering to
  0.05 at 100 deg and behind (game). Blind severity is 1 inside 9 m facing it and falls with log E to 0 where the
  flash adds less than the surroundings: 50 lux at night, 300 indoors, 2000 by day (typical levels, estimates),
  which is 141, 58 and 22 m facing it. Whiteout 0.5 + 4.5 x severity seconds, afterimage 2 + 6 x severity (game).

`flashEffect(r, { viewDeg, ambient, occluded, protectionDb })` or `flashAt(eye, viewDir, flashPos, opts)` return
`{ lux, blind, whiteout_s, afterimage_s, spl_db, deafen, deaf_s }`.

## Smoke: emission, drift, obscuration

Published (Tables B-2, B-4): burn 50 to 90 s, average 60 (coloured); dense white smoke for 105 to 150 s (white).

- **Emission.** A rate that ramps up over 1.5 s, holds, and ramps down over the last 3 s, integrating to 1 over
  the burn. `rate()` drives the hiss and a particle system.
- **Puffs.** Every 0.5 s a Gaussian puff leaves the grenade (wherever it is: it ignites in flight). It drifts with
  the wind, rises about 4 m as it cools, grows as sigma^2 = 0.25^2 + 2 K age with K = 0.15 + 0.10 x wind speed, and
  thins with a 45 s time constant. All game tuning.
- **Obscuration.** Each puff carries a share of a total "extinction area": 2400 m2 for a coloured can, tuned so the
  steady plume has optical depth 4 (2 % of light gets through) across it where it is 2 m wide in a 2 m/s wind;
  7500 m2 for the white can (the manual calls it dense). `transmission(a, b)` = exp(-optical depth) along a sight
  line, in closed form per puff. This is a unitless game quantity, not a mass of anything.

`new SmokePlume(variant, { burn, origin, wind })`, then `setOrigin(pos)`, `step(dt)`, `transmission(a, b)`, `puffs`,
`colour`.

## Checks (`check.json`: 20 Python and 10 JS checks, all passed)

- Frag: exactly lethal at 5 m and exactly at the wound threshold at 15 m; never rising with distance; zero from 20 m.
- Flash: 175 dB at 5 ft is inside 170 to 180; 1,000,000 lux at 1 m; blind and deafen both at full strength at 9 m and
  weaker beyond, for night, indoors and day; blinding falls as the view turns away; deafen ends at the 140 dB radius.
- Smoke: the emission curve integrates to 1; the puffs carry the whole yield; a puff drifts at the wind speed;
  emission stops with the burn; one puff matches the closed form m / (2 pi sigma^2); the plateau plume meets its
  tuning target (optical depth 4 +/- 10 %).
- JS against Python: frag at 11 distances, 216 flash cases, both plumes at 8 or 14 times, to 1e-9 or better.

## Limits

Radial effects with a yes/no line of sight: no partial cover, no reflection of the flash off walls beyond a flat
2 %, no room acoustics. The plume ignores buildings and terrain and assumes a steady wind. Damage numbers, durations
and the smoke's density are game tuning to be balanced; only the radii, levels and times marked published are from
the manual.
