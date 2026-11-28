# -*- coding: utf-8 -*-
"""
Laser Align - shaft alignment simulator (coupling offset/angularity + soft foot)

Self-contained tab module for the CM Toolkit merged app. Mirrors the internal
tab pattern used in cmdx_tab.py / bearing_tab.py: an App subclass whose
.build() returns a root widget with its own internal top nav + ScreenManager.
Never call .run() on this - main.py only calls .build().
"""
from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
import theme as T
from theme import ModernInput, build_pill_tab_bar, RoundedButton

# ------------------------------------------------------------------
# COLORS - mapped onto the shared design tokens (theme.py)
# ------------------------------------------------------------------
BG = T.BG
PANEL = T.CARD
BORDER = T.LINE
TEXT = T.TEXT
TEXT_2 = T.TEXT_2
MUTED = T.TEXT_3
ACCENT = T.ACCENTS["laser"]
ACCENT_HEX = T.hex_of(ACCENT)
# status text colours - always shown with the word (GOOD / ACCEPTABLE / ...)
GOOD = T.GOOD_TEXT
WARN = T.ALERT_TEXT
BAD = T.DANGER_TEXT

# General rule-of-thumb shaft alignment tolerances by RPM band.
# These are widely-cited industry guideline figures, not a specific vendor
# or standards-body table - always confirm against OEM/coupling tolerances
# for critical machinery.
TOLERANCE_BANDS = [
    # (max_rpm, good_offset_mm, good_ang_mm100, ok_offset_mm, ok_ang_mm100)
    (1000, 0.07, 0.03, 0.12, 0.05),
    (2000, 0.05, 0.02, 0.08, 0.03),
    (4000, 0.03, 0.015, 0.05, 0.02),
    (6000, 0.02, 0.01, 0.03, 0.015),
    (999999, 0.01, 0.005, 0.02, 0.01),
]

SOFT_FOOT_THRESHOLD_MM = 0.05  # ~2 mils, common rule-of-thumb soft foot limit


def band_for_rpm(rpm):
    for max_rpm, go, ga, oo, oa in TOLERANCE_BANDS:
        if rpm <= max_rpm:
            return go, ga, oo, oa
    return TOLERANCE_BANDS[-1][1:]


def classify(offset_mm, ang_mm100, rpm):
    go, ga, oo, oa = band_for_rpm(rpm)
    offset_mm, ang_mm100 = abs(offset_mm), abs(ang_mm100)
    if offset_mm <= go and ang_mm100 <= ga:
        return "GOOD", GOOD
    if offset_mm <= oo and ang_mm100 <= oa:
        return "ACCEPTABLE", WARN
    return "CORRECT BEFORE RUNNING", BAD


def _fit(label):
    label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    return label


def section_label(text, color=TEXT, size=None):
    # grows to fit when the text wraps, so a long label never runs into
    # the field or line below it
    lbl = _fit(Label(text=text, color=color, bold=True, font_size=size or T.FS_TITLE,
                      halign="left", valign="bottom", size_hint_y=None, height=dp(26)))
    lbl.bind(texture_size=lambda w, ts: setattr(w, "height", max(dp(22), ts[1] + dp(4))))
    return lbl


def caption_label(text):
    """Upper-case caption for result groups and table headers."""
    return T.section_label(text)


def body_label(text, color=TEXT, markup=False, bold=False, mono=False):
    lbl = _fit(Label(text=text, color=color, font_size=T.FS_BODY, halign="left", valign="top",
                      size_hint_y=None, markup=markup, bold=bold))
    if mono:
        lbl.font_name = T.MONO
    lbl.bind(texture_size=lambda w, ts: setattr(w, "height", ts[1] + dp(4)))
    return lbl


def field(hint, default=""):
    return ModernInput(hint_text=hint, text=default, multiline=False,
                        accent=ACCENT, mono=True)


def labeled_field(label_text, hint, default=""):
    box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    box.bind(minimum_height=box.setter("height"))
    box.add_widget(section_label(label_text, TEXT_2, T.FS_BODY))
    ti = field(hint, default)
    box.add_widget(ti)
    return box, ti


def panel(title):
    """A rounded card container with a title."""
    outer = T.Card(padding=[T.S4, T.S3, T.S4, T.S4], spacing=T.S2)
    outer.add_widget(section_label(title))
    return outer


def safe_float(text, default=0.0):
    try:
        return float(text.strip())
    except Exception:
        return default


# ------------------------------------------------------------------
# CALCULATOR SCREEN - coupling offset/angularity -> foot corrections
# ------------------------------------------------------------------
class CalcScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="calc", **kwargs)
        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=T.S3, padding=[T.S4, T.S3, T.S4, T.S4], size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(body_label(
            "Enter the offset and angularity your laser unit reports at the coupling, "
            "plus the movable machine's foot distances (MF1 = near foot, MF2 = far foot, "
            "same naming Easy-Laser uses). Corrections are extrapolated out to each foot.", MUTED))

        setup = panel("Machine setup")
        grid = GridLayout(cols=2, spacing=[T.S3, T.S2], size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        b1, self.rpm_in = labeled_field("RPM", "e.g. 1485", "1485")
        b2, self.s2s_in = labeled_field("Sensor to sensor (mm)", "e.g. 200", "200")
        b3, self.sensor_in = labeled_field("Sensor to coupling (mm)", "e.g. 100", "100")
        b4, self.cf_in = labeled_field("Sensor to MF1 (mm)", "e.g. 150", "150")
        b5, self.ff_in = labeled_field("MF1 to MF2 (mm)", "e.g. 300", "300")
        grid.add_widget(b1); grid.add_widget(b2); grid.add_widget(b3); grid.add_widget(b4); grid.add_widget(b5)
        setup.add_widget(grid)
        col.add_widget(setup)
        col.add_widget(body_label(
            "Field names match Easy-Laser's own setup screen. \"Sensor to sensor\" is shown "
            "for reference/record-keeping but isn't used in the correction math below - only "
            "\"Sensor to coupling\" and \"Sensor to nearest foot\" feed the calculation "
            "(validated against real Easy-Laser results to within ~0.02mm across several jobs).",
            MUTED))

        vert = panel("Vertical plane (side view)")
        vert.add_widget(body_label("Offset sign: + = remove shim, - = add shim", MUTED))
        vgrid = GridLayout(cols=2, spacing=[T.S3, T.S2], size_hint_y=None)
        vgrid.bind(minimum_height=vgrid.setter("height"))
        bv1, self.v_off_in = labeled_field("Offset at coupling (mm)", "e.g. 0.08")
        bv2, self.v_ang_in = labeled_field("Angularity (mm/100 mm)", "e.g. 0.02")
        vgrid.add_widget(bv1); vgrid.add_widget(bv2)
        vert.add_widget(vgrid)
        col.add_widget(vert)

        horiz = panel("Horizontal plane (top view)")
        horiz.add_widget(body_label("Offset sign: + = move left, - = move right", MUTED))
        hgrid = GridLayout(cols=2, spacing=[T.S3, T.S2], size_hint_y=None)
        hgrid.bind(minimum_height=hgrid.setter("height"))
        bh1, self.h_off_in = labeled_field("Offset at coupling (mm)", "e.g. 0.10")
        bh2, self.h_ang_in = labeled_field("Angularity (mm/100 mm)", "e.g. 0.04")
        hgrid.add_widget(bh1); hgrid.add_widget(bh2)
        horiz.add_widget(hgrid)
        col.add_widget(horiz)

        calc_btn = RoundedButton(text="Calculate", accent=ACCENT)
        calc_btn.bind(on_release=self.calculate)
        col.add_widget(calc_btn)

        self.result_panel = panel("Results")
        self.result_body = BoxLayout(orientation="vertical", spacing=T.S1, size_hint_y=None)
        self.result_body.bind(minimum_height=self.result_body.setter("height"))
        self.result_panel.add_widget(self.result_body)
        col.add_widget(self.result_panel)

        root.add_widget(col)
        self.add_widget(root)
        self._show_placeholder()

    def _show_placeholder(self):
        self.result_body.clear_widgets()
        self.result_body.add_widget(body_label("Enter values above and tap Calculate.", MUTED))

    def calculate(self, *a):
        rpm = safe_float(self.rpm_in.text, 1500)
        sensor = safe_float(self.sensor_in.text, 0)
        cf = safe_float(self.cf_in.text, 0)
        ff = safe_float(self.ff_in.text, 0)
        h_off = safe_float(self.h_off_in.text, 0)
        h_ang = safe_float(self.h_ang_in.text, 0)
        v_off = safe_float(self.v_off_in.text, 0)
        v_ang = safe_float(self.v_ang_in.text, 0)

        d1 = sensor + cf          # sensor rig to MF1
        d2 = sensor + cf + ff     # sensor rig to MF2

        h_ff = h_off + h_ang * (d1 / 100.0)
        h_bf = h_off + h_ang * (d2 / 100.0)
        v_ff = v_off + v_ang * (d1 / 100.0)
        v_bf = v_off + v_ang * (d2 / 100.0)

        def dir_h(val):
            return "Move Left" if val >= 0 else "Move Right"

        def dir_v(val):
            return "Remove shim" if val >= 0 else "Add shim"

        def move(foot, direction, val):
            return body_label("%s: %s [color=%s][b]%.2f mm[/b][/color]" % (
                foot, direction, ACCENT_HEX, abs(val)), TEXT, markup=True)

        def status(text, color):
            return body_label("[b]%s[/b]" % text, color, markup=True)

        h_label, h_color = classify(h_off, h_ang, rpm)
        v_label, v_color = classify(v_off, v_ang, rpm)

        self.result_body.clear_widgets()
        self.result_body.add_widget(caption_label("Vertical (shims)"))
        self.result_body.add_widget(move("MF1 (near foot)", dir_v(v_ff), v_ff))
        self.result_body.add_widget(move("MF2 (far foot)", dir_v(v_bf), v_bf))
        self.result_body.add_widget(status("Vertical condition: %s" % v_label, v_color))
        self.result_body.add_widget(caption_label("Horizontal (sideways)"))
        self.result_body.add_widget(move("MF1 (near foot)", dir_h(h_ff), h_ff))
        self.result_body.add_widget(move("MF2 (far foot)", dir_h(h_bf), h_bf))
        self.result_body.add_widget(status("Horizontal condition: %s" % h_label, h_color))
        self.result_body.add_widget(body_label(
            "Guideline only - verify against coupling/OEM tolerance for critical machines. "
            "Correct vertical (shims) first, then horizontal. Shim direction and the sensor-"
            "to-coupling distance were reverse-engineered from real Easy-Laser screenshots, "
            "not an official spec - double-check against your own readings.", MUTED))


# ------------------------------------------------------------------
# SOFT FOOT SCREEN
# ------------------------------------------------------------------
class SoftFootScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="softfoot", **kwargs)
        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=T.S3, padding=[T.S4, T.S3, T.S4, T.S4], size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(body_label(
            "Loosen each hold-down bolt one at a time and record the rise/gap at that "
            "foot (dial indicator or laser). A rise above %.2f mm suggests soft foot at "
            "that corner." % SOFT_FOOT_THRESHOLD_MM, MUTED))

        p = panel("Foot readings (mm)")
        grid = GridLayout(cols=2, spacing=[T.S3, T.S2], size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        self.foot_inputs = {}
        for name in ("Front-Left", "Front-Right", "Back-Left", "Back-Right"):
            b, ti = labeled_field(name, "e.g. 0.03")
            self.foot_inputs[name] = ti
            grid.add_widget(b)
        p.add_widget(grid)
        col.add_widget(p)

        check_btn = RoundedButton(text="Check", accent=ACCENT)
        check_btn.bind(on_release=self.check)
        col.add_widget(check_btn)

        self.result_panel = panel("Results")
        self.result_body = BoxLayout(orientation="vertical", spacing=T.S1, size_hint_y=None)
        self.result_body.bind(minimum_height=self.result_body.setter("height"))
        self.result_panel.add_widget(self.result_body)
        col.add_widget(self.result_panel)

        root.add_widget(col)
        self.add_widget(root)
        self.result_body.add_widget(body_label("Enter readings above and tap Check.", MUTED))

    def check(self, *a):
        self.result_body.clear_widgets()
        any_soft = False
        for name, ti in self.foot_inputs.items():
            val = abs(safe_float(ti.text, 0))
            if val > SOFT_FOOT_THRESHOLD_MM:
                any_soft = True
                shim = val            # shim the full measured gap (parallel soft foot)
                self.result_body.add_widget(body_label(
                    "%s: %.2f mm - [b]SOFT FOOT[/b] (shim ~%.2f mm)" % (name, val, shim), BAD, markup=True))
            else:
                self.result_body.add_widget(body_label("%s: %.2f mm - [b]OK[/b]" % (name, val), GOOD, markup=True))
        if not any_soft:
            self.result_body.add_widget(body_label("[b]No soft foot detected at any corner.[/b]", GOOD, markup=True))
        else:
            self.result_body.add_widget(body_label(
                "Correct soft foot before proceeding with coupling alignment - it will "
                "throw off offset/angularity readings otherwise. The shim shown is the full gap, "
                "right for a parallel soft foot; if the gap differs across the foot (angled or "
                "bent foot), inspect and step-shim rather than adding one shim.", MUTED))


# ------------------------------------------------------------------
# GUIDE SCREEN - tolerance reference
# ------------------------------------------------------------------
class GuideScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="guide", **kwargs)
        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=T.S2, padding=[T.S4, T.S3, T.S4, T.S4], size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(section_label("General alignment tolerance guideline"))
        col.add_widget(body_label(
            "Widely-cited rule-of-thumb figures by shaft speed. Always prefer OEM or "
            "coupling manufacturer tolerances for critical or high-speed machines.", MUTED))

        table = T.Card(padding=[T.S2, T.S2], spacing=0)
        header = GridLayout(cols=5, size_hint_y=None, height=dp(44), spacing=dp(4))
        for h in ("RPM up to", "Good\noffset", "Good\nang/100mm", "OK\noffset", "OK\nang/100mm"):
            header.add_widget(_fit(Label(text=h, bold=True, font_size=T.FS_CAPTION, color=MUTED,
                                          halign="center", valign="middle")))
        table.add_widget(header)

        for i, (max_rpm, go, ga, oo, oa) in enumerate(TOLERANCE_BANDS):
            row = GridLayout(cols=5, size_hint_y=None, height=dp(36), spacing=dp(4))
            with row.canvas.before:
                Color(*BORDER)
                ln = Line(width=1)
            row.bind(pos=lambda w, v, ln=ln: setattr(ln, "points", [w.x, w.top, w.right, w.top]),
                     size=lambda w, v, ln=ln: setattr(ln, "points", [w.x, w.top, w.right, w.top]))
            rpm_txt = "%d" % max_rpm if max_rpm < 999999 else "6000+"
            for j, val in enumerate((rpm_txt, "%.3f" % go, "%.3f" % ga, "%.3f" % oo, "%.3f" % oa)):
                row.add_widget(_fit(Label(text=val, font_size=T.FS_CAPTION, font_name=T.MONO,
                                           color=TEXT if j else TEXT_2, bold=(j == 0),
                                           halign="center", valign="middle")))
            table.add_widget(row)
        col.add_widget(table)

        col.add_widget(section_label("Offset vs. angularity"))
        col.add_widget(body_label(
            "Offset (parallel) misalignment: shaft centerlines are parallel but not "
            "coincident. Angularity misalignment: shaft centerlines meet at an angle "
            "rather than running parallel. Most real-world misalignment is a mix of both, "
            "which is why the coupling reading alone isn't enough - it has to be "
            "extrapolated out to MF1 (near foot) and MF2 (far foot) on the Calculator tab, "
            "same naming convention Easy-Laser uses. Vertical results are given as Add/Remove "
            "shim; horizontal results are given as Move Left/Right. Correct vertical first, "
            "then horizontal - shimming can shift the horizontal reading slightly."))

        col.add_widget(section_label("Soft foot"))
        col.add_widget(body_label(
            "Soft foot is a mechanical condition where one or more feet don't sit flush "
            "on the baseplate, so tightening that bolt distorts the machine frame and "
            "throws off alignment readings. Always resolve soft foot before trusting "
            "coupling offset/angularity numbers."))

        root.add_widget(col)
        self.add_widget(root)


# ------------------------------------------------------------------
# ROOT WIDGET / APP
# ------------------------------------------------------------------
class RootWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(CalcScreen())
        self.sm.add_widget(SoftFootScreen())
        self.sm.add_widget(GuideScreen())

        nav, self.nav_buttons = build_pill_tab_bar(
            [("calc", "Calculator", ACCENT), ("softfoot", "Soft Foot", ACCENT), ("guide", "Guide", ACCENT)],
            on_switch=lambda n: self.switch(n))

        self.add_widget(nav)
        self.add_widget(self.sm)

        footer = Label(text="Built by Gnaneswar", color=MUTED, font_size=T.FS_CAPTION,
                        size_hint_y=None, height=dp(26))
        self.add_widget(footer)

        self.switch("calc")

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    _bar = None
    SUBTITLES = {"calc": "Coupling offset & angularity to foot corrections",
                 "softfoot": "Soft foot check, corner by corner",
                 "guide": "Tolerance guideline & reference"}

    def bind_bar(self, set_bar):
        self._bar = set_bar
        set_bar(None, self.SUBTITLES.get(self.sm.current, ""))

    def switch(self, name):
        self.sm.current = name
        for n, btn in self.nav_buttons.items():
            btn.set_active(n == name)
        if self._bar:
            self._bar(None, self.SUBTITLES.get(name, ""))

    def handle_back(self):
        """Called by main.py on the Android hardware back button. Return
        True if handled internally, False to let main.py return to Home."""
        if self.sm.current != "calc":
            self.switch("calc")
            return True
        return False


class LaserAlignApp(App):
    title = "Laser Align"

    def build(self):
        return RootWidget()


if __name__ == "__main__":
    LaserAlignApp().run()
