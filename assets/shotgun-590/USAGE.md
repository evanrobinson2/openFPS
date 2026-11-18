# Pump shotgun, 12 gauge (shotgun-590): how to use this asset

A simulation-grade pump-action shotgun in its full-length configuration: 20 in barrel, full-length magazine tube with
the magazine cap, synthetic stock and forend, bead front sight. The mechanism follows the owner's manual; recoil,
ballistics and sound are simulated from published figures; the shape is a parametric recipe traced from a
public-domain profile photo. No maker's names or logos. Credit: carpetshark.

**Sample artifact:** [`sample/index.html`](sample/index.html) loads, fires and pumps the gun in a page: the mechanism
and recoil drawn from the model's own part boxes, pellet holes on a target, a downrange table and synthesised sound.

## Status

| Part | State |
|---|---|
| Action and recoil (`action/`) | Ready. The mechanism passes the manual's function test, loading and unloading procedures; recoil matches the SAAMI momentum balance. Shooter coupling and stroke timing are tuning. |
| Ballistics (`ballistics/`) | Ready. The slug matches the maker's published table within 0.55 % in velocity and 0.04 in in path. The buckshot pattern is calibrated to a published rule of thumb, not to a measured pattern of this load. |
| Sound (`sound/`) | Cinematic mode is the default (designed sound, measured, **not yet heard by the owner**); the physical simulation is mode `'realistic'`. Version 3. Thirty-three synthesised sounds; levels, duration, spectrum and B-duration checked against published 12 gauge measurements; the JavaScript matches the Python to rounding. Not checked by listening. |
| Geometry (`model/`) | Ready as a recipe: 40 named parts, 10 clips, 14 sockets, one level of detail, flat materials. Right-side silhouette against the reference: IoU 0.974. **Open:** the photo cannot satisfy both the published overall length (used) and the published barrel length; widths and internal shapes are inferred. See `notes/NOTES.md`. |

## Run the sample

The modules load JSON with `fetch`, so serve the repository over http:

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/shotgun-590/sample/
```

## Use it in your own page

```html
<script src="assets/shotgun-590/action/shotgun590-action.js"></script>          <!-- window.Shotgun590Action -->
<script src="assets/shotgun-590/ballistics/shotgun590-ballistics.js"></script>  <!-- window.Shotgun590Ballistics -->
<script src="assets/shotgun-590/sound/shotgun590-sound.js"></script>            <!-- window.Shotgun590Sound -->
<script>
const A = Shotgun590Action, B = Shotgun590Ballistics, S = Shotgun590Sound, base = 'assets/shotgun-590/';
await Promise.all([A.load(base + 'action/action.json'), B.load(base + 'ballistics/ballistics.json'), S.load(base + 'sound/params.json')]);

const gun = A.create();                                    // empty, closed, safety on
gun.holdActionLock(true); gun.setSlide(1); gun.loadThroughPort('buck00'); gun.setSlide(0); gun.holdActionLock(false);
for (let i = 0; i < 8; i++) gun.insertShell('buck00');     // nine in all
gun.setSafety(false);

for (const e of gun.pullTrigger()) if (e.type === 'fire') {
  S.play(audioCtx, 'shot_' + e.load + '_shooter', { normalize: true });
  const shot = B.fire({ origin: muzzle, dir: B.aim(lineOfSight, 'bore').dir, load: e.load, rng: B.rng(seed) });
  // each frame: shot.advance(dt); and A.recoil(t, e.load, 'shoulder') -> { pos, pitch, pivot }
}
gun.releaseTrigger();

// a pump: drive the slide from your own input, or play the built-in stroke
const s = A.stroke(t);                                     // { x, speed, forward, done }
for (const e of gun.setSlide(s.x)) { /* 'eject', 'shell_released', 'chambered', 'locked', ... */ }
const p = A.pose(gun.slide, s.forward);                    // slideZ, boltZ, boltLock, elevator for the model's nodes
</script>
```

Full APIs: `action/README.md`, `ballistics/README.md`, `sound/README.md`.

### Sound: cinematic by default

Since 2026-11-17 `S.play()` plays a **designed, game-style sound** (mode `'cinematic'`): for a shot, a crack, a dense
broadband body, a deep falling thump, a long tail that follows the surroundings and a compressed bus; for the pump, a
two-stroke rack with the action's own event times, close and forward in the mix. It is the heaviest gun of the set by
design. The owner's defect report on the simulated shot was "like I punched a bucket": the cinematic shot has no
resonant filter and no decaying tone, and the receiver, barrel and stock modes stay out of it (they remain in the
pump). The physical simulation is unchanged and plays with `{ mode: 'realistic' }`; `render()` and `buffer()` always
return it. The same object as the other guns is also available:

```js
const G = await Shotgun590Sound.build(audioCtx);          // or { mode: 'realistic' }
const chain = await G.chain({ overlay: 'range' });        // 'range' (default), 'room', 'covered', 'field'; null = no tail
chain.output.connect(audioCtx.destination);
chain.fire({ key: 'buck00' });                            // or 'slug'
chain.mech('pump');                                       // the rack on its own; also 'pump_back', 'pump_forward', 'shell_insert', 'dry_fire', ...
chain.fire({ pump: true });                               // the shot, then the rack 0.45 s later
await chain.set({ distance: 50, bearing: 'side' });       // heard 50 m away
await chain.set({ hpd: true });                           // earmuffs
await chain.set({ mode: 'realistic' });                   // the physical simulation
```

With `S.play(ac, name)` the old names choose the cinematic sound: `shot_slug_shooter_room` is the slug in the room,
`shot_buck00_range_front_50m` the buckshot 50 m away, `pump` the rack. `normalize` is ignored in cinematic mode (the mix
is designed); `gain`, `when` and `destination` work as before, and `pump: true` adds the rack.
Design, full API, measurements and limits: [`shared/cinematic-sound/README.md`](../../shared/cinematic-sound/README.md).

### Sound: which shot to play

`shot_<load>_<listener>` (load `buck00` or `slug`, listener `shooter` or `bystander`) is the shot fired in the
default surroundings, an outdoor range with the shooter under a covered firing point, and is what the sample page
plays. The same shot is also built as `..._room` (a plywood-lined training room), `..._covered` (the firing point
and backstop without the woods), `..._field` (open grass, ground reflection only) and
`..._free` (no reflection at all). Use `_free` if your game adds its own reverb: outdoors and dry, a shot is over
within a few milliseconds, and it is the surroundings that give it body. The other sounds (`pump`, `pump_back`,
`pump_forward`, `shell_insert`, `dry_fire`, `safety`, `action_release`) and the API are as before. Six more sounds,
`shot_buck00_range_side_25m` to `shot_buck00_range_front_100m`, are the buckshot shot heard far off on that range.
Default shots are 1.4 s long. `python3 sound/sim.py wav` writes listening WAVs to `sound/audio/`, which git ignores.

## Frame and units

Metres and seconds. +Z towards the muzzle, +Y up, +X to the shooter's left; the origin is on the bore axis at the
receiver's front face. The ejection port is on -X. Time zero of a shot is the trigger break.

Moving nodes: `slide_assembly` and `bolt_slide_group` (translate -Z by the stroke, 97.5 mm), `bolt_group` (follows
after 9.5 mm), `bolt_lock`, `elevator_group`, `trigger`, `safety_button`, `action_lock_lever`, `magazine_follower`,
`magazine_cap_group`, `barrel_assembly`, `trigger_housing_group`. Clips: `pump_stroke`, `pump_back`, `pump_forward`,
`trigger_pull`, `dry_fire`, `safety_to_fire`, `safety_to_safe`, `action_release`, `shell_insert`, `takedown`.
Sockets: `socket_muzzle`, `socket_ads_eye`, `socket_hand_right`, `socket_trigger_finger`, `socket_hand_left` (rides
the forend), `socket_shoulder`, `socket_eject`, `socket_load`, `socket_chamber`, `socket_lifter`,
`socket_magazine_mouth`, `socket_sling_front`, `socket_sling_rear`, `socket_bayonet_lug`. `shell_template` is one
2 3/4 in shell to instance at the chamber, the elevator and the loading port. Positions are in `model/inventory.json`.

## Rebuild

| What | Command (from `assets/shotgun-590/`) | Needs |
|---|---|---|
| Reference trace | `python3 model/tools/trace_reference.py` | numpy, Pillow, the profile photo in `refs-local/` |
| Geometry | `blender -b --python model/build.py` | Blender 4.x or 5.x. Writes `model/masters/shotgun590.glb` and `.blend` and `model/inventory.json`. `model/masters/` is ignored by git, and `tools/check_assets.py` skips a folder of that name, so a local build does not fail the check |
| Model checks | `python3 model/tools/checks.py` | the build |
| Renders and comparison | `blender -b model/masters/shotgun590.blend --python model/tools/render.py`, then `python3 model/tools/compare.py` | the build; the photo in `refs-local/` |
| Action | `python3 action/sim.py`, then `node action/test_action.js` | numpy, matplotlib, node |
| Ballistics | `python3 ballistics/sim.py`, then `node ballistics/test.js` | numpy, matplotlib, node |
| Sound | `python3 sound/sim.py`, then `python3 sound/verify_js.py` | numpy, matplotlib, node (scipy if present) |

Order matters: the simulations read `model/inventory.json`, and the sound reads `action/action.json`.
`model/rebuild.sh` runs the build, the matched render and the comparison in one go.

## Published specifications: where they come from

The overall length (41 in), barrel (20 in), length of pull (13.87 in), weight (7.25 lb) and capacity (9) used here
are those of the maker's model number **50645**. They were **not read from the maker**: mossberg.com returned
HTTP 403 to automated requests on 2026-11-17, so they come from a dealer's copy of the maker's specification sheet
for that model number (`notes/REFERENCES.md`). **They still need confirming against mossberg.com by hand.**

## Limits

- One reference view. Only the right side is measured; widths, the left side's details and all internal shapes are
  inferred (`notes/NOTES.md`, `notes/COMPARE.md`).
- The modelled barrel measures 21.2 in from the breech in a 41.0 in gun; the published barrel is 20 in. Unresolved.
- Flat materials, no textures, no markings, one level of detail. The sample page draws part boxes, not the mesh.
- No modifications, conversions or ways round the safety are modelled, by design.
- Each simulation's README lists its own limits.

## Sources

`notes/REFERENCES.md` cites every source and its licence. `notes/MANUAL_NOTES.md` summarises the facts used from
the owner's manual, by page. `notes/DECOMPOSITION.md` is the reference-to-model record. Neither the manual nor any
page of it is in this repository.
