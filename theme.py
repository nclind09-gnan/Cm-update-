# -*- coding: utf-8 -*-
"""
theme.py - the CM Toolkit design system: colour tokens, type scale, spacing,
icons and the shared widgets every tool builds its screens from.

Look: "field instrument dark". Deep graphite surfaces, crisp light text, and
one accent colour per tool, used only where it means something (the tool's
icon, the selected tab, the main action and the result). Status colours
(good / alert / danger) are kept for meaning and always go with a word.

Tokens are defined once here; tool modules map their own palette names onto
them, so a colour change is made in one place.
"""
import math

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle


def _rgba(hex_str, a=1.0):
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


# ----------------------------------------------------------------------
# tokens
# ----------------------------------------------------------------------
# neutrals (graphite ramp)
BG = _rgba("0E1116")          # screen background, also input field fill
CARD = _rgba("161B22")        # cards, panels, list groups
RAISED = _rgba("1E242D")      # pressed rows, selected segment track
LINE = _rgba("252C36")        # dividers, card borders
FIELD_LINE = _rgba("2E3642")  # input / outline-button borders
SELECTED = _rgba("2A323D")    # selected segment of a segmented control
TEXT = _rgba("E8ECF1")        # primary text           (15.8:1 on BG)
TEXT_2 = _rgba("A7B0BC")      # secondary text          (8.4:1 on BG)
TEXT_3 = _rgba("8C96A3")      # labels, captions        (6.0:1 on BG)
ICON = _rgba("6B7582")        # chevrons, inactive icons (3.6:1, non-text)
ON_ACCENT = _rgba("0B0F14")   # text on a bright accent fill

TEXT_HEX, TEXT_2_HEX, TEXT_3_HEX = "E8ECF1", "A7B0BC", "8C96A3"

# one accent per tool
ACCENTS = {
    "home": _rgba("4C9BF5"),
    "cmdx": _rgba("4C9BF5"),
    "rotor": _rgba("22C3B4"),
    "bearing": _rgba("F5A23A"),
    "laser": _rgba("A97BF5"),
    "turbo": _rgba("F0606E"),
    "basics": _rgba("4CCB74"),
    "sim": _rgba("F05B9C"),
}

# status - always shown with a word, never colour alone
GOOD, ALERT, DANGER = _rgba("22C55E"), _rgba("F59E0B"), _rgba("EF4444")
GOOD_TEXT, ALERT_TEXT, DANGER_TEXT = _rgba("4ADE80"), _rgba("FBBF24"), _rgba("F87171")
GOOD_HEX, ALERT_HEX, DANGER_HEX = "4ADE80", "FBBF24", "F87171"

# chart series on a dark plot (distinct in lightness as well as hue)
SERIES = {
    "blue": _rgba("5B9CF6"), "green": _rgba("4CCB74"), "orange": _rgba("F59E42"),
    "red": _rgba("F0606E"), "purple": _rgba("B18CFF"), "amber": _rgba("F5C542"),
    "teal": _rgba("2EC4B6"), "grey": _rgba("8C96A3"),
}
PLOT_BG = CARD
GRID = _rgba("252C36")
GRID_FAINT = _rgba("1C222B")

# type scale (sp) - five sizes
FS_CAPTION, FS_BODY, FS_TITLE, FS_HEADER, FS_DISPLAY = sp(12), sp(14), sp(16), sp(20), sp(28)
MONO = "RobotoMono-Regular"   # bundled with Kivy; used for readings

# spacing (dp) on a 4/8 grid, radii, touch
S1, S2, S3, S4, S6, S8 = dp(4), dp(8), dp(12), dp(16), dp(24), dp(32)
R_CARD, R_FIELD, R_CHIP = dp(12), dp(10), dp(20)
TOUCH = dp(48)
BUTTON_H = dp(52)


def hex_of(rgba):
    return "%02X%02X%02X" % tuple(int(round(c * 255)) for c in rgba[:3])


def soft(rgba, a=0.16):
    """The accent at low strength, for icon tiles and selected rows."""
    return (rgba[0], rgba[1], rgba[2], a)


def _luma(rgba):
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgba[0]) + 0.7152 * ch(rgba[1]) + 0.0722 * ch(rgba[2])


def on_color(fill):
    """Readable text colour on a filled control: dark on bright accents,
    white on dark fills."""
    return ON_ACCENT if _luma(fill) > 0.18 else (1, 1, 1, 1)


def fit_label(label):
    label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    return label


# ----------------------------------------------------------------------
# icons - drawn with Kivy graphics, one stroke weight, so they stay crisp
# and take the tool's colour (Kivy has no SVG)
# ----------------------------------------------------------------------
def draw_icon(name, cx, cy, size, color):
    """Draw a line icon centred on (cx, cy) in the current canvas.
    `size` is the icon box in px."""
    s = size / 24.0
    w = max(1.0, dp(1.6))

    def P(x, y):
        return cx + (x - 12) * s, cy - (y - 12) * s

    def poly(pts):
        out = []
        for x, y in pts:
            out.extend(P(x, y))
        Line(points=out, width=w, cap="round", joint="round")

    def circ(x, y, r, fill=False):
        px, py = P(x, y)
        if fill:
            Ellipse(pos=(px - r * s, py - r * s), size=(2 * r * s, 2 * r * s))
        else:
            Line(circle=(px, py, r * s), width=w)

    Color(*color)
    if name == "pulse":                                  # CM/DX
        poly([(3, 12), (6, 12), (9, 5), (13, 19), (16, 12), (21, 12)])
    elif name == "rotor":                                # balance
        circ(12, 12, 8)
        circ(12, 12, 1.5, True)
        circ(17, 8, 1.8, True)
    elif name == "bearing":
        circ(12, 12, 9)
        circ(12, 12, 4)
        for a in range(0, 360, 60):
            circ(12 + 6.5 * math.sin(math.radians(a)), 12 - 6.5 * math.cos(math.radians(a)), 1.2, True)
    elif name == "align":                                # laser alignment
        poly([(2, 12), (9, 12)])
        poly([(15, 12), (22, 12)])
        poly([(9, 8), (15, 8), (15, 16), (9, 16), (9, 8)])
        poly([(12, 3), (12, 6)])
    elif name == "turbine":
        circ(12, 12, 2.5)
        for a in (90, 210, 330):
            r = math.radians(a)
            poly([(12 + 3 * math.cos(r), 12 - 3 * math.sin(r)),
                  (12 + 9 * math.cos(r + 0.5), 12 - 9 * math.sin(r + 0.5))])
    elif name == "book":                                 # basics
        poly([(4, 5), (11, 5), (12, 7), (12, 19), (11, 17), (4, 17), (4, 5)])
        poly([(20, 5), (13, 5), (12, 7)])
        poly([(20, 5), (20, 17), (13, 17), (12, 19)])
    elif name == "wave":                                 # simulation
        pts = []
        for i in range(25):
            x = 3 + 18 * i / 24.0
            pts.append((x, 12 - 5 * math.sin((x - 3) / 18.0 * 2 * math.pi * 1.5)))
        poly(pts)
    elif name == "chevron":
        poly([(9, 6), (15, 12), (9, 18)])
    elif name == "back":
        poly([(15, 6), (9, 12), (15, 18)])
    else:                                                # neutral dot
        circ(12, 12, 3, True)


class Icon(Widget):
    """A line icon as a widget (fixed size, drawn in the given colour)."""

    def __init__(self, name, color, size_px=None, **kwargs):
        size_px = size_px or dp(22)
        super().__init__(size_hint=(None, None), size=(size_px, size_px), **kwargs)
        self.name, self.color = name, color
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        with self.canvas:
            draw_icon(self.name, self.center_x, self.center_y, self.width, self.color)


class IconTile(Widget):
    """The accent icon on a soft accent square - how a tool is recognised."""

    def __init__(self, name, accent, tile=None, **kwargs):
        tile = tile or dp(40)
        super().__init__(size_hint=(None, None), size=(tile, tile), **kwargs)
        self.name, self.accent = name, accent
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(*soft(self.accent))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            draw_icon(self.name, self.center_x, self.center_y, self.width * 0.55, self.accent)


# ----------------------------------------------------------------------
# widgets
# ----------------------------------------------------------------------
class _Pressable(ButtonBehavior):
    """Shared pressed feedback: a short dim of the fill, no layout change."""

    def _press_alpha(self, *a):
        if hasattr(self, "_press"):
            self._press.a = 0.10 if self.state == "down" else 0.0


class RoundedButton(_Pressable, BoxLayout):
    """The main action button (Calculate, Diagnose, Check ...). Text colour
    is chosen for contrast against the accent unless given."""

    def __init__(self, text, accent, text_color=None, height=None, outline=False, **kwargs):
        super().__init__(size_hint_y=None, height=max(height or BUTTON_H, dp(44)), **kwargs)
        self.outline = outline
        with self.canvas.before:
            if outline:
                self._color = Color(0, 0, 0, 0)
                self._rect = RoundedRectangle(radius=[R_CARD])
                Color(*FIELD_LINE)
                self._line = Line(width=dp(1))
            else:
                self._color = Color(*accent)
                self._rect = RoundedRectangle(radius=[R_CARD])
            self._press = Color(1, 1, 1, 0)
            self._press_rect = RoundedRectangle(radius=[R_CARD])
        self.bind(pos=self._redraw, size=self._redraw, state=self._press_alpha)
        if text_color is None:
            text_color = accent if outline else on_color(accent)
        self.label = Label(text=text, bold=True, font_size=FS_TITLE, color=text_color,
                           halign="center", valign="middle")
        self.label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        self.add_widget(self.label)

    def _redraw(self, *a):
        self._rect.pos = self._press_rect.pos = self.pos
        self._rect.size = self._press_rect.size = self.size
        if self.outline:
            self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, R_CARD)


class NavCard(_Pressable, BoxLayout):
    """A tappable row: icon tile (or accent dot), title, one-line
    description, chevron. Rows grow when a long title wraps."""

    def __init__(self, title, subtitle, accent, card_bg=None, title_color=None,
                 subtitle_color=None, height=None, icon=None, **kwargs):
        super().__init__(orientation="horizontal", padding=[S4, S3, S3, S3],
                         spacing=S3, size_hint_y=None, height=(height or dp(76)), **kwargs)
        self.card_bg = card_bg or CARD
        with self.canvas.before:
            Color(*self.card_bg)
            self._bg = RoundedRectangle(radius=[R_CARD])
            Color(*LINE)
            self._border = Line(width=dp(1))
            self._press = Color(1, 1, 1, 0)
            self._press_rect = RoundedRectangle(radius=[R_CARD])
        self.bind(pos=self._redraw, size=self._redraw, state=self._press_alpha)

        if icon:
            tile = IconTile(icon, accent)
        else:
            tile = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
            with tile.canvas:
                Color(*accent)
                dot = Ellipse(size=(dp(10), dp(10)))
            tile.bind(pos=lambda w, v: setattr(dot, "pos", v))
        anchor = BoxLayout(size_hint_x=None, width=tile.width, orientation="vertical")
        anchor.add_widget(Widget())
        anchor.add_widget(tile)
        anchor.add_widget(Widget())
        self.add_widget(anchor)

        self._base_height = height or dp(76)
        text_col = BoxLayout(orientation="vertical", spacing=dp(2))
        title_lbl = Label(text=title, bold=True, font_size=FS_TITLE, color=title_color or TEXT,
                          halign="left", valign="bottom", size_hint_y=None, height=dp(22))
        title_lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        sub_lbl = Label(text=subtitle, font_size=FS_BODY, color=subtitle_color or TEXT_2,
                        halign="left", valign="top", size_hint_y=None)
        sub_lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        title_lbl.bind(texture_size=lambda w, ts: (setattr(w, "height", max(dp(22), ts[1])), self._fit()))
        sub_lbl.bind(texture_size=lambda w, ts: (setattr(w, "height", ts[1]), self._fit()))
        self._title_lbl, self._sub_lbl = title_lbl, sub_lbl
        text_col.add_widget(Widget())
        text_col.add_widget(title_lbl)
        text_col.add_widget(sub_lbl)
        text_col.add_widget(Widget())
        self.add_widget(text_col)

        chev = BoxLayout(size_hint_x=None, width=dp(20), orientation="vertical")
        chev.add_widget(Widget())
        chev.add_widget(Icon("chevron", ICON, dp(20)))
        chev.add_widget(Widget())
        self.add_widget(chev)

    def _fit(self, *a):
        need = S3 * 2 + self._title_lbl.height + dp(2) + self._sub_lbl.height + dp(8)
        self.height = max(self._base_height, need)

    def _redraw(self, *a):
        self._bg.pos = self._press_rect.pos = self.pos
        self._bg.size = self._press_rect.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, R_CARD)


class PillButton(_Pressable, BoxLayout):
    """A tab / segmented-control button: accent fill when selected, quiet
    outline when not. Colours passed by callers still win."""

    def __init__(self, text, accent, inactive=None, text_color=None,
                 inactive_text_color=None, **kwargs):
        super().__init__(padding=[S2, dp(6)], **kwargs)
        self.accent = accent
        self.inactive = inactive if inactive is not None else (0, 0, 0, 0)
        self.active_text_color = text_color if text_color is not None else on_color(accent)
        self.inactive_text_color = inactive_text_color or TEXT_2
        with self.canvas.before:
            self._color = Color(*self.inactive)
            self._rect = RoundedRectangle(radius=[R_CHIP])
            self._line_color = Color(*FIELD_LINE)
            self._line = Line(width=dp(1))
            self._press = Color(1, 1, 1, 0)
            self._press_rect = RoundedRectangle(radius=[R_CHIP])
        self.bind(pos=self._redraw, size=self._redraw, state=self._press_alpha)
        self.label = Label(text=text, bold=True, font_size=FS_BODY, color=self.inactive_text_color,
                           halign="center", valign="middle")
        self.label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        self.add_widget(self.label)

    def _redraw(self, *a):
        self._rect.pos = self._press_rect.pos = self.pos
        self._rect.size = self._press_rect.size = self.size
        r = min(R_CHIP, self.height / 2.0)
        self._rect.radius = self._press_rect.radius = [r]
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, r)

    def set_active(self, active):
        self._color.rgba = self.accent if active else self.inactive
        self._line_color.a = 0 if active else 1
        self.label.color = self.active_text_color if active else self.inactive_text_color


def build_pill_tab_bar(specs, on_switch, height=dp(56), spacing=S2, padding=S2):
    """specs: list of (name, label, accent) tuples.
    Returns (bar_widget, buttons_dict) - buttons_dict maps name -> PillButton
    so the caller can call set_active on the right ones after a switch."""
    bar = BoxLayout(size_hint_y=None, height=height, spacing=spacing,
                    padding=[S4, padding])
    buttons = {}
    for name, label, accent in specs:
        btn = PillButton(label, accent)
        btn.bind(on_release=lambda inst, n=name: on_switch(n))
        bar.add_widget(btn)
        buttons[name] = btn
    return bar, buttons


class ModernInput(BoxLayout):
    """A rounded input field: dark well, hairline border, accent border while
    focused. Exposes .text like a plain TextInput so existing call sites keep
    working unchanged."""

    def __init__(self, hint_text="", text="", multiline=False, height=None,
                 panel_color=None, text_color=None, accent=None, font_size=None,
                 mono=False, **kwargs):
        ti_keys = ("readonly", "input_filter", "halign", "valign")
        ti_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in ti_keys}
        super().__init__(size_hint_y=None, height=max(height or TOUCH, dp(40)), padding=dp(2), **kwargs)
        self.accent = accent or ACCENTS["home"]
        text_color = text_color or TEXT
        with self.canvas.before:
            Color(*(panel_color or BG))
            self._rect = RoundedRectangle(radius=[R_FIELD])
            self._line_color = Color(*FIELD_LINE)
            self._line = Line(width=dp(1))
        self.bind(pos=self._redraw, size=self._redraw)
        if mono:
            ti_kwargs["font_name"] = MONO
        self.ti = TextInput(
            hint_text=hint_text, text=text, multiline=multiline,
            background_normal="", background_active="", background_color=(0, 0, 0, 0),
            foreground_color=text_color, hint_text_color=TEXT_3,
            cursor_color=self.accent, font_size=font_size or FS_TITLE,
            padding=[S3, S3, S3, S3], **ti_kwargs,
        )
        self.ti.bind(focus=self._focus)
        self.add_widget(self.ti)
        if multiline and height is None:
            self.height = dp(100)

    def _focus(self, ti, focused):
        self._line_color.rgba = self.accent if focused else FIELD_LINE
        self._line.width = dp(1.6) if focused else dp(1)

    def _redraw(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, R_FIELD)

    @property
    def text(self):
        return self.ti.text

    @text.setter
    def text(self, value):
        self.ti.text = value


class Card(BoxLayout):
    """A vertical card (CARD fill, hairline border) whose height follows its
    content. Use for input groups and results."""

    def __init__(self, fill=None, border=None, padding=None, spacing=None, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         padding=padding if padding is not None else S4,
                         spacing=spacing if spacing is not None else S3, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            self._fill = Color(*(fill or CARD))
            self._rect = RoundedRectangle(radius=[R_CARD])
            self._bcol = Color(*(border or LINE))
            self._line = Line(width=dp(1))
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, R_CARD)


def section_label(text, color=None):
    """An upper-case section caption (12 sp, tracked)."""
    lbl = Label(text=text.upper(), bold=True, font_size=FS_CAPTION, color=color or TEXT_3,
                halign="left", valign="middle", size_hint_y=None, height=dp(24))
    return fit_label(lbl)
