// 'realistic' must be the physical sound exactly as it was before cinematic mode existed. This renders the same jobs through
// (a) the modules of the merged commit aa037ac, unpacked by `git archive aa037ac assets/*/sound | tar -x -C audio/_base` (ignored by git), and
// (b) the current modules with mode 'realistic', both in OfflineAudioContext, and compares every sample. Credit: carpetshark.
const FS = 48000;
async function run(build, dur) { const off = new OfflineAudioContext(2, Math.ceil(dur * FS), FS); await build(off); const b = await off.startRendering(); return [b.getChannelData(0), b.getChannelData(1)]; }
function diff(a, b) { let d = 0, p = 0; for (let c = 0; c < 2; c++) for (let i = 0; i < a[c].length; i++) { d = Math.max(d, Math.abs(a[c][i] - b[c][i])); p = Math.max(p, Math.abs(a[c][i])); } return { samples: a[0].length, peak: +p.toFixed(6), max_abs_difference: d, identical: d === 0 && p > 0 }; }
export default async function identity(guns, render, say) {
  const out = {}, dummy = new OfflineAudioContext(1, 1, FS), B = './audio/_base/assets/';
  if (guns.hk416) { say('identity hk416');
    const Old = (await import(B + 'hk416/sound/hk416-sound.js')).default, So = await Old.build(dummy), Sn = guns.hk416.S; out.hk416 = {};
    for (const [nm, variant, o] of [['single_range_berm', 'single', { overlay: 'range_berm' }], ['single_default', 'single', {}], ['auto1s_hallway_earmuffs', 'auto1s', { overlay: 'hallway', hpd: true }], ['single_dry_no_ear', 'single', { overlay: null, ear: false }], ['bystander_open_field_ground', 'single', { overlay: 'open_field', perspective: 'bystander' }]]) {
      const so = { perspective: o.perspective || 'shooter', ground: nm.includes('ground') };
      const a = await run(async (off) => { const c = await So.chain(o, off); c.output.connect(off.destination); const s = off.createBufferSource(); s.buffer = So.shot(variant, so); s.connect(c.input); s.start(0.02); }, 4);
      const b = await run(async (off) => { const c = await Sn.chain(Object.assign({ mode: 'realistic' }, o), off); c.output.connect(off.destination); const s = off.createBufferSource(); s.buffer = Sn.shot(variant, Object.assign({ mode: 'realistic' }, so)); s.connect(c.input); s.start(0.02); }, 4);
      out.hk416[nm] = diff(a, b);
    }
    { const a = await run(async (off) => { const c = await So.chain({ overlay: 'indoor_range' }, off); c.output.connect(off.destination); const s = off.createBufferSource(); s.buffer = So.mech('charge'); s.connect(c.input); s.start(0.02); }, 2);
      const b = await run(async (off) => { const c = await Sn.chain({ overlay: 'indoor_range', mode: 'realistic' }, off); c.output.connect(off.destination); await c.mech('charge', { when: 0.02 }); }, 2); out.hk416.mech_charge_via_chain_mech = diff(a, b); }
    { const a = await run(async (off) => { const c = await So.chain({ overlay: 'range_berm' }, off); c.output.connect(off.destination); const s = off.createBufferSource(); s.buffer = So.shot('single'); s.connect(c.input); s.start(0.02); }, 3);
      const b = await run(async (off) => { const c = await Sn.chain({ overlay: 'range_berm', mode: 'realistic' }, off); c.output.connect(off.destination); await c.fire({ when: 0.02 }); }, 3); out.hk416.single_via_chain_fire = diff(a, b); }
  }
  if (guns.g44v) { say('identity g44v');
    const Old = (await import(B + 'g44v/sound/g44v-sound.js')).default, Sn = guns.g44v.S; out.g44v = {};
    for (const [nm, load, o, so] of [['standard_indoor', 'cci_standard_velocity', { overlay: 'indoor_range', hpd: false, ear: true }, {}], ['minimag_open_air_ground', 'cci_mini_mag', { overlay: null }, { ground: true }], ['quiet_berm_earmuffs', 'cci_quiet_22', { overlay: 'outdoor_berm', hpd: true }, {}], ['bystander_no_ear', 'cci_standard_velocity', { overlay: null, ear: false }, { perspective: 'bystander' }]]) {
      // the old chain() builds its nodes on the context given to build(), so the old module is built on the offline context itself
      const a = await run(async (off) => { const So = await Old.build(off), c = So.chain(o); c.output.connect(off.destination); const s = off.createBufferSource(); s.buffer = So.shot(load, so); s.connect(c.input); s.start(0.02); }, 1.5);
      const b = await run(async (off) => { const c = await Sn.chain(Object.assign({ mode: 'realistic' }, o), off); c.output.connect(off.destination); const s = off.createBufferSource(); s.buffer = Sn.shot(load, Object.assign({ mode: 'realistic' }, so)); s.connect(c.input); s.start(0.02); }, 1.5);
      out.g44v[nm] = diff(a, b);
    }
    { const a = await run(async (off) => { const So = await Old.build(off), c = So.chain({ overlay: 'indoor_range' }); c.output.connect(off.destination); const s = off.createBufferSource(); s.buffer = So.mech('slide_rack'); s.connect(c.input); s.start(0.02); }, 1.5);
      const b = await run(async (off) => { const c = await Sn.chain({ overlay: 'indoor_range', mode: 'realistic' }, off); c.output.connect(off.destination); await c.mech('slide_rack', { when: 0.02 }); }, 1.5); out.g44v.slide_rack_via_chain_mech = diff(a, b); }
  }
  if (guns['shotgun-590']) { say('identity shotgun-590');
    // the old module is a classic script that sets window.Shotgun590Sound: load it in a frame so that it does not replace the current one
    const fr = document.createElement('iframe'); fr.style.display = 'none'; document.body.appendChild(fr);
    await new Promise((res, rej) => { const el = fr.contentDocument.createElement('script'); el.src = new URL(B + 'shotgun-590/sound/shotgun590-sound.js', import.meta.url).href; el.onload = res; el.onerror = rej; fr.contentDocument.head.appendChild(el); });
    const So = fr.contentWindow.Shotgun590Sound, Sn = window.Shotgun590Sound; await So.load(new URL(B + 'shotgun-590/sound/params.json', import.meta.url).href); out['shotgun-590'] = {};
    for (const [name, opts] of [['shot_buck00_shooter', { normalize: true }], ['shot_slug_bystander_room', { normalize: true }], ['shot_buck00_range_front_50m', {}], ['pump', { normalize: true, gain: 0.5 }], ['shell_insert', {}]]) {
      const a = await run(async (off) => { So.play(off, name, Object.assign({ when: 0.02 }, opts)); }, 2.2);
      const b = await run(async (off) => { Sn.play(off, name, Object.assign({ when: 0.02, mode: 'realistic' }, opts)); }, 2.2);
      out['shotgun-590']['play_' + name] = diff(a, b);
    }
    { const a = await run(async (off) => { So.play(off, 'shot_buck00_shooter', { when: 0.02, normalize: true }); }, 2.2);
      const b = await run(async (off) => { const c = await guns['shotgun-590'].S.chain({ mode: 'realistic', overlay: 'range' }, off); c.output.connect(off.destination); await c.fire({ key: 'buck00', when: 0.02 }); }, 2.2); out['shotgun-590'].buck00_range_via_chain_fire = diff(a, b); }
    const names = So.names(); let worst = 0; for (const n of names) { const x = So.render(n), y = Sn.render(n); if (x.length !== y.length) worst = Infinity; else for (let i = 0; i < x.length; i++) worst = Math.max(worst, Math.abs(x[i] - y[i])); }
    out['shotgun-590'].render_all_names = { sounds: names.length, max_abs_difference_pa: worst, identical: worst === 0 };
    fr.remove();
  }
  out.all_identical = Object.values(out).every((g) => Object.values(g).every((r) => r.identical));
  return out;
}
