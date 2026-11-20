# Tactical helmets: how to use this asset

A parametric helmet generator. One Blender Python recipe builds a ballistic shell from numbers, then fits the kit
onto its surface: rubber edge band, side accessory rails, a night-vision shroud with its bungees, hook-and-loop
panels, a counterweight pouch, an inner pad set, a four-point chinstrap, a rail-mounted headset or a fabric cover.
Three presets ship, and a random mode draws as many new helmets as you want from the same ranges. Credit: carpetshark.

| Preset | What it is | Built from |
|---|---|---|
| `helmet_us_highcut` | US high-cut ballistic helmet: Ranger-green paint, rails, one-hole metal shroud, bungees, loop panels, IR marker, 7-pad liner, 4-point chinstrap | US Army ACH manual dimensions (size L), ACH hardware study |
| `helmet_pmc_highcut` | Contractor high-cut: tan paint, black rails, three-hole polymer shroud, rail-mounted headset with boom mic, counterweight pouch | FAST XP data sheet coverage, weight and thickness |
| `helmet_east_midcut` | Eastern European mid-cut under a digital-camo cover, front NVG mount plate | 6B47 published weight |

**Sample artifact:** [`sample/index.html`](sample/index.html) shows every built helmet with a straps toggle.

## Build

```
pip install bpy numpy pillow          # bpy = Blender as a Python module (4.2+; tested on 5.3)
cd assets/helmets/model
python3 build.py                      # the three presets, full quality with baked AO (about 25 s each on 4 CPUs)
python3 build.py --random 12          # twelve new helmets, seeds 1..12
python3 build.py --seeds 7,19,42      # particular seeds (the same seed always gives the same helmet)
python3 build.py --fast               # quick: half mesh density, small textures, no AO
python3 check.py                      # check the shells against the published figures -> notes/checks.json
```

Outputs go to `model/work/` and are never committed (rule 2): `<id>.glb`, `<id>.stats.json` (size, area, triangles,
sockets) and `<id>/tex/` (the procedural maps).

## Make your own helmet

Copy a preset in `model/presets.json`, change the numbers and build it with `--preset <id>`. Everything is in
millimetres and in the shell's own coordinates: `a` is the azimuth (0 front, 90 the wearer's left, 180 back) and `t`
runs down a meridian from the crown (0) through the widest line (1).

| Block | Controls |
|---|---|
| `shell` | `length`, `width`, `height` (the exterior, matched exactly), `thickness`, `dome_height`, curvature (`plan_n` planform squareness, `dome_m` crown flatness, `egg`, `front_taper`, `crown_back`, `flare`), and `cut`: rim depth below the crown at each azimuth, which makes it high, mid or full cut |
| `colours` | `shell`, `rails`, `loop`, `shroud`, `webbing`, `pads`, `bungee`, `headset`, `pouch`, `trim` |
| `rails` | side rails along the rim: azimuth range, height above the rim, section, screw positions |
| `shroud` | NVG shroud: plate size, receiver, one- or `three_hole`, `metal` or polymer, `bungee` |
| `loop_panels` | loop patches laid flat on the shell (`a`, `t`, `w`, `h`, `r`, `mirror`) |
| `pouch`, `marker`, `headset`, `cover`, `front_plate` | optional kit; a `cover` takes a pattern `seed` and four `colours` |
| `pads` | inner pads (`t_frac` places them a fraction of the way down to the rim) |
| `retention` | front and rear anchor azimuths, `bolts`, webbing width, and two strap poses: `hang` (on a stand) and `worn` (round a head); set `"strap_pose": "worn"` on the preset for a character |
| `comm_groove` | the shallow channel over the crown for an over-the-head headset band |

`helmetkit.random_preset(seed, presets)` mixes the presets' curvature, picks a size (M/L/XL), a cut, paint and kit;
covers come with mid cuts and take the front plate, high cuts take rails, shroud and sometimes a headset or pouch.

## Frame, units and sockets

glTF frame: metres, +Y up, +Z forward (the face), +X the wearer's left. The origin is the top of the wearer's head
(inner crown less the 3/4 in crown pad), so to wear a helmet put its origin on the head's vertex. Sockets (empties):

| Socket | Where |
|---|---|
| `socket_head_top` | the origin |
| `socket_nvg` | in the shroud's (or front plate's) mount opening, facing forward |
| `socket_rail_L`, `socket_rail_R` | the middle of each side rail, on its face (lights, cameras, headset adapters) |

Parts are named meshes (`shell`, `edge_trim`, `rail_L`, `shroud_receiver`, `bungee`, `loop_panel`, `pad`,
`chin_strap`, `ear_cup` ...); materials are named by what they are (`shell_paint`, `shell_laminate`,
`edge_trim_rubber`, `velcro_loop`, `webbing_nylon`, `cover_fabric` ...) so the game can recolour by role.
`runtime/helmets.js` has `attachHelmet`, `setStrapsVisible` and the published facts per preset.

## Checks

`model/check.py` (results in `notes/checks.json`), all passing:
- US shell exterior equals the ACH size L maximum from TM 10-8470-204-10 (266.7 x 241.3 x 177.8 mm), and its inside
  fits the largest L head (8 1/4 in) with two 3/4 in pads.
- Contractor shell outer area 1021.6 cm² against the FAST XP data sheet's 994 cm² for L high cut (+2.8 %, inside its ±3 %),
  and mass 828 g against 841 g.
- Eastern shell mass 986 g against the published "no more than 1 kg".

## Limits

- No official side or top drawing of these shells was reachable, so the curvature between the measured extents is
  from knowledge of the real helmets, not overlaid on a drawing. See `notes/SOURCES.md`.
- Accessories are sized by class, not from makers' drawings, and carry no makers' names or logos.
- No night-vision device yet: `socket_nvg` is where one goes.
- Full builds are about 160k-220k triangles (hero detail). `--fast` is the game LOD, about half that.
