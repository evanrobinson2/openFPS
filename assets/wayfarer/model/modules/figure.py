"""A 1.80 m player figure for scale. Not part of the ship: it is only added to blockouts and renders."""
from kit import MB, finish

def figure_mb(s, y, z, facing=1, seated=False, m='figure_grey'):
    """Standing (or seated) mannequin with feet (or seat) at z. facing = +1 looks forward (toward the nose)."""
    mb = MB(); f = -facing
    if seated:
        hip = z + 0.12
        mb.capsule((s, y - 0.10, hip), (s + f * 0.42, y - 0.10, hip), 0.075, m); mb.capsule((s, y + 0.10, hip), (s + f * 0.42, y + 0.10, hip), 0.075, m)
        mb.capsule((s + f * 0.42, y - 0.10, hip), (s + f * 0.46, y - 0.10, hip - 0.42), 0.06, m); mb.capsule((s + f * 0.42, y + 0.10, hip), (s + f * 0.46, y + 0.10, hip - 0.42), 0.06, m)
        top = hip + 0.58
    else:
        hip = z + 0.92
        mb.capsule((s, y - 0.10, z + 0.08), (s, y - 0.10, hip), 0.075, m); mb.capsule((s, y + 0.10, z + 0.08), (s, y + 0.10, hip), 0.075, m)
        top = hip + 0.58
    mb.capsule((s, y, hip + 0.06), (s, y, top - 0.10), 0.155, m)                       # torso
    mb.capsule((s, y - 0.22, top - 0.06), (s + f * 0.05, y - 0.25, top - 0.62), 0.05, m)   # arms
    mb.capsule((s, y + 0.22, top - 0.06), (s + f * 0.05, y + 0.25, top - 0.62), 0.05, m)
    mb.sphere((s, y, top + 0.19), 0.11, m, n=12)                                       # head: crown at top + 0.30
    return mb

def add_figure(name, s, y, z, parent, **kw):
    return finish(name, figure_mb(s, y, z, **kw), parent, group='figure')
