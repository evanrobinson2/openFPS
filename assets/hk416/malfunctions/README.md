# HK416 D14.5RS: malfunction simulation

Stoppages for the HK416 model in this folder, tied to the operating cycle in `../action/`: failure to fire, hangfire,
failure to feed, stovepipe, double feed, failure to extract, bolt over-ride and squib. For each one: where in the cycle
it arises and why, how it shows on the model, how likely it is and what moves that, and the clearing sequence as a state
machine and clips. It produces data and a small runtime for a game to play back; it is not game code.

This is education about recognising a stoppage and making a rifle safe. Nothing here is about defeating a safety device
or altering a weapon. Model and simulation credit: carpetshark.

Rebuild everything (Python 3; matplotlib for the plots; node for the test):

```
python3 sim.py                 # about 4 minutes: calibrates, runs the checks, writes the four JSON files and plots/
node test_malfunctions.js      # about 20 seconds: JS against Python, and 22 million simulated rounds against the sourced figures
```

The build is deterministic: the same inputs give byte-identical JSON.

| File | What it is |
|---|---|
| `sim.py` | the model, the calibration and the checks; every parameter is in its `PARAMS` table with a source |
| `content.py` | sources, descriptions, cues, poses, actions, clip keyframes and procedures (prose and step lists, no model) |
| `plots.py` | the plots (called by `sim.py`) |
| `malfunctions.json` | parameters, ammunition and magazine tables, the action-simulation values it rests on, each stoppage's description and pose, calibration targets, a table of rates by condition |
| `procedures.json` | actions, clips (existing and new), procedures, the diagnosis rules, the transition table, clearing times |
| `validation.json` | results of the checks |
| `parity.json` | seeded reference runs from `sim.py` for the JavaScript to reproduce |
| `hk416-malfunctions.js` | self-contained browser and Node runtime (no three.js), seeded, the same model function for function |
| `test_malfunctions.js` | Node checks: parity with `sim.py`, long-run rates against the sourced figures, the state machine |
| `plots/` | five figures |

## Conventions

- Frame and time as in `../action/`: metres, +Z towards the muzzle, +Y up, +X to the shooter's left, origin on the bore axis at
  the upper receiver's front face; time zero is the trigger break. Carrier travel is rearward millimetres.
- A probability is per round fired unless it says otherwise. MRBS is mean rounds between stoppages.
- Source labels: **manual** (HK maintenance manual, page given; see `../notes/MANUAL_NOTES.md`), **published** (a named
  publication), **action** (taken from `../action/action.json`), **inferred** (an engineering estimate), **guess** (no data
  behind it), **calibrated** (solved by `sim.py` so that a published or inferred figure is reproduced; not a prediction).
- The manual has no stoppage drill. Its clearing steps (p. 3), safety rules (p. 4), cycle of operation (pp. 8 to 12),
  gauges (pp. 17 to 24) and function check (p. 26) are used and cited; the drills themselves follow US Army TC 3-22.9.

## A shot as a chain of margins

The manual's cycle has eight steps (p. 8): feeding, chambering, locking, firing, unlocking, extracting, ejecting, cocking.
Each step that can fail is given a margin: what the action simulation says is available, over what is needed. A stoppage
happens when shot-to-shot scatter eats the margin. The scatter is logistic (heavier tails than a normal), so each
probability is `p = 1 / (1 + ratio^k)`, or for the carrier energy `p = 1 / (1 + exp(margin / s))`.

| Cycle step (manual p. 8) | Margin | Clean rifle, from the action simulation | Curve | What moves it |
|---|---|---|---|---|
| 4 firing | hammer energy at the pin / primer all-fire energy | 0.481 J / 0.334 J = 1.44 | k = 32.2 | dust and cold oil in the pin channel, carbon, a firing pin shorter than the 0.53 mm indent, primer hardness |
| 5 unlocking to 8 cocking | carrier kinetic energy left at a given travel (curve from `action.json`) | 9.06 J at the peak; 4.23 J left at 62.2 mm (case clears the port), 3.56 J at 75.5 mm (bolt behind the next round), 3.20 J at 82 mm (bolt catch) | scatter s = 0.30 J | ammunition drive, cold, worn piston rings (energy); dust, carbon, dry running, cold (friction) |
| 6 extracting | rim shear strength x claw condition / case drag when the bolt starts back | 1700 N / 815 N = 2.09 (drag = 0.2 x 3.7 MPa x 1,100 mm^2 from the action simulation) | k = 17.2 | extractor claw gap against its gauges, extractor spring; dust, carbon, a hot chamber, sticky cases |
| 7 ejecting | time the port is open to the case / time the case needs to leave | 28.6 ms / 5.25 ms = 5.4 (window: carrier beyond 62.2 mm; case needs 12 mm sideways at 2.28 m/s) | k = 5.98 | ejector and extractor springs, dust, carbon; a short stroke shortens the window |
| 1 feeding | time the bolt is behind the magazine / time the stack needs to rise | 19.0 ms / about 10 ms with 29 rounds, 4.6 ms with one | k = 15.5 | magazine spring wear, dust in the magazine, how full it is; a short stroke shortens the dwell |
| 1 feeding | feed ramp jam and two-round feed: plain per-round hazards (geometry, not energy) | 6.8e-05 and 3.2e-06 per round, clean, HK steel magazine | x exp(4.36 x dust) | dust, feed-lip damage, magazine type, ammunition |
| 2 chambering, 3 locking | carrier energy on closing / work to seat the round and turn the bolt | 2.98 J / 0.75 J = 3.97 | k = 8.88 | dust and carbon in the chamber, weak buffer spring, a short stroke |

The steepness `k` of each curve is set so that the clean rifle has the baseline probability below; the dust coefficients are
set so that the dust test's counts come out. Hangfire, dud and squib are properties of the round, drawn before the cycle.
A hangfire that fires still runs the cycle. A carrier that stops short of 62.2 mm pushes the fired case back into the chamber;
short of 75.5 mm it closes on an empty chamber; short of 82 mm on the last round it fails to lock open. These three need no
extra parameters: they fall out of the energy curve (`plots/02_carrier_energy_margin.png`).

## The stoppages

| # | Stoppage | In the action simulation's terms | Carrier held at | On the model | The shooter | Clearing |
|---|---|---|---|---|---|---|
| 1 | **Failure to fire (misfire)** (`failure_to_fire`) | Sear release to primer contact runs as normal (8.3 ms). The hammer delivers 0.48 J to the firing pin against a primer all-fire energy of 0.334 J: a ratio of 1.44. Dust, congealed oil or carbon in the firing pin channel lowers the delivered energy; a pin protruding less than the 0.53 mm indent cuts the indent short. The carrier never moves: travel 0 mm, bolt locked, hammer down. | 0 mm | nodes `trigger`; clips `trigger_pull`; props: none | sees: bolt fully forward, port closed by the carrier; nothing ejected. Hears: a dry click: hammer on firing pin. Trigger: normal break, a click, then no reset. **Hazard:** At the click it cannot be told from a hangfire. Keep the muzzle on the backstop. | `immediate_action` (range: `misfire_range`) |
| 2 | **Hangfire (delayed ignition)** (`hangfire`) | The firing train is normal up to the primer. Ignition, which follows primer contact by about 0.2 ms in the action simulation, is delayed by tens of milliseconds up to seconds. The M855 specification holds the whole action time (primer to gas port) to 3 ms at mean plus five standard deviations, so a hangfire is far outside normal ammunition. When it fires, the cycle runs as normal from that moment. | 0 mm | nodes `trigger`, `bolt_carrier`, `bolt_head`; clips `trigger_pull`; props: none | sees: exactly what a misfire shows, until it fires; then a normal ejection. Hears: click ... bang; a gap under a quarter of a second is not noticed. Trigger: normal break. **Hazard:** If the action is opened during the delay the round can fire unlocked or outside the chamber, at the shooter's hand and face. This is the reason for the wait. | `immediate_action` (range: `misfire_range`) |
| 3 | **Failure to feed** (`failure_to_feed`) | Three mechanisms. Short stroke: the carrier has 3.56 J left as it passes the pick-up point at 75.5 mm; if dust, cold or a weak round take more than that, it turns round short of the next round and closes on an empty chamber. Feed ramp jam: the round leaves the lips at the wrong angle and its nose stops below the chamber mouth, with the carrier held at about 45 mm on its way forward. Failure to chamber: the carrier arrives with 2.98 J and needs about 0.75 J to seat the round and turn the bolt; a dirty chamber raises that and the carrier stops about 6 mm short, bolt not turned. | nose jam 45.5 mm, bolt over empty chamber 0 mm, failure to chamber 6.0 mm | nodes `bolt_carrier`, `bolt_head`, `dust_cover`, `mag_round_1_case`, `mag_round_1_bullet`; clips `dust_cover_open`; props: prop_round | sees: feed ramp jam: bolt held about half way, brass and bullet nose-up in the port; empty chamber: bolt forward, everything looks normal; out of battery: carrier a few millimetres short of closed. Hears: shot, then a muffled stop; or a click on the next pull. Trigger: jam or out of battery: dead or soft; empty chamber: a click. **Hazard:** None by itself. Do not hammer the forward assist on a round that will not seat. | `immediate_action` |
| 4 | **Failure to eject (stovepipe)** (`stovepipe`) | The case mouth clears the port when the carrier passes 62.2 mm, 23.5 ms after the trigger break; the bolt comes back past that point at 52.0 ms. The case has that 28.5 ms window to get out and normally needs about 5 ms (12 mm sideways at 2.3 m/s). A fouled or weak ejector slows it; a short stroke shortens the window. Caught, the case is pinched by its head between the bolt face and the front edge of the port with the carrier held at about 27.5 mm. If the carrier never reaches 62.2 mm the case stays on the bolt face and is pushed back into the chamber. | stovepipe 27.5 mm, case in receiver 45.5 mm, rechambered case 0 mm | nodes `bolt_carrier`, `bolt_head`, `dust_cover`; clips `dust_cover_open`; props: prop_case | sees: an empty case sticking out of the ejection port, bolt a few centimetres open; or brass lying lengthwise in the port. Hears: shot, then a soft brassy stop; no case lands. Trigger: dead: the bolt is out of battery (rechambered case: a click). **Hazard:** None by itself. Keep fingers clear of the port; the bolt is under spring load. | `stovepipe_clear` |
| 5 | **Double feed** (`double_feed`) | The cycle is normal to full stroke. On the way forward the bolt strips a round whose nose meets the head of the case still in the chamber: the round is 57.4 mm long, so the bolt face stops that far behind the chamber and the carrier is held at about 68 mm. With two live rounds the carrier stops near 50 mm. | stuck case plus round 68.0 mm, two live 50.0 mm | nodes `bolt_carrier`, `bolt_head`, `dust_cover`, `mag_round_1_case`, `mag_round_1_bullet`; clips `dust_cover_open`; props: prop_case, prop_round, prop_round_2 | sees: bolt held most of the way back; brass in the chamber and a second round behind or beside it. Hears: shot, then a hard stop with no closing. Trigger: dead. **Hazard:** Tap and rack does not clear it: the magazine has to come out first. | `double_feed_clear` |
| 6 | **Failure to extract** (`failure_to_extract`) | Extraction starts as the bolt finishes turning, 3.3 ms after ignition, with 3.7 MPa still in the bore pressing the case wall on the chamber: about 0.8 kN of drag against a rim that shears at roughly 1.7 kN. Dust, a hot chamber or a sticky case raise the drag; a worn claw lowers what the extractor can hold. The carrier itself cycles normally. | empty magazine 82.0 mm, closed 0 mm | nodes `bolt_carrier`, `bolt_head`, `dust_cover`, `bolt_catch`; clips `dust_cover_open`; props: prop_case | sees: last round: bolt locked back with a fired case still in the chamber; no case left the port. Hears: shot with no brass landing. Trigger: a click on the next pull, or the bolt is locked back on the empty magazine. **Hazard:** With rounds in the magazine it becomes a double feed. A torn rim cannot be racked out; it needs a rod from the muzzle. | `immediate_action` |
| 7 | **Bolt over-ride** (`bolt_override`) | A timing race. The bolt is behind the magazine (carrier beyond 75.5 mm) for 19.0 ms. In that time the magazine spring has to lift the stack about 6 mm; with 29 rounds still in the magazine that takes about 10 ms. A weak spring, dust in the magazine or a short stroke narrows the gap. The carrier is held at about 50 mm. | 50.0 mm | nodes `bolt_carrier`, `bolt_head`, `dust_cover`, `charging_handle`; clips `dust_cover_open`, `rack_bound`; props: prop_round | sees: bolt held about half open; a live round high in the port, above the bolt. Hears: shot, then a hard stop. Trigger: dead. **Hazard:** The charging handle is pinned by the round. Forcing it bends the handle. | `bolt_override_clear` |
| 8 | **Squib (bullet lodged in the bore)** (`squib`) | No pressure curve to speak of: the bullet stops before the gas port (242.6 mm from the bolt face), no gas reaches the piston and the carrier stays at 0 mm with the fired case still chambered. | 0 mm | nodes `trigger`; clips `trigger_pull`; props: prop_bullet | sees: bolt forward, nothing ejected; no strike downrange. Hears: a pop, far quieter than a shot. Trigger: normal break. **Hazard:** The bore is blocked. Stop on a pop instead of a bang, less recoil than normal, an action that did not cycle. Do not fire again until a rod has passed through the bore. | `squib_stop` |
| 9 | **Failure to lock back on the last round** (`failure_to_lock_back`) | The follower lifts the bolt catch, which holds the carrier at 82 mm on its way forward (manual p. 26, step 10). A carrier that turns round short of 82 mm, with 3.15 J to spare when clean, never passes the catch. | 0 mm | nodes `bolt_carrier`; props: none | sees: bolt forward where it should be locked open. Hears: click. Trigger: a click on the next pull. **Hazard:** None. A click on an empty rifle. | `immediate_action` |

Variants: `failure_to_fire`: `light_strike`, `dud`; `hangfire`: `delayed`; `failure_to_feed`: `nose_jam`, `bolt_over_empty_chamber`, `failure_to_chamber`; `stovepipe`: `stovepipe`, `case_in_receiver`, `rechambered_case`; `double_feed`: `stuck_case_plus_round`, `two_live`; `failure_to_extract`: `claw_slip`, `torn_rim`; `bolt_override`: `override`; `squib`: `lodged`; `failure_to_lock_back`: `closed_on_empty`.

How to show one: play `HK416Action.sample(t)` as for any shot, but take the carrier from `gun.carrierAt(t)`, which is the action
simulation's own curve (within 0.3 mm) until the carrier, on its way forward, reaches the stop position, and holds there.
`gun.stopTime()` is that moment, for cutting the cycle sound. `gun.pose()` then gives the carrier travel, the bolt angle and
the brass to draw. Do not spawn the ejected case for a stovepipe, a failure to extract or a double feed behind a stuck case.

The cases, loose rounds and cleaning rod are **props the model does not contain** (`prop_case`, `prop_round`, `prop_round_2`,
`prop_bullet`, `prop_rod`): a 5.56 mm case is 44.7 mm long and 9.6 mm across the head, a round 57.4 mm. Each pose is a base
position and a unit axis towards the mouth or nose, in the gun frame. The stop positions and poses are worked out from the
model's own geometry (bolt face at Z = -14 mm in battery, ejection port from -86 to -21 mm, top round in the magazine with its
base at -74 mm) by contact: a stovepiped case is one case diameter thick between the bolt face and the port's front edge, so
the bolt face is 17 mm back and the carrier at 27.5 mm; a round nose-on to a case in the chamber holds the bolt face 57.4 mm
back and the carrier at 68 mm. They are not measured from photographs of real stoppages. The model has no extractor, ejector,
hammer or firing pin nodes, so the part that failed is never seen.

## Probabilities and their sources

### What is published

| Figure | Value | Source |
|---|---|---|
| HK416, extreme dust test, fall 2007: class 1 and 2 weapon stoppages in 60,000 rounds (10 rifles x 6,000) | 210: failure to feed 141, to chamber 7, to fire 5, to extract 3, to eject 49, bolt locked to the rear 0, bolt failed to lock to the rear 3, other 2 | Army briefing, slide 7 |
| The same test: magazine stoppages; class 3 stoppages; total | 9; 14; 233 (MRBS 274 on class 1 and 2) | Army briefing, slide 6; CRS RS22888 |
| The same test, other rifles (all stoppages) | XM8 127, SCAR 226, M4 882; M4 magazine stoppages 239, and 148 in the summer run | Army briefing, slide 6; CRS RS22888 |
| Test protocol | 25 h of dusting per rifle, 120-round cycles, wipe and lubricate every 600 rounds, full clean every 1,200 | Army briefing, slides 2 to 5; army.mil, 18 December 2007 |
| Stoppage classes | class 1: cleared by the shooter within 10 s; class 2: longer; class 3: needs an armourer | army.mil, 18 December 2007 |
| Repeatability | M4: 296 class 1 and 2 stoppages in the summer run, 863 in the fall run, same protocol | Army briefing, slides 6 and 12 |
| New M4s and M16s, Army laboratory test, 2005 to 2006 | about 5,000 rounds between stoppages | CRS RS22888 |
| M4 requirement (1990, M855); M4A1 with M855A1 (2013); Individual Carbine requirement | 600; 1,691; 3,592 MRBS | Military.com, 14 June 2013, as summarised in Wikipedia "Individual Carbine" |
| M4, USMC test, 2002 | 186 failures in 69,000 rounds | CRS RS22888 |
| M855 lot acceptance: function and casualty, 800 rounds per weapon type | accept at 1 misfire, reject at 3; a bullet left in the bore rejects the lot; failure to extract and weapon stoppage: accept 0, reject 2 | MIL-C-63989C, Tables III and IV |
| M855 action time (primer to gas port); port pressure; velocity | mean + 5 sd at most 3 ms; mean - 3 sd at least 12,700 psi and within 2,000 psi at -65 and +125 F; 3,000 +/- 40 ft/s, sd at most 40 | MIL-C-63989C 3.15, 3.8, 3.10.3, 3.6 |
| HK steel against aluminium magazines; no gas in the receiver; cooling limit | the manual guarantees reliability only with the steel magazine; it credits the piston system with a longer interval between stoppages; let the rifle cool after 250 rounds in under 3 minutes | manual pp. 5, 6, 4 |
| Firing pin protrusion; extractor claw gauges | 0.90 to 1.10 mm; 1.28 mm GO, 1.59 mm NO-GO | manual pp. 17, 21, 23, 24 |

No stoppage rate for a clean HK416 was found, and none by type for any rifle outside the dust test. Nothing usable was
found for hangfire or squib rates in modern factory ammunition; the specification only bounds them (one bullet left in the
bore in the sample rejects a lot).

### What is calibrated, and to what

1. **Clean baseline (assumed).** A clean HK416 on the test's maintenance schedule is set to 5000 MRBS, the Army laboratory
   figure for new M4s and M16s. The split by type is a judgement that follows the dust test's proportions loosely. Seven
   fresh-rifle targets (`p_*_clean` in the parameter table) carry the split; one common factor (`clean_scale` = 0.800) brings
   the total, with fouling between cleanings and a warm barrel, to the target.
2. **Dust (published).** With `dust: 1` and the test's protocol, one coefficient per type is solved so the expected count
   equals the HK416's: carrier friction for the 3 failures to lock back, hammer energy loss for the 5 failures to fire,
   case drag for the 3 failures to extract, ejection speed for the 49 failures to eject, chambering work for the 7 failures
   to chamber, and the feed-jam exponent for the 150 feed stoppages (141 weapon plus 9 magazine).
3. **Aluminium magazines (published, another rifle).** Their extra dust exponent is solved so the dust test gains 193.5 feed
   stoppages per 60,000 rounds, the midpoint of the M4's magazine stoppages in the two runs.

How the briefing's categories map onto this simulation (an inference; the briefing does not define them further):

- FFD: `failure_to_feed:nose_jam`, `failure_to_feed:bolt_over_empty_chamber`, `bolt_override`, `double_feed:two_live`
- FTC: `failure_to_feed:failure_to_chamber`
- FFR: `failure_to_fire`, `hangfire (a perceived one)`, `squib`
- FXT: `failure_to_extract`, `double_feed:stuck_case_plus_round`
- FEJ: `stovepipe`
- FBR: `failure_to_lock_back`

### Results

The dust test, simulated in full (40 repeats of 10 rifles x 6,000 rounds, seeds 1000 .. 1399, every stoppage cleared by the
state machine before the next shot). These match because they were calibrated to; the check is that the full simulation,
with its state machine and maintenance schedule, lands where the per-round arithmetic said it would.

| Type | Published (one run) | Poisson 95 % of that count | Simulated, mean per 60,000 | Analytic | Monte Carlo standard error |
|---|---|---|---|---|---|
| failure to feed, with magazine stoppages | 150 | 126.95 to 176.02 | 152.7 | 150.0 | 1.95 |
| failure to chamber | 7 | 2.8 to 14.42 | 7.7 | 7.0 | 0.44 |
| failure to fire | 5 | 1.61 to 11.67 | 5.3 | 5.0 | 0.36 |
| failure to extract | 3 | 0.6 to 8.77 | 2.5 | 3.0 | 0.25 |
| failure to eject | 49 | 36.25 to 64.78 | 48.9 | 49.0 | 1.11 |
| bolt failed to lock to the rear | 3 | 0.6 to 8.77 | 2.9 | 2.9 | 0.27 |
| **all class 1 and 2** | 217 (219 less 2 "other") | | **219.9** (MRBS 273 against 276) | | |

What the simulation makes of the briefing's single "failure to feed" figure (an inference, per 60,000 rounds): feed ramp jams
96, bolt over-rides 39, bolt closed on an empty chamber after a short stroke 14, two-round feeds 4. Of the failures to
eject: stovepipes 34, case loose in the receiver 14, fired case pushed back into the chamber 0.6. Of the failures to extract,
2.4 became double feeds because a round was fed behind the case.

Not calibrated, so worth reading as predictions:

- **Stoppages bunch up before each wipe.** The second half of each 600-round interval has 5.0 times the stoppages of the
  first. The briefing (slide 9) says only that cleaning appeared to help; it gives no number.
- **Stoppage classes.** By clearing time the simulation gives 207.7 class 1, 11.0 class 2 and 1.2 class 3 per 60,000 rounds.
  Published: 219 class 1 and 2 together, 14 class 3. The simulated class 3 are only cases that need a rod and squibs; the
  briefing does not say what its 14 were, and parts breakage is not modelled, so the simulation is low here.

Aluminium magazines add 197 feed stoppages per 60,000 rounds in dust (calibrated to 193.5; the M4's were 148 and 239).

Clean rifle, same protocol without dust (300 rifles, 1,800,000 rounds): 353 stoppages, **5099 MRBS** (analytic 4998; target 5000).
By type: bolt failed to lock to the rear 19, failure to eject 88, failure to feed 154, failure to fire 61, failure to chamber 10, failure to extract 21. For context only: the M4's 1990 requirement was 600 MRBS, the M4A1 measured 1,691 with M855A1 in 2013, and
the Individual Carbine requirement was 3,592.

The M855 rates sit comfortably inside the lot acceptance plan, which is all that can be said for them: a lot at the
simulated rates passes the first 800-round sample with probability 0.9998 on misfires (2.8e-05 per round), 0.9996 on a bullet left
in the bore (5e-07) and 0.9974 on failures to extract (3.2e-06). The action simulation's primer-to-port time is 0.97 ms against the
specification's 3 ms limit.

### How the rates shift

Analytic, averaged over a 30-round magazine, one thing changed at a time. Everything below the first row rests on inferred
or guessed sensitivities (see the parameter table); only the two dust rows at the test's own conditions are tied to data.

| Condition | MRBS | fail to feed | bolt over-ride | stovepipe | double feed | fail to extract | fail to fire | hangfire | squib |
|---|---|---|---|---|---|---|---|---|---|
| clean, lubricated, M855, HK steel magazine, 20 C | 5,600 | 7.6e-05 | 1.7e-05 | 4.1e-05 | 6.2e-06 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| 600 rounds since lubrication, 1,200 since cleaning | 4,898 | 8.4e-05 | 1.9e-05 | 4.9e-05 | 1.0e-05 | 2.5e-07 | 3.1e-05 | 2.0e-06 | 5.0e-07 |
| run dry | 4,917 | 8.6e-05 | 3.0e-05 | 4.2e-05 | 6.2e-06 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| dust 0.25, just wiped | 4,398 | 1.1e-04 | 2.2e-05 | 5.1e-05 | 7.9e-06 | 1.2e-07 | 3.0e-05 | 2.0e-06 | 5.0e-07 |
| dust 0.5, 300 rounds since the wipe | 1,714 | 3.2e-04 | 6.3e-05 | 1.2e-04 | 2.0e-05 | 2.4e-07 | 4.0e-05 | 2.0e-06 | 5.0e-07 |
| dust 1 (Aberdeen), just wiped | 1,950 | 2.9e-04 | 5.3e-05 | 1.1e-04 | 1.7e-05 | 1.9e-07 | 3.7e-05 | 2.0e-06 | 5.0e-07 |
| dust 1 (Aberdeen), 600 rounds since the wipe | 83 | 0.0061 | 0.0022 | 0.0031 | 2.7e-04 | 1.0e-06 | 1.5e-04 | 2.0e-06 | 5.0e-07 |
| dust 1, aluminium magazine, 600 since the wipe | 40 | 0.017 | 0.0037 | 0.0031 | 7.8e-04 | 1.0e-06 | 1.5e-04 | 2.0e-06 | 5.0e-07 |
| -54 C | 580 | 5.7e-04 | 7.2e-04 | 9.6e-05 | 6.2e-06 | 1.1e-07 | 2.6e-04 | 2.0e-06 | 5.0e-07 |
| +52 C | 5,953 | 7.2e-05 | 1.2e-05 | 4.0e-05 | 6.2e-06 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| barrel at the manual's heat limit (250 rounds in 3 minutes) | 4,743 | 7.6e-05 | 1.7e-05 | 4.1e-05 | 3.7e-05 | 1.2e-06 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| commercial .223 | 2,974 | 1.4e-04 | 9.4e-05 | 5.0e-05 | 6.2e-06 | 1.1e-07 | 3.0e-05 | 3.0e-06 | 1.0e-06 |
| steel-cased import | 1,234 | 2.1e-04 | 1.6e-04 | 5.8e-05 | 7.4e-05 | 2.5e-06 | 2.7e-04 | 1.0e-05 | 2.0e-06 |
| old, damp or reloaded ammunition | 127 | 6.5e-04 | 7.0e-04 | 1.2e-04 | 1.0e-05 | 2.5e-07 | 0.005 | 0.001 | 3.0e-04 |
| aluminium magazine, clean | 4,695 | 1.1e-04 | 1.7e-05 | 4.1e-05 | 7.7e-06 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| magazine spring worn (1.0) | 446 | 7.6e-05 | 0.0021 | 4.1e-05 | 6.2e-06 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| feed lips damaged (0.5) | 678 | 0.0011 | 1.7e-05 | 4.1e-05 | 3.2e-04 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| extractor claw gap 1.80 mm (NO-GO is 1.59) | 147 | 7.6e-05 | 1.7e-05 | 4.1e-05 | 0.0064 | 2.2e-04 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| weak ejector spring (1.0) | 377 | 7.5e-05 | 1.7e-05 | 0.0025 | 6.2e-06 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| piston rings worn (1.0) | 36 | 0.011 | 0.014 | 0.0017 | 6.1e-06 | 1.5e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| piston rings worn, commercial .223, -20 C | 2 | 0.28 | 0.18 | 0.057 | 3.5e-06 | 1.2e-06 | 3.2e-05 | 3.0e-06 | 1.0e-06 |
| weak buffer spring (1.0) | 3,519 | 1.8e-04 | 1.7e-05 | 4.1e-05 | 6.2e-06 | 1.1e-07 | 2.8e-05 | 2.0e-06 | 5.0e-07 |
| firing pin protrusion 0.45 mm (GO is 0.90) | 85 | 7.5e-05 | 1.7e-05 | 4.0e-05 | 6.1e-06 | 1.1e-07 | 0.012 | 2.0e-06 | 5.0e-07 |

"Fail to extract" in this table is only the case left in the chamber with nothing fed behind it; with rounds in the magazine
a failure to extract shows as a double feed. The runtime inputs behind these rows:

| Input (`create()` option or state) | Range | What it does |
|---|---|---|
| `dust` | 0 to 1 | 0 is a clean range, 1 the Aberdeen dust chamber. The rifle carries 30 % of the load straight after a wipe and lubrication, rising to all of it at 600 rounds (`state.nLube`) |
| `state.nLube`, `state.nClean` | rounds | rounds since the last wipe and lubrication, and since the last full clean (carbon index 1 at 1,200); `gun.maintain('wipe_lube' or 'clean')` resets them |
| `dry` | true or false | run without lubricant: more carrier friction |
| `ambientC` | -54 to 52 | cold lowers the drive and thickens the oil; heat raises the drive slightly |
| `state.heatK` | kelvin above ambient | barrel heat: +2 K a shot, cooling over 10 minutes; 432 K is the manual's limit (250 rounds in 3 minutes, p. 4). It raises case drag only |
| `ammo` | `m855`, `commercial_223`, `steel_case`, `degraded` | drive energy, dud, hangfire and squib rates, primer hardness, case drag |
| `magType`, `magSpringWear`, `magLipDamage`, `magSeated` | `hk_steel`, `gi_aluminium`; 0 to 1; 0 to 1; true or false | feed jams, two-round feeds and the over-ride timing; an unlatched magazine feeds nothing until tapped |
| `extractorGapMm`, `extractorSpringWeak` | mm; 0 to 1 | claw capacity: full between the 1.28 and 1.59 mm gauges, falling outside them |
| `ejectorWeak`, `bufferSpringWeak`, `pistonRingsWorn` | 0 to 1 | ejection speed; closing energy (manual p. 26); drive energy (manual p. 27) |
| `firingPinProtrusionMm` | mm | no effect inside the gauge limits (0.90 to 1.10 mm); below the 0.53 mm indent it cuts the strike short |
| `mode` | `range`, `military` | on a range a click is followed by a 30 s wait before the action is opened |

Ammunition table (all guesses except that M855 is the action simulation's own load):

| `ammo` | Drive energy | Dud | Hangfire | Squib | Primer hardness | Case drag | Feed jams |
|---|---|---|---|---|---|---|---|
| `m855`: M855 ball, in specification | x1.00 | 2e-05 | 2e-06 | 5e-07 | x1.00 | x1.00 | x1.0 |
| `commercial_223`: Commercial .223 ball | x0.92 | 3e-05 | 3e-06 | 1e-06 | x0.90 | x1.00 | x1.0 |
| `steel_case`: Steel-cased import | x0.90 | 1e-04 | 1e-05 | 2e-06 | x1.10 | x1.20 | x1.2 |
| `degraded`: Old, damp or reloaded (the manual forbids reloads, p. 26) | x0.85 | 5e-03 | 1e-03 | 3e-04 | x1.00 | x1.05 | x1.5 |

A hangfire's delay is lognormal with a median of 80 ms (95 % under 0.58 s); under 0.25 s the shooter notices nothing and the
shot simply goes. A squib leaves the bullet 20 to 200 mm down the bore, short of the gas port, which is why the action does
not cycle.

## Clearing: procedures, state machine, clips

### Procedures

The manual gives the clearing sequence (p. 3: safe, magazine out, charging handle with the port towards the ground, bolt
catch, inspect by eye and with a rod) and nothing on stoppages. The drills are from US Army TC 3-22.9 (May 2016), chapter 8:
immediate action (para 8-35) and remedial action (para 8-36). **Their step order and paragraph numbers were read from a
secondary summary, because the publication could not be opened while this was built; check them against the TC before
relying on them.** The misfire wait and the squib response are standard range practice.

| Procedure | When | Steps | End | Source |
|---|---|---|---|---|
| **Immediate action: tap, rack, reassess** (`immediate_action`) | The hammer fell with a click and nothing happened, and the cause is not known. Not for a pop or weak shot. | `tap`, `rack`, `reassess` | ready; then `remedial_clear` | TC 3-22.9 (2016) para 8-35, as summarised; the motions are those of the manual's loading note (p. 8) and clearing step 4 (p. 3) |
| **Misfire on a range: wait, then tap, rack, reassess** (`misfire_range`) | Click, no bang, no recoil, on a range where nothing is gained by hurrying. | `wait` (30 s), `tap`, `rack`, `reassess` | ready; then `remedial_clear` | standard range practice for a possible hangfire, then TC 3-22.9 para 8-35 |
| **Stove pipe** (`stovepipe_clear`) | A case is standing in, or lying in, the ejection port and the trigger is dead. | `sweep_case`, `rack`, `reassess` | ready; then `remedial_clear` | TC 3-22.9 (2016) para 8-36 remedial action, stove pipe, as summarised |
| **Double feed** (`double_feed_clear`) | Brass and a second round are both at the chamber, or immediate action has failed twice. | `strip_mag`, `rack`, `rack`, `lock_back`, `inspect_chamber` -> `stuck_case_rod` if not clear, `insert_mag`, `release_bolt`, `reassess` | ready; then `stuck_case_rod` | TC 3-22.9 (2016) para 8-36 remedial action, double feed, as summarised: magazine out, clear, confirm, fresh magazine, chamber. Many instructors lock the bolt back first to take the spring off the wedged rounds |
| **Remedial action** (`remedial_clear`) | Immediate action has failed twice, or the trigger will not press, or it feels soft. | `strip_mag`, `rack`, `rack`, `lock_back`, `inspect_chamber` -> `stuck_case_rod` if not clear, `insert_mag`, `release_bolt`, `reassess` | ready; then `stuck_case_rod` | TC 3-22.9 (2016) para 8-36, as summarised: look, remove the magazine, clear, inspect, then act on what is found |
| **Bolt over-ride** (`bolt_override_clear`) | A round is wedged above the bolt and the charging handle is bound. | `strip_mag`, `handle_strike`, `hold_bolt_strike` (if handle bound), `lock_back`, `inspect_chamber` -> `stuck_case_rod` if not clear, `insert_mag`, `release_bolt`, `reassess` | ready; then `remedial_clear` | TC 3-22.9 (2016) para 8-36 remedial action, bolt override, as summarised |
| **Pop or weak shot: stop, unload, prove the bore** (`squib_stop`) | A pop or weak report, little recoil, the action did not cycle. Any one of these is enough to stop. | `strip_mag`, `lock_back`, `safe`, `inspect_chamber`, `check_bore`, `rod` | made safe | standard range practice; the unloading and the rod check are the manual's clearing steps 2 to 6 (p. 3), and a clear bore is one of its conditions for handling (p. 4, rule 3) |
| **Case stuck in the chamber** (`stuck_case_rod`) | A fired case is still in the chamber and racking does not bring it out. | `strip_mag` (if mag in), `lock_back`, `safe`, `rod`, `inspect_chamber`, `selector_fire`, `insert_mag`, `release_bolt`, `reassess` | ready | the manual's clearing steps (p. 3) and its tool list, which includes a 5.56 mm broken shell extractor (p. 17) |
| **Reload** (`reload`) | The magazine is empty: bolt locked open, or a rack shows the follower. | `strip_mag` (if mag in), `insert_mag`, `release_bolt` (if bolt open), `rack` (if bolt closed), `reassess` | ready; then `remedial_clear` | manual p. 8 (loading) and p. 26 (bolt catch) |

Diagnosis uses only what the shooter can see (`gun.observe()`), first match wins:

| Sees | Procedure | Why |
|---|---|---|
| report: pop | `squib_stop` | a pop or weak shot is never cleared by racking and firing |
| port: case in port | `stovepipe_clear` | brass in the port |
| port: case loose in port | `stovepipe_clear` | brass in the port |
| port: brass and round | `double_feed_clear` | two things at the chamber |
| port: two rounds | `double_feed_clear` | two things at the chamber |
| port: round above bolt | `bolt_override_clear` | round above the bolt, handle bound |
| port: round nose up | `remedial_clear` | trigger dead, bolt held open by a round |
| port: out of battery | `remedial_clear` | trigger soft, bolt not closed |
| port: bolt held open, mag: in | `reload` | bolt locked open on the follower |
| port: bolt held open, mag: out | `reload` | bolt locked open, no magazine |
| port: closed, trigger: click | `immediate_action` | click with the bolt closed (on a range: misfire_range, to cover a hangfire) |
| port: closed | `immediate_action` | bolt closed, rifle not ready |

After two immediate actions that leave the rifle not ready, the next is `remedial_clear` (TC 3-22.9 para 8-36, as summarised).
In `range` mode the first response to a click is `misfire_range`.

Three things the state machine teaches by consequence, each checked in `test_malfunctions.js`:

- **A pop is not a click.** Tap, rack and fire after a squib returns `fired_into_obstruction` and the rifle is out of
  service. Nothing further is simulated.
- **The wait is for the hangfire.** If the action is opened while a hangfire is pending, the result is
  `hangfire_fired_with_the_action_open` and the simulation stops. Forced perceptible hangfires: with the 30 s wait, 0 of 400
  were opened early; with immediate action, 175 of 400.
- **A double feed is not racked out.** `rack` with the magazine in returns `rounds_pinned_magazine_must_come_out`.

### State machine

The rifle's state: `chamber` (live, empty, dud, fired, stuck, stuck_torn), `feedway` (clear, nose_jam, stovepipe, case_loose, round_behind_case, two_rounds, round_over_bolt), `bolt` (closed, out_of_battery, blocked, held_open), `hammer`, `bore` (clear, obstructed), `selector`, `status` (ok, needs_inspection, out_of_service), `mag` (present, seated, rounds, type), `carrierMm`, and a pending hangfire. Ready means: status ok, chamber live, bolt closed, feedway clear, bore clear, hammer cocked, selector fire, no hangfire pending.

The transition table, with the random outcomes taken at their likely value (the full table with events is `transitions` in
`procedures.json`):

| Stoppage as found | chamber / feedway / bolt / hammer | Sees | `tap` | `rack` | `lock_back` | other |
|---|---|---|---|---|---|---|
| failure_to_fire | dud / clear / closed / down | closed | no change | **ready** | empty / clear / held_open | `safe`: no: selector will not turn hammer not cocked |
| squib | fired / clear / closed / down, bore obstructed | closed | no change | live / clear / closed | empty / clear / held_open | `safe`: no: selector will not turn hammer not cocked |
| failure_to_feed:nose_jam | empty / nose_jam / blocked / cocked | round nose up | no change | **ready** | empty / clear / held_open | - |
| failure_to_feed:bolt_over_empty_chamber | empty / clear / closed / cocked | closed | no change | **ready** | empty / clear / held_open | - |
| failure_to_feed:failure_to_chamber | live / clear / out_of_battery / cocked | out of battery | no change | **ready** | empty / clear / held_open | `forward_assist`: **ready** |
| stovepipe:stovepipe | empty / stovepipe / blocked / cocked | case in port | no change | **ready** | empty / clear / held_open | `sweep_case`: **ready** |
| stovepipe:rechambered_case | fired / clear / closed / cocked | closed | no change | **ready** | empty / clear / held_open | - |
| double_feed:stuck_case_plus_round | stuck / round_behind_case / blocked / cocked | brass and round | no change | stuck / round_behind_case / blocked | stuck / round_behind_case / held_open | - |
| double_feed:two_live | empty / two_rounds / blocked / cocked | two rounds | no change | empty / two_rounds / blocked | empty / two_rounds / held_open | - |
| failure_to_extract (magazine empty) | stuck / clear / held_open / cocked | bolt held open | no change | empty / clear / held_open | empty / clear / held_open | - |
| bolt_override | empty / round_over_bolt / blocked / cocked | round above bolt | no change | no: charging handle bound | no: charging handle bound | `handle_strike`: **ready** |
| failure_to_lock_back | empty / clear / closed / cocked | closed | no change | empty / clear / held_open | empty / clear / held_open | - |

### Actions and clips

Each action takes a fixed time (a guess), which decides the stoppage class. `anim` names an existing clip of the model or a new
motion below.

| Action | Seconds | Hands | Clips |
|---|---|---|---|
| `tap` | 0.4 | Support-hand palm strikes the magazine floorplate upward, then tugs down to prove it is latched. | `mag_tap` |
| `rack` | 0.9 | Support hand pulls the charging handle fully to the rear and lets it go; do not ride it forward (manual p. 8). Port towards the ground, watch what comes out (manual p. 3, step 4). | `rack_full` |
| `reassess` | 0.5 | Both hands back on the rifle, eyes to the ejection port, then to the target. Fire only if the target still warrants it. | - |
| `lock_back` | 1.2 | Hold the charging handle to the rear and press the bolt catch in (manual p. 3, step 5); ease the handle forward. | `lock_back` |
| `strip_mag` | 0.9 | Press the magazine release and pull the magazine out (manual p. 3, step 3). In a double feed it is pinned and needs a firm pull. | `mag_release`, `mag_out` |
| `insert_mag` | 1.2 | Seat a loaded magazine until the catch engages its recess (manual p. 8), then tug it. | `mag_in` |
| `release_bolt` | 0.3 | Press the bolt catch. The carrier runs forward from 82 mm and chambers a round (manual p. 26, step 2). | `bolt_catch`, `release_bolt` |
| `sweep_case` | 0.8 | Support hand grasps the trapped case and pulls it out of the port; the bolt goes forward. | `sweep_case` |
| `handle_strike` | 1.5 | Magazine out. Pull the charging handle as far back as it will go, then strike it forward with the palm so the bolt is driven back off the round. | `rack_bound`, `handle_strike` |
| `hold_bolt_strike` | 3.0 | Pull the handle to the rear again, hold the bolt back through the port with a tool or a finger, and send the handle forward sharply. | `handle_strike` |
| `forward_assist` | 0.3 | One light tap. The manual treats a bolt that moves under the forward assist as a symptom: dirty chamber, damaged round or weak buffer spring (p. 26, step 3). If it does not close, rack instead. | `forward_assist` |
| `wait` | 30.0 | Nothing moves. Rifle shouldered and pointed at the backstop, finger off the trigger. | - |
| `safe` | 0.3 | Thumb rotates the selector to safe. It only turns with the hammer cocked (manual p. 3, step 2). | `safety_to_safe` |
| `selector_fire` | 0.3 | Thumb rotates the selector to semi. | `safety_to_fire` |
| `inspect_chamber` | 1.5 | Bolt locked back; look through the ejection port into the chamber and the magazine well (manual p. 3, step 6). | - |
| `check_bore` | 8.0 | Rifle unloaded and locked open. Pass a cleaning rod through the bore (manual p. 3, step 6, the physical check). If it stops short, the bore is blocked. | `rod_probe` |
| `rod` | 60.0 | Rifle unloaded, bolt locked back. A cleaning rod from the muzzle pushes the stuck case out, or drives a lodged bullet back out through the chamber. After a squib the barrel is inspected before the rifle is used again. | `rod_probe` |

Existing clips reused as they are: `charge`, `dust_cover_open`, `mag_release`, `mag_out`, `mag_in`, `bolt_catch`, `safety_to_fire`, `safety_to_safe`, `trigger_pull`. The `charge` clip draws the
carrier 75 mm, short of the 95 mm stroke (noted in `../action/README.md`), so racking uses `rack_full` instead.

New motions, as keyframe data in `model/build.py`'s `key()` format (24 fps; `loc` in mm from the rest pose with L towards the
muzzle, S to the shooter's left, Z up; `rot` in degrees). They are **data for the model recipe to bake; they have not been
added to `build.py`, baked or checked for clearance.** `x0` is the carrier travel the stoppage left, `x1` where it ends up.
`HK416Malfunctions.motion(name, {x0, x1})` resolves the symbols and `sampleMotion()` interpolates.

| Motion | Tracks (node, channel: frame value ...) | Note |
|---|---|---|
| `mag_tap` | `mag_body` loc Z: 1→z0 3→0.6 5→0.0 7→-0.8 9→0.0 | an unlatched magazine starts 6 mm low (z0 = -6), a latched one at z0 = 0 |
| `rack_full` | `charging_handle` loc L: 1→0 9→-95.0 12→-95.0 14→0; `bolt_carrier` loc L: 1→-x0 9→-95.0 12→-95.0 14→-x1; `dust_cover` rot Y: 1→-175 14→-175 | the charge clip extended to the 95 mm stroke of the action simulation, from any starting position; released, the carrier closes in two frames |
| `lock_back` | `charging_handle` loc L: 1→0 8→-95.0 14→-95.0 20→0; `bolt_carrier` loc L: 1→-x0 8→-95.0 14→-95.0 16→-82.0 20→-82.0; `bolt_catch` rot Y: 10→0 13→5.5 20→5.5; `dust_cover` rot Y: 1→-175 20→-175 | handle to the buffer stop, carrier caught at 82 mm on the way forward; the handle returns alone |
| `release_bolt` | `bolt_catch` rot Y: 1→5.5 3→0; `bolt_carrier` loc L: 1→-82.0 2→-82.0 3→-x1 6→-x1 | the carrier closes from 82 mm in about 43 ms (one frame); for exact timing follow action.json from where carrier_mm falls through 82 |
| `rack_bound` | `charging_handle` loc L: 1→0 4→-8.0 7→-8.0 10→0 | bolt over-ride: the handle moves 8 mm and stops against the round |
| `handle_strike` | `charging_handle` loc L: 1→0 8→-x0 12→-x0 14→0; `bolt_carrier` loc L: 1→-x0 12→-x0 14→-95.0 17→-95.0 19→-x1 | handle drawn to where the round stops it, then struck forward; the carrier jumps back off the round and closes |
| `sweep_case` | `prop_case` loc S: 1→0 8→-60.0; `prop_case` loc Z: 1→0 8→-25.0; `bolt_carrier` loc L: 1→-x0 8→-x0 10→-x1 | prop_case leaves the port to the right and down; the carrier then closes |
| `forward_assist` | `forward_assist_button` loc L: 1→0 3→6.0 6→0; `bolt_carrier` loc L: 1→-x0 3→-x1 6→-x1 | the button travels 6 mm inwards; in build.py its axis is 4 degrees off L, (L, S, Z) = (0.997, 0.073, 0), keyed here along L only |
| `rod_probe` | `prop_rod` loc L: 1→0 48→-depth | prop_rod enters at socket_muzzle and travels down the bore; on a squib it stops at the bullet (depth = 368 - 34 - lodgedMm), otherwise at the bolt face (382 mm) |

Clearing times from the state machine (400 forced stoppages each; median and 90th percentile, seconds), and the class that gives:

| Stoppage | First procedure | Median | 90 % | Class |
|---|---|---|---|---|
| `failure_to_fire:dud` | `immediate_action` | 1.8 | 1.8 | 1 |
| `failure_to_fire:light_strike` | `immediate_action` | 1.8 | 1.8 | 1 |
| `failure_to_feed:nose_jam` | `remedial_clear` | 7.4 | 7.4 | 1 |
| `failure_to_feed:bolt_over_empty_chamber` | `immediate_action` | 1.8 | 1.8 | 1 |
| `failure_to_feed:failure_to_chamber` | `remedial_clear` | 7.4 | 7.4 | 1 |
| `stovepipe:stovepipe` | `stovepipe_clear` | 2.2 | 2.2 | 1 |
| `stovepipe:case_in_receiver` | `stovepipe_clear` | 2.2 | 2.2 | 1 |
| `stovepipe:rechambered_case` | `immediate_action` | 1.8 | 1.8 | 1 |
| `double_feed:stuck_case_plus_round` | `double_feed_clear` | 7.4 | 70.7 | 1 or 2; 3 when racking does not bring the case out |
| `double_feed:two_live` | `double_feed_clear` | 7.4 | 7.4 | 1 |
| `failure_to_extract:claw_slip` | `reload` | 11.2 | 11.2 | 2; 3 when racking does not bring the case out |
| `failure_to_extract:torn_rim` | `reload` | 74.5 | 74.5 | 3 (rod) |
| `bolt_override` | `bolt_override_clear` | 7.1 | 10.1 | 1 or 2 |
| `squib` | `squib_stop` | 71.9 | 71.9 | 3 |
| `failure_to_lock_back` | `immediate_action` | 5.6 | 5.6 | 1 |

In `range` mode a misfire adds the 30 s wait (31.8 s in all).

## Runtime API (`hk416-malfunctions.js`)

```js
const M = HK416Malfunctions;                                   // or require('./hk416-malfunctions.js')
await M.load('malfunctions.json', 'procedures.json');          // or M.use(malfunctionsJson, proceduresJson)
const gun = M.create({ seed: 7, dust: 0.5, ammo: 'm855', magType: 'hk_steel', mode: 'range' });
const r = gun.fire();                  // one trigger press
```

- `create(opts)`: `seed` (default 1) plus any input from the table above. The generator is mulberry32, the one
  `hk416-action.js` uses; the same seed and the same calls give the same history, in the browser, in Node and in `sim.py`.
- `gun.fire({ force })` returns `{ outcome, variant, stoppage, fired, report, trigger, travelMm, shortStroke }`. `outcome` is
  `fired`, one of the stoppages, or `click` / `dead_trigger` (pressing the trigger on a rifle that is not ready), `on_safe`,
  `fired_into_obstruction`, `out_of_service`. A hangfire adds `delayS` and `perceptible`; a short one resolves at once and
  carries the cycle's result in `then`. A squib adds `lodgedMm`. `force: 'stovepipe'` or `'double_feed:two_live'` makes that
  stoppage happen, for demonstrations; it goes through the same state changes as a drawn one.
- `gun.advance(dt)`: let time pass (cooling; a pending hangfire fires if its time comes).
- `gun.ready`, `gun.state`, `gun.observe()`, `gun.diagnose()`: the state, what can be seen, and the procedure for it.
- `gun.act(name, args)`: one action, returning `{ ok, events, seconds }`. `gun.step()`: the next step of the procedure the
  picture calls for, with its label and what to expect. `gun.runProcedure(id)`, `gun.clear()`: a whole procedure, or
  everything until ready, made safe or out of service; `clear()` also returns the stoppage class.
- `gun.pose()`, `gun.carrierAt(t)`, `gun.stopTime()`, `gun.describe()`: for showing it (see "The stoppages").
- `gun.probabilities()`, `gun.margins()`: the analytic per-round probabilities and the physical margins of the next shot.
- `gun.set(cfg)`, `gun.maintain('wipe_lube' | 'clean')`, `gun.reset()`.
- `M.runProtocol(seed, rounds, cfg, opts)`: one rifle through a firing schedule with every stoppage cleared; returns counts by
  type and class and the round numbers. `M.edtCategory(key)` maps a type to the dust test's category.
- `M.motion(name, ctx)`, `M.sampleMotion(motion, t)`: the clearing clips. `M.core` exposes the pure functions on a state object.

Each `fire()` draws five random numbers and each `act()` two, whatever happens, so a history stays aligned across languages.
About a million shots a second in Node.

## Checks

`python3 sim.py` (results in `validation.json`):

| Check | Result |
|---|---|
| dust test, counts by type | pass: FFD 152.7 vs 150; FTC 7.7 vs 7; FFR 5.3 vs 5; FXT 2.5 vs 3; FEJ 48.9 vs 49; FBR 2.9 vs 3 per 60,000 rounds (40 repeats; calibration targets) |
| dust test, total class 1 and 2 | pass: simulated 219.9 per 60,000 rounds, published 219 less 2 "other" = 217; MRBS 273 against 274 |
| dust test, stoppages rise between wipes | pass: second half of each 600-round interval has 4.96 times the stoppages of the first (the briefing says only that cleaning appeared to help; it gives no number) |
| dust test, aluminium magazines | pass: extra feed stoppages 197 per 60,000 rounds; the M4's magazine stoppages were 148 and 239 (calibrated to the midpoint 193.5) |
| clean rifle, mean rounds between stoppages | pass: simulated 5099 over 1800000 rounds (analytic 4998); assumed target about 5,000 (Army laboratory figure for new M4s; no HK416 figure exists) |
| M855 rates against lot acceptance | pass: chance a lot at the simulated rates passes the first sample: misfire 0.9998 (accept 1 in 800), bullet in bore 0.9996 (accept 0), failure to extract 0.9974 (accept 0) |
| action time against the M855 specification | pass: primer to gas port 0.97 ms in the action simulation; the specification allows 3 ms at mean plus five standard deviations |
| every stoppage is cleared | pass: 16 forced stoppages x 400 trials x 2 modes end ready (squib: made safe, awaiting inspection) |
| the wait covers a hangfire | pass: forced perceptible hangfires: range mode (30 s wait) 0 of 400 opened early; military immediate action 175 of 400 opened the action before the round fired |
| Monte Carlo against the analytic probabilities | pass: largest deviation 1.56 standard errors over 7 outcomes in 1000000 shots (dust 0.6, degraded ammunition, aluminium magazine) |
| seeded runs reproduce | pass: same seed gives the same 11 stoppages at the same rounds; another seed differs |
| node and clip names exist | pass: 10 model nodes and 8 existing clips referenced are in model/inventory.json and stats_lod0.json; 9 new motions; props: prop_case, prop_round, prop_round_2, prop_bullet, prop_rod |

`node test_malfunctions.js`:

```
ok   margins and per-round probabilities match sim.py: 140 numbers in 5 states, largest relative difference 8.5e-16
ok   seeded sequences match sim.py: 1600 steps over 4 seeds
ok   protocol runs match sim.py: 4 runs, 110 stoppages at the same rounds with the same types and classes
ok   dust test long run equals sim.py exactly: 8795 stoppages in 2400000 rounds (40 repeats of 10 rifles x 6,000)
ok   dust test rates against the 2007 briefing (per 60,000 rounds, simulated vs published): FFD 152.7 vs 150, FTC 7.7 vs 7, FFR 5.3 vs 5, FXT 2.5 vs 3, FEJ 48.9 vs 49, FBR 2.9 vs 3
ok   dust test total 219.9 per 60,000 rounds against 217 published (219 class 1 and 2, less 2 "other"): MRBS 273 vs 274
ok   clean long run equals sim.py exactly: 353 stoppages in 1800000 rounds
ok   clean rifle 5099 rounds between stoppages against the assumed 5,000 (Army laboratory figure for new M4s)
     (4.2 million simulated rounds in 3.3 s)
ok   dust test, 150 repeats, mean per 60,000 rounds (simulated +/- standard error vs target): FFD 152.38 +/- 1.01 vs 150, FTC 7.29 +/- 0.22 vs 7, FFR 5.01 +/- 0.18 vs 5, FXT 2.89 +/- 0.14 vs 3, FEJ 49.91 +/- 0.58 vs 49, FBR 2.90 +/- 0.14 vs 3
     total 220.4 per 60,000 (MRBS 272; published 219, MRBS 274). Classes by clearing time, a prediction: class 1 207.9, class 2 11.0, class 3 1.4 (published: 219 class 1 and 2, 14 class 3 of unstated kind; parts breakage is not modelled)
ok   clean rifle, 6 million rounds: 1150 stoppages, 5217 rounds between stoppages (target 5,000; standard error 154)
ok   aluminium magazines in the dust test add 208 feed stoppages per 60,000 rounds (the M4's magazine stoppages: 148 and 239)
     (17.4 million simulated rounds in 20.3 s)
ok   validation.json: 12 checks passed, 0 failed
ok   the same seed gives the same 300-shot history; another seed gives another
ok   the eight stoppages of the brief (15 variants x 20 seeds) can each be produced, posed and cleared
ok   tap, rack and fire after a squib is reported as a round fired into a blocked bore, and the rifle is out of service
ok   racking a double feed with the magazine in clears nothing
ok   the selector will not go to safe with the hammer down (manual p. 3)
ok   carrierAt() follows action.json's carrier curve within 0.30 mm over the whole cycle
ok   stroke, hold-open, eject and pick-up positions and the hammer energy are those of action.json (rerun sim.py if the action changes)
ok   rack_full starts from the stoppage position and draws the carrier to 95 mm
all checks passed
```

The first four are the JS-vs-Python parity: the margins and probabilities agree to rounding, and the same seeds give the
same stoppages at the same round numbers, so the long runs agree exactly, not statistically. Plots:
`plots/01_dust_test_by_type.png`, `02_carrier_energy_margin.png`, `03_probability_vs_dust.png`, `04_dust_test_run.png`,
`05_conditions.png`.

The honest summary: the dust test counts and the clean total match because they were calibrated to. What the simulation
adds is the structure between them (which margin fails, where the carrier stops, what the shooter then sees and does), the
consequences that follow without extra parameters (short strokes, double feeds from stuck cases, classes from clearing
times), and exact reproducibility. No rate here has been validated against a second, independent data set, because none was
found for the HK416.

## Parameters

| Parameter | Value | Source | Note |
|---|---|---|---|
| `dust_residual` | 0.3  | guess | share of the dust load still in the rifle straight after a wipe and lubrication |
| `lube_interval` | 600 rounds | published | dust test: wipe and lubricate every 600 rounds (edt3) |
| `clean_interval` | 1200 rounds | published | dust test: full clean every 1,200 rounds (edt3) |
| `heat_per_shot` | 2 K | inferred | mean barrel temperature rise per shot: about 1.1 kJ of the 6.5 kJ charge into 1.1 kg of steel |
| `heat_tau` | 600 s | guess | barrel cooling time constant in still air |
| `heat_ref` | 432 K | manual | rise after 250 rounds in 180 s with the two values above: the manual's cooling limit (p. 4) is heat index 1 |
| `cold_ref` | -54 C | published | -65 F, the cold extreme of MIL-C-63989C 3.10: cold index 1 |
| `hot_ref` | 52 C | published | +125 F, the hot extreme of MIL-C-63989C 3.10: hot index 1 |
| `hammer_energy` | 0.4807 J | action | hammer energy at the firing pin (action validation.hammer_energy) |
| `primer_allfire` | 0.334 J | guess | No. 41 primer all-fire: 3.94 oz ball from 12 in (commonly quoted, unconfirmed) |
| `indent_nominal` | 0.5302 mm | action | primer indent of a normal strike (action validation.primer_indent) |
| `primer_f0` | 400 N | action | primer cup yield force |
| `primer_k` | 1e+06 N/m | action | primer cup hardening slope |
| `fp_protrusion_go` | 0.9 mm | manual | firing pin protrusion GO (pp. 17, 21) |
| `fp_protrusion_nogo` | 1.1 mm | manual | firing pin protrusion NO-GO (pp. 17, 21) |
| `clean_scale` | 0.8004  | calibrated | common factor on the seven clean targets (p_*_clean) so that the clean rifle run through the test protocol gives about 5,000 rounds between stoppages |
| `p_light_clean` | 1e-05 /round | inferred | light strikes in a clean rifle with M855: target for k_fire |
| `k_fire` | 32.23  | calibrated | steepness of the light-strike curve p = 1 / (1 + ratio^k), ratio = delivered energy / all-fire energy |
| `eta_dust` | 0.07817  | calibrated | share of hammer energy lost at full dust load; solved for the dust test failure-to-fire count |
| `eta_cold` | 0.1  | guess | share of hammer energy lost to congealed lubricant at cold index 1 |
| `eta_foul` | 0.01  | guess | share lost per unit of carbon fouling (small: no gas enters the receiver, manual p. 6) |
| `energy_scatter` | 0.3 J | inferred | logistic scale of shot-to-shot carrier energy (sd 0.54 J, 6 percent of 9.06 J), from the port pressure scatter MIL-C-63989C 3.8 allows |
| `drag_dust` | 20.76 N | calibrated | extra carrier friction at full dust load; solved for the dust test failure-to-lock-back count |
| `drag_foul` | 1 N | guess | extra carrier friction per unit of carbon fouling |
| `drag_dry` | 4 N | guess | extra carrier friction when run dry (the action simulation's lubricated rail friction is 5 N) |
| `drag_cold` | 6 N | guess | extra carrier friction at cold index 1 |
| `drive_cold` | 0.1  | inferred | carrier drive energy lost at cold index 1; the specification lets port pressure fall 2,000 psi (about 14 percent) at -65 F |
| `drive_hot` | 0.04  | inferred | carrier drive energy gained at hot index 1 |
| `drive_rings` | 0.25  | guess | carrier drive energy lost with worn piston rings (manual p. 27: not enough gas) |
| `p_catch` | 0.0002 /last round | guess | bolt catch or follower fails to hold the bolt although the carrier passed it |
| `rim_strength` | 1700 N | inferred | force that shears the rim: 250 MPa brass in shear over 6 mm of claw by 1.14 mm of rim |
| `p_fxt_clean` | 4e-06 /round | inferred | failures to extract in a clean rifle with M855: target for k_extract |
| `k_extract` | 17.21  | calibrated | steepness of the extraction curve p = 1 / (1 + ratio^k), ratio = extractor capacity / case drag |
| `stick_dust` | 0.1134  | calibrated | rise in case drag at full dust load; solved for the dust test failure-to-extract count |
| `stick_foul` | 0.05  | guess | rise in case drag per unit of carbon fouling |
| `stick_heat` | 0.15  | guess | rise in case drag at heat index 1 |
| `extractor_go` | 1.28 mm | manual | extractor claw GO gauge (pp. 17, 23) |
| `extractor_nogo` | 1.59 mm | manual | extractor claw NO-GO gauge (pp. 17, 24) |
| `p_torn` | 0.2  | guess | share of failures to extract that tear the rim when the claw is in gauge |
| `eject_clear_mm` | 12 mm | guess | sideways travel that takes the case out of the bolt's path |
| `p_fej_clean` | 5e-05 /round | inferred | failures to eject in a clean rifle: target for k_eject |
| `k_eject` | 5.978  | calibrated | steepness of the ejection curve p = 1 / (1 + ratio^k), ratio = time window / time the case needs |
| `slow_dust` | 0.4888  | calibrated | share of ejection speed lost at full dust load; solved for the dust test failure-to-eject count |
| `slow_foul` | 0.03  | guess | share of ejection speed lost per unit of carbon fouling |
| `slow_ejector` | 0.5  | guess | share of ejection speed lost with a weak ejector spring |
| `slow_extractor` | 0.3  | guess | share of ejection speed lost with a weak extractor spring (the case pivots on the claw) |
| `p_stove` | 0.7  | guess | share of failures to eject that leave the case standing in the port; the rest lie loose in the receiver |
| `rise_mm` | 6 mm | guess | how far the magazine must lift the stack to present the next round |
| `follower_mass` | 0.015 kg | guess | follower plus a third of the magazine spring |
| `mag_spring_f0` | 15 N | guess | magazine spring force on the last round |
| `mag_spring_per_round` | 1.1 N | guess | added spring force per round in the magazine (48 N full) |
| `p_override_clean` | 1.2e-05 /round | inferred | bolt over-rides in a clean rifle, mean over a 30-round magazine: target for k_feed_time |
| `k_feed_time` | 15.5  | calibrated | steepness of the over-ride curve p = 1 / (1 + ratio^k), ratio = time the bolt is behind the magazine / time the stack needs to rise |
| `p_nose_clean` | 8.5e-05 /round | inferred | feed ramp jams in a clean rifle with an HK steel magazine |
| `p_two_clean` | 4e-06 /round | inferred | two-round feeds in a clean rifle with an HK steel magazine |
| `feed_dust` | 4.365  | calibrated | exponent of the feed-jam rise with dust, p ~ exp(b c); solved for the dust test failure-to-feed count (150 with the magazine stoppages) |
| `lip_nose` | 30  | guess | feed ramp jam multiplier at feed-lip damage 1 |
| `lip_two` | 200  | guess | two-round feed multiplier at feed-lip damage 1 |
| `chamber_work` | 0.75 J | inferred | work to strip, seat and lock a round: the action simulation's 15 N feed drag over 30 mm, plus the extractor snapping over the rim and the bolt turning |
| `p_ftc_clean` | 6e-06 /round | inferred | failures to chamber in a clean rifle: target for k_chamber |
| `k_chamber` | 8.881  | calibrated | steepness of the chambering curve p = 1 / (1 + ratio^k), ratio = carrier energy on closing / work needed |
| `chamber_dust` | 0.5259  | calibrated | rise in chambering work at full dust load; solved for the dust test failure-to-chamber count |
| `chamber_foul` | 0.1  | guess | rise in chambering work per unit of carbon fouling |
| `buffer_weak` | 0.3  | guess | share of closing energy lost with a weak buffer spring (manual p. 26, step 3) |
| `hang_median` | 0.08 s | guess | median hangfire delay (lognormal) |
| `hang_sigma` | 1.2  | guess | log standard deviation of the hangfire delay: 95 percent under 0.58 s |
| `hang_perceptible` | 0.25 s | guess | delay above which the shooter notices a click before the shot |
| `squib_min_mm` | 20 mm | guess | least bullet travel of a squib |
| `squib_max_mm` | 200 mm | inferred | most bullet travel of a squib: short of the gas port, 208 mm of travel in the action simulation, or the action would have cycled |
| `rack_extracts` | 0.5  | guess | chance one rack pulls out a case the claw slipped off |
| `rack_clears_port` | 0.9  | guess | chance one rack, port down, drops a trapped case |
| `rack_clears_nose` | 0.85  | guess | chance one rack clears a round from the feed ramp with the magazine in |
| `strike_frees` | 0.7  | guess | chance striking the charging handle forward frees an over-ridden round, magazine out |
| `strike_frees_mag_in` | 0.2  | guess | the same with the magazine still in |
| `hold_strike_frees` | 0.95  | guess | chance the second method (bolt held back) frees it |
| `assist_seats` | 0.6  | guess | chance a tap on the forward assist closes a bolt that stopped short |

Magazines: `hk_steel` (HK steel 30-round (manual pp. 5, 6)): feed jam x1.0, two-round feed x1.0, dust friction on the stack 6 N, extra dust exponent 0 (manual / calibrated); `gi_aluminium` (US issue aluminium 30-round): feed jam x1.5, two-round feed x1.5, dust friction on the stack 12 N, extra dust exponent 0.751 (published / calibrated).

Taken from `../action/action.json` when `sim.py` runs (rerun it if the action simulation changes; `test_malfunctions.js` checks
they still agree): the carrier's kinetic energy at each millimetre of travel, the times it passes each millimetre out and
back, full stroke 95.01 mm, unlock 10.5 mm, hammer cocked by 32 mm, case clear of the port at 62.2 mm, bolt behind the next
round at 75.5 mm, bolt catch at 82 mm, hammer energy 0.481 J, primer indent 0.53 mm, chamber pressure when extraction starts
3.7 MPa, ejection speed before the deflector 2.28 m/s, moving mass 0.518 kg, round mass 12.3 g.

## Inferences, omissions and corrections

Inferences that carry weight:

- Clean-rifle baseline. No HK416 laboratory stoppage rate was found. The clean rifle is set near the Army laboratory figure for new M4s and M16s (about 5,000 rounds between stoppages), which is an assumption that a clean HK416 is no worse than a clean M4.
- The split of that clean baseline between types (feed 60 percent, eject 25, fire 15, the rest small) follows the proportions of the 2007 dust test loosely, with a larger share for ammunition. It is a judgement.
- The dust test counts are matched by solving one dust coefficient per type. They are calibration targets, not predictions.
- The briefing's "failure to feed" is not split further. Here it is split into rounds jammed on the feed ramp, the bolt closing on an empty chamber after a short stroke (from the energy model), bolt over-rides (from the timing model) and two-round feeds. The nine magazine-attributed stoppages are counted as feed stoppages.
- The rifles in the dust test are assumed to have used HK steel magazines. The briefing describes a basic load in aluminium magazines but does not say which magazine each rifle used.
- The aluminium magazine penalty in dust is taken from the M4's magazine-attributed stoppages in the same test series (148 and 239 per 60,000 rounds, midpoint 194). That is a different rifle; it is the only published number.
- Hangfire and squib rates, and every ammunition class other than in-specification M855, are guesses. No usable published rate exists for modern factory 5.56 mm. The M855 values are only checked to be consistent with the lot acceptance plan.
- The hangfire delay distribution (lognormal, median 80 ms) is a guess shaped by the general description of hangfires as mostly short.
- Shot-to-shot scatter of the carrier energy (logistic, scale 0.30 J) is inferred from the port pressure scatter the M855 specification allows; every scatter in the model is logistic (heavier tails than a normal).
- Every multiplier for dry running, cold, heat, carbon fouling, spring wear, feed-lip damage, extractor gap, weak ejector and worn piston rings. Directions follow the manual and common armourer practice; sizes are judgement.
- Dust carried in the rifle between wipes: 30 percent of the full load straight after a wipe and lubrication, rising linearly to the full load at 600 rounds.
- The chance that a rack extracts a slipped case (0.5), clears a case from the port (0.9) or a round from the feed ramp (0.85), that striking the charging handle frees an over-ridden round (0.7, then 0.95), or that the forward assist seats a round (0.6).
- Carrier stop positions and the poses of the case and round in each stoppage: worked out from the model's port, bolt face and magazine geometry by contact, not measured from photographs of real stoppages.
- Action durations (tap 0.4 s, rack 0.9 s and so on), which decide whether a stoppage counts as class 1 or class 2.
- Barrel heating of 2 K per shot with a 10 minute cooling time constant, scaled so the manual's limit (250 rounds in 3 minutes) is heat index 1.

Corrections to the earlier partial work (`content.py` only, written before the modelling rules):

- The dust test counts by type are now the briefing's own (slide 7); the earlier notes had only the totals.
- The M855 specification was read for the acceptance plan; the earlier notes had no ammunition source.
- The over-ride procedure follows TC 3-22.9 (strike the charging handle forward, then hold the bolt back and strike), not a
  butt strike on the ground, which the TC summary does not describe.
- Failure to lock back is kept as a ninth outcome because the dust test counts it and the energy curve produces it, though
  the brief lists eight.
- The earlier clean baseline of 1 in 5,900 and its split had no derivation and were dropped.

Sources that could not be opened and are cited at second hand: the dust test briefing (read as a text rendering of the
slides), TC 3-22.9 (step order from a secondary summary), the MRBS figures of 600, 1,691 and 3,592 (from a secondary
summary), and the No. 41 primer all-fire energy (commonly quoted, unconfirmed). MIL-C-63989C was read directly.

## Known limits

- Rates are per-round probabilities, calibrated at two points: an assumed clean baseline and one published dust test. Between and beyond those points the model interpolates with inferred physics. It does not predict the reliability of any real rifle.
- The dust test is one test with a protocol the Army itself found not repeatable for the M4 (296 stoppages in one run, 863 in the next). The HK416 was run once.
- The energy and timing margins come from the action simulation, whose carrier, spring and gas parameters are themselves inferred. The margins are consistent with that model, not measured on a rifle.
- Parts breakage is not modelled: no broken extractors, bolts, firing pins or springs, and none of the 14 class 3 stoppages or the 3 headspace and case rupture events the dust test recorded for the HK416. Wear inputs are static settings.
- Not modelled: cook-off, slam-fire, doubling, out-of-battery firing other than a hangfire opened too early, case-head separation, pierced or blown primers, bolt locked to the rear early, and any trigger group fault.
- A squib is always a bullet lodged in the bore with the action not cycled. Firing a second round behind it is reported as a destroyed barrel and the simulation stops there; no damage is simulated.
- Hand-cycled feeding during clearing is assumed never to misfeed. Ejected live rounds are counted, not recovered.
- One stoppage per shot. Compound stoppages only arise through the state machine (a stuck case becomes a double feed when a round is fed behind it).
- The shooter always diagnoses correctly from what can be seen and follows the procedure. No fumbles, no stress, no darkness.
- Carrier travel after a short stroke is a scaled copy of the full-stroke curve, not a solved cycle.
- The clips are keyframe data in build.py's format. They have not been baked into the model or checked for clearance. Cases, loose rounds and the cleaning rod are props the model does not contain.
- The model has no extractor, ejector, hammer or firing pin nodes, so the parts that fail are never seen; only the carrier, the bolt head and the brass show the stoppage.

## Sources

- **Heckler & Koch USA, Maintenance Manual for HK416 Enhanced Carbine & Rifle System, 5.56 mm NATO (54 pages). Not in this repository; facts summarised with page numbers**. Used for: clearing steps (p. 3); bore free of obstructions, factory-loaded undamaged cartridges only, cooling after 250 rounds in under 3 minutes (p. 4); HK steel magazines against aluminium ones (pp. 5, 6); no propellant gas in the receiver, longer interval between stoppages (p. 6); what the extractor, ejector and firing pin do, and that the pin reaches the primer only with the bolt fully locked (p. 7); do not ride the charging handle (p. 8); cycle of operation (pp. 8 to 12); firing pin protrusion 0.90 to 1.10 mm and extractor claw gauges 1.28 / 1.59 mm (pp. 17, 21, 23, 24); function check, forward assist as a symptom check, last-round hold-open, no reloads (p. 26); ejector and piston rings (p. 27); magazine catch tension (p. 37). The manual has no stoppage drill.
- **US Army PEO Soldier, "M4 Carbine Extreme Dust Test" briefing, v3.5 (Aberdeen Test Center, fall 2007 test, briefed December 2007), slides 2 to 12** <https://www.slideshare.net/slideshow/m4-carbine-extreme-dust-test-brief-v350/15832677>. Used for: the only published HK416 stoppage counts by type: 10 rifles x 6,000 rounds, 25 h of dusting per rifle, 120-round cycles, wipe and lubricate every 600 rounds, full clean every 1,200. HK416 class 1 and 2 weapon stoppages 210 (failure to feed 141, to chamber 7, to fire 5, to extract 3, to eject 49, bolt locked to the rear 0, bolt failed to lock to the rear 3, other 2), magazine stoppages 9, class 3 stoppages 14. M4 magazine stoppages 148 (summer) and 239 (fall). Read through a text rendering of the slides, not the original file.
- **US Army, "M-4 Carbine Has High Soldier Confidence Despite Test" (army.mil, 18 December 2007)** <https://www.army.mil/article/6649/m_4_carbine_has_high_soldier_confidence_despite_test>. Used for: the dust test protocol and the stoppage classes: class 1 cleared by the shooter within 10 s, class 2 cleared by the shooter in more than 10 s, class 3 needs an armourer.
- **Congressional Research Service RS22888, "The Army's M-4 Carbine: Background and Issues for Congress" (2008)** <https://www.everycrsreport.com/files/20080530_RS22888_03edaa907691c2e89542641b3279702c8bd8e5d3.html>. Used for: dust test totals (XM8 127, SCAR 226, HK416 233, M4 882); Army laboratory test October 2005 to April 2006: 10 new M16s and 10 new M4s averaged about 5,000 rounds between stoppages; USMC 2002: M4 186 failures in 69,000 rounds.
- **M4 mean rounds between stoppage figures as reported by Military.com (14 June 2013) and summarised in Wikipedia, "Individual Carbine" and "M4 carbine"** <https://en.wikipedia.org/wiki/Individual_Carbine>. Used for: 600 MRBS required of the M4 in 1990 (M855); 1,691 MRBS for the M4A1 with M855A1 (2013); 3,592 required by the Individual Carbine competition. Context for the clean baseline; read from the secondary summary, not the Army documents.
- **MIL-C-63989C(AR), Military Specification: Cartridge, 5.56 mm, Ball, M855 (superseded revision, public on everyspec.com)** <https://everyspec.com/MIL-SPECS/MIL-SPECS-MIL-C/MIL-C-63989C_37913/>. Used for: lot acceptance, Table III and Table IV: 800 rounds per weapon type in the function and casualty test; first sample accepted with at most 1 misfire, rejected at 3; a bullet remaining in the bore rejects the lot; failure to extract and weapon stoppage accepted at 0, rejected at 2. Action time (primer ignition to the bullet passing the gas port): mean plus five standard deviations at most 3 ms (3.15). Port pressure mean minus three standard deviations at least 12,700 psi (3.8), within 2,000 psi of that at -65 and +125 F (3.10.3). Velocity 3,000 +/- 40 ft/s, standard deviation at most 40 ft/s (3.6).
- **US Army TC 3-22.9, Rifle and Carbine (May 2016), chapter 8: immediate action (para 8-35) and remedial action (para 8-36)** <https://irp.fas.org/doddir/army/tc3-22-9.pdf>. Used for: the clearing sequences: tap, rack, reassess; remedial action when immediate action has failed twice or the trigger will not press or feels soft; the stove pipe, double feed and bolt override procedures. Step order and paragraph numbers were read from a secondary summary (highgroundshooter.com, 14 February 2022) because the publication itself could not be opened in this session; check them against the TC before quoting.
- **Standard range practice for a misfire and for a weak shot (hunter-education courses and firearm manuals)** <https://www.hunter-ed.com/iowa/studyGuide/Beware-of-Hang-Fires/202013_12894>. Used for: keep the muzzle on the backstop and wait before opening the action after a misfire (30 s is used here; some ranges say 60); after a pop or weak shot, stop, unload and prove the bore clear before firing again. Recalled, not quoted.
- **HK416 action simulation, ../action/action.json (built by ../action/sim.py)**. Used for: carrier kinetic energy against travel, the times the carrier passes each position, 95 mm stroke, eject / feed pick-up / hold-open positions, hammer energy 0.48 J, the primer cup model, chamber pressure when extraction starts, ejection speed, masses.
- **US military small rifle primer sensitivity (No. 41): 3.94 oz ball, all-fire 12 in**. Used for: the all-fire energy 0.334 J. Recalled from the commonly quoted figure; not confirmed against the primer specification in this session.
