"""
Simulation - interactive teaching tools for CM Toolkit.

Sub-tabs:
  1. Balance Demo     - the whole single-plane job on one screen, with sliders
                        on every measured value and a live vector diagram
  2. Fault Signature  - the waveform and spectrum each of 27 faults actually
                        produces, synthesised from the machine geometry you set
  3. Orbit            - two proximity probes and a Keyphasor on a rotor with
                        split criticals: orbit, timebase and full spectrum
  4. Resonance        - a coast-down through the first and second criticals:
                        Bode, the shaft's deflected shape, the orbit, AF and
                        separation margin for each critical
  5. Phase Survey     - a field phase survey on a motor and pump or fan: tap
                        points, read phase from tach and waveform, match the
                        fault pattern, and meet the measurement traps
  6. Waveform Builder - five sine waves, overlaid or merged, with zoom, time
                        cursors, the spectrum of the sum and its statistics

Orbit and Resonance share their physics with orbit_engine.py, Phase Survey
with phase_engine.py and Waveform Builder with wave_engine.py.

Navigation follows CM/DX: a card menu, tap to open a tool full screen, back
returns to the menu.

The balancing maths is imported directly from rotor_tab so the demo and the
calculator can never drift apart.

Angle convention: measured CLOCKWISE from the phase reference mark, 0 deg at
the top - identical to the Rotor Balance tab.
"""

import cmath
import math

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Ellipse, Triangle, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget

from theme import ModernInput, NavCard, PillButton, RoundedButton
import fault_engine
import orbit_engine
import phase_engine
import wave_engine
from rotor_tab import (
    to_complex, to_clock_deg, clock_position,
    single_plane_correction,
)

# ---------- palette: rose accent, distinct from the other six tools ----------
COLOR_BG = (1, 1, 1, 1)
COLOR_ACCENT = (0.886, 0.247, 0.541, 1)        # rose
COLOR_ACCENT_SOFT = (0.973, 0.882, 0.929, 1)
COLOR_TEXT = (0.06, 0.09, 0.16, 1)
COLOR_TEXT_MUTED = (0.357, 0.392, 0.447, 1)
COLOR_PANEL_BG = (0.97, 0.97, 0.98, 1)
COLOR_BORDER = (0.86, 0.88, 0.92, 1)
COLOR_GRID = (0.84, 0.86, 0.90, 1)
COLOR_GRID_FAINT = (0.92, 0.93, 0.96, 1)

TEXT_HEX = "0F172A"
MUTED_HEX = "5B6472"
ACCENT_HEX = "E23F8A"

# Vector colours, following the convention of the reference balancer
C_ORIGINAL = (0.153, 0.306, 0.788)      # blue   - O
C_TRIALRUN = (0.055, 0.561, 0.267)      # green  - O+T
C_EFFECT = (0.886, 0.400, 0.055)        # orange - T (effect of trial weight)
C_CORRECTION = (0.820, 0.180, 0.180)    # red    - correction weight
C_TRIMRUN = (0.502, 0.251, 0.682)       # purple - trim run
C_TRIMWT = (0.839, 0.651, 0.055)        # amber  - final trim weight

HEX_ORIGINAL = "274EC9"
HEX_TRIALRUN = "0E8F44"
HEX_EFFECT = "E2660E"
HEX_CORRECTION = "D12E2E"
HEX_TRIMRUN = "8040AE"
HEX_TRIMWT = "D6A60E"


# =====================================================================
# Vector diagram
# =====================================================================
class VectorChart(Widget):
    """Polar vector plot, 0 deg at top and angles increasing clockwise.

    Vibration vectors are drawn to a common auto-scale. Weight vectors are a
    different physical quantity (mass, not vibration) so they are never
    scaled against the vibration vectors - they are drawn as fixed-length
    direction indicators instead, which is the honest way to show them on
    the same picture."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vib_vectors = []      # dicts: mag, angle, color, label, tail
        self.dir_vectors = []      # dicts: angle, color, label
        self.show_labels = True
        self.manual_scale = None   # units per division, or None for auto
        self._label_widgets = []
        self.bind(pos=self.redraw, size=self.redraw)

    def set_data(self, vib_vectors, dir_vectors, show_labels=True, manual_scale=None):
        self.vib_vectors = vib_vectors or []
        self.dir_vectors = dir_vectors or []
        self.show_labels = show_labels
        self.manual_scale = manual_scale
        self.redraw()

    # -- geometry helpers -------------------------------------------------
    @staticmethod
    def _xy(cx, cy, scale, mag, angle_deg):
        rad = math.radians(angle_deg)
        return (cx + mag * scale * math.sin(rad),
                cy + mag * scale * math.cos(rad))

    @staticmethod
    def _arrow(x1, y1, x2, y2, color, width=2.0):
        r, g, b = color[:3]
        Color(r, g, b, 1)
        Line(points=[x1, y1, x2, y2], width=width)
        ang = math.atan2(y2 - y1, x2 - x1)
        head = dp(11)
        spread = math.radians(23)
        Triangle(points=[
            x2, y2,
            x2 - head * math.cos(ang - spread), y2 - head * math.sin(ang - spread),
            x2 - head * math.cos(ang + spread), y2 - head * math.sin(ang + spread),
        ])

    def redraw(self, *args):
        self.canvas.clear()
        for w in self._label_widgets:
            self.remove_widget(w)
        self._label_widgets = []

        if self.width <= 1 or self.height <= 1:
            return

        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) * 0.42

        # ---- scale -------------------------------------------------------
        mags = [v["mag"] for v in self.vib_vectors if v.get("mag")]
        # the effect vector's tip sits at the trial-run tip, so the plain max
        # of the drawn magnitudes is enough to bound the picture
        max_mag = max(mags) if mags else 0.0
        if self.manual_scale and self.manual_scale > 0:
            # manual: fixed units per division, 4 divisions to the edge
            scale = radius / (self.manual_scale * 4.0)
            divisions = 4
        else:
            scale = (radius * 0.88 / max_mag) if max_mag > 0 else 0.0
            divisions = 4

        with self.canvas:
            # grid rings
            for i in range(1, divisions + 1):
                Color(*(COLOR_GRID if i == divisions else COLOR_GRID_FAINT))
                Line(circle=(cx, cy, radius * i / divisions), width=1.0)
            # spokes every 30 deg
            Color(*COLOR_GRID_FAINT)
            for deg in range(0, 360, 30):
                rad = math.radians(deg)
                Line(points=[cx, cy,
                             cx + radius * math.sin(rad),
                             cy + radius * math.cos(rad)], width=0.9)
            # main axes a little stronger
            Color(*COLOR_GRID)
            Line(points=[cx - radius, cy, cx + radius, cy], width=1.0)
            Line(points=[cx, cy - radius, cx, cy + radius], width=1.0)

            # ---- vibration vectors --------------------------------------
            if scale > 0:
                for v in self.vib_vectors:
                    if not v.get("mag"):
                        continue
                    tail = v.get("tail")
                    if tail:
                        x1, y1 = self._xy(cx, cy, scale, tail[0], tail[1])
                    else:
                        x1, y1 = cx, cy
                    x2, y2 = self._xy(cx, cy, scale, v["mag"], v["angle"])
                    # a tip-to-tip vector is drawn from its tail to the
                    # absolute position of its own tip
                    if tail:
                        x2, y2 = self._xy(cx, cy, scale, v["mag"], v["angle"])
                    self._arrow(x1, y1, x2, y2, v["color"])

            # ---- weight direction indicators ----------------------------
            for d in self.dir_vectors:
                r, g, b = d["color"][:3]
                Color(r, g, b, 1)
                rad = math.radians(d["angle"])
                ex = cx + radius * 0.97 * math.sin(rad)
                ey = cy + radius * 0.97 * math.cos(rad)
                # dashed so it reads as "direction only", not a scaled magnitude
                steps = 11
                for s in range(steps):
                    if s % 2:
                        continue
                    t0 = s / steps
                    t1 = (s + 1) / steps
                    Line(points=[cx + (ex - cx) * t0, cy + (ey - cy) * t0,
                                 cx + (ex - cx) * t1, cy + (ey - cy) * t1], width=1.8)
                Ellipse(pos=(ex - dp(5), ey - dp(5)), size=(dp(10), dp(10)))

        # ---- cardinal angle labels + vector labels ----------------------
        for deg in (0, 90, 180, 270):
            rad = math.radians(deg)
            lx = cx + radius * 1.10 * math.sin(rad)
            ly = cy + radius * 1.10 * math.cos(rad)
            lbl = Label(text=str(deg), font_size=dp(11), color=COLOR_TEXT_MUTED,
                        size_hint=(None, None), size=(dp(30), dp(16)))
            lbl.center = (lx, ly)
            self.add_widget(lbl)
            self._label_widgets.append(lbl)

        if self.show_labels and scale > 0:
            for v in self.vib_vectors:
                if not v.get("mag") or not v.get("label"):
                    continue
                x, y = self._xy(cx, cy, scale, v["mag"] * 0.62, v["angle"])
                if v.get("tail"):
                    tx, ty = self._xy(cx, cy, scale, v["tail"][0], v["tail"][1])
                    ex, ey = self._xy(cx, cy, scale, v["mag"], v["angle"])
                    x, y = (tx + ex) / 2.0, (ty + ey) / 2.0
                r, g, b = v["color"][:3]
                lbl = Label(text=v["label"], font_size=dp(10), bold=True,
                            color=(r, g, b, 1), size_hint=(None, None),
                            size=(dp(96), dp(16)))
                lbl.center = (x, y)
                self.add_widget(lbl)
                self._label_widgets.append(lbl)


# =====================================================================
# Slider-backed numeric field
# =====================================================================
class SliderField(BoxLayout):
    """A labelled numeric entry with a slider underneath. Typing and sliding
    stay in sync, and either one fires the callback."""

    def __init__(self, label_text, value, vmin, vmax, on_change,
                 fmt="{:.2f}", wrap=False, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(92), spacing=dp(2), **kwargs)
        self._on_change = on_change
        self._fmt = fmt
        self._wrap = wrap          # True for angles: 0-360 wrap-around
        self._vmin, self._vmax = vmin, vmax
        self._syncing = False

        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44),
                        spacing=dp(8))
        lbl = Label(text=label_text, font_size=dp(13), bold=True,
                    color=COLOR_TEXT_MUTED, halign="left", valign="middle")
        lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        top.add_widget(lbl)

        self.field = ModernInput(
            text=fmt.format(value), multiline=False, height=dp(42),
            font_size=dp(16), panel_color=COLOR_BORDER,
            text_color=COLOR_TEXT, accent=COLOR_ACCENT,
            size_hint_x=None, width=dp(104),
        )
        self.field.ti.bind(text=self._on_text)
        top.add_widget(self.field)
        self.add_widget(top)

        self.slider = Slider(min=vmin, max=vmax, value=value,
                             size_hint_y=None, height=dp(40),
                             cursor_size=(dp(26), dp(26)))
        self.slider.bind(value=self._on_slide)
        self.add_widget(self.slider)

    # -- value plumbing ---------------------------------------------------
    @property
    def value(self):
        try:
            return float(self.field.text)
        except (ValueError, TypeError):
            return None

    def set_value(self, v):
        self._syncing = True
        self.field.text = self._fmt.format(v)
        if self._vmin <= v <= self._vmax:
            self.slider.value = v
        self._syncing = False

    def _on_slide(self, inst, val):
        if self._syncing:
            return
        self._syncing = True
        self.field.text = self._fmt.format(val)
        self._syncing = False
        self._on_change()

    def _on_text(self, inst, text):
        if self._syncing:
            return
        try:
            v = float(text)
        except (ValueError, TypeError):
            return
        if self._wrap:
            v = v % 360.0
        self._syncing = True
        # let a typed value beyond the slider's range extend it rather than
        # silently clamping what the user asked for
        if v > self._vmax:
            self._vmax = v
            self.slider.max = v
        if v < self._vmin:
            self._vmin = v
            self.slider.min = v
        self.slider.value = v
        self._syncing = False
        self._on_change()


# =====================================================================
# Small UI helpers
# =====================================================================
def panel(**kwargs):
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6),
                    size_hint_y=None, **kwargs)
    with box.canvas.before:
        Color(*COLOR_PANEL_BG)
        box._bg = RoundedRectangle(radius=[dp(12)])
        Color(*COLOR_BORDER)
        box._line = Line(rounded_rectangle=(0, 0, 10, 10, dp(12)), width=1.1)

    def _upd(*a):
        box._bg.pos = box.pos
        box._bg.size = box.size
        box._line.rounded_rectangle = (box.x, box.y, box.width, box.height, dp(12))
    box.bind(pos=_upd, size=_upd)
    box.bind(minimum_height=box.setter("height"))
    return box


def step_header(number, title, hex_color):
    lbl = Label(
        text=f"[b][color={hex_color}]{number}  {title}[/color][/b]",
        markup=True, size_hint_y=None, height=dp(28), font_size=dp(15),
        halign="left", valign="middle")
    lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
    return lbl


def readout(text=""):
    lbl = Label(text=text, markup=True, size_hint_y=None, halign="left",
                valign="top", font_size=dp(15), color=COLOR_TEXT)
    lbl.bind(texture_size=lambda i, v: setattr(i, "height", v[1] + dp(8)))
    lbl.bind(width=lambda i, v: setattr(i, "text_size", (v, None)))
    return lbl


def note(markup_text, height=dp(44)):
    lbl = Label(text=markup_text, markup=True, size_hint_y=None, height=height,
                halign="left", valign="top")
    lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
    return lbl


# =====================================================================
# Balance Demo
# =====================================================================
class BalanceDemoScreen(Screen):
    """The complete single-plane job on one screen: original run, trial
    weight, trial run, correction, trim run, final trim. Every measured
    value has a slider, and the vector diagram redraws live."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.show_o = True
        self.show_ot = True
        self.show_t = True
        self.show_trim = True
        self.show_labels = True

        root = BoxLayout(orientation="vertical")

        # --- chart pinned at the top so it stays visible while sliding ---
        chart_box = BoxLayout(orientation="vertical", size_hint_y=None,
                              height=dp(300), padding=[dp(6), dp(6), dp(6), 0])
        self.chart = VectorChart()
        chart_box.add_widget(self.chart)
        root.add_widget(chart_box)

        self.legend = Label(text="", markup=True, size_hint_y=None, height=dp(38),
                            font_size=dp(12), halign="center", valign="middle")
        self.legend.bind(size=lambda i, v: setattr(i, "text_size", v))
        root.add_widget(self.legend)

        # --- scrolling controls ------------------------------------------
        scroll = ScrollView()
        form = GridLayout(cols=1, spacing=dp(12), size_hint_y=None,
                          padding=(dp(12), dp(6), dp(12), dp(24)))
        form.bind(minimum_height=form.setter("height"))

        form.add_widget(note(
            f"[color={MUTED_HEX}][size=13]Drag any slider and watch the vector "
            "diagram and the answers update. Angles are clockwise from the "
            "reference mark, 0° at the top.[/size][/color]", height=dp(56)))

        # ---- display controls -------------------------------------------
        disp = panel()
        disp.add_widget(step_header("", "SHOW", TEXT_HEX))
        row1 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        self.btn_o = PillButton("O", accent=C_ORIGINAL + (1,), inactive=COLOR_PANEL_BG,
                                text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        self.btn_ot = PillButton("O+T", accent=C_TRIALRUN + (1,), inactive=COLOR_PANEL_BG,
                                 text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        self.btn_t = PillButton("T", accent=C_EFFECT + (1,), inactive=COLOR_PANEL_BG,
                                text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        self.btn_trim = PillButton("Trim", accent=C_TRIMRUN + (1,), inactive=COLOR_PANEL_BG,
                                   text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        self.btn_o.bind(on_release=lambda i: self._toggle("show_o", self.btn_o))
        self.btn_ot.bind(on_release=lambda i: self._toggle("show_ot", self.btn_ot))
        self.btn_t.bind(on_release=lambda i: self._toggle("show_t", self.btn_t))
        self.btn_trim.bind(on_release=lambda i: self._toggle("show_trim", self.btn_trim))
        for b in (self.btn_o, self.btn_ot, self.btn_t, self.btn_trim):
            row1.add_widget(b)
        disp.add_widget(row1)

        row2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        self.btn_labels = PillButton("Vector labels", accent=COLOR_ACCENT,
                                     inactive=COLOR_PANEL_BG, text_color=(1, 1, 1, 1),
                                     inactive_text_color=COLOR_TEXT)
        self.btn_labels.bind(on_release=lambda i: self._toggle("show_labels", self.btn_labels))
        row2.add_widget(self.btn_labels)
        disp.add_widget(row2)
        form.add_widget(disp)

        # ---- step 1: original run ---------------------------------------
        p1 = panel()
        p1.add_widget(step_header("1.", "ORIGINAL RUN", HEX_ORIGINAL))
        self.o_amp = SliderField("Amplitude", 5.58, 0.0, 20.0, self.recompute)
        self.o_ph = SliderField("Phase (deg)", 34.0, 0.0, 360.0, self.recompute,
                                fmt="{:.0f}", wrap=True)
        p1.add_widget(self.o_amp)
        p1.add_widget(self.o_ph)
        form.add_widget(p1)

        # ---- step 2: trial weight ---------------------------------------
        p2 = panel()
        p2.add_widget(step_header("2.", "TRIAL WEIGHT", HEX_EFFECT))
        self.t_mass = SliderField("Mass", 1.0, 0.0, 50.0, self.recompute)
        self.t_ang = SliderField("Angle (deg)", 0.0, 0.0, 360.0, self.recompute,
                                 fmt="{:.0f}", wrap=True)
        p2.add_widget(self.t_mass)
        p2.add_widget(self.t_ang)
        form.add_widget(p2)

        # ---- step 3: trial run ------------------------------------------
        p3 = panel()
        p3.add_widget(step_header("3.", "TRIAL RUN (O+T)", HEX_TRIALRUN))
        self.tr_amp = SliderField("Amplitude", 4.0, 0.0, 20.0, self.recompute)
        self.tr_ph = SliderField("Phase (deg)", 120.0, 0.0, 360.0, self.recompute,
                                 fmt="{:.0f}", wrap=True)
        p3.add_widget(self.tr_amp)
        p3.add_widget(self.tr_ph)
        form.add_widget(p3)

        # ---- step 4: correction (calculated) ----------------------------
        p4 = panel()
        p4.add_widget(step_header("4.", "CORRECTION WEIGHT", HEX_CORRECTION))
        self.corr_out = readout()
        p4.add_widget(self.corr_out)
        form.add_widget(p4)

        # ---- step 5: trim run -------------------------------------------
        p5 = panel()
        p5.add_widget(step_header("5.", "TRIM RUN", HEX_TRIMRUN))
        p5.add_widget(note(
            f"[color={MUTED_HEX}][size=12]What is left after the correction "
            "is fitted. Leave at zero if you are not trimming.[/size][/color]",
            height=dp(36)))
        self.trim_amp = SliderField("Amplitude", 0.0, 0.0, 20.0, self.recompute)
        self.trim_ph = SliderField("Phase (deg)", 0.0, 0.0, 360.0, self.recompute,
                                   fmt="{:.0f}", wrap=True)
        p5.add_widget(self.trim_amp)
        p5.add_widget(self.trim_ph)
        form.add_widget(p5)

        # ---- step 6: final (calculated) ---------------------------------
        p6 = panel()
        p6.add_widget(step_header("6.", "FINAL", HEX_TRIMWT))
        self.final_out = readout()
        p6.add_widget(self.final_out)
        form.add_widget(p6)

        # ---- reset -------------------------------------------------------
        reset = RoundedButton(text="Reset to example", height=dp(46),
                              accent=COLOR_ACCENT)
        reset.bind(on_release=lambda i: self.reset_example())
        form.add_widget(reset)

        form.add_widget(note(
            f"[color={MUTED_HEX}][size=12]A demo, not a measurement. The "
            "numbers here are whatever you set them to - it is showing you how "
            "the vector solution behaves, not what any real machine is "
            "doing.[/size][/color]", height=dp(56)))

        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

        self._sync_toggle_buttons()
        self.recompute()

    # -- toggles -----------------------------------------------------------
    def _toggle(self, attr, btn):
        setattr(self, attr, not getattr(self, attr))
        btn.set_active(getattr(self, attr))
        self.recompute()

    def _sync_toggle_buttons(self):
        self.btn_o.set_active(self.show_o)
        self.btn_ot.set_active(self.show_ot)
        self.btn_t.set_active(self.show_t)
        self.btn_trim.set_active(self.show_trim)
        self.btn_labels.set_active(self.show_labels)

    def reset_example(self):
        self.o_amp.set_value(5.58)
        self.o_ph.set_value(34.0)
        self.t_mass.set_value(1.0)
        self.t_ang.set_value(0.0)
        self.tr_amp.set_value(4.0)
        self.tr_ph.set_value(120.0)
        self.trim_amp.set_value(0.0)
        self.trim_ph.set_value(0.0)
        self.recompute()

    # -- the live calculation ---------------------------------------------
    def recompute(self, *args):
        vals = [self.o_amp.value, self.o_ph.value,
                self.t_mass.value, self.t_ang.value,
                self.tr_amp.value, self.tr_ph.value]
        if any(v is None for v in vals):
            self.corr_out.text = f"[color={MUTED_HEX}]Fill in every value.[/color]"
            self.final_out.text = ""
            return
        o_amp, o_ph, t_mass, t_ang, tr_amp, tr_ph = vals

        vib, dirs = [], []
        if self.show_o:
            vib.append(dict(mag=o_amp, angle=o_ph, color=C_ORIGINAL,
                            label=f"O {o_amp:.2f}@{o_ph:.0f}"))
        if self.show_ot:
            vib.append(dict(mag=tr_amp, angle=tr_ph, color=C_TRIALRUN,
                            label=f"O+T {tr_amp:.2f}@{tr_ph:.0f}"))

        if t_mass <= 0:
            self.corr_out.text = (
                f"[color={MUTED_HEX}]Set a trial weight above zero to get a "
                "correction.[/color]")
            self.final_out.text = ""
            self.chart.set_data(vib, dirs, self.show_labels)
            self._set_legend(None, None)
            return

        O = to_complex(o_amp, o_ph)
        OT = to_complex(tr_amp, tr_ph)
        T = to_complex(t_mass, t_ang)

        try:
            Wc, S, E = single_plane_correction(O, OT, T)
        except ValueError:
            self.corr_out.text = (
                f"[color={HEX_CORRECTION}]The trial weight has not changed the "
                "reading, so there is nothing to solve. Move the trial run "
                "away from the original run.[/color]")
            self.final_out.text = ""
            self.chart.set_data(vib, dirs, self.show_labels)
            self._set_legend(None, None)
            return

        e_mag, e_ang = to_clock_deg(E)
        s_mag, s_ang = to_clock_deg(S)
        wc_mag, wc_ang = to_clock_deg(Wc)

        # effect vector, drawn tip-to-tip from O to O+T
        if self.show_t:
            vib.append(dict(mag=tr_amp, angle=tr_ph, color=C_EFFECT,
                            tail=(o_amp, o_ph),
                            label=f"T {e_mag:.2f}@{e_ang:.0f}"))
        dirs.append(dict(angle=wc_ang, color=C_CORRECTION))

        pct = (e_mag / o_amp * 100.0) if o_amp > 1e-9 else 0.0
        self.corr_out.text = (
            f"[b][color={HEX_CORRECTION}]{wc_mag:.2f} @ {wc_ang:.1f}°[/color][/b]"
            f"  [color={MUTED_HEX}](~{clock_position(wc_ang)} o'clock)[/color]\n"
            f"[color={MUTED_HEX}]Effect of trial weight: {e_mag:.2f} @ "
            f"{e_ang:.1f}°  ({pct:.0f}% of original)\n"
            f"Sensitivity: {s_mag:.4f} per unit mass @ {s_ang:.1f}°[/color]")

        # ---- trim stage --------------------------------------------------
        trim_amp = self.trim_amp.value or 0.0
        trim_ph = self.trim_ph.value or 0.0
        if trim_amp > 1e-9:
            if self.show_trim:
                vib.append(dict(mag=trim_amp, angle=trim_ph, color=C_TRIMRUN,
                                label=f"Trim {trim_amp:.2f}@{trim_ph:.0f}"))
            R = to_complex(trim_amp, trim_ph)
            Wt = -R / S                     # extra weight, same sensitivity
            total = Wc + Wt                 # everything that ends up on the rotor
            wt_mag, wt_ang = to_clock_deg(Wt)
            tot_mag, tot_ang = to_clock_deg(total)
            dirs.append(dict(angle=wt_ang, color=C_TRIMWT))
            self.final_out.text = (
                f"[b][color={HEX_TRIMWT}]Add {wt_mag:.2f} @ {wt_ang:.1f}°"
                f"[/color][/b]\n"
                f"[color={MUTED_HEX}]On top of the correction already fitted.\n"
                f"Total on the rotor: {tot_mag:.2f} @ {tot_ang:.1f}°\n"
                f"Reusing the same sensitivity - no second trial run "
                f"needed.[/color]")
        else:
            self.final_out.text = (
                f"[color={MUTED_HEX}]No trim needed. Raise the trim-run "
                "amplitude to see what a second pass would ask for.[/color]")

        self.chart.set_data(vib, dirs, self.show_labels)
        self._set_legend(wc_ang, e_mag)

    def _set_legend(self, wc_ang, e_mag):
        parts = []
        if self.show_o:
            parts.append(f"[color={HEX_ORIGINAL}]● O[/color]")
        if self.show_ot:
            parts.append(f"[color={HEX_TRIALRUN}]● O+T[/color]")
        if self.show_t and e_mag:
            parts.append(f"[color={HEX_EFFECT}]● T (effect)[/color]")
        if wc_ang is not None:
            parts.append(f"[color={HEX_CORRECTION}]- - correction dir[/color]")
        self.legend.text = ("   ".join(parts) +
                            f"\n[color={MUTED_HEX}][size=11]Dashed lines show "
                            "weight direction only - mass is not to the "
                            "vibration scale.[/size][/color]")


# =====================================================================
# Root
# =====================================================================
# =====================================================================
# Fault Signature - waveform and spectrum synthesised from machine geometry
# =====================================================================
C_TRACE = (0.043, 0.431, 0.659)
C_MARK = (0.710, 0.325, 0.102)
BAND_V = (0.918, 0.957, 0.925, 1)
BAND_A = (0.969, 0.933, 0.957, 1)
BAND_H = (0.929, 0.937, 0.973, 1)
ZONE_COLOR = {"A": "1A7A4A", "B": "2F6F3E", "C": "9A5B00", "D": "A8291F"}


def _eng(v):
    """Short frequency label."""
    if v >= 1000:
        return ("%.0fk" % (v / 1000.0)) if v >= 10000 else ("%.1fk" % (v / 1000.0))
    if v >= 10:
        return "%.0f" % v
    return "%.1f" % v


def _sig(v, n=3):
    if v == 0:
        return "0"
    try:
        d = max(0, n - 1 - int(math.floor(math.log10(abs(v)))))
    except ValueError:
        return "0"
    return "%.*f" % (min(4, d), v)


class TraceChart(Widget):
    """Draws either the time waveform or the spectrum. Kept deliberately
    simple: one polyline for the trace plus a few grid lines, so a redraw
    costs almost nothing on a phone."""

    def __init__(self, kind, **kwargs):
        super().__init__(**kwargs)
        self.kind = kind            # "wave" or "spec"
        self.res = None
        self.xmin = 0.0
        self.xmax = 1.0
        self.show_bands = True
        self.show_marks = True
        self.labels = []
        self.bind(pos=self._redraw, size=self._redraw)

    def set_data(self, res, xmax, show_bands=True, show_marks=True, xmin=0.0):
        self.res = res
        self.xmin = max(0.0, xmin)
        self.xmax = max(self.xmin + 1e-9, xmax)
        self.show_bands = show_bands
        self.show_marks = show_marks
        self._redraw()

    # -- drawing ---------------------------------------------------------
    def _clear_labels(self):
        for lb in self.labels:
            self.remove_widget(lb)
        self.labels = []

    def _label(self, text, x, y, color, size=10, anchor="center"):
        lb = Label(text=text, font_size=dp(size), color=color,
                   size_hint=(None, None), size=(dp(70), dp(14)))
        lb.texture_update()
        w = max(dp(24), lb.texture_size[0] + dp(4))
        lb.size = (w, dp(14))
        if anchor == "center":
            lb.pos = (x - w / 2.0, y)
        elif anchor == "right":
            lb.pos = (x - w, y)
        else:
            lb.pos = (x, y)
        self.add_widget(lb)
        self.labels.append(lb)
        return lb

    def _redraw(self, *a):
        self.canvas.clear()
        self._clear_labels()
        r = self.res
        if r is None or self.width < dp(40) or self.height < dp(40):
            return

        L = dp(42)
        R = dp(8)
        B = dp(18)
        T = dp(16) if self.kind == "wave" else dp(22)
        x0 = self.x + L
        y0 = self.y + B
        pw = self.width - L - R
        ph = self.height - B - T
        if pw <= 1 or ph <= 1:
            return

        muted = (*COLOR_TEXT_MUTED[:3], 1)

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=(self.x, self.y), size=self.size)

            if self.kind == "spec" and self.show_bands and not r.env:
                # the band carrying the evidence moves as a bearing fails, so
                # shade the three measurement regions
                span = self.xmax - self.xmin
                for lo, hi, col in ((0.0, 1000.0, BAND_V),
                                    (1000.0, 5000.0, BAND_A),
                                    (5000.0, 1e12, BAND_H)):
                    if lo >= self.xmax or hi <= self.xmin:
                        continue
                    a1 = x0 + pw * (max(lo, self.xmin) - self.xmin) / span
                    a2 = x0 + pw * (min(hi, self.xmax) - self.xmin) / span
                    if a2 - a1 < 2:
                        continue
                    Color(*col)
                    Rectangle(pos=(a1, y0), size=(a2 - a1, ph))

            # grid
            Color(*COLOR_GRID_FAINT)
            for i in range(1, 4):
                yy = y0 + ph * i / 4.0
                Line(points=[x0, yy, x0 + pw, yy], width=1)
            for i in range(1, 5):
                xx = x0 + pw * i / 5.0
                Line(points=[xx, y0, xx, y0 + ph], width=1)

            Color(*COLOR_GRID)
            Line(points=[x0, y0 + ph, x0, y0, x0 + pw, y0], width=1.2)

        if self.kind == "wave":
            self._draw_wave(r, x0, y0, pw, ph, muted)
        else:
            self._draw_spec(r, x0, y0, pw, ph, muted)

    def _draw_wave(self, r, x0, y0, pw, ph, muted):
        x = r.wave
        n = len(x)
        yr = 0.0
        for v in x:
            if abs(v) > yr:
                yr = abs(v)
        yr = yr * 1.08 if yr > 0 else 1.0

        step = max(1, int(n / max(1.0, pw * 1.5)))
        pts = []
        i = 0
        while i < n:
            pts.append(x0 + pw * i / float(n - 1))
            pts.append(y0 + ph * 0.5 + (x[i] / yr) * ph * 0.5)
            i += step
        with self.canvas:
            Color(*C_TRACE)
            Line(points=pts, width=1.2)

        for i in range(5):
            v = yr - 2 * yr * i / 4.0
            self._label(_sig(v, 3), x0 - dp(4), y0 + ph * (1 - i / 4.0) - dp(7),
                        muted, 9, "right")
        tw = r.t_rec * 1000.0
        for i in range(3):
            xx = x0 + pw * i / 2.0
            self._label("%.0f" % (tw * i / 2.0), xx, y0 - dp(16), muted, 9)

    def _draw_spec(self, r, x0, y0, pw, ph, muted):
        lo, hi = self.xmin, self.xmax
        span = hi - lo
        k_lo = max(1, int(lo / r.df))
        k_hi = min(r.nb, int(hi / r.df) + 2)
        mx = 0.0
        for k in range(k_lo, k_hi):
            if r.mag[k] > mx:
                mx = r.mag[k]
        if mx <= 0:
            mx = 1.0
        top = mx * 1.1
        to_x = lambda hz: x0 + pw * (hz - lo) / span

        pts = []
        for k in range(k_lo, k_hi):
            xx = to_x(k * r.df)
            yy = y0 + ph * (r.mag[k] / top)
            pts.extend([xx, y0, xx, yy, xx, y0])
        with self.canvas:
            Color(*C_TRACE)
            if len(pts) >= 4:
                Line(points=pts, width=1.0)

        for i in range(5):
            self._label(_sig(top * (1 - i / 4.0), 3), x0 - dp(4),
                        y0 + ph * (1 - i / 4.0) - dp(7), muted, 9, "right")
        for i in range(4):
            hz = lo + span * i / 3.0
            self._label(_eng(hz), x0 + pw * i / 3.0, y0 - dp(16), muted, 9)

        if not self.show_marks:
            return
        marks = r.marks
        if r.env and r.ctx["def_hz"] > 0:
            # an envelope spectrum is read by its harmonic family
            marks = [(n * r.ctx["def_hz"], (("%dx" % n) if n > 1 else "") + r.ctx["def_name"])
                     for n in range(1, 7)]
        marks = sorted([m for m in marks if lo <= m[0] <= hi], key=lambda m: m[0])
        with self.canvas:
            Color(*C_MARK, 0.45)
            for hz, lab in marks:
                xx = to_x(hz)
                Line(points=[xx, y0, xx, y0 + ph], width=1)
        last = -1e9
        for hz, lab in marks:
            xx = to_x(hz)
            if xx - dp(20) <= last:
                continue
            self._label(lab, xx, y0 + ph + dp(2), (*C_MARK, 1), 9)
            last = xx + dp(20)


class LazySlider(BoxLayout):
    """A labelled slider that updates its readout while you drag but only
    recomputes once you let go. A full synthesis is a few hundred milliseconds
    on a phone, so recomputing on every pixel of travel would make the control
    feel broken."""

    def __init__(self, label_text, value, vmin, vmax, step, fmt, on_change,
                 on_live=None, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(56), spacing=dp(0), **kwargs)
        self._fmt = fmt
        self._on_change = on_change
        self._on_live = on_live      # optional: cheap update on every move
        self.value = value
        row = BoxLayout(size_hint_y=None, height=dp(20))
        self.lbl = Label(text=label_text, font_size=dp(11), bold=True,
                         color=COLOR_TEXT_MUTED, halign="left", valign="middle")
        self.lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.val = Label(text=fmt % value, font_size=dp(11), color=COLOR_TEXT,
                         halign="right", valign="middle", size_hint_x=None, width=dp(96))
        self.val.bind(size=lambda i, v: setattr(i, "text_size", v))
        row.add_widget(self.lbl)
        row.add_widget(self.val)
        self.add_widget(row)
        self.slider = Slider(min=vmin, max=vmax, value=value, step=step,
                             size_hint_y=None, height=dp(32),
                             cursor_size=(dp(22), dp(22)))
        self.slider.bind(value=self._live)
        self.slider.bind(on_touch_up=self._release)
        self.add_widget(self.slider)

    def _live(self, inst, v):
        self.value = v
        self.val.text = self._fmt % v
        if self._on_live is not None:
            self._on_live(v)

    def _release(self, inst, touch):
        # the slider grabs the touch that moves it, so the release belongs to
        # it even when the finger has drifted off the thin track (the usual
        # case on a phone). Checking the grab, not the position, also stops
        # the release being handled twice.
        if touch.grab_current is inst:
            self._on_change()
        return False

    def set_value(self, v):
        self.value = v
        self.slider.value = v
        self.val.text = self._fmt % v


class Segment(BoxLayout):
    """A compact segmented control."""

    def __init__(self, options, value, on_change, label_text=None, **kwargs):
        h = dp(56) if label_text else dp(34)
        super().__init__(orientation="vertical", size_hint_y=None, height=h,
                         spacing=dp(2), **kwargs)
        if label_text:
            lb = Label(text=label_text, font_size=dp(11), bold=True,
                       color=COLOR_TEXT_MUTED, halign="left", valign="middle",
                       size_hint_y=None, height=dp(18))
            lb.bind(size=lambda i, v: setattr(i, "text_size", v))
            self.add_widget(lb)
        row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(4))
        self.buttons = {}
        self._on_change = on_change
        self.value = value
        for key, text in options:
            btn = PillButton(text, accent=COLOR_ACCENT, inactive=COLOR_PANEL_BG,
                             text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            btn.bind(on_release=lambda i, k=key: self._pick(k))
            row.add_widget(btn)
            self.buttons[key] = btn
        self.add_widget(row)
        self._sync()

    def _pick(self, key):
        self.value = key
        self._sync()
        self._on_change(key)

    def set_value(self, key):
        self.value = key
        self._sync()

    def _sync(self):
        for k, b in self.buttons.items():
            b.set_active(k == self.value)


class Choice(BoxLayout):
    """A labelled dropdown. A segmented row cannot hold seven settings on a
    phone without becoming unreadable, and a control that cannot show the
    value the engine is using is worse than no control at all."""

    def __init__(self, label_text, options, value, on_change, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(58), spacing=dp(2), **kwargs)
        self._on_change = on_change
        self._by_text = dict((text, key) for key, text in options)
        self._by_key = dict(options)
        lb = Label(text=label_text, font_size=dp(11), bold=True,
                   color=COLOR_TEXT_MUTED, halign="left", valign="middle",
                   size_hint_y=None, height=dp(18))
        lb.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.add_widget(lb)
        self.spinner = Spinner(
            text=self._by_key.get(value, options[0][1]),
            values=[t for _, t in options],
            size_hint_y=None, height=dp(36), font_size=dp(13),
            background_normal="", background_down="",
            background_color=COLOR_PANEL_BG, color=COLOR_TEXT)
        self.spinner.bind(text=self._picked)
        self.add_widget(self.spinner)
        self.value = value
        self._syncing = False

    def _picked(self, inst, text):
        if self._syncing:
            return
        key = self._by_text.get(text)
        if key is None:
            return
        self.value = key
        self._on_change(key)

    def set_options(self, options, value):
        """Swap the list (e.g. faults that apply to the chosen machine)."""
        self._syncing = True
        self._by_text = dict((text, key) for key, text in options)
        self._by_key = dict(options)
        self.spinner.values = [t for _, t in options]
        self.value = value
        self.spinner.text = self._by_key.get(value, options[0][1])
        self._syncing = False

    def set_value(self, key):
        key = str(key)
        if key not in self._by_key:
            return
        self._syncing = True
        self.value = key
        self.spinner.text = self._by_key[key]
        self._syncing = False


class FaultSignatureScreen(Screen):
    """Pick a fault, see the waveform and spectrum it actually produces.

    Every frequency comes from the geometry set on this screen, and the three
    measurement units are derived from one another, so the relationships
    between them are real rather than drawn in."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg = Rectangle()
        # a Screen draws relative to itself, so its background starts at (0, 0)
        self.bind(pos=lambda w, v: setattr(w._bg, "pos", (0, 0)),
                  size=lambda w, v: setattr(w._bg, "size", v))
        self.st = fault_engine.Settings()
        self.st.lines = 400          # a phone sized record; 800+ still works
        self.res = None
        self._pending = None

        root = BoxLayout(orientation="vertical")
        scroll = ScrollView(do_scroll_x=False)
        self.col = BoxLayout(orientation="vertical", size_hint_y=None,
                             padding=[dp(12), dp(10)], spacing=dp(10))
        self.col.bind(minimum_height=self.col.setter("height"))
        scroll.add_widget(self.col)
        root.add_widget(scroll)
        self.add_widget(root)

        self._build_picker()
        self._build_charts()
        self._build_readout()
        self._build_controls()
        self._build_guide()

        self.apply_fault(self.st.fault_id, initial=True)

    # -- section helpers --------------------------------------------------
    def _head(self, text):
        lb = Label(text="[b]%s[/b]" % text, markup=True, font_size=dp(11),
                   color=COLOR_TEXT_MUTED, halign="left", valign="middle",
                   size_hint_y=None, height=dp(18))
        lb.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.col.add_widget(lb)

    def _card(self, height=None):
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        padding=dp(8), spacing=dp(6))
        with box.canvas.before:
            Color(*COLOR_PANEL_BG)
            box._bg = RoundedRectangle(radius=[dp(10)])
        box.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
                 size=lambda w, v: setattr(w._bg, "size", v))
        if height:
            box.height = height
        else:
            box.bind(minimum_height=box.setter("height"))
        self.col.add_widget(box)
        return box

    # -- fault picker ------------------------------------------------------
    def _build_picker(self):
        """One horizontally scrolling strip of chips. A vertical list of 19
        buttons would push the charts off a phone screen, and the whole point
        is to watch the trace change as you move between faults."""
        self._head("FAULT")
        strip = ScrollView(size_hint=(1, None), height=dp(42),
                           do_scroll_y=False, do_scroll_x=True,
                           bar_width=0)
        row = BoxLayout(orientation="horizontal", size_hint_x=None,
                        height=dp(38), spacing=dp(6), padding=[0, dp(2)])
        row.bind(minimum_width=row.setter("width"))
        self.fault_buttons = {}
        group = None
        for f in fault_engine.FAULTS:
            if group is not None and f["group"] != group:
                sep = Widget(size_hint_x=None, width=dp(1))
                with sep.canvas:
                    Color(*COLOR_BORDER)
                    sep._r = Rectangle()
                sep.bind(pos=lambda w, v: setattr(w._r, "pos", v),
                         size=lambda w, v: setattr(w._r, "size", v))
                row.add_widget(sep)
            group = f["group"]
            btn = PillButton(f["name"], accent=COLOR_ACCENT, inactive=COLOR_PANEL_BG,
                             text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            btn.label.font_size = dp(12)
            btn.label.texture_update()
            btn.size_hint_x = None
            btn.width = btn.label.texture_size[0] + dp(26)
            btn.bind(on_release=lambda i, fid=f["id"]: self.apply_fault(fid))
            row.add_widget(btn)
            self.fault_buttons[f["id"]] = btn
        strip.add_widget(row)
        self.col.add_widget(strip)
        self._strip = strip
        self._strip_row = row

    # -- charts ------------------------------------------------------------
    def _build_charts(self):
        self._head("TIME WAVEFORM")
        self.wave_meta = Label(text="", font_size=dp(10), color=COLOR_TEXT_MUTED,
                               halign="left", valign="middle",
                               size_hint_y=None, height=dp(14))
        self.wave_meta.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.col.add_widget(self.wave_meta)
        self.wave_chart = TraceChart("wave", size_hint_y=None, height=dp(180))
        self.col.add_widget(self.wave_chart)

        self.spec_head = Label(text="[b]SPECTRUM[/b]", markup=True, font_size=dp(11),
                               color=COLOR_TEXT_MUTED, halign="left", valign="middle",
                               size_hint_y=None, height=dp(18))
        self.spec_head.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.col.add_widget(self.spec_head)
        self.spec_meta = Label(text="", font_size=dp(10), color=COLOR_TEXT_MUTED,
                               halign="left", valign="middle",
                               size_hint_y=None, height=dp(14))
        self.spec_meta.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                            texture_size=lambda i, ts: setattr(i, "height", max(dp(14), ts[1])))
        self.col.add_widget(self.spec_meta)
        self.res_info = Label(text="", markup=True, font_size=dp(10),
                              color=COLOR_TEXT_MUTED, halign="left", valign="middle",
                              size_hint_y=None, height=dp(14))
        self.res_info.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                           texture_size=lambda i, ts: setattr(i, "height", max(dp(14), ts[1])))
        self.col.add_widget(self.res_info)
        self.spec_chart = TraceChart("spec", size_hint_y=None, height=dp(200))
        self.col.add_widget(self.spec_chart)

    def _build_readout(self):
        box = self._card()
        self.readout = Label(text="", markup=True, font_size=dp(12),
                             color=COLOR_TEXT, halign="left", valign="top",
                             size_hint_y=None)
        self.readout.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                          texture_size=lambda i, ts: setattr(i, "height", ts[1]))
        box.add_widget(self.readout)
        self.warn = Label(text="", markup=True, font_size=dp(11),
                          color=(0.60, 0.36, 0.02, 1), halign="left", valign="top",
                          size_hint_y=None, height=0)
        self.warn.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        box.add_widget(self.warn)

    # -- controls ----------------------------------------------------------
    def _build_controls(self):
        self._head("MACHINE")
        box = self._card()
        self.s_rpm = LazySlider("Shaft speed", self.st.rpm, 300, 6000, 15,
                                "%.0f rpm", self._changed)
        self.s_sev = LazySlider("Fault severity", self.st.sev, 0, 10, 0.5,
                                "%.1f / 10", self._changed)
        self.s_bg = LazySlider("Background level", self.st.bg, 0.2, 4, 0.1,
                               "x%.1f", self._changed)
        self.s_fr = LazySlider("Resonance", self.st.fr, 800, 6000, 100,
                               "%.0f Hz", self._changed)
        for w in (self.s_rpm, self.s_sev, self.s_bg, self.s_fr):
            box.add_widget(w)

        self._head("COMPONENTS")
        box = self._card()
        self.seg_brg = Choice("Bearing",
                              [(str(i), fault_engine.BEARINGS[i]["id"])
                               for i in range(len(fault_engine.BEARINGS))],
                              "0", self._set_bearing)
        self.seg_def = Segment([("bpfo", "Outer"), ("bpfi", "Inner"), ("bsf", "Ball")],
                               "bpfo", self._set_defect, "Bearing defect location")
        box.add_widget(self.seg_def)
        self.s_teeth = LazySlider("Pinion teeth", self.st.teeth, 12, 90, 1,
                                  "%.0f teeth", self._changed)
        self.s_blades = LazySlider("Blades / vanes", self.st.blades, 2, 24, 1,
                                   "%.0f blades", self._changed)
        self.s_poles = LazySlider("Motor poles", self.st.poles, 2, 12, 2,
                                  "%.0f poles", self._changed)
        for w in (self.s_teeth, self.s_blades, self.s_poles):
            box.add_widget(w)
        self.seg_lf = Segment([("50", "50 Hz"), ("60", "60 Hz")], "50",
                              self._set_lf, "Supply frequency")
        box.add_widget(self.seg_lf)

        self._head("ANALYSIS")
        box = self._card()
        self.seg_unit = Segment([("vel", "Velocity"), ("acc", "Accel"), ("dis", "Displ")],
                                "vel", self._set_unit, "Measurement")
        box.add_widget(self.seg_unit)
        self.seg_mode = Segment([("spec", "Normal"), ("env", "Envelope")], "spec",
                                self._set_mode, "Spectrum type")
        box.add_widget(self.seg_mode)
        self.seg_fmax = Choice("F-max", [("200", "200 Hz"), ("500", "500 Hz"),
                                         ("1000", "1 kHz"), ("2000", "2 kHz"),
                                         ("5000", "5 kHz"), ("10000", "10 kHz"),
                                         ("20000", "20 kHz"), ("40000", "40 kHz")],
                               "500", self._set_fmax)
        box.add_widget(self.seg_fmax)
        self.seg_lines = Choice("Lines of resolution",
                                [("200", "200"), ("400", "400"), ("800", "800"),
                                 ("1600", "1600"), ("3200", "3200")],
                                "400", self._set_lines)
        box.add_widget(self.seg_lines)
        self.seg_span = Choice("Waveform span",
                               [("0.5", "1/2 revolution"), ("1", "1 revolution"),
                                ("2", "2 revolutions"), ("4", "4 revolutions"),
                                ("8", "8 revolutions"), ("20", "20 revolutions"),
                                ("0", "Full record")],
                               "8", self._set_span)
        box.add_widget(self.seg_span)
        self.seg_aa = Segment([("on", "Filter on"), ("off", "Defeated")], "on",
                              self._set_aa, "Anti-alias filter")
        box.add_widget(self.seg_aa)

    # -- guide -------------------------------------------------------------
    def _build_guide(self):
        box = self._card()
        self.g_name = Label(text="", markup=True, font_size=dp(16), color=COLOR_TEXT,
                            halign="left", valign="top", size_hint_y=None, height=dp(24))
        self.g_name.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        box.add_widget(self.g_name)
        self.g_body = Label(text="", markup=True, font_size=dp(12.5),
                            color=COLOR_TEXT, halign="left", valign="top",
                            size_hint_y=None)
        self.g_body.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                         texture_size=lambda i, ts: setattr(i, "height", ts[1]))
        box.add_widget(self.g_body)

        self._head("CALCULATED FREQUENCIES")
        box = self._card()
        self.freq_tab = Label(text="", markup=True, font_size=dp(11.5),
                              color=COLOR_TEXT, halign="left", valign="top",
                              size_hint_y=None, font_name="RobotoMono-Regular")
        self.freq_tab.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                           texture_size=lambda i, ts: setattr(i, "height", ts[1]))
        box.add_widget(self.freq_tab)

    # -- control callbacks -------------------------------------------------
    def _set_bearing(self, k):
        self.st.bearing = int(k)
        self._changed()

    def _set_defect(self, k):
        self.st.defect = k
        self._changed()

    def _set_lf(self, k):
        self.st.lf = float(k)
        self._changed()

    def _set_unit(self, k):
        self.st.unit = k
        self._changed()

    def _set_mode(self, k):
        self.st.mode = k
        self._changed()

    def _set_fmax(self, k):
        self.st.fmax = float(k)
        self._changed()

    def _set_lines(self, k):
        self.st.lines = int(k)
        self._changed()

    def _set_span(self, k):
        self.st.wf_rev = float(k)
        self._changed()

    def _set_aa(self, k):
        self.st.aa = (k == "on")
        self._changed()

    def apply_fault(self, fid, initial=False):
        f = fault_engine.FAULT_BY_ID[fid]
        self.st.fault_id = fid
        for k, b in self.fault_buttons.items():
            b.set_active(k == fid)
        self._scroll_to_chip(fid)
        # open each fault where its signature is actually visible
        self.st.fmax = float(f.get("fmax", 500))
        self.seg_fmax.set_value(str(int(self.st.fmax)))
        self.st.lines = int(f.get("lines", 400))
        self.seg_lines.set_value(str(self.st.lines))
        self.st.wf_rev = float(f.get("wf_rev", 8))
        self.seg_span.set_value("%g" % self.st.wf_rev)
        self._changed()

    def _scroll_to_chip(self, fid):
        """Bring the selected chip into view - with 19 of them in one strip the
        active one is often off screen."""
        btn = self.fault_buttons.get(fid)
        strip = getattr(self, "_strip", None)
        row = getattr(self, "_strip_row", None)
        if btn is None or strip is None or row is None:
            return

        def _do(*_a):
            span = row.width - strip.width
            if span <= 0:
                strip.scroll_x = 0
                return
            centre = btn.x - row.x + btn.width * 0.5 - strip.width * 0.5
            strip.scroll_x = max(0.0, min(1.0, centre / span))

        Clock.schedule_once(_do, 0)

    def _changed(self, *a):
        """Recompute, but never more than once per frame burst - a synthesis
        is a few hundred milliseconds on a phone."""
        self.st.rpm = self.s_rpm.value
        self.st.sev = self.s_sev.value
        self.st.bg = self.s_bg.value
        self.st.fr = self.s_fr.value
        self.st.teeth = int(self.s_teeth.value)
        self.st.blades = int(self.s_blades.value)
        self.st.poles = int(self.s_poles.value)
        if self._pending is not None:
            self._pending.cancel()
        # a synthesis blocks the UI thread, and the heaviest combination takes
        # the better part of a second on a phone, so say so and give Kivy a
        # frame to draw that before the work starts
        self.readout.text = "[color=%s]Computing...[/color]" % MUTED_HEX
        self._pending = Clock.schedule_once(self._recompute, 0.03)

    def _recompute(self, *a):
        self._pending = None
        try:
            self.res = fault_engine.compute(self.st)
        except Exception as exc:
            self.readout.text = "[color=B00020]Could not build this signal: %s[/color]" % exc
            return
        self._refresh()

    # -- rendering ---------------------------------------------------------
    def _refresh(self):
        r = self.res
        st = self.st
        f = fault_engine.FAULT_BY_ID[st.fault_id]

        # waveform window: a spectrum needs a long record, a waveform a
        # readable one, so show a window of it as an analyst would
        full = r.wave
        if st.wf_rev > 0 and r.f1 > 0:
            want = int(round(st.wf_rev * r.fs / r.f1))
        else:
            want = len(full)
        n = max(32, min(len(full), want))
        shown = full[:n]
        tw = n / r.fs
        wr = fault_engine.Result()
        wr.wave = shown
        wr.t_rec = tw
        wr.env = r.env
        wr.marks = r.marks
        wr.ctx = r.ctx
        wr.df = r.df
        wr.nb = r.nb
        wr.mag = r.mag
        self.wave_chart.set_data(wr, tw)

        rev_shown = tw * r.f1
        rev_all = r.t_rec * r.f1
        unit = "g envelope" if r.env else fault_engine.UNIT_WAVE[st.unit]
        if n < len(full):
            span = "%.1f of %.1f rev - %.0f ms" % (rev_shown, rev_all, tw * 1000)
        else:
            span = "%.1f rev - %.0f ms" % (rev_all, r.t_rec * 1000)
        self.wave_meta.text = "%s - ms vs %s" % (span, unit)

        # spectrum
        if r.env:
            xmax = min(r.nb * r.df, max(12 * r.f1, 4.5 * r.ctx["def_hz"]))
        else:
            xmax = st.fmax
        self.spec_chart.set_data(r, xmax, show_bands=True, show_marks=st.marks)
        self.spec_head.text = "[b]%s[/b]" % ("ENVELOPE SPECTRUM" if r.env else "SPECTRUM")
        sunit = "g envelope" if r.env else fault_engine.UNIT_SPEC[st.unit]
        shown_lines = min(r.nb, int(xmax / r.df) + 1)
        T_rec = 1.0 / r.df
        fs_val = st.fmax * 2.56
        N_samp = int(round(fs_val * T_rec))
        self.spec_meta.text = ("df=%.3f Hz  T=%.2fs  fs=%.0f Hz  N=%d  %d lines  Hanning  Hz vs %s"
                               % (r.df, T_rec, fs_val, N_samp, shown_lines, sunit))

        # per-fault resolution check: does the current df resolve the key signature feature?
        fid = st.fault_id
        c = r.ctx
        f1 = c["f1"]
        broadband = fid in ("brg1", "cav")
        if fid in ("brg1", "brg2", "brg3", "brg4"):
            key_hz = c["def_hz"]
            key_name = "%s harmonic spacing" % c["def_name"]
        elif fid in ("gear", "gearcrack"):
            key_hz = f1
            key_name = "1X sideband spacing around GMF"
        elif fid == "elec":
            h = max(1, int(round(2.0 * c["lf"] / f1)))
            diff = abs(2.0 * c["lf"] - h * f1)
            key_hz = diff if diff > 0.01 else f1
            key_name = "|2×LF − %d×1X| separation" % h
        elif fid == "rotorbar":
            key_hz = max(0.05, c["ppf"])
            key_name = "PPF sideband spacing"
        elif fid in ("belt", "beltmis", "sheave"):
            key_hz = max(0.05, c["belt_hz"])
            key_name = "belt frequency"
        else:
            key_hz = f1
            key_name = "1X harmonic spacing"
        bins = key_hz / r.df if r.df > 0 else 0.0
        if broadband and not r.env:
            # no discrete lines to separate: F-max decides what you see here
            verdict_col = MUTED_HEX
            verdict_txt = "BROADBAND"
        elif bins >= 3.0:
            verdict_col = "1A7A4A"
            verdict_txt = "RESOLVED"
        elif bins >= 2.0:
            verdict_col = "CC8800"
            verdict_txt = "MARGINAL"
        else:
            need = st.fmax * 3.0 / key_hz
            opts = [n for n in (200, 400, 800, 1600, 3200) if n >= need]
            verdict_col = "A8291F"
            if opts:
                verdict_txt = "TOO COARSE - set %d lines" % opts[0]
            else:
                verdict_txt = "TOO COARSE - lower F-max"
        if broadband and not r.env:
            self.res_info.text = ("[color=%s][b]%s[/b][/color]  no discrete lines to "
                                  "separate - F-max matters here, not lines"
                                  % (verdict_col, verdict_txt))
        else:
            self.res_info.text = ("[color=%s][b]%s[/b][/color]  key spacing %.2f Hz "
                                  "(%s) = %.1f bins, need 3"
                                  % (verdict_col, verdict_txt, key_hz, key_name, bins))

        # readout
        zc = ZONE_COLOR.get(r.zone, "5B6472")
        bits = ["Shaft [b]%.0f rpm[/b] = %.2f Hz" % (st.rpm, r.f1),
                "Nyquist %.0f Hz" % (r.fs / 2.0),
                "Crest factor [b]%.2f[/b]" % r.crest]
        if not r.env:
            bits.insert(1, "Overall [b]%.2f mm/s RMS[/b] (10-%.0f Hz)  "
                           "[color=%s][b]Zone %s[/b][/color] %s"
                        % (r.overall, r.band_hi, zc, r.zone, r.zone_text))
        self.readout.text = "\n".join(bits)

        if r.aliased and not r.env and not st.aa:
            self.warn.text = ("[b]Aliasing:[/b] %s above the %.0f Hz Nyquist limit, "
                              "so it folds back and appears at a false low frequency. "
                              "Raise F-max or switch the filter on."
                              % (", ".join(r.aliased), r.fs / 2.0))
            self.warn.height = self.warn.texture_size[1] + dp(6)
        elif r.aliased and st.aa:
            self.warn.text = ("[b]Filtered out:[/b] %s above the %.0f Hz Nyquist limit, "
                              "so the anti-alias filter has removed it. Raise F-max to see it."
                              % (", ".join(r.aliased), r.fs / 2.0))
            self.warn.height = self.warn.texture_size[1] + dp(6)
        else:
            self.warn.text = ""
            self.warn.height = 0

        # guide
        self.g_name.text = "[b]%s[/b]  [size=11][color=%s]%s[/color][/size]" % (
            f["name"], MUTED_HEX, f["fam"])
        looks = "\n".join("  -  " + s for s in f["look"])
        self.g_body.text = (
            "%s\n\n"
            "[color=%s][b]IN THE SPECTRUM[/b][/color]\n%s\n\n"
            "[color=%s][b]IN THE TIME WAVEFORM[/b][/color]\n%s\n\n"
            "[color=%s]%s[/color]"
            % (f["note"], MUTED_HEX, looks, MUTED_HEX, f["wave"], MUTED_HEX, f["phys"])
        )

        c = r.ctx
        o = c["brg_o"]
        rows = [("Shaft speed (1X)", c["f1"], 1.0),
                ("BPFO  outer race", o["bpfo"] * c["f1"], o["bpfo"]),
                ("BPFI  inner race", o["bpfi"] * c["f1"], o["bpfi"]),
                ("BSF   roller", o["bsf"] * c["f1"], o["bsf"]),
                ("FTF   cage", o["ftf"] * c["f1"], o["ftf"]),
                ("GMF   gear mesh", c["teeth"] * c["f1"], float(c["teeth"])),
                ("BPF   blade pass", c["blades"] * c["f1"], float(c["blades"])),
                ("2 x line frequency", 2 * c["lf"], 2 * c["lf"] / c["f1"]),
                ("PPF   pole pass", c["ppf"], c["ppf"] / c["f1"])]
        lines = ["%-18s %9s %8s %8s" % ("", "Hz", "CPM", "Orders")]
        for name, hz, orders in rows:
            lines.append("%-18s %9.2f %8.0f %8.3f" % (name, hz, hz * 60.0, orders))
        self.freq_tab.text = "\n".join(lines)




# =====================================================================
# Shared plotting base for the rotor dynamics tools
# =====================================================================
C_ORBIT = (0.153, 0.306, 0.788)          # blue: the orbit and X probe
C_ORBIT_Y = (0.055, 0.561, 0.267)        # green: Y probe
C_CLEAR = (0.820, 0.180, 0.180)          # red: clearance / limits
C_OPBAND = (0.937, 0.953, 1.0, 1)        # operating speed range
C_PHASE = (0.502, 0.251, 0.682)          # purple: phase


def _nice_step(span, divs=4):
    """A 1-2-5 grid step that splits span into about `divs` divisions."""
    if span <= 0:
        return 1.0
    raw = span / float(divs)
    mag = 10.0 ** math.floor(math.log10(raw))
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= m * mag:
            return m * mag
    return 10.0 * mag


class _Plot(Widget):
    """Canvas widget with throwaway text labels, redrawn whole on change -
    the same lightweight pattern as TraceChart."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.labels = []
        self.bind(pos=self._redraw, size=self._redraw)

    def _reset(self):
        self.canvas.clear()
        for lb in self.labels:
            self.remove_widget(lb)
        self.labels = []

    def _label(self, text, x, y, color=None, size=10, anchor="center", bold=False):
        lb = Label(text=text, font_size=dp(size), bold=bold, markup=True,
                   color=color or (*COLOR_TEXT_MUTED[:3], 1),
                   size_hint=(None, None), size=(dp(70), dp(14)))
        lb.texture_update()
        w = max(dp(16), lb.texture_size[0] + dp(4))
        lb.size = (w, dp(14))
        if anchor == "center":
            lb.pos = (x - w / 2.0, y - dp(7))
        elif anchor == "right":
            lb.pos = (x - w, y - dp(7))
        else:
            lb.pos = (x, y - dp(7))
        self.add_widget(lb)
        self.labels.append(lb)
        return lb

    def _redraw(self, *a):
        pass


def _arrow_head(x, y, ang, size):
    sp = math.radians(26)
    Triangle(points=[x, y,
                     x - size * math.cos(ang - sp), y - size * math.sin(ang - sp),
                     x - size * math.cos(ang + sp), y - size * math.sin(ang + sp)])


# =====================================================================
# Orbit plot
# =====================================================================
class OrbitChart(_Plot):
    """Shaft orbit in true orientation, as seen from the driver end, with
    the two probes, the Keyphasor and the bearing clearance drawn in.
    Keyphasor marks follow the Bently convention: the trace is blanked for
    a moment just before each dot, so the orbit runs from blank to dot -
    that is the direction of precession."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.res = None
        self.revs = 4
        self.scale = "auto"
        self.compact = False

    def set_data(self, res, revs, scale="auto"):
        self.res = res
        self.revs = revs
        self.scale = scale
        self._redraw()

    def _redraw(self, *a):
        self._reset()
        r = self.res
        if r is None or self.width < dp(60) or self.height < dp(60):
            return
        spr = orbit_engine.SPR
        rot = r["settings"].rotor.rot
        n_show = min(r["n"], self.revs * spr + 1)
        oh, ov = r["oh"], r["ov"]
        mr = 0.0
        for i in range(n_show):
            m = math.hypot(oh[i], ov[i])
            if m > mr:
                mr = m
        clear = orbit_engine.CLEARANCE
        view = clear * 1.06 if self.scale == "clear" else max(mr * 1.15, 2.0)
        step = _nice_step(view, 4)
        view = step * math.ceil(view / step - 1e-9)
        cx, cy = self.center_x, self.center_y
        R = min(self.width, self.height) * 0.42
        k = R / view
        muted = (*COLOR_TEXT_MUTED[:3], 1)

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            # rings
            ring = step
            while ring <= view + 1e-9:
                Color(*(COLOR_GRID if abs(ring - view) < 1e-9 else COLOR_GRID_FAINT))
                Line(circle=(cx, cy, ring * k), width=1)
                ring += step
            Color(*COLOR_GRID_FAINT)
            Line(points=[cx - R, cy, cx + R, cy], width=1)
            Line(points=[cx, cy - R, cx, cy + R], width=1)
            # probe axes
            for name, deg in orbit_engine.PROBE_DEG.items():
                a = math.radians(deg)
                col = C_ORBIT if name == "X" else C_ORBIT_Y
                Color(*col, 0.35)
                Line(points=[cx - R * math.cos(a), cy - R * math.sin(a),
                             cx + R * 1.06 * math.cos(a), cy + R * 1.06 * math.sin(a)],
                     width=1)
                Color(*col, 1)
                px, py = cx + R * 1.1 * math.cos(a), cy + R * 1.1 * math.sin(a)
                Rectangle(pos=(px - dp(4), py - dp(4)), size=(dp(8), dp(8)))
            # Keyphasor probe at the top
            Color(*COLOR_TEXT[:3], 1)
            kx, ky = cx, cy + R * 1.1
            Triangle(points=[kx - dp(5), ky + dp(5), kx + dp(5), ky + dp(5), kx, ky - dp(3)])
            # clearance
            if clear <= view * 1.001:
                Color(*C_CLEAR, 0.7)
                Line(circle=(cx, cy, clear * k), width=1.3)

            # the orbit, blanked just before each Keyphasor event
            blank = max(2, spr // 14)
            seg = []
            Color(*C_ORBIT, 1)
            for i in range(n_show):
                in_blank = (i % spr) >= spr - blank
                if in_blank:
                    if len(seg) >= 4:
                        Line(points=seg, width=1.4 if not self.compact else 1.2)
                    seg = []
                    continue
                seg.extend([cx + oh[i] * k, cy + ov[i] * k])
            if len(seg) >= 4:
                Line(points=seg, width=1.4 if not self.compact else 1.2)
            # Keyphasor dots: one per revolution
            dr = dp(4.2) if not self.compact else dp(3.4)
            for j in range(self.revs):
                i = j * spr
                if i >= n_show:
                    break
                x, y = cx + oh[i] * k, cy + ov[i] * k
                Color(1, 1, 1, 1)
                Ellipse(pos=(x - dr - dp(1.5), y - dr - dp(1.5)),
                        size=(2 * dr + dp(3), 2 * dr + dp(3)))
                Color(*COLOR_TEXT[:3], 1)
                Ellipse(pos=(x - dr, y - dr), size=(2 * dr, 2 * dr))

            # rotation direction, top left corner
            ax0 = self.x + dp(20)
            ay0 = self.top - dp(20)
            rr = dp(10)
            pts = []
            for d in range(30, 331, 15):
                t = math.radians(d * rot)
                pts.extend([ax0 + rr * math.cos(t), ay0 + rr * math.sin(t)])
            Color(*COLOR_TEXT_MUTED[:3], 1)
            Line(points=pts, width=1.3)
            te = math.radians(330 * rot)
            tang = te + rot * math.pi / 2.0
            _arrow_head(ax0 + rr * math.cos(te), ay0 + rr * math.sin(te), tang, dp(6))

        if not self.compact:
            for name, deg in orbit_engine.PROBE_DEG.items():
                a = math.radians(deg)
                col = C_ORBIT if name == "X" else C_ORBIT_Y
                self._label("[b]%s[/b]" % name, cx + R * 1.1 * math.cos(a) + dp(11) * math.cos(a),
                            cy + R * 1.1 * math.sin(a) + dp(11) * math.sin(a), (*col, 1), 11)
            self._label("KP", cx + dp(16), cy + R * 1.1, muted, 9)
            self._label("rotation", self.x + dp(36), self.top - dp(20), muted, 9, "left")
        self._label("%s um/div" % _sig(step, 3), self.right - dp(6), self.y + dp(10),
                    muted, 9, "right")
        if clear <= view * 1.001 and not self.compact:
            a = math.radians(-60)
            self._label("clearance", cx + clear * k * math.cos(a) + dp(6),
                        cy + clear * k * math.sin(a) - dp(8), (*C_CLEAR, 1), 9, "left")


# =====================================================================
# X and Y timebase
# =====================================================================
class TimebaseChart(_Plot):
    """The two probe waveforms on one common scale, with the Keyphasor
    events marked - the raw material the orbit is built from."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.res = None
        self.revs = 4

    def set_data(self, res, revs):
        self.res = res
        self.revs = revs
        self._redraw()

    def _redraw(self, *a):
        self._reset()
        r = self.res
        if r is None or self.width < dp(60) or self.height < dp(60):
            return
        spr = orbit_engine.SPR
        n_show = min(r["n"], self.revs * spr + 1)
        L, Rm, B, T, gap = dp(38), dp(8), dp(16), dp(4), dp(10)
        x0 = self.x + L
        pw = self.width - L - Rm
        ph = (self.height - B - T - gap) / 2.0
        ym = 0.0
        for key in ("x", "y"):
            for i in range(n_show):
                if abs(r[key][i]) > ym:
                    ym = abs(r[key][i])
        step = _nice_step(ym * 1.1 if ym > 0 else 1.0, 2)
        top = step * math.ceil(ym * 1.05 / step) if ym > 0 else step
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        panels = (("x", "X", C_ORBIT, self.y + B + ph + gap),
                  ("y", "Y", C_ORBIT_Y, self.y + B))
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            for key, name, col, y0 in panels:
                Color(*COLOR_GRID_FAINT)
                for j in range(1, self.revs):
                    xx = x0 + pw * j / float(self.revs)
                    Line(points=[xx, y0, xx, y0 + ph], width=1)
                Color(*COLOR_GRID)
                Line(points=[x0, y0 + ph / 2.0, x0 + pw, y0 + ph / 2.0], width=1)
                Line(rectangle=(x0, y0, pw, ph), width=1)
                stp = max(1, int(n_show / max(1.0, pw * 1.5)))
                pts = []
                i = 0
                while i < n_show:
                    pts.extend([x0 + pw * i / float(n_show - 1),
                                y0 + ph / 2.0 + r[key][i] / top * ph / 2.0])
                    i += stp
                Color(*col, 1)
                Line(points=pts, width=1.2)
                Color(*COLOR_TEXT[:3], 1)
                for j in range(self.revs):
                    i = j * spr
                    xx = x0 + pw * i / float(n_show - 1)
                    yy = y0 + ph / 2.0 + r[key][i] / top * ph / 2.0
                    Ellipse(pos=(xx - dp(3), yy - dp(3)), size=(dp(6), dp(6)))
        for key, name, col, y0 in panels:
            self._label("[b]%s[/b]" % name, x0 + dp(4), y0 + ph - dp(7), (*col, 1), 10, "left")
            self._label(_sig(top, 3), x0 - dp(3), y0 + ph - dp(2), muted, 9, "right")
            self._label(_sig(-top, 3), x0 - dp(3), y0 + dp(2), muted, 9, "right")
        f1 = r["f1"]
        for j in range(self.revs + 1):
            if self.revs > 8 and j % 2:
                continue
            self._label("%d" % j, x0 + pw * j / float(self.revs), self.y + dp(8), muted, 9)
        self._label("rev  (%.0f ms)" % (1000.0 * self.revs / f1), x0 + pw, self.y + dp(8) + dp(11),
                    muted, 9, "right")


# =====================================================================
# Full spectrum
# =====================================================================
class FullSpectrumChart(_Plot):
    """Two-sided spectrum built from the X/Y pair: forward components (with
    rotation) to the right, reverse to the left. The one plot that answers
    'which way is it going round' for every frequency at once."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.res = None

    def set_data(self, res):
        self.res = res
        self._redraw()

    def _redraw(self, *a):
        self._reset()
        r = self.res
        if r is None or self.width < dp(60) or self.height < dp(40):
            return
        fs = r["fs"]
        orders, amp = fs["orders"], fs["amp"]
        L, Rm, B, T = dp(38), dp(8), dp(16), dp(18)
        x0, y0 = self.x + L, self.y + B
        pw, ph = self.width - L - Rm, self.height - B - T
        om = 4.0
        mx = max(amp) if amp else 1.0
        top = mx * 1.12 if mx > 0 else 1.0
        to_x = lambda o: x0 + pw * (o + om) / (2 * om)
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.973, 0.965, 0.988, 1)
            Rectangle(pos=(x0, y0), size=(pw / 2.0, ph))
            Color(*COLOR_GRID_FAINT)
            for o in range(-4, 5):
                Line(points=[to_x(o), y0, to_x(o), y0 + ph], width=1)
            Color(*COLOR_GRID)
            Line(points=[x0, y0, x0 + pw, y0], width=1.2)
            Line(points=[to_x(0), y0, to_x(0), y0 + ph], width=1.2)
            pts = []
            for o, a in zip(orders, amp):
                xx = to_x(o)
                pts.extend([xx, y0, xx, y0 + ph * a / top, xx, y0])
            Color(*C_TRACE, 1)
            if len(pts) >= 4:
                Line(points=pts, width=1.1)
        # label the main lines
        peaks = []
        for i in range(1, len(amp) - 1):
            if amp[i] >= amp[i - 1] and amp[i] >= amp[i + 1] and amp[i] > 0.06 * mx:
                peaks.append(i)
        peaks.sort(key=lambda i: -amp[i])
        used = []
        for i in peaks[:5]:
            xx = to_x(orders[i])
            if any(abs(xx - u) < dp(30) for u in used):
                continue
            used.append(xx)
            o = abs(orders[i])
            name = ("%dX" % round(o)) if abs(o - round(o)) < 0.02 else ("%.2fX" % o)
            self._label(name, xx, y0 + ph * amp[i] / top + dp(8), (*C_MARK, 1), 9)
        for o in range(-4, 5, 2):
            self._label("%dX" % o if o else "0", to_x(o), self.y + dp(8), muted, 9)
        self._label("REVERSE", x0 + dp(4), self.top - dp(9), muted, 9, "left")
        self._label("FORWARD", x0 + pw - dp(4), self.top - dp(9), muted, 9, "right")
        self._label(_sig(top, 3), x0 - dp(3), y0 + ph - dp(2), muted, 9, "right")


# =====================================================================
# Bode
# =====================================================================
class BodeChart(_Plot):
    """Phase lag above, amplitude below, against speed - the Bently layout.
    Phase lag increases DOWNWARD, so a roll through a critical reads as the
    phase trace falling while the amplitude rises. Tap or drag on it to move
    the cursor."""

    def __init__(self, on_cursor=None, **kwargs):
        super().__init__(**kwargs)
        self.sw = None
        self.cursor = None
        self.on_cursor = on_cursor
        self._geom = None

    def set_data(self, sw, cursor):
        self.sw = sw
        self.cursor = cursor
        self._redraw()

    # -- touch: the plot is the most natural place to choose a speed --------
    def _rpm_at(self, touch):
        g = self._geom
        if g is None:
            return None
        x0, pw, xmax, lo = g
        f = (touch.x - x0) / pw
        return max(lo, min(xmax, f * xmax))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or self.on_cursor is None:
            return super().on_touch_down(touch)
        touch.grab(self)
        rpm = self._rpm_at(touch)
        if rpm is not None:
            self.on_cursor(rpm)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            rpm = self._rpm_at(touch)
            if rpm is not None:
                self.on_cursor(rpm)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def _redraw(self, *a):
        self._reset()
        b = self.sw
        if b is None or self.width < dp(60) or self.height < dp(80):
            return
        st = b["settings"]
        rpm, amp, lag = b["rpm"], b["amp"], b["lag"]
        L, Rm, B, T, gap = dp(40), dp(8), dp(18), dp(6), dp(16)
        x0 = self.x + L
        pw = self.width - L - Rm
        hp = (self.height - B - T - gap) * 0.42
        ha = (self.height - B - T - gap) * 0.58
        ya = self.y + B
        yp = ya + ha + gap
        xmax = st.max_rpm
        self._geom = (x0, pw, xmax, st.slow_roll)
        to_x = lambda n: x0 + pw * n / xmax
        astep = _nice_step(max(amp) * 1.05, 4)
        atop = astep * math.ceil(max(amp) * 1.05 / astep)
        lo = 90.0 * math.floor(min(lag) / 90.0)
        hi = 90.0 * math.ceil(max(lag) / 90.0)
        if hi - lo < 180:
            hi = lo + 180
        dstep = 180.0 if hi - lo > 360 else 90.0
        to_yp = lambda d: yp + hp - hp * (d - lo) / (hi - lo)     # lag grows downward
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        crits = b.get("crits", [])
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            # operating range on both panels
            Color(*C_OPBAND)
            for y, h in ((ya, ha), (yp, hp)):
                Rectangle(pos=(to_x(st.op_min), y), size=(to_x(st.op_max) - to_x(st.op_min), h))
            Color(*COLOR_GRID_FAINT)
            v = astep
            while v < atop - 1e-9:
                yy = ya + ha * v / atop
                Line(points=[x0, yy, x0 + pw, yy], width=1)
                v += astep
            d = lo + dstep
            while d < hi:
                Line(points=[x0, to_yp(d), x0 + pw, to_yp(d)], width=1)
                d += dstep
            xs = _nice_step(xmax, 5)
            n = xs
            while n < xmax:
                for y, h in ((ya, ha), (yp, hp)):
                    Line(points=[to_x(n), y, to_x(n), y + h], width=1)
                n += xs
            Color(*COLOR_GRID)
            Line(rectangle=(x0, ya, pw, ha), width=1)
            Line(rectangle=(x0, yp, pw, hp), width=1)
            for c in crits:
                # half power line and points for each critical that has them
                if c["af"] is not None:
                    yy = ya + ha * (c["peak"] / math.sqrt(2.0)) / atop
                    Color(*C_MARK, 0.8)
                    Line(points=[to_x(c["n1"]), yy, to_x(c["n2"]), yy], width=1,
                         dash_length=dp(4), dash_offset=dp(3))
                    for nn in (c["n1"], c["n2"]):
                        Ellipse(pos=(to_x(nn) - dp(3), yy - dp(3)), size=(dp(6), dp(6)))
                Color(*C_CLEAR, 0.8)
                for nc in c["peaks"]:
                    Line(points=[to_x(nc), ya, to_x(nc), ya + ha], width=1)
                    Line(points=[to_x(nc), yp, to_x(nc), yp + hp], width=1)
            # traces
            pa, pp = [], []
            for k in range(len(rpm)):
                pa.extend([to_x(rpm[k]), ya + ha * amp[k] / atop])
                pp.extend([to_x(rpm[k]), to_yp(lag[k])])
            Color(*C_ORBIT, 1)
            Line(points=pa, width=1.4)
            Color(*C_PHASE, 1)
            Line(points=pp, width=1.4)
            # cursor
            if self.cursor is not None:
                kc = min(range(len(rpm)), key=lambda i: abs(rpm[i] - self.cursor))
                Color(*COLOR_TEXT[:3], 0.8)
                for y, h in ((ya, ha), (yp, hp)):
                    Line(points=[to_x(self.cursor), y, to_x(self.cursor), y + h], width=1.2)
                Color(*C_ORBIT, 1)
                Ellipse(pos=(to_x(self.cursor) - dp(3.5), ya + ha * amp[kc] / atop - dp(3.5)), size=(dp(7), dp(7)))
                Color(*C_PHASE, 1)
                Ellipse(pos=(to_x(self.cursor) - dp(3.5), to_yp(lag[kc]) - dp(3.5)), size=(dp(7), dp(7)))
        v = 0.0
        while v <= atop + 1e-9:
            self._label(_sig(v, 3), x0 - dp(3), ya + ha * v / atop, muted, 9, "right")
            v += astep
        # lag keeps counting past 360 through a second critical, as on a real Bode
        shift = 360.0 * math.ceil(-lo / 360.0) if lo < 0 else 0.0
        d = lo
        while d <= hi + 1e-6:
            self._label("%d" % int(round(d + shift)), x0 - dp(3), to_yp(d), muted, 9, "right")
            d += dstep
        n = 0.0
        while n <= xmax + 1e-6:
            self._label(_eng(n), to_x(n), self.y + dp(8), muted, 9, "right" if n >= xmax - 1e-6 else "center")
            n += xs
        self._label("[b]PHASE LAG[/b] deg, down", x0 + pw - dp(4), yp + hp - dp(8),
                    (*C_PHASE, 1), 9, "right")
        self._label("[b]AMPLITUDE[/b] 1X um pp", x0 + dp(4), ya + ha - dp(8), (*C_ORBIT, 1), 9, "left")
        self._label("operating", (to_x(st.op_min) + to_x(st.op_max)) / 2.0, ya + dp(8), muted, 8)
        for c in crits:
            self._label("%s %.0f" % ("1st" if c["mode"] == 1 else "2nd", c["nc"]), to_x(c["nc"]),
                        ya + ha + gap / 2.0, (*C_CLEAR, 1), 9)


TAU = 2.0 * math.pi
C_MODE1 = (0.122, 0.541, 0.357)      # green: first mode
C_MODE2 = (0.769, 0.416, 0.071)      # orange: second mode


class ShaftChart(_Plot):
    """The shaft between its two bearings, bent the way it is at the cursor
    speed: a family of dashed shapes over one revolution (like a mode shape
    figure), the envelope, and the shaft now, animated while on screen."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shape = None
        self.st = None
        self.full = 1.0
        self.theta = 0.6

    def set_data(self, shape, st, full):
        self.shape = shape
        self.st = st
        self.full = full or 1.0       # largest bend of the whole coast-down, um peak
        self._redraw()

    def set_theta(self, theta):
        """Redraw only the moving shaft: the cheap part, run every frame."""
        self.theta = theta
        self.canvas.after.clear()
        sh, st, geo = self.shape, self.st, getattr(self, "_geo", None)
        if sh is None or geo is None:
            return
        X, yc, k = geo
        d = sh["d"]
        n = len(d)
        e = cmath.exp(1j * theta)
        now = []
        for i, z in enumerate(d):
            now.extend([X(i / (n - 1.0)), yc + (z * e).real * k])
        iu = int(round(st.xu * (n - 1)))
        ip = int(round(st.xp * (n - 1)))
        with self.canvas.after:
            Color(*C_CLEAR, 1)
            Line(points=now, width=dp(1.8))
            Color(*C_ORBIT, 1)
            Line(points=[X(st.xp), self.top - dp(14), X(st.xp), now[2 * ip + 1]], width=1,
                 dash_length=dp(2), dash_offset=dp(2))
            Color(*COLOR_TEXT[:3], 1)
            Ellipse(pos=(X(st.xu) - dp(5), now[2 * iu + 1] - dp(5)), size=(dp(10), dp(10)))

    def _redraw(self, *a):
        self._reset()
        sh = self.shape
        if sh is None or self.width < dp(80) or self.height < dp(60):
            return
        st = self.st
        d = sh["d"]
        n = len(d)
        L, Rm = dp(26), dp(58)
        x0 = self.x + L
        pw = self.width - L - Rm
        yc = self.y + self.height / 2.0 + dp(6)
        amp = self.height / 2.0 - dp(30)
        # one scale for the whole coast-down, so the swing follows the amplitude
        k = amp / self.full
        X = lambda f: x0 + pw * f
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            # scale bar: full height is the largest bend of the coast-down
            sx = X(1) + dp(30)
            Color(*COLOR_TEXT_MUTED[:3], 1)
            Line(points=[sx, yc - amp, sx, yc + amp], width=1)
            Line(points=[sx - dp(4), yc - amp, sx + dp(4), yc - amp], width=1)
            Line(points=[sx - dp(4), yc + amp, sx + dp(4), yc + amp], width=1)
            # pinned bearings
            for f in (0.0, 1.0):
                bx = X(f)
                Color(*COLOR_TEXT_MUTED[:3], 1)
                Triangle(points=[bx, yc - dp(2), bx - dp(10), yc - dp(18), bx + dp(10), yc - dp(18)])
                Color(*COLOR_TEXT[:3], 1)
                Ellipse(pos=(bx - dp(3), yc - dp(3)), size=(dp(6), dp(6)))
            px = X(st.xp)
            Color(*C_ORBIT, 1)
            Triangle(points=[px, self.top - dp(14), px - dp(6), self.top - dp(4), px + dp(6), self.top - dp(4)])
        self._geo = (X, yc, k)
        self.set_theta(self.theta)
        sx = X(1) + dp(30)
        self._label("+%s" % _sig(self.full, 2), sx + dp(5), yc + amp, muted, 9, "left")
        self._label("-%s" % _sig(self.full, 2), sx + dp(5), yc - amp, muted, 9, "left")
        self._label("um", sx + dp(5), yc, muted, 9, "left")
        self._label("bearing", X(0), yc - dp(27), muted, 9)
        self._label("bearing", X(1), yc - dp(27), muted, 9)
        self._label("unbalance", X(st.xu), self.y + dp(9), (*COLOR_TEXT[:3], 1), 9)
        self._label("%s probe" % st.probe, px + dp(8), self.top - dp(9), (*C_ORBIT, 1), 9, "left")
        if sh["q2"] > 0.15 * sh["q1"]:
            self._label("node of mode 2", X(0.5), self.y + dp(9) if abs(st.xu - 0.5) > 0.15 else self.y + dp(22),
                        (*C_MODE2, 1), 9)


C_HIGH = (0.784, 0.208, 0.180)       # red: high spot
C_HEAVY = (0.086, 0.094, 0.153)      # near black: heavy spot


class EndViewChart(_Plot):
    """Looking along the shaft at the unbalance: the bearing bore, the orbit
    of the shaft centre, and the shaft disc whirling round it with the heavy
    spot (black) and high spot (red) on its rim. Drawn to one scale for the
    whole coast-down; set_theta moves only the disc, so animation is cheap."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sp = None
        self.st = None
        self.rmax = 1.0
        self.theta = 0.6

    def set_data(self, sp, st, rmax):
        self.sp = sp
        self.st = st
        self.rmax = rmax or 1.0
        self._redraw()

    def _geom(self):
        cx, cy = self.center_x, self.center_y + dp(4)
        R0 = min(self.width, self.height) * 0.42
        return cx, cy, R0, R0 * 0.62 / self.rmax, R0 * 0.16

    def _redraw(self, *a):
        self._reset()
        sp = self.sp
        if sp is None or self.width < dp(60) or self.height < dp(60):
            return
        cx, cy, R0, k, rd = self._geom()
        rot = self.st.rotor.rot
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*COLOR_GRID)
            Line(circle=(cx, cy, R0), width=1.3)
            Color(*COLOR_TEXT_MUTED[:3], 1)
            Line(points=[cx - dp(7), cy, cx + dp(7), cy], width=1)
            Line(points=[cx, cy - dp(7), cx, cy + dp(7)], width=1)
            # orbit of the shaft centre
            pts = []
            for i in range(65):
                e = cmath.exp(1j * TAU * i / 64.0)
                pts.extend([cx + (sp["h"] * e).real * k, cy + (sp["v"] * e).real * k])
            Color(*C_ORBIT, 1)
            Line(points=pts, width=1.3)
            # rotation arrow, top left
            ax0, ay0, rr = self.x + dp(16), self.top - dp(16), dp(8)
            arc = []
            for dd in range(30, 331, 15):
                t = math.radians(dd * rot)
                arc.extend([ax0 + rr * math.cos(t), ay0 + rr * math.sin(t)])
            Color(*COLOR_TEXT_MUTED[:3], 1)
            Line(points=arc, width=1.2)
        self._label("rotation", self.x + dp(28), self.top - dp(16), (*COLOR_TEXT_MUTED[:3], 1), 9, "left")
        self._label("orbit", self.x + dp(6), self.top - dp(32), (*C_ORBIT, 1), 9, "left")
        self.set_theta(self.theta)

    def set_theta(self, theta):
        self.theta = theta
        self.canvas.after.clear()
        sp = self.sp
        if sp is None:
            return
        cx, cy, R0, k, rd = self._geom()
        st = self.st
        rot = st.rotor.rot
        e = cmath.exp(1j * theta)
        sx, sy = cx + (sp["h"] * e).real * k, cy + (sp["v"] * e).real * k
        c = math.radians(orbit_engine.KP_DEG) - rot * math.radians(st.rotor.hs_deg)
        ah = c + rot * theta                              # heavy spot turns with the shaft
        al = ah - rot * math.radians(sp["lag"])           # high spot trails it
        with self.canvas.after:
            Color(*C_ORBIT, 0.8)
            Line(points=[cx, cy, sx, sy], width=1, dash_length=dp(3), dash_offset=dp(3))
            Color(*COLOR_PANEL_BG)
            Ellipse(pos=(sx - rd, sy - rd), size=(2 * rd, 2 * rd))
            Color(*COLOR_TEXT[:3], 1)
            Line(circle=(sx, sy, rd), width=1.4)
            Ellipse(pos=(sx - dp(2), sy - dp(2)), size=(dp(4), dp(4)))
            # arc along the rim from the heavy spot back to the high spot
            arc = []
            steps = 24
            for i in range(steps + 1):
                t = ah + (al - ah) * i / float(steps)
                arc.extend([sx + (rd + dp(7)) * math.cos(t), sy + (rd + dp(7)) * math.sin(t)])
            Color(*C_HIGH, 1)
            Line(points=arc, width=1.3)
            Color(*C_HEAVY, 1)
            Ellipse(pos=(sx + rd * math.cos(ah) - dp(6), sy + rd * math.sin(ah) - dp(6)), size=(dp(12), dp(12)))
            Color(*C_HIGH, 1)
            Ellipse(pos=(sx + rd * math.cos(al) - dp(6), sy + rd * math.sin(al) - dp(6)), size=(dp(12), dp(12)))


class LagCurveChart(_Plot):
    """Heavy spot to high spot angle against speed, increasing downward."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sw = None
        self.cursor = None

    def set_data(self, sw, cursor):
        self.sw = sw
        self.cursor = cursor
        self._redraw()

    def _redraw(self, *a):
        self._reset()
        b = self.sw
        if b is None or self.width < dp(60) or self.height < dp(50):
            return
        st = b["settings"]
        lag, rpm = b["spot_lag"], b["rpm"]
        L, Rm, T, B = dp(36), dp(8), dp(6), dp(18)
        x0, y0 = self.x + L, self.y + B
        pw, ph = self.width - L - Rm, self.height - T - B
        xmax = st.max_rpm
        lo = min(0.0, 90.0 * math.floor(min(lag) / 90.0))
        hi = max(180.0, 90.0 * math.ceil(max(lag) / 90.0))
        X = lambda n: x0 + pw * n / xmax
        Y = lambda d: y0 + ph - ph * (d - lo) / (hi - lo)       # lag grows downward
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*C_OPBAND)
            Rectangle(pos=(X(st.op_min), y0), size=(X(st.op_max) - X(st.op_min), ph))
            Color(*COLOR_GRID_FAINT)
            d = lo
            while d <= hi + 1e-6:
                Line(points=[x0, Y(d), x0 + pw, Y(d)], width=1)
                d += 90.0
            Color(*C_CLEAR, 0.7)
            for c in b["crits"]:
                Line(points=[X(c["nc"]), y0, X(c["nc"]), y0 + ph], width=1, dash_length=dp(3), dash_offset=dp(3))
            pts = []
            for n, l in zip(rpm, lag):
                pts.extend([X(n), Y(l)])
            Color(*C_HIGH, 1)
            Line(points=pts, width=1.5)
            if self.cursor is not None:
                kc = min(range(len(rpm)), key=lambda i: abs(rpm[i] - self.cursor))
                Color(*COLOR_TEXT[:3], 0.8)
                Line(points=[X(self.cursor), y0, X(self.cursor), y0 + ph], width=1.1)
                Color(*C_HIGH, 1)
                Ellipse(pos=(X(self.cursor) - dp(4), Y(lag[kc]) - dp(4)), size=(dp(8), dp(8)))
        d = lo
        while d <= hi + 1e-6:
            self._label("%d" % int(round(d)), x0 - dp(3), Y(d), muted, 9, "right")
            d += 90.0
        xs = _nice_step(xmax, 4)
        n = 0.0
        while n <= xmax + 1e-6:
            self._label(_eng(n), X(n), self.y + dp(7), muted, 9, "right" if n >= xmax - 1e-6 else "center")
            n += xs
        self._label("[b]HIGH SPOT LAG[/b] deg, down", x0 + pw - dp(4), y0 + ph - dp(8), (*C_HIGH, 1), 9, "right")


class ModeRefChart(_Plot):
    """A small reference figure of one mode shape of a pinned-pinned shaft."""

    def __init__(self, mode, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *a):
        self._reset()
        if self.width < dp(40) or self.height < dp(30):
            return
        x0, pw = self.x + dp(10), self.width - dp(20)
        yc, a = self.center_y, self.height / 2.0 - dp(6)
        col = C_MODE1 if self.mode == 1 else C_MODE2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*COLOR_GRID)
            Line(points=[x0, yc, x0 + pw, yc], width=1, dash_length=dp(4), dash_offset=dp(3))
            for j in range(7):
                s = math.cos(math.pi * j / 6.0)
                pts = []
                for q in range(31):
                    pts.extend([x0 + pw * q / 30.0, yc + a * s * math.sin(self.mode * math.pi * q / 30.0)])
                Color(*col, 1)
                if j in (0, 6):
                    Line(points=pts, width=dp(1.3))
                else:
                    Line(points=pts, width=1, dash_length=dp(3), dash_offset=dp(2))
            Color(*COLOR_TEXT_MUTED[:3], 1)
            for bx in (x0, x0 + pw):
                Triangle(points=[bx, yc - dp(1), bx - dp(5), yc - dp(9), bx + dp(5), yc - dp(9)])


# =====================================================================
# Screen base: the scrolling column, section heads and cards
# =====================================================================
class _ToolScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg = Rectangle()
        # a Screen draws relative to itself, so its background starts at (0, 0)
        self.bind(pos=lambda w, v: setattr(w._bg, "pos", (0, 0)),
                  size=lambda w, v: setattr(w._bg, "size", v))
        self._pending = None
        scroll = ScrollView(do_scroll_x=False)
        self.col = BoxLayout(orientation="vertical", size_hint_y=None,
                             padding=[dp(12), dp(10)], spacing=dp(10))
        self.col.bind(minimum_height=self.col.setter("height"))
        scroll.add_widget(self.col)
        self.scroll = scroll
        self.add_widget(scroll)

    def _head(self, text):
        lb = Label(text="[b]%s[/b]" % text, markup=True, font_size=dp(11),
                   color=COLOR_TEXT_MUTED, halign="left", valign="middle",
                   size_hint_y=None, height=dp(18))
        lb.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.col.add_widget(lb)
        return lb

    def _card(self):
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        padding=dp(8), spacing=dp(6))
        with box.canvas.before:
            Color(*COLOR_PANEL_BG)
            box._bg = RoundedRectangle(radius=[dp(10)])
        box.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
                 size=lambda w, v: setattr(w._bg, "size", v))
        box.bind(minimum_height=box.setter("height"))
        self.col.add_widget(box)
        return box

    def _text(self, parent, size=12, mono=False, color=None):
        lb = Label(text="", markup=True, font_size=dp(size), color=color or COLOR_TEXT,
                   halign="left", valign="top", size_hint_y=None)
        if mono:
            lb.font_name = "RobotoMono-Regular"
        lb.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                texture_size=lambda i, ts: setattr(i, "height", ts[1]))
        parent.add_widget(lb)
        return lb

    def _meta(self):
        lb = Label(text="", markup=True, font_size=dp(10), color=COLOR_TEXT_MUTED,
                   halign="left", valign="middle", size_hint_y=None, height=dp(14))
        lb.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                texture_size=lambda i, ts: setattr(i, "height", max(dp(14), ts[1])))
        self.col.add_widget(lb)
        return lb

    def _square(self, widget):
        """Keep a chart square to the column width so circles stay circles."""
        widget.size_hint_y = None
        self.col.bind(width=lambda c, w: setattr(widget, "height", max(dp(200), w - dp(24))))
        widget.height = dp(320)
        self.col.add_widget(widget)

    def _changed(self, *a):
        if self._pending is not None:
            self._pending.cancel()
        self._pending = Clock.schedule_once(self._recompute, 0.03)

    def _recompute(self, *a):
        pass


# =====================================================================
# Orbit tool
# =====================================================================
class OrbitScreen(_ToolScreen):
    """Two proximity probes 90 deg apart, a Keyphasor, and the orbit they
    trace. Every number in the readout is measured from the probe signals,
    not taken from the model."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.st = orbit_engine.OrbitSettings()
        self.st.comp = True
        self.res = None

        self._head("CONDITION")
        grid = GridLayout(cols=3, size_hint_y=None, height=dp(80), spacing=dp(6))
        self.cond_buttons = {}
        for c in orbit_engine.CONDITIONS:
            btn = PillButton(c["name"], accent=COLOR_ACCENT, inactive=COLOR_PANEL_BG,
                             text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            btn.label.font_size = dp(11.5)
            btn.label.halign = "center"
            btn.label.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
            btn.bind(on_release=lambda i, cid=c["id"]: self.apply_cond(cid))
            grid.add_widget(btn)
            self.cond_buttons[c["id"]] = btn
        self.col.add_widget(grid)

        self._head("ORBIT")
        self.orbit_meta = self._meta()
        self.orbit = OrbitChart()
        self._square(self.orbit)

        box = self._card()
        self.readout = self._text(box, 11.5, mono=True)
        self.verdict = self._text(box, 12)

        self._head("TIMEBASE - X AND Y PROBES")
        self.timebase = TimebaseChart(size_hint_y=None, height=dp(200))
        self.col.add_widget(self.timebase)

        self._head("FULL SPECTRUM")
        self.fs_meta = self._meta()
        self.fullspec = FullSpectrumChart(size_hint_y=None, height=dp(170))
        self.col.add_widget(self.fullspec)

        self._head("MACHINE")
        box = self._card()
        rot = self.st.rotor
        self.s_rpm = LazySlider("Shaft speed", self.st.rpm, 300, 12000, 50, "%.0f rpm", self._changed)
        self.s_sev = LazySlider("Severity", self.st.sev, 0, 10, 0.5, "%.1f / 10", self._changed)
        self.s_nc = LazySlider("First critical (mean)", rot.nc, 1000, 6000, 50, "%.0f rpm", self._changed)
        self.s_split = LazySlider("Support asymmetry (split)", rot.split * 100, 0, 40, 1,
                                  "%.0f %%", self._changed)
        self.s_zeta = LazySlider("Damping ratio", rot.zeta, 0.03, 0.5, 0.01, "%.2f", self._changed)
        for w in (self.s_rpm, self.s_sev, self.s_nc, self.s_split, self.s_zeta):
            box.add_widget(w)
        self.seg_rot = Segment([("1", "CCW"), ("-1", "CW")], "1", self._set_rot,
                               "Rotation (viewed from driver)")
        box.add_widget(self.seg_rot)

        self._head("DISPLAY")
        box = self._card()
        self.seg_filt = Segment([("direct", "Direct"), ("1x", "1X"), ("2x", "2X"),
                                 ("not1x", "Not-1X")], "direct", self._set_filt, "Filter")
        box.add_widget(self.seg_filt)
        self.ch_revs = Choice("Revolutions shown",
                              [("1", "1 revolution"), ("2", "2 revolutions"),
                               ("4", "4 revolutions"), ("8", "8 revolutions"),
                               ("16", "16 revolutions")], "4", self._set_revs)
        box.add_widget(self.ch_revs)
        self.seg_scale = Segment([("auto", "Fit orbit"), ("clear", "Bearing clearance")],
                                 "auto", self._set_scale, "Orbit scale")
        box.add_widget(self.seg_scale)
        self.seg_comp = Segment([("on", "Compensated"), ("off", "Raw")], "on",
                                self._set_comp, "Slow roll compensation")
        box.add_widget(self.seg_comp)
        self.s_ro = LazySlider("Slow roll runout + glitch", rot.runout, 0, 15, 0.5,
                               "%.1f um", self._changed)
        box.add_widget(self.s_ro)

        self._head("WHAT YOU ARE LOOKING AT")
        box = self._card()
        self.g_name = self._text(box, 14)
        self.g_body = self._text(box, 12)

        self.apply_cond("unbalance")

    # -- controls ---------------------------------------------------------
    def apply_cond(self, cid):
        c = orbit_engine.COND_BY_ID[cid]
        self.st.cond = cid
        for k, b in self.cond_buttons.items():
            b.set_active(k == cid)
        self.st.rpm = float(c["rpm"])
        self.st.sev = float(c["sev"])
        self.s_rpm.set_value(self.st.rpm)
        self.s_sev.set_value(self.st.sev)
        # each condition opens where it is easiest to read
        self.st.filt = "direct"
        self.seg_filt.set_value("direct")
        revs = 8 if cid in ("whirl", "whip") else (2 if cid == "rub" else 4)
        self.st.revs = revs
        self.ch_revs.set_value(str(revs))
        self._changed()

    def _set_rot(self, k):
        self.st.rotor.rot = int(k)
        self._changed()

    def _set_filt(self, k):
        self.st.filt = k
        self._changed()

    def _set_revs(self, k):
        self.st.revs = int(k)
        self._draw()

    def _set_scale(self, k):
        self._draw()

    def _set_comp(self, k):
        self.st.comp = (k == "on")
        self._changed()

    def _changed(self, *a):
        self.orbit_meta.text = "Computing..."
        super()._changed()

    def _recompute(self, *a):
        self._pending = None
        rot = self.st.rotor
        self.st.rpm = self.s_rpm.value
        self.st.sev = self.s_sev.value
        rot.nc = self.s_nc.value
        rot.split = self.s_split.value / 100.0
        rot.zeta = self.s_zeta.value
        rot.runout = self.s_ro.value
        try:
            self.res = orbit_engine.compute_orbit(self.st)
        except Exception as e:      # never leave the screen blank
            self.orbit_meta.text = "Could not build the orbit: %s" % e
            return
        self._draw()

    # -- rendering --------------------------------------------------------
    def _draw(self):
        r = self.res
        if r is None:
            return
        st = self.st
        rot = st.rotor
        c = orbit_engine.COND_BY_ID[st.cond]
        self.orbit.set_data(r, st.revs, self.seg_scale.value)
        self.timebase.set_data(r, st.revs)
        self.fullspec.set_data(r)

        filt = {"direct": "Direct (unfiltered)", "1x": "1X filtered", "2x": "2X filtered",
                "not1x": "Not-1X (1X removed)"}[st.filt]
        self.orbit_meta.text = ("%s - %d rev - %s - viewed from driver, %s rotation"
                                % (filt, st.revs, "compensated" if st.comp else "raw (runout included)",
                                   "CCW" if rot.rot > 0 else "CW"))
        self.fs_meta.text = "Built from the X/Y pair - forward = with rotation - um pp"

        X, Y = r["probes"]["X"], r["probes"]["Y"]

        def vec(p, key):
            a, ph = p[key + "_pp"], p[key + "_lag"]
            # below about 1 um the phase is noise, so do not print one
            return ("%.1f/%.0f" % (a, ph)) if a >= 1.0 else ("%.1f/ -" % a)
        lines = ["%-8s %10s %10s" % ("", "X probe", "Y probe"),
                 "%-8s %10s %10s" % ("Direct", "%.1f" % X["direct_pp"], "%.1f" % Y["direct_pp"]),
                 "%-8s %10s %10s" % ("1X", vec(X, "x1"), vec(Y, "x1")),
                 "%-8s %10s %10s" % ("2X", vec(X, "x2"), vec(Y, "x2")),
                 "um pp / phase lag deg"]
        self.readout.text = "\n".join(lines)

        fwd, rev = r["fwd1"], r["rev1"]
        if fwd + rev <= 1e-9:
            prec = "none"
        elif fwd >= rev:
            prec = "[color=1A7A4A][b]FORWARD[/b][/color]"
        else:
            prec = "[color=A8291F][b]REVERSE[/b][/color]"
        ell = (min(fwd, rev) / max(fwd, rev)) if max(fwd, rev) > 0 else 0.0
        shape = ("near circular" if fwd > 0 and rev / max(fwd, 1e-9) < 0.1 else
                 "line (all in one direction)" if ell > 0.85 else "elliptical")
        bits = ["1X precession %s  (forward %.1f / reverse %.1f um, %s)"
                % (prec, 2 * fwd, 2 * rev, shape)]
        f1 = r["f1"]
        crit_w, crit_s = rot.crit_weak(), rot.crit_stiff()
        bits.append("Split criticals %.0f and %.0f rpm - running at %.2f x mean critical"
                    % (crit_w, crit_s, st.rpm / rot.nc))
        if r["sub"] is not None:
            o, a, isf = r["sub"]
            bits.append("Subsynchronous [b]%.2fX[/b] = %.0f cpm, %.1f um pp, %s"
                        % (o, o * st.rpm, a, "forward" if isf else "reverse"))
        if r["whirl"] is not None:
            f_rpm, lock = r["whirl"]
            if lock > 0:
                bits.append("[color=A8291F][b]Whip:[/b][/color] locked at the first critical "
                            "(%.0f cpm) - no longer tracking speed" % f_rpm)
            else:
                bits.append("Whirl tracks speed at %.2fX; it locks into whip once that "
                            "reaches the critical, above %.0f rpm"
                            % (orbit_engine.WHIRL_RATIO, crit_w / orbit_engine.WHIRL_RATIO))
        use = 100.0 * r["max_r"] / orbit_engine.CLEARANCE
        bits.append("Orbit reaches %.0f%% of the bearing radial clearance (%.0f um)"
                    % (use, orbit_engine.CLEARANCE))
        self.verdict.text = "\n".join(bits)

        self.g_name.text = "[b]%s[/b]" % c["name"]
        looks = "\n".join("  -  " + s for s in c["orbit"])
        self.g_body.text = (
            "%s\n\n[color=%s][b]IN THE ORBIT[/b][/color]\n%s\n\n"
            "[color=%s][b]PHASE[/b][/color]\n%s\n\n"
            "[color=%s][b]TRY THIS[/b][/color]\n%s\n\n"
            "[color=%s]Reading direction: the trace is blanked just before each "
            "Keyphasor dot, so the shaft travels from blank to dot. Compare that "
            "with the rotation arrow: same way is forward precession, opposite "
            "is reverse.[/color]"
            % (c["note"], MUTED_HEX, looks, MUTED_HEX, c["phase"], MUTED_HEX, c["try"], MUTED_HEX))


# =====================================================================
# Resonance tool
# =====================================================================
class ResonanceScreen(_ToolScreen):
    """A coast-down through the first and second criticals of a flexible
    rotor, measured the way a monitoring system records it, then read like an
    analyst: each critical, its amplification factor by half power, its
    separation margin - and the shaft's own shape at any speed."""

    SCENARIOS = [
        ("Between criticals", {}),
        ("Unbalance at midspan", {"xu": 0.5}),
        ("Probe at midspan", {"xp": 0.5}),
        ("Probe near unbalance", {"xp": 0.2}),
        ("Too close to 2nd", {"nc2": 4300}),
        ("Split (Y probe)", {"probe": "Y"}),
        ("Heavily damped", {"zeta": 0.35, "split": 6, "ecc": 30}),
        ("Raw slow roll", {"comp": "off", "ro": 8}),
    ]
    DEFAULTS = {"nc1": 2400, "nc2": 7200, "zeta": 0.12, "split": 12, "ecc": 22, "xu": 0.3,
                "xp": 0.8, "hs": 60, "probe": "X", "comp": "on", "ro": 4, "omin": 3300,
                "omax": 3900, "max": "9000", "cursor": 3600}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.st = orbit_engine.SweepSettings()
        self.sw = None
        self.cursor = 3600.0
        self._cur_ev = None
        self._anim_ev = None
        self.theta = 0.6
        rot = self.st.rotor

        intro = self._text(self.col, 12.5)
        intro.text = ("A coast-down through the first and second critical speeds of a "
                      "flexible rotor, with the 1X vector measured at every speed step. "
                      "Below the Bode, the shaft itself: how it bends at the cursor speed.")

        self._head("SCENARIOS")
        grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter("height"))
        for name, settings in self.SCENARIOS:
            btn = PillButton(name, accent=COLOR_ACCENT, inactive=COLOR_PANEL_BG,
                             text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            btn.size_hint_y = None
            btn.height = dp(36)
            btn.label.font_size = dp(11.5)
            btn.bind(on_release=lambda i, s=settings: self.apply(s))
            grid.add_widget(btn)
        self.col.add_widget(grid)

        self._head("BODE")
        self.bode_meta = self._meta()
        self.bode = BodeChart(on_cursor=self._bode_tapped, size_hint_y=None, height=dp(320))
        self.col.add_widget(self.bode)
        box = self._card()
        self.s_cursor = LazySlider("Cursor speed (or tap the Bode)", self.cursor, 300,
                                   self.st.max_rpm, 10, "%.0f rpm", self._cursor_moved,
                                   on_live=self._cursor_moved)
        box.add_widget(self.s_cursor)
        self.verdict = self._text(box, 12)

        self._head("SHAFT CHARACTERISTICS")
        self.view = "side"
        self.seg_view = Segment([("side", "Side view"), ("end", "End view: heavy & high spot")],
                                "side", self._set_view)
        self.col.add_widget(self.seg_view)
        # the two views live in their own boxes; one at a time sits in the holder
        self.view_holder = BoxLayout(orientation="vertical", size_hint_y=None)
        self.col.add_widget(self.view_holder)
        side = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        side.bind(minimum_height=side.setter("height"))
        self.side_box = side
        self.shaft_meta = self._meta_in(side)
        self.shaft = ShaftChart(size_hint_y=None, height=dp(220))
        side.add_widget(self.shaft)
        self.mix = self._meta_in(side)
        refs = GridLayout(cols=2, size_hint_y=None, height=dp(78), spacing=dp(8))
        for i in (1, 2):
            cell = BoxLayout(orientation="vertical")
            cell.add_widget(ModeRefChart(i))
            cap = Label(text="", font_size=dp(10), color=COLOR_TEXT_MUTED, size_hint_y=None, height=dp(16))
            cell.add_widget(cap)
            setattr(self, "cap%d" % i, cap)
            refs.add_widget(cell)
        side.add_widget(refs)

        end = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        end.bind(minimum_height=end.setter("height"))
        self.end_box = end
        self.end_meta = self._meta_in(end)
        self.endview = EndViewChart(size_hint_y=None, height=dp(260))
        end.add_widget(self.endview)
        self.end_legend = self._meta_in(end)
        self.lagcurve = LagCurveChart(size_hint_y=None, height=dp(170))
        end.add_widget(self.lagcurve)
        self.end_text = self._meta_in(end, 11.5)
        hint = self._card_in(end)
        self.bal_hint = self._text(hint, 11.5)
        self._show_view()

        self._head("ORBIT AT THE CURSOR")
        box = self._card()
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(170), spacing=dp(8))
        self.mini = OrbitChart(size_hint_x=0.5)
        self.mini.compact = True
        row.add_widget(self.mini)
        self.cur_text = Label(text="", markup=True, font_size=dp(11.5), color=COLOR_TEXT,
                              halign="left", valign="middle", size_hint_x=0.5)
        self.cur_text.bind(size=lambda i, v: setattr(i, "text_size", v))
        row.add_widget(self.cur_text)
        box.add_widget(row)

        self._head("ROTOR")
        box = self._card()
        self.s_nc = LazySlider("1st critical (bow mode)", rot.nc, 1000, 6000, 50, "%.0f rpm", self._changed)
        self.s_nc2 = LazySlider("2nd critical (S mode)", self.st.nc2, 2000, 12000, 50, "%.0f rpm", self._changed)
        self.s_zeta = LazySlider("Damping ratio", rot.zeta, 0.03, 0.5, 0.01, "%.2f", self._changed)
        self.s_split = LazySlider("Support asymmetry (split)", rot.split * 100, 0, 40, 1,
                                  "%.0f %%", self._changed)
        self.s_ecc = LazySlider("Unbalance", rot.ecc * 2, 10, 120, 2, "%.0f um", self._changed)
        self.s_xu = LazySlider("Unbalance position along span", self.st.xu, 0.05, 0.95, 0.05,
                               "%.2f of span", self._changed)
        self.s_hs = LazySlider("Heavy spot (against rotation from notch)", rot.hs_deg,
                               0, 355, 5, "%.0f deg", self._changed)
        for w in (self.s_nc, self.s_nc2, self.s_zeta, self.s_split, self.s_ecc, self.s_xu, self.s_hs):
            box.add_widget(w)

        self._head("MEASUREMENT")
        box = self._card()
        self.seg_probe = Segment([("X", "X probe"), ("Y", "Y probe")], "X", self._set_probe, "Probe")
        box.add_widget(self.seg_probe)
        self.s_xp = LazySlider("Probe position along span", self.st.xp, 0.05, 0.95, 0.05,
                               "%.2f of span", self._changed)
        box.add_widget(self.s_xp)
        self.seg_comp = Segment([("on", "Compensated"), ("off", "Raw")], "on", self._set_comp,
                                "Slow roll vector (%.0f rpm)" % self.st.slow_roll)
        box.add_widget(self.seg_comp)
        self.s_ro = LazySlider("Slow roll runout + glitch", rot.runout, 0, 15, 0.5, "%.1f um",
                               self._changed)
        box.add_widget(self.s_ro)
        self.ch_max = Choice("Coast-down from",
                             [("4500", "4500 rpm"), ("6000", "6000 rpm"), ("9000", "9000 rpm"),
                              ("12000", "12000 rpm"), ("15000", "15000 rpm")], "9000", self._set_max)
        box.add_widget(self.ch_max)

        self._head("OPERATING RANGE")
        box = self._card()
        self.s_omin = LazySlider("Minimum operating speed", self.st.op_min, 300, 15000, 50,
                                 "%.0f rpm", self._changed)
        self.s_omax = LazySlider("Maximum continuous speed", self.st.op_max, 300, 15000, 50,
                                 "%.0f rpm", self._changed)
        box.add_widget(self.s_omin)
        box.add_widget(self.s_omax)

        self._head("READING IT")
        box = self._card()
        guide = self._text(box, 12)
        guide.text = (
            "[b]A critical[/b] is where the amplitude peaks AND the phase lag rolls about "
            "90 deg. Through each critical the lag grows by about 180 deg, so after the "
            "second it has rolled about 360 deg. A peak without the phase roll is not a "
            "rotor resonance.\n\n"
            "[b]Two criticals, two shapes[/b]: at the first the shaft bows into one arc, "
            "both halves together. At the second it bends into an S: the halves move "
            "against each other about a still middle (a node). Between them the shape is "
            "a mix - the shaft plot shows which mode dominates.\n\n"
            "[b]Where the unbalance is[/b]: it excites a mode in proportion to how much "
            "that mode moves there. At midspan (the node of the second mode) the second "
            "critical almost vanishes.\n\n"
            "[b]Where the probe is[/b]: it sees a mode in proportion to how much that mode "
            "moves there. A probe at midspan cannot see the second critical at all. If the "
            "probe and unbalance are on the same side of that node, the two modes cancel "
            "between the criticals: an antiresonance, where the amplitude dips and the "
            "phase rolls back.\n\n"
            "[b]Amplification factor[/b] = Nc / (N2 - N1), N1 and N2 the speeds at 0.707 of "
            "that critical's peak (dashed). About 1 / (2 x damping ratio).\n\n"
            "[b]Separation margin[/b]: every critical needs its own. AF below 2.5: none. "
            "2.5 to 3.55: 5%% below minimum, 15%% above maximum continuous. Above 3.55 up "
            "to 16%% below and 26%% above (the exact curve depends on the API edition; "
            "this tool applies those upper figures).\n\n"
            "[b]Split criticals[/b]: with the support stiffer one way, each critical "
            "splits. A half power AF across a double hump means nothing; the tool applies "
            "the largest margin instead.\n\n"
            "[b]Slow roll[/b]: switch to Raw and the Bode starts from the runout vector, "
            "not zero, and the low speed phase is the runout's, not the rotor's. The shaft "
            "plot does not change - runout is the probe track, not a bend in the shaft.")

        self._changed()

    # -- animation only while the screen is showing --------------------------
    def on_enter(self, *a):
        if self._anim_ev is None:
            self._anim_ev = Clock.schedule_interval(self._tick, 1 / 15.0)

    def on_leave(self, *a):
        if self._anim_ev is not None:
            self._anim_ev.cancel()
            self._anim_ev = None

    def _tick(self, dt):
        self.theta = (self.theta + dt * TAU / 1.6) % TAU
        if self.view == "side":
            self.shaft.set_theta(self.theta)
        else:
            self.endview.set_theta(self.theta)

    # -- side / end view -----------------------------------------------------
    def _meta_in(self, parent, size=10):
        lb = Label(text="", markup=True, font_size=dp(size), color=COLOR_TEXT_MUTED,
                   halign="left", valign="top", size_hint_y=None, height=dp(14))
        lb.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                texture_size=lambda i, ts: setattr(i, "height", max(dp(14), ts[1])))
        parent.add_widget(lb)
        return lb

    def _card_in(self, parent):
        box = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(8), spacing=dp(6))
        with box.canvas.before:
            Color(*COLOR_ACCENT_SOFT)
            box._bg = RoundedRectangle(radius=[dp(8)])
        box.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
                 size=lambda w, v: setattr(w._bg, "size", v))
        box.bind(minimum_height=box.setter("height"))
        parent.add_widget(box)
        return box

    def _show_view(self):
        h = self.view_holder
        h.clear_widgets()
        box = self.side_box if self.view == "side" else self.end_box
        h.add_widget(box)
        h.height = box.height
        box.bind(height=lambda w, v: setattr(h, "height", v) if w.parent is h else None)

    def _set_view(self, k):
        self.view = k
        self._show_view()
        self._draw_cursor()

    # -- controls ---------------------------------------------------------
    def apply(self, changes):
        v = dict(self.DEFAULTS)
        v.update(changes)
        self.s_nc.set_value(v["nc1"])
        self.s_nc2.set_value(v["nc2"])
        self.s_zeta.set_value(v["zeta"])
        self.s_split.set_value(v["split"])
        self.s_ecc.set_value(v["ecc"])
        self.s_xu.set_value(v["xu"])
        self.s_xp.set_value(v["xp"])
        self.s_hs.set_value(v["hs"])
        self.s_ro.set_value(v["ro"])
        self.s_omin.set_value(v["omin"])
        self.s_omax.set_value(v["omax"])
        self.seg_probe.set_value(v["probe"])
        self.st.probe = v["probe"]
        self.seg_comp.set_value(v["comp"])
        self.st.comp = v["comp"] == "on"
        self.ch_max.set_value(v["max"])
        self.st.max_rpm = float(v["max"])
        self.s_cursor.slider.max = self.st.max_rpm
        self.cursor = float(v["cursor"])
        self.s_cursor.set_value(self.cursor)
        self._changed()

    def _set_probe(self, k):
        self.st.probe = k
        self._changed()

    def _set_comp(self, k):
        self.st.comp = (k == "on")
        self._changed()

    def _set_max(self, k):
        self.st.max_rpm = float(k)
        self.s_cursor.slider.max = self.st.max_rpm
        if self.cursor > self.st.max_rpm:
            self.cursor = self.st.max_rpm
            self.s_cursor.set_value(self.cursor)
        self._changed()

    def _bode_tapped(self, rpm):
        self.s_cursor.set_value(round(rpm / 10.0) * 10.0)     # moves the slider, which redraws

    def _cursor_moved(self, *a):
        # many moves can arrive in one frame while dragging: draw once per frame
        self.cursor = self.s_cursor.value
        if self._cur_ev is None:
            self._cur_ev = Clock.schedule_once(self._draw_cursor_now, 0)

    def _draw_cursor_now(self, *a):
        self._cur_ev = None
        self._draw_cursor()

    def _changed(self, *a):
        self.bode_meta.text = "Computing..."
        super()._changed()

    def _recompute(self, *a):
        self._pending = None
        st = self.st
        rot = st.rotor
        rot.nc = self.s_nc.value
        if self.s_nc2.value < 1.3 * rot.nc:              # keep the two modes apart
            self.s_nc2.set_value(round(1.3 * rot.nc / 50.0) * 50.0)
        st.nc2 = self.s_nc2.value
        rot.zeta = self.s_zeta.value
        rot.split = self.s_split.value / 100.0
        rot.ecc = self.s_ecc.value / 2.0
        st.xu = self.s_xu.value
        st.xp = self.s_xp.value
        rot.hs_deg = self.s_hs.value
        rot.runout = self.s_ro.value
        st.op_min = min(self.s_omin.value, self.s_omax.value)
        st.op_max = max(self.s_omin.value, self.s_omax.value)
        try:
            self.sw = orbit_engine.sweep(st)
        except Exception as e:
            self.bode_meta.text = "Could not run the coast-down: %s" % e
            return
        b = self.sw
        self.bode_meta.text = ("%s probe at %.0f%% of span - %d steps, %.0f to %.0f rpm - %s - "
                               "operating range shaded"
                               % (st.probe, st.xp * 100, len(b["rpm"]), st.slow_roll, st.max_rpm,
                                  "slow roll compensated" if st.comp else "raw"))
        self.cap1.text = "1st mode (bow) - %.0f rpm" % rot.nc
        self.cap2.text = "2nd mode (S) - %.0f rpm" % st.nc2
        self._verdict()
        self._draw_cursor()

    def _draw_end(self):
        b, st = self.sw, self.st
        sp = orbit_engine.spots_at(st, self.cursor)
        self.endview.set_data(sp, st, b["spot_rmax"])
        self.endview.set_theta(self.theta)
        self.lagcurve.set_data(b, self.cursor)
        lag = sp["lag"]
        if lag < 30 or lag > 330:
            where = "the high spot is on the heavy spot - the shaft bulges towards the unbalance"
        elif lag < 150:
            where = "the high spot trails the heavy spot by about a quarter turn" + (
                " - the signature of a critical" if abs(lag - 90) < 20 else "")
        elif lag < 210:
            where = "the high spot is opposite the heavy spot - the shaft bulges away from the unbalance"
        else:
            where = "the high spot trails by three quarters of a turn"
        self.end_meta.text = ("Looking along the shaft at the unbalance (%.0f%% of span), viewed from "
                              "the driver end, %.0f rpm. The disc whirls round its orbit, drawn to one "
                              "scale for the whole coast-down." % (st.xu * 100, self.cursor))
        self.end_legend.text = ("[color=161827][b]black[/b][/color] heavy spot (where the unbalance is)   "
                                "[color=C8352E][b]red[/b][/color] high spot (the side that bulges out)   "
                                "lag [color=C8352E][b]%.0f deg[/b][/color]" % lag)
        swing = (self.cursor > 1.25 * st.rotor.nc and self.cursor < 0.9 * st.nc2
                 and abs(orbit_engine.mode_shape(2, st.xu)) > 0.2)
        self.end_text.text = ("High spot lags heavy spot by [b]%.0f deg[/b] against rotation: %s.%s"
                              % (lag, where,
                                 "\nBetween the criticals the second mode already pulls the shaft the "
                                 "other way here, so the high spot swings partly back before the second "
                                 "critical carries it round. Put the unbalance at midspan and the dip "
                                 "disappears." if swing else ""))
        corr = (st.rotor.hs_deg + 180.0) % 360.0
        hi_at = (st.rotor.hs_deg + lag) % 360.0
        wrong = (hi_at + 180.0) % 360.0
        err = abs((wrong - corr + 540.0) % 360.0 - 180.0)
        if err < 25:
            tail = ("close enough well below the first critical, which is why the rule of thumb "
                    "works on rigid rotors.")
        elif err > 150:
            tail = ("almost on the heavy spot itself, adding to the unbalance. Above a critical the "
                    "weight belongs near the high spot instead.")
        else:
            tail = ("so at this speed the weight position cannot be read off the high spot. It has "
                    "to come from a trial weight run (influence coefficients), which measures the "
                    "lag instead of assuming it.")
        self.bal_hint.text = ("[b]Balancing:[/b] the correction weight goes opposite the [b]heavy[/b] "
                              "spot, at %.0f deg against rotation from the notch. The vibration you "
                              "measure points at the [b]high[/b] spot (%.0f deg here). A weight opposite "
                              "the high spot would be %.0f deg out - %s" % (corr, hi_at, err, tail))

    def _verdict(self):
        b = self.sw
        st = self.st
        ok_hex, bad_hex = "1A7A4A", "A8291F"
        lines = []
        reasons = {"node": "the unbalance is at its node, so it is not excited",
                   "probe": "the probe is at its node, so it cannot see it",
                   "above": "it is above this coast-down - start it higher",
                   "damped": "no distinct peak - damped flat, treated as critically damped"}
        for i, name in ((0, "1st"), (1, "2nd")):
            c = b["by_mode"][i]
            if c is None:
                lines.append("[b]%s critical[/b] not seen: %s." % (name, reasons[orbit_engine.missing_reason(st, i)]))
                continue
            where = (" / ".join("%.0f" % p for p in c["peaks"])) if c["split"] else "%.0f" % c["nc"]
            if c["af"] is not None:
                af = "AF %.0f/(%.0f-%.0f) = [b]%.2f[/b]" % (c["nc"], c["n2"], c["n1"], c["af"])
            else:
                af = {"split": "AF n/a (split pair)", "edge": "AF n/a (sweep ends first)",
                      "overlap": "AF n/a (runs into the other peak)"}.get(c["why"], "AF below 2.5")
            if c["sm_side"] == "inside":
                mg = "inside the operating range"
            else:
                need = c["req_lo"] if c["sm_side"] == "below" else c["req_hi"]
                mg = "margin %.1f%% %s (needs %.0f%%)" % (c["sm"], c["sm_side"], need)
            col = ok_hex if c["sm_ok"] else bad_hex
            lines.append("[b]%s critical[/b] %s rpm, %.1f um pp - %s - [color=%s][b]%s %s[/b][/color]"
                         % (name, where, c["peak"], af, col, mg, "OK" if c["sm_ok"] else "- TOO CLOSE"))
        if len(b["crits"]) >= 2 and orbit_engine.antiresonance(st):
            lines.append("[size=11][color=%s]Antiresonance between the criticals: the probe and the "
                         "unbalance are on the same side of the 2nd mode's node, so the modes cancel "
                         "there and the phase rolls back instead of building to 360 deg.[/color][/size]" % MUTED_HEX)
        verdict = ("[color=%s][b]ACCEPTABLE[/b][/color]" % ok_hex) if b["ok"] else ("[color=%s][b]NOT ACCEPTABLE[/b][/color]" % bad_hex)
        lines.append("API check: %s - every critical against the operating range %.0f-%.0f rpm"
                     % (verdict, st.op_min, st.op_max))
        self.verdict.text = "\n".join(lines)

    def _draw_cursor(self):
        b = self.sw
        if b is None:
            return
        st = self.st
        self.bode.set_data(b, self.cursor)
        sh = orbit_engine.shape_at(st, self.cursor)
        self.shaft.set_data(sh, st, b["shape_max"])
        self._draw_end()
        self.shaft.set_theta(self.theta)
        tot = sh["q1"] + sh["q2"]
        p1 = int(round(100 * sh["q1"] / tot)) if tot > 0 else 0
        r1, r2 = self.cursor / st.rotor.nc, self.cursor / st.nc2
        if r1 < 0.8:
            where = "below the 1st critical: a gentle bow, in phase with the unbalance"
        elif r1 <= 1.2:
            where = "at the 1st critical: one big bow, both halves together"
        elif r2 < 0.8:
            where = "between the criticals: the bow has rolled behind the unbalance, the S mode is growing"
        elif r2 <= 1.2:
            where = "at the 2nd critical: an S shape about a still middle"
        else:
            where = "above the 2nd critical"
        self.shaft_meta.text = ("%.0f rpm, %s probe direction - %s. Drawn to one scale for the "
                                "whole coast-down, so the swing follows the real amplitude."
                                % (self.cursor, st.probe, where))
        mags = [abs(z) for z in sh["d"]]
        big = max(mags)
        at = mags.index(big) / float(len(mags) - 1)
        full = b["shape_max"] or 1.0
        self.mix.text = ("Largest bend now [b]%.1f um pp[/b] at %.0f%% of span - %.0f%% of the "
                         "coast-down maximum (%.0f um pp near %.0f rpm)\n"
                         "Mode mix: [color=1F8A5B][b]mode 1 %d%%[/b][/color]  "
                         "[color=C46A12][b]mode 2 %d%%[/b][/color]"
                         % (2 * big, at * 100, 100 * big / full, 2 * full, b["shape_max_rpm"], p1, 100 - p1))
        try:
            r = orbit_engine.orbit_at(st, self.cursor)
        except Exception:
            return
        self.mini.set_data(r, 1, "auto")
        p = r["probes"][st.probe]
        prec = ("[color=1A7A4A]forward[/color]" if r["fwd1"] >= r["rev1"] else "[color=A8291F]reverse[/color]")
        self.cur_text.text = ("[b]%.0f rpm[/b]\n%.2f x 1st, %.2f x 2nd\n\n"
                              "%s probe 1X\n[b]%.1f um pp / %.0f deg[/b]\n\n"
                              "1X precession %s"
                              % (self.cursor, r1, r2, st.probe, p["x1_pp"], p["x1_lag"], prec))



# =====================================================================
# Phase survey tool
# =====================================================================
C_H = (0.153, 0.306, 0.788)          # blue: horizontal
C_V = (0.055, 0.561, 0.267)          # green: vertical
C_A = (0.886, 0.400, 0.055)          # orange: axial
C_TACH = (0.784, 0.208, 0.180)       # red: tach pulse
C_STEEL = (0.80, 0.83, 0.87)
C_STEEL2 = (0.62, 0.66, 0.72)
HEX_H, HEX_V, HEX_A = "274EC9", "0E8F44", "E2660E"
REL_HEX = {"in": "1A7A4A", "anti": "A8291F", "quad": "274EC9", "mid": "9A5B00"}


def _dir_color(pid):
    if pid in ("FOOT", "BASE"):
        return C_V
    d = pid.lstrip("0123456789")[:1]
    return C_H if d == "H" else (C_V if d == "V" else C_A)


def _fmt_amp(v):
    return "%.1f" % v if v >= 10 else "%.2f" % v


class PhaseMapChart(_Plot):
    """The machine train with a phase clock above each bearing for H, V and
    A. 0 deg at the top, increasing clockwise. Tap a clock to measure there."""

    def __init__(self, on_pick, **kwargs):
        super().__init__(**kwargs)
        self.on_pick = on_pick
        self.scr = None
        self.hits = []

    def set_data(self, scr):
        self.scr = scr
        self._redraw()

    def needed_height(self, w):
        r = max(dp(12), min(dp(19), w * 0.052))
        step = 2 * r + dp(22)
        return dp(22) + dp(48) + dp(44) + r + 2 * step + r + dp(12)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        touch.grab(self)
        touch.ud["pm0"] = touch.pos
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            p0 = touch.ud.get("pm0", touch.pos)
            if abs(touch.x - p0[0]) < dp(14) and abs(touch.y - p0[1]) < dp(14):
                for pid, x, y, r in self.hits:
                    if (touch.x - x) ** 2 + (touch.y - y) ** 2 <= r * r:
                        self.on_pick(pid)
                        break
            return True
        return super().on_touch_up(touch)

    def _redraw(self, *a):
        self._reset()
        s = self.scr
        if s is None or self.width < dp(120):
            return
        st, T = s.st, phase_engine.TRAINS[s.st.train]
        w = self.width
        r = max(dp(12), min(dp(19), w * 0.052))
        step = 2 * r + dp(22)
        base = self.y + dp(22)
        cy = base + dp(48)
        X = lambda f: self.x + dp(14) + (w - dp(28)) * f
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        ink = (*COLOR_TEXT[:3], 1)
        self.hits = []
        fan = T["driven"] == "fan"
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*C_STEEL2, 1)
            Rectangle(pos=(X(0.02), base - dp(7)), size=(X(0.98) - X(0.02), dp(7)))
            # motor
            Color(*C_STEEL, 1)
            RoundedRectangle(pos=(X(0.06), cy - dp(30)), size=(X(0.40) - X(0.06), dp(60)), radius=[dp(5)])
            Color(*C_STEEL2, 1)
            f = 0.09
            while f < 0.38:
                Line(points=[X(f), cy - dp(26), X(f), cy + dp(26)], width=1)
                f += 0.03
            Rectangle(pos=(X(0.08), base), size=(X(0.38) - X(0.08), cy - dp(30) - base))
            # driven machine
            if not fan:
                Color(*C_STEEL, 1)
                Ellipse(pos=(X(0.715) - dp(34), cy - dp(34)), size=(dp(68), dp(68)))
                Rectangle(pos=(X(0.66), base), size=(X(0.77) - X(0.66), cy - dp(26) - base))
            else:
                Color(*C_STEEL2, 1)
                Rectangle(pos=(X(0.52), base), size=(X(0.78) - X(0.52), cy - dp(16) - base))
                Color(*C_STEEL, 1)
                Rectangle(pos=(X(0.86), cy - dp(46)), size=(dp(12), dp(92)))
                Color(*C_STEEL2, 1)
                Rectangle(pos=(X(0.86) + dp(12), cy - dp(40)), size=(dp(4), dp(80)))
            # shaft and coupling
            Color(*ink)
            Line(points=[X(0.03), cy, X(0.445), cy], width=dp(1.5))
            Line(points=[X(0.465), cy, X(0.93 if fan else 0.95), cy], width=dp(1.5))
            Color(*C_STEEL2, 1)
            Rectangle(pos=(X(0.43), cy - dp(10)), size=(X(0.48) - X(0.43), dp(20)))
            # bearings
            for fx in T["x"]:
                bx = X(fx)
                Color(*C_STEEL2, 1)
                Rectangle(pos=(bx - dp(9), cy - dp(13)), size=(dp(18), dp(26)))
                Color(*ink)
                Ellipse(pos=(bx - dp(3), cy - dp(3)), size=(dp(6), dp(6)))
        self._label("MOTOR", (X(0.06) + X(0.40)) / 2.0, cy + dp(18), muted, 9, bold=True)
        self._label("FAN" if fan else "PUMP", X(0.86) + dp(6) if fan else X(0.715),
                    cy + (dp(54) if fan else dp(16)), muted, 9, bold=True)
        for i, fx in enumerate(T["x"]):
            self._label(str(i + 1), X(fx), cy - dp(22), ink, 11, bold=True)
        # clocks: A, V, H stacked above each bearing
        for i, fx in enumerate(T["x"]):
            for j, d in enumerate(("A", "V", "H")):
                y = cy + dp(44) + r + j * step
                self._clock("%d%s" % (i + 1, d), X(fx), y, r)
        for j, (d, c) in enumerate((("A", C_A), ("V", C_V), ("H", C_H))):
            self._label(d, self.x + dp(4), cy + dp(44) + r + j * step, (*c, 1), 10, "left", True)

    def _clock(self, pid, x, y, r):
        s = self.scr
        sv = s.sv
        rd = sv.last(pid)
        col = _dir_color(pid)
        sel = pid == s.selected
        with self.canvas:
            Color(1, 1, 1, 1)
            Ellipse(pos=(x - r, y - r), size=(2 * r, 2 * r))
            if sel:
                Color(*COLOR_ACCENT)
                Line(circle=(x, y, r), width=dp(1.6))
            elif rd:
                Color(*col, 1)
                Line(circle=(x, y, r), width=dp(1))
            else:
                Color(*COLOR_BORDER)
                Line(circle=(x, y, r), width=1, dash_length=dp(3), dash_offset=dp(3))
            Color(*COLOR_TEXT_MUTED[:3], 1)
            Line(points=[x, y + r, x, y + r - dp(4)], width=1)
            if rd:
                ph = math.radians(s.shown(rd["lag"]))
                low = sv.is_low(pid)
                ex, ey = x + (r - dp(3)) * math.sin(ph), y + (r - dp(3)) * math.cos(ph)
                if low:
                    Color(*COLOR_TEXT_MUTED[:3], 1)
                    Line(points=[x, y, ex, ey], width=1, dash_length=dp(2), dash_offset=dp(2))
                else:
                    Color(*col, 1)
                    Line(points=[x, y, ex, ey], width=dp(1.3))
                Color(*col, 1)
                Ellipse(pos=(x - dp(2), y - dp(2)), size=(dp(4), dp(4)))
        if rd:
            self._label("%d" % round(s.shown(rd["lag"])), x, y - r - dp(7),
                        (*COLOR_TEXT_MUTED[:3], 1) if sv.is_low(pid) else (*COLOR_TEXT[:3], 1), 9, bold=True)
        else:
            self._label(pid, x, y, (*COLOR_TEXT_MUTED[:3], 1), 9)
        self.hits.append((pid, x, y, r + dp(6)))


class ReadingChart(_Plot):
    """Tach pulses and the selected point's waveform: raw in grey, the 1X
    component in colour, and the time from pulse to the next positive peak."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = None

    def set_data(self, data):
        self.data = data
        self._redraw()

    def _redraw(self, *a):
        self._reset()
        if self.width < dp(80) or self.height < dp(60):
            return
        L, Rm, T, B = dp(40), dp(8), dp(8), dp(38)
        x0, pw = self.x + L, self.width - L - Rm
        ph = self.height - T - B
        yb = self.y + B
        y0 = yb + ph / 2.0
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*COLOR_BORDER)
            Line(rectangle=(x0, yb, pw, ph), width=1)
            Color(*COLOR_GRID)
            Line(points=[x0, y0, x0 + pw, y0], width=1)
        d = self.data
        if d is None:
            self._label("No reading here yet - press Take reading", x0 + pw / 2.0, y0, muted, 10)
            return
        s, pid, rpm = d["s"], d["pid"], d["rpm"]
        SPR = phase_engine.SPR
        n = int(SPR * 2.25)
        c1 = s["c1"]
        x1 = []
        mx = 0.0
        for i in range(n):
            e = cmath.exp(1j * TAU * i / SPR)
            v = (c1 * e).real
            x1.append(v)
            mx = max(mx, abs(s["x"][i]), abs(v))
        mx = mx * 1.1 or 1.0
        X = lambda k: x0 + pw * k / (n - 1.0)
        Y = lambda v: y0 + (v / mx) * ph / 2.0
        col = _dir_color(pid)
        lag = s["lag"]
        kp = lag / 360.0 * SPR
        px, py = X(kp), Y(abs(c1))
        trev = 60000.0 / rpm
        dt = lag / 360.0 * trev
        ay = yb - dp(22)
        with self.canvas:
            Color(*C_TACH, 1)
            for k in range(3):
                xx = X(k * SPR)
                Line(points=[xx, yb, xx, yb - dp(12)], width=dp(1.4))
            Color(*COLOR_BORDER)
            raw = []
            for i in range(n):
                raw.extend([X(i), Y(s["x"][i])])
            Line(points=raw, width=dp(0.8))
            Color(*col, 1)
            f1 = []
            for i in range(n):
                f1.extend([X(i), Y(x1[i])])
            Line(points=f1, width=dp(1.3))
            Color(*COLOR_TEXT[:3], 1)
            Line(points=[px, py, px, yb], width=1, dash_length=dp(3), dash_offset=dp(3))
            Ellipse(pos=(px - dp(3.5), py - dp(3.5)), size=(dp(7), dp(7)))
            Line(points=[X(0), ay, px, ay], width=1)
            if px - X(0) > dp(10):
                _arrow_head(px, ay, 0.0, dp(6))
                _arrow_head(X(0), ay, math.pi, dp(6))
        self._label("tach", x0 - dp(4), yb - dp(6), (*C_TACH, 1), 9, "right", True)
        self._label("dt %.1f ms" % dt, (X(0) + px) / 2.0 + (dp(36) if px - X(0) < dp(70) else 0), ay + dp(8),
                    (*COLOR_TEXT[:3], 1), 9, bold=True)
        self._label(_sig(mx, 2), x0 - dp(3), yb + ph - dp(5), muted, 9, "right")
        self._label("-" + _sig(mx, 2), x0 - dp(3), yb + dp(5), muted, 9, "right")
        for k in range(3):
            self._label("%d ms" % round(k * trev), X(k * SPR), self.y + dp(6), muted, 9)


class OdsChart(_Plot):
    """Operating deflection shape from the survey: side view (V and A) and
    top view (H and A), motion exaggerated, animated while on screen."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scr = None
        self.theta = 0.9

    def set_data(self, scr):
        self.scr = scr
        self._redraw()

    def set_theta(self, th):
        self.theta = th
        self.canvas.after.clear()
        s = self.scr
        geo = getattr(self, "_geo", None)
        if s is None or geo is None:
            return
        X, strips, k = geo
        T = phase_engine.TRAINS[s.st.train]
        unit = s.st.unit
        sv = s.sv

        def m(rd):
            if rd and rd["setup"].unit == unit:
                return rd["amp"] * math.cos(th - math.radians(rd["lag"])) * k
            return 0.0
        with self.canvas.after:
            for d, yc in strips:
                pos = []
                for i, fx in enumerate(T["x"]):
                    b = i + 1
                    rr, ra = sv.last("%d%s" % (b, d)), sv.last("%dA" % b)
                    pos.append((X(fx) + m(ra), yc + m(rr), bool(rr or ra)))
                Color(*COLOR_TEXT[:3], 1)
                for a_, b_ in ((0, 1), (2, 3)):
                    a, b = pos[a_], pos[b_]
                    ext = 0.18
                    Line(points=[a[0] - (b[0] - a[0]) * ext, a[1] - (b[1] - a[1]) * ext,
                                 b[0] + (b[0] - a[0]) * ext, b[1] + (b[1] - a[1]) * ext], width=dp(1.6))
                for x, y, has in pos:
                    if has:
                        Color(*COLOR_ACCENT)
                        Ellipse(pos=(x - dp(5), y - dp(5)), size=(dp(10), dp(10)))
                    else:
                        Color(1, 1, 1, 1)
                        Ellipse(pos=(x - dp(5), y - dp(5)), size=(dp(10), dp(10)))
                        Color(*COLOR_TEXT_MUTED[:3], 1)
                        Line(circle=(x, y, dp(5)), width=1)

    def _redraw(self, *a):
        self._reset()
        s = self.scr
        if s is None or self.width < dp(80):
            return
        T = phase_engine.TRAINS[s.st.train]
        h = self.height
        X = lambda f: self.x + dp(22) + (self.width - dp(44)) * f
        strips = [("V", self.y + h * 0.73), ("H", self.y + h * 0.25)]
        mx = 0.0
        for kk in phase_engine.STD:
            rd = s.sv.last(kk)
            if rd and rd["setup"].unit == s.st.unit:
                mx = max(mx, rd["amp"])
        k = dp(20) / mx if mx > 0 else 0.0
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*COLOR_GRID)
            for d, yc in strips:
                Line(points=[X(0.02), yc, X(0.98), yc], width=1, dash_length=dp(4), dash_offset=dp(4))
        self._label("Side view: vertical and axial", self.x + dp(4), strips[0][1] + h * 0.2, muted, 9, "left", True)
        self._label("Top view: horizontal and axial", self.x + dp(4), strips[1][1] + h * 0.2, muted, 9, "left", True)
        for d, yc in strips:
            for i, fx in enumerate(T["x"]):
                self._label(str(i + 1), X(fx), yc - dp(17), muted, 9)
        if not mx:
            self._label("Measure the bearings to see how the machine moves",
                        self.center_x, self.center_y, muted, 10)
        self._geo = (X, strips, k)
        self.set_theta(self.theta)


class PhaseSurveyScreen(_ToolScreen):
    """A field phase survey on a motor and its driven machine: tap a point to
    take a reading, read the phase from the tach pulse and the waveform, and
    let the relationships between points point to the fault - with the traps
    that catch people in the field."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.st = phase_engine.Setup()
        self.sv = phase_engine.Survey()
        self.conv = "lag"
        self.selected = "3V"
        self.anim = True
        self._anim_ev = None
        self.theta = 0.9

        self._head("MACHINE AND FAULT")
        box = self._card()
        self.seg_train = Segment([(k, phase_engine.TRAINS[k]["name"]) for k in ("pump", "fan")],
                                 "pump", self._set_train)
        box.add_widget(self.seg_train)
        self.ch_fault = Choice("Fault", self._fault_options(), "static", self._set_fault)
        box.add_widget(self.ch_fault)
        self.s_sev = LazySlider("Severity", 5.0, 1, 10, 0.5, "%.1f / 10", self._machine_changed)
        self.s_rpm = LazySlider("Running speed", 1480, 600, 3000, 10, "%.0f rpm", self._machine_changed)
        box.add_widget(self.s_sev)
        box.add_widget(self.s_rpm)

        self._head("PHASE MAP")
        self._meta().text = ("Tap a clock to take a reading there. 0 deg at the top, clockwise. Viewed from "
                             "the motor non-drive end the shaft turns clockwise; H sensors on the right, V on "
                             "top, all axial sensors pointing towards the driven end.")
        self.pmap = PhaseMapChart(self._pick, size_hint_y=None, height=dp(330))
        self.col.bind(width=lambda c, w: setattr(self.pmap, "height", self.pmap.needed_height(w - dp(24))))
        self.col.add_widget(self.pmap)
        legend = Label(text="[color=%s]H horizontal[/color]   [color=%s]V vertical[/color]   [color=%s]A axial[/color]"
                       % (HEX_H, HEX_V, HEX_A), markup=True, font_size=dp(11), color=COLOR_TEXT,
                       size_hint_y=None, height=dp(16))
        self.col.add_widget(legend)
        self._head("EXTRA POINTS")
        grid = GridLayout(cols=3, size_hint_y=None, height=dp(84), spacing=dp(6))
        self.extra_btns = {}
        for pid, name in phase_engine.EXTRA:
            b = PillButton(name, accent=COLOR_ACCENT, inactive=COLOR_PANEL_BG,
                           text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            b.label.font_size = dp(11)
            b.label.markup = True
            b.bind(on_release=lambda i, p=pid: self._pick(p))
            grid.add_widget(b)
            self.extra_btns[pid] = b
        self.col.add_widget(grid)
        grid = GridLayout(cols=2, size_hint_y=None, height=dp(84), spacing=dp(6))
        for text, fn in (("Take reading", self._take), ("Repeat 5 times", self._repeat),
                         ("Measure all points", self._measure_all), ("Clear survey", self._clear)):
            b = PillButton(text, accent=COLOR_ACCENT, inactive=COLOR_ACCENT_SOFT,
                           text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            b.label.font_size = dp(12)
            b.set_active(False)
            b.bind(on_release=lambda i, f=fn: f())
            grid.add_widget(b)
        self.col.add_widget(grid)
        self.banner = self._meta()

        self._head("THE READING")
        self.wave_meta = self._meta()
        self.reading = ReadingChart(size_hint_y=None, height=dp(190))
        self.col.add_widget(self.reading)
        box = self._card()
        self.formula = self._text(box, 12)

        self._head("SURVEY SHEET")
        self.sheet_meta = self._meta()
        box = self._card()
        self.sheet = self._text(box, 11, mono=True)
        self._text(box, 10, color=COLOR_TEXT_MUTED).text = (
            "Amplitude / phase.  L = too low for a trustworthy phase,  S = repeat readings disagree "
            "by more than 20 deg,  * = taken with a different setup from the current one.  "
            "[ ] marks the selected point.")

        self._head("WHAT THE PHASES SAY")
        box = self._card()
        self.checks = self._text(box, 11.5)
        self._head("PATTERNS THAT FIT")
        box = self._card()
        self.match = self._text(box, 12)

        self._head("MOTION FROM YOUR READINGS")
        self._meta().text = ("Operating deflection shape drawn from the survey, motion exaggerated. "
                             "Hollow bearings have not been measured.")
        self.ods = OdsChart(size_hint_y=None, height=dp(220))
        self.col.add_widget(self.ods)
        self.seg_anim = Segment([("on", "Animate"), ("off", "Pause")], "on", self._set_anim)
        self.col.add_widget(self.seg_anim)

        self._head("MEASUREMENT TRAPS")
        box = self._card()
        self.seg_conv = Segment([("lag", "Lag"), ("lead", "Lead")], "lag", self._set_conv, "Phase convention")
        box.add_widget(self.seg_conv)
        self._text(box, 11, color=COLOR_TEXT_MUTED).text = (
            "Some instruments report lead (360 minus lag). Every absolute number changes and comparisons "
            "flip sign, so a team must agree on one before sharing surveys.")
        self.seg_unit = Segment([("vel", "Velocity"), ("acc", "Accel"), ("dis", "Displ")], "vel",
                                self._set_unit, "Measured as")
        box.add_widget(self.seg_unit)
        self._text(box, 11, color=COLOR_TEXT_MUTED).text = (
            "Acceleration leads velocity by 90 deg and displacement lags it by 90 deg. Change the unit "
            "mid-survey and every new reading is 90 deg off the old ones.")
        self.s_tape = LazySlider("Reflective tape moved by", 0, 0, 350, 10, "%.0f deg", self._set_tape)
        box.add_widget(self.s_tape)
        self._text(box, 11, color=COLOR_TEXT_MUTED).text = (
            "Moving the tape shifts every phase by the same amount. Relative phase between points "
            "survives; absolute phase does not. Move it halfway through a survey and the sheet is no "
            "longer comparable.")
        self.seg_axdir = Segment([("same", "Same direction"), ("into", "Into machine")], "same",
                                 self._set_axdir, "Driven-machine axial sensors")
        box.add_widget(self.seg_axdir)
        self._text(box, 11, color=COLOR_TEXT_MUTED).text = (
            "If the axial sensors on each side of the coupling face into their own machine, every "
            "driven-side axial reading gains 180 deg. Angular misalignment then shows 2A and 3A in "
            "phase, and the one rule that identifies it fails. Try it on Angular misalignment.")
        self.seg_flip = Segment([("0", "Normal"), ("1", "Reversed")], "0", self._set_flip,
                                "Selected sensor mounted")
        box.add_widget(self.seg_flip)
        self._text(box, 11, color=COLOR_TEXT_MUTED).text = (
            "An accelerometer on the opposite face of the housing reads 180 deg off. Applies to the "
            "point currently selected.")
        self._text(box, 12).text = "[b]Low amplitude[/b]"
        self._text(box, 11, color=COLOR_TEXT_MUTED).text = (
            "A neighbouring machine running at 97% of this speed leaks into every 1X reading. On a "
            "strong reading it hardly matters; on a weak one it drags the phase around. Use Repeat 5 "
            "times on 3A under static unbalance, then on 3V, and compare the scatter.")

        self._head("ABOUT THIS FAULT")
        box = self._card()
        self.g_name = self._text(box, 14)
        self.g_body = self._text(box, 12)

        # open on a realistic working state: a static unbalance survey already taken
        for k in phase_engine.STD:
            self.sv.take(k, self.st)
        self._render()

    # -- helpers ------------------------------------------------------------
    def _fault_options(self):
        return [(fid, name) for fid, name, trains in phase_engine.FAULTS if self.st.train in trains]

    def shown(self, lag):
        return phase_engine.wrap(360.0 - lag) if self.conv == "lead" else lag

    # -- controls -----------------------------------------------------------
    def _set_train(self, k):
        self.st.train = k
        opts = self._fault_options()
        if self.st.fault not in dict(opts):
            self.st.fault = "static"
        self.ch_fault.set_options(opts, self.st.fault)
        self.sv.clear()
        self._render()

    def _set_fault(self, k):
        self.st.fault = k
        self.sv.clear()
        self._render()

    def _machine_changed(self, *a):
        sev, rpm = self.s_sev.value, self.s_rpm.value
        if sev != self.st.sev or rpm != self.st.rpm:
            self.st.sev, self.st.rpm = sev, rpm
            self.sv.clear()
            self._render()

    def _set_conv(self, k):
        self.conv = k
        self._render()

    def _set_unit(self, k):
        self.st.unit = k
        self._render()

    def _set_tape(self, *a):
        self.st.tape = float(self.s_tape.value)
        self._render()

    def _set_axdir(self, k):
        self.st.axdir = k
        self._render()

    def _set_flip(self, k):
        if k == "1":
            self.st.flip[self.selected] = True
        else:
            self.st.flip.pop(self.selected, None)
        self._render()

    def _pick(self, pid):
        self.selected = pid
        self.seg_flip.set_value("1" if self.st.flip.get(pid) else "0")
        self.sv.take(pid, self.st)
        self._render()

    def _take(self):
        self.sv.take(self.selected, self.st)
        self._render()

    def _repeat(self):
        for _ in range(5):
            self.sv.take(self.selected, self.st)
        self._render()

    def _measure_all(self):
        phase_engine.measure_all(self.sv, self.st)
        self._render()

    def _clear(self):
        self.sv.clear()
        self._render()

    def _set_anim(self, k):
        self.anim = (k == "on")
        if self.anim:
            self.on_enter()
        else:
            self.on_leave()

    def on_enter(self, *a):
        if self.anim and self._anim_ev is None:
            self._anim_ev = Clock.schedule_interval(self._tick, 1 / 15.0)

    def on_leave(self, *a):
        if self._anim_ev is not None:
            self._anim_ev.cancel()
            self._anim_ev = None

    def _tick(self, dt):
        self.theta = (self.theta + dt * TAU / 2.2) % TAU
        self.ods.set_theta(self.theta)

    # -- rendering ----------------------------------------------------------
    def _render(self):
        st, sv = self.st, self.sv
        self.pmap.set_data(self)
        self.ods.set_data(self)
        for pid, name in phase_engine.EXTRA:
            rd = sv.last(pid)
            b = self.extra_btns[pid]
            b.label.text = name + ("  [b]%d[/b]" % round(self.shown(rd["lag"])) if rd else "")
            b.set_active(pid == self.selected)
        self.banner.text = ("[color=A8291F]This survey mixes readings taken with different setups (unit, "
                            "tape position or axial sensor direction). Phases from different setups cannot "
                            "be compared - clear the survey or re-measure.[/color]" if sv.mixed_setup() else "")
        self._render_reading()
        self._render_sheet()
        self._render_checks()
        f = phase_engine.FAULT_NAME[st.fault]
        p, lst = phase_engine.GUIDE[st.fault]
        self.g_name.text = "[b]%s[/b]" % f
        self.g_body.text = p + "\n\n" + "\n".join("  -  " + x for x in lst)

    def _render_reading(self):
        pid = self.selected
        rd = self.sv.last(pid)
        name = phase_engine.label(pid)
        if not rd:
            self.reading.set_data(None)
            self.wave_meta.text = "%s: not measured" % name
            self.formula.text = ""
            return
        s = phase_engine.synth(pid, rd["setup"], rd["seed"])
        self.reading.set_data({"s": s, "pid": pid, "rpm": rd["setup"].rpm})
        self.wave_meta.text = ("[b]%s[/b] - 1X filtered (coloured) over the raw signal (grey), "
                               "averaged over %d revolutions" % (name, phase_engine.NREV))
        trev = 60000.0 / rd["setup"].rpm
        lag = s["lag"]
        dt = lag / 360.0 * trev
        txt = "Phase lag = dt / T x 360 = %.1f / %.1f x 360 = [b]%d deg[/b]" % (dt, trev, round(lag))
        if self.conv == "lead":
            txt += "\nShown as lead: 360 - %d = [b]%d deg[/b]" % (round(lag), round(self.shown(lag)))
        txt += "\n1X amplitude [b]%s %s[/b]" % (_fmt_amp(rd["amp"]), phase_engine.UNIT_TXT[rd["setup"].unit])
        self.formula.text = txt

    def _cell(self, pid):
        sv = self.sv
        rd = sv.last(pid)
        sel = pid == self.selected
        if not rd:
            body = "-"
        else:
            tags = ""
            if sv.is_low(pid):
                tags += "L"
            if sv.scatter(pid) > 20:
                tags += "S"
            if rd["sig"] != self.st.sig(pid):
                tags += "*"
            body = "%s/%d%s" % (_fmt_amp(rd["amp"]), round(self.shown(rd["lag"])), tags)
        body = ("[" + body + "]") if sel else (" " + body + " ")
        return body

    def _render_sheet(self):
        st, sv = self.st, self.sv
        drv = phase_engine.TRAINS[st.train]["driven"]
        lines = ["%-7s%-13s%-13s%s" % ("", " H", " V", " A")]
        for b in range(1, 5):
            nm = "%d %s" % (b, "motor" if b <= 2 else drv)
            lines.append("%-7s%-13s%-13s%s" % (nm, self._cell("%dH" % b), self._cell("%dV" % b), self._cell("%dA" % b)))
        for pid, name in phase_engine.EXTRA:
            if sv.r.get(pid):
                lines.append("%-14s%s" % (name, self._cell(pid)))
        self.sheet.text = "\n".join(lines).replace("[", "&bl;").replace("]", "&br;")
        n = len(sv.r)
        self.sheet_meta.text = ("%d points, %s, phase %s" % (n, phase_engine.UNIT_TXT[st.unit], self.conv)
                                if n else "Empty - take readings on the phase map")

    def _render_checks(self):
        st, sv = self.st, self.sv
        A = phase_engine.analyse(sv)
        if not A["checks"]:
            self.checks.text = "[color=%s]Take readings at two or more related points.[/color]" % MUTED_HEX
        else:
            out = []
            for c in A["checks"]:
                d = c.get("d")
                t = "[color=%s][b]%s[/b][/color]" % (REL_HEX[c["k"]], c["t"])
                if d is not None:
                    t += " [color=%s](%+d)[/color]" % (MUTED_HEX, round(d))
                if c["extra"]:
                    t += " [color=%s]%s[/color]" % (MUTED_HEX, c["extra"])
                out.append("[b]%s[/b]   %s" % (c["label"], t))
            self.checks.text = "\n".join(out)
        m, ok = sv.level(st)
        if A["checks"] and not ok:
            self.match.text = ("[color=%s]Highest reading is only %s %s. At this level there is no fault to "
                               "diagnose: the phases just describe residual unbalance and background, so no "
                               "pattern is matched.[/color]" % (MUTED_HEX, _fmt_amp(m), phase_engine.UNIT_TXT[st.unit]))
            return
        P_ = phase_engine.patterns(sv, A, st.train)
        good = [p for p in P_ if p["score"] >= 0.75]
        if not good:
            if P_:
                p = P_[0]
                self.match.text = ("[color=%s]No pattern fits well yet. Closest: %s (%d of %d rules).[/color]"
                                   % (MUTED_HEX, p["n"], len(p["yes"]), len(p["yes"]) + len(p["no"])))
            else:
                self.match.text = "[color=%s]Not enough readings to compare against any pattern.[/color]" % MUTED_HEX
            return
        out = []
        for i, p in enumerate(good[:3]):
            head = "[b]%s[/b]" % p["n"] if i == 0 else "[color=%s][b]%s[/b][/color]" % (MUTED_HEX, p["n"])
            ev = "Fits: " + ", ".join(p["yes"])
            if p["no"]:
                ev += ". Against: " + ", ".join(p["no"])
            if p["missing"]:
                ev += ". Still to measure: " + ", ".join(p["missing"])
            out.append("%s  [color=%s]%d of %d rules[/color]\n[size=%d]%s[/size]"
                       % (head, MUTED_HEX, len(p["yes"]), len(p["yes"]) + len(p["no"]), int(dp(11)), ev))
        out.append("[color=%s][size=%d]Rules of thumb, not proof: confirm with the spectrum, amplitudes and "
                   "the machine's history.[/size][/color]" % (MUTED_HEX, int(dp(10.5))))
        self.match.text = "\n\n".join(out)


# =====================================================================
# Waveform builder tool
# =====================================================================
C_WAVES = [(0.153, 0.306, 0.788), (0.055, 0.561, 0.267), (0.886, 0.400, 0.055),
           (0.502, 0.251, 0.682), (0.000, 0.533, 0.565)]
HEX_WAVES = ["274EC9", "0E8F44", "E2660E", "8040AE", "008890"]
C_MERGED = (0.06, 0.09, 0.16)
C_CURSOR = (0.820, 0.180, 0.180)


def _trace(points_fn, x0, pw, y0, sc, cols, env):
    """Turn a min/max envelope into one Kivy line."""
    pts = []
    for k, (first, lo, hi) in enumerate(env):
        x = x0 + pw * k / float(cols)
        if k == 0:
            pts.extend([x, y0 + first * sc])
        pts.extend([x, y0 + hi * sc, x, y0 + lo * sc])
    return pts


class MiniWave(_Plot):
    def __init__(self, idx, **kwargs):
        super().__init__(**kwargs)
        self.idx = idx
        self.w = None

    def set_data(self, w):
        self.w = w
        self._redraw()

    def _redraw(self, *a):
        self._reset()
        w = self.w
        if w is None or self.width < dp(40):
            return
        T = 3.0 / w.f if w.f > 0 else 0.05
        y0 = self.center_y
        sc = (self.height / 2.0 - dp(5)) / 10.0
        cols = max(2, int(self.width / 2))
        env = wave_engine.envelope(lambda t: wave_engine.value(w.a, w.f, t), 0.0, T, cols, 4)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*COLOR_GRID)
            Line(points=[self.x, y0, self.right, y0], width=1)
            Color(*(C_WAVES[self.idx] if w.on else COLOR_TEXT_MUTED[:3]), 1)
            Line(points=_trace(None, self.x, self.width, y0, sc, cols, env), width=dp(1.1))
        self._label("3 cycles, %s ms" % wave_engine.fmt_ms(T * 1000) if w.f > 0 else "50 ms",
                    self.right - dp(2), self.y + dp(7), (*COLOR_TEXT_MUTED[:3], 1), 9, "right")


class MergedChart(_Plot):
    """The five waves overlaid, or their sum, for the zoomed part of the
    record, with two time cursors."""

    def __init__(self, scr, **kwargs):
        super().__init__(**kwargs)
        self.scr = scr
        self._geom = None

    def _frac(self, touch):
        if self._geom is None:
            return None
        x0, pw = self._geom
        return max(0.0, min(1.0, (touch.x - x0) / pw))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or not self.scr.show_cur:
            return super().on_touch_down(touch)
        p = self._frac(touch)
        if p is None:
            return super().on_touch_down(touch)
        cur = self.scr.cur
        touch.grab(self)
        touch.ud["wc"] = 0 if abs(p - cur[0]) <= abs(p - cur[1]) else 1
        cur[touch.ud["wc"]] = p
        self.scr._cursor_moved()
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            p = self._frac(touch)
            if p is not None:
                self.scr.cur[touch.ud.get("wc", 0)] = p
                self.scr._cursor_moved()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def _redraw(self, *a):
        self._reset()
        s = self.scr
        if self.width < dp(80) or self.height < dp(60):
            return
        act = wave_engine.active(s.waves)
        L, Rm, T, B = dp(38), dp(8), dp(8), dp(20)
        x0, pw = self.x + L, self.width - L - Rm
        ph = self.height - T - B
        yb = self.y + B
        y0 = yb + ph / 2.0
        self._geom = (x0, pw)
        w0 = s.zA * s.span
        ww = (s.zB - s.zA) * s.span
        sum_a = sum(a for _, a, _ in act)
        ext = max(sum_a, 0.5) if s.mode == "merged" else max([a for _, a, _ in act] + [0.5])
        stp = _nice_step(ext, 3)
        top = stp * math.ceil(ext * 1.05 / stp)
        sc = ph / 2.0 / top
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
        v = -top
        while v <= top + 1e-9:
            yy = y0 + v * sc
            with self.canvas:
                Color(*(COLOR_BORDER if abs(v) < 1e-9 else COLOR_GRID_FAINT))
                Line(points=[x0, yy, x0 + pw, yy], width=1)
            self._label(_sig(v, 3) if abs(v) > 1e-9 else "0", x0 - dp(4), yy, muted, 9, "right")
            v += stp
        ts = _nice_step(ww, 5)
        t = math.ceil(w0 / ts - 1e-9) * ts
        while t <= w0 + ww + 1e-9:
            xx = x0 + pw * (t - w0) / ww
            with self.canvas:
                Color(*COLOR_GRID_FAINT)
                Line(points=[xx, yb, xx, yb + ph], width=1)
            anc = "right" if xx > x0 + pw - dp(18) else ("left" if xx < x0 + dp(12) else "center")
            self._label(_sig(t, 4), xx, self.y + dp(7), muted, 9, anc)
            t += ts
        with self.canvas:
            Color(*COLOR_BORDER)
            Line(rectangle=(x0, yb, pw, ph), width=1)
        if not act:
            self._label("Switch on at least one wave", x0 + pw / 2.0, y0, muted, 10)
            return
        cols = max(2, int(pw / 1.5))
        Tspan, off = ww / 1000.0, w0 / 1000.0
        with self.canvas:
            if s.mode == "all":
                for i, a, f in act:
                    env = wave_engine.envelope(lambda tt, a=a, f=f: wave_engine.value(a, f, tt), off, Tspan, cols, 5)
                    Color(*C_WAVES[i], 1)
                    Line(points=_trace(None, x0, pw, y0, sc, cols, env), width=dp(1))
            else:
                env = wave_engine.envelope(lambda tt: wave_engine.sum_at(act, tt), off, Tspan, cols, 5)
                Color(*C_MERGED, 1)
                Line(points=_trace(None, x0, pw, y0, sc, cols, env), width=dp(1))
                Color(*COLOR_TEXT_MUTED[:3], 1)
                ys = y0 + sum_a * sc
                Line(points=[x0, ys, x0 + pw, ys], width=1, dash_length=dp(4), dash_offset=dp(4))
            if s.show_cur:
                for c in s.cur:
                    x = x0 + pw * c
                    Color(*C_CURSOR, 1)
                    Line(points=[x, yb, x, yb + ph], width=dp(1))
                    Triangle(points=[x - dp(6), yb + ph, x + dp(6), yb + ph, x, yb + ph - dp(8)])
        if s.mode == "merged":
            self._label("sum of amplitudes %.1f" % sum_a, x0 + pw - dp(4), y0 + sum_a * sc - dp(8), muted, 9, "right")
        if s.show_cur:
            for k, c in enumerate(s.cur):
                self._label("B" if k else "A", x0 + pw * c + dp(8), yb + ph - dp(9), (*C_CURSOR, 1), 10, "left", True)


class OverviewStrip(_Plot):
    """The whole record with the zoom window highlighted. Drag the window to
    move it, or drag across the strip to choose a new section."""

    def __init__(self, scr, **kwargs):
        super().__init__(**kwargs)
        self.scr = scr
        self._geom = None

    def _frac(self, touch):
        x0, pw = self._geom
        return max(0.0, min(1.0, (touch.x - x0) / pw))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or self._geom is None:
            return super().on_touch_down(touch)
        s = self.scr
        p = self._frac(touch)
        touch.grab(self)
        if s.zA <= p <= s.zB and s.zB - s.zA < 0.999:
            touch.ud["ov"] = ("pan", p - s.zA, touch.x)
        else:
            touch.ud["ov"] = ("sel", p, touch.x)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            s = self.scr
            mode, v, x0 = touch.ud["ov"]
            p = self._frac(touch)
            if mode == "pan":
                w = s.zB - s.zA
                s.set_zoom(p - v, p - v + w)
            elif abs(touch.x - x0) > dp(4):
                s.set_zoom(min(v, p), max(v, p))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            s = self.scr
            mode, v, x0 = touch.ud["ov"]
            if mode == "sel" and abs(touch.x - x0) <= dp(4):
                w = s.zB - s.zA
                if w > 0.999:
                    w = 0.25
                p = self._frac(touch)
                s.set_zoom(p - w / 2.0, p + w / 2.0)
            return True
        return super().on_touch_up(touch)

    def _redraw(self, *a):
        self._reset()
        s = self.scr
        if self.width < dp(80):
            return
        act = wave_engine.active(s.waves)
        L, Rm = dp(38), dp(8)
        x0, pw = self.x + L, self.width - L - Rm
        self._geom = (x0, pw)
        y0 = self.center_y
        h = self.height
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(*COLOR_BORDER)
            Line(rectangle=(x0, self.y + dp(2), pw, h - dp(4)), width=1)
            if act:
                ext = sum(a for _, a, _ in act) if s.mode == "merged" else max(a for _, a, _ in act)
                sc = (h / 2.0 - dp(5)) / max(ext, 0.5)
                cols = max(2, int(pw / 2))
                if s.mode == "merged":
                    env = wave_engine.envelope(lambda tt: wave_engine.sum_at(act, tt), 0.0, s.span / 1000.0, cols, 3)
                    Color(*COLOR_TEXT_MUTED[:3], 1)
                    Line(points=_trace(None, x0, pw, y0, sc, cols, env), width=1)
                else:
                    for i, a, f in act:
                        env = wave_engine.envelope(lambda tt, a=a, f=f: wave_engine.value(a, f, tt), 0.0,
                                                   s.span / 1000.0, cols, 3)
                        Color(*C_WAVES[i], 0.8)
                        Line(points=_trace(None, x0, pw, y0, sc, cols, env), width=1)
            xa, xb = x0 + pw * s.zA, x0 + pw * s.zB
            Color(1, 1, 1, 0.65)
            Rectangle(pos=(x0, self.y + dp(3)), size=(xa - x0, h - dp(6)))
            Rectangle(pos=(xb, self.y + dp(3)), size=(x0 + pw - xb, h - dp(6)))
            Color(*COLOR_ACCENT)
            Line(rectangle=(xa, self.y + dp(2), max(dp(2), xb - xa), h - dp(4)), width=dp(1.3))
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        self._label("0", x0 - dp(4), y0, muted, 9, "right")
        self._label("%s ms" % wave_engine.fmt_ms(s.span), x0 + pw - dp(2), self.y + dp(9), muted, 9, "right")


class SpectrumChart(_Plot):
    def __init__(self, scr, **kwargs):
        super().__init__(**kwargs)
        self.scr = scr

    def _redraw(self, *a):
        self._reset()
        s = self.scr
        sp = s.spec
        if sp is None or self.width < dp(80) or self.height < dp(60):
            return
        act = wave_engine.active(s.waves)
        L, Rm, T, B = dp(38), dp(8), dp(26), dp(20)
        x0, pw = self.x + L, self.width - L - Rm
        ph = self.height - T - B
        yb = self.y + B
        mag = sp["mag"]
        mx = max(mag) if mag else 0.0
        stp = _nice_step(max(mx, 0.5) * 1.1, 4)
        top = stp * math.ceil(max(mx, 0.5) * 1.1 / stp)
        f0, f1 = 0.0, float(sp["fmax"])
        inb = [f for _, _, f in act if f < sp["fmax"]]
        fit = s.spec_zoom == "fit" and inb
        if fit:
            lo, hi = min(inb), max(inb)
            pad = max(8 * sp["df"], 0.15 * (hi - lo))
            f0, f1 = max(0.0, lo - pad), min(float(sp["fmax"]), hi + pad)
        X = lambda f: x0 + pw * (f - f0) / (f1 - f0)
        Y = lambda a: yb + ph * a / top
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
        v = 0.0
        while v <= top + 1e-9:
            with self.canvas:
                Color(*(COLOR_GRID_FAINT if v else COLOR_BORDER))
                Line(points=[x0, Y(v), x0 + pw, Y(v)], width=1)
            self._label(_sig(v, 3) if v else "0", x0 - dp(4), Y(v), muted, 9, "right")
            v += stp
        fsx = _nice_step(f1 - f0, 5)
        f = math.ceil(f0 / fsx) * fsx
        while f <= f1 + 1e-9:
            with self.canvas:
                Color(*COLOR_GRID_FAINT)
                Line(points=[X(f), yb, X(f), yb + ph], width=1)
            self._label(_sig(f, 4), X(f), self.y + dp(7), muted, 9)
            f += fsx
        df = sp["df"]
        i0 = max(0, int(f0 / df))
        i1 = min(sp["lines"], int(math.ceil(f1 / df)))
        with self.canvas:
            Color(*COLOR_BORDER)
            Line(rectangle=(x0, yb, pw, ph), width=1)
            Color(*COLOR_ACCENT)
            if fit:
                pts = []
                for i in range(i0, i1 + 1):
                    pts.extend([X(i * df), Y(mag[i])])
                if len(pts) >= 4:
                    Line(points=pts, width=dp(1))
            else:
                # one bar per pixel column, the tallest line in it: dense
                # spectra stay honest without drawing thousands of lines
                cols = {}
                for i in range(i0, i1 + 1):
                    c = int(X(i * df))
                    if mag[i] > cols.get(c, -1.0):
                        cols[c] = mag[i]
                pts = []
                for c in sorted(cols):
                    pts.extend([c, yb, c, Y(cols[c]), c, yb])
                if len(pts) >= 4:
                    Line(points=pts, width=1)
        placed = []
        for i, a, fq in act:
            if fq >= sp["fmax"] or (fit and not (f0 <= fq <= f1)):
                continue
            got = wave_engine.peak_near(sp, fq)
            px, py = X(fq), Y(got)
            with self.canvas:
                Color(*C_WAVES[i], 1)
                Triangle(points=[px - dp(5), py + dp(12), px + dp(5), py + dp(12), px, py + dp(4)])
            ly = py + dp(18)
            for qx, qy in placed:
                if abs(qx - px) < dp(60) and abs(qy - ly) < dp(12):
                    ly = qy + dp(12)
            placed.append((px, ly))
            self._label("%s Hz" % wave_engine.fmt_hz(fq), px, min(self.top - dp(7), ly), (*C_WAVES[i], 1), 9, bold=True)


class WaveformScreen(_ToolScreen):
    """Five sine waves, each with its own amplitude and frequency, seen alone,
    overlaid, and added into the one complex waveform a sensor records -
    then that waveform taken apart again by the spectrum."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.waves = wave_engine.default_waves()
        self.mode = "merged"
        self.span = 100.0
        self.span_manual = False
        self.zA, self.zB = 0.0, 1.0
        self.cur = [0.25, 0.5]
        self.show_cur = True
        self.fmax, self.lines, self.spec_zoom = 2500, 1600, "full"
        self.spec = None
        self._spec_ev = None
        self._live_ev = None

        self._head("START FROM")
        grid = GridLayout(cols=2, size_hint_y=None, height=dp(124), spacing=dp(6))
        for k, (name, ws) in enumerate(wave_engine.PRESETS):
            b = PillButton(name, accent=COLOR_ACCENT, inactive=COLOR_PANEL_BG,
                           text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            b.label.font_size = dp(12)
            b.bind(on_release=lambda i, kk=k: self._preset(kk))
            grid.add_widget(b)
        self.col.add_widget(grid)

        self._head("FIVE WAVE BUILDERS")
        self.cards = []
        for i in range(5):
            self._build_card(i)

        self._head("MERGE")
        self.seg_mode = Segment([("all", "All waves"), ("merged", "Merged waveform")], "merged", self._set_mode)
        self.col.add_widget(self.seg_mode)
        self.merge_meta = self._meta()
        box = self._card()
        self.s_span = LazySlider("Record length", 0, 0, 1000, 1, "%.0f", self._span_changed,
                                 on_live=self._span_live)
        box.add_widget(self.s_span)
        row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        b = PillButton("Auto length", accent=COLOR_ACCENT, inactive=COLOR_ACCENT_SOFT,
                       text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        b.label.font_size = dp(12)
        b.set_active(False)
        b.bind(on_release=lambda *a: self._auto_span())
        row.add_widget(b)
        self.seg_cur = Segment([("on", "Cursors on"), ("off", "Off")], "on", self._set_cur)
        row.add_widget(self.seg_cur)
        box.add_widget(row)
        row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        for text, fn in (("Zoom in +", lambda: self.zoom_by(0.5)), ("Zoom out -", lambda: self.zoom_by(2.0)),
                         ("Show all", lambda: self.set_zoom(0.0, 1.0))):
            b = PillButton(text, accent=COLOR_ACCENT, inactive=COLOR_ACCENT_SOFT,
                           text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            b.label.font_size = dp(12)
            b.set_active(False)
            b.bind(on_release=lambda i, f=fn: f())
            row.add_widget(b)
        self.col.add_widget(row)
        self.zoom_info = self._meta()
        self.merged = MergedChart(self, size_hint_y=None, height=dp(250))
        self.col.add_widget(self.merged)
        self.overview = OverviewStrip(self, size_hint_y=None, height=dp(54))
        self.col.add_widget(self.overview)
        self._meta().text = ("Overview of the whole record: drag the highlighted window to move through it, "
                             "or drag across the strip to pick a new section. Drag on the chart to move "
                             "cursors A and B.")
        self.legend = self._meta()
        box = self._card()
        self.cursor_box = self._text(box, 12)

        self._head("SPECTRUM OF THE MERGED WAVEFORM")
        box = self._card()
        row = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(6))
        self.ch_fmax = Choice("F-max", [(str(f), "%d Hz" % f) for f in wave_engine.FMAX_OPTIONS], "2500",
                              self._set_fmax)
        self.ch_lines = Choice("Lines", [(str(l), str(l)) for l in wave_engine.LINE_OPTIONS], "1600",
                               self._set_lines)
        self.ch_zoom = Choice("Show", [("full", "0 to F-max"), ("fit", "Zoom to waves")], "full",
                              self._set_spec_zoom)
        for w in (self.ch_fmax, self.ch_lines, self.ch_zoom):
            row.add_widget(w)
        box.add_widget(row)
        self.spec_meta = self._meta()
        self.spectrum = SpectrumChart(self, size_hint_y=None, height=dp(220))
        self.col.add_widget(self.spectrum)
        box = self._card()
        self.spec_note = self._text(box, 12)

        self._head("MERGED WAVEFORM STATISTICS")
        box = self._card()
        self.stats_lbl = self._text(box, 12)
        self.stat_note = self._text(box, 11.5, color=COLOR_TEXT_MUTED)

        self._head("READING WHAT YOU SEE")
        box = self._card()
        self._text(box, 12).text = (
            "[b]Each wave alone[/b] is a pure sine: one frequency, one line in the spectrum, crest factor 1.41.\n\n"
            "[b]Merged[/b], the sensor only ever sees the sum. The waveform is the sum at every instant; the "
            "spectrum takes it apart again into the same five lines, at the same heights.\n\n"
            "[b]Peaks add, RMS does not.[/b] If all five peaks happened to line up the peak would be the sum of "
            "the amplitudes, but the RMS is the square root of the sum of squares. That gap is why the crest "
            "factor of a complex waveform is above 1.41.\n\n"
            "[b]Two close frequencies[/b] (try the Beat preset) make the merged waveform swell and fade. The "
            "spectrum shows two lines only if the lines of resolution can split them.\n\n"
            "[b]Wave frequency 0 Hz[/b] is a constant offset (DC), which most vibration instruments filter out.")

        self._changed_all(True)

    # -- builder cards --------------------------------------------------------
    def _build_card(self, i):
        w = self.waves[i]
        box = self._card()
        top = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
        name = Label(text="[b][color=%s]%s[/color][/b]" % (HEX_WAVES[i], wave_engine.NAMES[i]), markup=True,
                     font_size=dp(14), halign="left", valign="middle")
        name.bind(size=lambda o, v: setattr(o, "text_size", v))
        top.add_widget(name)
        seg = Segment([("on", "On"), ("off", "Off")], "on" if w.on else "off",
                      lambda k, ii=i: self._set_on(ii, k == "on"))
        seg.size_hint_x = None
        seg.width = dp(120)
        seg.height = dp(30)
        top.add_widget(seg)
        box.add_widget(top)
        mini = MiniWave(i, size_hint_y=None, height=dp(64))
        box.add_widget(mini)
        sa = LazySlider("Amplitude", w.a, 0, 10, 0.1, "%.1f mm/s pk",
                        lambda ii=i: self._amp_done(ii), on_live=lambda v, ii=i: self._amp_live(ii, v))
        box.add_widget(sa)
        sf = LazySlider("Frequency", w.f, 0, 2000, 0.5, "%.2f Hz",
                        lambda ii=i: self._freq_done(ii), on_live=lambda v, ii=i: self._freq_live(ii, v))
        box.add_widget(sf)
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        lb = Label(text="Exact frequency, Hz", font_size=dp(11), color=COLOR_TEXT_MUTED,
                   halign="left", valign="middle")
        lb.bind(size=lambda o, v: setattr(o, "text_size", v))
        row.add_widget(lb)
        fin = ModernInput(text=wave_engine.fmt_hz(w.f), input_filter="float", height=dp(40),
                          panel_color=(1, 1, 1, 1), text_color=COLOR_TEXT, accent=COLOR_ACCENT,
                          font_size=dp(13))
        fin.size_hint_x = None
        fin.width = dp(120)
        fin.ti.bind(on_text_validate=lambda t, ii=i: self._freq_typed(ii, t.text),
                    focus=lambda t, f, ii=i: (not f) and self._freq_typed(ii, t.text))
        row.add_widget(fin)
        box.add_widget(row)
        facts = self._text(box, 11, color=COLOR_TEXT_MUTED)
        self.cards.append({"seg": seg, "mini": mini, "sa": sa, "sf": sf, "fin": fin, "facts": facts})

    def _card_text(self, i):
        w, c = self.waves[i], self.cards[i]
        c["facts"].text = ("%d CPM  -  period %s ms  -  RMS %.2f" % (round(w.f * 60), wave_engine.fmt_ms(1000.0 / w.f),
                                                                   w.a / math.sqrt(2.0))
                           if w.f > 0 else "0 Hz: a constant offset (DC)")
        c["mini"].set_data(w)

    def _set_on(self, i, on):
        self.waves[i].on = on
        self._changed_all(False)

    def _amp_live(self, i, v):
        self.waves[i].a = float(v)
        self._card_text(i)
        self._live_redraw()

    def _amp_done(self, i):
        self.waves[i].a = float(self.cards[i]["sa"].value)
        self._changed_all(False)

    def _freq_live(self, i, v):
        self.waves[i].f = float(v)
        self.cards[i]["fin"].text = wave_engine.fmt_hz(self.waves[i].f)
        self._card_text(i)

    def _freq_done(self, i):
        self.waves[i].f = float(self.cards[i]["sf"].value)
        self._changed_all(True)

    def _freq_typed(self, i, text):
        try:
            v = float(text)
        except (TypeError, ValueError):
            v = self.waves[i].f
        v = max(0.0, min(wave_engine.FMAX_MAX, v))
        if abs(v - self.waves[i].f) < 1e-9:
            self.cards[i]["fin"].text = wave_engine.fmt_hz(v)
            return
        self.waves[i].f = v
        self.cards[i]["fin"].text = wave_engine.fmt_hz(v)
        self.cards[i]["sf"].set_value(v)
        self._changed_all(True)

    def _preset(self, k):
        for i, (on, a, f) in enumerate(wave_engine.PRESETS[k][1]):
            w = self.waves[i]
            w.on, w.a, w.f = bool(on), float(a), float(f)
            c = self.cards[i]
            c["seg"].set_value("on" if w.on else "off")
            c["sa"].set_value(w.a)
            c["sf"].set_value(w.f)
            c["fin"].text = wave_engine.fmt_hz(w.f)
        self.span_manual = False
        self._changed_all(True)

    # -- merge controls -------------------------------------------------------
    def _set_mode(self, k):
        self.mode = k
        self._changed_all(False)

    def _set_cur(self, k):
        self.show_cur = (k == "on")
        self.merged._redraw()
        self._cursor_text()

    def _span_live(self, v):
        self.s_span.val.text = "%s ms" % wave_engine.fmt_ms(wave_engine.span_from_slider(v))

    def _span_changed(self):
        self.span_manual = True
        self.span = wave_engine.span_from_slider(self.s_span.value)
        self.zA, self.zB = 0.0, 1.0
        self._changed_all(False)

    def _auto_span(self):
        self.span_manual = False
        self._changed_all(True)

    def set_zoom(self, a, b):
        wmin = min(1.0, max(0.0005, 0.05 / self.span))
        w = max(wmin, min(1.0, b - a))
        a = max(0.0, a)
        if a + w > 1.0:
            a = 1.0 - w
        self.zA, self.zB = a, a + w
        self.merged._redraw()
        self.overview._redraw()
        self._cursor_text()
        self._zoom_info()

    def zoom_by(self, factor):
        w = (self.zB - self.zA) * factor
        c = (self.zA + self.zB) / 2.0
        self.set_zoom(c - w / 2.0, c + w / 2.0)

    def _cursor_moved(self):
        self.merged._redraw()
        self._cursor_text()

    def _zoom_info(self):
        w0, ww = self.zA * self.span, (self.zB - self.zA) * self.span
        fm = wave_engine.fmt_ms
        self.zoom_info.text = ("Showing the whole record" if self.zB - self.zA > 0.999 else
                               "Showing %s - %s ms of %s ms (x%.1f)" % (fm(w0), fm(w0 + ww), fm(self.span),
                                                                     1.0 / (self.zB - self.zA)))

    def _cursor_text(self):
        if not self.show_cur:
            self.cursor_box.text = "[color=%s]Time cursors are off.[/color]" % MUTED_HEX
            return
        w0, ww = self.zA * self.span, (self.zB - self.zA) * self.span
        ta, tb = w0 + self.cur[0] * ww, w0 + self.cur[1] * ww
        dt = abs(tb - ta)
        f = 1000.0 / dt if dt > 0 else 0.0
        act = [w for w in wave_engine.active(self.waves) if w[2] > 0]
        near = ""
        if f > 0 and act:
            best = min(act, key=lambda w: abs(w[2] - f))
            near = "  -  nearest: %s (%s Hz)" % (wave_engine.NAMES[best[0]], wave_engine.fmt_hz(best[2]))
        fm = wave_engine.fmt_ms
        self.cursor_box.text = (
            "A %s ms  -  B %s ms  -  [b]dt %s ms[/b] -> 1/dt = [b]%s[/b]%s\n[color=%s][size=%d]Drag A and B onto "
            "two neighbouring peaks of a repeating pattern: 1/dt is its frequency.[/size][/color]"
            % (fm(ta), fm(tb), fm(dt), ("%s Hz = %d CPM" % (wave_engine.fmt_hz(f), round(f * 60))) if f else "-",
               near, MUTED_HEX, int(dp(10.5))))

    def _legend(self):
        act = wave_engine.active(self.waves)
        if self.mode == "all":
            self.legend.text = "   ".join("[color=%s]%s: %.1f at %s Hz[/color]" % (HEX_WAVES[i], wave_engine.NAMES[i],
                                                                               a, wave_engine.fmt_hz(f))
                                          for i, a, f in act)
        else:
            self.legend.text = "Merged waveform = " + (" + ".join(wave_engine.NAMES[i] for i, _, _ in act)
                                                       if act else "nothing switched on")

    # -- spectrum controls ----------------------------------------------------
    def _set_fmax(self, k):
        self.fmax = int(k)
        self._schedule_spec()

    def _set_lines(self, k):
        self.lines = int(k)
        self._schedule_spec()

    def _set_spec_zoom(self, k):
        self.spec_zoom = k
        self.spectrum._redraw()

    # -- update ---------------------------------------------------------------
    def _live_redraw(self):
        # coalesce slider moves: at most one merged redraw per frame
        if self._live_ev is None:
            self._live_ev = Clock.schedule_once(self._do_live, 0)

    def _do_live(self, *a):
        self._live_ev = None
        self.merged._redraw()
        self.overview._redraw()

    def _changed_all(self, freq_changed):
        act = wave_engine.active(self.waves)
        if not self.span_manual and freq_changed:
            ns = wave_engine.auto_span(act)
            if ns != self.span:
                self.zA, self.zB = 0.0, 1.0
            self.span = ns
        self.s_span.set_value(wave_engine.slider_from_span(self.span))
        self.s_span.val.text = "%s ms%s" % (wave_engine.fmt_ms(self.span), "" if self.span_manual else " (auto)")
        for i in range(5):
            self._card_text(i)
        self.merge_meta.text = (("Every wave on its own, drawn on the same time axis." if self.mode == "all" else
                                 "The waves added point by point: this is the one signal a sensor would record.")
                                + " Time in ms, amplitude in mm/s.")
        self.merged._redraw()
        self.overview._redraw()
        self._zoom_info()
        self._legend()
        self._cursor_text()
        self._schedule_spec()

    def _schedule_spec(self):
        if self._spec_ev is not None:
            self._spec_ev.cancel()
        self._spec_ev = Clock.schedule_once(self._do_spec, 0.03)

    def _do_spec(self, *a):
        self._spec_ev = None
        act = wave_engine.active(self.waves)
        self.spec = wave_engine.spectrum(act, self.fmax, self.lines)
        self.spectrum._redraw()
        sp = self.spec
        self.spec_meta.text = ("Frequency in Hz - Hanning window - df = F-max / lines = %d / %d = %.3f Hz - "
                               "record %.0f ms - amplitude mm/s peak"
                               % (sp["fmax"], sp["lines"], sp["df"], sp["T"] * 1000))
        notes = wave_engine.spectrum_notes(act, sp)
        self.spec_note.text = "\n\n".join(notes) if notes else (
            "[color=%s]Every wave below F-max shows as its own line at its own height.[/color]" % MUTED_HEX)
        s = wave_engine.stats(act)
        if s is None:
            self.stats_lbl.text = "[color=%s]Switch on at least one wave.[/color]" % MUTED_HEX
            self.stat_note.text = ""
            return
        rows = wave_engine.stats_rows(s)
        self.stats_lbl.text = "\n".join("[b]%s[/b]   %s\n[color=%s][size=%d]%s[/size][/color]"
                                        % (k, v, MUTED_HEX, int(dp(10.5)), m) for k, v, m in rows)
        self.stat_note.text = wave_engine.stats_note(s)


# the menu, in the CM/DX shape: a card per tool, tap to open it full screen,
# back returns here
MENU_SUBTITLE = "Interactive teaching tools"

MENU = [
    ("balance", "Balance Demo", "Single-plane job on one screen, live vectors",
     (0.153, 0.306, 0.788, 1)),
    ("fault", "Fault Signature", "Waveform and spectrum of 27 machinery faults",
     (0.886, 0.247, 0.541, 1)),
    ("orbit", "Orbit", "Two probes, live orbit shape with Keyphasor dots",
     (0.055, 0.561, 0.267, 1)),
    ("resonance", "Resonance", "Two criticals: Bode, shaft shape, AF and margin",
     (0.502, 0.251, 0.682, 1)),
    ("phase", "Phase Survey", "Tap points, read phase, find the fault, avoid the traps",
     (0.886, 0.400, 0.055, 1)),
    ("waveform", "Waveform Builder", "Five waves, merged waveform, spectrum and statistics",
     (0.000, 0.533, 0.565, 1)),
]


class MenuScreen(Screen):
    """The section menu, following CM/DX: one card per tool, tapped to open
    it full screen. A pill bar runs out of room past three tools on a phone;
    cards do not, and they have space to say what each one is for."""

    def __init__(self, on_pick, **kwargs):
        super().__init__(name="menu", **kwargs)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg = Rectangle()
        # a Screen draws relative to itself, so its background starts at (0, 0)
        self.bind(pos=lambda w, v: setattr(w._bg, "pos", (0, 0)),
                  size=lambda w, v: setattr(w._bg, "size", v))

        scroll = ScrollView(do_scroll_x=False)
        col = BoxLayout(orientation="vertical", size_hint_y=None,
                        padding=[dp(14), dp(14)], spacing=dp(12))
        col.bind(minimum_height=col.setter("height"))

        intro = Label(
            text=("Interactive teaching tools. Each one is built on the same "
                  "maths the calculators use, so nothing here can drift away "
                  "from what the rest of the app computes."),
            markup=True, font_size=dp(12.5), color=COLOR_TEXT_MUTED,
            halign="left", valign="top", size_hint_y=None)
        intro.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)),
                   texture_size=lambda i, ts: setattr(i, "height", ts[1]))
        col.add_widget(intro)

        for name, title, subtitle, accent in MENU:
            card = NavCard(title, subtitle, accent,
                           card_bg=COLOR_PANEL_BG,
                           title_color=COLOR_TEXT,
                           subtitle_color=COLOR_TEXT_MUTED,
                           height=dp(84))
            card.bind(on_release=lambda i, n=name: on_pick(n))
            col.add_widget(card)

        scroll.add_widget(col)
        self.add_widget(scroll)


class RootWidget(BoxLayout):
    """Owns the section menu and screen manager, and exposes handle_back()
    for main.py's hardware back button."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        header = BoxLayout(orientation="horizontal", size_hint_y=None,
                           height=dp(76), padding=(dp(12), dp(12)), spacing=dp(6))
        with header.canvas.before:
            Color(*COLOR_ACCENT)
            header._bg = Rectangle()
        header.bind(pos=lambda w, v: setattr(header._bg, "pos", v),
                    size=lambda w, v: setattr(header._bg, "size", v))

        self.back_btn = PillButton("<", accent=(1, 1, 1, 0.22),
                                   inactive=(1, 1, 1, 0.22),
                                   text_color=(1, 1, 1, 1))
        self.back_btn.size_hint_x = None
        self.back_btn.width = dp(44)
        self.back_btn.bind(on_release=lambda *a: self.show_menu())
        self.back_btn.opacity = 0
        self.back_btn.disabled = True
        header.add_widget(self.back_btn)

        text_col = BoxLayout(orientation="vertical", spacing=dp(2))
        self.title = Label(text="[b]Simulation[/b]", markup=True, color=(1, 1, 1, 1),
                           font_size=dp(20), size_hint_y=None, height=dp(26),
                           halign="left", valign="middle")
        self.title.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.subtitle = Label(text=MENU_SUBTITLE, color=(1, 0.92, 0.96, 1),
                              font_size=dp(12.5), size_hint_y=None, height=dp(22),
                              halign="left", valign="middle")
        self.subtitle.bind(size=lambda i, v: setattr(i, "text_size", v))
        text_col.add_widget(self.title)
        text_col.add_widget(self.subtitle)
        header.add_widget(text_col)
        self.add_widget(header)

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(MenuScreen(on_pick=self.open_tool))
        self.sm.add_widget(BalanceDemoScreen(name="balance"))
        self.sm.add_widget(FaultSignatureScreen(name="fault"))
        self.sm.add_widget(OrbitScreen(name="orbit"))
        self.sm.add_widget(ResonanceScreen(name="resonance"))
        self.sm.add_widget(PhaseSurveyScreen(name="phase"))
        self.sm.add_widget(WaveformScreen(name="waveform"))
        self.add_widget(self.sm)

        # same credit line as the other tools, shown under the menu and
        # every sub-tool alike
        footer = Label(text="Built by Gnaneswar", color=COLOR_TEXT_MUTED, font_size=dp(12),
                       size_hint_y=None, height=dp(24))
        with footer.canvas.before:
            Color(*COLOR_BG)
            footer._bg = Rectangle()
        footer.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
                    size=lambda w, v: setattr(w._bg, "size", v))
        self.add_widget(footer)

        self.show_menu()

    def open_tool(self, name):
        self.sm.current = name
        for key, title, subtitle, _accent in MENU:
            if key == name:
                self.title.text = "[b]%s[/b]" % title
                self.subtitle.text = subtitle
                break
        self.back_btn.opacity = 1
        self.back_btn.disabled = False

    def show_menu(self):
        self.sm.current = "menu"
        self.title.text = "[b]Simulation[/b]"
        self.subtitle.text = MENU_SUBTITLE
        self.back_btn.opacity = 0
        self.back_btn.disabled = True

    def handle_back(self):
        """Inside a tool, back returns to the menu; from the menu, main.py
        falls through to Home. Same unwinding as CM/DX."""
        if self.sm.current != "menu":
            self.show_menu()
            return True
        return False


class SimulationApp(App):
    """Standalone-runnable wrapper, same pattern as the other tool modules."""

    def build(self):
        try:
            Window.clearcolor = COLOR_BG
        except Exception:
            pass
        return RootWidget()


if __name__ == "__main__":
    SimulationApp().run()
