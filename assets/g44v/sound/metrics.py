#!/usr/bin/env python3
"""Measures of an impulse waveform in pascals, as the hearing-conservation literature defines them.  Used by sim.py (checks) and
diagnose.py (before and after).  Nothing here reads a recording."""
import math
import numpy as np
from scipy.signal import butter, sosfiltfilt
P_REF = 20e-6
def db(p): return 20 * math.log10(max(abs(float(p)), 1e-30) / P_REF)
def a_weight(f):
    f2 = np.asarray(f, float) ** 2
    ra = (12194.0 ** 2 * f2 ** 2) / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194.0 ** 2))
    return ra * 10 ** (2.0 / 20)          # IEC 61672 A-weighting, linear gain, 0 dB at 1 kHz
def sel(x, fs, weighted=False):
    """sound exposure level, dB re (20 uPa)^2 s; A-weighted in the frequency domain if asked"""
    if weighted:
        X = np.fft.rfft(x); x = np.fft.irfft(X * a_weight(np.fft.rfftfreq(len(x), 1 / fs)), len(x))
    return 10 * math.log10(max(float(np.sum(x * x)) / fs, 1e-30) / P_REF ** 2)
def a_duration(x, fs, up=16):
    """A-duration (MIL-STD-1474 / CHABA): time from the start of the principal pressure wave to its first return to ambient.
    Measured on the waveform interpolated `up` times; the start is where the pressure first passes 5 % of the peak."""
    from scipy.signal import resample
    i = int(np.argmax(np.abs(x))); a = max(0, i - 64); b = min(len(x), i + 192); y = resample(x[a:b], (b - a) * up); y = y * np.sign(y[np.argmax(np.abs(y))])
    k = int(np.argmax(y)); pk = y[k]; s = k
    while s > 0 and y[s] > 0.05 * pk: s -= 1
    e = k
    while e < len(y) - 1 and y[e] > 0: e += 1
    return (e - s) / (fs * up)
def negative_phase(x, fs):
    """depth of the negative phase relative to the peak, and its length (from the first zero crossing to the return within 5 % of the depth)"""
    i = int(np.argmax(np.abs(x))); sg = np.sign(x[i]); y = x * sg; e = i
    while e < len(y) - 1 and y[e] > 0: e += 1
    seg = y[e:e + int(0.004 * fs)]
    if len(seg) < 2 or seg.min() >= 0: return dict(depth_re_peak=0.0, length_ms=0.0)
    j = int(np.argmin(seg)); d = seg[j]; k = j
    while k < len(seg) - 1 and seg[k] < 0.05 * d: k += 1
    return dict(depth_re_peak=round(float(d / y[i]), 3), length_ms=round(k / fs * 1e3, 3))
def b_duration(x, fs):
    """B-duration: total time the envelope is within 20 dB of the peak (Hilbert envelope, 0.1 ms smoothing)"""
    from scipy.signal import hilbert
    env = np.abs(hilbert(x)); n = max(1, int(1e-4 * fs)); env = np.convolve(env, np.ones(n) / n, 'same')
    return float(np.sum(env > 0.1 * env.max())) / fs
BANDS = [125, 250, 500, 1000, 2000, 4000, 8000]
def band_envelopes(x, fs):
    """per octave band: exposure level, peak level, the time the band's envelope stays within 20 dB of its own peak, and the
    share of the band's energy that arrives more than 2 ms after the band's peak"""
    out = {}
    pad = np.concatenate([np.zeros(int(0.02 * fs)), x, np.zeros(int(0.05 * fs))])
    for fc in BANDS:
        sos = butter(3, [fc / math.sqrt(2), min(fc * math.sqrt(2), 0.49 * fs)], 'bandpass', fs=fs, output='sos'); y = sosfiltfilt(sos, pad)
        from scipy.signal import hilbert
        env = np.abs(hilbert(y)); i = int(np.argmax(env)); e2 = y * y; tot = float(e2.sum())
        late = np.nonzero(env > 0.1 * env[i])[0]
        out[str(fc)] = dict(t20_ms=round((int(late[-1]) - i) / fs * 1e3, 2), sel_db=round(10 * math.log10(max(tot / fs, 1e-30) / P_REF ** 2), 1), peak_db=round(db(env[i]), 1),
                            within_20db_ms=round(float(np.sum(env > 0.1 * env[i])) / fs * 1e3, 2), late_energy_share=round(float(e2[i + int(0.002 * fs):].sum()) / max(tot, 1e-30), 4))
    return out
def windows(x, fs, t0, edges_ms=(0, 2, 8, 30, 200)):
    """exposure level in windows after the blast arrives at t0 (dB), to show where the energy sits in time"""
    out = {}
    for a, b in zip(edges_ms[:-1], edges_ms[1:]):
        seg = x[int((t0 + a * 1e-3) * fs):int((t0 + b * 1e-3) * fs)]
        out['%g-%g ms' % (a, b)] = round(10 * math.log10(max(float(np.sum(seg * seg)) / fs, 1e-30) / P_REF ** 2), 1) if len(seg) else None
    return out
def summary(x, fs, t0=None):
    pk = float(np.max(np.abs(x))); i = int(np.argmax(np.abs(x))); t0 = (i / fs - 0.0003) if t0 is None else t0
    la = sel(x, fs, True)
    e = x * x; i0 = int(max(t0, 0) * fs); first = float(e[i0:i0 + int(0.002 * fs)].sum()) / float(e.sum())
    return dict(first_2ms_energy_share=round(first, 4), peak_db=round(db(pk), 2), a_duration_ms=round(a_duration(x, fs) * 1e3, 3), b_duration_ms=round(b_duration(x, fs) * 1e3, 2), negative_phase=negative_phase(x, fs),
                sel_db=round(sel(x, fs), 2), lae_db=round(la, 2), peak_minus_lae_db=round(db(pk) - la, 2), laeq8_db=round(la - 10 * math.log10(28800), 2),
                spectral_centroid_hz=round(float(np.sum(np.fft.rfftfreq(len(x), 1 / fs) * np.abs(np.fft.rfft(x)) ** 2) / np.sum(np.abs(np.fft.rfft(x)) ** 2))),
                energy_by_time=windows(x, fs, t0), bands=band_envelopes(x, fs))
