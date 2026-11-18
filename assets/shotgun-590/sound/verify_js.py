#!/usr/bin/env python3
"""Parity check: shotgun590-sound.js (run under node) against sim.py's renderer, from the same params.json.
Writes compare/js_parity.json. Usage: python3 sound/verify_js.py"""
import json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim

P = json.load(open(os.path.join(HERE, 'params.json'))); res = {}; worst = -999.0
with tempfile.TemporaryDirectory() as d:
    subprocess.run(['node', os.path.join(HERE, 'verify_js.mjs'), d], check=True)
    times = json.load(open(d + '/times.json'))
    for name, snd in P['sounds'].items():
        a = sim.render(snd, P['fs']); b = np.fromfile(f'{d}/{name}.f64'); assert len(a) == len(b), (name, len(a), len(b))
        err = 20 * np.log10(np.max(np.abs(a - b)) / np.max(np.abs(a)) + 1e-300); worst = max(worst, float(err))
        res[name] = dict(samples=len(a), max_error_db_re_peak=round(float(err), 1), js_ms=times[name]); print(f'{name:28s} max |py - js| = {err:7.1f} dB re peak   js {times[name]:4d} ms')
json.dump(dict(note='largest sample difference between sim.py and shotgun590-sound.js, dB relative to the signal peak; js_ms is node synthesis time', worst_db=round(worst, 1), passed=worst < -120, outputs=res),
          open(os.path.join(HERE, 'compare', 'js_parity.json'), 'w'), indent=1)
print(f'worst: {worst:.1f} dB re peak'); sys.exit(0 if worst < -120 else 1)
