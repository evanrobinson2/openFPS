# Generic QD 5.56 mm suppressor: notes

## Brief (2026-11-17)

A generic quick-detach 5.56 mm suppressor for `socket_muzzle` of the HK416: no maker's name or logo, placeholder
panels; a parametric recipe with mount, baffle stack (named baffles), tube and end cap, and the QD attach motion as a
clip. Simulation: gas dynamics through the stack from the HK416 interior ballistics, the reduction of the muzzle's
sound level with the supersonic crack unchanged, first-round pop, flash suppression, back-pressure on the operating
cycle, and can heating. Sound synthesised from the simulation as something `assets/hk416/sound` can apply. Checks
against published data and a JS-against-Python parity test. Limits written down.

## Decisions and inferences

1. **No reference image.** The brief asks for a generic can, so nothing was traced. The layout is mine: a 174 mm by
   38.1 mm tube, 52 mm of it over the muzzle device, six 50° cone baffles on a 15.5 mm pitch with spacer skirts, a
   thicker blast baffle 19 mm ahead of the hider, a 7.2 mm bore, a 4.5 mm end cap. All are tagged `[class]`,
   `[rifle]` or `[inferred]` in `model/geom.py`.
2. **The mount.** The HK416 recipe carries an A2-pattern flash hider, and the brief says the can fits
   `socket_muzzle`, so the can goes over that hider. It seats on the hider's front shoulder; a collar turned 60°
   closes three jaws on the jam ring behind the hider. This is a plausible mechanism, not a real product's. The cam
   that drives the jaws is inside the collar and is not modelled: the collar's pocket is drawn at its open radius.
3. **Clips.** Baffles 2 to 6 have a scallop cut in the apex lip, alternating top and bottom. Their open area is
   counted (44.5 mm² against 40.7 mm² plain); the cross-flow they cause is not modelled.
4. **Placeholder panels.** `marking_panel` on the tube, `index_panel` and `collar_index` as lock witness marks. All
   plain.
5. **Salvage.** The old partial work (`geom.py`, `gas.py`, `build.py`) was reused in structure and re-checked against
   the rules. Changed: every dimension re-tagged with its source; the flash hider's bore corrected from an assumed
   4.5 mm radius to the recipe's 7.8 mm; jaws, panels, sockets, hierarchy and clips added; the gas model's tuned
   "core jet" (four free parameters) replaced by a carry-over term with a published form and one calibrated factor;
   the dipole, breech leak, acoustics, action coupling, heat strings and flash input are new. The old `.glb` files
   were not used.
6. **Interior ballistics.** The bore state is the HK416 action's. Its mean pressure at bullet exit is 126 MPa, about
   twice what is usually quoted for a 14.5 in 5.56 barrel. It was kept, because the brief says to use the HK416
   figures and the two assets must agree; the consequence is written in the limits.
7. **Calibration.** Uncalibrated, the model gives a 15.4 dB reduction at 1 m with the plain labyrinth carry-over and
   49 dB with none. One factor on the carry-over (`clip_factor`, 0.819) is solved for the 22.5 dB midpoint of the
   published range. The directivity needed a second: a compact monopole alone is the same in all directions
   (14.9 dB at the ear), the full compact dipole cancels it behind the muzzle (50 dB), so the share of the dipole
   (`dipole_share`, 0.393) is solved for the 20.5 dB midpoint at the ear.
8. **Change to the HK416 action.** `assets/hk416/action/sim.py` gained one optional input, `residual_thrust` (with
   `case_seal_len`), read from `over`. It is off unless passed, so the shipped `action.json` is unchanged. It was
   needed because the shipped model has no way for bore pressure to push the bolt back, and that is how a can acts on
   a piston rifle whose gas system vents early.
9. **Flash.** `assets/hk416/flash/` is on another branch. Its phase names were read from that branch so the scale
   keys match; nothing else was taken from it and the coupling is untested.

## Omissions

- No textures, wear or heat tint on the model; three materials and a panel shade.
- No LOD1: the model is 12,936 triangles.
- No threads, wrench flats on the mount, welds, detent or cam.
- No sound of the can itself (ringing), no ejection-port pop, no piston-vent noise.
- No point-of-impact shift, no change in muzzle velocity.
- No temperature map along the can.

## Change log

| Version | Date | What |
|---|---|---|
| 1 | 2026-11-17 | First version in openFPS, rebuilt from the paused partial work. |
| 1.1 | 2026-11-17 | Change request (owner's decision that cinematic sound is the default; the brief asked that the can work with HK416 sound v2). `soundOverlay()` / `core.sound_overlay()` now also scale the v2 tables' gas-volume body (`bm`) with the pop and the jet's gain (`g`): without this the patched v2 rifle was 145.2 dB at the ear instead of 136.8 dB (reduction 12.2 dB instead of 20.6 dB; the three level cases of `sim/test.js` failed on v2 and now pass). The v1 path is unchanged. In v2 the jet is not lengthened (its envelope is shared). The cinematic chain of the HK416 takes the patched tables as `suppressor`: 9.9 dB quieter at the gun, the bullet's crack unchanged sample for sample. The sample page is pinned to `mode: 'realistic'`. **Open:** the parity case `sound overlay` in `sim/test.js` still fails, as it did before this change, because its reference numbers in `suppressor.json` were generated from the v1 HK416 tables; `python3 sim/sim.py` was not rerun here. |
