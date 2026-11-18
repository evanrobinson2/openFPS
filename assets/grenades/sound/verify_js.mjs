// node sound/verify_js.mjs <out.bin> : render every recipe and bounce example with the JS synthesiser, write Float64 samples
import fs from 'fs';
import { render, bounceRecipe } from './grenades-sound.js';
const P = JSON.parse(fs.readFileSync(new URL('./params.json', import.meta.url)));
const chunks = [], index = {};
let off = 0;
const put = (name, arr) => { index[name] = [off, arr.length]; chunks.push(Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength)); off += arr.length; };
for (const [name, rec] of Object.entries(P.recipes)) put(name, render(rec, P.sample_rate));
for (const key of Object.keys(P.bounce_examples)) { const [b, s, v] = key.split('|'); put('bounce:' + key, render(bounceRecipe(P, b, s, +v), P.sample_rate)); }
fs.writeFileSync(process.argv[2], Buffer.concat(chunks)); fs.writeFileSync(process.argv[2] + '.json', JSON.stringify(index));
