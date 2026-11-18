"""python3 model/tools/checks.py   (after blender -b --python model/build.py)

Structural checks of the built model: decomposition coverage, hierarchy, clip clearances, the exported GLB's frame,
and the model's dimensions against the published figures. Writes model/checks.json. These are structural and
dimensional results only; the visual comparison is model/compare.json (model/tools/compare.py)."""
import json, os, struct
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = json.load(open(os.path.join(HERE, 'inventory.json'))); DEC = json.load(open(os.path.join(HERE, 'decomposition.json')))
P = INV['params']; parts = INV['parts']; res = {}; IN = 25.4

# ---- decomposition coverage
feats = DEC['features']; named = {p for f in feats for p in f['parts']}
missing = sorted(p for f in feats if f['status'] in ('built', 'merged') for p in f['parts'] if p not in parts)
unsourced = sorted(n for n, p in parts.items() if not any(s in {f['id'] for f in feats} for s in p['source']))
res['decomposition'] = dict(features=len(feats), built=sum(f['status'] == 'built' for f in feats), merged=sum(f['status'] == 'merged' for f in feats), omitted=[f['id'] for f in feats if f['status'] == 'omitted'],
                            parts=len(parts), parts_missing=missing, parts_without_a_source_feature=unsourced, parts_not_named_by_a_feature=sorted(set(parts) - named),
                            by_basis={b: sum(1 for p in parts.values() if p['basis'] == b) for b in ('traced', 'manual', 'inferred')}, passed=not missing and not unsourced)
# ---- hierarchy
H = INV['hierarchy']; roots = [n for n, p in H.items() if p is None]
def chain(n):
    out = []
    while n: out.append(n); n = H[n]
    return out
res['hierarchy'] = dict(root=roots, orphans=[n for n in H if chain(n)[-1] != 'shotgun_590'], moving_groups=sorted(g for g in set(H.values()) if g and g != 'shotgun_590'), passed=roots == ['shotgun_590'])
# ---- clearances at the ends of the pump stroke (bounding boxes along Z, mm)
S, lm = P['stroke'], P['lost_motion']; z = lambda n: parts[n]['bbox_mm']['z']
cav_rear = P['recv_rear'][1] + P['cavity_wall']
res['pump_clearance'] = dict(
    forend_rear_at_full_stroke_mm=round(z('forend')[0] - S, 2), receiver_front_mm=0.0,
    bolt_rear_at_full_stroke_mm=round(z('bolt')[0] - (S - lm), 2), cavity_rear_mm=round(cav_rear, 2),
    bolt_slide_rear_at_full_stroke_mm=round(z('bolt_slide')[0] - S, 2),
    bolt_face_at_full_stroke_mm=round(z('bolt')[1] - (S - lm), 2), port_rear_mm=round(P['port'][0], 2),
    passed=bool(z('forend')[0] - S >= -0.01 and z('bolt')[0] - (S - lm) >= cav_rear and z('bolt_slide')[0] - S >= cav_rear),
    note='at full stroke the forend stops short of the receiver face and the bolt and bolt slide stay inside the receiver cavity')
res['pump_clearance']['bolt_slide_clearance_mm'] = round(z('bolt_slide')[0] - S - cav_rear, 2)
# ---- published dimensions
butt_mid = (41 - 577) * INV['ruler']['mm_per_px']; trig = (411 - 577) * INV['ruler']['mm_per_px']
zs = [b for p in parts.values() for b in p['bbox_mm']['z'] if p['group'] != 'shell_template']
oal = max(zs) - min(zs); lop = trig - butt_mid          # photo pixels: trigger face x 411; the slanted butt runs from x 29 at its heel to x 53 at its toe, middle x 41
barrel = P['muzzle'] - P['breech']; mass = INV['totals']['mass_g_from_volumes'] / 1e3
def row(name, model, pub, unit, tol, note): return dict(what=name, model=round(model, 2), published=pub, unit=unit, difference_pct=round(100 * (model - pub) / pub, 1), within_tolerance=abs(model - pub) / pub <= tol, tolerance_pct=tol * 100, note=note)
res['published_dimensions'] = [
    row('overall length', oal / IN, 41.0, 'in', 0.03, 'NOT met: see notes/NOTES.md, "The ruler". The photo cannot give both 41 in overall and 20 in of barrel'),
    row('length of pull (trigger face to the middle of the butt)', lop / IN, 13.87, 'in', 0.03, 'independent of the ruler\'s anchor points; not met with the barrel ruler'),
    row('barrel (ejection port front edge to muzzle)', barrel / IN, 20.0, 'in', 0.005, 'the ruler since change request 1: the photo is scaled to this figure, so this is a calibration, not a check'),
    row('weight (mesh volumes x densities)', mass / 0.45359237, 7.25, 'lb', 0.15, 'solid parts, guessed hollow-stock density, no springs or small internals: a plausibility figure only'),
    row('magazine tube inside diameter vs a 12 gauge rim (22.45 mm max)', P['tube_r'] * 2 - 2 * P['tube_wall'], 22.45, 'mm', 0.05, 'the tube\'s inside must clear the rim: model inside diameter over rim diameter'),
]
res['published_dimensions'][-1]['within_tolerance'] = bool(res['published_dimensions'][-1]['model'] >= 22.45)      # the rim must pass: a hard bound, not a tolerance
res['published_dimensions'][-1]['note'] = 'the tube\'s inside must clear the rim. NOT met with the barrel ruler: the traced tube is 23.2 mm outside'
res['published_dimensions_summary'] = dict(met=[r['what'] for r in res['published_dimensions'] if r['within_tolerance']], not_met=[r['what'] for r in res['published_dimensions'] if not r['within_tolerance']])
# ---- the exported GLB: frame, nodes, clips, no images
glb = os.path.join(HERE, 'masters', 'shotgun590.glb')
if os.path.exists(glb):
    d = open(glb, 'rb').read(); n = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + n]); nodes = {x['name']: x for x in j['nodes']}
    def world(name):
        par = {c: i for i, x in enumerate(j['nodes']) for c in x.get('children', [])}; idx = [i for i, x in enumerate(j['nodes']) if x['name'] == name][0]; t = [0.0, 0.0, 0.0]
        while True:
            tr = j['nodes'][idx].get('translation', [0, 0, 0]); t = [a + b for a, b in zip(t, tr)]
            if idx not in par: return t
            idx = par[idx]
    mz = world('socket_muzzle'); sh = world('socket_shoulder'); ej = world('socket_eject')
    anims = sorted(a['name'] for a in j.get('animations', []))
    res['glb'] = dict(bytes=len(d), nodes=len(j['nodes']), meshes=len(j.get('meshes', [])), images=len(j.get('images', [])), animations=anims,
                      socket_muzzle_m=[round(v, 4) for v in mz], socket_shoulder_m=[round(v, 4) for v in sh], socket_eject_m=[round(v, 4) for v in ej],
                      frame_ok=bool(abs(mz[2] - P['muzzle'] * 1e-3) < 1e-4 and abs(mz[0]) < 1e-6 and sh[1] < 0 and sh[2] < 0 and ej[0] < 0),
                      clips_ok=anims == sorted(INV['clips']), passed=None)
    res['glb']['passed'] = bool(res['glb']['frame_ok'] and res['glb']['clips_ok'] and res['glb']['images'] == 0 and all(n in nodes for n in list(parts) + list(INV['sockets'])))
else:
    res['glb'] = dict(passed=None, note='masters/shotgun590.glb not found: run model/build.py first')
res['totals'] = INV['totals']; res['clips'] = INV['clips']; res['sockets'] = INV['sockets']
json.dump(res, open(os.path.join(HERE, 'checks.json'), 'w'), indent=1)
for k in ('decomposition', 'hierarchy', 'pump_clearance', 'glb'): print(k, 'PASS' if res[k]['passed'] else 'FAIL', {a: b for a, b in res[k].items() if a not in ('passed', 'note', 'moving_groups', 'animations')})
for r in res['published_dimensions']: print(('ok   ' if r['within_tolerance'] else 'NOT MET ') + r['what'], r['model'], 'vs', r['published'], r['unit'], f"({r['difference_pct']:+.1f} %)")
