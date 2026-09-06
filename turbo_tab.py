# -*- coding: utf-8 -*-
"""
Turbomachinery Insights - a browsable learning-reference tool for CM Toolkit.

Unlike CM/DX (signature-driven diagnostics) or the calculators, this tool is
purely educational: short, plain-English write-ups of the rotordynamics
concepts and fault mechanisms that are specific to (or especially important
on) turbomachinery - compressors, turbines, and high-speed rotating
equipment generally running on fluid-film bearings with proximity-probe
monitoring.

Content here is written from general condition-monitoring/rotordynamics
practice (API 670 monitoring conventions, standard turbomachinery and
vibration-analysis references, ISO 18436-2/CAT II style fault-symptom
tables) in the author's own words - no text is lifted from any single
source.

The screen opens on a row of category pill-tabs (Fundamentals, Bearings &
Instabilities, Aerodynamic & Hydraulic, Common Faults, Diagnostics & Plots,
plus an "All" tab) so the topic list underneath can be filtered down to
whatever the person is currently working on. Tapping a topic still opens
the same style of detail popup as before - Overview / Key Points / Practical
Tip - mirroring cmdx_tab.py's ComponentsScreen pattern.
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.core.window import Window

from theme import RoundedButton, NavCard, PillButton

# ------------------------------------------------------------------
# COLORS - a distinct accent (crimson/turbine-red) not used by the other
# four tools (blue=CM/DX, teal=Rotor, amber=Bearing, purple=Laser)
# ------------------------------------------------------------------
BG = (0.078, 0.09, 0.102, 1)
PANEL = (0.11, 0.129, 0.149, 1)
TEXT = (0.9, 0.91, 0.925, 1)
MUTED = (0.545, 0.584, 0.631, 1)
ACCENT = (0.867, 0.267, 0.298, 1)   # crimson


def body_label(text, color=TEXT):
    lbl = Label(text=text, color=color, size_hint_y=None, halign="left", valign="top")
    lbl.bind(width=lambda inst, val: setattr(lbl, "text_size", (val, None)))
    lbl.bind(texture_size=lambda inst, val: setattr(lbl, "height", val[1] + dp(6)))
    return lbl


# ------------------------------------------------------------------
# LEARNING CONTENT
# Each entry: name, category tag (shown as the card subtitle), overview
# paragraph, key_points (list), tip (one practical takeaway).
# ------------------------------------------------------------------
TURBO_TOPICS = [
    dict(name="What Is Turbomachinery?",
         category="Fundamentals",
         overview=("Turbomachinery refers to rotating equipment that transfers energy "
                    "between a rotor and a fluid - steam/gas turbines, centrifugal and "
                    "axial compressors, and high-speed pumps. Compared to general "
                    "industrial machinery, these units typically run at much higher "
                    "speeds, sit on fluid-film (journal) bearings rather than rolling-"
                    "element bearings, and are monitored with non-contact proximity "
                    "probes reading the shaft directly instead of casing-mounted "
                    "accelerometers."),
         key_points=[
             "High rotating speeds often place the machine above its first critical speed.",
             "Fluid-film bearings mean the shaft rides on an oil film, not a fixed raceway.",
             "Monitoring standard is API 670, not the accelerometer-based ISO 10816 approach.",
             "A single train (turbine-compressor-gearbox) may have 10-20+ probes.",
         ],
         tip="When you see 'X-Y proximity probes' or 'keyphasor' in a report, you're looking at "
             "shaft relative displacement, not casing velocity - the two aren't directly comparable."),

    dict(name="Rotordynamics & Critical Speed",
         category="Fundamentals",
         overview=("Every rotor has natural (critical) speeds where a lateral resonance "
                    "amplifies vibration - conceptually the same phenomenon as structural "
                    "resonance, but here the 'structure' is the spinning shaft itself, "
                    "supported by bearing stiffness and damping. Turbomachinery is "
                    "deliberately designed to run either well below its first critical "
                    "speed ('rigid rotor') or comfortably between criticals ('flexible "
                    "rotor'), and startup/shutdown always means passing through one or "
                    "more critical speeds."),
         key_points=[
             "Vibration peaks sharply near a critical speed, with a fast phase shift through it.",
             "Bearing oil-film stiffness/damping - not just the shaft - sets where criticals fall.",
             "Startup and coastdown are the highest-risk windows for critical-speed excitation.",
             "A Bode plot (amplitude & phase vs. speed) is the standard way to see this.",
         ],
         tip="If a unit vibrates worst at a specific RPM during startup and then smooths out at "
             "operating speed, suspect a critical speed rather than a running-speed fault."),

    dict(name="Oil Whirl & Oil Whip",
         category="Bearings & Instabilities",
         overview=("Oil whirl is a subsynchronous vibration (roughly 0.42x-0.48x running "
                    "speed) caused by the oil film in a journal bearing dragging the shaft "
                    "around inside its own wedge of oil, rather than the shaft simply "
                    "riding stably in it. If the whirl frequency ever coincides with the "
                    "rotor's first critical speed, it can lock in and grow uncontrollably - "
                    "this locked-in condition is called oil whip, and is far more severe."),
         key_points=[
             "Classic signature: a sharp non-synchronous peak near 0.42x-0.48x running speed.",
             "Oil whirl frequency tracks with running speed; oil whip frequency locks near the rotor critical.",
             "More likely at light bearing loads, low oil viscosity, or excessive bearing clearance.",
             "Whip can escalate quickly and is considered a machine-protection-trip-worthy fault.",
         ],
         tip="Don't confuse a whirl/whip peak with rotating stall or looseness - check whether the "
             "frequency stays a fixed fraction of running speed (whirl) or locks to a fixed Hz value (whip)."),

    dict(name="Surge & Rotating Stall (Compressors)",
         category="Aerodynamic & Hydraulic",
         overview=("Centrifugal and axial compressors can become aerodynamically unstable "
                    "when operated too far left on their performance curve (low flow, high "
                    "head). Rotating stall is a localized flow separation that rotates "
                    "around the impeller/diffuser at a fraction of shaft speed; if flow "
                    "drops further, the whole machine can surge - a violent flow reversal "
                    "that repeats cyclically and shakes the entire train, not just the "
                    "compressor."),
         key_points=[
             "Rotating stall shows as a subsynchronous peak, often 0.6x-0.9x running speed.",
             "Surge is far more dramatic: low-frequency (often <10 Hz) pulsation with audible banging.",
             "Both are process/aerodynamic faults, not mechanical ones - vibration is a symptom.",
             "Repeated surge cycling causes real mechanical damage (seals, thrust bearing, blades).",
         ],
         tip="If vibration correlates with flow/head swings on the process trend rather than a fixed "
             "mechanical frequency, loop in process engineering - this isn't a balance or alignment fix."),

    dict(name="Blade & Vane Pass Frequency",
         category="Aerodynamic & Hydraulic",
         overview=("Every rotor with blades or vanes generates a pressure pulse each time a "
                    "blade passes a fixed point (a diffuser vane, volute tongue, or nozzle) - "
                    "this shows up as a peak at blade-pass frequency (number of blades x "
                    "running speed) and its harmonics. Some level is normal and expected; the "
                    "concern is when amplitude rises over time or sidebands appear around it."),
         key_points=[
             "Frequency = (number of blades or vanes) x running speed.",
             "Rising amplitude at a constant blade-pass frequency often means clearance/gap changes.",
             "Sidebands around blade-pass frequency can indicate uneven blade loading or a cracked/missing blade.",
             "Radial gap between impeller and diffuser/volute strongly affects blade-pass amplitude.",
         ],
         tip="Trend blade-pass amplitude over time rather than judging a single reading - a slow, "
             "steady rise is the more useful early-warning signal than the absolute value."),

    dict(name="Rotor & Seal Rub",
         category="Bearings & Instabilities",
         overview=("Rub occurs when a rotating part contacts a stationary part - most often "
                    "a labyrinth seal, but also bearings or close-clearance internal parts. "
                    "Light, intermittent rub tends to add harmonics and can look similar to "
                    "looseness; heavy, sustained rub excites the rotor's natural frequency "
                    "and can appear as a strong subsynchronous or 1/2x-order response, "
                    "sometimes with a rapid thermal bow developing on top of it."),
         key_points=[
             "Light rub: multiple running-speed harmonics, often intermittent/unstable in amplitude.",
             "Heavy rub: can excite a natural frequency response, with truncated/flattened time-waveform peaks.",
             "Thermal rub (rotor bows from frictional heating) can slowly shift 1x phase over minutes to hours.",
             "Seal rub specifically is a top cause of unplanned turbomachinery vibration trips.",
         ],
         tip="A slowly drifting 1x phase angle with no change in operating conditions is a classic "
             "thermal-rub red flag - don't dismiss it as sensor noise."),

    dict(name="Thrust Bearing Wear & Axial Position",
         category="Bearings & Instabilities",
         overview=("Turbomachinery trains carry continuous axial (thrust) loads from "
                    "pressure differentials across impellers/blades, carried by a thrust "
                    "bearing - almost always monitored separately from radial vibration, "
                    "via an axial position (proximity) probe rather than a velocity or "
                    "acceleration sensor. Because thrust-pad babbitt wear is often gradual, "
                    "axial position trending is one of the most valuable long-term health "
                    "indicators on a turbomachinery train."),
         key_points=[
             "Monitored as axial shaft position (mils/mm), not vibration amplitude.",
             "Gradual position drift toward the alarm/trip limit indicates progressive pad wear.",
             "A sudden position jump suggests pad failure or a process upset overloading the thrust bearing.",
             "Thrust bearing failure is one of the few faults that can destroy a machine in seconds.",
         ],
         tip="Trend axial position on the same chart across shutdowns/startups - a baseline that "
             "creeps further from zero each run cycle is worth a bearing inspection before it trips."),

    dict(name="Proximity Probes & API 670 Basics",
         category="Fundamentals",
         overview=("API 670 is the standard most turbomachinery trains are monitored to. "
                    "Unlike casing-mounted accelerometers (ISO 10816 style), API 670 systems "
                    "use eddy-current proximity probes reading the shaft directly, typically "
                    "in X-Y pairs at each bearing plus a keyphasor (once-per-turn reference) "
                    "and axial position probes - giving both vibration amplitude and shaft "
                    "orbit/phase information that casing sensors can't provide."),
         key_points=[
             "X-Y probe pairs (usually 90 deg apart) let you plot the shaft's actual orbit, not just amplitude.",
             "The keyphasor provides the once-per-rev timing mark used for all phase measurements.",
             "Readings are shaft-relative displacement (peak-to-peak, mils or microns), not casing velocity.",
             "API 670 also defines alarm/trip logic (e.g. 2-out-of-3 voting) for machine protection, not just monitoring.",
         ],
         tip="If you're used to reading in./sec or mm/s from CM/DX-style accelerometer work, remember "
             "proximity-probe data is displacement (mils/microns pk-pk) - don't compare the numbers directly."),

    dict(name="Torsional Vibration",
         category="Fundamentals",
         overview=("All the fault types above are lateral (radial/axial) vibration - shaft "
                    "bending or moving sideways/along its axis. Torsional vibration is "
                    "different: it's a twisting oscillation along the shaft's rotational "
                    "axis, invisible to standard radial vibration sensors, and is a "
                    "particular concern on trains with gearboxes, couplings, or "
                    "variable-frequency drives, where torque pulsations can fatigue "
                    "shafts and coupling elements over time with no visible radial symptom."),
         key_points=[
             "Cannot be seen on ordinary radial vibration or proximity-probe data - needs dedicated torsional analysis.",
             "VFD-driven trains and gear-coupled trains are the highest-risk candidates.",
             "Torsional fatigue failures can occur with completely normal-looking radial vibration trends.",
             "Usually addressed at the design stage (torsional analysis) rather than retrofitted after the fact.",
         ],
         tip="If a gear or VFD-driven coupling keeps failing with no radial vibration explanation, "
             "torsional resonance is worth raising with a specialist, since it won't show up in this app's other tools."),
    dict(name="Orbit Plots: Seeing Shaft Motion in 2D",
         category="Diagnostics & Plots",
         overview=("A single vibration probe only shows motion along one axis - but a "
                    "shaft's actual path inside its bearing clearance is two-dimensional. "
                    "Mount a second probe 90 degrees from the first, in the same radial "
                    "plane, and the two signals can be combined into an orbit plot: a "
                    "closed 2-D trace of the shaft centerline's path. Orbits can be built "
                    "from raw unfiltered data (showing everything present) or from a single "
                    "filtered frequency component such as 1X (showing only that contribution)."),
         key_points=[
             "Needs two probes perpendicular to each other in the same radial plane (typically labeled X/Y).",
             "Plotted on equal X/Y scales so the trace isn't visually stretched or distorted.",
             "A positive-going signal on a probe always means the shaft moved toward that probe.",
             "Orbit shape alone never tells you which way the shaft is actually rotating - that has to come from elsewhere (a marked arrow, visual check, or cautious use of slow-roll data).",
         ],
         tip="If someone shows you only one probe's waveform and talks about 'the orbit,' ask whether "
             "a second, perpendicular probe reading actually exists - one signal alone can't produce an orbit."),

    dict(name="Keyphasor Marks & Direction of Precession",
         category="Diagnostics & Plots",
         overview=("A Keyphasor is a once-per-revolution timing reference, usually from a "
                    "notch or key sensed by a separate probe at a different axial location. "
                    "When overlaid on an orbit, it appears as a dot (the instant the timing "
                    "event occurs) breaking up an otherwise blank trace. Because the dot "
                    "marks equal time intervals, the sequence of dots shows the direction "
                    "the shaft is actually moving around its orbit - called precession - "
                    "which can be the same as (forward) or opposite to (reverse) the shaft's "
                    "physical rotation direction."),
         key_points=[
             "One Keyphasor dot appears per shaft revolution captured in the plot.",
             "The dot sequence shows precession direction, not necessarily the rotation direction.",
             "Forward precession = orbit direction matches rotation; reverse = orbit direction opposes it.",
             "On a single complex orbit, part of the path can precess forward while another part precesses in reverse.",
             "Counting dots also reveals subsynchronous/supersynchronous frequency ratios (e.g. 3 dots on the "
             "orbit for a 1/3X or 2/3X component) - handy for spotting fractional-order vibration at a glance.",
         ],
         tip="Reverse precession over even part of an orbit is worth flagging - it's associated with certain "
             "instabilities (like some rub or fluid-induced whirl conditions) and is easy to miss without the timing dot."),

    dict(name="Orbit Compensation & What Shape Tells You",
         category="Diagnostics & Plots",
         overview=("Raw shaft signals often include a 'slow roll' component - mechanical or "
                    "electrical runout that's present even at very low speed and isn't true "
                    "vibration. Compensation subtracts that baseline out, leaving an orbit "
                    "that reflects only the rotor's actual dynamic response. Beyond "
                    "compensation, orbit shape itself is diagnostic: a near-circular 1X orbit "
                    "is typical of a lightly loaded, well-behaved rotor, while a flattened or "
                    "banana-shaped orbit often points to high radial bearing load pushing the "
                    "shaft into a stiffer part of its oil film."),
         key_points=[
             "Compensation removes slow-roll runout so the orbit reflects real dynamic motion, not sensor/shaft imperfections.",
             "A 'Not-1X' orbit (running-speed component subtracted out) can reveal smaller subsynchronous or "
             "supersynchronous activity that would otherwise be hidden by a dominant 1X signal.",
             "Peak-to-peak amplitude is read by measuring across the orbit parallel to a given probe's own axis - not simply vertically or horizontally.",
             "Comparing orbits from the same location at different speeds is a practical way to spot a rotor passing through a resonance (orbit grows, then shrinks again).",
             "Comparing orbits from different axial locations at the same speed hints at the rotor's overall deflection shape along the train.",
         ],
         tip="Always look at an uncompensated orbit first. Compensation is genuinely useful, but applied "
             "incorrectly it can make a healthy rotor look faulty (or hide a real problem) - treat it as a "
             "refinement step, not the first thing you view."),

    dict(name="Journal Bearings & Eddy-Current Probes",
         category="Fundamentals",
         overview=("Journal (fluid-film) bearings - also called sleeve or Babbitt bearings - support "
                    "the shaft on a thin film of oil rather than rolling elements, which is why "
                    "turbomachinery needs a different sensing approach than rolling-element-bearing "
                    "equipment. Non-contact eddy-current probes are mounted permanently in the bearing "
                    "housing and measure the gap to the shaft using a high-frequency oscillator; within "
                    "the probe's linear range, output voltage changes proportionally with that gap."),
         key_points=[
             "Common journal bearing styles include plain, lemon/elliptical-bore, pressure-dam, offset, and tilting-pad designs.",
             "An eddy-current probe's signal has two parts: an AC component (dynamic shaft motion) and a DC component (average gap/position).",
             "Probe sensitivity is typically quoted in mV per mil of displacement - a stated 200 mV/mil probe means a 5 mil peak-to-peak shaft movement gives 1V peak-to-peak output.",
             "The probe should sit near the middle of its linear range, and two probes on the same plane should be matched in sensitivity.",
             "Casing-mounted accelerometers still have a role (showing how the housing itself moves relative to ground) but the oil film attenuates shaft motion, limiting what they reveal about the shaft directly.",
         ],
         tip="Two probes mounted 90 degrees apart (typically X horizontal, Y vertical) are what make orbit and "
             "centerline analysis possible - a single probe only gives you gap in one direction."),

    dict(name="Shaft Centerline Plots & Eccentricity Ratio",
         category="Diagnostics & Plots",
         overview=("While the orbit shows dynamic shaft motion, the average shaft centerline plot shows "
                    "where the shaft is actually sitting inside its bearing clearance - built from the DC "
                    "(position) component of the probe signal rather than the AC (vibration) component. "
                    "Tracking this position from rest through startup to full speed, and comparing cold "
                    "vs. hot or loaded vs. unloaded conditions, is one of the most effective ways to catch "
                    "bearing wear or a developing alignment problem before it shows up as vibration."),
         key_points=[
             "Needs the same two orthogonal probes as an orbit, but uses their DC output instead of AC.",
             "Eccentricity ratio (often written as the Greek letter epsilon) describes where the shaft center sits between the bearing center (ratio = 0) and the bearing wall (ratio = 1).",
             "A ratio drifting toward 0 (shaft riding too centered) can signal a stability risk; drifting toward 1 means the shaft is approaching the bearing wall.",
             "A normal startup path commonly traces up and to one side as the shaft rides up on its oil wedge - a path that looks different from that baseline is worth investigating.",
             "Overlaying the orbit for a given point on top of its corresponding centerline position ties dynamic motion and average position together in a single picture.",
         ],
         tip="If a bearing's average position keeps creeping further from its normal startup path run after run, "
             "that alone is worth flagging - it's an early wear/preload signal even before vibration amplitude rises."),

    dict(name="Reading Orbit Shape for Common Faults",
         category="Diagnostics & Plots",
         overview=("Different fault mechanisms leave recognizably different fingerprints on an orbit's "
                    "shape, especially when you compare the direct (unfiltered) orbit against its 1X-filtered "
                    "counterpart. None of these patterns are proof on their own - they're strong hints that "
                    "narrow down where to look next."),
         key_points=[
             "Unbalance: orbit grows larger but stays elliptical and dominated by 1X, so direct and filtered orbits look similar; width-to-height ratio can run up to roughly 4:1.",
             "Misalignment: orbit tends to flatten further, sometimes past a 5:1 width-to-height ratio, often with a noticeably stronger 2X component pulling the direct orbit away from the filtered 1X shape.",
             "Preload (from gravity, fluid forces, seals, piping strain, or misalignment): shaft's average position (on the centerline plot) shifts and eccentricity ratio rises; orbit can become highly elliptical or even figure-eight shaped, sometimes with reverse precession.",
             "A loose rotating part: amplitude and phase fluctuate over time as its own residual unbalance vector slowly rotates relative to the rotor's - best caught by watching a live orbit rather than a single snapshot.",
             "Rub: waveform distortion, extra harmonics of 1X, sub-order components (1/2X, 1/4X), a rising noise floor, and an orbit that flattens or develops a tear-drop edge as it worsens.",
         ],
         tip="Don't diagnose from orbit shape alone - cross-check against the centerline position and spectrum. "
             "A flattened orbit could be misalignment, preload, or rub; the accompanying centerline shift and "
             "spectrum content are what narrow it down."),

    dict(name="Sub-Synchronous Vibration: Reading the Keyphasor Dots",
         category="Diagnostics & Plots",
         overview=("When more than one Keyphasor dot appears on a filtered orbit, that's a direct sign of "
                    "sub-synchronous (less-than-1X) vibration, and both how many dots appear and which way "
                    "they drift on a live display narrow down the likely cause. This is one of the fastest "
                    "field checks available before pulling up a full spectrum."),
         key_points=[
             "Exactly 0.5X, with two dots sitting stationary on a live display, is commonly associated with a rub.",
             "Just below 0.5X, with dots slowly drifting against the direction of rotation, points toward oil whirl.",
             "Just above 0.5X, with dots drifting in the same direction as rotation, is more often linked to a structural or rotor resonance being excited.",
             "General loop-counting rule for an orbit with one timing mark: vibration frequency (as a multiple of running speed) = (number of loops plus or minus 1) / number of rotations captured - internal loops add, external loops subtract.",
             "More loops in the direct (unfiltered) orbit generally mean a stronger fractional-order component relative to 1X.",
         ],
         tip="If you only have a static snapshot, count the Keyphasor dots for the ratio; if you can watch a live "
             "orbit, the direction the dots drift is often the faster way to tell oil whirl from a resonance response."),

    dict(name="Oil Whirl vs. Oil Whip",
         category="Bearings & Instabilities",
         overview=("Both are self-excited instabilities in fluid-film (journal) bearings, but they differ "
                    "sharply in severity. Oil whirl is a subsynchronous vibration, typically in the "
                    "0.38X-0.48X range, driven by conditions like very low bearing loading, excessive "
                    "clearance, or light loading with low damping. Oil whip is what happens when that whirl "
                    "frequency locks onto a rotor's natural frequency - usually once running speed is more "
                    "than roughly twice the critical speed - turning a moderate instability into a severe, "
                    "potentially destructive one."),
         key_points=[
             "Oil whirl: frequency tracks with running speed (stays in the 0.38X-0.48X band); shows as two Keyphasor dots on the filtered orbit since it's below 0.5X.",
             "Oil whirl typically shows forward precession, with an inner loop appearing on the direct orbit and a fairly circular overall motion.",
             "Oil whip: locked onto the rotor's natural frequency rather than tracking speed; vibration can escalate to very high levels quickly.",
             "Oil whip is treated as a machine-protection-level event - severe cases can warrant an immediate shutdown rather than continued monitoring.",
             "A live display showing stationary dots near half running speed, combined with rapidly climbing amplitude, is the escalation pattern to watch for.",
         ],
         tip="Don't wait to see how far oil whirl develops before acting - because whip can follow whirl quickly "
             "once the whirl frequency nears a rotor critical, treat sustained 0.38X-0.48X vibration as worth "
             "investigating immediately, not just logging for a trend."),

    dict(name="Bode, Polar & Cascade Plots for Startup/Shutdown",
         category="Diagnostics & Plots",
         overview=("Orbits are great for a snapshot at one speed, but several other plot types exist "
                    "specifically to show how vibration evolves across a startup or coastdown. A Bode plot "
                    "graphs 1X (or nX) amplitude and phase lag against shaft speed as two stacked graphs; a "
                    "Polar plot shows the same underlying data as a single spiral trace in polar coordinates "
                    "(sometimes miscalled a Nyquist plot). Cascade and waterfall plots stack many individual "
                    "spectra - one per speed or time step - so you can watch how each frequency component "
                    "grows or fades."),
         key_points=[
             "Bode and Polar plots use the same underlying vector data; Bode separates amplitude and phase onto two axes, Polar combines them into one spiral.",
             "Both are especially useful for finding the slow-roll vector, resonance speeds, synchronous amplification factor, heavy-spot location, and rotor mode shape during a startup or coastdown.",
             "A Cascade (or waterfall) plot stacks spectra over a speed or time range, with frequency on one axis and speed/time on the other - useful for watching how various orders (1X, 2X, oil whirl, blade-pass, etc.) shift and interact.",
             "A Full Spectrum version of a cascade (built from two orthogonal probes together) separates forward from reverse-precessing components - handy for confirming whether a subsynchronous peak is whirl-like (reverse) or resonance-like (forward).",
             "A Campbell diagram is the design-side counterpart: it plots a rotor's natural frequencies against speed together with excitation lines (1X, blade-pass, oil-whirl band, gear mesh, etc.) to check for crossings that would need to be avoided.",
         ],
         tip="If a resonance crossing looks marginal on a Bode plot, check the corresponding Cascade or Full "
             "Spectrum plot too - it'll show whether anything else (a blade-pass order, oil whirl band) is "
             "converging on the same speed at the same time, which changes how concerning the crossing is."),

    # ------------------------------------------------------------------
    # Added set: CAT II-style general fault reference, rolling-element
    # bearing/electrical/drivetrain frequencies, steam whirl, cavitation,
    # and the remaining transient-plot concepts (full spectrum/waterfall,
    # cold vs. hot centerline reference, timebase/orbit runout
    # compensation) - rounding this tab out into a complete quick-reference
    # for machinery diagnostics as well as pure turbo rotordynamics.
    # ------------------------------------------------------------------

    dict(name="Unbalance",
         category="Common Faults",
         overview=("The single most common cause of machine vibration: the rotor's mass "
                    "centerline doesn't coincide with its rotation centerline, so every "
                    "revolution generates a centrifugal force that repeats once per turn. "
                    "It shows up as a clean, dominant 1X peak and is usually the first "
                    "fault ruled in or out before chasing anything more complex."),
         key_points=[
             "Dominant 1X in both horizontal and vertical radial readings is the primary signature.",
             "Phase difference (H-to-H, V-to-V) between inboard and outboard bearings should be nearly the same.",
             "Phase difference between H and V at a single bearing runs about 90 deg +/- 30 deg.",
             "High axial vibration alongside the 1X radial reading suggests an overhung rotor configuration.",
             "A rundown/coastdown test shows amplitude falling off smoothly with speed and no phase shift - if phase shifts instead, suspect something else is contributing.",
         ],
         tip="Unbalance that seems to 'develop' during continuous operation is usually a clue in itself - "
             "check for wear, a broken or missing part, or process dust/scale buildup on the rotor first, "
             "rather than jumping straight to a field balance."),

    dict(name="Misalignment",
         category="Common Faults",
         overview=("Misalignment between coupled shafts - angular, parallel (offset), or a "
                    "combination - forces the coupling to flex every revolution, generating "
                    "strong 1X and 2X (and sometimes higher) harmonics along with elevated "
                    "axial vibration. It is one of the few faults that can be confirmed "
                    "directly at standstill, with dial indicators or a laser alignment tool, "
                    "which makes it worth checking early rather than inferring from spectra alone."),
         key_points=[
             "Dominant 1X and/or 2X, 3X or higher harmonics in the spectrum.",
             "Axial amplitude often runs high - over roughly 50% of the radial amplitude.",
             "On horizontal direct-coupled machines, phase across the coupling (comparing the two shafts) is often close to 180 deg apart.",
             "Waveform stays periodic and the spectral noise floor stays lower than a comparably loose machine - useful for telling misalignment apart from looseness.",
         ],
         tip="A spectrum alone rarely proves misalignment beyond doubt - confirm with a dial-indicator or "
             "laser alignment check at standstill before committing to a coupling realignment."),

    dict(name="Mechanical Looseness",
         category="Common Faults",
         overview=("Looseness covers anything from a loose hold-down bolt or bearing fit to "
                    "a cracked frame or foundation - any condition that lets a part move more "
                    "than it should. Because the resulting motion isn't a clean sinusoid, "
                    "looseness tends to generate a rich harmonic series and a generally noisy, "
                    "somewhat unpredictable spectrum rather than one clean dominant peak."),
         key_points=[
             "Often dominant at 2X, or shows a full series of harmonics (1X, 2X, 3X, 4X...).",
             "Time waveform looks random, without clean periodic spacing between major peaks.",
             "Spectrum shows an elevated noise floor compared to a tight, well-aligned machine.",
             "Loose parts vibrating independently will show a significant phase difference between them.",
             "A gradually increasing trend over time (rather than a fixed level) is a useful supporting clue.",
         ],
         tip="Listen as well as measure - a change in noise pattern (rattling, banging) alongside a rising "
             "harmonic series is a strong looseness indicator even before the trend crosses an alarm level."),

    dict(name="Bent Rotor",
         category="Common Faults",
         overview=("A permanently bent (bowed) shaft looks a lot like unbalance on a single "
                    "spectrum, but the axial signature and rundown behavior separate the two: "
                    "a bow effectively produces a mass eccentricity that also twists the shaft "
                    "out of true along its length, so axial readings around the shaft at a "
                    "single bearing don't stay in phase with each other the way a straight, "
                    "unbalanced rotor's would."),
         key_points=[
             "Symptoms resemble unbalance on a bare spectrum - high 1X, similar rundown amplitude decay.",
             "High axial vibration is a distinguishing clue, more pronounced than typical pure unbalance.",
             "Inboard and outboard bearings vibrate axially out of phase with each other.",
             "Axial phase measured at the 12, 3, 6, and 9 o'clock positions around one bearing differs by about 90 deg from one position to the next.",
         ],
         tip="Small runout from a permanent bow can sometimes be balanced out like ordinary unbalance; a "
             "temporary bow in a flexible rotor may instead be worked out by slow-rolling the machine below "
             "its first critical speed for an extended period before a normal startup."),

    dict(name="Resonance",
         category="Common Faults",
         overview=("Resonance itself isn't a defect - every structure and rotor has natural "
                    "frequencies - but it becomes a problem the moment one of those natural "
                    "frequencies coincides with running speed or one of its harmonics, "
                    "amplifying an otherwise modest forcing vibration into a large, highly "
                    "directional response."),
         key_points=[
             "A directional 1X response is a telltale sign: horizontal amplitude much greater than vertical (or vice versa), sometimes by a factor of 4-8x or more.",
             "H-to-V phase at the resonant point tends to sit near 0 deg or 180 deg rather than a more typical intermediate value.",
             "Response is speed-dependent - a Bode plot through the resonance shows an amplitude peak together with roughly a 180 deg phase change from just below to just above it.",
             "Common fixes address the structure or support (stiffening, added mass, damping) rather than the rotor itself, since the resonance is a system characteristic, not a rotor fault.",
         ],
         tip="Don't chase resonance as if it were unbalance - a bare-metal 'as-found' bump test or a Bode "
             "plot through a speed change will confirm whether you're dealing with a structural natural "
             "frequency rather than a rotor mass problem."),

    dict(name="Electrical Faults (Motors & Generators)",
         category="Common Faults",
         overview=("On motor- or generator-driven trains, several purely electrical "
                    "conditions can produce vibration that looks mechanical at first glance. "
                    "Because these vibrations are generated by the magnetic field rather than "
                    "rotating mass, the tell-tale sign is that they vanish immediately the "
                    "instant power is removed, whereas a mechanical fault's vibration decays "
                    "only as the rotor coasts down."),
         key_points=[
             "2x line frequency indicates stator problems: stationary eccentricity, stator distortion/soft foot, or shorted stator laminations - watch for amplitude 'beats' if this is close to running speed or a harmonic of it.",
             "2x line frequency with sidebands at pole-pass frequency (poles x slip) points to rotor problems such as rotating eccentricity or localized heating; phase and amplitude will drift with time as the rotor heats.",
             "1X and harmonics with pole-pass sidebands can indicate broken rotor bars or shorted rotor laminations.",
             "Electric current spectrum analysis is a strong complementary check, particularly for detecting cracked or broken rotor bars.",
             "Synchronous speed (cpm) = (2 x supply frequency in cpm) / number of poles; slip frequency = synchronous speed - actual rotor speed.",
         ],
         tip="If a suspicious vibration disappears the instant the machine is de-energized rather than "
             "coasting down like normal mechanical vibration, treat it as electrical in origin and pull a "
             "high-resolution (zoom) FFT around 2x line frequency and pole-pass sidebands."),

    dict(name="Faulty Gear (Gear Mesh Frequency)",
         category="Common Faults",
         overview=("On gear-coupled trains, a healthy gearbox still produces a Gear Mesh "
                    "Frequency (GMF) peak - it's simply the number of teeth engaging per "
                    "revolution. The diagnostic question is whether GMF and its harmonics "
                    "stay low and stable, or grow and pick up sidebands that point to tooth "
                    "wear, pitting, or a cracked/broken tooth."),
         key_points=[
             "GMF = number of teeth on the faulty gear x that gear's running speed.",
             "A rising GMF amplitude and harmonics over time tracks general wear or pitting.",
             "GMF modulated by 1X sidebands of the faulty gear (peaks appearing at GMF minus 1X and GMF plus 1X) points to an eccentric or damaged individual gear.",
             "A single cracked or broken tooth tends to show as a distinct once-per-revolution impact in the time waveform, more than in the spectrum alone.",
         ],
         tip="Check the time waveform alongside the spectrum for gear problems - a periodic impact spike "
             "at shaft rate is often clearer evidence of a localized tooth defect than the GMF sidebands are."),

    dict(name="Belt & Sheave Defects",
         category="Common Faults",
         overview=("On belt-driven auxiliary equipment (fans, some pumps) rather than "
                    "directly coupled turbomachinery, belt wear, looseness, mismatch, or "
                    "sheave eccentricity produce their own characteristic frequencies, "
                    "distinct from - and usually well below - the running-speed orders seen "
                    "on the shafts themselves."),
         key_points=[
             "Belt frequency = (pi x pulley rpm x pitch diameter) / belt length - worn, loose, or mismatched belts excite this frequency and its harmonics.",
             "Belt or sheave misalignment tends to show up as high 1X vibration specifically in the axial direction.",
             "An eccentric (out-of-round) pulley produces high 1X vibration at that pulley's own running speed, with a directional phase pattern.",
             "An eccentric pulley's own vibration can be reduced by balancing it, but the belt itself will keep vibrating at belt frequency until any runout is corrected.",
         ],
         tip="Belt-frequency peaks sit below shaft running speed and won't match any shaft's 1X - if an "
             "unexplained low subsynchronous peak shows up on belt-driven auxiliary equipment, calculate "
             "belt frequency from pulley rpm, pitch diameter, and belt length before assuming it's a rotor issue."),

    dict(name="Steam Whirl Instability (Alford Force)",
         category="Bearings & Instabilities",
         overview=("Distinct from oil whirl, steam whirl (sometimes called the Alford force "
                    "effect) is an aerodynamic - not lubrication-driven - instability seen in "
                    "steam turbines. Non-uniform clearance around blade tips or seals means "
                    "steam leaks unevenly around the circumference, generating a net "
                    "destabilizing force that pushes the rotor in a whirling motion, most "
                    "commonly at high loads where leakage flow and pressure differentials "
                    "are greatest."),
         key_points=[
             "Dominant sub-harmonic peaks, often near 0.5X, sometimes appearing as a cluster of varying-amplitude sub-harmonic peaks on a live spectral display.",
             "Forward sub-harmonic (whirl-direction) components dominate, similar in appearance to oil whirl on a spectrum alone.",
             "Overall vibration levels fluctuate rather than sitting at a steady value.",
             "Amplitude is load-dependent - generally worse at high load - so a common operational mitigation is imposing a load restriction on the machine.",
         ],
         tip="Don't assume every 0.5X-ish peak on a steam turbine is oil whirl - if amplitude tracks load "
             "rather than bearing condition, and load restriction calms it down, steam/seal clearance "
             "effects (not the oil film) are the more likely driver."),

    dict(name="Cavitation & Suction/Discharge Recirculation",
         category="Aerodynamic & Hydraulic",
         overview=("On pumps and other hydraulic machinery, operating far off the best "
                    "efficiency point can cause the liquid itself to misbehave - cavitation "
                    "(vapor bubbles forming and violently collapsing) or internal "
                    "recirculation at the suction or discharge. Both are process/hydraulic "
                    "conditions rather than mechanical defects, but left uncorrected they "
                    "erode impellers and volutes and can excite structural resonances."),
         key_points=[
             "Cavitation generates broadband, high-frequency vibration riding on top of the normal vane-pass signature, along with a characteristic crackling or 'gravel' noise.",
             "Suction or discharge recirculation shows as broadband, non-synchronous vibration at low frequencies, with the overall level fluctuating rather than staying steady.",
             "Recirculation-driven vibration changes with system resistance - in some vertical mixed-flow pumps, vibration can rise sharply as discharge pressure (system resistance) increases.",
             "Both problems can excite substructural resonances if the broadband energy happens to land on a natural frequency of the piping or support structure.",
         ],
         tip="Fixing cavitation or recirculation is a process/hydraulic exercise, not a balance or "
             "alignment job - suction conditions, guide vanes, or vortex breakers are the usual remedies, "
             "and the pump OEM should be consulted before modifying the wet end."),

    dict(name="Rolling-Element Bearing Defect Frequencies",
         category="Bearings & Instabilities",
         overview=("Auxiliary equipment on a turbomachinery train (lube oil pumps, cooling "
                    "fans, some gearbox-driven accessories) often still rides on rolling-"
                    "element rather than fluid-film bearings. A faulty anti-friction bearing "
                    "generates one of four non-synchronous defect frequencies, each tied to a "
                    "specific bearing component and calculable purely from bearing geometry "
                    "and running speed."),
         key_points=[
             "Fundamental Train Frequency (FTF): cage defect.",
             "Ball Spin Frequency (BSF): defect in a rolling element (ball or roller).",
             "Ball Pass Frequency Outer race (BPFO): outer race defect.",
             "Ball Pass Frequency Inner race (BPFI): inner race defect.",
             "All four are functions of bearing geometry (ball/roller diameter Db, pitch diameter Dp, contact angle, number of elements Z) and are always non-synchronous - they will not line up with 1X, 2X, etc.",
             "These frequencies aren't always visible on a normal vibration spectrum; acceleration enveloping/demodulation techniques are often needed to bring them out, along with listening for characteristic noise.",
         ],
         tip="If a suspected bearing-defect peak lines up almost exactly with an integer multiple of "
             "running speed, look again - true bearing defect frequencies are non-synchronous by nature, "
             "so a clean integer match points toward a different cause."),

    dict(name="Shaft Centerline: Cold vs. Hot References",
         category="Diagnostics & Plots",
         overview=("The average shaft centerline plot is built from the DC (position) "
                    "component of the probe signal, referenced against a baseline voltage "
                    "recorded when the rotor is resting at the bottom of its bearing "
                    "clearance. On machines that run hot (steam and gas turbines especially), "
                    "which reference condition - cold or hot - is used for that baseline "
                    "makes a real difference in how the resulting plot should be read."),
         key_points=[
             "A reference taken under cold conditions before a cold startup makes thermal growth of the casing and structure look like the rotor is drifting within its bearing clearance as the machine warms up - it usually isn't.",
             "The most reliable check for correct compensation: at low speed there is essentially no dynamic force on the rotor, so a properly referenced plot should show the rotor sitting very close to the plot's center (near-zero apparent displacement) at slow roll.",
             "Best practice where possible is to collect the DC reference from a hot shutdown and use that as the baseline, so cold-vs-hot thermal growth doesn't get misread as rotor movement.",
             "A shutdown trace that returns close to the plot's origin at low speed confirms the reference was taken correctly; one that ends up far from the origin usually reflects a mismatched cold/hot reference rather than an actual bearing problem.",
         ],
         tip="Before concluding a rotor 'moved' within its bearing clearance during warm-up, check whether "
             "the shaft centerline reference voltages were taken cold or hot - that mismatch alone can "
             "produce a very convincing-looking (but misleading) displacement trace."),

    dict(name="Transient Runout Compensation (Timebase & Orbit)",
         category="Diagnostics & Plots",
         overview=("The slow-roll vector used to compensate a Bode or Polar plot is a single "
                    "1X amplitude-and-phase value, but the underlying runout it represents is "
                    "actually a full waveform, not just a simple sine wave - so timebase and "
                    "orbit plots need their own, more direct compensation approach: "
                    "subtracting an entire low-speed reference waveform, not just a vector."),
         key_points=[
             "During a startup or shutdown transient, a waveform captured at very low ('slow roll') speed is assumed to represent pure runout, unaffected by real dynamic forces.",
             "That slow-roll waveform is subtracted point-by-point from a waveform captured at any higher speed, leaving only the actual rotor vibration.",
             "Because an overall orbit is just two such waveforms (X and Y) combined, the same subtraction process compensates the orbit as well - revealing the true dynamic path once runout is removed.",
             "Uncompensated orbits and waveforms at running speed can look distorted or irregular purely from runout - always suspect this before concluding the rotor itself is misbehaving.",
         ],
         tip="If an orbit or waveform only starts looking clean after runout compensation is applied, treat "
             "that as confirmation the 'defect' was largely a runout artifact - but only trust the "
             "compensation if a genuine low-speed slow-roll waveform was actually captured during that run."),

    dict(name="Spectrum, Full Spectrum & Waterfall/Cascade Plots",
         category="Diagnostics & Plots",
         overview=("Beyond the orbit, several frequency-domain plots round out a full "
                    "diagnostic picture. The ordinary spectrum (via FFT) shows amplitude vs. "
                    "frequency for one probe at a time, discarding phase information in the "
                    "process. The Full Spectrum combines both orthogonal probes and rotation "
                    "direction into one plot with forward and reverse frequency axes, "
                    "recovering the orbit-shape and precession information an ordinary "
                    "spectrum throws away. Waterfall (spectra vs. time) and Cascade (spectra "
                    "vs. speed) plots stack many individual spectra so trends across an event "
                    "or startup/shutdown become visible at a glance."),
         key_points=[
             "An FFT only reconstructs a signal from sine components - it doesn't prove the vibration truly occurs at every displayed frequency, especially for non-sinusoidal or impact-type signals with lots of harmonics.",
             "A random/non-periodic signal (an intermittent impact, for instance) shows up as broadband noise on an FFT and can partially mask the real frequency of interest.",
             "In a Full Spectrum, adding the forward and reverse amplitudes at a given frequency gives the orbit's major diameter at that frequency; subtracting them gives the minor diameter - similar forward/reverse amplitudes mean a highly elliptical or linear orbit at that frequency.",
             "A Full Spectrum shows orbit shape and precession per frequency, but not orientation - the actual overall orbit still needs to be checked to make full sense of it.",
             "Cascade/Waterfall plots make it easy to spot which frequency components track running speed (sloped lines) versus which don't (vertical lines, e.g. line-frequency electrical noise or a fixed structural resonance).",
         ],
         tip="A vertical (constant-frequency, non-speed-tracking) line on a cascade or waterfall plot is "
             "almost never a rotor fault - it's usually either electrical line-frequency noise getting "
             "into the wiring or a fixed structural/probe-support resonance being excited across a speed range."),
]


# ------------------------------------------------------------------
# TAB CATEGORIES
# Ordered list of (category_key, short_tab_label). "All" is a synthetic
# category shown first that doesn't filter anything. The keys here must
# exactly match the "category" values used in TURBO_TOPICS above.
# ------------------------------------------------------------------
CATEGORIES = [
    ("All", "All"),
    ("Fundamentals", "Fundamentals"),
    ("Bearings & Instabilities", "Bearings"),
    ("Aerodynamic & Hydraulic", "Aero/Hydraulic"),
    ("Common Faults", "Common Faults"),
    ("Diagnostics & Plots", "Plots"),
]


class TurboInsightsScreen(Screen):
    """Tabbed learning reference: a row of category pills up top switches
    which subset of NavCards is shown below. Tapping a card opens a detail
    popup (Overview / Key Points / Practical Tip), same as before."""

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

        self.active_category = "All"
        self.tab_buttons = {}

        outer = BoxLayout(orientation="vertical")

        header = BoxLayout(orientation="vertical", size_hint_y=None,
                            padding=[dp(14), dp(14), dp(14), dp(4)], spacing=dp(4))
        header.bind(minimum_height=header.setter("height"))
        header.add_widget(Label(text="[b]Turbomachinery Insights[/b]", markup=True, color=TEXT,
                                 size_hint_y=None, height=dp(30), font_size=dp(18),
                                 halign="left", valign="middle"))
        intro = body_label(
            "A quick-reference for rotordynamics, turbo-specific instabilities, and general "
            "vibration diagnostics - handy for day-to-day fault-finding and for CAT II-style "
            "study review. Pick a category, then tap a topic to read more.", MUTED)
        header.add_widget(intro)
        outer.add_widget(header)

        # Horizontal, scrollable row of category pill-tabs.
        tab_scroll = ScrollView(size_hint_y=None, height=dp(54), do_scroll_y=False, bar_width=0)
        tab_row = BoxLayout(orientation="horizontal", size_hint_x=None, size_hint_y=1,
                             spacing=dp(8), padding=[dp(14), dp(6), dp(14), dp(6)])
        tab_row.bind(minimum_width=tab_row.setter("width"))
        for key, label in CATEGORIES:
            btn = PillButton(label, accent=ACCENT, inactive=PANEL,
                              text_color=(1, 1, 1, 1), inactive_text_color=MUTED,
                              size_hint_x=None, width=dp(14) * max(len(label), 6) + dp(24))
            btn.bind(on_release=lambda inst, k=key: self.switch_category(k))
            tab_row.add_widget(btn)
            self.tab_buttons[key] = btn
        self.tab_buttons["All"].set_active(True)
        tab_scroll.add_widget(tab_row)
        outer.add_widget(tab_scroll)

        # Scrollable card list - rebuilt whenever the category changes.
        self.list_scroll = ScrollView()
        self.list_col = BoxLayout(orientation="vertical", spacing=dp(10),
                                   padding=[dp(14), dp(8), dp(14), dp(14)], size_hint_y=None)
        self.list_col.bind(minimum_height=self.list_col.setter("height"))
        self.list_scroll.add_widget(self.list_col)
        outer.add_widget(self.list_scroll)

        self.add_widget(outer)
        self._populate_cards("All")

    def switch_category(self, key):
        if key == self.active_category:
            return
        self.active_category = key
        for k, btn in self.tab_buttons.items():
            btn.set_active(k == key)
        self._populate_cards(key)
        self.list_scroll.scroll_y = 1

    def _populate_cards(self, key):
        self.list_col.clear_widgets()
        topics = TURBO_TOPICS if key == "All" else [t for t in TURBO_TOPICS if t["category"] == key]
        for topic in topics:
            card = NavCard(topic["name"], topic["category"], ACCENT,
                            card_bg=PANEL, title_color=TEXT, subtitle_color=MUTED, height=dp(78))
            card.bind(on_release=lambda inst, t=topic: self.open_topic(t))
            self.list_col.add_widget(card)
        count_note = Label(text="%d topic%s" % (len(topics), "" if len(topics) == 1 else "s"),
                            color=MUTED, font_size=dp(12), size_hint_y=None, height=dp(22),
                            halign="left", valign="middle")
        count_note.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        self.list_col.add_widget(count_note)
        footer = Label(text="Built by Gnaneswar", color=MUTED, font_size=dp(12),
                       size_hint_y=None, height=dp(30))
        self.list_col.add_widget(footer)

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def open_topic(self, topic):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        sc = ScrollView()
        inner = GridLayout(cols=1, size_hint_y=None, spacing=dp(10))
        inner.bind(minimum_height=inner.setter("height"))
        inner.add_widget(body_label("Overview:\n" + topic["overview"]))
        inner.add_widget(body_label(
            "Key points:\n- " + "\n- ".join(topic["key_points"])))
        inner.add_widget(body_label("Practical tip:\n" + topic["tip"], ACCENT))
        sc.add_widget(inner)
        content.add_widget(sc)
        close = RoundedButton(text="Close", accent=PANEL)
        content.add_widget(close)
        popup = Popup(title=topic["name"], content=content, size_hint=(0.92, 0.85))
        close.bind(on_release=popup.dismiss)
        popup.open()


class TurboApp(App):
    """Standalone-runnable wrapper, same pattern as the other tool modules
    so it can be run directly during development (`python turbo_tab.py`)
    or merged as a screen by main.py."""

    def build(self):
        try:
            Window.clearcolor = BG
        except Exception:
            pass
        root = BoxLayout(orientation="vertical")
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(TurboInsightsScreen(name="turbo_insights"))
        root.add_widget(sm)
        return root


if __name__ == "__main__":
    TurboApp().run()
