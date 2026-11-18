# Facts used from the owner's manual

Owner's manual 103855 for the 500, 590, Shockwave and Compact Cruiser pump actions. Page numbers are PDF pages. The
manual is all rights reserved: this file summarises facts and does not reproduce its text or figures. Its safety
rules are not summarised here; a game is not a place to learn gun handling.

| Page | Fact | Where it is used |
|---|---|---|
| 4, Fig. 1A and 1B | Part names: receiver, ejection port, chamber and breech, barrel, muzzle, magazine tube, forearm, trigger, trigger guard, safety button, bolt. The chamber is the rear of the barrel's inside; the breech is the barrel's rear face. | Part names in `model/build.py`. Fig. 1A as a cross-check of the photo ruler (`NOTES.md`). |
| 5, Fig. 2 and 3 | The safety button is on the top rear of the receiver. Fully rearward is ON (SAFE) and covers a red dot; forward is OFF (FIRE) and shows the dot. | `safety_button`, `safety_red_dot`, clips `safety_to_fire` and `safety_to_safe`, `setSafety()`. |
| 6, Fig. 4 | The action lock lever is on the left of the trigger housing, just behind the trigger guard. Pressing it lets the closed action be opened without pulling the trigger. | `action_lock_lever`, clip `action_release`, `holdActionLock()`. |
| 6 to 7, Fig. 5 and 6 | 590 models: the barrel's takedown mount slides over the magazine tube and the magazine cap holds it, finger tight. The barrel extension seats against a shoulder in the top of the receiver. | `barrel_ring`, `magazine_cap`, the `takedown` clip. |
| 8 | Capacity: the models this manual covers hold six in all. One fewer may fit with 3 in shells. Chambered for 2 3/4 in and 3 in shells. | The capacity of the full-length gun (nine in all) is the maker's specification, not this manual's figure. The "one fewer with 3 in" note is kept. |
| 8, Fig. 7 | To load fully or to fire single shots: open the action, put the first shell through the ejection port into the chamber or onto the elevator, close the action. | `loadThroughPort()`. |
| 9, Fig. 8 | Load the magazine with the action closed and the trigger guard up: push each shell in until its rim snaps past the cartridge stop. | `insertShell()`, clip `shell_insert`, sound `shell_insert`. |
| 9 | Pulling the trigger through its travel with the safety OFF fires. Pulling the forearm completely rearward ejects the case through the ejection port. The action lock lever must be depressed to eject an unfired shell. | `pullTrigger()`, `setSlide()`, the action lock rule. |
| 10 | Pushing the forearm fully forward chambers a shell from the magazine. Pulling it completely rearward releases the next shell onto the elevator. | The `shell_released` and `chambered` events. |
| 10, Fig. 9 | Unloading: open the action slowly and take out the chambered shell; fully rearward releases the next one, which drops out of the port; close the action; then press the cartridge stop through the bottom opening to release shells one at a time. | `tipOutElevatorShell()`, `releaseFromMagazine()`. |
| 10 to 11, Fig. 10 | Takedown starts with the bolt's front in the middle of the ejection port; 590 models: unscrew the magazine cap, then draw the barrel out. | The first steps of the `takedown` clip. |
| 13, Fig. 16 | The trigger housing is held by one pin through the receiver (a punch of at most 3/16 in). The housing lifts out rear first. It is not to be taken apart. | `trigger_housing_pin`, `trigger_housing_group`. The housing's internals are not modelled. |
| 13, Fig. 17 | The cartridge interrupter and the cartridge stop then come out of the receiver's side walls. | `cartridge_interrupter`, `cartridge_stop`. |
| 14, Fig. 18 and 19 | The bolt slide lifts out when the action is about three quarters back; the bolt slides out forwards through the barrel opening; the elevator pivots out and its two arms are squeezed together to free it; the forearm and action slide come off the front of the magazine tube. | The rest of the `takedown` clip. |
| 16, Fig. 21 | The elevator's studs fit 1/4 in holes in the receiver. The ejector is in the wall opposite the ejection port and fits a slot in the bolt. The bolt lock faces the top front of the receiver. | `elevator_stud_r/l`, `ejector`, `bolt_lock`. |
| 17, Fig. 22 and 23 | The bolt slide's side lugs sit in a slot in each action slide bar; its top lug fits the bolt lock. The stop and interrupter hook inwards. | `bolt_slide`, `action_bar_left/right`, the lost-motion unlock. |
| 20 | Function test: lever held, the action opens and closes freely. Safety ON, pull: the hammer does not fall. Release, safety OFF: it does not fall. Pull: it falls. Open the action, safety ON. | `action/test_action.js` runs this sequence. |
| 28, 30 | Parts lists: barrel assembly, front sight, takedown parts, front swivel stud, magazine cap (590), receiver, ejector and screw, magazine follower, spring and tube, action slide assembly, cartridge interrupter and stop, elevator, bolt slide, bolt assembly, trigger housing assembly, trigger housing pin, rear swivel stud. | The model's part list. |

Not taken from the manual: anything about altering the gun, and nothing was looked for.
