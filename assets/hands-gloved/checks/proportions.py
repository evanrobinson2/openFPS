"""Check the hand's proportions against the anthropometric sources.  Writes checks/proportions.json.

    python3 checks/proportions.py

Each row says how the model's number was measured and whether the comparison is independent ('check') or the number
was a design input ('by construction': it shows the recipe built what it was given, not that the input is right)."""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(HERE, 'model'))
import handlib as hl
h = hl.Hand(); g = hl.P['glove']; rows = []
def perim(P_): return float(np.linalg.norm(np.roll(P_, -1, axis=0) - P_, axis=1).sum())
def row(name, model, ref, src, kind, how, tol_pct=None):
    d = model - ref; r = dict(dimension=name, model_mm=round(model, 2), reference_mm=ref, difference_mm=round(d, 2), difference_pct=round(100 * d / ref, 2), source=src, kind=kind, how=how)
    if tol_pct is not None: r['tolerance_pct'] = tol_pct; r['pass'] = bool(abs(100 * d / ref) <= tol_pct)
    rows.append(r)
A = hl.ANSUR; palm = h.shells['palm']; R = 2 * hl.NSEG; ring = lambda i: palm['V'][i * R:(i + 1) * R]
sd = lambda k: A[k][1]
# hand length: stylion to the tip of the middle finger (skin, without the glove's 1.5 mm tip allowance and shell)
s = hl.seg('middle'); tip_y = hl.mcp3_y() + s['pp'] + s['mp'] + s['dp'] + s['tip']
row('hand length (stylion to tip of digit III)', tip_y - hl.P['stylion_y'], A['hand_length'][0], 'A', 'by construction', 'skeleton: wrist offset + bone lengths; the 1.04 scale on B was set to give this')
# hand breadth and circumference at the metacarpal heads: the palm shell's widest ring, less the glove
us = sorted(set(np.round(palm['s'], 4))); wid = [np.ptp(ring(i)[:, 0]) for i in range(len(us) - 0) if i * R < len(palm['V']) - 2]
i_b = int(np.argmax(wid)); row('hand breadth (across the metacarpal heads)', wid[i_b] - 2 * g, A['hand_breadth'][0], 'A', 'by construction', 'widest ring of the palm shell, less 2 x glove')
i_c = int(np.argmin([abs(u - 0.80) for u in us])); pr = ring(i_c)[:, [0, 2]]
row('hand circumference (round the metacarpal heads)', perim(pr) - 2 * math.pi * g, A['hand_circumference'][0], 'A', 'fitted', 'perimeter of the palm shell ring at 80 % of the palm, less 2 pi x glove; the section exponent (3.8) was tuned to this with the 29.5 mm thickness held', 1.0)
i_w = int(np.argmin([abs(-7.0 + u * (hl.mcp3_y() + 12.0)) for u in us])); pw = ring(i_w)[:, [0, 2]]
row('wrist circumference', perim(pw) - 2 * math.pi * g, A['wrist_circumference'][0], 'A', 'fitted', 'perimeter of the palm shell ring at the wrist joint, less 2 pi x glove; the half-axes 30.8 x 21.4 mm were tuned to this', 1.0)
row('palm length (wrist crease to the crease of digit III)', hl.mcp3_y() + hl.P['web_offset'] - hl.P['stylion_y'], A['palm_length'][0], 'A', 'by construction', 'MCP III + 19.2 mm crease offset (set to give this)')
row('forearm (radiale to stylion)', h.J['forearm'][2], A['radiale_stylion'][0], 'A', 'by construction', 'forearm bone length')
# finger lengths against an independent sample: base landmark fitted on the middle finger, the other digits compared
k = 195.5 / A['hand_length'][0]; base = (hl.finger_len('middle') - hl.P['glove_tip']) * k - hl.HSIAO_LENGTH['middle']
for f in hl.FING:
    m = (hl.finger_len(f) - hl.P['glove_tip']) * k - base
    row(f'{f} finger length (base to tip), scaled to the 195.5 mm hands of H', m, hl.HSIAO_LENGTH[f], 'H',
        'fitted' if f == 'middle' else 'check', f'MCP to tip less a base offset of {base:.1f} mm fitted on the middle finger', None if f == 'middle' else 6.0)
s = hl.seg('thumb'); row('thumb length (MCP joint to tip), scaled to the hands of H', (s['pp'] + s['dp'] + s['tip']) * k, hl.HSIAO_LENGTH['thumb'], 'H', 'reported', "H's thumb base landmark is not the joint centre; no tolerance set")
# finger breadths at the middle joint
for f in hl.FING + ('thumb',):
    sh = h.shells['finger_' + f] if f != 'thumb' else h.shells['thumb']; j = sh['joints'][1 if f != 'thumb' else 2]
    i = int(np.argmin(np.abs(sh['s'][:len(sh['s']) - 2:hl.NSEG] - j))); rg = sh['V'][i * hl.NSEG:(i + 1) * hl.NSEG]
    m = h.J[(f + '_01') if f != 'thumb' else 'thumb_01'][1]; wid_f = np.ptp(rg @ m[:3, 0])
    row(f'{f} breadth at the {"PIP" if f != "thumb" else "IP"} joint', wid_f - 2 * g, hl.HSIAO_BREADTH[f], 'H', 'by construction', 'width of the shell ring at the joint, less 2 x glove')
# segment proportions: phalanx lengths as a share of the ray (identical to B by construction; listed for the record)
for f in hl.FING:
    s = hl.seg(f); t, d, m_, p, mc = hl.BURY[f]; row(f'{f}: proximal / middle / distal phalanx ratio check (proximal share)', 100 * s['pp'] / (s['pp'] + s['mp'] + s['dp']), round(100 * p / (p + m_ + d), 2), 'B', 'by construction', 'percent of the three phalanges')
# gloved finger against the photograph (R2-S01: three gloved fingers side by side are 295 px at 3.97 px/mm)
mean3 = np.mean([hl.breadth(f) + 2 * g for f in ('middle', 'ring', 'little')])
row('gloved finger breadth, mean of three (R2-S01: 24.7 mm, winter glove)', mean3, 24.7, 'reference R2', 'reported', 'model glove is 1.2 mm thick; the glove in R2 is a thicker cold-weather glove')
checks = [r for r in rows if 'pass' in r]
out = dict(asset='hands-gloved', size=hl.SIZE, percentile_note='ANSUR II male mean; the 50th percentile differs by at most 0.5 mm in the dimensions used', sources={k: hl.SRC[k] for k in ('A', 'B', 'H')},
           rows=rows, summary=dict(independent_checks=len(checks), passed=sum(r['pass'] for r in checks), worst_pct=max(abs(r['difference_pct']) for r in checks)))
json.dump(out, open(os.path.join(HERE, 'checks', 'proportions.json'), 'w'), indent=1)
for r in rows: print(f"{r['dimension'][:62]:62s} {r['model_mm']:8.2f} vs {r['reference_mm']:7.2f}  {r['difference_pct']:+6.2f} %  {r['kind']:16s} {r.get('pass', '')}")
print(out['summary'])
