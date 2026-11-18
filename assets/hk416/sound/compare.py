"""Checks of the sound simulation. Run through `python3 sound/sim.py compare`.

1. recording_trust(): provenance and condition of the two local reference recordings (numbers only).
2. diagnose(): the simulation at each microphone position, through a model of that microphone
   (bandwidth, off-axis response, clipping), against the recordings, in bands and time windows.
3. published(): simulated peak levels against published 5.56 mm figures.
4. sim-only plots and the internal open-field consistency check.

The recordings are measurement references only. Nothing derived from their audio is written anywhere
except scalar numbers in sound/compare/*.json; no plot is drawn from a recording.
Point OPENFPS_REF_AUDIO at the folder that holds them (default sound/refs-local/, ignored by git).
"""
import json, math, os, struct, wave
import numpy as np
from scipy import signal
import sim

REFS = {'ongun': 'HK_416_5.56mm_on_gun_DPA4062_clean_Seven_shots_x_1.wav',
        'side1m': 'HK_416_5.56mm_1m_left_off_axis_MKH416_clean_Six_shots_x_2.wav'}
OCT = [125, 250, 500, 1000, 2000, 4000, 8000]
WINDOWS_MS = [(0, 1), (1, 10), (10, 30), (30, 58), (58, 75), (100, 200)]      # after the blast onset at the microphone
# Microphone models. Published: Sennheiser MKH 416 max SPL 130 dB (1 % THD), 40 Hz to 20 kHz, 25 mV/Pa; DPA 4062 omni,
# 20 Hz to 20 kHz, peak SPL before clipping 154 dB. Inferred: hard clip 3 dB above the 1 % point as a peak value (136 dB),
# and the MKH 416 response 90 degrees off axis by octave band 63 Hz..16 kHz (read from the published polar diagram, approximate).
MICS = {'side1m': dict(name='Sennheiser MKH 416 (interference tube), 90 deg off axis', clip_db_peak=136.0, hp_hz=40.0,
                       off_axis_db=[-6, -6, -7, -8, -9, -12, -17, -20, -25]),
        'ongun': dict(name='DPA 4062 miniature omni on the rifle', clip_db_peak=154.0, hp_hz=20.0, off_axis_db=[0] * 9)}
r1 = lambda v, n=1: None if v is None or not np.isfinite(v) else round(float(v), n)
db = lambda v: 20 * math.log10(max(float(v), 1e-12))


def read_wav(path):
    """24-bit PCM reader. Returns sample rate, integer samples, and the chunk list."""
    with open(path, 'rb') as f: d = f.read()
    chunks = []; i = 12; info = {}
    while i < len(d) - 8:
        cid = d[i:i + 4].decode('latin1'); n = struct.unpack('<I', d[i + 4:i + 8])[0]; chunks.append(cid.strip())
        if cid == 'bext': info['bext_originator'] = d[i + 8 + 256:i + 8 + 288].split(b'\0')[0].decode('latin1').strip(); info['bext_time_reference_samples'] = struct.unpack('<Q', d[i + 8 + 338:i + 8 + 346])[0]
        i += 8 + n + (n & 1)
    with wave.open(path) as w:
        sr = w.getframerate(); bits = 8 * w.getsampwidth(); ch = w.getnchannels(); raw = np.frombuffer(w.readframes(w.getnframes()), np.uint8)
    b = raw.reshape(-1, 3).astype(np.int32); v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16); v = np.where(v >= 1 << 23, v - (1 << 24), v)
    info.update(sample_rate=sr, bits=bits, channels=ch, seconds=round(len(v) / sr, 3), chunks=chunks)
    return sr, v, info


def blast_onsets(x, sr, skip_click=False):
    """Sample index of each muzzle-blast onset: the first sample at or above 0.75 of full scale in each cluster,
    skipping a smaller event that precedes the main burst by 5 to 13 ms (the trigger break on the on-gun microphone)."""
    idx = np.where(np.abs(x) >= 0.75)[0]; out = [int(idx[0])]
    for i in idx:
        if i - out[-1] > 0.2 * sr: out.append(int(i))
    if not skip_click: return out
    fixed = []
    for o in out:
        seg = np.abs(x[o + int(.005 * sr):o + int(.013 * sr)]); pre = np.abs(x[max(0, o - int(.012 * sr)):max(1, o - int(.005 * sr))])
        fixed.append(o + int(.005 * sr) + int(np.argmax(seg >= 0.75)) if len(seg) and (seg >= 0.9).any() and pre.max() < 0.3 else o)
    return fixed


def octave(x, sr, fc):
    return signal.sosfilt(signal.butter(4, [fc / 2 ** .5, min(fc * 2 ** .5, sr / 2 * .95)], 'band', fs=sr, output='sos'), x)


def window_table(x, sr, onsets):
    """Median over shots of the rms level in each window and octave band, dB re full scale."""
    rows = {'broadband': x}; rows.update({str(fc): octave(x, sr, fc) for fc in OCT}); out = {}
    for name, y in rows.items():
        out[name] = []
        for a, b in WINDOWS_MS:
            v = [np.sqrt(np.mean(y[o + int(a * sr / 1e3):o + int(b * sr / 1e3)] ** 2)) for o in onsets if o + int(b * sr / 1e3) <= len(y)]
            out[name].append(r1(db(np.median(v))) if v else None)
    return out


def recording_trust():
    """Numbers that say what in each recording can be believed."""
    res = {}
    for key, fn in REFS.items():
        path = os.path.join(sim.REFDIR, fn)
        if not os.path.exists(path): continue
        sr, v, info = read_wav(path); x = v / 2 ** 23; on = blast_onsets(x, sr, key == 'ongun'); m = dict(file_name_says=fn.replace('_', ' ')[:-4], **info)
        a = np.abs(v); m['peak_dbfs'] = r1(db(np.abs(x).max()), 2); m['samples_at_full_scale'] = int(np.sum(a >= 8388600))
        m['low_byte_in_use_fraction'] = r1(np.mean((v & 0xFF) != 0), 3)
        f, Pxx = signal.welch(x, sr, nperseg=8192); lv = lambda fc: 10 * math.log10(Pxx[np.argmin(abs(f - fc))])
        m['long_term_spectrum_db_re_1khz'] = {str(fc): r1(lv(fc) - lv(1000)) for fc in (20, 50, 100, 10000, 20000, 30000, 40000)}
        m['shots'] = len(on); m['shot_spacing_ms'] = [r1(d / sr * 1e3) for d in np.diff(on) if d < sr]
        per = dict(clipped_samples=[], clipped_runs=[], longest_flat_top_us=[], first_clip_ms=[], last_clip_ms=[], crest_db_0_30ms=[], t_largest_ms=[], first_half_ms_peak_fs=[])
        for o in on:
            seg = v[o - int(.002 * sr):o + int(.03 * sr)]; c = (np.abs(seg) >= 8388600).astype(int); e = np.diff(np.concatenate(([0], c, [0]))); st = np.where(e == 1)[0]; en = np.where(e == -1)[0]
            xs = seg / 2 ** 23; per['clipped_samples'].append(int(c.sum())); per['clipped_runs'].append(len(st)); per['longest_flat_top_us'].append(r1((en - st).max() / sr * 1e6, 0) if len(st) else 0)
            per['first_clip_ms'].append(r1(st[0] / sr * 1e3 - 2, 2) if len(st) else None); per['last_clip_ms'].append(r1(en[-1] / sr * 1e3 - 2, 2) if len(st) else None)
            per['crest_db_0_30ms'].append(r1(db(np.abs(xs).max() / np.sqrt(np.mean(xs ** 2))))); per['t_largest_ms'].append(r1(np.argmax(np.abs(xs)) / sr * 1e3 - 2, 2))
            k0 = int(np.argmax(np.abs(xs) > 0.05)); per['first_half_ms_peak_fs'].append(r1(np.abs(xs[k0:k0 + int(.0005 * sr)]).max(), 2))
        m['per_shot'] = per
        # the level the signal sits at between shots, and how repeatable it is
        for a_, b_ in [(30, 60), (100, 150), (180, 210)]:
            L = [db(np.sqrt(np.mean(x[o + int(a_ * sr / 1e3):o + int(b_ * sr / 1e3)] ** 2))) for o in on if o + int(b_ * sr / 1e3) < len(x)]
            m['rms_dbfs_%d_%dms_after_shot' % (a_, b_)] = dict(median=r1(np.median(L)), spread=r1(np.max(L) - np.min(L)))
        # low-frequency overload recovery: the same slow excursion after every shot
        lp = signal.sosfiltfilt(signal.butter(2, 300, fs=sr, output='sos'), x); segs = [lp[o + int(.012 * sr):o + int(.035 * sr)] for o in on if o + int(.035 * sr) < len(x)]
        C = np.corrcoef(np.array(segs)); m['lf_below_300hz_12_35ms'] = dict(mean_correlation_between_shots=r1((C.sum() - len(C)) / (len(C) ** 2 - len(C)), 2), most_negative_fs=[r1(s.min(), 2) for s in segs])
        # a mechanical click before the blast (trigger break), and the bolt closing after it
        pre = []; late = []
        for o in on:
            lead = np.abs(x[max(0, o - int(.003 * sr)):o + 1]); ob = o - (len(lead) - 1 - int(np.argmax(lead > 0.1)))        # blast onset: first sample above 0.1 FS
            w = np.abs(x[max(0, ob - int(.014 * sr)):max(1, ob - int(.004 * sr))])
            if len(w) > int(.008 * sr) and w.max() > 4 * np.median(w) and (key == 'ongun' or o == on[0] or o - on[on.index(o) - 1] > sr):
                pre.append(dict(ms_before_blast=r1((len(w) - int(np.argmax(w > 0.3 * w.max()))) / sr * 1e3 + 4, 2), peak_dbfs=r1(db(w.max()))))
            if key == 'ongun' and o + int(.09 * sr) < len(x):
                w2 = x[o + int(.045 * sr):o + int(.09 * sr)] ** 2; n = int(.002 * sr); e2 = np.convolve(w2, np.ones(n) / n, 'same'); late.append(r1(45 + np.argmax(e2) / sr * 1e3))
        m['click_before_blast'] = pre; m['late_burst_ms_after_blast'] = late
        # reverberant decay after the last shot of each string, by band (20 ms rms, line fit 0.12 to 0.40 s and 0.4 to 0.8 s)
        ends = [on[i] for i in range(len(on)) if i == len(on) - 1 or on[i + 1] - on[i] > sr]; dec = {}
        for name, y in [('broadband', x)] + [(str(fc), octave(x, sr, fc)) for fc in [250, 500, 1000, 2000, 4000, 8000, 16000]]:
            t60a, t60b, l1 = [], [], []
            for o in ends:
                w = int(.02 * sr); e = np.array([np.mean(y[i:i + w] ** 2) for i in range(o + int(.1 * sr), min(len(y) - w, o + int(1.0 * sr)), w)]); t = 0.11 + np.arange(len(e)) * 0.02; L = 10 * np.log10(e + 1e-20)
                ma = (t > 0.12) & (t < 0.4); mb = (t > 0.4) & (t < 0.8); t60a.append(-60 / np.polyfit(t[ma], L[ma], 1)[0]); t60b.append(-60 / np.polyfit(t[mb], L[mb], 1)[0]); l1.append(L[0])
            dec[name] = dict(t60_s_fit_120_400ms=r1(np.mean(t60a), 2), t60_s_fit_400_800ms=r1(np.mean(t60b), 2), level_dbfs_at_110ms=r1(np.mean(l1)))
        m['decay_after_last_shot'] = dec
        m['window_levels_dbfs'] = dict(windows_ms=WINDOWS_MS, table=window_table(x, sr, on))
        m['pre_roll_rms_dbfs'] = r1(db(np.sqrt(np.mean(x[:int(.003 * sr)] ** 2)))); m['file_end_rms_dbfs'] = r1(db(np.sqrt(np.mean(x[-int(.05 * sr):] ** 2)) + 1e-12))
        res[key] = m
    return res


def mic_chain(p, key):
    """Pressure (Pa, 48 kHz) -> what the microphone model delivers, as a fraction of its clip level (full scale)."""
    mic = MICS[key]; n = 1 << int(math.ceil(math.log2(len(p)))); W = sim.band_weights(n); g = np.zeros(n // 2 + 1)
    for b in range(9): g += W[b] * 10 ** (mic['off_axis_db'][b] / 20)
    y = np.fft.irfft(np.fft.rfft(p, n) * g, n)[:len(p)]
    y = signal.sosfilt(signal.butter(2, mic['hp_hz'], 'high', fs=sim.FS, output='sos'), y)
    clip = sim.P_REF * 10 ** (mic['clip_db_peak'] / 20)
    return np.clip(y / clip, -1, 1), float(np.max(np.abs(y)) / clip)


def sim_at_mic(P, key):
    """One simulated shot over open ground at the microphone position, through the microphone model."""
    p = sim.synth_dry(P, key, 'single', field=True); y, over = mic_chain(p, key)
    pp = P['persp'][key]; onset = int(round((pp['t_first'] + pp['t0']) * sim.FS))
    return p, y, onset, over


def shares(x, sr, onsets, span_ms=50.0):
    """Median over shots: share of the energy in 0-2, 2-10 and 10-span ms after onset (per cent), the crest factor over
    the span (dB) and the time by which 90 % of the span's energy has arrived (ms)."""
    rows = []
    for o in onsets:
        seg = x[o:o + int(span_ms * sr / 1e3)]
        if len(seg) < int(span_ms * sr / 1e3): continue
        e = seg ** 2; tot = e.sum(); k = lambda ms: int(ms * sr / 1e3); cum = np.cumsum(e) / tot
        rows.append([100 * e[:k(2)].sum() / tot, 100 * e[k(2):k(10)].sum() / tot, 100 * e[k(10):].sum() / tot, db(np.abs(seg).max() / math.sqrt(tot / len(seg))), np.argmax(cum >= 0.9) / sr * 1e3])
    m = np.median(np.array(rows), 0)
    return dict(share_0_2ms_pct=r1(m[0]), share_2_10ms_pct=r1(m[1]), share_10ms_on_pct=r1(m[2], 2), crest_db=r1(m[3]), t90_ms=r1(m[4], 2))


def clip_at(p, over_db):
    """Hard-clip a pressure signal over_db below its own peak (what a chain overloaded by over_db does)."""
    lim = np.max(np.abs(p)) * 10 ** (-over_db / 20); return np.clip(p, -lim, lim)


def energy_shares(P, trust_audio):
    """How much of the first 50 ms is 'click' and how much is 'body', and how far clipping alone moves that."""
    out = dict(note='Energy in the first 50 ms after the blast onset. Clipping removes energy from the peak and so moves the shares towards the later '
                    'windows: the rows "simulation clipped N dB" bound that effect. 28 dB is the published 164 dB peak over the MKH 416 clip level (136 dB).', microphones={}, shooter={})
    for key in REFS:
        p, y, onset, over = sim_at_mic(P, key); m = dict(simulation=shares(p, sim.FS, [onset]), simulation_through_microphone_model=shares(y, sim.FS, [onset]))
        for od in (10, 20, 28, 40): m['simulation_clipped_%d_db' % od] = shares(clip_at(p, od), sim.FS, [onset])
        if key in trust_audio: x, sr, on = trust_audio[key]; m['recording'] = shares(x, sr, on)
        out['microphones'][key] = m
    pp = P['persp']['shooter']; onset = int(round((pp['t_first'] + pp['t0']) * sim.FS)) - 2; dry = sim.synth_dry(P, 'shooter', 'single', False)
    pk0 = np.max(np.abs(dry)); pkdb = sim.levels(dry)['peak_db_spl']
    out['shooter']['dry_free_field'] = shares(dry, sim.FS, [onset]); out['shooter']['open_ground'] = shares(sim.synth_dry(P, 'shooter', 'single', True), sim.FS, [onset])
    for ov in ['open_field', 'range_berm', 'indoor_range']:
        w = signal.fftconvolve(dry, sim.build_ir(P, ov, 'shooter')); out['shooter'][ov] = shares(w, sim.FS, [onset])
        if hasattr(sim, 'ear_playback'): out['shooter'][ov + '_through_ear_stage'] = shares(sim.ear_playback(w / pk0 * 10 ** (-1 / 20), pkdb), sim.FS, [onset])
    if hasattr(sim, 'ear_playback'): out['shooter']['dry_free_field_through_ear_stage'] = shares(sim.ear_playback(dry / pk0 * 10 ** (-1 / 20), pkdb), sim.FS, [onset])
    return out


def distances(sim_tab, rec_tab, wins, bands):
    """Level distance (mean absolute difference) and shape distance (rms difference after removing each side's band mean), dB."""
    out = {}
    for wi in wins:
        a = np.array([sim_tab[str(b)][wi] for b in bands], float); c = np.array([rec_tab[str(b)][wi] for b in bands], float)
        out['%d-%d ms' % tuple(WINDOWS_MS[wi])] = dict(level_distance_db=r1(np.mean(np.abs(a - c))), shape_distance_db=r1(np.sqrt(np.mean(((a - a.mean()) - (c - c.mean())) ** 2))), sim_minus_recording_db=r1(np.mean(a - c)))
    return out


def diagnose(P, trust):
    res = dict(note='Simulation: one shot over open ground at the microphone position, through the microphone model, levels in dB re the '
                    'microphone clip level. Recording: dB re digital full scale. The two scales coincide only if the file full scale is the '
                    'microphone clip level, which is an assumption. Windows are after the blast onset at the microphone.',
               windows_ms=WINDOWS_MS, octave_bands_hz=OCT, microphones=MICS, pairs={})
    for key in REFS:
        p, y, onset, over = sim_at_mic(P, key); tab = window_table(y, sim.FS, [onset]); m = dict(simulation=dict(peak_db_spl=sim.levels(p)['peak_db_spl'], overload_db=r1(db(over)), window_levels_db_re_clip=tab))
        e = np.abs(y[onset:onset + int(.2 * sim.FS)]); n = int(.001 * sim.FS); es = np.sqrt(np.convolve(e ** 2, np.ones(n) / n, 'same')); above = np.where(es > 0.1)[0]
        m['simulation']['last_ms_within_20db_of_clip'] = r1(above[-1] / sim.FS * 1e3) if len(above) else 0.0
        if key in trust:
            rt = trust[key]['window_levels_dbfs']['table']; m['recording_window_levels_dbfs'] = rt
            m['all_windows'] = distances(tab, rt, range(len(WINDOWS_MS)), OCT)
            m['trusted_windows'] = distances(tab, rt, [3, 4] if key == 'ongun' else [3, 5], [250, 500, 1000, 2000, 4000, 8000])
        res['pairs'][key] = m
    # timing the recordings can be trusted on, against the action simulation
    cyc = {e[0]: e[1] for e in P['cycle']}; tm = dict(simulation_ms=dict(trigger_break_to_bullet_exit=r1(-cyc['sear'] * 1e3, 2) if 'sear' in cyc else None, bullet_exit_to_bolt_closed=r1(cyc['battery'] * 1e3, 1)))
    if 'ongun' in trust:
        tm['recording_ms'] = dict(click_to_blast_on_gun=r1(np.median([c['ms_before_blast'] for c in trust['ongun']['click_before_blast']]), 2), click_to_blast_1m=r1(np.median([c['ms_before_blast'] for c in trust['side1m']['click_before_blast']]), 2) if trust.get('side1m', {}).get('click_before_blast') else None,
                                  blast_to_late_burst_on_gun=r1(np.median(trust['ongun']['late_burst_ms_after_blast'])))
    res['timing'] = tm
    # the reverberant tail: every shooter overlay, measured the way the recordings were
    dry = sim.synth_dry(P, 'shooter', 'single', False); pk = np.max(np.abs(dry)); tails = {}
    for ov in P['overlays']:
        h = sim.build_ir(P, ov, 'shooter'); wet = signal.fftconvolve(dry, h); o = int(np.argmax(np.abs(wet) > 0.5 * np.max(np.abs(wet)))); w = int(.02 * sim.FS)
        e = np.array([np.mean(wet[i:i + w] ** 2) for i in range(o + int(.1 * sim.FS), min(len(wet) - w, o + int(1.0 * sim.FS)), w)]); t = 0.11 + np.arange(len(e)) * 0.02; L = 10 * np.log10(e + 1e-20); ma = (t > 0.12) & (t < 0.4) & (L > -200)
        g = lambda a, b: db(np.sqrt(np.mean(wet[o + int(a * sim.FS):o + int(b * sim.FS)] ** 2)) / pk + 1e-12)
        tails[ov] = dict(rms_10_30ms_db_re_direct_peak=r1(g(.01, .03)), rms_30_100ms_db_re_direct_peak=r1(g(.03, .1)), rms_100_200ms_db_re_direct_peak=r1(g(.1, .2)),
                         t60_s_fit_120_400ms=r1(-60 / np.polyfit(t[ma], L[ma], 1)[0], 2) if ma.sum() > 3 and np.ptp(L[ma]) > 0.5 else None)
    res['shooter_tail_by_overlay'] = tails
    if 'side1m' in trust:
        # the recorded tail against the published peak, if full scale is the MKH 416 clip level (upper bound: the file may be scaled lower)
        res['recorded_tail_bound'] = dict(tail_rms_dbfs_100_150ms=trust['side1m']['rms_dbfs_100_150ms_after_shot']['median'], assumed_full_scale_db_spl_peak=MICS['side1m']['clip_db_peak'], published_peak_db_spl_at_1m=164.0,
                                          tail_db_re_true_peak_upper_bound=r1(trust['side1m']['rms_dbfs_100_150ms_after_shot']['median'] + MICS['side1m']['clip_db_peak'] - 164.0))
    return res


def published(P):
    """Simulated free-field peaks against published 5.56 mm figures (see README for the sources)."""
    out = {}
    def pk(persp, field=False): return sim.levels(sim.synth_dry(P, persp, 'single', field, parts=('blast',)))['peak_db_spl']
    out['1 m left of the muzzle, 90 deg'] = dict(simulation_db=pk('side1m'), published_db=164.0, source='Dater / Larson Davis firearm sound briefing: M4 (14.5 in, M855), MIL-STD-1474 position 1 m left of the muzzle; HK416 equal to the M4 unsuppressed')
    out["shooter's ear"] = dict(simulation_db=pk('shooter'), simulation_over_ground_db=pk('shooter', True), published_db='155 to 160', source="commonly quoted at-ear peaks for unsuppressed 5.56 mm carbines (recalled from the literature; not re-fetched)")
    return out


def run(P):
    os.makedirs(sim.COMPARE, exist_ok=True)
    trust = recording_trust()
    if trust: json.dump(dict(note='Condition of the local reference recordings. Scalars only; no audio and nothing that could rebuild it.', recordings=trust), open(os.path.join(sim.COMPARE, 'recording_trust.json'), 'w'), indent=1)
    else: print('no reference recordings found in %s: recording side skipped' % sim.REFDIR)
    res = diagnose(P, trust); res['published_peaks'] = published(P)
    audio = {}
    for key, fn in REFS.items():
        path = os.path.join(sim.REFDIR, fn)
        if os.path.exists(path): sr, v, _ = read_wav(path); x = v / 2 ** 23; audio[key] = (x, sr, [o - int(.0015 * sr) for o in blast_onsets(x, sr, key == 'ongun')])
    res['energy_shares'] = energy_shares(P, audio)
    chk = {}
    for persp in ['shooter', 'bystander', 'downrange']:
        a = sim.synth_dry(P, persp, 'single', True, parts=('blast',)); b = signal.fftconvolve(sim.synth_dry(P, persp, 'single', False, parts=('blast',)), sim.build_ir(P, 'open_field', persp, skip=('groundscatter',)))[:len(a)]
        chk[persp] = r1(10 * np.log10(np.sum((a - b) ** 2) / np.sum(a ** 2)))
    res['open_field_ir_vs_direct_ground_render_error_db'] = chk
    res['model_version'] = P.get('version')
    json.dump(res, open(os.path.join(sim.COMPARE, 'diagnosis.json'), 'w'), indent=1)
    for key, m in res['pairs'].items():
        print('\n== %s: simulated peak %.1f dB SPL, %.1f dB over the microphone clip level' % (key, m['simulation']['peak_db_spl'], m['simulation']['overload_db']))
        for k in ('all_windows', 'trusted_windows'):
            for w, d in m.get(k, {}).items(): print('  %-16s %-12s level %5.1f dB  shape %5.1f dB  (sim - rec %+.1f dB)' % (k, w, d['level_distance_db'], d['shape_distance_db'], d['sim_minus_recording_db']))
    for grp in ('microphones', 'shooter'):
        for k, v in res['energy_shares'][grp].items():
            for kk, vv in (v.items() if grp == 'microphones' else [('', v)]): print('  shares %-10s %-38s %s' % (k, kk, list(vv.values())))
    print('\ntiming', res['timing']); print('published', {k: (v['simulation_db'], v['published_db']) for k, v in res['published_peaks'].items()})
    print('open-field IR vs direct ground render (blast only), error dB:', chk)
    plots(P)


def plots(P):
    """Simulation-only plots (nothing from a recording)."""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 2, figsize=(15, 10))
    for row, persp in enumerate(['shooter', 'bystander', 'downrange']):
        for col, (T, ttl) in enumerate([(0.03, 'first 30 ms'), (0.2, 'first 200 ms, dB')]):
            a = ax[row, col]
            for field, c in ((False, '#00798c'), (True, '#d1495b')):
                x = sim.synth_dry(P, persp, 'single', field)[:int(T * sim.FS)]; t = np.arange(len(x)) / sim.FS * 1e3
                a.plot(t, x if col == 0 else 20 * np.log10(np.abs(x) / sim.P_REF + 1e-3), lw=0.7, color=c, label='open ground' if field else 'free field')
            a.set_title('%s, single shot: %s' % (persp, ttl)); a.set_ylabel('Pa' if col == 0 else 'dB SPL (instantaneous)'); a.grid(alpha=.3); a.legend(fontsize=8)
            if col: a.set_ylim(40, 165)
    plt.tight_layout(); plt.savefig(os.path.join(sim.COMPARE, 'sim_perspectives.png'), dpi=80); plt.close()
