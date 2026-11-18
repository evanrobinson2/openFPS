#!/usr/bin/env python3
"""Measurements taken on a synthesised pressure waveform (pascals). Used by sim.py for its checks, and by
`python3 sound/measure.py <params.json> <out.json>` to snapshot the band envelopes of any version of params.json.
Nothing here reads a recording.

Definitions
- peak level: 20 log10(max |p| / 20 uPa).
- A-duration (MIL-STD-1474D): time from the onset of the first wave to its first return to ambient pressure.
- negative phase: from that zero crossing until the pressure has come back to 10 % of its most negative value.
- B-duration (MIL-STD-1474D): total time the envelope of the pressure fluctuations, positive and negative, is within
  20 dB of the peak, reflections included. The envelope here is the running maximum of |p| over 1 ms.
- rms9: rms level of a 9.07 ms window that starts 1.13 ms before the onset: the measure of Maher and Shaw (2010),
  400 samples at 44.1 kHz starting 50 samples before the muzzle blast.
- third-octave maximum: the 1/3-octave band holding the most energy in a 42.67 ms window from the onset: the
  analysis window of Murphy and Tubbs (2007).
- band envelopes: octave bands 63 Hz to 8 kHz (zero-phase brick-wall filters); for each, the sound exposure level,
  the rms level in five windows after the onset, and the time after which the band stays 20 dB under its own maximum.
"""
import json, math, sys
import numpy as np

PREF = 20e-6
OCT = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
WINDOWS_MS = [(0, 2), (2, 10), (10, 50), (50, 200), (200, 500)]

def db(p): return 20 * math.log10(max(abs(p), 1e-12) / PREF)

def onset(y, frac=0.05):
    pk = float(np.max(np.abs(y)))
    return int(np.argmax(np.abs(y) >= frac * pk))

def onset_of_peak(y, fs, frac=0.02):
    """onset of the wave that carries the largest peak: walk back from the peak to the last quiet sample before it"""
    ip = int(np.argmax(np.abs(y))); pk = abs(y[ip]); i = ip
    while i > 0 and abs(y[i - 1]) >= frac * pk and ip - i < int(0.004 * fs): i -= 1
    return i

def a_duration(y, fs):
    i0 = onset_of_peak(y, fs); ip = int(np.argmax(np.abs(y))); s = 1.0 if y[ip] > 0 else -1.0; i = ip
    while i + 1 < len(y) and s * y[i + 1] > 0: i += 1
    if i + 1 >= len(y): return None
    frac = s * y[i] / (s * y[i] - s * y[i + 1])
    return (i + frac - i0) / fs                          # from the first sample of the wave; the true onset lies up to one sample (21 microseconds) earlier

def negative_phase(y, fs):
    ip = int(np.argmax(np.abs(y))); i = ip
    while i + 1 < len(y) and y[i + 1] > 0: i += 1
    z = i + 1; j = z; n_end = min(len(y), z + int(0.02 * fs))
    if z >= n_end: return None
    seg = y[z:n_end]; imin = int(np.argmin(seg)); pmin = float(seg[imin]); k = imin
    while k + 1 < len(seg) and seg[k + 1] < 0.1 * pmin: k += 1
    return dict(duration_ms=round((k + 1) / fs * 1e3, 3), min_pa=round(pmin, 2), min_re_peak=round(pmin / abs(y[ip]), 4), time_of_min_ms=round(imin / fs * 1e3, 3))

def b_duration(y, fs, win=0.001):
    a = np.abs(y); w = max(1, int(win * fs)); pad = np.concatenate([np.zeros(w - 1), a]); env = np.max(np.lib.stride_tricks.sliding_window_view(pad, w), axis=1)
    return float(np.sum(env >= 0.1 * a.max())) / fs

def rms9(y, fs):
    i0 = onset(y, 0.02); a = max(0, i0 - int(round(50 / 44100 * fs))); n = int(round(400 / 44100 * fs)); seg = y[a:a + n]
    return db(math.sqrt(float(np.mean(seg ** 2))))

def third_octave_max(y, fs, win=2048):
    i0 = onset_of_peak(y, fs); seg = np.zeros(win); s = y[i0:i0 + win]; seg[:len(s)] = s
    sp = np.abs(np.fft.rfft(seg)) ** 2; f = np.fft.rfftfreq(win, 1 / fs); out = {}
    for n in range(-10, 13):                             # 100 Hz to 16 kHz
        fc = 1000 * 2 ** (n / 3); m = (f >= fc * 2 ** (-1 / 6)) & (f < fc * 2 ** (1 / 6))
        if m.any(): out[round(fc)] = 10 * math.log10(2 * sp[m].sum() / win ** 2 / PREF ** 2 + 1e-30)   # band level averaged over the window
    best = max(out, key=out.get)
    return dict(band_hz=best, level_db=round(out[best], 1), bands={k: round(v, 1) for k, v in out.items()})

def octave(y, fs, fc):
    sp = np.fft.rfft(y); f = np.fft.rfftfreq(len(y), 1 / fs); sp[(f < fc / math.sqrt(2)) | (f >= fc * math.sqrt(2))] = 0
    return np.fft.irfft(sp, len(y))

def band_envelopes(y, fs):
    i0 = onset(y, 0.02); out = {}
    for fc in OCT:
        b = octave(y, fs, fc); e = float(np.sum(b ** 2)) / fs; row = dict(sel_db=round(10 * math.log10(e / PREF ** 2 + 1e-30), 1))
        for a, z in WINDOWS_MS:
            seg = b[i0 + int(a * fs / 1e3): i0 + int(z * fs / 1e3)]
            row[f'rms_{a}_{z}ms_db'] = round(db(math.sqrt(float(np.mean(seg ** 2)))), 1) if len(seg) > 8 else None
        w = int(0.002 * fs); env = np.sqrt(np.convolve(b ** 2, np.ones(w) / w, 'same')); m = env.max(); above = np.nonzero(env >= 0.1 * m)[0]
        row['stays_20db_down_after_ms'] = round((above[-1] - i0) / fs * 1e3, 1) if len(above) else None
        out[str(fc)] = row
    return out

def summary(y, fs):
    pk = float(np.max(np.abs(y))); i0 = onset(y, 0.02); e = float(np.sum(y ** 2)) / fs
    def frac_after(ms): return float(np.sum(y[i0 + int(ms * fs / 1e3):] ** 2)) / fs / e
    sp = np.abs(np.fft.rfft(y)) ** 2; f = np.fft.rfftfreq(len(y), 1 / fs)
    return dict(peak_db=round(db(pk), 1), sel_db=round(10 * math.log10(e / PREF ** 2), 1), b_duration_ms=round(b_duration(y, fs) * 1e3, 2),
                energy_after_2ms_db=round(10 * math.log10(frac_after(2) + 1e-30), 1), energy_after_10ms_db=round(10 * math.log10(frac_after(10) + 1e-30), 1),
                energy_after_50ms_db=round(10 * math.log10(frac_after(50) + 1e-30), 1), spectral_centroid_hz=round(float((f * sp).sum() / sp.sum())),
                energy_below_250hz_db=round(10 * math.log10(sp[f < 250].sum() / sp.sum() + 1e-30), 1), bands=band_envelopes(y, fs))

if __name__ == '__main__':
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import sim
    P = json.load(open(sys.argv[1])); out = {}
    for name, snd in P['sounds'].items(): out[name] = summary(sim.render(snd, P['fs'], P.get('filters')) if 'filters' in P else sim.render(snd, P['fs']), P['fs'])
    json.dump(dict(note='band envelopes and summary measures of every sound in ' + os.path.basename(sys.argv[1]) + ' (see measure.py for the definitions); simulation only', sounds=out), open(sys.argv[2], 'w'), indent=1)
    for k, v in out.items(): print(f"{k:30s} peak {v['peak_db']:6.1f} dB  B {v['b_duration_ms']:7.2f} ms  after 10 ms {v['energy_after_10ms_db']:6.1f} dB  centroid {v['spectral_centroid_hz']} Hz")
