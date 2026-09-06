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
from kivy.graphics import Color, Rectangle, RoundedRectangle
from theme import ModernInput, build_pill_tab_bar, RoundedButton

# ------------------------------------------------------------------
# COLORS (teal-accented dark theme, consistent with the CM Toolkit palette)
# ------------------------------------------------------------------
BG = (0.043, 0.055, 0.078, 1)
PANEL = (0.11, 0.13, 0.18, 1)
TEXT = (0.92, 0.94, 0.97, 1)
MUTED = (0.55, 0.60, 0.68, 1)
ACCENT = (0.09, 0.68, 0.62, 1)
GOOD = (0.16, 0.72, 0.38, 1)
WARN = (0.95, 0.68, 0.15, 1)
BAD = (0.86, 0.22, 0.22, 1)

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


def section_label(text, color=ACCENT):
    return _fit(Label(text=text, color=color, bold=True, font_size=sp(15),
                       halign="left", valign="bottom", size_hint_y=None, height=dp(26)))


def body_label(text, color=TEXT):
    lbl = _fit(Label(text=text, color=color, font_size=sp(13.5), halign="left", valign="top",
                      size_hint_y=None))
    lbl.bind(texture_size=lambda w, ts: setattr(w, "height", ts[1] + dp(4)))
    return lbl


def field(hint, default=""):
    return ModernInput(hint_text=hint, text=default, multiline=False, height=dp(44),
                        accent=ACCENT)


def labeled_field(label_text, hint, default=""):
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(68), spacing=dp(2))
    box.add_widget(section_label(label_text, MUTED))
    ti = field(hint, default)
    box.add_widget(ti)
    return box, ti


def panel(title):
    """A rounded panel container with a title bar."""
    outer = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8),
                       padding=[dp(12), dp(10)])
    outer.bind(minimum_height=outer.setter("height"))
    with outer.canvas.before:
        Color(*PANEL)
        rect = RoundedRectangle(radius=[dp(14)])
    outer.bind(pos=lambda w, v: setattr(rect, "pos", v), size=lambda w, v: setattr(rect, "size", v))
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
        col = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(12), size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(body_label(
            "Enter the offset and angularity your laser unit reports at the coupling, "
            "plus the movable machine's foot distances (MF1 = near foot, MF2 = far foot, "
            "same naming Easy-Laser uses). Corrections are extrapolated out to each foot.", MUTED))

        setup = panel("Machine setup")
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        b1, self.rpm_in = labeled_field("RPM", "e.g. 1485", "1485")
        b2, self.s2s_in = labeled_field("Sensor to sensor (mm)", "e.g. 200", "200")
        b3, self.sensor_in = labeled_field("Sensor to coupling (mm)", "e.g. 100", "100")
        b4, self.cf_in = labeled_field("Sensor to nearest foot - MF1 (mm)", "e.g. 150", "150")
        b5, self.ff_in = labeled_field("MF1 to MF2 - foot spacing (mm)", "e.g. 300", "300")
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
        vgrid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        vgrid.bind(minimum_height=vgrid.setter("height"))
        bv1, self.v_off_in = labeled_field("Offset at coupling (mm)\n+ = Remove shim, - = Add shim", "e.g. 0.08")
        bv2, self.v_ang_in = labeled_field("Angularity (mm / 100mm)", "e.g. 0.02")
        vgrid.add_widget(bv1); vgrid.add_widget(bv2)
        vert.add_widget(vgrid)
        col.add_widget(vert)

        horiz = panel("Horizontal plane (top view)")
        hgrid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        hgrid.bind(minimum_height=hgrid.setter("height"))
        bh1, self.h_off_in = labeled_field("Offset at coupling (mm)\n+ = move Left, - = move Right", "e.g. 0.10")
        bh2, self.h_ang_in = labeled_field("Angularity (mm / 100mm)", "e.g. 0.04")
        hgrid.add_widget(bh1); hgrid.add_widget(bh2)
        horiz.add_widget(hgrid)
        col.add_widget(horiz)

        calc_btn = RoundedButton(text="Calculate", accent=ACCENT)
        calc_btn.bind(on_release=self.calculate)
        col.add_widget(calc_btn)

        self.result_panel = panel("Results")
        self.result_body = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
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

        h_label, h_color = classify(h_off, h_ang, rpm)
        v_label, v_color = classify(v_off, v_ang, rpm)

        self.result_body.clear_widgets()
        self.result_body.add_widget(section_label("Vertical (shims)", ACCENT))
        self.result_body.add_widget(body_label(
            "MF1 (near foot): %s %.2f mm" % (dir_v(v_ff), abs(v_ff))))
        self.result_body.add_widget(body_label(
            "MF2 (far foot): %s %.2f mm" % (dir_v(v_bf), abs(v_bf))))
        self.result_body.add_widget(body_label("Vertical condition: %s" % v_label, v_color))
        self.result_body.add_widget(section_label("Horizontal (sideways)", ACCENT))
        self.result_body.add_widget(body_label(
            "MF1 (near foot): %s %.2f mm" % (dir_h(h_ff), abs(h_ff))))
        self.result_body.add_widget(body_label(
            "MF2 (far foot): %s %.2f mm" % (dir_h(h_bf), abs(h_bf))))
        self.result_body.add_widget(body_label("Horizontal condition: %s" % h_label, h_color))
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
        col = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(12), size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(body_label(
            "Loosen each hold-down bolt one at a time and record the rise/gap at that "
            "foot (dial indicator or laser). A rise above %.2f mm suggests soft foot at "
            "that corner." % SOFT_FOOT_THRESHOLD_MM, MUTED))

        p = panel("Foot readings (mm)")
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
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
        self.result_body = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
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
                shim = val - SOFT_FOOT_THRESHOLD_MM if val > SOFT_FOOT_THRESHOLD_MM else 0
                self.result_body.add_widget(body_label(
                    "%s: %.2f mm - SOFT FOOT (shim ~%.2f mm)" % (name, val, shim), BAD))
            else:
                self.result_body.add_widget(body_label("%s: %.2f mm - OK" % (name, val), GOOD))
        if not any_soft:
            self.result_body.add_widget(body_label("No soft foot detected at any corner.", GOOD))
        else:
            self.result_body.add_widget(body_label(
                "Correct soft foot before proceeding with coupling alignment - it will "
                "throw off offset/angularity readings otherwise.", MUTED))


# ------------------------------------------------------------------
# GUIDE SCREEN - tolerance reference
# ------------------------------------------------------------------
class GuideScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="guide", **kwargs)
        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12), size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        col.add_widget(section_label("General alignment tolerance guideline"))
        col.add_widget(body_label(
            "Widely-cited rule-of-thumb figures by shaft speed. Always prefer OEM or "
            "coupling manufacturer tolerances for critical or high-speed machines.", MUTED))

        header = GridLayout(cols=5, size_hint_y=None, height=dp(30), spacing=dp(4))
        for h in ("RPM up to", "Good\noffset", "Good\nang/100mm", "OK\noffset", "OK\nang/100mm"):
            header.add_widget(_fit(Label(text=h, bold=True, font_size=sp(11), color=ACCENT,
                                          halign="center", valign="middle")))
        col.add_widget(header)

        for max_rpm, go, ga, oo, oa in TOLERANCE_BANDS:
            row = GridLayout(cols=5, size_hint_y=None, height=dp(30), spacing=dp(4))
            rpm_txt = "%d" % max_rpm if max_rpm < 999999 else "6000+"
            for val in (rpm_txt, "%.3f" % go, "%.3f" % ga, "%.3f" % oo, "%.3f" % oa):
                row.add_widget(_fit(Label(text=val, font_size=sp(11), color=TEXT,
                                           halign="center", valign="middle")))
            col.add_widget(row)

        col.add_widget(section_label("Offset vs. angularity", ACCENT))
        col.add_widget(body_label(
            "Offset (parallel) misalignment: shaft centerlines are parallel but not "
            "coincident. Angularity misalignment: shaft centerlines meet at an angle "
            "rather than running parallel. Most real-world misalignment is a mix of both, "
            "which is why the coupling reading alone isn't enough - it has to be "
            "extrapolated out to MF1 (near foot) and MF2 (far foot) on the Calculator tab, "
            "same naming convention Easy-Laser uses. Vertical results are given as Add/Remove "
            "shim; horizontal results are given as Move Left/Right. Correct vertical first, "
            "then horizontal - shimming can shift the horizontal reading slightly."))

        col.add_widget(section_label("Soft foot", ACCENT))
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

        footer = Label(text="Built by Gnaneswar", color=MUTED, font_size=sp(11),
                        size_hint_y=None, height=dp(26))
        self.add_widget(footer)

        self.switch("calc")

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def switch(self, name):
        self.sm.current = name
        for n, btn in self.nav_buttons.items():
            btn.set_active(n == name)

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
