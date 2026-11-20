"""Material library. Names are shading roles the game can read. Colours are linear-ish sRGB picks:
the paint is the Army's aircraft green (CARC 34031 class, very dark olive drab, dead flat) [PUB]; the rest are inferred
from what the parts are made of (see USAGE.md)."""
import bpy

#            name                base colour (sRGB 0..1)      metal rough  alpha
LIB = {
    'paint_od':          ((0.150, 0.165, 0.120), 0.0, 0.78, 1.0),   # exterior skin, CARC aircraft green
    'paint_od_interior': ((0.190, 0.205, 0.160), 0.0, 0.70, 1.0),   # door jambs, frames seen from inside
    'paint_black':       ((0.030, 0.031, 0.032), 0.0, 0.62, 1.0),   # blades, anti-glare, instrument panel
    'paint_grey':        ((0.330, 0.345, 0.340), 0.0, 0.62, 1.0),   # cockpit / cabin interior grey
    'paint_yellow':      ((0.780, 0.560, 0.050), 0.0, 0.60, 1.0),   # blade tips, handles, warnings
    'paint_red':         ((0.550, 0.060, 0.040), 0.0, 0.55, 1.0),
    'paint_white':       ((0.800, 0.800, 0.770), 0.0, 0.55, 1.0),
    'glass':             ((0.300, 0.380, 0.360), 0.0, 0.04, 0.22),  # acrylic / laminated transparencies
    'glass_lens':        ((0.850, 0.850, 0.800), 0.0, 0.08, 0.45),
    'lens_red':          ((0.800, 0.050, 0.030), 0.0, 0.10, 0.75),
    'lens_green':        ((0.050, 0.650, 0.250), 0.0, 0.10, 0.75),
    'rubber':            ((0.022, 0.022, 0.024), 0.0, 0.88, 1.0),   # tyres, seals, boots
    'steel':             ((0.420, 0.425, 0.430), 1.0, 0.42, 1.0),   # bolts, pins, oleo pistons
    'steel_dark':        ((0.110, 0.112, 0.118), 1.0, 0.55, 1.0),   # cadmium / phosphate hardware, exhaust
    'chrome':            ((0.780, 0.790, 0.800), 1.0, 0.12, 1.0),   # oleo pistons, servo rods
    'aluminium':         ((0.560, 0.570, 0.580), 1.0, 0.48, 1.0),   # bare structure, seat frames, floor edges
    'alu_dull':          ((0.210, 0.215, 0.220), 1.0, 0.52, 1.0),   # anodised fittings, sills, seat carriers
    'frame_grey':        ((0.085, 0.090, 0.088), 0.0, 0.48, 1.0),   # seat frames, pedal arms, console structure: dark grey enamel
    'titanium':          ((0.360, 0.355, 0.345), 1.0, 0.50, 1.0),   # rotor hub, spindles
    'elastomer':         ((0.080, 0.070, 0.060), 0.0, 0.80, 1.0),   # hub bearings
    'exhaust_dark':      ((0.018, 0.016, 0.015), 0.6, 0.85, 1.0),   # duct interiors, soot
    'fabric_seat':       ((0.230, 0.250, 0.190), 0.0, 0.95, 1.0),   # troop seat nylon
    'fabric_belt':       ((0.300, 0.300, 0.270), 0.0, 0.90, 1.0),
    'quilt':             ((0.250, 0.265, 0.220), 0.0, 0.92, 1.0),   # cabin soundproofing blankets
    'floor':             ((0.090, 0.095, 0.090), 0.0, 0.90, 1.0),   # non-skid cabin floor
    'armor':             ((0.120, 0.125, 0.115), 0.0, 0.70, 1.0),   # crew seat armour buckets
    'panel_face':        ((0.045, 0.047, 0.050), 0.0, 0.92, 1.0),   # instrument and console faces
    'instrument':        ((0.010, 0.010, 0.012), 0.0, 0.20, 1.0),   # gauge dials (texture)
    'placard':           ((0.700, 0.700, 0.650), 0.0, 0.60, 1.0),
    'wire':              ((0.060, 0.060, 0.060), 0.0, 0.70, 1.0),
}


def setup(ctx):
    for name, (col, metal, rough, alpha) in LIB.items():
        m = bpy.data.materials.new(name); m.use_nodes = True
        b = m.node_tree.nodes.get('Principled BSDF')
        b.inputs['Base Color'].default_value = (*[c ** 2.2 for c in col], 1.0)
        b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
        if alpha < 1.0:
            b.inputs['Alpha'].default_value = alpha
            try: m.surface_render_method = 'BLENDED'
            except Exception: m.blend_method = 'BLEND'
        m.use_backface_culling = alpha >= 1.0 and name != 'instrument'
        ctx.mats[name] = m
