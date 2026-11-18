# Matched comparison: model against the reference figures

Method (`model/tools/render.py`, `model/tools/compare.py`): each figure crop gets a camera fitted by hand to it
(azimuth, elevation, lean, distance in `model/tools/views.json`; the figures carry no camera data, so these are
inferred), with the model's body centre placed on the same pixel and the same pixels per millimetre. The render's
alpha channel is the model's silhouette. The figure's silhouette is everything not connected to the picture border
through background brightness. The numbers are in `model/work/compare.json`; `renders/match_*.jpg` show the render
with the figure's silhouette outline in red. Side-by-sides with the figure are in `refs-local/compare/` (local only).

**What the numbers are.** `iou` is the overlap of the two silhouettes (intersection over union) in the crop.
`edge_offset_mm` is model minus figure for the silhouette's bounding box. `width_at_height` compares the
silhouette width at five heights. This measures outline and placement only. It says nothing about colour (the
figures are greyscale), surface detail, or the sides the figures don't show. It is not a fidelity percentage.

| View | Figure | IoU | Edge offsets, mm (left, top, right, bottom) | What limits it |
|---|---|---|---|---|
| `frag_figA2` | Fig. A-2 | 0.90 | -2.5, -1.2, -0.1, +1.7 | The figure silhouette includes the cast shadow at the base and left. The lever cap and ear are close but simplified; the fuze tower is a plain cone. |
| `flash_figA12` | Fig. A-12 | 0.83 | +1.1, -3.0, +0.2, +1.1 | The pull ring is a free part and sits differently; the model's fuze reads 3 mm taller; the figure's top hexagon is 4 % wider than the base (perspective or a turned top), the model's are equal. |
| `smoke_green_figB3` | Fig. B-3, third can | 0.91 | -0.9, -0.2, +4.5, +1.2 | Ring pose. This can set the can height. |
| `smoke_yellow_figB3` | Fig. B-3, second can | 0.91 | -0.7, +7.0, +2.2, -0.5 | The photo's fuze is taller in the frame than the green can's. |
| `smoke_violet_figB3` | Fig. B-3, first can | 0.84 | 0.0, +7.8, -4.9, -5.2 | The four photos are scaled differently in height: this can is 9 % taller for its width than the green one. Its lever is sprung outward and its ring lies across the top. |
| `smoke_red_figB3` | Fig. B-3, fourth can | 0.84 | 0.0, +10.6, +2.4, -6.3 | Same height scaling issue (13 %). |
| `smoke_white_figB5` | Fig. B-5 | 0.77 | -5.0, (-24.8), +2.3, -1.0 | Dark lever, fuze and ring on a dark background: the figure silhouette is the can only, so the top offset and the IoU are not meaningful. Left, right and bottom are. |

Read with the numbers: the bodies match their figures to about 1 to 3 mm at the outline where the figure can be
measured; fuze heads, levers and rings are simplified shapes at the right place and size, with differences of 3 to
5 mm. The figures are small (the stun grenade is 192 x 325 px in the PDF), so nothing finer can be claimed.

Visible differences that remain (see NOTES.md for the full ledger):
1. Markings are placeholder words and plain bars by the brief's rule, not the stencilled designations and lot numbers.
2. The frag's fuze is a cone, a block under the lever, a hinge pin and a bent lever with two ears. The die-cast
   detail of the real head (ribs, the notch in the lever cap, the stamped text) is not modelled.
3. The stun grenade shows light through its side holes in the figure. The model has a solid placeholder core, so
   the centre column of holes is dark.
4. M18 paint: the figure shows a dark can with light marks, the table says light green with black marks. The matched
   renders use the figure's tones; the default build follows the table. The owner should choose.
5. Lighting, backdrop and wear (scuffed band, chipped paint) are not reproduced.

Owner review has not happened yet. These results are the model's side of step 5 of the reference-to-3D order.
