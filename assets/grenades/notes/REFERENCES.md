# Reference sources (cited, not committed)

One source, approved by carpetshark on 2026-11-18 as the reference pack for this asset:

**US Army FM 3-23.30, *Grenades and Pyrotechnic Signals*, 15 October 2009** (approved for public release).
Keep a local copy in `refs-local/` (ignored by git) if you rebuild the comparison. Page numbers are PDF pages.

| ID | What | Where | Used for |
|---|---|---|---|
| `figA2` | Fig. A-2, photo of the fragmentation grenade | p114 | `frag` shape (and the `impact` body) |
| `tabA1` | Table A-1 | p114 | `frag` weight, delay, throwing distance, casualty and killing radius, colours |
| `figA12` | Fig. A-12, photo of the stun grenade | p123 | `flash` shape |
| `tabA5` | Table A-5 | p123 | `flash` length, hexagon size, weight, delay, candlepower, decibels, 9 m, colours |
| `figB3` | Fig. B-3, four photos of the coloured smoke grenade | p129 | `smoke-*` shape, markings layout, band |
| `tabB2` | Table B-2 | p130 | `smoke` weight, delay, throwing distance, burn time, colours, four top holes |
| `tabB3` | Table B-3 (a different grenade in the same can) | p131 | can diameter 2.5 in only |
| `figB5` | Fig. B-5, photo of the white smoke grenade | p131 | `smoke-white` shape |
| `tabB4` | Table B-4 | p132 | `smoke-white` weight, delay, throwing distance, burn time, colours |
| `figA1` | Fig. A-1, confidence clip | p113 | read, not modelled (see NOTES.md, omissions) |

Local files the tools name (all in `refs-local/`, none in git): `figA2-M67.png`, `figA12-M84.png`, `figB3-M18.png`
(the two image strips of Fig. B-3 joined), `figB5-ANM8.png`. They are the figures' image rectangles rendered from the
PDF at 4x (288 dpi): `figA2` page rect (205.0, 73.5, 389.0, 305.4) pt, `figA12` (268.9, 73.5, 361.1, 229.3),
`figB3` (99.0, 398.3, 531.0, 574.3), `figB5` (256.4, 381.5, 373.6, 597.5). Every pixel coordinate in
`DECOMPOSITION.md` and `model/tools/views.json` is in those files.

**Not used, on purpose.** The tables' filler and fuze rows, and anything about how a device works inside. This asset
is a game model of the exterior and of published effect figures.

Other published figures used, each named where it is used:
- Body diameter of the fragmentation grenade, 2.5 in: a widely published figure for this grenade (it is not in
  Table A-1). Cross-checked in `figA2`: the body's outline fits a circle. Its overall length is often published as
  3.53 in (89.7 mm); the model uses 84.5 mm measured in `figA2` and NOTES.md records the difference.
- 140 dB peak as the unprotected impulse-noise limit: OSHA 29 CFR 1910.95 and MIL-STD-1474.
- Drag coefficients (smooth sphere, short cylinder): S. F. Hoerner, *Fluid-Dynamic Drag*.
- Jet noise peak at a Strouhal number near 0.2; Hertz contact time; free ring and free-free beam bending modes:
  standard textbook results, formulas given in `sound/sim.py`.

The figures in a US Army field manual are US government work. The figure images are still not committed here: the
comparison images in `renders/` contain the model render and a traced outline of each figure's silhouette (a
measurement), not the figure's pixels. Side-by-side images with the figures are written to `refs-local/compare/`
for local review only. The main session can decide to commit them if the owner confirms their status.

Product designations are those of the US Army. openFPS is not affiliated with any maker; the model carries no
maker's names or logos (the maker's label visible in `figA12` is a plain panel on the model).
