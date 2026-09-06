# -*- coding: utf-8 -*-
"""
component_data.py - Machine components and their faults, for CM/DX's
"Components" reference tab.

Content is based on the "Analysis Definitions" section of the Mobius
Institute Vibration Analysis Handbook (signatures/causes paraphrased from
the book's diagnostic descriptions, not quoted). Recommendations are
standard field-maintenance practice, since the handbook itself is
diagnostic (how to recognize a fault) rather than prescriptive (how to
fix it) - those are written from general condition-monitoring practice,
not lifted from any one source.

Structure: COMPONENTS is a list of (component_name, component_subtitle,
[fault_dicts]) tuples. Each fault dict has: name, signature, causes
(list), actions (list) - same field names as cmdx_tab.py's FAULTS so the
Components screen can reuse the same detail-popup rendering pattern.
"""

COMPONENTS = [
    ("Rotor / Unbalance", "Heavy-spot conditions on a rotating shaft", [
        dict(name="Static unbalance",
             signature="Dominant 1X peak, radial (vertical & horizontal), low in axial. "
                        "Phase at both bearings is in-phase; 90° V-to-H phase shift.",
             causes=["A single heavy spot on the rotor", "Uneven material buildup or wear",
                     "Missing balance weight", "Casting/manufacturing defect"],
             actions=["Single-plane field balance at the rotor.",
                      "Check for buildup, missing weights, or debris before balancing.",
                      "Confirm waveform is sinusoidal - if not, rule out misalignment, bent shaft, or looseness first."]),
        dict(name="Couple unbalance",
             signature="Dominant 1X peak, radial, low in axial. Bearings 180° out-of-phase "
                        "with each other (opposite ends of the rotor).",
             causes=["Two heavy spots 180° apart on a rotor that is long relative to its diameter",
                      "May appear statically balanced but generates opposing centrifugal forces when running"],
             actions=["Two-plane field balance is required (single-plane won't correct it).",
                      "Verify phase relationship between both bearings before balancing."]),
        dict(name="Dynamic unbalance",
             signature="Dominant 1X peak, radial. Phase between bearings typically 30°-150° "
                        "out-of-phase (a mix of static + couple).",
             causes=["Combination of static and couple unbalance",
                      "Common on rotors that are long relative to their diameter"],
             actions=["Two-plane field balance required.",
                      "Treat as the default assumption on long rotors unless phase data confirms pure static/couple."]),
        dict(name="Overhung rotor unbalance",
             signature="High 1X in all three directions but highest in axial. Axial phase "
                        "in-phase at both bearings; radial phase in-phase at both bearings.",
             causes=["Heavy spot on a cantilevered/overhung rotor (close-coupled pumps, axial fans, small turbines)",
                      "The unbalance creates a bending moment that shows up as axial vibration"],
             actions=["Balance the overhung rotor - single or two-plane depending on rotor geometry.",
                      "Don't mistake the strong axial 1X for misalignment or a cocked bearing - check phase first."]),
    ]),

    ("Shaft Alignment", "Coupling misalignment and shaft bow", [
        dict(name="Parallel (offset) misalignment",
             signature="High 2X radial with smaller 1X radial; can extend to 3X-5X. "
                        "V/H phase in-phase or 180° out; across-coupling phase out-of-phase.",
             causes=["Shaft centerlines parallel but not coincident",
                      "Poor alignment practice at installation", "Thermal growth", "Shifting foundation",
                      "Pipe strain pulling the machine off alignment"],
             actions=["Laser-align the coupled shafts (see the Laser Align tool).",
                      "Recheck alignment hot vs. cold if thermal growth is suspected.",
                      "Correct pipe strain/soft foot before re-aligning."]),
        dict(name="Angular (gap) misalignment",
             signature="High 1X axial with smaller 2X axial; some 1X radial. Components "
                        "out-of-phase axially across the coupling.",
             causes=["Shaft centerlines meet at an angle rather than running parallel",
                      "Poor alignment practice", "Thermal growth", "Shifting foundation or pipe strain"],
             actions=["Laser-align the coupled shafts, correcting angularity at both feet.",
                      "Verify with axial phase readings on both sides of the coupling."]),
        dict(name="Bent shaft",
             signature="High 1X axial (dominant if bend is mid-shaft) or high 2X axial (if bend "
                        "is near the coupling). 180° phase shift axially across the shaft.",
             causes=["Excessive heat causing thermal bow", "Long-term storage sag (catenary)",
                      "Physical impact or mishandling"],
             actions=["Confirm with axial phase readings 180° apart at each end of the shaft.",
                      "Straighten or replace the shaft - vibration alone can't be corrected by balancing or alignment.",
                      "Check for the root cause (overheating, improper storage/support) to prevent recurrence."]),
    ]),

    ("Rolling Element Bearings", "Ball/roller bearing wear stages and installation faults", [
        dict(name="Stage 1 fault (early lubrication/wear)",
             signature="Very low amplitude, very high frequency (often above 10 kHz). Invisible "
                        "to standard spectrum/waveform - needs enveloping/PeakVue/Shock Pulse/Spike Energy.",
             causes=["Early lubrication breakdown", "Very minor surface damage just beginning"],
             actions=["Re-grease/re-lubricate per schedule and recheck with high-frequency techniques.",
                      "No replacement needed yet - this is the earliest detectable stage."]),
        dict(name="Stage 2 fault",
             signature="Still low amplitude/high frequency, but enveloping and demodulation start "
                        "showing results; acceleration time waveform may show early defect signs, "
                        "especially on slow-speed machines.",
             causes=["Bearing wear progressing past the earliest lubrication-only stage"],
             actions=["Increase monitoring frequency on this bearing.",
                      "Plan a bearing replacement during the next convenient outage.",
                      "Verify high-frequency filter settings and accelerometer mounting for reliable trending."]),
        dict(name="Stage 3 fault - outer race",
             signature="Non-synchronous harmonics at a non-integer multiple of 1X (BPFO-related). "
                        "No 1X sidebands if the outer race is stationary.",
             causes=["Spalling/pitting damage on the outer race"],
             actions=["Schedule bearing replacement soon - damage is now visible if the bearing is pulled.",
                      "Confirm with time waveform (impacts visible) and BPFO frequency calculation."]),
        dict(name="Stage 3 fault - inner race",
             signature="Non-synchronous harmonics (BPFI-related) with 1X sidebands, since the "
                        "damaged spot passes through the load zone once per revolution.",
             causes=["Spalling/pitting damage on the inner race"],
             actions=["Schedule bearing replacement soon.",
                      "Confirm with time waveform impacts and BPFI frequency calculation."]),
        dict(name="Stage 3 fault - ball/roller damage",
             signature="Non-synchronous harmonics with FTF (cage) sidebands around 0.4x-0.46x running speed.",
             causes=["Spalling/pitting damage on one or more rolling elements"],
             actions=["Schedule bearing replacement soon.",
                      "Confirm with time waveform impacts and FTF (cage) frequency calculation."]),
        dict(name="Stage 4 fault (advanced damage)",
             signature="Classic bearing harmonics/sidebands disappear into a raised, noisy floor "
                        "('haystacks'); 1X harmonics appear as internal clearance grows.",
             causes=["Bearing damage has progressed to the point where geometry has changed",
                      "High-frequency techniques lose effectiveness as periodicity is lost"],
             actions=["Replace the bearing as soon as possible - this stage indicates significant, advanced damage.",
                      "Watch overall vibration levels, which will now be rising sharply."]),
        dict(name="Cocked bearing - on shaft",
             signature="Raised 1X, 2X, and 3X axial. Rotating ('wobble') phase pattern - 90° phase "
                        "shift moving around the shaft at 12/3/6/9 o'clock.",
             causes=["Inner race not seated true/perpendicular on the shaft during installation"],
             actions=["Re-install the bearing correctly, ensuring the inner race seats square on the shaft.",
                      "Use phase readings (not just spectrum) to distinguish this from unbalance or misalignment."]),
        dict(name="Cocked bearing - in housing",
             signature="Raised 1X, 2X, and 3X axial. Static (not rotating) phase pattern - 180° "
                        "phase difference between two fixed points on the housing face.",
             causes=["Outer race not seated true/perpendicular in the housing during installation"],
             actions=["Re-install the bearing correctly, ensuring the outer race seats square in the housing.",
                      "Use phase readings to distinguish this from shaft misalignment."]),
        dict(name="Fluting / EDM (electrical discharge damage)",
             signature="Series of peaks between roughly 100-180 kCPM (1.6-3 kHz), commonly spaced "
                        "by the BPFO frequency, often exciting a resonance.",
             causes=["Electrical current passing through the bearing (common with VFDs and DC motors)",
                      "Etches a washboard/ripple pattern onto the raceways"],
             actions=["Install shaft grounding rings or insulated bearings to stop current from passing through the bearing.",
                      "Check VFD grounding and common-mode filtering.",
                      "Replace the damaged bearing - fluting damage doesn't reverse."]),
        dict(name="Rolling elements skidding",
             signature="Raised noise floor around 100-180 kCPM with BPFO/BPFI peaks poking "
                        "through it. More common on non-drive-end and vertical machines.",
             causes=["Insufficient load on the rolling elements", "Lubricant not performing correctly",
                      "Wrong bearing selection for the application (common with cylindrical roller bearings)"],
             actions=["Re-grease and monitor for improvement.",
                      "Listen for an audible skidding sound and check for a temperature change (IR camera).",
                      "Review bearing selection if skidding recurs after re-lubrication."]),
        dict(name="Inner race sliding on shaft",
             signature="Raised 3X peak with harmonics (6X, 9X...).",
             causes=["Incorrect bearing fit/installation - inner race not gripping the shaft tightly enough"],
             actions=["Re-fit the bearing with correct interference fit, or sleeve/build up the shaft.",
                      "Verify with a strobe or shaft/race timing marks before disassembly."]),
        dict(name="Outer race loose in housing",
             signature="Elevated 4X peak.",
             causes=["Incorrect bearing fit/installation - outer race not gripping the housing tightly enough",
                      "Worn or oversized housing bore"],
             actions=["Re-fit the bearing with correct housing tolerance, or repair/sleeve the housing bore.",
                      "Verify with timing marks on housing and outer race before disassembly."]),
    ]),

    ("Journal (Sleeve) Bearings", "Fluid-film bearing wear and oil-induced instability", [
        dict(name="Wear / excessive clearance",
             signature="1X and harmonics; noise floor may lift. Half-order and one-third-order "
                        "harmonics in more severe cases.",
             causes=["Bearing bore wear increasing clearance", "Poor lubricant film due to wear"],
             actions=["Inspect and measure bearing clearance against OEM spec.",
                      "Re-babbitt or replace the bearing if clearance is out of tolerance."]),
        dict(name="Oil whirl",
             signature="Strong sub-synchronous peak between 0.38X-0.48X radial (never exactly 0.5X).",
             causes=["Excessive bearing clearance combined with light radial load",
                      "Oil film builds up and forces the journal to orbit within the bearing"],
             actions=["Increase radial load or reduce bearing clearance if practical.",
                      "Consider a bearing redesign (e.g. tilting-pad) if oil whirl is chronic.",
                      "Review oil viscosity/supply pressure."]),
    ]),

    ("Looseness", "Excessive clearance between rotating or stationary machine elements", [
        dict(name="Rotating looseness",
             signature="Large number of 1X harmonics, sometimes past 10X; noise floor rises from "
                        "impacting. Phase is erratic/unsteady.",
             causes=["Excessive clearance in a rolling element or journal bearing",
                      "Advanced bearing wear (can appear during Stage 4 bearing failure)"],
             actions=["Inspect and correct bearing clearance or replace the worn bearing.",
                      "Confirm with time waveform - impacting shows clearly in acceleration units."]),
        dict(name="Structural looseness",
             signature="Strong 1X in the direction of least stiffness (often horizontal); harmonics "
                        "only appear if there's impacting. 180° phase between the moving part and "
                        "the stationary foundation.",
             causes=["Failed grout or cracked concrete base", "Cracked or corroded mounting hardware",
                      "Loose hold-down bolts"],
             actions=["Torque-check and re-tighten all hold-down bolts to spec.",
                      "Inspect and repair grout/foundation cracking.",
                      "Re-check after correction - resonance and unbalance can mimic this, so confirm with the "
                      "1X horizontal-vs-vertical amplitude ratio test."]),
        dict(name="Loose pedestal bearings",
             signature="1X, 2X (sometimes higher than 1X), and 3X radial; sub-harmonics (1/2X, "
                        "1/3X...) in severe cases. Erratic phase.",
             causes=["Cracked bearing pedestal", "Loose pillow-block bolts", "Faulty vibration isolators"],
             actions=["Inspect pedestal for cracks and re-torque hold-down bolts.",
                      "Replace isolators if faulty.",
                      "Don't mistake the high 2X for misalignment - confirm with erratic phase readings first."]),
    ]),

    ("Resonance", "Structural natural frequencies amplifying machine vibration", [
        dict(name="General resonance",
             signature="A strong, broad-based 'hump' at a natural frequency, typically in one "
                        "direction only; 180° phase shift as you cross through the resonant frequency.",
             causes=["A structural or rotor natural frequency lying close to running speed or "
                      "another forcing frequency (bearing defect, vane pass, etc.)"],
             actions=["Run a bump test or variable-speed run-up to confirm the natural frequency.",
                      "Stiffen, add mass to, or otherwise modify the structure to shift the natural frequency away from "
                      "running/forcing frequencies.",
                      "Reducing the forcing vibration (fix unbalance/misalignment) also reduces the resonance response."]),
        dict(name="Resonance excited by fluting/skidding",
             signature="Series of peaks between roughly 100-180 kCPM, spaced by BPFO/BPFI - a "
                        "bearing defect exciting a nearby structural natural frequency.",
             causes=["Bearing fluting (EDM) or skidding generating high-frequency energy that "
                      "happens to excite a natural frequency in that range"],
             actions=["Address the underlying bearing fault (see Rolling Element Bearings) - fixing the excitation "
                      "source resolves the resonance response.",
                      "If it recurs across bearing replacements, consider structural stiffening."]),
    ]),

    ("Rotor Rub", "Rotating parts contacting stationary components", [
        dict(name="Rotor rub",
             signature="1X and harmonics with a raised noise floor; sub-harmonics (1/2X, 1/3X...) "
                        "in severe cases. Erratic phase; waveform may show clipping.",
             causes=["Excessive shaft deflection bringing a rotating part into contact with a "
                      "stationary part (seal, labyrinth, etc.)", "Bearing failure allowing excess shaft movement",
                      "Thermal growth closing running clearances"],
             actions=["Identify and increase the running clearance at the contact point if safe to do so.",
                      "Investigate the root cause of excess shaft movement (bearing wear, misalignment, unbalance).",
                      "Shut down promptly if rub is severe - continued rubbing can quickly escalate to major damage."]),
    ]),

    ("Eccentricity", "Center of rotation offset from the geometric centerline", [
        dict(name="Eccentric rotor/gear/pulley (general)",
             signature="Strong 1X radial, especially parallel to the component; can mimic unbalance.",
             causes=["Manufacturing or machining error", "Wear creating an off-center running surface"],
             actions=["Confirm against unbalance using phase and, for belt-driven equipment, by removing "
                      "the belt and re-checking 1X.",
                      "Replace or re-machine the eccentric component - balancing alone won't fully fix eccentricity."]),
        dict(name="Eccentric motor rotor",
             signature="Peak at 2x line frequency with pole-pass sidebands around both 1X and 2xLF.",
             causes=["Rotor not concentric with the stator bore, producing a rotating variable air gap"],
             actions=["Motor current analysis can confirm alongside vibration.",
                      "Repair or replace the rotor/bearings responsible for the off-center running.",
                      "If intermittent with temperature, suspect thermal rotor bow instead (see Induction Motors)."]),
        dict(name="Eccentric motor stator (soft foot related)",
             signature="High peak at 2x line frequency (100/120 Hz), radial; strongest at the point(s) "
                        "closest to the rotor.",
             causes=["Soft foot or a warped baseplate pulling the stator out of round",
                      "Distorted motor frame from improper mounting"],
             actions=["Check and correct soft foot before anything else - this is very often the root cause.",
                      "Recheck the 2xLF peak after correcting soft foot/mounting."]),
        dict(name="Eccentric pulley or sheave",
             signature="Strong 1X radial, highest parallel to the belts; motor and driven "
                        "component show 1X at two different frequencies due to the speed ratio.",
             causes=["Sheave bore not concentric with its outside diameter",
                      "Sheave not seated true on the shaft"],
             actions=["Remove the belt and re-check 1X on the motor alone to confirm it's the sheave, not the motor.",
                      "Replace or re-true the eccentric sheave."]),
        dict(name="Eccentric gear",
             signature="High gearmesh peak with sidebands at the turning speed of the eccentric gear's shaft.",
             causes=["Gear bore not concentric with its pitch circle", "Gear not seated true on its shaft"],
             actions=["Identify which shaft's turning speed matches the sideband spacing to isolate the offending gear.",
                      "Replace the eccentric gear at the next opportunity - wear will accelerate otherwise."]),
    ]),

    ("Pumps, Fans & Compressors", "Hydraulic and aerodynamic fault sources", [
        dict(name="Blade pass / vane pass",
             signature="Peak at (number of blades or vanes) x RPM; harmonics and running-speed "
                        "sidebands possible.",
             causes=["Normal operating peak - only a concern if amplitude is rising",
                      "Uneven gap between blades/vanes and stationary diffusers",
                      "Obstructions or sharp bends in the flow path"],
             actions=["Trend the amplitude - a stable blade/vane pass peak is normal.",
                      "If rising, inspect diffuser clearances and flow path for obstructions or wear."]),
        dict(name="Flow turbulence",
             signature="Random, low-frequency vibration, typically 50-2000 CPM.",
             causes=["Turbulent flow from duct/pipe geometry, partially closed dampers/valves, "
                      "or operating far from the best-efficiency point"],
             actions=["Review system curve vs. pump/fan operating point - operating too far from BEP "
                      "increases turbulence.",
                      "Check dampers, valves, and duct/pipe transitions upstream and downstream."]),
        dict(name="Cavitation",
             signature="Random, high-frequency 'noise' - a broadband hump in the high-frequency "
                        "range, plus a hump around the blade/vane pass peak. Often audible as a "
                        "gravel-like rattling sound.",
             causes=["Insufficient suction pressure / NPSH starvation", "Clogged or undersized suction line",
                      "Entrained air"],
             actions=["Check suction pressure/NPSH available against the pump's NPSH required.",
                      "Inspect suction strainer/line for restriction, and check for air entrainment.",
                      "Do not run for extended periods while cavitating - it erodes impeller and casing surfaces."]),
        dict(name="Pump off-design flow / impeller wear",
             signature="Elevated vane pass and/or broadband vibration when operating well away "
                        "from the pump's best-efficiency point (BEP).",
             causes=["Pump operating outside its designed flow/pressure window",
                      "Impeller wear or corrosion", "Excessive clearance between impeller and casing"],
             actions=["Maintain the pump's operating flow and pressure within the designed parameters.",
                      "If the flow is within specifications, inspect the pump impeller for signs of corrosion.",
                      "Measure the air gaps between the impeller and the casing to ensure proper clearances."]),
        dict(name="Roots blower lobe clearance",
             signature="Elevated vibration at lobe-pass frequency (number of lobes x shaft speed) "
                        "with a growing noise floor as clearance increases.",
             causes=["Excessive clearance between male and female lobes", "Lobe wear from contamination",
                      "Timing gear wear affecting lobe synchronization"],
             actions=["Verify the lobe root clearances for both male and female lobes and correct any deviations.",
                      "Check timing gear condition if lobe synchronization is suspect."]),
    ]),

    ("Induction Motors", "AC induction motor rotor and stator faults", [
        dict(name="Rotor bar faults - Type I",
             signature="Pole-pass sidebands around 1X and its harmonics (1X-4X); needs a "
                        "high-resolution spectrum to resolve.",
             causes=["Cracked/broken rotor bars, shorted end rings or laminations, loose rotor bar joints"],
             actions=["Confirm with motor current signature analysis (current clamp spectrum around line frequency).",
                      "Plan rotor repair/replacement - broken bars typically worsen under load cycling."]),
        dict(name="Rotor bar faults - Type II",
             signature="Elevated rotor bar pass frequency (RBF) with 2x-line-frequency sidebands.",
             causes=["Cracked/broken rotor bars", "Arcing between rotor bars and end ring",
                      "Porosity in rotor bar castings"],
             actions=["Confirm with motor current signature analysis.",
                      "Plan rotor repair/replacement."]),
        dict(name="Rotor bow",
             signature="High 1X radial, similar to static unbalance; may also show 2x-line-frequency "
                        "peak with pole-pass sidebands. Often disappears once the rotor cools.",
             causes=["Localized heating from broken rotor bars or uneven current flow, causing "
                      "the rotor to bow thermally"],
             actions=["Re-check vibration cold vs. running - a fault that disappears on cooldown points to rotor bow.",
                      "Investigate the electrical cause (broken bars, uneven phase currents) rather than just re-balancing."]),
        dict(name="Loose rotor bars",
             signature="Peak at rotor bar pass frequency (RBF) with 2x-line-frequency sidebands - "
                        "common enough on its own that only a rising trend is a concern.",
             causes=["Rotor bar joints loosening over time or thermal cycling"],
             actions=["Trend the RBF peak amplitude - investigate further only if it's increasing.",
                      "Plan rotor repair if the trend continues to rise."]),
        dict(name="Loose rotor (slipping on shaft)",
             signature="High 1X and harmonics, often intermittent and load/temperature dependent.",
             causes=["Rotor core has worked loose on the shaft, often after a load or voltage transient"],
             actions=["Do not confuse with rotating looseness in a bearing - check both.",
                      "Rotor needs to be re-secured to the shaft (shop repair) - not a field fix."]),
        dict(name="Loose stator windings",
             signature="High 2x-line-frequency (100/120 Hz) radial vibration.",
             causes=["Stator winding coils not fully secured in the slots"],
             actions=["Address promptly - loose windings abrade insulation and can lead to a ground fault or short.",
                      "Schedule a stator re-wedge/re-tightening at the motor shop."]),
        dict(name="Shorted laminations",
             signature="High 2x-line-frequency radial with pole-pass sidebands around 1X.",
             causes=["Insulation breakdown between stator/rotor laminations causing local heating and warping"],
             actions=["Motor shop repair required - laminations need re-insulating or the stack replacing.",
                      "Monitor motor temperature in the meantime; this fault tends to worsen under heat."]),
        dict(name="Loose connections",
             signature="High 2x-line-frequency with sidebands at one-third line frequency (16.66/20 Hz).",
             causes=["A loose electrical connection causing a phasing/single-phasing-like problem"],
             actions=["Inspect and re-torque motor terminal box and supply connections.",
                      "Thermal-scan connections under load to find the loose/hot joint."]),
    ]),

    ("Synchronous & DC Motors", "Field-specific electrical fault signatures", [
        dict(name="Loose stator coils (synchronous motors)",
             signature="High coil-passing frequency (CPF) with possible 1X sidebands.",
             causes=["Stator coils not fully secured, generating vibration at coil-passing rate"],
             actions=["Schedule stator coil re-tightening/re-wedging at the motor shop."]),
        dict(name="DC grounding fault",
             signature="Elevated line-frequency peak (50/60 Hz), which shouldn't normally be present "
                        "in a DC motor spectrum.",
             causes=["Broken armature (rotor) windings", "Commutator risers not correctly bonded to the armature"],
             actions=["Electrical shop inspection of armature windings and commutator bonding required."]),
        dict(name="SCR tuning fault",
             signature="1X sidebands around the 1x and 2x SCR firing frequency peaks.",
             causes=["SCR firing circuit tuning out of adjustment, causing amplitude to rise/fall once per revolution"],
             actions=["Have the SCR drive re-tuned by an electrical technician.",
                      "Confirm with a time waveform showing amplitude rising and falling at 1X."]),
        dict(name="Phase loss",
             signature="Peaks at 1/3x and 2/3x SCR firing frequency, alongside the normal 1x SCR peak.",
             causes=["A blown fuse or failed firing card dropping one phase of the SCR circuit"],
             actions=["Check fuses and firing cards on the DC drive.",
                      "Restore the missing phase - do not continue running two-phase for extended periods."]),
        dict(name="Loose connectors / control card fault",
             signature="Harmonics of line frequency (50/60 Hz) that shouldn't normally be present.",
             causes=["Loose electrical connectors", "Shorted control card", "Fuse or firing card problems"],
             actions=["Inspect and re-torque connections; test/replace the control card if connections check out."]),
        dict(name="DC motor hunting",
             signature="Broader, lower 1X peak than normal with sidebands around the SCR firing "
                        "frequency, spaced by the RPM fluctuation amount.",
             causes=["Fault in the speed comparator card causing small, continuous RPM fluctuation"],
             actions=["Have the speed control/comparator card inspected and repaired.",
                      "Confirm with a live high-resolution spectrum showing the 1X peak drifting in frequency."]),
    ]),

    ("Gearbox", "Gear mesh and tooth-condition faults", [
        dict(name="Gear mesh (normal reference)",
             signature="A peak at gear mesh frequency (teeth x shaft speed) is normal - only "
                        "rising amplitude, new harmonics, or growing sidebands indicate a developing fault.",
             causes=["Baseline condition, not itself a fault"],
             actions=["Trend the gear mesh peak and its sidebands over time rather than reacting to a single reading.",
                      "Use time waveform analysis for the best early diagnosis of a developing gear fault."]),
        dict(name="Tooth wear",
             signature="Growing sidebands (spaced at the worn gear's turning speed) around gear "
                        "mesh frequency; broader-based natural-frequency peak.",
             causes=["Progressive wear on the gear teeth surfaces"],
             actions=["Sample gearbox oil for wear metals and check via wear particle analysis.",
                      "Plan gear/gearbox inspection or replacement based on trend severity."]),
        dict(name="Tooth load",
             signature="Gear mesh peak amplitude increases without new sidebands or harmonics appearing.",
             causes=["Increased load being transmitted through the gearbox",
                      "Not necessarily a fault - can simply reflect a process load change"],
             actions=["Confirm against actual process load before assuming a fault.",
                      "If load hasn't changed, check for alignment or mounting issues increasing effective load."]),
        dict(name="Eccentric gears",
             signature="One dominant sideband (rather than a full family) on either side of gear "
                        "mesh, at the eccentric gear's turning speed.",
             causes=["Gear bore not concentric with its pitch circle"],
             actions=["Identify the offending gear via sideband spacing and plan its replacement.",
                      "Check for resulting backlash/natural-frequency excitation."]),
        dict(name="Misaligned gears",
             signature="2X gear mesh peaks and 2X turning-speed sidebands elevated more than 1X.",
             causes=["Gearbox input/output shafts not properly aligned to their mating shafts"],
             actions=["Check and correct shaft alignment into and out of the gearbox.",
                      "Inspect for uneven tooth wear pattern (angular contact wear) confirming misalignment."]),
        dict(name="Gear backlash",
             signature="1X sidebands around gear mesh, often with a broad-based peak from an "
                        "excited gear natural frequency.",
             causes=["Excess backlash, often related to gear eccentricity or wear"],
             actions=["Measure and compare backlash against OEM spec.",
                      "Replace worn gears if backlash exceeds tolerance."]),
        dict(name="Cracked or broken tooth",
             signature="High 1X radial at the damaged gear's turning speed; a new gear "
                        "natural-frequency peak with 1X sidebands.",
             causes=["A cracked or broken gear tooth"],
             actions=["Stop and inspect as soon as practical - a broken tooth can rapidly damage adjacent teeth.",
                      "Time waveform / time-synchronous averaging gives the clearest confirmation before teardown.",
                      "Check oil/wear-particle analysis for metal fragments."]),
        dict(name="Hunting tooth frequency",
             signature="A distinct low-frequency peak (audible as a 'growl'), plus its second harmonic.",
             causes=["Same tooth pairs repeatedly meshing together (common with integer gear ratios), "
                      "causing localized wear from a manufacturing or handling defect on specific teeth"],
             actions=["Inspect the specific teeth implicated by the hunting tooth frequency calculation.",
                      "Consider a gear set with a non-integer ratio on replacement to avoid repeat-tooth wear."]),
    ]),

    ("Couplings", "Coupling-specific fault signatures", [
        dict(name="Coupling unbalance",
             signature="High 1X radial on both sides of the coupling; sinusoidal waveform; 90° "
                        "V-to-H phase shift.",
             causes=["Lost coupling part", "Incorrect assembly", "Key fitted incorrectly",
                      "Excess grease in a gearflex coupling"],
             actions=["Inspect the coupling for missing parts, incorrect keying, or grease imbalance.",
                      "Balance the coupling in place if the cause can't be found/corrected."]),
        dict(name="Non-parallel coupling faces",
             signature="High 1X (with a smaller 2X) axial; 180° phase shift axially across the coupling.",
             causes=["Coupling flange faces not machined/mounted parallel (coupling itself is not true)"],
             actions=["Check coupling face runout with a dial indicator.",
                      "Replace or re-machine the coupling if faces aren't parallel within tolerance."]),
        dict(name="Coupling wear",
             signature="Series of turning-speed harmonics, similar to looseness, but visible on "
                        "both coupled components rather than just one.",
             causes=["Wear in a flexible coupling element (rubber, grid, gear teeth, etc.)"],
             actions=["Inspect the coupling element for wear and replace if worn.",
                      "Distinguish from bearing/mounting looseness by checking whether both machines show the harmonics."]),
        dict(name="Misaligned 3-jaw coupling",
             signature="High 3X radial, often with 6X and 9X also present.",
             causes=["3-jaw coupling misalignment"],
             actions=["Re-align the coupled shafts.",
                      "Inspect the jaw/spider element for wear once misalignment is corrected."]),
        dict(name="Locked gearflex coupling",
             signature="High axial vibration, often with a 3X peak; may change suddenly between "
                        "'locked' and normal states.",
             causes=["Incorrect or insufficient lubrication preventing the gear teeth from sliding freely"],
             actions=["Re-lubricate with the correct grade of coupling grease.",
                      "If it keeps locking, inspect the coupling teeth for wear or damage preventing free sliding."]),
    ]),

    ("Belt Drives", "V-belt and sheave fault signatures", [
        dict(name="Worn belts",
             signature="Peak at belt (fundamental pass) frequency and harmonics - often the 2nd "
                        "harmonic is the highest.",
             causes=["Belt wear or looseness (age, incorrect tension)"],
             actions=["Check belt tension against spec and re-tension if slack.",
                      "Inspect belts for cracking, glazing, or uneven wear and replace as a matched set if worn."]),
        dict(name="Sheave misalignment",
             signature="High 1X axial on both the driving and driven component.",
             causes=["Sheaves not aligned to each other (offset, angular, or twisted)"],
             actions=["Re-align sheaves using a straightedge or laser belt-alignment tool.",
                      "Recheck belt tension after alignment, since realignment can change effective tension."]),
        dict(name="Belt resonance",
             signature="High 1X radial with a broader-than-normal peak base, where the belt's "
                        "natural frequency coincides with a sheave RPM.",
             causes=["Belt natural frequency happens to coincide with driving or driven sheave speed"],
             actions=["Adjust belt tension or length to shift its natural frequency away from running speed.",
                      "Confirm with a run-up test - amplitude will spike sharply as speed passes through resonance."]),
    ]),
]
