# openFPS

Simulation-grade first-person assets, built in code. Each asset is a simulation of the real thing (mechanism,
recoil, ballistics, sound) with its geometry as a parametric recipe in code, not a mesh file, and its sound synthesised at
runtime, not recorded.

Read [MODELING_RULES.md](MODELING_RULES.md) before adding anything. In short: simulation-grade; no mesh files; no
audio files; every asset ships `USAGE.md`, a sample page and `provenance.json`; modelling by a 2026 frontier model.

## Assets

| Asset | What | Sample |
|---|---|---|
| [HK416 D14.5RS](assets/hk416/USAGE.md) | 5.56 mm rifle: action and recoil, ballistics (M855, Mk 262, M856), synthesised sound with ten surroundings and earmuffs. Parametric geometry recipe: 301 named parts, 13 clips, 7 sockets. | [`assets/hk416/sample/`](assets/hk416/sample/index.html) |
| [Pump shotgun 590](assets/shotgun-590/USAGE.md) | 12 gauge pump action: pump cycle and controls from the owner's manual, recoil, ballistics (00 buck, rifled slug), synthesised sound. Parametric geometry recipe: 40 named parts, 10 clips, 14 sockets. | [`assets/shotgun-590/sample/`](assets/shotgun-590/sample/index.html) |

## Try it

```
python3 -m http.server 8790
# open http://127.0.0.1:8790/assets/hk416/sample/
```

## Check the rules

```
python3 tools/check_assets.py
```

CI runs the same check on every push.

## Licence

Free for noncommercial use; commercial use needs a licence from carpetshark. Code is under
[PolyForm Noncommercial 1.0.0](LICENSE.md) and documentation under [CC BY-NC 4.0](LICENSE-DOCS.txt). See
[COMMERCIAL.md](COMMERCIAL.md) for what counts as commercial and how to ask for a licence.

## Credits

By carpetshark. Modelling and simulation by Claude (see each asset's `provenance.json`).
Product names are trademarks of their owners; openFPS is not affiliated with any manufacturer.
