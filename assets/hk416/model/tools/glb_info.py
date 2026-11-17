"""python3 tools/glb_info.py file.glb : animations, rest pose of the moving parts, images, sizes."""
import json, struct, sys
d = open(sys.argv[1], 'rb').read(); n = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + n])
print('bytes', len(d), 'nodes', len(j['nodes']), 'meshes', len(j.get('meshes', [])), 'materials', [m['name'] for m in j.get('materials', [])])
print('images', [(i.get('name'), i.get('mimeType')) for i in j.get('images', [])])
print('animations', [(a['name'], len(a['channels'])) for a in j.get('animations', [])])
for nd in j['nodes']:
    if nd['name'] in ('mag_body', 'stock_body', 'front_sight_arm', 'dust_cover', 'charging_handle'): print(' ', nd['name'], nd.get('translation'), nd.get('rotation'))
