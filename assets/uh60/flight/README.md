# UH-60 flight model

`uh60-flight.js` (browser and node, no dependencies). Usage, check results and limits are in `../USAGE.md`.

Where each constant comes from is in the `P` table at the top of the file: TM = TM 1-1520-237-10, PUB = a published
figure (NASA CR-166309 and the type's data sheets), INF = inferred. Four numbers are fitted, not sourced, so that the
manual's worked torque examples come out: profile drag `cd0` and `cd2`, induced-power factor `kInd`, and fuselage
flat-plate area `fx`; the engine lapse exponent is set so the manual's 94 percent hover example is achievable.

    node verify.mjs      # writes flight.json, exits 1 if a case is outside tolerance
