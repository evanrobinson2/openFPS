#!/usr/bin/env python3
"""Parity check: hk416-sound.js (run under node) against sim.py stage B, from the same params.json.
Writes compare/js_parity.json. Usage: python3 sound/verify_js.py"""
import json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim

P = sim.prep(json.load(open(os.path.join(HERE, 'params.json'))))
jobs = [['dry_%s_%s_%s' % (p, v, 'field' if f else 'free'), 'dry', p, v, f] for p in ['shooter', 'bystander', 'downrange'] for v in sim.VARIANTS for f in (False, True)]
jobs += [['mech_' + c, 'mech', c] for c in sim.MECH_CLIPS] + [['steel_' + k, 'steel', k, None, 1] for k in P['steel']]
jobs += [['ir_%s_%s' % (o, p), 'ir', o, p] for o, v in P['overlays'].items() for p in v['persp']]
py = dict(dry=lambda *a: sim.synth_dry(P, *a), mech=lambda *a: sim.synth_mech(P, *a), steel=lambda *a: sim.synth_steel(P, *a), ir=lambda *a: sim.build_ir(P, *a))
with tempfile.TemporaryDirectory() as d:
    json.dump(jobs, open(d + '/jobs.json', 'w'))
    subprocess.run(['node', os.path.join(HERE, 'verify_js.mjs'), d], check=True)
    times = json.load(open(d + '/times.json')); res = {}; worst = -999
    for name, kind, *args in jobs:
        a = py[kind](*args); b = np.fromfile('%s/%s.f64' % (d, name)); assert len(a) == len(b), (name, len(a), len(b))
        err = 20 * np.log10(np.max(np.abs(a - b)) / np.max(np.abs(a)) + 1e-300); worst = max(worst, err)
        res[name] = dict(max_error_db_re_peak=round(float(err), 1), js_ms=times[name])
        print('%-34s max |py - js| = %7.1f dB re peak   js %5d ms' % (name, err, times[name]))
json.dump(dict(note='max sample difference between sim.py and hk416-sound.js, dB relative to the signal peak; js_ms is node synthesis time', worst_db=round(float(worst), 1), outputs=res),
          open(os.path.join(HERE, 'compare', 'js_parity.json'), 'w'), indent=1)
print('worst: %.1f dB re peak' % worst)
