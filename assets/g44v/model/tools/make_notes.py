"""python3 tools/make_notes.py : writes ../notes/DECOMPOSITION.md from inventory.json (the source-indexed part list) so the notes cannot drift from the recipe."""
import json, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
inv = json.load(open(os.path.join(HERE, 'inventory.json'))); chk = json.load(open(os.path.join(HERE, 'checks.json')))
L = ['# G44 V: source-indexed decomposition', '',
     'Written by `model/tools/make_notes.py` from `model/inventory.json`. One row per object the recipe builds. "No." is the item number of the manual\'s component',
     'list and exploded drawing (pp. 36-37). Status: **traced** = an outline polygon traced from the maker\'s dimension image (`model/outlines.json`, pixel coordinates kept);',
     '**measured** = read off a named picture with the stated ruler; **published** = the maker\'s specification table; **inferred** = not visible or not legible in any source,',
     'built from how the part must work (each one is a stated guess). Positions are mm: L from the slide\'s rear face toward the muzzle, Z up from the bore axis.', '',
     '| No. | Object | Status | Source region and evidence | Pivot (L, S, Z) | Extent L | Extent Z | Material |', '|---|---|---|---|---|---|---|---|']
for q in inv['parts']:
    b = q['bbox_mm']; L.append('| %s | `%s` | %s | %s | %s | %.1f to %.1f | %.1f to %.1f | %s |' % (q['part_no'] or '-', q['name'], q['status'], q['source'].replace('|', '/'), ', '.join('%.1f' % x for x in q['pivot_mm']),
                                                                                          b['L'][0], b['L'][1], b['Z'][0], b['Z'][1], q['material']))
n = {}
for q in inv['parts']: n[q['status']] = n.get(q['status'], 0) + 1
L += ['', 'Objects by status: ' + ', '.join('%s %d' % kv for kv in sorted(n.items())) + '. Manual items modelled: %d of %d (items 25 and 30 are blank in the manual).' % (chk['inventory']['modelled'], chk['inventory']['manual_items']), '',
      '## Numbers', '', '| Parameter | Value | Status | Source |', '|---|---|---|---|']
for k, v in inv['params'].items(): L.append('| `%s` | %s | %s | %s |' % (k, json.dumps(v['value']) if not isinstance(v['value'], float) else ('%.3f' % v['value']).rstrip('0').rstrip('.'), v['status'], v['source']))
L += ['', '## Sockets', '', '| Socket | Parent | L, S, Z (mm) | What it is |', '|---|---|---|---|']
for s in inv['sockets']: L.append('| `%s` | `%s` | %.1f, %.1f, %.1f | %s |' % (s['name'], s['parent'], s['pos_mm']['L'], s['pos_mm']['S'], s['pos_mm']['Z'], s['note']))
L += ['', '## Clips (30 fps)', '', '| Clip | Frames | Moving nodes | Interpenetrating pairs |', '|---|---|---|---|']
for c, v in inv['clips'].items(): L.append('| `%s` | %d | %s | %d |' % (c, chk['clips'][c]['frames'], ', '.join('`%s`' % x for x in v['nodes']), len(chk['clips'][c]['intersecting'])))
L += ['', '## Pairs fixed to each other (skipped by the interpenetration check)', ''] + ['- `%s` on `%s`: %s' % tuple(a) for a in inv['attached']]
os.makedirs(os.path.join(HERE, '..', 'notes'), exist_ok=True); open(os.path.join(HERE, '..', 'notes', 'DECOMPOSITION.md'), 'w').write('\n'.join(L) + '\n'); print('wrote notes/DECOMPOSITION.md', len(L), 'lines')
