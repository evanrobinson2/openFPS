#!/bin/sh
# fast iteration: rebuild without textures, dump triangles, run the checks
cd "$(dirname "$0")"
/opt/homebrew/bin/blender -b --python build.py -- --fast 2>&1 | grep -E "^LOD0|Error|Traceback|  File" 
/opt/homebrew/bin/blender -b work/hk416_lod0.blend --python tools/dump_tris.py 2>&1 | grep dumped
/opt/homebrew/bin/blender -b work/hk416_lod0.blend --python tools/checks.py 2>&1 | grep -E "^(INVENTORY|ASSEMBLY|  fasteners|ANIM|EXPORT|Traceback|  File|[A-Za-z]*Error)"
