# Generic QD 5.56 mm suppressor: how to use this asset

A simulation-grade quick-detach suppressor for the HK416 D14.5RS (`assets/hk416/`). It is a generic can: no maker,
no logo, no product measured. The shape is a parametric recipe of named parts; the gas flow through the baffle stack
is simulated from the rifle's own interior ballistics, and the sound, the back-pressure on the action, the can's
heating and the flash scales all come out of that one simulation. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) fires the rifle with and without the can: the chamber
pressures in a moving section, the synthesised sound at three listeners, the carrier with and without back-pressure,
can heating through a string, and the two QD clips.

## Status

| Part | State |
|---|---|
| Geometry (`model/`) | Ready as a recipe. `geom.py` holds every dimension; `build.py` is Blender Python: 17 named meshes, 3 sockets, clips `qd_attach` and `qd_detach`. It writes `model/build/suppressor-qd-556.glb`, a build output that is never committed. Renders of a build are in `renders/`. Generic design, not yet reviewed by the owner. |
| Gas dynamics (`sim/`) | Ready. Blast chamber, six baffles, end cap; driven by the HK416 bore state at bullet exit. |
| Sound | Ready as a patch for `assets/hk416/sound/params.json`. Two parameters are calibrated to published reductions (22.5 dB at 1 m, 20.5 dB at the ear). The supersonic crack is untouched. Not validated by listening. |
| Back-pressure | Ready as an input and an overlay for the HK416 action: carrier 6 % faster at ejection, rate 800 to 825 rpm. Predicted, no HK416 measurement to check against. |
| Heat | Ready. 1970 J into a cold can per shot (6.5 K); strings with still-air cooling. |
| Flash | Interface only. `assets/hk416/flash/` was not on this branch, so the scales are documented and untested against it. |
| JS runtime | Ready. `sim/suppressor-qd-556.js` is bit-identical to the Python on 802 checked numbers. |

## Run the sample

The modules load JSON with `fetch`, so serve the repo over http:

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/suppressor-qd-556/sample/
```

## Use it in your own page

```html
<script src="assets/hk416/action/hk416-action.js"></script>               <!-- window.HK416Action -->
<script src="assets/suppressor-qd-556/sim/suppressor-qd-556.js"></script> <!-- window.SuppressorQD556 -->
<script type="module">
import HK416Sound from './assets/hk416/sound/hk416-sound.js';
const Q = window.SuppressorQD556;
await Q.load('assets/suppressor-qd-556/sim/suppressor.json');

// sound: patch the HK416 tables, then use the HK416 sound module as usual
const hkParams = await (await fetch('assets/hk416/sound/params.json')).json();
const ac = new AudioContext({ sampleRate: 48000 });
const S = await HK416Sound.build(ac, { params: Q.soundParams(hkParams, 'subsequent') });   // or 'first_round', 'hot'
const buf = S.shot('single');                    // normalised; S.info(buf).peak_db_spl is the true level

// action: the suppressed cycle, rate and recoil
const hkAction = await (await fetch('assets/hk416/action/action.json')).json();
HK416Action.use(Q.actionData(hkAction));         // HK416Action.sample(t) now plays the suppressed rifle

// heat and the state of the can for the next shot
const h = Q.heatString(shotTimesSoFar);          // [{ T_before_K, o2, heat_J, T_after_K }]
const last = h[h.length - 1];
const shot = Q.runShot({ t_wall: last.T_before_K, o2: last.o2 });        // the gas model, live
const live = await HK416Sound.build(ac, { params: Q.soundParams(hkParams, Q.acoustics(shot)) });

// flash: scale the bare flash phase by phase, move it to socket_exit
const f = Q.flashInput('subsequent');            // f.scale.primary, f.scale.secondary, f.exit_offset_m, f.delay_s
</script>
```

With the HK416's default cinematic sound the same patched tables switch the can on and off on a chain:
`await chain.set({ suppressor: Q.soundParams(hkParams, 'subsequent') })`, `null` to take it off (crack, thump and tail
change, the bullet's crack stays: `shared/cinematic-sound/README.md`). The example above builds a whole suppressed
rifle and works in both modes; add `mode: 'realistic'` to `build()` for the physical levels this page talks about.

Full API, physics, sources, checks and limits: [`sim/README.md`](sim/README.md).

## Fitting it to the rifle

Parent the `suppressor` node to the rifle's `socket_muzzle` with an identity transform. `socket_mount` is the
asset's origin and sits on that socket; `socket_exit` (0.122 m down-range) is the new muzzle for the bullet, the
flash, the smoke and the sound; `socket_thermal` is the top of the tube over the blast baffle, the hottest skin.

The can slides over the rifle's flash hider (0.4 mm clearance) and seats on its front shoulder. Turning the collar
60° drives three jaws 1.3 mm inward onto the jam ring behind the hider, so the hider cannot pull out. The rest pose
is attached and locked. `qd_attach` (1.5 s at 24 fps) starts with the can 75 mm down-range and open; `qd_detach` is
the reverse. With the can fitted the rifle is 122 mm longer and 0.612 kg heavier.

| Node | Children |
|---|---|
| `suppressor` (root; moved by the clips) | `can_body`, `lock_collar`, `jaw_1` to `jaw_3`, the three sockets |
| `can_body` | `mount_body`, `tube`, `blast_sleeve`, `blast_baffle`, `baffle_2` to `baffle_6`, `end_cap`, `marking_panel`, `index_panel` |
| `lock_collar` (turns about the bore) | `collar_index` |

Parts, masses, chamber volumes, sockets, clips and fit clearances are in `model/inventory.json`.

## Frame and units

Metres and seconds. +Z down-range, +Y up, +X to the shooter's left; the origin is `socket_mount`. Time zero of a
shot in the simulation is the bullet base leaving the barrel crown, 9.487 ms after the trigger break on the
`HK416Action` clock (`SuppressorQD556.exitAfterSear`).

## Rebuild

| What | Command (from `assets/suppressor-qd-556/`) | Needs |
|---|---|---|
| Dimensions, volumes, masses | `python3 model/geom.py` (writes `model/inventory.json`) | Python 3 |
| Geometry | `blender -b --python model/build.py` (add `-- --fast` to skip the renders) | Blender 4.x or 5.x. Writes `model/build/*.glb` (ignored by git), `model/build_stats.json` and `renders/`. The on-rifle renders need a local build of `assets/hk416/model` |
| Simulation | `python3 sim/sim.py` | numpy, scipy, matplotlib; `assets/hk416/action` and `assets/hk416/sound` |
| JS parity and module checks | `node sim/test.js` (writes `sim/parity.json`) | node 22 or later |

## Limits

- Generic by brief: there is no reference image and nothing was measured from a real can. Dimensions are class
  figures and my own layout. The can is on the heavy side of its class (612 g).
- A real A2-pattern flash hider is not a suppressor mount; the collar-and-jaw lock here is a plausible mechanism,
  not a copy of one. Threads, the cam inside the collar, the detent and welds are not modelled.
- The gas model is lumped (no waves). The two headline sound reductions are calibrated, not predicted.
- No ejection-port or gas-vent sound source: levels at the shooter's ear are a lower bound.
- The can is one temperature; no glow, mirage or point-of-impact shift is computed.
- The flash coupling is an interface, not a tested link.
- Nothing has been validated by listening or against a measurement of this rifle. See `sim/README.md` for the rest.

## Sources

`notes/REFERENCES.md` lists every source and what was taken from it. `notes/NOTES.md` records the design decisions,
inferences and the change log.
