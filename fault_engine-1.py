# -*- coding: utf-8 -*-
"""
fault_engine.py - vibration fault signature synthesis for CM Toolkit.

Pure Python, no numpy: adding numpy complicates the python-for-android build,
and everything here is O(N log N) or better, so it runs fine without it.
No Kivy imports either, so the whole engine can be exercised from a plain
interpreter (see self_test() at the bottom, which the CI workflow runs).

HOW THE SIGNAL IS BUILT
-----------------------
Everything is synthesised internally as DISPLACEMENT in micrometres, because
that is the quantity a nonlinearity (looseness, rub) physically truncates.
Velocity and acceleration are obtained by differentiating:

    v = dx/dt    ->  multiply a bin at frequency f by  (2*pi*f)
    a = d2x/dt2  ->  multiply a bin at frequency f by  (2*pi*f)^2

so the three measurement units are not three separate drawings; they are one
signal viewed three ways, and the 1/f weighting that makes a bearing defect
invisible in velocity and obvious in acceleration falls out of the arithmetic
instead of being faked.

Two synthesis paths, each correct in its own regime:
  * a fault that TRUNCATES the motion is built in displacement and clipped
    there, then differentiated - so its harmonics are generated, not drawn in;
  * every other fault is built directly in the display unit at each
    component's TRUE frequency, which matters above Nyquist: a real
    accelerometer sees the component before the sampler does, so an aliased
    line lands at a false frequency but keeps its true amplitude.
"""

import math

TAU = 2.0 * math.pi
G = 9.80665

# ----------------------------------------------------------------------
# FFT - iterative radix 2, with cached twiddles so repeated calls are cheap
# ----------------------------------------------------------------------
_TWIDDLE = {}


def _twiddles(n):
    t = _TWIDDLE.get(n)
    if t is None:
        cos_t, sin_t = [], []
        length = 2
        while length <= n:
            ang = -TAU / length
            half = length >> 1
            c = [math.cos(ang * k) for k in range(half)]
            s = [math.sin(ang * k) for k in range(half)]
            cos_t.append(c)
            sin_t.append(s)
            length <<= 1
        t = (cos_t, sin_t)
        _TWIDDLE[n] = t
    return t


def fft(re, im):
    """In-place complex FFT. re/im are mutable sequences of equal power-of-2
    length."""
    n = len(re)
    if n <= 1:
        return
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    cos_t, sin_t = _twiddles(n)
    length = 2
    stage = 0
    while length <= n:
        half = length >> 1
        ct = cos_t[stage]
        st = sin_t[stage]
        for i in range(0, n, length):
            for k in range(half):
                wr = ct[k]
                wi = st[k]
                a = i + k
                b = a + half
                xr = re[b]
                xi = im[b]
                vr = xr * wr - xi * wi
                vi = xr * wi + xi * wr
                ur = re[a]
                ui = im[a]
                re[a] = ur + vr
                im[a] = ui + vi
                re[b] = ur - vr
                im[b] = ui - vi
        length <<= 1
        stage += 1


def ifft(re, im):
    """In-place inverse FFT, via conjugation."""
    n = len(re)
    for i in range(n):
        im[i] = -im[i]
    fft(re, im)
    inv = 1.0 / n
    for i in range(n):
        re[i] *= inv
        im[i] = -im[i] * inv


# ----------------------------------------------------------------------
# deterministic pseudo-random, so a trace does not reshuffle when an
# unrelated control moves
# ----------------------------------------------------------------------
class Rand(object):
    __slots__ = ("s",)

    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def next(self):
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.s
        t = (t ^ (t >> 15)) * (1 | t) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    def gauss(self):
        u = 0.0
        while u <= 0.0:
            u = self.next()
        v = self.next()
        return math.sqrt(-2.0 * math.log(u)) * math.cos(TAU * v)


def _hash_seed(text):
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


# ----------------------------------------------------------------------
# unit conversion, all peak referenced
# ----------------------------------------------------------------------
def vel_to_disp(v, f):
    """velocity mm/s peak -> displacement um peak"""
    return v * 1000.0 / (TAU * f) if f > 0 else 0.0


def acc_to_disp(a, f):
    """acceleration g peak -> displacement um peak"""
    return a * G * 1e6 / ((TAU * f) ** 2) if f > 0 else 0.0


def unit_gain(unit, f):
    """multiplier taking a displacement-um bin at f into the display unit"""
    if unit == "dis":
        return 1.0                      # um, instantaneous
    if unit == "vel":
        return TAU * f / 1000.0         # mm/s peak
    return (TAU * f) ** 2 / (1e6 * G)   # g peak


UNIT_LABEL = {"vel": "mm/s", "acc": "g", "dis": "um"}
UNIT_WAVE = {"vel": "mm/s pk", "acc": "g pk", "dis": "um"}
UNIT_SPEC = {"vel": "mm/s pk", "acc": "g pk", "dis": "um pk-pk"}


# ----------------------------------------------------------------------
# bearing geometry - defect orders from real dimensions
#   FTF  = 1/2 (1 - (Bd/Pd) cos a)
#   BPFO = N/2 (1 - (Bd/Pd) cos a)
#   BPFI = N/2 (1 + (Bd/Pd) cos a)
#   BSF  = Pd/(2 Bd) (1 - ((Bd/Pd) cos a)^2)
# ----------------------------------------------------------------------
BEARINGS = [
    {"id": "6205",  "name": "6205 ball (9 x 7.94, PD 39.0)",   "n": 9,  "bd": 7.94,  "pd": 39.04, "th": 0.0},
    {"id": "6308",  "name": "6308 ball (8 x 15.08, PD 65.0)",  "n": 8,  "bd": 15.08, "pd": 65.0,  "th": 0.0},
    {"id": "6316",  "name": "6316 ball (8 x 25.4, PD 122.5)",  "n": 8,  "bd": 25.4,  "pd": 122.5, "th": 0.0},
    {"id": "NU314", "name": "NU314 cyl roller (13 x 22)",      "n": 13, "bd": 22.0,  "pd": 107.5, "th": 0.0},
    {"id": "22220", "name": "22220 spher roller (17 x 20)",    "n": 17, "bd": 20.0,  "pd": 150.0, "th": 10.0},
]


def bearing_orders(b):
    r = (b["bd"] / b["pd"]) * math.cos(math.radians(b["th"]))
    return {
        "ftf": 0.5 * (1.0 - r),
        "bpfo": b["n"] / 2.0 * (1.0 - r),
        "bpfi": b["n"] / 2.0 * (1.0 + r),
        "bsf": (b["pd"] / (2.0 * b["bd"])) * (1.0 - r * r),
    }


# ISO 10816-3 evaluation zones, velocity RMS mm/s over 10-1000 Hz
ISO_GROUPS = [
    {"id": "g2r", "name": "Medium 15-300 kW, rigid",    "ab": 1.4, "bc": 2.8, "cd": 7.1},
    {"id": "g2f", "name": "Medium 15-300 kW, flexible", "ab": 2.3, "bc": 4.5, "cd": 7.1},
    {"id": "g1r", "name": "Large >300 kW, rigid",       "ab": 2.3, "bc": 4.5, "cd": 7.1},
    {"id": "g1f", "name": "Large >300 kW, flexible",    "ab": 3.5, "bc": 7.1, "cd": 11.0},
]


def iso_zone(rms, g):
    if rms <= g["ab"]:
        return "A", "newly commissioned"
    if rms <= g["bc"]:
        return "B", "acceptable long term"
    if rms <= g["cd"]:
        return "C", "unsatisfactory - plan action"
    return "D", "severe - damage likely"


# ----------------------------------------------------------------------
# Fault models
#
# Each build(c) returns:
#   comps    [(hz, v)]              discrete lines, v = velocity mm/s peak
#   impacts  [(rate, fr, accG, q)]  repetitive impacting that rings a resonance
#   rand     [(lo, hi, accG, velMM, flat)]  band limited random content
#   clip     fraction of peak displacement at which the motion truncates
#   marks    [(hz, label)]          what to annotate on the spectrum
#   env_band centre frequency for envelope demodulation
# Amplitudes are quoted at severity 10 and scale with the severity setting;
# the healthy baseline underneath does not scale.
# ----------------------------------------------------------------------
def _band(lo, hi, accG=0.0, velMM=0.0, flat=False):
    return (lo, hi, accG, velMM, flat)


def baseline(c):
    return {
        "comps": [(c["f1"], 0.55), (2 * c["f1"], 0.16),
                  (3 * c["f1"], 0.07), (4 * c["f1"], 0.04)],
        # a real floor is roughly flat in velocity across the low band and
        # roughly flat in acceleration above it, matched around 1 kHz
        "rand": [_band(6.0, 1000.0, velMM=0.011 * c["bg"], flat=True),
                 _band(1000.0, c["nyq"], accG=0.0030 * c["bg"], flat=True),
                 _band(c["fr"] * 0.75, c["fr"] * 1.25, accG=0.0016 * c["bg"])],
    }


def _orders_marks(f1, ns):
    return [(n * f1, "%dX" % n) for n in ns]


def _f_unbalance(c):
    s = c["s"]
    return {"comps": [(c["f1"], 10 * s), (2 * c["f1"], 0.5 * s)],
            "marks": _orders_marks(c["f1"], [1, 2])}


def _f_angmis(c):
    s = c["s"]
    return {"comps": [(c["f1"], 4 * s), (2 * c["f1"], 5.5 * s), (3 * c["f1"], 2 * s)],
            "marks": _orders_marks(c["f1"], [1, 2, 3])}


def _f_parmis(c):
    s = c["s"]
    return {"comps": [(c["f1"], 3 * s), (2 * c["f1"], 7 * s),
                      (3 * c["f1"], 2.5 * s), (4 * c["f1"], 1 * s)],
            "marks": _orders_marks(c["f1"], [1, 2, 3, 4])}


def _f_bent(c):
    s = c["s"]
    return {"comps": [(c["f1"], 7 * s), (2 * c["f1"], 2 * s)],
            "marks": _orders_marks(c["f1"], [1, 2])}


def _f_looseA(c):
    s = c["s"]
    return {"comps": [(c["f1"], 6 * s)],
            "clip": 0.80 - 0.22 * s,
            "marks": _orders_marks(c["f1"], [1, 2, 3, 4, 5, 6])}


def _f_looseB(c):
    s, f1 = c["s"], c["f1"]
    comps = [(f1, 5.5 * s)]
    # a long, strong harmonic train - the harmonics stay a large fraction of
    # 1X rather than dying away after two or three orders
    for n in range(2, 17):
        comps.append((n * f1, 3.6 * s * math.exp(-n / 11.0)))
    # half orders: the rotor repeats only every second revolution
    for k in range(1, 20, 2):
        comps.append(((k / 2.0) * f1, 1.7 * s * math.exp(-k / 16.0)))
    return {"comps": comps, "clip": 0.70 - 0.2 * s,
            "marks": [(0.5 * f1, "0.5X"), (f1, "1X"), (1.5 * f1, "1.5X"),
                      (2 * f1, "2X"), (3 * f1, "3X"), (5 * f1, "5X"),
                      (8 * f1, "8X"), (12 * f1, "12X")]}


def _f_rub(c):
    s, f1, fr = c["s"], c["f1"], c["fr"]
    comps = [(f1, 4 * s), (f1 / 2.0, 2.4 * s), (f1 / 3.0, 1.4 * s)]
    for n in range(2, 11):
        comps.append((n * f1, 2.6 * s / n))
    return {"comps": comps, "clip": 0.62 - 0.18 * s, "env_band": fr,
            "rand": [_band(f1 * 5, c["nyq"], accG=0.004 * s),
                     _band(fr * 0.7, fr * 1.3, accG=0.02 * s)],
            "impacts": [(f1, fr, 0.9 * s, 16.0)],
            "marks": [(f1 / 3.0, "1/3X"), (f1 / 2.0, "1/2X"), (f1, "1X"), (2 * f1, "2X")]}


def _f_whirl(c):
    s, f1 = c["s"], c["f1"]
    return {"comps": [(0.44 * f1, 6.5 * s), (f1, 1.6 * s), (0.88 * f1, 0.5 * s)],
            "marks": [(0.44 * f1, "0.44X"), (f1, "1X")]}


def _f_whip(c):
    s, f1 = c["s"], c["f1"]
    fc = c["fcrit"] if f1 > 2.1 * c["fcrit"] else 0.45 * f1
    return {"comps": [(fc, 9 * s), (f1, 1.8 * s)],
            "marks": [(fc, "whip"), (f1, "1X")]}


# ---- the four stage bearing model ----------------------------------
# The band carrying the evidence moves DOWN as the damage develops.
# Stage 1 is only in the stress wave region; stage 4 is back at running
# speed with the high frequency energy collapsing again.

def _f_brg1(c):
    s = c["s"]
    return {"env_band": 24000.0,
            "impacts": [(c["def_hz"], 24000.0, 0.40 * s, 45.0)],
            "rand": [_band(9000.0, 40000.0, accG=0.0016 * s)],
            "marks": [(c["def_hz"], c["def_name"])]}


def _f_brg2(c):
    s, fr = c["s"], c["fr"]
    return {"env_band": fr,
            "impacts": [(c["def_hz"], fr, 1.1 * s, 30.0)],
            "rand": [_band(fr * 0.7, fr * 1.3, accG=0.003 * s),
                     _band(9000.0, 40000.0, accG=0.009 * s)],
            "marks": [(fr, "brg nat freq"), (c["def_hz"], c["def_name"])]}


def _f_brg3(c):
    s, fr = c["s"], c["fr"]
    comps, marks = [], []
    for n in range(1, 9):
        hz = n * c["def_hz"]
        comps.append((hz, 2.0 * s / math.sqrt(n)))
        if n <= 3:
            marks.append((hz, c["def_name"] if n == 1 else "%dx%s" % (n, c["def_name"])))
        if c["mod_hz"] > 0:
            for k in (1, 2):
                comps.append((hz + k * c["mod_hz"], 0.7 * s / (n * k)))
                comps.append((max(0.0, hz - k * c["mod_hz"]), 0.7 * s / (n * k)))
    comps.append((c["f1"], 1.2 * s))
    return {"comps": comps, "env_band": fr,
            "impacts": [(c["def_hz"], fr, 2.6 * s, 18.0)],
            "rand": [_band(fr * 0.55, fr * 1.45, accG=0.008 * s),
                     _band(9000.0, 40000.0, accG=0.013 * s)],
            "marks": marks}


def _f_brg4(c):
    s, fr, f1 = c["s"], c["fr"], c["f1"]
    comps = [(n * f1, 4.5 * s * math.exp(-n / 7.0)) for n in range(1, 13)]
    for n in range(1, 5):
        comps.append((n * c["def_hz"], 0.45 * s / n))
    return {"comps": comps, "env_band": fr,
            "impacts": [(c["def_hz"], fr, 1.0 * s, 5.0)],
            "rand": [_band(f1 * 2, 8000.0, accG=0.022 * s),
                     _band(fr * 0.4, fr * 1.6, accG=0.03 * s),
                     _band(9000.0, 40000.0, accG=0.0035 * s)],
            "marks": [(f1, "1X"), (c["def_hz"], c["def_name"])]}


def _f_gear(c):
    s, f1, fr = c["s"], c["f1"], c["fr"]
    gmf = c["teeth"] * f1
    comps = [(f1, 1.0 * s)]
    marks = []
    for h in (1, 2, 3):
        hz = h * gmf
        comps.append((hz, (5 if h == 1 else 2.4 if h == 2 else 1.1) * s))
        marks.append((hz, ("%dx" % h if h > 1 else "") + "GMF"))
        for k in (1, 2, 3):
            comps.append((hz + k * f1, 1.1 * s / (h * k)))
            comps.append((hz - k * f1, 1.1 * s / (h * k)))
    return {"comps": comps, "env_band": gmf,
            "rand": [_band(fr * 0.8, fr * 1.2, accG=0.01 * s)], "marks": marks}


def _f_gearcrack(c):
    s, f1, fr = c["s"], c["f1"], c["fr"]
    gmf = c["teeth"] * f1
    comps = [(gmf, 3.2 * s), (2 * gmf, 1.4 * s), (f1, 1.6 * s)]
    for k in range(1, 9):
        comps.append((gmf + k * f1, 1.5 * s / math.sqrt(k)))
        comps.append((gmf - k * f1, 1.5 * s / math.sqrt(k)))
    return {"comps": comps, "env_band": fr,
            "impacts": [(f1, fr, 2.2 * s, 14.0)],
            "marks": [(gmf, "GMF"), (f1, "1X")]}


def _f_blade(c):
    s, f1 = c["s"], c["f1"]
    bpf = c["blades"] * f1
    comps = [(f1, 1.3 * s)]
    marks = []
    for h in (1, 2, 3):
        hz = h * bpf
        comps.append((hz, (6 if h == 1 else 2 if h == 2 else 0.9) * s))
        marks.append((hz, ("%dx" % h if h > 1 else "") + "BPF"))
    return {"comps": comps, "env_band": bpf, "marks": marks}


def _f_cav(c):
    s, f1, fr = c["s"], c["f1"], c["fr"]
    return {"comps": [(f1, 0.9 * s), (c["blades"] * f1, 1.6 * s)],
            "env_band": fr,
            "rand": [_band(1500.0, c["nyq"], accG=0.055 * s),
                     _band(fr * 0.7, fr * 1.3, accG=0.03 * s)],
            "marks": [(c["blades"] * f1, "BPF")]}


def _f_elec(c):
    s, f1, lf = c["s"], c["f1"], c["lf"]
    return {"comps": [(2 * lf, 5 * s), (4 * lf, 0.8 * s), (f1, 0.9 * s), (2 * f1, 0.5 * s)],
            "marks": [(2 * lf, "2xLF"), (2 * f1, "2X")]}


def _f_rotorbar(c):
    s, f1, ppf = c["s"], c["f1"], c["ppf"]
    comps = [(f1, 3.2 * s), (2 * f1, 0.9 * s)]
    for k in (1, 2, 3):
        comps.append((f1 + k * ppf, 0.75 * s / k))
        comps.append((f1 - k * ppf, 0.75 * s / k))
    return {"comps": comps,
            "marks": [(f1, "1X"), (f1 + ppf, "+PPF"), (f1 - ppf, "-PPF")]}


def _f_softfoot(c):
    s = c["s"]
    return {"comps": [(c["f1"], 6.5 * s), (2 * c["f1"], 2.6 * s), (3 * c["f1"], 0.8 * s)],
            "marks": _orders_marks(c["f1"], [1, 2, 3])}


def _f_belt(c):
    s, f1, b = c["s"], c["f1"], c["belt_hz"]
    comps = [(f1, 1.4 * s)]
    marks = []
    # the belt passes any one flaw once per belt revolution, and a loose or
    # worn belt slaps as it does so, giving a short harmonic train
    for n in (1, 2, 3, 4):
        amp = (2.4, 6.0, 2.0, 1.0)[n - 1] * s
        comps.append((n * b, amp))
        marks.append((n * b, ("%dx" % n if n > 1 else "") + "belt"))
    return {"comps": comps, "marks": marks}


def _f_sheave(c):
    s, f1 = c["s"], c["f1"]
    return {"comps": [(f1, 8.0 * s), (2 * f1, 1.2 * s), (c["belt_hz"], 1.0 * s)],
            "marks": [(f1, "1X"), (c["belt_hz"], "belt")]}


def _f_misalign_belt(c):
    s, f1 = c["s"], c["f1"]
    return {"comps": [(f1, 3.0 * s), (2 * f1, 1.4 * s), (c["belt_hz"], 2.2 * s)],
            "marks": [(f1, "1X"), (2 * f1, "2X"), (c["belt_hz"], "belt")]}


def _f_resonance(c):
    """Running on or near a natural frequency. Nothing new is generated - an
    ordinary force is simply amplified, which is why the spectrum looks
    innocent while the amplitude is alarming."""
    # the natural frequency must sit inside the speed range the user can
    # actually drive through, or the demonstration cannot happen
    s, f1, fn = c["s"], c["f1"], c["fcrit"]
    # the closer running speed sits to the natural frequency, the bigger the
    # amplification, exactly as a single degree of freedom system behaves
    q = 12.0
    ratio = f1 / fn if fn > 0 else 0.0
    denom = math.sqrt((1 - ratio ** 2) ** 2 + (ratio / q) ** 2)
    amp = (1.2 / denom) if denom > 1e-6 else 1.2
    amp = min(amp, 14.0)
    return {"comps": [(f1, amp * s), (2 * f1, 0.5 * s), (fn, 1.6 * s)],
            "rand": [_band(fn * 0.9, fn * 1.1, velMM=0.08 * s)],
            "marks": [(f1, "1X"), (fn, "natural freq")]}


def _f_crack(c):
    s, f1 = c["s"], c["f1"]
    return {"comps": [(f1, 5.5 * s), (2 * f1, 4.0 * s), (3 * f1, 0.9 * s)],
            "marks": _orders_marks(c["f1"], [1, 2, 3])}


def _f_cocked(c):
    s, f1 = c["s"], c["f1"]
    return {"comps": [(f1, 4.5 * s), (2 * f1, 3.2 * s), (3 * f1, 1.4 * s)],
            "marks": _orders_marks(c["f1"], [1, 2, 3])}


def _f_turbulence(c):
    s, f1 = c["s"], c["f1"]
    return {"comps": [(f1, 1.0 * s), (c["blades"] * f1, 1.2 * s)],
            "rand": [_band(1.0, max(2.0, 0.9 * f1), velMM=0.55 * s)],
            "marks": [(f1, "1X")]}


FAULTS = [
    {"id": "unbalance", "name": "Unbalance", "fam": "Rotor", "group": "Rotor & coupling",
     "fmax": 500, "wf_rev": 8, "build": _f_unbalance,
     "note": "A heavy spot throws a rotating centrifugal force once per revolution. The force rises with the square of speed, so the 1X line grows four times when speed doubles.",
     "look": ["1X dominant, with very little else in the spectrum.",
              "Radial far exceeds axial, except on an overhung rotor.",
              "No harmonics worth the name; a large 2X points elsewhere.",
              "Phase steady, and it moves with the heavy spot when you add a trial weight."],
     "wave": "A single clean sine wave, one cycle per revolution, repeating identically turn after turn. Crest factor sits near 1.4, the value for a pure sine. No impacts and no flat spots. If the trace wanders, or repeats only every second revolution, it is not plain unbalance.",
     "phys": "Switch to displacement and 1X grows; switch to acceleration and it shrinks. Unbalance is a low frequency fault, which is why velocity is the unit for balancing work."},

    {"id": "angmis", "name": "Angular misalignment", "fam": "Coupling", "group": "Rotor & coupling",
     "fmax": 500, "wf_rev": 8, "build": _f_angmis,
     "note": "Shaft centrelines meet at an angle, so the coupling is flexed and released twice per revolution. The bending moment acts along the shaft, which drives the axial reading up.",
     "look": ["1X and 2X both strong, 2X typically 40 to 70 percent of 1X.",
              "Axial vibration unusually high for a between bearings machine.",
              "Axial phase across the coupling differs by roughly 180 degrees.",
              "Check soft foot and pipe strain before you touch the shims."],
     "wave": "A distorted sine showing two peaks per revolution, often an M or W shape with one peak taller than the other. It repeats cleanly every revolution. The same pattern appears axially at an amplitude a radial only fault would never produce.",
     "phys": "Misalignment and unbalance both put energy at 1X. The 2X line and the axial phase step separate them; amplitude alone will not."},

    {"id": "parmis", "name": "Parallel misalignment", "fam": "Coupling", "group": "Rotor & coupling",
     "fmax": 500, "wf_rev": 8, "build": _f_parmis,
     "note": "Offset centrelines shear the coupling twice per revolution, which is why 2X commonly overtakes 1X.",
     "look": ["2X larger than 1X, one of the more reliable single indicators.",
              "Mostly radial, unlike angular misalignment.",
              "Radial phase across the coupling differs by roughly 180 degrees.",
              "3X and 4X grow as the offset grows."],
     "wave": "Two full cycles per revolution, clearly and repeatably, often with the peaks slightly flattened. Counting cycles against a tacho pulse is the quickest confirmation available, and it needs no phase measurement.",
     "phys": "Most real misalignment mixes both kinds, so expect a large 1X and a large 2X together rather than a textbook case of either."},

    {"id": "bent", "name": "Bent shaft", "fam": "Rotor", "group": "Rotor & coupling",
     "fmax": 500, "wf_rev": 8, "build": _f_bent,
     "note": "A bowed shaft throws a force once per revolution just as unbalance does, so the spectrum alone cannot separate them. Phase is the test.",
     "look": ["High axial 1X on a machine that is not overhung.",
              "Axial phase differs by about 180 degrees across the same machine.",
              "A bend near the coupling also lifts 2X.",
              "Balancing masks it; it does not fix it."],
     "wave": "Indistinguishable from unbalance, a clean sine at one cycle per revolution. That is the point: the waveform cannot tell you which it is. Only comparing axial phase at the two ends of the rotor will, which is why this is a phase job and not a spectrum job.",
     "phys": "Compare this with Unbalance at the same severity. The two spectra are nearly identical, and so are the waveforms."},

    {"id": "looseA", "name": "Structural looseness", "fam": "Looseness", "group": "Looseness & rub",
     "fmax": 500, "wf_rev": 8, "build": _f_looseA,
     "note": "Loose hold down bolts or failed grout let the machine lift off its base on one half of each revolution and land on the other. The motion is truncated, and a truncated sine is no longer a sine.",
     "look": ["1X with a harmonic train running to about 5X or 6X.",
              "Vertical often exceeds horizontal, the reverse of normal.",
              "Phase changes across foot, baseplate and foundation.",
              "It amplifies everything else, so fix it before diagnosing further."],
     "wave": "A sine flattened on ONE side only. The machine lifts freely and is stopped on the way back down, so one half of the trace is rounded and the other runs along a shelf. It still repeats once per revolution. A trace clipped evenly on both sides is a sensor or amplifier problem, not looseness.",
     "phys": "The harmonics are generated, not drawn in: the displacement waveform is clipped before the units are derived, exactly as the machine's motion is clipped by the base it sits on."},

    {"id": "looseB", "name": "Rotating looseness", "fam": "Looseness", "group": "Looseness & rub",
     "fmax": 500, "wf_rev": 4, "build": _f_looseB,
     "note": "Excessive clearance in a bearing housing or a loose fit on the shaft lets the rotor move freely within its own clearance every revolution, so it is knocked about inside the housing.",
     "look": ["A long harmonic train, commonly out to 10X and beyond, the harmonics a substantial fraction of 1X rather than small.",
              "Half order lines at 0.5X, 1.5X, 2.5X when the rotor repeats only every second revolution.",
              "The low frequency region fills with lines rather than showing two or three clean peaks.",
              "Strongly directional, worst along the axis the clearance allows."],
     "wave": "Erratic and NOT repeatable turn to turn. Successive revolutions differ in amplitude and shape, peaks are ragged, and small impacts appear where the rotor takes up clearance. Overlay two revolutions and they will not sit on top of one another. That non repeatability is the clearest symptom, and it separates this from structural looseness, which repeats faithfully.",
     "phys": "Half order content means the motion repeats every two revolutions, not every one. That is a clearance signature and close to unambiguous."},

    {"id": "rub", "name": "Rotor rub", "fam": "Contact", "group": "Looseness & rub",
     "fmax": 2000, "wf_rev": 2, "build": _f_rub,
     "note": "The rotor touches a stationary part. Each contact is brief and violent, so it both truncates the orbit and sprays energy across the spectrum.",
     "look": ["Sub harmonics at 1/2X and 1/3X, the rub repeating every two or three revolutions.",
              "A long harmonic series sitting on a raised noise floor.",
              "Often intermittent, coming and going with load or temperature.",
              "A full annular rub can drive the rotor backwards; that shows in an orbit, not a spectrum."],
     "wave": "Flattened on one side with a burst of high frequency ringing at the moment of contact. The flat and the burst do not occur every revolution; they repeat every second or third, so a slow pattern rides on top of the running speed cycle. The ringing is what separates a rub from plain looseness.",
     "phys": "The contact is a nonlinearity, so it creates frequencies that were not in the forcing. That is why sub harmonics can exist at all."},

    {"id": "whirl", "name": "Oil whirl", "fam": "Fluid-film", "group": "Fluid film",
     "fmax": 500, "wf_rev": 8, "build": _f_whirl,
     "note": "In a plain journal bearing the oil wedge circulates a little under half shaft speed and can drag the journal round with it. The line sits at 0.38 to 0.48X and tracks speed.",
     "look": ["A line at 0.42 to 0.48X, usually larger than 1X once established.",
              "It tracks shaft speed: raise the speed and it moves with it.",
              "Journal bearings only; it cannot happen in a rolling element bearing.",
              "Often cured by changing oil temperature, viscosity or bearing loading."],
     "wave": "Two sine waves of close but unequal frequency, running speed and roughly half of it, so the trace shows a slow beat swelling and shrinking over about two revolutions. The pattern repeats every second revolution rather than every one.",
     "phys": "Compare with Oil whip. Whirl follows speed; whip stops following and parks on the rotor's natural frequency. That difference is the whole diagnosis."},

    {"id": "whip", "name": "Oil whip", "fam": "Fluid-film", "group": "Fluid film",
     "fmax": 500, "wf_rev": 8, "build": _f_whip,
     "note": "Once the shaft runs past twice its first critical, the whirl frequency reaches that critical and locks onto it. From then on the line stays at the natural frequency however fast the machine is driven.",
     "look": ["A large line at the rotor's natural frequency, not at a fixed order.",
              "It stops tracking speed, the giveaway against whirl.",
              "Amplitudes can be violent and the condition is unstable.",
              "Needs a bearing design change, not an adjustment."],
     "wave": "A large, almost pure sine at the natural frequency with the smaller running speed cycle riding on it. Because the two are not harmonically related the pattern never repeats exactly; successive revolutions drift against one another.",
     "phys": "Drag the shaft speed slider and watch this line stay still while the 1X marker moves past it. That behaviour names the fault."},

    {"id": "brg1", "name": "Bearing - stage 1", "fam": "Rolling bearing", "group": "Rolling bearing",
     "fmax": 40000, "lines": 800, "wf_rev": 1, "build": _f_brg1,
     "note": "Subsurface fatigue has begun. There is no visible damage, no defect frequency and nothing in the velocity spectrum, only microscopic stress waves from material being worked below the surface, up in the ultrasonic region.",
     "look": ["Nothing in the velocity spectrum, and nothing at the defect frequencies.",
              "All the evidence is above about 10 kHz. Raise F-max to 40 kHz and a low broad rise appears; at 1 kHz the bearing looks perfect.",
              "No discrete peaks even up there: it is random stress wave energy, not a tone.",
              "Found by shock pulse, PeakVue, spike energy or high frequency envelope. Nothing else will see it."],
     "wave": "Nothing at all in a velocity or acceleration trace. A high frequency demodulated trace shows very low level random spikes with no pattern you could time. There is no repeating impact yet because there is no spall to strike.",
     "phys": "Roughly 80 to 90 percent of the bearing's life is still ahead of it. Set F-max to 1 kHz and this bearing reads as healthy; that is not the instrument failing, it is the wrong band. Switch to Envelope to pull the defect rate out of the stress wave band."},

    {"id": "brg2", "name": "Bearing - stage 2", "fam": "Rolling bearing", "group": "Rolling bearing",
     "fmax": 5000, "wf_rev": 1, "build": _f_brg2,
     "note": "A small spall has formed. Rolling elements now strike a real edge, and each strike rings the natural frequencies of the bearing components themselves, typically 1 to 5 kHz.",
     "look": ["Bearing natural frequencies appear in the 1 to 5 kHz region.",
              "Around them, a picket fence of sidebands spaced at the defect frequency. This identifies the stage.",
              "Still little or nothing at the defect frequency itself at the low end.",
              "The stress wave energy above 10 kHz keeps growing."],
     "wave": "Low level repetitive impacts, visible in acceleration and invisible in velocity. The spacing between them is the defect period, and crest factor begins to climb above the 3 or so of a healthy bearing. Switch to Velocity and they vanish: that contrast is the lesson of this stage.",
     "phys": "The sideband spacing around the natural frequency is the defect rate, so a clean low frequency spectrum does not mean a clean bearing. Roughly 10 to 20 percent of life remains."},

    {"id": "brg3", "name": "Bearing - stage 3", "fam": "Rolling bearing", "group": "Rolling bearing",
     "fmax": 5000, "wf_rev": 1, "build": _f_brg3,
     "note": "The damage is open and would be obvious if the bearing were pulled. Now the defect frequency itself finally appears down in the ordinary velocity spectrum, with harmonics.",
     "look": ["Defect frequency and its harmonics clear in the low frequency spectrum: BPFO, 2xBPFO and beyond.",
              "Sidebands spaced at the rate that modulates that particular defect.",
              "The 1 to 5 kHz natural frequency region still active, and broadening.",
              "Wear may now be visible on the shaft or in the grease."],
     "wave": "Clear repetitive impacts well above the background, spaced at the defect period and easy to time. Crest factor is at its highest here, typically 4 to 6. This is the easiest stage to read from the waveform alone.",
     "phys": "Sideband spacing names the defect: an inner race fault is modulated once per shaft revolution as it passes the load zone, a rolling element fault at cage speed, and an outer race fault under steady load barely at all. Replace at the next opportunity: weeks, not months."},

    {"id": "brg4", "name": "Bearing - stage 4", "fam": "Rolling bearing", "group": "Rolling bearing",
     "fmax": 5000, "wf_rev": 1, "build": _f_brg4,
     "note": "The damage has spread and the rolling elements no longer strike one clean edge. Discrete defect lines break down into random noise, clearance opens up, and the evidence moves back down to running speed.",
     "look": ["Defect frequencies fade while the noise floor rises. A falling defect peak here is bad news, not good.",
              "A forest of running speed harmonics in the low frequency region as clearance grows.",
              "The high frequency stress wave energy falls back, having peaked in stage 3. This is the most counter intuitive part of the whole pattern.",
              "Audible, hot, and close to failure."],
     "wave": "The clean impacts of stage 3 are gone. The trace is random and hashy with irregular spikes that no longer keep time, and crest factor FALLS BACK as the signal turns into noise. A falling crest factor late in a bearing's life means the damage has spread, not healed.",
     "phys": "This is the trap in bearing trending. An analyst watching only the defect peak, or only a high frequency overall, sees both drop and concludes the bearing improved. The low frequency harmonics and the raised noise floor tell the truth."},

    {"id": "gear", "name": "Gear tooth wear", "fam": "Gearbox", "group": "Gear & flow",
     "fmax": 5000, "wf_rev": 1, "build": _f_gear,
     "note": "Uniform wear across the teeth changes the shape of the mesh but not its timing, so the gear mesh frequency and its harmonics grow while the sidebands stay modest.",
     "look": ["Gear mesh frequency = teeth x shaft speed, with 2x and 3x GMF.",
              "Sidebands spaced at 1X of the worn gear's shaft, which is how you tell which gear it is.",
              "Often excites a gearcase resonance well above GMF.",
              "Compare against a baseline; GMF is present on every healthy gearbox."],
     "wave": "A high frequency mesh carrier, one cycle per tooth, whose amplitude swells and falls once per revolution of the worn gear. The modulation is smooth and gradual, not a sudden blow; that gentle envelope separates general wear from a single cracked tooth.",
     "phys": "GMF is identical seen from either shaft, so the mesh line alone never says which gear is worn. Only the sideband spacing does."},

    {"id": "gearcrack", "name": "Cracked gear tooth", "fam": "Gearbox", "group": "Gear & flow",
     "fmax": 5000, "wf_rev": 2, "build": _f_gearcrack,
     "note": "One tooth is cracked, so the mesh stiffness drops for a moment once per revolution of that gear. The result is a short impact every revolution rather than a change at mesh frequency.",
     "look": ["Dense sidebands at 1X crowding both sides of GMF.",
              "The GMF line itself may barely change.",
              "Energy spread thinly over many lines rather than concentrated.",
              "An averaged spectrum can hide it completely."],
     "wave": "ONE sharp impact per revolution of the cracked gear. This is the clearest indicator of this fault by a wide margin, and the reason to keep the time waveform at all. Time the gap between impacts against shaft speed to confirm which gear it is. The mesh carrier runs on normally between the blows.",
     "phys": "A once per revolution impact spreads its energy across many spectral lines, so nothing stands out in the spectrum while the waveform shows it plainly. This is the standard argument for waveform analysis."},

    {"id": "blade", "name": "Blade / vane pass", "fam": "Pump & fan", "group": "Gear & flow",
     "fmax": 1000, "wf_rev": 2, "build": _f_blade,
     "note": "Each blade passing the cutwater or a casing tongue produces a pressure pulse. The rate is blade count x shaft speed, and it rises sharply when the running clearance is uneven.",
     "look": ["Blade pass frequency = blades x shaft speed, with harmonics.",
              "Grows with uneven clearance, a damaged blade or a flow restriction.",
              "Some BPF is normal; it is the change that matters.",
              "Sidebands at 1X suggest one blade is different from the rest."],
     "wave": "A regular pulse for every blade passing, so you can count the blades directly off one revolution of the trace. Evenly spaced and even in height when all blades are alike; one short or tall pulse in the set points at a single damaged blade.",
     "phys": "Change the blade count and watch the line move. If a measured peak does not move when you correct the blade count, it is not blade pass."},

    {"id": "cav", "name": "Cavitation", "fam": "Pump & fan", "group": "Gear & flow",
     "fmax": 10000, "wf_rev": 0.5, "build": _f_cav,
     "note": "Vapour bubbles form in the low pressure region and collapse against the impeller. Each collapse is a random event, so the energy has no periodicity at all.",
     "look": ["Random broadband energy, typically above 2 kHz, with no discrete lines.",
              "A hump with no peaks in it, which is unusual and diagnostic.",
              "Blade pass may be raised too if the inlet is starved.",
              "A suction side problem: NPSH, not the pump."],
     "wave": "A continuous random crackle with no repeating pattern anywhere in it. Overlay any two intervals and nothing lines up. It sounds, and looks, like gravel being pumped. Every other fault here repeats at something; this one is the exception, and that absence is the diagnosis.",
     "phys": "There is no frequency to find because there is no repeating event. A spectrum showing a hump with no peaks is telling you something real."},

    {"id": "elec", "name": "Stator / air gap", "fam": "Motor", "group": "Electrical",
     "fmax": 500, "wf_rev": 8, "build": _f_elec,
     "note": "An uneven air gap pulls the rotor towards the narrow side twice per electrical cycle, so the forcing frequency is twice line frequency and has nothing to do with shaft speed.",
     "look": ["A line at 2x line frequency: 100 Hz on a 50 Hz supply.",
              "It does NOT sit at an exact order of shaft speed on an induction motor.",
              "Disappears the instant power is removed. That is the definitive test.",
              "Needs resolution to separate from a nearby running speed harmonic."],
     "wave": "A beat. 2x line frequency and 2x running speed are close but not equal, so the trace swells and fades at the difference between them, often once or twice a second. A slow regular pulsing envelope on an otherwise ordinary trace is the signature, and you can hear it as well as see it.",
     "phys": "On a 2 pole 50 Hz motor the shaft turns near 49.5 Hz, so 2X running speed sits at 99 Hz while 2x line frequency is exactly 100 Hz - 1 Hz apart. On a 4 pole machine at 1485 rpm the shaft turns near 24.75 Hz and it is 4X that lands at 99 Hz. Either way you need the resolution to split them: raise the lines until the two separate. That is why resolution matters."},

    {"id": "rotorbar", "name": "Broken rotor bar", "fam": "Motor", "group": "Electrical",
     "fmax": 200, "lines": 1600, "wf_rev": 20, "build": _f_rotorbar,
     "note": "A cracked or broken rotor bar makes the rotor magnetically asymmetric, so the torque dips each time the fault slips past a pole. The result is 1X modulated at pole pass frequency.",
     "look": ["Sidebands around 1X spaced at pole pass frequency, usually only 1 to 3 Hz away.",
              "Sidebands also appear around the running speed harmonics.",
              "Amplitude is often modest; the spacing is the diagnosis.",
              "Needs high resolution and a long measurement to resolve."],
     "wave": "The 1X sine with a slow amplitude modulation: it swells and fades a few times a second at pole pass frequency. You must look at a long record to see it. At eight revolutions the envelope is invisible; at twenty it becomes obvious. Set the waveform span to Full record and the beating stands out.",
     "phys": "Pole pass frequency = poles x slip speed. At a few hertz, 400 lines will never resolve it. Try 400 lines and then 3200 and watch the sidebands appear."},

    {"id": "softfoot", "name": "Soft foot", "fam": "Mounting", "group": "Rotor & coupling",
     "fmax": 500, "wf_rev": 8, "build": _f_softfoot,
     "note": "One foot does not sit flat, so bolting it down twists the frame and pulls the bearings out of line. The machine is distorted by its own hold down bolts.",
     "look": ["Raised 1X with a moderate 2X, so it reads like unbalance or misalignment.",
              "The spectrum alone will not identify it. The test will.",
              "Often appears right after a machine is moved, shimmed or re-grouted.",
              "Check it BEFORE aligning, or you will align a distorted machine."],
     "wave": "Nothing distinctive - it looks like unbalance. The diagnosis is not in the trace at all: loosen one hold down bolt at a time with the machine running and watch the 1X amplitude. A change of more than about 20 percent when one particular bolt is released names that foot. Run that test before you trust any alignment reading.",
     "phys": "This is here as a deliberate counter example. Three faults in this tab produce almost the same spectrum - unbalance, bent shaft and soft foot - and each is separated by a different physical test, not by the spectrum."},

    {"id": "belt", "name": "Worn / loose belt", "fam": "Belt drive", "group": "Belt drive",
     "fmax": 200, "wf_rev": 8, "build": _f_belt,
     "note": "A worn, cracked or slack belt slaps as the flaw passes round the drive. Belt frequency = pi x sheave pitch diameter x rpm / (60 x belt length), and it is always BELOW running speed.",
     "look": ["Peaks at belt frequency and its harmonics, with 2x belt frequency commonly the largest.",
              "Belt frequency is sub synchronous - typically 0.3 to 0.8X - which narrows the possibilities immediately.",
              "Amplitude is often unsteady because belt tension varies as it runs.",
              "Set the sheave diameter and belt length and the line moves to where it should be."],
     "wave": "An unsteady, non repeating trace with soft impacts at belt frequency rather than at running speed. Because belt frequency is not a whole fraction of shaft speed, the pattern drifts against the revolution rather than locking to it.",
     "phys": "Anything sub synchronous should prompt three questions: belt drive, oil whirl, or rotating looseness at half order. Belt frequency is the only one you can calculate in advance from a tape measure, so calculate it and look there first."},

    {"id": "sheave", "name": "Eccentric sheave", "fam": "Belt drive", "group": "Belt drive",
     "fmax": 500, "wf_rev": 8, "build": _f_sheave,
     "note": "The sheave is not round, or is not concentric with its bore, so belt tension rises and falls once per revolution of that sheave.",
     "look": ["High 1X of the offending sheave's shaft, strongly directional along the belt line.",
              "Horizontal and vertical amplitudes differ markedly, unlike plain unbalance.",
              "Balancing will not fix it - the sheave itself is the problem.",
              "Belt frequency may also be present."],
     "wave": "A clean once per revolution cycle, like unbalance, but the amplitude depends heavily on which direction you measure. Take a reading in line with the belts and another at right angles: a large difference points at the sheave rather than at the rotor.",
     "phys": "Unbalance is roughly equal in all radial directions. A fault that is strongly directional is usually a stiffness or a geometry problem, not a mass problem."},

    {"id": "beltmis", "name": "Sheave misalignment", "fam": "Belt drive", "group": "Belt drive",
     "fmax": 500, "wf_rev": 8, "build": _f_misalign_belt,
     "note": "The two sheaves are not in the same plane, so the belt is dragged sideways as it enters and leaves each one.",
     "look": ["High AXIAL 1X on a belt drive, which should not normally be there.",
              "Some 2X, and belt frequency alongside it.",
              "Belts run hot and wear on one flank.",
              "A straight edge across both sheave faces finds it in seconds."],
     "wave": "Once per revolution, strongest in the axial direction. On a belt drive, axial vibration at 1X is almost always sheave misalignment, because nothing else on a belt drive pushes along the shaft.",
     "phys": "The same reasoning as coupling misalignment: axial vibration needs an axial force, and on a belt drive only a misaligned sheave supplies one."},

    {"id": "resonance", "name": "Resonance", "fam": "Structural", "group": "Structural",
     "fmax": 500, "wf_rev": 8, "build": _f_resonance,
     "note": "Nothing new is being generated. An ordinary force - often quite small residual unbalance - happens to land on a natural frequency of the machine or its structure, and the response is amplified many times over.",
     "look": ["A single very large peak with nothing else to explain it.",
              "Amplitude is extremely sensitive to speed: change the speed a little and it falls away sharply.",
              "Phase sweeps through about 180 degrees as the speed passes through the natural frequency, 90 degrees at the peak.",
              "Balancing may reduce it but the machine stays sensitive - the structure is the problem."],
     "wave": "A large, almost pure sine at the resonant frequency. The waveform looks innocent, which is the trap: a clean sine at a dangerous amplitude.",
     "phys": "Drag the shaft speed slider slowly and watch the 1X amplitude rise and fall as it passes the natural frequency. A bump test or a coast down is how you find this on a real machine, and the fix is to change stiffness or mass, not to balance harder."},

    {"id": "crack", "name": "Cracked shaft", "fam": "Rotor", "group": "Rotor & coupling",
     "fmax": 500, "wf_rev": 8, "build": _f_crack,
     "note": "A transverse crack makes the shaft stiffer in one direction than the other, so it flexes unevenly as it turns. The asymmetry shows as 2X alongside 1X.",
     "look": ["1X and 2X both significant, with 2X growing relative to 1X as the crack opens.",
              "The pattern CHANGES steadily over weeks - that trend is the diagnosis, not any single reading.",
              "Phase also drifts as the crack grows.",
              "A rising 2X on a machine that was previously clean deserves immediate attention."],
     "wave": "Two unequal peaks per revolution, repeating consistently. On its own it looks like misalignment, and that is exactly why a cracked shaft gets missed.",
     "phys": "This is the most dangerous entry in this tab and the hardest to call from one measurement. No single spectrum identifies it; only the trend does. If 1X and 2X are both climbing month on month and alignment has been checked, stop and investigate the shaft."},

    {"id": "cocked", "name": "Cocked bearing", "fam": "Rolling bearing", "group": "Rolling bearing",
     "fmax": 500, "wf_rev": 8, "build": _f_cocked,
     "note": "The bearing inner ring is not square on the shaft, or the outer ring is not square in its housing, so the bearing is forced to wobble once per revolution.",
     "look": ["Significant AXIAL 1X and 2X at a bearing, with no coupling nearby to blame.",
              "Phase across the SAME bearing housing differs by about 180 degrees top to bottom, or side to side.",
              "No defect frequencies - the bearing is not damaged yet, only badly fitted.",
              "It will damage the bearing in time if it is left."],
     "wave": "A once and twice per revolution pattern in the axial direction. The giveaway is not the shape but the phase: measure at four points around one bearing housing and you will find a twisting motion rather than a uniform one.",
     "phys": "Four readings around a single housing separate a cocked bearing from misalignment. A cocked bearing twists about its own centre; misalignment moves the whole housing together."},

    {"id": "turbulence", "name": "Flow turbulence", "fam": "Pump & fan", "group": "Gear & flow",
     "fmax": 200, "wf_rev": 4, "build": _f_turbulence,
     "note": "Air or liquid passing through the machine is not moving smoothly. Pressure fluctuations buffet the rotor at frequencies that have nothing to do with how fast it turns.",
     "look": ["Random, low frequency energy BELOW running speed, with no discrete peaks.",
              "Often a broad hump between 1 and 20 Hz.",
              "Varies with damper or valve position, which is the quickest confirmation.",
              "Common on fans with poor inlet conditions or a restricted duct."],
     "wave": "A slow, random wandering of the trace with no repeating pattern, as if the signal has a drifting baseline under it. Different from cavitation, which is a fast high frequency crackle.",
     "phys": "Sub synchronous and random is a short list: flow turbulence, or a rub, or looseness. Turbulence is the one that changes when you move a damper, and it has no discrete lines at all."},
]

FAULT_BY_ID = dict((f["id"], f) for f in FAULTS)


# ----------------------------------------------------------------------
# Settings and synthesis
# ----------------------------------------------------------------------
class Settings(object):
    """Everything the user can change. Plain attributes so the UI can poke
    them directly."""

    def __init__(self):
        self.fault_id = "unbalance"
        self.rpm = 1485.0
        self.sev = 6.0            # 0-10
        self.bg = 1.0             # background level multiplier
        self.fr = 2800.0          # structural / bearing natural frequency, Hz
        self.bearing = 0          # index into BEARINGS
        self.defect = "bpfo"      # bpfo | bpfi | bsf
        self.teeth = 23
        self.blades = 7
        self.sheave = 200.0       # driver sheave pitch diameter, mm
        self.belt = 1500.0        # belt length, mm
        self.lf = 50.0            # supply frequency
        self.poles = 4
        self.iso = 0              # index into ISO_GROUPS
        self.unit = "vel"         # vel | acc | dis
        self.mode = "spec"        # spec | env
        self.fmax = 500.0
        self.lines = 400
        self.wf_rev = 8.0         # waveform window, revolutions (0 = full record)
        self.aa = True            # anti-alias filter, as a real analyser has
        self.marks = True


def context(st):
    f1 = st.rpm / 60.0
    fs = 2.56 * st.fmax
    o = bearing_orders(BEARINGS[st.bearing])
    def_order = o[st.defect]
    # what modulates each defect: an inner race fault passes the load zone once
    # per shaft revolution, a rolling element once per cage revolution, and a
    # stationary outer race under steady load is essentially unmodulated
    mod_order = 1.0 if st.defect == "bpfi" else (o["ftf"] if st.defect == "bsf" else 0.0)
    ns = 120.0 * st.lf / st.poles
    ppf = max(0.15, st.poles * max(0.0, ns - st.rpm) / 60.0)
    return {
        "f1": f1, "fs": fs, "nyq": fs / 2.0, "s": st.sev / 10.0, "bg": st.bg,
        "fr": st.fr, "fcrit": max(8.0, st.fr / 55.0),
        "brg_o": o, "def_order": def_order, "def_hz": def_order * f1,
        "def_name": st.defect.upper(), "mod_hz": mod_order * f1,
        "teeth": st.teeth, "blades": st.blades, "lf": st.lf,
        "poles": st.poles, "ppf": ppf, "ns": ns,
        # belt frequency = pi x sheave pitch diameter x rpm / (60 x belt length)
        "belt_hz": (math.pi * st.sheave * st.rpm / (60.0 * st.belt)) if st.belt > 0 else 0.0,
        "sheave": st.sheave, "belt": st.belt,
    }


def _add_sine(buf, n, amp, w_dt, ph):
    """Add amp*sin(w_dt*k + ph) for k in 0..n-1, using the two term recurrence
    s[k] = 2cos(w)s[k-1] - s[k-2]. One multiply and one subtract per sample
    instead of a sin() call, which matters on a phone."""
    if amp == 0.0:
        return
    k2 = 2.0 * math.cos(w_dt)
    s0 = amp * math.sin(ph)
    s1 = amp * math.sin(w_dt + ph)
    buf[0] += s0
    if n > 1:
        buf[1] += s1
    for i in range(2, n):
        s2 = k2 * s1 - s0
        buf[i] += s2
        s0 = s1
        s1 = s2


def _add_random(buf, n, fs, bands, rnd, unit):
    """Fill a conjugate symmetric spectrum with band limited random content and
    transform it back, so the random part lands at exactly the designed level
    and cannot alias."""
    if not bands:
        return
    re = [0.0] * n
    im = [0.0] * n
    df = fs / n
    half = n >> 1
    for k in range(1, half):
        f = k * df
        acc = 0.0
        vel = 0.0
        for (lo, hi, aG, vM, flat) in bands:
            if lo <= f <= hi:
                if flat:
                    shape = 1.0
                else:
                    mid = (lo + hi) * 0.5
                    hw = (hi - lo) * 0.5
                    shape = math.exp(-((f - mid) / (hw * 0.7)) ** 2 * 0.5) + 0.35
                if aG:
                    acc += aG * shape
                if vM:
                    vel += vM * shape
        if acc <= 0.0 and vel <= 0.0:
            continue
        amp = 0.0
        if acc > 0.0:
            amp += acc_to_disp(abs(acc * rnd.gauss()), f)
        if vel > 0.0:
            amp += vel_to_disp(abs(vel * rnd.gauss()), f)
        a = amp * unit_gain(unit, f) * n * 0.5
        ph = rnd.next() * TAU
        cr = a * math.cos(ph)
        ci = a * math.sin(ph)
        re[k] = cr
        im[k] = ci
        re[n - k] = cr
        im[n - k] = -ci
    ifft(re, im)
    for i in range(n):
        buf[i] += re[i]


class Result(object):
    __slots__ = ("wave", "mag", "df", "nb", "fs", "n", "t_rec", "f1",
                 "marks", "unit", "env", "overall", "zone", "zone_text",
                 "ctx", "aliased", "wave_t", "crest", "band_hi")


def compute(st):
    """Build the signal and its spectrum for the current settings."""
    c = context(st)
    f = FAULT_BY_ID[st.fault_id]
    fs = c["fs"]
    nyq = c["nyq"]

    n = 1
    while n < 2.56 * st.lines:
        n <<= 1
    # Differentiating in the frequency domain treats the record as periodic, so
    # the wrap discontinuity would ring as a spike at both ends. Build a longer
    # record and keep the middle. The envelope needs the extra length anyway.
    mult = 4 if st.mode == "env" else 2
    n2 = n * mult
    dt = 1.0 / fs
    t2 = n2 / fs

    base = baseline(c)
    m = f["build"](c) or {}
    comps = base["comps"] + list(m.get("comps", []))
    rand = base["rand"] + list(m.get("rand", []))
    impacts = list(m.get("impacts", []))
    clip = m.get("clip")
    seed = _hash_seed(f["id"]) + st.poles

    def build_unit(unit):
        buf = [0.0] * n2
        rl = Rand(seed)
        for (hz, v) in comps:
            if hz <= 0.0 or v <= 0.0:
                continue
            # a real analyser low pass filters before it samples, so content
            # above Nyquist is removed rather than folded back
            if st.aa and hz >= nyq:
                continue
            amp = vel_to_disp(v, hz) * unit_gain(unit, hz)
            _add_sine(buf, n2, amp, TAU * hz * dt, rl.next() * TAU)
        for (rate, fr, accG, q) in impacts:
            if rate <= 0.0:
                continue
            if st.aa and fr >= nyq:
                continue
            period = 1.0 / rate
            a0 = acc_to_disp(accG, fr) * unit_gain(unit, fr)
            decay = math.pi * fr / q
            w = TAU * fr
            k = 0
            while k * period < t2:
                t0 = k * period
                i0 = int(t0 / dt)
                if i0 < 0:
                    i0 = 0
                i = i0
                while i < n2:
                    td = i * dt - t0
                    if td >= 0.0:
                        env = math.exp(-decay * td)
                        if env < 1e-4:
                            break
                        buf[i] += a0 * env * math.sin(w * td)
                    i += 1
                k += 1
        _add_random(buf, n2, fs, rand, Rand(seed + 7), unit)
        return buf

    need_acc = (st.mode == "env")

    if clip:
        # the restraint acts in ONE direction, so the trace is flattened on a
        # single side, which is what the textbook signature describes
        disp = build_unit("dis")
        cf = max(0.25, clip)
        pk = 0.0
        for v in disp:
            if v > pk:
                pk = v
            elif -v > pk:
                pk = -v
        lim = cf * pk
        for i in range(n2):
            if disp[i] < -lim:
                disp[i] = -lim - (disp[i] + lim) * 0.08
        re = list(disp)
        im = [0.0] * n2
        fft(re, im)
        df2 = fs / n2
        units = [st.unit] + (["acc"] if need_acc and st.unit != "acc" else [])
        out = {}
        for unit in units:
            r = [0.0] * n2
            i2 = [0.0] * n2
            for k in range(n2):
                fk = (k if k <= n2 // 2 else n2 - k) * df2
                g = 0.0 if k == 0 else unit_gain(unit, fk)
                r[k] = re[k] * g
                i2[k] = im[k] * g
            ifft(r, i2)
            out[unit] = r
    else:
        out = {st.unit: build_unit(st.unit)}
        if need_acc and st.unit != "acc":
            out["acc"] = build_unit("acc")

    off = (n2 - n) >> 1
    x = out[st.unit][off:off + n]

    if st.mode == "env":
        acc_long = out.get("acc", out[st.unit])
        env_sig = envelope(acc_long, n2, fs, m.get("env_band") or st.fr)
        spec = spectrum(env_sig, n2, fs)
        shown = env_sig[off:off + n]
    else:
        spec = spectrum(x, n, fs)
        if st.unit == "dis":
            # displacement is read peak to peak by convention, so one sinusoid's
            # line equals the peak to trough span of the waveform above it
            mag = spec[0]
            for k in range(len(mag)):
                mag[k] *= 2.0
        shown = x

    mag, df, nb = spec

    # overall velocity RMS over the ISO band, converted from the displayed
    # spectrum rather than built again in the time domain
    overall = 0.0
    if st.mode != "env":
        gain_disp = 2.0 if st.unit == "dis" else 1.0
        for k in range(1, nb):
            fk = k * df
            if fk < 10.0 or fk > 1000.0:
                continue
            gshown = unit_gain(st.unit, fk) * gain_disp
            if gshown <= 0.0:
                continue
            v = mag[k] / gshown * unit_gain("vel", fk)
            overall += (v / math.sqrt(2.0)) ** 2
        # a Hanning window spreads every component over about 1.5 bins, so the
        # squares summed above over count by that noise bandwidth
        overall = math.sqrt(overall / 1.5)

    # the ISO band is 10-1000 Hz, but the spectrum only reaches F-max, so say
    # which band the figure actually covers rather than implying the full one
    band_hi = min(1000.0, st.fmax)
    zone, ztext = iso_zone(overall, ISO_GROUPS[st.iso])

    # honest warning when real content sits above Nyquist
    aliased = []
    for (hz, lab) in m.get("marks", []):
        if hz > nyq:
            aliased.append("%s %.0f Hz" % (lab, hz))

    rms = 0.0
    pk = 0.0
    for v in shown:
        rms += v * v
        if abs(v) > pk:
            pk = abs(v)
    rms = math.sqrt(rms / max(1, len(shown)))

    r = Result()
    r.wave = shown
    r.mag = mag
    r.df = df
    r.nb = nb
    r.fs = fs
    r.n = n
    r.t_rec = n / fs
    r.f1 = c["f1"]
    r.marks = list(m.get("marks", []))
    r.unit = st.unit
    r.env = (st.mode == "env")
    r.overall = overall
    r.zone = zone
    r.zone_text = ztext
    r.ctx = c
    r.aliased = aliased
    r.crest = (pk / rms) if rms > 0 else 0.0
    r.band_hi = band_hi
    return r


def spectrum(x, n, fs):
    """Hanning windowed amplitude spectrum. A bin centred component reads back
    at its own peak amplitude."""
    re = [0.0] * n
    im = [0.0] * n
    for i in range(n):
        re[i] = x[i] * 0.5 * (1.0 - math.cos(TAU * i / n))
    fft(re, im)
    nb = int(n / 2.56)
    mag = [0.0] * nb
    for k in range(nb):
        # 4/N with the Hanning coherent gain of 0.5 folded in
        mag[k] = 4.0 * math.hypot(re[k], im[k]) / n
    return mag, fs / n, nb


def envelope(x_acc, n, fs, fr):
    """Band pass about the resonance, form the analytic signal, and return the
    magnitude of its envelope with the mean removed."""
    re = list(x_acc)
    im = [0.0] * n
    fft(re, im)
    df = fs / n
    lo = max(df, fr * 0.55)
    hi = min(fs * 0.5, fr * 1.45)
    r2 = [0.0] * n
    i2 = [0.0] * n
    for k in range(1, n >> 1):
        f = k * df
        if lo <= f <= hi:
            r2[k] = 2.0 * re[k]    # analytic signal: positive frequencies only
            i2[k] = 2.0 * im[k]
    ifft(r2, i2)
    env = [0.0] * n
    mean = 0.0
    for i in range(n):
        e = math.hypot(r2[i], i2[i])
        env[i] = e
        mean += e
    mean /= n
    for i in range(n):
        env[i] -= mean
    return env


# ----------------------------------------------------------------------
# self test - run by the CI workflow so a bad edit cannot reach a build
# ----------------------------------------------------------------------
def self_test():
    fails = []

    def check(name, got, want, tol):
        if want == 0:
            ok = abs(got) <= tol
        else:
            ok = abs(got - want) <= tol * abs(want)
        if not ok:
            fails.append("%s: got %r want %r" % (name, got, want))
        return ok

    # bearing geometry against published 6205 values, and the identities
    # BPFO + BPFI = ball count, and FTF x ball count = BPFO
    o = bearing_orders(BEARINGS[0])
    check("6205 BPFO", o["bpfo"], 3.5848, 1e-3)
    check("6205 BPFI", o["bpfi"], 5.4152, 1e-3)
    check("6205 BSF", o["bsf"], 2.3567, 1e-3)
    check("6205 FTF", o["ftf"], 0.3983, 1e-3)
    check("BPFO+BPFI = N", o["bpfo"] + o["bpfi"], 9.0, 1e-9)
    check("FTF x N = BPFO", o["ftf"] * 9.0 - o["bpfo"], 0.0, 1e-9)

    # the FFT must read a bin centred sine back at its own amplitude
    n, fs = 1024, 2560.0
    x = [7.0 * math.sin(TAU * 20 * i / n + 0.3) for i in range(n)]
    mag, df, nb = spectrum(x, n, fs)
    check("FFT amplitude", mag[20], 7.0, 1e-6)

    # the three measurement units must be one signal seen three ways
    st = Settings()
    st.fault_id = "unbalance"; st.sev = 10; st.bg = 0.0001
    st.rpm = 1500; st.fmax = 500; st.lines = 400

    def peak(r, hz):
        k = int(round(hz / r.df))
        return max(r.mag[max(1, k - 2):k + 3])

    st.unit = "vel"; rv = compute(st); v = peak(rv, rv.f1)
    st.unit = "acc"; a = peak(compute(st), rv.f1)
    st.unit = "dis"; d = peak(compute(st), rv.f1)
    check("acc from vel", a, v * TAU * rv.f1 / 1000.0 / G, 1e-6)
    check("dis from vel", d, v * 1000.0 / (math.pi * rv.f1), 1e-6)

    # Parseval: the waveform and its spectrum must describe the same signal
    for fid, unit in (("unbalance", "vel"), ("looseA", "vel"), ("brg3", "acc")):
        st = Settings()
        st.fault_id = fid; st.unit = unit; st.sev = 7; st.lines = 400
        st.fmax = 5000 if fid == "brg3" else 500
        r = compute(st)
        nn = len(r.wave)
        wr = math.sqrt(sum(q * q for q in r.wave) / nn)
        mg, _, _ = spectrum(r.wave, nn, r.fs)
        sr = math.sqrt(sum((q / math.sqrt(2.0)) ** 2 for q in mg[1:]) / 1.5)
        check("Parseval " + fid, sr, wr, 0.05)

    # the four stage bearing model: high frequency energy must peak at stage 3
    # and fall back at stage 4, and the defect must only become visible in the
    # ordinary velocity spectrum at stage 3
    hf = {}
    snr = {}
    for fid in ("brg1", "brg2", "brg3", "brg4"):
        st = Settings()
        st.fault_id = fid; st.unit = "acc"; st.fmax = 40000; st.sev = 7; st.lines = 400
        r = compute(st)
        s2 = 0.0
        for k in range(1, r.nb):
            f = k * r.df
            if 9000.0 <= f < 40000.0:
                s2 += (r.mag[k] / math.sqrt(2.0)) ** 2
        hf[fid] = math.sqrt(s2 / 1.5)
        st.unit = "vel"; st.fmax = 1000
        r2 = compute(st)
        k = int(round(r2.ctx["def_hz"] / r2.df))
        pk = max(r2.mag[max(1, k - 2):k + 3])
        snr[fid] = pk / (sum(r2.mag[1:]) / (r2.nb - 1))
    if not (hf["brg1"] < hf["brg2"] < hf["brg3"] and hf["brg4"] < hf["brg3"]):
        fails.append("bearing HF energy must rise to stage 3 then fall: %r" % hf)
    if not (snr["brg3"] > 10 and snr["brg1"] < 5 and snr["brg2"] < 5):
        fails.append("defect must only show in the velocity spectrum at stage 3: %r" % snr)

    # envelope must find the defect rate where the plain spectrum cannot
    st = Settings()
    st.fault_id = "brg2"; st.unit = "acc"; st.fmax = 5000
    st.mode = "env"; st.sev = 7; st.lines = 400
    r = compute(st)
    k = int(round(r.ctx["def_hz"] / r.df))
    best, bk = 0.0, k
    for j in range(max(1, k - 2), k + 3):
        if r.mag[j] > best:
            best, bk = r.mag[j], j
    if abs(bk * r.df - r.ctx["def_hz"]) > 2.5 * r.df:
        fails.append("envelope peak %.1f Hz, defect %.1f Hz" % (bk * r.df, r.ctx["def_hz"]))
    if best / (sum(r.mag[1:]) / (r.nb - 1)) < 8:
        fails.append("envelope signal to noise too low")

    # every fault must build at every extreme without blowing up
    for f in FAULTS:
        for rpm in (300, 1485, 6000):
            for fmax in (200, 1000, 10000):
                for unit in ("vel", "acc", "dis"):
                    st = Settings()
                    st.fault_id = f["id"]; st.rpm = rpm; st.fmax = fmax
                    st.unit = unit; st.sev = 10; st.lines = 200
                    try:
                        r = compute(st)
                    except Exception as exc:
                        fails.append("%s %s/%s/%s raised %s" % (f["id"], rpm, fmax, unit, exc))
                        continue
                    for q in r.wave:
                        if q != q or q in (float("inf"), float("-inf")):
                            fails.append("%s %s/%s/%s produced a bad sample" % (f["id"], rpm, fmax, unit))
                            break

    return fails


if __name__ == "__main__":
    import time
    t0 = time.time()
    problems = self_test()
    el = time.time() - t0
    if problems:
        print("FAIL (%d)" % len(problems))
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print("fault_engine self test OK (%d faults, %.1f s)" % (len(FAULTS), el))
