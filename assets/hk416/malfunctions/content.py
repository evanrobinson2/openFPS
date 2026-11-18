"""Authored content for the HK416 malfunction simulation: sources, what each stoppage is, what the shooter
perceives, how it shows on the model, and how it is cleared. Numbers and the model live in sim.py.

Everything here is range safety and education: recognising a stoppage and making the rifle safe. Nothing here is
about defeating a safety device or altering a weapon.

Source tags: manual = HK maintenance manual (page given); published = a named publication; doctrine = a published
procedure; action = the sibling action simulation (../action/action.json); inferred = an engineering estimate;
guess = a number with no data behind it; calibrated = solved by sim.py so that a published or inferred figure is
reproduced."""

SOURCES = [
    dict(id='hk_manual', kind='manual',
         title='Heckler & Koch USA, Maintenance Manual for HK416 Enhanced Carbine & Rifle System, 5.56 mm NATO (54 pages). Not in this repository; facts summarised with page numbers',
         used_for='clearing steps (p. 3); bore free of obstructions, factory-loaded undamaged cartridges only, cooling after 250 rounds in under 3 minutes (p. 4); HK steel '
                  'magazines against aluminium ones (pp. 5, 6); no propellant gas in the receiver, longer interval between stoppages (p. 6); what the extractor, ejector and '
                  'firing pin do, and that the pin reaches the primer only with the bolt fully locked (p. 7); do not ride the charging handle (p. 8); cycle of operation '
                  '(pp. 8 to 12); firing pin protrusion 0.90 to 1.10 mm and extractor claw gauges 1.28 / 1.59 mm (pp. 17, 21, 23, 24); function check, forward assist as a '
                  'symptom check, last-round hold-open, no reloads (p. 26); ejector and piston rings (p. 27); magazine catch tension (p. 37). The manual has no stoppage drill'),
    dict(id='edt3', kind='published',
         title='US Army PEO Soldier, "M4 Carbine Extreme Dust Test" briefing, v3.5 (Aberdeen Test Center, fall 2007 test, briefed December 2007), slides 2 to 12',
         url='https://www.slideshare.net/slideshow/m4-carbine-extreme-dust-test-brief-v350/15832677',
         used_for='the only published HK416 stoppage counts by type: 10 rifles x 6,000 rounds, 25 h of dusting per rifle, 120-round cycles, wipe and lubricate every 600 rounds, '
                  'full clean every 1,200. HK416 class 1 and 2 weapon stoppages 210 (failure to feed 141, to chamber 7, to fire 5, to extract 3, to eject 49, bolt locked to '
                  'the rear 0, bolt failed to lock to the rear 3, other 2), magazine stoppages 9, class 3 stoppages 14. M4 magazine stoppages 148 (summer) and 239 (fall). '
                  'Read through a text rendering of the slides, not the original file'),
    dict(id='army_edt_article', kind='published',
         title='US Army, "M-4 Carbine Has High Soldier Confidence Despite Test" (army.mil, 18 December 2007)',
         url='https://www.army.mil/article/6649/m_4_carbine_has_high_soldier_confidence_despite_test',
         used_for='the dust test protocol and the stoppage classes: class 1 cleared by the shooter within 10 s, class 2 cleared by the shooter in more than 10 s, class 3 needs an armourer'),
    dict(id='crs_rs22888', kind='published',
         title='Congressional Research Service RS22888, "The Army\'s M-4 Carbine: Background and Issues for Congress" (2008)',
         url='https://www.everycrsreport.com/files/20080530_RS22888_03edaa907691c2e89542641b3279702c8bd8e5d3.html',
         used_for='dust test totals (XM8 127, SCAR 226, HK416 233, M4 882); Army laboratory test October 2005 to April 2006: 10 new M16s and 10 new M4s averaged about 5,000 '
                  'rounds between stoppages; USMC 2002: M4 186 failures in 69,000 rounds'),
    dict(id='mrbs_figures', kind='published',
         title='M4 mean rounds between stoppage figures as reported by Military.com (14 June 2013) and summarised in Wikipedia, "Individual Carbine" and "M4 carbine"',
         url='https://en.wikipedia.org/wiki/Individual_Carbine',
         used_for='600 MRBS required of the M4 in 1990 (M855); 1,691 MRBS for the M4A1 with M855A1 (2013); 3,592 required by the Individual Carbine competition. Context for the '
                  'clean baseline; read from the secondary summary, not the Army documents'),
    dict(id='mil_c_63989c', kind='published',
         title='MIL-C-63989C(AR), Military Specification: Cartridge, 5.56 mm, Ball, M855 (superseded revision, public on everyspec.com)',
         url='https://everyspec.com/MIL-SPECS/MIL-SPECS-MIL-C/MIL-C-63989C_37913/',
         used_for='lot acceptance, Table III and Table IV: 800 rounds per weapon type in the function and casualty test; first sample accepted with at most 1 misfire, rejected '
                  'at 3; a bullet remaining in the bore rejects the lot; failure to extract and weapon stoppage accepted at 0, rejected at 2. Action time (primer ignition '
                  'to the bullet passing the gas port): mean plus five standard deviations at most 3 ms (3.15). Port pressure mean minus three standard deviations at least '
                  '12,700 psi (3.8), within 2,000 psi of that at -65 and +125 F (3.10.3). Velocity 3,000 +/- 40 ft/s, standard deviation at most 40 ft/s (3.6)'),
    dict(id='tc_3_22_9', kind='doctrine',
         title='US Army TC 3-22.9, Rifle and Carbine (May 2016), chapter 8: immediate action (para 8-35) and remedial action (para 8-36)',
         url='https://irp.fas.org/doddir/army/tc3-22-9.pdf',
         used_for='the clearing sequences: tap, rack, reassess; remedial action when immediate action has failed twice or the trigger will not press or feels soft; the stove '
                  'pipe, double feed and bolt override procedures. Step order and paragraph numbers were read from a secondary summary (highgroundshooter.com, 14 February '
                  '2022) because the publication itself could not be opened in this session; check them against the TC before quoting'),
    dict(id='range_practice', kind='doctrine',
         title='Standard range practice for a misfire and for a weak shot (hunter-education courses and firearm manuals)',
         url='https://www.hunter-ed.com/iowa/studyGuide/Beware-of-Hang-Fires/202013_12894',
         used_for='keep the muzzle on the backstop and wait before opening the action after a misfire (30 s is used here; some ranges say 60); after a pop or weak shot, stop, '
                  'unload and prove the bore clear before firing again. Recalled, not quoted'),
    dict(id='action_sim', kind='action',
         title='HK416 action simulation, ../action/action.json (built by ../action/sim.py)',
         used_for='carrier kinetic energy against travel, the times the carrier passes each position, 95 mm stroke, eject / feed pick-up / hold-open positions, hammer energy '
                  '0.48 J, the primer cup model, chamber pressure when extraction starts, ejection speed, masses'),
    dict(id='primer_sensitivity', kind='guess',
         title='US military small rifle primer sensitivity (No. 41): 3.94 oz ball, all-fire 12 in',
         used_for='the all-fire energy 0.334 J. Recalled from the commonly quoted figure; not confirmed against the primer specification in this session'),
]

# What the briefing's categories are taken to mean in this simulation (the briefing does not define them further).
EDT_MAP = dict(
    FFD=['failure_to_feed:nose_jam', 'failure_to_feed:bolt_over_empty_chamber', 'bolt_override', 'double_feed:two_live'],
    FTC=['failure_to_feed:failure_to_chamber'],
    FFR=['failure_to_fire', 'hangfire (a perceived one)', 'squib'],
    FXT=['failure_to_extract', 'double_feed:stuck_case_plus_round'],
    FEJ=['stovepipe'],
    FBR=['failure_to_lock_back'],
)

INFERENCES = [
    'Clean-rifle baseline. No HK416 laboratory stoppage rate was found. The clean rifle is set near the Army laboratory figure for new M4s and M16s (about 5,000 rounds between stoppages), which is an assumption that a clean HK416 is no worse than a clean M4.',
    'The split of that clean baseline between types (feed 60 percent, eject 25, fire 15, the rest small) follows the proportions of the 2007 dust test loosely, with a larger share for ammunition. It is a judgement.',
    'The dust test counts are matched by solving one dust coefficient per type. They are calibration targets, not predictions.',
    'The briefing\'s "failure to feed" is not split further. Here it is split into rounds jammed on the feed ramp, the bolt closing on an empty chamber after a short stroke (from the energy model), bolt over-rides (from the timing model) and two-round feeds. The nine magazine-attributed stoppages are counted as feed stoppages.',
    'The rifles in the dust test are assumed to have used HK steel magazines. The briefing describes a basic load in aluminium magazines but does not say which magazine each rifle used.',
    'The aluminium magazine penalty in dust is taken from the M4\'s magazine-attributed stoppages in the same test series (148 and 239 per 60,000 rounds, midpoint 194). That is a different rifle; it is the only published number.',
    'Hangfire and squib rates, and every ammunition class other than in-specification M855, are guesses. No usable published rate exists for modern factory 5.56 mm. The M855 values are only checked to be consistent with the lot acceptance plan.',
    'The hangfire delay distribution (lognormal, median 80 ms) is a guess shaped by the general description of hangfires as mostly short.',
    'Shot-to-shot scatter of the carrier energy (logistic, scale 0.30 J) is inferred from the port pressure scatter the M855 specification allows; every scatter in the model is logistic (heavier tails than a normal).',
    'Every multiplier for dry running, cold, heat, carbon fouling, spring wear, feed-lip damage, extractor gap, weak ejector and worn piston rings. Directions follow the manual and common armourer practice; sizes are judgement.',
    'Dust carried in the rifle between wipes: 30 percent of the full load straight after a wipe and lubrication, rising linearly to the full load at 600 rounds.',
    'The chance that a rack extracts a slipped case (0.5), clears a case from the port (0.9) or a round from the feed ramp (0.85), that striking the charging handle frees an over-ridden round (0.7, then 0.95), or that the forward assist seats a round (0.6).',
    'Carrier stop positions and the poses of the case and round in each stoppage: worked out from the model\'s port, bolt face and magazine geometry by contact, not measured from photographs of real stoppages.',
    'Action durations (tap 0.4 s, rack 0.9 s and so on), which decide whether a stoppage counts as class 1 or class 2.',
    'Barrel heating of 2 K per shot with a 10 minute cooling time constant, scaled so the manual\'s limit (250 rounds in 3 minutes) is heat index 1.',
]

LIMITS = [
    'Rates are per-round probabilities, calibrated at two points: an assumed clean baseline and one published dust test. Between and beyond those points the model interpolates with inferred physics. It does not predict the reliability of any real rifle.',
    'The dust test is one test with a protocol the Army itself found not repeatable for the M4 (296 stoppages in one run, 863 in the next). The HK416 was run once.',
    'The energy and timing margins come from the action simulation, whose carrier, spring and gas parameters are themselves inferred. The margins are consistent with that model, not measured on a rifle.',
    'Parts breakage is not modelled: no broken extractors, bolts, firing pins or springs, and none of the 14 class 3 stoppages or the 3 headspace and case rupture events the dust test recorded for the HK416. Wear inputs are static settings.',
    'Not modelled: cook-off, slam-fire, doubling, out-of-battery firing other than a hangfire opened too early, case-head separation, pierced or blown primers, bolt locked to the rear early, and any trigger group fault.',
    'A squib is always a bullet lodged in the bore with the action not cycled. Firing a second round behind it is reported as a destroyed barrel and the simulation stops there; no damage is simulated.',
    'Hand-cycled feeding during clearing is assumed never to misfeed. Ejected live rounds are counted, not recovered.',
    'One stoppage per shot. Compound stoppages only arise through the state machine (a stuck case becomes a double feed when a round is fed behind it).',
    'The shooter always diagnoses correctly from what can be seen and follows the procedure. No fumbles, no stress, no darkness.',
    'Carrier travel after a short stroke is a scaled copy of the full-stroke curve, not a solved cycle.',
    'The clips are keyframe data in build.py\'s format. They have not been baked into the model or checked for clearance. Cases, loose rounds and the cleaning rod are props the model does not contain.',
    'The model has no extractor, ejector, hammer or firing pin nodes, so the parts that fail are never seen; only the carrier, the bolt head and the brass show the stoppage.',
]

# ---------------------------------------------------------------------------------------------- malfunctions
# 'state' is the mechanism in the action simulation's terms. 'shows' is how to pose the HK416 model.
# Prop poses are in the gun frame (metres, +Z muzzle, +Y up, +X shooter's left): base position and unit axis towards the nose or mouth.
MALFUNCTIONS = {
    'failure_to_fire': dict(
        n=1, name='Failure to fire (misfire)', cycle_step='4 firing',
        cause='The hammer falls and the round does not fire. Either the blow was too light to set off the primer, or the round is a dud.',
        state='Sear release to primer contact runs as normal (8.3 ms). The hammer delivers 0.48 J to the firing pin against a primer all-fire energy of 0.334 J: a ratio of 1.44. '
              'Dust, congealed oil or carbon in the firing pin channel lowers the delivered energy; a pin protruding less than the 0.53 mm indent cuts the indent short. '
              'The carrier never moves: travel 0 mm, bolt locked, hammer down.',
        conditions=['firing pin protrusion below the indent depth (the gauge limits are 0.90 and 1.10 mm, manual pp. 17 and 21)',
                    'grit or congealed oil in the firing pin channel (dust, cold)', 'hard primers or deteriorated ammunition'],
        hazard='At the click it cannot be told from a hangfire. Keep the muzzle on the backstop.',
        variants={'light_strike': 'the primer shows a shallow dent', 'dud': 'the primer shows a full dent and did nothing'},
        cues=dict(report='none', recoil='none', trigger='normal break, a click, then no reset',
                  sees=['bolt fully forward, port closed by the carrier', 'nothing ejected'], hears=['a dry click: hammer on firing pin'], sound=['mech_trigger']),
        shows=dict(carrier_mm=0, bolt_deg=0, nodes=['trigger'], clips=['trigger_pull'], props=[], note='nothing moves but the trigger; the hammer is not a node'),
        procedure='immediate_action', procedure_range='misfire_range'),
    'hangfire': dict(
        n=2, name='Hangfire (delayed ignition)', cycle_step='4 firing',
        cause='The primer is struck and the charge takes time to light. The round fires after a delay.',
        state='The firing train is normal up to the primer. Ignition, which follows primer contact by about 0.2 ms in the action simulation, is delayed by tens of '
              'milliseconds up to seconds. The M855 specification holds the whole action time (primer to gas port) to 3 ms at mean plus five standard deviations, so a '
              'hangfire is far outside normal ammunition. When it fires, the cycle runs as normal from that moment.',
        conditions=['old, damp, oil-soaked or badly stored ammunition', 'reloads (the manual allows factory-loaded cartridges only, pp. 4 and 26)'],
        hazard='If the action is opened during the delay the round can fire unlocked or outside the chamber, at the shooter\'s hand and face. This is the reason for the wait.',
        variants={'delayed': 'click, a pause, then a normal shot'},
        cues=dict(report='click, pause, then the normal report', recoil='normal, late', trigger='normal break',
                  sees=['exactly what a misfire shows, until it fires', 'then a normal ejection'], hears=['click ... bang; a gap under a quarter of a second is not noticed'],
                  sound=['mech_trigger', 'shot delayed by delayS', 'mech_cycle']),
        shows=dict(carrier_mm=0, bolt_deg=0, nodes=['trigger', 'bolt_carrier', 'bolt_head'], clips=['trigger_pull'], props=[],
                   note='hold the rest pose for delayS, then play HK416Action.sample() from its t = 8.5 ms (ignition)'),
        procedure='immediate_action', procedure_range='misfire_range'),
    'failure_to_feed': dict(
        n=3, name='Failure to feed', cycle_step='1 feeding, 2 chambering, 3 locking',
        cause='The bolt comes forward and the next round does not reach the chamber, or does not seat.',
        state='Three mechanisms. Short stroke: the carrier has 3.56 J left as it passes the pick-up point at 75.5 mm; if dust, cold or a weak round take more than that, it '
              'turns round short of the next round and closes on an empty chamber. Feed ramp jam: the round leaves the lips at the wrong angle and its nose stops below the '
              'chamber mouth, with the carrier held at about 45 mm on its way forward. Failure to chamber: the carrier arrives with 2.98 J and needs about 0.75 J to seat the '
              'round and turn the bolt; a dirty chamber raises that and the carrier stops about 6 mm short, bolt not turned.',
        conditions=['magazine: weak spring, damaged feed lips, dirt inside; aluminium magazines more than HK steel (manual pp. 5 and 6)', 'magazine not latched',
                    'short stroke: worn piston rings (manual p. 27), weak ammunition, dust, cold, a dry carrier', 'dirty chamber, damaged round, weak buffer spring (manual p. 26, step 3)'],
        hazard='None by itself. Do not hammer the forward assist on a round that will not seat.',
        variants={'nose_jam': 'round part stripped, nose stopped below the chamber, bolt holding it there',
                  'bolt_over_empty_chamber': 'bolt closed, chamber empty: short stroke or an unlatched magazine',
                  'failure_to_chamber': 'round almost home, bolt not turned, carrier a few millimetres short'},
        cues=dict(report='the previous shot was normal', recoil='normal, then the rifle feels dead',
                  trigger='jam or out of battery: dead or soft; empty chamber: a click',
                  sees=['feed ramp jam: bolt held about half way, brass and bullet nose-up in the port', 'empty chamber: bolt forward, everything looks normal',
                        'out of battery: carrier a few millimetres short of closed'],
                  hears=['shot, then a muffled stop; or a click on the next pull'], sound=['mech_cycle cut at stopTimeS', 'mech_trigger']),
        shows=dict(carrier_mm=dict(nose_jam=45.5, bolt_over_empty_chamber=0, failure_to_chamber=6.0), bolt_deg=dict(nose_jam=22.5, bolt_over_empty_chamber=0, failure_to_chamber=9.0),
                   nodes=['bolt_carrier', 'bolt_head', 'dust_cover', 'mag_round_1_case', 'mag_round_1_bullet'], clips=['dust_cover_open'],
                   props=[dict(variant='nose_jam', prop='prop_round', pos=[0.0024, -0.0150, -0.0490], axis=[0.0, 0.21, 0.978], note='base still under the lips, nose on the feed ramp')],
                   note='nose jam: hide mag_round_1 and show prop_round in its place, moved 25 mm forward and tipped 12 degrees nose-up'),
        procedure='immediate_action'),
    'stovepipe': dict(
        n=4, name='Failure to eject (stovepipe)', cycle_step='7 ejecting',
        cause='The fired case is pulled from the chamber and does not leave the port before the bolt returns. The bolt traps it.',
        state='The case mouth clears the port when the carrier passes 62.2 mm, 23.5 ms after the trigger break; the bolt comes back past that point at 52.0 ms. The case '
              'has that 28.5 ms window to get out and normally needs about 5 ms (12 mm sideways at 2.3 m/s). A fouled or weak ejector slows it; a short stroke shortens '
              'the window. Caught, the case is pinched by its head between the bolt face and the front edge of the port with the carrier held at about 27.5 mm. If the '
              'carrier never reaches 62.2 mm the case stays on the bolt face and is pushed back into the chamber.',
        conditions=['weak or fouled ejector, brass shavings under it (manual p. 27)', 'worn extractor or weak extractor spring: the case drops off the bolt face', 'short stroke', 'dust and dry running'],
        hazard='None by itself. Keep fingers clear of the port; the bolt is under spring load.',
        variants={'stovepipe': 'case caught by its head, standing out of the port', 'case_in_receiver': 'case loose in the port over the next round, bolt stopped on both',
                  'rechambered_case': 'short stroke: the fired case went back into the chamber; a click on the next pull'},
        cues=dict(report='the shot was normal', recoil='normal', trigger='dead: the bolt is out of battery (rechambered case: a click)',
                  sees=['an empty case sticking out of the ejection port, bolt a few centimetres open', 'or brass lying lengthwise in the port'],
                  hears=['shot, then a soft brassy stop; no case lands'], sound=['mech_cycle cut at stopTimeS']),
        shows=dict(carrier_mm=dict(stovepipe=27.5, case_in_receiver=45.5, rechambered_case=0), bolt_deg=dict(stovepipe=22.5, case_in_receiver=22.5, rechambered_case=0),
                   nodes=['bolt_carrier', 'bolt_head', 'dust_cover'], clips=['dust_cover_open'],
                   props=[dict(variant='stovepipe', prop='prop_case', pos=[-0.004, 0.002, -0.026], axis=[-0.94, 0.26, 0.21], note='head pinched between bolt face and port front edge, mouth outside'),
                          dict(variant='case_in_receiver', prop='prop_case', pos=[-0.006, -0.004, -0.072], axis=[0.0, 0.10, 0.995], note='lying in the port over the next round')],
                   note='do not spawn the HK416Action.ejectCase() brass for this shot'),
        procedure='stovepipe_clear'),
    'double_feed': dict(
        n=5, name='Double feed', cycle_step='6 extracting, then 1 feeding',
        cause='Two things want the chamber at once. Usually a fired case was left in the chamber and the bolt drove the next round into it. Less often the magazine lets go of two rounds.',
        state='The cycle is normal to full stroke. On the way forward the bolt strips a round whose nose meets the head of the case still in the chamber: the round is 57.4 mm '
              'long, so the bolt face stops that far behind the chamber and the carrier is held at about 68 mm. With two live rounds the carrier stops near 50 mm.',
        conditions=['everything that causes a failure to extract', 'damaged or spread feed lips (two live rounds)'],
        hazard='Tap and rack does not clear it: the magazine has to come out first.',
        variants={'stuck_case_plus_round': 'fired case in the chamber, live round wedged behind it', 'two_live': 'two rounds released together, both wedged at the chamber mouth'},
        cues=dict(report='the shot was normal', recoil='normal', trigger='dead',
                  sees=['bolt held most of the way back', 'brass in the chamber and a second round behind or beside it'], hears=['shot, then a hard stop with no closing'],
                  sound=['mech_cycle cut at stopTimeS']),
        shows=dict(carrier_mm=dict(stuck_case_plus_round=68.0, two_live=50.0), bolt_deg=22.5, nodes=['bolt_carrier', 'bolt_head', 'dust_cover', 'mag_round_1_case', 'mag_round_1_bullet'],
                   clips=['dust_cover_open'],
                   props=[dict(variant='stuck_case_plus_round', prop='prop_case', pos=[0.0, 0.0, -0.014], axis=[0.0, 0.0, 1.0], note='fired case fully in the chamber'),
                          dict(variant='stuck_case_plus_round', prop='prop_round', pos=[0.0, -0.012, -0.0714], axis=[0.0, 0.20, 0.98], note='nose against the case head'),
                          dict(variant='two_live', prop='prop_round', pos=[0.002, -0.006, -0.0535], axis=[0.0, 0.10, 0.995], note='upper round'),
                          dict(variant='two_live', prop='prop_round_2', pos=[-0.002, -0.016, -0.0535], axis=[0.0, 0.26, 0.966], note='lower round')]),
        procedure='double_feed_clear'),
    'failure_to_extract': dict(
        n=6, name='Failure to extract', cycle_step='6 extracting',
        cause='The fired case stays in the chamber. The claw slipped off the rim, or it held and tore through the rim.',
        state='Extraction starts as the bolt finishes turning, 3.3 ms after ignition, with 3.7 MPa still in the bore pressing the case wall on the chamber: about 0.8 kN of '
              'drag against a rim that shears at roughly 1.7 kN. Dust, a hot chamber or a sticky case raise the drag; a worn claw lowers what the extractor can hold. '
              'The carrier itself cycles normally.',
        conditions=['extractor claw outside its gauges (1.28 mm GO, 1.59 mm NO-GO, manual pp. 17, 23, 24) or a weak extractor spring', 'dirty or hot chamber, steel or lacquered cases'],
        hazard='With rounds in the magazine it becomes a double feed. A torn rim cannot be racked out; it needs a rod from the muzzle.',
        variants={'claw_slip': 'rim intact; racking may catch it', 'torn_rim': 'part of the rim is gone; the extractor has nothing to hold'},
        cues=dict(report='the shot was normal', recoil='normal', trigger='a click on the next pull, or the bolt is locked back on the empty magazine',
                  sees=['last round: bolt locked back with a fired case still in the chamber', 'no case left the port'], hears=['shot with no brass landing'], sound=['mech_cycle', 'mech_trigger']),
        shows=dict(carrier_mm=dict(empty_magazine=82.0, closed=0), bolt_deg=dict(empty_magazine=22.5, closed=0), nodes=['bolt_carrier', 'bolt_head', 'dust_cover', 'bolt_catch'],
                   clips=['dust_cover_open'], props=[dict(prop='prop_case', pos=[0.0, 0.0, -0.014], axis=[0.0, 0.0, 1.0], note='fired case in the chamber, seen only with the bolt back')],
                   note='do not spawn ejected brass for this shot'),
        procedure='immediate_action'),
    'bolt_override': dict(
        n=7, name='Bolt over-ride', cycle_step='1 feeding',
        cause='The next round is not in place when the bolt comes forward, and the bolt rides over it. The round ends up wedged above the bolt.',
        state='A timing race. The bolt is behind the magazine (carrier beyond 75.5 mm) for 19.0 ms. In that time the magazine spring has to lift the stack about 6 mm; with '
              '29 rounds still in the magazine that takes about 10 ms. A weak spring, dust in the magazine or a short stroke narrows the gap. The carrier is held at about 50 mm.',
        conditions=['weak magazine spring or a sticking follower', 'dust in the magazine', 'a full magazine (the heaviest stack)'],
        hazard='The charging handle is pinned by the round. Forcing it bends the handle.',
        variants={'override': 'live round wedged over the bolt head; bolt held part open'},
        cues=dict(report='the shot was normal', recoil='normal', trigger='dead',
                  sees=['bolt held about half open', 'a live round high in the port, above the bolt'], feels=['the charging handle moves a few millimetres and stops hard'],
                  hears=['shot, then a hard stop'], sound=['mech_cycle cut at stopTimeS']),
        shows=dict(carrier_mm=50.0, bolt_deg=22.5, nodes=['bolt_carrier', 'bolt_head', 'dust_cover', 'charging_handle'], clips=['dust_cover_open', 'rack_bound'],
                   props=[dict(prop='prop_round', pos=[0.0, 0.010, -0.085], axis=[0.0, -0.17, 0.985], note='between the top of the bolt and the receiver roof, nose down towards the chamber')]),
        procedure='bolt_override_clear'),
    'squib': dict(
        n=8, name='Squib (bullet lodged in the bore)', cycle_step='4 firing',
        cause='A round with little or no powder. The primer, or a fraction of a charge, pushes the bullet into the barrel and leaves it there.',
        state='No pressure curve to speak of: the bullet stops before the gas port (242.6 mm from the bolt face), no gas reaches the piston and the carrier stays at 0 mm with '
              'the fired case still chambered.',
        conditions=['reloads with a missed or light charge', 'contaminated powder', 'very rare in factory military ammunition: one bullet left in the bore rejects a whole lot (MIL-C-63989C)'],
        hazard='The bore is blocked. Stop on a pop instead of a bang, less recoil than normal, an action that did not cycle. Do not fire again until a rod has passed through the bore.',
        variants={'lodged': 'bullet stopped in the bore; fired case still chambered'},
        cues=dict(report='a pop or a weak, hollow report', recoil='little or none', trigger='normal break',
                  sees=['bolt forward, nothing ejected', 'no strike downrange'], hears=['a pop, far quieter than a shot'], sound=['mech_trigger', 'squib_pop (not in the sound model yet)']),
        shows=dict(carrier_mm=0, bolt_deg=0, nodes=['trigger'], clips=['trigger_pull'],
                   props=[dict(prop='prop_bullet', pos=[0.0, 0.0, 0.0203], axis=[0.0, 0.0, 1.0], note='add lodgedMm to z: bullet base position in the bore; not visible from outside')]),
        procedure='squib_stop'),
    'failure_to_lock_back': dict(
        n=9, name='Failure to lock back on the last round', cycle_step='after 8 cocking',
        cause='The magazine is empty but the bolt closes instead of locking open.',
        state='The follower lifts the bolt catch, which holds the carrier at 82 mm on its way forward (manual p. 26, step 10). A carrier that turns round short of 82 mm, '
              'with 3.15 J to spare when clean, never passes the catch.',
        conditions=['short stroke', 'weak magazine spring, worn follower or bolt catch'],
        hazard='None. A click on an empty rifle.',
        variants={'closed_on_empty': 'last round fired and ejected; bolt forward, chamber and magazine empty'},
        cues=dict(report='the last shot was normal', recoil='normal', trigger='a click on the next pull', sees=['bolt forward where it should be locked open'], hears=['click'],
                  sound=['mech_cycle', 'mech_trigger']),
        shows=dict(carrier_mm=0, bolt_deg=0, nodes=['bolt_carrier'], clips=[], props=[]),
        procedure='immediate_action'),
}

# ---------------------------------------------------------------------------------------------- actions
ACTIONS = {
    'tap': dict(label='Tap', time_s=0.4, hand='Support-hand palm strikes the magazine floorplate upward, then tugs down to prove it is latched.', anim=['mag_tap'], sound=['mag_tap']),
    'rack': dict(label='Rack', time_s=0.9,
                 hand='Support hand pulls the charging handle fully to the rear and lets it go; do not ride it forward (manual p. 8). Port towards the ground, watch what comes out (manual p. 3, step 4).',
                 anim=['rack_full'], sound=['mech_charge']),
    'reassess': dict(label='Reassess', time_s=0.5, hand='Both hands back on the rifle, eyes to the ejection port, then to the target. Fire only if the target still warrants it.', anim=[], sound=[]),
    'lock_back': dict(label='Lock the bolt back', time_s=1.2, hand='Hold the charging handle to the rear and press the bolt catch in (manual p. 3, step 5); ease the handle forward.',
                      anim=['lock_back'], sound=['mech_bolt_lock_back']),
    'strip_mag': dict(label='Remove the magazine', time_s=0.9, hand='Press the magazine release and pull the magazine out (manual p. 3, step 3). In a double feed it is pinned and needs a firm pull.',
                      anim=['mag_release', 'mag_out'], sound=['mag_out']),
    'insert_mag': dict(label='Insert a loaded magazine', time_s=1.2, hand='Seat a loaded magazine until the catch engages its recess (manual p. 8), then tug it.', anim=['mag_in'], sound=['mag_in']),
    'release_bolt': dict(label='Release the bolt', time_s=0.3, hand='Press the bolt catch. The carrier runs forward from 82 mm and chambers a round (manual p. 26, step 2).',
                         anim=['bolt_catch', 'release_bolt'], sound=['mech_bolt_release']),
    'sweep_case': dict(label='Remove the case from the port', time_s=0.8, hand='Support hand grasps the trapped case and pulls it out of the port; the bolt goes forward.', anim=['sweep_case'], sound=[]),
    'handle_strike': dict(label='Charging handle: pull, then strike forward', time_s=1.5,
                          hand='Magazine out. Pull the charging handle as far back as it will go, then strike it forward with the palm so the bolt is driven back off the round.',
                          anim=['rack_bound', 'handle_strike'], sound=[]),
    'hold_bolt_strike': dict(label='Hold the bolt back and strike the handle', time_s=3.0,
                             hand='Pull the handle to the rear again, hold the bolt back through the port with a tool or a finger, and send the handle forward sharply.',
                             anim=['handle_strike'], sound=[]),
    'forward_assist': dict(label='Forward assist', time_s=0.3,
                           hand='One light tap. The manual treats a bolt that moves under the forward assist as a symptom: dirty chamber, damaged round or weak buffer spring (p. 26, step 3). If it does not close, rack instead.',
                           anim=['forward_assist'], sound=[]),
    'wait': dict(label='Wait, muzzle on the backstop', time_s=30.0, hand='Nothing moves. Rifle shouldered and pointed at the backstop, finger off the trigger.', anim=[], sound=[]),
    'safe': dict(label='Selector to safe', time_s=0.3, hand='Thumb rotates the selector to safe. It only turns with the hammer cocked (manual p. 3, step 2).', anim=['safety_to_safe'], sound=[]),
    'selector_fire': dict(label='Selector to fire', time_s=0.3, hand='Thumb rotates the selector to semi.', anim=['safety_to_fire'], sound=[]),
    'inspect_chamber': dict(label='Inspect the chamber', time_s=1.5, hand='Bolt locked back; look through the ejection port into the chamber and the magazine well (manual p. 3, step 6).', anim=[], sound=[]),
    'check_bore': dict(label='Check the bore with a rod', time_s=8.0, hand='Rifle unloaded and locked open. Pass a cleaning rod through the bore (manual p. 3, step 6, the physical check). If it stops short, the bore is blocked.',
                       anim=['rod_probe'], sound=[]),
    'rod': dict(label='Clear with a rod (armourer)', time_s=60.0,
                hand='Rifle unloaded, bolt locked back. A cleaning rod from the muzzle pushes the stuck case out, or drives a lodged bullet back out through the chamber. After a squib the barrel is inspected before the rifle is used again.',
                anim=['rod_probe'], sound=[]),
}

# New motions, in build.py's key() format so the model recipe can bake them: 24 fps; ('loc', axis) in mm from the rest pose with
# L + towards the muzzle, S + to the shooter's left, Z up; ('rot', axis) in degrees about the Blender axis through the part pivot.
# 'x0' is the carrier travel the stoppage left (shows.carrier_mm); 'x1' is where the carrier ends (0 closed, or the new stop).
MOTIONS = {
    'mag_tap': dict(fps=24, note='an unlatched magazine starts 6 mm low (z0 = -6), a latched one at z0 = 0', tracks=[
        dict(node='mag_body', chan=['loc', 'Z'], keys=[[1, 'z0'], [3, 0.6], [5, 0.0], [7, -0.8], [9, 0.0]])]),
    'rack_full': dict(fps=24, note='the charge clip extended to the 95 mm stroke of the action simulation, from any starting position; released, the carrier closes in two frames', tracks=[
        dict(node='charging_handle', chan=['loc', 'L'], keys=[[1, 0], [9, -95.0], [12, -95.0], [14, 0]]),
        dict(node='bolt_carrier', chan=['loc', 'L'], keys=[[1, '-x0'], [9, -95.0], [12, -95.0], [14, '-x1']]),
        dict(node='dust_cover', chan=['rot', 'Y'], keys=[[1, -175], [14, -175]])]),
    'lock_back': dict(fps=24, note='handle to the buffer stop, carrier caught at 82 mm on the way forward; the handle returns alone', tracks=[
        dict(node='charging_handle', chan=['loc', 'L'], keys=[[1, 0], [8, -95.0], [14, -95.0], [20, 0]]),
        dict(node='bolt_carrier', chan=['loc', 'L'], keys=[[1, '-x0'], [8, -95.0], [14, -95.0], [16, -82.0], [20, -82.0]]),
        dict(node='bolt_catch', chan=['rot', 'Y'], keys=[[10, 0], [13, 5.5], [20, 5.5]]),
        dict(node='dust_cover', chan=['rot', 'Y'], keys=[[1, -175], [20, -175]])]),
    'release_bolt': dict(fps=24, note='the carrier closes from 82 mm in about 43 ms (one frame); for exact timing follow action.json from where carrier_mm falls through 82', tracks=[
        dict(node='bolt_catch', chan=['rot', 'Y'], keys=[[1, 5.5], [3, 0]]),
        dict(node='bolt_carrier', chan=['loc', 'L'], keys=[[1, -82.0], [2, -82.0], [3, '-x1'], [6, '-x1']])]),
    'rack_bound': dict(fps=24, note='bolt over-ride: the handle moves 8 mm and stops against the round', tracks=[
        dict(node='charging_handle', chan=['loc', 'L'], keys=[[1, 0], [4, -8.0], [7, -8.0], [10, 0]])]),
    'handle_strike': dict(fps=24, note='handle drawn to where the round stops it, then struck forward; the carrier jumps back off the round and closes', tracks=[
        dict(node='charging_handle', chan=['loc', 'L'], keys=[[1, 0], [8, '-x0'], [12, '-x0'], [14, 0]]),
        dict(node='bolt_carrier', chan=['loc', 'L'], keys=[[1, '-x0'], [12, '-x0'], [14, -95.0], [17, -95.0], [19, '-x1']])]),
    'sweep_case': dict(fps=24, note='prop_case leaves the port to the right and down; the carrier then closes', tracks=[
        dict(node='prop_case', chan=['loc', 'S'], keys=[[1, 0], [8, -60.0]]),
        dict(node='prop_case', chan=['loc', 'Z'], keys=[[1, 0], [8, -25.0]]),
        dict(node='bolt_carrier', chan=['loc', 'L'], keys=[[1, '-x0'], [8, '-x0'], [10, '-x1']])]),
    'forward_assist': dict(fps=24, note='the button travels 6 mm inwards; in build.py its axis is 4 degrees off L, (L, S, Z) = (0.997, 0.073, 0), keyed here along L only', tracks=[
        dict(node='forward_assist_button', chan=['loc', 'L'], keys=[[1, 0], [3, 6.0], [6, 0]]),
        dict(node='bolt_carrier', chan=['loc', 'L'], keys=[[1, '-x0'], [3, '-x1'], [6, '-x1']])]),
    'rod_probe': dict(fps=24, note='prop_rod enters at socket_muzzle and travels down the bore; on a squib it stops at the bullet (depth = 368 - 34 - lodgedMm), otherwise at the bolt face (382 mm)', tracks=[
        dict(node='prop_rod', chan=['loc', 'L'], keys=[[1, 0], [48, '-depth']])]),
}

# Clips that already exist in model/build.py and are reused as they are.
EXISTING_CLIPS = ['charge', 'dust_cover_open', 'mag_release', 'mag_out', 'mag_in', 'bolt_catch', 'safety_to_fire', 'safety_to_safe', 'trigger_pull']
PROPS = ['prop_case', 'prop_round', 'prop_round_2', 'prop_bullet', 'prop_rod']

# ---------------------------------------------------------------------------------------------- procedures
# A step is {action, expect} with optional 'if' (a condition on what the shooter can see) and 'branch' (go to another procedure).
def step(action, expect, **kw):
    d = dict(action=action, expect=expect); d.update(kw); return d

_REMEDIAL = [step('strip_mag', 'the magazine comes out; loose rounds may fall with it'),
             step('rack', 'whatever is loose drops through the magazine well; the extractor tries the chamber'),
             step('rack', 'second pull'),
             step('lock_back', 'bolt held open'),
             step('inspect_chamber', 'chamber and feedway empty', branch=dict(chamber_not_clear='stuck_case_rod')),
             step('insert_mag', 'a fresh loaded magazine is latched'),
             step('release_bolt', 'a round is chambered and the bolt locks'),
             step('reassess', 'ready to fire')]

PROCEDURES = {
    'immediate_action': dict(
        name='Immediate action: tap, rack, reassess', source='TC 3-22.9 (2016) para 8-35, as summarised; the motions are those of the manual\'s loading note (p. 8) and clearing step 4 (p. 3)',
        when='The hammer fell with a click and nothing happened, and the cause is not known. Not for a pop or weak shot.',
        end='ready', fallback='remedial_clear', attempts=2,
        steps=[step('tap', 'the magazine is latched'),
               step('rack', 'whatever was in the chamber is thrown out; a fresh round is chambered and the bolt locks'),
               step('reassess', 'bolt fully forward, port clear: ready')]),
    'misfire_range': dict(
        name='Misfire on a range: wait, then tap, rack, reassess', source='standard range practice for a possible hangfire, then TC 3-22.9 para 8-35',
        when='Click, no bang, no recoil, on a range where nothing is gained by hurrying.',
        end='ready', fallback='remedial_clear', attempts=1,
        steps=[step('wait', 'if it was a hangfire the shot goes into the backstop and the rifle cycles; otherwise nothing happens', args=dict(seconds=30)),
               step('tap', 'the magazine is latched'),
               step('rack', 'the dud is ejected, port towards the ground; a fresh round is chambered'),
               step('reassess', 'ready. The dud is set aside as the range directs')]),
    'stovepipe_clear': dict(
        name='Stove pipe', source='TC 3-22.9 (2016) para 8-36 remedial action, stove pipe, as summarised',
        when='A case is standing in, or lying in, the ejection port and the trigger is dead.',
        end='ready', fallback='remedial_clear', attempts=1,
        steps=[step('sweep_case', 'the case is out and the bolt goes forward'),
               step('rack', 'the rifle is cycled: a fresh round is chambered'),
               step('reassess', 'ready')]),
    'double_feed_clear': dict(
        name='Double feed', source='TC 3-22.9 (2016) para 8-36 remedial action, double feed, as summarised: magazine out, clear, confirm, fresh magazine, chamber. Many instructors lock the bolt back first to take the spring off the wedged rounds',
        when='Brass and a second round are both at the chamber, or immediate action has failed twice.',
        end='ready', fallback='stuck_case_rod', attempts=1, steps=_REMEDIAL),
    'remedial_clear': dict(
        name='Remedial action', source='TC 3-22.9 (2016) para 8-36, as summarised: look, remove the magazine, clear, inspect, then act on what is found',
        when='Immediate action has failed twice, or the trigger will not press, or it feels soft.',
        end='ready', fallback='stuck_case_rod', attempts=1, steps=_REMEDIAL),
    'bolt_override_clear': dict(
        name='Bolt over-ride', source='TC 3-22.9 (2016) para 8-36 remedial action, bolt override, as summarised',
        when='A round is wedged above the bolt and the charging handle is bound.',
        end='ready', fallback='remedial_clear', attempts=1,
        steps=[step('strip_mag', 'pressure from below is removed'),
               step('handle_strike', 'the bolt is driven back off the round, which drops through the magazine well'),
               step('hold_bolt_strike', 'second method, only if the first did not free it', **{'if': 'handle_bound'}),
               step('lock_back', 'bolt held open'),
               step('inspect_chamber', 'chamber and feedway empty', branch=dict(chamber_not_clear='stuck_case_rod')),
               step('insert_mag', 'a fresh loaded magazine is latched'),
               step('release_bolt', 'a round is chambered and the bolt locks'),
               step('reassess', 'ready')]),
    'squib_stop': dict(
        name='Pop or weak shot: stop, unload, prove the bore', source='standard range practice; the unloading and the rod check are the manual\'s clearing steps 2 to 6 (p. 3), and a clear bore is one of its conditions for handling (p. 4, rule 3)',
        when='A pop or weak report, little recoil, the action did not cycle. Any one of these is enough to stop.',
        end='made_safe', fallback=None, attempts=1,
        steps=[step('strip_mag', 'no round can feed'),
               step('lock_back', 'the fired case is drawn out and the bolt held open; the hammer is now cocked'),
               step('safe', 'selector on safe'),
               step('inspect_chamber', 'chamber empty'),
               step('check_bore', 'the rod stops short: a bullet is in the bore'),
               step('rod', 'the bullet is driven out by an armourer and the barrel inspected; the rifle is out of use until then')]),
    'stuck_case_rod': dict(
        name='Case stuck in the chamber', source='the manual\'s clearing steps (p. 3) and its tool list, which includes a 5.56 mm broken shell extractor (p. 17)',
        when='A fired case is still in the chamber and racking does not bring it out.',
        end='ready', fallback=None, attempts=1,
        steps=[step('strip_mag', 'no round can feed onto the case', **{'if': 'mag_in'}),
               step('lock_back', 'bolt held open'),
               step('safe', 'selector on safe'),
               step('rod', 'the case is pushed out from the muzzle end and falls through the magazine well'),
               step('inspect_chamber', 'chamber empty'),
               step('selector_fire', 'selector back to semi'),
               step('insert_mag', 'a loaded magazine is latched'),
               step('release_bolt', 'a round is chambered and the bolt locks'),
               step('reassess', 'ready. Have the extractor gauged (1.28 / 1.59 mm, manual pp. 23 and 24)')]),
    'reload': dict(
        name='Reload', source='manual p. 8 (loading) and p. 26 (bolt catch)',
        when='The magazine is empty: bolt locked open, or a rack shows the follower.',
        end='ready', fallback='remedial_clear', attempts=1,
        steps=[step('strip_mag', 'the empty magazine is out', **{'if': 'mag_in'}),
               step('insert_mag', 'a loaded magazine is latched'),
               step('release_bolt', 'a round is chambered and the bolt locks', **{'if': 'bolt_open'}),
               step('rack', 'a round is chambered and the bolt locks', **{'if': 'bolt_closed'}),
               step('reassess', 'ready')]),
}

# What the shooter can see -> which procedure. Evaluated top to bottom; the first match wins.
DIAGNOSIS = [
    dict(see=dict(report='pop'), procedure='squib_stop', why='a pop or weak shot is never cleared by racking and firing'),
    dict(see=dict(port='case_in_port'), procedure='stovepipe_clear', why='brass in the port'),
    dict(see=dict(port='case_loose_in_port'), procedure='stovepipe_clear', why='brass in the port'),
    dict(see=dict(port='brass_and_round'), procedure='double_feed_clear', why='two things at the chamber'),
    dict(see=dict(port='two_rounds'), procedure='double_feed_clear', why='two things at the chamber'),
    dict(see=dict(port='round_above_bolt'), procedure='bolt_override_clear', why='round above the bolt, handle bound'),
    dict(see=dict(port='round_nose_up'), procedure='remedial_clear', why='trigger dead, bolt held open by a round'),
    dict(see=dict(port='out_of_battery'), procedure='remedial_clear', why='trigger soft, bolt not closed'),
    dict(see=dict(port='bolt_held_open', mag='in'), procedure='reload', why='bolt locked open on the follower'),
    dict(see=dict(port='bolt_held_open', mag='out'), procedure='reload', why='bolt locked open, no magazine'),
    dict(see=dict(port='closed', trigger='click'), procedure='immediate_action', why='click with the bolt closed (on a range: misfire_range, to cover a hangfire)'),
    dict(see=dict(port='closed'), procedure='immediate_action', why='bolt closed, rifle not ready'),
]
