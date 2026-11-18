#!/usr/bin/env python3
"""python3 sound/verify_js.py : the JS synthesiser against the Python renderer, sample by sample. Writes compare/js_parity.json."""
import json, os, subprocess, tempfile, array, math, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim
P = json.load(open(os.path.join(HERE, 'params.json')))
tmp = os.path.join(tempfile.mkdtemp(), 'js.bin')
subprocess.run(['node', os.path.join(HERE, 'verify_js.mjs'), tmp], check=True)
idx = json.load(open(tmp + '.json')); data = array.array('d'); data.frombytes(open(tmp, 'rb').read())
res = {}; worst = -400.0
def cmp(name, py):
    global worst
    o, n = idx[name]; js = data[o:o + n]; pk = max(abs(v) for v in py) or 1.0
    err = max(abs(a - b) for a, b in zip(py, js)) if n == len(py) else float('inf')
    d = 20 * math.log10(max(err, 1e-300) / pk); res[name] = dict(samples=n, python_samples=len(py), peak_pa=pk, max_error_db_re_peak=round(d, 1)); worst = max(worst, d)
for name, rec in P['recipes'].items(): cmp(name, sim.render(rec))
for key in P['bounce_examples']:
    b, s, v = key.split('|'); cmp('bounce:' + key, sim.render(sim.bounce_recipe(b, s, float(v))))
ok = worst < -120.0
os.makedirs(os.path.join(HERE, 'compare'), exist_ok=True)
json.dump(dict(_doc='JS synthesiser (grenades-sound.js) against the Python renderer (sim.py), every sample. Limit: -120 dB re the peak.', worst_db=round(worst, 1), passed=ok, sounds=res), open(os.path.join(HERE, 'compare', 'js_parity.json'), 'w'), indent=1)
print('worst error', round(worst, 1), 'dB re peak;', 'PASSED' if ok else 'FAILED'); sys.exit(0 if ok else 1)
