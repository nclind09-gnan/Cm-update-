"""
wave_engine - the maths behind the CM Toolkit Waveform Builder. Pure Python,
no Kivy and no numpy:  python wave_engine.py  runs the self test (used by the
CI sanity check).

Five sine waves, each with its own amplitude (mm/s peak) and frequency
(0 to 2000 Hz; 0 Hz is a constant offset). They can be seen one by one, laid
over each other, or added into the single complex waveform a sensor records,
and that sum is taken apart again by a Hanning-windowed FFT the way an
analyser does it - with its resolution and picket-fence limits.
"""

import math

from fault_engine import fft

TAU = 2.0 * math.pi
FMAX_MAX = 2000.0
NAMES = ["Wave 1", "Wave 2", "Wave 3", "Wave 4", "Wave 5"]
FMAX_OPTIONS = [500, 1000, 2000, 2500]
LINE_OPTIONS = [400, 800, 1600, 3200]

# (name, [(on, amplitude, frequency) x 5])
PRESETS = [
    ("Motor 1485 rpm", [(1, 5, 24.75), (1, 2, 49.5), (1, 1.5, 100), (1, 1, 88.7), (1, 0.8, 1200)]),
    ("1X + harmonics", [(1, 5, 25), (1, 2.5, 50), (1, 1.6, 75), (1, 1.2, 100), (1, 0.9, 125)]),
    ("Beat (2X vs 2xLF)", [(1, 3, 99), (1, 3, 100), (0, 1, 25), (0, 1, 50), (0, 1, 200)]),
    ("Sidebands (AM)", [(1, 4, 500), (1, 1.5, 475), (1, 1.5, 525), (0, 1, 25), (0, 1, 50)]),
    ("One wave only", [(1, 5, 25), (0, 2, 50), (0, 1.5, 100), (0, 1, 150), (0, 0.8, 1200)]),
    ("Low + high", [(1, 5, 10), (1, 1, 1500), (0, 1, 25), (0, 1, 50), (0, 1, 100)]),
]


class Wave(object):
    __slots__ = ("on", "a", "f")

    def __init__(self, on=True, a=1.0, f=25.0):
        self.on, self.a, self.f = bool(on), float(a), float(f)


def default_waves():
    return [Wave(*p) for p in PRESETS[0][1]]


def active(waves):
    """[(index, amplitude, frequency)] of the waves that are switched on."""
    return [(i, w.a, w.f) for i, w in enumerate(waves) if w.on and w.a > 0]


def value(a, f, t):
    return a if f == 0 else a * math.sin(TAU * f * t)


def sum_at(act, t):
    s = 0.0
    for _, a, f in act:
        s += a if f == 0 else a * math.sin(TAU * f * t)
    return s


def fmt_hz(f):
    return "%.1f" % f if f >= 100 else ("%.2f" % f if f >= 10 else "%.3f" % f)


def fmt_ms(t):
    return "%.0f" % t if t >= 100 else ("%.1f" % t if t >= 10 else "%.2f" % t)


def auto_span(act):
    """Record length in ms: four cycles of the lowest wave, and at least
    1.5 beat periods when two waves are close together."""
    fs = sorted(f for _, _, f in act if f > 0)
    if not fs:
        return 100.0
    ms = 4000.0 / fs[0]
    for i in range(1, len(fs)):
        d = fs[i] - fs[i - 1]
        if 0 < d < fs[i - 1]:
            ms = max(ms, 1500.0 / d)
    return max(5.0, min(2000.0, ms))


def span_from_slider(v):
    """Slider 0..1000 -> 2 ms .. 2000 ms, logarithmic."""
    return 2.0 * 1000.0 ** (v / 1000.0)


def slider_from_span(ms):
    return 1000.0 * math.log(ms / 2.0) / math.log(1000.0)


def envelope(fn, t0, T, cols, sub=6):
    """Min/max of fn over each of `cols` columns from t0 to t0+T, so a dense
    high-frequency trace is drawn honestly rather than aliased by the
    pixel grid. Returns [(first, lo, hi)] per column."""
    out = []
    for k in range(cols):
        a = t0 + T * k / cols
        b = t0 + T * (k + 1) / cols
        lo, hi, first = 1e30, -1e30, 0.0
        for j in range(sub + 1):
            v = fn(a + (b - a) * j / sub)
            if j == 0:
                first = v
            if v < lo:
                lo = v
            if v > hi:
                hi = v
        out.append((first, lo, hi))
    return out


def spectrum(act, fmax, lines):
    """Hanning-windowed amplitude spectrum (mm/s peak) of the merged waveform.
    Waves at or above F-max are removed, as the anti-alias filter would."""
    fs = 2.56 * fmax
    n = int(round(2.56 * lines))
    use = [w for w in act if w[2] < fmax]
    filtered = [w for w in act if w[2] >= fmax]
    re = [0.0] * n
    im = [0.0] * n
    # sines by rotation: exact enough, and far cheaper than sin() per sample
    rot = []
    for _, a, f in use:
        w = TAU * f / fs
        rot.append([a, f == 0, math.cos(w), math.sin(w), 1.0, 0.0])
    for i in range(n):
        s = 0.0
        for r in rot:
            if r[1]:
                s += r[0]
            else:
                s += r[0] * r[5]
                c, si = r[4], r[5]
                r[4] = c * r[2] - si * r[3]
                r[5] = c * r[3] + si * r[2]
        re[i] = s * 0.5 * (1.0 - math.cos(TAU * i / n))
    fft(re, im)
    mag = [0.0] * (lines + 1)
    for i in range(lines + 1):
        m = math.hypot(re[i], im[i]) * 2.0 / n / 0.5
        mag[i] = m * 0.5 if i == 0 else m
    return {"mag": mag, "df": fs / n, "fmax": fmax, "lines": lines,
            "filtered": filtered, "T": n / fs}


def peak_near(spec, f):
    k = int(round(f / spec["df"]))
    a = 0.0
    for j in range(max(0, k - 2), min(spec["lines"], k + 2) + 1):
        a = max(a, spec["mag"][j])
    return a


def suggest(d, fhi):
    opts = []
    for f in FMAX_OPTIONS:
        for l in LINE_OPTIONS:
            if d >= 3.0 * f / l:
                opts.append((f, l))
    if not opts:
        return "Even the finest setting here (500 Hz, 3200 lines, df 0.156 Hz) cannot split them."
    keep = [o for o in opts if o[0] > fhi]
    pool = keep if keep else opts
    pool.sort(key=lambda o: (-o[0], o[1]))
    f, l = pool[0]
    return ("Try F-max %d Hz with %d lines (df %.3f Hz)%s"
            % (f, l, f / float(l), "." if keep else ", though that F-max cuts off your higher waves."))


def spectrum_notes(act, spec):
    """Plain-language notes: unresolved pairs, picket fence, above F-max."""
    notes = []
    fs = sorted([w for w in act if w[2] < spec["fmax"]], key=lambda w: w[2])
    for i in range(1, len(fs)):
        d = fs[i][2] - fs[i - 1][2]
        a, b = NAMES[fs[i - 1][0]], NAMES[fs[i][0]]
        if 0 < d < 3 * spec["df"]:
            notes.append("[b]%s and %s[/b] are %s Hz apart, only %.1f lines: too close to show as two "
                         "peaks (they need about 3 lines between them). %s"
                         % (a, b, fmt_hz(d), d / spec["df"], suggest(d, fs[i][2])))
        elif d == 0:
            notes.append("[b]%s and %s[/b] have the same frequency, so they add into one line "
                         "(how much depends on their phase)." % (a, b))
    pf = []
    for i, a, f in act:
        if f <= 0 or f >= spec["fmax"]:
            continue
        got = peak_near(spec, f)
        err = 1.0 - got / a
        if err > 0.03:
            pf.append("%s reads %.2f for %.2f (%d%% low)" % (NAMES[i], got, a, round(err * 100)))
    if pf:
        notes.append("[b]Picket fence:[/b] %s. Its frequency falls between two spectral lines, and "
                     "with a Hanning window a peak between lines reads up to 15%% low. Real "
                     "analysers do the same; a different line count changes it." % ", ".join(pf))
    if spec["filtered"]:
        notes.append("[b]%s[/b] above F-max: the anti-alias filter removes it from the spectrum, "
                     "though it is still in the waveform."
                     % ", ".join("%s (%s Hz)" % (NAMES[i], fmt_hz(f)) for i, a, f in spec["filtered"]))
    return notes


def stats(act):
    """CAT II statistics of the merged waveform, measured from a sampled
    record (about 20 samples per cycle of the highest wave, 1 to 4 s long,
    capped so a phone stays responsive)."""
    if not act:
        return None
    fpos = [f for _, _, f in act if f > 0]
    lo = min(fpos) if fpos else 10.0
    hi = max(fpos) if fpos else 10.0
    dur = min(4.0, max(1.0, 4.0 / lo))
    fs = max(200.0, 20.0 * hi)
    n = int(dur * fs)
    if n > 40000:
        n = 40000
        dur = n / fs
    rot = []
    dc = 0.0
    for _, a, f in act:
        if f == 0:
            dc += a
        else:
            w = TAU * f / fs
            rot.append([a, math.cos(w), math.sin(w), 1.0, 0.0])
    pk, tr, s1, s2 = -1e30, 1e30, 0.0, 0.0
    for i in range(n):
        v = dc
        for r in rot:
            v += r[0] * r[4]
            c, si = r[3], r[4]
            r[3] = c * r[1] - si * r[2]
            r[4] = c * r[2] + si * r[1]
        if v > pk:
            pk = v
        if v < tr:
            tr = v
        s1 += v
        s2 += v * v
    rms = math.sqrt(s2 / n)
    mean = s1 / n
    cf = max(pk, -tr) / rms if rms > 0 else 0.0
    rms_th = math.sqrt(sum((a * a if f == 0 else a * a / 2.0) for _, a, f in act))
    sum_a = sum(a for _, a, _ in act)
    asym = pk / -tr if -tr > 0 else 0.0
    return {"pk": pk, "tr": tr, "pp": pk - tr, "rms": rms, "rms_th": rms_th, "cf": cf,
            "asym": asym, "sum": sum_a, "mean": mean, "dur": dur}


def stats_rows(s):
    cf, asym = s["cf"], s["asym"]
    return [
        ("Peak (+)", "%.2f mm/s" % s["pk"], "highest point of the merged waveform"),
        ("Peak (-)", "%.2f mm/s" % s["tr"], "lowest point"),
        ("Peak-to-peak", "%.2f mm/s" % s["pp"], "the full swing"),
        ("RMS", "%.2f mm/s" % s["rms"], "sqrt(sum A^2/2) = %.2f: RMS adds by squares, not by amplitudes" % s["rms_th"]),
        ("Crest factor", "%.2f" % cf, "about 1.41: a near-pure sine" if cf < 1.6 else
         ("smooth periodic signal; no impacting" if cf < 3.5 else "high: sharp peaks well above the RMS, as impacts produce")),
        ("Asymmetry +/-", "%.2f" % asym, "symmetric about zero" if abs(asym - 1) < 0.1 else
         ("positive side reaches further" if asym > 1 else "negative side reaches further")),
    ]


def stats_note(s):
    top = max(s["pk"], -s["tr"])
    txt = ("Over %.1f s of the merged signal. The peak is %d%% of the sum of the amplitudes "
           "(%.1f mm/s): " % (s["dur"], round(100 * top / s["sum"]) if s["sum"] else 0, s["sum"]))
    txt += ("here the peaks do line up." if top > 0.97 * s["sum"] else
            "the individual peaks rarely line up, so the merged peak is lower than their sum.")
    if abs(s["mean"]) > 0.05:
        txt += " Mean %.2f mm/s from the 0 Hz offset." % s["mean"]
    return txt


# ----------------------------------------------------------------------
# self test - run in CI
# ----------------------------------------------------------------------
def self_test(verbose=True):
    import time
    t0 = time.time()
    fails = []
    # a bin-centred wave reads back at its own amplitude
    sp = spectrum([(0, 4.0, 100.0)], 1000, 800)          # df 1.25 Hz, 100 Hz on a line
    a = peak_near(sp, 100.0)
    if abs(a - 4.0) > 0.02:
        fails.append("bin-centred amplitude %.3f, expected 4" % a)
    # between lines it reads low, but never more than about 15 %
    sp = spectrum([(0, 4.0, 100.625)], 1000, 800)
    a = peak_near(sp, 100.625)
    if not (0.83 * 4 < a < 0.97 * 4):
        fails.append("picket fence amplitude %.3f" % a)
    if not any("Picket" in n for n in spectrum_notes([(0, 4.0, 100.625)], sp)):
        fails.append("picket fence not reported")
    # above F-max is filtered
    sp = spectrum([(0, 2.0, 1200.0)], 1000, 800)
    if max(sp["mag"]) > 0.05 or not sp["filtered"]:
        fails.append("wave above F-max not filtered")
    # beat: 99 and 100 Hz not resolved at 2500/1600, resolved at 500/3200
    act = [(0, 3.0, 99.0), (1, 3.0, 100.0)]
    if not any("too close" in n for n in spectrum_notes(act, spectrum(act, 2500, 1600))):
        fails.append("beat pair should be unresolved at 2500 Hz / 1600 lines")
    if any("too close" in n for n in spectrum_notes(act, spectrum(act, 500, 3200))):
        fails.append("beat pair should resolve at 500 Hz / 3200 lines")
    if auto_span(act) < 1500:
        fails.append("auto span too short for a 1 Hz beat: %.0f ms" % auto_span(act))
    # statistics: one sine -> crest 1.414, RMS A/sqrt2
    s = stats([(0, 5.0, 25.0)])
    if abs(s["cf"] - math.sqrt(2)) > 0.02 or abs(s["rms"] - 5 / math.sqrt(2)) > 0.02:
        fails.append("pure sine stats cf %.3f rms %.3f" % (s["cf"], s["rms"]))
    s = stats([(i, w.a, w.f) for i, w in enumerate(default_waves())])
    if abs(s["rms"] - s["rms_th"]) > 0.03 * s["rms_th"] or s["cf"] <= 1.5:
        fails.append("merged stats rms %.3f vs %.3f cf %.2f" % (s["rms"], s["rms_th"], s["cf"]))
    s = stats([(0, 2.0, 0.0), (1, 3.0, 50.0)])
    if abs(s["mean"] - 2.0) > 0.02:
        fails.append("DC offset mean %.3f" % s["mean"])
    dt = time.time() - t0
    if verbose:
        if fails:
            print("wave_engine self test FAILED:")
            for f in fails:
                print("  - " + f)
        else:
            print("wave_engine self test OK (%.1f s)" % dt)
    return fails


if __name__ == "__main__":
    import sys
    sys.exit(1 if self_test() else 0)
