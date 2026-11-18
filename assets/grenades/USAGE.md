# Grenades: how to use this asset

Four hand grenades for a game, as simulations: `frag`, `flash`, `smoke` (red, yellow, green, violet, and
`smoke-white`) and `impact` (game-only). Flight, bounce, fuse, effects and sound are simulated from the published
figures in US Army FM 3-23.30 (2009); the shapes are parametric recipes measured from that manual's figures.
Credit: carpetshark.

**Content boundary.** This is what a player sees, hears and feels: exterior shape, published weight, delay,
throwing distance and effect figures, game-level effects, synthesised sound. Nothing about how a real device works
inside is modelled or described; every interior is a solid placeholder.

**Sample artifact:** [`sample/index.html`](sample/index.html) pulls the pin and throws: the flight with bounces, the
fuse (and cooking it), the frag's radii, the flash's blind and deafen, a smoke plume on the wind, every sound
synthesised, and a table of published figures against the simulation.

## Status

| Part | State |
|---|---|
| Throw (`throw/`) | Ready. Drag flight calibrated to the published average distances; bounce and roll on seven grounds; delay and burn times sampled inside the published windows; cook-off; the game-only impact rule. 57 checks pass. |
| Effects (`effects/`) | Ready. Frag damage on the published 5 m and 15 m radii; flash on the published candlepower, 170 to 180 dB at 5 ft and 9 m; smoke plume and sight-line obscuration. 30 checks pass. Damage, durations and smoke density are game tuning. |
| Sound (`sound/`) | Ready. Synthesised in the browser from `params.json`; the JS port matches the Python to -312 dB. Not yet checked by listening. |
| Geometry (`model/`) | Ready as a recipe. `build.py` is Blender Python: 8 variants, 11 to 16 named parts each, 3 or 4 clips, 5 to 9 sockets, two LODs. It writes `refs-local/build/grenade_<variant>.glb`, build outputs that are never committed. Matched renders against the manual's figures are in `renders/`, the numbers in `notes/COMPARISON.md`. Not yet reviewed by the owner. The sample page doesn't draw the model. |

Two things need the owner's decision before the shapes are final (details in `notes/NOTES.md`): the coloured smoke
can's paint (the manual's table and its photo disagree) and the flash's hole count (table 12, photo 18).

## Run the sample

The modules load JSON with `fetch`, so serve the repo over http:

```
cd openFPS
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/grenades/sample/
```

## Use it in your own page

```html
<script src="assets/grenades/throw/grenades-throw.js"></script>      <!-- window.GrenadeThrow -->
<script src="assets/grenades/effects/grenades-effects.js"></script>  <!-- window.GrenadeEffects -->
<script type="module">
import GrenadeSound from './assets/grenades/sound/grenades-sound.js';
await GrenadeThrow.load('assets/grenades/throw/throw.json');
await GrenadeEffects.load('assets/grenades/effects/effects.json');
const S = await GrenadeSound.build(new AudioContext({ sampleRate: 48000 }));

const g = new GrenadeThrow.Grenade('frag', { seed: 1, surface: 'packed_dirt' });
g.pullPin(); S.play('pin_pull');
g.throwFrom(hand, GrenadeThrow.releaseVelocity('frag', aimDir, 1.0)); S.play(S.leverRelease('frag'));
// every frame:
for (const e of g.update(dt)) {
  if (e.type === 'bounce') S.play(S.bounce('frag', e.surface, e.normalSpeed), { distance: dist(e.pos) });
  if (e.type === 'function') {                                   // kind: 'detonate' or 'ignite'
    S.play('detonation_frag', { distance: dist(e.pos) });
    const hit = GrenadeEffects.fragDamage(dist(e.pos), { cover: !lineOfSight(e.pos) });   // { damage, lethal, casualty }
  }
}
// flash:  GrenadeEffects.flashAt(eye, viewDir, e.pos, { ambient: 'indoor' })  -> { blind, whiteout_s, deafen, deaf_s, ... }
// smoke:  const plume = new GrenadeEffects.SmokePlume('smoke-red', { burn: e.burn, origin: e.pos, wind });
//         plume.setOrigin(g.pos); plume.step(dt); plume.transmission(eyeA, eyeB);
</script>
```

Full APIs: `throw/README.md`, `effects/README.md`, `sound/README.md`.

## Variants and their published figures

| Variant | Weight | Delay | Average throw | Effect figures | Source |
|---|---|---|---|---|---|
| `frag` | 14 oz | 4 to 5.5 s | 35 m | killing radius 5 m, casualty radius 15 m | FM Table A-1 |
| `flash` | 13.3 oz | 1 to 2.3 s | not published (35 m used) | over 1,000,000 candlepower; 170 to 180 dB at 5 ft; effects within 9 m | FM Table A-5 |
| `smoke-red`, `-yellow`, `-green`, `-violet` | 19 oz | 0.7 to 2.0 s | 35 m | burns 50 to 90 s, average 60 | FM Table B-2 |
| `smoke-white` | 24 oz | 0.7 to 2.0 s | 30 m | dense white smoke for 105 to 150 s | FM Table B-4 |
| `impact` | as frag | none | as frag | as frag | **Game-only.** Functions on its first hard contact after 0.35 s. Every number is game tuning; it imitates no real fuze |

`data/grenades.json` holds these with their sources.

## Frame and units

Metres and seconds. Simulations: +Y up, the ground is y = 0. Model (glTF): +Y up along the grenade's axis, the safety
lever on +X, the pull ring towards +Z, origin at the body centre. Sockets: `socket_grip`, `socket_effect`,
`socket_pin_ring`, `socket_thumb`, `socket_lever_hinge`, and `socket_emit_1..4` on the smoke cans; positions are in
`model/work/stats_grenade_<variant>.json`. Clips: `pin_pull`, `lever_squeeze`, `lever_release`, and
`safety_clip_off` on the frag and impact. Hierarchy: `grenade_<variant>` > `body_group` (body, markings) and `fuze`
(`fuze_body`, `hinge_lug`, `lever`, `safety_pin` > `pull_ring`, `safety_clip`).

## Rebuild

| What | Command (from `assets/grenades/`) | Needs |
|---|---|---|
| Throw | `python3 throw/sim.py`, then `node throw/test.js` | Python 3, node |
| Effects | `python3 effects/sim.py`, then `node effects/test.js` | Python 3, node |
| Sound | `python3 sound/sim.py`, then `python3 sound/verify_js.py` | Python 3, node; the model's stats files |
| Geometry | `blender -b --python model/build.py` (options: `--only frag,flash`, `--lod 0`, `--m18-livery figure`, `--flash-holes 12`) | Blender 4.x or 5.x. Writes `refs-local/build/*.glb` (ignored by git and by `tools/check_assets.py`); part, socket and clip lists go to `model/work/stats_*.json` |
| Matched renders and numbers | `model/rebuild.sh` | Blender, Pillow, numpy, scipy, and local copies of the figures in `refs-local/` |

## Limits

- Exterior only; flat materials, no baked textures. Markings are placeholder words and plain bars: no designations,
  lot numbers or maker's names.
- The figures are small greyscale photos: outlines are matched to a few millimetres, colours come from the tables'
  words, and the hidden sides are inferred. `notes/NOTES.md` lists every inference, omission and correction.
- Release angle and height, drag coefficients, ground and contact numbers are estimates; damage, durations, smoke
  density, mechanical sound levels and the playback mapping are game tuning. Each is labelled where it is defined.
- No spin in flight, no terrain, no room acoustics, no partial cover.

## Sources

`notes/REFERENCES.md` cites the manual's figures and tables. `notes/DECOMPOSITION.md` indexes what was read from each
figure and the grammar derived from it. `notes/COMPARISON.md` gives the matched comparison. The manual and its
figures are not in this repository.
