# Muzzle flash: sources (cited, not committed)

Nothing in this list is in the repository. Local copies of the photographs live in `../refs-local/flash/` (ignored by
git) under the file names below; `compare/make_compare.py` reads them from there. Only pictures and plots drawn from
the simulation are committed.

## Publications

| Short name | Full reference | What it is used for |
|---|---|---|
| Klingenberg & Mach 1976 | G. Klingenberg and H. Mach, "Investigation of combustion phenomena associated with the flow of hot propellant gases. I: Spectroscopic temperature measurements inside the muzzle flash of a rifle", *Combustion and Flame* 27 (1976), pp. 163-176. | Temperatures of the three flash phases of a 7.62 mm rifle: primary 1645 K, intermediate about 1600 K rising to 1940 K at 100 to 300 mm, secondary about 2500 K at 300 to 500 mm. Read from the abstract; the full paper was not available. |
| Klingenberg & Heimerl | G. Klingenberg and J. M. Heimerl, *Gun Muzzle Blast and Flash*, Progress in Astronautics and Aeronautics vol. 139, AIAA, 1992; and G. Klingenberg, "Gun muzzle blast and flash", *Propellants, Explosives, Pyrotechnics* 14, no. 2 (1989). | The standard description this model follows: primary flash at the muzzle, intermediate flash behind the Mach disc of the under-expanded jet, secondary flash when the fuel-rich gas re-ignites in air, and its suppression by alkali salts and by muzzle devices. Used for the structure, not for numbers (not re-read in this session). |
| Heimerl & Klingenberg | J. M. Heimerl, G. Klingenberg and co-workers, work on the intermediate flash of the 7.62 mm rifle and its gas-gun simulator, BRL reports of 1986-88 (for example DTIC ADA181760). | Oxygen entrained behind the Mach disc reacts near the axis and raises the temperature: the reason the model ties the visible intermediate flash to burning (`dT_chem`, `flush_k`, `glow_floor`). Read from an abstract. |
| CARS report | "CARS temperature measurements in the muzzle flash region of a 7.62 mm rifle", US Army Ballistic Research Laboratory, DTIC ADA190786. Authors not confirmed in this session. | 1468 K at 0.70 ms falling to about 500 K at 1.53 ms in the intermediate flash region. A late-time check, which the model fails (see README). Read from an abstract. |
| Lewis & Carlson 1964 | C. H. Lewis and D. J. Carlson, "Normal shock location in underexpanded gas and gas-particle jets", *AIAA Journal* 2 (1964), pp. 776-777. | Mach disc distance x/D = 0.69 M sqrt(gamma p_e / p_inf). Quoted from memory of the standard form; not re-read. |
| Ashkenas & Sherman 1966 | H. Ashkenas and F. S. Sherman, "The structure and utilization of supersonic free jets in low density wind tunnels", *Rarefied Gas Dynamics* 4, vol. 2 (1966), pp. 84-105. | Cross-check of the Mach disc distance, x/D = 0.67 sqrt(p_0 / p_inf). Quoted from memory of the standard form. |
| Schmidt & Shear 1975 | E. M. Schmidt and D. D. Shear, "Optical measurements of muzzle blast", *AIAA Journal* 13 (1975), pp. 1086-1091. | Shadowgraphs of the 5.56 mm M16 muzzle flow: the growing, then retreating, Mach disc that the jet model imitates. Structure only. |
| Turner 1973 | J. S. Turner, *Buoyancy Effects in Fluids*, Cambridge University Press, 1973. | Entrainment coefficient of puffs and thermals (0.25 to 0.3) for the smoke. |
| TTAG flash hider shootout | The Truth About Guns, "AR-15 Flash Hider Shootout" (thetruthaboutguns.com/ar-15-flash-hider-shootout). | Light-meter readings beside a 16 in AR-15 in a dark range: bare muzzle 10,760 lx, A2 birdcage 0.48 lx, ambient 0.25 lx. The only absolute brightness numbers used. Also the A2 photo below. |
| HK manual | HK416 maintenance manual, p. 7 (see `../notes/MANUAL_NOTES.md`). | Muzzle velocities at four barrel lengths, used to test the 16 in reference run. |

## Photographs

| Local file | What it shows | Source and licence |
|---|---|---|
| `ttag_a2.jpg` | A2 birdcage on a 16 in AR-15, side-on, dark range, three shots in one 3.2 s exposure. Lit slots, slot-jet glow, a dark gap, and the glow behind the Mach disc. **The primary reference.** | TTAG flash hider shootout (above). Copyright TTAG; not redistributable. |
| `crop_a2.png` | An enlargement of the hider in `ttag_a2.jpg`, made locally. | As above. |
| `ttag_bare.jpg` | The same rifle with a bare muzzle: the frame is burnt out by the secondary flash. | As above. |
| `wm_1.jpg` | An M4 with its issue hider at night: a full secondary flash, about 0.44 m long and 0.40 m high. | Wikimedia Commons, "103rd Rescue Squadron trains at the firing range 150409-Z-SV144-044.jpg". US Air National Guard photo, public domain. |
| `wm_0.jpg` | Same event, another shot: a long plume with smoke. Looked at, not measured. | Wikimedia Commons, "New York National Guard (16911320668).jpg". US military photo, public domain. |
| `wm_2.jpg` | A Marine's M4A1 at dusk: a smaller secondary flash through the hider with spark streaks. | Wikimedia Commons, "200929-M-ET529-1618M.jpg". US Marine Corps photo, public domain. |
| `wn_3.jpg` | Schlieren picture of a rifle with a slotted flash suppressor just after the bullet leaves: the blast, the gas cloud, the bullet inside it. Looked at for the order of events, not measured. | Wikimedia Commons, "Schlieren Imaging Flash Suppressor.JPG" (from the article "Flash suppressor"). Licence not checked. |

The two public-domain service photos could be committed under rule 6, but none is: every committed picture here is
simulation output.

The rifles in the photographs are AR-15s and M4s with the five-slot A2 hider, not an HK416 with HK's hider. No
photograph of a 5.56 mm HK416 flash good enough to measure was found.
