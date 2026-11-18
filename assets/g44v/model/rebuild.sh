#!/bin/sh
# rebuild the model from the recipe, then run the checks (writes inventory.json, checks.json; meshes go to work/, ignored)
cd "$(dirname "$0")"
/opt/homebrew/bin/blender -b --python build.py 2>&1 | grep -E "^G44V|Error:|^  File \"/.*build.py"
/opt/homebrew/bin/blender -b work/g44v.blend --python tools/checks.py 2>&1 | grep -E "^(INVENTORY|DIMENSION|MASS|CLIPS|CHECKS)|Error:|^  File \"/.*checks.py" | cut -c1-${COLS:-900}
