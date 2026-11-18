# HK416 D14.5RS: simulated discharge sound

Everything in this folder is synthesised from physics and published numbers. No recording, and nothing derived from a recording, is in this repository. Under openFPS's rules no audio files are committed at all: the sound is the simulation, and `hk416-sound.js` synthesises it in the browser at load.

Credit: carpetshark. Simulation by Claude Fable 5.2.

**Version 2 (2026-11-17).** The owner heard version 1 as "clicks" that did not sound like the recordings. This version (a) establishes what the two reference recordings can be trusted for, (b) drives the muzzle source and the action noise from the action simulation (`../action/action.json`), (c) adds rough-ground scattering and an outdoor range with far-field listeners, and (d) replaces the playback "ear" stage, which let the shock through untouched. The change request is recorded in `../notes/NOTES.md`. Sections marked **v2** are new.

## What is here

| File | What it is |
|---|---|
| `sim.py` | The simulator. Stage A turns physics into tables (`params.json`); stage B turns tables into waveforms. |
| `params.json` | Every derived table: path lists, pulse sizes, ground and air filters, modal tables, room recipes, earmuff filter. Written by `sim.py`. |
| `hk416-sound.js` | Browser port of stage B. Reads `params.json` and synthesises the same shots, mechanical sounds, steel hits and impulse responses at load. |
| `manifest.json` | One entry per rendered output: file, what it is for, true simulated level, scale. |
| `audio/` | Listening renders (FLAC). Written by `sim.py dry` / `overlays`; never committed. |
| `masters/` | 24-bit WAV masters of the dry sounds. Not committed (rebuild them). |
| `compare.py`, `compare/` | Checks: condition of the reference recordings (`recording_trust.json`), simulation against them through a microphone model (`diagnosis.json`; `diagnosis_v1.json` is the same measurement of version 1), published peaks, JS parity (`js_parity.json`), one simulation-only plot. Numbers only: no plot is drawn from a recording. |
| `verify_js.py`, `verify_js.mjs` | Parity check of the JS port against Python, run under node. |
| `index.html` | Minimal listening page (uses the JS module). Nothing plays until you press Play. |

## Rebuild

From `assets/hk416/`, with Python 3 (numpy, scipy, matplotlib), ffmpeg (FLAC) and node (parity check only):

```
python3 sound/sim.py all        # params.json, audio/, masters/, manifest.json, compare/
python3 sound/sim.py params     # only params.json
python3 sound/sim.py dry        # dry shots, mechanical clips, steel hits
python3 sound/sim.py overlays   # impulse responses and the earmuff filter
python3 sound/sim.py compare    # checks; set OPENFPS_REF_AUDIO to the folder with your licensed reference recordings for the recording side
python3 sound/sim.py listen     # local listening renders, sound/audio/listen_*.wav (ignored by git)
python3 sound/sim.py scoring    # unprocessed far-field renders, sound/audio/scoring/*.wav (ignored by git)
python3 sound/verify_js.py      # JS port against Python
python3 -m http.server 8777     # then open http://127.0.0.1:8777/sound/index.html
```

The build is deterministic: all randomness comes from named mulberry32 streams that Python and JS share.

## Signal chain

```
dry *_free (pascals, free field)  ->  convolve with ir_<overlay>_<perspective>  ->  [earmuff FIR]  ->  playback mapping
```

- `dry_*_free` has no reflections at all and is the convolver input. `dry_*_field` is the same shot over open ground (the Part 1 render: direct sound plus ground reflection).
- Each impulse response has the direct path as its first sample (value 1 after multiplying by `units_per_fullscale`), so the convolver output replaces the dry signal. Use `ConvolverNode.normalize = false`.
- **Hearing protection is applied after the room**, at the ear. It is linear, so the order does not change the result, but that is where it sits physically.
- **Playback.** The shot is 157 dB at the ear. Speakers cannot do that, so every buffer is normalised to −1 dBFS and `S.info(buffer)` carries the true level. Played linearly at a safe volume, a 0.2 ms shock is a tick whatever follows it. The `ear` stage of `chain()` models what the ear itself does to such a peak; see "The ear stage" below.

## Geometry (from the model)

Range frame: x right, y up, z downrange. Sockets from `hk416.glb`.

| Quantity | Value | Source |
|---|---|---|
| Barrel | 14.5 in (368.3 mm) | NOTES.md, manual p. 7 |
| Muzzle device | A2-style birdcage flash hider ("compensator"), 6 slots | NOTES.md, manual p. 6 |
| Muzzle relative to the aiming eye | 0.659 m ahead, 0.066 m below | `socket_muzzle` − `socket_ads_eye` |
| Eye height | 1.62 m | range page camera |
| Shooter's ear | 0.04 m right, 0.01 m below, 0.10 m behind the eye | inferred (head on the stock) |
| Ear to muzzle | 0.762 m at 174.8° from the bore | derived. The brief guessed 150°; the sockets give 175° (171° for the left ear) |
| Ejection port | `socket_eject`, 0.208 m ahead of the eye | model |
| Bystander | 5 m to the right of the shooter (97.5° from the bore, 5.04 m from the muzzle) | brief |
| Downrange | 50 m ahead, 2 m beside the line of fire | brief; the 2 m offset is assumed (nobody stands on the line) |
| Comparison mic "on gun" | 0.40 m behind the muzzle, 0.06 m above the bore | inferred; the recording does not say |
| Comparison mic "1 m left" | 1 m left of the muzzle at 90° | recording title |

## Physics and parameters

### 1. Muzzle source (v2)

Three parts: the shock, the gas-volume body and the jet noise. The shock is anchored to a published level; the other two are computed from the action simulation's blow-down (bore pressure and temperature after the bullet leaves).

**Gas state at the muzzle, from `action.json`** (derived, not tuned here):

| Quantity | Value | How |
|---|---|---|
| Gas in the bore at bullet exit | 1.656 g at 122.6 MPa, 1788 K | Noble-Abel gas in the bore volume, action sim tables |
| Enthalpy leaving the muzzle | 4336 J | ∫ ṁ h₀ dt over the blow-down |
| Of which jet kinetic energy | 2925 J (6.13 MW at exit) | expansion to 1 atm: jet 2200 m/s, fully expanded diameter 47.9 mm |
| Gas volume at 1 atm, V∞ | 8.28 L | (γ−1)/γ · H / p₀, γ = 1.24 |
| Gas momentum, J | 2.062 N·s | action sim recoil impulse minus bullet momentum (SAAMI convention) |
| Efflux time τ_b | 0.5 ms | time for 63 % of the jet energy to leave |

The action sim's exit pressure is high against the roughly 60 to 70 MPa usually quoted for a 14.5 in barrel; it is calibrated only to peak pressure and muzzle velocity. Everything in this section inherits that.

**Shock.** A Friedlander pulse, p(t) = P (1 − t/T) e^(−t/T).

| Parameter | Value | Source |
|---|---|---|
| Total peak at 1 m, 90° | 164 dB (3170 Pa) | Published: M4, M855, 14.5 in, 1 m left of the muzzle (Dater, Larson Davis "Firearm Sound Briefing"); the same briefing has the HK416 equal to the M4 unsuppressed |
| Positive phase at 1 m, 90° | 0.30 ms | Inferred from published 5.56 rifle A-durations (0.2 to 0.4 ms) |
| Directivity of the peak | P ∝ μ cos θ + √(1 − μ² sin² θ), μ = 0.78 | Fansler and Schmidt muzzle blast scaling. μ is recalled, not re-fetched. Front to back is 18 dB; the data stop at 150° and the shooter (175°) is an extrapolation |
| Duration against angle | T ∝ l′^0.5 | inferred |
| Distance law | weak-shock (Landau) lengthening, s = √(1 + k ln r) | as version 1 |
| Secondary pulse | −10 dB at 90°, 0.45 ms, 0.7 ms later | inferred (PEW Science reports a secondary blast on 14.5 in 5.56 rifles; size and timing are mine) |

**Gas-volume body (new).** Far from a compact source, the pressure's second time-moment is fixed by what the source put into the air: M(θ) = (ρ₀ V∞ + cos θ · J / c₀) / 4πr. The first term is the monopole of the gas volume, the second the dipole of the gas momentum (Lighthill; Dowling and Ffowcs Williams, *Sound and Sources of Sound*). Version 1's pulse did not respect this: behind the gun its shock implied 0.37 L of gas where conservation requires the equivalent of 3.4 L. Version 2 adds what the shock and secondary pulse do not carry as a slow term,

b(t) = ΔM (e^(−t/τ_b)/τ_b − e^(−t/τ_m)/τ_m) / (τ_m − τ_b),

which has zero impulse and second moment ΔM. It starts at ΔM/(τ_b τ_m), so the shock is reduced by that much and the total peak stays on the published anchor. τ_m = 3 ms is the time for the plume to give up its kinetic energy by entrainment (inferred: Ricou-Spalding entrainment gives 1.7 ms, the same with a compressible-shear-layer correction about 7 ms). Ahead of about 60° the anchored shock already carries more than the conserved moment and no body is added. The result at the shooter's ear: a 1376 Pa shock carrying a 119 Pa step that decays in 0.5 ms, then a −24 Pa tail that lasts several ms. It is a real but modest low-frequency term.

Cross-check of the two independent routes: the simulation's fast (static-enthalpy) gas volume is 2.69 L, the published 164 dB, 0.3 ms pulse implies 3.0 L; the monopole positive impulse from the simulation is 0.434 Pa·s at 1 m, the published pulse has 0.35 Pa·s.

**Jet noise (new).** Acoustic power = η × jet mechanical power(t), η = 0.5 % (NASA SP-8072 gives 0.3 to 1 % for supersonic jets), multiplied by 1 − e^(−t/0.467 ms) because a starting jet is not yet turbulent along its core (inferred: jet front reaching 15 diameters). Spectrum: a broad hump, +6/−6 dB per octave about f = 0.03 u_j/D_j (SP-8072 rocket data 0.02 to 0.04), which rises from 1378 Hz at exit to 3408 Hz as the jet shrinks. Directivity: −6, 0, −10, −17, −20 dB at 0, 45, 90, 135, 180° from the jet axis (typical supersonic-jet shape, recalled). It lasts 3 ms and is 20 dB down behind the gun.

| Other | Value | Source |
|---|---|---|
| Shock rise | 10 µs ramp, synthesised at 192 kHz, band-limited to 48 kHz | numerical choice |
| Shot-to-shot spread | 0.7 dB sd | inferred |
| Muzzle velocity | 850 m/s | HK maintenance manual p. 7 |

Resulting peaks (free field): 1 m at 90° 164.4 dB (published 164.0; the 0.4 dB is the jet noise and secondary pulse riding on the anchor), shooter's ear 157.5 dB (commonly quoted at-ear figures for 5.56 carbines: 155 to 160 dB, recalled, not re-fetched).

**Directivity by band.** Overlays need the source's directivity to weight each reflection. Version 1 used the shock's peak directivity at all frequencies. Version 2 computes the energy of the whole source (shock, body, secondary, jet) per octave band on a grid of angles (`params.dirband`) and uses that.

### 2. Ballistic shock (N-wave)

| Parameter | Value | Source |
|---|---|---|
| Bullet | M855: 5.70 mm, 23.0 mm long, 4.02 g | published |
| Velocity along the path | v = 850 e^(−0.001 x) m/s | inferred fit (about 10 % lost per 100 m) |
| Amplitude and duration | Whitham: Δp = 0.53 p₀ (M²−1)^(1/8) d / (b^(3/4) l^(1/4)), T = 1.82 M b^(1/4) d / (c (M²−1)^(3/8) l^(1/4)) | Whitham 1952 |
| Geometry | the ray leaves the trajectory at acos(1/M); a listener gets the wave only if that ray starts ahead of the muzzle | Mach cone |

Downrange listener: Mach 2.36, miss distance 2.0 m, Δp = 565 Pa (149 dB), T = 0.12 ms, arriving 64.8 ms after the shot; its ground reflection follows 4.6 ms later; the muzzle blast arrives 79 ms after the crack at 135 dB. The same briefing measured 148.5 dB for M855 at 1 m from the path. The shooter and the bystander get no N-wave: their angle from the bore is above 90° − μ = 66°, so the cone never reaches them. Reflections of the N-wave off berms and walls are not modelled.

### 3. Mechanical action (v2)

Version 1 used its own event times and guessed levels. Version 2 takes every time, mass and speed from `../action/action.json`. (Version 1 was written to do so, but could not read the file's layout and silently fell back.) The cycle is now 74.9 ms (801 rpm).

**Level.** Radiated sound energy = η × energy lost in the impact. η = 3 × 10⁻⁴ for metal on metal (Richards, Westcott and Jeyapalan 1979 measured 10⁻⁴ to 10⁻³ for impact ringing), 5 × 10⁻⁵ for the tungsten-filled buffer (inferred), 10⁻³ for a free brass case and 5 × 10⁻⁵ for a case landing on dirt (inferred). Each event is a sum of decaying modes plus a short contact click, scaled so its free-field energy is that figure.

| Event | Time after bullet exit | Energy lost | Peak at 1 m |
|---|---|---|---|
| Trigger break (sear releases the hammer) | -9.49 ms | 0.0354 J | 97.2 dB |
| Hammer on firing pin | -1.49 ms | 0.481 J | 110.6 dB |
| Carrier picks up the bolt, unlock | +2.36 ms | 0.718 J | 109.6 dB |
| Piston rod stops | +3.46 ms | 0.785 J | 103.6 dB |
| Case hits the brass deflector | +13.80 ms | 0.00838 J | 99.3 dB |
| Moving parts on the buffer stop | +22.67 ms | 2.4 J | 102.5 dB |
| Buffer spring surge | +22.67 ms | 0.0988 J | 96.8 dB |
| Round stripped from the magazine | +36.22 ms | 0.0693 J | 99.5 dB |
| Bolt and round stop in the chamber | +60.80 ms | 0.341 J | 99.5 dB |
| Carrier home on the barrel extension | +63.82 ms | 2.95 J | 111.2 dB |
| Trigger reset (semi) | +120 to 160 ms | 0.02 J (inferred) | 94.7 dB |
| Case lands, bounces twice | +0.79, 1.27, 1.43 s | 20 %, 2 %, 0.6 % of its 0.19 J (inferred) | 91.7, 78.2, 73.8 dB |

**Modes, from the model recipe** (`model/build.py` dimensions, handbook constants, loss factor 0.02 for an assembled rifle in the hands, inferred): barrel as a steel cantilever from the barrel nut (341 mm, 8.9 mm radius): 115, 721, 2018, 3955 Hz; upper receiver side wall (3 mm aluminium, 190 × 40 mm): 4755, 6369, 9598 Hz; receiver extension as a quarter-wave air column (191 mm): 449 Hz; buffer spring standing waves from 41.8 Hz; case ovalling 8.2 kHz. The gas block and flash hider are not in the beam model, so real barrel modes sit somewhat lower.

**Sliding noise (new).** Between the events the carrier and buffer slide: sound power = 3 × 10⁻⁵ × friction force (5 N, action sim) × carrier speed(t), from first movement to battery, as band noise centred on 2 to 8 kHz. The efficiency and the band shape are inferred. It is about 77 dB at 1 m: a faint continuous sound under the impacts.

Clips rendered on their own: `cycle`, `case_drop`, `trigger`, `trigger_reset`, `charge` (timed to the model's `charge` clip), `bolt_lock_back` (empty magazine, manual p. 26), `bolt_release`.

### 4. Propagation

| Parameter | Value | Source |
|---|---|---|
| Atmosphere | 20 °C, 50 % RH, 101.325 kPa, c = 343.2 m/s | stated |
| Air absorption | ISO 9613-1 formula, as a filter per path (dry) or per octave band (overlays) | ISO 9613-1 |
| Spreading | 1/r | |
| Ground | Delany-Bazley impedance, σ = 300 kPa·s/m² (packed dirt, sparse grass), spherical-wave reflection coefficient Q = R_p + (1 − R_p) F(w) | Delany and Bazley 1970; Chien and Soroka 1975. σ is inferred for the range page's dirt |
| Ground roughness (v2) | rms height 10 mm (inferred). The specular bounce keeps exp(−2 (k σ_h cos θ)²) in amplitude; the rest of the energy is scattered diffusely (Lambert patches within 20 m of the listener, and of the muzzle for far listeners) | Rayleigh roughness criterion. At normal incidence 13 % of the energy is diffuse at 1 kHz, 42 % at 2 kHz, 89 % at 4 kHz, so above 2 kHz the ground bounce is a 30 ms hiss, not a second crack |

### 5. Listener perspectives

Shooter's ear (default), bystander, downrange, as in the geometry table. Version 2 adds far-field listeners for the outdoor range: `side25`, `side50`, `side100` (90° to the right of the muzzle) and `front25`, `front50`, `front100` (ahead, 2 m beside the line of fire, so they also get the bullet's N-wave). All are mono, a single point with no head or body shadow.

### 6. Steel plate

A free circular AR500 plate, 10 mm thick, radii 0.18, 0.20, 0.22, 0.25, 0.30 m (the range page's five plates, each at its own distance).

| Parameter | Value | Source |
|---|---|---|
| Steel | E = 207 GPa, ρ = 7850 kg/m³, ν = 0.29 | handbook |
| Mode frequencies | f = λ² / (2π a²) · h √(E / (12 ρ (1 − ν²))) | thin-plate theory |
| λ² | first 15 from Leissa's free-plate table, then (π/2 (n + 2s))² × 0.97 | Leissa 1969 (recalled; the first eight are reliable, the rest approximate), asymptotic above |
| Excitation | bullet momentum m v at the plate (v from the drag law), half-sine contact of length/velocity ≈ 28 µs, at a random radius 15 to 60 % out | derived |
| Radiation | efficiency (f/f_c)² below coincidence (f_c = 1210 Hz), 1 above | crude, inferred |
| Damping | η = 0.004 (mount) + radiation loss; T60 = 2.2 / (η f) | inferred |
| Splash | 0.6 ms noise burst, a quarter of the modal rms | inferred |

Lowest modes: 400 Hz (0.18 m) down to 144 Hz (0.30 m), 28 to 70 modes below 16 kHz. Heard at the firing point: 107 to 119 dB peak. The files carry no delay; add bullet flight time (about dist/830 s) plus dist/343 s. The plate ring is free field with air absorption per mode; it does not go through the room responses, which are built for the muzzle.

## Environment overlays

Method: taps from geometry (image sources, Lambert patches or scatterers), each with a gain per octave band (63 Hz to 16 kHz) that includes wall absorption, air absorption and the blast directivity toward that path; then a zero-phase octave filter bank; then, for rooms, a noise tail with the Eyring decay time per band. The gain of every tap is relative to the direct path at that listener, so the blast directivity matters: the shooter stands in the quietest direction, and reflections of the forward blast come back 18 dB hotter than an omnidirectional source would give.

Statistical tail: variance per sample = ⟨D²⟩ (r_d / D_d)² · 4πc/V · e^(−13.8 t / T60_b) / fs, the energy rate of the image-source lattice for a source with mean-square directivity ⟨D²⟩ = 2.04. Before the mixing time only the scattered share (1 − (1 − s)^n) is added; after it, all of it. Eyring: T60 = 0.161 V / (−S ln(1 − ᾱ) + 4 m V).

| Overlay | Geometry | Surfaces (α at 500 Hz) | Result |
|---|---|---|---|
| `concrete_room` | 4 × 5 × 3 m, shooter 1.2 m from the back wall | painted block walls 0.06, concrete floor and ceiling 0.02 | T60 2.3 s at 500 Hz; +19 dB energy over free field |
| `furnished_room` | 4.5 × 6 × 2.5 m | gypsum walls 0.05, carpet with furniture folded in 0.45, plaster ceiling 0.06; scattering 0.35 | T60 0.6 s; +12 dB |
| `hallway` | 1.8 × 2.6 × 30 m, firing down its length from 3 m in | gypsum walls and ceiling, vinyl floor 0.03, wood doors at the ends; image sources to 300 ms | T60 1.7 s; +15 dB; end-wall slap at 157 ms |
| `indoor_range` | bay 12 × 3 × 28 m, 25 m lane, stall partitions 0.6 m either side | block and acoustic panel walls 0.48, ceiling baffles 0.80, granulated rubber backstop 0.70, concrete floor | T60 0.3 s; +4 dB |
| `warehouse` | 40 × 10 × 60 m | metal cladding 0.10, insulated metal roof 0.20, concrete floor | T60 4.7 s (file cut at 4 s); +2 dB shooter, +12 dB downrange |
| `open_field` | flat ground only | ground model above, with rough-ground scattering | ground bounce 7.3 ms after the direct sound at the shooter, then 30 ms of scattered hiss |
| `outdoor_range` (v2) | **assumed** generic rifle range in a wooded clearing: 91 m lane, backstop 60 × 6 m, one side berm 3 m high 15 m to the left, forest edge 15 m high at 40 m left, 120 m right, 110 m ahead, 40 m behind | soil berms 0.40, Lambert; forest edge scatters back 5 to 10 % of the energy at 500 Hz to 4 kHz (order of magnitude after Wunderli and Salomons 2009, recalled) | side berm return from 87 ms, backstop at 0.53 s, tree lines to 0.8 s. The layout is not any real range and nothing in it was fitted to a recording |
| `range_berm` | the range page: ground, bench top 0.57 m under the muzzle, berm face 60 × 6 m at 59 m | soil berm 0.40, Lambert scattering in 1 m patches | slapback from 0.34 to 0.38 s, −47 dB in energy re the direct sound (about 110 dB SPL) |
| `forest_edge` | tree line 80 m ahead, stand 300 × 120 m | 0.04 trunks/m², radius 0.12 m, single scattering; foliage loss from ISO 9613-2 Table A.1 | a diffuse wash from 0.47 s decaying over about 0.5 s, −65 dB in energy |
| `street_canyon` | street 18 m wide, facades 20 m, firing along it; far facade at 150 m | brick and glass 0.03, asphalt 0.03, facade scattering 0.3 | flutter between the facades (105 ms round trip), diffuse bursts, far slap at 0.87 s |
| `valley` | rock wall 180 m left, forested slope 320 m right, rock head wall 750 m ahead | rock 0.04, forested slope 0.50, 6 m Lambert patches, first order only | echoes at 1.0, 1.9 and 4.4 s, −56 dB in energy |

Absorption coefficients are handbook values for 125 Hz to 4 kHz, extrapolated at 63 Hz, 8 kHz and 16 kHz; the rubber backstop, soil berm and forested slope are inferred. The full tables and the per-band T60 (Eyring and Sabine) are in `params.json` under `overlays.*.persp.*.doc` and in `manifest.json`.

Perspectives: every overlay exists for the shooter. The warehouse and the outdoor overlays also exist for the bystander and the downrange listener. The four small interiors do not (5 m to the side does not fit in them).

**Hearing protection** (`hpd_earmuff`): passive earmuff, NRR 30 class. Mean attenuation 15, 21, 28, 40, 42, 37, 40, 40, 40 dB at 63 Hz to 16 kHz (typical published values for a large-cup muff, recalled; inferred at 63 Hz and 16 kHz), as a 256-tap minimum-phase FIR. Applied after the room. Level-dependent effects at 150 dB+ are ignored.

## Can the recordings be trusted? (v2)

Two local reference recordings (Sonniss GDC 2016, Pole Position Production; never in git). All numbers are in `compare/recording_trust.json`.

| | On gun | 1 m left |
|---|---|---|
| Microphone (file name) | DPA 4062 miniature omni, on the gun | Sennheiser MKH 416 interference-tube microphone, 1 m left of the muzzle, off axis |
| Published limits | peak SPL before clipping 154 dB, 20 Hz to 20 kHz | max SPL 130 dB at 1 % THD, 40 Hz to 20 kHz |
| Metadata (BWF) | originator "Pole Position Production"; description of a 40-channel session at 0 to 55 m; no gain, pad or position data | same |
| Format | 96000 Hz, 24 bit mono, 3.766 s, 7 shots | 96000 Hz, 24 bit mono, 9.099 s, 12 shots (2 strings of 6) |
| Peak | 0.00 dBFS, 144 samples at full scale | 0.00 dBFS, 1000 samples at full scale |
| Flat tops per shot | 9 to 21 samples in up to 8 runs, longest 115 µs | 72 to 99 samples in up to 30 runs, longest 188 µs, spread over the first 13 ms |
| Crest factor, first 30 ms | 13.2 to 13.4 dB | 7.7 to 8.5 dB (a linear record of this shot would be about 27 dB) |
| Largest sample | 0.7 to 3.4 ms after the blast starts | 0.1 to 1.2 ms after it starts; the first half millisecond reaches only 0.09 to 0.56 of full scale |
| Level 100 to 150 ms after each shot | -19.8 dBFS rms (spread 1.7 dB) | -14.0 dBFS rms (spread 0.9 dB) |
| Low frequencies after the shot | no repeatable excursion | the same slow negative swing after every shot, to -0.46 of full scale, 12 to 35 ms after onset (correlation between shots 0.84) |
| Bandwidth | content to 45 kHz, no brick-wall filter; 20 Hz is +9 dB re 1 kHz | same; 20 Hz is +6 dB re 1 kHz (no high-pass in the chain) |
| Editing | 5 ms pre-roll, faded to silence at the end; "clean" in the name | 29 ms pre-roll, digital silence between strings |
| Click before the blast | 7.71 ms before, at -4 dBFS | 8.9 ms before, at -31 dBFS |
| Second burst | 62.4 to 68.5 ms after the blast, reaching full scale | not separable from the tail |
| Decay after the last shot, 0.12 to 0.40 s | T60 0.96 s; 500 Hz 0.96, 2 kHz 0.81, 8 kHz 0.72, 16 kHz 0.48 s | T60 1.09 s; 500 Hz 1.03, 2 kHz 0.94, 8 kHz 0.77, 16 kHz 0.57 s |

What this says:

1. **Neither microphone could record the blast.** 164 dB at 1 m is 34 dB above the MKH 416's rated maximum; about 165 dB at the handguard is 11 dB above the DPA's clipping point. Both files show it: the first arrival is small, the largest samples come later, the 1 m file is flat-topped on and off for 13 ms, and its crest factor is 8 dB where a linear record would have 27.
2. **The 1 m microphone shows overload recovery.** The same slow negative swing follows every shot. Its low frequencies in the first 40 ms are an artefact.
3. **The on-gun microphone is not an acoustic record of relative levels.** A click 7.71 ms before the blast reaches −2 to −4 dBFS and the bolt closing reaches full scale, the same as the blast. Through the air the bolt is about 40 dB below the blast at that distance. Either the capsule is driven by the gun's vibration, or the blast is limited by 35 dB or more, or both.
4. **The click before the blast is the trigger break.** It is also at the 1 m microphone, small (-31 dBFS) and 8.9 ms before the blast. The action simulation puts the sear release 9.49 ms before the bullet leaves. If that click is 100 to 105 dB at 1 m, full scale in that file is about 130 to 136 dB: the microphone's own limit.
5. **The place was reverberant.** Both microphones agree on T60 about 1 s at 500 Hz to 2 kHz, falling to 0.5 s at 16 kHz (air absorption alone gives 0.65 s at 16 kHz, so the paths are long: outdoors or a very large space). Which, and what stood around, cannot be told from the files.

| Feature | Trust | Why |
|---|---|---|
| Peak level, rise, pulse shape, crest factor | no | microphones 11 to 34 dB over their limits |
| Share of energy early against late | no | clipping takes 20 to 30 dB off the blast and nothing off the tail |
| Low frequencies in the first 40 ms (1 m) | no | overload recovery |
| Relative level of blast, bolt and click (on gun) | no | structure-borne pickup or limiting |
| Event timing: trigger break, blast, bolt closing | yes | sample-accurate and repeatable to 0.1 ms |
| Decay time by band after the last shot | yes | both microphones agree, signal well under full scale |
| Band balance of the tail, 250 Hz to 8 kHz | partly | linear there, but coloured by the off-axis tube microphone and by the place |
| Absolute level of the tail | upper bound only | at most -42.0 dB re the true peak, if full scale is the microphone's clip level |

## Diagnosis and results (v2)

`compare.py` renders the simulation at each microphone over open ground, passes it through a model of that microphone (published bandwidth and clip level, the MKH 416's off-axis response by band) and measures both sides the same way. All numbers: `compare/diagnosis.json`; version 1 measured identically: `compare/diagnosis_v1.json`.

**How much of the "click" gap is clipping?** Energy in the first 50 ms, split 0 to 2 / 2 to 10 / 10 ms on (per cent), and crest factor:

| | 1 m left | On gun |
|---|---|---|
| Recording | 3.2 / 39.3 / 55.58, crest 9.0 dB | 7.2 / 74.4 / 18.11, crest 14.7 dB |
| Simulation, linear | 94.0 / 6.0 / 0.01, crest 27.7 dB | 92.1 / 7.5 / 0.39, crest 27.5 dB |
| Simulation clipped 20 dB | 67.9 / 32.0 / 0.07, crest 15.2 dB | 64.3 / 33.9 / 1.84, crest 14.2 dB |
| Simulation clipped 28 dB (164 dB into a 136 dB limit) | 53.6 / 46.2 / 0.22, crest 12.2 dB | 47.9 / 46.0 / 6.08, crest 11.4 dB |
| Simulation clipped 40 dB | 31.2 / 67.1 / 1.72, crest 9.1 dB | 22.3 / 53.5 / 24.25, crest 7.6 dB |

Clipping alone takes the crest factor from 27 dB to the recorded 9 to 15 dB and the first 2 ms from over 90 % of the energy to about half. It does not produce the recordings' energy after 10 ms (56 % at 1 m): that is the reverberant place, plus overload recovery at 1 m and vibration pickup on the gun. So the recordings' energy split is not a target.

**Trusted features, before and after.**

| Feature | Recording | Version 1 | Version 2 |
|---|---|---|---|
| Trigger break to blast | 7.71 ms (on gun), 8.9 ms (1 m) | not modelled | 9.49 ms (action sim) |
| Blast to bolt closed | 65.5 ms (median, on gun) | 62.0 ms (built-in table) | 63.8 ms (action sim) |
| On gun, 30 to 58 ms (action running): level below the recording / band-shape distance | | 41.4 / 6.8 dB | 26.7 / 6.5 dB |
| On gun, 58 to 75 ms (bolt closing): the same | | 29.0 / 6.3 dB | 16.9 / 7.0 dB |
| 1 m, 30 to 58 ms: the same | | 58.7 / 16.5 dB | 48.3 / 11.4 dB |
| 1 m, 100 to 200 ms (tail): the same | | 80.0 / 3.0 dB | 63.1 / 6.7 dB |
| Tail 100 to 200 ms at the shooter, re the direct peak | at most -42.0 dB (1 m, bound) | `range_berm` -88.6 dB | `range_berm` -72.7, `outdoor_range` -62.8, `indoor_range` -41.9 dB |
| Decay time 0.12 to 0.40 s | 1.0 s | none outdoors | `outdoor_range` 0.78 s, `indoor_range` 0.82 s |

The level columns compare the simulation re its microphone model's clip level with the recording re full scale. They coincide only if full scale is the clip level, which is an assumption, and the simulated side is open ground with no reverberation. The level gaps that remain (17 to 63 dB) are therefore mostly the recording's place and the on-gun vibration pickup, not the gun. Nothing was tuned to close them.

**Published peaks.** 1 m left: 164.4 dB against 164.0 dB published. Shooter's ear: 157.5 dB against 155 to 160 dB commonly quoted.

**The shot at the shooter's ear, first 50 ms** (0 to 2 / 2 to 10 / 10 ms on, crest):

| Render | Shares | Crest |
|---|---|---|
| Dry, free field, linear | 95.2 / 4.6 / 0.24 | 27.4 dB |
| `open_field`, linear | 70.1 / 19.8 / 10.03 | 26.1 dB |
| `range_berm` (default), linear | 62.9 / 29.7 / 7.38 | 24.8 dB |
| Dry, free field, through the ear stage | 70.8 / 26.6 / 2.57 | 14.4 dB |
| `range_berm` (default), through the ear stage | 26.1 / 44.1 / 29.75 | 9.6 dB |
| `indoor_range`, through the ear stage | 14.4 / 34.4 / 51.22 | 6.9 dB |

In a real browser (Chromium, `OfflineAudioContext`, the module's own `chain()`), the default chain gave 23.8 / 45.0 / 31.2 and a crest of 10.9 dB; version 1's compressor gave a crest of 24 to 27 dB on the same input, because a compressor with any attack time cannot act on a 0.2 ms pulse. That, more than the source model, is why version 1 played as a click.

**What is physically true.** Heard linearly, in the open, a rifle shot at the ear is a 0.2 ms shock, a ground bounce 7 ms later, 30 ms of ground-scattered hiss 30 dB down and the action 35 dB down. Version 2 adds real energy after the shock (the share after 2 ms rises from 5 % dry to 30 to 37 % over ground) but the linear crest factor stays near 25 dB. Recordings and ears do not hear it linearly.

Internal check: the free-field shot convolved with the `open_field` response (without the scattering patches, which the direct render lacks) matches the directly rendered open-ground shot to -14.5 dB (shooter), -29.5 dB (bystander), -31.9 dB (downrange).

## The ear stage (v2)

`chain({ ear: true })` is a model of the listener, not of the gun, and it is the one part of the chain that is a playback choice. The middle ear does not follow a pressure peak of 157 dB: the stapes' travel is limited, and the AHAAH model of impulse-noise hazard (Price and Kalb) puts the onset of that limit near 130 dB. The stage is a memoryless limit, L tanh(p/L) with L = 134 dB peak (inferred within 130 to 140), then make-up gain. It is calibrated from the true peak of `S.shot('single')` at the chain's perspective, so it removes about 23 dB from the shock at the shooter's ear, less for a distant listener and nothing behind earmuffs or for a mechanical clip (pass `peakDb: S.info(buffer).peak_db_spl` for buffers other than a shot). It does to the signal what the overloaded microphones did, for the same physical reason, and it is why a shot is not heard as a click. Limits: no middle-ear band-pass, no acoustic reflex, no cochlea; in a small hard room the reverberation itself sits above the limit and is distorted.

## The JS module

```js
import HK416Sound from './sound/hk416-sound.js';
const S = await HK416Sound.build(ctx, { paramsUrl });   // paramsUrl optional: params.json next to the module by default
S.shot('single' | 'semi3' | 'auto1s', { perspective, ground })   // AudioBuffer, peak −1 dBFS, free field unless ground: true
S.mech('cycle' | 'case_drop' | 'trigger' | 'trigger_reset' | 'charge' | 'bolt_lock_back' | 'bolt_release')
S.steel(radius, { dist, seed })                   // nearest of the five plates; seed varies the hit
await S.ir('range_berm', 'shooter')               // AudioBuffer, direct path = 1.0 at sample 0
S.hpd()                                           // earmuff FIR
await S.chain({ overlay, perspective, hpd, ear, peakDb }) // { input, output, set() }: room, earmuffs, ear stage
S.info(buffer)                                    // true peak in Pa and dB SPL, Pa per full scale
S.defaultOverlay                                  // 'range_berm'
S.perspectives                                    // shooter, bystander, downrange, side25/50/100, front25/50/100
```

Changes in version 2, all compatible with version 1 callers:

- `chain()` with no `overlay` key uses `S.defaultOverlay`. `overlay: null` or `'dry'` is still the free-field shot.
- `ear: true` is now the ear stage above (a `WaveShaperNode` and a gain) instead of a `DynamicsCompressorNode`. `peakDb` is new and optional.
- `auto1s` is 14 rounds at the action simulation's period (74.9 ms), not 15 at 70.6 ms.
- New overlay `outdoor_range` and six far-field perspectives.

`python3 sound/verify_js.py` runs the module under node and compares all outputs with Python sample by sample. The worst difference is −160 dB relative to peak (steel; everything else is below −238 dB). Results: `compare/js_parity.json`. The ear stage is Web Audio only; `sim.ear_playback` is its Python twin for the local renders (no 4× oversampling, so the two differ slightly at the limit).

For a game: fire `S.shot('single')` per round (it carries its own action and case sounds), through one `S.chain`. `auto1s` and `semi3` are fixed strings for listening.

## Known limitations

- Levels are anchored to one published figure (164 dB at 1 m) and one recalled directivity constant. The at-ear level could be off by 3 dB.
- The gas state comes from the action simulation, whose muzzle pressure is probably high by a factor near 2. The body's moment and the jet noise scale with it.
- The body's time shape (two lags) and its 3 ms mixing time are inferred; only its moment is derived. The jet's efficiency, build-up time, spectrum and directivity are published ranges or recalled shapes, not measurements of this rifle.
- The directivity is for a bare muzzle; the birdcage is represented only through the 90° anchor.
- Mechanical levels rest on one published range of impact-noise efficiency (a factor of 10 wide) and inferred loss factors. The gas vent at the piston, the magazine and bone conduction through the stock are not modelled.
- No head, body or rifle shadowing; mono listeners.
- Overlays apply one response to the whole dry signal, so mechanical sounds and the N-wave get the room as if they came from the muzzle with the muzzle's directivity. For the shooter this makes the action's reverberation too loud.
- Overlay reflections use the direct path's waveform with a per-octave gain, not the waveform that leaves in the reflection's direction.
- Rough-ground scattering uses one roughness height and Lambert's law; the directly rendered `ground: true` shot has the weakened specular bounce but not the scattered part.
- `outdoor_range` is an assumed layout. Far-field tails depend almost entirely on what stands around the range, which the model cannot know. There is no diffraction over berms, no wind, turbulence or temperature gradient, and scattering is first order.
- Rooms are empty shoeboxes with averaged surfaces. The octave filter bank is zero-phase, so strongly coloured reflections ring a few milliseconds early at low frequencies. The warehouse response is cut at 4 s.
- The steel plate uses thin-plate modes with approximate higher eigenvalues and a crude radiation model.
- The reference recordings are overloaded and cannot validate the blast. No calibrated pressure record of this rifle was available.
- Checked by measurement and by rendering in a browser. The owner has not yet listened to version 2.

## Sources

- Heckler & Koch USA, *Maintenance Manual for HK416 Enhanced Carbine & Rifle System* (summarised in `../MANUAL_NOTES.md`): muzzle velocity, cyclic rate, piston operation, tungsten buffer, deflector, bolt hold-open.
- P. Dater, Larson Davis "Firearm Sound Briefing": M4 164 dB at 1 m left of the muzzle; HK416 relative to M4; M855 bullet flight noise 148.5 dB at 1 m.
- K. Fansler and E. Schmidt, "The prediction of gun muzzle blast properties utilizing scaling" (BRL, 1983) and Fansler, ARL-TR-1434 (1997): scaling length and directivity form.
- PEW Science, Research Supplement 6.127 (unsuppressed 14.5 in M4A1): secondary blast, qualitative.
- G. B. Whitham, "The flow pattern of a supersonic projectile" (1952): N-wave amplitude and duration.
- M. J. Lighthill (1952); A. P. Dowling and J. E. Ffowcs Williams, *Sound and Sources of Sound* (1983): monopole and dipole radiation of a compact source.
- NASA SP-8072, "Acoustic loads generated by the propulsion system" (1971): acoustic efficiency, spectrum peak and directivity of supersonic jets (recalled).
- F. P. Ricou and D. B. Spalding (1961): jet entrainment.
- E. J. Richards, M. E. Westcott and R. K. Jeyapalan, "On the prediction of impact noise" (J. Sound Vib., 1979 on): radiated fraction of impact energy.
- G. R. Price and J. T. Kalb, AHAAH model (US Army Research Laboratory): the middle ear's limit on stapes displacement.
- J. M. Wunderli and E. M. Salomons (2009), "A model to predict the sound reflection from forests" (recalled, order of magnitude only).
- US Department of Energy, *Range Design Criteria* (2012): typical berm heights (recalled).
- Sennheiser MKH 416 and DPA 4062 data sheets: maximum SPL and bandwidth.
- ISO 9613-1 (air absorption) and ISO 9613-2 Table A.1 (foliage).
- Delany and Bazley (1970); Chien and Soroka (1975): ground impedance and spherical-wave reflection.
- A. W. Leissa, *Vibration of Plates* (1969): free circular plate eigenvalues.
- Allen and Berkley (1979): image-source method; Eyring (1930): decay time.
