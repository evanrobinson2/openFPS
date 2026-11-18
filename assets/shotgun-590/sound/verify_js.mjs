// node sound/verify_js.mjs <outdir> : renders every sound with shotgun590-sound.js and writes raw float64 files (used by verify_js.py)
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';
const require = createRequire(import.meta.url), here = path.dirname(fileURLToPath(import.meta.url)), out = process.argv[2];
const S = require('./shotgun590-sound.js'); S.use(JSON.parse(fs.readFileSync(path.join(here, 'params.json'), 'utf8')));
const times = {};
for (const name of S.names()) { const t = Date.now(); const y = S.render(name); times[name] = Date.now() - t; fs.writeFileSync(path.join(out, name + '.f64'), Buffer.from(y.buffer)); }
fs.writeFileSync(path.join(out, 'times.json'), JSON.stringify(times));
