# -*- coding: utf-8 -*-
"""
Vibration Basics - a browsable learning-reference tool for CM Toolkit.

Foundational vibration-analysis concepts that the app's other tools assume
familiarity with. Written from general industry vibration-analysis practice,
in the author's own words and own organization - no text is lifted from any
single source or course.

Navigation is two levels deep:
  Topic list  ->  Sub-topic list (per topic)  ->  detail popup (per sub-topic)
Each sub-topic has its own Overview / Key Points / Practical Tip, same
structure as the other tools' reference tabs. Hardware/gesture back unwinds
one level at a time via handle_back(), same contract as the other tool
modules (see main.py).
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


def sub(name, overview, key_points, tip):
    return dict(name=name, overview=overview, key_points=key_points, tip=tip)


# ------------------------------------------------------------------
# LEARNING CONTENT - Batch 1 (topics 1-8), each sub-topic structured as
# Overview / Key Points / Practical Tip.
# ------------------------------------------------------------------
BASICS_TOPICS = [
    dict(name="Introducing Vibration", category="Fundamentals", subtopics=[
        sub("What Is Vibration?",
            "Vibration is oscillating, cyclic motion around a reference point, described by "
            "amplitude (how much movement) and frequency (how often it repeats). Every mechanical "
            "fault in rotating machinery applies a repeating force at some characteristic rate, "
            "which is why it leaves a recognizable vibration signature rather than a random, "
            "meaningless shake.",
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
    ]),

    dict(name="Displacement, Velocity & Acceleration", category="Fundamentals", subtopics=[
        sub("Displacement",
            "Displacement is how far something moves - the actual distance the shaft or casing "
            "travels from its reference position.",
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
            [
                "A healthy, balanced vibration signal is typically close to symmetric (skewness near zero).",
                "A consistent lean in one direction can point to a directional mechanical asymmetry - a consistent rub, or a preload pushing the shaft toward one side.",
                "Used less often than crest factor or kurtosis in routine monitoring.",
                "Most useful as a secondary check when a waveform looks visibly asymmetric and the more common indicators aren't telling the whole story.",
            ],
            "If a waveform looks lopsided when you view it, skewness is the statistic that "
            "quantifies that impression - useful for confirming what your eye already noticed."),
        sub("Form Factor",
            "Form factor is the RMS value of a signal divided by its average (mean) absolute value, "
            "describing waveform 'shape' independent of overall size.",
            [
                "A pure sine wave has a form factor of about 1.11 - another useful reference baseline.",
                "Like the other shape indicators, it works best as a trend over time rather than read as a single absolute number.",
                "Less commonly used than crest factor or kurtosis in day-to-day CM work, but appears in some vendor software and standards.",
                "None of these four indicators - crest factor, kurtosis, skewness, form factor - should be used alone to confirm a fault.",
            ],
            "Use a rising trend in any of these shape indicators as a trigger to go look at the "
            "time waveform and spectrum in more detail, not as a standalone diagnosis."),
    ]),

    dict(name="An Introduction to Phase", category="Fundamentals", subtopics=[
        sub("Out-of-Phase",
            "'Out of phase' describes two measurement points - or two directions at the same point "
            "- moving in opposition rather than together, even though they're vibrating at the same "
            "frequency.",
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
            [
                "Built from two real-time signals, rather than viewed as two separate one-dimensional waveforms.",
                "Naturally encodes amplitude, frequency, and phase all in one picture.",
                "Considered one of the richest single diagnostic plots available for shaft-relative measurements.",
                "Requires two probes mounted perpendicular to each other in the same radial plane.",
                "The Turbomachinery Insights tab covers orbit construction, Keyphasor marks, and orbit shape reading in much more depth.",
            ],
            "If you only ever see one probe's waveform, you're seeing a 1-D slice of what's "
            "actually 2-D motion - an orbit is what fills in the missing dimension."),
    ]),

    dict(name="Amplitude Modulation", category="Signal Behavior", subtopics=[
        sub("Amplitude Modulation",
            "Amplitude modulation (AM) happens when a carrier frequency's strength rises and falls "
            "at a second, slower rate.",
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
            [
                "Energy spread broadly across a frequency range rather than concentrated into sharp peaks.",
                "Often points to friction-type problems - rubbing, cavitation, electrical noise - rather than a fault tied to one specific rotating component.",
                "Easy to overlook if you're only scanning for peaks.",
                "A rising noise floor over time, even without new discrete peaks, is a legitimate trend to flag.",
            ],
            "Compare the noise floor level against a known-good baseline spectrum from the same "
            "point - a subtle floor rise is easy to miss without that direct comparison."),
        sub("Feature Five: Sum and Difference",
            "Sum-and-difference peaks appear where two frequencies interact nonlinearly, showing "
            "up at neither original frequency but at their sum and their difference.",
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
    ]),

    dict(name="Signal Processing", category="Fundamentals", subtopics=[
        sub("A Quick Overview",
            "The spectrum plot you read is the result of digitally sampling a continuous vibration "
            "signal and running it through a Fast Fourier Transform (FFT).",
            [
                "Understanding the basics explains why settings like Fmax and sample rate matter.",
                "The core pieces: filtering (isolating frequency ranges of interest), sampling (converting continuous signal to digital data points), and the FFT itself (converting sampled data into a frequency spectrum).",
                "Every spectrum you look at has already passed through this whole pipeline - none of it is a raw, direct measurement of frequency.",
                "Getting any one of these three steps wrong - a bad filter, wrong sample rate, poor FFT settings - can produce a misleading spectrum even from perfectly good raw vibration.",
            ],
            "When a spectrum looks wrong or unexpected, don't only question the machine - check "
            "the instrument's sampling and processing settings too."),
        sub("Filters",
            "A filter selectively passes or blocks certain frequency ranges.",
            [
                "Show up in two places: inside the sensor/instrument chain (removing electrical noise or out-of-range frequencies before recording), and after the fact in software (isolating a specific order like 1X).",
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
            [
                "A classic cause of a confusing or seemingly impossible peak in a spectrum.",
                "Anti-aliasing filters (removing frequency content above the Nyquist limit before sampling) are what prevent this in practice.",
                "An aliased peak can appear at a frequency with no physical explanation on the machine - often the first clue something is wrong with the measurement rather than the machine.",
                "Modern digital instruments with proper anti-aliasing filters largely prevent this, but it remains a risk with misconfigured settings or older analog equipment.",
            ],
            "If a spectrum shows a peak that doesn't correspond to anything physically in the "
            "machine and doesn't make sense, consider whether it could be an alias of a real "
            "higher frequency that exceeded the instrument's sampling limit."),
    ]),

    dict(name="Time Waveform Analysis", category="Signal Behavior", subtopics=[
        sub("A Simple Time Waveform",
            "Close to a single clean sine wave, usually corresponding to one dominant frequency, "
            "like pure unbalance.",
            [
                "The easiest waveform shape to read - smooth, regular, and repeating at a consistent rate.",
                "The baseline shape everything more complex gets compared against.",
                "A simple waveform's period - the time for one full cycle - directly corresponds to the frequency you'd see as a single peak in the spectrum.",
            ],
            "If a waveform looks like a clean sine wave, you likely already know what the "
            "spectrum will show before you even look at it - a single dominant peak."),
        sub("A More Complex Waveform",
            "Combines multiple frequencies, or shows sharp irregular features.",
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
            [
                "Produced by the combined effect of every rotating element and every fault currently present on the machine, all overlapping in one continuous trace.",
                "The whole point of both time-waveform and spectrum analysis is separating that one combined signal back out into its individual, physically meaningful contributors.",
                "No single measurement - waveform or spectrum - is 'more true' than the other; they're two mathematically equivalent representations of the same signal.",
            ],
            "Remember that a 'confusing' waveform isn't a broken measurement - it's simply the "
            "real, combined sum of everything happening on the machine at once."),
        sub("Waveform Patterns",
            "A handful of recurring waveform patterns are worth learning to recognize by eye.",
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
            [
                "The waveform's peaks grow and shrink in a steady cycle, distinct from the faster oscillation happening underneath it.",
                "This envelope shape is often the first place beating is actually noticed, before anyone thinks to check the spectrum.",
                "Confirming it as true beating, rather than AM, still requires checking the spectrum for two close peaks.",
            ],
            "If you spot a slow pulsing envelope in a waveform, note it and go confirm in the "
            "spectrum whether it's beating (two close peaks) or AM (one peak with sidebands)."),
        sub("Amplitude Modulation (in the Waveform)",
            "Shows up in the waveform very similarly to beating - a rising and falling envelope.",
            [
                "The underlying cause is a single mechanism being modulated rather than two independent sources interfering.",
                "The two can look alike in the waveform.",
                "Confirming which one you're seeing usually still requires checking the spectrum for sidebands (modulation) versus two separate close peaks (beating).",
            ],
            "Don't try to distinguish AM from beating by eye in the waveform alone - the "
            "spectrum check is what actually settles it."),
        sub("Amplitude Modulation and Gears",
            "Gear problems are one of the most common real-world sources of amplitude modulation.",
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
            [
                "Frequently shows up clearly in the waveform before it's obvious in the overall vibration level or even the spectrum.",
                "When a spectrum looks ambiguous, or a crest factor/kurtosis reading has crept up, checking the time waveform for repeating spikes is usually the fastest way to get direct confirmation.",
                "The spacing between repeating spikes often corresponds to a specific bearing defect frequency or gear mesh event, worth timing against known component frequencies.",
            ],
            "Time the spacing between repeating spikes in a waveform and compare it to known "
            "bearing/gear frequencies - that spacing is often the fastest route from 'something's "
            "impacting' to 'here's exactly what's impacting.'"),
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
