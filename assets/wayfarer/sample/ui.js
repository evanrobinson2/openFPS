// Controls for the Wayfarer viewer: views, module toggles, cutaway and one slider per mechanism clip.
(function () {
  const NICE = { gear_retract: 'Landing gear up', lift_lower: 'Lift chassis down', lander_bay_open: 'Lander bay open and lower', crew_hatch_open: 'Crew hatch' };
  const el = (t, a, kids) => { const e = document.createElement(t); Object.assign(e, a || {}); (kids || []).forEach(k => e.append(k)); return e; };
  const nice = c => NICE[c] || c.replace(/^door_/, 'Door: ').replace(/_open$/, '').replace(/_/g, ' ');
  function start(opt) {
    const $ = id => document.getElementById(id), status = $('status'), sliders = {};
    WayfarerViewer.start({
      mount: $('stage'), urls: opt.urls, background: opt.background,
      onStatus: (s, f) => { status.textContent = s === 'loading' ? 'Loading the model' + (f ? ' ' + Math.round(f * 100) + '%' : '...') : s === 'none' ? '' : status.textContent; },
      onMissing: () => { $('viewer').style.display = 'none'; $('missing').style.display = 'block'; },
      onTick: api => { for (const c in sliders) sliders[c].value = api.progress(c); },
      onReady: api => {
        status.textContent = api.tris.toLocaleString() + ' triangles, ' + api.clips.length + ' clips.';
        api.views.forEach(v => $('views').append(el('button', { textContent: v, onclick: () => api.view(v) })));
        api.modules.forEach(m => {
          const cb = el('input', { type: 'checkbox', checked: true, onchange: () => api.showModule(m, cb.checked) });
          $('mods').append(el('label', {}, [cb, m.replace('_', ' ')]));
        });
        const fb = el('input', { type: 'checkbox', checked: true, onchange: () => api.showFasteners(fb.checked) });
        $('mods').append(el('label', {}, [fb, 'fasteners']));
        $('cut').oninput = e => api.cutaway(+e.target.value);
        const main = api.clips.filter(c => !c.startsWith('door_')), doors = api.clips.filter(c => c.startsWith('door_'));
        main.concat(doors).forEach(c => {
          const r = el('input', { type: 'range', min: 0, max: 1, step: 0.001, value: 0, oninput: () => api.clipTo(c, +r.value) });
          sliders[c] = r;
          $('clips').append(el('div', { className: 'clip' }, [el('span', { textContent: nice(c) }), r,
            el('button', { textContent: 'Play', onclick: () => api.play(c, 1) }), el('button', { textContent: 'Back', onclick: () => api.play(c, -1) })]));
        });
        if (opt.onReady) opt.onReady(api);
      },
    });
  }
  window.WayfarerUI = { start };
})();
