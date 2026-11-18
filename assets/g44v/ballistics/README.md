# G44 V: exterior ballistics

Point-mass trajectories for three CCI .22 LR loads fired from the 102 mm barrel. Credit: carpetshark.

```
python3 sim.py     # ballistics.json, plots/, and the DATA block of g44v-ballistics.js (run ../action/sim.py first)
node test.js       # checks g44v-ballistics.js against ballistics.json, writes parity.json
```

## The model

- G1 drag function (the standard table) with each load's published G1 coefficient; ICAO standard sea-level air; RK4 at 1 ms.
- Muzzle velocities are the action simulation's 102 mm barrel figures (271, 300 and 186 m/s), not the box figures.
- Line of sight 15.9 mm above the bore, from the model's sights. Default zero 25 m (inferred: the manual gives none and the rear sight is adjustable).
- Dispersion: 3 to 4 MOA standard deviation per axis for pistol and load together. Inferred, not measured.
- Twist 1 in 16 in (the SAAMI standard; this model's twist is not published); Miller stability 1.2 to 1.4. Spin drift is not modelled.

## API

```js
G44VBallistics.poi('cci_standard_velocity', 25, 50)   // { y, x, v, tof, energy, mach }: metres from the line of sight, 25 m zero, at 50 m
const shot = G44VBallistics.fire({ origin, dir, up, ammo, zero, rng });   // origin on the line of sight; the bullet starts at the muzzle
shot.advance(dt, targets)                              // [hit] when a target is struck: { target, point, t, speed, energy, momentum, angleDeg, mach }
shot.trace(targets, maxT)                              // first hit or null
G44VBallistics.configure({ gravity, wind, rho, sound })
```

Targets are discs or planes: `{ name, point, normal, radius }`.

## Check against published data

The model flown from CCI's own test-barrel velocity and coefficient, against CCI's downrange table (100 yd zero, sights 1.5 in above the bore):

| Load | Velocity at 50, 75, 100 yd: model minus CCI | Path at 25, 50, 75 yd: model minus CCI |
|---|---|---|
| Standard Velocity (1070 fps, BC 0.120) | -2.7, -2.5, -3.1 fps | +0.01, +0.02, +0.05 in |
| Mini-Mag (1235 fps, BC 0.130) | -2.9, -3.4, -4.5 fps | +0.02, 0.00, +0.06 in |
| Quiet-22 (710 fps, BC 0.120) | -1.1, -0.7, -1.8 fps | -0.05, -0.05, -0.04 in |

CCI prints velocity to 1 fps and path to 0.1 in. JS against Python: 9 cases, difference 0 (`parity.json`).

From the pistol, 25 m zero: at 50 m the bullet is 73 mm low (Standard Velocity), 58 mm (Mini-Mag), 173 mm (Quiet-22). All three loads are subsonic from this barrel. Maximum range 1.0 to 1.5 km, inside the 1.5 mile warning printed on .22 LR boxes.

## Limits

- The pistol velocities come from a simulation, not a chronograph.
- A single G1 coefficient per load, as published; no spin drift, no Coriolis, no terminal effects (targets only report what struck them).
- Dispersion and zero are inferred.
