"""Check built helmets against published numbers. Run after build.py; writes ../notes/checks.json.

    python3 check.py

Each check names its source (see ../notes/SOURCES.md). Pass bands are the publisher's tolerance where one is given
(Gentex: +/-3 %), otherwise stated in the check.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
IN = 25.4

# densities of the shell materials (g/cm3): inference from the fibre and matrix, see SOURCES.md
DENSITY = {'helmet_us_highcut': 1.30, 'helmet_pmc_highcut': 1.10, 'helmet_east_midcut': 1.25}


def load(i):
    p = os.path.join(HERE, 'work', i + '.stats.json')
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    presets = {p['id']: p for p in json.load(open(os.path.join(HERE, 'presets.json')))['presets']}
    out = []

    def check(name, value, target, lo, hi, source, unit=''):
        ok = lo <= value <= hi
        out.append({'check': name, 'value': round(value, 2), 'target': target, 'pass_band': [round(lo, 2), round(hi, 2)],
                    'unit': unit, 'pass': ok, 'source': source})

    us = load('helmet_us_highcut')
    if us:
        e = us['exterior_mm']
        for k, v in (('length', 10.5), ('width', 9.5), ('height', 7.0)):
            check(f'US shell exterior {k} = ACH size L maximum', e[k], v * IN, v * IN - 2, v * IN + 0.5,
                  'TM 10-8470-204-10 (2008) WP 0002 Table 1, Large: 10.5 x 9.5 x 7.0 in', 'mm')
        sh = presets['helmet_us_highcut']['shell']
        inner_len = e['length'] - 2 * sh['thickness'] - 2 * sh['crown_standoff']
        check('US inner length less two 3/4 in pads fits the largest L head (8 1/4 in)', inner_len, 8.25 * IN,
              8.25 * IN, 8.25 * IN + 15, 'TM 10-8470-204-10 WP 0004 Table 1 (L head length 7 3/4 to 8 1/4 in); pads 3/4 in', 'mm')
        m = us['shell_volume_cm3'] * DENSITY['helmet_us_highcut']
        check('US bare shell mass plausible under the 53 oz system weight (shell + retention + pads)', m, 53 * 28.35,
              0.6 * 53 * 28.35, 0.85 * 53 * 28.35, 'TM 10-8470-204-10 WP 0002 Table 1 (L: 53 oz with retention and suspension)', 'g')
    pmc = load('helmet_pmc_highcut')
    if pmc:
        a = pmc['shell_outer_area_cm2']
        check('Contractor shell coverage = FAST XP high cut, size L', a, 994, 994 * 0.97, 994 * 1.03,
              'Ops-Core FAST XP data sheet (REV.20251203): L high cut 154 in2 / 994 cm2, +/-3 %', 'cm2')
        m = pmc['shell_volume_cm3'] * DENSITY['helmet_pmc_highcut']
        check('Contractor shell mass = FAST XP high cut L (841 g with paint and edge band)', m, 841, 841 * 0.9, 841 * 1.1,
              'Ops-Core FAST XP data sheet: shell 841 g (L, high cut), 7.37 mm thick', 'g')
    east = load('helmet_east_midcut')
    if east:
        m = east['shell_volume_cm3'] * DENSITY['helmet_east_midcut']
        check('Eastern shell mass within the published "no more than 1 kg"', m, 1000, 700, 1000,
              '6B47 published weight <= 1 kg (Armokom via Wikipedia "6B47 helmet"; Army Recognition, 23 Aug 2014)', 'g')
    path = os.path.join(HERE, '..', 'notes', 'checks.json')
    json.dump(out, open(path, 'w'), indent=1)
    for c in out:
        print(('PASS ' if c['pass'] else 'FAIL ') + c['check'], c['value'], c['unit'], 'band', c['pass_band'])


if __name__ == '__main__':
    main()
