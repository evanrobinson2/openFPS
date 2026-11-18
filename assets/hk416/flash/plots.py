"""Plots of the flash simulation (called by sim.py). Simulation data only: nothing here is drawn from a photograph."""
import os, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import physics as ph
from physics import P

def make(out, ctx, outdir):
    os.makedirs(outdir, exist_ok=True)
    shot, bare, cal = ctx['shot'], ctx['bare'], ctx['cal']
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': 0.3, 'figure.dpi': 110})
    t = np.linspace(0, 3e-3, 1501); tm = t * 1e3
    # 1. the drive
    f, ax = plt.subplots(1, 3, figsize=(12, 3.4))
    ax[0].semilogy(tm, shot.p0(t) / 1e6); ax[0].set(title='Bore reservoir pressure (action/)', xlabel='ms after bullet exit', ylabel='MPa')
    ax[1].plot(tm, shot.T0t(t)); ax[1].set(title='Bore reservoir temperature (action/)', xlabel='ms after bullet exit', ylabel='K')
    ax[2].plot(tm, shot.mdot(t), label='mass flow, kg/s'); ax[2].plot(tm, shot.thrust(t) / 1e3, label='gas thrust, kN (action/)')
    ax[2].set(title='Flow out of the muzzle', xlabel='ms after bullet exit'); ax[2].legend()
    f.tight_layout(); f.savefig(os.path.join(outdir, '01_drive.png')); plt.close(f)
    # 2. the jet
    f, ax = plt.subplots(figsize=(7.5, 4))
    tj = np.linspace(1e-6, 1.5e-3, 1500)
    ax.plot(tj * 1e3, shot.x_disk(tj) * 1e3, lw=2, label='Mach disc of the mouth jet')
    ax.plot(tj * 1e3, shot.x_full(tj) * math.sqrt(shot.f_ax) * 1e3, '--', label='its steady position for the pressure at that moment')
    ax.plot(tj * 1e3, bare.x_disk(tj) * 1e3, ':', label='bare muzzle, for comparison')
    ax.plot(tj * 1e3, shot.x_disk(tj, shot.f_slot) * 1e3, label='slot jets (distance along the jet)')
    ax.plot(tj * 1e3, shot.ve * tj * 1e3, 'k', lw=0.7, label='bullet base'); ax.plot(tj * 1e3, shot.x_front(tj) * 1e3, 'gray', lw=0.7, label='gas front')
    ax.set(ylim=(0, 320), xlabel='ms after bullet exit', ylabel='mm from the hider face', title='Under-expanded muzzle jet: where the Mach disc stands'); ax.legend(fontsize=8)
    f.tight_layout(); f.savefig(os.path.join(outdir, '02_jet.png')); plt.close(f)
    # 3. light
    L = out['light']; phs = out['phases']; lt = np.array(L['t_ms'])
    f, ax = plt.subplots(1, 2, figsize=(12, 3.8))
    for k, lab in (('primary', 'primary (lit slots)'), ('intermediate', 'intermediate (behind the Mach disc)')):
        ax[0].semilogy(lt, np.maximum(phs[k]['intensity_cd'], 1e-9), label=lab)
    ax[0].semilogy(lt, np.maximum(np.array(phs['slot_jet']['intensity_cd']) * len(out['hider']['slots']), 1e-9), label='slot jets, all six')
    ax[0].semilogy(lt, np.maximum(L['intensity_cd'], 1e-9), 'k', lw=1.5, label='light source (total, side-on)')
    ax[0].set(xlim=(0, 1.5), ylim=(1e-4, 30), xlabel='ms after bullet exit', ylabel='cd', title='Luminous intensity of an ordinary shot'); ax[0].legend(fontsize=8)
    s = phs['secondary']
    ax[1].plot(s['t_ms'], s['intensity_cd_full'], label='full fireball'); ax[1].plot(s['t_ms'], s['intensity_cd'], label='partial, through the hider (x %.1f)' % s['hider_scale'])
    ax[1].set(xlabel='ms after bullet exit', ylabel='cd', title='Secondary flash, on the %.0f %% of shots that light' % (100 * s['probability'])); ax[1].legend(fontsize=8)
    f.tight_layout(); f.savefig(os.path.join(outdir, '03_light.png')); plt.close(f)
    # 4. temperatures against the published rifle measurements
    f, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(lt, phs['primary']['T_K'], label='model: primary (gas in the cage)'); ax.plot(lt, phs['intermediate']['T_K'], label='model: intermediate (behind the Mach disc)')
    ax.axhline(P('T_secondary'), color='C3', label='model: secondary')
    for y, lab, c in ((1645, 'Klingenberg & Mach 1976: primary 1645 K', 'C0'), (2500, 'secondary about 2500 K', 'C3')): ax.axhline(y, ls=':', color=c, label=lab)
    ax.axhspan(1600, 1940, color='C1', alpha=0.15, label='intermediate 1600 rising to 1940 K')
    ax.set(xlim=(0, 1.5), ylim=(1000, 2700), xlabel='ms after bullet exit', ylabel='K', title='Flash temperatures: this 5.56 mm model and a measured 7.62 mm rifle'); ax.legend(fontsize=7.5, loc='lower left')
    f.tight_layout(); f.savefig(os.path.join(outdir, '04_temperatures.png')); plt.close(f)
    # 5. spectra
    sp = out['spectra']; f, ax = plt.subplots(figsize=(7.5, 3.6))
    for k in ('primary', 'intermediate', 'secondary'): ax.semilogy(sp['wavelength_nm'], np.maximum(sp[k], 1e-12), label=k)
    ax.set(xlabel='nm', ylabel='W m-2 sr-1 nm-1', title='Model spectra (continuum plus Na, K, CaOH and CuOH features)'); ax.legend()
    f.tight_layout(); f.savefig(os.path.join(outdir, '05_spectra.png')); plt.close(f)
    # 6. smoke
    sm = out['smoke']; f, ax = plt.subplots(1, 3, figsize=(12, 3.4))
    for tr in sm['tracks_no_wind']:
        if tr['name'].startswith('slot_') and tr['name'] != 'slot_1': continue
        p = np.array(tr['pos_m']); lab = tr['name'].replace('slot_1', 'slot (one of six)')
        ax[0].loglog(sm['t_s'], np.maximum(np.linalg.norm(p - p[0] * 0 - np.array(next(s_['pos'] for s_ in sm['sources'] if s_['name'] == tr['name'])), axis=1), 1e-4), label=lab)
        ax[1].loglog(sm['t_s'], np.maximum(tr['radius_m'], 1e-4), label=lab); ax[2].loglog(sm['t_s'], np.maximum(tr['tau_centre_whole'], 1e-5), label=lab)
    ax[0].set(title='Distance travelled, m', xlabel='s after bullet exit'); ax[1].set(title='Puff radius, m', xlabel='s after bullet exit')
    ax[2].set(title='Optical depth through the centre', xlabel='s after bullet exit'); ax[0].legend(fontsize=7)
    f.tight_layout(); f.savefig(os.path.join(outdir, '06_smoke.png')); plt.close(f)
    print('plots ->', outdir)
