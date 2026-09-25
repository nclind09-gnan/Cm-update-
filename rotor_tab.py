"""
Rotor Balance Calculator - Android app (Kivy)

Five sub-tabs:
  1. Single Plane   - influence-coefficient (vector) method, 1 plane
  2. Two Plane      - influence-coefficient method with cross-effect, 2 planes
  3. Trial Weight   - force-based trial weight estimator
  4. Weight Split   - resolve one correction onto two fixed positions
  5. Trim Balance   - reuse a known sensitivity, no new trial run

Angle convention: measured CLOCKWISE from the phase reference mark
(keyphasor), as viewed from the sensor end.
"""

import cmath
import math

from kivy.animation import Animation
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Line, Ellipse, Triangle, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.textinput import TextInput
from theme import ModernInput, PillButton, RoundedButton
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

# ---------- color palette: blue UI, white background ----------
COLOR_BG = (1, 1, 1, 1)
COLOR_PRIMARY = (0.114, 0.306, 0.847, 1)          # #1D4ED8
COLOR_PRIMARY_LIGHT = (0.235, 0.51, 0.965, 1)      # #3B82F6
COLOR_TEXT = (0.06, 0.09, 0.16, 1)                 # #0F172A
COLOR_TEXT_MUTED = (0.357, 0.392, 0.447, 1)        # #5B6472
COLOR_PANEL_BG = (0.96, 0.97, 0.99, 1)
COLOR_BORDER = (0.85, 0.89, 0.95, 1)
COLOR_SUCCESS = (0.082, 0.502, 0.235, 1)           # #15803D
COLOR_ERROR = (0.753, 0.224, 0.169, 1)             # #C0392B
COLOR_WARNING = (0.718, 0.475, 0.122, 1)           # #B7791F

PRIMARY_HEX = "1D4ED8"
TEXT_HEX = "0F172A"
MUTED_HEX = "5B6472"
SUCCESS_HEX = "15803D"
ERROR_HEX = "C0392B"
WARNING_HEX = "B7791F"

# vector-diagram specific colors, matching the classic O / O+T / T triangle
ORIGINAL_COLOR = (0.851, 0.282, 0.059)   # red-orange
RESULTANT_COLOR = (0.086, 0.396, 0.835)  # blue
EFFECT_COLOR = (0.055, 0.604, 0.655)     # teal
ORIGINAL_HEX = "D9480F"
RESULTANT_HEX = "1665D5"
EFFECT_HEX = "0E9AA7"

GRAVITY = 9.80665  # m/s^2

# NOTE: Window.clearcolor is set by the merged app's tab switcher (see main.py),
# not here, since multiple tabs share one Window in the merged build.


# ---------- BEGIN BALANCING MATH ----------
def to_complex(mag, theta_clock_deg):
    """Map (magnitude, clockwise-degrees) onto the complex plane.

    Clockwise angles are mapped with a negative exponent, so the whole
    complex plane is simply reflected. Every vector in this module uses
    the same mapping, so sums, differences, products and quotients all
    behave normally - only the angle read-out needs converting back."""
    phi = -math.radians(theta_clock_deg)
    return cmath.rect(mag, phi)


def to_clock_deg(z):
    """Inverse of to_complex: complex number -> (magnitude, clockwise deg)."""
    mag, phi = cmath.polar(z)
    theta = (-math.degrees(phi)) % 360
    return mag, theta


def clock_position(theta_deg):
    """Nearest clock-face hour for an angle, for quick field reference."""
    hour = round(theta_deg / 30) % 12
    return 12 if hour == 0 else hour


def convert_phase(angle_deg, is_lag):
    """Mirrors a phase reading between lag and lead convention.
    Applying it twice returns the original angle (it's its own inverse),
    so the same function converts either direction."""
    return (360 - angle_deg) % 360 if is_lag else angle_deg


def single_plane_correction(O, OT, T):
    """Single-plane influence-coefficient solution.

    O  = original vibration vector
    OT = vibration vector with trial weight installed
    T  = trial weight vector (mass at angle)

    Returns (Wc, S, E) where:
      E  = effect of the trial weight      = OT - O
      S  = sensitivity (vibration per unit mass) = E / T
      Wc = TOTAL weight that must be present in the plane = -O / S

    Wc is the total, so if the trial weight is left installed the
    additional weight still to add is (Wc - T).
    Raises ValueError if the trial weight produced no usable change."""
    E = OT - O
    if abs(E) < 1e-9:
        raise ValueError("no-effect")
    S = E / T
    Wc = -O / S
    return Wc, S, E


def two_plane_correction(A10, A20, T1, A11, A21, T2, A12, A22):
    """Two-plane influence-coefficient solution, including cross-effect.

    A10, A20 = original vibration at bearing 1 and bearing 2
    T1       = trial weight vector placed in plane 1
    A11, A21 = vibration at bearings 1 and 2 with T1 installed
    T2       = trial weight vector placed in plane 2
    A12, A22 = vibration at bearings 1 and 2 with T2 installed
               (T1 having been removed first)

    Influence coefficients:
      a11 = effect of plane-1 weight on bearing 1 = (A11 - A10) / T1
      a21 = effect of plane-1 weight on bearing 2 = (A21 - A20) / T1
      a12 = effect of plane-2 weight on bearing 1 = (A12 - A10) / T2
      a22 = effect of plane-2 weight on bearing 2 = (A22 - A20) / T2

    Then solve simultaneously for the TOTAL weights W1, W2 that cancel
    both bearings at once:
      a11*W1 + a12*W2 = -A10
      a21*W1 + a22*W2 = -A20

    by Cramer's rule, with D = a11*a22 - a12*a21:
      W1 = (-A10*a22 + A20*a12) / D
      W2 = (-A20*a11 + A10*a21) / D

    Returns (W1, W2, coeffs_dict).
    Raises ValueError if a trial weight had no effect, or if the two
    planes are not independent enough to solve (D near zero)."""
    E11 = A11 - A10
    E21 = A21 - A20
    E12 = A12 - A10
    E22 = A22 - A20

    if abs(E11) < 1e-9 and abs(E21) < 1e-9:
        raise ValueError("no-effect-1")
    if abs(E12) < 1e-9 and abs(E22) < 1e-9:
        raise ValueError("no-effect-2")

    a11 = E11 / T1
    a21 = E21 / T1
    a12 = E12 / T2
    a22 = E22 / T2

    D = a11 * a22 - a12 * a21
    # Scale-aware singularity check: compare the determinant against the
    # magnitude of the terms that formed it, so the test works whatever
    # units the readings are in.
    scale = max(abs(a11 * a22), abs(a12 * a21), 1e-30)
    if abs(D) < 1e-9 * scale:
        raise ValueError("singular")

    W1 = (-A10 * a22 + A20 * a12) / D
    W2 = (-A20 * a11 + A10 * a21) / D

    coeffs = {"a11": a11, "a21": a21, "a12": a12, "a22": a22, "D": D}
    return W1, W2, coeffs


def estimate_trial_weight(rotor_mass_kg, radius_mm, rpm, force_pct):
    """Force-based trial weight estimate.

    Sizes the trial weight so its centrifugal force is a chosen small
    percentage of the rotor's static weight - large enough to produce a
    clear change in the reading, small enough to stay safe.

      centrifugal force  Fc = m * r * omega^2
      target force       Ft = (pct/100) * M * g

    Setting Fc = Ft and solving for m:
      m = (pct/100) * M * g / (r * omega^2)

    with omega = 2*pi*rpm/60, r in metres, M in kg -> m in kg.

    Returns (mass_grams, force_newtons, unbalance_g_mm).
    Raises ValueError on non-positive inputs."""
    if rotor_mass_kg <= 0 or radius_mm <= 0 or rpm <= 0 or force_pct <= 0:
        raise ValueError("bad-input")
    omega = 2.0 * math.pi * rpm / 60.0
    r_m = radius_mm / 1000.0
    target_force = (force_pct / 100.0) * rotor_mass_kg * GRAVITY
    mass_kg = target_force / (r_m * omega * omega)
    mass_g = mass_kg * 1000.0
    unbalance_g_mm = mass_g * radius_mm
    return mass_g, target_force, unbalance_g_mm


def split_weight(Wc_mag, Wc_angle, angle_a, angle_b):
    """Resolve one correction weight onto two fixed angular positions.

    Solves for real masses Wa, Wb such that the vector sum of a weight
    Wa at angle_a and a weight Wb at angle_b equals the required
    correction vector:

        Wa * unit(angle_a) + Wb * unit(angle_b) = Wc

    Writing the unit vectors as (x, y) components gives a 2x2 real
    system, solved by Cramer's rule with det = xa*yb - xb*ya.

    A negative result is physically meaningful: it means mass must go at
    the opposite side of that position (or be removed there instead).
    Raises ValueError if the two positions are parallel (0 or 180 deg
    apart), where no unique split exists."""
    ea = to_complex(1.0, angle_a)
    eb = to_complex(1.0, angle_b)
    C = to_complex(Wc_mag, Wc_angle)

    xa, ya = ea.real, ea.imag
    xb, yb = eb.real, eb.imag
    cx, cy = C.real, C.imag

    det = xa * yb - xb * ya
    if abs(det) < 1e-9:
        raise ValueError("parallel")

    Wa = (cx * yb - cy * xb) / det
    Wb = (xa * cy - ya * cx) / det
    return Wa, Wb


def fixed_positions(count, offset_deg):
    """Angles of `count` equally spaced fixed positions (blades, bolt
    holes), starting at offset_deg and running clockwise."""
    step = 360.0 / count
    return [(offset_deg + i * step) % 360.0 for i in range(count)]


def bracketing_positions(angles, target_deg):
    """Pick the two fixed positions that bracket a target angle.

    Returns (angle_before, angle_after). Works on the circle, so a target
    between the last and first position wraps correctly."""
    target = target_deg % 360.0
    ordered = sorted(a % 360.0 for a in angles)
    for i, a in enumerate(ordered):
        nxt = ordered[(i + 1) % len(ordered)]
        span = (nxt - a) % 360.0
        rel = (target - a) % 360.0
        # A zero span means duplicate positions; skip it.
        if span > 0 and rel <= span:
            return a, nxt
    # Fallback (should not be reached for a valid, non-degenerate set).
    return ordered[0], ordered[1 % len(ordered)]
# ---------- END BALANCING MATH ----------


# ---------- reusable UI building blocks ----------
class HeaderBar(BoxLayout):
    """Fixed blue app-bar at the top of the screen."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            height=dp(78),
            padding=(dp(16), dp(14)),
            **kwargs,
        )
        with self.canvas.before:
            Color(*COLOR_PRIMARY)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        title = Label(
            text="[b]Rotor Balance Calculator[/b]",
            markup=True,
            color=(1, 1, 1, 1),
            font_size=dp(20),
            size_hint_y=None,
            height=dp(26),
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self.subtitle = Label(
            text="Influence coefficient method",
            color=(0.85, 0.9, 1, 1),
            font_size=dp(14),
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="middle",
        )
        self.subtitle.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self.add_widget(title)
        self.add_widget(self.subtitle)

    def set_subtitle(self, text):
        self.subtitle.text = text

    def _update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class Panel(BoxLayout):
    """A rounded white/light-blue card with a border, used to group
    sections (vector diagram, rotor view, etc.)."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(8), **kwargs)
        with self.canvas.before:
            Color(*COLOR_PANEL_BG)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
            Color(*COLOR_BORDER)
            self.border_line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(14)), width=1.2
            )
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(14))


# ---------- 360-degree polar vector chart ----------
class PolarChart(Widget):
    """Draws the classic balancing vector triangle: Original and
    Trial-run vectors from the center, with the Effect vector drawn
    tip-to-tip between them (since Effect = Trial-run - Original),
    plus the Correction vector from the center. Numeric values are
    listed in the legend below the chart, not on the chart itself."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.original = None
        self.trial_run = None
        self.correction_angle = None
        self.correction_color = (0.082, 0.502, 0.235)
        self.bind(pos=self.redraw, size=self.redraw)

    def set_data(self, original, trial_run, correction_angle=None, correction_color=None):
        self.original = original
        self.trial_run = trial_run
        self.correction_angle = correction_angle
        if correction_color is not None:
            self.correction_color = correction_color
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        if self.width <= 1 or self.height <= 1:
            return
        cx = self.center_x
        cy = self.center_y
        radius = min(self.width, self.height) * 0.40

        with self.canvas:
            # outer circle + cross hairs
            Color(0.78, 0.83, 0.90, 1)
            Line(circle=(cx, cy, radius), width=1.1)
            Line(circle=(cx, cy, radius * 0.66), width=0.8)
            Line(circle=(cx, cy, radius * 0.33), width=0.8)
            Line(points=[cx - radius, cy, cx + radius, cy], width=0.8)
            Line(points=[cx, cy - radius, cx, cy + radius], width=0.8)

            # 30-degree tick marks
            Color(0.86, 0.89, 0.94, 1)
            for deg in range(0, 360, 30):
                rad = math.radians(deg)
                x1 = cx + radius * 0.92 * math.sin(rad)
                y1 = cy + radius * 0.92 * math.cos(rad)
                x2 = cx + radius * math.sin(rad)
                y2 = cy + radius * math.cos(rad)
                Line(points=[x1, y1, x2, y2], width=0.9)

        # Scale is based ONLY on the vibration vectors (Original, Trial-run).
        # Correction weight is a different physical quantity (mass, not
        # vibration), so it is drawn as a direction indicator at fixed
        # length rather than being scaled against the vibration vectors.
        mags = []
        if self.original:
            mags.append(self.original["mag"])
        if self.trial_run:
            mags.append(self.trial_run["mag"])
        max_mag = max(mags) if mags else 0

        with self.canvas:
            if max_mag > 0:
                scale = radius * 0.86 / max_mag

                ox, oy = (None, None)
                if self.original:
                    ox, oy = self._point(cx, cy, scale, self.original)
                    self._draw_arrow(cx, cy, ox, oy, self.original["color"])

                tx, ty = (None, None)
                if self.trial_run:
                    tx, ty = self._point(cx, cy, scale, self.trial_run)
                    self._draw_arrow(cx, cy, tx, ty, self.trial_run["color"])

                # Effect vector: tip of Original -> tip of Trial-run
                if ox is not None and tx is not None:
                    self._draw_arrow(ox, oy, tx, ty, EFFECT_COLOR)

            # correction direction indicator
            if self.correction_angle is not None:
                r, g, b = self.correction_color
                Color(r, g, b, 1)
                rad = math.radians(self.correction_angle)
                ex = cx + radius * 0.94 * math.sin(rad)
                ey = cy + radius * 0.94 * math.cos(rad)
                Line(points=[cx, cy, ex, ey], width=2.0)
                Ellipse(pos=(ex - dp(5), ey - dp(5)), size=(dp(10), dp(10)))

    @staticmethod
    def _point(cx, cy, scale, v):
        rad = math.radians(v["angle"])
        return (cx + v["mag"] * scale * math.sin(rad),
                cy + v["mag"] * scale * math.cos(rad))

    @staticmethod
    def _draw_arrow(x1, y1, x2, y2, color):
        r, g, b = color[:3]
        Color(r, g, b, 1)
        Line(points=[x1, y1, x2, y2], width=2.0)
        ang = math.atan2(y2 - y1, x2 - x1)
        head = dp(10)
        spread = math.radians(24)
        Triangle(points=[
            x2, y2,
            x2 - head * math.cos(ang - spread), y2 - head * math.sin(ang - spread),
            x2 - head * math.cos(ang + spread), y2 - head * math.sin(ang + spread),
        ])


# ---------- rotor view with animated correction marker ----------
class RotorView(Widget):
    """A simple face-on rotor illustration showing the reference mark,
    a trial-weight marker, and an animated correction-weight marker."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trial_angle = None
        self.correction_angle = None
        self._anim_angle = 0.0
        self._anim = None

        self.trial_label = Label(
            text="Trial",
            markup=True,
            font_size=dp(12),
            color=COLOR_TEXT_MUTED,
            size_hint=(None, None),
            size=(dp(46), dp(18)),
            opacity=0,
        )
        self.corr_label = Label(
            text="Correct",
            markup=True,
            font_size=dp(12),
            bold=True,
            color=COLOR_SUCCESS,
            size_hint=(None, None),
            size=(dp(58), dp(18)),
            opacity=0,
        )
        self.add_widget(self.trial_label)
        self.add_widget(self.corr_label)
        self.bind(pos=self._rebuild, size=self._rebuild)

    def set_weights(self, trial_angle, correction_angle):
        self.trial_angle = trial_angle
        self.correction_angle = correction_angle
        if self._anim is not None:
            self._anim.cancel(self)
        self._anim_angle = 0.0
        self._rebuild()
        if correction_angle is not None:
            self._anim = Animation(_anim_angle=correction_angle, duration=0.9, t="out_cubic")
            self._anim.bind(on_progress=lambda *a: self._update_markers())
            self._anim.start(self)

    def _rebuild(self, *args):
        self.canvas.clear()
        if self.width <= 1 or self.height <= 1:
            return
        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) * 0.36

        with self.canvas:
            Color(0.90, 0.93, 0.97, 1)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))
            Color(0.72, 0.78, 0.86, 1)
            Line(circle=(cx, cy, radius), width=1.4)
            Color(0.55, 0.62, 0.72, 1)
            Line(circle=(cx, cy, radius * 0.16), width=1.2)

            # reference mark at 0 degrees (12 o'clock)
            Color(*COLOR_PRIMARY)
            Line(points=[cx, cy + radius * 0.82, cx, cy + radius * 1.02], width=2.4)

        self._update_markers()

    def _update_markers(self, *args):
        if self.width <= 1 or self.height <= 1:
            return
        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) * 0.36

        # Markers are redrawn into a fresh canvas layer each frame, so the
        # base rotor art is rebuilt alongside them (cheap at this size).
        self.canvas.after.clear()
        with self.canvas.after:
            if self.trial_angle is not None:
                rad = math.radians(self.trial_angle)
                x = cx + radius * 0.78 * math.sin(rad)
                y = cy + radius * 0.78 * math.cos(rad)
                Color(0.62, 0.66, 0.74, 1)
                Ellipse(pos=(x - dp(8), y - dp(8)), size=(dp(16), dp(16)))
                self.trial_label.opacity = 1
                self.trial_label.center = (x, y - dp(20))
            else:
                self.trial_label.opacity = 0

            if self.correction_angle is not None:
                rad = math.radians(self._anim_angle)
                x = cx + radius * 0.78 * math.sin(rad)
                y = cy + radius * 0.78 * math.cos(rad)
                Color(*COLOR_SUCCESS)
                Ellipse(pos=(x - dp(10), y - dp(10)), size=(dp(20), dp(20)))
                self.corr_label.opacity = 1
                self.corr_label.center = (x, y - dp(22))
            else:
                self.corr_label.opacity = 0


class LabeledInput(BoxLayout):
    def __init__(self, label_text, hint_text="", **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(72), **kwargs)
        self.label = Label(
            text=label_text,
            size_hint_y=None,
            height=dp(24),
            font_size=dp(14),
            color=COLOR_TEXT_MUTED,
            halign="left",
            bold=True,
        )
        self.label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self.input = ModernInput(
            hint_text=hint_text,
            multiline=False,
            height=dp(46),
            font_size=dp(17),
            panel_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            accent=COLOR_PRIMARY,
        )
        self.add_widget(self.label)
        self.add_widget(self.input)

    @property
    def value(self):
        try:
            return float(self.input.text)
        except ValueError:
            return None

    def set_value(self, v, fmt="{:.3f}"):
        self.input.text = fmt.format(v)


# ---------- small helpers for building forms ----------
def section_label(text):
    lbl = Label(
        text=f"[b][color={TEXT_HEX}]{text}[/color][/b]",
        markup=True,
        size_hint_y=None,
        height=dp(26),
        font_size=dp(15),
        halign="left",
        valign="middle",
    )
    lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
    return lbl


def note_label(markup_text, height=dp(46)):
    lbl = Label(
        text=markup_text,
        markup=True,
        size_hint_y=None,
        height=height,
        halign="left",
        valign="top",
    )
    lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
    return lbl


def result_label():
    lbl = Label(
        text="",
        markup=True,
        size_hint_y=None,
        halign="left",
        valign="top",
        font_size=dp(16),
        color=COLOR_TEXT,
    )
    lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1] + dp(10)))
    lbl.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
    return lbl


def scroll_form():
    """Returns (scrollview, form_gridlayout) ready to receive widgets."""
    scroll = ScrollView()
    form = GridLayout(
        cols=1, spacing=dp(14), size_hint_y=None,
        padding=(dp(14), dp(14), dp(14), dp(24))
    )
    form.bind(minimum_height=form.setter("height"))
    scroll.add_widget(form)
    return scroll, form


def footer_label():
    lbl = Label(
        text=f"[color={MUTED_HEX}]Created by Gnaneswar[/color]",
        markup=True,
        size_hint_y=None,
        height=dp(40),
        halign="center",
        valign="middle",
        font_size=dp(13),
    )
    lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
    return lbl


TAB_SUBTITLES = {
    "single": "Single plane \u00b7 influence coefficient method",
    "two": "Two plane \u00b7 with cross-effect",
    "trial": "Trial weight estimator \u00b7 force based",
    "split": "Split a correction onto fixed positions",
    "trim": "Trim run \u00b7 reuse known sensitivity",
}


class BalanceApp(App):
    def build(self):
        self.title = "Rotor Balance"

        # Shared phase convention across every tab that reads phase.
        # False = Phase Lag (angles used as entered).
        self.apply_conversion = False
        self._conv_pairs = []          # list of (lag_btn, lead_btn)
        self.last_sensitivity = None   # (mag, angle) from the last single-plane solve

        root = BoxLayout(orientation="vertical")
        self.header = HeaderBar()
        root.add_widget(self.header)
        root.add_widget(self._build_tab_bar())

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(self._make_screen("single", self._build_single_tab()))
        self.sm.add_widget(self._make_screen("two", self._build_two_plane_tab()))
        self.sm.add_widget(self._make_screen("trial", self._build_trial_tab()))
        self.sm.add_widget(self._make_screen("split", self._build_split_tab()))
        self.sm.add_widget(self._make_screen("trim", self._build_trim_tab()))
        root.add_widget(self.sm)

        self._update_convention_buttons()
        self.switch_tab("single")
        return root

    # ---------- tab plumbing ----------
    @staticmethod
    def _make_screen(name, content):
        scr = Screen(name=name)
        scr.add_widget(content)
        return scr

    def _build_tab_bar(self):
        """Two rows of pills: 3 on top, 2 below, so labels stay readable
        on a narrow phone screen."""
        bar = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(92),
                         padding=[dp(8), dp(6)], spacing=dp(6))
        row1 = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        row2 = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))

        self.tab_buttons = {}
        specs_row1 = [("single", "Single Plane"), ("two", "Two Plane"), ("trial", "Trial Weight")]
        specs_row2 = [("split", "Weight Split"), ("trim", "Trim Balance")]

        for row, specs in ((row1, specs_row1), (row2, specs_row2)):
            for name, label in specs:
                btn = PillButton(label, accent=COLOR_PRIMARY, inactive=COLOR_PANEL_BG,
                                  text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
                btn.bind(on_release=lambda inst, n=name: self.switch_tab(n))
                row.add_widget(btn)
                self.tab_buttons[name] = btn

        bar.add_widget(row1)
        bar.add_widget(row2)
        return bar

    def switch_tab(self, name):
        self.sm.current = name
        for key, btn in self.tab_buttons.items():
            btn.set_active(key == name)
        self.header.set_subtitle(TAB_SUBTITLES.get(name, ""))

    # ---------- phase convention (shared) ----------
    def _make_convention_block(self, parent):
        parent.add_widget(section_label("PHASE CONVENTION"))
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        lag_btn = PillButton("Phase Lag", accent=COLOR_PRIMARY, inactive=COLOR_PANEL_BG,
                              text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        lead_btn = PillButton("Phase Lead", accent=COLOR_PRIMARY, inactive=COLOR_PANEL_BG,
                               text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        lag_btn.bind(on_release=lambda inst: self.set_convention(False))
        lead_btn.bind(on_release=lambda inst: self.set_convention(True))
        row.add_widget(lag_btn)
        row.add_widget(lead_btn)
        parent.add_widget(row)
        self._conv_pairs.append((lag_btn, lead_btn))

        parent.add_widget(note_label(
            f"[color={MUTED_HEX}][size=14]"
            "[b]Lag[/b]: vibration peak trails behind the reference mark, opposite "
            "the direction of shaft rotation - most instruments' default.\n"
            "[b]Lead[/b]: peak appears ahead of the reference mark, in the same "
            "direction as shaft rotation.[/size][/color]", height=dp(70)))

    def set_convention(self, apply_conversion):
        self.apply_conversion = apply_conversion
        self._update_convention_buttons()
        # Recompute whichever tabs already have results showing.
        self.compute_single(None, quiet=True)
        self.compute_two_plane(None, quiet=True)
        self.compute_trim(None, quiet=True)

    def _update_convention_buttons(self):
        for lag_btn, lead_btn in self._conv_pairs:
            lead_btn.set_active(self.apply_conversion)
            lag_btn.set_active(not self.apply_conversion)

    # ---------- trial-weight-handling toggle (shared pattern) ----------
    def _make_trial_handling_block(self, parent, attr_name, title="TRIAL WEIGHT AFTER THE RUN",
                                    note=None):
        """Adds a Removed / Left-in-place selector. Stores the boolean on
        self.<attr_name> (True = trial weight was removed)."""
        setattr(self, attr_name, True)
        parent.add_widget(section_label(title))
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        rem_btn = PillButton("Removed", accent=COLOR_PRIMARY, inactive=COLOR_PANEL_BG,
                              text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        keep_btn = PillButton("Left in place", accent=COLOR_PRIMARY, inactive=COLOR_PANEL_BG,
                               text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)

        def _set(removed):
            setattr(self, attr_name, removed)
            rem_btn.set_active(removed)
            keep_btn.set_active(not removed)
            self.compute_single(None, quiet=True)
            self.compute_two_plane(None, quiet=True)

        rem_btn.bind(on_release=lambda inst: _set(True))
        keep_btn.bind(on_release=lambda inst: _set(False))
        rem_btn.set_active(True)
        keep_btn.set_active(False)
        row.add_widget(rem_btn)
        row.add_widget(keep_btn)
        parent.add_widget(row)
        default_note = ("If the trial weight is left on the rotor, the app subtracts it "
                        "from the total so you only add the difference.")
        parent.add_widget(note_label(
            f"[color={MUTED_HEX}][size=14]{note or default_note}[/size][/color]",
            height=dp(62 if note else 46)))

    # =====================================================
    # TAB 1 - SINGLE PLANE
    # =====================================================
    def _build_single_tab(self):
        scroll, form = scroll_form()

        form.add_widget(note_label(
            f"[color={MUTED_HEX}][size=14]Angles measured clockwise from the "
            "phase reference mark, as viewed from the sensor end.[/size][/color]"))

        panel = Panel(size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))

        self._make_convention_block(panel)
        self._make_trial_handling_block(panel, "single_trial_removed")

        self.o_amp = LabeledInput("ORIGINAL VIBRATION AMPLITUDE", "e.g. 4.2")
        self.o_phase = LabeledInput("ORIGINAL PHASE ANGLE (deg)", "e.g. 48")
        self.t_wt = LabeledInput("TRIAL WEIGHT MASS", "e.g. 5.0")
        self.t_angle = LabeledInput("TRIAL WEIGHT PLACEMENT ANGLE (deg)", "e.g. 90")
        self.tr_amp = LabeledInput("VIBRATION AMPLITUDE WITH TRIAL WEIGHT", "e.g. 2.1")
        self.tr_phase = LabeledInput("PHASE ANGLE WITH TRIAL WEIGHT (deg)", "e.g. 310")

        for w in (self.o_amp, self.o_phase, self.t_wt, self.t_angle, self.tr_amp, self.tr_phase):
            panel.add_widget(w)

        btn = RoundedButton(text="Compute Correction Weight", height=dp(50), accent=COLOR_PRIMARY)
        btn.bind(on_release=self.compute_single)
        panel.add_widget(btn)
        form.add_widget(panel)

        self.result_label = result_label()
        form.add_widget(self.result_label)

        chart_panel = Panel(size_hint_y=None)
        chart_panel.bind(minimum_height=chart_panel.setter("height"))
        chart_panel.add_widget(section_label("Vector Diagram"))
        chart_panel.add_widget(note_label(
            f"[color={MUTED_HEX}][size=13]Angles below are shown after "
            "phase-convention conversion.[/size][/color]", height=dp(22)))
        self.polar_chart = PolarChart(size_hint_y=None, height=dp(280))
        chart_panel.add_widget(self.polar_chart)
        self.chart_legend = result_label()
        self.chart_legend.font_size = dp(15)
        chart_panel.add_widget(self.chart_legend)
        form.add_widget(chart_panel)

        rotor_panel = Panel(size_hint_y=None, height=dp(340))
        rotor_panel.add_widget(section_label("Rotor View"))
        self.rotor_view = RotorView()
        rotor_panel.add_widget(self.rotor_view)
        form.add_widget(rotor_panel)

        form.add_widget(footer_label())
        return scroll

    def compute_single(self, instance, quiet=False):
        vals = [self.o_amp.value, self.o_phase.value, self.t_wt.value,
                self.t_angle.value, self.tr_amp.value, self.tr_phase.value]
        if any(v is None for v in vals):
            if not quiet:
                self.result_label.text = (
                    f"[color={ERROR_HEX}]Please fill in every field with a number.[/color]")
            return
        o_amp, o_phase, t_wt, t_angle, tr_amp, tr_phase = vals

        if t_wt <= 0:
            self.result_label.text = (
                f"[color={ERROR_HEX}]Trial weight must be greater than zero.[/color]")
            return

        o_phase_i = convert_phase(o_phase, self.apply_conversion)
        tr_phase_i = convert_phase(tr_phase, self.apply_conversion)

        O = to_complex(o_amp, o_phase_i)
        OT = to_complex(tr_amp, tr_phase_i)
        T = to_complex(t_wt, t_angle)

        try:
            Wc, S, E = single_plane_correction(O, OT, T)
        except ValueError:
            self.result_label.text = (
                f"[color={WARNING_HEX}]The trial weight barely changed the vibration reading. "
                "Try a heavier trial weight or a different placement angle.[/color]")
            return

        # What still has to be installed, given what is on the rotor now.
        W_add = Wc if self.single_trial_removed else (Wc - T)
        residual = O + S * Wc

        e_mag, e_ang = to_clock_deg(E)
        s_mag, s_ang = to_clock_deg(S)
        wc_mag, wc_ang = to_clock_deg(Wc)
        add_mag, add_ang = to_clock_deg(W_add)
        res_mag, _ = to_clock_deg(residual)

        # Trial weight adequacy check - a change that is too small makes the
        # sensitivity unreliable, even though the arithmetic still works.
        pct_change = (abs(E) / abs(O) * 100.0) if abs(O) > 1e-12 else 0.0
        phase_change = abs((tr_phase_i - o_phase_i + 180.0) % 360.0 - 180.0)
        if pct_change < 20.0 and phase_change < 20.0:
            warn = (f"\n\n[color={WARNING_HEX}]Note: the trial weight changed amplitude by only "
                    f"{pct_change:.0f}% and phase by {phase_change:.0f}\u00b0. A change of at "
                    "least 20-30% in one of them gives a more reliable result.[/color]")
        else:
            warn = ""

        if self.single_trial_removed:
            action = ("Remove the trial weight, then install the correction weight\n"
                      "at the stated angle (clockwise from the reference mark).")
            headline = f"CORRECTION WEIGHT: {wc_mag:.2f} @ {wc_ang:.1f}\u00b0"
        else:
            action = ("Leave the trial weight where it is and add the extra weight\n"
                      "shown above at the stated angle (clockwise from the reference mark).")
            headline = f"ADD: {add_mag:.2f} @ {add_ang:.1f}\u00b0"

        self.last_sensitivity = (s_mag, s_ang)

        self.result_label.text = (
            f"[b][color={SUCCESS_HEX}]{headline} "
            f"(~{clock_position(add_ang if not self.single_trial_removed else wc_ang)} o'clock)"
            f"[/color][/b]\n\n"
            f"[color={MUTED_HEX}]Total weight needed in plane: {wc_mag:.2f} @ {wc_ang:.1f}\u00b0\n"
            f"Effect vector (E): {e_mag:.3f} @ {e_ang:.1f}\u00b0\n"
            f"Sensitivity (S = E/T): {s_mag:.4f} per unit mass @ {s_ang:.1f}\u00b0\n"
            f"Predicted residual vibration: {res_mag:.3f}[/color]\n\n"
            f"[color={TEXT_HEX}]{action}[/color]{warn}"
        )

        self.polar_chart.set_data(
            original={"mag": o_amp, "angle": o_phase_i, "color": ORIGINAL_COLOR},
            trial_run={"mag": tr_amp, "angle": tr_phase_i, "color": RESULTANT_COLOR},
            correction_angle=wc_ang,
            correction_color=COLOR_SUCCESS[:3],
        )
        self.chart_legend.text = "\n\n".join([
            f"[color={ORIGINAL_HEX}]\u25CF  Original: {o_amp:.2f} @ {o_phase_i:.1f}\u00b0[/color]",
            f"[color={RESULTANT_HEX}]\u25CF  Trial run (O+T): {tr_amp:.2f} @ {tr_phase_i:.1f}\u00b0[/color]",
            f"[color={EFFECT_HEX}]\u25CF  Effect of trial weight: {e_mag:.2f} @ {e_ang:.1f}\u00b0[/color]",
            f"[color={SUCCESS_HEX}]\u25CF  Correction weight: {wc_mag:.2f} @ {wc_ang:.1f}\u00b0[/color]",
        ])
        self.rotor_view.set_weights(trial_angle=t_angle, correction_angle=wc_ang)

    # =====================================================
    # TAB 2 - TWO PLANE
    # =====================================================
    def _build_two_plane_tab(self):
        scroll, form = scroll_form()

        form.add_widget(note_label(
            f"[color={MUTED_HEX}][size=14]Two-plane balancing accounts for cross-effect: "
            "weight in one plane changes vibration at both bearings. Take the plane-2 "
            "trial run with the plane-1 trial weight already removed.[/size][/color]",
            height=dp(70)))

        panel = Panel(size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))

        self._make_convention_block(panel)
        self._make_trial_handling_block(
            panel, "two_trial_removed",
            title="TRIAL WEIGHT 2 AFTER THE RUN",
            note=("Trial weight 1 must already have been removed before trial run 2 - "
                  "the cross-effect maths depends on it. This setting is only about "
                  "whether trial weight 2 is still on the rotor."))

        panel.add_widget(section_label("ORIGINAL RUN (no trial weights)"))
        self.tp_a1_amp = LabeledInput("BEARING 1 AMPLITUDE", "e.g. 6.0")
        self.tp_a1_ph = LabeledInput("BEARING 1 PHASE (deg)", "e.g. 30")
        self.tp_a2_amp = LabeledInput("BEARING 2 AMPLITUDE", "e.g. 4.5")
        self.tp_a2_ph = LabeledInput("BEARING 2 PHASE (deg)", "e.g. 200")
        for w in (self.tp_a1_amp, self.tp_a1_ph, self.tp_a2_amp, self.tp_a2_ph):
            panel.add_widget(w)

        panel.add_widget(section_label("TRIAL RUN 1 (weight in plane 1)"))
        self.tp_t1_wt = LabeledInput("TRIAL WEIGHT 1 MASS", "e.g. 10")
        self.tp_t1_ang = LabeledInput("TRIAL WEIGHT 1 ANGLE (deg)", "e.g. 0")
        self.tp_b1_amp = LabeledInput("BEARING 1 AMPLITUDE", "e.g. 4.0")
        self.tp_b1_ph = LabeledInput("BEARING 1 PHASE (deg)", "e.g. 80")
        self.tp_b2_amp = LabeledInput("BEARING 2 AMPLITUDE", "e.g. 4.8")
        self.tp_b2_ph = LabeledInput("BEARING 2 PHASE (deg)", "e.g. 210")
        for w in (self.tp_t1_wt, self.tp_t1_ang, self.tp_b1_amp,
                  self.tp_b1_ph, self.tp_b2_amp, self.tp_b2_ph):
            panel.add_widget(w)

        panel.add_widget(section_label("TRIAL RUN 2 (weight in plane 2)"))
        self.tp_t2_wt = LabeledInput("TRIAL WEIGHT 2 MASS", "e.g. 10")
        self.tp_t2_ang = LabeledInput("TRIAL WEIGHT 2 ANGLE (deg)", "e.g. 0")
        self.tp_c1_amp = LabeledInput("BEARING 1 AMPLITUDE", "e.g. 6.3")
        self.tp_c1_ph = LabeledInput("BEARING 1 PHASE (deg)", "e.g. 40")
        self.tp_c2_amp = LabeledInput("BEARING 2 AMPLITUDE", "e.g. 2.2")
        self.tp_c2_ph = LabeledInput("BEARING 2 PHASE (deg)", "e.g. 250")
        for w in (self.tp_t2_wt, self.tp_t2_ang, self.tp_c1_amp,
                  self.tp_c1_ph, self.tp_c2_amp, self.tp_c2_ph):
            panel.add_widget(w)

        btn = RoundedButton(text="Compute Both Planes", height=dp(50), accent=COLOR_PRIMARY)
        btn.bind(on_release=self.compute_two_plane)
        panel.add_widget(btn)
        form.add_widget(panel)

        self.tp_result = result_label()
        form.add_widget(self.tp_result)

        # Chart for bearing 1 / plane 1
        cp1 = Panel(size_hint_y=None)
        cp1.bind(minimum_height=cp1.setter("height"))
        cp1.add_widget(section_label("Bearing 1 \u00b7 Plane 1"))
        self.tp_chart1 = PolarChart(size_hint_y=None, height=dp(260))
        cp1.add_widget(self.tp_chart1)
        self.tp_legend1 = result_label()
        self.tp_legend1.font_size = dp(14)
        cp1.add_widget(self.tp_legend1)
        form.add_widget(cp1)

        # Chart for bearing 2 / plane 2
        cp2 = Panel(size_hint_y=None)
        cp2.bind(minimum_height=cp2.setter("height"))
        cp2.add_widget(section_label("Bearing 2 \u00b7 Plane 2"))
        self.tp_chart2 = PolarChart(size_hint_y=None, height=dp(260))
        cp2.add_widget(self.tp_chart2)
        self.tp_legend2 = result_label()
        self.tp_legend2.font_size = dp(14)
        cp2.add_widget(self.tp_legend2)
        form.add_widget(cp2)

        form.add_widget(footer_label())
        return scroll

    def compute_two_plane(self, instance, quiet=False):
        fields = [
            self.tp_a1_amp, self.tp_a1_ph, self.tp_a2_amp, self.tp_a2_ph,
            self.tp_t1_wt, self.tp_t1_ang, self.tp_b1_amp, self.tp_b1_ph,
            self.tp_b2_amp, self.tp_b2_ph,
            self.tp_t2_wt, self.tp_t2_ang, self.tp_c1_amp, self.tp_c1_ph,
            self.tp_c2_amp, self.tp_c2_ph,
        ]
        vals = [f.value for f in fields]
        if any(v is None for v in vals):
            if not quiet:
                self.tp_result.text = (
                    f"[color={ERROR_HEX}]Please fill in every field with a number.[/color]")
            return

        (a1m, a1p, a2m, a2p,
         t1w, t1a, b1m, b1p, b2m, b2p,
         t2w, t2a, c1m, c1p, c2m, c2p) = vals

        if t1w <= 0 or t2w <= 0:
            self.tp_result.text = (
                f"[color={ERROR_HEX}]Both trial weights must be greater than zero.[/color]")
            return

        cv = self.apply_conversion
        a1p_i, a2p_i = convert_phase(a1p, cv), convert_phase(a2p, cv)
        b1p_i, b2p_i = convert_phase(b1p, cv), convert_phase(b2p, cv)
        c1p_i, c2p_i = convert_phase(c1p, cv), convert_phase(c2p, cv)

        A10 = to_complex(a1m, a1p_i)
        A20 = to_complex(a2m, a2p_i)
        A11 = to_complex(b1m, b1p_i)
        A21 = to_complex(b2m, b2p_i)
        A12 = to_complex(c1m, c1p_i)
        A22 = to_complex(c2m, c2p_i)
        T1 = to_complex(t1w, t1a)
        T2 = to_complex(t2w, t2a)

        try:
            W1, W2, co = two_plane_correction(A10, A20, T1, A11, A21, T2, A12, A22)
        except ValueError as exc:
            reason = str(exc)
            if reason == "no-effect-1":
                msg = ("Trial weight 1 barely changed either bearing. "
                       "Use a heavier weight or a different angle.")
            elif reason == "no-effect-2":
                msg = ("Trial weight 2 barely changed either bearing. "
                       "Use a heavier weight or a different angle.")
            else:
                msg = ("The two trial runs are too similar to separate the planes. "
                       "Try different trial weight angles or masses.")
            self.tp_result.text = f"[color={WARNING_HEX}]{msg}[/color]"
            return

        # Trial weight 1 is always already off the rotor by this point (the
        # plane-2 trial run requires it), so plane 1 always gets the full
        # correction. Only trial weight 2 can still be installed.
        W1_add = W1
        W2_add = W2 if self.two_trial_removed else (W2 - T2)

        w1m, w1a = to_clock_deg(W1)
        w2m, w2a = to_clock_deg(W2)
        add1m, add1a = to_clock_deg(W1_add)
        add2m, add2a = to_clock_deg(W2_add)

        # Predicted residuals at both bearings with W1 and W2 installed.
        r1 = A10 + co["a11"] * W1 + co["a12"] * W2
        r2 = A20 + co["a21"] * W1 + co["a22"] * W2
        r1m, _ = to_clock_deg(r1)
        r2m, _ = to_clock_deg(r2)

        a11m, a11a = to_clock_deg(co["a11"])
        a21m, a21a = to_clock_deg(co["a21"])
        a12m, a12a = to_clock_deg(co["a12"])
        a22m, a22a = to_clock_deg(co["a22"])

        if self.two_trial_removed:
            action = ("Remove trial weight 2, then install both correction weights\n"
                      "together before the next run.")
            l1 = f"PLANE 1: {w1m:.2f} @ {w1a:.1f}\u00b0"
            l2 = f"PLANE 2: {w2m:.2f} @ {w2a:.1f}\u00b0"
        else:
            action = ("Leave trial weight 2 where it is. Install the plane 1 weight\n"
                      "in full, and add only the extra shown for plane 2.")
            l1 = f"PLANE 1 - INSTALL: {add1m:.2f} @ {add1a:.1f}\u00b0"
            l2 = f"PLANE 2 - ADD: {add2m:.2f} @ {add2a:.1f}\u00b0"

        self.tp_result.text = (
            f"[b][color={SUCCESS_HEX}]{l1}\n{l2}[/color][/b]\n\n"
            f"[color={MUTED_HEX}]Total needed \u2014 plane 1: {w1m:.2f} @ {w1a:.1f}\u00b0, "
            f"plane 2: {w2m:.2f} @ {w2a:.1f}\u00b0\n\n"
            f"Influence coefficients (per unit mass):\n"
            f"  a11 plane1\u2192brg1: {a11m:.4f} @ {a11a:.1f}\u00b0\n"
            f"  a21 plane1\u2192brg2: {a21m:.4f} @ {a21a:.1f}\u00b0\n"
            f"  a12 plane2\u2192brg1: {a12m:.4f} @ {a12a:.1f}\u00b0\n"
            f"  a22 plane2\u2192brg2: {a22m:.4f} @ {a22a:.1f}\u00b0\n\n"
            f"Predicted residual \u2014 brg 1: {r1m:.3f}, brg 2: {r2m:.3f}[/color]\n\n"
            f"[color={TEXT_HEX}]{action}[/color]"
        )

        self.tp_chart1.set_data(
            original={"mag": a1m, "angle": a1p_i, "color": ORIGINAL_COLOR},
            trial_run={"mag": b1m, "angle": b1p_i, "color": RESULTANT_COLOR},
            correction_angle=w1a,
            correction_color=COLOR_SUCCESS[:3],
        )
        self.tp_legend1.text = "\n\n".join([
            f"[color={ORIGINAL_HEX}]\u25CF  Brg 1 original: {a1m:.2f} @ {a1p_i:.1f}\u00b0[/color]",
            f"[color={RESULTANT_HEX}]\u25CF  Brg 1 with trial wt 1: {b1m:.2f} @ {b1p_i:.1f}\u00b0[/color]",
            f"[color={SUCCESS_HEX}]\u25CF  Plane 1 correction: {w1m:.2f} @ {w1a:.1f}\u00b0[/color]",
        ])

        self.tp_chart2.set_data(
            original={"mag": a2m, "angle": a2p_i, "color": ORIGINAL_COLOR},
            trial_run={"mag": c2m, "angle": c2p_i, "color": RESULTANT_COLOR},
            correction_angle=w2a,
            correction_color=COLOR_SUCCESS[:3],
        )
        self.tp_legend2.text = "\n\n".join([
            f"[color={ORIGINAL_HEX}]\u25CF  Brg 2 original: {a2m:.2f} @ {a2p_i:.1f}\u00b0[/color]",
            f"[color={RESULTANT_HEX}]\u25CF  Brg 2 with trial wt 2: {c2m:.2f} @ {c2p_i:.1f}\u00b0[/color]",
            f"[color={SUCCESS_HEX}]\u25CF  Plane 2 correction: {w2m:.2f} @ {w2a:.1f}\u00b0[/color]",
        ])

    # =====================================================
    # TAB 3 - TRIAL WEIGHT ESTIMATION
    # =====================================================
    def _build_trial_tab(self):
        scroll, form = scroll_form()

        form.add_widget(note_label(
            f"[color={MUTED_HEX}][size=14]Sizes a trial weight so its centrifugal force is a "
            "small, chosen fraction of the rotor's static weight - big enough to move the "
            "reading, small enough to stay safe.[/size][/color]", height=dp(70)))

        panel = Panel(size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))

        self.tw_mass = LabeledInput("ROTOR MASS (kg)", "e.g. 500")
        self.tw_radius = LabeledInput("CORRECTION RADIUS (mm)", "e.g. 300")
        self.tw_rpm = LabeledInput("BALANCING SPEED (RPM)", "e.g. 1500")
        self.tw_pct = LabeledInput("TARGET FORCE (% of rotor weight)", "e.g. 10")
        self.tw_pct.input.text = "10"
        for w in (self.tw_mass, self.tw_radius, self.tw_rpm, self.tw_pct):
            panel.add_widget(w)

        panel.add_widget(note_label(
            f"[color={MUTED_HEX}][size=13]5-10% is the usual range. Use the lower end on "
            "large or high-speed rotors, the higher end on small or slow ones."
            "[/size][/color]", height=dp(46)))

        btn = RoundedButton(text="Estimate Trial Weight", height=dp(50), accent=COLOR_PRIMARY)
        btn.bind(on_release=self.compute_trial_weight)
        panel.add_widget(btn)
        form.add_widget(panel)

        self.tw_result = result_label()
        form.add_widget(self.tw_result)
        form.add_widget(footer_label())
        return scroll

    def compute_trial_weight(self, instance):
        vals = [self.tw_mass.value, self.tw_radius.value,
                self.tw_rpm.value, self.tw_pct.value]
        if any(v is None for v in vals):
            self.tw_result.text = (
                f"[color={ERROR_HEX}]Please fill in every field with a number.[/color]")
            return
        mass, radius, rpm, pct = vals
        try:
            mass_g, force_n, unbal = estimate_trial_weight(mass, radius, rpm, pct)
        except ValueError:
            self.tw_result.text = (
                f"[color={ERROR_HEX}]All four values must be greater than zero.[/color]")
            return

        omega = 2.0 * math.pi * rpm / 60.0
        self.tw_result.text = (
            f"[b][color={SUCCESS_HEX}]SUGGESTED TRIAL WEIGHT: {mass_g:.1f} g[/color][/b]\n"
            f"[color={TEXT_HEX}]at {radius:.0f} mm radius[/color]\n\n"
            f"[color={MUTED_HEX}]Target centrifugal force: {force_n:.0f} N "
            f"({pct:.0f}% of rotor weight)\n"
            f"Resulting unbalance: {unbal:,.0f} g\u00b7mm\n"
            f"Angular velocity: {omega:.1f} rad/s\n"
            f"Rotor static weight: {mass * GRAVITY:.0f} N[/color]\n\n"
            f"[color={TEXT_HEX}]Place it at any convenient angle, then check that it changes "
            "amplitude by at least 20-30% or phase by at least 20-30\u00b0. If it does not, "
            "increase the weight and repeat.[/color]"
        )

    # =====================================================
    # TAB 4 - WEIGHT SPLIT
    # =====================================================
    def _build_split_tab(self):
        scroll, form = scroll_form()

        form.add_widget(note_label(
            f"[color={MUTED_HEX}][size=14]When weight cannot go exactly where the calculation "
            "asks - fan blades, bolt holes, fixed pockets - this splits one correction into "
            "two weights at positions you can actually reach.[/size][/color]", height=dp(70)))

        panel = Panel(size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))

        self.sp_wt = LabeledInput("CORRECTION WEIGHT MASS", "e.g. 19.4")
        self.sp_ang = LabeledInput("CORRECTION ANGLE (deg)", "e.g. 35.8")
        panel.add_widget(self.sp_wt)
        panel.add_widget(self.sp_ang)

        # Mode selector
        panel.add_widget(section_label("AVAILABLE POSITIONS"))
        mode_row = BoxLayout(orientation="horizontal", size_hint_y=None,
                              height=dp(44), spacing=dp(8))
        self.sp_mode_two = PillButton("Two angles", accent=COLOR_PRIMARY,
                                       inactive=COLOR_PANEL_BG, text_color=(1, 1, 1, 1),
                                       inactive_text_color=COLOR_TEXT)
        self.sp_mode_even = PillButton("Equally spaced", accent=COLOR_PRIMARY,
                                        inactive=COLOR_PANEL_BG, text_color=(1, 1, 1, 1),
                                        inactive_text_color=COLOR_TEXT)
        self.sp_mode_two.bind(on_release=lambda inst: self.set_split_mode("two"))
        self.sp_mode_even.bind(on_release=lambda inst: self.set_split_mode("even"))
        mode_row.add_widget(self.sp_mode_two)
        mode_row.add_widget(self.sp_mode_even)
        panel.add_widget(mode_row)

        self.sp_angle_a = LabeledInput("POSITION A ANGLE (deg)", "e.g. 0")
        self.sp_angle_b = LabeledInput("POSITION B ANGLE (deg)", "e.g. 60")
        self.sp_count = LabeledInput("NUMBER OF POSITIONS", "e.g. 6")
        self.sp_offset = LabeledInput("FIRST POSITION OFFSET (deg)", "e.g. 0")
        self.sp_offset.input.text = "0"
        for w in (self.sp_angle_a, self.sp_angle_b, self.sp_count, self.sp_offset):
            panel.add_widget(w)

        btn = RoundedButton(text="Split the Weight", height=dp(50), accent=COLOR_PRIMARY)
        btn.bind(on_release=self.compute_split)
        panel.add_widget(btn)
        form.add_widget(panel)

        self.sp_result = result_label()
        form.add_widget(self.sp_result)
        form.add_widget(footer_label())

        self.split_mode = "two"
        self._update_split_mode_ui()
        return scroll

    def set_split_mode(self, mode):
        self.split_mode = mode
        self._update_split_mode_ui()

    def _update_split_mode_ui(self):
        two = self.split_mode == "two"
        self.sp_mode_two.set_active(two)
        self.sp_mode_even.set_active(not two)
        # Show only the fields that apply to the selected mode.
        for w, visible in ((self.sp_angle_a, two), (self.sp_angle_b, two),
                            (self.sp_count, not two), (self.sp_offset, not two)):
            w.opacity = 1 if visible else 0
            w.disabled = not visible
            w.height = dp(72) if visible else 0
            w.size_hint_y = None

    def compute_split(self, instance):
        wt = self.sp_wt.value
        ang = self.sp_ang.value
        if wt is None or ang is None:
            self.sp_result.text = (
                f"[color={ERROR_HEX}]Enter the correction weight and its angle.[/color]")
            return
        if wt <= 0:
            self.sp_result.text = (
                f"[color={ERROR_HEX}]Correction weight must be greater than zero.[/color]")
            return

        if self.split_mode == "two":
            ang_a, ang_b = self.sp_angle_a.value, self.sp_angle_b.value
            if ang_a is None or ang_b is None:
                self.sp_result.text = (
                    f"[color={ERROR_HEX}]Enter both position angles.[/color]")
                return
            extra = ""
        else:
            count, offset = self.sp_count.value, self.sp_offset.value
            if count is None or offset is None:
                self.sp_result.text = (
                    f"[color={ERROR_HEX}]Enter the number of positions and the offset.[/color]")
                return
            n = int(round(count))
            if n < 2:
                self.sp_result.text = (
                    f"[color={ERROR_HEX}]There must be at least 2 positions.[/color]")
                return
            if n > 360:
                self.sp_result.text = (
                    f"[color={ERROR_HEX}]Maximum 360 positions.[/color]")
                return
            positions = fixed_positions(n, offset)
            ang_a, ang_b = bracketing_positions(positions, ang)
            extra = (f"\n[color={MUTED_HEX}]{n} positions every "
                     f"{360.0 / n:.1f}\u00b0 from {offset:.1f}\u00b0. "
                     f"Nearest pair either side of {ang % 360:.1f}\u00b0 chosen "
                     f"automatically.[/color]")

        try:
            Wa, Wb = split_weight(wt, ang, ang_a, ang_b)
        except ValueError:
            self.sp_result.text = (
                f"[color={ERROR_HEX}]Those two positions are directly in line "
                "(0\u00b0 or 180\u00b0 apart), so the split has no unique answer. "
                "Pick two positions that are not opposite each other.[/color]")
            return

        def describe(name, w, a):
            if w >= 0:
                return (f"[b][color={SUCCESS_HEX}]{name}: {w:.2f} @ {a % 360:.1f}\u00b0"
                        f"[/color][/b]")
            return (f"[b][color={WARNING_HEX}]{name}: {abs(w):.2f} @ "
                    f"{(a + 180) % 360:.1f}\u00b0[/color][/b]"
                    f"[color={MUTED_HEX}]  (negative \u2014 opposite side)[/color]")

        # Verify the split really does reproduce the requested vector.
        check = (Wa * to_complex(1.0, ang_a)) + (Wb * to_complex(1.0, ang_b))
        chk_mag, chk_ang = to_clock_deg(check)

        self.sp_result.text = (
            f"{describe('POSITION A', Wa, ang_a)}\n"
            f"{describe('POSITION B', Wb, ang_b)}\n\n"
            f"[color={MUTED_HEX}]Requested: {wt:.2f} @ {ang % 360:.1f}\u00b0\n"
            f"Check (A + B combined): {chk_mag:.2f} @ {chk_ang:.1f}\u00b0\n"
            f"Total mass used: {abs(Wa) + abs(Wb):.2f}[/color]{extra}\n\n"
            f"[color={TEXT_HEX}]A negative result means that weight belongs on the opposite "
            "side of the rotor - or remove that much material at the stated position "
            "instead.[/color]"
        )

    # =====================================================
    # TAB 5 - TRIM BALANCE
    # =====================================================
    def _build_trim_tab(self):
        scroll, form = scroll_form()

        form.add_widget(note_label(
            f"[color={MUTED_HEX}][size=14]Once the sensitivity is known from an earlier trial "
            "run, further corrections need no new trial weight - just measure the vibration "
            "that is left and compute directly.[/size][/color]", height=dp(70)))

        panel = Panel(size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))

        self._make_convention_block(panel)

        panel.add_widget(section_label("CURRENT (RESIDUAL) VIBRATION"))
        self.tm_amp = LabeledInput("AMPLITUDE", "e.g. 1.4")
        self.tm_phase = LabeledInput("PHASE ANGLE (deg)", "e.g. 120")
        panel.add_widget(self.tm_amp)
        panel.add_widget(self.tm_phase)

        panel.add_widget(section_label("KNOWN SENSITIVITY (S)"))
        self.tm_s_mag = LabeledInput("SENSITIVITY MAGNITUDE (per unit mass)", "e.g. 0.4132")
        self.tm_s_ang = LabeledInput("SENSITIVITY ANGLE (deg)", "e.g. 189.2")
        panel.add_widget(self.tm_s_mag)
        panel.add_widget(self.tm_s_ang)

        load_btn = RoundedButton(text="Load from Single Plane tab",
                                  height=dp(46), accent=COLOR_PRIMARY_LIGHT)
        load_btn.bind(on_release=self.load_sensitivity)
        panel.add_widget(load_btn)

        btn = RoundedButton(text="Compute Trim Weight", height=dp(50), accent=COLOR_PRIMARY)
        btn.bind(on_release=self.compute_trim)
        panel.add_widget(btn)
        form.add_widget(panel)

        self.tm_result = result_label()
        form.add_widget(self.tm_result)
        form.add_widget(footer_label())
        return scroll

    def load_sensitivity(self, instance):
        if not self.last_sensitivity:
            self.tm_result.text = (
                f"[color={WARNING_HEX}]No sensitivity stored yet. Run a calculation on the "
                "Single Plane tab first, then come back.[/color]")
            return
        s_mag, s_ang = self.last_sensitivity
        self.tm_s_mag.set_value(s_mag, "{:.4f}")
        self.tm_s_ang.set_value(s_ang, "{:.1f}")
        self.tm_result.text = (
            f"[color={SUCCESS_HEX}]Loaded sensitivity {s_mag:.4f} @ {s_ang:.1f}\u00b0 "
            "from the Single Plane tab.[/color]")

    def compute_trim(self, instance, quiet=False):
        vals = [self.tm_amp.value, self.tm_phase.value,
                self.tm_s_mag.value, self.tm_s_ang.value]
        if any(v is None for v in vals):
            if not quiet:
                self.tm_result.text = (
                    f"[color={ERROR_HEX}]Please fill in every field with a number.[/color]")
            return
        amp, phase, s_mag, s_ang = vals

        if s_mag <= 0:
            self.tm_result.text = (
                f"[color={ERROR_HEX}]Sensitivity magnitude must be greater than zero.[/color]")
            return

        phase_i = convert_phase(phase, self.apply_conversion)
        O = to_complex(amp, phase_i)
        S = to_complex(s_mag, s_ang)
        Wc = -O / S
        wc_mag, wc_ang = to_clock_deg(Wc)

        self.tm_result.text = (
            f"[b][color={SUCCESS_HEX}]TRIM WEIGHT: {wc_mag:.2f} @ {wc_ang:.1f}\u00b0 "
            f"(~{clock_position(wc_ang)} o'clock)[/color][/b]\n\n"
            f"[color={MUTED_HEX}]Residual vibration in: {amp:.2f} @ {phase_i:.1f}\u00b0\n"
            f"Sensitivity used: {s_mag:.4f} @ {s_ang:.1f}\u00b0[/color]\n\n"
            f"[color={TEXT_HEX}]Add this weight on top of what is already installed, then "
            "run again. If several trims in a row stop improving things, re-check the "
            "weights actually fitted and look for looseness, misalignment or a bearing "
            "problem rather than continuing to trim.[/color]"
        )


if __name__ == "__main__":
    BalanceApp().run()
