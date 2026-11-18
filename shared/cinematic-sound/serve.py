#!/usr/bin/env python3
"""Serve the repository for the sample pages and the cinematic acceptance page, and accept the page's rendered WAVs.

    python3 shared/cinematic-sound/serve.py [port]        (default 8781)
    open http://127.0.0.1:8781/shared/cinematic-sound/measure.html?save=1

POST /save/<name>.wav writes into shared/cinematic-sound/audio/, which git ignores (rule 3: no audio file enters git).
POST /results writes compare/results.json (numbers only). Binds to 127.0.0.1 only. Credit: carpetshark.
"""
import http.server, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        m = re.fullmatch(r'/save/([A-Za-z0-9_.-]+\.wav)', self.path)
        if m: dest = os.path.join(HERE, 'audio', m.group(1))
        elif self.path == '/results': dest = os.path.join(HERE, 'compare', 'results.json')
        else: self.send_error(404); return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'wb').write(body)
        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
    def log_message(self, *a): pass

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8781
    http.server.ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
