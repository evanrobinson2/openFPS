# HK416 model vs HK's maintenance manual

Compared 2026-11-17 (Claude Opus 5.5). Model: `hk416.glb` (301 parts), measured from its own geometry. Manual: HK USA HK416 maintenance manual (see `MANUAL_NOTES.md`). Its cover photo and parts breakdown show the **early HK416 (2005)**: M4-style collapsible stock, A2-style grip, and the HK diopter drum rear sight. Our model follows the later D14.5RS reference photos: HK's ribbed adjustable stock, HK ergonomic grip, quad rail, folding front and rear sights. Several differences below come from that generation gap, not from modelling error.

## Dimensions
| Item | Manual (14.5 in) | Model | Verdict |
|---|---|---|---|
| Barrel | 14.5 in (368.3 mm) | 368.3 mm | Match |
| Overall length, collapsed | 31.0 in (787 mm), M4-style stock | 803.7 mm, HK stock | +17 mm. Expected: the HK stock is longer than the manual's stock; 804 mm is the published figure for this configuration |
| Overall length, extended | 34.9 in (886 mm) | not measured here (the `stock_extend` clip exists) | To check |
| Height without sights | 7.25 in (184 mm) | 191 mm (rail top to grip bottom, no sights, no magazine) | +7 mm (4 %). Likely the HK grip's lower bottom; worth a look |
| Width | 2.25 in (57 mm) | 60.0 mm (overall, including controls) | +3 mm (5 %). Within the selector, charging handle and QD-cup spread |
| Weight | 7.7 lb complete, 5.5 lb upper | no masses in the model | Missing: add per-part masses so the action and recoil simulations can use them |

## Parts in the manual's breakdown (pp. 45 to 50) vs the model
Present and visible: upper and lower receivers, barrel, barrel nut, gas block with its 2 pins, crush washer, compensator (flash hider), ejection port cover with spring, hinge rod and clip, forward assist (button, housing, pin), charging handle with latch, bolt carrier, bolt head, bolt catch, magazine catch and release, selector (both sides, with stops), trigger, trigger and hammer pins, sear pins, takedown and pivot pins, receiver extension (buffer tube), end plate with sling eyes, castle nut, sliding buttstock with latch, pistol grip.

Not modelled, by design (`BRIEF.md`: "Do not model what no player ever sees: fire-control internals, springs, gas-system internals"): gas piston, 3 piston rings and piston rod (manual items 6 to 9), threaded piston-guide bushing (27), firing pin and its retaining pin, cam pin, ejector, extractor and their springs (39 to 51), hammer, disconnector and auto sear bodies (only their pins show), buffer and recoil spring (53, 59).

These now matter. The action simulation drives the carrier, hammer and firing pin, and the sound model needs the piston and buffer impacts. Visible through the open ejection port: the cam pin, the extractor and the case. Visible when the bolt locks back: the hammer. If those views appear in the game, the following should be modelled: the hammer, cam pin, extractor, ejector and firing pin tip; the piston and rod (if the handguard ever comes off); and the buffer and spring (only for a disassembly view).

## Sights
- Manual: the HK diopter rear sight is a **rotary drum** with a "V" notch (1) and diopters 2, 3 and 4 (100 to 400 yd), zeroed at 100 yd with the V notch.
- Model: a **folding rear sight with one ghost-ring aperture** and a windage knob (`NOTES.md` calls it a compromise between the replica and the profile photo).
- Consequence: the model can't show the 100/200/300/400 yd drum settings. For an accurate HK diopter sight, the rear sight should become a rotating drum with a V notch and three apertures, plus a drum-rotation clip. The front sight post and ears match the manual's description (a front post centred in a halo of light).

## Operation (manual's cycle vs the model's clips)
| Manual | Model | Note |
|---|---|---|
| Charging handle pulls the carrier back; the carrier locks back on the bolt catch | `charge` (carrier about 91 mm), `bolt_catch` | OK |
| Magazine release and insertion | `mag_release`, `mag_out`, `mag_in` | OK |
| Ejection port cover opens when the carrier moves | `dust_cover_open` | OK |
| Selector: safe, semi, auto | `safety_to_fire` / `safety_to_safe` (two positions) | Missing the **auto** position (manual: safe, semi, auto). Add a third selector stop and clip |
| Hammer falls, firing pin strikes, carrier trips the auto sear | trigger rotation only (`trigger_pull`) | Hammer and firing pin not modelled (see above) |
| Bolt holds open on the last round (follower lifts the bolt catch) | `bolt_catch` exists; no follower-driven hold-open clip | The range page should hold the carrier back on empty and release it on reload |
| Stock collapse and extend | `stock_extend` / `stock_collapse` | OK (different stock from the manual's) |

## Suggested follow-ups (model work, Fable's lane, on request)
1. Add per-part masses (or material densities) so the simulations use real weights (target 3.49 kg complete with an empty magazine, as the manual specifies).
2. Model the parts the action simulation moves and the player can see: hammer, cam pin, firing pin tip, extractor and ejector.
3. Add the selector's auto position and its clip.
4. Optionally, an HK diopter drum rear sight variant.
5. Check the 7 mm height excess at the grip.
