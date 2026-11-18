#!/usr/bin/env python3
"""Parity check: g44v-sound.js (run under node) against sim.py stage B, from the same params.json.
Writes compare/js_parity.json. Usage: python3 verify_js.py"""
import json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim
P = json.load(open(os.path.join(HERE, 'params.json'))); jobs = sim.JOBS(P)
py = dict(dry=lambda *a: sim.synth_dry(P, *a), mech=lambda *a: sim.synth_mech(P, *a), ir=lambda *a: sim.build_ir(P, *a))
with tempfile.TemporaryDirectory() as d:
    json.dump(jobs, open(d + '/jobs.json', 'w'))
    subprocess.run(['node', os.path.join(HERE, 'verify_js.mjs'), d], check=True)
    times = json.load(open(d + '/times.json')); res = {}; worst = -999
    for name, kind, *args in jobs:
        a = py[kind](*args); b = np.fromfile('%s/%s.f64' % (d, name)); assert len(a) == len(b), (name, len(a), len(b))
        err = 20 * np.log10(np.max(np.abs(a - b)) / np.max(np.abs(a)) + 1e-300); worst = max(worst, err)
        res[name] = dict(max_error_db_re_peak=round(float(err), 1), js_ms=times[name])
json.dump(dict(note='max sample difference between sim.py and g44v-sound.js, dB relative to the signal peak; js_ms is node synthesis time', outputs=len(res), worst_db=round(float(worst), 1), by_output=res),
          open(os.path.join(HERE, 'compare', 'js_parity.json'), 'w'), indent=1)
print('%d outputs, worst: %.1f dB re peak' % (len(res), worst))
