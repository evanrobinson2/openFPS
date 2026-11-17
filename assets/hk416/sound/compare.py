"""Matched comparison of the simulation against the two local reference recordings.

The recordings are measurement references only: nothing derived from their audio is written anywhere
except numbers and plots in sound/compare/. Run through `python3 sound/sim.py compare`.
"""
import json, os, warnings
import numpy as np
from scipy import signal
from scipy.io import wavfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sim

REFS = {'ongun': 'HK_416_5.56mm_on_gun_DPA4062_clean_Seven_shots_x_1.wav',
        'side1m': 'HK_416_5.56mm_1m_left_off_axis_MKH416_clean_Six_shots_x_2.wav'}
THIRD = [50 * 2 ** (i / 3) for i in range(0, 27)]          # 50 Hz .. 20 kHz


def shots(x, sr):
    """Shot onsets: peaks of the 300 Hz - 6 kHz envelope that stand 12 dB above the preceding 20-60 ms."""
    sos = signal.butter(2, 400, fs=sr, output='sos')
    e = np.sqrt(np.maximum(signal.sosfiltfilt(sos, x * x), 1e-20)); thr = 0.35 * e.max()
    on = []; i = 0; gap = int(0.15 * sr)
    while i < len(e):
        if e[i] > thr:
            j = i + int(np.argmax(e[i:i + int(0.02 * sr)])); pk = np.max(np.abs(x[i:i + int(0.02 * sr)]))
            k = max(0, i - int(0.004 * sr)); seg = np.abs(x[k:j + 1]); on.append(k + int(np.argmax(seg > 0.1 * pk))); i += gap
        else: i += 1
    return np.array(on)


def third_oct(x, sr):
    X = np.abs(np.fft.rfft(x * signal.windows.tukey(len(x), 0.1), 1 << 15)) ** 2; f = np.fft.rfftfreq(1 << 15, 1 / sr)
    out = []
    for fc in THIRD:
        m = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6)); out.append(X[m].sum() if fc < sr / 2 * 0.9 else np.nan)
    out = np.array(out); return 10 * np.log10(out / np.nansum(out) + 1e-20)


def measure(x, sr, label):
    x = x / np.max(np.abs(x)); on = shots(x, sr); m = dict(label=label, sample_rate=sr, shots=len(on))
    m['clipped_fraction_of_shot_window'] = round(float(np.mean(np.abs(np.concatenate([x[o:o + int(0.01 * sr)] for o in on])) > 0.985)), 4)
    if len(on) > 1:
        d = np.diff(on) / sr; d = d[d < 1.0]; m['shot_spacing_ms'] = [round(v * 1e3, 1) for v in d]; m['shot_spacing_mean_ms'] = round(float(d.mean() * 1e3), 1)
    rise, pos, first_pk, t_main, close, dec20 = [], [], [], [], [], []
    for o in on:
        seg = x[o:o + int(0.02 * sr)]; pk = np.max(np.abs(seg))
        i_pk = int(np.argmax(np.abs(seg) >= 0.5 * pk)); sgn = np.sign(seg[i_pk])
        # first major excursion: from the 0.5*pk crossing, walk to its local maximum
        j = i_pk
        while j + 1 < len(seg) and sgn * seg[j + 1] >= sgn * seg[j]: j += 1
        a = sgn * seg[j]; pre = sgn * x[max(0, o - int(0.001 * sr)):o + j + 1][::-1]
        i10 = int(np.argmax(pre < 0.1 * a)); i90 = int(np.argmax(pre < 0.9 * a)); rise.append((i10 - i90) / sr * 1e6)
        z = j
        while z + 1 < len(seg) and sgn * seg[z] > 0: z += 1
        k = j
        while k > 0 and sgn * seg[k] > 0: k -= 1
        pos.append((z - k) / sr * 1e3); first_pk.append(float(sgn * a)); t_main.append(int(np.argmax(np.abs(seg))) / sr * 1e3)
        env = np.abs(x[o:o + int(0.1 * sr)]); w = int(0.001 * sr); es = np.convolve(env ** 2, np.ones(w) / w, 'same')
        lo, hi = int(0.04 * sr), int(0.095 * sr)
        if len(es) > hi: close.append((lo + int(np.argmax(es[lo:hi]))) / sr * 1e3)
        ip = int(np.argmax(es)); tail = np.maximum.accumulate(es[ip:][::-1])[::-1]; below = np.argmax(tail < es.max() * 0.01) if (tail < es.max() * 0.01).any() else len(tail); dec20.append((ip + below) / sr * 1e3)
    med = lambda v: round(float(np.median(v)), 3) if len(v) else None
    m.update(rise_10_90_us=med(rise), first_excursion_width_ms=med(pos), first_excursion_sign_and_size=med(first_pk), time_of_largest_peak_ms=med(t_main),
             late_event_40_95ms_after_onset_ms=med(close), time_until_1ms_energy_stays_20dB_down_ms_max100=med(dec20))
    o = on[0]; w = x[max(0, o - int(0.002 * sr)):o + int(0.03 * sr)]; m['third_octave_db_re_total'] = [round(float(v), 1) for v in third_oct(w, sr)]
    return m, on, x


def run(P):
    os.makedirs(sim.COMPARE, exist_ok=True); res = dict(note='Reference recordings are normalised, peak-limited/clipped and carry the recording chain; levels are relative.', third_octave_hz=[round(f, 1) for f in THIRD], pairs={})
    fig, ax = plt.subplots(4, 2, figsize=(15, 16))
    for col, (persp, fn) in enumerate(REFS.items()):
        s = sim.synth_dry(P, persp, 'semi3', field=True); ms, ons, xs = measure(s, sim.FS, 'simulation ' + persp)
        ms['peak_db_spl'] = sim.levels(s)['peak_db_spl']; pair = dict(simulation=ms)
        path = os.path.join(sim.REFDIR, fn); have = os.path.exists(path)
        if have:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore'); sr, r = wavfile.read(path)
            r = r.astype(float) / 2 ** 31; mr, onr, xr = measure(r, sr, 'recording ' + persp); pair['recording'] = mr
            d = np.array(ms['third_octave_db_re_total']) - np.array(mr['third_octave_db_re_total']); ok = np.isfinite(d)
            pair['third_octave_rms_difference_db'] = round(float(np.sqrt(np.mean(d[ok] ** 2))), 1)
        res['pairs'][persp] = pair
        for row, (pre, post, title) in enumerate([(0.5e-3, 6e-3, 'first 6 ms'), (5e-3, 0.1, 'first 100 ms'), (0.02, 0.9, 'string')]):
            a = ax[row, col]
            if have: i = onr[0]; seg = xr[max(0, i - int(pre * sr)):i + int(post * sr)]; a.plot((np.arange(len(seg)) / sr - min(pre, i / sr)) * 1e3, seg, lw=0.6, color='#888', label='recording (normalised)')
            i = ons[0]; seg = xs[max(0, i - int(pre * sim.FS)):i + int(post * sim.FS)]; a.plot((np.arange(len(seg)) / sim.FS - min(pre, i / sim.FS)) * 1e3, seg, lw=0.9, color='#d1495b', label='simulation (normalised)')
            a.set_title('%s: %s' % (persp, title)); a.set_xlabel('ms after onset'); a.grid(alpha=.3); a.legend(fontsize=8)
        a = ax[3, col]
        if have: a.semilogx(THIRD, mr['third_octave_db_re_total'], 'o-', color='#888', ms=3, label='recording')
        a.semilogx(THIRD, ms['third_octave_db_re_total'], 'o-', color='#d1495b', ms=3, label='simulation'); a.set_title('%s: 1/3-octave spectrum of the first 30 ms (dB re total)' % persp)
        a.set_xlabel('Hz'); a.set_ylim(-45, 0); a.grid(alpha=.3, which='both'); a.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(os.path.join(sim.COMPARE, 'compare_waveform_spectrum.png'), dpi=80); plt.close()

    # simulation-only views: every perspective, and what each overlay adds
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

    ovs = list(P['overlays']); fig, ax = plt.subplots(5, 2, figsize=(15, 16)); dry = sim.synth_dry(P, 'shooter', 'single', False)
    for a, o in zip(ax.flat, ovs):
        h = sim.build_ir(P, o, 'shooter'); wet = signal.fftconvolve(dry, h)[:int(min(len(h) / sim.FS + 0.3, 6.0) * sim.FS)]
        f, t, S = signal.spectrogram(wet, sim.FS, nperseg=1024, noverlap=768)
        a.pcolormesh(t, f / 1e3, 10 * np.log10(S / sim.P_REF ** 2 + 1e-9), vmin=0, vmax=110, shading='auto', cmap='magma'); a.set_ylim(0, 16)
        a.set_title('%s (shooter): spectrogram, dB re 20 uPa^2/Hz' % P['overlays'][o]['title'], fontsize=9); a.set_ylabel('kHz')
    plt.tight_layout(); plt.savefig(os.path.join(sim.COMPARE, 'overlays_spectrograms.png'), dpi=70); plt.close()

    # consistency: free-field render convolved with the open-field IR should equal the open-ground render
    chk = {}
    for persp in ['shooter', 'bystander', 'downrange']:
        a = sim.synth_dry(P, persp, 'single', True, parts=('blast',)); b = signal.fftconvolve(sim.synth_dry(P, persp, 'single', False, parts=('blast',)), sim.build_ir(P, 'open_field', persp))[:len(a)]
        chk[persp] = round(float(10 * np.log10(np.sum((a - b) ** 2) / np.sum(a ** 2))), 1)
    res['open_field_ir_vs_direct_ground_render_error_db'] = chk
    json.dump(res, open(os.path.join(sim.COMPARE, 'compare.json'), 'w'), indent=1)
    for persp, pair in res['pairs'].items():
        print('\n== %s' % persp)
        keys = ['shots', 'shot_spacing_mean_ms', 'rise_10_90_us', 'first_excursion_width_ms', 'time_of_largest_peak_ms', 'late_event_40_95ms_after_onset_ms', 'time_until_1ms_energy_stays_20dB_down_ms_max100', 'clipped_fraction_of_shot_window']
        for k in keys: print('  %-36s recording %-10s simulation %s' % (k, pair.get('recording', {}).get(k, 'n/a'), pair['simulation'].get(k)))
        print('  third-octave rms difference: %s dB; simulated peak %s dB SPL' % (pair.get('third_octave_rms_difference_db', 'n/a'), pair['simulation']['peak_db_spl']))
    print('\nopen-field IR vs direct ground render (blast only), error dB:', chk)
