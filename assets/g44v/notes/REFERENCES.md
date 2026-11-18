# Reference sources (cited, not committed)

The shape was measured from these. None of them is in this repository: the manual and the maker's images are all rights
reserved. Keep local copies in `refs-local/` (ignored by git) to re-trace or re-run the matched comparison.
`model/outlines.json` holds every traced outline in the pixel coordinates of the dimension image, with the ruler, so each
number can be checked against that image.

| Local file | What it shows | Source | Used for |
|---|---|---|---|
| `refs-local/glock-web/18162-Glock-44-V.jpg` | Left side and rear view with numbered dimension lines (1654 x 1042 px). The primary reference and the ruler. | The maker's product page for this model (image URL recorded in `model/outlines.json`). | All traced outlines; positions of pins, controls, serrations, panels; widths from the rear view. |
| `refs-local/Instructions-for-use_Relaunch_G44V_032026-en.pdf` | Instructions for use, edition 03-26, 48 pages. | Supplied by carpetshark. | Part list and exploded drawing (pp. 36-37), nomenclature (p. 9), operation and field strip (pp. 6-7, 11-12, 18-23, 30-34), backstraps and magazine catch (pp. 38-40). |
| `refs-local/img/p27_0.png` | Manual p. 27 picture 30: the slide from below, square on. | Extracted from the PDF. | Breech face, firing pin lug slot, firing pin safety, rail cuts. Ruler: 3610 px = 174 mm. |
| `refs-local/img/p23_4.png`, `p23_5.png` | Manual p. 23 picture 27: slide from above and from the left, square on. | Extracted from the PDF. | Ejection port, barrel hood, top panel, sights. Ruler: 608 px = 174 mm. |
| `refs-local/img/p21_2.png` | Manual p. 21 picture 18: pistol with the slide locked open. | Extracted from the PDF. | Lock-open travel (42 mm), exposed barrel diameter. Ruler: 484 px = 174 mm. |
| `refs-local/img/p23_3.png`, `p22_*.png` | Manual pp. 22-23 pictures 21-26: field strip. | Extracted from the PDF. | Order of the field-strip clip; the nose lug that carries the recoil spring. |
| `refs-local/pages/*.png` | Page renders and contact sheets made while studying the manual. | Made locally from the PDF. | Reading only. |

Published numbers that are not images: the maker's specification table (`notes/MANUAL_NOTES.md`); CCI product pages for
parts 35, 30 and 960 (cci-ammunition.com, retrieved 2026-11-17); SAAMI Z299.1 (rimfire) for the .22 Long Rifle pressure
limit, case and bore dimensions and standard twist; the two sound-level figures cited in `sound/README.md`.

GLOCK and G44 are trademarks of their owner. openFPS is not affiliated with or endorsed by the maker, and the model
carries no maker's names or logos.
