// Node side of the parity check: synthesise with hk416-sound.js and dump raw float64 for verify_js.py.
import fs from 'node:fs';
import { makeCore } from './hk416-sound.js';
const [, , outDir] = process.argv;
const P = JSON.parse(fs.readFileSync(new URL('params.json', import.meta.url)));
const core = makeCore(P), jobs = JSON.parse(fs.readFileSync(outDir + '/jobs.json')), times = {};
for (const [name, kind, ...args] of jobs) {
  const t = performance.now(); const x = core[kind](...args); times[name] = Math.round(performance.now() - t);
  fs.writeFileSync(`${outDir}/${name}.f64`, Buffer.from(x.buffer, x.byteOffset, x.byteLength));
}
fs.writeFileSync(outDir + '/times.json', JSON.stringify(times));
