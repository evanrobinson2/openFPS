# Generic 2 MOA red-dot sight: how to use this asset

A generic 30 mm class tube red-dot sight on a rail mount. Its optics are simulated: the dot is the image of an LED
in a ray-traced collimator, so it has real parallax; its brightness is a luminance that either holds against the scene
or washes out. The shape is a parametric recipe. No maker's name or logo. It mounts on `socket_optic` of the HK416
(`assets/hk416/`). Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) draws the sight picture: move your eye and watch the dot
leave the target, change the light and the brightness switch, fire and see where the parallax puts the shot.

## Status

| Part | State |
|---|---|
| Optics (`optics/`) | Ready. Exact ray trace of the collimator, parallax map, dot size and blur, window tint, brightness against scene luminance, zero tables for the HK416. Nine checks pass (`optics/checks.json`). |
| Runtime (`optics/optic-red-dot.js`) | Ready. Carries the same ray trace (agrees with the Python to 3e-13 rad) and a fast polynomial (within 0.03 MOA of it). Zero tables agree with the rifle's ballistics runtime to 0.08 mm (`optics/parity.json`). |
| Geometry (`model/`) | Ready as a recipe. `build.py` is Blender Python: 27 named parts, 6 clips, 5 sockets. It writes `model/work/optic-red-dot.glb`, a build output that is never committed. Fits the HK416 with no intersections (`model/fit.json`). Renders of a build are in `renders/`. The shape is generic: see Limits. |

## Run the sample

The modules load JSON with `fetch`, so serve the repository over http:

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/optic-red-dot/sample/
```

## Use it in your own page

```html
<script src="assets/hk416/ballistics/hk416-ballistics.js"></script>   <!-- window.HK416Ballistics -->
<script src="assets/optic-red-dot/optics/optic-red-dot.js"></script>  <!-- window.OpticRedDot -->
<script>
const R = OpticRedDot;
await R.load('assets/optic-red-dot/optics/reddot.json');
R.mountTo(HK416Ballistics);            // the line of sight is now 75.8 mm over the bore; zero with a distance: fire({zero: 50})

// every frame: eye relative to socket_eye in mm (right, up, back)
const P = R.sightPicture({ x: 3, y: -1, z: 0 });
// P.front, P.rear {x, y, r}: the two apertures as circles; P.dot {x, y, r}: the dot; all tangents from the optical axis
// P.visible: false when the eye can no longer see the dot through both apertures; P.tint: multiply the scene by it

const e = R.parallax(3, -1, 25);       // eye 3 mm right, 1 mm low, target at 25 m
// e.moa: how far the dot is off the aiming point; e.poiShiftMm: where the shot goes if you steer the dot back on
const d = R.dot(8, 5000);              // switch position 8 against 5,000 cd/m2 (sunlit grass)
// d.luminance, d.contrast, d.look ('washed_out' | 'crisp' | 'bright' | 'blooming' ...), d.apparentMoa, d.halo
R.recommend(5000);                     // the lowest position that gives a crisp dot in this light
</script>
```

Full API, physics, sources and checks: [`optics/README.md`](optics/README.md).

## Frame, units and sockets

The HK416's frame: metres and seconds, +Z toward the muzzle, +Y up, +X to the shooter's left. The origin is
`socket_mount`, which sits on the rifle's `socket_optic` (rail top, on the centreline). Put the asset's root there with
no rotation.

| Socket | Position (m) | What it is |
|---|---|---|
| `socket_mount` | 0, 0, 0 | on the rifle's `socket_optic` |
| `socket_eye` | 0, 0.0390, -0.2006 | design eye point: the camera for aiming. It is on the optical axis, at the same distance along the rifle as `socket_ads_eye`, 10.3 mm higher |
| `socket_rear_window` | 0, 0.0390, -0.0420 | rear window |
| `socket_objective` | 0, 0.0390, 0.0560 | front window (the collimating doublet) |
| `socket_emitter` | -0.0095, 0.0295, -0.0360 | the LED, at 4:30 on the bore wall as the shooter sees it |

Eye offsets and angles in the runtime are as the shooter sees them: right and up (right is -X).

Clips (24 fps; `model/stats.json` has the frame counts): `brightness` (frame k+1 is switch position k, 30° each),
`elevation_adjust` and `windage_adjust` (one turn, 24 clicks of 0.5 MOA; frame k+1 is k clicks),
`elevation_cap_off`, `windage_cap_off`, `mount_clamp_open`.

Materials `lens_front` and `lens_rear` mark the two windows: that is where a renderer tints the scene and draws the dot.

## Rebuild

| What | Command (from `assets/optic-red-dot/`) | Needs |
|---|---|---|
| Optics tables, checks, plots | `python3 optics/sim.py` (about 30 s) | Python 3, numpy, scipy, matplotlib; reads `../hk416/ballistics/ballistics.json` |
| Runtime parity | `node optics/test.js` | node |
| Geometry | `blender -b --python model/build.py` | Blender 4.x or 5.x. Writes `model/work/` (ignored by git), `model/stats.json`, `model/inventory.json` |
| Renders and fit check | `blender -b model/work/optic-red-dot.blend --python model/render.py -- --rifle /path/to/hk416.glb` | a local build of the HK416 (`assets/hk416/model/build.py -- --fast`) |

Run them in that order: the geometry reads `optics/reddot.json`.

## Limits

- **The shape is generic.** No reference image was chosen for this sight, so there was nothing to reconstruct: the
  recipe is a proposal built from class dimensions and from the simulation's own numbers, and it has not had owner
  review. It is not a model of any product. `model/inventory.json` says where each part's dimensions come from.
- The collimator is my own design solved to the class's external figures, not any maker's prescription. Its parallax
  falls below the averages one published study measured on three real sights (see the README): treat it as a good
  sight of its class, not as a particular one.
- Dot luminances per switch position are inferred: makers publish the number of positions, not luminances.
- The eye is a pinhole plus a pupil-size formula: no astigmatism (which smears a real dot for many shooters), no glare.
- The sample page draws the tube's two apertures, not the whole model.
- More in [`optics/README.md`](optics/README.md) and [`notes/NOTES.md`](notes/NOTES.md).

## Sources

[`notes/REFERENCES.md`](notes/REFERENCES.md) lists every published figure used and where it was read. No manual,
photograph or drawing is in this repository.
