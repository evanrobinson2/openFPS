# HK416 D14.5RS: action and recoil simulation

A physical simulation of one shot of the HK416 (14.5 in barrel, short-stroke gas piston), from the trigger break to the
carrier back in battery, with the recoil it puts into a shooter and the flight of the ejected case. It produces data for
a game to play back; it is not game code. Model and simulation credit: carpetshark.

Rebuild everything (about 10 seconds; Python 3 with numpy, scipy and matplotlib):

```
python3 sim.py          # writes action.json and plots/
node test_action.js     # checks hk416-action.js against action.json
```

The build is deterministic: the same inputs give a byte-identical `action.json`.

| File | What it is |
|---|---|
| `sim.py` | the simulation; every parameter is in its `PARAMS` table with a source |
| `plots.py` | the plots (called by `sim.py`) |
| `action.json` | sampled curves, event times, brass initial conditions, parameters and validation, units stated in each block |
| `hk416-action.js` | self-contained playback module (no three.js): `HK416Action.sample(t)`, `.ejectCase(rng)` and so on |
| `test_action.js` | Node checks of the module, including seeded brass against `sim.py` |
| `plots/` | eight plots of the key curves |

## Conventions

- Frame: that of `hk416.glb`. Metres, +Z towards the muzzle, +Y up, +X to the shooter's left, origin on the bore axis at
  the upper receiver's front face. The ejection port is on -X.
- **Time zero is the sear releasing the hammer** (the trigger break). The charge ignites 8.51 ms later.
- `carrier_mm` is rearward travel (the node moves in -Z). `bolt_deg` is 0 locked and 22.5 unlocked. `hammer_deg` is 0 on
  the sear, positive towards the firing pin (64° at rest on the pin) and -6 while the
  carrier holds it overcocked. `firing_pin_mm` is forward travel from the pin's rearmost position; it meets the primer at 1.5 mm.
- The model has no `hammer` or `firing_pin` node (only `hammer_pin_l` and `hammer_pin_r`, per `inventory.json`). Their
  curves are still output, for timing and audio.

## The physics

All of it is lumped-parameter: a handful of ordinary differential equations, not a fluid or finite-element model.

1. **Firing train.** The hammer is a rigid body on its pin, driven by a torsion spring whose torque falls linearly from
   the cocked to the fired position. It falls 60°, strikes the floating firing pin (an inelastic blow; the hammer face stays
   on the pin), carries it 1.5 mm to the primer and indents the cup against a yield-plus-hardening force. The primer
   initiates at 0.30 mm of indent; the charge is alight 0.15 ms later. The indent is capped by the manual's firing pin protrusion.
2. **Internal ballistics.** Résal energy balance with a Nobel-Abel gas, a pressure-power burn law with a quadratic form
   function, and the Lagrange pressure gradient between breech and bullet base. Shot-start pressure, engraving and bore
   friction are equivalent pressures. After the bullet leaves, the bore empties as an isentropic reservoir through a sonic muzzle.
   The pressure at the gas port is the Lagrange profile at the port position once the bullet base has passed it.
3. **Gas system.** Compressible orifice flow (choked or subsonic, either direction) from the bore into a gas cylinder
   with its own mass and energy balance; the piston and rod push the carrier until the cylinder vents (3 mm) and the rod
   reaches its stop (16 mm). No gas reaches the receiver.
4. **Carrier group.** One degree of freedom along the bore. The carrier runs 3 mm free, then the cam track turns the bolt
   22.5° over the next 7.5 mm, working against lug friction from the residual chamber pressure. It then picks up the bolt
   and case (momentum shared), cocks the hammer (the spring energy comes out of the carrier), throws the case out when the
   case mouth clears the port's front edge, compresses the buffer spring and meets the tube end through a stiff, lossy
   bumper. The spring drives it home: it picks up the top round, drags it off the feed lips, chambers it (the bolt stops,
   the carrier runs on), turns the bolt locked and closes against an overdamped contact (no bolt bounce, as the HK
   buffer's tungsten granules intend). On auto the carrier trips the auto sear 1.5 mm before it closes.
5. **Recoil.** The gun body and the carrier group are separate masses, so the gun feels the bore force, the piston's
   forward reaction on the gas block, the buffer spring, the buffer impact and the bolt closing, each at its own time.
   The carrier is solved in the accelerating gun's frame, so the stance changes the cycle slightly. The shooter is a
   linear mass-spring-damper chain: gun plus arm mass, a spring and damper to an effective torso mass, and a spring and
   damper from the torso to the ground. Pitch and yaw are each a second-order system about a support pivot, driven by the
   axial force on the gun body times a lever arm: the bore height above the pivot for pitch, a small lateral offset for
   yaw (a right-handed shooter's shoulder yielding).
6. **Brass.** The ejector spring's energy turns the case about the extractor claw; it leaves the bolt at 35° with the
   carrier's rearward speed added, makes one impulsive bounce off the brass deflector, and flies under gravity and
   quadratic drag. Ground contact is a randomised cylinder bounce (restitution, Coulomb friction, a spin kick), then a
   slide to rest.

## What is published and what is inferred

Sources, in order of authority:

- **manual**: Heckler & Koch USA, *Maintenance Manual for HK416 Enhanced Carbine & Rifle System, 5.56 mm NATO*, summarised in
  `../MANUAL_NOTES.md` with page references. Muzzle velocity, chamber pressure, cyclic rate range, weight, trigger pull and
  firing pin protrusion come from it. Its page 9 "locking rollers" paragraph is G3 text and is ignored.
- **published**: widely published figures (M855 bullet and charge weight from US Army TM 43-0001-27, 5.56×45 case
  dimensions, the AR-pattern 22.5° bolt rotation, the SAAMI free-recoil gas velocity convention).
- **model**: measured from `hk416.glb` and `build.py` (photo-derived, so real to the accuracy of the model, not a drawing).
- **inferred**: an engineering estimate. Nothing with this label was measured, and HK publishes none of it (buffer and
  carrier masses, spring rates, piston and port sizes, hammer inertia, every shooter parameter, every brass parameter).
- **calibrated**: solved by `sim.py` so that a published figure is reproduced. These are not predictions.

Four parameters are calibrated. The burn coefficient and the form-function coefficient are solved together for the manual's
chamber pressure and muzzle velocity. The blowdown thrust scale is set so the propellant gas carries the SAAMI
convention's momentum; the raw lumped blowdown gives an effective gas velocity of
1759 m/s against the convention's 1,219 m/s, because it treats the whole charge as stagnant gas at the
mean pressure and ignores heat loss. The gas port diameter is solved so the shouldered gun cycles at 800 rpm, the midpoint
of the manual's range; it comes out at 1.22 mm (AR-15 carbine ports are about 1.6 mm, for comparison only).

| Parameter | Value | Source | Note |
|---|---|---|---|
| `m_bullet` | 4.018 g | published | M855 ball, 62 gr |
| `m_charge` | 1.691 g | published | M855: 26.1 gr WC844 (US Army TM 43-0001-27); varies by lot |
| `m_case` | 6.2 g | inferred | fired 5.56 brass case with primer cup, about 95 gr |
| `m_round` | 12.3 g | published | M855 cartridge, about 190 gr |
| `barrel_len` | 368.3 mm | manual | 14.5 in, bolt face to muzzle |
| `bullet_base0` | 34.3 mm | inferred | bullet base from the bolt face when chambered (57.4 mm overall, 23.1 mm bullet) |
| `bore_area` | 24.8 mm² | inferred | 5.56 mm lands / 5.69 mm grooves, mean |
| `chamber_vol` | 1.76 cm³ | inferred | case capacity behind the seated bullet |
| `port_to_muzzle` | 125.7 mm | model | gas block centre to barrel crown in hk416.glb (photo-derived, not a published port position) |
| `p_max_target` | 358.5 MPa | manual | chamber pressure 52,000 psi (p. 7) |
| `v_muzzle_target` | 850 m/s | manual | 2,790 ft/s for the 14.5 in barrel (p. 7) |
| `force_const` | 1e+06 J/kg | inferred | propellant force (impetus), typical double-base ball powder |
| `gamma` | 1.24 | inferred | ratio of specific heats of propellant gas |
| `covolume` | 0.00095 m^3/kg | inferred | Nobel-Abel covolume |
| `rho_prop` | 1620 kg/m^3 | inferred | solid propellant density |
| `flame_temp` | 2850 K | inferred | adiabatic flame temperature; sets the gas constant R = F/T0 |
| `form_theta` | -0.3009 | calibrated | form function psi = (1+th)Z - th Z^2; negative = progressive (deterred ball grain); solved for the manual muzzle velocity |
| `burn_exp` | 0.9 | inferred | pressure exponent of the burn rate |
| `burn_coeff` | 594.6 1/s | calibrated | vivacity dZ/dt at 100 MPa; solved for the manual chamber pressure |
| `loss_factor` | 0.2 | inferred | heat loss to the bore as a fraction of the work done on bullet and gas |
| `gas_velocity_conv` | 1219 m/s | published | SAAMI free-recoil convention: propellant gas leaves at 4,000 ft/s (high-power rifle) |
| `blowdown_scale` | 0.5956 | calibrated | scale on the lumped blowdown thrust so total gas momentum equals the SAAMI convention (the raw lumped figure is kept in validation) |
| `p_ign` | 5 MPa | inferred | primer/igniter pressure that starts the charge burning |
| `p_shot_start` | 30 MPa | inferred | bullet pull and crimp release pressure |
| `p_engrave` | 22 MPa | inferred | extra engraving resistance, decays over engrave_len |
| `p_friction` | 8 MPa | inferred | bore friction as an equivalent pressure |
| `engrave_len` | 4 mm | inferred |  |
| `muzzle_cf` | 1.247 | derived | sonic-exit thrust coefficient (g+1)(2/(g+1))^(g/(g-1)) during blowdown |
| `brake_beta` | 0 | inferred | momentum recovered by the muzzle device; the HK "compensator" is a flash hider, taken as 0 |
| `trigger_pull` | 23.6 N | manual | 4.6 to 6 lb (20.5 to 26.7 N), midpoint; not used in the dynamics |
| `hammer_inertia` | 1.6e-05 kg m^2 | inferred | about 33 g hammer, 22 mm radius of gyration about its pin |
| `hammer_torque_cocked` | 0.62 N m | inferred | hammer spring torque on the sear |
| `hammer_torque_fired` | 0.4 N m | inferred | hammer spring torque resting on the firing pin |
| `hammer_fall` | 60 deg | inferred | rotation from the sear to first contact with the firing pin |
| `hammer_eff` | 0.9 | inferred | fraction of spring torque left after pivot friction |
| `hammer_strike_r` | 30 mm | inferred | hammer pin to the face that strikes the firing pin |
| `hammer_overcock` | 6 deg | inferred | how far the carrier holds the hammer below the sear |
| `fp_mass` | 8.3 g | inferred | AR-pattern firing pin, about 0.3 oz |
| `fp_float` | 1.5 mm | inferred | free travel of the floating pin before its tip meets the primer |
| `fp_protrusion` | 1 mm | manual | firing pin protrusion 0.90 to 1.10 mm (p. 17): the hard stop on indentation |
| `primer_f0` | 400 N | inferred | primer cup yield force |
| `primer_k` | 1e+06 N/m | inferred | primer cup hardening slope |
| `primer_fire_indent` | 0.3 mm | inferred | indent at which the priming mix initiates |
| `primer_delay` | 0.15 ms | inferred | primer initiation to flame in the charge (start of the ballistics model) |
| `port_d` | 1.219 mm | calibrated | barrel gas port diameter; solved for the target cyclic rate |
| `cyclic_target` | 800 rpm | manual | midpoint of the manual 700 to 900 rpm (p. 7) |
| `piston_d` | 10 mm | inferred | piston diameter, from the 9.8 mm piston tube in the model |
| `cyl_vol0` | 0.6 cm³ | inferred | gas cylinder dead volume |
| `vent_open_x` | 3 mm | inferred | piston travel at which the cylinder vents |
| `vent_area` | 12 mm² | inferred | vent area once open |
| `leak_area` | 0.15 mm² | inferred | leakage past the three piston rings |
| `rod_stop_x` | 16 mm | inferred | travel at which the piston rod stops and the carrier runs on alone |
| `orifice_cd` | 0.8 | inferred | discharge coefficient |
| `cyl_heat_eff` | 0.75 | inferred | fraction of inflow enthalpy kept (wall heat loss) |
| `m_piston_rod` | 63 g | inferred | piston plus piston rod |
| `rod_spring` | 20 N | inferred | piston rod return spring |
| `m_carrier` | 300 g | inferred | carrier with cam pin, firing pin and retaining pin (AR-pattern scale) |
| `m_bolt` | 48 g | inferred | bolt head with extractor and ejector |
| `m_buffer` | 150 g | inferred | HK buffer with tungsten granules (weight not in the manual) |
| `m_spring_eff` | 20 g | inferred | one third of the buffer spring |
| `spring_preload` | 30 N | inferred | buffer spring force in battery |
| `spring_rate` | 330 N/m | inferred | buffer spring rate |
| `stroke_contact` | 94 mm | inferred | carrier travel at which the buffer meets the tube end (AR pattern, about 3.75 in total) |
| `buffer_k` | 1.5e+06 N/m | inferred | buffer bumper stiffness |
| `buffer_restitution` | 0.25 | inferred | low because the tungsten granules deaden the rebound (manual p. 5 names them) |
| `battery_k` | 1e+07 N/m | inferred | carrier to barrel extension contact stiffness (overdamped, zeta 2: no bolt bounce) |
| `rail_friction` | 5 N | inferred | sliding friction of carrier, buffer and hammer drag |
| `cam_dwell` | 3 mm | inferred | carrier free travel before the cam track starts turning the bolt |
| `cam_len` | 7.5 mm | inferred | carrier travel over which the bolt turns |
| `bolt_angle` | 22.5 deg | published | AR-pattern bolt rotation between locked and unlocked |
| `lug_r` | 8 mm | inferred | mean radius of the locking lug faces |
| `lug_mu` | 0.15 | inferred | steel on steel, lubricated |
| `case_head_area` | 72 mm² | inferred | 9.6 mm case head: bolt thrust per unit chamber pressure |
| `case_wall_area` | 1100 mm² | inferred | case body wall bearing on the chamber |
| `case_mu` | 0.2 | inferred | brass on steel during primary extraction |
| `cock_x` | 32 mm | inferred | carrier travel by which the hammer is fully cocked |
| `bolt_face_z` | -14 mm | model | front of bolt_head in hk416.glb |
| `case_len` | 44.7 mm | published | 5.56x45 case length 44.70 mm |
| `case_r` | 4.5 mm | published | case body radius (9.6 mm head, 9.0 mm body) |
| `port_front_z` | -21 mm | model | front edge of the ejection port in build.py |
| `feed_pick_bolt_x` | 65 mm | inferred | bolt travel at which the bolt face meets the top round on the return |
| `feed_free_x` | 45 mm | inferred | carrier travel at which the round is clear of the feed lips |
| `feed_friction` | 15 N | inferred | drag of stripping the round from the lips |
| `sear_trip_x` | 1.5 mm | inferred | carrier travel at which the auto sear is tripped on closing |
| `hold_open_x` | 82 mm | inferred | carrier travel at which the bolt catch holds the bolt after the last round |
| `ejector_energy` | 0.049 J | inferred | ejector spring: 22 N compressed to 13 N over 2.8 mm |
| `ejector_eff` | 0.8 | inferred |  |
| `case_cm` | 17.5 mm | inferred | centre of mass from the case head |
| `eject_release_deg` | 35 deg | inferred | case rotation about the extractor claw at release |
| `eject_elev_deg` | 12 deg | inferred | upward tilt of the ejection plane |
| `deflector_deg` | 40 deg | inferred | deflector face normal, from straight out (-X) towards the muzzle (+Z) |
| `deflector_e` | 0.5 | inferred | restitution of brass on the deflector |
| `deflector_spin` | 0.6 | inferred | spin kept after the deflector |
| `brass_cd_area` | 306 mm² | inferred | drag coefficient times mean projected area of a tumbling case |
| `eject_height` | 1400 mm | inferred | ejection port above the ground for a standing shooter (trajectory samples only) |
| `m_gun` | 3490 g | manual | complete gun 7.7 lb (p. 7) |
| `m_magazine` | 619 g | inferred | HK steel 30-round magazine (about 250 g) with 30 rounds |

Shooter models (all inferred; orders of magnitude from published mass-spring-damper shoulder models, tuned to plausible
muzzle rise, not fitted to measurements):

| Stance | m_arm kg | k_s N/m | c_s N·s/m | m_t kg | k_t N/m | c_t N·s/m | h m | I kg·m² | K N·m/rad | ζ | e_yaw m | K_yaw | pivot (gun frame) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ads | 2 | 30000 | 400 | 25 | 6000 | 700 | 0.041 | 1.1 | 250 | 0.5 | 0.012 | 250 | [0.0, -0.041, -0.396] |
| hip | 2.5 | 8000 | 220 | 25 | 6000 | 700 | 0.085 | 0.53 | 90 | 0.4 | 0.02 | 90 | [0.0, -0.107, -0.178] |

Surfaces for the brass (inferred): concrete restitution 0.45, friction 0.35; dirt restitution 0.12, friction 0.70.
Shot-to-shot scatter (inferred): speed 12%, azimuth 9°, elevation 6°, spin 25%.

## Validation

| Quantity | Simulation | Published | Status |
|---|---|---|---|
| Muzzle velocity | 850 m/s | 850 m/s (manual p. 7) | calibration target, not a prediction |
| Peak chamber pressure | 358.5 MPa | 358.5 MPa, 52,000 psi (manual p. 7) | calibration target |
| Cyclic rate, shouldered | 801 rpm | 700 to 900 rpm (manual p. 7) | port diameter calibrated to the 800 midpoint |
| Cyclic rate, hip / gun floating free | 799 / 818 rpm | 700 to 900 rpm | predicted from the same port; inside the range |
| Lock time, sear release to pin on primer | 8.3 ms | about 10 ms for mil-spec AR-15 and HK416 fire control (Wikipedia, "Lock time"; probably a calculated figure) | predicted from inferred hammer parameters; 17% short |
| Sear release to ignition | 8.51 ms | none found | prediction |
| Hammer energy at the pin | 0.48 J | No. 41 primer all-fire about 0.34 J (commonly quoted, unverified) | above all-fire |
| Primer indent | 0.53 mm | protrusion limit 0.90 to 1.10 mm (manual p. 17) | inside the limit |
| Barrel time, ignition to exit | 0.98 ms | about 1 ms (no source pinned) | prediction |
| Pressure at the port as the bullet passes | 149 MPa | no HK figure; 5.56 port-pressure figures for AR ports nearer the breech run roughly 90 to 180 MPa | prediction, plausible only |
| Chamber pressure when the bolt starts to turn / finishes | 19 / 3.7 MPa | none | prediction |
| Recoil impulse | 5.48 N·s | 5.48 N·s by the SAAMI formula | equal by calibration of the blowdown |
| Free recoil, gun with full magazine (4.11 kg) | 1.33 m/s, 3.65 J | recoil tables give about 4 to 5 J for 5.56 rifles of 3.2 to 3.6 kg | consistent |
| Free recoil, gun alone (3.49 kg) | 1.57 m/s, 4.30 J | as above | consistent |
| Mean force on the shooter, automatic | 71 N | impulse × rate = 73 N | momentum check on the coupled model |
| Peak carrier speed / at ejection | 5.9 / 4.0 m/s | no HK figure; 4 to 6 m/s is commonly quoted for AR carriers | plausible only |
| Ejection | 5.9 m/s towards 4.4 o'clock, 15 rev/s | manual: the case strikes the deflector and leaves to the right | qualitative agreement |

The honest summary: muzzle velocity, chamber pressure, recoil impulse and the shouldered cyclic rate match because they were
calibrated to. Lock time, barrel time, indent, hip and free-gun cyclic rates, carrier speed, the event timeline and the
ejection pattern are outputs, and they are plausible but unverified against any HK416 measurement.

### What drives the cyclic rate

The first cycle takes 72.9 ms: 8.5 ms of lock time and ignition, 24.3 ms for the carrier to reach the buffer stop, and
40.0 ms for the spring to bring it home. In a sustained burst the period settles at 74.9 ms (801 rpm), because the shoulder
is by then pushing the gun forward against the returning carrier. The return stroke is over half of it,
so the rate is set mostly by how fast the carrier leaves the buffer (gas drive and buffer rebound) and by the moving mass
against the spring. One parameter changed at a time, shouldered:

| Parameter changed | Factor | Cyclic rate, rpm | Peak carrier speed, m/s |
|---|---|---|---|
| `port_d` | ×0.9 | 747 | 5.45 |
| `port_d` | ×1.1 | 839 | 6.30 |
| `spring_rate` | ×0.8 | 789 | 5.90 |
| `spring_rate` | ×1.2 | 809 | 5.89 |
| `spring_preload` | ×0.8 | 791 | 5.91 |
| `spring_preload` | ×1.2 | 801 | 5.88 |
| `m_buffer` | ×0.8 | 822 | 6.11 |
| `m_buffer` | ×1.2 | 778 | 5.70 |
| `m_carrier` | ×0.9 | 822 | 6.11 |
| `m_carrier` | ×1.1 | 778 | 5.70 |
| `buffer_restitution` | ×0.5 | 780 | 5.90 |
| `buffer_restitution` | ×1.6 | 826 | 5.89 |
| `stroke_contact` | ×0.95 | 826 | 5.90 |
| `rail_friction` | ×2 | 758 | 5.89 |
| `feed_friction` | ×2 | 773 | 5.90 |

## Event timeline, one shot (shouldered, semi)

| Event | t after sear release, ms | t after ignition, ms | What happens |
|---|---|---|---|
| `sear_release` | 0.00 |  | trigger breaks; hammer leaves the sear |
| `hammer_strike` | 8.00 |  | hammer meets the firing pin (60° of fall) |
| `primer_contact` | 8.29 |  | pin tip meets the primer after 1.5 mm of float: **lock time** |
| `primer_fire` | 8.36 |  | indent reaches 0.30 mm; priming mix initiates |
| `ignition` | 8.51 | 0.00 | flame in the charge; ballistics model starts |
| `peak_pressure` | 8.99 | 0.48 | chamber pressure peaks at 358 MPa |
| `bullet_passes_port` | 9.33 | 0.82 | bullet base passes the gas port; gas enters the cylinder |
| `bullet_exit` | 9.49 | 0.98 | bullet leaves at 850 m/s |
| `carrier_moves` | 10.13 | 1.62 | carrier has moved 1 mm |
| `unlock_start` | 10.57 | 2.06 | cam track starts turning the bolt (3 mm) |
| `unlock` | 11.85 | 3.34 | bolt turned 22.5°, lugs clear (10.5 mm) |
| `extract` | 11.85 | 3.34 | bolt starts back; extractor pulls the case |
| `piston_rod_stop` | 12.95 | 4.43 | piston rod reaches its stop (16 mm); carrier runs on alone |
| `hammer_cocked` | 16.31 | 7.80 | hammer pushed below the sear (32 mm) |
| `eject` | 23.29 | 14.78 | case mouth clears the port; case pivots out and hits the deflector |
| `buffer_impact` | 32.16 | 23.64 | buffer meets the end of the tube |
| `max_travel` | 32.85 | 24.34 | carrier stops at 95.0 mm and turns round |
| `feed` | 45.70 | 37.19 | bolt face picks up the top round |
| `chambered` | 70.28 | 61.77 | round seated; bolt stops, carrier runs on |
| `lock` | 72.46 | 63.95 | bolt turned back to locked |
| `auto_sear_trip` | 72.88 | 64.37 | carrier trips the auto sear (on auto, the next sear release) |
| `in_battery` | 73.30 | 64.79 | carrier closed |

## Recoil outputs

| | Aimed (shouldered) | Hip |
|---|---|---|
| One shot: peak rearward travel | 8.5 mm | 17.5 mm |
| One shot: peak muzzle rise | 0.47° | 2.50° |
| One shot: peak yaw to the right | 0.14° | 0.59° |
| One shot: peak force into the support | 228 N | 159 N |
| 10 rounds auto: peak rearward travel | 16.2 mm | 22.8 mm |
| 10 rounds auto: peak / sustained muzzle rise | 0.82° / 0.64° | 5.03° / 3.74° |
| 10 rounds auto: peak yaw | 0.24° | 1.18° |

The pose is an offset from rest in the gun's frame: a translation along the bore, plus pitch and yaw about the stance's
pivot (the buttpad centre when aimed, `socket_hand_right` at the hip). Muzzle rise comes from the bore axis sitting 41 mm
above the buttpad centre (measured from the model) or an inferred 85 mm above the hip-fire support.

## Playback API (`hk416-action.js`)

```js
await HK416Action.load('action.json');            // or HK416Action.use(parsedJson)
const s = HK416Action.sample(t, { stance: 'ads', mode: 'semi' });   // t = seconds since the trigger break
bolt_carrier.position.z = rest.z + s.carrierZ;     // metres, <= 0
bolt_head.rotation.z    = s.boltRot;               // radians, 0 locked .. 0.393 unlocked
// s.hammer (rad), s.firingPin (m), s.chamberPressureMPa, s.receiverForce (N), s.carrierVel (m/s)
// s.recoil = { pos:[x,y,z] m, pitch rad (muzzle up), yaw rad (muzzle right), pivot:[x,y,z], supportForce N }
```

- `sample(t, opts)`: `opts.stance` is `'ads'` or `'hip'`; `opts.mode` is `'semi'` (one shot at t = 0) or `'auto'`
  (shots every `HK416Action.period` seconds, `opts.shots` of them); `opts.shotTimes` gives explicit trigger-break times
  instead (a semi-auto string); `opts.lastRound` holds the carrier on the bolt catch after the final shot.
- `recoil(t, shotTimes, stance)`: the pose alone. Bursts are built by adding shifted copies of the single-shot response.
  Against the fully coupled 10-round simulation this is within 0.9 mm of 16 mm and 0.04° of 0.82° aimed,
  1.0 mm of 23 mm and 0.20° of 5.03° at the hip. `recoilBurst10(t, stance)` returns the coupled result itself.
- To apply the pose in a Y-up right-handed scene: rotate the gun about `pivot` by `rotation.x = -pitch` and
  `rotation.y = -yaw`, then translate by `pos`. For a left-handed shooter negate the yaw.
- `events()`: the ordered event list above, in seconds, for sound and effects cues.
- `ejectCase(rng)`: a case's initial `pos`, `vel` and `angVel` in the gun frame, relative to the gun, with seeded scatter.
  Spawn it `brass.release_time_s` (27.3 ms) after the trigger break, transform by the gun's world pose and add the gun's
  velocity. `rng` is any function returning [0, 1); `HK416Action.rng(seed)` gives the generator `sim.py` uses.
- `stepCase(state, dt, { groundY, surface, rng })`: flight, bounce and slide to rest in a Y-up frame. `state.justBounced`
  holds the impact speed on the step a bounce happens (for the brass sound). With `dt = 1/240` and the same seed it
  reproduces the trajectories stored in `action.json` (checked by `test_action.js`).

## Charging handle and reload: where the existing clips are physically wrong

Noted only; the clips are not rebuilt.

- **`charge` travel.** The clip pulls the carrier 75 mm. The real carrier is drawn to the buffer stop, about
  95 mm here, and the bolt face has to pass the base of the top round (carrier travel about 75.5 mm, inferred)
  to strip it. At 75 mm the clip stops marginally short of feeding.
- **`charge` return.** The clip returns the carrier over five frames (0.21 s) with the handle. Released, the spring closes
  the carrier from full stroke in about 40 ms, and the handle is pushed forward by hand separately and latches.
- **Empty magazine.** After the last round the follower lifts the bolt catch and the carrier stops at about 82 mm on its
  way forward (manual p. 26; the position is inferred). Firing the last round should leave the ejection port open on the
  follower, not a closed bolt: `sample(t, { lastRound: true })` does this.
- **Reload from bolt-locked.** No charging handle is needed. After `mag_in`, the `bolt_catch` clip should release the
  carrier, which runs forward from the hold-open position and chambers a round. The `charge` clip belongs to a reload
  on a closed bolt (or a first load), and on an empty magazine it should end with the carrier held back, not closed.
- **Dust cover.** Correct as built: it opens on the first carrier movement and stays open, when firing as when charging.
- **`trigger_pull`.** The break sits at the end of the 6° rotation; the hammer then takes 8 ms to reach the pin, so the
  shot follows the break by 8.5 ms. Nothing to change beyond starting `sample()` at the break.

## Known limits

- Lumped models throughout. The ballistics are calibrated to two published numbers; the pressure curve's shape, the
  port pressure and the blowdown are model outputs, not measurements. Propellant constants are typical values, not WC844 data.
- The gas system, carrier, buffer, spring, hammer and firing pin parameters are inferred from AR-pattern scale and from the
  model's geometry. The cyclic rate is right because the port diameter was solved for it; a different but equally plausible
  set of inferred values would give a different port and a somewhat different timeline.
- The gas port position is taken from the model's gas block (photo-derived), not from a barrel drawing.
- The bore force steps down at bullet exit, where the in-bore model hands over to the scaled blowdown.
- The buffer is one rigid mass with a low rebound; the tungsten granules' dead-blow action is not simulated. The piston
  rod's return is not simulated. Bolt and carrier are rigid; the cam path is a smoothed helix.
- The firing pin is modelled starting from its rearmost position; a real floating pin often rests lightly on the primer
  after chambering. The disconnector and trigger reset are not modelled: after a semi shot the hammer simply returns to 0.
- The shooter is linear and passive: no grip-strength changes, no active recovery, no fatigue, no stance shift, and the
  support can pull as well as push. Human recoil response varies widely; treat the pose curves as a physically shaped
  starting point for tuning feel, not as a measured shooter.
- Muzzle device: the flash hider is given no braking and no compensating thrust.
- Ejection is an energy argument plus one bounce; the deflector geometry is a single plane and the scatter is assumed.
  The brass ground model is a point mass with a randomised cylinder bounce, not a rigid-body cylinder.
- One ammunition (M855 at the manual's figures), one temperature, a full magazine, a clean gun. Magazine weight is not
  reduced as rounds are fired.

## Optional input: residual bore pressure on the case head

`run(..., over={'residual_thrust': 1.0, 'case_seal_len': 0.006})` adds one force to the carrier group: once the lugs
are clear, the pressure still in the bore pushes on the case head (`case_head_area`) for as long as the case neck
seals the chamber (`case_seal_len` of travel, default 6 mm). It is off unless passed, so `action.json` and every
figure above are unchanged. It exists for muzzle devices that hold pressure in the bore: `assets/suppressor-qd-556`
passes it together with its own blowdown tables, and re-solves `port_d` so that the bare rifle still runs at 800 rpm
with the term on (1.156 mm). With the term on and the shipped port the bare rifle runs at 826 rpm.
