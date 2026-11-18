# Reference sources

The reference pack was approved by carpetshark on 2026-11-18 (`GRENADES_SHOTGUN_BRIEF.md`). Local copies live in
`refs-local/` (ignored by git). One public-domain photo appears in a committed comparison image; nothing else from
these sources is in the repository.

| File in `refs-local/` | What it is | Source and licence | Used for |
|---|---|---|---|
| `commons-atf-mossberg-590.jpg` (1148 x 263 px) | Right side, full length, white ground: 20 in barrel, full-length magazine tube, synthetic stock and forend, bead sight, lug band. | Wikimedia Commons, `File:Mossberg 590.jpg`, https://commons.wikimedia.org/wiki/File:Mossberg_590.jpg. Author: U.S. Bureau of Alcohol, Tobacco, Firearms and Explosives (ATF.gov). **Public domain** (work of the US federal government, Commons tag PD-USGov-DOJ). Retrieved 2026-11-17. | **The primary profile.** Every traced number in `model/build.py` and `model/reference_trace.json` is a pixel of this image. It appears in `renders/compare_right.jpg`. |
| `commons-peo-590a1-cropped-1280.jpg` (1920 x 389 px) | Left side of a 590A1 with a heat shield. | Wikimedia Commons, `File:PEO Mossberg 590A1 (cropped).jpg`, https://commons.wikimedia.org/wiki/File:PEO_Mossberg_590A1_(cropped).jpg. "Photo Courtesy of PEO Soldier" (US Army). **Public domain.** Retrieved 2026-11-17. | Left-side controls only: the action lock lever, the ejector screw, the side plug, the loading port. It is a different model (heavier barrel, heat shield), so nothing else is taken from it. Not committed. |
| `commons-shotgun-mossberg-590.jpg` (640 x 247 px) | Right side with a sling, low resolution. | Wikimedia Commons, `File:Shotgun Mossberg 590.jpg`. Public domain (Commons tag PD-USArmy; no author recorded). Retrieved 2026-11-17. | Looked at, not used: too small to measure. |
| `mossberg-103855-pump-manual.pdf`, `mossberg-p04.png` to `p20`, `p28` to `p31` | Owner's manual 103855, "500, 590, Shockwave and Compact Cruiser" pump actions (layout dated 2/27/18). | O.F. Mossberg & Sons. **All rights reserved**: never committed, no page images, no long quotations. | Controls, operation, capacity note, takedown order, part names (`notes/MANUAL_NOTES.md`, by page). Its drawings show the short models; they were used for the mechanism, and Fig. 1A as a cross-check of the ruler. |

## Cited, not held

| What | Source | Note |
|---|---|---|
| Overall length 41 in, barrel 20 in, length of pull 13.87 in, weight 7.25 lb, capacity 9, cylinder bore, bead sight | The maker's product listing for model number **50645** (590, 12 gauge, 20 in, 9 shot), https://www.mossberg.com/firearms/shotguns/590.html. | **The maker's site refused automated requests (HTTP 403) on 2026-11-17**, so these figures were read from a dealer's listing that reproduces the maker's specification sheet for the same model number (kygunco.com, "Mossberg 590 Heat Shield 12 Gauge 20 in 9rd", MPN 50645) and agree with other dealers' listings of the 20 in 9-shot 590 (41 in, 13.87 in). That listing's gun has a heat shield, which the chosen profile and the brief's configuration do not: the shield is not modelled. Someone should confirm the five figures against the maker's own page by hand. |
| Full-length parts schematic | Brownells, Mossberg 590 12 gauge schematic, https://www.brownells.co.uk/Schematics/Mossberg/Shotguns/Mossberg-590-12-Gauge-Schematic | **Also refused automated requests (HTTP 403).** It was not read. Part names come from the manual's two parts lists (pp. 28 and 30), which share the action, trigger group, bolt, slide and magazine parts with the full-length gun. |
| Slug: 438 gr, 1610 ft/s, G1 BC .110, and the downrange table (velocity, energy, 10 mph wind drift, path with a 100 yd zero) | Federal Premium, Power-Shok Rifled Slug, part F127 RS, https://www.federalpremium.com/shotshell/power-shok/power-shok-rifled-slug/11-F127+RS.html, read 2026-11-17 | The ballistics check. |
| Buckshot: nine 00 pellets, 1325 ft/s, lead at 11.35 g/cc | Federal Premium, Power-Shok Buckshot, part F127 00, https://www.federalpremium.com/shotshell/power-shok/power-shok-buckshot/11-F127+00.html, read 2026-11-17 | No downrange or pattern figures are published for it. |
| 00 buck is .33 caliber; a cylinder bore spreads about 1 in per yard | R. Mann, "Buckshot Basics", Shooting Illustrated, 31 January 2012, https://www.shootingillustrated.com/content/buckshot-basics/ | A rule of thumb, used as the pattern's nominal. |
| Recoil momentum balance and the 1.5 gas factor for shotguns of average barrel length | SAAMI, "Gun Recoil Formulae" (2018), https://saami.org/technical-information/recoil-formulae/ | The factor was read from a summary of the note, not from the PDF itself. |
| Peak level at the shooter's ear, 12 gauge: 151.5 dB (28 in) and 161.5 dB (18.5 in) | W. Krammer, Ball State University, as reproduced in E.A.R. Inc., "Gunfire Noise Level Reference Chart"; range 150 to 165 dB in Meinke et al., 2017 (PMC5634813) | A loose check of the synthesised shot's level. |
| 12 gauge 2 3/4 in maximum average pressure, 11,500 psi; rim and body diameters | ANSI/SAAMI Z299.2 | **Recalled, not re-read.** Used only as an upper bound and for the template shell's size. |

The model carries no maker's names, logos, roll marks or serial numbers. "Mossberg" and "590" are trademarks of
O.F. Mossberg & Sons; openFPS is not affiliated with or endorsed by them.
