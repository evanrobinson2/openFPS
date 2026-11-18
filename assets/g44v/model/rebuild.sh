#!/bin/sh
# rebuild the model from the recipe, then run the checks. Writes inventory.json, checks.json and notes/DECOMPOSITION.md (committed);
# the meshes go to <repo>/build/g44v/ (ignored: meshes are build outputs and never enter git)
cd "$(dirname "$0")"
B=../../../build/g44v
/opt/homebrew/bin/blender -b --python build.py 2>&1 | grep -E "^G44V|Error:|^  File \"/.*build.py"
/opt/homebrew/bin/blender -b $B/g44v.blend --python tools/checks.py 2>&1 | grep -E "^(INVENTORY|DIMENSION|MASS|CLIPS|CHECKS)|Error:|^  File \"/.*checks.py" | cut -c1-${COLS:-900}
python3 tools/make_notes.py
