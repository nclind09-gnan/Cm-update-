"""
bearing_engine - the maths behind the CM Toolkit Bearing Defect Lab.
Pure Python, no Kivy and no numpy:  python bearing_engine.py  runs the self
test (used by the CI sanity check).

WHAT IS SIMULATED
-----------------
A rolling element bearing with a local defect (a spall) on the outer race,
the inner race, one rolling element, or the cage, at one of five wear stages
from healthy to end of life. The signal is built the way the physics makes
it, so the textbook signatures come out of the arithmetic instead of being
drawn in:

  * every time a rolling element meets the defect there is a short impact.
    An impact is far too short to show at the defect frequency itself; what
    it does is ring the bearing housing (and the sensor mount) at its
    natural frequency, a decaying burst a few milliseconds long:

        a(t) = A_k exp(-zeta w_r t) sin(w_d t),   w_d = w_r sqrt(1 - zeta^2)

  * the impacts repeat at the defect frequency (BPFO, BPFI, 2 x BSF, FTF),
    and their strength follows the load the element carries at that moment.
    The load around the bearing is the Stribeck distribution

        q(psi) = q_max (1 - (1 - cos psi) / (2 eps)) ^ n,   n = 1.5 ball, 1.1 roller

    so an outer race defect (fixed in the load zone) hits evenly, an inner
    race defect (turning with the shaft) is strong only while it passes
    through the load zone - amplitude modulation at 1X - and a damaged ball
    is modulated by the cage at FTF;

  * the rolling elements slip, so the impact spacing jitters by a fraction of
    a percent. That is why real defect harmonics smear out higher up, and
    why the measured defect frequency sits a little below the calculated one;

  * rolling noise, the resonance "haystack" of later stages, and end of life
    broadband noise are added as shaped random spectra;

  * the accelerometer mount is a low pass filter. A handheld probe cannot
    pass the resonance band, so the envelope loses the defect.

Envelope (demodulation) analysis then does what a data collector does:
band pass around the resonance, take the magnitude of the analytic signal
(Hilbert transform) and analyse that envelope. The repetition rate of the
impacts - the defect frequency - appears there even when the ordinary
velocity spectrum shows nothing at all.

The whole chain runs on a 16384 sample record at 12.8 kHz (F-max 5 kHz,
6400 lines, 0.78 Hz resolution, 1.28 s), a handful of FFTs per update.
"""

import math

from fault_engine import fft, ifft, Rand

TAU = 2.0 * math.pi
G = 9.80665

FS = 12800.0
N = 16384
FMAX = 5000.0
LINES = 6400

# ----------------------------------------------------------------------
# geometry
# ----------------------------------------------------------------------
# typical dimensions, mm. The first five match the Fault Signature tool.
PRESETS = [
    {"id": "6205", "name": "6205 deep groove ball", "n": 9, "bd": 7.94, "pd": 39.04, "th": 0.0, "roller": False},
    {"id": "6308", "name": "6308 deep groove ball", "n": 8, "bd": 15.08, "pd": 65.0, "th": 0.0, "roller": False},
    {"id": "6316", "name": "6316 deep groove ball", "n": 8, "bd": 25.4, "pd": 122.5, "th": 0.0, "roller": False},
    {"id": "NU314", "name": "NU314 cylindrical roller", "n": 13, "bd": 22.0, "pd": 107.5, "th": 0.0, "roller": True},
    {"id": "22220", "name": "22220 spherical roller", "n": 17, "bd": 20.0, "pd": 150.0, "th": 10.0, "roller": True},
    {"id": "7310", "name": "7310 angular contact (40 deg)", "n": 12, "bd": 17.46, "pd": 80.0, "th": 40.0, "roller": False},
]

LOCATIONS = [
    ("outer", "Outer race"),
    ("inner", "Inner race"),
    ("ball", "Rolling element"),
    ("cage", "Cage"),
]
LOC_NAME = dict(LOCATIONS)

STAGE_NAMES = ["Healthy", "Stage 1", "Stage 2", "Stage 3", "Stage 4"]
STAGE_TITLES = [
    "Healthy bearing",
    "Stage 1 - sub-surface fatigue, ultrasonic only",
    "Stage 2 - small defect rings the resonance",
    "Stage 3 - defect frequencies appear in velocity",
    "Stage 4 - end of life, random noise takes over",
]

MOUNTS = [
    ("stud", "Stud mount", 12000.0, 4.0),
    ("magnet", "Flat magnet", 7000.0, 3.0),
    ("curved", "Two-rail magnet", 2800.0, 2.5),
    ("hand", "Handheld probe", 1100.0, 1.6),
]
MOUNT_BY_ID = dict((m[0], m) for m in MOUNTS)

ENV_BANDS = [
    ("auto", "Around resonance"),
    ("wide", "500 Hz - 5 kHz"),
    ("low", "10 - 500 Hz (wrong)"),
]
ENV_FMAX = [("auto", "Auto"), ("250", "250 Hz"), ("500", "500 Hz"), ("1000", "1000 Hz"), ("2000", "2000 Hz")]

# colours shared with the Bearing Freq tab so a line reads the same in both
DEFECT_HEX = {"FTF": "7C3AED", "BSF": "0891B2", "2xBSF": "0E7490", "BPFO": "D97706",
              "BPFI": "DC2626", "1X": "334155"}


def orders_from_geometry(n, bd, pd, th_deg):
    """Defect frequencies as multiples of shaft speed (outer race fixed,
    inner race turning)."""
    r = (bd / pd) * math.cos(math.radians(th_deg))
    return {
        "FTF": 0.5 * (1.0 - r),
        "BPFO": n / 2.0 * (1.0 - r),
        "BPFI": n / 2.0 * (1.0 + r),
        "BSF": (pd / (2.0 * bd)) * (1.0 - r * r),
    }


def geometry_from_orders(o):
    """Recover the geometry a catalogue's defect factors imply.

        N            = BPFO + BPFI
        (Bd/Pd) cos a = 1 - 2 FTF
        Bd/Pd         = (1 - ((Bd/Pd) cos a)^2) / (2 BSF)
        cos a         = ((Bd/Pd) cos a) / (Bd/Pd)
    """
    n = o["BPFO"] + o["BPFI"]
    dc = 1.0 - 2.0 * o["FTF"]
    ratio = (1.0 - dc * dc) / (2.0 * o["BSF"]) if o["BSF"] > 0 else dc
    if ratio <= 0:
        ratio = dc
    c = dc / ratio if ratio > 0 else 1.0
    th = math.degrees(math.acos(max(-1.0, min(1.0, c))))
    if c > 1.02:
        th = 0.0
    return {"n": n, "dc": dc, "ratio": ratio, "th": th}


def normalize_factors(a, b, c, ftf):
    """Read four catalogue numbers whatever order and convention they came
    in. Returns (orders, notes).

    The outer race factor is the one equal to N x FTF (N = the two race
    factors added), so BPFO and BPFI are told apart by physics, not by
    column position. The third number is BSF in some catalogues and the
    ball defect frequency 2 x BSF in others; with no contact angle
    BSF = (1 - d^2) / (2 d), d = 1 - 2 FTF, and a contact angle only lowers
    it, so a value well above that is a 2 x BSF figure."""
    notes = []
    n = a + b
    lo, hi = min(a, b), max(a, b)
    bpfo, bpfi = (lo, hi)
    if abs(n * ftf - lo) > abs(n * ftf - hi):
        bpfo, bpfi = hi, lo
    if a != bpfo:
        notes.append("the first two factors were BPFI then BPFO")
    d = 1.0 - 2.0 * ftf
    bsf0 = (1.0 - d * d) / (2.0 * d) if 0 < d < 1 else c
    r = c / bsf0 if bsf0 > 0 else 1.0
    if 1.3 < r <= 2.6:
        bsf = c / 2.0
        notes.append("the ball factor was 2 x BSF (ball defect frequency), halved to BSF")
    elif r > 2.6:
        bsf = bsf0
        notes.append("the ball factor did not fit the geometry, so BSF was worked out from FTF (no contact angle)")
    else:
        bsf = c
    return {"BPFO": bpfo, "BPFI": bpfi, "BSF": bsf, "FTF": ftf}, notes


class Bearing(object):
    """Either real geometry (mm) or catalogue factors (orders)."""

    def __init__(self, name, orders, n=None, bd=None, pd=None, th=None, roller=False, source="preset"):
        self.name = name
        self.orders = dict(orders)
        self.n, self.bd, self.pd, self.th = n, bd, pd, th
        self.roller = roller
        self.source = source
        self.notes = []

    @classmethod
    def from_geometry(cls, name, n, bd, pd, th, roller=False, source="custom"):
        return cls(name, orders_from_geometry(n, bd, pd, th), n, bd, pd, th, roller, source)

    @classmethod
    def from_orders(cls, name, bpfo, bpfi, bsf, ftf, source="catalog"):
        orders, notes = normalize_factors(bpfo, bpfi, bsf, ftf)
        b = cls(name, orders, source=source)
        b.notes = notes
        return b

    def elements(self):
        if self.n:
            return int(round(self.n))
        return max(3, int(round(self.orders["BPFO"] + self.orders["BPFI"])))


def preset_bearing(pid):
    for p in PRESETS:
        if p["id"] == pid:
            return Bearing.from_geometry(p["name"], p["n"], p["bd"], p["pd"], p["th"], p["roller"], "preset")
    p = PRESETS[0]
    return Bearing.from_geometry(p["name"], p["n"], p["bd"], p["pd"], p["th"], p["roller"], "preset")


# ----------------------------------------------------------------------
# settings
# ----------------------------------------------------------------------
class Settings(object):
    def __init__(self):
        self.bearing = preset_bearing("6205")
        self.rpm = 1485.0
        self.loc = "outer"
        self.stage = 2
        self.load = 100.0          # % of the stage's nominal impact strength
        self.zone = 180.0          # load zone width, degrees (360 = all round)
        self.def_ang = 0.0         # outer race defect, degrees from load zone centre
        self.slip = 1.0            # % rolling element slip
        self.fr = 3000.0           # housing resonance, Hz
        self.mount = "stud"
        self.env_band = "auto"
        self.env_fmax = "auto"
        self.unb = 1.2             # 1X from residual unbalance, mm/s peak
        self.seed = 1

    def copy(self):
        s = Settings()
        s.__dict__.update(self.__dict__)
        return s


def frequencies(st):
    """Calculated and actual (with slip) defect frequencies in Hz."""
    f1 = st.rpm / 60.0
    o = st.bearing.orders
    calc = dict((k, v * f1) for k, v in o.items())
    calc["2xBSF"] = 2.0 * calc["BSF"]
    calc["1X"] = f1
    s = st.slip / 100.0
    ftf = o["FTF"] * f1 * (1.0 - s)
    n = st.bearing.orders["BPFO"] / o["FTF"] if o["FTF"] > 0 else st.bearing.elements()
    act = {
        "1X": f1,
        "FTF": ftf,
        # the elements pass a point on the fixed outer race at N x cage speed,
        # and a point on the turning inner race at N x (shaft - cage)
        "BPFO": n * ftf,
        "BPFI": n * (f1 - ftf),
        "BSF": calc["BSF"] * (1.0 - s),
    }
    act["2xBSF"] = 2.0 * act["BSF"]
    return calc, act


def defect_key(loc):
    return {"outer": "BPFO", "inner": "BPFI", "ball": "2xBSF", "cage": "FTF"}[loc]


def mod_key(loc):
    """What modulates the impact strength."""
    return {"outer": None, "inner": "1X", "ball": "FTF", "cage": None}[loc]


# ----------------------------------------------------------------------
# load zone
# ----------------------------------------------------------------------
def load_factor(psi, zone_deg, roller):
    """Stribeck load distribution, normalised to 1 at the zone centre.
    psi in radians from the centre of the load zone."""
    if zone_deg >= 359.0:
        eps = 1.6                  # preloaded / fully loaded all round
    else:
        half = math.radians(zone_deg / 2.0)
        eps = (1.0 - math.cos(half)) / 2.0
    x = 1.0 - (1.0 - math.cos(psi)) / (2.0 * eps)
    if x <= 0.0:
        return 0.0
    return x ** (1.1 if roller else 1.5)


# ----------------------------------------------------------------------
# stage model
# ----------------------------------------------------------------------
# imp    impact strength at the load zone centre, g peak at the resonance
# zeta   damping of the ring; a fresh small spall rings longest
# jit    random spread of the impact spacing on top of slip, fraction of a period
# ampsd  random spread of each impact's strength
# tone   defect frequency harmonics in velocity, mm/s peak (stage 3+)
# hay    rms g of the noise hump around the resonance
# floor  rms g of broadband rolling noise
# lowno  rms g of low frequency random noise (end of life)
# x1     1X multiplier (clearance grows at end of life)
# harm   number of running speed harmonics from looseness
# hfd    ultrasonic (20-60 kHz) stress wave energy, g - beyond this record
STAGES = [
    {"imp": 0.0, "zeta": 0.05, "jit": 0.0, "ampsd": 0.0, "tone": 0.0, "hay": 0.0,
     "floor": 0.025, "lowno": 0.0, "x1": 1.0, "harm": 1, "hfd": 0.05},
    {"imp": 0.10, "zeta": 0.035, "jit": 0.003, "ampsd": 0.25, "tone": 0.0, "hay": 0.0,
     "floor": 0.026, "lowno": 0.0, "x1": 1.0, "harm": 1, "hfd": 0.45},
    {"imp": 1.4, "zeta": 0.03, "jit": 0.004, "ampsd": 0.20, "tone": 0.0, "hay": 0.02,
     "floor": 0.03, "lowno": 0.0, "x1": 1.0, "harm": 2, "hfd": 0.9},
    {"imp": 3.2, "zeta": 0.045, "jit": 0.008, "ampsd": 0.30, "tone": 0.9, "hay": 0.09,
     "floor": 0.05, "lowno": 0.005, "x1": 1.3, "harm": 3, "hfd": 1.6},
    {"imp": 0.9, "zeta": 0.10, "jit": 0.09, "ampsd": 0.7, "tone": 0.25, "hay": 0.75,
     "floor": 0.32, "lowno": 0.10, "x1": 2.6, "harm": 8, "hfd": 1.1},
]


def stage_params(stage, loc):
    p = dict(STAGES[stage])
    if loc == "cage" and stage > 0:
        # a cage fault does not spall; it rattles. Weak, irregular knocks at
        # cage speed and a sub-synchronous FTF line.
        p["imp"] *= 0.6
        p["hay"] *= 0.3            # no spalled race to roughen the rolling
        p["jit"] = max(p["jit"], 0.012)
        p["ampsd"] = max(p["ampsd"], 0.5)
    if loc == "ball" and stage > 0:
        p["jit"] *= 1.6            # a damaged ball also skids and turns
    return p


# ----------------------------------------------------------------------
# the signal
# ----------------------------------------------------------------------
def _add_sine(x, n, amp, f, ph):
    """Add amp*sin(2 pi f t + ph) by rotation - far cheaper than sin()."""
    w = TAU * f / FS
    c, s = math.cos(w), math.sin(w)
    re, im = math.cos(ph), math.sin(ph)
    for i in range(n):
        x[i] += amp * im
        re, im = re * c - im * s, re * s + im * c


def _vel_to_acc(v, f):
    """mm/s peak -> g peak at f"""
    return v * TAU * f / 1000.0 / G


def _impacts(st, act, p, rnd, n):
    """Times, strengths and the modulation phase of each impact."""
    key = defect_key(st.loc)
    rate = act[key]
    out = []
    if rate <= 0 or p["imp"] <= 0:
        return out
    roller = st.bearing.roller
    period = 1.0 / rate
    f1, ftf = act["1X"], act["FTF"]
    T = n / FS
    # start a little before zero so the record does not open on silence
    t = -0.5 * period * rnd.next()
    k = 0
    zone_c = 0.0
    while t < T:
        if st.loc == "outer":
            psi = math.radians(st.def_ang)
        elif st.loc == "inner":
            # defect turns with the shaft past the fixed load zone
            psi = TAU * f1 * t + 1.1
        elif st.loc == "ball":
            # the ball rides round with the cage
            psi = TAU * ftf * t + 0.4
        else:
            psi = TAU * ftf * t
        lf = load_factor(psi, st.zone, roller)
        if st.loc == "cage":
            lf = 0.35 + 0.65 * lf
        # a defect outside the load zone is not completely silent: the
        # elements are still pressed on by centrifugal force and the fit
        a = p["imp"] * (st.load / 100.0) * max(0.04, lf)
        if st.loc == "ball":
            # the spall strikes the inner and outer race in turn; the outer
            # race strike is felt more strongly at a housing sensor
            a *= 1.0 if k % 2 == 0 else 0.55
        a *= max(0.05, 1.0 + p["ampsd"] * rnd.gauss() * 0.6)
        out.append((t, a, lf, k))
        jit = p["jit"] + 0.25 * st.slip / 100.0
        t += period * (1.0 + jit * rnd.gauss())
        k += 1
    return out


def _noise_bands(st, p):
    """Shaped random noise as (centre Hz, width Hz, rms g, flat?)."""
    fr = st.fr
    b = [(2500.0, 2500.0, p["floor"], True)]
    if p["hay"] > 0:
        b.append((fr, 0.22 * fr, p["hay"] * st.load / 100.0, False))
    if p["lowno"] > 0:
        b.append((600.0, 600.0, p["lowno"], True))
    return b


def _add_noise_freq(re, im, n, bands, rnd):
    """Random phase noise added straight into the spectrum. Parseval sets
    the scale: rms^2 = 2 sum |X_k|^2 / N^2 over the positive bins."""
    df = FS / n
    half = n // 2
    for (fc, bw, rms, flat) in bands:
        if rms <= 0:
            continue
        lo = max(1, int((fc - bw) / df)) if flat else max(1, int((fc - 3 * bw) / df))
        hi = min(half - 1, int((fc + bw) / df) if flat else int((fc + 3 * bw) / df))
        if hi <= lo:
            continue
        br = [0.0] * (hi - lo + 1)
        bi = [0.0] * (hi - lo + 1)
        tot = 0.0
        for k in range(lo, hi + 1):
            f = k * df
            w = 1.0 if flat else math.exp(-0.5 * ((f - fc) / bw) ** 2)
            a, b2 = rnd.gauss() * w, rnd.gauss() * w
            br[k - lo], bi[k - lo] = a, b2
            tot += a * a + b2 * b2
        if tot <= 0:
            continue
        sc = rms * n / math.sqrt(2.0 * tot)
        for k in range(lo, hi + 1):
            re[k] += br[k - lo] * sc
            im[k] += bi[k - lo] * sc
            re[n - k] += br[k - lo] * sc
            im[n - k] -= bi[k - lo] * sc


def _mount_gain(f, mount):
    """Complex response of the accelerometer on its mount: a second order
    low pass at the mounted resonance."""
    _, _, fm, q = MOUNT_BY_ID[mount]
    r = f / fm
    dr, di = 1.0 - r * r, r / q
    d = dr * dr + di * di
    return dr / d, -di / d


def build(st, n=N, with_vel=True):
    """Synthesise one record. Returns a dict with the acceleration waveform
    (g), velocity waveform (mm/s), their spectra, the envelope and its
    spectrum, and the impacts used."""
    p = stage_params(st.stage, st.loc)
    calc, act = frequencies(st)
    rnd = Rand(1000 + 37 * st.seed + 11 * st.stage + {"outer": 1, "inner": 2, "ball": 3, "cage": 4}[st.loc])
    x = [0.0] * n
    f1 = act["1X"]

    # --- running speed content (mm/s), turned into g -----------------------
    unb = st.unb * p["x1"]
    _add_sine(x, n, _vel_to_acc(unb, f1), f1, 0.3)
    for h in range(2, p["harm"] + 1):
        v = unb * (0.35 if h == 2 else 0.5 * math.exp(-(h - 2) / 3.0)) * (1.0 if p["harm"] > 3 else 0.6)
        _add_sine(x, n, _vel_to_acc(v, h * f1), h * f1, 1.3 * h)
    if st.stage == 4:
        # looseness at end of life: half orders appear as well
        for h in (0.5, 1.5, 2.5):
            _add_sine(x, n, _vel_to_acc(0.18 * unb, h * f1), h * f1, 0.7 * h)

    # --- defect frequency lines in velocity (stage 3 and 4) -----------------
    key = defect_key(st.loc)
    fd = act[key]
    tone = p["tone"] * st.load / 100.0
    if tone > 0 and fd > 0:
        mk = mod_key(st.loc)
        fm = act[mk] if mk else 0.0
        for h in range(1, 7):
            fh = h * fd
            if fh >= FMAX:
                break
            v = tone / (h ** 0.8)
            if st.loc == "outer":
                v *= max(0.1, load_factor(math.radians(st.def_ang), st.zone, st.bearing.roller))
            _add_sine(x, n, _vel_to_acc(v, fh), fh, 0.9 * h)
            if fm > 0:
                for s in (1, 2):
                    vs = v * (0.45 if s == 1 else 0.18)
                    for sgn in (-1, 1):
                        fs_ = fh + sgn * s * fm
                        if 0 < fs_ < FMAX:
                            _add_sine(x, n, _vel_to_acc(vs, fs_), fs_, 0.5 * h + sgn * s)
        if st.loc == "cage" or st.stage == 4:
            ftf = act["FTF"]
            _add_sine(x, n, _vel_to_acc(0.35 * st.load / 100.0 * (2.0 if st.loc == "cage" else 1.0), ftf), ftf, 0.2)

    # --- impacts ringing the resonance --------------------------------------
    imps = _impacts(st, act, p, rnd, n)
    wr = TAU * st.fr
    z = p["zeta"]
    wd = wr * math.sqrt(1.0 - z * z)
    dec = z * wr
    dt = 1.0 / FS
    L = int(math.log(1e4) / dec / dt) + 2
    # a bigger, rougher spall excites a broader spread of frequencies; let a
    # few impacts land on a second, higher mode as well
    wr2 = TAU * min(FMAX * 0.92, st.fr * 1.55)
    dec2 = (z * 1.3) * wr2
    for (t0, a, lf, k) in imps:
        i0 = int(math.ceil(t0 * FS))
        if i0 < 0:
            i0 = 0
        cd, sd = math.cos(wd * dt), math.sin(wd * dt)
        cd2, sd2 = math.cos(wr2 * dt), math.sin(wr2 * dt)
        tau = i0 * dt - t0
        e = math.exp(-dec * tau)
        ed = math.exp(-dec * dt)
        e2 = math.exp(-dec2 * tau)
        ed2 = math.exp(-dec2 * dt)
        c, s = math.cos(wd * tau), math.sin(wd * tau)
        c2, s2 = math.cos(wr2 * tau), math.sin(wr2 * tau)
        a2 = 0.35 * a
        z1 = dec / wd
        z2 = dec2 / wr2
        for i in range(i0, min(n, i0 + L)):
            # e^-at (cos bt - (a/b) sin bt) has zero area, so an impact adds
            # no false low frequency line of its own: the ring is all there is
            x[i] += a * e * (c - z1 * s) + a2 * e2 * (c2 - z2 * s2)
            e *= ed
            e2 *= ed2
            c, s = c * cd - s * sd, c * sd + s * cd
            c2, s2 = c2 * cd2 - s2 * sd2, c2 * sd2 + s2 * cd2

    # --- into the frequency domain: noise, the sensor mount -----------------
    re = x
    im = [0.0] * n
    fft(re, im)
    _add_noise_freq(re, im, n, _noise_bands(st, p), rnd)
    df = FS / n
    half = n // 2
    for k in range(1, half + 1):
        gr, gi = _mount_gain(k * df, st.mount)
        a, b = re[k], im[k]
        re[k], im[k] = a * gr - b * gi, a * gi + b * gr
        if k != half:
            a, b = re[n - k], im[n - k]
            re[n - k], im[n - k] = a * gr + b * gi, -a * gi + b * gr
    re[0] = im[0] = 0.0          # an accelerometer does not pass DC

    # --- spectra (Hanning applied as a 3 point convolution in frequency) ----
    lines = int(n / 2.56)
    acc_mag = [0.0] * (lines + 1)
    vel_mag = [0.0] * (lines + 1)
    for k in range(lines + 1):
        km, kp = (k - 1) % n, (k + 1) % n
        wr_ = 0.5 * re[k] - 0.25 * (re[km] + re[kp])
        wi_ = 0.5 * im[k] - 0.25 * (im[km] + im[kp])
        m = 4.0 * math.hypot(wr_, wi_) / n
        acc_mag[k] = m
        f = k * df
        vel_mag[k] = m * G * 1000.0 / (TAU * f) if f >= 2.0 else 0.0

    # --- waveforms ----------------------------------------------------------
    ar, ai = list(re), list(im)
    ifft(ar, ai)
    acc = ar
    vel = None
    if with_vel:
        vr = [0.0] * n
        vi = [0.0] * n
        for k in range(1, n):
            kk = k if k <= half else k - n
            f = kk * df
            if abs(f) < 2.0:
                continue
            # divide by j w and convert g -> mm/s
            g = G * 1000.0 / (TAU * f)
            vr[k] = im[k] * g
            vi[k] = -re[k] * g
        ifft(vr, vi)
        vel = vr

    lo, hi = env_band(st)
    env, env_mag = envelope(re, im, n, lo, hi)

    return {"acc": acc, "vel": vel, "acc_mag": acc_mag, "vel_mag": vel_mag, "df": df,
            "lines": lines, "env": env, "env_mag": env_mag, "band": (lo, hi),
            "imps": imps, "calc": calc, "act": act, "p": p, "n": n}


def env_band(st):
    if st.env_band == "wide":
        return 500.0, FMAX
    if st.env_band == "low":
        return 10.0, 500.0
    return max(300.0, 0.6 * st.fr), min(FMAX, 1.4 * st.fr)


def envelope(re, im, n, lo, hi):
    """Band pass between lo and hi, keep positive frequencies (the analytic
    signal, i.e. x + j Hilbert(x)), take its magnitude - the envelope - and
    return it with its Hanning windowed amplitude spectrum (g peak)."""
    df = FS / n
    zr = [0.0] * n
    zi = [0.0] * n
    k0 = max(1, int(math.ceil(lo / df)))
    k1 = min(n // 2 - 1, int(hi / df))
    for k in range(k0, k1 + 1):
        # gentle edges (raised cosine over 5 % of the band) keep the
        # filter from ringing on its own
        w = 1.0
        edge = max(2, int(0.05 * (k1 - k0)))
        if k - k0 < edge:
            w = 0.5 * (1 - math.cos(math.pi * (k - k0) / edge))
        elif k1 - k < edge:
            w = 0.5 * (1 - math.cos(math.pi * (k1 - k) / edge))
        zr[k] = 2.0 * re[k] * w
        zi[k] = 2.0 * im[k] * w
    ifft(zr, zi)
    env = [math.hypot(zr[i], zi[i]) for i in range(n)]
    mean = sum(env) / n
    er = [0.0] * n
    ei = [0.0] * n
    for i in range(n):
        er[i] = (env[i] - mean) * 0.5 * (1.0 - math.cos(TAU * i / n))
    fft(er, ei)
    lines = int(n / 2.56)
    mag = [4.0 * math.hypot(er[k], ei[k]) / n for k in range(lines + 1)]
    mag[0] = 0.0
    return env, mag


# ----------------------------------------------------------------------
# reading the result
# ----------------------------------------------------------------------
def stats(acc):
    n = len(acc)
    s1 = sum(acc) / n
    s2 = s3 = s4 = 0.0
    pk = tr = 0.0
    for v in acc:
        d = v - s1
        d2 = d * d
        s2 += d2
        s3 += d2 * d
        s4 += d2 * d2
        if v > pk:
            pk = v
        if v < tr:
            tr = v
    var = s2 / n
    rms = math.sqrt(var)
    if rms <= 0:
        return {"rms": 0.0, "pk": 0.0, "tr": 0.0, "pp": 0.0, "cf": 0.0, "kurt": 0.0, "skew": 0.0}
    return {"rms": rms, "pk": pk, "tr": tr, "pp": pk - tr, "cf": max(pk, -tr) / rms,
            "kurt": (s4 / n) / (var * var), "skew": (s3 / n) / (var * rms)}


def band_rms(mag, df, lo, hi):
    """RMS over a band from a Hanning spectrum (noise bandwidth 1.5 bins)."""
    s = 0.0
    for k in range(max(1, int(lo / df)), min(len(mag) - 1, int(hi / df)) + 1):
        s += mag[k] * mag[k] / 2.0
    return math.sqrt(s / 1.5)


def peak_near(mag, df, f, tol=None):
    """Highest line within tol of f; (amplitude, frequency)."""
    if f <= 0:
        return 0.0, 0.0
    tol = tol if tol is not None else max(2.5 * df, 0.012 * f)
    k0 = max(1, int((f - tol) / df))
    k1 = min(len(mag) - 1, int(math.ceil((f + tol) / df)))
    best, bk = 0.0, k0
    for k in range(k0, k1 + 1):
        if mag[k] > best:
            best, bk = mag[k], k
    return best, bk * df


def noise_floor(mag, k0, k1):
    """Median of a band - a robust floor that ignores the lines."""
    v = sorted(mag[max(1, k0):max(k0 + 1, k1)])
    return v[len(v) // 2] if v else 0.0


def candidates(act, fmax):
    """Every frequency a bearing can explain, with a label."""
    out = []
    for key in ("FTF", "BSF", "BPFO", "BPFI", "1X"):
        f = act[key]
        for h in range(1, 13):
            fh = h * f
            if fh > fmax:
                break
            out.append((fh, ("%dx%s" % (h, key)) if h > 1 else key, key, h, 0))
    f1, ftf = act["1X"], act["FTF"]
    for h in range(1, 7):
        for s in (1, 2):
            for sgn in (-1, 1):
                fi = h * act["BPFI"] + sgn * s * f1
                if 0 < fi <= fmax:
                    out.append((fi, "%s%s%s%dX" % ("%dx" % h if h > 1 else "", "BPFI", "+" if sgn > 0 else "-", s),
                                "BPFI", h, sgn * s))
        fb = h * act["2xBSF"]
        for s in (1,):
            for sgn in (-1, 1):
                fi = fb + sgn * act["FTF"]
                if 0 < fi <= fmax:
                    out.append((fi, "%dxBSF%sFTF" % (2 * h, "+" if sgn > 0 else "-"), "BSF", 2 * h, sgn))
    return out


def find_peaks(mag, df, fmax, count=8, f_lo=2.0):
    """The tallest local maxima, at least 3 lines apart and clearly above the
    local floor."""
    k1 = min(len(mag) - 2, int(fmax / df))
    k0 = max(2, int(f_lo / df))
    floor = noise_floor(mag, k0, k1)
    cand = []
    for k in range(k0, k1):
        m = mag[k]
        if m > mag[k - 1] and m >= mag[k + 1] and m > 4.0 * floor:
            cand.append((m, k))
    cand.sort(reverse=True)
    out = []
    for m, k in cand:
        if all(abs(k - j) > 3 for _, j in out):
            out.append((m, k))
        if len(out) >= count:
            break
    # refine each frequency by the Hanning amplitude ratio of the two lines
    res = []
    for m, k in out:
        a, b = mag[k - 1], mag[k + 1]
        if b >= a:
            d = (2 * b - m) / (m + b) if (m + b) > 0 else 0.0
        else:
            d = -(2 * a - m) / (m + a) if (m + a) > 0 else 0.0
        d = max(-0.5, min(0.5, d))
        res.append(((k + d) * df, m))
    return res, floor


def match(f, cands, df, prefer=None):
    """The simplest explanation within tolerance wins: a low harmonic before
    a high one, a line before a sideband. BPFO is exactly N x FTF, so the
    nearest candidate alone would call every BPFO line a cage harmonic."""
    best = None
    for fc, lab, key, h, sb in cands:
        tol = max(2.0 * df, 0.015 * fc)
        e = abs(f - fc)
        if e <= tol:
            score = e / tol + 0.15 * (h - 1) + (1.0 if sb else 0.0) - (0.6 if key == prefer else 0.0)
            if best is None or score < best[0]:
                best = (score, fc, lab, key, h, sb)
    return best


def diagnose(res, st):
    """Read the envelope spectrum the way an analyst would: which family of
    lines is there, with which sidebands. Purely from the computed spectrum."""
    act = res["act"]
    df = res["df"]
    fmax = env_fmax(st, act)
    peaks, floor = find_peaks(res["env_mag"], df, fmax, 10)
    cands = candidates(act, fmax)
    fam = {"BPFO": 0, "BPFI": 0, "BSF": 0, "FTF": 0, "1X": 0}
    side = {"BPFI": 0, "BSF": 0}
    rows = []
    # the tallest line sets the family the rest are read against first
    lead = match(peaks[0][0], cands, df) if peaks else None
    prefer = lead[3] if lead and lead[3] != "1X" else None
    for f, m in peaks:
        mt = match(f, cands, df, prefer)
        lab = mt[2] if mt else "?"
        rows.append((f, m, lab, mt[1] if mt else None))
        if mt:
            fam[mt[3]] += 1
            if mt[5] != 0 and mt[3] in side:
                side[mt[3]] += 1
    snr = (peaks[0][1] / floor) if (peaks and floor > 0) else 0.0
    if not peaks or snr < 6.0:
        verdict = ("No clear repeating impact: the envelope spectrum is noise. Either the bearing is "
                   "healthy, the defect is too young to ring the resonance yet, or the filter band and mount "
                   "do not reach the resonance.")
        found = None
    else:
        top = max(("BPFO", "BPFI", "BSF", "FTF"), key=lambda k: fam[k])
        if fam[top] == 0:
            found = None
            verdict = ("Envelope peaks are there, but they do not line up with this bearing's defect "
                       "frequencies (%s). Check the shaft speed and the bearing model."
                       % ", ".join(r[2] for r in rows[:3]))
        else:
            found = top
            txt = {"BPFO": "Outer race defect: BPFO and its harmonics%s.",
                   "BPFI": "Inner race defect: BPFI and harmonics%s.",
                   "BSF": "Rolling element defect: 2xBSF family%s.",
                   "FTF": "Cage problem: FTF and its harmonics%s."}[top]
            if top == "BPFO":
                extra = ", with no running speed sidebands - the defect sits still in the load zone"
            elif top == "BPFI":
                extra = (", sidebanded at 1X (%d sideband lines found) - the defect turns in and out of the "
                         "load zone once per revolution" % side["BPFI"]) if side["BPFI"] else \
                    ", sidebands at 1X expected but weak at this load zone"
            elif top == "BSF":
                extra = (", sidebanded at FTF (%d found) - the ball rides round the load zone with the cage"
                         % side["BSF"]) if side["BSF"] else ""
            else:
                extra = ""
            verdict = txt % extra
            if top == "BSF" and fam["BSF"] and any(r[2] == "BSF" for r in rows):
                verdict += " BSF itself shows too: the ball hits the inner and outer race unequally."
    return {"peaks": rows, "floor": floor, "snr": snr, "verdict": verdict, "found": found}


def env_fmax(st, act):
    if st.env_fmax != "auto":
        return float(st.env_fmax)
    need = 5.5 * max(act["BPFI"], act["2xBSF"]) if st.loc != "cage" else 12.0 * act["1X"]
    if st.loc == "outer":
        need = 6.5 * act["BPFO"]
    for f in (250.0, 500.0, 1000.0, 2000.0):
        if f >= need:
            return f
    return 2000.0


def summary(res, st):
    """Numbers for the statistics card."""
    a = stats(res["acc"])
    v = stats(res["vel"]) if res["vel"] is not None else None
    df = res["df"]
    vrms = band_rms(res["vel_mag"], df, 10.0, 1000.0)
    arms = band_rms(res["acc_mag"], df, 2.0, FMAX)
    hf = band_rms(res["acc_mag"], df, 1000.0, FMAX)
    key = defect_key(st.loc)
    fd = res["act"][key]
    e_def, _ = peak_near(res["env_mag"], df, fd)
    v_def, _ = peak_near(res["vel_mag"], df, fd)
    e = res["env"]
    epk = max(e) - min(e) if e else 0.0
    return {"acc": a, "vel": v, "vrms": vrms, "arms": arms, "hf": hf, "env_def": e_def,
            "vel_def": v_def, "env_pp": epk, "hfd": res["p"]["hfd"] * (st.load / 100.0 if st.stage else 1.0)}


def stage_trend(st, n=4096):
    """Run every stage with the same settings on a shorter record: how the
    measurements evolve from new to failed."""
    out = []
    for s in range(5):
        t = st.copy()
        t.stage = s
        r = build(t, n=n, with_vel=False)
        a = stats(r["acc"])
        df = r["df"]
        fd = r["act"][defect_key(t.loc)]
        e_def, _ = peak_near(r["env_mag"], df, fd)
        out.append({"stage": s, "rms": a["rms"], "cf": a["cf"], "kurt": a["kurt"],
                    "vrms": band_rms(r["vel_mag"], df, 10.0, 1000.0),
                    "env": e_def, "hfd": STAGES[s]["hfd"]})
    return out


# ----------------------------------------------------------------------
# words
# ----------------------------------------------------------------------
STAGE_DETAIL = [
    {"what": "Smooth raceways under a healthy oil film. Only rolling noise and running speed.",
     "ultra": "Low, steady.",
     "env": "Noise only; no lines.",
     "spec": "1X from residual unbalance; nothing at bearing frequencies.",
     "wave": "Random rolling noise: crest factor about 3 to 4, kurtosis about 3.",
     "action": "Baseline. Record it - every later reading is compared with this one.",
     "life": "-"},
    {"what": "Sub-surface fatigue cracks or lubrication starting to fail. The stress waves are at 20-60 kHz, "
             "far above an ordinary spectrum.",
     "ultra": "Rising: ultrasound, shock pulse, spike energy, PeakVue and HFD see it first.",
     "env": "At best a faint line at the defect frequency, barely out of the noise.",
     "spec": "Nothing changes. The velocity spectrum and overall level look healthy.",
     "wave": "Crest factor and kurtosis begin to creep up.",
     "action": "Check the lubrication - grease or oil condition, quantity, contamination. Trend weekly.",
     "life": "Typically 10-20 % of the remaining life is left after this stage is passed."},
    {"what": "A small spall. Every pass of a rolling element is a sharp knock that rings the bearing and housing "
             "natural frequencies (here %s Hz).",
     "ultra": "Higher still.",
     "env": "The defect frequency and its harmonics stand clearly out of the floor - this is the stage envelope "
            "analysis is made for.",
     "spec": "Still almost nothing at the defect frequency in velocity: the energy is up at the resonance, "
             "where velocity weighting makes it tiny.",
     "wave": "Sharp, evenly spaced impacts. Crest factor and kurtosis are at their highest while the RMS is "
             "still low.",
     "action": "Plan the replacement. Shorten the monitoring interval; watch the envelope amplitude trend.",
     "life": "Weeks to months, depending on load and speed."},
    {"what": "The spall has grown and spread. Impacts are larger and the defect is now wide enough to "
             "produce a low frequency response of its own.",
     "ultra": "High.",
     "env": "Many harmonics, with sidebands (1X for inner race, FTF for a rolling element). The floor rises.",
     "spec": "Defect frequencies and their harmonics now appear in velocity, sidebanded; a raised "
             "'haystack' of noise grows around the resonance.",
     "wave": "Large impacts; crest factor still high but the RMS is rising too.",
     "action": "Replace at the next opportunity. Do not run to failure on a critical machine.",
     "life": "Days to a few weeks. Under 1-5 % of the bearing's life remains."},
    {"what": "Damage spread round the race; clearance has opened up. Impacts happen everywhere, so they are "
             "no longer periodic - they merge into random noise.",
     "ultra": "May fall again as the surfaces are smoothed - a trap if you trend only one number.",
     "env": "Discrete lines fade into a high, flat floor; the defect frequency can even disappear.",
     "spec": "1X and many running speed harmonics rise (looseness), sub-harmonics and FTF appear, broadband "
             "noise lifts the whole spectrum.",
     "wave": "Random, high amplitude. RMS is high, so the crest factor FALLS back towards 3 even though the "
             "bearing is at its worst.",
     "action": "Replace now. Heat, noise and a seized or broken cage are close.",
     "life": "Hours to days."},
]


LOC_NOTES = {
    "outer": ("The outer race is fixed in the housing, so a spall on it sits still. If it is in the load zone "
              "every element hits it equally hard: evenly spaced impacts of the same size, no modulation, and an "
              "envelope spectrum of BPFO and clean harmonics with no sidebands. Turn the defect position away "
              "from the load zone and watch the impacts shrink - a spall at 12 o'clock under a gravity load can "
              "stay silent for a long time."),
    "inner": ("The inner race turns with the shaft, so the spall is carried in and out of the load zone once "
              "per revolution. The impacts are strong for part of each revolution and weak for the rest: "
              "amplitude modulation at 1X. In the spectrum that becomes sidebands spaced at 1X around BPFI and "
              "its harmonics. Open the load zone to 360 degrees (a preloaded or unbalanced rotor) and the "
              "sidebands shrink."),
    "ball": ("A spalled ball spins at BSF and its defect touches the inner race and the outer race once each per "
             "spin, so the impacts come at 2 x BSF. The two strikes differ, so BSF itself shows too. The ball "
             "travels round the bearing with the cage, in and out of the load zone, so everything is modulated "
             "at FTF - sidebands spaced at the cage frequency. A ball can also turn and hide its spall, which "
             "makes rolling element defects the most erratic of the four."),
    "cage": ("The cage carries no load and does not spall. A worn or broken cage rattles and lets the elements "
             "bunch, which shows as FTF - a sub-synchronous line, roughly 0.4 x running speed - and as modulation "
             "of the other bearing tones at FTF. Its impacts are weak and irregular. Cage problems usually come "
             "with, or after, race and element damage."),
}


def fmt_hz(f):
    return "%.1f" % f if f >= 100 else ("%.2f" % f if f >= 10 else "%.3f" % f)


# ----------------------------------------------------------------------
# self test - run in CI
# ----------------------------------------------------------------------
def self_test(verbose=True):
    import time
    t0 = time.time()
    fails = []

    def check(name, got, want, tol):
        if abs(got - want) > tol:
            fails.append("%s: %.4f, expected %.4f" % (name, got, want))

    o = orders_from_geometry(9, 7.94, 39.04, 0.0)
    check("6205 BPFO", o["BPFO"], 3.5848, 2e-3)
    check("6205 BPFI", o["BPFI"], 5.4152, 2e-3)
    check("6205 FTF", o["FTF"], 0.3983, 1e-3)
    check("BPFO + BPFI = N", o["BPFO"] + o["BPFI"], 9.0, 1e-9)
    g = geometry_from_orders(o)
    check("geometry back: N", g["n"], 9.0, 1e-9)
    check("geometry back: Bd/Pd", g["ratio"], 7.94 / 39.04, 1e-6)
    check("geometry back: angle", g["th"], 0.0, 0.5)
    o40 = orders_from_geometry(12, 17.46, 80.0, 40.0)
    check("contact angle recovered", geometry_from_orders(o40)["th"], 40.0, 0.2)

    # catalogue rows hold BPFI, BPFO, 2 x BSF, FTF (SKF 6205 shown)
    cat, notes = normalize_factors(5.427, 3.573, 4.65, 0.397)
    check("catalogue BPFO", cat["BPFO"], 3.573, 1e-9)
    check("catalogue BPFI", cat["BPFI"], 5.427, 1e-9)
    check("catalogue BSF halved", cat["BSF"], 2.325, 1e-9)
    if len(notes) != 2:
        fails.append("catalogue notes %r" % notes)
    ok, notes = normalize_factors(o["BPFO"], o["BPFI"], o["BSF"], o["FTF"])
    if notes or abs(ok["BSF"] - o["BSF"]) > 1e-12:
        fails.append("correct factors were changed: %r" % notes)

    check("load zone centre", load_factor(0.0, 180.0, False), 1.0, 1e-9)
    if load_factor(math.radians(120), 180.0, False) != 0.0:
        fails.append("outside a 180 deg load zone must be unloaded")
    if load_factor(math.radians(179), 360.0, False) <= 0.0:
        fails.append("a 360 deg load zone must load everywhere")

    st = Settings()
    calc, act = frequencies(st)
    if not act["BPFO"] < calc["BPFO"]:
        fails.append("slip must lower BPFO")

    # outer race, stage 2: envelope finds BPFO, plain velocity does not
    st.loc, st.stage = "outer", 2
    r = build(st)
    s = summary(r, st)
    d = diagnose(r, st)
    if d["found"] != "BPFO":
        fails.append("stage 2 outer race diagnosed as %s" % d["found"])
    f_top = d["peaks"][0][0] if d["peaks"] else 0
    if abs(f_top - act["BPFO"]) > 3 * r["df"]:
        fails.append("tallest envelope line %.1f Hz, BPFO %.1f" % (f_top, act["BPFO"]))
    if s["acc"]["cf"] < 4.5:
        fails.append("stage 2 crest factor only %.2f" % s["acc"]["cf"])
    if s["vel_def"] > 0.3:
        fails.append("stage 2 BPFO in velocity already %.2f mm/s" % s["vel_def"])

    # inner race: sidebands at 1X
    st.loc = "inner"
    r = build(st)
    d = diagnose(r, st)
    if d["found"] != "BPFI":
        fails.append("stage 2 inner race diagnosed as %s" % d["found"])
    a0, _ = peak_near(r["env_mag"], r["df"], act["BPFI"])
    a1, _ = peak_near(r["env_mag"], r["df"], act["BPFI"] - act["1X"], 2 * r["df"])
    if a1 < 0.12 * a0:
        fails.append("inner race 1X sideband weak: %.3f vs %.3f" % (a1, a0))

    # rolling element
    st.loc = "ball"
    r = build(st)
    d = diagnose(r, st)
    if d["found"] != "BSF":
        fails.append("stage 2 ball diagnosed as %s" % d["found"])

    # handheld probe loses the resonance
    st.loc, st.mount = "outer", "hand"
    r = build(st)
    e_hand = summary(r, st)["env_def"]
    st.mount = "stud"
    e_stud = summary(build(st), st)["env_def"]
    if e_hand > 0.5 * e_stud:
        fails.append("handheld envelope %.3f vs stud %.3f" % (e_hand, e_stud))

    # stage 3 shows the defect in velocity; healthy shows nothing
    st.stage = 3
    s3 = summary(build(st), st)
    if s3["vel_def"] < 0.3:
        fails.append("stage 3 BPFO in velocity %.2f mm/s" % s3["vel_def"])
    st.stage = 0
    r0 = build(st)
    if diagnose(r0, st)["found"] is not None:
        fails.append("healthy bearing diagnosed as faulty")

    # trend: crest factor rises to stage 2/3 then falls at stage 4; RMS keeps rising
    st.stage = 2
    tr = stage_trend(st)
    cfs = [t["cf"] for t in tr]
    if not (max(cfs[2], cfs[3]) > cfs[0] + 1.5 and cfs[4] < max(cfs[2], cfs[3]) - 1.0):
        fails.append("crest factor trend %s" % ", ".join("%.2f" % c for c in cfs))
    if not tr[4]["rms"] > tr[3]["rms"] > tr[0]["rms"]:
        fails.append("RMS trend %s" % ", ".join("%.3f" % t["rms"] for t in tr))

    dt = time.time() - t0
    if verbose:
        if fails:
            print("bearing_engine self test FAILED:")
            for f in fails:
                print("  - " + f)
        else:
            print("bearing_engine self test OK (%.1f s)" % dt)
    return fails


if __name__ == "__main__":
    import sys
    sys.exit(1 if self_test() else 0)
