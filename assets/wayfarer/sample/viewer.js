// Wayfarer viewer. Needs THREE (r146), THREE.GLTFLoader, THREE.OrbitControls and THREE.RoomEnvironment on the page.
// WayfarerViewer.start({ mount, urls:[...], onStatus, onReady }) loads the first URL that answers.
// Ship frame: s = metres aft of the nose, y = starboard, z = up from the barrel axis.
// glTF frame: x = -y, y = z, z = 15 - s.
(function () {
  const MODULES = ['fuselage', 'cockpit', 'engines', 'landing_gear', 'lift_chassis', 'lander_bay', 'gadgets', 'interior'];
  const ship = (s, y, z) => new THREE.Vector3(-y, z, 15 - s);
  const VIEWS = {
    'Port bow': { eye: ship(-9, -14, 6), at: ship(13, 0, -0.6) },
    'Side': { eye: ship(15, -27, 0), at: ship(15, 0, -0.5) },
    'Engines': { eye: ship(41, -12, 5), at: ship(24, 0, 0) },
    'Under the lift': { eye: ship(2.5, -5.5, -3.9), at: ship(11.4, 0, -3.4) },
    'Under the bay': { eye: ship(27, -6.5, -4.0), at: ship(17.4, 0, -3.2) },
    'Cockpit': { eye: ship(5.6, 0, 1.75), at: ship(1.5, 0, 1.1), inside: true },
    'Crew deck': { eye: ship(8.5, 0, 1.75), at: ship(13.5, 0, 1.2), inside: true },
    'Hold': { eye: ship(9.1, 0.9, -0.7), at: ship(12.5, -0.3, -1.6), inside: true },
    'Lander bay': { eye: ship(14.5, 1.9, -0.6), at: ship(18.5, 0, -1.6), inside: true },
    'Engineering': { eye: ship(21.6, 0, 1.75), at: ship(24.4, 0, 1.0), inside: true },
  };

  function start(opt) {
    const mount = opt.mount, say = opt.onStatus || (() => {});
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.8;
    mount.appendChild(renderer.domElement);
    const scene = new THREE.Scene(); scene.background = new THREE.Color(opt.background || 0x15181c);
    const pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
    const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-20, 30, 25); scene.add(sun);
    const inside = new THREE.PointLight(0xfff1dd, 0.0, 14); scene.add(inside);
    const camera = new THREE.PerspectiveCamera(45, 1, 0.05, 400);
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.1;
    const cut = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 100);     // keeps x < constant : cuts the port side away
    renderer.clippingPlanes = [cut];
    const api = { modules: MODULES, views: Object.keys(VIEWS), clips: [], scene, camera, controls };
    let mixer = null, actions = {}, root = null, dirty = true;
    const clock = new THREE.Clock();

    function size() {
      const w = mount.clientWidth, h = mount.clientHeight || Math.round(w * 0.6);
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); dirty = true;
    }
    new ResizeObserver(size).observe(mount); size();
    controls.addEventListener('change', () => { dirty = true; });

    api.view = function (name) {
      const v = VIEWS[name]; if (!v) return;
      camera.position.copy(v.eye); controls.target.copy(v.at);
      camera.fov = v.inside ? 70 : 40; camera.near = v.inside ? 0.05 : 0.5; camera.updateProjectionMatrix();
      inside.intensity = v.inside ? 1.2 : 0; inside.position.copy(v.eye);
      controls.update(); dirty = true;
    };
    api.showModule = function (name, on) { const o = root && root.getObjectByName(name); if (o) o.visible = on; dirty = true; };
    api.showFasteners = function (on) { if (root) root.traverse(o => { if (/_bolts$/.test(o.name)) o.visible = on; }); dirty = true; };
    api.cutaway = function (t) { cut.constant = t <= 0 ? 100 : 4.6 - 4.6 * t; dirty = true; };   // t 0..1 : off .. centreline
    api.clipTo = function (name, t) {                                    // t 0..1 along the clip
      const a = actions[name]; if (!a) return;
      a.paused = true; a.time = t * a.getClip().duration; mixer.update(0); dirty = true;
    };
    api.play = function (name, dir) {
      const a = actions[name]; if (!a) return;
      a.paused = false; a.timeScale = dir; if (dir > 0 && a.time >= a.getClip().duration) a.time = 0;
      if (dir < 0 && a.time <= 0) a.time = a.getClip().duration;
    };
    api.progress = name => { const a = actions[name]; return a ? a.time / a.getClip().duration : 0; };

    function loop() {
      requestAnimationFrame(loop);
      const dt = clock.getDelta();
      if (mixer) {
        let moving = false;
        for (const k in actions) { const a = actions[k]; if (!a.paused && a.timeScale) moving = true; }
        if (moving) {
          mixer.update(dt); dirty = true;
          for (const k in actions) {
            const a = actions[k], d = a.getClip().duration;
            if (a.timeScale < 0 && a.time <= 0) { a.time = 0; a.paused = true; }
            if (a.timeScale > 0 && a.time >= d) { a.time = d; a.paused = true; }
          }
          if (opt.onTick) opt.onTick(api);
        }
      }
      if (controls.update() || dirty) { renderer.render(scene, camera); dirty = false; }
    }

    function load(i) {
      if (i >= opt.urls.length) { say('none'); if (opt.onMissing) opt.onMissing(); return; }
      say('loading');
      new THREE.GLTFLoader().load(opt.urls[i], g => {
        root = g.scene; scene.add(root);
        root.traverse(o => { if (o.isMesh && o.material) { o.material.envMapIntensity = 0.55; if (o.material.transparent) o.renderOrder = 2; } });
        mixer = new THREE.AnimationMixer(root);
        for (const c of g.animations) {
          const a = mixer.clipAction(c); a.setLoop(THREE.LoopOnce); a.clampWhenFinished = true; a.play(); a.paused = true; a.time = 0;
          actions[c.name] = a;
        }
        mixer.update(0);
        api.clips = g.animations.map(c => c.name).sort();
        let tris = 0; root.traverse(o => { if (o.isMesh) tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3; });
        api.tris = Math.round(tris);
        api.view('Port bow'); say('ready'); if (opt.onReady) opt.onReady(api); loop();
      }, e => { if (e.total) say('loading', e.loaded / e.total); }, () => load(i + 1));
    }
    load(0);
    return api;
  }
  window.WayfarerViewer = { start, MODULES, VIEWS };
})();
