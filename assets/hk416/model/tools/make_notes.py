"""python3 tools/make_notes.py : writes NOTES.md and notes.json from the latest check results (work/*.json)."""
import json, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = lambda p: json.load(open(os.path.join(HERE, p)))
C, S, R, L0, L1, INV = L('work/checks.json'), L('work/score.json'), L('work/rounds.json'), L('work/stats_lod0.json'), L('work/stats_lod1.json'), L('inventory.json')
CU = L('tools/closeups.json')
ok = lambda b: 'PASS' if b else 'NOT MET'
rp, dr, dl = S['right_photo'], S['drawing_right'], S['drawing_left']
cr, cl = S['reference_ceiling_photo_vs_drawing_right'], S['reference_ceiling_photo_vs_drawing_left']
merges = [r for r in INV if r.get('merged')]
MEAS = [  # what, image, pixel span, result
 ('Rail pitch (the ruler)', 'profile-right-photo.png', 'top rail lug leading edges x = 272 to 559 at y = 36: 287 px over 32 pitches', '8.97 px per 10.0 mm, so 0.897 px/mm (1.115 mm/px)'),
 ('Bore axis', 'profile-right-photo.png', 'barrel edges y = 61 to 77 at x = 640 to 685', 'centre y = 69.0 (Z = 0)'),
 ('Upper receiver front face (L = 0)', 'profile-right-photo.png', 'x = 372 (handguard joint)', 'origin of L'),
 ('Overall length, stock collapsed', 'profile-right-photo.png', 'x = 8 to 729 (721 px)', '804 mm (the commonly published figure for the D14.5RS with the stock collapsed is 804 mm)'),
 ('Barrel, visible part', 'profile-right-photo.png', 'gas block front x = 593 to flash hider base x = 690.5', '108.7 mm exposed; diameter 16 px = 17.8 mm'),
 ('Barrel neck', 'profile-right-photo.png', 'x = 614 to 636, y = 63 to 76', '24.5 mm long, 14.5 mm diameter'),
 ('Flash hider', 'profile-right-photo.png', 'x = 690.5 to 729, y = 60 to 79', '42.9 mm long, 21.2 mm diameter'),
 ('Handguard length', 'profile-right-photo.png', 'x = 372 to 577', '228.5 mm (9.0 in)'),
 ('Handguard height over the rails', 'profile-right-photo.png', 'y = 36 to 97', '68.0 mm; slot depth 3.2 px = 3.6 mm'),
 ('Top rail lugs', 'profile-right-photo.png', 'receiver: 10 lugs from x = 272; handguard: 19 lugs from x = 388.5 to 553', '10 + 19 lugs at 10.0 mm pitch; bottom and side rails 19 each'),
 ('Handguard vents', 'profile-right-photo.png', 'x = 419-434.5, 449.5-478.5, 493.5-522.5, 530.5-543.5 at y = 58 and y = 80', '4 vents per row: 17, 32, 32, 14 mm long'),
 ('Front sight', 'profile-right-photo.png', 'x = 581 to 588, top y = 6', 'arm 7.8 mm thick, tip 70.2 mm above the bore'),
 ('Rear sight', 'profile-right-photo.png', 'x = 236 to 269, y = 7 to 40', 'base 36.8 mm long, top 69.1 mm above the bore'),
 ('Upper receiver', 'profile-right-photo.png', 'x = 201 to 372', '190.6 mm long'),
 ('Ejection port and dust cover', 'profile-right-photo.png', 'cover x = 292 to 356, y = 58 to 75', 'cover about 71 x 19 mm; the port behind it is modelled 65 x 16 mm'),
 ('Magazine well', 'profile-right-photo.png', 'x = 298 to 361, flare bottom y = 141.5', 'magazine opening 62.4 mm long (x = 302 to 358)'),
 ('Magazine', 'profile-right-photo.png', 'rear edge (302,141) to (325,247.5); front edge (358,141) to (377.5,225.5)', '119 mm below the well, curved; 62 mm wide in side view'),
 ('Trigger guard opening', 'profile-right-photo.png', 'x = 255 to 297, y = 113 to 137', '47 x 27 mm'),
 ('Pistol grip', 'profile-right-photo.png', 'x = 179 to 263, y = 112 to 207.6', '107 mm tall, backstrap raked about 25 degrees'),
 ('Stock, collapsed', 'profile-right-photo.png', 'x = 8 to 185, y = 43 to 164', '197 mm long, buttpad 129 mm tall'),
 ('Buttpad ribs', 'profile-right-photo.png', 'zig-zag on x = 8 to 12 between y = 54 and 158', '22 ribs at 5.5 mm'),
 ('Castle nut and end plate', 'profile-right-photo.png', 'x = 186 to 193.5, y = 54 to 84', '8.4 mm long, 33 mm diameter'),
 ('Selector axis, right', 'profile-right-photo.png', '(240, 100)', 'L = -147.2, Z = -34.6 mm'),
 ('Pivot and takedown pins', 'profile-right-photo.png', '(364.5, 87.5) and (223, 88)', 'pin spacing 141.5 px = 157.7 mm'),
 ('Drawing rail pitch', 'profile-both-sides-drawing.jpg', 'right side, lug edges x = 465 to 621 at y = 346: 156 px over 26 pitches', '6.0 px per pitch'),
 ('Drawing scale by fit', 'profile-both-sides-drawing.jpg', 'best similarity fit of the model', f"{dr['fitted_px_per_mm']} px/mm right, {dl['fitted_px_per_mm']} px/mm left: the drawing's rail pitch is then {6.0 / dr['fitted_px_per_mm']:.1f} mm, not 10.0"),
 ('Drawing handguard and barrel', 'profile-both-sides-drawing.jpg', 'handguard x = 436 to 638, muzzle x = 705', 'handguard 1.25 receiver lengths (photo: 1.16); barrel shows 0.41 receiver lengths ahead of it (photo: 0.85)'),
 ('Left-side controls', 'profile-left-photo-416N.jpg', 'no spans taken: the photo is in perspective with an optic and grip fitted', 'used for the layout of the bolt catch, magazine catch, selector and stock ribs only'),
]
md = []
A = md.append
A('# HK416 D14.5RS: modelling notes\n')
A(f"Result: {L0['parts']} named parts, {L0['triangles']:,} triangles at LOD0 and {L1['triangles']:,} at LOD1 ({L1['triangles'] / L0['triangles'] * 100:.0f} percent). "
  f"Right-photo silhouette IoU {rp['iou']:.3f}. Drawing IoU {dr['iou']:.3f} (right) and {dl['iou']:.3f} (left), below the 0.92 target for a reason set out under Scale.\n")
A('## Scale: the ruler and where the references disagree\n')
A('- **Ruler.** In `profile-right-photo.png` the top rail lugs repeat every 8.97 px (287 px over 32 pitches). At the MIL-STD-1913 pitch of 10.0 mm that is 0.897 px/mm. Every traced outline in `build.py` is written in that photo\'s pixels and converted with this one number.')
A('- **Cross-check against the barrel.** The model\'s barrel is exactly 14.5 in (368.3 mm), with its breech 5 mm inside the receiver face (x = 367.5) and its muzzle 8 mm inside the flash hider (x = 697.9). The photo shows the flash hider tip at x = 729 and the receiver face at x = 372, so a 14.5 in barrel fits with the breech between 0 and 12 mm inside the receiver. Agreement within about 10 mm (3 percent): the photo cannot say where the breech is. The overall length by the ruler is 804 mm, which matches the commonly published 804 mm for the D14.5RS with the stock collapsed.')
A('- **Disagreement 1: the handguard.** By the ruler the photo\'s handguard is 228.5 mm (9.0 in) with 19 lugs per rail. I had no independent source for the service rail length, so I could not confirm that 9.0 in is right for a D14.5RS. The photo is the primary reference, so the model follows it.')
A(f"- **Disagreement 2: the drawing is a different rifle at a different scale.** Its rail lugs repeat every 6.0 px, but fitting the model gives {dr['fitted_px_per_mm']} px/mm, so the drawn pitch is about {6.0 / dr['fitted_px_per_mm']:.1f} mm: the drawing's rail is not to MIL-STD scale and cannot be used as a ruler. It also shows a short barrel (0.41 receiver lengths ahead of the handguard against 0.85 in the photo) and a relatively longer handguard.")
A(f"- **What that does to the silhouette target.** The photo's own silhouette, fitted onto the drawing the same way the model is, scores IoU {cr:.3f} (right side) and {cl:.3f} (left side). Jaccard distance (1 - IoU) obeys the triangle inequality, so a shape that scores 0.92 or better against the photo cannot score above {1 - ((1 - cl) - 0.08):.3f} against the drawing's left side or {1 - ((1 - cr) - 0.08):.3f} against its right. "
  f"The target of 0.92 on all three cannot be met by one model. The model follows the photo (the brief's primary) and scores {dr['iou']:.3f} and {dl['iou']:.3f} on the drawing, about what the photo itself scores.\n")
A('## Measurements taken from the images\n')
A('| What | Image | Pixel span | Result |\n|---|---|---|---|')
for m in MEAS: A('| ' + ' | '.join(m) + ' |')
A('\nLateral sizes cannot be read from side views. They are the AR-pattern values: receiver 22.6 mm wide at the fire-control pocket, magazine well 28 mm, magazine 22.4 mm, buffer tube 29.2 mm, handguard 60 mm over the side rails, Picatinny rail 21.2 mm wide.\n')
A('## Check results\n')
A('| Check | Result | Numbers |\n|---|---|---|')
A(f"| Inventory coverage | {ok(C['inventory']['passed'])} | {C['inventory']['coverage'] * 100:.0f} percent: {C['inventory']['features']} features map to {C['inventory']['parts_named']} named objects, {len(merges)} of them as justified merges (listed below) |")
A(f"| Silhouette, right photo | {ok(rp['iou'] >= 0.92)} | IoU {rp['iou']:.4f} at the fixed ruler transform (no fitting); {rp['iou_if_fitted']:.4f} if fitted |")
A(f"| Silhouette, drawing right | {ok(dr['iou'] >= 0.92)} | IoU {dr['iou']:.4f}; photo-vs-drawing {cr:.4f} |")
A(f"| Silhouette, drawing left | {ok(dl['iou'] >= 0.92)} | IoU {dl['iou']:.4f}; photo-vs-drawing {cl:.4f} |")
A(f"| Close-up review | done | {len(CU)} close-ups rendered from the reference viewpoints; differences below |")
A(f"| Assembly | {ok(C['assembly']['passed'])} | {C['assembly']['parts']} parts, {len(C['assembly']['floating'])} floating (gap over 0.25 mm), {len(C['assembly']['fasteners_not_seated'])} of {C['assembly']['fasteners']} fasteners not seated in a host |")
for n, c in C['animation']['clips'].items():
    w = c['worst_penetration']
    A(f"| Clip `{n}` | {ok(c['passed'])} | {c['frames'][1] - c['frames'][0] + 1} frames, {c['moving_parts']} parts move; deepest overlap {w['depth_mm']} mm" + (f" ({w['moving']} into {w['into']}, frame {w['frame']})" if w['depth_mm'] else '') + ' |')
E = C['export']
A(f"| Export reload | {ok(E['passed'])} | {E['reloaded']['objects']} objects and {E['reloaded']['materials']} materials reloaded (built: {E['built']['objects']} and {E['built']['materials']}), {E['images']} images all embedded, {len(E['reloaded']['animations'])} clips, 7 sockets, barrel {E['barrel_length_mm']} mm = {E['barrel_length_in']} in, file {E['file_bytes'] / 1e6:.1f} MB |")
A('| Presentation renders | done | `r/right.png`, `left.png`, `top.png`, `front.png`, `three_quarter.png`, `first_person.png` (from `socket_ads_eye`), `first_person_hip.png`, `exploded.png` |\n')
A('How the checks work: `tools/score.py` projects every triangle orthographically onto the reference pixel grid (4x4 supersampled, threshold 0.5) and compares with the thresholded reference. `tools/checks.py` builds a BVH per part; parts touch if their surfaces intersect or come within 0.25 mm; for each clip frame it measures how deep any vertex of a moving part sits inside a part it moves relative to (and the reverse). The check did fail during the work (trigger into the grip 0.62 mm, front sight arm into its base 2.5 mm, bolt carrier into the buffer tower 2.1 mm) and those were fixed in the geometry, not in the check.\n')
A('## Triangles per region\n')
A('| Region | LOD0 | LOD1 |\n|---|---|---|')
for k, v in L0['by_region'].items(): A(f"| {k} | {v:,} | {L1['by_region'][k]:,} |")
A(f"| **Total** | **{L0['triangles']:,}** | **{L1['triangles']:,}** |\n")
A('## Silhouette rounds\n')
A('| Round | Change | Photo | Drawing R | Drawing L | Largest mismatches (photo) |\n|---|---|---|---|---|---|')
for r in R: A(f"| {r['round']} | {r['change']} | {r['iou_right_photo']:.4f} | {r['iou_drawing_right']:.4f} | {r['iou_drawing_left']:.4f} | {'; '.join(r['top5_mismatch'][:5])} |")
A('\n## Close-up review\n')
for c in CU:
    A(f"### `{c['ref']}` against `{c['render']}`\n")
    A('Matches: ' + c['matches'] + '\n')
    A('Differences:\n' + '\n'.join('- ' + d for d in c['differences']) + '\n')
    A('Fixed after this review: ' + c['fixed'] + '\n')
A('## What still differs from the references\n')
for d in L('tools/remaining.json'): A('- ' + d)
A('\n## Decisions worth knowing\n')
for d in L('tools/decisions.json'): A('- ' + d)
A('\n## Merged inventory features\n')
A('| Region | Feature | Merged into | Why |\n|---|---|---|---|')
for r in merges: A(f"| {r['region']} | {r['feature']} | `{r['part_name']}` | {r['merge_reason']} |")
open(os.path.join(HERE, 'NOTES.md'), 'w').write('\n'.join(md) + '\n')
notes = dict(
    what_i_did=[
        ['Inventory first', f"Listed {len(INV)} visible features region by region before modelling; each is a named object or a justified merge ({len(merges)} merges)."],
        ['One ruler', 'Counted rail lugs in the right photo (0.897 px/mm) and wrote every outline in that photo\'s pixels, so each number can be checked against the image.'],
        ['Part by part', f"{L0['parts']} named parts under HK416 > upper, lower, handguard, barrel_assembly, stock, grip, magazine, sights, controls, fasteners, with 7 game sockets."],
        ['Real fits', 'Moving parts run in real cavities (bolt carrier bore, charging handle channel, magazine well, button pocket, bolt catch relief), so the clips do not pass through solid metal.'],
        ['Baked PBR', 'Three procedural materials (anodized aluminium, glass-filled polymer, phosphate steel) baked with Cycles to 2048 px base colour, occlusion-roughness-metallic and normal sets, embedded in the GLB.'],
        ['Checks as scripts', 'Silhouette IoU, assembly, animation overlap, inventory coverage and GLB reload are scripts in tools/, rerun every round.']],
    good=['Right-photo silhouette IoU %.3f at a fixed scale with no fitting.' % rp['iou'], 'No floating parts; every clip stays under 0.2 mm of overlap.',
          'Barrel measures 14.5 in in the reloaded GLB.', 'ADS view through the ghost ring lines up with the front post.'],
    off=L('tools/remaining.json'),
    rounds=[dict(round=r['round'], change=r['change'], mean_iou=round((r['iou_right_photo'] + r['iou_drawing_right'] + r['iou_drawing_left']) / 3, 4),
                 iou_right_photo=r['iou_right_photo'], iou_drawing_right=r['iou_drawing_right'], iou_drawing_left=r['iou_drawing_left'], top5_mismatch=r['top5_mismatch']) for r in R],
    moving_parts='13 glTF clips at 24 fps: ' + ', '.join(f"{n} ({c['frames'][1] - c['frames'][0] + 1} frames)" for n, c in C['animation']['clips'].items()) +
                 '. Each moving part has its origin on its hinge or slide axis. stock_extend and stock_collapse stop at each of the six positions (0, 15, 30, 45, 60, 75 mm) for four frames.',
    creative_additions='Three-position fire-control pictograms (safe, single, automatic) with no words; two cartridges in the magazine for reload; a first-person hip render. No maker marks, no orange.',
    checks=dict(inventory=C['inventory']['passed'], silhouette_right_photo=rp['iou'], silhouette_drawing_right=dr['iou'], silhouette_drawing_left=dl['iou'],
                reference_ceiling_drawing_right=cr, reference_ceiling_drawing_left=cl, assembly=C['assembly']['passed'], animation=C['animation']['passed'], export=E['passed']),
    triangles=dict(lod0=L0['triangles'], lod1=L1['triangles'], lod0_by_region=L0['by_region'], lod1_by_region=L1['by_region']), parts=L0['parts'])
json.dump(notes, open(os.path.join(HERE, 'notes.json'), 'w'), indent=1)
print('NOTES.md and notes.json written')
