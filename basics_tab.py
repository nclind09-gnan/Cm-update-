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
