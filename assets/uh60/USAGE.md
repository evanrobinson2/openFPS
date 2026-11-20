# UH-60A Black Hawk

A boardable, flyable UH-60A built by code from the Army operator's manual (TM 1-1520-237-10): parametric airframe,
rotor system, landing gear, cockpit and 14-seat cabin; a physics flight model; synthesised sound. No mesh, texture or
audio file is an input or is stored in git.

## Files

| Path | What it is |
|---|---|
| `model/build.py` | Entry point. Builds `model/work/uh60_lod0.glb` and `uh60_lod1.glb` (git-ignored). |
| `model/recipe.py` | Every dimension, with its source tag, and the build context (nodes, clips, sockets). |
| `model/airframe.py`, `rotors.py`, `gear.py`, `interior.py`, `hardware.py` | The assemblies. |
| `model/crew_seat.py` | Pilot's and copilot's armoured seats from the maintenance manual's seat drawings (bucket, cushions, harness, guide tubes, attenuators, struts, tracks, armoured wings). |
| `model/manual_art.py`, `panel.py` | The instrument panel, lower and upper consoles, engine control quadrant, cyclic and collective grips, built on the manual's own drawings (figures 2-9, 2-8, 2-7, 2-13, 2-14). Needs PyMuPDF and OpenCV (`pip install pymupdf opencv-python-headless`) and the manual at `model/refs-local/tm10.pdf`. |
| `model/floor.py`, `cockpit_floor.py` | Cabin floor from figure 6-11 (tie-down and seat-stud pans, hook door, sills, kick strips) and the cockpit floor from figure 2-4 (pedals, lower console, seat tracks and frames, boots). Each paints its own floor map. |
| `model/skin.py`, `detail.py` | Surface maps painted by code: panel seams, rivets, markings, wear; instrument faces; fabric, quilt, floor. |
| `model/tools/` | `fit_drawing.py` (overlay the manual's station diagram on a render), `render.py`, `pack_web.py`. |
| `flight/uh60-flight.js` | Flight model (browser and node). `flight/verify.mjs` checks it against the manual; results in `flight.json`. |
| `sound/uh60-sound.js` | Sound synthesiser driven by the flight state. `sound/verify.mjs` checks its spectrum; results in `sound.json`. |
| `sample/index.html` | Sample page: studio, walk and fly views. |
| `notes/SOURCES.md` | Sources, what was read from each, and what is inferred. |

## Build

    pip install bpy shapely pymupdf pillow numpy      # bpy = Blender 5.3 as a Python module
    cd model && python3 build.py                      # both LODs, about 2 minutes on a CPU
    python3 tools/pack_web.py                         # work/web/: the sample page with the model beside it
    cd work/web && python3 -m http.server             # open http://localhost:8000/index.html

`build.py --lod 1 --fast` skips the surface maps for quick shape work; `--blend` also saves a `.blend` for
`tools/render.py` and `tools/fit_drawing.py`. The overlay tool needs the manual as `model/refs-local/tm10.pdf`
(git-ignored; see `notes/SOURCES.md` for where it comes from).

| | LOD0 | LOD1 |
|---|---|---|
| Triangles | 578 k | 157 k |
| Skin maps | 4096 | 2048 |
| Rivet and screw heads | geometry (about 14,000) | in the normal map |
| GLB | 21.6 MB | 7.0 MB |

## Frame and units

Authoring: inches in the manual's own STA / BL (+ left) / WL. Export: metres, glTF +Y up, +Z forward (nose), +X left,
origin on the static ground line under the main rotor mast.

## Nodes, clips, sockets

| Node | Moves | How |
|---|---|---|
| `main_rotor` | spins about its local Y (mast tilted 3 degrees forward), counter-clockwise from above | set rotation from `out.psi`, or play `rotor_spin` |
| `main_blade_1` to `_4` | morph target `droop`: 1 = blades hanging at rest, 0 = flying | drive from rotor speed and thrust |
| `tail_rotor` | spins about its local Y (canted 20 degrees) | `out.psiTail` |
| `stabilator` | pitches about its local X | `out.stabilator` (degrees, trailing edge down positive) |
| `cabin_door_L`, `cabin_door_R` | slide aft 66 in | clips `cabin_door_L_open`, `cabin_door_R_open` |
| `cockpit_door_L`, `cockpit_door_R` | hinge on the forward edge | clips `cockpit_door_L_open`, `cockpit_door_R_open` |
| `cyclic_L/R`, `collective_L/R` | pivot at the floor | rotate from the control inputs |

Sockets (empties): `eye_pilot` (right seat), `eye_copilot`, `spawn_cabin`, `spawn_ground_left`, `seat_gunner_left`,
`seat_gunner_right`.

Materials are named by role (`skin_od`, `glass`, `rubber`, `steel`, `fabric_seat`, `instrument`, ...). Walk collision
should skip `glass*`, `lens*` and the rotor nodes; the sample page uses the recipe's cabin and door stations instead
of mesh collision.

## Flight model

    import { UH60Flight } from './uh60-flight.js';
    const f = new UH60Flight({ running: false });          // cold on the pad; default is rotor at 100 percent
    f.eng.forEach(e => e.on = true);                        // start: rotor runs up at about 30 percent torque
    f.step(dt, { collective, lon, lat, pedal, fps: true }); // collective 0..1, others -1..1; call at 120 Hz or faster
    const { position, basis } = f.toThree();                // metres, the model's export frame
    f.out                                                    // telemetry: ias, agl, vs, heading, rotorPct, torquePct[2], ngPct[2], thrust, bvi, ...

Blade-element thrust with momentum inflow (including the vortex-ring branch), ground effect, tip-path-plane tilt and
hub moment, tail rotor, stabilator on its airspeed schedule, fin, fuselage drag, two governed engines with rotor speed
as a degree of freedom (so engine-out autorotation works), three sprung wheels. `fps: true` adds the attitude and
heading hold of the aircraft's flight path stabilisation, plus a low-speed drift damper that is a game aid
(`assist: false` removes it).

Check (`node flight/verify.mjs`), manual's worked examples against the model:

| Case | Manual | Model |
|---|---|---|
| Hover out of ground effect, 19,500 lb, 2,000 ft, 30 C | 94 % torque | 92.1 % |
| Hover at 10 ft wheel height, same day | 80 % | 74.9 % |
| Cruise 135 KTAS, 17,000 lb, 6,000 ft, 30 C | 62 % | 61.5 % |
| Cruise 82 KTAS, same | 41 % | 41.4 % |
| Both engines cut at 80 kt | rotor stays in limits | 2,400 ft/min down, rotor 110 % with collective full down |

Limits: the drag polar, induced-power factor and flat-plate area are fitted to those four points; ground effect is
5 points optimistic at 10 ft; no retreating-blade stall or compressibility limit on speed; no wind or turbulence;
run-up takes about 12 seconds, not the real minute or more.

## Sound

    import { UH60Sound } from './uh60-sound.js';
    const s = new UH60Sound(); await s.start();   // from a click; runs in an AudioWorklet
    s.setMode('cinematic' | 'realistic');         // cinematic is the default
    s.setListener({ view: 'cockpit' | 'cabin' | 'outside', distance, doorsOpen });
    s.update(f.out);                              // every frame

Sources: main-rotor blade passage (4 x 258 rpm = 17.2 Hz) with loading, thickness and blade-vortex slap; tail rotor
(79.3 Hz); two gas-generator whines that follow Ng and beat against each other; combustion roar; transmission mesh
tones tied to rotor speed; airframe wind noise. `node sound/verify.mjs` renders it offline and checks those
frequencies, that slap raises the 300 to 1500 Hz band, that whine follows Ng, and that it is silent when shut down.
Limits: source levels are balanced by ear, not from measured sound power; gear-mesh frequencies are inferred.
