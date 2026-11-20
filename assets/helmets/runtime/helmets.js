// openFPS helmets: small runtime helpers for the glTF helmets that model/build.py writes.
// Frame (glTF): metres, +Y up, +Z forward (the face), +X the wearer's left. The origin is the top of the wearer's
// head (inner crown less the crown pad), so a helmet goes on by putting its origin on the head's vertex.
//
//   import { attachHelmet, helmetParts, setStrapsVisible } from './helmets.js';
//   const helmet = (await new GLTFLoader().loadAsync('helmet_us_highcut.glb')).scene;
//   attachHelmet(helmet, headBone, { vertex: new THREE.Vector3(0, 0.11, 0.01) });   // the head's top in bone space
//   helmet.getObjectByName('socket_nvg')    // where a night-vision mount goes; also socket_rail_L / _R

const STRAPS = ['chin_strap', 'nape_strap', 'chin_cup', 'nape_pad', 'ladder_lock'];

export function helmetParts(root) {
  // part name -> meshes. Mesh names are the part names from helmetkit.py (Blender adds .001, .002 ...)
  const out = {};
  root.traverse((o) => {
    if (!o.isMesh) return;
    const k = o.name.replace(/[._]\d+$/, '').replace(/\.\d+$/, '');
    (out[k] ||= []).push(o);
  });
  return out;
}

export function setStrapsVisible(root, on) {
  root.traverse((o) => { if (o.isMesh && STRAPS.some((s) => o.name.startsWith(s))) o.visible = on; });
}

export function attachHelmet(helmet, headBone, { vertex, pitch = 0 } = {}) {
  // put the helmet's origin on the head's vertex (in the bone's space), level with the bone, tilted by `pitch` (rad)
  headBone.add(helmet);
  helmet.position.copy(vertex);
  helmet.rotation.set(pitch, 0, 0);
  return helmet;
}

// published figures each preset was checked against (notes/checks.json)
export const HELMET_FACTS = {
  helmet_us_highcut: { size: 'L', exteriorMm: [266.7, 241.3, 177.8], systemWeightG: 1503, source: 'TM 10-8470-204-10 WP 0002 Table 1' },
  helmet_pmc_highcut: { size: 'L', coverageCm2: 994, shellG: 841, thicknessMm: 7.37, source: 'FAST XP data sheet' },
  helmet_east_midcut: { size: 'L', shellMaxG: 1000, source: '6B47 published weight' },
};
