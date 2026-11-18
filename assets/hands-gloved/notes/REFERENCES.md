# Reference sources (cited, not committed)

Three photographs of gloved hands on an M27 (the Marine Corps' HK416 variant) are the chosen references for the
grips and the glove. None of them is in this repository. Keep local copies in `refs-local/` (ignored by git) under the
file names below to re-run `checks/compare.py`. `refs-local/sources.json` (local) records the download URLs.

| ID | Local file | Pixels | What it shows | Source |
|---|---|---|---|---|
| R1 | `R1_firing_hand_rear_right.jpg` | 4761 x 3174 | Firing hand on the pistol grip from behind and to the right, index finger on the trigger; support hand on the front of the magazine well. Knit-backed tactical gloves. Primary reference for the glove and for the firing grip. | Wikimedia Commons, "Exercise Joint Viking 25- Cold Weather Training Week 5 (8892593).jpg"; DVIDS image 8892593, U.S. Marine Corps photo, 27 Feb 2025. Public domain (work of the U.S. federal government). |
| R2 | `R2_support_hand_right_profile.jpg` | 5617 x 4213 | Right profile. Support hand under the handguard, four fingers up the right side, thumb tip over the top rail; firing hand on the grip, mostly covered by its cuff. Primary reference for the support grip. | Wikimedia Commons, "1st Battalion, 2nd Marine Regimen in Cold Weather Training during Nordic Response 24 in Norway (8242979).jpg"; DVIDS image 8242979, U.S. Marine Corps photo, Feb 2024. Public domain. |
| R3 | `R3_right_side_prone.jpg` | 5184 x 3456 | Right side, prone. Firing hand with the index finger straight along the receiver; support hand around the magazine well and magazine. Reference for the indexed trigger finger and for the magazine grip. | Wikimedia Commons, "Exercise Joint Viking 25- Cold Weather Training Week 2 (8864224).jpg"; DVIDS image 8864224, U.S. Marine Corps photo, Feb 2025. Public domain. |

The crops used in the decomposition are cut from these with `tools/crops.py` (regions listed in
`notes/DECOMPOSITION.md`).

## How they were chosen

All 49 images in Wikimedia Commons' category "M27 Infantry Automatic Rifle" were looked at as thumbnails on
2026-11-17. The three kept are the ones where a gloved hand on the rifle fills enough pixels to measure, the rifle is
the HK416 pattern (so the model's rifle is the right ruler), and the licence is public domain. Between them they show
each hand in two positions. No reference shows the left side of the rifle, so the firing hand's thumb is never seen:
that part of the grip is an inference (see `notes/NOTES.md`).

**Selection status: approved by the owner.** The owner approved R1, R2 and R3 (and the CR-1 rework) in the project
thread, message `cmsg_01K1vC6sgxYrGKq5a7aX428P3KySEwyFdWgdFJWbWQTJbj`, 2026-11-18 02:49 UTC ("appprove"). The modeller
of version 2 read that message itself. The approval covers these three references and CR-1 as recorded in
`notes/NOTES.md`; it is not an approval of the result. If the owner later picks different references, the
decomposition, studies, grips and comparisons must be redone from them (rule 7: a new version).

CR-2 (2026-11-18, version 3) kept these three references as approved. It was a direction to continue the work, not an
approval of version 2's result or of version 3's (`notes/NOTES.md`).

## Notes on use

- The photographs are public domain, but they show identifiable people and makers' marks, so they are still kept out
  of git. Only simulation-generated renders are committed.
- The appearance of U.S. Department of Defense visual information does not imply or constitute DoD endorsement.
- The gloves in R1 carry a maker's name on the wrist tab and a printed pattern on the back. The model has neither:
  a plain placeholder panel and plain knit (rule 2).
- Numbers that come from publications (anthropometry, joint ranges) are listed with their sources in
  `model/handlib.py` (`SRC`) and `notes/NOTES.md`.
