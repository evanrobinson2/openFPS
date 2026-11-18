# Generic 1-6x24 LPVO: how to use this asset

A generic 1-6x24 low-power variable optic with a second-focal-plane reticle, in a one-piece cantilever mount. Its
optics are simulated: a thin-lens zoom gives the field of view, the exit pupil and the eye relief at every
magnification, and from those the eye box and the scope shadow. The reticle is an original bullet-drop design whose
marks come from the HK416's ballistics for M855 and Mk 262. The shape is a parametric recipe. No maker's name or logo.
It mounts on `socket_optic` of the HK416 (`assets/hk416/`) with the rifle's sights folded. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) draws the view through the tube pixel by pixel: zoom,
move your eye until the shadow comes in, hold a range mark on a board and fire.

## Status

| Part | State |
|---|---|
| Optics (`optics/`) | Ready. Cams solved for any magnification; pupils, eye relief, field, vignetting, eye box; zero and hold tables; rendering model. Six checks pass (`optics/checks.json`). |
| Reticle | Ready. "Staple BDC": original, second focal plane, true at 6x. Marks agree with the rifle's ballistics runtime to 0.00004 mrad for both loads (`optics/parity.json`). |
| Runtime (`optics/optic-lpvo.js`) | Ready. Carries the same first-order optics as the Python (agreement to 5e-10 mm). `shade()` costs about 0.08 µs per pixel. |
| Geometry (`model/`) | Ready as a recipe. `build.py` is Blender Python: 37 named parts, 8 clips, 5 sockets. It writes `model/work/optic-lpvo-1-6.glb`, a build output that is never committed. Fits the HK416 with no intersections and 4.2 mm over the folded rear sight (`model/fit.json`). Renders of a build are in `renders/`. The shape is generic: see Limits. |

## Run the sample

The modules load JSON with `fetch`, so serve the repository over http:

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/optic-lpvo-1-6/sample/
```

## Use it in your own page

```html
<script src="assets/hk416/ballistics/hk416-ballistics.js"></script>    <!-- window.HK416Ballistics -->
<script src="assets/optic-lpvo-1-6/optics/optic-lpvo.js"></script>     <!-- window.OpticLPVO -->
<script>
const L = OpticLPVO;
await L.load('assets/optic-lpvo-1-6/optics/lpvo.json');
L.mountTo(HK416Ballistics);            // the line of sight is now 80.0 mm over the bore; zero with a distance: fire({zero: 200})

// when the magnification or the light changes
const st = L.state(3.5, { luminance: 2500 });   // st.tanReal (scope camera half field), st.exitPupil, st.eyeRelief, st.reticleScale ...

// per pixel of the eye lens: eye relative to socket_eye in mm (right, up, back); ax, ay = tangents from the optical axis
const s = L.shade(st, { x: 1.5, y: 0, z: 10 }, ax, ay);
// s.inField, s.u, s.v: where to sample the scope pass; s.brightness: field stop x vignetting x eye box (the scope shadow)

L.drawReticle(ctx, cx, cy, pixelsPerApparentMrad, { illumination: 0.6 });   // 2D canvas; or use L.reticle(M).primitives
L.hold('M855', '200m', 450);           // mrad to hold over at 450 m
</script>
```

Full API, physics, sources and checks: [`optics/README.md`](optics/README.md).

## Frame, units and sockets

The HK416's frame: metres and seconds, +Z toward the muzzle, +Y up, +X to the shooter's left. The origin is
`socket_mount`, which sits on the rifle's `socket_optic` (rail top, on the centreline). Put the asset's root there with
no rotation, and play the rifle's `sights_down` clip: the eyepiece passes over the rear sight.

| Socket | Position (m) | What it is |
|---|---|---|
| `socket_mount` | 0, 0, 0 | on the rifle's `socket_optic` |
| `socket_eye` | 0, 0.0432, -0.2074 | design eye point: the 6x exit pupil. The camera for aiming. 6.8 mm behind and 14.5 mm above the rifle's `socket_ads_eye` |
| `socket_ocular_lens` | 0, 0.0432, -0.1070 | the eye lens: where the picture-in-picture is composited |
| `socket_reticle_plane` | 0, 0.0432, -0.0645 | second image plane (thin-lens position) |
| `socket_objective` | 0, 0.0432, 0.1370 | objective lens: the camera for the scope pass |

Eye offsets and field directions in the runtime are as the shooter sees them: right and up (right is -X).

Clips (24 fps; `model/stats.json` has the frame counts): `magnification` (the power ring and its throw lever, half a
turn; frame f is 6^((f-1)/60) power: frame 1 = 1x, 61 = 6x), `elevation_turn` and `windage_turn` (one turn, 100
clicks of 0.1 mrad; frame k+1 is k clicks), `elevation_cap_off`, `windage_cap_off`, `illumination` (frame k+1 is knob
position k, 0 to 10), `dioptre`, `mount_clamp_open`.

Materials `lens_ocular` and `lens_objective` mark the two outer lenses; the picture-in-picture shader runs on
`lens_ocular`.

## Rebuild

| What | Command (from `assets/optic-lpvo-1-6/`) | Needs |
|---|---|---|
| Optics tables, reticle, checks, plots | `python3 optics/sim.py` (about 5 s) | Python 3, numpy, scipy, matplotlib; reads `../hk416/ballistics/ballistics.json` |
| Runtime parity and reticle against the ballistics runtime | `node optics/test.js` | node |
| Geometry | `blender -b --python model/build.py` | Blender 4.x or 5.x. Writes `model/work/` (ignored by git), `model/stats.json`, `model/inventory.json` |
| Renders and fit check | `blender -b model/work/optic-lpvo-1-6.blend --python model/render.py -- --rifle /path/to/hk416.glb` | a local build of the HK416 (`assets/hk416/model/build.py -- --fast`) |

Run them in that order: the geometry reads `optics/lpvo.json`.

## Limits

- **The shape is generic.** No reference image was chosen for this scope, so there was nothing to reconstruct: the
  recipe is a proposal built from class dimensions (257 mm long, 30 mm tube, 24 mm objective) and inferred
  proportions, and it has not had owner review. It is not a model of any product. `model/inventory.json` says where
  each part's dimensions come from.
- The optics are first order (thin lenses). They give pupils, fields and eye relief; they do not give aberrations.
  Distortion and transmission are stated estimates. The thin-lens layout is 182 mm long inside a 257 mm body.
- Eye relief dips to 91 mm between 1.25x and 2x, more than the published scopes of this class move.
- The reticle is true at 6x only (second focal plane). The marks are for the HK416's 14.5 in barrel: 850 m/s M855 and
  770 m/s Mk 262, standard atmosphere.
- The raised iron sights cannot be used with the scope fitted: the eyepiece sits where the rear sight stands up.
- More in [`optics/README.md`](optics/README.md) and [`notes/NOTES.md`](notes/NOTES.md).

## Sources

[`notes/REFERENCES.md`](notes/REFERENCES.md) lists every published figure used and where it was read. No manual,
photograph or drawing is in this repository.
