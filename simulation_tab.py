"""
Simulation - interactive teaching tools for CM Toolkit.

Sub-tabs:
  1. Balance Demo   - the whole single-plane job on one screen, with sliders
                      on every measured value and a live vector diagram
  (Fault Signature, Orbit and Resonance follow in a later update.)

The balancing maths is imported directly from rotor_tab so the demo and the
calculator can never drift apart.

Angle convention: measured CLOCKWISE from the phase reference mark, 0 deg at
the top - identical to the Rotor Balance tab.
"""

import math

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Line, Ellipse, Triangle, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget

from theme import ModernInput, PillButton, RoundedButton
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
TAB_SUBTITLES = {
    "balance": "Balance demo · live vector solution",
}


class RootWidget(BoxLayout):
    """Owns the sub-tab bar and screen manager, and exposes handle_back()
    for main.py's hardware back button."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        header = BoxLayout(orientation="vertical", size_hint_y=None,
                           height=dp(76), padding=(dp(16), dp(12)))
        with header.canvas.before:
            Color(*COLOR_ACCENT)
            header._bg = Rectangle()
        header.bind(pos=lambda w, v: setattr(header._bg, "pos", v),
                    size=lambda w, v: setattr(header._bg, "size", v))
        title = Label(text="[b]Simulation[/b]", markup=True, color=(1, 1, 1, 1),
                      font_size=dp(20), size_hint_y=None, height=dp(26),
                      halign="left", valign="middle")
        title.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.subtitle = Label(text=TAB_SUBTITLES["balance"], color=(1, 0.92, 0.96, 1),
                              font_size=dp(13), size_hint_y=None, height=dp(20),
                              halign="left", valign="middle")
        self.subtitle.bind(size=lambda i, v: setattr(i, "text_size", v))
        header.add_widget(title)
        header.add_widget(self.subtitle)
        self.add_widget(header)

        bar = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(8), dp(6)],
                        spacing=dp(6))
        self.tab_buttons = {}
        for name, label in (("balance", "Balance Demo"),):
            btn = PillButton(label, accent=COLOR_ACCENT, inactive=COLOR_PANEL_BG,
                             text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
            btn.bind(on_release=lambda i, n=name: self.switch_tab(n))
            bar.add_widget(btn)
            self.tab_buttons[name] = btn
        self.add_widget(bar)

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(BalanceDemoScreen(name="balance"))
        self.add_widget(self.sm)

        self.switch_tab("balance")

    def switch_tab(self, name):
        self.sm.current = name
        for key, btn in self.tab_buttons.items():
            btn.set_active(key == name)
        self.subtitle.text = TAB_SUBTITLES.get(name, "")

    def handle_back(self):
        """Nothing to unwind yet - main.py falls through to Home."""
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
