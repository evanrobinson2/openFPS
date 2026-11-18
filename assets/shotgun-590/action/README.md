# Shotgun 590: action and recoil simulation

The pump mechanism as a state machine that follows the owner's manual, the shot inside the barrel, the recoil it puts
into a shooter, the timing of a pump stroke, and the flight of the ejected hull. It produces data and a small runtime
for a game; it is not game code, and nothing in it describes how to build or alter a firearm. Credit: carpetshark.

Rebuild (a few seconds; Python 3 with numpy and matplotlib; needs `model/inventory.json`):

```
python3 action/sim.py          # writes action.json and plots/
node action/test_action.js     # checks shotgun590-action.js against action.json and the manual's procedures
```

| File | What it is |
|---|---|
| `sim.py` | the simulation; every parameter is in `PARAMS`, `LOADS`, `STANCES` or `HULL` with its basis (published, manual, derived, inferred, guess) and source |
| `action.json` | parameters, the manual facts used, sampled curves, events, recoil tracks, checks |
| `shotgun590-action.js` | the runtime: `create()`, `pose()`, `stroke()`, `recoil()`, `shot()`, `ejectHull()`, `stepHull()` |
| `test_action.js` | 30 Node checks |
| `plots/` | the shot, the recoil, the pump stroke |

## Conventions

Metres, seconds, the model's frame: +Z towards the muzzle, +Y up, +X to the shooter's left, origin on the bore axis at
the receiver's front face. The ejection port is on -X. **Time zero of a shot is the trigger break**; ignition follows
after `lock_time` (6 ms, a guess). Slide position `x` runs from 0 (fully forward, locked) to 1 (fully rearward).

## The mechanism (`create()`)

A gun object holds `slide`, `safety`, `hammerCocked`, `actionLocked`, `chamber`, `lifter` (the elevator), `tube` and
`capacity` (8). Every method returns the events it caused, in order.

| Method | Manual | Events |
|---|---|---|
| `setSafety(on)` | p5: rearward is safe | `safety` |
| `holdActionLock(down)`, `canOpen()` | p6, p9: the lever opens a cocked, closed action | `action_lock_lever` |
| `pullTrigger()`, `releaseTrigger()` | p9, p20 | `blocked` (why: `safety`, `action_open`, `hammer_down`), `hammer_fall`, then `fire` (with the load) or `click` |
| `setSlide(x)`, `pump()` | p9, p10 | rearward: `unlock`, `hammer_cocked`, `eject` (with the shell and whether it was fired), `shell_released`, `rear_stop`; forward: `lift`, `feed`, `chambered`, `locked`; or `blocked` (`action_locked`) |
| `insertShell(load)` | p9: into the magazine, action closed | `shell_inserted`, or `refused` (`magazine_full`, `close_the_action_first`) |
| `loadThroughPort(load)` | p8: first shell onto the elevator, action open | `shell_on_elevator` |
| `releaseFromMagazine()`, `tipOutElevatorShell()` | p10: unloading | `shell_removed` |

The magazine is last in, first out: the shell pushed in last is nearest the receiver and feeds next. A stroke that
stops short of the rear (before 93 % of travel) releases no shell, so the action closes on an empty chamber.

Two rules are **inferred**, because the manual describes neither case: the trigger must be let go and pulled again for
each shot (holding it through the pump does not fire on closing), and the hammer cannot fall while the action is open.

## The physics

1. **The shot.** Base pressure against payload travel: a straight rise to a peak, then adiabatic expansion
   (gamma 1.25). The peak's position is solved so a 30 in barrel gives the load's published speed; the curve is then
   scaled so this gun's 20 in barrel gives the same published speed, because that is the speed the ballistics module
   flies. The charge's mass enters as one third (energy) and one half (momentum), the usual Lagrange
   approximation. After the payload leaves, the gas thrust decays exponentially with the impulse that makes the total
   equal the SAAMI recoil momentum (gas at 1.5 times muzzle velocity).
2. **Recoil.** A planar gun (published 7.25 lb; centre of mass and pitch inertia from the model's part volumes,
   scaled to that weight) against a shoulder: a pad spring and damper into a body mass that is itself sprung and
   damped. Pitch about the butt (shoulder) or the grip (hip), driven by the bore's height above that point. All
   shooter numbers are tuning guesses.
3. **The pump stroke.** Hand-driven: slide position is `stroke x (t / T)^1.6` each way, so the slide is still moving
   when it meets its stop (about 1.1 m/s). Default 0.14 s back, 0.02 s dwell, 0.16 s forward: game tuning. Event
   positions come from the model's geometry: the lost motion, the fired hull's length, the cartridge stop's release
   6 mm before the rear, the shell's place on the elevator.
4. **The hull.** Leaves the port sideways at 1.2 times the slide's speed, a little up and back, with seeded jitter;
   flies with gravity and a little drag; bounces by surface. All tuning.

## Results

| | 00 buck, nine pellets | 1 oz slug |
|---|---|---|
| Muzzle velocity (published, and what the tracks deliver) | 403.9 m/s (1325 ft/s) | 490.7 m/s (1610 ft/s) |
| Peak pressure of the scaled curve | 70.0 MPa | 72.1 MPa |
| Barrel time | 2.37 ms | 2.24 ms |
| Free recoil, unloaded gun (SAAMI) | 4.62 m/s, 35.1 J (25.9 ft lb) | 5.02 m/s, 41.5 J (30.6 ft lb) |
| At the shoulder: back, muzzle rise, peak force | 44 mm, 2.9 degrees, 1.18 kN | 48 mm, 3.1 degrees, 1.28 kN |
| From the hip: back, muzzle rise | 79 mm, 4.0 degrees | 85 mm, 4.4 degrees |
| 20 in barrel against the 30 in test barrel, by this curve | 6 % slower (an estimate, not used) | 7 % slower |

## Checks (`action.json`, `checks`; 16 of 17 pass)

| Check | Result |
|---|---|
| The force on the gun integrates to the SAAMI momentum | 15.20 against 15.19 kg m/s (buck); 16.53 against 16.52 (slug) |
| Peak pressure is under the industry maximum average pressure (79.3 MPa, a recalled figure) | 70.0 and 72.1 MPa |
| A held gun peaks a little under its free recoil speed | 4.03 and 4.14 of 4.62 m/s (buck); 4.43 and 4.53 of 5.02 (slug) |
| The gun settles by 0.8 s | within 0.02 mm and 0.02 degrees |
| The bolt travels further than a fired 3 in hull is long | 82.5 mm against 76.2 mm |
| The events of a stroke are in order | yes |
| The modelled magazine tube holds the published eight shells | **Fails** since the ruler became the 20 in barrel (`notes/NOTES.md`, change request 1): 0.500 m inside, 45 mm allowed for follower and spring, seven 59 mm shells fit. The mechanism still holds the published eight |
| The muzzle velocity is the published one | a calibration, shown for completeness |
| `test_action.js` | 30 of 30: the manual's function test (p20), action lock (p6, p9), loading to nine and firing them in the right order (p8, p9), the events of one pump, unloading (p10), poses, stroke timing, pressure and recoil playback, seeded hulls against `sim.py` within 0.007 mm |

## Limits

- The pressure curve is a fitted shape, not interior ballistics from powder data: charge and wad masses, the peak
  pressure, the start pressure and the lock time are guesses. Only the muzzle velocity and the recoil momentum are
  tied to published figures.
- The shooter model is tuning. It has not been compared with a measured recoil trace.
- The force needed to work the pump is not modelled, nor is a shell's motion between the events.
- 3 in shells are not among the loads; set `capacity` to 7 if you add one (manual p8).
- The mechanism's internal dimensions are inferred (`notes/NOTES.md`). The events are right in order and in what the
  manual says causes them; their exact slide positions are estimates.
