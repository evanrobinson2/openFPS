#!/bin/sh
# rebuild the model, render the matched view, compare it with the reference photo
cd "$(dirname "$0")/.."
B=/opt/homebrew/bin/blender
$B -b --python model/build.py 2>&1 | grep -E "BUILT|Error|Traceback|  File|assert"
$B -b model/masters/shotgun590.blend --python model/tools/render.py -- --only match_right,match_right_alpha --samples 16 2>&1 | grep -E "Error|Traceback|  File"
python3 model/tools/compare.py "$@"
