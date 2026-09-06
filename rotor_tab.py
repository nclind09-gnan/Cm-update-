"""
Rotor Balance Calculator - Android app (Kivy)
Single-plane, influence-coefficient (vector) method, with a 360-degree
polar vector diagram and an animated rotor view.

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

# NOTE: Window.clearcolor is set by the merged app's tab switcher (see main.py),
# not here, since multiple tabs share one Window in the merged build.

# ---------- balancing math ----------
def to_complex(mag, theta_clock_deg):
    phi = -math.radians(theta_clock_deg)
    return cmath.rect(mag, phi)


def to_clock_deg(z):
    mag, phi = cmath.polar(z)
    theta = (-math.degrees(phi)) % 360
    return mag, theta


def clock_position(theta_deg):
    hour = round(theta_deg / 30) % 12
    return 12 if hour == 0 else hour


def convert_phase(angle_deg, is_lag):
    """Mirrors a phase reading between lag and lead convention.
    Applying it twice returns the original angle (it's its own inverse),
    so the same function converts either direction."""
    return (360 - angle_deg) % 360 if is_lag else angle_deg


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
        subtitle = Label(
            text="Single plane \u00b7 influence coefficient method",
            color=(0.85, 0.9, 1, 1),
            font_size=dp(14),
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="middle",
        )
        subtitle.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self.add_widget(title)
        self.add_widget(subtitle)

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
    NOT drawn on the chart itself (that caused clutter) - they go in
    a separate legend below, set via the app's chart_legend label."""

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
        self.clear_widgets()
        if self.width < 20 or self.height < 20:
            return

        cx, cy = self.center_x, self.center_y
        R = min(self.width, self.height) / 2 - dp(30)
        if R <= 0:
            return

        # Scale is based ONLY on the vibration vectors (Original, Trial-run).
        # Correction weight is a different physical quantity (mass, not
        # vibration amplitude) so it is never scaled into this radius -
        # it's drawn as a fixed-radius angle marker instead.
        mags = [1e-9]
        if self.original:
            mags.append(self.original["mag"])
        if self.trial_run:
            mags.append(self.trial_run["mag"])
        scale = R / max(mags)  # auto-zoom to fit the vibration vectors

        with self.canvas:
            # grid rings
            Color(0.85, 0.88, 0.93, 1)
            for f in (0.25, 0.5, 0.75, 1.0):
                Line(circle=(cx, cy, R * f), width=1)
            # tick lines every 30 degrees
            Color(0.9, 0.92, 0.96, 1)
            for t in range(0, 360, 30):
                rad = math.radians(t)
                x2 = cx + R * math.sin(rad)
                y2 = cy + R * math.cos(rad)
                Line(points=[cx, cy, x2, y2], width=1)

            if self.original and self.trial_run:
                ox, oy = self._point(cx, cy, scale, self.original)
                tx, ty = self._point(cx, cy, scale, self.trial_run)

                self._draw_arrow(cx, cy, ox, oy, self.original["color"])
                self._draw_arrow(cx, cy, tx, ty, self.trial_run["color"])
                self._draw_arrow(ox, oy, tx, ty, EFFECT_COLOR)

            if self.correction_angle is not None:
                r, g, b = self.correction_color
                Color(r, g, b, 1)
                rad = math.radians(self.correction_angle)
                mx = cx + R * math.sin(rad)
                my = cy + R * math.cos(rad)
                Ellipse(pos=(mx - dp(8), my - dp(8)), size=(dp(16), dp(16)))

            # center point
            Color(*COLOR_TEXT)
            Ellipse(pos=(cx - dp(3), cy - dp(3)), size=(dp(6), dp(6)))

        # angle labels at the cardinal points only - kept simple and spaced out
        for t in (0, 90, 180, 270):
            rad = math.radians(t)
            lx = cx + (R + dp(20)) * math.sin(rad)
            ly = cy + (R + dp(20)) * math.cos(rad)
            lbl = Label(
                text=f"{t}\u00b0",
                font_size=dp(12),
                color=COLOR_TEXT_MUTED,
                size_hint=(None, None),
                size=(dp(40), dp(20)),
            )
            lbl.pos = (lx - dp(20), ly - dp(10))
            self.add_widget(lbl)

    @staticmethod
    def _point(cx, cy, scale, v):
        rad = math.radians(v["angle"])
        mag = v["mag"] * scale
        return cx + mag * math.sin(rad), cy + mag * math.cos(rad)

    @staticmethod
    def _draw_arrow(x1, y1, x2, y2, color):
        r, g, b = color
        Color(r, g, b, 1)
        Line(points=[x1, y1, x2, y2], width=2.6)

        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return
        d_x, d_y = dx / length, dy / length
        p_x, p_y = d_y, -d_x

        ah_len = dp(11)
        ah_half = dp(5.5)
        back_x = x2 - ah_len * d_x
        back_y = y2 - ah_len * d_y
        left_x = back_x + ah_half * p_x
        left_y = back_y + ah_half * p_y
        right_x = back_x - ah_half * p_x
        right_y = back_y - ah_half * p_y
        Triangle(points=[x2, y2, left_x, left_y, right_x, right_y])


# ---------- rotor view with animated correction marker ----------
class RotorView(Widget):
    """Draws a circular rotor disc with a reference mark at the top,
    a trial-weight marker, and an animated correction-weight marker."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trial_angle = None
        self.correction_angle = None
        self._anim_angle = 0
        self._cx = 0
        self._cy = 0
        self._R = 0

        self.trial_label = Label(
            text="Trial",
            font_size=dp(10),
            color=COLOR_TEXT_MUTED,
            size_hint=(None, None),
            size=(dp(70), dp(30)),
            text_size=(dp(70), dp(30)),
            halign="center",
            valign="top",
            opacity=0,
            bold=True,
        )
        self.correction_label = Label(
            text="Correction",
            font_size=dp(10),
            color=COLOR_SUCCESS,
            size_hint=(None, None),
            size=(dp(90), dp(30)),
            text_size=(dp(90), dp(30)),
            halign="center",
            valign="top",
            opacity=0,
            bold=True,
        )
        self.add_widget(self.trial_label)
        self.add_widget(self.correction_label)
        self.bind(pos=self._rebuild, size=self._rebuild)

    def set_weights(self, trial_angle, correction_angle):
        self.trial_angle = trial_angle
        self.correction_angle = correction_angle
        self.trial_label.text = f"Trial\n{trial_angle:.1f}\u00b0"
        self.correction_label.text = f"Correction\n{correction_angle:.1f}\u00b0"
        self._anim_angle = 0
        self._update_markers()
        Animation.cancel_all(self, "_anim_angle")
        anim = Animation(_anim_angle=correction_angle, duration=1.0, t="out_cubic")
        anim.bind(on_progress=lambda *a: self._update_markers())
        anim.start(self)

    def _rebuild(self, *args):
        self.canvas.before.clear()
        if self.width < 20 or self.height < 20:
            return
        cx, cy = self.center_x, self.center_y
        R = min(self.width, self.height) / 2 - dp(34)
        if R <= 0:
            return
        self._cx, self._cy, self._R = cx, cy, R

        with self.canvas.before:
            # rotor disc
            Color(0.9, 0.93, 0.98, 1)
            Ellipse(pos=(cx - R, cy - R), size=(R * 2, R * 2))
            Color(*COLOR_PRIMARY)
            Line(circle=(cx, cy, R), width=2)
            Line(circle=(cx, cy, R * 0.15), width=1.4)
            # reference mark, 0 degrees at the top
            Color(*COLOR_WARNING)
            Ellipse(pos=(cx - dp(5), cy + R - dp(5)), size=(dp(10), dp(10)))

        self._update_markers()

    def _update_markers(self, *args):
        if self._R <= 0:
            return
        cx, cy, R = self._cx, self._cy, self._R
        self.canvas.after.clear()

        with self.canvas.after:
            if self.trial_angle is not None:
                Color(*COLOR_TEXT_MUTED)
                rad = math.radians(self.trial_angle)
                tx = cx + R * math.sin(rad)
                ty = cy + R * math.cos(rad)
                Ellipse(pos=(tx - dp(7), ty - dp(7)), size=(dp(14), dp(14)))
                self.trial_label.pos = (tx - dp(35), ty + dp(10))
                self.trial_label.opacity = 1

            if self.correction_angle is not None:
                Color(*COLOR_SUCCESS)
                rad = math.radians(self._anim_angle)
                mx = cx + R * math.sin(rad)
                my = cy + R * math.cos(rad)
                Ellipse(pos=(mx - dp(8), my - dp(8)), size=(dp(16), dp(16)))
                self.correction_label.pos = (mx - dp(45), my + dp(12))
                self.correction_label.opacity = 1


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


class BalanceApp(App):
    def build(self):
        self.title = "Rotor Balance"
        root = BoxLayout(orientation="vertical")
        root.add_widget(HeaderBar())

        scroll = ScrollView()
        form = GridLayout(
            cols=1, spacing=dp(14), size_hint_y=None, padding=(dp(14), dp(14), dp(14), dp(24))
        )
        form.bind(minimum_height=form.setter("height"))

        note = Label(
            text=(
                f"[color={MUTED_HEX}][size=14]Angles measured clockwise from the "
                "phase reference mark, as viewed from the sensor end.[/size][/color]"
            ),
            markup=True,
            size_hint_y=None,
            height=dp(46),
            halign="left",
            valign="top",
        )
        note.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        form.add_widget(note)

        input_panel = Panel(size_hint_y=None)
        input_panel.bind(minimum_height=input_panel.setter("height"))

        self.apply_conversion = False  # default: Phase Lag selected, angles used as-entered

        convention_label = Label(
            text="PHASE CONVENTION",
            size_hint_y=None,
            height=dp(24),
            font_size=dp(14),
            color=COLOR_TEXT_MUTED,
            halign="left",
            bold=True,
        )
        convention_label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        input_panel.add_widget(convention_label)

        convention_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8)
        )
        self.lag_btn = PillButton("Phase Lag", accent=COLOR_PRIMARY, inactive=COLOR_PANEL_BG,
                                   text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        self.lead_btn = PillButton("Phase Lead", accent=COLOR_PRIMARY, inactive=COLOR_PANEL_BG,
                                    text_color=(1, 1, 1, 1), inactive_text_color=COLOR_TEXT)
        self.lag_btn.bind(on_release=lambda inst: self.set_convention(False))
        self.lead_btn.bind(on_release=lambda inst: self.set_convention(True))
        convention_row.add_widget(self.lag_btn)
        convention_row.add_widget(self.lead_btn)
        input_panel.add_widget(convention_row)

        convention_hint = Label(
            text=(
                f"[color={MUTED_HEX}][size=14]"
                "[b]Lag[/b]: vibration peak trails behind the reference mark, opposite "
                "the direction of shaft rotation - most instruments' default.\n"
                "[b]Lead[/b]: peak appears ahead of the reference mark, in the same "
                "direction as shaft rotation.[/size][/color]"
            ),
            markup=True,
            size_hint_y=None,
            height=dp(70),
            halign="left",
            valign="top",
        )
        convention_hint.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        input_panel.add_widget(convention_hint)

        self._update_convention_buttons()

        self.o_amp = LabeledInput("ORIGINAL VIBRATION AMPLITUDE", "e.g. 4.2")
        self.o_phase = LabeledInput("ORIGINAL PHASE ANGLE (deg)", "e.g. 48")
        self.t_wt = LabeledInput("TRIAL WEIGHT MASS", "e.g. 5.0")
        self.t_angle = LabeledInput("TRIAL WEIGHT PLACEMENT ANGLE (deg)", "e.g. 90")
        self.tr_amp = LabeledInput("VIBRATION AMPLITUDE WITH TRIAL WEIGHT", "e.g. 2.1")
        self.tr_phase = LabeledInput("PHASE ANGLE WITH TRIAL WEIGHT (deg)", "e.g. 310")

        for w in (self.o_amp, self.o_phase, self.t_wt, self.t_angle, self.tr_amp, self.tr_phase):
            input_panel.add_widget(w)

        self.compute_btn = RoundedButton(
            text="Compute Correction Weight",
            height=dp(50),
            accent=COLOR_PRIMARY,
        )
        self.compute_btn.bind(on_release=self.compute)
        input_panel.add_widget(self.compute_btn)

        form.add_widget(input_panel)

        self.result_label = Label(
            text="",
            markup=True,
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=dp(16),
            color=COLOR_TEXT,
        )
        self.result_label.bind(
            texture_size=lambda inst, val: setattr(inst, "height", val[1] + dp(10))
        )
        self.result_label.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        form.add_widget(self.result_label)

        chart_panel = Panel(size_hint_y=None)
        chart_panel.bind(minimum_height=chart_panel.setter("height"))
        chart_title = Label(
            text=f"[b][color={TEXT_HEX}]Vector Diagram[/color][/b]",
            markup=True,
            size_hint_y=None,
            height=dp(24),
            halign="left",
        )
        chart_title.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        chart_panel.add_widget(chart_title)

        chart_note = Label(
            text=f"[color={MUTED_HEX}][size=13]Angles below are shown after phase-convention conversion.[/size][/color]",
            markup=True,
            size_hint_y=None,
            height=dp(22),
            halign="left",
        )
        chart_note.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        chart_panel.add_widget(chart_note)

        self.polar_chart = PolarChart(size_hint_y=None, height=dp(280))
        chart_panel.add_widget(self.polar_chart)

        self.chart_legend = Label(
            text="",
            markup=True,
            size_hint_y=None,
            font_size=dp(15),
            halign="left",
            valign="top",
            color=COLOR_TEXT,
        )
        self.chart_legend.bind(
            texture_size=lambda inst, val: setattr(inst, "height", val[1] + dp(6))
        )
        self.chart_legend.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        chart_panel.add_widget(self.chart_legend)

        form.add_widget(chart_panel)

        rotor_panel = Panel(size_hint_y=None, height=dp(340))
        rotor_title = Label(
            text=f"[b][color={TEXT_HEX}]Rotor View[/color][/b]",
            markup=True,
            size_hint_y=None,
            height=dp(24),
            halign="left",
        )
        rotor_title.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        rotor_panel.add_widget(rotor_title)
        self.rotor_view = RotorView()
        rotor_panel.add_widget(self.rotor_view)
        form.add_widget(rotor_panel)

        footer = Label(
            text=f"[color={MUTED_HEX}]Created by Gnaneswar[/color]",
            markup=True,
            size_hint_y=None,
            height=dp(40),
            halign="center",
            valign="middle",
            font_size=dp(13),
        )
        footer.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        form.add_widget(footer)

        scroll.add_widget(form)
        root.add_widget(scroll)
        return root

    def set_convention(self, apply_conversion):
        self.apply_conversion = apply_conversion
        self._update_convention_buttons()
        self.compute(None)

    def _update_convention_buttons(self):
        self.lead_btn.set_active(self.apply_conversion)
        self.lag_btn.set_active(not self.apply_conversion)

    def compute(self, instance):
        vals = [
            self.o_amp.value,
            self.o_phase.value,
            self.t_wt.value,
            self.t_angle.value,
            self.tr_amp.value,
            self.tr_phase.value,
        ]
        if any(v is None for v in vals):
            self.result_label.text = f"[color={ERROR_HEX}]Please fill in every field with a number.[/color]"
            return
        o_amp, o_phase, t_wt, t_angle, tr_amp, tr_phase = vals

        if t_wt <= 0:
            self.result_label.text = f"[color={ERROR_HEX}]Trial weight must be greater than zero.[/color]"
            return

        o_phase_i = convert_phase(o_phase, self.apply_conversion)
        tr_phase_i = convert_phase(tr_phase, self.apply_conversion)

        O = to_complex(o_amp, o_phase_i)
        OT = to_complex(tr_amp, tr_phase_i)
        T = to_complex(t_wt, t_angle)
        E = OT - O

        if abs(E) < 1e-6:
            self.result_label.text = (
                f"[color={WARNING_HEX}]The trial weight barely changed the vibration reading. "
                "Try a heavier trial weight or a different placement angle.[/color]"
            )
            return

        S = E / T
        Wc = -O / S
        residual = O + S * Wc

        e_mag, e_ang = to_clock_deg(E)
        s_mag, s_ang = to_clock_deg(S)
        wc_mag, wc_ang = to_clock_deg(Wc)
        res_mag, _ = to_clock_deg(residual)

        self.result_label.text = (
            f"[b][color={SUCCESS_HEX}]CORRECTION WEIGHT: {wc_mag:.2f} @ {wc_ang:.1f}\u00b0 "
            f"(~{clock_position(wc_ang)} o'clock)[/color][/b]\n\n"
            f"[color={MUTED_HEX}]Effect vector (E): {e_mag:.3f} @ {e_ang:.1f}\u00b0\n"
            f"Sensitivity (S = E/T): {s_mag:.3f} @ {s_ang:.1f}\u00b0\n"
            f"Predicted residual vibration: {res_mag:.3f}[/color]\n\n"
            f"[color={TEXT_HEX}]Remove the trial weight, then install the correction weight\n"
            "at the stated angle (clockwise from the reference mark).[/color]"
        )

        self.polar_chart.set_data(
            original={"mag": o_amp, "angle": o_phase_i, "color": ORIGINAL_COLOR},
            trial_run={"mag": tr_amp, "angle": tr_phase_i, "color": RESULTANT_COLOR},
            correction_angle=wc_ang,
            correction_color=COLOR_SUCCESS[:3],
        )
        self.chart_legend.text = "\n\n".join(
            [
                f"[color={ORIGINAL_HEX}]\u25CF  Original: {o_amp:.2f} @ {o_phase_i:.1f}\u00b0[/color]",
                f"[color={RESULTANT_HEX}]\u25CF  Trial run (O+T): {tr_amp:.2f} @ {tr_phase_i:.1f}\u00b0[/color]",
                f"[color={EFFECT_HEX}]\u25CF  Effect of trial weight: {e_mag:.2f} @ {e_ang:.1f}\u00b0[/color]",
                f"[color={SUCCESS_HEX}]\u25CF  Correction weight: {wc_mag:.2f} @ {wc_ang:.1f}\u00b0[/color]",
            ]
        )
        self.rotor_view.set_weights(trial_angle=t_angle, correction_angle=wc_ang)


if __name__ == "__main__":
    BalanceApp().run()
