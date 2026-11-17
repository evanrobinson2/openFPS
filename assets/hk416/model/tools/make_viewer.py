"""python3 tools/make_viewer.py : writes viewer.html with the latest check results embedded."""
import json, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p, d=None):
    p = os.path.join(HERE, p); return json.load(open(p)) if os.path.exists(p) else d
data = dict(checks=load('work/checks.json', {}), score=load('work/score.json', {}), rounds=load('work/rounds.json', []),
            lod0=load('work/stats_lod0.json', {}), lod1=load('work/stats_lod1.json', {}), closeups=load('tools/closeups.json', []))
for k in ('lod0', 'lod1'): data[k].pop('by_part', None)
html = open(os.path.join(HERE, 'tools', 'viewer_template.html')).read().replace('/*DATA*/null', json.dumps(data))
open(os.path.join(HERE, 'viewer.html'), 'w').write(html)
print('viewer.html', len(html), 'bytes')
