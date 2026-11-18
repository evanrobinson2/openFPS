"""Shot list shared by render.py (which renders them) and sheet.py (which annotates the orthographic ones).
All positions are in the ship frame (s aft, y starboard, z up). An orthographic shot is defined by the point it is
centred on, the direction it looks along, the image's right and up axes, and the width it covers in metres."""
# name: dict(kind='ortho', centre, right, up, width, aspect, cut=None | distance of the cut plane from the centre along the view)
ORTHO = {
    'port_side':    dict(centre=(15.0, 0.0, -0.6), right=(1, 0, 0), up=(0, 0, 1), width=33.0, aspect=3.0),
    'section_cl':   dict(centre=(15.0, 0.0, -0.6), right=(1, 0, 0), up=(0, 0, 1), width=33.0, aspect=3.0, cut=0.0),
    'top':          dict(centre=(15.0, 0.0, 0.0), right=(1, 0, 0), up=(0, 1, 0), width=33.0, aspect=3.0),
    'plan_main':    dict(centre=(15.0, 0.0, 0.0), right=(1, 0, 0), up=(0, 1, 0), width=33.0, aspect=3.0, cut=1.9),
    'plan_lower':   dict(centre=(15.0, 0.0, 0.0), right=(1, 0, 0), up=(0, 1, 0), width=33.0, aspect=3.0, cut=-0.5),
    'bottom':       dict(centre=(15.0, 0.0, 0.0), right=(1, 0, 0), up=(0, -1, 0), width=33.0, aspect=3.0),
    'front':        dict(centre=(0.0, 0.0, -0.6), right=(0, -1, 0), up=(0, 0, 1), width=11.0, aspect=1.25),
    'rear':         dict(centre=(30.0, 0.0, -0.6), right=(0, 1, 0), up=(0, 0, 1), width=11.0, aspect=1.25),
    'section_lift': dict(centre=(11.4, 0.0, -0.6), right=(0, 1, 0), up=(0, 0, 1), width=11.0, aspect=1.25, cut=0.0),
    'section_bay':  dict(centre=(17.4, 0.0, -0.6), right=(0, 1, 0), up=(0, 0, 1), width=11.0, aspect=1.25, cut=0.0),
}
# perspective: eye, target, lens (mm)
PERSP = {
    'three_quarter': dict(eye=(-13.0, -19.0, 7.5), target=(14.0, 0.0, -0.8), lens=50),
    'three_quarter_low': dict(eye=(-9.0, -15.0, -3.2), target=(13.0, 0.0, -1.2), lens=35),
    'rear_quarter': dict(eye=(41.0, -15.0, 5.0), target=(18.0, 0.0, -0.5), lens=50),
    'cockpit': dict(eye=(4.6, 0.0, 1.50), target=(1.2, 0.0, 0.85), lens=16),
    'pilot_eye': dict(eye=(2.83, -0.72, 1.32), target=(1.2, -0.35, 0.72), lens=14),
    'cockpit_panel': dict(eye=(3.25, 0.0, 1.22), target=(1.95, 0.0, 0.55), lens=20),
    'cockpit_seat': dict(eye=(4.0, 0.25, 1.25), target=(2.85, -0.72, 0.72), lens=22),
    'cockpit_side': dict(eye=(5.6, -1.2, 1.55), target=(2.6, 0.6, 0.7), lens=18),
    'nose': dict(eye=(-7.5, -6.5, 1.8), target=(3.0, 0.0, -0.2), lens=45),
    'engines': dict(eye=(36.0, -11.0, 3.5), target=(25.5, -1.5, 0.2), lens=40),
    'engine_under': dict(eye=(22.6, -6.2, -3.0), target=(26.2, -3.2, -0.9), lens=24),
    'engine_aft': dict(eye=(33.5, -4.5, 1.6), target=(28.6, -1.5, 0.2), lens=30),
    'engine_gap': dict(eye=(27.6, -7.2, 1.9), target=(26.0, -2.6, 0.5), lens=30),
    'intake': dict(eye=(17.5, -9.5, 1.2), target=(25.0, -2.6, 0.2), lens=45),
    'gear': dict(eye=(1.5, -6.5, -3.4), target=(7.5, -1.0, -3.0), lens=30),
    'lander_bay': dict(eye=(13.9, -1.62, -0.55), target=(17.6, 0.2, -1.6), lens=14),
    'under_bay': dict(eye=(24.5, -7.5, -3.9), target=(17.2, 0.0, -3.0), lens=28),
    'crew_deck': dict(eye=(8.5, 0.0, 1.75), target=(12.5, 0.3, 0.9), lens=15),
    'mission_bay': dict(eye=(14.2, 0.2, 1.8), target=(19.5, -0.2, 0.8), lens=15),
    'engineering': dict(eye=(21.5, -0.4, 1.8), target=(24.3, 0.3, 1.0), lens=14),
    'under_lift': dict(eye=(3.2, -6.0, -3.3), target=(10.8, 0.0, -3.6), lens=26),
    'ramp_top': dict(eye=(12.4, -0.35, -2.75), target=(8.6, 0.0, -4.5), lens=16),
    'hold': dict(eye=(13.55, -1.0, -0.75), target=(10.6, 0.3, -1.9), lens=14),
}

def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def project(shot, p, px_w):
    """Ship-frame point -> pixel (x, y) in an orthographic shot rendered px_w wide."""
    c, r, u = shot['centre'], shot['right'], shot['up']
    d = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
    k = px_w / shot['width']; px_h = px_w / shot['aspect']
    return (px_w / 2 + k * (d[0] * r[0] + d[1] * r[1] + d[2] * r[2]), px_h / 2 - k * (d[0] * u[0] + d[1] * u[1] + d[2] * u[2]))
