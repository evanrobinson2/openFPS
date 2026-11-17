# HK416 D14.5RS: simulated discharge sound

Everything in this folder is synthesised from physics and published numbers. No recording, and nothing derived from a recording, is in this repository. Under openFPS's rules no audio files are committed at all: the sound is the simulation, and `hk416-sound.js` synthesises it in the browser at load.

Credit: carpetshark. Simulation by Claude.

## What is here

| File | What it is |
|---|---|
| `sim.py` | The simulator. Stage A turns physics into tables (`params.json`); stage B turns tables into waveforms. |
| `params.json` | Every derived table: path lists, pulse sizes, ground and air filters, modal tables, room recipes, earmuff filter. Written by `sim.py`. |
| `hk416-sound.js` | Browser port of stage B. Reads `params.json` and synthesises the same shots, mechanical sounds, steel hits and impulse responses at load. |
| `manifest.json` | One entry per rendered output: file, what it is for, true simulated level, scale. |
| `audio/` | Listening renders (FLAC). Written by `sim.py dry` / `overlays`; never committed. |
| `masters/` | 24-bit WAV masters of the dry sounds. Not committed (rebuild them). |
| `compare.py`, `compare/` | Matched comparison against licensed reference recordings you supply locally. Only `js_parity.json` and the simulation-only plot are committed. |
| `verify_js.py`, `verify_js.mjs` | Parity check of the JS port against Python, run under node. |
| `index.html` | Minimal listening page (uses the JS module). Nothing plays until you press Play. |

## Rebuild

From `assets/hk416/`, with Python 3 (numpy, scipy, matplotlib), ffmpeg (FLAC) and node (parity check only):

```
python3 sound/sim.py all        # params.json, audio/, masters/, manifest.json, compare/
python3 sound/sim.py params     # only params.json
python3 sound/sim.py dry        # dry shots, mechanical clips, steel hits
python3 sound/sim.py overlays   # impulse responses and the earmuff filter
python3 sound/sim.py compare    # comparison (needs your own licensed reference recordings for the recording side)
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
- **Playback mapping is not physics.** The shot is 157 dB at the ear and the berm echo is 47 dB below it. Speakers cannot do that, so every file is normalised to −1 dBTP and the page runs a compressor ("ear compression") so the tails stay audible. `manifest.json` and `S.info(buffer)` carry the true level.

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

### 1. Muzzle blast

A Friedlander pulse, p(t) = P (1 − t/T) e^(−t/T), which has zero net impulse and a negative phase of −0.135 P at t = 2T.

| Parameter | Value | Source |
|---|---|---|
| Peak at 1 m, 90° | 164 dB (3170 Pa) | Published: M4, M855, 14.5 in, 1 m left of the muzzle (Dater, Larson Davis "Firearm Sound Briefing"). The same briefing has the HK416 equal to the M4 unsuppressed. The A2 flash hider is included in this figure |
| Positive phase at 1 m, 90° | 0.30 ms | Inferred from published 5.56 rifle A-durations (0.2 to 0.4 ms) |
| Directivity | P ∝ l′(θ) = μ cos θ + √(1 − μ² sin² θ), μ = 0.78 | Fansler and Schmidt muzzle blast scaling. μ is recalled from the literature; I could not re-fetch the report (DTIC returned 403), so treat it as approximate. Front to back is 18 dB |
| Angles used | shooter 174.8°, bystander 97.5°, downrange 2.3° | derived. Fansler's data stops at 150°; the shooter value is an extrapolation |
| Duration against angle | T ∝ l′^0.5 | inferred |
| Distance law, nonlinear | P = P₁/(r s), T = T₁ s, s = √(1 + k ln r), k = (γ+1)/(2γ) · P₁/(p₀ c T₁) | Weak-shock (Landau) lengthening of a spherical N-wave, referenced to 1 m. At 50 m ahead the pulse is 1.65 times longer and 4.3 dB weaker than linear spreading |
| Shock rise | 10 µs ramp, synthesised at 192 kHz, then band-limited to 48 kHz | numerical choice |
| Secondary pulse | −10 dB at 90°, 0.45 ms, 0.7 ms later, μ = 0.3 | Inferred. PEW Science reports a significant secondary (afterburn) blast on unsuppressed 14.5 in 5.56 rifles; the size and timing are mine |
| Jet noise | −22 dB rms re peak, 1.2 ms decay, 800 Hz high-pass | inferred (bore blow-down time) |
| Shot-to-shot spread | 0.7 dB sd | inferred |
| Muzzle velocity | 850 m/s | HK maintenance manual p. 7 (see `../MANUAL_NOTES.md`). I started with 884 m/s (M4 figure) and replaced it |

Resulting peaks (free field): shooter's ear 157.1 dB, bystander 146.7 dB, comparison mics 163.0 and 164.0 dB. Commonly quoted at-ear figures for 5.56 carbines are in the 155 to 160 dB range (not re-checked against a primary source).

**Nonlinear handling, in short:** peak and duration follow weak-shock theory along each path; everything after that is linear (air absorption, ground, rooms). Linear ISO absorption is applied to the shock as well. At 50 m the real shock is thinner than this filter leaves it by roughly a factor of two; at the shooter and bystander the difference is nil.

### 2. Ballistic shock (N-wave)

| Parameter | Value | Source |
|---|---|---|
| Bullet | M855: 5.70 mm, 23.0 mm long, 4.02 g | published |
| Velocity along the path | v = 850 e^(−0.001 x) m/s | inferred fit (about 10 % lost per 100 m) |
| Amplitude and duration | Whitham: Δp = 0.53 p₀ (M²−1)^(1/8) d / (b^(3/4) l^(1/4)), T = 1.82 M b^(1/4) d / (c (M²−1)^(3/8) l^(1/4)) | Whitham 1952 |
| Geometry | the ray leaves the trajectory at acos(1/M); a listener gets the wave only if that ray starts ahead of the muzzle | Mach cone |

Downrange listener: Mach 2.36, miss distance 2.0 m, Δp = 565 Pa (149 dB), T = 0.12 ms, arriving 64.8 ms after the shot; its ground reflection follows 4.6 ms later; the muzzle blast arrives 79 ms after the crack at 135 dB. The same briefing measured 148.5 dB for M855 at 1 m from the path. The shooter and the bystander get no N-wave: their angle from the bore is above 90° − μ = 66°, so the cone never reaches them. Reflections of the N-wave off berms and walls are not modelled.

### 3. Mechanical action

Each event is a sum of decaying modes plus a short contact click, placed at its source on the rifle. Times are after the bullet leaves the muzzle; the cycle is 70.6 ms (850 rpm, the range page's rate; the manual gives 700 to 900).

| Event | Time | Level at 1 m | Notes |
|---|---|---|---|
| Hammer on firing pin | −1.3 ms | 92 dB | barrel time about 1 ms, inferred |
| Piston and rod strike the carrier, unlock | +0.4 ms | 100 dB | short-stroke piston (manual p. 8 to 12); rings on the barrel bending modes |
| Case hits the brass deflector | +11 ms | 88 dB | manual: the case strikes the deflector on the way out |
| Carrier bottoms on the buffer | +21 ms | 101 dB | HK buffer with tungsten granules: modelled as a damped thud (short T60) |
| Buffer spring | +21 ms | 82 dB | standing waves, 41.8 Hz fundamental (k ≈ 350 N/m, 50 g), harmonics 6 to 29 |
| Round stripped from the magazine | +46 ms | 90 dB | scrape |
| Carrier home, bolt locked | +62 ms | 104 dB | cycle − hammer fall (≈ 7 ms) − barrel time |
| Trigger reset (semi) | +120 to 160 ms | 80 dB | shooter cadence, not physics |
| Case lands, bounces twice | +0.79, 1.27, 1.43 s | 78, 72, 66 dB | flight from `socket_eject` at the range page's ejection velocity; lands 2.1 m right |

All levels and decay times are inferred. Frequencies: barrel free-free bending 631, 1740, 3410 Hz (steel tube 368 mm, 18 mm OD, 5.56 mm bore); carrier longitudinal about 15 kHz; case ovalling 8.2 kHz (brass, 0.35 mm wall, 4.5 mm radius).

If `../action/action.json` exists when `params` is built, its event times replace this table (`apply_action_timeline` in `sim.py`). It did not exist when this was built; `params.json` records which timeline was used.

Clips rendered on their own: `cycle`, `case_drop`, `trigger`, `trigger_reset`, `charge` (timed to the glTF `charge` clip), `bolt_lock_back` (empty magazine, manual p. 26), `bolt_release`.

### 4. Propagation

| Parameter | Value | Source |
|---|---|---|
| Atmosphere | 20 °C, 50 % RH, 101.325 kPa, c = 343.2 m/s | stated |
| Air absorption | ISO 9613-1 formula, as a filter per path (dry) or per octave band (overlays) | ISO 9613-1 |
| Spreading | 1/r | |
| Ground | Delany-Bazley impedance, σ = 300 kPa·s/m² (packed dirt, sparse grass), spherical-wave reflection coefficient Q = R_p + (1 − R_p) F(w) | Delany and Bazley 1970; Chien and Soroka 1975. σ is inferred for the range page's dirt |

### 5. Listener perspectives

Shooter's ear (default), bystander, downrange, as in the geometry table. All are mono, a single point with no head or body shadow.

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
| `open_field` | flat ground only | ground model above | ground bounce 7.3 ms after the direct sound at the shooter |
| `range_berm` | the range page: ground, bench top 0.57 m under the muzzle, berm face 60 × 6 m at 59 m | soil berm 0.40, Lambert scattering in 1 m patches | slapback from 0.34 to 0.38 s, −47 dB in energy re the direct sound (about 110 dB SPL) |
| `forest_edge` | tree line 80 m ahead, stand 300 × 120 m | 0.04 trunks/m², radius 0.12 m, single scattering; foliage loss from ISO 9613-2 Table A.1 | a diffuse wash from 0.47 s decaying over about 0.5 s, −65 dB in energy |
| `street_canyon` | street 18 m wide, facades 20 m, firing along it; far facade at 150 m | brick and glass 0.03, asphalt 0.03, facade scattering 0.3 | flutter between the facades (105 ms round trip), diffuse bursts, far slap at 0.87 s |
| `valley` | rock wall 180 m left, forested slope 320 m right, rock head wall 750 m ahead | rock 0.04, forested slope 0.50, 6 m Lambert patches, first order only | echoes at 1.0, 1.9 and 4.4 s, −56 dB in energy |

Absorption coefficients are handbook values for 125 Hz to 4 kHz, extrapolated at 63 Hz, 8 kHz and 16 kHz; the rubber backstop, soil berm and forested slope are inferred. The full tables and the per-band T60 (Eyring and Sabine) are in `params.json` under `overlays.*.persp.*.doc` and in `manifest.json`.

Perspectives: every overlay exists for the shooter. The warehouse and the outdoor overlays also exist for the bystander and the downrange listener. The four small interiors do not (5 m to the side does not fit in them).

**Hearing protection** (`hpd_earmuff`): passive earmuff, NRR 30 class. Mean attenuation 15, 21, 28, 40, 42, 37, 40, 40, 40 dB at 63 Hz to 16 kHz (typical published values for a large-cup muff, recalled; inferred at 63 Hz and 16 kHz), as a 256-tap minimum-phase FIR. Applied after the room. Level-dependent effects at 150 dB+ are ignored.

## Comparison with the real recordings

`python3 sound/sim.py compare` renders the simulation at the two microphone positions (over open ground, semi-automatic, three rounds) and measures both sides the same way. Plots: `compare/compare_waveform_spectrum.png`; numbers: `compare/compare.json`.

The brief described the recordings as close-mic'd and hard-gated. They are not clean pressure records: both are normalised to full scale and overloaded. The MKH 416 clips flat for 7.4 % of the first 10 ms of every shot (164 dB at a microphone rated near 130 dB), and both carry 100 ms or more of noise after each shot at only 15 to 25 dB below peak. So peak shape cannot be validated against them; timing and coarse spectrum can.

| Measure | On gun: recording | On gun: simulation | 1 m left: recording | 1 m left: simulation |
|---|---|---|---|---|
| Shots found | 7 | 3 | 12 (2 × 6; the detector reports 13) | 3 |
| Mean shot spacing | 293 ms | 250 ms | 241 ms | 250 ms |
| 10 to 90 % rise of the first excursion | 10 µs | 21 µs | 115 µs | 21 µs |
| Width of the first excursion | 0.04 ms | 0.19 ms | 0.23 ms | 0.29 ms |
| Time of the largest peak after onset | 12.0 ms | 0.02 ms | 5.6 ms | 0.02 ms |
| Late event 40 to 95 ms after onset | 74.6 ms | 60.8 ms | 60.7 ms | 62.0 ms |
| Time until energy stays 20 dB down | over 100 ms | 8.8 ms | over 100 ms | 7.3 ms |
| 1/3-octave spectrum, rms difference | 3.6 dB | | 4.4 dB | |

Biggest disagreements:

1. **Body.** The recordings stay loud for over 100 ms; the simulated dry shot over open ground is 20 dB down within 9 ms. Part of that is microphone and preamp overload and whatever space the recording was made in; the simulation has only ground. This is the "snap" complaint in reverse: the dry physics really is a crack, and the body a shooter hears comes from the surroundings (overlays) and from the ear's own compression (playback mapping).
2. **Where the peak is.** In the recordings the largest peak comes 6 to 12 ms after the onset, which a muzzle blast cannot do at 0.4 or 1 m; it is consistent with a capsule that overloads on the direct blast and recovers on the ground reflection (the simulated ground bounce arrives 8.1 ms after the direct sound on the gun, 6.6 ms at 1 m).
3. **Late event.** The on-gun recording has a second sharp event 74.6 ms after the shot; the simulation puts the bolt closing at 62 ms (60.8 ms after onset at that mic). At 1 m the two agree (60.7 against 62.0 ms). I did not tune to either.
4. **Spectrum.** Both recordings and the simulation peak near 1.25 kHz. The simulation has 3 to 8 dB less above 4 kHz (clipping adds highs to the recordings) and, at 1 m, 10 dB less below 80 Hz.
5. **Shot spacing** is the shooter's cadence (241 and 293 ms), not physics; the simulation's semi string uses 250 ms.

Adjustments made, and why:

| Change | Reason |
|---|---|
| Muzzle velocity 884 → 850 m/s | HK manual p. 7 for the 14.5 in barrel (published fact replaces the M4 figure) |
| Buffer impact made a damped thud (T60 25 ms and shorter) | manual: tungsten-granule buffer |
| Piston and rod strike, deflector strike, bolt lock-back added as events | manual, cycle of operation |
| Nothing was changed after comparing with the recordings | they are too overloaded to justify a parameter change |

Internal check: the free-field shot convolved with the `open_field` response matches the directly rendered open-ground shot to −14.5 dB (shooter), −22 dB (bystander, downrange). The residual is the overlay's approximation that a reflected blast has the same pulse length as the direct one.

## The JS module

```js
import HK416Sound from './sound/hk416-sound.js';
const S = await HK416Sound.build(ctx);            // fetches params.json next to the module
S.shot('single' | 'semi3' | 'auto1s', { perspective, ground })   // AudioBuffer, peak −1 dBFS
S.mech('cycle' | 'case_drop' | 'trigger' | 'trigger_reset' | 'charge' | 'bolt_lock_back' | 'bolt_release')
S.steel(radius, { dist, seed })                   // nearest of the five plates; seed varies the hit
await S.ir('range_berm', 'shooter')               // AudioBuffer, direct path = 1.0 at sample 0
S.hpd()                                           // earmuff FIR
await S.chain({ overlay, perspective, hpd, ear }) // { input, output, set() }: convolver, earmuffs, compressor
S.info(buffer)                                    // true peak in Pa and dB SPL, Pa per full scale
```

`python3 sound/verify_js.py` runs the module under node and compares all 52 outputs with Python sample by sample. The worst difference is −160 dB relative to peak (steel; everything else is below −238 dB), so the two are the same to floating-point rounding. Synthesis time in node: single shot 10 to 80 ms, 1 s burst up to 0.7 s, impulse responses 4 to 170 ms each. Results are cached; impulse responses are built on first use. Results are in `compare/js_parity.json`.

For a game: fire `S.shot('single')` per round (it carries its own action and case sounds), through one `S.chain`. `auto1s` and `semi3` are fixed strings for listening.

## Known limitations

- Levels are anchored to one published figure (164 dB at 1 m) and one recalled directivity constant. The at-ear level could be off by 3 dB.
- The directivity is for a bare muzzle; the birdcage is represented only through the 90° anchor.
- The secondary pulse, jet noise, every mechanical level and every decay time are inferred, not measured.
- No head, body or rifle shadowing; mono listeners.
- Overlays apply one response to the whole dry signal, so mechanical sounds and the N-wave get the room as if they came from the muzzle with the blast's directivity.
- Rooms are empty shoeboxes with averaged surfaces. The octave filter bank is zero-phase, so strongly coloured reflections ring a few milliseconds early at low frequencies.
- Outdoor overlays are first-order: no berm-to-ground or wall-to-wall paths, no wind, turbulence or temperature gradients. Trees are single scatterers.
- The warehouse response is cut at 4 s, short of its 4.7 s T60.
- The steel plate uses thin-plate modes with approximate higher eigenvalues and a crude radiation model; a plate that swings or falls on its mount is not modelled.
- The comparison recordings are overloaded, so the blast pulse shape is unvalidated.
- Nobody has listened to this yet. It was checked by measurement and by rendering in a browser at zero volume.

## Sources

- Heckler & Koch USA, *Maintenance Manual for HK416 Enhanced Carbine & Rifle System* (summarised in `../MANUAL_NOTES.md`): muzzle velocity, cyclic rate, piston operation, tungsten buffer, deflector, bolt hold-open.
- P. Dater, Larson Davis "Firearm Sound Briefing": M4 164 dB at 1 m left of the muzzle; HK416 relative to M4; M855 bullet flight noise 148.5 dB at 1 m.
- K. Fansler and E. Schmidt, "The prediction of gun muzzle blast properties utilizing scaling" (BRL, 1983) and Fansler, ARL-TR-1434 (1997): scaling length and directivity form.
- PEW Science, Research Supplement 6.127 (unsuppressed 14.5 in M4A1): secondary blast, qualitative.
- G. B. Whitham, "The flow pattern of a supersonic projectile" (1952): N-wave amplitude and duration.
- ISO 9613-1 (air absorption) and ISO 9613-2 Table A.1 (foliage).
- Delany and Bazley (1970); Chien and Soroka (1975): ground impedance and spherical-wave reflection.
- A. W. Leissa, *Vibration of Plates* (1969): free circular plate eigenvalues.
- Allen and Berkley (1979): image-source method; Eyring (1930): decay time.
