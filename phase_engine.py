"""
phase_engine - field phase analysis physics for the CM Toolkit Phase Survey
tool. Pure Python, no Kivy and no numpy:  python phase_engine.py  runs the
self test (used by the CI sanity check).

THE MACHINE
A motor driving a pump (rotor between bearings) or an overhung fan through a
flexible coupling. Bearing 1 motor NDE, 2 motor DE, 3 driven DE, 4 driven NDE.
Each fault is a pattern of forces at the bearings:
  - a rotating force (unbalance, bent shaft) turns with the shaft, so at a
    bearing the H reading lags the V reading by 90 deg
  - a directional force (misalignment, eccentric loads) acts along one line,
    so H and V move in phase or 180 deg apart
  - axial forces can be a piston motion of the whole housing, or a wobble
    (cocked bearing) whose phase changes round the housing face
Each bearing's support is a damped spring in H, V and A, so the force
pattern is shaped by real dynamics (and amplified near a natural frequency
for the resonance fault).

CONVENTIONS
  - viewed from the motor non-drive end the shaft turns clockwise
  - horizontal sensors on the right-hand side, vertical on top, all axial
    sensors pointing towards the driven end
  - phase lag = degrees from the tach pulse to the next positive peak of the
    1X signal; lead = 360 - lag
  - amplitude mm/s RMS (velocity), g RMS (acceleration), um pk-pk (displacement)

Every reading is measured from a synthesized signal over 8 revolutions:
1X + harmonics + broadband noise + a neighbouring machine at 97 % of running
speed, which is what makes weak readings scatter as they do in the field.
"""

import cmath
import math

from fault_engine import Rand, TAU

D2R = math.pi / 180.0
SPR = 64
NREV = 8
NOISE = 0.22          # mm/s rms broadband
NEIGHBOUR = 0.25      # mm/s peak, neighbouring machine at 0.97 x speed
ZETA = 0.08
FN = {"motor": {"H": 3600.0, "V": 5400.0, "A": 3800.0},
      "driven": {"H": 3000.0, "V": 4800.0, "A": 3600.0}}

TRAINS = {
    "pump": {"name": "Motor + pump", "x": [0.10, 0.36, 0.55, 0.88], "driven": "pump"},
    "fan": {"name": "Motor + overhung fan", "x": [0.10, 0.36, 0.55, 0.74], "driven": "fan"},
}
FAULTS = [
    ("healthy", "Healthy", ("pump", "fan")),
    ("static", "Static unbalance", ("pump", "fan")),
    ("couple", "Couple unbalance", ("pump",)),
    ("dynamic", "Dynamic unbalance", ("pump",)),
    ("overhung", "Overhung unbalance", ("fan",)),
    ("angular", "Angular misalignment", ("pump", "fan")),
    ("parallel", "Parallel misalignment", ("pump", "fan")),
    ("bent", "Bent shaft", ("pump", "fan")),
    ("cocked", "Cocked bearing", ("pump", "fan")),
    ("loose", "Structural looseness", ("pump", "fan")),
    ("resonance", "Resonance", ("pump", "fan")),
]
FAULT_NAME = dict((f[0], f[1]) for f in FAULTS)

GUIDE = {
    "healthy": ("Only residual unbalance and the background. All levels low. Use it as the baseline: notice how much the phase of small readings wanders.",
                ["Low amplitude everywhere, so phase is less trustworthy than on a faulty machine.",
                 "H to V still close to 90 deg at each bearing: residual unbalance is still a rotating force."]),
    "static": ("The mass centre of the driven rotor is off its axis, so the whole rotor is pushed outwards once per revolution, the same way at both bearings.",
               ["3H and 4H in phase, 3V and 4V in phase (within about 30 deg).",
                "H to V close to 90 deg at each bearing: a rotating force.",
                "Axial low. Its phase is unreliable for the same reason."]),
    "couple": ("Two equal heavy spots at opposite ends and opposite sides. The rotor rocks about its centre, so the two bearings move in opposite directions.",
               ["3H vs 4H about 180 deg, 3V vs 4V about 180 deg.",
                "H to V about 90 deg at each bearing.",
                "Needs two-plane balancing: a single weight cannot fix it."]),
    "dynamic": ("Static and couple together, the usual real case. The phase difference between the two bearings is neither 0 nor 180.",
                ["3H vs 4H somewhere between, here around 100 deg.",
                 "H to V about 90 deg at each bearing.",
                 "Two-plane balancing."]),
    "overhung": ("The fan wheel sits outboard of both bearings. Its unbalance bends and rocks the shaft, so the wheel wobbles and pushes the shaft axially once per revolution.",
                 ["High axial 1X at the fan bearings, 3A and 4A in phase.",
                  "Radial phase between 3 and 4 often close to 180 deg (the shaft pivots between them).",
                  "Across the coupling the axial is NOT 180 deg - that separates it from angular misalignment."]),
    "angular": ("The shaft centrelines meet at an angle at the coupling. Each revolution the coupling pushes one shaft while it pulls the other, along the axis.",
                ["High axial 1X, often with 2X.",
                 "2A vs 3A about 180 deg across the coupling.",
                 "Each rotor moves axially as one piece: 1A in phase with 2A, 3A with 4A."]),
    "parallel": ("The shaft centrelines are offset. The coupling forces the two shaft ends in opposite radial directions, along a fixed line.",
                 ["2H vs 3H and 2V vs 3V about 180 deg across the coupling.",
                  "H to V close to 0 or 180 deg at the coupling bearings: straight-line motion.",
                  "Strong 2X in the raw waveform."]),
    "bent": ("The driven shaft is bowed. The bearings see unbalance-like radial vibration, and the journals tilt in opposite directions, so the ends move axially against each other.",
             ["High axial 1X.",
              "3A vs 4A about 180 deg across the same rotor.",
              "Radial behaves like static unbalance."]),
    "cocked": ("The outer race of bearing 4 sits tilted in its housing. The rotating tilt makes the housing face wobble, so axial readings round the housing are out of phase with each other.",
               ["Take the four axial points round bearing 4 (top, right, bottom, left).",
                "Top vs bottom about 180 deg, left vs right about 180 deg, top to right about 90 deg.",
                "A single axial reading shows only that axial is high."]),
    "loose": ("A foot of the driven machine is not held down. The foot lifts and lands each revolution, the response is nonlinear, and the phase will not repeat.",
              ["Repeat a reading at 4V: phase and amplitude jump from reading to reading.",
               "Driven foot vs base: about 180 deg and a big amplitude step across the joint.",
               "Harmonics in the raw waveform."]),
    "resonance": ("The driven machine's support has a horizontal natural frequency close to running speed. A modest unbalance force is amplified in that one direction only, with its phase shifted.",
                  ["Horizontal much higher than vertical at bearings 3 and 4.",
                   "H to V far from 90 deg, near 180: the motion is directional.",
                   "Move the running speed a little: the phase swings fast. That speed sensitivity is the proof."]),
}

STD = ["1H", "1V", "1A", "2H", "2V", "2A", "3H", "3V", "3A", "4H", "4V", "4A"]
EXTRA = [("4AT", "4A top"), ("4AR", "4A right"), ("4AB", "4A bottom"), ("4AL", "4A left"),
         ("FOOT", "Driven foot"), ("BASE", "Base under it")]
EXTRA_NAME = dict(EXTRA)
UNIT_TXT = {"vel": "mm/s RMS", "acc": "g RMS", "dis": "um pk-pk"}


def label(pid):
    return EXTRA_NAME.get(pid, pid)


def wrap(a):
    a = math.fmod(a, 360.0)
    return a + 360.0 if a < 0 else a


def sdiff(a, b):
    """Signed b - a in (-180, 180]."""
    return math.fmod(math.fmod(b - a, 360.0) + 540.0, 360.0) - 180.0


def P(A, lag_deg):
    """A cos(wt - lag)  ->  phasor A e^{-i lag}."""
    return A * cmath.exp(-1j * lag_deg * D2R)


def lag_of(p):
    return wrap(-math.degrees(cmath.phase(p)))


class Setup(object):
    """Everything that decides what a reading shows."""

    def __init__(self):
        self.train = "pump"
        self.fault = "static"
        self.sev = 5.0
        self.rpm = 1480.0
        self.unit = "vel"
        self.tape = 0.0
        self.axdir = "same"      # same | into
        self.flip = {}           # point id -> True when that sensor is reversed

    def copy(self):
        s = Setup()
        s.__dict__.update(self.__dict__)
        s.flip = dict(self.flip)
        return s

    def sig(self, pid):
        return "%s|%g|%s|%d" % (self.unit, self.tape, self.axdir, 1 if self.flip.get(pid) else 0)


def _side(b):
    return "motor" if b <= 2 else "driven"


def G(b, d, st):
    fn, z = FN[_side(b)][d], ZETA
    if st.fault == "resonance" and _side(b) == "driven" and d == "H":
        fn, z = 1500.0, 0.05
    r = st.rpm / fn
    return 1.0 / complex(1.0 - r * r, 2.0 * z * r)


def model(st):
    """1X velocity phasors (mm/s peak) at every point, plus harmonic ratios
    and which points have a phase that will not repeat."""
    a = 0.9 * st.sev
    R = dict((b, {"H": 0j, "V": 0j}) for b in range(1, 5))
    AX = dict((b, 0j) for b in range(1, 5))
    WOB = dict((b, 0j) for b in range(1, 5))
    H2, H3 = {}, {}

    def rot(b, F, hs):
        R[b]["V"] += P(F, hs)
        R[b]["H"] += P(F, hs + 90.0)

    def dirf(b, F, psi, lag):
        R[b]["V"] += P(F * math.cos(psi * D2R), lag)
        R[b]["H"] += P(F * math.sin(psi * D2R), lag)

    def ax(b, F, lag):
        AX[b] += P(F, lag)

    rot(1, 0.55, 200)
    rot(2, 0.6, 210)
    rot(3, 0.5, 110)
    rot(4, 0.45, 125)
    ax(1, 0.18, 300)
    ax(2, 0.2, 310)
    ax(3, 0.18, 120)
    ax(4, 0.16, 130)
    f = st.fault
    if f == "static":
        rot(3, a, 40); rot(4, a, 40); rot(2, 0.12 * a, 40); rot(1, 0.06 * a, 40)
    elif f == "couple":
        rot(3, a, 40); rot(4, a, 220)
    elif f == "dynamic":
        rot(3, a, 40); rot(4, 0.75 * a, 140)
    elif f == "overhung":
        rot(4, 1.25 * a, 40); rot(3, 0.45 * a, 220); ax(3, 0.75 * a, 60); ax(4, 0.8 * a, 60)
    elif f == "angular":
        ax(2, 0.95 * a, 70); ax(1, 0.6 * a, 70); ax(3, 0.95 * a, 250); ax(4, 0.6 * a, 250)
        dirf(2, 0.25 * a, 0, 70); dirf(3, 0.25 * a, 0, 250)
        for k in (1, 2, 3, 4):
            H2["%dA" % k] = 0.5
    elif f == "parallel":
        dirf(2, 0.95 * a, 35, 120); dirf(3, 0.95 * a, 35, 300)
        dirf(1, 0.4 * a, 35, 120); dirf(4, 0.4 * a, 35, 300)
        ax(2, 0.25 * a, 120); ax(3, 0.25 * a, 300)
        for k in ("2H", "2V", "3H", "3V", "1H", "1V", "4H", "4V"):
            H2[k] = 0.7
    elif f == "bent":
        rot(3, 0.8 * a, 40); rot(4, 0.8 * a, 40); ax(3, 0.85 * a, 100); ax(4, 0.85 * a, 280)
    elif f == "cocked":
        WOB[4] = P(0.9 * a, 30); ax(4, 0.1 * a, 30); rot(4, 0.3 * a, 40); rot(3, 0.2 * a, 40)
        H2["4A"] = 0.3
    elif f == "loose":
        rot(3, 0.5 * a, 40); rot(4, 0.55 * a, 40)
        for k in ("4H", "4V", "FOOT"):
            H2[k] = 0.45
            H3[k] = 0.3
    elif f == "resonance":
        rot(3, 0.16 * a, 40); rot(4, 0.16 * a, 40)
    out = {}
    for b in range(1, 5):
        # velocity leads displacement by 90: a factor i, the same at every point
        out["%dH" % b] = R[b]["H"] * G(b, "H", st) * 1j
        out["%dV" % b] = R[b]["V"] * G(b, "V", st) * 1j
        ga = G(b, "A", st) * 1j

        def at(beta, b=b, ga=ga):
            return (AX[b] + WOB[b] * cmath.exp(-1j * beta * D2R)) * ga
        out["%dA" % b] = at(90)                 # the standard axial point is on the H side
        if b == 4:
            out["4AT"], out["4AR"], out["4AB"], out["4AL"] = at(0), at(90), at(180), at(270)
    out["FOOT"] = out["4V"] * (1.35 if f == "loose" else 0.9)
    out["BASE"] = out["4V"] * (-0.45 if f == "loose" else 0.8)
    if f == "loose":
        out["4H"] *= 1.5
        out["4V"] *= 1.5
    jitter = {"4H": 110.0, "4V": 110.0, "FOOT": 30.0} if f == "loose" else {}
    return {"p": out, "h2": H2, "h3": H3, "jitter": jitter}


def unit_factor(unit, rpm):
    w = TAU * rpm / 60.0
    if unit == "acc":
        return 1j * w / 1000.0 / 9.80665       # g peak, leads 90
    if unit == "dis":
        return 1000.0 / (1j * w)                # um peak, lags 90
    return 1.0 + 0j


def display(unit, pk):
    return 2.0 * pk if unit == "dis" else pk / math.sqrt(2.0)


def synth(pid, st, seed):
    """One reading at point pid: the sampled waveform (8 revolutions, tach
    pulse at the start of each) and the measured 1X amplitude and lag."""
    m = model(st)
    rr = Rand(seed)
    for _ in range(3):
        rr.next()                               # decorrelate nearby seeds
    p1 = m["p"].get(pid, 0j)
    if pid in m["jitter"]:
        p1 *= cmath.exp(1j * (rr.next() - 0.5) * m["jitter"][pid] * D2R)
        p1 *= 1.0 + (rr.next() - 0.5) * 0.6
    uf = unit_factor(st.unit, st.rpm)
    uf2 = unit_factor(st.unit, 2 * st.rpm)
    uf3 = unit_factor(st.unit, 3 * st.rpm)
    rev_axial = st.axdir == "into" and (pid in ("3A", "4A") or pid.startswith("4A"))
    flip = (-1.0 if st.flip.get(pid) else 1.0) * (-1.0 if rev_axial else 1.0)
    tape = cmath.exp(-1j * st.tape * D2R)       # tach fires later: every lag grows by tape
    q1 = p1 * uf * tape * flip
    q2 = p1 * m["h2"].get(pid, 0.0) * uf2 * tape * tape * flip
    q3 = p1 * m["h3"].get(pid, 0.0) * uf3 * tape * tape * tape * flip
    nb = cmath.exp(1j * rr.next() * TAU) * unit_factor(st.unit, 0.97 * st.rpm) * NEIGHBOUR
    nscale = abs(uf) * NOISE
    n = SPR * NREV
    x = [0.0] * n
    acc = 0j
    for i in range(n):
        th = TAU * i / SPR
        e1 = cmath.exp(1j * th)
        v = ((q1 * e1).real + (q2 * e1 * e1).real + (q3 * e1 * e1 * e1).real
             + (nb * cmath.exp(1j * 0.97 * th)).real + nscale * rr.gauss())
        x[i] = v
        acc += v / e1
    c1 = 2.0 * acc / n
    return {"x": x, "c1": c1, "amp": display(st.unit, abs(c1)), "lag": lag_of(c1)}


# ----------------------------------------------------------------------
# the survey sheet and what the phases say
# ----------------------------------------------------------------------
class Survey(object):
    def __init__(self):
        self.r = {}          # pid -> list of readings
        self._seed = 1

    def clear(self):
        self.r = {}

    def take(self, pid, st):
        seed = (self._seed * 2654435761) & 0xFFFFFFFF
        self._seed += 1
        s = synth(pid, st, seed)
        lst = self.r.setdefault(pid, [])
        lst.append({"amp": s["amp"], "lag": s["lag"], "seed": seed, "setup": st.copy(), "sig": st.sig(pid)})
        if len(lst) > 8:
            lst.pop(0)

    def last(self, pid):
        lst = self.r.get(pid)
        return lst[-1] if lst else None

    def scatter(self, pid):
        lst = self.r.get(pid) or []
        m = 0.0
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                m = max(m, abs(sdiff(lst[i]["lag"], lst[j]["lag"])))
        return m

    def max_amp(self, unit):
        m = 0.0
        for pid in self.r:
            rd = self.last(pid)
            if rd and rd["setup"].unit == unit:
                m = max(m, rd["amp"])
        return m

    def _floor(self, rd):
        s = rd["setup"]
        return display(s.unit, abs(unit_factor(s.unit, s.rpm)) * 0.45)

    def is_low(self, pid):
        rd = self.last(pid)
        if not rd:
            return False
        return rd["amp"] < max(0.15 * self.max_amp(rd["setup"].unit), self._floor(rd))

    def noisy(self, pid):
        rd = self.last(pid)
        return rd is None or rd["amp"] < self._floor(rd)

    def pair(self, a, b):
        ra, rb = self.last(a), self.last(b)
        if not ra or not rb or self.is_low(a) or self.is_low(b):
            return None
        return sdiff(ra["lag"], rb["lag"])

    def pair_hv(self, b):
        h, v = "%dH" % b, "%dV" % b
        if self.noisy(h) or self.noisy(v):
            return None
        return sdiff(self.last(h)["lag"], self.last(v)["lag"])

    def high_axial(self, apts, rpts):
        amax = rmax = 0.0
        anyp = False
        for k in apts:
            rd = self.last(k)
            if rd:
                anyp = True
                if not self.is_low(k):
                    amax = max(amax, rd["amp"])
        for k in rpts:
            rd = self.last(k)
            if rd:
                rmax = max(rmax, rd["amp"])
        if not anyp or rmax == 0:
            return None
        return amax >= 0.5 * rmax

    def radial_over(self, bs):
        anyp, ok = False, True
        for b in bs:
            h, v, a = self.last("%dH" % b), self.last("%dV" % b), self.last("%dA" % b)
            if not a or (not h and not v):
                continue
            anyp = True
            if max(h["amp"] if h else 0.0, v["amp"] if v else 0.0) < a["amp"]:
                ok = False
        return ok if anyp else None

    def ratio_hv(self, b):
        h, v = self.last("%dH" % b), self.last("%dV" % b)
        if not h or not v:
            return None
        return h["amp"] >= 3.0 * v["amp"]

    def level(self, st):
        m = 0.0
        for k in STD:
            rd = self.last(k)
            if rd and rd["setup"].unit == st.unit:
                m = max(m, rd["amp"])
        return m, m >= display(st.unit, abs(unit_factor(st.unit, st.rpm)) * 2.5)

    def step(self, a, b):
        ra, rb = self.last(a), self.last(b)
        if not ra or not rb:
            return None
        return ra["amp"] >= 2.0 * rb["amp"]

    def mixed_setup(self):
        sigs = set()
        for lst in self.r.values():
            for rd in lst:
                s = rd["setup"]
                sigs.add((s.unit, s.tape, s.axdir))
        return len(sigs) > 1


def rel(d):
    a = abs(d)
    if a <= 30:
        return "in", "in phase"
    if a >= 150:
        return "anti", "180 deg out"
    if 60 <= a <= 120:
        return "quad", "about 90 deg"
    return "mid", "about %d deg" % round(a)


def analyse(sv):
    checks = []

    def addc(lab, d, extra=""):
        if d is None:
            return
        k, t = rel(d)
        checks.append({"label": lab, "k": k, "t": t, "d": d, "extra": extra})

    for b in range(1, 5):
        d = sv.pair_hv(b)
        if d is not None:
            k, t = rel(d)
            extra = "rotating force" if k == "quad" else ("straight-line motion" if k in ("in", "anti") else "")
            checks.append({"label": "%dH - %dV" % (b, b), "k": k, "t": t, "d": d, "extra": extra})
    addc("1H - 2H", sv.pair("1H", "2H"))
    addc("1V - 2V", sv.pair("1V", "2V"))
    addc("3H - 4H", sv.pair("3H", "4H"))
    addc("3V - 4V", sv.pair("3V", "4V"))
    addc("2H - 3H", sv.pair("2H", "3H"), "across coupling")
    addc("2V - 3V", sv.pair("2V", "3V"), "across coupling")
    addc("1A - 2A", sv.pair("1A", "2A"))
    addc("2A - 3A", sv.pair("2A", "3A"), "across coupling")
    addc("3A - 4A", sv.pair("3A", "4A"))
    addc("4A top - bottom", sv.pair("4AT", "4AB"))
    addc("4A left - right", sv.pair("4AL", "4AR"))
    addc("Foot - base", sv.pair("FOOT", "BASE"), "across the joint")
    hm = sv.high_axial(["1A", "2A"], ["1H", "1V", "2H", "2V"])
    hd = sv.high_axial(["3A", "4A"], ["3H", "3V", "4H", "4V"])
    if hm is not None:
        checks.append({"label": "Motor axial", "k": "anti" if hm else "in", "t": "high" if hm else "low", "extra": "vs radial"})
    if hd is not None:
        checks.append({"label": "Driven axial", "k": "anti" if hd else "in", "t": "high" if hd else "low", "extra": "vs radial"})
    scat = [k for k in sv.r if sv.scatter(k) > 20 and not sv.is_low(k)]
    for k in scat:
        checks.append({"label": label(k), "k": "mid", "t": "unstable",
                       "extra": "repeat readings differ by %d deg" % round(sv.scatter(k))})
    return {"checks": checks, "hm": hm, "hd": hd, "scat": scat}


def _cls(d, k):
    return None if d is None else rel(d)[0] == k


def _between(d):
    return None if d is None else 40 < abs(d) < 140


def patterns(sv, A, train):
    hv = sv.pair_hv

    def straight(b):
        d = hv(b)
        return None if d is None else rel(d)[0] in ("in", "anti")

    def either(a, b):
        return None if (a is None and b is None) else bool(a or b)

    nhd = None if A["hd"] is None else (not A["hd"])
    drv = ("3H", "3V", "4H", "4V")
    steady = None
    if any(len(sv.r.get(k) or []) > 1 for k in drv):
        steady = not any(k in A["scat"] for k in drv)
    st_c = ("driven phase repeats", steady)
    cands = [
        ("Static unbalance", None, [("3H, 4H in phase", _cls(sv.pair("3H", "4H"), "in")), ("3V, 4V in phase", _cls(sv.pair("3V", "4V"), "in")),
                                    ("3H-3V about 90", _cls(hv(3), "quad")), ("4H-4V about 90", _cls(hv(4), "quad")), ("driven axial low", nhd), st_c]),
        ("Couple unbalance", None, [("3H, 4H 180", _cls(sv.pair("3H", "4H"), "anti")), ("3V, 4V 180", _cls(sv.pair("3V", "4V"), "anti")),
                                    ("3H-3V about 90", _cls(hv(3), "quad")), ("4H-4V about 90", _cls(hv(4), "quad")), ("driven axial low", nhd), st_c]),
        ("Dynamic unbalance", None, [("3H, 4H in between", _between(sv.pair("3H", "4H"))), ("3V, 4V in between", _between(sv.pair("3V", "4V"))),
                                     ("3H-3V about 90", _cls(hv(3), "quad")), ("4H-4V about 90", _cls(hv(4), "quad")), ("driven axial low", nhd), st_c]),
        ("Overhung unbalance", "fan", [("driven axial high", A["hd"]), ("3A, 4A in phase", _cls(sv.pair("3A", "4A"), "in")),
                                       ("2A-3A not 180", None if sv.pair("2A", "3A") is None else not _cls(sv.pair("2A", "3A"), "anti"))]),
        ("Angular misalignment", None, [("axial high", None if (A["hd"] is None and A["hm"] is None) else bool(A["hd"] or A["hm"])),
                                        ("2A-3A 180 across coupling", _cls(sv.pair("2A", "3A"), "anti")),
                                        ("1A, 2A in phase", _cls(sv.pair("1A", "2A"), "in")), ("3A, 4A in phase", _cls(sv.pair("3A", "4A"), "in"))]),
        ("Parallel misalignment", None, [("2H-3H 180 across coupling", _cls(sv.pair("2H", "3H"), "anti")), ("2V-3V 180 across coupling", _cls(sv.pair("2V", "3V"), "anti")),
                                         ("straight-line at 2", straight(2)), ("straight-line at 3", straight(3)), ("radial above axial at 2 and 3", sv.radial_over([2, 3]))]),
        ("Bent shaft", None, [("driven axial high", A["hd"]), ("3A-4A 180", _cls(sv.pair("3A", "4A"), "anti"))]),
        ("Cocked bearing (4)", None, [("4A top-bottom 180", _cls(sv.pair("4AT", "4AB"), "anti")), ("4A left-right 180", _cls(sv.pair("4AL", "4AR"), "anti"))]),
        ("Looseness", None, [("phase repeats badly", True if A["scat"] else (False if any(len(v) > 1 for v in sv.r.values()) else None)),
                             ("foot-base 180", _cls(sv.pair("FOOT", "BASE"), "anti")),
                             ("big step foot to base", sv.step("FOOT", "BASE"))]),
        ("Resonance", None, [("straight-line at 3 or 4", either(straight(3), straight(4))),
                             ("H at least 3 x V at 3 or 4", either(sv.ratio_hv(3), sv.ratio_hv(4)))]),
    ]
    res = []
    for name, only, conds in cands:
        if only and only != train:
            continue
        known = [c for c in conds if c[1] is not None]
        if len(known) < 2:
            continue
        yes = [c[0] for c in known if c[1]]
        no = [c[0] for c in known if not c[1]]
        res.append({"n": name, "score": len(yes) / float(len(known)), "yes": yes, "no": no,
                    "missing": [c[0] for c in conds if c[1] is None]})
    res.sort(key=lambda r: (-r["score"], len(r["missing"]), -len(r["yes"])))
    return res


def measure_all(sv, st):
    for k in STD:
        sv.take(k, st)
    if st.fault == "cocked":
        for k in ("4AT", "4AR", "4AB", "4AL"):
            sv.take(k, st)
    if st.fault == "loose":
        for k in ("FOOT", "BASE", "4V", "4V", "4V", "4V"):
            sv.take(k, st)


# ----------------------------------------------------------------------
# self test - run in CI
# ----------------------------------------------------------------------
def self_test(verbose=True):
    import time
    t0 = time.time()
    fails = []
    expect = {"static": "Static unbalance", "couple": "Couple unbalance", "dynamic": "Dynamic unbalance",
              "overhung": "Overhung unbalance", "angular": "Angular misalignment",
              "parallel": "Parallel misalignment", "bent": "Bent shaft", "cocked": "Cocked bearing (4)",
              "loose": "Looseness", "resonance": "Resonance"}
    for fid, name, trains in FAULTS:
        for train in trains:
            st = Setup()
            st.train, st.fault = train, fid
            sv = Survey()
            measure_all(sv, st)
            if fid == "healthy":
                if sv.level(st)[1]:
                    fails.append("healthy machine reads as worth diagnosing")
                continue
            P_ = patterns(sv, analyse(sv), train)
            if not P_ or P_[0]["n"] != expect[fid]:
                fails.append("%s on %s ranks %r first" % (fid, train, P_[0]["n"] if P_ else None))
    # traps: the tape shifts every phase equally; acceleration leads by 90
    st = Setup()
    a = synth("3V", st, 7)["lag"]
    st.tape = 90.0
    b = synth("3V", st, 7)["lag"]
    st.tape = 0.0
    st.unit = "acc"
    c = synth("3V", st, 7)["lag"]
    if abs(sdiff(a + 90.0, b)) > 4 or abs(sdiff(a - 90.0, c)) > 4:
        fails.append("tape / unit shifts wrong: %.0f %.0f %.0f" % (a, b, c))
    # reversed driven axial sensors hide angular misalignment
    st = Setup()
    st.fault = "angular"
    st.axdir = "into"
    sv = Survey()
    measure_all(sv, st)
    d = sv.pair("2A", "3A")
    if d is None or abs(d) > 30:
        fails.append("reversed axial sensors should make 2A-3A read in phase")
    # weak readings scatter, strong ones do not
    st = Setup()
    sv = Survey()
    for _ in range(5):
        sv.take("3A", st)
        sv.take("3V", st)
    if not (sv.scatter("3A") > 40 and sv.scatter("3V") < 10):
        fails.append("scatter: weak %.0f, strong %.0f" % (sv.scatter("3A"), sv.scatter("3V")))
    dt = time.time() - t0
    if verbose:
        if fails:
            print("phase_engine self test FAILED:")
            for f in fails:
                print("  - " + f)
        else:
            print("phase_engine self test OK (%d faults, %.1f s)" % (len(FAULTS), dt))
    return fails


if __name__ == "__main__":
    import sys
    sys.exit(1 if self_test() else 0)
