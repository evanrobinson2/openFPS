# Reference sources (cited, not committed)

Version 2 of the shape (2026-11-18) is built from Heckler & Koch's own documents. None of them is in this repository.
Keep local copies in `model/refs-local/` (ignored by git) to re-check the model with `model/tools/fit_drawing.py`.
All are public HK documents served from HK's manuals bucket, `https://s3.amazonaws.com/hk-manuals/files/`.

| Key | Document | What the recipe takes from it |
|---|---|---|
| HKTD | Heckler & Koch, "HK416 Cal. 5.56 mm x 45" technical data, Ident-No. 968 071, V003.12.08 (`Military/HK416/`). | p. 12: the dimensioned vector drawing (side and top view) and the dimension table: A 804/900 mm (14.5 in, stock collapsed/extended), B 78 mm, C 240 mm, D 368 mm, E 371 mm, 3490 g; buttstock travel 96 mm in 6 positions; MIL-STD-1913 rails at 3, 6, 9 and 12 o'clock. Every outline and position in `build.py`. |
| HKA5 | Heckler & Koch, "HK416 A5" technical data sheet, Id. 975584, V002.03.13. | Per-barrel dimensions (10, 11, 14.5, 16.5, 20 in) used for `--barrel`; width 74 mm, sight radius 430 mm. |
| HKMM | Heckler & Koch GmbH, "Rifle HK416 Calibre 5.56 mm x 45" Maintenance Manual (HK416 10 / 14.5 / 16.5 / 20 in), 84 pp. (`Armorer/HK416/`). | Fig. 1a "Illustration of individual components" (97 parts): the part breakdown and part names; Part III disassembly figures for hidden faces (right side, grip width, handguard bolt, flash hider). |
| HKUS | Heckler & Koch USA, "Maintenance Manual for HK416 Enhanced Carbine & Rifle System" (2013). | Specifications and tolerances; the mechanism simulations in `action/`. |
| HKOM | Heckler & Koch, HK416 operator's manuals (2007 and Enhanced Carbine). | Controls and their positions (selector, bolt catch, magazine release, stock latch, sights). |
| HKMAG | Heckler & Koch steel magazine instructions; HKTD magazine table (195 x 87 x 22 mm, 250 g). | Magazine depth and the stamped ribs. |
| 1913 | MIL-STD-1913 (Picatinny rail). | 10.0 mm pitch, 5.23 mm slots, 21.2 mm rail width, 15.7 mm top flat. |

## How the drawing was measured

HKTD p. 12 is a vector drawing, so its lines can be read to about 0.3 PDF points (about 1 mm on the rifle).
It shows the rifle's left side, muzzle left, with the 16.5 in barrel and the stock collapsed. Scale: 3.682 mm per
point, from HKTD's own A = 855 mm and C = 240 mm; the drawing's D and E agree within 1 %.

    side view:  L = (161.55 - x) * 3.682      Z = (613.125 - y) * 3.682
    top view:   L = (426.70 - x) * 3.682      S = (y - 640.52) * 3.682   (the top view shows the right side up)

`model/drawing_trace.json` holds the closed outlines traced from the side view (magazine with its ribs, pistol grip
and its panel): the regions were flood-filled from seed points, moved out to the line centres and simplified to
0.25 mm. Everything else was read off the drawing as numbers, written next to each value in `build.py`.

The 14.5 in default is the drawing's rifle with the barrel and flash hider moved back by
51 mm (HKTD's D: 419 to 368 mm). The gas block, front sight and handguard stay where they are: HKTD gives the same sight radius E = 371 mm for both barrels. That gives 805 mm overall with the stock collapsed, against HK's 804 mm.

## What the drawing cannot show

Widths and the right side come from the top view, HKMM's figures or MIL-STD-1913, and say so in `build.py`.
A few numbers are marked INFERRED: the ejection port and dust cover size (AR-15 pattern, HKMM Fig. 1a part 2),
the pistol grip width, and the position of the third fire-control pictogram, which the selector hub hides.

## Version 1

Version 1 (2026-11-17) was traced from one studio photo plus a Wikimedia drawing and replica close-ups. Its notes and
sources are kept in `v1-photo/`.

HK416 is a trademark of Heckler & Koch. openFPS is not affiliated with or endorsed by Heckler & Koch, and the model
carries no maker's names or logos.
