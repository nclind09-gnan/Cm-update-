"""
Simulation - interactive teaching tools for CM Toolkit.

Sub-tabs:
  1. Balance Demo     - the whole single-plane job on one screen, with sliders
                        on every measured value and a live vector diagram
  2. Fault Signature  - the waveform and spectrum each of 27 faults actually
                        produces, synthesised from the machine geometry you set
  3. Orbit            - two proximity probes and a Keyphasor on a rotor with
                        split criticals: orbit, timebase and full spectrum
  4. Resonance        - a coast-down through the first critical: Bode and
                        polar plots, amplification factor, separation margin

Orbit and Resonance share their physics with orbit_engine.py.

Navigation follows CM/DX: a card menu, tap to open a tool full screen, back
returns to the menu.

The balancing maths is imported directly from rotor_tab so the demo and the
calculator can never drift apart.

Angle convention: measured CLOCKWISE from the phase reference mark, 0 deg at
the top - identical to the Rotor Balance tab.
"""

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

    def __init__(self, label_text, value, vmin, vmax, step, fmt, on_change, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(56), spacing=dp(0), **kwargs)
        self._fmt = fmt
        self._on_change = on_change
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

    def _release(self, inst, touch):
        if inst.collide_point(*touch.pos):
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
        self.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
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
# Bode and polar
# =====================================================================
class BodeChart(_Plot):
    """Phase lag above, amplitude below, against speed - the Bently layout.
    Phase lag increases DOWNWARD, so a roll through a critical reads as the
    phase trace falling while the amplitude rises."""

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
        if b is None or self.width < dp(60) or self.height < dp(80):
            return
        st = b["settings"]
        rpm, amp, lag = b["rpm"], b["amp"], b["lag"]
        L, Rm, B, T, gap = dp(40), dp(8), dp(18), dp(6), dp(12)
        x0 = self.x + L
        pw = self.width - L - Rm
        hp = (self.height - B - T - gap) * 0.42
        ha = (self.height - B - T - gap) * 0.58
        ya = self.y + B
        yp = ya + ha + gap
        xmax = st.max_rpm
        to_x = lambda n: x0 + pw * n / xmax
        astep = _nice_step(max(amp) * 1.05, 4)
        atop = astep * math.ceil(max(amp) * 1.05 / astep)
        lo = 90.0 * math.floor(min(lag) / 90.0)
        hi = 90.0 * math.ceil(max(lag) / 90.0)
        if hi - lo < 180:
            hi = lo + 180
        to_yp = lambda d: yp + hp - hp * (d - lo) / (hi - lo)     # lag grows downward
        muted = (*COLOR_TEXT_MUTED[:3], 1)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            # operating range on both panels
            Color(*C_OPBAND)
            for y, h in ((ya, ha), (yp, hp)):
                Rectangle(pos=(to_x(st.op_min), y), size=(to_x(st.op_max) - to_x(st.op_min), h))
            Color(*COLOR_GRID_FAINT)
            for i in range(1, 4):
                yy = ya + ha * i / 4.0
                Line(points=[x0, yy, x0 + pw, yy], width=1)
            d = lo + 90
            while d < hi:
                Line(points=[x0, to_yp(d), x0 + pw, to_yp(d)], width=1)
                d += 90
            xs = _nice_step(xmax, 5)
            n = xs
            while n < xmax:
                for y, h in ((ya, ha), (yp, hp)):
                    Line(points=[to_x(n), y, to_x(n), y + h], width=1)
                n += xs
            Color(*COLOR_GRID)
            Line(rectangle=(x0, ya, pw, ha), width=1)
            Line(rectangle=(x0, yp, pw, hp), width=1)
            # half power line and points
            if b["af"] is not None:
                hpw = b["peak"] / math.sqrt(2.0)
                yy = ya + ha * hpw / atop
                Color(*C_MARK, 0.8)
                Line(points=[to_x(b["n1"]), yy, to_x(b["n2"]), yy], width=1,
                     dash_length=dp(4), dash_offset=dp(3))
                for nn in (b["n1"], b["n2"]):
                    Ellipse(pos=(to_x(nn) - dp(3), yy - dp(3)), size=(dp(6), dp(6)))
            # criticals
            Color(*C_CLEAR, 0.8)
            for nc in b["peaks"]:
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
                Color(*COLOR_TEXT[:3], 0.75)
                for y, h in ((ya, ha), (yp, hp)):
                    Line(points=[to_x(self.cursor), y, to_x(self.cursor), y + h], width=1.1)
        for i in range(5):
            self._label(_sig(atop * i / 4.0, 3), x0 - dp(3), ya + ha * i / 4.0, muted, 9, "right")
        d = lo
        while d <= hi + 1e-6:
            self._label("%d" % (int(round(d)) % 360), x0 - dp(3), to_yp(d), muted, 9, "right")
            d += 90
        n = 0.0
        while n <= xmax + 1e-6:
            self._label(_eng(n), to_x(n), self.y + dp(8), muted, 9)
            n += xs
        self._label("[b]PHASE LAG[/b] deg, increasing downward", x0 + dp(4), yp + dp(9),
                    (*C_PHASE, 1), 9, "left")
        self._label("[b]AMPLITUDE[/b] 1X um pp", x0 + dp(4), ya + ha - dp(8), (*C_ORBIT, 1), 9, "left")
        self._label("operating", (to_x(st.op_min) + to_x(st.op_max)) / 2.0, ya + dp(8), muted, 8)
        for nc in b["peaks"]:
            self._label("%.0f" % nc, to_x(nc), ya + ha + gap / 2.0, (*C_CLEAR, 1), 9)


class PolarChart(_Plot):
    """The same 1X vectors as the Bode, drawn as one curve: amplitude is the
    radius, phase lag the angle. 0 deg is at the probe (top here) and lag
    increases against rotation. A critical shows as a loop."""

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
        if b is None or self.width < dp(60) or self.height < dp(60):
            return
        st = b["settings"]
        rot = st.rotor.rot
        cx, cy = self.center_x, self.center_y - dp(4)
        R = min(self.width, self.height) * 0.40
        mx = max(b["amp"])
        step = _nice_step(mx * 1.05, 4)
        view = step * math.ceil(mx * 1.05 / step)
        k = R / view
        muted = (*COLOR_TEXT_MUTED[:3], 1)

        def xy(amp, lag):
            a = math.radians(lag * rot)      # clockwise on screen for CCW rotation
            return cx + amp * k * math.sin(a), cy + amp * k * math.cos(a)

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            ring = step
            while ring <= view + 1e-9:
                Color(*(COLOR_GRID if abs(ring - view) < 1e-9 else COLOR_GRID_FAINT))
                Line(circle=(cx, cy, ring * k), width=1)
                ring += step
            Color(*COLOR_GRID_FAINT)
            for d in range(0, 360, 30):
                a = math.radians(d)
                Line(points=[cx, cy, cx + R * math.sin(a), cy + R * math.cos(a)], width=1)
            pts = []
            op = []
            for n, a, l in zip(b["rpm"], b["amp"], b["lag"]):
                x, y = xy(a, l)
                pts.extend([x, y])
                if st.op_min <= n <= st.op_max:
                    op.extend([x, y])
            Color(*C_ORBIT, 1)
            Line(points=pts, width=1.4)
            if len(op) >= 4:
                Color(*C_OPBAND[:3], 1)
                Color(0.30, 0.45, 0.95, 0.35)
                Line(points=op, width=dp(3.2))
            # speed ticks every 1000 rpm
            Color(*COLOR_TEXT[:3], 1)
            tick = 1000.0 if st.max_rpm <= 7000 else 2000.0
            for i, n in enumerate(b["rpm"]):
                if i and (b["rpm"][i - 1] // tick) != (n // tick):
                    x, y = xy(b["amp"][i], b["lag"][i])
                    Ellipse(pos=(x - dp(2.5), y - dp(2.5)), size=(dp(5), dp(5)))
            if self.cursor is not None:
                kk = min(range(len(b["rpm"])), key=lambda i: abs(b["rpm"][i] - self.cursor))
                x, y = xy(b["amp"][kk], b["lag"][kk])
                Color(*C_CLEAR, 1)
                Ellipse(pos=(x - dp(5), y - dp(5)), size=(dp(10), dp(10)))
        for d in (0, 90, 180, 270):
            a = math.radians(d * rot)
            self._label("%d" % d, cx + R * 1.12 * math.sin(a), cy + R * 1.12 * math.cos(a), muted, 9)
        tick = 1000.0 if st.max_rpm <= 7000 else 2000.0
        for i, n in enumerate(b["rpm"]):
            if i and (b["rpm"][i - 1] // tick) != (n // tick):
                x, y = xy(b["amp"][i], b["lag"][i])
                self._label("%gk" % (round(n / tick) * tick / 1000.0), x + dp(12), y + dp(6),
                            (*COLOR_TEXT[:3], 1), 8)
        self._label("0 deg = probe, lag against rotation", self.x + dp(4), self.top - dp(8),
                    muted, 9, "left")
        self._label("%s um/div" % _sig(step, 3), self.right - dp(4), self.y + dp(8), muted, 9, "right")


# =====================================================================
# Screen base: the scrolling column, section heads and cards
# =====================================================================
class _ToolScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg = Rectangle()
        self.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
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
    """A coast-down through the first critical, measured the way a
    monitoring system records it, then read like an analyst: critical speed,
    amplification factor by half power, and separation margin."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.st = orbit_engine.SweepSettings()
        self.sw = None
        self.cursor = 3600.0
        self.cur_orbit = None

        intro = self._text(self.col, 12.5)
        intro.text = ("A coast-down from full speed, with the 1X vector measured "
                      "at every speed step. Move the critical, the damping and the "
                      "operating range, and the separation margin is checked against "
                      "the API limits.")

        self._head("BODE")
        self.bode_meta = self._meta()
        self.bode = BodeChart(size_hint_y=None, height=dp(300))
        self.col.add_widget(self.bode)

        box = self._card()
        self.verdict = self._text(box, 12)

        self._head("POLAR")
        self.polar = PolarChart()
        self._square(self.polar)

        self._head("AT THE CURSOR SPEED")
        box = self._card()
        self.s_cursor = LazySlider("Cursor speed", self.cursor, 300, self.st.max_rpm, 50,
                                   "%.0f rpm", self._cursor_moved)
        box.add_widget(self.s_cursor)
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
        rot = self.st.rotor
        self.s_nc = LazySlider("First critical (mean)", rot.nc, 1000, 6000, 50, "%.0f rpm", self._changed)
        self.s_zeta = LazySlider("Damping ratio", rot.zeta, 0.03, 0.5, 0.01, "%.2f", self._changed)
        self.s_split = LazySlider("Support asymmetry (split)", rot.split * 100, 0, 40, 1,
                                  "%.0f %%", self._changed)
        self.s_ecc = LazySlider("Unbalance (response far above critical)", rot.ecc * 2,
                                10, 120, 2, "%.0f um pp", self._changed)
        self.s_hs = LazySlider("Heavy spot (against rotation from notch)", rot.hs_deg,
                               0, 355, 5, "%.0f deg", self._changed)
        for w in (self.s_nc, self.s_zeta, self.s_split, self.s_ecc, self.s_hs):
            box.add_widget(w)

        self._head("MEASUREMENT")
        box = self._card()
        self.seg_probe = Segment([("X", "X probe"), ("Y", "Y probe")], "X", self._set_probe, "Probe")
        box.add_widget(self.seg_probe)
        self.seg_comp = Segment([("on", "Compensated"), ("off", "Raw")], "on", self._set_comp,
                                "Slow roll vector (%.0f rpm)" % self.st.slow_roll)
        box.add_widget(self.seg_comp)
        self.s_ro = LazySlider("Slow roll runout + glitch", rot.runout, 0, 15, 0.5, "%.1f um",
                               self._changed)
        box.add_widget(self.s_ro)
        self.ch_max = Choice("Coast-down from",
                             [("3000", "3000 rpm"), ("4500", "4500 rpm"), ("6000", "6000 rpm"),
                              ("9000", "9000 rpm"), ("12000", "12000 rpm")], "6000", self._set_max)
        box.add_widget(self.ch_max)

        self._head("OPERATING RANGE")
        box = self._card()
        self.s_omin = LazySlider("Minimum operating speed", self.st.op_min, 300, 12000, 50,
                                 "%.0f rpm", self._changed)
        self.s_omax = LazySlider("Maximum continuous speed", self.st.op_max, 300, 12000, 50,
                                 "%.0f rpm", self._changed)
        box.add_widget(self.s_omin)
        box.add_widget(self.s_omax)

        self._head("READING A BODE PLOT")
        box = self._card()
        guide = self._text(box, 12)
        guide.text = (
            "[b]The critical[/b] is where the amplitude peaks AND the phase lag has rolled "
            "90 deg from its slow roll value. Use both: a peak without the phase roll is "
            "not a resonance (it may be a structural or process effect).\n\n"
            "[b]Phase through a critical[/b]: below it the high spot is on the heavy spot. "
            "At the critical it lags by 90 deg, well above by close to 180 deg. Lag "
            "always increases with speed through a resonance.\n\n"
            "[b]Amplification factor[/b] = critical speed / (N2 - N1), where N1 and N2 are "
            "the speeds at which the amplitude is 0.707 of the peak (the half power "
            "points, marked on the amplitude trace). It is about 1 / (2 x damping ratio). "
            "Higher AF means a sharper, less damped critical.\n\n"
            "[b]Separation margin[/b]: how far the critical sits from the operating "
            "range, as a percentage of the nearest operating speed. Below AF 2.5 the "
            "critical is treated as critically damped and needs no margin. From 2.5 to "
            "3.55 it needs 5%% below minimum speed and 15%% above maximum continuous. "
            "Above 3.55 the requirement rises with AF to as much as 16%% below and 26%% "
            "above; the exact curve depends on the API edition, so this tool applies "
            "those upper figures.\n\n"
            "[b]Split criticals[/b]: when the support is stiffer one way than the other, "
            "there are two criticals. One probe may show one broad peak while the other "
            "shows a double hump - switch probes and compare. A half power AF read across "
            "a double hump means nothing, and the tool will say so.\n\n"
            "[b]Slow roll[/b]: at low speed a proximity probe still sees shaft runout and "
            "electrical glitches. Switch compensation to Raw and look at the bottom of "
            "the Bode and the start of the polar loop: the curve starts from the runout "
            "vector, not from zero, and the phase there is the runout's, not the rotor's.")

        self._changed()

    # -- controls ---------------------------------------------------------
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

    def _cursor_moved(self, *a):
        self.cursor = self.s_cursor.value
        self._draw_cursor()

    def _changed(self, *a):
        self.bode_meta.text = "Computing..."
        super()._changed()

    def _recompute(self, *a):
        self._pending = None
        st = self.st
        rot = st.rotor
        rot.nc = self.s_nc.value
        rot.zeta = self.s_zeta.value
        rot.split = self.s_split.value / 100.0
        rot.ecc = self.s_ecc.value / 2.0
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
        self.bode_meta.text = ("%s probe - %d speed steps from %.0f to %.0f rpm - %s - "
                               "operating range shaded"
                               % (st.probe, len(b["rpm"]), st.slow_roll, st.max_rpm,
                                  "slow roll compensated" if st.comp else "raw"))
        self._verdict()
        self._draw_cursor()

    def _verdict(self):
        b = self.sw
        st = self.st
        ok_hex, bad_hex = "1A7A4A", "A8291F"
        lines = []
        if b["split_seen"]:
            lines.append("[b]Two peaks[/b] at %s rpm - split criticals seen by this probe. "
                         "Margin measured from the %.0f rpm peak, nearest the range."
                         % (" and ".join("%.0f" % p for p in b["peaks"]), b["nc_margin"]))
            lines.append("A half power AF across a double hump is not valid. Switch probes, "
                         "or read each peak from the polar loop.")
        else:
            lines.append("[b]Critical[/b] %.0f rpm   peak %.1f um pp   phase lag %.0f deg there"
                         % (b["nc"], b["peak"], b["lag_at_nc"] % 360))
            if b["af"] is not None:
                lines.append("[b]AF[/b] = %.0f / (%.0f - %.0f) = [b]%.2f[/b]   "
                             "(model damping says about %.1f)"
                             % (b["nc"], b["n2"], b["n1"], b["af"], 1.0 / (2.0 * st.rotor.zeta)))
            else:
                lines.append("[b]AF[/b] - no half power points either side: heavily damped, "
                             "treated as below 2.5")
        if b["peak_at_edge"]:
            lines.append("[color=%s]The peak is at the top of the coast-down - the critical "
                         "may be above it. Start the coast-down higher.[/color]" % bad_hex)
        lines.append(b["af_band"])
        if b["sm_side"] == "inside":
            col = ok_hex if b["sm_ok"] else bad_hex
            lines.append("[color=%s][b]Critical inside the operating range[/b][/color]%s"
                         % (col, "" if b["sm_ok"] else " - not acceptable for continuous running"))
        else:
            need = b["req_lo"] if b["sm_side"] == "below" else b["req_hi"]
            col = ok_hex if b["sm_ok"] else bad_hex
            lines.append("[color=%s][b]Separation margin %.1f%% %s the range - %s[/b][/color]"
                         " (needs %.0f%%)"
                         % (col, b["sm"], b["sm_side"], "OK" if b["sm_ok"] else "TOO CLOSE", need))
        self.verdict.text = "\n".join(lines)

    def _draw_cursor(self):
        b = self.sw
        if b is None:
            return
        self.bode.set_data(b, self.cursor)
        self.polar.set_data(b, self.cursor)
        # the orbit at the cursor speed: same rotor, 1X filtered
        o = orbit_engine.OrbitSettings()
        o.rotor = self.st.rotor.copy()
        o.cond = "unbalance"
        o.sev = 4.5                 # response factor 1.0 - same unbalance as the sweep
        o.rpm = self.cursor
        o.filt = "1x"
        o.comp = self.st.comp
        o.revs = 1
        try:
            r = orbit_engine.compute_orbit(o)
        except Exception:
            return
        self.mini.set_data(r, 1, "auto")
        p = r["probes"][self.st.probe]
        fwd, rev = r["fwd1"], r["rev1"]
        prec = ("[color=1A7A4A]forward[/color]" if fwd >= rev else "[color=A8291F]reverse[/color]")
        rot = self.st.rotor
        self.cur_text.text = ("[b]%.0f rpm[/b]\n%.2f x mean critical\n\n"
                              "%s probe 1X\n[b]%.1f um pp / %.0f deg[/b]\n\n"
                              "1X precession %s\n\n"
                              "[size=10][color=%s]Split criticals %.0f / %.0f rpm. "
                              "Between them the 1X turns reverse only if the split is wide "
                              "for the damping - try 20%% split, damping 0.05."
                              "[/color][/size]"
                              % (self.cursor, self.cursor / rot.nc, self.st.probe,
                                 p["x1_pp"], p["x1_lag"], prec, MUTED_HEX,
                                 rot.crit_weak(), rot.crit_stiff()))


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
    ("resonance", "Resonance", "Coast-down through a critical: Bode, polar, AF",
     (0.502, 0.251, 0.682, 1)),
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
        self.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
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
        self.add_widget(self.sm)

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
