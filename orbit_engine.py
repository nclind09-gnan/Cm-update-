"""
orbit_engine - shaft orbit and run-up / coast-down physics for the CM Toolkit
Simulation tools (Orbit and Resonance). Pure Python, no Kivy and no numpy, so
it runs anywhere, including the CI sanity check:  python orbit_engine.py

THE ROTOR
One rotor mass carried in fluid-film bearings. The support is stiffer in one
direction than the other (on most machines the vertical is stiffer than the
horizontal), so there are two closely spaced "split" criticals rather than
one. In each principal direction the response is that of a damped single
degree of freedom system, so everything that follows - elliptical 1X orbits,
phase rolling through 90 deg at a critical, 180 deg above it, reverse
precession between split criticals - comes out of the model rather than
being drawn in.

CONVENTIONS (API 670 and the usual Bently Nevada practice)
  - everything is viewed from the driver end
  - Y probe 45 deg left of vertical, X probe 45 deg right of vertical
  - Keyphasor probe at the top (vertical)
  - a probe reads positive when the shaft moves TOWARDS it
  - phase lag = degrees of shaft rotation from the Keyphasor event to the
    next positive peak of that probe's 1X signal
  - shaft locations (heavy spot, crack, glitch) are measured AGAINST the
    direction of rotation from the Keyphasor notch
  - amplitudes are micrometres peak-to-peak
Internally angles are ordinary maths angles: from the horizontal to the
right, counter-clockwise positive.
"""

import cmath
import math

from fault_engine import fft, Rand, TAU

SPR = 128            # samples per revolution
REVS = 32            # revolutions in the record used for filtering and spectra
KP_DEG = 90.0        # Keyphasor probe at the top
PROBE_DEG = {"X": 45.0, "Y": 135.0}
CLEARANCE = 100.0    # bearing radial clearance, um (200 um diametral)
WHIRL_RATIO = 0.46   # oil whirl runs at a little under half running speed
RUB_DEG = 120.0      # where the seal or bearing contact happens (upper left)


def _wrap360(a):
    a = math.fmod(a, 360.0)
    return a + 360.0 if a < 0 else a


def gain(r, zeta, kind):
    """Complex response of a damped SDOF at frequency ratio r.
    kind 'unb' : force grows with speed squared (unbalance), so the
                 response per unit eccentricity is r^2 / (1 - r^2 + 2 i z r)
    kind 'static': force of fixed size (crack, preload), response per unit
                 static deflection is 1 / (1 - r^2 + 2 i z r)"""
    d = complex(1.0 - r * r, 2.0 * zeta * r)
    return (r * r if kind == "unb" else 1.0) / d


# ----------------------------------------------------------------------
# settings
# ----------------------------------------------------------------------
class Rotor(object):
    """The machine: criticals, damping, support asymmetry, rotation."""

    def __init__(self):
        self.nc = 2400.0       # mean first critical, rpm
        self.split = 0.12      # (stiff - weak) / mean critical
        self.zeta = 0.12       # damping ratio; AF is about 1 / (2 zeta)
        self.axis_deg = 0.0    # direction of the weak (flexible) support axis
        self.rot = 1           # +1 counter-clockwise, -1 clockwise, from driver
        self.ecc = 15.0        # unbalance: um peak response far above critical
        self.hs_deg = 60.0     # heavy spot, deg against rotation from notch
        self.runout = 4.0      # slow roll runout (mechanical + electrical), um
        self.noise = 0.25      # um rms

    def crit_weak(self):
        return self.nc * (1.0 - self.split / 2.0)

    def crit_stiff(self):
        return self.nc * (1.0 + self.split / 2.0)

    def copy(self):
        r = Rotor()
        r.__dict__.update(self.__dict__)
        return r


def forced(rot, rpm, mult, amp, loc_deg, kind, stiff_scale=1.0):
    """Horizontal and vertical response phasors (um peak) to a force that is
    fixed in the shaft at location loc_deg and turns with it at mult x speed.

    h(t) = Re(Ph e^{i w t}),  v(t) = Re(Pv e^{i w t}),  w = mult x speed,
    with t = 0 at the Keyphasor event."""
    c = math.radians(KP_DEG) - rot.rot * math.radians(loc_deg)
    base = cmath.exp(1j * rot.rot * mult * c)
    fh = base
    fv = -1j * rot.rot * base
    # into the principal frame: p along the weak axis, q along the stiff one
    a = math.radians(rot.axis_deg)
    ca, sa = math.cos(a), math.sin(a)
    fp = fh * ca + fv * sa
    fq = -fh * sa + fv * ca
    w = mult * rpm
    gp = gain(w / rot.crit_weak(), rot.zeta, kind)
    gq = gain(w / rot.crit_stiff(), rot.zeta, kind) * stiff_scale
    p = amp * gp * fp
    q = amp * gq * fq
    return (mult, p * ca - q * sa, p * sa + q * ca)


def runout_at(rot, s):
    """Slow roll runout seen by a probe looking at shaft location s (rad,
    against rotation from the notch): a little mechanical 1X runout from an
    imperfect probe track, plus one electrical glitch."""
    if rot.runout <= 0:
        return 0.0
    g = math.radians(200.0)
    d = math.atan2(math.sin(s - g), math.cos(s - g))
    return rot.runout * (0.55 * math.cos(s - math.radians(40.0))
                         + 0.9 * math.exp(-0.5 * (d / math.radians(7.0)) ** 2))


# ----------------------------------------------------------------------
# orbit conditions
# ----------------------------------------------------------------------
CONDITIONS = [
    {"id": "unbalance", "name": "Unbalance", "rpm": 3600, "sev": 5,
     "note": "Mass unbalance turns with the shaft, so the force is pure 1X and always forward. The orbit is a 1X ellipse with one Keyphasor dot, and its shape and phase come entirely from where the running speed sits relative to the two split criticals.",
     "orbit": ["One Keyphasor dot, steady from revolution to revolution.",
               "Elliptical rather than circular: the support is stiffer one way than the other.",
               "Forward precession (blank then dot runs the same way as the shaft) - except on a lightly damped rotor between its split criticals.",
               "Filtered 1X and Direct orbits look almost the same - there is little else in the signal."],
     "phase": "Below the critical the high spot sits on the heavy spot. Through the critical the high spot falls 90 deg behind, and well above it 180 deg behind. That is why balancing a machine that runs above its critical means putting the weight close to where the vibration peak appears.",
     "try": "Drop the speed to the critical (2400 rpm) and watch the orbit grow and the phase swing. Then set support asymmetry to 20%, damping to 0.05 and speed to 2400 rpm: the 1X orbit turns reverse. Raise the damping again and it goes back to forward - reverse precession between split criticals only happens when the split is wide compared with the damping."},

    {"id": "preload", "name": "Misalignment / preload", "rpm": 3600, "sev": 6,
     "note": "Misalignment, a pulled bearing or a heavy gear load push the journal hard into one side of its bearing. The oil film there gets much stiffer, so motion in that direction is squeezed and the orbit flattens. The film is also nonlinear, which adds 2X.",
     "orbit": ["Flattened ellipse, then a banana, then a figure-eight as the preload rises.",
               "Often two Keyphasor dots on a figure-eight, because 2X is now strong.",
               "Part of the orbit can run in reverse precession at the inner loop.",
               "The 1X filtered orbit becomes a thin line along the soft direction."],
     "phase": "X and Y 1X phases move towards being 0 or 180 deg apart rather than 90: the motion is close to a straight line.",
     "try": "Raise severity in steps of 2 and watch ellipse to banana to figure-eight. Then switch the filter to 2X."},

    {"id": "rub", "name": "Partial rub", "rpm": 3600, "sev": 6,
     "note": "The shaft touches a seal or bearing for part of every revolution. Contact stiffens the rotor for a moment and the friction drags the surface backwards against rotation, so the orbit is clipped where it touches and gets kicked.",
     "orbit": ["A flattened or dented side where the contact is - the orbit cannot pass the seal.",
               "Sharp corners at the contact, meaning harmonics (2X, 3X).",
               "At heavier rub, 1/2X appears and the orbit shows TWO Keyphasor dots and an inner loop.",
               "Friction at contact pushes the precession towards reverse for a moment."],
     "phase": "The 1X phase becomes unsteady in a real machine (thermal bow from the rub point). Here, watch the harmonics in the full spectrum.",
     "try": "Set the filter to Not-1X to strip out the 1X and see what the rub is adding."},

    {"id": "crack", "name": "Cracked shaft", "rpm": 1200, "sev": 6,
     "note": "A transverse crack opens and closes once per revolution under gravity, so the shaft stiffness changes twice per revolution. That is a 2X force, and it is resonant when 2X equals the critical - at HALF the critical speed.",
     "orbit": ["Near half the critical speed: an inner loop, one Keyphasor dot, both 1X and 2X forward.",
               "Away from half critical the 2X falls back and the orbit looks like plain unbalance.",
               "The 1X vector also drifts as the crack grows (bow) - the trend that saves machines."],
     "phase": "Watch the 2X vector: it is the one that changes. A 2X peak in a run-up or coast-down at half the critical speed is the classic signature.",
     "try": "Move the speed above and below 1200 rpm (half of 2400) and watch the inner loop appear and vanish."},

    {"id": "whirl", "name": "Oil whirl", "rpm": 3800, "sev": 6,
     "note": "A lightly loaded journal lets the oil wedge drive it round the bearing at the average oil speed - a little under half running speed. The motion is self-excited, forward and nearly circular, and it is NOT locked to the shaft.",
     "orbit": ["A large loop with an inner loop at roughly 0.46X.",
               "About two Keyphasor dots per orbit cycle that wander round, because 0.46X is not a whole fraction.",
               "Forward precession.",
               "Filter to 1X and the whirl disappears; filter to Not-1X and it is nearly all that is left."],
     "phase": "There is no stable phase for the whirl component - it is not driven by the shaft. Only the small 1X still has a steady phase.",
     "try": "Raise the speed: the whirl frequency rises with it, until it meets the first critical and locks there. That is oil whip."},

    {"id": "whip", "name": "Oil whip", "rpm": 7000, "sev": 6,
     "note": "Once running speed passes about twice the first critical, the whirl frequency reaches the critical and locks there. The rotor now whirls at its own natural frequency, the amplitude grows to the bearing clearance, and it stops responding to speed.",
     "orbit": ["Very large, nearly circular forward orbit filling most of the bearing clearance.",
               "Keyphasor dots scattered, since the subsynchronous frequency is fixed while speed changes.",
               "The subsynchronous component no longer tracks speed - it sits at the first critical.",
               "Destructive. A trip, not a trend."],
     "phase": "The 1X is usually small by comparison. The danger is entirely in the subsynchronous component.",
     "try": "Lower the speed slowly: the frequency stays at the critical until speed falls below about twice it, then it starts tracking speed again as whirl."},
]
COND_BY_ID = dict((c["id"], c) for c in CONDITIONS)


class OrbitSettings(object):
    def __init__(self):
        self.cond = "unbalance"
        self.rpm = 3600.0
        self.sev = 5.0
        self.filt = "direct"      # direct | 1x | 2x | not1x
        self.revs = 4             # revolutions drawn on the orbit
        self.comp = False         # slow roll (waveform) compensation
        self.rotor = Rotor()


def _whirl_state(rot, rpm):
    """Frequency (rpm) of the fluid-induced instability, and how far into
    whip it is (0 = whirl tracking speed, 1 = fully locked at the critical)."""
    track = WHIRL_RATIO * rpm
    crit = rot.crit_weak()
    if track < crit:
        return track, 0.0
    return crit, min(1.0, (track - crit) / (0.25 * crit))


def components(st):
    """The shaft motion for this condition as (mult, Ph, Pv) phasors, plus
    any post-processing (rub contact). mult is in orders of running speed."""
    rot = st.rotor
    s = st.sev
    rpm = st.rpm
    comps = []
    rub = None
    c = st.cond
    ecc = rot.ecc
    if c == "unbalance":
        comps.append(forced(rot, rpm, 1, ecc * (0.25 + s / 6.0), rot.hs_deg, "unb"))
    elif c == "preload":
        # the loaded direction is squeezed: stiffness there climbs steeply
        comps.append(forced(rot, rpm, 1, ecc, rot.hs_deg, "unb",
                            stiff_scale=1.0 / (1.0 + 0.45 * s)))
        # nonlinear film: a 2X standing (not rotating) force along the load
        a1 = abs(comps[0][1]) + abs(comps[0][2])
        c2 = 0.07 * s * a1
        psi = -math.radians(min(90.0, max(0.0, (s - 3.0) * 13.0)))
        ax = math.radians(rot.axis_deg + 90.0)
        ph = c2 * cmath.exp(1j * psi)
        comps.append((2, ph * math.cos(ax), ph * math.sin(ax)))
    elif c == "rub":
        comps.append(forced(rot, rpm, 1, ecc * 1.4, rot.hs_deg, "unb"))
        rub = s
        if s >= 5:
            # partial rub above twice the critical: a forward 1/2X
            a1 = 0.5 * (abs(comps[0][1]) + abs(comps[0][2]))
            a = 0.07 * (s - 4.0) * a1
            ph = a * cmath.exp(1j * 0.7)
            comps.append((0.5, ph, -1j * rot.rot * ph))
    elif c == "crack":
        comps.append(forced(rot, rpm, 1, ecc * 0.5, rot.hs_deg, "unb"))
        # gravity opens and closes the crack: 2X stiffness force (static size)
        comps.append(forced(rot, rpm, 2, 0.9 * s, 150.0, "static"))
        # and the crack bows the shaft a little: extra 1X of static size
        comps.append(forced(rot, rpm, 1, 0.5 * s, 150.0, "static"))
    elif c in ("whirl", "whip"):
        comps.append(forced(rot, rpm, 1, ecc * 0.35, rot.hs_deg, "unb"))
        f_rpm, lock = _whirl_state(rot, rpm)
        a = CLEARANCE * (0.18 + 0.05 * s) * (1.0 + 0.9 * lock)
        a = min(a, 0.80 * CLEARANCE)
        ph = a * cmath.exp(1j * 1.9)
        # nearly circular, slightly squashed along the stiff axis
        comps.append((f_rpm / rpm, ph, -1j * rot.rot * ph * 0.88))
    return comps, rub


def _synth(st, comps, rub, n, f1):
    """Sample horizontal and vertical shaft motion and each probe's signal."""
    rot = st.rotor
    h = [0.0] * n
    v = [0.0] * n
    dt = 1.0 / (SPR * f1)
    for mult, ph, pv in comps:
        w = TAU * mult * f1 * dt
        for i in range(n):
            e = cmath.exp(1j * w * i)
            h[i] += (ph * e).real
            v[i] += (pv * e).real
    if rub is not None:
        # partial contact on one side: the stator stops the shaft going past
        # it, and friction drags the surface back against rotation
        ac = math.radians(RUB_DEG)
        ux, uy = math.cos(ac), math.sin(ac)
        tx, ty = -uy * rot.rot, ux * rot.rot
        dmax = max(h[i] * ux + v[i] * uy for i in range(n))
        lim = dmax * (1.0 - 0.055 * rub)
        for i in range(n):
            d = h[i] * ux + v[i] * uy
            if d > lim:
                ex = d - lim
                dd = lim + 0.12 * ex - d
                fr = -0.35 * ex
                h[i] += dd * ux + fr * tx
                v[i] += dd * uy + fr * ty
    return h, v


def compute_orbit(st):
    """Everything the Orbit screen shows, measured from the probe signals."""
    rot = st.rotor
    f1 = st.rpm / 60.0
    n = SPR * REVS
    comps, rub = components(st)
    h, v = _synth(st, comps, rub, n, f1)
    rnd = Rand(1234567)
    probes = {}
    raw = {}
    for name, deg in PROBE_DEG.items():
        a = math.radians(deg)
        ca, sa = math.cos(a), math.sin(a)
        off = rot.rot * math.radians(deg - KP_DEG)
        sig = [0.0] * n
        for i in range(n):
            s_loc = TAU * i / SPR - off
            ro = runout_at(rot, s_loc)
            sig[i] = h[i] * ca + v[i] * sa + ro + rot.noise * rnd.gauss()
            if st.comp:
                # waveform compensation: subtract the slow roll record
                sig[i] -= ro
        mean = sum(sig) / n
        sig = [x - mean for x in sig]
        raw[name] = sig
    # measured vectors (before the display filter)
    for name in PROBE_DEG:
        sig = raw[name]
        v1 = dft_order(sig, 1.0)
        v2 = dft_order(sig, 2.0)
        probes[name] = {
            "direct_pp": max(sig) - min(sig),
            "x1_pp": 2.0 * abs(v1), "x1_lag": _wrap360(-math.degrees(cmath.phase(v1))),
            "x2_pp": 2.0 * abs(v2), "x2_lag": _wrap360(-math.degrees(cmath.phase(v2))),
            "v1": v1, "v2": v2,
        }
    # display filter
    shown = {}
    for name in PROBE_DEG:
        sig = raw[name]
        if st.filt == "direct":
            out = sig
        elif st.filt == "1x":
            out = order_wave(probes[name]["v1"], 1.0, n)
        elif st.filt == "2x":
            out = order_wave(probes[name]["v2"], 2.0, n)
        else:
            w1 = order_wave(probes[name]["v1"], 1.0, n)
            out = [sig[i] - w1[i] for i in range(n)]
        shown[name] = out
    # rebuild the orbit in true orientation from the two probes (they are
    # 90 deg apart, so this is an exact rotation)
    ax, ay = math.radians(PROBE_DEG["X"]), math.radians(PROBE_DEG["Y"])
    oh = [shown["X"][i] * math.cos(ax) + shown["Y"][i] * math.cos(ay) for i in range(n)]
    ov = [shown["X"][i] * math.sin(ax) + shown["Y"][i] * math.sin(ay) for i in range(n)]

    fs = full_spectrum(raw["X"], raw["Y"], rot.rot)
    # 1X precession from the exact 1X forward / reverse circles
    fwd1, rev1 = fwd_rev(raw["X"], raw["Y"], 1.0, rot.rot)
    sub = None
    sub_mult = None
    for mult, ph, pv in comps:
        if mult < 0.9 and mult > 0.0:
            sub_mult = mult
    if sub_mult is not None:
        # measure it: the strongest forward or reverse line below 0.9X
        best = 0.0
        for k in range(len(fs["orders"])):
            o = fs["orders"][k]
            if 0.1 < abs(o) < 0.9 and fs["amp"][k] > best:
                best = fs["amp"][k]
                sub = (abs(o), fs["amp"][k], o * rot.rot > 0)
    return {
        "settings": st, "f1": f1, "n": n,
        "x": shown["X"], "y": shown["Y"], "oh": oh, "ov": ov,
        "probes": probes, "fs": fs,
        "fwd1": fwd1, "rev1": rev1,
        "sub": sub,
        "whirl": _whirl_state(rot, st.rpm) if st.cond in ("whirl", "whip") else None,
        "max_r": max(math.hypot(oh[i], ov[i]) for i in range(n)),
    }


def dft_order(sig, order):
    """Complex amplitude C of the component at `order` x speed, so that the
    component is Re(C e^{i w t}); exact for whole orders over whole revs."""
    n = len(sig)
    w = TAU * order / SPR
    acc = 0j
    for i in range(n):
        acc += sig[i] * cmath.exp(-1j * w * i)
    return 2.0 * acc / n


def order_wave(c, order, n):
    w = TAU * order / SPR
    return [(c * cmath.exp(1j * w * i)).real for i in range(n)]


def fwd_rev(x, y, order, rotdir):
    """Forward and reverse circle radii (um) of a component, from the X/Y
    pair. Y is 90 deg counter-clockwise of X, so x + i y turns
    counter-clockwise for a counter-clockwise motion."""
    n = len(x)
    w = TAU * order / SPR
    ccw = 0j
    cw = 0j
    for i in range(n):
        z = complex(x[i], y[i])
        e = cmath.exp(-1j * w * i)
        ccw += z * e
        cw += z / e
    ccw = abs(ccw) / n
    cw = abs(cw) / n
    return (ccw, cw) if rotdir > 0 else (cw, ccw)


def full_spectrum(x, y, rotdir, max_order=4.0):
    """Full (two-sided) spectrum from the X/Y pair, Hanning windowed.
    Positive orders are forward (with rotation), negative are reverse.
    Amplitude is the circle's diameter, um pp."""
    n = len(x)
    re = [0.0] * n
    im = [0.0] * n
    for i in range(n):
        wnd = 0.5 * (1.0 - math.cos(TAU * i / n))
        re[i] = x[i] * wnd
        im[i] = y[i] * wnd
    fft(re, im)
    kmax = int(max_order * REVS)
    orders = []
    amp = []
    for k in range(-kmax, kmax + 1):
        j = k % n
        a = 2.0 * math.hypot(re[j], im[j]) / n * 2.0
        o = k / float(REVS)
        orders.append(o if rotdir > 0 else -o)
        amp.append(a)
    if rotdir < 0:
        orders.reverse()
        amp.reverse()
    return {"orders": orders, "amp": amp}


# ----------------------------------------------------------------------
# run-up / coast-down sweep (Bode, polar and shaft shape)
# ----------------------------------------------------------------------
# The rotor in the Resonance tool is a flexible shaft between two bearings,
# described by its first two bending modes. Like the classic pinned-pinned
# beam, mode i has the shape sin(i pi x) along the span (x = 0 and 1 at the
# bearings): mode 1 a single bow, mode 2 an S with a node at midspan. Each
# mode is a damped SDOF, split into weak and stiff directions like the
# Orbit rotor. An unbalance at xu excites mode i in proportion to
# sin(i pi xu); a probe at xp sees it in proportion to sin(i pi xp).

def mode_shape(i, x):
    return math.sin(i * math.pi * x)


class SweepSettings(object):
    def __init__(self):
        self.rotor = Rotor()
        self.rotor.runout = 4.0
        self.rotor.ecc = 11.0      # peaks near 50-100 um pp at the criticals
        self.nc2 = 7200.0          # second critical (rotor.nc is the first)
        self.xu = 0.3              # unbalance position, fraction of span
        self.xp = 0.8              # probe position, fraction of span
        self.max_rpm = 9000.0
        self.slow_roll = 300.0     # rpm used for the slow roll vector
        self.probe = "X"
        self.comp = True           # subtract the slow roll vector
        self.op_min = 3300.0
        self.op_max = 3900.0       # maximum continuous speed
        self.points = 240


def modal(st, rpm):
    """Horizontal and vertical modal response (um peak per unit mode shape)
    of modes 1 and 2 at this speed."""
    rot = st.rotor
    c = math.radians(KP_DEG) - rot.rot * math.radians(rot.hs_deg)
    base = cmath.exp(1j * rot.rot * c)
    fh, fv = base, -1j * rot.rot * base
    out = []
    for i, nc in ((1, rot.nc), (2, st.nc2)):
        ex = rot.ecc * mode_shape(i, st.xu)
        gw = gain(rpm / (nc * (1.0 - rot.split / 2.0)), rot.zeta, "unb")
        gs = gain(rpm / (nc * (1.0 + rot.split / 2.0)), rot.zeta, "unb")
        out.append((ex * gw * fh, ex * gs * fv))
    return out


def response_at(st, rpm, x, md=None):
    """h and v response phasors at position x along the span."""
    md = md or modal(st, rpm)
    h = v = 0j
    for i, (qh, qv) in enumerate(md):
        s = mode_shape(i + 1, x)
        h += qh * s
        v += qv * s
    return h, v


def project(h, v, probe):
    a = math.radians(PROBE_DEG[probe])
    return h * math.cos(a) + v * math.sin(a)


def shape_at(st, rpm, points=41):
    """The deflected shape along the span in the probe's direction, as
    phasors, plus how much each mode contributes."""
    md = modal(st, rpm)
    d = []
    for k in range(points):
        h, v = response_at(st, rpm, k / float(points - 1), md)
        d.append(project(h, v, st.probe))
    q1 = abs(project(md[0][0], md[0][1], st.probe))
    q2 = abs(project(md[1][0], md[1][1], st.probe))
    return {"d": d, "q1": q1, "q2": q2}


def _measure(st, rpm, probe, rnd, spr=32, revs=4):
    """One probe's 1X vector at one speed, by DFT over whole revolutions,
    with runout and noise in the signal."""
    rot = st.rotor
    deg = PROBE_DEG[probe]
    off = rot.rot * math.radians(deg - KP_DEG)
    h, v = response_at(st, rpm, st.xp)
    p = project(h, v, probe)
    n = spr * revs
    acc = 0j
    w = TAU / spr
    for i in range(n):
        e = cmath.exp(1j * w * i)
        x = (p * e).real + runout_at(rot, w * i - off) + rot.noise * rnd.gauss()
        acc += x / e
    return 2.0 * acc / n


def sweep(st):
    """A coast-down measured the way a monitoring system does it: at each
    speed the probe signal is sampled over whole revolutions (runout and
    noise included) and the 1X vector is extracted by DFT."""
    rnd = Rand(97531)
    lo, hi = st.slow_roll, st.max_rpm
    speeds = [lo + (hi - lo) * k / float(st.points - 1) for k in range(st.points)]
    vecs = [_measure(st, rpm, st.probe, rnd) for rpm in speeds]
    slow = vecs[0]
    if st.comp:
        vecs = [c - slow for c in vecs]
    amp = [2.0 * abs(c) for c in vecs]
    lag = [_wrap360(-math.degrees(cmath.phase(c))) for c in vecs]
    if st.comp:
        # the compensated slow roll vector is zero by construction, so its
        # phase means nothing: carry the next point's back to it
        lag[0] = lag[1]
    un = [lag[0]]
    for k in range(1, len(lag)):
        d = lag[k] - (un[-1] % 360.0)
        if d > 180:
            d -= 360
        elif d < -180:
            d += 360
        un.append(un[-1] + d)
    res = {"rpm": speeds, "amp": amp, "lag": un, "vec": vecs,
           "slow": slow, "settings": st}
    res.update(analyse(res, st))
    # the largest bend anywhere on the shaft at any speed: the shaft plot is
    # drawn to this one scale, so its swing follows the real amplitude
    mx, at = 0.0, speeds[0]
    for rpm in speeds[::2]:
        md = modal(st, rpm)
        for k in range(31):
            h, v = response_at(st, rpm, k / 30.0, md)
            a = abs(project(h, v, st.probe))
            if a > mx:
                mx, at = a, rpm
    res["shape_max"] = mx
    res["shape_max_rpm"] = at
    # heavy spot to high spot angle over the coast-down, unwrapped
    lags, rmax, prev = [], 0.0, None
    for rpm in speeds:
        sp = spots_at(st, rpm)
        lg = sp["lag"]
        if prev is not None:
            d = lg - (prev % 360.0)
            if d > 180:
                d -= 360
            elif d < -180:
                d += 360
            lg = prev + d
        lags.append(lg)
        prev = lg
        rmax = max(rmax, math.hypot(abs(sp["h"]), abs(sp["v"])))
    res["spot_lag"] = lags
    res["spot_rmax"] = rmax
    return res


def spots_at(st, rpm):
    """Heavy spot and high spot at the unbalance plane. The shaft whirls on
    a 1X orbit; its forward-whirling part is a circle turning with the shaft,
    and the point of the rim facing outward along it is the high spot.
    lag = degrees the high spot trails the heavy spot, against rotation
    (0 together, 90 at a critical, about 180 well above it)."""
    rot = st.rotor
    h, v = response_at(st, rpm, st.xu)
    if rot.rot > 0:
        fwd = (h + 1j * v) / 2.0
    else:
        fwd = (h.conjugate() + 1j * v.conjugate()) / 2.0
    c = math.radians(KP_DEG) - rot.rot * math.radians(rot.hs_deg)
    lag = _wrap360(rot.rot * math.degrees(c - cmath.phase(fwd)))
    return {"h": h, "v": v, "lag": lag, "fwd": abs(fwd)}


def orbit_at(st, rpm):
    """1X orbit at the probe position from both probes, in the dictionary
    shape OrbitChart draws. Compensated the same way as the sweep."""
    rnd = Rand(24680)
    cx = _measure(st, rpm, "X", rnd)
    cy = _measure(st, rpm, "Y", rnd)
    if st.comp:
        cx -= _measure(st, st.slow_roll, "X", rnd)
        cy -= _measure(st, st.slow_roll, "Y", rnd)
    ax, ay = math.radians(PROBE_DEG["X"]), math.radians(PROBE_DEG["Y"])
    oh, ov = [], []
    for i in range(SPR + 1):
        e = cmath.exp(1j * TAU * i / SPR)
        x, y = (cx * e).real, (cy * e).real
        oh.append(x * math.cos(ax) + y * math.cos(ay))
        ov.append(x * math.sin(ax) + y * math.sin(ay))
    ccw, cw = abs(cx + 1j * cy) / 2.0, abs(cx - 1j * cy) / 2.0
    fwd, rev = (ccw, cw) if st.rotor.rot > 0 else (cw, ccw)

    class _S(object):
        pass
    s = _S()
    s.rotor = st.rotor
    probes = {}
    for name, c in (("X", cx), ("Y", cy)):
        probes[name] = {"x1_pp": 2.0 * abs(c), "x1_lag": _wrap360(-math.degrees(cmath.phase(c)))}
    return {"oh": oh, "ov": ov, "n": SPR + 1, "settings": s, "probes": probes,
            "fwd1": fwd, "rev1": rev,
            "max_r": max(math.hypot(oh[i], ov[i]) for i in range(SPR + 1))}


def analyse(res, st):
    """Every critical read off the measured Bode data the way an analyst
    would: find the peaks, treat a close pair as one split critical, then
    the half power AF and the separation margin for each."""
    rpm, amp = res["rpm"], res["amp"]
    n = len(rpm)
    sm = []
    for k in range(n):
        seg = amp[max(0, k - 1):k + 2]
        sm.append(sum(seg) / len(seg))
    gmax = max(sm[3:])
    win = max(2, n // 40)
    peaks = []
    for k in range(3, n - 1):
        lo_k, hi_k = max(0, k - win), min(n, k + win + 1)
        if sm[k] >= max(sm[lo_k:hi_k]) and sm[k] >= 0.12 * gmax:
            if peaks:
                p0 = peaks[-1]
                dip = min(sm[p0:k + 1])
                if dip > 0.92 * min(sm[p0], sm[k]):
                    if sm[k] > sm[p0]:
                        peaks[-1] = k
                    continue
            peaks.append(k)
    # peaks within 30 % of each other in speed are one split critical
    clusters = []
    for p in peaks:
        if clusters and rpm[p] / rpm[clusters[-1][-1]] < 1.3:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    mid = 0.5 * (st.op_min + st.op_max)
    crits = []
    for ci, c in enumerate(clusters):
        top = max(c, key=lambda q: amp[q])
        left, right = 0, n - 1
        if ci > 0:
            a0 = clusters[ci - 1][-1]
            left = min(range(a0, c[0] + 1), key=lambda j: sm[j])
        if ci < len(clusters) - 1:
            b0 = clusters[ci + 1][0]
            right = min(range(c[-1], b0 + 1), key=lambda j: sm[j])
        pk = amp[top]
        hp = pk / math.sqrt(2.0)
        n1 = n2 = None
        for j in range(top, left, -1):
            if amp[j - 1] < hp <= amp[j]:
                n1 = rpm[j - 1] + (rpm[j] - rpm[j - 1]) * (hp - amp[j - 1]) / (amp[j] - amp[j - 1])
                break
        for j in range(top, right):
            if amp[j + 1] < hp <= amp[j]:
                n2 = rpm[j] + (rpm[j + 1] - rpm[j]) * (amp[j] - hp) / (amp[j] - amp[j + 1])
                break
        split = len(c) > 1
        af = rpm[top] / (n2 - n1) if (not split and n1 is not None and n2 is not None and n2 > n1) else None
        why = ""
        if split:
            why = "split"
        elif n1 is None or n2 is None:
            edge = top >= n - 3 or (n2 is None and right == n - 1) or (n1 is None and left == 0)
            why = "edge" if edge else "overlap"
        ncm = min([rpm[q] for q in c], key=lambda p: abs(p - mid))
        cr = {"peaks": [rpm[q] for q in c], "nc": rpm[top], "peak": pk, "lag": res["lag"][top],
              "n1": n1, "n2": n2, "af": af, "split": split, "why": why, "nc_margin": ncm,
              "edge": top >= n - 3}
        # an AF that cannot be read is never assumed critically damped
        cr.update(margin(ncm, af, st.op_min, st.op_max, split or why in ("overlap", "edge")))
        crits.append(cr)
    # label each critical with its mode: two peaks are mode 1 then 2, a lone
    # peak goes to the nearer design critical
    if len(crits) == 1:
        c = crits[0]
        c["mode"] = 1 if abs(math.log(c["nc"] / st.rotor.nc)) <= abs(math.log(c["nc"] / st.nc2)) else 2
    else:
        for i, c in enumerate(crits):
            c["mode"] = i + 1
    crits = crits[:2]
    by_mode = [None, None]
    for c in crits:
        by_mode[c["mode"] - 1] = c
    out = {"crits": crits, "by_mode": by_mode, "ok": all(c["sm_ok"] for c in crits)}
    # the first critical found, under the old single-critical names
    if crits:
        c = crits[0]
        out.update({"nc": c["nc"], "peak": c["peak"], "af": c["af"], "n1": c["n1"], "n2": c["n2"],
                    "lag_at_nc": c["lag"], "split_seen": c["split"], "peaks": c["peaks"],
                    "peak_at_edge": c["edge"], "nc_margin": c["nc_margin"]})
    return out


def missing_reason(st, i):
    """Why mode i+1 shows no critical in this coast-down."""
    nc = st.rotor.nc if i == 0 else st.nc2
    if abs(mode_shape(i + 1, st.xu)) < 0.1:
        return "node"
    if abs(mode_shape(i + 1, st.xp)) < 0.1:
        return "probe"
    if nc * (1.0 - st.rotor.split / 2.0) > 0.95 * st.max_rpm:
        return "above"
    return "damped"


def antiresonance(st):
    """True when probe and unbalance are on the same side of mode 2's node:
    the modes arrive in step and cancel between the criticals."""
    return (mode_shape(1, st.xu) * mode_shape(1, st.xp) *
            mode_shape(2, st.xu) * mode_shape(2, st.xp)) > 0


def margin(nc, af, op_min, op_max, unmeasured=False):
    """Separation margin check, after API 612 / 617.
    AF < 2.5          : critically damped, no margin required
    2.5 <= AF <= 3.55 : 5 % below minimum speed, 15 % above max continuous
    AF > 3.55         : rises with AF to at most 16 % below / 26 % above
                        (the exact curve differs between editions, so the
                        upper limits are used here - the conservative choice)"""
    if unmeasured:
        # no valid AF: it cannot be called critically damped, so apply the
        # largest margin rather than none
        req_lo, req_hi = 16.0, 26.0
        band = "AF not measurable here - largest margin applied (16% below / 26% above)"
    elif af is None or af < 2.5:
        req_lo, req_hi = 0.0, 0.0
        band = "AF below 2.5 - critically damped, no margin required"
    elif af <= 3.55:
        req_lo, req_hi = 5.0, 15.0
        band = "AF 2.5 to 3.55 - needs 5% below min / 15% above max"
    else:
        req_lo, req_hi = 16.0, 26.0
        band = "AF above 3.55 - needs up to 16% below min / 26% above max"
    if op_min <= nc <= op_max:
        sm, side, ok = 0.0, "inside", req_lo == 0 and req_hi == 0
    elif nc < op_min:
        sm = 100.0 * (op_min - nc) / op_min
        side, ok = "below", sm >= req_lo
    else:
        sm = 100.0 * (nc - op_max) / op_max
        side, ok = "above", sm >= req_hi
    return {"sm": sm, "sm_side": sm and side or side, "req_lo": req_lo,
            "req_hi": req_hi, "sm_ok": ok, "af_band": band}


# ----------------------------------------------------------------------
# self test - run in CI
# ----------------------------------------------------------------------
def self_test(verbose=True):
    import time
    t0 = time.time()
    fails = []

    def near(a, b, tol):
        return abs(a - b) <= tol

    def angdiff(a, b):
        return abs((a - b + 180.0) % 360.0 - 180.0)

    # 1. well below the critical the high spot is the heavy spot
    st = OrbitSettings()
    st.rotor.runout = 0.0
    st.rotor.noise = 0.0
    st.rotor.split = 0.0
    st.rpm = 300.0
    r = compute_orbit(st)
    for name, deg in PROBE_DEG.items():
        want = _wrap360(st.rotor.hs_deg + st.rotor.rot * (deg - KP_DEG))
        got = r["probes"][name]["x1_lag"]
        if angdiff(got, want) > 3.0:
            fails.append("low speed %s phase %.1f, heavy spot geometry says %.1f" % (name, got, want))

    # 2. at the critical the lag is 90 deg more, far above it 180 deg more
    base = r["probes"]["X"]["x1_lag"]
    for rpm, extra, tol in ((2400.0, 90.0, 4.0), (24000.0, 180.0, 4.0)):
        st.rpm = rpm
        rr = compute_orbit(st)
        got = rr["probes"]["X"]["x1_lag"]
        if angdiff(got, base + extra) > tol:
            fails.append("phase at %.0f rpm %.1f, expected %.1f" % (rpm, got, base + extra))

    # 3. isotropic support -> 1X orbit is a forward circle, X and Y 90 deg apart
    st.rpm = 3600.0
    rr = compute_orbit(st)
    if rr["rev1"] > 0.02 * rr["fwd1"]:
        fails.append("isotropic rotor not circular: rev/fwd %.3f" % (rr["rev1"] / rr["fwd1"]))
    dphi = angdiff(rr["probes"]["Y"]["x1_lag"], rr["probes"]["X"]["x1_lag"])
    if not near(dphi, 90.0, 2.0):
        fails.append("X/Y 1X phase difference %.1f, not 90" % dphi)
    # 1X amplitude equals the analytic response
    _m, ph, pv = forced(st.rotor, 3600.0, 1, st.rotor.ecc * (0.25 + st.sev / 6.0),
                        st.rotor.hs_deg, "unb")
    want = 2.0 * abs(ph * math.cos(math.radians(45)) + pv * math.sin(math.radians(45)))
    if not near(rr["probes"]["X"]["x1_pp"], want, 0.01 * want):
        fails.append("1X amplitude %.2f, analytic %.2f" % (rr["probes"]["X"]["x1_pp"], want))

    # 4. reverse precession between split criticals, forward outside them
    st = OrbitSettings()
    st.rotor.runout = 0.0
    st.rotor.noise = 0.0
    st.rotor.split = 0.25
    st.rotor.zeta = 0.04
    for rpm, want_fwd in ((1200.0, True), (2400.0, False), (5000.0, True)):
        st.rpm = rpm
        rr = compute_orbit(st)
        if (rr["fwd1"] > rr["rev1"]) != want_fwd:
            fails.append("precession at %.0f rpm wrong (fwd %.2f rev %.2f)" % (rpm, rr["fwd1"], rr["rev1"]))

    # 5. whirl tracks 0.46X, whip locks at the weak critical
    st = OrbitSettings()
    st.rotor.runout = 0.0
    st.cond = "whirl"
    st.rpm = 3800.0
    rr = compute_orbit(st)
    if rr["sub"] is None or not near(rr["sub"][0], WHIRL_RATIO, 0.04) or not rr["sub"][2]:
        fails.append("whirl measured at %r" % (rr["sub"],))
    st.cond = "whip"
    for rpm in (6500.0, 8000.0):
        st.rpm = rpm
        rr = compute_orbit(st)
        f = rr["sub"][0] * rpm if rr["sub"] else 0.0
        if not near(f, st.rotor.crit_weak(), 0.04 * st.rotor.crit_weak()):
            fails.append("whip at %.0f rpm measured %.0f cpm, critical %.0f" % (rpm, f, st.rotor.crit_weak()))
        if rr["max_r"] > CLEARANCE:
            fails.append("whip orbit %.0f um exceeds clearance" % rr["max_r"])

    # 6. crack 2X peaks near half the critical
    st = OrbitSettings()
    st.rotor.runout = 0.0
    st.rotor.noise = 0.0
    st.cond = "crack"
    best = (0.0, 0.0)
    for rpm in range(600, 2401, 50):
        st.rpm = float(rpm)
        a = compute_orbit(st)["probes"]["X"]["x2_pp"]
        if a > best[0]:
            best = (a, rpm)
    lo, hi = st.rotor.crit_weak() / 2.0, st.rotor.crit_stiff() / 2.0
    if not (lo - 60 <= best[1] <= hi + 60):
        fails.append("crack 2X peaks at %d rpm, half critical %.0f-%.0f" % (best[1], lo, hi))

    # 7. slow roll compensation removes runout
    st = OrbitSettings()
    st.rotor.noise = 0.0
    st.rotor.runout = 8.0
    st.sev = 0.0
    st.rotor.ecc = 0.0
    st.comp = False
    a = compute_orbit(st)["probes"]["X"]["direct_pp"]
    st.comp = True
    b = compute_orbit(st)["probes"]["X"]["direct_pp"]
    if a < 6.0 or b > 0.01:
        fails.append("compensation: raw %.2f um, compensated %.3f um" % (a, b))

    # rub at severity 6 shows a clear 1/2X (two Keyphasor positions)
    st = OrbitSettings()
    st.cond = "rub"
    st.sev = 6.0
    rr = compute_orbit(st)
    if rr["sub"] is None or not near(rr["sub"][0], 0.5, 0.02) or \
            rr["sub"][1] < 0.1 * rr["probes"]["X"]["x1_pp"]:
        fails.append("rub 1/2X too weak: %r" % (rr["sub"],))

    # 8. preload makes a figure eight with strong 2X
    st = OrbitSettings()
    st.rotor.runout = 0.0
    st.cond = "preload"
    st.sev = 9.0
    rr = compute_orbit(st)
    p = rr["probes"]["X"]
    if p["x2_pp"] < 0.25 * p["x1_pp"]:
        fails.append("preload 2X only %.2f of 1X" % (p["x2_pp"] / p["x1_pp"]))

    # 9. Bode, first critical alone (second pushed beyond the sweep):
    # measured critical, 90 deg at the peak, AF = 1 / 2 zeta
    sw = SweepSettings()
    sw.rotor.split = 0.0
    sw.rotor.zeta = 0.1
    sw.rotor.noise = 0.05
    sw.nc2 = 40000.0
    sw.max_rpm = 6000.0
    sw.points = 400
    res = sweep(sw)
    if not near(res["nc"], sw.rotor.nc, 0.03 * sw.rotor.nc):
        fails.append("Bode critical %.0f rpm, model %.0f" % (res["nc"], sw.rotor.nc))
    if res["af"] is None or not near(res["af"], 1.0 / (2 * sw.rotor.zeta), 0.6):
        fails.append("AF %.2f, expected about %.2f" % (res["af"] or 0, 1.0 / (2 * sw.rotor.zeta)))
    geo = _wrap360(sw.rotor.hs_deg + sw.rotor.rot * (PROBE_DEG[sw.probe] - KP_DEG))
    roll = (res["lag_at_nc"] - geo) % 360.0
    if not near(roll, 90.0, 8.0):
        fails.append("phase roll to the critical %.1f deg, expected 90" % roll)

    # 10. two criticals: both found near the model, lag rolls about 360 deg
    sw = SweepSettings()
    sw.rotor.split = 0.0
    sw.rotor.noise = 0.05
    res = sweep(sw)
    bm = res["by_mode"]
    if not (bm[0] and bm[1]):
        fails.append("two criticals expected, found %r" % [c["nc"] for c in res["crits"]])
    else:
        if not near(bm[0]["nc"], sw.rotor.nc, 0.06 * sw.rotor.nc) or not near(bm[1]["nc"], sw.nc2, 0.06 * sw.nc2):
            fails.append("criticals at %.0f / %.0f, model %.0f / %.0f" % (bm[0]["nc"], bm[1]["nc"], sw.rotor.nc, sw.nc2))
    total = res["lag"][-1] - res["lag"][3]
    if not near(total, 360.0, 50.0):
        fails.append("phase roll over both criticals %.0f deg, expected about 360" % total)
    # probe and unbalance on the same side of the node: antiresonance, the
    # phase comes back and the total roll is about 180
    sw.xp = 0.2
    res = sweep(sw)
    total = res["lag"][-1] - res["lag"][3]
    if not antiresonance(sw) or not near(total, 180.0, 50.0):
        fails.append("antiresonance case rolls %.0f deg, expected about 180" % total)
    # unbalance or probe at midspan (mode 2 node): only one critical shows
    for attr in ("xu", "xp"):
        sw = SweepSettings()
        sw.rotor.noise = 0.05
        setattr(sw, attr, 0.5)
        res = sweep(sw)
        if res["by_mode"][1] is not None or res["by_mode"][0] is None:
            fails.append("%s at midspan should hide the 2nd critical" % attr)
        if missing_reason(sw, 1) != ("node" if attr == "xu" else "probe"):
            fails.append("missing reason for %s at midspan wrong" % attr)
    # the second critical too close to the operating range fails its margin
    sw = SweepSettings()
    sw.nc2 = 4300.0
    res = sweep(sw)
    if res["ok"] or res["by_mode"][1] is None or res["by_mode"][1]["sm_ok"]:
        fails.append("2nd critical close to the range should fail the margin")
    # split criticals on the probe that sees both directions: two humps, no AF
    sw = SweepSettings()
    sw.probe = "Y"
    sw.rotor.noise = 0.0
    res = sweep(sw)
    if not res["split_seen"] or res["af"] is not None or res["crits"][0]["req_lo"] != 16.0:
        fails.append("Y probe split first critical not handled: %r" % (res["peaks"],))
    sw.probe = "X"
    res = sweep(sw)
    if res["split_seen"] or res["af"] is None:
        fails.append("X probe single peak mis-read as split")
    # the shaft shape: mode 2 has a node at midspan and dominates near nc2
    sw = SweepSettings()
    sh = shape_at(sw, sw.nc2)
    if not (sh["q2"] > 3 * sh["q1"] and abs(sh["d"][20]) < 0.35 * max(abs(x) for x in sh["d"])):
        fails.append("shape at the 2nd critical is not an S with a still middle")
    sh = shape_at(sw, sw.rotor.nc)
    if not sh["q1"] > 3 * sh["q2"]:
        fails.append("shape at the 1st critical is not a bow")
    # heavy spot vs high spot at the unbalance plane (unbalance at midspan, so
    # only the first mode acts): together, 90 deg at the critical, ~180 above
    sw2 = SweepSettings()
    sw2.xu = 0.5
    sw2.rotor.split = 0.0
    for rpm, want, tol in ((300.0, 0.0, 6.0), (sw2.rotor.nc, 90.0, 6.0), (3.0 * sw2.rotor.nc, 180.0, 15.0)):
        lg = spots_at(sw2, rpm)["lag"]
        if abs((lg - want + 180.0) % 360.0 - 180.0) > tol:
            fails.append("high spot lag at %.0f rpm %.0f deg, expected about %.0f" % (rpm, lg, want))
    # one scale for the coast-down: far from a critical the bend is small
    res = sweep(sw)
    low = max(abs(x) for x in shape_at(sw, 1000.0)["d"])
    if not (res["shape_max"] > 0 and low < 0.1 * res["shape_max"]):
        fails.append("shaft bend at 1000 rpm is %.0f%% of the maximum" % (100 * low / max(res["shape_max"], 1e-9)))
    # whip never exceeds the bearing clearance at any speed
    st = OrbitSettings()
    st.cond = "whip"
    st.sev = 10.0
    for rpm in (6000.0, 9000.0, 12000.0):
        st.rpm = rpm
        if compute_orbit(st)["max_r"] > CLEARANCE:
            fails.append("whip at %.0f rpm passes the clearance" % rpm)
    # separation margin arithmetic
    m = margin(2400.0, 5.0, 3300.0, 3900.0)
    if not (near(m["sm"], 100 * 900 / 3300.0, 0.01) and m["sm_ok"] and m["req_lo"] == 16.0):
        fails.append("separation margin arithmetic %r" % m)
    m = margin(2400.0, 2.0, 2200.0, 2600.0)
    if not m["sm_ok"]:
        fails.append("critically damped critical inside range should pass")

    dt = time.time() - t0
    if verbose:
        if fails:
            print("orbit_engine self test FAILED:")
            for f in fails:
                print("  - " + f)
        else:
            print("orbit_engine self test OK (%d conditions, %.1f s)" % (len(CONDITIONS), dt))
    return fails


if __name__ == "__main__":
    import sys
    sys.exit(1 if self_test() else 0)
