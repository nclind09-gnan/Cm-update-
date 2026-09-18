# -*- coding: utf-8 -*-
"""
Vibration Basics - a browsable learning-reference tool for CM Toolkit.

Foundational vibration-analysis concepts that the app's other tools assume
familiarity with. Written from general industry vibration-analysis practice,
in the author's own words and own organization - no text is lifted from any
single source or course.

Navigation is two levels deep:
  Topic list  ->  Sub-topic list (per topic)  ->  detail popup (per sub-topic)
Each sub-topic popup covers, in order: Overview, Why it matters, What it is,
How it works/is used, Key Points, and a Practical Tip. Hardware/gesture back
unwinds one level at a time via handle_back(), same contract as the other
tool modules (see main.py).
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.core.window import Window

from theme import RoundedButton, NavCard, PillButton

# ------------------------------------------------------------------
# COLORS - signal green, distinct from the other five tools
# ------------------------------------------------------------------
BG = (0.075, 0.09, 0.086, 1)
PANEL = (0.106, 0.129, 0.122, 1)
TEXT = (0.9, 0.92, 0.91, 1)
MUTED = (0.545, 0.60, 0.58, 1)
ACCENT = (0.22, 0.78, 0.42, 1)   # signal green


def body_label(text, color=TEXT):
    lbl = Label(text=text, color=color, size_hint_y=None, halign="left", valign="top")
    lbl.bind(width=lambda inst, val: setattr(lbl, "text_size", (val, None)))
    lbl.bind(texture_size=lambda inst, val: setattr(lbl, "height", val[1] + dp(6)))
    return lbl


def sub(name, overview, why, what, how, key_points, tip):
    return dict(name=name, overview=overview, why=why, what=what, how=how,
                key_points=key_points, tip=tip)


# ------------------------------------------------------------------
# LEARNING CONTENT - Batch 1 (topics 1-8), each sub-topic structured as
# Overview / Why / What / How / Key Points / Practical Tip.
# ------------------------------------------------------------------
BASICS_TOPICS = [
    dict(name="Introducing Vibration", category="Fundamentals", subtopics=[
        sub("What Is Vibration?",
            "Vibration is oscillating, cyclic motion around a reference point, described by "
            "amplitude (how much movement) and frequency (how often it repeats). Every mechanical "
            "fault in rotating machinery applies a repeating force at some characteristic rate, "
            "which is why it leaves a recognizable vibration signature rather than a random, "
            "meaningless shake.",
            "Understanding vibration as a phenomenon is the entry point to condition monitoring - "
            "without grasping that faults produce cyclic, repeatable patterns, none of the later "
            "diagnostic tools (spectra, phase, orbits) make sense. If you don't know why vibration "
            "is meaningful in the first place, severity numbers are just arbitrary figures on a "
            "screen.",
            "Vibration is the back-and-forth oscillation of a mechanical system around a reference "
            "(equilibrium) position. In rotating machinery it's caused by out-of-balance forces, "
            "misalignment, looseness, bearing wear, and dozens of other mechanical conditions, each "
            "applying a repeating force at a characteristic rate tied to the machine's rotation.",
            "In practice, vibration is measured by a sensor - accelerometer, velocity pickup, or "
            "proximity probe - that converts physical motion into an electrical signal. That signal "
            "is then described using amplitude (size) and frequency (rate), and analysts read both "
            "together, since a large amplitude at low frequency and a small amplitude at high "
            "frequency can represent forces of similar real-world severity.",
            [
                "Amplitude answers 'how much' motion is happening; frequency answers 'how often,' typically expressed in Hz or cycles per minute (CPM).",
                "A full cycle is one complete repetition of the motion, returning to the same position moving in the same direction.",
                "A 'vibration signature' is the specific combination of amplitude, frequency, and phase that a given fault produces.",
                "Each mechanical problem tends to excite the machine at a frequency tied to a physical rotating element - shaft speed, bearing geometry, number of gear teeth, number of fan blades, and so on.",
                "Overall vibration level is a single combined number; real diagnostic work almost always requires breaking that number down by frequency.",
            ],
            "Before reaching for a severity chart, get in the habit of asking two questions about "
            "any reading: how big (amplitude), and how often (frequency) - that pairing is the "
            "foundation everything else in vibration analysis builds on."),
        sub("Why We Monitor Vibration",
            "Vibration monitoring exists to catch developing mechanical faults early enough to plan "
            "a repair, instead of discovering them when the machine fails.",
            "Unplanned failures cost far more than planned repairs - in downtime, secondary damage, "
            "and safety risk. Vibration is the single most information-rich early-warning signal "
            "available on most rotating machinery, typically detecting problems weeks or months "
            "before temperature, noise, or visible symptoms appear.",
            "Vibration monitoring is a predictive-maintenance technique: measuring machine vibration "
            "at regular intervals, trending it over time, and diagnosing the specific fault behind "
            "any change, so maintenance can be scheduled based on actual condition rather than on "
            "a fixed calendar or run-to-failure.",
            "Implemented as a route-based program (a technician walking a fixed set of measurement "
            "points on a schedule), a permanently-installed online system, or a combination. "
            "Readings are compared against both the machine's own historical baseline and against "
            "published severity standards, and any significant change triggers deeper diagnostic "
            "analysis.",
            [
                "Predictive maintenance aims to fix what's actually degrading, rather than servicing on a fixed schedule or waiting for failure.",
                "Vibration typically gives earlier warning than temperature or audible noise for most rotating-machinery faults.",
                "Trending against a machine's own history is often more informative than comparing to a universal standard.",
                "The economic case is usually about avoided downtime and secondary damage, not the repair cost itself.",
                "A good program identifies not just that something changed, but specifically what and how urgently - which is what the rest of this app is for.",
            ],
            "Establish a solid baseline reading on a machine you know is healthy - without a "
            "baseline, you're comparing every future reading against a guess."),
        sub("Amplitude: Peak, Peak-to-Peak, RMS & Average",
            "The same vibration can be described by several different amplitude measures, and "
            "comparing numbers taken in different measures is a common source of error.",
            "Two readings of exactly the same vibration can differ by a factor of nearly three "
            "purely because of which amplitude measure was used - so knowing which one a number "
            "represents is essential before comparing it to a standard, a baseline, or another "
            "technician's reading.",
            "Peak is the maximum displacement from zero in one direction. Peak-to-peak is the full "
            "swing from the lowest to the highest point. RMS (root-mean-square) is a statistical "
            "measure of the signal's effective energy content. Average is the mean absolute value "
            "over the measurement period.",
            "In practice: displacement is conventionally reported peak-to-peak, velocity is "
            "conventionally reported RMS for standards-based work (ISO 10816/20816) and sometimes "
            "peak elsewhere, and acceleration is reported as peak or RMS depending on the "
            "application. Instruments let you select which, so always confirm the setting before "
            "recording or comparing a number.",
            [
                "For a pure sine wave, peak = 1.414 x RMS, and peak-to-peak = 2 x peak - useful conversion factors, though they only hold exactly for a clean sine wave.",
                "RMS is preferred for overall severity judgments because it reflects the signal's true energy content, not just its largest excursion.",
                "Peak and peak-to-peak are more sensitive to short, sharp events (impacts) than RMS is.",
                "Standards specify which measure to use - ISO velocity zones, for example, are defined in RMS.",
                "A reading with no stated amplitude measure is ambiguous and shouldn't be compared against anything.",
            ],
            "Always record which amplitude measure a reading used alongside the number itself - "
            "'4.2 mm/s' means nothing without knowing whether it's RMS or peak."),
        sub("Frequency, Period, Hz, CPM & Orders",
            "Frequency can be expressed several different ways in vibration work, and converting "
            "between them fluently is a basic working skill.",
            "Bearing catalogs quote frequencies in orders, instruments often display Hz, and much "
            "of the rotating-machinery world thinks in RPM and CPM - so diagnosing a fault usually "
            "requires converting between these on the fly. Getting a conversion wrong means "
            "matching a peak to the wrong component entirely.",
            "Frequency is how many cycles occur per unit of time. Period is the inverse - the time "
            "for one complete cycle. Hz is cycles per second; CPM is cycles per minute; an 'order' "
            "expresses frequency as a multiple of the machine's own running speed.",
            "Converted using simple relationships: CPM = Hz x 60, and orders = frequency divided by "
            "running speed frequency. Analysts commonly switch a spectrum's X-axis between Hz, CPM, "
            "and orders depending on the task - orders are especially useful on variable-speed "
            "machines, since fault peaks stay at fixed order values even as actual speed changes.",
            [
                "Period and frequency are inverses: a 0.02 second period equals 50 Hz.",
                "CPM = Hz x 60. A machine at 1,800 RPM has a running speed of 30 Hz, or 1,800 CPM.",
                "1X means one times running speed; 2X is twice running speed, and so on - these are 'orders'.",
                "On variable-speed machines, an order-based X-axis keeps fault peaks in the same position regardless of actual speed, which a Hz-based axis cannot do.",
                "Always confirm what units a given spectrum's X-axis is in before identifying peaks.",
            ],
            "Get comfortable converting a machine's RPM to Hz in your head (divide by 60) - it's "
            "the single most-used conversion in day-to-day vibration work."),
        sub("Vibration Sensors: An Overview",
            "Three main sensor families cover almost all vibration measurement, each with a "
            "different operating principle and frequency range.",
            "The sensor determines what you're physically capable of measuring - no amount of "
            "clever analysis can recover information a sensor never captured. Choosing the wrong "
            "sensor type for a given machine or fault is a fundamental error that invalidates "
            "everything downstream.",
            "Accelerometers measure acceleration via a piezoelectric crystal or MEMS element and "
            "cover a wide frequency range. Velocity pickups (coil-and-magnet) generate a signal "
            "proportional to velocity directly. Proximity (eddy-current) probes measure "
            "displacement non-contact, reading the gap to a shaft.",
            "Accelerometers mount on the machine casing and are by far the most common general-"
            "purpose choice. Velocity pickups are largely legacy but still found in older "
            "installations. Proximity probes are permanently installed through the bearing housing "
            "on fluid-film-bearing machines (turbines, large compressors), where casing measurements "
            "can't see shaft motion through the oil film.",
            [
                "Accelerometers: widest frequency range, best for bearing/gear diagnostics, most common overall.",
                "Velocity pickups: self-generating (no power needed), but limited frequency range and moving parts that wear.",
                "Proximity probes: measure shaft-relative displacement directly, essential for fluid-film-bearing machinery.",
                "Casing-mounted sensors measure how the housing moves; proximity probes measure how the shaft moves - these are not interchangeable.",
                "Sensor choice sets a hard limit on usable frequency range, which no later processing can extend.",
            ],
            "Check a sensor's specified frequency range against the fault frequencies you're "
            "hunting before trusting a measurement - especially at the high end for bearing work."),
        sub("Forced vs. Free Vibration",
            "Vibration is either driven continuously by an active force (forced) or is a system "
            "ringing at its own natural frequency after being disturbed (free).",
            "The distinction determines how you interpret a frequency: a forced-vibration peak "
            "points directly at a rotating component, while a free-vibration response points at a "
            "structural property. Confusing the two leads to chasing a component fault that doesn't "
            "exist, when the real issue is a resonance.",
            "Forced vibration is driven by an ongoing external force at that force's own frequency - "
            "unbalance forcing at 1X, gear mesh forcing at tooth-pass frequency. Free vibration is "
            "a structure oscillating at its own natural frequency after being struck or disturbed, "
            "decaying over time as damping absorbs the energy.",
            "In practice, forced vibration frequencies track with machine speed (a 1X peak moves as "
            "RPM changes), while natural frequencies stay fixed regardless of running speed - which "
            "is exactly the test used to distinguish them. A bump test deliberately excites free "
            "vibration to identify a structure's natural frequencies.",
            [
                "Forced vibration frequencies change with machine speed; natural frequencies do not.",
                "Resonance occurs when a forcing frequency coincides with a natural frequency, dramatically amplifying vibration.",
                "Free vibration decays over time; forced vibration continues as long as the force is applied.",
                "Varying machine speed and watching which peaks move is the standard practical test to tell them apart.",
                "Natural frequencies and resonance are covered in far more depth in their own topic.",
            ],
            "If a vibration peak stubbornly stays at the same frequency while the machine's speed "
            "changes, you're looking at a natural frequency, not a rotating-component fault."),
    ]),

    dict(name="Measurement Locations & Directions", category="Fundamentals", subtopics=[
        sub("Horizontal, Vertical & Axial",
            "Vibration is measured in three directions at each bearing, and comparing the three is "
            "itself a diagnostic technique.",
            "Different faults load a machine in different directions, so the relative amplitudes "
            "across the three directions often identify the fault type before any spectrum is even "
            "examined. Measuring only one direction routinely misses faults that would have been "
            "obvious from the comparison.",
            "Horizontal is perpendicular to the shaft, parallel to the ground. Vertical is "
            "perpendicular to the shaft and to the ground. Axial is parallel to the shaft's axis of "
            "rotation.",
            "A sensor is placed at each bearing in each of the three directions (or a triaxial "
            "sensor captures all three at once). The three readings are then compared: most "
            "machines are less stiff horizontally, so horizontal readings typically run somewhat "
            "higher than vertical on a healthy machine - a normal pattern, not a fault.",
            [
                "High axial vibration is a classic indicator of misalignment or a bent shaft, since most other faults load radially.",
                "Horizontal typically exceeds vertical on a healthy machine, because foundations are usually stiffer vertically.",
                "Vertical exceeding horizontal can suggest a foundation, mounting, or soft-foot problem.",
                "Comparing all three directions at the same bearing is often faster at narrowing the fault type than analyzing a single spectrum.",
                "Consistency matters - always measure the same directions at the same points, so trends are comparable.",
            ],
            "Take all three directions at every point as a matter of routine - the comparison "
            "between them frequently identifies the fault type faster than the spectra do."),
        sub("Sensor Mounting Methods",
            "How a sensor is attached to the machine sets a hard ceiling on the highest frequency "
            "it can accurately measure.",
            "A magnet-mounted or handheld sensor can silently attenuate or distort exactly the "
            "high-frequency content bearing diagnostics depend on - meaning a bearing fault can be "
            "genuinely present and genuinely invisible, purely because of mounting choice.",
            "Mounting method refers to how the sensor is physically coupled to the machine surface: "
            "stud-mounted (screwed permanently into a drilled hole), adhesive-mounted, "
            "magnet-mounted, or handheld with a probe tip.",
            "Chosen by trading off convenience against frequency range: stud mounting gives the "
            "widest usable frequency range and is standard for permanent installations, adhesive is "
            "a close second, magnets are the common route-based compromise, and handheld probe tips "
            "are the least accurate and should be avoided for anything beyond rough low-frequency "
            "checks.",
            [
                "Stud mounting: best frequency response, typically usable to 10 kHz or beyond.",
                "Adhesive mounting: nearly as good as stud, without drilling.",
                "Magnet mounting: convenient for routes, but the usable range often drops to roughly 2 kHz depending on magnet and surface.",
                "Handheld probe tips: worst frequency response, often limited to about 1 kHz or less, and highly variable between readings.",
                "The mounting surface matters too - it should be flat, clean, and paint-free for best coupling.",
            ],
            "If you're hunting a high-frequency bearing fault with a magnet-mounted sensor and "
            "seeing nothing, don't conclude the bearing is fine - the mounting may simply be "
            "filtering out the evidence."),
        sub("Repeatability & Measurement Consistency",
            "Trending only works if each reading is taken the same way at the same place - "
            "inconsistency creates apparent 'changes' that are really just measurement variation.",
            "Since most diagnosis rests on comparing a reading to that machine's own history, "
            "sloppy repeatability directly corrupts the one comparison the whole program depends "
            "on. A false alarm from a moved sensor wastes as much time as a missed fault.",
            "Repeatability is the practice of taking each measurement under matching conditions - "
            "same exact location, same direction, same mounting method, same machine operating "
            "state, same instrument settings - so that any difference in the reading reflects a "
            "real change in the machine.",
            "Achieved by permanently marking measurement locations (paint dots, adhesive mounting "
            "pads, or drilled/tapped stud holes), documenting the route and settings, and recording "
            "operating conditions (load, speed, temperature) alongside each reading.",
            [
                "Mark measurement points physically so the same spot is used every time.",
                "Record machine operating conditions with each reading - load and speed changes alter vibration legitimately.",
                "Keep instrument settings (Fmax, lines, averaging, units) identical between visits on the same point.",
                "A change in reading with no change in the machine usually means something about the measurement changed.",
                "Consistent, boring technique is what makes trending trustworthy.",
            ],
            "Before investigating an alarming change, first confirm the measurement was taken the "
            "same way as the baseline - measurement error is a more common explanation than sudden "
            "machine degradation."),
    ]),

    dict(name="Units & Conversions", category="Fundamentals", subtopics=[
        sub("Metric & Imperial Vibration Units",
            "Vibration work routinely mixes metric and imperial units, and converting between them "
            "accurately is a basic requirement.",
            "Equipment, standards, and colleagues will hand you numbers in both systems - a bearing "
            "catalog in one, an ISO standard in another, a legacy trend chart in a third. "
            "Mis-converting means comparing a reading against the wrong threshold entirely.",
            "The common pairs are: velocity in mm/s (metric) versus in/sec (imperial); displacement "
            "in microns (metric) versus mils, meaning thousandths of an inch (imperial); and "
            "acceleration in m/s squared (metric) versus g (multiples of gravity).",
            "Converted with fixed factors: 1 in/sec equals 25.4 mm/s; 1 mil equals 25.4 microns; and "
            "1 g equals approximately 9.81 m/s squared. Most instruments can display either system, "
            "so the safest practice is setting the instrument to match whatever standard or "
            "historical data you'll be comparing against.",
            [
                "Velocity: 1 in/sec = 25.4 mm/s.",
                "Displacement: 1 mil = 25.4 microns (both are 'thousandths', just of different base units).",
                "Acceleration: 1 g = 9.81 m/s squared, approximately.",
                "The 25.4 factor appears in both velocity and displacement conversions because it's just inches-to-millimetres.",
                "Set the instrument to the same unit system as your reference standard rather than converting by hand after the fact.",
            ],
            "Set your instrument's units once to match whatever standard your site uses, and leave "
            "it - most conversion errors happen when switching back and forth mid-program."),
        sub("Speed & Frequency Conversions",
            "Machine speed, frequency, and order are three views of the same thing, converted with "
            "simple arithmetic.",
            "Nearly every fault identification involves relating a spectrum peak back to the "
            "machine's running speed - which requires converting fluently between RPM, Hz, CPM, and "
            "orders. This is probably the most frequently used arithmetic in the whole discipline.",
            "RPM is revolutions per minute (machine speed). Hz is cycles per second. CPM is cycles "
            "per minute. An order is a multiple of running speed.",
            "Applied using: Hz = RPM divided by 60; CPM = Hz times 60 (so CPM and RPM are "
            "numerically equal for the shaft's own rotation); and order = peak frequency divided by "
            "running-speed frequency. Working in orders is the most robust approach on "
            "variable-speed equipment.",
            [
                "Hz = RPM / 60. A 3,600 RPM machine runs at 60 Hz.",
                "CPM = Hz x 60, which makes running speed in CPM numerically identical to RPM.",
                "Order = observed frequency / running speed frequency, giving 1X, 2X, 3.2X, and so on.",
                "Fractional orders (0.42X, 0.5X) are just as meaningful as whole-number ones and often indicate specific instability or looseness conditions.",
                "On variable-speed machines, orders are the only frequency expression that stays stable as speed changes.",
            ],
            "When identifying an unknown peak, convert it to orders first - a peak at 2.0X "
            "immediately suggests different causes than one at 0.48X, regardless of the actual Hz "
            "value."),
    ]),

    dict(name="Forcing Frequencies Overview", category="Fundamentals", subtopics=[
        sub("The Family of Fault Frequencies",
            "Most mechanical faults excite vibration at one of a fairly small set of predictable, "
            "calculable frequencies tied to machine geometry.",
            "Because these frequencies are calculable in advance from the machine's own physical "
            "details, a spectrum peak can be matched to a specific component rather than guessed "
            "at. Knowing the whole family exists, and roughly where each lives, is what turns "
            "spectrum reading from pattern-guessing into identification.",
            "The main families are: running-speed orders (1X, 2X, 3X and so on); bearing defect "
            "frequencies (BPFO, BPFI, BSF, FTF); gear mesh frequency and its harmonics; blade or "
            "vane pass frequency; belt frequencies; and electrical frequencies related to line "
            "frequency and motor pole count.",
            "Calculated ahead of time from machine data - shaft speed, bearing part number, tooth "
            "counts, blade counts, pulley diameters - and kept as a reference list for that machine. "
            "When a spectrum peak appears, it's compared against this list first, before treating it "
            "as unexplained. This app's Bearing Freq tool calculates the bearing family directly.",
            [
                "Running speed orders (1X, 2X...) cover unbalance, misalignment, looseness and similar.",
                "Bearing defect frequencies are non-integer orders calculated from bearing internal geometry - see the Bearing Freq tool.",
                "Gear mesh frequency = number of teeth x that gear's rotational speed.",
                "Blade/vane pass frequency = number of blades x shaft speed - common on fans, pumps and compressors.",
                "Electrical faults tend to appear at line frequency (50 or 60 Hz) or twice line frequency, and at pole-pass sidebands.",
                "Building this reference list before troubleshooting saves substantial time during analysis.",
            ],
            "Build and keep a forcing-frequency list for each critical machine while things are "
            "calm - trying to calculate them for the first time during a breakdown is slow and "
            "error-prone."),
    ]),

    dict(name="Displacement, Velocity & Acceleration", category="Fundamentals", subtopics=[
        sub("Displacement",
            "Displacement is how far something moves - the actual distance the shaft or casing "
            "travels from its reference position.",
            "Some faults - especially shaft position issues in fluid-film bearings, or very slow "
            "machinery - are only meaningfully described by actual distance moved. Using velocity "
            "or acceleration on, say, a 50 RPM gearbox risks missing real problems, since those "
            "units are far less sensitive at very low frequency.",
            "Displacement is the literal physical distance a point on the machine - shaft or "
            "casing - moves from its rest/reference position during one cycle of vibration. It's a "
            "direct geometric quantity (inches, mils, or microns of movement), not a derived rate "
            "like velocity or acceleration.",
            "Measured directly by non-contact proximity (eddy-current) probes that sense the gap "
            "between the probe tip and the shaft surface, or indirectly by double-integrating an "
            "accelerometer's signal in software. Field technicians read displacement mainly for "
            "shaft-relative measurements on fluid-film bearings and for very low-speed equipment "
            "where velocity or acceleration would understate the real motion.",
            [
                "Usually measured in mils (thousandths of an inch) or microns.",
                "Most meaningful at low frequencies - slow-speed machinery, or shaft centerline position monitoring.",
                "At higher frequencies, the same underlying force produces a much smaller displacement, making it a poor choice for spotting high-frequency faults.",
                "Conventionally reported peak-to-peak (the full swing from one extreme to the other) rather than as an RMS value.",
                "Common application: shaft relative-displacement (proximity) probes on fluid-film bearing machines.",
            ],
            "If you're looking at very low-speed equipment - well under a few hundred RPM - "
            "displacement is often the more sensitive and appropriate unit to trend."),
        sub("Velocity",
            "Velocity describes how fast that displacement is changing - not just how far something "
            "moves, but how quickly it gets there.",
            "Most industrial rotating equipment (roughly 500-10,000 RPM) has its dominant fault "
            "frequencies concentrated in the range where velocity is most sensitive to "
            "fatigue-related energy - exactly why the major international standards (ISO "
            "10816/20816) chose velocity as their basis. Using velocity means your 'general health' "
            "number is actually meaningful across most common fault types.",
            "Velocity is the rate of change of displacement - literally how much distance is "
            "covered per second. It's a derived quantity, one level of calculus removed from "
            "displacement.",
            "Most commonly measured directly by a velocity pickup (a self-generating coil-and-"
            "magnet sensor) or, more often today, derived in software by integrating an "
            "accelerometer's signal once. Field readings are typically reported as RMS velocity in "
            "mm/s or in/sec, then compared against ISO severity zone charts for a pass/fail-style "
            "assessment.",
            [
                "Usually measured in mm/s or in/sec, typically as an RMS value for standards-based readings.",
                "Correlates well with fatigue and damage potential across the broad mid-frequency range (roughly 10 Hz-1 kHz) most general vibration standards are built around.",
                "The most common choice for an overall, at-a-glance machine health number.",
                "ISO 10816/20816 severity zones are defined in velocity for exactly this reason.",
                "Loses sensitivity at very high frequencies (bearing/gear defect ranges) - the same limitation as displacement, but less severe.",
            ],
            "When in doubt about which parameter to trend for general 'is this machine healthy' "
            "monitoring, velocity RMS is the safest default."),
        sub("Acceleration",
            "Acceleration describes how fast the velocity itself is changing - essentially, how "
            "abrupt the motion is.",
            "Bearing and gear faults generate very short, sharp force impulses - events so brief "
            "that by the time they're converted down to velocity or displacement, their signature "
            "has been mathematically smoothed away and can hide in the noise. Acceleration is the "
            "only one of the three parameters that stays sensitive enough to catch these events "
            "while they're still small and repairable.",
            "Acceleration is the rate of change of velocity - literally how quickly the speed of "
            "motion itself is changing. It's two levels of calculus removed from displacement, "
            "which is exactly why its amplitude grows with frequency for a given physical force.",
            "Measured directly by an accelerometer (a piezoelectric or MEMS sensor), the most "
            "common vibration sensor type in industry because it's simple, robust, and covers a "
            "wide frequency range. Analysts read raw acceleration for bearing/gear diagnostics, and "
            "also process it further into 'envelope' or 'demodulated' spectra specifically to pull "
            "out repeating impact signatures.",
            [
                "Usually measured in g's (units of gravity, 1g is about 9.81 m/s\u00b2) or m/s\u00b2.",
                "For a given amount of force, acceleration's amplitude rises with frequency, keeping it sensitive where velocity and displacement fade.",
                "The right choice for bearing defects, gear mesh, and other high-frequency phenomena (roughly above 1-2 kHz).",
                "Accelerometers are also the most common and versatile sensor type, so acceleration is often the 'native' measurement even when velocity or displacement is what gets displayed after conversion in software.",
                "Very sensitive to mounting quality - a loosely mounted accelerometer can produce misleading high-frequency readings.",
            ],
            "If a bearing fault is suspected but doesn't show clearly in velocity, don't conclude "
            "the bearing is fine - check acceleration (or envelope/demodulation) before ruling it "
            "out."),
        sub("Choosing the Right Parameter",
            "Because displacement, velocity, and acceleration are mathematically linked - each is "
            "the rate of change of the one before it - the exact same underlying motion looks "
            "different depending on which one you plot.",
            "Picking the wrong parameter for a given frequency range can genuinely hide a real "
            "fault - not just make it harder to see, but mathematically attenuate it toward zero. "
            "Knowing which parameter to trust for which situation is one of the first practical "
            "judgment calls a vibration analyst has to make correctly.",
            "The three parameters are three mathematically linked descriptions of the exact same "
            "physical motion, related to each other by simple differentiation and integration - "
            "but each one's sensitivity is weighted differently across the frequency range.",
            "In practice, most portable vibration instruments let you select which parameter to "
            "display, or show several at once. A simple working rule: use displacement below "
            "roughly 10 Hz (600 CPM), velocity from there up to roughly 1 kHz, and acceleration "
            "above that - adjusting based on the specific machine and known fault frequencies of "
            "interest.",
            [
                "Rule of thumb: displacement for slow rotation or shaft position, velocity for general overall machine health, acceleration for bearing/gear/high-frequency diagnostics.",
                "Integration (deriving displacement from velocity, or velocity from acceleration) and differentiation (the reverse) are how instruments convert between the three from a single sensor.",
                "A rough frequency-range guide many analysts use: displacement below ~10 Hz, velocity from ~10 Hz to ~1 kHz, acceleration above ~1 kHz - though this varies by machine and standard.",
                "Comparing two readings taken in different units without converting them first is a common source of confusing or seemingly contradictory data.",
            ],
            "If two readings from the same event seem to disagree on severity, check which unit "
            "each is in before assuming a contradiction."),
    ]),

    dict(name="Amplitude Factors: Crest Factor, Kurtosis & More", category="Fundamentals", subtopics=[
        sub("Crest Factor",
            "Crest factor is the peak value of a signal divided by its RMS value - a quick, "
            "single-number way to flag 'something spiky is happening.'",
            "Overall vibration level (RMS) can stay completely normal even while a bearing is "
            "actively developing early-stage damage, because a few sharp, brief impacts don't move "
            "an averaged number much. Crest factor exists specifically to catch that blind spot - "
            "it's sensitive to exactly the kind of signal overall RMS is bad at detecting.",
            "Crest factor is a ratio - peak amplitude divided by RMS amplitude - that quantifies "
            "how 'spiky' a signal is relative to its average energy level.",
            "Calculated directly from time waveform data (no FFT needed) by most vibration "
            "instruments and software automatically. Practically, analysts trend it over time on "
            "the same measurement point and watch for a rise above the machine's own historical "
            "baseline, rather than comparing to one universal threshold.",
            [
                "A pure sine wave has a crest factor of about 1.41 (the square root of 2) - a useful reference baseline.",
                "Occasional sharp impacts, like an early-stage bearing defect, push the peak value up much faster than the RMS value, raising crest factor noticeably above that baseline.",
                "Easy to calculate directly from time waveform data without needing a full spectrum.",
                "Works best trended over time on the same measurement point, since a machine's 'normal' baseline crest factor varies.",
            ],
            "A crest factor climbing well above its historical baseline is a good trigger to go "
            "look at the time waveform directly, even if overall vibration hasn't moved yet."),
        sub("Kurtosis",
            "Kurtosis measures how 'peaked' or impulsive a waveform's statistical distribution is.",
            "Crest factor alone can sometimes be misleading - a single large but isolated spike can "
            "distort it - so kurtosis offers a second, statistically different way of asking the "
            "same underlying question: is this signal being driven by rare, sharp impacts rather "
            "than smooth continuous motion.",
            "Kurtosis is a statistical measure of a signal's distribution shape, specifically how "
            "much of its energy is concentrated in rare extreme values (the 'tails' of the "
            "distribution) versus spread out smoothly.",
            "Computed from the full time waveform's statistical distribution, typically over the "
            "same measurement interval as other waveform indicators. Best practice is trending it "
            "over time alongside crest factor, since the two occasionally disagree and "
            "cross-checking catches more real faults than either alone.",
            [
                "A perfectly smooth sine wave sits at a kurtosis value around 3 (sometimes reported as 0 when 'excess kurtosis' subtracts that baseline).",
                "Rising kurtosis reflects a signal increasingly dominated by sharp, infrequent impacts rather than smooth continuous motion.",
                "Tends to rise during early-stage bearing or gear defects.",
                "Can fall again once damage becomes severe and widespread enough that impacting turns frequent and the signal starts to look noisier and less distinctly 'spiky' - so a falling trend after a rise isn't automatically good news.",
                "Sometimes used alongside crest factor as a cross-check, since the two respond slightly differently to the same underlying damage.",
            ],
            "Track kurtosis over time rather than reading one snapshot - a rise-then-plateau-then-"
            "fall pattern can actually indicate progressing, not improving, damage."),
        sub("Skewness",
            "Skewness describes whether a waveform's distribution leans more toward positive or "
            "negative values rather than being symmetric around zero.",
            "Most fault types produce reasonably symmetric vibration, so a shift toward asymmetry "
            "is a specific, less-common signal worth separating out - it points at a different "
            "class of problem (directional mechanical constraint) than the more common symmetric "
            "fault signatures.",
            "Skewness quantifies asymmetry in a waveform's statistical distribution - whether "
            "values lean further in the positive direction or the negative direction relative to a "
            "perfectly balanced, symmetric signal.",
            "Calculated the same way as the other statistical indicators, from time waveform data. "
            "In practice it's checked less routinely than crest factor or kurtosis, typically "
            "pulled up specifically when a waveform already looks visually lopsided and a numeric "
            "confirmation is wanted.",
            [
                "A healthy, balanced vibration signal is typically close to symmetric (low skewness).",
                "A consistent lean in one direction can point to a directional mechanical asymmetry, such as a consistent rub or a preload pushing the shaft toward one side.",
                "Used less often than crest factor or kurtosis in routine monitoring.",
                "Most useful as a secondary check when a waveform looks visually unusual and the more common indicators aren't telling the whole story.",
            ],
            "If a waveform looks lopsided when you view it, skewness is the statistic that "
            "quantifies that impression - useful for confirming what your eye already noticed."),
        sub("Form Factor",
            "Form factor is the RMS value of a signal divided by its average (mean) absolute value, "
            "describing waveform 'shape' independent of overall size.",
            "Form factor offers yet another lens on waveform shape, useful in the less common cases "
            "where crest factor and kurtosis don't clearly agree, or where a specific standard or "
            "vendor's software already reports it - having a working understanding avoids treating "
            "it as a mystery number.",
            "Form factor is the ratio of RMS value to average (mean) absolute value - a measure of "
            "how 'peaky' versus 'flat' a waveform's overall energy distribution is, independent of "
            "its absolute size.",
            "Calculated automatically by software that supports it, from the same time waveform "
            "data as the other shape indicators; used mainly as a supplementary trend rather than a "
            "primary diagnostic on its own.",
            [
                "A pure sine wave has a form factor of about 1.11 - another useful reference baseline.",
                "Like the other shape indicators, it works best as a trend over time rather than read as a single absolute number.",
                "Less commonly used than crest factor or kurtosis in day-to-day CM work, but appears in some vendor software and standards.",
                "None of these four indicators - crest factor, kurtosis, skewness, form factor - should be used alone to confirm a fault.",
            ],
            "Use a rising trend in any of these shape indicators as a trigger to go look at the "
            "time waveform and spectrum in more detail, not as a standalone diagnosis."),
        sub("Overall Level vs. Shape Indicators",
            "The overall vibration level and the statistical shape indicators answer different "
            "questions, and a complete picture needs both.",
            "Relying on overall level alone creates a specific, well-known blind spot: early "
            "bearing damage can progress substantially while the overall number barely moves. "
            "Understanding why that happens is what motivates collecting shape indicators at all.",
            "Overall level (usually velocity RMS) is a single number summarizing total vibration "
            "energy - it answers 'how much vibration is there'. Shape indicators (crest factor, "
            "kurtosis, skewness, form factor) describe the character of the signal - they answer "
            "'what kind of vibration is it'.",
            "Used together in practice: overall level is the primary screening number on a route "
            "and is what severity standards are written against, while shape indicators are checked "
            "alongside it to catch impulsive faults that the averaged overall number would smooth "
            "away. Both are trended over time on the same point.",
            [
                "Overall level reflects total energy; a few brief sharp impacts contribute very little to it.",
                "Shape indicators are specifically sensitive to the impulsive content that overall level under-weights.",
                "A normal overall level with a rising crest factor is a meaningful, actionable combination - not a contradiction.",
                "Severity standards (ISO 10816/20816) are written against overall level, not shape indicators, so shape indicators are interpreted against the machine's own history instead.",
                "Neither one replaces spectrum or waveform analysis when something changes - they're screening tools that tell you when to look deeper.",
            ],
            "Don't clear a machine on overall level alone if a shape indicator has been climbing - "
            "that combination is exactly the early-bearing-damage pattern overall level is known to "
            "miss."),
    ]),

    dict(name="An Introduction to Phase", category="Fundamentals", subtopics=[
        sub("In-Phase",
            "'In phase' describes two measurement points - or two directions at the same point - "
            "reaching their peak motion at the same time, moving together rather than in "
            "opposition.",
            "In-phase behaviour is the reference condition that 'out of phase' is defined against, "
            "and it's a positive diagnostic signal in its own right: a rotor whose bearings move "
            "in phase with each other is behaving in a specific, identifiable way that points "
            "toward certain faults (notably static unbalance) and away from others.",
            "Two signals are in phase when their timing offset is zero, or close to it - both "
            "reaching maximum displacement in the same direction at the same instant, repeating "
            "that relationship every revolution.",
            "Measured the same way as any phase relationship: comparing two simultaneous vibration "
            "channels, or each channel against a shared tachometer reference, and reading the "
            "resulting angular difference. A difference near zero degrees indicates in-phase "
            "motion; readings within roughly 30 degrees are usually treated as effectively in "
            "phase for diagnostic purposes.",
            [
                "A phase difference near 0 degrees means in-phase; near 180 degrees means out-of-phase.",
                "Both ends of a rotor vibrating in phase at 1X is the classic signature of static (force) unbalance.",
                "In-phase vertical and horizontal readings at a single bearing suggest motion along one dominant direction rather than an orbiting path.",
                "Small phase differences (under about 30 degrees) are normally treated as in phase, since real measurements always carry some variation.",
                "In-phase is a finding, not an absence of one - it actively narrows the list of candidate faults.",
            ],
            "Don't treat an in-phase result as 'nothing found' - two points moving together at 1X "
            "is a specific, useful clue that points toward static unbalance rather than "
            "misalignment or a couple condition."),
        sub("Out-of-Phase",
            "'Out of phase' describes two measurement points - or two directions at the same point "
            "- moving in opposition rather than together, even though they're vibrating at the same "
            "frequency.",
            "Two faults can produce virtually identical amplitude and frequency readings while "
            "having completely different root causes and completely different repair paths - phase "
            "is frequently the only thing that tells them apart, which is why it's worth learning "
            "even though it's less intuitive than amplitude.",
            "'Out of phase' describes a specific timing relationship: two points (or two "
            "directions) vibrating at the same frequency but reaching their peak motion at "
            "different times, up to fully opposite times (180 degrees apart) for a purely "
            "out-of-phase condition.",
            "Determined in practice by comparing two simultaneous vibration measurements - either "
            "to each other, or each to a shared tachometer reference - and reading the timing "
            "offset, usually reported in degrees on the instrument or software.",
            [
                "Phase describes the timing relationship between a repeating vibration event and a fixed reference point.",
                "Two points perfectly 'in phase' move together - same direction, same time; 'out of phase' points move in opposition.",
                "A phase difference of 180 degrees is true opposition; smaller differences describe a partial, more gradual timing offset.",
                "Two points sharing the same amplitude and frequency but different phase relationships usually point to different root causes.",
            ],
            "Phase readings only mean something when compared - to a shaft reference, or to another "
            "point. A single phase number without a comparison point carries no diagnostic "
            "information."),
        sub("Where Does Phase Come From?",
            "Phase is a timing measurement, not an amplitude measurement - it comes from comparing "
            "exactly when a vibration signal's peak occurs relative to some fixed, repeating timing "
            "reference.",
            "Without understanding that phase requires a timing reference, it's easy to "
            "misunderstand what a phase number actually represents, or to try to compare phase "
            "readings that were never referenced to the same starting point - which produces "
            "meaningless results.",
            "Phase is fundamentally a comparison of timing, not a property that exists in "
            "isolation - it's always 'the phase of X relative to Y,' where Y is some fixed, "
            "repeating reference event.",
            "In practice, every phase reading you'll see in this app or in field instruments has an "
            "implicit or explicit reference baked into it - either the shaft's own tachometer "
            "pulse, or another vibration channel. Always confirm what that reference is before "
            "comparing two phase numbers from different sources.",
            [
                "Without a timing reference, you can measure how big a vibration is, but not where in the rotation it's happening.",
                "That reference is almost always tied to the shaft's own rotation.",
                "Phase is expressed consistently in degrees (0-360) relative to one specific point on the shaft, revolution after revolution.",
                "This timing-based nature is what makes phase useful for things amplitude alone can't do, like locating an unbalance heavy spot.",
            ],
            "Think of phase as answering 'when in the rotation' rather than 'how much' - a "
            "fundamentally different kind of question than amplitude."),
        sub("Using a Tachometer Reference",
            "In practice, the timing reference usually comes from a tachometer, laser, or "
            "keyphasor probe generating a once-per-revolution pulse.",
            "Balancing calculations, and any comparison of a fault's location relative to a "
            "specific point on the shaft, are only possible because a tachometer reference exists - "
            "without it, you'd know a vibration's frequency and amplitude, but never which side of "
            "the rotor is actually heavy.",
            "A tachometer reference is a physical, once-per-revolution timing signal generated by a "
            "sensor detecting a specific mark - notch, reflective tape, magnetic key - on the "
            "rotating shaft.",
            "In practice, a laser or optical tach is aimed at a piece of reflective tape on the "
            "shaft, or a proximity probe is aimed at a machined notch/keyway; each rotation "
            "produces one pulse, and the vibration instrument times the vibration signal's peak "
            "against that pulse to compute absolute phase, typically displayed in degrees.",
            [
                "The reference is a single, sharp timing mark firing at the same physical point on the shaft every rotation - often a reflective strip, notch, or key.",
                "Comparing the vibration signal's peak timing to that pulse gives absolute phase.",
                "Absolute phase says, in effect, 'the vibration peaks this many degrees after the shaft passes its reference mark.'",
                "This is exactly the information a balancing calculation needs to locate a heavy spot on the rotor.",
                "Common reference types: optical/laser tach, magnetic pickup, and eddy-current keyphasor probes (the latter typical on fluid-film bearing machines).",
            ],
            "Always note which type of reference and which direction it's read from - a phase "
            "reading is meaningless without knowing exactly what timing mark it was measured "
            "against."),
        sub("Relative Phase: Two-Channel",
            "Relative phase compares two vibration measurement points to each other directly, "
            "rather than each to the tachometer reference.",
            "Not every job has a working tachometer, and even when one exists, comparing two "
            "vibration points directly to each other reveals structural/mode-shape information a "
            "single tach-referenced reading can't - so relative phase is a genuinely separate and "
            "complementary tool, not just a fallback.",
            "Relative phase is the timing difference between two simultaneously measured vibration "
            "channels, compared directly to each other rather than to a shaft tachometer.",
            "Requires two channels measured at the same instant - two accelerometers, or two "
            "probes - feeding into an instrument capable of dual-channel phase comparison; the "
            "resulting number or plot shows how 'in step' or 'out of step' the two points are with "
            "each other.",
            [
                "Common comparisons: two different bearings on the same machine, or horizontal vs. vertical readings at a single bearing.",
                "Reveals mode shape - how different parts of a rotor or structure move relative to each other.",
                "Unbalance typically shows points moving in-phase with each other.",
                "Misalignment or looseness often shows a notably out-of-phase relationship between points sharing the same amplitude and frequency.",
                "Doesn't require a tachometer reference at all - just two simultaneous vibration channels compared to each other.",
            ],
            "When you don't have, or can't get, a good tach signal, relative phase between two "
            "vibration channels can still separate several common fault types."),
        sub("Representing Phase Data",
            "Phase is usually expressed as a single number in degrees, but it's often more useful "
            "shown visually.",
            "A single numeric phase reading only tells you the state at one moment; visual "
            "representations - polar, Bode, orbit - exist because tracking how phase changes across "
            "a startup, shutdown, or operating range reveals resonances and mode shapes that a "
            "static number simply cannot show.",
            "Phase data can be represented as a single number for one speed/moment, or plotted "
            "across a range of conditions - polar and Bode plots for tracking one channel's "
            "amplitude and phase across changing speed, and orbit plots for showing two channels' "
            "combined motion with phase built in geometrically.",
            "The choice depends on the task: a single static number is enough for confirming an "
            "unbalance correction; a polar or Bode plot is needed when investigating a startup or "
            "shutdown resonance; an orbit plot is used when the two-dimensional shape of the "
            "shaft's motion itself matters, not just a number.",
            [
                "A polar plot places amplitude and phase together on one chart, useful for tracking how a specific vibration order changes across a startup or shutdown.",
                "An orbit plot combines two perpendicular measurement channels into a 2-D trace of the shaft's actual path, with phase timing built into where a Keyphasor mark lands.",
                "A Bode plot separates amplitude and phase onto two stacked graphs against speed, covering the same underlying data as a polar plot in a different layout.",
                "Simple numeric phase readings (e.g. '1X = 0.2 mils pp at 145 degrees') remain the most common format for routine balancing work.",
            ],
            "For a quick single-speed check, a numeric phase reading is enough; for anything "
            "involving a startup, shutdown, or resonance, a polar or Bode plot shows far more."),
        sub("Summary of Phase",
            "Phase is the timing relationship between a vibration signal and a fixed reference - "
            "either the shaft's own once-per-rev mark (absolute phase) or between two measurement "
            "points (relative phase).",
            "Phase is genuinely one of the higher-value but under-used tools in basic vibration "
            "work - many people stop at amplitude and frequency, but phase is frequently what turns "
            "an ambiguous diagnosis into a confident one.",
            "In short, phase is the timing relationship between a repeating vibration signal and a "
            "fixed reference, expressed in degrees, available as either absolute phase (referenced "
            "to the shaft) or relative phase (referenced to another vibration channel).",
            "Practically, always collect phase alongside amplitude and frequency when the goal is "
            "balancing or when distinguishing between fault types (like unbalance vs. misalignment) "
            "that share similar amplitude/frequency signatures - amplitude and frequency alone are "
            "often not enough to finish the diagnosis.",
            [
                "Expressed in degrees; essential for balancing work and for separating fault types that share the same amplitude and frequency.",
                "Absolute phase locates a heavy spot relative to a shaft reference mark; relative phase compares two measurement points to reveal mode shape.",
                "Represented numerically, or visually via polar, Bode, or orbit plots.",
                "Amplitude alone frequently can't tell unbalance, bent shaft, and misalignment apart - their phase relationships usually can.",
            ],
            "If two points with the same 1X amplitude behave differently, trust the phase "
            "comparison over amplitude alone."),
        sub("Introducing Orbits",
            "An orbit plot combines two perpendicular vibration probes' signals into a single "
            "two-dimensional trace of the shaft centerline's actual path.",
            "A single vibration channel only shows one slice of what is inherently two-dimensional "
            "motion; without combining two perpendicular channels into an orbit, a large class of "
            "information about how the shaft is actually moving inside its bearing clearance is "
            "simply invisible.",
            "An orbit is the two-dimensional path traced by the shaft centerline, built by "
            "combining the simultaneous signals from two perpendicular proximity probes into a "
            "single X-Y plot.",
            "Requires two probes physically mounted 90 degrees apart in the same radial plane, "
            "feeding their signals into software (or an oscilloscope) that plots one channel "
            "against the other in real time, typically with a Keyphasor dot marking the "
            "once-per-revolution timing reference on the trace.",
            [
                "Built from two real-time signals, rather than viewed as two separate one-dimensional waveforms.",
                "Naturally encodes amplitude, frequency, and phase all in one picture.",
                "Considered one of the richest single diagnostic plots available for shaft-relative measurements.",
                "Requires two probes mounted perpendicular to each other in the same radial plane.",
                "The Turbomachinery Insights tab covers orbit construction, Keyphasor marks, and orbit shape reading in much more depth.",
            ],
            "If you only ever see one probe's waveform, you're seeing a 1-D slice of what's "
            "actually 2-D motion - an orbit is what fills in the missing dimension."),
        sub("Phase Lag vs. Phase Lead",
            "Phase can be measured against the direction of shaft rotation or with it, and the two "
            "conventions give answers 360 degrees apart from each other.",
            "Getting the convention wrong in a balancing job typically puts the correction weight "
            "roughly opposite where it should go, making the vibration worse instead of better. "
            "This is one of the most consequential conventions to get right in practical vibration "
            "work.",
            "Phase lag measures the angle opposite to the direction of shaft rotation - the "
            "vibration peak trails behind the reference mark. Phase lead measures it in the same "
            "direction as rotation - the peak appears ahead of the mark. They describe the same "
            "physical event from opposite measurement conventions, related by: lead = 360 degrees "
            "minus lag.",
            "Determined by the instrument's own convention, which varies by manufacturer - most "
            "vibration instruments and tach-based analyzers report phase lag by default. The "
            "practical requirement is to identify which convention your instrument uses before "
            "doing any balancing calculation, and to stay consistent throughout a job. This app's "
            "Rotor Balance tool lets you select which convention your readings use.",
            [
                "Lag = measured opposite to rotation direction; lead = measured with rotation direction.",
                "Mathematically, lead = 360 - lag, so the two never disagree about the physics, only about the bookkeeping.",
                "Most instruments default to phase lag, but this is not universal - confirm rather than assume.",
                "Mixing conventions mid-job is a common cause of a balance attempt that makes vibration worse.",
                "The Rotor Balance tool in this app has an explicit lag/lead setting for exactly this reason.",
            ],
            "Confirm your instrument's phase convention once, write it down, and use the same one "
            "for every reading in a balancing job - consistency matters more than which convention "
            "you pick."),
        sub("Using Phase to Diagnose Faults",
            "Specific phase patterns across a machine correspond to specific fault types, making "
            "phase one of the fastest ways to separate look-alike faults.",
            "Unbalance, misalignment, a bent shaft, looseness and resonance can all produce a "
            "dominant 1X peak of similar amplitude - amplitude and frequency alone genuinely cannot "
            "separate them. Phase patterns can, which is why phase is worth the extra effort to "
            "collect.",
            "Phase-based diagnosis means taking phase readings at multiple points and directions on "
            "a machine, then comparing the pattern of relationships between them against known "
            "fault signatures.",
            "Applied by collecting 1X phase at each bearing in each direction, then examining the "
            "pattern: across the coupling, between bearings on the same machine, and between "
            "directions at one bearing. The overall pattern - not any single number - is what maps "
            "to a fault type.",
            [
                "Static unbalance: both bearings on the rotor move roughly in phase at 1X.",
                "Couple unbalance: the two ends of the rotor move roughly 180 degrees out of phase.",
                "Angular misalignment: typically shows a notable axial phase difference across the coupling, often near 180 degrees.",
                "Bent shaft: often shows an axial phase difference between measurement points on the same machine.",
                "Looseness: phase readings tend to be unstable or erratic between repeated measurements rather than holding a consistent value.",
                "Resonance: phase shifts substantially (often approaching 180 degrees) as the machine passes through the resonant speed.",
            ],
            "When two candidate faults produce the same spectrum, collect phase across the machine "
            "before disassembling anything - the phase pattern usually resolves the ambiguity in "
            "minutes."),
        sub("Common Phase Measurement Pitfalls",
            "Phase readings can be corrupted by several practical measurement problems that produce "
            "plausible-looking but wrong numbers.",
            "Unlike an obviously bad amplitude reading, a corrupted phase reading often looks "
            "entirely reasonable - just wrong - which means it can quietly send a balancing job or "
            "diagnosis in the wrong direction without any obvious warning sign.",
            "The main pitfalls are: an unstable or poorly-triggering tachometer signal, inconsistent "
            "sensor orientation between readings, a machine operating near a resonance (where phase "
            "shifts rapidly with small speed changes), and mixing phase conventions or reference "
            "points between readings.",
            "Guarded against by confirming the tach signal is clean and triggering reliably before "
            "trusting any phase number, keeping sensor orientation and mounting identical across "
            "readings, noting the machine's speed with each reading, and repeating a reading to "
            "confirm it's stable before acting on it.",
            [
                "An intermittent or noisy tach trigger produces phase readings that wander unpredictably.",
                "Reversing sensor orientation between readings flips the phase by 180 degrees - a silent, easy error.",
                "Near a resonance, small speed changes cause large phase shifts, so readings taken at slightly different speeds won't agree.",
                "Unstable, non-repeating phase readings are themselves a diagnostic clue, often pointing at looseness.",
                "Always repeat a phase reading before acting on it - if it doesn't repeat, find out why before proceeding.",
            ],
            "Take every phase reading at least twice before using it. A number that doesn't repeat "
            "isn't a measurement - it's either a bad setup or a genuine looseness finding, and "
            "either way you need to know which."),
    ]),

    dict(name="Amplitude Modulation", category="Signal Behavior", subtopics=[
        sub("Amplitude Modulation",
            "Amplitude modulation (AM) happens when a carrier frequency's strength rises and falls "
            "at a second, slower rate.",
            "Amplitude modulation is one of the most common signatures gear and bearing faults "
            "actually produce in the real world - recognizing it, rather than just seeing 'extra "
            "peaks' and being confused, is a core diagnostic skill that directly identifies which "
            "specific component is degrading.",
            "Amplitude modulation is a specific kind of signal behavior where a higher-frequency "
            "'carrier' signal's strength is being varied - pulsed up and down - by a separate, "
            "lower-frequency event.",
            "Detected in practice by spotting sidebands (extra peaks evenly spaced around a carrier "
            "peak) in a spectrum, then measuring the spacing between those sidebands and the "
            "carrier to identify the modulating frequency, which is then matched against the "
            "machine's known component speeds (a specific gear, for instance) to locate the fault.",
            [
                "Classic example: gear mesh frequency being 'pulsed' once per revolution of a damaged gear tooth.",
                "Produces sidebands in a spectrum - extra peaks evenly spaced on either side of the main carrier frequency.",
                "Sideband spacing equals the modulating frequency, not the carrier frequency.",
                "That spacing is usually the real diagnostic clue - it points at whatever component is doing the modulating.",
                "In the time waveform, AM shows up as a rising-and-falling amplitude envelope around the faster carrier oscillation.",
            ],
            "When you see sidebands, measure their spacing first - it usually identifies the "
            "specific faulty component faster than the carrier peak itself does."),
        sub("Frequency Modulation",
            "Frequency modulation (FM) is related to AM but distinct - the carrier's speed, not its "
            "strength, shifts slightly back and forth at a slower rate.",
            "While less common than amplitude modulation, mistaking FM for AM (or vice versa) can "
            "point troubleshooting at the wrong mechanism, so it's worth being able to tell them "
            "apart when sidebands appear and the waveform doesn't show the expected AM-style "
            "amplitude envelope.",
            "Frequency modulation is a signal behavior where a carrier's frequency - not its "
            "strength - is being shifted slightly back and forth by a separate, slower event.",
            "Distinguished from AM primarily by examining the time waveform directly - FM shows "
            "subtle timing/spacing shifts between cycles rather than an obvious rise-and-fall in "
            "amplitude - and is confirmed by correlating the sideband spacing with a known slower "
            "mechanical event, same as with AM.",
            [
                "Seen in some gear and turbine-blade interactions.",
                "Also produces sidebands around a carrier peak, similar in appearance to AM in a spectrum.",
                "The time waveform is usually the clearer way to tell FM from AM: AM shows an obvious amplitude 'beat' envelope, FM shows a subtler shift in timing.",
                "Generally less common in everyday CM work than AM, but shows up in specific gear-mesh and blade-pass scenarios.",
            ],
            "If sidebands are present but the time waveform doesn't show an obvious amplitude "
            "envelope, consider FM rather than assuming AM by default."),
        sub("Noise",
            "In this context, 'noise' means a raised, non-discrete energy floor in the spectrum.",
            "A rising noise floor is a real, measurable change in machine condition that's easy to "
            "miss if you're trained to only look at discrete peaks - learning to read the noise "
            "floor as its own feature closes that gap.",
            "In spectral terms, 'noise' refers to vibration energy that's spread broadly across "
            "many frequencies rather than concentrated into sharp, identifiable peaks.",
            "Read by comparing the overall height/level of the spectrum's baseline (between and "
            "around the peaks) against a historical baseline spectrum from the same point; a "
            "broadly elevated floor, without new discrete peaks, still counts as a meaningful trend "
            "worth investigating.",
            [
                "Broad and spread out across a frequency range, rather than concentrated into sharp peaks.",
                "Often points to friction-type problems - rubbing, cavitation, electrical arcing.",
                "A useful signal in its own right, separate from reading individual peaks.",
                "Easy to overlook if you're only scanning a spectrum for the tallest peaks.",
            ],
            "Get in the habit of glancing at the overall noise floor level, not just peak heights "
            "- a rising floor with no new discrete peaks is still a real change worth "
            "investigating."),
        sub("Beating",
            "Beating occurs when two nearby-but-different frequencies combine, producing a slow "
            "pulsing pattern in the combined amplitude.",
            "Beating can look alarming - a strong, slow pulsing vibration - but understanding its "
            "cause prevents wasted troubleshooting effort chasing a 'fault' that's actually just "
            "two machines running at very slightly different speeds.",
            "Beating is a purely mathematical interference effect that occurs whenever two "
            "frequencies close to each other in value are physically summed together - it isn't a "
            "fault mechanism in either source, just what happens when two similar frequencies "
            "overlap.",
            "Identified by finding two separate, closely-spaced peaks in the spectrum, then "
            "confirming their frequency difference matches the pulsing rate observed in the time "
            "waveform; correction, if needed, means adjusting one of the two source speeds, not "
            "treating the vibration itself as a defect.",
            [
                "Classic example: two machines running at almost, but not exactly, the same speed.",
                "A mathematical result of constructive and destructive interference between two independent sources.",
                "Not a fault in either machine by itself - an important distinction from modulation.",
                "The beat rate equals the difference between the two frequencies involved.",
            ],
            "If a pulsing vibration pattern's rate matches the speed difference between two nearby "
            "machines, that's beating, not a defect on either one."),
        sub("Beating vs. Amplitude Modulation",
            "Beating and amplitude modulation can look alike - both produce a pulsing envelope - "
            "but they come from genuinely different mechanisms.",
            "These two phenomena look almost identical in a raw time waveform, but require "
            "completely different corrective actions, so being able to reliably tell them apart "
            "directly changes what troubleshooting steps you'd take next.",
            "The distinction is about mechanism, not appearance: beating comes from two separate, "
            "independent frequency sources interfering; amplitude modulation comes from one source "
            "whose output is being varied by a second, related mechanism.",
            "The reliable way to distinguish them is checking the spectrum, not the waveform: two "
            "distinct close peaks confirms beating, while one peak flanked by symmetric sidebands "
            "confirms AM.",
            [
                "Beating: two independent sources at close but different frequencies.",
                "AM: a single mechanism whose output is being mechanically varied.",
                "The fix is different for each: beating usually means addressing a speed mismatch between two sources, while AM points at a specific modulating fault within one machine.",
                "Confusing the two can send troubleshooting in entirely the wrong direction, so it's worth deliberately checking which one you're looking at.",
            ],
            "Don't assume a pulsing waveform is a fault - rule out beating from a nearby second "
            "source first."),
        sub("Spectrum Analysis of Beating",
            "In a spectrum, true beating shows up as two distinct, closely spaced peaks - not one "
            "peak with sidebands.",
            "The spectrum is specifically what resolves the ambiguity that the time waveform can't "
            "- a concrete, practical example of why vibration analysts are taught to always check "
            "both representations of a signal rather than relying on just one.",
            "In frequency terms, beating is the presence of two separate, real frequency components "
            "close together, as opposed to modulation's single carrier-plus-sidebands structure.",
            "Practically, this means zooming into the spectrum around the pulsing region - "
            "potentially increasing frequency resolution/lines if needed - to visually confirm "
            "whether there are two separate peaks or one peak with symmetric sidebands.",
            [
                "Usually the cleanest way to distinguish beating from amplitude modulation.",
                "The two can look very similar in the time waveform's pulsing envelope but appear clearly different once converted to a spectrum.",
                "Two close peaks = beating; one peak with evenly spaced sidebands = AM.",
                "Frequency resolution matters here - if a spectrum's resolution is too coarse, two close beating peaks can blur together and look like a single peak.",
            ],
            "If a slow pulse in the waveform doesn't resolve into two distinct peaks even in a "
            "fine-resolution spectrum, lean toward AM rather than beating."),
        sub("Correcting Beating",
            "Because beating comes from two independent sources at nearly the same speed, "
            "correcting it usually means addressing why those two speeds differ.",
            "Treating beating as a mechanical defect to 'fix' on the vibrating machine wastes time "
            "and can lead to unnecessary maintenance action on equipment that isn't actually "
            "faulty - understanding the real cause redirects effort to where it's actually needed.",
            "'Correcting' beating means addressing the speed mismatch between the two interfering "
            "sources, not performing maintenance on either machine's internal components as if "
            "something inside it were broken.",
            "In practice, this might mean adjusting a variable-speed drive on one of the two "
            "machines, or - if the small speed difference is expected and harmless - simply "
            "documenting the beating as a known, benign characteristic rather than continuing to "
            "investigate it as a fault.",
            [
                "Not treated as a defect on either machine individually.",
                "May mean resolving a drive/control issue on one of the two sources.",
                "Sometimes it's simply an expected small speed difference between two nominally identical machines, producing an otherwise harmless pulsing pattern.",
                "Worth confirming there's no coupling or shared load path between the two sources before concluding it's purely benign.",
            ],
            "Before spending time 'fixing' a beating pattern, confirm it's not actually causing a "
            "real problem (like fatigue loading from the repeated pulsing) - sometimes it's simply "
            "cosmetic."),
        sub("Intermodulation",
            "Intermodulation happens when two frequencies interact nonlinearly and generate new "
            "frequencies at their sum and their difference.",
            "Intermodulation peaks can be genuinely confusing if you don't know to look for them, "
            "since they appear at frequencies that don't match any single known component - "
            "recognizing the pattern turns a mystery peak into a clear nonlinearity diagnosis.",
            "Intermodulation is the generation of entirely new frequency components, at the "
            "mathematical sum and difference of two original frequencies, caused by a nonlinear "
            "interaction between them somewhere in the mechanical system.",
            "Identified by taking two known, real peaks already present in a spectrum, calculating "
            "their sum and difference, and checking whether an otherwise-unexplained peak matches "
            "one of those calculated values - a match strongly suggests a nonlinear condition like "
            "looseness or rubbing is present.",
            [
                "The new frequencies don't correspond to either original source directly.",
                "A sign of nonlinearity somewhere in the mechanical system - looseness or rubbing are common culprits.",
                "A perfectly linear system would keep two input frequencies separate rather than generating new ones from their interaction.",
                "Related to, but distinct from, simple beating, which doesn't generate new frequencies - just an amplitude pattern from the two originals.",
            ],
            "A spectrum peak that matches neither a known running-speed order nor a known "
            "component frequency, but does match the sum or difference of two other peaks, is a "
            "strong nonlinearity clue."),
    ]),

    dict(name="Understanding Spectra", category="Signal Behavior", subtopics=[
        sub("Feature One: Pure Frequency",
            "A single sharp peak with little else around it usually points to a straightforward, "
            "single-source cause.",
            "Recognizing the simplest case first gives you a baseline for everything more "
            "complicated - if you can't confidently read a single clean peak, the more complex "
            "features like harmonics and sidebands will be much harder to interpret correctly.",
            "A pure frequency feature is a single, narrow, well-defined peak in the spectrum with "
            "minimal surrounding energy, representing one dominant, simple vibration source.",
            "Read directly off the spectrum by identifying the tallest, cleanest peak and noting "
            "its frequency (usually compared against running speed as '1X,' '2X,' etc.) and "
            "amplitude; a spectrum dominated by one such peak generally means a simple, single-"
            "cause condition like straightforward unbalance.",
            [
                "Pure unbalance showing up as a clean 1X peak is the classic example.",
                "The simplest spectrum feature to read.",
                "The baseline everything else - harmonics, sidebands, noise - gets compared against.",
                "A spectrum dominated by one clean peak with a low noise floor generally indicates a well-behaved, simple vibration source.",
            ],
            "When a spectrum is dominated by one clean peak, resist over-analyzing it - simple "
            "problems often really are simple."),
        sub("Feature Two: Harmonics",
            "Harmonics are peaks at whole-number multiples of a fundamental frequency - 2X, 3X, "
            "4X, and so on.",
            "The specific pattern of which harmonics appear, and how strong they are relative to "
            "the fundamental, is one of the most information-dense single features in a spectrum - "
            "many textbook fault 'signatures' are defined primarily by their harmonic pattern.",
            "Harmonics are peaks occurring at exact whole-number multiples of a fundamental (base) "
            "frequency - 2X, 3X, 4X, and so on, relative to whatever 1X represents (usually running "
            "speed).",
            "Read by identifying the fundamental peak first, then checking each subsequent whole-"
            "number multiple for a peak and noting its relative height compared to the fundamental; "
            "comparing this pattern against known fault signatures (e.g., strong 2X suggesting "
            "possible misalignment) is standard diagnostic practice.",
            [
                "Their presence and relative size compared to the fundamental are often diagnostic.",
                "A strong 2X alongside 1X is a common misalignment signature.",
                "A long train of many harmonics can point toward looseness or a more nonlinear mechanical response.",
                "Harmonics of running speed are usually written as 'nX' to distinguish them from harmonics of other frequencies, like gear mesh harmonics.",
            ],
            "Don't just note that harmonics are present - count how many and compare their "
            "relative heights; the overall pattern carries information beyond any single peak."),
        sub("Feature Three: Sidebands",
            "Sidebands are extra peaks evenly spaced on either side of a central peak, produced by "
            "modulation.",
            "Sidebands are frequently the single most specific diagnostic clue available in a "
            "spectrum - they don't just say 'something's wrong,' they identify which component, by "
            "frequency, is causing it.",
            "Sidebands are pairs (or sets) of smaller peaks positioned symmetrically on either side "
            "of a larger, central 'carrier' peak, spaced apart from it by a consistent frequency "
            "interval.",
            "Read by identifying a peak with clearly visible smaller peaks flanking it, then "
            "measuring the frequency gap between the carrier and its nearest sideband (that gap is "
            "the modulating frequency), and matching that modulating frequency against the "
            "machine's known component speeds.",
            [
                "The spacing between sidebands usually identifies the modulating source, separately from the carrier frequency itself.",
                "Spotting sidebands and measuring their spacing - not just noting the carrier peak - is often what actually pins down a gear or bearing fault to a specific component.",
                "Sidebands can appear on just one side or both sides of a carrier peak depending on the type of modulation.",
                "Multiple sets of sidebands (different spacings around the same carrier) can indicate more than one modulating source acting on the same component.",
            ],
            "If you spot one sideband, look for its pair on the other side of the carrier - true "
            "modulation sidebands come in symmetric spacing."),
        sub("Feature Four: Noise",
            "A raised, non-discrete noise floor is its own spectrum feature worth reading "
            "separately from individual peaks.",
            "An overlooked noise floor rise represents a real category of diagnostic information "
            "that a peak-only reading strategy completely misses - deliberately including it in "
            "your reading routine closes a genuine blind spot.",
            "The noise floor is the baseline energy level present across the spectrum between and "
            "around discrete peaks, representing broadband (non-specific-frequency) vibration "
            "energy.",
            "Read by visually comparing the general 'height' of the spectrum's baseline (not the "
            "peaks) against a historical reference spectrum from the same point, looking for a "
            "broad rise rather than any single new peak.",
            [
                "Energy spread broadly across a frequency range rather than concentrated into sharp peaks.",
                "Often points to friction-type problems (rubbing, cavitation, electrical noise) rather than a fault tied to one specific rotating component.",
                "Easy to overlook if you're only scanning for peaks.",
                "A rising noise floor over time, even without new discrete peaks, is a legitimate trend to flag.",
            ],
            "Compare the noise floor level against a known-good baseline spectrum from the same "
            "point - a subtle floor rise is easy to miss without that direct comparison."),
        sub("Feature Five: Sum and Difference",
            "Sum-and-difference peaks appear where two frequencies interact nonlinearly, showing "
            "up at neither original frequency but at their sum and their difference.",
            "Like intermodulation under Amplitude Modulation, these peaks can look like unexplained "
            "mystery frequencies until you know to check them against sums and differences of other "
            "known peaks - recognizing this pattern converts confusion into a clear nonlinearity "
            "finding.",
            "Sum-and-difference peaks are new frequency components appearing at the arithmetic sum "
            "or difference of two other real frequencies present in the same spectrum, caused by "
            "nonlinear interaction between them.",
            "Identified by taking any two significant peaks already present, computing their sum "
            "and their difference, and checking whether an otherwise-unexplained peak in the "
            "spectrum matches either calculated value.",
            [
                "A strong clue that you're looking at nonlinear behavior like looseness or rubbing.",
                "Spotting a peak that doesn't correspond to any expected running-speed order, bearing frequency, or gear mesh rate, but does match the sum or difference of two other peaks, is the key tell.",
                "Related directly to the intermodulation concept covered under Amplitude Modulation.",
                "Worth checking for whenever a spectrum has an unexplained peak that doesn't fit any known component frequency.",
            ],
            "Keep a short list of the machine's known frequencies - 1X, bearing defect "
            "frequencies, gear mesh - handy; an unexplained peak often resolves once checked "
            "against sums and differences of that list."),
        sub("Spectral Regions",
            "Different frequency ranges tend to be dominated by different fault families.",
            "Reading a spectrum region-by-region, rather than randomly, is a habit that directly "
            "improves diagnostic speed and consistency - it ensures you don't miss a fault simply "
            "because you didn't happen to look at the right part of the frequency range.",
            "Spectral regions describes the general tendency of different fault types to "
            "concentrate their energy in characteristic frequency bands - low frequency for basic "
            "running-speed issues, mid-range for looseness, high frequency for bearing/gear-mesh "
            "events.",
            "Applied practically as a scan routine: start at 1X and work upward through harmonics, "
            "then check for sidebands around major peaks, then check the noise floor across the "
            "full range - covering low, mid, and high regions in a consistent order every time.",
            [
                "Low frequency: basic running-speed faults (unbalance, misalignment).",
                "Mid-range: looseness and early bearing issues often show up here first.",
                "High frequency: bearing defect frequencies and gear mesh typically appear here.",
                "Scanning a spectrum region by region, rather than jumping straight to the tallest peak, is a practical habit.",
                "A practical scan order: check 1X first, then harmonics up to about 5X, then sidebands around the biggest peaks, then finally the noise floor.",
            ],
            "Build a consistent scan routine - 1X, harmonics, sidebands, noise floor - and use it "
            "every time; consistency catches things that jumping straight to the biggest peak "
            "would miss."),
        sub("Linear vs. Logarithmic Amplitude Scales",
            "The same spectrum looks dramatically different depending on whether its amplitude axis "
            "is linear or logarithmic, and each scale reveals different things.",
            "A small but diagnostically important peak sitting beside a very large one can be "
            "effectively invisible on a linear scale - it's physically there in the data but too "
            "small to see. Switching scales is often the difference between spotting an early "
            "bearing fault and missing it entirely.",
            "A linear amplitude scale spaces amplitude values evenly, so the tallest peaks dominate "
            "visually. A logarithmic scale compresses large values and expands small ones, making "
            "low-amplitude features visible alongside large ones.",
            "Switched in the instrument or software display settings. Common practice: use linear "
            "for severity judgments and routine screening, where the biggest peaks are what matter, "
            "and switch to logarithmic when hunting for small early-stage faults, sidebands, or "
            "low-level bearing frequencies hiding near a dominant 1X peak.",
            [
                "Linear scale: proportional and intuitive, best for judging relative severity of dominant peaks.",
                "Logarithmic scale: reveals small peaks that a linear scale would visually flatten into the baseline.",
                "Early bearing faults are often visible on a log scale well before they're visible on a linear one.",
                "The underlying data is identical - only the display changes, so switching costs nothing and risks nothing.",
                "dB scales are a specific logarithmic form used in some vendor software and standards.",
            ],
            "Make a habit of glancing at every spectrum in both linear and log scale - it takes "
            "seconds and routinely surfaces small peaks that linear display hides."),
        sub("Orders vs. Hz vs. CPM on the X-Axis",
            "A spectrum's horizontal axis can be displayed in Hz, CPM, or orders of running speed, "
            "and the choice affects how easily faults are identified.",
            "On variable-speed machinery, a fault peak moves along a Hz-based axis as speed changes, "
            "making trending between visits genuinely difficult. An order-based axis keeps that same "
            "peak in a fixed position regardless of speed - which turns an awkward comparison into "
            "a straightforward one.",
            "Hz displays absolute frequency in cycles per second. CPM displays it in cycles per "
            "minute. Orders display it as a multiple of the machine's own running speed, so the "
            "running speed peak always sits at exactly 1.0 regardless of actual RPM.",
            "Selected in the display settings, and usually requires the instrument to know the "
            "machine's running speed (from a tach signal or manual entry) before an order axis can "
            "be calculated. Constant-speed machines are commonly viewed in Hz or CPM; variable-speed "
            "machines are best viewed in orders.",
            [
                "An order axis places 1X at 1.0, 2X at 2.0, and so on, regardless of actual machine speed.",
                "Order display requires a known running speed - from a tachometer or entered manually.",
                "Variable-speed machines are far easier to trend and compare in orders.",
                "Bearing defect frequencies are non-integer orders (e.g. 3.58X), which are easy to spot on an order axis.",
                "CPM is often preferred in plants where everyone already thinks in RPM, since running speed in CPM equals RPM numerically.",
            ],
            "On any variable-speed machine, switch the spectrum to an order axis before comparing "
            "against previous readings - it removes speed variation as a confounding factor."),
        sub("Haystacks & Broadband Humps",
            "A broad, rounded 'hump' of raised energy across a frequency range is a distinct "
            "spectrum feature, different from both discrete peaks and a uniformly raised noise "
            "floor.",
            "Haystacks are easy to dismiss as 'just noise', but they carry specific diagnostic "
            "meaning - often pointing at a resonance being excited or at advanced bearing "
            "degradation - so recognizing them as their own category avoids overlooking a "
            "significant finding.",
            "A haystack (or broadband hump) is a wide, rounded region of elevated amplitude "
            "centred on some frequency range, without the sharp definition of a discrete peak, and "
            "without the flat uniformity of a general noise floor rise.",
            "Identified visually by its characteristic mounded shape. Interpreted by noting its "
            "centre frequency and whether that centre stays fixed as machine speed changes: a fixed "
            "centre suggests a natural frequency or resonance being excited, while advanced bearing "
            "wear tends to produce haystacks in the bearing-frequency region that may carry "
            "sidebands.",
            [
                "Shape is the tell: sharp and narrow means a discrete fault frequency; broad and rounded means a haystack.",
                "A haystack whose centre frequency doesn't move with machine speed usually indicates a resonance.",
                "Advanced bearing wear often produces haystacks in the high-frequency region, sometimes with sidebands riding on them.",
                "Distinct from a uniformly raised noise floor, which is flat across the range rather than mounded around a centre.",
                "Late-stage bearing damage sometimes shows haystacks replacing the discrete defect peaks seen earlier - a progression, not an improvement.",
            ],
            "Note the centre frequency of any haystack and check whether it moves when machine "
            "speed changes - that one test separates a resonance from a bearing-related cause."),
    ]),

    dict(name="Signal Processing", category="Fundamentals", subtopics=[
        sub("A Quick Overview",
            "The spectrum plot you read is the result of digitally sampling a continuous vibration "
            "signal and running it through a Fast Fourier Transform (FFT).",
            "Every spectrum you'll ever look at has already been processed through sampling and an "
            "FFT - understanding that this processing pipeline exists, and can introduce its own "
            "artifacts, prevents treating spectrum output as infallible raw truth.",
            "Signal processing, in this context, is the chain of steps - filtering, sampling, and "
            "the FFT - that converts a continuous, real-world vibration signal into the discrete, "
            "frequency-domain spectrum you actually read.",
            "In practice, you don't perform these steps manually; the instrument or software does "
            "them automatically based on settings you choose (Fmax, number of lines, filter type), "
            "but knowing what those settings actually control is what lets you configure them "
            "correctly for a given diagnostic goal.",
            [
                "Understanding the basics explains why settings like Fmax and sample rate matter.",
                "The core pieces are: filtering (isolating frequency ranges of interest), sampling (converting the continuous signal into digital data points), and the FFT itself (converting sampled data into a frequency spectrum).",
                "Every spectrum you look at has already passed through this whole pipeline - none of it is a raw, direct measurement of frequency.",
                "Getting any one of these three steps wrong - a bad filter, wrong sample rate, poor FFT settings - can produce a misleading spectrum even from perfectly good raw vibration.",
            ],
            "When a spectrum looks wrong or unexpected, don't only question the machine - check "
            "the instrument's sampling and processing settings too."),
        sub("Filters",
            "A filter selectively passes or blocks certain frequency ranges.",
            "Without filtering, unwanted frequency content (electrical noise, out-of-range "
            "vibration) would contaminate every measurement - filters are what make clean, "
            "trustworthy spectra possible in the first place.",
            "A filter is a processing step, in hardware or software, that selectively allows some "
            "frequency ranges through while blocking others.",
            "Applied at two points in a typical workflow: inside the sensor/instrument's signal "
            "conditioning (removing noise before digitizing), and afterward in analysis software "
            "(isolating a specific order like 1X for trending) - both controlled by settings you "
            "typically choose when setting up a measurement.",
            [
                "Show up in two places: inside the sensor/instrument chain (removing electrical noise or out-of-range frequencies before recording), and after the fact in software (isolating a specific order like 1X from an orbit or trend plot).",
                "Both uses share the same underlying idea - deliberately excluding frequency content you don't want.",
                "Common filter types include low-pass (blocks high frequencies), high-pass (blocks low frequencies), and band-pass (keeps only a specific range).",
                "Anti-aliasing filters - a specific low-pass filter applied before sampling - are essential to prevent aliasing, covered separately below.",
            ],
            "Know whether a given reading has been filtered and to what range - an unfiltered "
            "'direct' reading and a filtered '1X' reading from the same point can look very "
            "different."),
        sub("Sampling and Aliasing",
            "Sampling converts a continuous analog vibration signal into a series of discrete "
            "digital data points, taken at a chosen sample rate.",
            "The link between sampling and aliasing explains why instrument settings like Fmax "
            "exist and matter - without understanding this connection, Fmax just looks like an "
            "arbitrary number to set, rather than a deliberate safeguard.",
            "Sampling and aliasing are two connected concepts: sampling is the act of digitizing a "
            "continuous signal, and aliasing is the specific error that can result if that "
            "digitization happens too slowly relative to the frequencies present.",
            "In practice, instrument manufacturers handle this automatically via anti-aliasing "
            "filters tied to the chosen Fmax/sample rate setting - your job as the user is mainly "
            "to choose an Fmax high enough to capture the frequencies you actually care about, with "
            "margin.",
            [
                "This digitization step is what makes computer-based frequency analysis possible at all.",
                "It comes with a hard limit on what frequency content can be correctly captured.",
                "That limit is what makes aliasing possible - a real high-frequency signal, if sampled too slowly, can be mathematically misrepresented as a false, lower frequency.",
                "Sampling rate and aliasing are two sides of the same coin - one sets the limit, the other is what happens when that limit is exceeded.",
            ],
            "Think of sample rate as setting a hard ceiling on trustworthy frequency content - "
            "anything reported above that ceiling should be treated with suspicion."),
        sub("Sampling the Signal, Sample Rate",
            "The Nyquist rule sets the real ceiling on what frequency content a given sample rate "
            "can correctly represent.",
            "Understanding the Nyquist relationship is what lets you correctly judge whether a "
            "given instrument setting is actually capable of showing you the fault frequency you're "
            "looking for, before you even take the measurement.",
            "Sample rate is literally how many digital data points per second are recorded from the "
            "continuous analog signal; the Nyquist rule defines the mathematical relationship "
            "between that rate and the highest frequency it can accurately represent.",
            "Applied practically by choosing an Fmax setting on the instrument that's comfortably "
            "above, not just barely above, the highest frequency of diagnostic interest - "
            "remembering that the underlying sample rate will typically be set several times higher "
            "than that Fmax by the instrument automatically.",
            [
                "To accurately capture a given frequency, you must sample at more than twice that frequency - the Nyquist rate.",
                "An instrument's Fmax setting and its underlying sample rate are directly linked.",
                "Choosing a higher Fmax to catch high-frequency bearing or gear-mesh content requires a correspondingly higher sample rate.",
                "Most instruments actually sample somewhat above the strict 2x Nyquist minimum (a common practice uses roughly 2.56x) to leave margin for the anti-aliasing filter's rolloff.",
            ],
            "If you need to see a specific high-frequency fault, like a bearing defect frequency, "
            "make sure the instrument's Fmax is set well above it, not just barely above - with "
            "margin for the anti-aliasing filter."),
        sub("Fast Fourier Transform",
            "The FFT is the specific piece of math that converts a sampled time waveform into a "
            "frequency spectrum.",
            "The FFT is the specific mathematical bridge between 'signal over time' and 'signal by "
            "frequency' - every spectrum plot you've ever looked at exists because of this one "
            "algorithm, making it worth understanding at least conceptually.",
            "The FFT is a mathematical algorithm that decomposes a complex time-domain signal into "
            "the set of individual sine-wave frequency components - each with its own amplitude and "
            "phase - that, added together, reconstruct the original signal.",
            "Applied automatically by instruments and software whenever a spectrum is generated "
            "from waveform data; the main user-facing consequence is that the amount of waveform "
            "data fed into the FFT (and the settings chosen) directly determines the resulting "
            "spectrum's frequency resolution.",
            [
                "Splits a complex signal into the individual frequencies and amplitudes that, added together, would reconstruct it.",
                "Called 'fast' because it's a computationally efficient algorithm for this calculation.",
                "Without it, converting waveforms into spectra in real time on field instruments wouldn't be practical.",
                "The number of 'lines' or points in a spectrum, and the resulting frequency resolution, is a direct consequence of how much time-waveform data went into the FFT.",
            ],
            "If two nearby peaks in a spectrum seem to blend together, more spectral lines (finer "
            "resolution) - not a different scale or zoom - is usually what separates them."),
        sub("Aliasing",
            "Aliasing happens when a real frequency higher than half the sample rate gets "
            "mathematically 'folded' down and misrepresented as a lower, false frequency.",
            "An aliased peak can send a diagnosis in a completely wrong direction, since it appears "
            "to be a real frequency but corresponds to nothing physical on the machine - "
            "recognizing the possibility of aliasing is a necessary sanity check before trusting an "
            "unusual spectrum result.",
            "Aliasing is a specific measurement error where a real frequency above the Nyquist "
            "limit gets mathematically misrepresented in the resulting spectrum as a false, lower "
            "frequency that doesn't actually exist in the machine.",
            "Prevented in practice by anti-aliasing filters built into modern instruments; when "
            "troubleshooting an unexplained peak, checking whether it could be a fold-down of some "
            "real higher frequency (by comparing it against the instrument's Fmax/sample rate "
            "setting) is a useful diagnostic step.",
            [
                "A classic cause of a confusing or seemingly impossible peak in a spectrum.",
                "Anti-aliasing filters (removing frequency content above the Nyquist limit before sampling) are what prevent this in practice.",
                "An aliased peak can appear at a frequency with no physical explanation on the machine - often the first clue something is wrong with the measurement rather than the machine.",
                "Modern digital instruments with proper anti-aliasing filters largely prevent this, but it remains a risk with misconfigured settings or older analog equipment.",
            ],
            "If a spectrum shows a peak that doesn't correspond to anything physically in the "
            "machine and doesn't make sense, consider whether it could be an alias of a real "
            "higher frequency that exceeded the instrument's sampling limit."),
        sub("Sensors & Signal Conditioning",
            "A raw sensor output has to be powered, amplified, and conditioned before it's suitable "
            "for digitizing - and problems in this stage corrupt everything downstream.",
            "Signal conditioning faults produce symptoms that look like machine problems: drifting "
            "readings, a noisy baseline, or missing low-frequency content. Knowing this stage "
            "exists means you can check it before concluding a machine is faulty.",
            "Signal conditioning is the electronics between the sensor element and the digitizer: "
            "providing sensor power, converting high-impedance signals to low-impedance ones, "
            "amplifying to a usable level, and applying initial filtering.",
            "Most modern accelerometers are ICP/IEPE type, meaning the instrument supplies a "
            "constant current down the same cable that carries the signal, and the amplifier is "
            "built into the sensor itself. Older charge-mode accelerometers instead need an external "
            "charge amplifier. Either way, the instrument must be set to the correct sensor type, "
            "and cables must be in good condition, or the readings will be wrong.",
            [
                "ICP/IEPE sensors carry power and signal on the same cable and have built-in amplification - the most common modern arrangement.",
                "Charge-mode sensors need a separate charge amplifier and are more sensitive to cable condition.",
                "The instrument must be configured for the correct sensor type and sensitivity (usually mV/g) or all amplitudes will be scaled wrong.",
                "Damaged cables and poor connections are a frequent cause of noisy or drifting readings that look like machine faults.",
                "Sensor settling time matters - readings taken immediately after attaching a sensor may drift before stabilizing.",
            ],
            "If readings look erratic or drift, check the sensor, cable, and instrument sensitivity "
            "setting before investigating the machine - measurement-chain faults are common and "
            "easy to rule out."),
        sub("Integration & the Ski-Slope Problem",
            "Converting acceleration to velocity or displacement in software can introduce a "
            "characteristic false rise at the low-frequency end of a spectrum.",
            "The ski-slope is a processing artifact that looks exactly like a serious low-frequency "
            "problem, and it appears routinely enough that mistaking it for a real fault is a common "
            "error. Recognizing it saves unnecessary investigation.",
            "Integration is the mathematical conversion from acceleration to velocity (single "
            "integration) or to displacement (double integration), performed in software. The "
            "'ski-slope' is the resulting artifact: a large, smooth rise in amplitude approaching "
            "zero Hz that doesn't correspond to any real machine vibration.",
            "It arises because integration mathematically amplifies low-frequency content, so any "
            "small low-frequency noise or DC offset in the acceleration signal gets magnified "
            "enormously. Prevented or reduced by applying a high-pass filter before integrating, "
            "allowing adequate sensor settling time, and simply disregarding the lowest-frequency "
            "region of integrated spectra where the artifact lives.",
            [
                "Appears as a smooth, steeply rising curve at the extreme low-frequency end of an integrated spectrum.",
                "Caused by integration mathematically amplifying low-frequency noise, not by real machine vibration.",
                "Far more common in double-integrated (displacement) spectra than single-integrated (velocity) ones.",
                "A genuine low-frequency fault produces a discrete peak, not a smooth rising slope - shape is the distinguishing feature.",
                "Allowing sensor settling time before measuring, and using appropriate high-pass filtering, both reduce it.",
            ],
            "Treat a smooth rising slope at the very bottom of an integrated spectrum as an "
            "artifact until proven otherwise - real faults appear as peaks, not slopes."),
    ]),

    dict(name="Time Waveform Analysis", category="Signal Behavior", subtopics=[
        sub("A Simple Time Waveform",
            "Close to a single clean sine wave, usually corresponding to one dominant frequency, "
            "like pure unbalance.",
            "Being able to instantly recognize a 'boring,' clean waveform as boring - rather than "
            "over-analyzing it - saves diagnostic time; not every waveform needs deep scrutiny, and "
            "simple ones are a useful calibration for what 'normal' looks like.",
            "A simple time waveform is one that closely resembles a single, smooth sine wave, "
            "indicating that one frequency dominates the signal almost completely.",
            "Recognized visually by its smooth, regular, repeating shape with no sharp "
            "irregularities; its corresponding spectrum will confirm this by showing essentially "
            "one dominant peak and little else.",
            [
                "The easiest waveform shape to read - smooth, regular, and repeating at a consistent rate.",
                "The baseline shape everything more complex gets compared against.",
                "A simple waveform's period - the time for one full cycle - directly corresponds to the frequency you'd see as a single peak in the spectrum.",
            ],
            "If a waveform looks like a clean sine wave, you likely already know what the "
            "spectrum will show before you even look at it - a single dominant peak."),
        sub("A More Complex Waveform",
            "Combines multiple frequencies, or shows sharp irregular features.",
            "Complex waveforms are where real diagnostic work usually happens - most interesting "
            "faults produce complexity, not simplicity, so developing comfort reading complex "
            "waveforms directly expands what you can diagnose from time-domain data alone.",
            "A complex waveform combines multiple overlapping frequencies and/or shows irregular, "
            "non-sinusoidal features, reflecting either several vibration sources at once or "
            "nonlinear mechanical behavior distorting the signal.",
            "Approached practically by looking for any repeating sub-pattern within the overall "
            "complexity - a recurring spike, a recurring envelope shape - rather than trying to "
            "characterize the whole waveform as one thing, then cross-checking findings against the "
            "spectrum.",
            [
                "Reflects either a mix of vibration sources overlapping, or nonlinear mechanical behavior (rubbing, looseness) distorting what would otherwise be a smooth signal.",
                "Reading a complex waveform usually means picking out repeating sub-patterns within it, rather than characterizing the whole thing as one shape.",
                "A complex waveform's corresponding spectrum will show multiple peaks rather than one dominant peak.",
            ],
            "Don't try to interpret a complex waveform's overall shape at a glance - look for a "
            "repeating sub-pattern within it first, then check the spectrum to confirm what "
            "frequencies are actually present."),
        sub("Where Does the Waveform Come From?",
            "The time waveform is literally what the sensor measured over time, before any "
            "frequency-domain math is applied.",
            "Knowing that the waveform is the unprocessed original signal - and the spectrum is a "
            "derived, processed product of it - is what justifies using the waveform as a sanity "
            "check whenever a spectrum result looks questionable.",
            "The time waveform is the direct, literal record of what the vibration sensor measured, "
            "moment by moment, before any frequency-domain processing, like an FFT, has been "
            "applied to it.",
            "Accessed in practice by selecting 'waveform' or 'time domain' view on an instrument or "
            "in software, typically alongside the spectrum view of the same measurement, so the two "
            "can be compared side by side.",
            [
                "Amplitude plotted directly against time.",
                "Useful for sanity-checking whether a spectrum peak represents real physical motion or a processing artifact.",
                "The waveform is the unprocessed ground truth the spectrum was calculated from.",
                "Every spectrum is derived from a waveform, but not every waveform detail survives being converted into a spectrum.",
            ],
            "When a spectrum peak looks suspicious or doesn't make sense, go back to the "
            "waveform it was calculated from before assuming the machine has a real problem."),
        sub("Use Acceleration, Velocity, or Displacement?",
            "Choosing which parameter to view the waveform in follows the same logic as for "
            "overall readings.",
            "The choice of unit for the waveform view has real diagnostic consequences, not a "
            "cosmetic preference, since the wrong choice can genuinely hide an impact event that's "
            "clearly visible in the right one.",
            "Just as with overall readings, a time waveform can be displayed in displacement, "
            "velocity, or acceleration units, and each emphasizes different aspects of the same "
            "underlying physical motion.",
            "Applied practically by defaulting to acceleration when specifically looking for "
            "impacting/bearing damage, and switching to velocity or displacement when the concern "
            "is lower-frequency, larger-scale motion instead.",
            [
                "Acceleration best reveals sharp, fast impacts.",
                "Velocity and displacement tend to smooth those same events out and can hide them entirely.",
                "If specifically hunting for impacting (bearing or gear tooth damage), acceleration is usually the parameter that shows it most clearly.",
                "The same underlying event can look dramatically different - an obvious spike vs. barely visible - purely because of which parameter was chosen.",
            ],
            "If you're not sure why a suspected impact isn't showing up in a waveform, check "
            "whether you're viewing it in velocity or displacement rather than acceleration."),
        sub("The Vibration Signal",
            "Every vibration signal, however complex it looks, is really just amplitude varying "
            "over time.",
            "Internalizing that 'the vibration signal' is always a sum of everything happening at "
            "once reframes how you should approach a confusing reading - it's not broken or wrong, "
            "it's just complex, and the job is to decompose it, not to expect it to look simple.",
            "The vibration signal is the single, combined, continuous measurement produced by every "
            "rotating element and every active fault on a machine, all superimposed into one trace.",
            "Approached practically through the combination of time-waveform inspection and "
            "spectrum decomposition (FFT), which together are the two main tools for separating "
            "that one combined signal back into its individual, diagnostically meaningful parts.",
            [
                "Produced by the combined effect of every rotating element and every fault currently present on the machine, all overlapping in one continuous trace.",
                "The whole point of both time-waveform and spectrum analysis is separating that one combined signal back out into its individual, physically meaningful contributors.",
                "No single measurement - waveform or spectrum - is 'more true' than the other; they're two mathematically equivalent representations of the same signal.",
            ],
            "Remember that a 'confusing' waveform isn't a broken measurement - it's simply the "
            "real, combined sum of everything happening on the machine at once."),
        sub("Waveform Patterns",
            "A handful of recurring waveform patterns are worth learning to recognize by eye.",
            "Pattern recognition by eye is genuinely faster than waiting for statistical indicators "
            "or spectra to confirm a finding - an experienced analyst often spots a problem in the "
            "waveform before any calculated number moves.",
            "Waveform patterns are the handful of visually recognizable shapes - repeating spikes, "
            "flattened/clipped peaks, pulsing envelopes - that each correspond to specific "
            "underlying mechanical conditions.",
            "Learned through deliberate practice: compare waveforms from known-good and known-"
            "faulty machines side by side, and build a mental library of what impacting, clipping, "
            "and beating/modulation actually look like at a glance.",
            [
                "Repeating sharp spikes: impacting - often bearing or gear tooth damage.",
                "A flattened or clipped-looking peak: mechanical looseness, or a signal overloading the sensor's range.",
                "A slow pulsing envelope: beating or amplitude modulation.",
                "Recognizing these shapes at a glance is often faster than waiting for a spectrum or statistical indicator to confirm what the waveform is already showing directly.",
            ],
            "Build a mental checklist of these three patterns - spikes, flattening, pulsing "
            "envelope - and scan for them specifically every time you open a waveform."),
        sub("Waveforms and Spectra",
            "The waveform and the spectrum are two views of the exact same underlying signal - "
            "one in time, one in frequency.",
            "Relying on only one of the two representations means systematically missing whatever "
            "that representation is weak at showing - using both together is simply more thorough, "
            "and the extra effort routinely pays off in catching things a single-view approach "
            "would miss.",
            "The waveform and spectrum are two mathematically equivalent representations of the "
            "identical underlying signal, one organized by time and the other by frequency, each "
            "revealing different aspects of the same data.",
            "Applied practically by making it standard procedure to glance at both views for any "
            "measurement that looks unusual, rather than defaulting to only the spectrum (more "
            "common in routine screening) or only the waveform.",
            [
                "Neither one tells the whole story alone.",
                "The spectrum is often easier to read for steady-state faults, since it separates overlapping frequencies that would be hard to pick apart in the waveform.",
                "The waveform preserves timing-based information - impacts, clipping, waveform shape - that the spectrum's averaging process can obscure or wash out.",
                "A thorough look uses both together, not one instead of the other.",
            ],
            "Make it a habit to check both the waveform and the spectrum for any measurement "
            "that looks unusual - each one catches things the other can miss."),
        sub("'Beating' (in the Waveform)",
            "In the time waveform specifically, beating appears as a slow, regular rise and fall "
            "in the overall amplitude envelope.",
            "Recognizing beating's specific waveform signature - a slow rise-and-fall envelope - "
            "lets you flag it immediately during a walk-around inspection, well before you'd have "
            "time to pull up and analyze a full spectrum on the spot.",
            "In the waveform, beating appears as a slow, regular growing-and-shrinking pattern in "
            "the overall envelope of peaks, distinct from and slower than the faster oscillation "
            "happening within that envelope.",
            "Identified visually by watching the peak heights across the waveform rise and fall in "
            "a steady, slower rhythm, then confirmed formally by checking the corresponding "
            "spectrum for two closely spaced peaks.",
            [
                "The waveform's peaks grow and shrink in a steady cycle, distinct from the faster oscillation happening underneath it.",
                "This envelope shape is often the first place beating is actually noticed, before anyone thinks to check the spectrum.",
                "Confirming it as true beating, rather than AM, still requires checking the spectrum for two close peaks.",
            ],
            "If you spot a slow pulsing envelope in a waveform, note it and go confirm in the "
            "spectrum whether it's beating (two close peaks) or AM (one peak with sidebands)."),
        sub("Amplitude Modulation (in the Waveform)",
            "Shows up in the waveform very similarly to beating - a rising and falling envelope.",
            "Since AM and beating look alike in the waveform, knowing this in advance prevents "
            "jumping to a conclusion based on the waveform alone - it sets the expectation that a "
            "spectrum check is required before diagnosing either one.",
            "In the waveform, amplitude modulation produces a rising-and-falling envelope pattern "
            "that's visually very similar to beating, despite arising from a different mechanism "
            "(one modulated source, not two independent ones).",
            "Distinguished from beating the same way regardless of which one is suspected: by "
            "checking the spectrum for sidebands around a single carrier (AM) versus two separate "
            "close peaks (beating).",
            [
                "The underlying cause is a single mechanism being modulated rather than two independent sources interfering.",
                "The two can look alike in the waveform.",
                "Confirming which one you're seeing usually still requires checking the spectrum for sidebands (modulation) versus two separate close peaks (beating).",
            ],
            "Don't try to distinguish AM from beating by eye in the waveform alone - the "
            "spectrum check is what actually settles it."),
        sub("Amplitude Modulation and Gears",
            "Gear problems are one of the most common real-world sources of amplitude modulation.",
            "Gearboxes are common, and AM from a damaged tooth is one of their most frequent and "
            "most diagnosable failure signatures - specifically knowing to look for this pattern on "
            "gear equipment is a high-value, narrowly applicable skill.",
            "This is a specific, common real-world case of amplitude modulation where a damaged or "
            "eccentric gear tooth causes the gear mesh frequency to pulse in strength once per "
            "revolution of that particular gear.",
            "Diagnosed practically by measuring the envelope's pulsing rate in the waveform, or "
            "sideband spacing in the spectrum, and matching that rate against each gear's "
            "individual rotational speed in the train, to identify specifically which gear is "
            "damaged.",
            [
                "A damaged or eccentric gear tooth can cause the gear mesh frequency's strength to pulse once per revolution of that specific gear.",
                "Produces a clear envelope pattern in the waveform.",
                "The modulating rate corresponds to the damaged gear's own rotational speed.",
                "Measuring that envelope's pulsing rate (or the sideband spacing in the spectrum) can identify which gear in a train is actually at fault.",
            ],
            "On a gearbox with multiple gears at different speeds, match the modulation/envelope "
            "rate to each gear's own rotational speed to identify which specific gear is "
            "damaged."),
        sub("'Non-linear' Clipped Vibration",
            "A waveform that looks flattened or 'clipped' at its peaks, rather than smoothly "
            "rounded.",
            "The two possible causes of a clipped-looking waveform - mechanical looseness versus a "
            "measurement/instrument problem - call for completely different next steps, so "
            "correctly distinguishing them avoids wasted maintenance effort or a missed real "
            "fault.",
            "Clipped vibration is a waveform whose peaks appear artificially flattened rather than "
            "smoothly rounded, caused either by a genuine mechanical constraint limiting motion in "
            "one direction, or by the signal exceeding the sensor/instrument's measurement range.",
            "Distinguished practically by checking the instrument's measurement range setting first "
            "to rule out simple overload, then, if the range was adequate, treating genuine "
            "flattening - especially if asymmetric - as a real mechanical looseness symptom.",
            [
                "Usually indicates either mechanical looseness (something limiting how far the shaft can move in one direction) or a signal overloading the sensor/instrument's measurement range.",
                "Distinguishing the two matters: a genuinely clipped sensor reading is a measurement problem to fix, while true mechanical clipping in the waveform is a real symptom.",
                "Mechanical clipping often looks asymmetric (flattened more on one side), while sensor overload clipping tends to be more symmetric.",
            ],
            "If a waveform looks clipped, first check whether the sensor/instrument range was "
            "appropriate for the amplitude present - rule out a measurement error before "
            "concluding it's mechanical."),
        sub("Impacting",
            "Brief, sharp, repeating spikes in the waveform - often the earliest visible sign of "
            "bearing or gear defects.",
            "Impacting is frequently the very first visible evidence of a developing bearing or "
            "gear fault, showing up in the waveform before overall vibration levels or even the "
            "spectrum clearly reflect it - which makes waveform inspection a genuinely early-"
            "warning tool, not just a confirmation step.",
            "Impacting is a waveform pattern of brief, sharp, repeating spikes, produced by a "
            "physical impact event, like a ball passing over a defect, occurring at a regular "
            "interval as the machine rotates.",
            "Diagnosed by measuring the time spacing between repeating spikes, converting that "
            "spacing to a frequency, and comparing it against the machine's known bearing defect "
            "frequencies or gear mesh rate to identify the specific fault.",
            [
                "Frequently shows up clearly in the waveform before it's obvious in the overall vibration level or even the spectrum.",
                "When a spectrum looks ambiguous, or a crest factor/kurtosis reading has crept up, checking the time waveform for repeating spikes is usually the fastest way to get direct confirmation.",
                "The spacing between repeating spikes often corresponds to a specific bearing defect frequency or gear mesh event, worth timing against known component frequencies.",
            ],
            "Time the spacing between repeating spikes in a waveform and compare it to known "
            "bearing/gear frequencies - that spacing is often the fastest route from 'something's "
            "impacting' to 'here's exactly what's impacting.'"),
        sub("Time-Synchronous Averaging",
            "Time-synchronous averaging isolates the vibration of one specific shaft by averaging "
            "waveform data locked to that shaft's own rotation, cancelling everything else.",
            "On a gearbox with several shafts, every shaft's vibration overlaps in the same "
            "measurement, making it genuinely hard to tell which shaft or gear is at fault. "
            "Time-synchronous averaging solves exactly this problem, and it's one of the most "
            "powerful techniques available for multi-shaft machines.",
            "Time-synchronous averaging (TSA) is a processing technique that averages many "
            "consecutive waveform segments, each triggered by a once-per-revolution tach pulse from "
            "one chosen shaft. Vibration synchronous with that shaft reinforces across the "
            "averages; everything not synchronous with it - other shafts, random noise - averages "
            "toward zero.",
            "Requires a tachometer signal from the shaft of interest. The instrument collects many "
            "revolutions of waveform data, aligns each to the tach trigger, and averages them. The "
            "result is a waveform showing only that shaft's contribution, which can then be examined "
            "for tooth-by-tooth gear detail or converted to a spectrum.",
            [
                "Requires a tach reference from the specific shaft being isolated - it cannot be done without one.",
                "Vibration synchronous with the chosen shaft is retained; everything else is suppressed.",
                "Particularly valuable on multi-shaft gearboxes where several sources overlap in one measurement.",
                "More averages give better separation, at the cost of longer measurement time.",
                "Enables tooth-by-tooth examination of a specific gear, which raw waveform data usually can't support.",
            ],
            "On a gearbox where you can't tell which shaft is causing a problem, TSA on each shaft "
            "in turn is usually faster than trying to untangle the combined spectrum analytically."),
    ]),

    dict(name="Sampling & Resolution", category="Measurement Setup", subtopics=[
        sub("Lines of Resolution & Fmax",
            "Two settings together define a spectrum's detail: Fmax (the highest frequency shown) "
            "and lines of resolution (how many discrete bins that range is divided into).",
            "These two settings determine whether a fault is even visible. Too low an Fmax and "
            "bearing frequencies fall off the end of the chart; too few lines and two adjacent "
            "peaks merge into one meaningless blob. Most 'I couldn't see the fault' situations "
            "trace back to one of these being set wrong.",
            "Fmax is the upper frequency limit of the spectrum display. Lines of resolution (often "
            "400, 800, 1600, 3200) is the number of frequency bins the 0-to-Fmax range is split "
            "into. Bin width - the actual frequency resolution - is simply Fmax divided by the "
            "number of lines.",
            "Set on the instrument before measuring. A practical approach: choose Fmax high enough "
            "to include the highest fault frequency of interest with margin (for bearings, several "
            "times the highest defect frequency), then choose lines high enough that the bin width "
            "is small enough to separate the peaks you care about. More lines costs measurement "
            "time, so it's a deliberate trade.",
            [
                "Bin width (Hz per line) = Fmax / number of lines. At Fmax 1,000 Hz with 800 lines, each bin is 1.25 Hz wide.",
                "Two peaks closer together than one bin width cannot be separated, no matter how you zoom the display.",
                "Higher Fmax with the same line count means coarser resolution - the two settings trade against each other.",
                "Route screening commonly uses 400-800 lines; detailed diagnostic work often uses 1600-6400.",
                "More lines requires a longer sample time, which is why high-resolution measurements take longer.",
            ],
            "Before measuring, calculate your bin width (Fmax / lines) and check it's smaller than "
            "the spacing between the peaks you need to separate - it takes seconds and prevents a "
            "wasted trip."),
        sub("Sample Time",
            "The time needed to collect one measurement is fixed by the resolution settings - it "
            "isn't a free choice.",
            "Technicians are often surprised that a high-resolution measurement takes many seconds "
            "or even minutes, and are tempted to cut it short. Understanding that sample time is "
            "mathematically required, not optional padding, prevents truncated measurements that "
            "produce inaccurate spectra.",
            "Sample time is the duration of continuous waveform data required to produce a spectrum "
            "at the chosen resolution. It's determined by the relationship: sample time equals the "
            "number of lines divided by Fmax.",
            "Calculated automatically by the instrument once Fmax and lines are set, and displayed "
            "before or during measurement. The practical consequence is that fine resolution on a "
            "low Fmax can require a surprisingly long measurement - and the machine must run at "
            "steady speed and load throughout, or the data is contaminated.",
            [
                "Sample time = lines / Fmax. 800 lines at 400 Hz Fmax needs 2 seconds of data per average.",
                "Low-frequency, high-resolution measurements take the longest - this is unavoidable physics, not instrument slowness.",
                "Machine speed and load must stay steady for the whole sample time, or the spectrum smears.",
                "Multiple averages multiply the total time - 8 averages means roughly 8 times the single-sample duration.",
                "If a machine can't hold steady conditions that long, reduce resolution rather than accept smeared data.",
            ],
            "If a machine's speed drifts during a long high-resolution measurement, the resulting "
            "peaks smear and widen - reduce the line count rather than trying to interpret a "
            "smeared spectrum."),
        sub("Dynamic Range",
            "Dynamic range is the span between the largest and smallest signals an instrument can "
            "capture in the same measurement.",
            "A bearing fault can be a thousand times smaller than the 1X unbalance peak on the same "
            "machine. If the instrument's dynamic range can't span that gap, the small signal is "
            "lost in quantization noise - present in reality, absent from the data.",
            "Dynamic range is the ratio between the largest signal an instrument can measure without "
            "clipping and the smallest it can distinguish from its own internal noise, usually "
            "expressed in dB. It's set primarily by the analog-to-digital converter's bit depth.",
            "In practice, modern 24-bit instruments have ample dynamic range for most work. Where "
            "it becomes limiting, the answer is usually to reduce the dominant signal's influence - "
            "filtering out the low-frequency content before digitizing, or using envelope processing "
            "that deliberately isolates the small high-frequency signals of interest.",
            [
                "Expressed in dB; higher bit-depth converters give wider dynamic range.",
                "A very large low-frequency peak can mask much smaller high-frequency content in the same measurement.",
                "Envelope/demodulation techniques sidestep this by isolating the small signals before analysis.",
                "Clipping at the top end and quantization noise at the bottom end are the two boundaries.",
                "Using a logarithmic amplitude display helps you see small peaks, but only if the instrument actually captured them.",
            ],
            "If you suspect a bearing fault is being masked by a large 1X peak, use envelope "
            "processing rather than just switching to a log display - the log scale can't reveal "
            "data the instrument never resolved."),
        sub("Windowing",
            "A window function tapers each data block's ends before the FFT, preventing a "
            "distortion called leakage.",
            "Without windowing, a genuine single-frequency peak smears sideways into neighbouring "
            "bins, making it look broader and shorter than it is - and potentially burying small "
            "nearby peaks under the smear. Windowing is applied by default precisely because raw "
            "unwindowed data is usually unusable.",
            "The FFT mathematically assumes the data block it's given repeats endlessly. When the "
            "block's start and end don't line up, that assumed repetition creates artificial "
            "discontinuities, which show up as energy smeared across frequencies - leakage. A window "
            "function tapers the block's ends toward zero so it joins smoothly to itself.",
            "Applied automatically by the instrument, with the window type selectable. The taper "
            "slightly reduces measured amplitude, so instruments apply a correction factor to "
            "compensate. Users mainly need to choose the appropriate window type for the "
            "measurement being made.",
            [
                "Leakage is energy from one real frequency spreading into adjacent frequency bins.",
                "Windowing tapers the data block's ends to reduce that spreading.",
                "A window is applied by default in essentially all vibration measurements - the question is which one, not whether.",
                "Windowing slightly reduces peak amplitude, which instruments correct for automatically.",
                "Leakage is worst when a signal's frequency falls between two bin centres rather than exactly on one.",
            ],
            "Don't disable windowing to 'see the raw data' - unwindowed spectra of real machine "
            "vibration are almost always harder to read, not more honest."),
        sub("Window Type & Bandwidth",
            "Different window functions trade frequency accuracy against amplitude accuracy, and "
            "the right choice depends on what you're measuring.",
            "Using an impact-test window on steady machine vibration, or vice versa, produces "
            "measurably wrong results. The choice is small but genuinely affects the numbers you "
            "then compare against standards or baselines.",
            "Hanning is a general-purpose window with good frequency resolution and moderate "
            "amplitude accuracy. Flat Top sacrifices frequency resolution for excellent amplitude "
            "accuracy. Uniform (rectangular, i.e. no window) is used for transient events that "
            "already start and end at zero. Each window also has an effective noise bandwidth that "
            "slightly widens apparent peaks.",
            "Chosen by task: Hanning for routine spectrum measurement of continuous machine "
            "vibration (the default for almost all CM work); Flat Top when the exact amplitude of a "
            "specific peak matters, such as calibration or precise balancing readings; Uniform for "
            "bump/impact tests where the signal naturally decays to zero within the block.",
            [
                "Hanning: the standard choice for routine vibration spectra.",
                "Flat Top: best amplitude accuracy, used when a peak's exact height matters more than its exact frequency.",
                "Uniform/rectangular: for transient or impact data that already begins and ends at zero.",
                "Each window has an effective noise bandwidth that slightly broadens peaks - Flat Top broadens them the most.",
                "Comparing readings taken with different windows introduces small but real amplitude differences.",
            ],
            "Keep the window type consistent across a trend - switching from Hanning to Flat Top "
            "mid-program will shift measured amplitudes and look like a machine change."),
        sub("Averaging",
            "Averaging several spectra together suppresses random content and stabilizes the "
            "repeating content you actually want to see.",
            "A single spectrum from a real machine is noisy enough that small but genuine peaks can "
            "be hard to distinguish from random fluctuation. Averaging is what makes those peaks "
            "reliably visible and makes repeat measurements comparable.",
            "Averaging combines several consecutive measurements into one result. Linear averaging "
            "weights all samples equally. Exponential averaging weights recent samples more heavily, "
            "giving a continuously updating view. Peak-hold retains the maximum value seen in each "
            "bin rather than averaging.",
            "Set as a number of averages on the instrument, typically 4 to 16 for routine work. More "
            "averages give a cleaner, more repeatable spectrum at the cost of proportionally longer "
            "measurement time. Peak-hold is used specifically when capturing the worst case during "
            "a transient event like a startup.",
            [
                "Random noise reduces with averaging; repeating (real) signals stay put and become clearer.",
                "Linear averaging is the standard choice for routine measurement.",
                "Exponential averaging suits live monitoring where you want a continuously updating display.",
                "Peak-hold captures maximum values rather than averaging - used for transients and startups.",
                "More averages means proportionally longer total measurement time.",
            ],
            "Use the same number of averages every time you measure a given point - changing it "
            "alters how much noise is suppressed and makes trend comparisons less reliable."),
        sub("Overlap Processing",
            "Overlap processing reuses part of each data block in the next average, cutting total "
            "measurement time substantially.",
            "On low-frequency, high-resolution measurements where each sample takes many seconds, "
            "the time saving from overlap is the difference between a practical route measurement "
            "and one nobody has time to take.",
            "Overlap processing means each successive averaged block reuses a percentage of the "
            "previous block's data rather than collecting entirely fresh data. At 50% overlap, half "
            "of each block is data already used in the prior average.",
            "Enabled as a percentage setting on the instrument, commonly 50% or 75%. The saving "
            "comes because fewer genuinely new samples are needed for a given number of averages. "
            "The trade-off is that overlapping averages aren't fully statistically independent, so "
            "very high overlap gives diminishing noise-reduction benefit.",
            [
                "Reduces total measurement time significantly, especially for long sample times.",
                "50% is a common, well-balanced setting.",
                "Overlapped averages are less statistically independent, so noise reduction per average is slightly reduced.",
                "Most valuable on low-Fmax, high-line-count measurements where sample time dominates.",
                "Keep the setting consistent across a trend, as with all other measurement settings.",
            ],
            "If route measurements are taking too long, enabling 50% overlap is usually a better "
            "first step than cutting resolution or averages."),
        sub("Reducing Noise",
            "Several techniques reduce unwanted content in a measurement, each addressing a "
            "different noise source.",
            "Noise directly limits the smallest fault you can detect. Since early fault detection "
            "is the entire point of condition monitoring, systematically reducing noise directly "
            "extends how early you can catch problems.",
            "Noise in this context covers several distinct things: random electrical noise in the "
            "measurement chain, mechanical noise from adjacent equipment, and broadband vibration "
            "from the machine itself that isn't related to the fault you're hunting.",
            "Addressed with different tools depending on source: averaging for random noise; good "
            "grounding, quality cables and correct sensor setup for electrical noise; solid sensor "
            "mounting for coupling losses; time-synchronous averaging for isolating one shaft from "
            "others; and band-pass filtering or envelope processing to focus on a specific frequency "
            "region.",
            [
                "Averaging suppresses random noise but not steady interference from another machine.",
                "Poor grounding and damaged cables are a common and easily fixed electrical noise source.",
                "Time-synchronous averaging removes everything not synchronous with a chosen shaft.",
                "Envelope processing isolates repetitive impacts from broadband background.",
                "Solid sensor mounting improves signal quality more than almost any processing setting.",
            ],
            "Before reaching for processing tricks, check the physical measurement first - mounting, "
            "cable condition and grounding fix more noise problems than any instrument setting."),
        sub("Resolution & Accuracy",
            "Resolution (the ability to separate two nearby frequencies) and accuracy (how correct "
            "a measured value is) are different properties that are easy to confuse.",
            "An instrument can display a frequency to two decimal places while being genuinely "
            "unable to distinguish two peaks 5 Hz apart. Confusing displayed precision with real "
            "resolving power leads to over-confident readings of merged or smeared peaks.",
            "Frequency resolution is set by bin width (Fmax divided by lines) and determines whether "
            "two nearby peaks appear separately. Amplitude accuracy depends on window type, "
            "calibration, sensor mounting and whether a peak falls cleanly on a bin centre. "
            "Displayed decimal places reflect neither.",
            "Managed by setting resolution appropriate to the separation you need, using Flat Top "
            "windowing when amplitude accuracy specifically matters, keeping sensors calibrated and "
            "properly mounted, and treating a peak's reported frequency as accurate only to roughly "
            "its bin width.",
            [
                "Resolution is about separating peaks; accuracy is about getting values right.",
                "A displayed value with many decimal places is not evidence of fine resolution.",
                "Peak frequency is only trustworthy to about one bin width.",
                "Amplitude accuracy is affected by window choice, calibration and mounting quality.",
                "Peaks falling between bin centres read slightly low in amplitude unless a Flat Top window is used.",
            ],
            "Treat a reported peak frequency as accurate to roughly one bin width, not to the "
            "decimal places shown - and if that isn't precise enough, increase the line count."),
    ]),

    dict(name="Natural Frequencies & Resonance", category="Machine Behaviour", subtopics=[
        sub("Introduction to Resonance",
            "Resonance is what happens when a forcing frequency coincides with a structure's own "
            "natural frequency, dramatically amplifying vibration.",
            "Resonance can turn a small, otherwise harmless force into destructive vibration - and "
            "because the root cause is a structural property rather than a component defect, "
            "repeatedly replacing components will never fix it. Recognizing resonance prevents a "
            "very expensive troubleshooting dead end.",
            "Every mechanical structure has natural frequencies at which it prefers to vibrate. When "
            "an applied force happens to occur at one of those frequencies, energy accumulates "
            "instead of dissipating, and vibration amplitude grows far beyond what the same force "
            "would produce at any other frequency.",
            "Diagnosed by establishing whether a problem frequency stays fixed while machine speed "
            "changes (indicating a structural natural frequency) versus tracking with speed "
            "(indicating a rotating-component force). Once confirmed, correction targets the "
            "structure or the forcing frequency, not the rotating components.",
            [
                "Amplification at resonance can be many times the vibration the same force would cause elsewhere.",
                "The root cause is a structural property, so replacing bearings or rebalancing won't resolve it.",
                "A forcing frequency and a natural frequency must coincide for resonance to occur - either can be changed to fix it.",
                "Resonance is often discovered when a machine is fine at one speed and unacceptable at another.",
                "Repeated component failures at one specific location are a classic hidden-resonance symptom.",
            ],
            "If a machine has had repeated failures of the same component despite correct repairs, "
            "test for resonance before replacing anything again."),
        sub("Natural Frequencies",
            "A natural frequency is a rate at which a structure will vibrate freely once disturbed, "
            "determined by its mass and stiffness.",
            "Natural frequencies are fixed properties you can measure and predict, which means "
            "resonance problems are preventable at design stage and correctable afterwards - but "
            "only if you know where the natural frequencies actually are.",
            "A natural frequency is determined by the relationship between a structure's stiffness "
            "and its mass: increasing stiffness raises the natural frequency, while increasing mass "
            "lowers it. Any real structure has many natural frequencies, not just one.",
            "Determined either by measurement (bump testing, or watching a coastdown) or by "
            "calculation and modelling at design stage. Once known, they're compared against the "
            "machine's forcing frequencies to check whether any dangerous coincidences exist.",
            [
                "Higher stiffness raises natural frequency; higher mass lowers it.",
                "Every structure has multiple natural frequencies, each with its own mode shape.",
                "Natural frequencies don't change with machine speed - that's the key diagnostic property.",
                "They can shift if the structure changes - loosened bolts, added mass, corroded supports.",
                "Knowing them lets you check in advance whether any operating speed will excite one.",
            ],
            "Keep a record of measured natural frequencies for critical machines - if one shifts "
            "over time, the structure itself has changed, which is a finding in its own right."),
        sub("Describing the Natural Frequency",
            "Natural frequencies are characterized by more than just their frequency value - "
            "damping and mode shape complete the picture.",
            "Two structures can share the same natural frequency but behave completely differently: "
            "one may amplify vibration modestly, the other severely. Frequency alone doesn't tell "
            "you how dangerous a resonance is or how to fix it.",
            "A natural frequency is described by three things: the frequency itself, the damping "
            "(how quickly free vibration decays), and the mode shape (the pattern of relative motion "
            "across the structure at that frequency).",
            "Measured together in a bump test or modal analysis. Damping is estimated from how "
            "quickly the ringing decays, or from the sharpness of the resonant peak. Mode shape is "
            "mapped by taking measurements at multiple locations and comparing amplitude and phase "
            "between them.",
            [
                "Frequency: where the resonance sits.",
                "Damping: how much energy is dissipated per cycle, controlling how severe the amplification is.",
                "Mode shape: which parts of the structure move, how much, and in what relative direction.",
                "A lightly damped resonance produces a tall, narrow peak; heavy damping gives a low, broad one.",
                "Mode shape determines where added stiffness or mass will actually be effective.",
            ],
            "When planning a resonance fix, get the mode shape first - stiffening a point that "
            "barely moves in that mode will have almost no effect."),
        sub("Damping & Amplification Factor",
            "Damping determines how much a resonance amplifies vibration, and the amplification "
            "factor quantifies it.",
            "Damping is often the most practical thing to change when a resonance can't be shifted "
            "in frequency. Understanding it tells you whether a resonance is a manageable nuisance "
            "or a genuine hazard.",
            "Damping is the mechanism by which vibration energy is dissipated, usually as heat. The "
            "amplification factor (often called Q) expresses how much vibration is magnified at "
            "resonance compared to the same force applied well away from resonance - low damping "
            "gives high amplification.",
            "Estimated from a Bode plot's peak sharpness during a startup or coastdown, or from how "
            "quickly a bump test's ringing decays. Increased in practice by adding damping "
            "treatments, constrained-layer materials, or in rotating machinery by adjusting bearing "
            "design and oil film characteristics.",
            [
                "Low damping means a tall, narrow, severe resonance peak; high damping means lower and broader.",
                "Amplification factor (Q) is a direct measure of how much worse vibration gets at resonance.",
                "Adding damping is often easier than shifting a natural frequency in an existing installation.",
                "Damping also controls how quickly free vibration dies away after a disturbance.",
                "In rotating machinery, the bearing oil film is a significant source of damping.",
            ],
            "If a resonance can't be moved out of the operating range, adding damping is usually "
            "the next most practical option - it reduces severity even though the resonance "
            "remains."),
        sub("Mode Shapes",
            "A mode shape is the specific deflection pattern a structure takes when vibrating at "
            "one of its natural frequencies.",
            "Mode shape determines where a fix will and won't work. Adding stiffness at a node "
            "(a point that doesn't move in that mode) accomplishes nothing, while the same "
            "reinforcement at an antinode can be highly effective.",
            "At each natural frequency, a structure deflects in a characteristic pattern. Points of "
            "maximum motion are antinodes; points of minimum or zero motion are nodes. Each natural "
            "frequency has its own distinct mode shape.",
            "Mapped by measuring amplitude and relative phase at many points across the structure "
            "while it's excited at the frequency of interest, then assembling those readings into a "
            "picture of the deflection pattern. Operating deflection shape (ODS) analysis does this "
            "using the machine's own running vibration.",
            [
                "Antinodes move most; nodes barely move at all.",
                "Stiffening or adding mass at a node has little effect on that mode.",
                "Each natural frequency has its own separate mode shape.",
                "Relative phase between measurement points is what reveals the shape, not amplitude alone.",
                "ODS analysis maps how a structure actually moves under real operating conditions.",
            ],
            "Before committing to a structural modification, map the mode shape - it tells you "
            "exactly where the modification needs to go to actually work."),
        sub("Critical Speed",
            "Critical speed is a rotor speed at which running speed coincides with one of the "
            "rotor's own natural frequencies.",
            "Passing through a critical speed during startup or shutdown produces a large, "
            "predictable vibration excursion. Knowing where the criticals are lets operators pass "
            "through them promptly rather than lingering, and lets analysts recognize the resulting "
            "vibration as normal rather than a fault.",
            "Critical speed is the specific rotational speed at which the rotor's own natural "
            "frequency is excited by its running speed (typically the 1X unbalance force). Machines "
            "are classified as rigid rotors (operating below the first critical) or flexible rotors "
            "(operating above one or more criticals).",
            "Identified from Bode or polar plots taken during startup or coastdown, where the "
            "critical appears as an amplitude peak accompanied by a phase shift approaching 180 "
            "degrees. Operators are usually instructed to accelerate through criticals rather than "
            "hold speed near them.",
            [
                "A critical speed shows on a Bode plot as an amplitude peak plus a large phase shift.",
                "Rigid rotors run below the first critical; flexible rotors run above one or more.",
                "Vibration rising then falling during startup is normal behaviour passing through a critical.",
                "Lingering at a critical speed is avoided because amplification there can be severe.",
                "Turbomachinery Insights covers rotor criticals in more depth for large fluid-film machines.",
            ],
            "Learn where your machine's criticals are from its startup Bode plot - vibration "
            "peaking as it accelerates through them is expected, not a fault."),
        sub("Plant Resonances",
            "Resonance isn't limited to the rotor - piping, baseplates, structural steel, and "
            "foundations all have natural frequencies that can be excited.",
            "Plant resonances are frequently missed because the vibration is measured on the machine "
            "while the resonant structure is something nearby. Repeated failures with no explanation "
            "found on the machine itself are a classic signature.",
            "A plant resonance is a natural frequency belonging to structure surrounding the "
            "machine - piping runs, support steel, baseplates, platforms, foundations - rather than "
            "the rotor itself.",
            "Detected by measuring vibration on the suspected structure rather than only on the "
            "machine bearings, and by bump testing that structure directly. Corrected by stiffening "
            "or adding supports, adding mass, adding damping, or changing the forcing frequency.",
            [
                "Piping resonance is very common and often produces vibration far from the driving machine.",
                "Baseplate and foundation resonances can amplify normal machine forces substantially.",
                "Measuring only at bearings will miss a resonance in nearby structure.",
                "Structural modifications (bracing, gusseting) shift natural frequencies by changing stiffness.",
                "Loose or deteriorated foundations lower stiffness, which lowers natural frequencies into the operating range.",
            ],
            "If bearing readings look acceptable but something nearby is clearly shaking, measure "
            "on that structure directly - the resonance may not be on the machine at all."),
        sub("Why Resonances Matter",
            "Resonance amplifies otherwise acceptable forces into damaging vibration, and it can't "
            "be fixed by servicing the rotating components.",
            "Resonance is responsible for a large share of 'we fixed it and it came back' "
            "situations. Recognizing it early avoids repeated unnecessary repairs and the escalating "
            "cost and frustration that follow.",
            "Because resonance multiplies whatever force is applied at that frequency, a level of "
            "unbalance or misalignment that would be perfectly tolerable at another speed becomes "
            "destructive. The resulting high vibration accelerates bearing, seal and coupling wear, "
            "and can cause fatigue cracking in structure.",
            "Managed either by eliminating the coincidence (changing operating speed, or changing "
            "the structure's natural frequency) or by reducing severity (adding damping, and "
            "minimizing the exciting force through precision balancing and alignment).",
            [
                "Small forces become large vibration - the force isn't the problem, the amplification is.",
                "Repeated component failures despite correct repair is the classic warning sign.",
                "Precision balancing and alignment reduce the exciting force, which helps but doesn't cure resonance.",
                "Structural fatigue cracking can result from sustained operation at resonance.",
                "Variable-speed machines are especially exposed, since their speed range may sweep across a natural frequency.",
            ],
            "When a repair doesn't hold, stop and test for resonance before repeating it - "
            "otherwise you're treating a symptom of a structural problem."),
        sub("Detecting Resonance Problems",
            "Several observable signs point toward resonance before any formal test is performed.",
            "Recognizing these signs early redirects troubleshooting toward the right test, saving "
            "the time that would otherwise go into component inspections that find nothing.",
            "Resonance detection means identifying the characteristic behaviours that distinguish a "
            "structural amplification problem from a rotating-component fault, using data you "
            "usually already have.",
            "Applied by checking several things: does vibration change sharply with small speed "
            "changes; does one direction show far higher amplitude than the others; does a coastdown "
            "show a distinct amplitude peak with a phase shift; and does a problem frequency stay "
            "fixed while speed varies.",
            [
                "A large vibration change from a small speed change strongly suggests resonance.",
                "Highly directional vibration (one axis far exceeding others) is a common resonance signature.",
                "A coastdown peak accompanied by roughly 180 degrees of phase shift is strong evidence.",
                "A problem frequency that doesn't move as speed changes indicates a natural frequency.",
                "Repeated unexplained component failures at one location are an indirect but telling clue.",
            ],
            "If you have a variable-speed drive, slowly varying speed while watching amplitude is "
            "the quickest informal resonance check available."),
        sub("Testing for Resonance",
            "Bump tests and coastdown tests are the two standard ways to measure natural frequencies "
            "directly.",
            "These tests convert a suspicion into a measured number. Knowing the actual natural "
            "frequency is what lets you decide whether it genuinely overlaps an operating speed and "
            "how far it needs to be moved.",
            "A bump (impact) test strikes the structure with a soft-faced hammer while measuring the "
            "resulting free vibration, revealing natural frequencies as peaks in the response. A "
            "coastdown test records vibration as the machine slows through its speed range, "
            "revealing resonances as amplitude peaks with accompanying phase shifts.",
            "Bump testing is done with the machine stopped, striking near an expected antinode, "
            "using a uniform window and peak-hold or a small number of averages. Coastdown testing "
            "records amplitude and phase against speed continuously, then plots them as a Bode or "
            "polar plot for interpretation.",
            [
                "Bump test: machine off, strike the structure, read natural frequencies from the response spectrum.",
                "Use a uniform/rectangular window for bump tests, since the signal decays to zero naturally.",
                "Coastdown test: record amplitude and phase versus speed as the machine slows.",
                "A resonance appears on a Bode plot as an amplitude peak with a phase shift approaching 180 degrees.",
                "Strike near a point that actually moves in the suspected mode, or the response may be too weak to read.",
            ],
            "For a quick bump test, strike with something soft-faced and non-marking, and take "
            "several strikes - a single strike can miss the mode or excite the wrong one."),
        sub("Correcting Resonance Problems",
            "Resonance is corrected by separating the forcing frequency from the natural frequency, "
            "or by reducing the amplification.",
            "Having a clear list of the available correction routes prevents the common trap of "
            "endlessly rebalancing a machine whose real problem is structural - and helps you pick "
            "the option that's actually feasible in your situation.",
            "There are four practical approaches: change the natural frequency (stiffness or mass), "
            "change the forcing frequency (operating speed), add damping, or reduce the exciting "
            "force. Which is viable depends on the machine and the installation.",
            "Applied by first identifying the mode shape so modifications are placed where they "
            "matter, then choosing the practical option: adding bracing or gussets to raise "
            "stiffness, adding mass to lower the natural frequency, adjusting operating speed if "
            "the process allows, adding damping treatments, or precision-balancing and aligning to "
            "minimize the exciting force.",
            [
                "Stiffening raises natural frequency; adding mass lowers it - either can move it clear of the forcing frequency.",
                "Changing operating speed is often the simplest fix when the process permits it.",
                "Adding damping reduces severity without moving the resonance.",
                "Precision balancing and alignment reduce the force being amplified - always worth doing, but not a cure alone.",
                "Map the mode shape before modifying, so changes go where they will actually have effect.",
            ],
            "Aim to move the natural frequency at least 15-20% clear of the forcing frequency - "
            "getting it only marginally clear often leaves the machine still noticeably affected."),
    ]),

    dict(name="Diagnosing Unbalance", category="Fault Diagnosis", subtopics=[
        sub("What Is Unbalance?",
            "Unbalance exists when a rotor's mass is not evenly distributed around its axis of "
            "rotation, creating a rotating centrifugal force.",
            "Unbalance is the single most common cause of machine vibration, so it's the first thing "
            "most analysts check - and because it's relatively straightforward to correct, "
            "identifying it accurately has a high practical payoff.",
            "Unbalance is a condition where the rotor's mass centreline doesn't coincide with its "
            "rotational centreline. The resulting uneven mass distribution generates a centrifugal "
            "force that rotates with the shaft, producing vibration at exactly running speed (1X).",
            "Detected by a dominant 1X peak in the spectrum, typically with radial (horizontal and "
            "vertical) vibration much higher than axial, and stable, repeatable phase readings. "
            "Corrected by adding or removing weight at a calculated angular position - which is what "
            "this app's Rotor Balance tool computes.",
            [
                "Produces vibration at exactly 1X running speed, the defining characteristic.",
                "Radial vibration dominates; axial vibration is normally low for pure unbalance.",
                "Centrifugal force grows with the square of speed - doubling speed quadruples the force.",
                "Phase readings are stable and repeatable, unlike looseness.",
                "The waveform is typically close to a clean sine wave.",
            ],
            "A dominant 1X with low axial vibration and stable phase is the textbook unbalance "
            "picture - but confirm it against the look-alike faults before adding weight."),
        sub("Mass Unbalance & Centrifugal Force",
            "The force unbalance generates depends on the unbalance mass, its radius from the "
            "centre, and the square of rotational speed.",
            "The speed-squared relationship explains why a rotor that's acceptable at low speed can "
            "be violent at full speed, and why high-speed machines demand far tighter balance "
            "tolerances than slow ones.",
            "Centrifugal force from unbalance is proportional to the unbalance mass, times its "
            "radius from the rotational centre, times the square of rotational speed. The product of "
            "mass and radius is the 'unbalance' itself, typically expressed in gram-millimetres "
            "(g-mm) or gram-inches.",
            "Used practically in two ways: to understand why the same unbalance produces "
            "dramatically different vibration at different speeds, and to calculate correction "
            "weights - since a small weight at a large radius produces the same effect as a large "
            "weight at a small radius.",
            [
                "Force is proportional to mass x radius x speed squared.",
                "Doubling speed quadruples the centrifugal force from the same unbalance.",
                "Unbalance is quantified as mass x radius, commonly in gram-millimetres (g-mm).",
                "A 10 g weight at 100 mm radius equals 1,000 g-mm - the same as 20 g at 50 mm.",
                "This trade lets you use a convenient weight size at whatever radius the rotor allows.",
            ],
            "When a correction weight won't physically fit at the calculated radius, recalculate "
            "for a different radius using the mass x radius relationship - the effect is what "
            "matters, not the specific weight."),
        sub("Causes of Unbalance",
            "Unbalance arises from manufacturing variation, in-service changes, and assembly "
            "practices.",
            "Knowing the likely cause guides whether balancing alone is sufficient or whether the "
            "underlying condition will simply recreate the unbalance - a rotor with ongoing erosion "
            "will go out of balance again regardless of how well it's corrected today.",
            "Causes divide into three groups: manufacturing and material issues (casting voids, "
            "machining tolerances, uneven material density), in-service changes (product buildup, "
            "erosion, corrosion, lost or damaged blades, thermal distortion), and assembly issues "
            "(keys, coupling fits, added components, previous repairs).",
            "Addressed by investigating what changed when unbalance appears suddenly, and by "
            "correcting the underlying cause where it's ongoing - cleaning fouling, repairing "
            "erosion, or fixing an assembly problem - rather than only adding correction weight.",
            [
                "Manufacturing: casting voids, uneven density, machining tolerances.",
                "In-service buildup: product, scale or dirt accumulating unevenly on a rotor.",
                "Erosion, corrosion or a lost blade removes mass unevenly.",
                "Thermal distortion can cause unbalance that appears only at operating temperature.",
                "Assembly: keys, couplings, and previously added balance weights that shifted or were lost.",
            ],
            "If a machine that was balanced recently goes out of balance again, look for an "
            "ongoing cause like fouling or erosion - re-balancing without fixing it just resets "
            "the clock."),
        sub("Static Unbalance",
            "Static unbalance is a single heavy spot in one plane, causing both ends of the rotor "
            "to move together, in phase.",
            "Static unbalance is the simplest type and can be corrected in a single plane, so "
            "correctly identifying it as static rather than couple or dynamic avoids unnecessary "
            "two-plane work.",
            "Static (or force) unbalance is a condition where the rotor's mass centreline is "
            "parallel to, but offset from, the rotational centreline - effectively a single heavy "
            "spot. Named 'static' because it can be detected with the rotor stationary on knife "
            "edges, where the heavy spot rolls to the bottom.",
            "Identified by 1X vibration at both bearings that is roughly in phase (phase difference "
            "near zero degrees) and by a phase relationship that stays consistent along the rotor. "
            "Corrected by adding weight opposite the heavy spot in a single correction plane.",
            [
                "Both bearings vibrate in phase at 1X - the defining signature.",
                "Detectable with the rotor stationary, unlike couple or dynamic unbalance.",
                "Correctable in a single plane, making it the simplest balancing case.",
                "Common on narrow rotors such as single-width fans and thin discs.",
                "Phase across the rotor is consistent, not opposed.",
            ],
            "Check phase at both bearings before starting: if they're in phase, single-plane "
            "balancing will work and you can skip the extra runs two-plane requires."),
        sub("Couple Unbalance",
            "Couple unbalance is two equal heavy spots 180 degrees apart at opposite ends of the "
            "rotor, making the ends move in opposition.",
            "Couple unbalance cannot be corrected in a single plane, no matter how carefully. "
            "Recognizing it prevents a frustrating cycle of single-plane attempts that never fully "
            "resolve the vibration.",
            "Couple unbalance is a condition where the rotor's mass centreline intersects the "
            "rotational centreline at the rotor's centre of gravity but is tilted relative to it. "
            "The result behaves like two equal unbalances at opposite ends, 180 degrees apart.",
            "Identified by 1X vibration at both bearings that is roughly 180 degrees out of phase. "
            "Correction requires two planes - weights added at both ends, 180 degrees apart from "
            "each other.",
            [
                "The two bearings vibrate roughly 180 degrees out of phase - the defining signature.",
                "Cannot be detected with the rotor stationary; it only appears during rotation.",
                "Requires two-plane correction; single-plane balancing cannot resolve it.",
                "More common on longer rotors where the two ends are well separated.",
                "Produces a rocking motion rather than the rotor's centre translating.",
            ],
            "If both bearings show similar 1X amplitude but are close to 180 degrees apart in "
            "phase, plan for two-plane balancing from the start rather than attempting single "
            "plane first."),
        sub("Dynamic Unbalance",
            "Dynamic unbalance is the general, real-world case - a combination of static and couple "
            "unbalance together.",
            "Almost every real rotor has dynamic unbalance rather than pure static or pure couple, "
            "so understanding it as the general case sets correct expectations: phase differences "
            "will usually be some intermediate value, not a clean 0 or 180 degrees.",
            "Dynamic unbalance is any combination of static and couple unbalance existing "
            "simultaneously, which is the normal condition for real rotors. The rotor's mass "
            "centreline is both offset from and tilted relative to the rotational centreline.",
            "Identified by 1X vibration at both bearings with a phase difference somewhere between "
            "0 and 180 degrees, rather than close to either extreme. Corrected by two-plane "
            "balancing, which resolves both the static and couple components together.",
            [
                "The normal real-world case - pure static or pure couple unbalance is rare.",
                "Phase difference between bearings falls somewhere between 0 and 180 degrees.",
                "Requires two-plane balancing to correct fully.",
                "Two-plane balancing automatically handles both components; they don't need separating manually.",
                "The nearer the phase difference is to 0 or 180, the more the condition resembles pure static or pure couple.",
            ],
            "Don't try to mentally separate dynamic unbalance into its static and couple parts - "
            "a proper two-plane balance handles both simultaneously."),
        sub("Overhung Rotor Unbalance",
            "Overhung rotors - where the rotating mass sits outboard of both bearings - produce "
            "unusually high axial vibration from unbalance.",
            "Overhung rotors break the normal rule that unbalance shows low axial vibration. Without "
            "knowing this, high axial readings on an overhung pump or fan get misdiagnosed as "
            "misalignment, sending the repair in the wrong direction.",
            "An overhung rotor is one where the impeller, fan or disc is mounted beyond the "
            "bearings rather than between them. The overhung mass creates a bending moment when "
            "unbalanced, producing significant axial as well as radial vibration.",
            "Identified by high 1X in both axial and radial directions on an overhung machine, with "
            "axial phase readings typically in phase across the bearings. Correction often requires "
            "two planes because both a force and a moment component are present.",
            [
                "Common on overhung pumps, fans and blowers where the impeller is outboard of the bearings.",
                "Produces high axial 1X, which would suggest misalignment on a between-bearings machine.",
                "Axial phase readings across the two bearings are typically in phase.",
                "Often requires two-plane correction due to the combined force and moment.",
                "Knowing the machine's construction is essential to interpreting the readings correctly.",
            ],
            "Always establish whether a machine is overhung before interpreting high axial 1X - on "
            "overhung rotors it points at unbalance, not automatically at misalignment."),
        sub("Vertical Machines",
            "Vertically mounted machines have different stiffness characteristics and support "
            "arrangements, which changes how unbalance presents.",
            "Vertical machines don't follow the horizontal-exceeds-vertical convention that most "
            "guidance assumes, and they're often more flexible near the top. Applying horizontal-"
            "machine expectations to them produces misleading conclusions.",
            "Vertical machines are mounted with the shaft axis vertical, typically supported at the "
            "bottom or partway up, leaving an unsupported upper section. Their stiffness varies with "
            "direction and height in ways horizontal machines' do not.",
            "Measured by taking readings at multiple heights as well as multiple directions, since "
            "amplitude commonly rises toward the top where support is weakest. Reference directions "
            "are usually specified relative to a fixed plant feature rather than horizontal/vertical, "
            "and should be recorded consistently.",
            [
                "Vibration typically increases with height on vertically mounted machines.",
                "Stiffness often differs substantially between the two radial directions.",
                "The usual 'horizontal exceeds vertical' rule doesn't apply in the same way.",
                "Measure at multiple heights, not just at the bearings, to see the deflection pattern.",
                "Structural resonance is comparatively common on tall vertical installations.",
            ],
            "On vertical machines, define and document your measurement directions against a fixed "
            "plant reference - otherwise readings taken on different days won't be comparable."),
        sub("Diagnosing Mass Unbalance",
            "Confirming unbalance means checking a specific set of characteristics together, not "
            "just seeing a 1X peak.",
            "A 1X peak alone is not diagnostic - several different faults produce one. Working "
            "through the full checklist is what separates a confident diagnosis from a guess, and "
            "prevents balancing a machine whose real problem is something else.",
            "Diagnosing unbalance means verifying a combination of evidence: a dominant 1X peak, "
            "low harmonic content, radial-dominant vibration (except on overhung rotors), stable "
            "repeatable phase, a near-sinusoidal waveform, and amplitude that rises with speed "
            "roughly as speed squared.",
            "Applied as a checklist before any correction work: check the spectrum for 1X dominance "
            "and low harmonics; compare radial versus axial; take phase at both bearings and confirm "
            "it's stable on repeat; check the waveform shape; and if possible, vary speed and "
            "confirm amplitude changes as expected.",
            [
                "1X dominant, with 2X and higher harmonics comparatively small.",
                "Radial vibration much higher than axial - except on overhung rotors.",
                "Phase stable and repeatable between measurements.",
                "Waveform close to a single clean sine wave.",
                "Amplitude rises sharply with speed, roughly as speed squared.",
                "Phase between bearings indicates whether it's static, couple, or dynamic unbalance.",
            ],
            "Run the full checklist before adding any weight - the cost of five extra minutes of "
            "checking is far lower than the cost of a balancing attempt on a misdiagnosed fault."),
        sub("Unbalance vs. Look-alike Faults",
            "Several other faults also produce a dominant 1X peak, and distinguishing them before "
            "balancing is essential.",
            "Attempting to balance a bent shaft, an eccentric rotor, or a resonance problem will "
            "not work and can waste hours. Every experienced analyst has a story about balancing a "
            "machine that turned out to have a different problem entirely.",
            "The main look-alikes are: misalignment (usually adds a significant 2X and high axial "
            "vibration), bent shaft (high axial 1X with a characteristic axial phase difference), "
            "eccentric rotor or sheave (1X that's highly directional), resonance (1X amplified "
            "dramatically at one specific speed), and looseness (1X present but with unstable phase "
            "and extra harmonics).",
            "Separated by checking the distinguishing features: axial vibration level, 2X content, "
            "phase stability, directionality, and behaviour as speed changes. Only once these are "
            "ruled out is balancing the correct response.",
            [
                "Misalignment: high axial vibration plus a notable 2X peak.",
                "Bent shaft: high axial 1X with an axial phase difference across the machine.",
                "Eccentricity: 1X strongly directional, much higher in one radial direction than the other.",
                "Resonance: 1X dramatically amplified at one particular speed, normal elsewhere.",
                "Looseness: unstable phase and a train of harmonics alongside the 1X.",
                "Balancing corrects none of these - it only addresses genuine mass unbalance.",
            ],
            "If balancing a machine produces little improvement despite correct calculations, stop "
            "and re-diagnose - persisting usually means the original diagnosis was wrong."),
        sub("Assessing Severity of Unbalance",
            "Unbalance severity is judged both by measured vibration against standards and by the "
            "residual unbalance against balance quality grades.",
            "Knowing when a machine is 'balanced enough' prevents both under-correcting (leaving "
            "damaging vibration) and over-correcting (spending hours chasing an improvement that "
            "doesn't matter for that machine's duty).",
            "Two different frameworks apply. Vibration severity standards (ISO 10816/20816) judge "
            "the resulting vibration against zone limits. Balance quality grades (ISO 21940-11, "
            "formerly ISO 1940) specify permissible residual unbalance for a rotor type, expressed "
            "as a G-grade such as G6.3 or G2.5.",
            "Applied by measuring overall vibration and comparing against the appropriate ISO zone "
            "for the machine class, and separately by calculating the residual unbalance achieved "
            "and comparing it against the G-grade specified for that rotor type. Lower G numbers "
            "mean tighter balance requirements.",
            [
                "ISO 10816/20816 judges the resulting vibration; ISO 21940-11 judges the residual unbalance itself.",
                "Balance quality grades are written as G followed by a number - lower means tighter.",
                "G6.3 is typical for general industrial machinery; G2.5 and below for higher-speed precision equipment.",
                "Permissible residual unbalance decreases as operating speed increases.",
                "Machine duty and criticality should inform how tight a target is worth pursuing.",
            ],
            "Set a target grade before you start balancing - without one, it's easy to keep "
            "chasing diminishing improvements long past the point of practical benefit."),
    ]),

    dict(name="Heavy Spot & High Spot", category="Balancing", subtopics=[
        sub("What Is the Heavy Spot?",
            "The heavy spot is the physical angular location of the excess mass on the rotor - the "
            "actual unbalance.",
            "The heavy spot is what you're ultimately trying to counteract when balancing, but it's "
            "not what a vibration sensor directly measures. Understanding the distinction between "
            "what exists physically and what's observed is the foundation of correct balancing.",
            "The heavy spot is the angular position on the rotor where the unbalance mass actually "
            "sits. It's a fixed physical property of the rotor: it doesn't move relative to the "
            "shaft, and it remains at the same angular position regardless of rotational speed.",
            "Located indirectly, by measuring the high spot and then accounting for the lag angle "
            "between them. Correction is made by adding weight 180 degrees from the heavy spot, or "
            "by removing material at the heavy spot itself.",
            [
                "A fixed physical location on the rotor - it doesn't change with speed.",
                "Cannot be measured directly by a vibration sensor.",
                "Correction weight goes 180 degrees opposite the heavy spot.",
                "Its angular position relative to the shaft's reference mark is what balancing calculations ultimately determine.",
                "Removing material at the heavy spot is an equally valid correction to adding weight opposite it.",
            ],
            "Remember the heavy spot is where the problem physically is, not where the sensor "
            "reports peak vibration - those two are the same only well below the first critical "
            "speed."),
        sub("What Is the High Spot?",
            "The high spot is the point on the shaft that passes closest to the sensor at the "
            "moment of peak vibration - what the instrument actually measures.",
            "The high spot is what phase readings report, so every balancing calculation starts "
            "from it. Confusing it with the heavy spot leads to placing correction weight at the "
            "wrong angle, especially on machines running above a critical speed.",
            "The high spot is the angular position of maximum shaft deflection as observed by a "
            "sensor - the point on the shaft surface closest to the probe when vibration peaks. It's "
            "an observed response, not a physical property of the rotor.",
            "Measured directly as the phase angle from a vibration reading referenced to the shaft's "
            "tachometer mark. It's the raw input to balancing calculations, which then derive the "
            "correction position from it.",
            [
                "What a phase measurement actually reports.",
                "A response to the unbalance force, not the unbalance itself.",
                "Its position relative to the heavy spot changes with speed.",
                "On a circular 1X-filtered orbit, the Keyphasor dot marks the high spot at the timing event.",
                "Balancing calculations work from the high spot and account for the lag internally.",
            ],
            "When reading phase, be clear that you're measuring the high spot - the vector "
            "balancing method handles converting that into the correct weight position "
            "automatically."),
        sub("The Relationship Between Them",
            "The high spot lags behind the heavy spot by an angle that depends on how far the "
            "machine is running relative to its critical speed.",
            "This lag angle is exactly why balancing calculations use vectors rather than simple "
            "arithmetic - the relationship isn't fixed, so the correction position can't be derived "
            "from phase alone without accounting for it.",
            "The angular difference between the heavy spot and the high spot is called the lag "
            "angle. It's caused by the phase lag inherent in any mechanical system's response to a "
            "rotating force, and it varies with the ratio of running speed to critical speed.",
            "Handled automatically by the influence coefficient method: the trial run measures how "
            "the machine actually responds, capturing the lag angle implicitly in the influence "
            "coefficient, so it never has to be calculated separately.",
            [
                "The high spot always lags the heavy spot, never leads it.",
                "Lag angle depends on the ratio of running speed to critical speed, and on damping.",
                "The vector balancing method captures this automatically through the trial run.",
                "This is why a trial run is necessary rather than optional.",
                "Attempting to balance using phase alone, without a trial run, means guessing the lag angle.",
            ],
            "Don't try to estimate the lag angle manually - the trial run measures the machine's "
            "actual response including the lag, which is far more reliable than any assumption."),
        sub("Effect of Critical Speed on the Lag Angle",
            "The lag angle shifts from near 0 degrees well below critical, through 90 degrees at "
            "critical, toward 180 degrees well above critical.",
            "A machine running above its first critical will have its heavy spot roughly opposite "
            "the measured high spot. Balancing it as though the two coincide puts the correction "
            "weight almost exactly where the heavy spot already is - doubling the unbalance instead "
            "of cancelling it.",
            "As running speed increases relative to the rotor's critical speed, the phase lag "
            "between the applied unbalance force and the resulting deflection increases: "
            "approximately 0 degrees well below critical, 90 degrees at critical, and approaching "
            "180 degrees well above critical.",
            "Accounted for automatically by the influence coefficient method, but worth "
            "understanding when interpreting results - it explains why a machine running above "
            "critical needs correction weight roughly at the measured high spot rather than opposite "
            "it, which can look counterintuitive.",
            [
                "Well below critical: lag near 0 degrees - high spot and heavy spot nearly coincide.",
                "At critical: lag near 90 degrees, with maximum amplification.",
                "Well above critical: lag approaching 180 degrees - high spot roughly opposite heavy spot.",
                "Damping affects how quickly the lag transitions through this range.",
                "This is visible directly on a Bode plot as the phase shift through resonance.",
            ],
            "If your calculated correction seems to be in a counterintuitive direction, check "
            "whether the machine runs above its first critical - that reverses the intuition "
            "entirely."),
        sub("Using Heavy & High Spot in Balancing",
            "Practical balancing works from measured high spot data and lets the influence "
            "coefficient method resolve the heavy spot position.",
            "Understanding the roles of both concepts makes the balancing procedure make sense "
            "rather than feeling like a black box - which matters when results don't come out as "
            "expected and you need to reason about why.",
            "In the balancing workflow, the high spot is the measured input (amplitude and phase "
            "from the original run), and the heavy spot is what the calculation implicitly locates. "
            "The influence coefficient derived from the trial run encodes the relationship between "
            "them for that specific machine at that specific speed.",
            "Applied in the standard sequence: measure the original vibration vector (high spot), "
            "add a known trial weight at a known angle, measure again, calculate the influence "
            "coefficient from the difference, then compute the correction weight. The lag angle "
            "never needs to be determined explicitly.",
            [
                "Original run vector = the high spot response to the existing unbalance.",
                "Trial run changes the unbalance in a known way, revealing how this machine responds.",
                "The influence coefficient encodes both sensitivity and lag angle for that machine and speed.",
                "The correction weight is computed from those two measurements, not from theory.",
                "Because the coefficient is machine-specific, it stays valid for future balancing at the same speed.",
            ],
            "Save the influence coefficient once you've calculated it - re-balancing the same "
            "machine at the same speed later can skip the trial run entirely."),
    ]),

    dict(name="Vector Method Balancing", category="Balancing", subtopics=[
        sub("Why Vector Balancing Works",
            "Vibration readings have both an amplitude and a phase angle, which makes them vectors "
            "- and vectors can be added and subtracted to predict the effect of adding weight.",
            "Treating vibration as just a number (amplitude only) loses the directional information "
            "needed to know where to put correction weight. Vector arithmetic is what makes it "
            "possible to calculate a correction rather than guess and check repeatedly.",
            "A vibration reading of, say, 5.0 mm/s at 60 degrees is a vector: a magnitude and a "
            "direction. Unbalance forces combine as vectors, so the vibration caused by two "
            "unbalances is the vector sum of their individual effects - which means adding a known "
            "weight produces a predictable, calculable change.",
            "Applied by measuring the vibration vector before and after adding a known trial weight. "
            "The vector difference between those two readings reveals exactly how that machine "
            "responds to weight at that location, which then allows calculating the weight needed "
            "to cancel the original vibration.",
            [
                "A vibration reading is a vector: amplitude (magnitude) plus phase (angle).",
                "Vector subtraction of two readings gives the effect of the change between them.",
                "This is why phase measurement is mandatory for calculated balancing.",
                "Amplitude-only 'trial and error' balancing works eventually but takes far more runs.",
                "The method makes no assumptions about the machine - it measures the actual response.",
            ],
            "Always record both amplitude and phase for every balancing run - an amplitude-only "
            "reading cannot be used in the calculation and means repeating the run."),
        sub("Vector Arithmetic Refresher",
            "Balancing calculations require converting between polar form (amplitude and angle) and "
            "rectangular form (horizontal and vertical components) to add and subtract vectors.",
            "Vectors can't be added or subtracted directly in polar form - you can't simply subtract "
            "the angles and magnitudes. Converting to rectangular form first is the step that makes "
            "the arithmetic work, and skipping it is the most common source of balancing "
            "calculation errors.",
            "Polar form expresses a vector as magnitude at an angle, e.g. 5.0 at 60 degrees. "
            "Rectangular form expresses it as two perpendicular components: x = magnitude x "
            "cos(angle), y = magnitude x sin(angle). Converting back: magnitude = square root of "
            "(x squared + y squared), angle = arctangent of (y / x), with care taken over which "
            "quadrant the result falls in.",
            "Used in every step of the calculation: convert both vectors to rectangular, add or "
            "subtract the x components and the y components separately, then convert the result back "
            "to polar to get a usable amplitude and angle.",
            [
                "To rectangular: x = A x cos(theta), y = A x sin(theta).",
                "To polar: A = sqrt(x squared + y squared), theta = atan2(y, x).",
                "Add or subtract vectors by adding or subtracting their x and y components separately.",
                "Never subtract polar magnitudes and angles directly - the result will be wrong.",
                "Watch the quadrant when converting back, or the angle can come out 180 degrees off.",
            ],
            "When converting back to polar, sanity-check the quadrant against the signs of x and y "
            "- a positive x with negative y must land between 270 and 360 degrees."),
        sub("The Influence Coefficient Concept",
            "The influence coefficient describes how much vibration change a given weight produces "
            "at a given location, for one specific machine at one specific speed.",
            "This single quantity captures everything about how the machine responds - its "
            "sensitivity, its lag angle, its dynamics - without needing any theoretical model. It's "
            "why the method works on any machine without knowing its design details.",
            "The influence coefficient is the vibration change per unit of weight added, expressed "
            "as a vector. Mathematically it's the vector difference between the trial run and "
            "original run readings, divided by the trial weight.",
            "Determined from the trial run and then used to calculate the required correction. "
            "Because it's specific to a machine, speed and weight location, it can be saved and "
            "reused for future balancing of that same machine, letting you skip the trial run "
            "entirely on subsequent jobs.",
            [
                "Calculated as (trial run vector minus original run vector) divided by trial weight.",
                "Expressed as vibration per gram, with an associated angle.",
                "Specific to one machine, one speed, and one weight plane/radius.",
                "Encodes both how sensitive the machine is and the lag angle, without either being calculated separately.",
                "Reusable - saving it lets future balancing skip the trial run.",
            ],
            "Record the influence coefficient, the speed and the weight radius together - the "
            "coefficient is only valid for that exact combination."),
        sub("Step 1: The Original Run",
            "Measure and record the machine's existing 1X vibration amplitude and phase before "
            "changing anything.",
            "This reading is the baseline everything else is calculated against. An inaccurate or "
            "unstable original run corrupts every subsequent step, so getting it right is worth "
            "extra care.",
            "The original run captures the vibration vector produced by the rotor's existing "
            "unbalance: a 1X-filtered amplitude and phase reading, taken at a defined measurement "
            "point and direction, with the machine at its normal operating speed.",
            "Performed by running the machine at operating speed until conditions are stable, then "
            "recording the 1X amplitude and phase. The reading should be repeated to confirm it's "
            "stable - drifting readings indicate either a thermal effect that hasn't settled or a "
            "different fault such as looseness.",
            [
                "Record 1X-filtered amplitude and phase, not overall vibration.",
                "Let the machine reach stable running conditions first - thermal effects can shift readings.",
                "Repeat the reading to confirm stability before proceeding.",
                "Note the measurement point, direction, speed and phase convention alongside the numbers.",
                "An unstable original run means stop and re-diagnose rather than continuing to balance.",
            ],
            "If the original run reading won't hold steady, don't proceed - unstable phase usually "
            "means looseness, which balancing will not fix."),
        sub("Step 2: The Trial Run",
            "Add a known weight at a known angular position and measure the resulting vibration "
            "vector.",
            "The trial run is what makes the method self-calibrating: it measures how this specific "
            "machine responds, removing the need for any assumptions about sensitivity or lag angle.",
            "The trial run introduces a deliberate, known change to the rotor's unbalance. The "
            "resulting change in vibration reveals the machine's response characteristics.",
            "Performed by attaching a trial weight at a measured radius and angular position, "
            "restarting to the same operating speed, letting conditions stabilize, and recording "
            "amplitude and phase again. The trial weight should be large enough to produce a clear "
            "change - a common guideline is one that changes amplitude by at least 30%, or shifts "
            "phase by at least 30 degrees.",
            [
                "Record the trial weight's mass, radius and angular position precisely.",
                "Run at the same speed and conditions as the original run.",
                "The change should be clear - at least 30% amplitude change or 30 degrees phase shift.",
                "Too small a trial weight gives a change lost in measurement noise.",
                "Too large a trial weight risks unacceptable vibration during the run.",
                "If little changes, the weight plane may be poorly chosen or the fault may not be unbalance.",
            ],
            "If the trial run produces almost no change, stop and reconsider - either the trial "
            "weight is too small, the plane is wrong, or the problem isn't unbalance at all."),
        sub("Step 3: Calculating the Influence Coefficient",
            "Subtract the original vector from the trial vector, then divide by the trial weight.",
            "This step converts two raw measurements into the machine's response characteristic - "
            "the piece of information that makes the correction calculable rather than iterative.",
            "The vector difference (trial run minus original run) is the effect of the trial weight "
            "alone. Dividing that effect by the trial weight gives the effect per gram - the "
            "influence coefficient.",
            "Calculated by converting both vectors to rectangular form, subtracting component by "
            "component, converting the result back to polar, then dividing the magnitude by the "
            "trial weight mass and noting the angle.",
            [
                "Effect vector = trial run vector - original run vector (done in rectangular form).",
                "Influence coefficient = effect vector / trial weight mass.",
                "Result is expressed as vibration units per gram, at some angle.",
                "The coefficient's angle includes the machine's lag angle automatically.",
                "A very small effect vector means the trial weight was inadequate - repeat with more.",
            ],
            "Keep the trial weight in place while calculating - the correction is computed relative "
            "to the current state, and removing it changes the situation."),
        sub("Step 4: Calculating the Correction Weight",
            "Divide the original vibration vector by the influence coefficient, then reverse the "
            "direction, to get the weight and angle needed.",
            "This is the payoff step - it produces a specific mass at a specific angle that should "
            "cancel the original vibration in one move, rather than requiring repeated guessing.",
            "The required correction is whatever weight produces a vibration effect equal and "
            "opposite to the original run vector. Dividing the original vector by the influence "
            "coefficient gives the magnitude and angle of the weight needed to reproduce the "
            "original vibration; adding 180 degrees reverses it to cancel instead.",
            "Calculated as: correction weight magnitude = original amplitude divided by influence "
            "coefficient magnitude; correction angle = original angle minus influence coefficient "
            "angle, plus 180 degrees. The result is a mass to install at a specified angular "
            "position, at the same radius used for the trial weight.",
            [
                "Correction magnitude = original vibration magnitude / influence coefficient magnitude.",
                "Correction angle = (original angle - influence coefficient angle) + 180 degrees.",
                "The +180 is what turns 'reproduce the vibration' into 'cancel it'.",
                "Install at the same radius the trial weight used, or scale the mass accordingly.",
                "If the calculated weight is impractically large or small, reconsider the weight radius.",
            ],
            "Use the mass x radius relationship if the calculated weight won't physically fit - "
            "the same effect can be achieved with a different mass at a different radius."),
        sub("Step 5: Worked Example (grams / mm)",
            "A complete numerical walkthrough of a single-plane balance using the vector method.",
            "Seeing the arithmetic done end to end with real numbers makes the method concrete and "
            "gives you a template to check your own calculations against.",
            "This example uses a fan running at constant speed, with vibration measured in mm/s at "
            "the bearing, phase in degrees (lag convention), and weights in grams at a 150 mm "
            "correction radius.",
            "STEP 1 - ORIGINAL RUN:\n"
            "  Vibration = 8.0 mm/s at 45 degrees\n"
            "  Rectangular: x = 8.0 x cos(45) = 5.657,  y = 8.0 x sin(45) = 5.657\n\n"
            "STEP 2 - TRIAL RUN (add 20 g at 0 degrees, radius 150 mm):\n"
            "  Vibration = 5.0 mm/s at 120 degrees\n"
            "  Rectangular: x = 5.0 x cos(120) = -2.500,  y = 5.0 x sin(120) = 4.330\n\n"
            "STEP 3 - EFFECT OF TRIAL WEIGHT (trial minus original):\n"
            "  x = -2.500 - 5.657 = -8.157\n"
            "  y = 4.330 - 5.657 = -1.327\n"
            "  Magnitude = sqrt(8.157^2 + 1.327^2) = sqrt(66.54 + 1.76) = 8.264 mm/s\n"
            "  Angle = atan2(-1.327, -8.157) = 189.2 degrees (third quadrant)\n\n"
            "  Influence coefficient = 8.264 / 20 g = 0.4132 mm/s per gram at 189.2 degrees\n\n"
            "STEP 4 - CORRECTION WEIGHT:\n"
            "  Magnitude = 8.0 / 0.4132 = 19.4 grams\n"
            "  Angle = (45 - 189.2) + 180 = 35.8 degrees\n\n"
            "  RESULT: install 19.4 g at 35.8 degrees, radius 150 mm.\n"
            "  Remember to REMOVE the 20 g trial weight first, unless you choose to leave it and "
            "combine both vectorially instead.",
            [
                "Work consistently in one phase convention (lag here) throughout.",
                "Convert to rectangular before subtracting - never subtract polar values directly.",
                "Watch quadrants: both components negative means the angle lies between 180 and 270 degrees.",
                "The correction radius must match the trial weight radius, or the mass must be scaled.",
                "Either remove the trial weight before installing the correction, or combine the two vectorially and install a single resultant weight.",
                "This app's Rotor Balance tool performs this entire calculation automatically.",
            ],
            "Work through this example by hand once with a calculator - having done it manually "
            "makes it far easier to spot when an automated result looks wrong."),
        sub("Step 6: The Trim Run",
            "After installing the correction, run again and verify the vibration has dropped to an "
            "acceptable level.",
            "One correction rarely achieves a perfect result, because measurement noise and small "
            "nonlinearities accumulate. The trim run confirms the improvement and provides the data "
            "for a second, finer correction if needed.",
            "The trim run is a verification measurement taken after the correction weight is "
            "installed, confirming the achieved vibration level and providing the starting point for "
            "any further refinement.",
            "Performed by removing the trial weight, installing the calculated correction, running "
            "back to the same speed and conditions, and measuring 1X amplitude and phase. If the "
            "result is within target, the job is done. If not, the same influence coefficient can be "
            "reused with the new reading to calculate a trim correction - no second trial run "
            "needed.",
            [
                "Always verify with a run rather than assuming the calculation worked.",
                "If vibration is acceptable against the target grade or standard, stop.",
                "If not, reuse the existing influence coefficient with the new reading - no new trial run required.",
                "Two or three corrections to reach a tight target is normal, not a sign of error.",
                "A result that gets worse indicates a calculation error, a wrong phase convention, or a misdiagnosis.",
            ],
            "If the first correction makes vibration worse rather than better, check your phase "
            "convention first - a lag/lead mix-up is the most common cause and puts the weight "
            "roughly 180 degrees out."),
    ]),

    dict(name="Two-Plane Balancing", category="Balancing", subtopics=[
        sub("When Two Planes Are Needed",
            "Two-plane balancing is required when the rotor has couple or dynamic unbalance, which "
            "single-plane correction cannot resolve.",
            "Attempting single-plane balancing on a rotor with significant couple unbalance leads to "
            "an endless cycle of partial improvements that never converge. Recognizing the need for "
            "two planes up front saves substantial time.",
            "Two-plane balancing corrects unbalance in two separate correction planes simultaneously, "
            "accounting for the fact that weight added in one plane affects vibration at both "
            "bearings.",
            "Indicated when the phase difference between the two bearings is substantially different "
            "from zero, when the rotor is long relative to its diameter, when it's overhung, or when "
            "single-plane attempts have failed to bring both ends within target.",
            [
                "Needed when phase between the two bearings is far from in-phase.",
                "Long rotors and overhung rotors typically require two planes.",
                "Narrow discs and thin fans are usually single-plane candidates.",
                "Couple and dynamic unbalance cannot be corrected in one plane, regardless of technique.",
                "Check the bearing-to-bearing phase relationship before deciding which approach to use.",
            ],
            "Take phase at both bearings before starting any balancing job - that single check "
            "determines whether you need one plane or two."),
        sub("Cross-Effect Explained",
            "Weight added in one correction plane affects vibration at both bearings, not just the "
            "nearer one - this interaction is called cross-effect.",
            "Cross-effect is why two-plane balancing needs four influence coefficients rather than "
            "two, and why the two planes can't simply be balanced independently one after the other. "
            "Ignoring it means each correction disturbs the other plane's result.",
            "Cross-effect is the influence that a weight in plane 1 has on the vibration measured at "
            "bearing 2, and vice versa. It arises because the rotor is a connected mechanical "
            "system - a force applied anywhere affects the whole rotor's motion.",
            "Handled by measuring four influence coefficients: the effect of plane 1 weight on "
            "bearing 1, plane 1 on bearing 2, plane 2 on bearing 1, and plane 2 on bearing 2. The "
            "resulting simultaneous equations are then solved for both correction weights together.",
            [
                "A weight in one plane changes vibration at both bearings.",
                "Requires four influence coefficients rather than two.",
                "The two planes must be solved together, not sequentially.",
                "Cross-effect is strongest on short, stiff rotors where the two planes are close together.",
                "This is why two trial runs are needed - one per plane.",
            ],
            "Don't try to balance one plane at a time and then the other - cross-effect means each "
            "correction will partly undo the previous one."),
        sub("The Original Run (Two-Plane)",
            "Measure and record amplitude and phase at both bearings simultaneously, before adding "
            "any weight.",
            "Two-plane calculations require a complete, consistent starting picture from both "
            "measurement points. An error or inconsistency in either reading propagates into both "
            "correction weights.",
            "The two-plane original run captures two vibration vectors: 1X amplitude and phase at "
            "bearing 1, and at bearing 2, both taken at the same operating speed and conditions.",
            "Performed with the machine at stable operating speed, recording both bearings' 1X "
            "amplitude and phase using the same phase reference and convention. Both readings should "
            "be confirmed stable on repeat before proceeding.",
            [
                "Record both bearings' amplitude and phase at the same speed and conditions.",
                "Use the same tachometer reference and phase convention for both.",
                "Label the readings clearly by bearing - mixing them up invalidates the whole calculation.",
                "Confirm both readings are stable before continuing.",
                "Note the measurement direction used at each bearing and keep it consistent throughout.",
            ],
            "Label every reading with its bearing number immediately as you take it - by the time "
            "you have six readings from three runs, unlabelled data is easy to confuse."),
        sub("Trial Run One",
            "Add a known trial weight in plane 1 only, then measure vibration at both bearings.",
            "This run isolates plane 1's influence, providing two of the four influence coefficients "
            "needed - specifically, how plane 1 weight affects each bearing.",
            "Trial run one introduces a known unbalance change in the first correction plane while "
            "leaving plane 2 untouched, so the resulting vibration change at both bearings can be "
            "attributed entirely to plane 1.",
            "Performed by installing a trial weight of known mass at a known angle and radius in "
            "plane 1, running to the same speed, and recording amplitude and phase at both bearings. "
            "The weight is then typically removed before trial run two, though some procedures leave "
            "it in place and account for it.",
            [
                "Trial weight goes in plane 1 only; plane 2 stays untouched.",
                "Measure and record both bearings after the change.",
                "Gives the plane 1 to bearing 1, and plane 1 to bearing 2 influence coefficients.",
                "Record the trial weight mass, angle and radius precisely.",
                "Usually removed before trial run two - be consistent and note what you did.",
            ],
            "Decide up front whether you'll remove trial weights between runs, and record that "
            "decision - the calculation differs depending on which approach you take."),
        sub("Trial Run Two",
            "Add a known trial weight in plane 2 only, then measure vibration at both bearings "
            "again.",
            "This run completes the picture, supplying the remaining two influence coefficients so "
            "the simultaneous equations can be solved.",
            "Trial run two mirrors trial run one, but applies the known weight change in the second "
            "correction plane, revealing how plane 2 weight affects each bearing.",
            "Performed by removing the plane 1 trial weight (if that's the chosen approach), "
            "installing a trial weight in plane 2 at a known mass, angle and radius, running to the "
            "same speed, and recording both bearings again.",
            [
                "Trial weight goes in plane 2 only this time.",
                "Remove the plane 1 trial weight first, if that's your chosen method.",
                "Gives the plane 2 to bearing 1, and plane 2 to bearing 2 influence coefficients.",
                "Use the same speed and conditions as all previous runs.",
                "After this run, all four influence coefficients are available.",
            ],
            "Keep the trial weight masses similar in magnitude between the two planes - wildly "
            "different trial weights can make the resulting calculation numerically unstable."),
        sub("The Balance Calculation",
            "Solve the four influence coefficients and two original readings simultaneously to get "
            "both correction weights.",
            "This is where two-plane balancing genuinely differs from doing single-plane twice - the "
            "simultaneous solution accounts for cross-effect so that both corrections work together "
            "rather than fighting each other.",
            "The calculation sets up two simultaneous vector equations: the combined effect of both "
            "correction weights at bearing 1 must cancel the original bearing 1 vibration, and the "
            "same must hold at bearing 2. With four known influence coefficients and two known "
            "original vectors, the two unknown correction weights can be solved.",
            "Performed by software in practice - the vector algebra involves solving simultaneous "
            "complex equations, which is tedious and error-prone by hand. The output is two "
            "correction weights, each with a mass and angular position, to be installed in their "
            "respective planes.",
            [
                "Two simultaneous vector equations, one per bearing.",
                "Four influence coefficients account for both direct effects and cross-effects.",
                "Solved for two unknowns: the plane 1 and plane 2 correction weights.",
                "Almost always done in software due to the complexity of the algebra.",
                "Both corrections must be installed together - installing only one won't give the predicted result.",
            ],
            "Install both correction weights before running again - the calculation assumes both "
            "are present, so testing with only one installed will give a misleading result."),
        sub("The Trim Run (Two-Plane)",
            "Install both correction weights, run again, and verify both bearings are within target.",
            "With two planes there are two results to satisfy, and it's common for one bearing to "
            "reach target before the other. The trim run shows where you actually stand on both.",
            "The two-plane trim run verifies the achieved result at both measurement points and "
            "provides the data for a further refinement pass if either bearing remains above target.",
            "Performed by removing all trial weights, installing both calculated corrections, "
            "running to the same speed, and measuring both bearings. If either is above target, the "
            "existing four influence coefficients can be reused with the new readings to calculate "
            "a trim correction - no additional trial runs needed.",
            [
                "Remove all trial weights and install both corrections before measuring.",
                "Check both bearings against the target, not just the worse one from before.",
                "Reuse the existing influence coefficients for trim calculations.",
                "It's common for one bearing to reach target before the other.",
                "Two or three passes to reach a tight tolerance is normal on two-plane jobs.",
            ],
            "Save all four influence coefficients at the end of the job - future re-balancing of "
            "that machine at the same speed can skip both trial runs entirely."),
        sub("Practical Tips for Two-Plane Work",
            "Several practical habits substantially improve two-plane balancing success rates.",
            "Two-plane jobs involve six or more readings and multiple weight installations, so small "
            "procedural errors compound quickly. Good discipline prevents most of the failures that "
            "occur in practice.",
            "These are field practices rather than theory: consistent labelling, consistent "
            "conditions, sensible trial weight sizing, and careful attention to the reference "
            "conventions used throughout the job.",
            "Applied throughout the job: label every reading by bearing and run; keep speed, load and "
            "temperature consistent across all runs; use the same phase convention and reference "
            "mark throughout; verify weights are securely attached; and check the machine's "
            "condition before starting, since balancing a machine with looseness or a bent shaft "
            "will not succeed.",
            [
                "Label every reading by bearing and run number as you take it.",
                "Keep speed, load and temperature consistent across every run.",
                "Use one phase convention and one reference mark for the whole job.",
                "Confirm trial and correction weights are securely attached before running.",
                "Rule out looseness, misalignment and bent shaft before starting - balancing won't fix them.",
                "Record the angular reference direction and confirm whether angles are measured with or against rotation.",
            ],
            "Write down the full setup - phase convention, angular reference direction, rotation "
            "direction, weight radius - before the first run. Reconstructing it later from memory "
            "is where most two-plane jobs go wrong."),
    ]),

    dict(name="Diagnosing Misalignment", category="Fault Diagnosis", subtopics=[
        sub("What Is Misalignment?",
            "Misalignment exists when the centrelines of two coupled shafts do not form a single "
            "continuous straight line during operation.",
            "Misalignment is second only to unbalance in frequency, and it's a leading cause of "
            "premature bearing, seal and coupling failure. Because it's often mistaken for "
            "unbalance, correctly identifying it prevents wasted balancing effort.",
            "Misalignment means the driver and driven shaft centrelines are offset, angled, or both, "
            "relative to each other. The coupling forces them to rotate together anyway, generating "
            "cyclic forces and loads on both machines' bearings.",
            "Detected by elevated axial vibration, a significant 2X component alongside 1X, and "
            "characteristic phase relationships across the coupling. Corrected by physically "
            "realigning the machines - which is what this app's Laser Align tool supports.",
            [
                "High axial vibration is the most distinctive indicator.",
                "2X is typically prominent, often comparable to or exceeding 1X.",
                "Phase across the coupling usually shows a substantial difference, often near 180 degrees.",
                "Flexible couplings tolerate misalignment but don't eliminate the resulting forces.",
                "Causes bearing, seal and coupling wear well before the coupling itself visibly fails.",
            ],
            "High axial vibration is the fastest screen for misalignment - if axial is low on a "
            "between-bearings machine, misalignment is unlikely to be the dominant fault."),
        sub("Angular Misalignment",
            "Angular misalignment means the two shaft centrelines meet at an angle rather than "
            "running parallel.",
            "Angular and parallel misalignment produce different phase signatures and require "
            "different correction moves, so distinguishing them speeds up the alignment job "
            "considerably.",
            "Angular misalignment (sometimes called face misalignment) exists when the shaft "
            "centrelines intersect at the coupling but at an angle, so the coupling faces are not "
            "parallel to each other.",
            "Identified by high axial vibration at 1X, with an axial phase difference across the "
            "coupling approaching 180 degrees. Corrected by adjusting shims and machine position to "
            "bring the shaft centrelines parallel.",
            [
                "Produces predominantly axial vibration at 1X.",
                "Axial phase across the coupling typically differs by roughly 180 degrees.",
                "The coupling faces are not parallel - there's a gap that varies around the circumference.",
                "Often caused by soft foot, foundation settling, or incorrect shimming.",
                "Frequently occurs together with parallel misalignment in real installations.",
            ],
            "Measure axial phase on both sides of the coupling - a near-180-degree difference "
            "points specifically at angular misalignment rather than parallel."),
        sub("Parallel (Offset) Misalignment",
            "Parallel misalignment means the shaft centrelines run parallel to each other but are "
            "laterally offset.",
            "Parallel misalignment produces a different signature from angular - more radial, with a "
            "stronger 2X - so recognizing which type dominates guides which alignment correction to "
            "prioritize.",
            "Parallel (or offset) misalignment exists when the two shaft centrelines are parallel "
            "but displaced sideways from each other, so they never intersect.",
            "Identified by high radial vibration with a strong 2X component, often exceeding 1X, and "
            "a radial phase difference across the coupling approaching 180 degrees. Corrected by "
            "moving the machine laterally and/or vertically to bring the centrelines into line.",
            [
                "Produces predominantly radial vibration, with 2X often dominant.",
                "Radial phase across the coupling typically differs by roughly 180 degrees.",
                "2X exceeding 1X is a strong parallel misalignment indicator.",
                "Corrected by lateral and vertical repositioning rather than angular adjustment.",
                "Commonly coexists with angular misalignment.",
            ],
            "A 2X peak larger than 1X is one of the more reliable single indicators of parallel "
            "misalignment - it's uncommon in most other fault types."),
        sub("Combined Misalignment",
            "Real installations almost always have both angular and parallel misalignment present "
            "together.",
            "Expecting a clean textbook signature of one type leads to confusion when the actual "
            "readings show a mixture. Knowing that combination is the norm sets realistic "
            "expectations for interpretation.",
            "Combined misalignment is the simultaneous presence of both angular and parallel "
            "misalignment, which is the normal real-world condition. The resulting vibration "
            "signature mixes characteristics of both.",
            "Identified by elevated vibration in both axial and radial directions, with significant "
            "1X and 2X content and phase differences that fall between the clean textbook values. "
            "Corrected by a full alignment procedure that addresses both components together, as "
            "laser alignment systems do.",
            [
                "The normal real-world case - pure angular or pure parallel is uncommon.",
                "Both axial and radial vibration are elevated.",
                "Phase differences often land between the clean 0 and 180 degree textbook values.",
                "A proper alignment procedure corrects both components simultaneously.",
                "Don't spend time trying to separate the two - correct the alignment fully instead.",
            ],
            "Don't get stuck trying to classify misalignment as purely angular or purely parallel - "
            "a full alignment procedure corrects both regardless of the mix."),
        sub("Causes of Misalignment",
            "Misalignment arises from installation practice, thermal effects, foundation issues, "
            "and piping forces.",
            "Knowing the cause determines whether a single alignment job will hold or whether the "
            "misalignment will return - a machine pulled out of alignment by pipe strain will drift "
            "again no matter how precisely it's aligned.",
            "Causes include: initial installation and shimming errors, soft foot, thermal growth "
            "between cold alignment and operating temperature, foundation settling or deterioration, "
            "pipe strain pulling the machine out of position, and worn or improperly installed "
            "couplings.",
            "Addressed by identifying which cause applies: checking for soft foot before aligning, "
            "applying thermal growth offsets during cold alignment, inspecting the foundation, and "
            "checking pipe strain by loosening flanges and watching for machine movement.",
            [
                "Soft foot must be corrected before alignment, or the alignment won't hold.",
                "Thermal growth means a correctly cold-aligned machine can be misaligned when hot.",
                "Pipe strain pulls machines out of position and recurs after every alignment.",
                "Foundation deterioration progressively changes alignment over time.",
                "Worn couplings can mask or mimic misalignment symptoms.",
            ],
            "If a machine goes out of alignment repeatedly, check pipe strain and soft foot before "
            "aligning again - otherwise you're treating the symptom each time."),
        sub("Spectrum Signature of Misalignment",
            "Misalignment produces a characteristic pattern of 1X, 2X and sometimes 3X, with "
            "elevated axial content.",
            "The spectrum is usually the first place misalignment is suspected, so knowing the "
            "specific pattern to look for speeds up recognition considerably.",
            "The classic misalignment spectrum shows 1X and 2X both prominent, with 2X often "
            "comparable to or larger than 1X, sometimes a noticeable 3X, and unusually high "
            "amplitudes in the axial direction compared to what unbalance alone would produce.",
            "Read by comparing the 2X-to-1X ratio and by comparing axial amplitude against radial. "
            "A 2X approaching or exceeding 1X, combined with axial vibration comparable to radial, "
            "is strongly suggestive. Phase measurements then confirm and refine the diagnosis.",
            [
                "1X and 2X both prominent, with 2X often at or above 1X amplitude.",
                "3X sometimes present, particularly with severe misalignment.",
                "Axial vibration unusually high compared to a pure unbalance case.",
                "Severe misalignment can generate additional harmonics beyond 3X.",
                "Always confirm a spectrum-based suspicion with phase readings before acting.",
            ],
            "Compare axial amplitude to radial at the same bearing - axial approaching or exceeding "
            "radial on a between-bearings machine is a strong misalignment flag."),
        sub("Phase Signature of Misalignment",
            "Phase readings across the coupling are the most reliable way to confirm misalignment "
            "and identify its type.",
            "Spectrum patterns for misalignment overlap with several other faults, but the phase "
            "signature across a coupling is distinctive and hard to confuse - it's what converts a "
            "suspicion into a confident diagnosis.",
            "Misalignment characteristically produces a large phase difference across the coupling: "
            "approximately 180 degrees in the axial direction for angular misalignment, and "
            "approximately 180 degrees in the radial direction for parallel misalignment.",
            "Measured by taking 1X phase on both sides of the coupling, in both axial and radial "
            "directions, and comparing. A large difference in axial phase points to angular "
            "misalignment; a large difference in radial phase points to parallel.",
            [
                "Take phase on both sides of the coupling, in both axial and radial directions.",
                "Roughly 180 degrees axial difference indicates angular misalignment.",
                "Roughly 180 degrees radial difference indicates parallel misalignment.",
                "Unbalance, by contrast, does not produce large phase differences across a coupling.",
                "Combined misalignment gives intermediate values in both directions.",
            ],
            "Phase across the coupling is the single most decisive misalignment measurement - if "
            "you take only one extra reading beyond the spectrum, make it this one."),
        sub("Misalignment vs. Unbalance",
            "The two most common faults are separated by axial vibration level, 2X content, and "
            "phase relationships.",
            "These two account for a large share of all machine vibration problems and their "
            "corrections are completely different - balancing versus alignment - so getting the "
            "distinction right has immediate practical consequence.",
            "The distinction rests on several simultaneous differences: unbalance is 1X-dominant "
            "with low axial and low 2X; misalignment shows high axial, prominent 2X, and large phase "
            "differences across the coupling.",
            "Applied as a quick comparison: check the 2X-to-1X ratio, compare axial to radial "
            "amplitude, and take phase across the coupling. Two or three of these pointing the same "
            "way gives a confident diagnosis.",
            [
                "Unbalance: 1X dominant, 2X small, axial low, phase consistent across the machine.",
                "Misalignment: 2X prominent, axial high, large phase difference across the coupling.",
                "Remember the overhung rotor exception - overhung unbalance also produces high axial.",
                "Both can be present simultaneously, in which case align first, then balance.",
                "Aligning a machine changes its vibration, so always align before balancing, never the reverse.",
            ],
            "When both faults appear present, always correct alignment first - alignment changes "
            "will alter the balance condition, making any prior balancing work obsolete."),
        sub("Soft Foot & Pipe Strain",
            "Soft foot and pipe strain distort a machine's frame, making good alignment impossible "
            "to achieve or hold.",
            "Attempting alignment without checking these first is a common cause of alignment jobs "
            "that either can't be brought into tolerance or drift back out shortly afterward.",
            "Soft foot is a condition where a machine's feet don't sit evenly on the base, so "
            "tightening the hold-down bolts distorts the frame. Pipe strain is external force from "
            "attached piping pulling the machine out of position.",
            "Soft foot is checked by loosening each foot bolt in turn with a dial indicator on the "
            "machine and watching for movement - more than a small amount indicates soft foot "
            "requiring shimming. Pipe strain is checked by loosening flange bolts and watching for "
            "machine movement.",
            [
                "Soft foot distorts the machine frame when bolts are tightened, changing internal alignment.",
                "Check each foot individually with a dial indicator before aligning.",
                "Pipe strain applies continuous external force, pulling alignment out over time.",
                "Both must be corrected before alignment, not after.",
                "This app's Laser Align tool includes a soft foot check for this reason.",
            ],
            "Always check soft foot before starting any alignment - it takes minutes and prevents "
            "an alignment that cannot be brought into tolerance."),
        sub("Thermal Growth",
            "Machines change dimensions as they heat to operating temperature, so a machine aligned "
            "cold may be misaligned hot.",
            "Aligning perfectly at ambient temperature and then finding high vibration at operating "
            "temperature is a classic, frustrating outcome. Thermal growth offsets are what prevent "
            "it.",
            "Thermal growth is the dimensional change a machine undergoes between ambient and "
            "operating temperature. Because driver and driven machines typically run at different "
            "temperatures and have different geometries, they grow by different amounts, changing "
            "their relative alignment.",
            "Handled by deliberately offsetting the cold alignment so the machines come into correct "
            "alignment once hot. Offset values come from manufacturer data, calculation from "
            "expected temperature rise and machine dimensions, or from measurement of hot and cold "
            "positions on the specific installation.",
            [
                "Driver and driven machines often grow by different amounts.",
                "Cold alignment is deliberately offset so the hot condition is correct.",
                "Offset values come from manufacturer data, calculation, or direct hot/cold measurement.",
                "Steam turbines, pumps handling hot fluids, and large motors show the largest effects.",
                "Vibration that's acceptable cold but rises as the machine warms up is a classic thermal growth signature.",
            ],
            "If vibration is fine at startup but climbs steadily as the machine reaches operating "
            "temperature, suspect thermal growth rather than a developing mechanical fault."),
    ]),

    dict(name="Diagnosing Looseness", category="Fault Diagnosis", subtopics=[
        sub("Structural (Type A) Looseness",
            "Structural looseness is loose or deteriorated machine mounting - foundation bolts, "
            "baseplate, or supporting structure.",
            "Looseness amplifies whatever vibration is already present, so it makes other faults "
            "look worse than they are. It also produces erratic readings that make any other "
            "diagnosis unreliable until it's fixed.",
            "Structural looseness covers loose hold-down bolts, cracked or deteriorated grout, "
            "corroded baseplates, and weakened foundations - anything that reduces the stiffness of "
            "the machine's connection to its support.",
            "Identified by directional 1X vibration (usually much higher vertically than "
            "horizontally, contrary to the normal pattern), a phase difference between the machine "
            "foot and the baseplate or foundation, and visible or audible evidence on inspection.",
            [
                "Vertical vibration exceeding horizontal is a common structural looseness signature.",
                "Phase differences between machine foot, baseplate and foundation reveal where the looseness is.",
                "Vibration amplitude may change when bolts are tightened - a direct confirmation test.",
                "Often accompanied by visible cracking in grout or rust staining around bolts.",
                "Amplifies other faults, so fix looseness before diagnosing anything else.",
            ],
            "Take phase readings at the machine foot and the foundation immediately below it - a "
            "significant difference between them localizes the looseness precisely."),
        sub("Rotating (Type B/C) Looseness",
            "Rotating looseness is excessive clearance between rotating and stationary components - "
            "worn bearings, loose fits, or a loose impeller.",
            "Rotating looseness produces a very distinctive spectrum (a long train of harmonics) "
            "that's hard to confuse with anything else, making it one of the more recognizable "
            "faults once you know the pattern.",
            "Rotating looseness covers excessive bearing clearance, a loose bearing in its housing, "
            "a loose impeller or coupling on a shaft, and worn fits generally. The loose component "
            "moves within its clearance each revolution, producing nonlinear, impacting behaviour.",
            "Identified by a long series of running-speed harmonics (often 1X through 10X or more), "
            "sometimes with half-order harmonics (0.5X, 1.5X, 2.5X), unstable phase readings, and a "
            "truncated or clipped time waveform.",
            [
                "Long harmonic series - many multiples of running speed - is the hallmark.",
                "Half-order harmonics (0.5X, 1.5X) often appear with more advanced looseness.",
                "Phase readings are unstable and don't repeat between measurements.",
                "The time waveform often shows clipping or truncation.",
                "Directional - amplitude varies substantially between radial directions.",
            ],
            "Unstable, non-repeating phase is one of the fastest indicators of looseness - if phase "
            "won't hold steady, suspect looseness before trying to balance anything."),
        sub("Looseness vs. Other Faults",
            "Looseness must be corrected before other diagnoses can be trusted, because it "
            "amplifies and distorts everything else.",
            "Diagnosing a machine with significant looseness is unreliable - the looseness "
            "exaggerates other faults' amplitudes and destabilizes phase readings, which are the two "
            "primary diagnostic inputs.",
            "Looseness acts as an amplifier and nonlinearity: it increases the response to whatever "
            "forces are present, generates additional harmonics, and makes phase readings erratic. "
            "This corrupts both amplitude-based severity judgments and phase-based fault "
            "identification.",
            "Managed by identifying and correcting looseness first, then re-measuring to get a clean "
            "picture of what else is present. Attempting balancing or alignment on a loose machine "
            "typically produces poor and non-repeatable results.",
            [
                "Looseness amplifies other faults, making them appear more severe than they are.",
                "It destabilizes phase readings, undermining phase-based diagnosis.",
                "Balancing a loose machine gives poor, non-repeating results.",
                "Fix looseness first, then re-measure before diagnosing anything else.",
                "The harmonic train from looseness can obscure other frequencies of interest in the spectrum.",
            ],
            "If you see a long harmonic train and unstable phase, stop diagnosing and go find the "
            "looseness - anything else you conclude from that data is unreliable."),
    ]),

    dict(name="Bent Shaft & Eccentricity", category="Fault Diagnosis", subtopics=[
        sub("Bent Shaft",
            "A bent shaft produces 1X vibration with unusually high axial content and a "
            "characteristic axial phase difference.",
            "A bent shaft looks very much like unbalance in a spectrum but cannot be corrected by "
            "balancing. Recognizing it prevents a fruitless balancing job on a shaft that needs "
            "straightening or replacement.",
            "A bent shaft is a shaft that isn't straight, so its centreline traces a curve rather "
            "than a line. Causes include thermal bowing, mechanical damage, improper storage, or "
            "excessive interference fits.",
            "Identified by high axial vibration at 1X (sometimes with 2X if the bend is near a "
            "coupling), and critically by an axial phase difference of roughly 180 degrees between "
            "the two ends of the same machine - which unbalance does not produce.",
            [
                "High axial 1X on a machine that is not overhung.",
                "Axial phase difference near 180 degrees across the same machine - the key distinguishing test.",
                "A bend near the coupling may also produce noticeable 2X.",
                "Thermal bow may appear only after the machine warms up, and disappear when cold.",
                "Cannot be corrected by balancing - the shaft must be straightened or replaced.",
            ],
            "Take axial phase at both ends of the same machine - a roughly 180-degree difference "
            "there distinguishes bent shaft from unbalance decisively."),
        sub("Eccentric Rotor & Sheave Eccentricity",
            "Eccentricity means the rotating component's geometric centre doesn't coincide with its "
            "rotational centre, producing highly directional 1X vibration.",
            "Eccentricity produces 1X like unbalance but cannot be fully corrected by balancing - "
            "adding weight can reduce vibration in one direction while leaving or worsening it in "
            "another, because the underlying geometry is wrong.",
            "An eccentric rotor is one where the component - a motor rotor, a pulley, a gear - is "
            "not concentric with its shaft. Sheave eccentricity specifically refers to belt pulleys "
            "that are out of round or mounted off-centre.",
            "Identified by 1X vibration that's strongly directional - much higher in one radial "
            "direction than the perpendicular one - and by a roughly 0 or 180 degree phase "
            "difference between horizontal and vertical readings at the same bearing. On belt "
            "drives, vibration peaks at the eccentric sheave's own rotational speed.",
            [
                "Strongly directional 1X - large difference between the two radial directions.",
                "Horizontal and vertical phase at the same bearing differ by roughly 0 or 180 degrees.",
                "On belt drives, the peak occurs at the eccentric sheave's rotational speed.",
                "Balancing can reduce vibration in one direction but won't fully correct it.",
                "The real fix is replacing or re-machining the eccentric component.",
            ],
            "Compare 1X amplitude in horizontal versus vertical at the same bearing - a large "
            "disparity points toward eccentricity rather than plain unbalance."),
    ]),

    dict(name="Bearing Fault Stages", category="Fault Diagnosis", subtopics=[
        sub("Stage 1: Earliest Detection",
            "The earliest detectable bearing damage appears only in ultrasonic and high-frequency "
            "techniques, with no change in normal vibration.",
            "Stage 1 offers the longest lead time for planning a bearing replacement - potentially "
            "months. Detecting it requires deliberately using the right technique, since standard "
            "spectra show nothing at all.",
            "Stage 1 is sub-surface fatigue and microscopic defects beginning to form. The energy "
            "released is very high frequency and very low amplitude - well above the range normal "
            "vibration analysis covers.",
            "Detected only by ultrasonic techniques, envelope/demodulation processing, or methods "
            "like Shock Pulse and PeakVue that are specifically designed for high-frequency, "
            "low-energy impacts. Standard velocity spectra and overall levels show no change "
            "whatsoever at this stage.",
            [
                "No change in overall vibration or standard velocity spectra.",
                "Detectable only by ultrasonic, envelope, Shock Pulse, or PeakVue techniques.",
                "Offers the longest possible warning - potentially several months of remaining life.",
                "Bearing defect frequencies are not yet visible in a normal spectrum.",
                "This is why high-frequency techniques are worth including in a monitoring program.",
            ],
            "If your program only measures velocity spectra, you're structurally unable to detect "
            "Stage 1 - adding an envelope or high-frequency measurement is what buys the extra "
            "lead time."),
        sub("Stage 2: Defect Frequencies Appear",
            "Bearing defect frequencies become visible in the spectrum, and natural frequencies of "
            "bearing components begin to be excited.",
            "Stage 2 is where conventional vibration analysis first sees the problem, and it's "
            "still early enough for comfortable planning. Recognizing it gives weeks to months of "
            "warning.",
            "Stage 2 is where microscopic damage has developed into a discrete defect large enough "
            "to produce measurable impacts. Bearing component natural frequencies start ringing, and "
            "the calculable defect frequencies begin appearing.",
            "Detected by the appearance of bearing defect frequencies (BPFO, BPFI, BSF, FTF) in the "
            "spectrum, ringing at bearing component natural frequencies typically in the 500 Hz to "
            "2 kHz region, and a continued rise in envelope and high-frequency measurements. Crest "
            "factor and kurtosis are typically rising.",
            [
                "Calculable defect frequencies (BPFO, BPFI, BSF, FTF) become visible in the spectrum.",
                "Bearing component natural frequencies get excited, often in the 500 Hz to 2 kHz range.",
                "Crest factor and kurtosis are typically climbing.",
                "Overall velocity may still look acceptable at this stage.",
                "This app's Bearing Freq tool calculates the defect frequencies to look for.",
            ],
            "Calculate the bearing's defect frequencies in advance and check those specific "
            "frequencies deliberately - they're easy to miss when scanning a spectrum generally."),
        sub("Stage 3: Clear Defect Frequencies & Sidebands",
            "Defect frequencies and their harmonics are clearly visible, with sidebands appearing - "
            "the damage is now significant.",
            "Stage 3 is the last comfortable point for planned replacement. Beyond it, remaining "
            "life becomes short and unpredictable, so recognizing Stage 3 should trigger scheduling "
            "rather than continued monitoring.",
            "Stage 3 is visible, developed damage - measurable spalling or wear on races or rolling "
            "elements. Defect frequencies show clear harmonics, and sidebands appear as the defect "
            "passes in and out of the load zone.",
            "Detected by clear defect frequencies with multiple harmonics, sidebands spaced at "
            "running speed or cage frequency around those peaks, rising overall vibration, and "
            "clearly elevated envelope readings. Wear may be visible on inspection and audible as "
            "changed bearing noise.",
            [
                "Defect frequencies with several harmonics clearly visible.",
                "Sidebands appear, spaced at running speed or cage frequency.",
                "Overall vibration levels now rising noticeably.",
                "Remaining life is typically weeks rather than months.",
                "This is the point to schedule replacement rather than continue monitoring.",
            ],
            "Treat clear sidebands around bearing defect frequencies as a scheduling trigger - "
            "past this point, remaining life becomes difficult to predict reliably."),
        sub("Stage 4: Imminent Failure",
            "Discrete defect frequencies give way to broadband noise and haystacks as damage becomes "
            "widespread - failure is imminent.",
            "Stage 4 is counterintuitive: the clear defect frequencies that were present in Stage 3 "
            "can disappear, which can look like improvement. Recognizing that this is deterioration, "
            "not recovery, is critical.",
            "Stage 4 is advanced, widespread damage - multiple defects, severe spalling, possible "
            "cage damage. Impacts become so frequent and irregular that they stop producing discrete "
            "frequencies and instead raise the broadband noise floor.",
            "Detected by discrete defect frequencies diminishing or disappearing, replaced by raised "
            "noise floor and haystacks; 1X often rises as the bearing's increased clearance allows "
            "shaft movement; overall vibration is high; and crest factor may fall even as damage "
            "worsens, because impacting is now continuous rather than distinct.",
            [
                "Discrete defect frequencies fade, replaced by broadband noise and haystacks.",
                "Crest factor may fall - continuous impacting rather than distinct spikes.",
                "1X often rises as bearing clearance increases.",
                "Audible noise and heat are usually obvious by this stage.",
                "Failure can occur at any time - remaining life is days or less.",
            ],
            "A falling crest factor combined with a rising noise floor is a serious warning, not "
            "an improvement - it typically means impacting has become continuous."),
    ]),

    dict(name="Demodulation & High-Frequency Techniques", category="Advanced Techniques", subtopics=[
        sub("Why Standard Spectra Miss Early Bearing Faults",
            "Early bearing defect signals are tiny and high-frequency, and standard velocity spectra "
            "are structurally poor at showing them.",
            "This explains why specialized techniques exist at all, and why a machine can show "
            "perfectly normal overall vibration while a bearing is already deteriorating.",
            "Early bearing impacts produce very small amounts of energy at high frequencies. In a "
            "velocity spectrum, this content is both attenuated by the choice of parameter and "
            "dwarfed by much larger low-frequency peaks like 1X, leaving it effectively invisible.",
            "Overcome by techniques that deliberately isolate the high-frequency impact content "
            "before analysis: filtering out the dominant low-frequency energy, then extracting the "
            "repetitive impact pattern. Envelope/demodulation, Shock Pulse, Spike Energy and PeakVue "
            "are all variations on this idea.",
            [
                "Early bearing impact energy is small and high-frequency.",
                "Velocity as a parameter de-emphasizes high frequencies.",
                "Large 1X peaks dominate the spectrum's dynamic range.",
                "The solution is to filter away the low-frequency content first, then analyze what remains.",
                "All the high-frequency techniques share this basic strategy, differing in implementation.",
            ],
            "Don't conclude a bearing is healthy from a normal velocity spectrum alone - that "
            "measurement is structurally incapable of showing early-stage damage."),
        sub("Envelope / Demodulation",
            "Envelope analysis extracts the repetition rate of high-frequency impacts, revealing "
            "bearing defect frequencies clearly.",
            "Envelope processing is the most widely available and generally applicable of the "
            "high-frequency techniques, and it directly produces the defect frequencies you can "
            "match against a bearing calculation - making the diagnosis specific rather than just "
            "'something is impacting'.",
            "Envelope analysis (also called demodulation or amplitude demodulation) band-pass "
            "filters the signal to a high-frequency region where bearing impacts ring, then extracts "
            "the envelope of that filtered signal - the slowly varying outline of its amplitude - "
            "and takes an FFT of that envelope.",
            "The resulting envelope spectrum shows the repetition rate of the impacts, which "
            "corresponds directly to bearing defect frequencies (BPFO, BPFI, BSF, FTF). Applied by "
            "selecting an appropriate band-pass region, which most instruments handle via preset "
            "envelope bands, then comparing the resulting peaks against calculated defect "
            "frequencies.",
            [
                "Band-pass filters to a high-frequency region, then analyzes the impact repetition rate.",
                "Produces peaks directly at bearing defect frequencies.",
                "Band selection matters - the filter must cover the region where the bearing actually rings.",
                "Most instruments offer preset envelope bands for common applications.",
                "Results are compared directly against calculated BPFO/BPFI/BSF/FTF values.",
            ],
            "Match envelope spectrum peaks against calculated defect frequencies from the Bearing "
            "Freq tool - that pairing is what identifies which specific bearing element is "
            "damaged."),
        sub("Shock Pulse Method (SPM)",
            "Shock Pulse Method uses a specially tuned transducer to measure the shock waves "
            "bearing impacts produce, reported as dB values.",
            "SPM provides a simple two-number condition assessment that doesn't require spectrum "
            "interpretation, making it accessible for routine screening by less specialized "
            "personnel.",
            "SPM uses a transducer resonant at approximately 32 kHz, tuned to respond to the shock "
            "waves generated by metal-to-metal impacts in a bearing. It reports two values: dBm "
            "(maximum, representing the strongest shocks) and dBc (carpet, representing the "
            "background level).",
            "Applied by taking readings at defined measurement points and comparing the dBm and dBc "
            "values against a normalized scale that accounts for bearing size and speed. The "
            "difference between dBm and dBc is itself informative about the nature of the damage.",
            [
                "Uses a transducer resonant around 32 kHz, tuned specifically for shock waves.",
                "Reports dBm (maximum) and dBc (carpet/background) values.",
                "Readings are normalized against bearing size and shaft speed.",
                "Provides a condition assessment without requiring spectrum analysis skills.",
                "Also sensitive to lubrication condition, which is often a useful secondary benefit.",
            ],
            "SPM readings are also strongly affected by lubrication - a sudden rise can indicate a "
            "lubrication problem rather than mechanical damage, which is worth checking first."),
        sub("Spike Energy",
            "Spike Energy is a proprietary high-frequency measurement that produces a single gSE "
            "value representing impact intensity.",
            "Spike Energy is common in installed monitoring systems and older instrument fleets, so "
            "understanding what a gSE number means is practically useful even though the technique "
            "is vendor-specific.",
            "Spike Energy measures high-frequency vibration content in a filtered band and processes "
            "it into a single value expressed in gSE units, representing the intensity of repetitive "
            "impacting.",
            "Applied as a trended single number alongside conventional vibration measurements. "
            "Because gSE values depend on the specific instrument, filter settings and measurement "
            "location, they're interpreted against that machine's own history rather than universal "
            "thresholds.",
            [
                "Produces a single gSE value rather than a spectrum.",
                "Sensitive to repetitive impacting from bearing and gear defects.",
                "Values are instrument- and setup-specific, so trend rather than compare absolutely.",
                "Common in installed monitoring systems and older portable instruments.",
                "A spectrum of spike energy is available on some instruments for more detail.",
            ],
            "Never compare gSE values between different instruments or measurement setups - trend "
            "them only against that same point's own history."),
        sub("PeakVue",
            "PeakVue captures the true peak values of high-frequency stress waves rather than "
            "averaging them, preserving impact amplitude information.",
            "PeakVue's distinguishing feature is that it doesn't average away the peaks, so the "
            "measured amplitude relates more directly to actual impact severity - which makes "
            "severity assessment more meaningful than techniques that report a processed index.",
            "PeakVue high-pass filters the acceleration signal to isolate stress waves, then samples "
            "and holds the true peak value within each sampling interval rather than averaging. An "
            "FFT of that peak-held waveform reveals the impact repetition rate.",
            "Applied by selecting an appropriate high-pass filter for the machine and fault type, "
            "then examining both the peak-held waveform (where individual impacts and their "
            "amplitudes are visible) and its spectrum (where defect frequencies appear). The "
            "waveform's peak g values relate to impact severity.",
            [
                "Uses peak-hold rather than averaging, preserving true impact amplitudes.",
                "High-pass filter selection should suit the machine speed and expected fault type.",
                "Both the peak-held waveform and its spectrum carry diagnostic information.",
                "Peak g values relate more directly to actual impact severity than processed indices do.",
                "Also effective for detecting gear faults and lubrication problems, not only bearings.",
            ],
            "Look at the PeakVue waveform as well as its spectrum - the waveform shows individual "
            "impact amplitudes and spacing that the spectrum alone doesn't convey."),
        sub("Comparing the Methods",
            "The high-frequency techniques share a common goal but differ in implementation, "
            "availability, and what their output means.",
            "Knowing the differences prevents comparing incompatible numbers, and helps you choose "
            "or interpret whichever technique your instruments actually support.",
            "All these methods isolate high-frequency impact content that standard spectra miss, "
            "but they differ in filtering approach, processing, output format, and whether they're "
            "open standards or vendor-proprietary.",
            "Selected mostly by what your instruments support. Envelope analysis is the most widely "
            "available and gives directly interpretable defect frequencies. SPM offers a simple "
            "screening number. Spike Energy is common in legacy and installed systems. PeakVue "
            "preserves true peak amplitudes. Whichever is used, consistency matters more than which "
            "one you pick.",
            [
                "All isolate high-frequency impacts that standard velocity spectra cannot show.",
                "Envelope analysis is the most widely available and directly gives defect frequencies.",
                "SPM and Spike Energy produce condition indices rather than defect frequencies.",
                "PeakVue preserves true peak amplitudes, aiding severity assessment.",
                "Values from different methods are not interchangeable - never compare across techniques.",
                "Consistency of method and setup over time matters more than which technique is chosen.",
            ],
            "Pick one high-frequency technique and use it consistently across your program - "
            "switching methods mid-trend makes the historical data unusable for comparison."),
    ]),
]


class SubtopicListScreen(Screen):
    """Lists the sub-topics for one top-level topic. Populated dynamically
    each time a topic is opened (see RootWidget.open_topic)."""

    def __init__(self, on_back, **kw):
        super().__init__(**kw)
        self._on_back = on_back
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

        root = BoxLayout(orientation="vertical")

        bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52),
                         padding=[dp(8), dp(4), dp(8), dp(4)], spacing=dp(8))
        with bar.canvas.before:
            Color(*PANEL)
            self._bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda w, v: setattr(self._bar_bg, "pos", v),
                 size=lambda w, v: setattr(self._bar_bg, "size", v))
        back_btn = PillButton(text="< Back", accent=ACCENT)
        back_btn.size_hint_x = None
        back_btn.width = dp(90)
        back_btn.bind(on_release=lambda *a: self._on_back())
        bar.add_widget(back_btn)
        self.title_lbl = Label(text="", bold=True, font_size=sp(16), color=TEXT)
        bar.add_widget(self.title_lbl)
        root.add_widget(bar)

        self.scroll = ScrollView()
        self.col = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14), size_hint_y=None)
        self.col.bind(minimum_height=self.col.setter("height"))
        self.scroll.add_widget(self.col)
        root.add_widget(self.scroll)

        self.add_widget(root)

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def populate(self, topic, open_subtopic_cb):
        self.title_lbl.text = topic["name"]
        self.col.clear_widgets()
        for s in topic["subtopics"]:
            card = NavCard(s["name"], topic["category"], ACCENT,
                            card_bg=PANEL, title_color=TEXT, subtitle_color=MUTED, height=dp(72))
            card.bind(on_release=lambda inst, sub_=s: open_subtopic_cb(sub_))
            self.col.add_widget(card)


class TopicListScreen(Screen):
    """Top-level list of the main topics."""

    def __init__(self, on_pick, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14), size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(Label(text="[b]Vibration Basics[/b]", markup=True, color=TEXT,
                              size_hint_y=None, height=dp(30), font_size=dp(18),
                              halign="left", valign="middle"))
        intro = body_label(
            "The foundational concepts the rest of the app builds on. Tap a topic to see its "
            "sub-topics.")
        intro.color = MUTED
        col.add_widget(intro)

        for topic in BASICS_TOPICS:
            subtitle = "%d sub-topics" % len(topic["subtopics"])
            card = NavCard(topic["name"], subtitle, ACCENT,
                            card_bg=PANEL, title_color=TEXT, subtitle_color=MUTED, height=dp(78))
            card.bind(on_release=lambda inst, t=topic: on_pick(t))
            col.add_widget(card)

        footer = Label(text="Built by Gnaneswar", color=MUTED, font_size=dp(12),
                       size_hint_y=None, height=dp(30))
        col.add_widget(footer)

        root.add_widget(col)
        self.add_widget(root)

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


class RootWidget(BoxLayout):
    """Root widget for the Basics tab. Owns the internal ScreenManager and
    navigation state, and exposes handle_back() for main.py's hardware/
    gesture back button (same contract as CM/DX's RootWidget)."""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.sm = ScreenManager(transition=SlideTransition(duration=0.15))
        self.topics_screen = TopicListScreen(name="basics_topics", on_pick=self.open_topic)
        self.sub_screen = SubtopicListScreen(name="basics_subtopics", on_back=self.go_back_to_topics)
        self.sm.add_widget(self.topics_screen)
        self.sm.add_widget(self.sub_screen)
        self.add_widget(self.sm)

    def open_topic(self, topic):
        self.sm.transition.direction = "left"
        self.sub_screen.populate(topic, self.open_subtopic_popup)
        self.sm.current = "basics_subtopics"

    def go_back_to_topics(self):
        self.sm.transition.direction = "right"
        self.sm.current = "basics_topics"

    def open_subtopic_popup(self, subtopic):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        sc = ScrollView()
        inner = GridLayout(cols=1, size_hint_y=None, spacing=dp(10))
        inner.bind(minimum_height=inner.setter("height"))
        inner.add_widget(body_label("Overview:\n" + subtopic["overview"]))
        inner.add_widget(body_label("Why it matters:\n" + subtopic["why"]))
        inner.add_widget(body_label("What it is:\n" + subtopic["what"]))
        inner.add_widget(body_label("How it works / is used:\n" + subtopic["how"]))
        inner.add_widget(body_label(
            "Key points:\n- " + "\n- ".join(subtopic["key_points"])))
        inner.add_widget(body_label("Practical tip:\n" + subtopic["tip"], ACCENT))
        sc.add_widget(inner)
        content.add_widget(sc)
        close = RoundedButton(text="Close", accent=PANEL)
        content.add_widget(close)
        popup = Popup(title=subtopic["name"], content=content, size_hint=(0.92, 0.85))
        close.bind(on_release=popup.dismiss)
        popup.open()

    def handle_back(self):
        """Called by main.py on hardware/gesture back. Returns True if this
        tool handled the navigation internally (so main.py should NOT fall
        back to Home), False if there's nothing left to unwind."""
        if self.sm.current == "basics_subtopics":
            self.go_back_to_topics()
            return True
        return False


class BasicsApp(App):
    """Standalone-runnable wrapper, same pattern as the other tool modules
    (`python basics_tab.py`), or merged as a screen by main.py."""

    def build(self):
        try:
            Window.clearcolor = BG
        except Exception:
            pass
        return RootWidget()


if __name__ == "__main__":
    BasicsApp().run()
