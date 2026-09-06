"""
Bearing Defect Frequency Scope — mobile app (Kivy)
Built by Gnaneswar

Catalog search across 18 manufacturers / 14,535 bearings, a custom-geometry
calculator, and an ISO 10816-3 vibration severity reference — all offline,
no internet needed once installed.
"""

import math
import traceback
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from theme import ModernInput, RoundedButton, PillButton

_IMPORT_ERROR = None
try:
    from bearing_data import DATA
except Exception:
    _IMPORT_ERROR = traceback.format_exc()
    DATA = {"data": {}, "labels": {}}  # placeholder so the rest of the file can still load

# ---------------------------------------------------------------- palette --
WHITE = (1, 1, 1, 1)
BG = (0.957, 0.969, 0.984, 1)       # #F4F7FB
PANEL_BORDER = (0.886, 0.906, 0.941, 1)  # #E2E8F0
TEXT = (0.059, 0.09, 0.165, 1)      # #0F172A
MUTED = (0.58, 0.639, 0.722, 1)     # #94A3B8
BLUE = (0.145, 0.388, 0.922, 1)     # #2563EB
BLUE_BG = (0.914, 0.933, 0.996, 1)  # #E9EEF5

CH_COLORS = {
    "BPFO": (0.851, 0.467, 0.024, 1),  # amber  #D97706
    "BPFI": (0.863, 0.149, 0.149, 1),  # red    #DC2626
    "BSF":  (0.035, 0.569, 0.698, 1),  # cyan   #0891B2
    "FTF":  (0.486, 0.227, 0.929, 1),  # violet #7C3AED
}
CH_NAMES = {
    "BPFO": "Ball Pass Freq., Outer",
    "BPFI": "Ball Pass Freq., Inner",
    "BSF": "Ball Spin Frequency",
    "FTF": "Fundamental Train (Cage)",
}
CH_ORDER = ["FTF", "BSF", "BPFI", "BPFO"]

ISO_ZONES = {
    "I":   {"title": "Class I \u2014 Small machines (\u226415 kW)", "bounds": (0.71, 1.8, 4.5)},
    "II":  {"title": "Class II \u2014 Medium machines (15\u201375 kW)", "bounds": (1.12, 2.8, 7.1)},
    "III": {"title": "Class III \u2014 Large, rigid foundation", "bounds": (1.8, 4.5, 11.2)},
    "IV":  {"title": "Class IV \u2014 Large, soft foundation", "bounds": (2.8, 7.1, 18.0)},
}
ZONE_COLORS = {
    "A": (0.063, 0.725, 0.506, 1),
    "B": (0.639, 0.902, 0.208, 1),
    "C": (0.976, 0.451, 0.086, 1),
    "D": (0.973, 0.443, 0.443, 1),
}
ZONE_NAMES = {"A": "Good", "B": "Acceptable", "C": "Unsatisfactory", "D": "Unacceptable"}


def fmt(n, digits=2):
    if n is None:
        return "\u2014"
    return f"{n:,.{digits}f}"


def zone_for(v, bounds):
    if v <= bounds[0]:
        return "A"
    if v <= bounds[1]:
        return "B"
    if v <= bounds[2]:
        return "C"
    return "D"


# ------------------------------------------------------------- UI helpers --
class Card(BoxLayout):
    """A white rounded panel with a border, used throughout the app."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*WHITE)
            self._bg = RoundedRectangle(radius=[dp(14)])
            Color(*PANEL_BORDER)
            self._border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(14)), width=1)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(14))


class SectionLabel(Label):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", MUTED)
        kwargs.setdefault("font_size", sp(12))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(20))
        kwargs.setdefault("halign", "left")
        super().__init__(**kwargs)
        self.bind(size=self._update_align)

    def _update_align(self, *_):
        self.text_size = self.size


class SpectrumWidget(Widget):
    """Simple canvas-drawn spectrum: colored vertical peaks at each order,
    with the 1X reference line and the peak's value printed underneath."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.peaks = []       # list of (label, order, value_text, color)
        self.max_order = 12
        self.size_hint_y = None
        self.height = dp(190)
        self.bind(pos=self.redraw, size=self.redraw)

    def set_peaks(self, peaks, max_order):
        self.peaks = peaks
        self.max_order = max(max_order, 1)
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*WHITE)
            Rectangle(pos=self.pos, size=self.size)

            pad_l, pad_r, pad_t, pad_b = dp(10), dp(10), dp(28), dp(46)
            plot_x = self.x + pad_l
            plot_w = self.width - pad_l - pad_r
            plot_y = self.y + pad_b
            plot_h = self.height - pad_t - pad_b
            if plot_w <= 0 or plot_h <= 0:
                return

            def xfor(order):
                return plot_x + (order / self.max_order) * plot_w

            # faint grid + 1X reference line (lightly darkened)
            step = 2 if self.max_order <= 20 else 4
            t = 0
            while t <= self.max_order:
                Color(0.58, 0.639, 0.722, 1) if t == 1 else Color(0.933, 0.949, 0.969, 1)
                Line(points=[xfor(t), plot_y, xfor(t), plot_y + plot_h], width=1.2 if t == 1 else 1)
                t += 1
            Color(*PANEL_BORDER)
            Line(points=[plot_x, plot_y, plot_x + plot_w, plot_y], width=1)

            for label, order, value_text, color in self.peaks:
                if order is None:
                    continue
                x = xfor(order)
                h = plot_h * 0.68
                Color(*color)
                Line(points=[x, plot_y, x, plot_y + h], width=2.6)

        # text labels drawn as child Labels (canvas text is painful in Kivy)
        for child in list(self.children):
            self.remove_widget(child)
        pad_l, pad_r, pad_t, pad_b = dp(10), dp(10), dp(28), dp(46)
        plot_x = self.x + pad_l
        plot_w = self.width - pad_l - pad_r
        plot_y = self.y + pad_b
        plot_h = self.height - pad_t - pad_b
        if plot_w <= 0 or plot_h <= 0:
            return

        def xfor(order):
            return plot_x + (order / self.max_order) * plot_w

        for i, (label, order, value_text, color) in enumerate(self.peaks):
            if order is None:
                continue
            x = xfor(order)
            h = plot_h * 0.68
            name_lbl = Label(text=label, color=color, bold=True, font_size=sp(14),
                              size_hint=(None, None), size=(dp(70), dp(18)),
                              pos=(x - dp(35), plot_y + h + dp(2)))
            self.add_widget(name_lbl)
            row_offset = dp(16) if i % 2 else 0
            val_lbl = Label(text=value_text, color=color, bold=True, font_size=sp(12),
                             size_hint=(None, None), size=(dp(70), dp(16)),
                             pos=(x - dp(35), plot_y - dp(18) - row_offset))
            self.add_widget(val_lbl)

        one_x = xfor(1)
        one_lbl = Label(text="1X", color=(0.278, 0.333, 0.412, 1), bold=True, font_size=sp(12),
                         size_hint=(None, None), size=(dp(30), dp(16)),
                         pos=(one_x - dp(15), plot_y + plot_h - dp(14)))
        self.add_widget(one_lbl)


# ------------------------------------------------------------------ tabs --
class CatalogTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(10), padding=dp(10), **kwargs)
        self.app = app
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))

        card = Card(padding=dp(14), spacing=dp(8), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))

        card.add_widget(SectionLabel(text="BRAND"))
        self.brand_spinner = Spinner(
            text="All brands",
            values=["All brands"] + sorted(DATA["data"].keys()),
            size_hint_y=None, height=dp(44), font_size=sp(15),
        )
        self.brand_spinner.bind(text=lambda *_: self.do_search())
        card.add_widget(self.brand_spinner)

        card.add_widget(SectionLabel(text="BEARING MODEL"))
        self.query_input = ModernInput(
            text="6205", multiline=False, height=dp(48),
            font_size=sp(17), panel_color=BLUE_BG, text_color=TEXT, accent=BLUE,
        )
        self.query_input.ti.bind(text=lambda *_: self.do_search())
        card.add_widget(self.query_input)

        self.results_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        self.results_box.bind(minimum_height=self.results_box.setter("height"))
        results_scroll = ScrollView(size_hint_y=None, height=dp(160))
        results_scroll.add_widget(self.results_box)
        card.add_widget(results_scroll)

        self.add_widget(card)
        self.do_search()

    def do_search(self):
        self.results_box.clear_widgets()
        q = self.query_input.text.strip().lower()
        if not q:
            return
        brand = self.brand_spinner.text
        keys = list(DATA["data"].keys()) if brand == "All brands" else [brand]
        count = 0
        for k in keys:
            for row in DATA["data"][k]:
                if q in row[0].lower():
                    self.results_box.add_widget(self._result_row(k, row))
                    count += 1
                    if count >= 30:
                        return

    def _result_row(self, brand, row):
        btn = Button(
            text=f"{row[0]}   [size=12]{brand}[/size]", markup=True,
            size_hint_y=None, height=dp(38), font_size=sp(14),
            background_normal="", background_color=(1, 1, 1, 1), color=TEXT,
            halign="left",
        )
        btn.bind(on_release=lambda *_: self.select(brand, row))
        return btn

    def select(self, brand, row):
        self.query_input.text = row[0]
        self.app.set_selection({
            "source": "catalog",
            "brand": brand, "model": row[0],
            "BPFO": row[1], "BPFI": row[2], "BSF": row[3], "FTF": row[4],
        })


class CustomTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(10), padding=dp(10), **kwargs)
        self.app = app
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))

        card = Card(padding=dp(14), spacing=dp(8), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))

        self.inputs = {}
        fields = [
            ("n", "NUMBER OF ROLLING ELEMENTS (N)", "9"),
            ("bd", "ROLLING ELEMENT DIAMETER \u2014 Bd (in)", "0.312"),
            ("pd", "PITCH DIAMETER \u2014 Pd (in)", "1.535"),
            ("angle", "CONTACT ANGLE \u2014 \u03b8 (degrees)", "0"),
        ]
        for key, label, default in fields:
            card.add_widget(SectionLabel(text=label))
            ti = ModernInput(text=default, multiline=False, height=dp(46),
                              font_size=sp(15), panel_color=BLUE_BG, text_color=TEXT, accent=BLUE)
            ti.ti.bind(text=lambda *_: self.compute())
            self.inputs[key] = ti
            card.add_widget(ti)

        btn = RoundedButton(text="Use this geometry", accent=BLUE, height=dp(46))
        btn.bind(on_release=lambda *_: self.compute())
        card.add_widget(btn)

        self.add_widget(card)

    def compute(self):
        try:
            n = float(self.inputs["n"].text or 0)
            bd = float(self.inputs["bd"].text or 0)
            pd = float(self.inputs["pd"].text or 0)
            angle = float(self.inputs["angle"].text or 0)
        except ValueError:
            return
        if not (n and bd and pd):
            return
        ratio = bd / pd
        cos_t = math.cos(math.radians(angle))
        bpfo = (n / 2) * (1 - ratio * cos_t)
        bpfi = (n / 2) * (1 + ratio * cos_t)
        bsf = (pd / (2 * bd)) * (1 - (ratio * cos_t) ** 2)
        ftf = 0.5 * (1 - ratio * cos_t)
        self.app.set_selection({
            "source": "custom", "brand": "", "model": "Custom geometry",
            "BPFO": bpfo, "BPFI": bpfi, "BSF": bsf, "FTF": ftf,
        })


class SeverityTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(10), padding=dp(10), **kwargs)
        self.app = app
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))

        card = Card(padding=dp(14), spacing=dp(8), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))

        card.add_widget(SectionLabel(text="MACHINE CLASS"))
        self.class_spinner = Spinner(
            text="II", values=list(ISO_ZONES.keys()),
            size_hint_y=None, height=dp(44), font_size=sp(15),
        )
        self.class_spinner.bind(text=lambda *_: self.update_result())
        card.add_widget(self.class_spinner)

        card.add_widget(SectionLabel(text="MEASURED VELOCITY (MM/S RMS)"))
        self.velocity_input = ModernInput(
            text="3.2", multiline=False, height=dp(46),
            font_size=sp(15), panel_color=BLUE_BG, text_color=TEXT, accent=BLUE,
        )
        self.velocity_input.ti.bind(text=lambda *_: self.update_result())
        card.add_widget(self.velocity_input)

        self.result_label = Label(
            text="", markup=True, size_hint_y=None, height=dp(60),
            font_size=sp(16), halign="left", valign="middle", color=TEXT,
        )
        self.result_label.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        card.add_widget(self.result_label)

        self.add_widget(card)

        # full reference tables for every class
        for key, z in ISO_ZONES.items():
            ref_card = Card(padding=dp(14), spacing=dp(4), size_hint_y=None)
            ref_card.bind(minimum_height=ref_card.setter("height"))
            ref_card.add_widget(Label(text=z["title"], color=TEXT, bold=True,
                                       font_size=sp(15), size_hint_y=None, height=dp(24),
                                       halign="left", text_size=(Window.width - dp(56), None)))
            b = z["bounds"]
            rows = [
                ("A", f"\u2264 {fmt(b[0])}"),
                ("B", f"{fmt(b[0])} \u2013 {fmt(b[1])}"),
                ("C", f"{fmt(b[1])} \u2013 {fmt(b[2])}"),
                ("D", f"> {fmt(b[2])}"),
            ]
            grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(2))
            grid.bind(minimum_height=grid.setter("height"))
            for letter, rng in rows:
                grid.add_widget(Label(text=letter, color=ZONE_COLORS[letter], bold=True,
                                       font_size=sp(14), size_hint_y=None, height=dp(28), halign="left"))
                grid.add_widget(Label(text=rng, color=TEXT, font_size=sp(14),
                                       size_hint_y=None, height=dp(28), halign="left"))
            ref_card.add_widget(grid)
            self.add_widget(ref_card)

        self.update_result()

    def update_result(self, *_):
        try:
            v = float(self.velocity_input.text or 0)
        except ValueError:
            v = 0
        bounds = ISO_ZONES[self.class_spinner.text]["bounds"]
        z = zone_for(v, bounds)
        r, g, b, a = ZONE_COLORS[z]
        hexc = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
        self.result_label.text = (
            f"[color={hexc}][b][size=28]{z}[/size][/b]  {ZONE_NAMES[z]}[/color]\n"
            f"[color=#64748b]measured {fmt(v)} mm/s RMS[/color]"
        )


# --------------------------------------------------------------- root UI --
class RootUI(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # header
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(64),
                            padding=[dp(14), dp(8)])
        header.add_widget(Label(text="VIBRATION REFERENCE", color=MUTED, bold=True,
                                 font_size=sp(11), size_hint_y=None, height=dp(16), halign="left",
                                 text_size=(Window.width - dp(28), None)))
        header.add_widget(Label(text="Bearing Defect Frequency Scope", color=TEXT, bold=True,
                                 font_size=sp(19), size_hint_y=None, height=dp(28), halign="left",
                                 text_size=(Window.width - dp(28), None)))
        self.add_widget(header)

        # shaft speed (shared across tabs)
        speed_card = Card(orientation="horizontal", padding=dp(12), spacing=dp(10),
                           size_hint_y=None, height=dp(64))
        speed_card.add_widget(Label(text="SHAFT SPEED\n(RPM)", color=MUTED, bold=True,
                                     font_size=sp(11), halign="left"))
        self.rpm_input = ModernInput(text="1750", multiline=False, font_size=sp(20),
                                      text_color=BLUE, panel_color=BLUE_BG, accent=BLUE,
                                      size_hint_x=0.5)
        self.rpm_input.ti.bind(text=lambda *_: self.refresh())
        speed_card.add_widget(self.rpm_input)
        self.add_widget(self._pad(speed_card))
        unit_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6),
                              padding=[dp(14), 0])
        self.unit_buttons = {}
        for u in ("Hz", "CPM", "Orders"):
            b = PillButton(u, accent=BLUE, inactive=BLUE_BG,
                            text_color=WHITE, inactive_text_color=TEXT)
            b.set_active(u == "Hz")
            b.bind(on_release=lambda inst, unit=u: self.set_unit(unit))
            self.unit_buttons[u] = b
            unit_row.add_widget(b)
        self.add_widget(unit_row)
        self.unit = "Hz"

        # mode switcher (segmented control)
        seg_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6), padding=[dp(14), 0])
        self.mode = "catalog"
        self.seg_buttons = {}
        for key, label in (("catalog", "Catalog"), ("custom", "Custom"), ("severity", "Severity")):
            b = PillButton(label, accent=BLUE, inactive=BLUE_BG,
                            text_color=WHITE, inactive_text_color=TEXT)
            b.set_active(key == "catalog")
            b.bind(on_release=lambda inst, k=key: self.set_mode(k))
            self.seg_buttons[key] = b
            seg_row.add_widget(b)
        self.add_widget(seg_row)

        # scrollable body
        self.scroll = ScrollView()
        self.body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10),
                               padding=[0, dp(4), 0, dp(24)])
        self.body.bind(minimum_height=self.body.setter("height"))
        self.scroll.add_widget(self.body)
        self.add_widget(self.scroll)

        footer = Label(text="Built by Gnaneswar", color=MUTED, font_size=sp(11),
                       size_hint_y=None, height=dp(28))
        self.add_widget(footer)

        self.catalog_tab = CatalogTab(app)
        self.custom_tab = CustomTab(app)
        self.severity_tab = SeverityTab(app)

        # results area (spectrum + cards + harmonics), shown for catalog/custom
        self.results_card_holder = BoxLayout(orientation="vertical", size_hint_y=None,
                                              spacing=dp(10), padding=[dp(10), 0])
        self.results_card_holder.bind(minimum_height=self.results_card_holder.setter("height"))
        self._build_results_area()

        self.set_mode("catalog")

    def _pad(self, widget):
        wrap = BoxLayout(size_hint_y=None, height=widget.height, padding=[dp(14), 0])
        wrap.add_widget(widget)
        return wrap

    def _update_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    # ---- results area (spectrum + defect cards + harmonics) ----
    def _build_results_area(self):
        holder = self.results_card_holder

        self.identity_label = Label(text="", color=TEXT, bold=True, font_size=sp(17),
                                     size_hint_y=None, height=dp(26), halign="left",
                                     text_size=(Window.width - dp(20), None))
        holder.add_widget(self.identity_label)

        spectrum_card = Card(padding=dp(6), size_hint_y=None)
        self.spectrum = SpectrumWidget()
        spectrum_card.add_widget(self.spectrum)
        spectrum_card.height = self.spectrum.height + dp(12)
        holder.add_widget(spectrum_card)

        grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(8))
        grid.bind(minimum_height=grid.setter("height"))
        self.channel_cards = {}
        for ch in CH_ORDER:
            c = Card(padding=dp(10), spacing=dp(2), size_hint_y=None, height=dp(112))
            with c.canvas.before:
                Color(*CH_COLORS[ch])
                topbar = Rectangle(pos=(c.x, c.y + c.height - dp(4)), size=(c.width, dp(4)))
            c.bind(pos=lambda inst, val, tb=topbar: setattr(tb, "pos", (inst.x, inst.y + inst.height - dp(4))),
                   size=lambda inst, val, tb=topbar: (setattr(tb, "size", (inst.width, dp(4))),
                                                        setattr(tb, "pos", (inst.x, inst.y + inst.height - dp(4)))))
            name_lbl = Label(text=CH_NAMES[ch], color=MUTED, font_size=sp(10.5), bold=True,
                              size_hint_y=None, height=dp(26), halign="left", valign="top")
            name_lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            label_lbl = Label(text=ch, color=(0.2, 0.255, 0.333, 1), bold=True, font_size=sp(13),
                               size_hint_y=None, height=dp(18), halign="left")
            label_lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            value_lbl = Label(text="\u2014", color=CH_COLORS[ch], bold=True, font_size=sp(22),
                               size_hint_y=None, height=dp(30), halign="left")
            value_lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            order_lbl = Label(text="", color=MUTED, font_size=sp(10.5),
                               size_hint_y=None, height=dp(16), halign="left")
            order_lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
            c.add_widget(name_lbl)
            c.add_widget(label_lbl)
            c.add_widget(value_lbl)
            c.add_widget(order_lbl)
            self.channel_cards[ch] = {"value": value_lbl, "order": order_lbl}
            grid.add_widget(c)
        holder.add_widget(grid)

        harm_card = Card(padding=dp(10), spacing=dp(4), size_hint_y=None)
        harm_card.bind(minimum_height=harm_card.setter("height"))
        harm_card.add_widget(Label(text="HARMONICS (1\u00d7 \u2013 5\u00d7)", color=MUTED, bold=True,
                                    font_size=sp(11), size_hint_y=None, height=dp(20), halign="left",
                                    text_size=(Window.width - dp(52), None)))
        self.harm_grid = GridLayout(cols=6, size_hint_y=None, spacing=dp(2))
        self.harm_grid.bind(minimum_height=self.harm_grid.setter("height"))
        harm_card.add_widget(self.harm_grid)
        holder.add_widget(harm_card)

        note = Label(
            text=("BPFO/BPFI/BSF/FTF are multiples of shaft running speed. "
                  "Hz = order \u00d7 (RPM \u00f7 60). CPM = order \u00d7 RPM."),
            color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(50),
            halign="left", valign="top",
        )
        note.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        holder.add_widget(note)

    def set_unit(self, unit):
        self.unit = unit
        for u, b in self.unit_buttons.items():
            b.set_active(u == unit)
        self.refresh()

    def set_mode(self, mode):
        self.mode = mode
        for k, b in self.seg_buttons.items():
            b.set_active(k == mode)

        self.body.clear_widgets()
        if mode == "catalog":
            self.body.add_widget(self.catalog_tab)
            self.body.add_widget(self.results_card_holder)
            if self.app.selection is None:
                self.catalog_tab.do_search()
        elif mode == "custom":
            self.body.add_widget(self.custom_tab)
            self.body.add_widget(self.results_card_holder)
            self.custom_tab.compute()
        else:
            self.body.add_widget(self.severity_tab)

    def handle_back(self):
        """Called by main.py on the Android hardware back button. Return
        True if handled internally, False to let main.py return to Home."""
        if self.mode != "catalog":
            self.set_mode("catalog")
            return True
        return False

    def refresh(self):
        sel = self.app.selection
        if sel is None or self.mode == "severity":
            return
        try:
            rpm = float(self.rpm_input.text or 0)
        except ValueError:
            rpm = 0
        shaft_hz = rpm / 60.0

        if sel["source"] == "catalog":
            self.identity_label.text = f"{sel['model']}  \u00b7  {sel['brand']}"
        else:
            self.identity_label.text = "Custom geometry"

        orders = {ch: sel[ch] for ch in CH_ORDER}
        max_order = max([12] + [math.ceil(o + 1) for o in orders.values() if o])

        def to_value(order, mult=1):
            o = order * mult
            if self.unit == "Orders":
                return o
            if self.unit == "Hz":
                return o * shaft_hz
            return o * rpm

        suffix = {"Hz": "Hz", "CPM": "CPM", "Orders": "X"}[self.unit]

        peaks = []
        for ch in CH_ORDER:
            order = orders[ch]
            val = to_value(order) if order is not None else None
            peaks.append((ch, order, fmt(val, 1) if val is not None else "", CH_COLORS[ch]))
            wid = self.channel_cards[ch]
            wid["value"].text = f"{fmt(val, 3 if self.unit == 'Orders' else 2)} {suffix}" if val is not None else "\u2014"
            wid["order"].text = f"{fmt(order, 3)}\u00d7 RPM" if order is not None else "not provided"
        self.spectrum.set_peaks(peaks, max_order)

        # harmonics grid: header + 4 rows x (name + 1..5)
        self.harm_grid.clear_widgets()
        headers = ["Freq"] + [f"{h}\u00d7" for h in range(1, 6)]
        for h in headers:
            self.harm_grid.add_widget(Label(text=h, color=MUTED, bold=True, font_size=sp(11),
                                             size_hint_y=None, height=dp(24)))
        for ch in CH_ORDER:
            order = orders[ch]
            self.harm_grid.add_widget(Label(text=ch, color=CH_COLORS[ch], bold=True, font_size=sp(11),
                                             size_hint_y=None, height=dp(24)))
            for h in range(1, 6):
                val = to_value(order, h) if order is not None else None
                self.harm_grid.add_widget(Label(
                    text=fmt(val, 2) if val is not None else "\u2014",
                    color=TEXT, font_size=sp(11), size_hint_y=None, height=dp(24)))


# ---------------------------------------------------------------- app ----
class BearingScopeApp(App):
    title = "Bearing Defect Frequency Scope"

    def build(self):
        Window.clearcolor = BG
        self.selection = None
        self.ui = RootUI(self)
        default_row = None
        for row in DATA["data"].get("SKF", []):
            if row[0] == "6205":
                default_row = row
                break
        if default_row:
            self.set_selection({
                "source": "catalog", "brand": "SKF", "model": default_row[0],
                "BPFO": default_row[1], "BPFI": default_row[2],
                "BSF": default_row[3], "FTF": default_row[4],
            })
        return self.ui

    def set_selection(self, sel):
        self.selection = sel
        self.ui.refresh()


class CrashApp(App):
    """Minimal fallback app: if anything goes wrong, show the error ON
    SCREEN (scrollable, selectable-by-screenshot) instead of just closing.
    No logcat, no permissions, no computer needed to read it."""

    def __init__(self, error_text, **kwargs):
        super().__init__(**kwargs)
        self.error_text = error_text

    def build(self):
        Window.clearcolor = (0.05, 0.05, 0.08, 1)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        root.add_widget(Label(
            text="App failed to start \u2014 screenshot everything below\nand send it in the chat:",
            color=(1, 0.4, 0.4, 1), bold=True, font_size=sp(16),
            size_hint_y=None, height=dp(60), halign="left", valign="top",
        ))
        scroll = ScrollView()
        error_label = Label(
            text=self.error_text, color=(1, 1, 1, 1), font_size=sp(13),
            size_hint_y=None, halign="left", valign="top",
            text_size=(Window.width - dp(32), None),
        )
        error_label.bind(texture_size=lambda w, ts: setattr(w, "height", ts[1]))
        scroll.add_widget(error_label)
        root.add_widget(scroll)
        return root


if __name__ == "__main__":
    if _IMPORT_ERROR:
        CrashApp(_IMPORT_ERROR).run()
    else:
        try:
            BearingScopeApp().run()
        except Exception:
            CrashApp(traceback.format_exc()).run()
