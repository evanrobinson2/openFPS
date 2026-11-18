#!/bin/sh
# rebuild every variant (LOD0), the figure-livery M18 cans, the matched renders and the comparison numbers
cd "$(dirname "$0")"
B=/opt/homebrew/bin/blender
$B -b --python build.py -- --lod 0 "$@" 2>&1 | grep -E "BUILT|Error|Traceback|  File"
$B -b --python build.py -- --lod 0 --m18-livery figure --only smoke-red,smoke-yellow,smoke-green,smoke-violet 2>&1 | grep -E "BUILT|Error|Traceback|  File"
$B -b --python tools/render.py -- --only frag_figA2,flash_figA12,smoke_violet_figB3,smoke_yellow_figB3,smoke_green_figB3,smoke_red_figB3,smoke_white_figB5 2>&1 | grep -E "Error|Traceback|MISSING|  File"
python3 tools/compare.py
