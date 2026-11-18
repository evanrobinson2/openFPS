#!/usr/bin/env python3
"""Before and after.  'Before' is the version-1 model, rebuilt from git (revision BEFORE_REV); 'after' is this folder.
For the shooter's ear, high-velocity load: where the energy sits in time, how long each octave band lasts, and what the playback mapping
does to both.  Writes compare/before_after.json.  Numbers only; nothing here reads a recording.

Two measures are reported as the owner's "click" test: the share of the shot's energy in the first 2 ms after the blast arrives, and the
time after its own peak at which each octave band's envelope is last within 20 dB of that peak (t20)."""
import importlib.util, json, os, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import metrics as M, sim
BEFORE_REV = 'eb6cdd3'; LOAD = 'cci_mini_mag'; FS = 48000
CHROME = dict(   # measured once by hand; not rebuilt by this script
    how='S.shot(cci_mini_mag, {ground: true}) played through S.chain({overlay: null, hpd: false, ear: true}) in an OfflineAudioContext, Chrome, 2026-11-17. Peak in each window, dB re full scale. Windows are times after the trigger break.',
    windows_ms=['4-7 (blast)', '10.5-13.5 (ground echo, slide on the frame)', '13.5-19', '21-30 (slide closes)', '30-60', '60-200'],
    before_input=[-1.0, -14.0, -46.1, -30.1, -58.6, None], before_ear_on=[-13.5, -23.9, -55.5, -36.8, -62.0, None],
    before_finding='the version-1 mapping (DynamicsCompressor, threshold -30 dB, ratio 6) turned the whole shot down by 12.5 dB and lifted what follows the blast by only 3 to 6 dB relative to it',
    after_input=[-1.0, -19.0, -28.8, -37.0, -45.4, -61.9], after_ear_on=[-1.6, -7.8, -14.2, -21.3, -30.1, -45.7],
    after_agrees_with_python='sim.ear_map gives the same six numbers, the same peak (0.8303) and the same sum of squares (9.8945)')
def old_model():
    d = tempfile.mkdtemp(); root = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()
    for sub in ('sound', 'action', 'model'): os.makedirs(os.path.join(d, sub))
    for f in ('sound/sim.py', 'sound/params.json', 'action/action.json', 'model/inventory.json'):
        open(os.path.join(d, f), 'w').write(subprocess.run(['git', 'show', '%s:assets/g44v/%s' % (BEFORE_REV, f)], cwd=root, capture_output=True, text=True, check=True).stdout)
    spec = importlib.util.spec_from_file_location('g44v_sound_v1', os.path.join(d, 'sound', 'sim.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m, json.load(open(os.path.join(d, 'sound', 'params.json')))
def brief(x, t0=None):
    s = M.summary(x, FS, t0)
    return dict(first_2ms_energy_share=s['first_2ms_energy_share'], t20_ms_by_band={b: v['t20_ms'] for b, v in s['bands'].items()}, band_exposure_db={b: v['sel_db'] for b, v in s['bands'].items()},
                band_peak_db={b: v['peak_db'] for b, v in s['bands'].items()}, late_energy_share_by_band={b: v['late_energy_share'] for b, v in s['bands'].items()},
                peak_db=s['peak_db'], a_duration_ms=s['a_duration_ms'], b_duration_ms=s['b_duration_ms'], negative_phase=s['negative_phase'], lae_db=s['lae_db'], peak_minus_lae_db=s['peak_minus_lae_db'],
                spectral_centroid_hz=s['spectral_centroid_hz'], exposure_by_time_db=s['energy_by_time'])
def main():
    old, Po = old_model(); P = json.load(open(os.path.join(HERE, 'params.json'))); k = P['ear_map_k']; out = dict(
        note='shooter\'s ear, %s. "pascals" is the physical signal; "as_played" is the signal after the playback mapping of chain({ear: true}) (version 1: a Web Audio DynamicsCompressor, measured in Chrome, see chrome_measurement; version 2: asinh(%g x)/asinh(%g), computed here and checked in Chrome).' % (LOAD, k, k),
        measures='first_2ms_energy_share: share of the energy in the 2 ms after the blast arrives. t20_ms_by_band: time after the band\'s own peak at which its envelope is last within 20 dB of that peak.')
    def t_arr(x): return int(np.argmax(np.abs(x))) / FS - 0.0003
    b_dry = old.synth_dry(Po, LOAD, 'shooter', False); b_def = old.synth_dry(Po, LOAD, 'shooter', True)
    a_dry = sim.synth_dry(P, LOAD, 'shooter', False); a_def = sim.synth_dry(P, LOAD, 'shooter', True); a_berm = np.convolve(a_dry, sim.build_ir(P, 'outdoor_berm'))[:int(0.6 * FS)]
    pk = float(np.max(np.abs(a_dry)))
    out['before'] = dict(dry_free_field=dict(pascals=brief(b_dry)), default_open_air=dict(pascals=brief(b_def)))
    out['after'] = dict(dry_free_field=dict(pascals=brief(a_dry), as_played=brief(sim.ear_map(a_dry, k, pk) / 20e-6 * 20e-6, t_arr(a_dry))),
                        default_open_air=dict(pascals=brief(a_def), as_played=brief(sim.ear_map(a_def, k, pk), t_arr(a_def))),
                        outdoor_berm=dict(pascals=brief(a_berm), as_played=brief(sim.ear_map(a_berm, k, pk), t_arr(a_berm))))
    # parts of the default shot, each alone, at the ear (pascals)
    L = P['loads'][LOAD]; ps = P['perspectives']['shooter']; n = int(P['dur_shot'] * FS)
    def part(Lp, field, paths=('direct', 'ground')):
        return sim.synth_parts(P, Lp, ps, field, LOAD)
    blast_only = dict(blast=L['blast'], n_blast=L['n_blast']); mech_only = dict(blast=[], n_blast=0, mech=L['mech'], friction=L['friction'])
    xb = part(blast_only, False); xbg = part(blast_only, True); xm = part(mech_only, True)
    out['after']['parts_at_the_ear'] = dict(
        blast_direct=dict(peak_db=round(M.db(np.max(np.abs(xb))), 1), exposure_db=round(M.sel(xb, FS), 1)),
        ground_reflection_and_scatter=dict(peak_db=round(M.db(np.max(np.abs(xbg - xb))), 1), exposure_db=round(M.sel(xbg - xb, FS), 1)),
        mechanical=dict(peak_db=round(M.db(np.max(np.abs(xm))), 1), exposure_db=round(M.sel(xm, FS), 1)),
        mechanical_events=[dict(name=e['name'], t_ms=round(e['t'] * 1e3, 2), modes_hz=[m['f'] for m in e['modes']], longest_decay_ms=round(max([m['tau'] for m in e['modes']] + [0]) * 1e3, 1)) for e in L['mech']])
    out['chrome_measurement'] = CHROME
    json.dump(out, open(os.path.join(HERE, 'compare', 'before_after.json'), 'w'), indent=1)
    def line(name, d): print('%-34s first 2 ms %5.1f %% | t20 ms %s | A-dur %.3f | peak-LAE %.1f' % (name, 100 * d['first_2ms_energy_share'], ' '.join('%s:%g' % kv for kv in d['t20_ms_by_band'].items()), d['a_duration_ms'], d['peak_minus_lae_db']))
    for ver in ('before', 'after'):
        for env, d in out[ver].items():
            if env == 'parts_at_the_ear': continue
            for dom, v in d.items(): line('%s %s %s' % (ver, env, dom), v)
    print(json.dumps(out['after']['parts_at_the_ear'], indent=None)[:1500])
if __name__ == '__main__':
    main()
