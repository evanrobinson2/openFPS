#!/usr/bin/env python3
"""Check every asset in assets/ against MODELING_RULES.md.

    python3 tools/check_assets.py

Fails (exit 1) on hard rules: mesh or audio files present, missing USAGE.md, sample/index.html or provenance.json.
Warns only (rule 5) when provenance.json doesn't name a recognised 2026 frontier model for its modelling.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
BANNED = {'.glb', '.gltf', '.fbx', '.obj', '.blend', '.blend1', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
REQUIRED = ['USAGE.md', 'sample/index.html', 'provenance.json']
# Models at or above the level of Claude Fable 5.2 or Astra 6.2. Extend this list as new frontier models ship.
FRONTIER_MODELS = ['claude fable 5.2', 'astra 6.2', 'claude opus 5.5']

errors, warnings = [], []
for aid in sorted(os.listdir(ASSETS)):
    adir = os.path.join(ASSETS, aid)
    if not os.path.isdir(adir):
        continue
    for rel in REQUIRED:
        if not os.path.exists(os.path.join(adir, rel)):
            errors.append(f'{aid}: missing {rel}')
    for dp, dn, fn in os.walk(adir):
        dn[:] = [d for d in dn if d not in ('refs-local', '__pycache__', 'masters', 'audio')]
        for f in fn:
            if os.path.splitext(f)[1].lower() in BANNED:
                errors.append(f'{aid}: banned file {os.path.relpath(os.path.join(dp, f), ROOT)} (rules 2 and 3)')
    prov = os.path.join(adir, 'provenance.json')
    if os.path.exists(prov):
        p = json.load(open(prov))
        mb = p.get('modelled_by') or []
        if not mb:
            warnings.append(f'{aid}: provenance.json has no modelled_by entries (rule 5)')
        for e in mb:
            m = str(e.get('model', '')).lower()
            if not any(m.startswith(f) for f in FRONTIER_MODELS):
                warnings.append(f"{aid}: '{e.get('part')}' modelled by '{e.get('model')}', not a recognised frontier model (rule 5)")

for w in warnings:
    print('warning:', w)
for e in errors:
    print('error:', e)
print(f'{len(errors)} errors, {len(warnings)} warnings')
sys.exit(1 if errors else 0)
