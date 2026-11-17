# HK416 maintenance manual: facts for the simulations

Source: Heckler & Koch USA, *Maintenance Manual for HK416 Enhanced Carbine & Rifle System, 5.56mm NATO* (Training Group, 54 pages, scanned 2013). Read 2026-11-17 by Claude Opus 5.5 from carpetshark's copy. The manual is copyrighted ("All rights reserved"), so it isn't committed; these are summarised facts with page references. Our model is the **D14.5RS** (ident 203551; upper U14.5RS 233219; barrel 14.5 in threaded with gas block 233215).

## Specifications (p. 7), for the 14.5 in barrel
| Item | Value |
|---|---|
| Calibre | 5.56×45 mm NATO (.223 Remington) |
| Muzzle velocity | 2,790 ft/s (850 m/s). Others: 10 in 2,540; 16.5 in 2,887; 20 in 3,002 ft/s |
| Chamber pressure | 52,000 psi (358.5 MPa) |
| Cyclic rate | 700 to 900 rounds/min |
| Max effective rate | semi 45 rounds/min; sustained 12 to 15 rounds/min |
| Max effective range | point targets 500 m; area targets 600 m; max range 3,600 m |
| Operation | gas operated (short-stroke piston), firing from a closed bolt |
| Bolt | rotating bolt head with multiple locking lugs |
| Modes | semi, full auto |
| Feed | HK steel 30-round box magazine |
| Twist | 1 in 7 in, right hand |
| Trigger pull | 4.6 to 6 lb (20.5 to 26.7 N) |
| Weight | complete gun 7.7 lb (3.49 kg); upper assembly 5.5 lb (2.49 kg) |
| Overall length | 34.9 in extended (886 mm), 31.0 in collapsed (787 mm). Our model notes 804 mm collapsed (different stock) |
| Height without sights / width | 7.25 in (184 mm) / 2.25 in (57 mm) |

## Cycle of operation (pp. 8 to 12)
Order: feeding, chambering, locking, firing, unlocking, extracting, ejecting, cocking.
- **Feeding:** the bolt, driven forward by the buffer (recoil) spring, strips the top round from the magazine lips.
- **Chambering:** the round seats on its shoulder (headspace). Near the end of chambering the carrier trips the auto-sear release; the hammer starts forward but is caught by the sear notch.
- **Locking:** the bolt lugs rotate into the barrel extension through the cam pin in the carrier's cam track. *Caution: the manual's locking paragraph (p. 9) describes locking rollers and a locking piece, which is HK's roller-delayed G3/MP5 text left in by mistake. It does not apply to the HK416's rotating bolt.*
- **Firing:** the trigger releases the hammer, which strikes the firing pin, which strikes the primer. The firing pin protrudes through the bolt face only when the bolt is fully locked. On semi, the disconnector catches the hammer while the trigger is held; releasing the trigger hands the hammer to the trigger notch. On auto, the selector holds the trigger tail down so the disconnector is bypassed; the auto sear holds the hammer until the carrier trips it on locking.
- **Unlocking:** gas from the barrel port enters the gas block and drives the piston and the piston rod rearward into the bolt carrier. The carrier's rearward motion rotates the cam pin and unlocks the lugs. No gas enters the receiver (no gas tube).
- **Extracting:** the extractor claw, under its spring and buffer, holds the case rim.
- **Ejecting:** the spring-loaded ejector pushes the case forward against the bolt face; when the case mouth clears the ejection port, it pivots out to the right, strikes the **brass deflector** and leaves.
- **Cocking:** the carrier rides over the hammer and pushes it back; on the return stroke it's held by the trigger, disconnector or sear.
- **Bolt hold-open:** after the last round, the magazine follower lifts the bolt catch and the carrier locks to the rear (p. 26).

## Parts that matter for the simulations
- **Gas system:** gas piston assembly (piston with **3 piston rings**), piston rod assembly, a gas block per barrel length (14.5 in: ident 203638), and a threaded bushing for piston guidance in the upper receiver. If the piston falls out of the gas block under its own weight, the rings are worn (p. 27).
- **Buffer:** the HK buffer (red dot, HK marking) contains **tungsten granules**, an anti-bounce mass that damps carrier bounce. Use the HK buffer spring (red coil). Both are unique to the HK416 (p. 5).
- **Bolt carrier group:** bolt carrier, firing pin, firing pin retaining pin, cam pin, bolt head, ejector with spring and pin (5×10), extractor with pin, compression spring and buffer (p. 48).
- **Ejection port cover:** a spring-loaded cover on a hinge rod.
- **Muzzle:** the "compensator" (flash hider) on a standard US 1/2-28 thread (p. 6), with a crush washer.
- **Lower:** hammer, trigger, disconnector, auto sear, selector, pistol grip, receiver extension (buffer tube), sliding buttstock.

## Tolerances (p. 17)
| Item | Value |
|---|---|
| Bolt headspace | GO 1.8507 in, NO-GO 1.859 in |
| Firing pin protrusion | GO 0.0354 in (0.90 mm), NO-GO 0.0433 in (1.10 mm) |
| Bore | 5.56 mm; erosion limit 5.59 mm |
| Extractor claw | GO 1.28 mm, NO-GO 1.59 mm |
| Barrel nut torque | 110 ± 10 N·m (81 ± 7 ft·lb) |
| Handguard | 7 ± 1 N·m |
| Receiver extension | 59 ± 10 N·m |

## Sights (pp. 13 to 15)
- HK diopter rear sight drum: a "V" notch marked 1, then diopters 2, 3 and 4.
- Zero at **100 yd with the V notch**; the 2, 3 and 4 diopters then give 200, 300 and 400 yd.
- Elevation: a quarter turn of the drum moves impact about 1.5 in at 100 yd (about 1.4 MOA).
- Windage: one full turn moves impact about 6 in at 100 yd.
- Sight picture: front post centred, with an even halo of light through the diopter.

## Heat (p. 4)
After 250 rounds of rapid fire in under 3 minutes, let it cool. The barrel is cold-hammer-forged and rated for over 20,000 rounds with minimal accuracy loss.
