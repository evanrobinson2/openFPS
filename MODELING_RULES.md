# openFPS modeling rules

These rules are strict. An asset that breaks one does not go into `assets/`. `tools/check_assets.py` checks the
mechanical ones; review covers the rest.

## 1. Simulation-grade, not lookalike
- Every asset is a simulation of the real thing, not a picture of it. A rifle has a firing train, an operating
  cycle, recoil, ballistics and sound derived from physics and published numbers. An optic has an eye box,
  parallax and a reticle that agrees with the ballistics. A muzzle device changes gas flow, sound and flash.
- Every number carries its source: a manual page, a published figure (named), a measurement (of what, and how),
  or an inference (stated as one). Guesses are labelled as guesses.
- Each simulation ships a check against something real: published data, a measured reference, or a parity test
  between its implementations. Results are committed (`*.json`, plots), and limits are written down.

## 2. Geometry is a parametric recipe, never a mesh file
- A model is code: a parametric description (for example a Python or Blender Python script) that builds named parts
  from measured numbers, with a kinematic hierarchy, sockets and clips. Rebuilding from the recipe gives the model.
- No `.glb`, `.gltf`, `.fbx`, `.obj`, `.blend` or other baked mesh in git (`.gitignore` blocks them). Meshes are
  build outputs: make them locally or in a build step, never commit them.
- Parts and materials are named by what they are. No maker's names or logos: use plain placeholder panels.

## 3. Sound is a simulation, never a recording
- No audio files in git: no `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a` or `.aac`, and nothing cut, sampled, filtered
  or learned from a recording.
- Sound is synthesised at runtime from the asset's simulation (source physics, propagation, room, hearing
  protection). Recordings may be used locally as measurement references only; they stay in `refs-local/`
  (ignored), and only numbers and simulation-only plots are committed.

## 4. Every asset documents itself and ships a sample
Each `assets/<id>/` folder contains:

| File | What it is |
|---|---|
| `USAGE.md` | How to use the asset: what it is, files, how to load it, the runtime API, the frame and units, how to rebuild, limits. |
| `sample/index.html` | A sample artifact: one self-contained page that loads the asset's runtime modules and shows them working. |
| `provenance.json` | Who made it and with which model (rule 5), plus its status. |
| Simulation folders | Source (`sim.py` or equivalent), derived tables (`*.json`), the browser runtime (`*.js`), checks and a README each. |

## 5. Made by a 2026 frontier model
- The modelling (geometry recipes and simulations) is done by a 2026 frontier model at or above the level of
  Claude Fable 5.2 or Astra 6.2.
- This is made evident rather than strictly enforced: `provenance.json` lists the model for each part in
  `modelled_by`, and commits carry a `Co-Authored-By` trailer naming it. `tools/check_assets.py` warns (it does not
  fail) when `modelled_by` is missing or names a model it doesn't recognise as frontier-level. Add new frontier
  models to `FRONTIER_MODELS` in that script.

## 6. References and copyright
- Reference images, manuals and recordings are cited, never committed, unless their licence allows it and the
  licence is recorded next to the file. Keep local copies in `refs-local/` (ignored).
- Summaries of facts from a manual are fine, with page numbers. Long quotations and page images are not.
- Credit is "carpetshark" only.

## 7. Change requests make a new version
Record each change request and what changed in the asset's notes. Never silently replace history.
