# -*- coding: utf-8 -*-
"""
theme.py - small shared UI helpers for a modern look, reused by cmdx_tab.py,
rotor_tab.py, bearing_tab.py, and laser_tab.py. Purely cosmetic (rounded pill
nav buttons + rounded input fields) - none of the domain logic in the four
tool modules lives here or depends on anything beyond these two widgets.
"""
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle


class RoundedButton(ButtonBehavior, BoxLayout):
    """A full-width rounded action button (e.g. Calculate/Diagnose/Check)."""

    def __init__(self, text, accent, text_color=(1, 1, 1, 1), height=None, **kwargs):
        super().__init__(size_hint_y=None, height=(height or dp(48)), **kwargs)
        with self.canvas.before:
            self._color = Color(*accent)
            self._rect = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._redraw, size=self._redraw)
        self.label = Label(text=text, bold=True, font_size=sp(15), color=text_color)
        self.add_widget(self.label)

    def _redraw(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size


class NavCard(ButtonBehavior, BoxLayout):
    """A modern flat nav card: rounded panel, colored accent stripe, title +
    subtitle, chevron. Used for the top-level Home screen and for CM/DX's
    internal section menu."""

    def __init__(self, title, subtitle, accent, card_bg=(0.11, 0.13, 0.18, 1),
                 title_color=(1, 1, 1, 1), subtitle_color=(0.58, 0.62, 0.70, 1),
                 height=None, **kwargs):
        super().__init__(orientation="horizontal", padding=[dp(18), dp(12), dp(16), dp(12)],
                          spacing=dp(14), size_hint_y=None, height=(height or dp(84)), **kwargs)
        with self.canvas.before:
            Color(*card_bg)
            self._bg = RoundedRectangle(radius=[dp(16)])
            Color(*accent)
            self._accent = RoundedRectangle(radius=[dp(3)])
        self.bind(pos=self._redraw, size=self._redraw)

        text_col = BoxLayout(orientation="vertical", spacing=dp(2))
        title_lbl = Label(text=title, bold=True, font_size=sp(17), color=title_color,
                           halign="left", valign="bottom", size_hint_y=None, height=dp(24))
        title_lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        sub_lbl = Label(text=subtitle, font_size=sp(12), color=subtitle_color,
                         halign="left", valign="top")
        sub_lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        text_col.add_widget(title_lbl)
        text_col.add_widget(sub_lbl)
        self.add_widget(text_col)

        chevron = Label(text=">", bold=True, font_size=sp(22), color=accent,
                         size_hint_x=None, width=dp(20))
        self.add_widget(chevron)

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._accent.pos = self.pos
        self._accent.size = (dp(6), self.height)


class PillButton(ButtonBehavior, BoxLayout):
    """A rounded nav-bar / segmented-control button that toggles between an
    active accent fill and an inactive fill, optionally also swapping text
    color (e.g. white-on-blue when active, dark-on-light when inactive)."""

    def __init__(self, text, accent, inactive=(0.16, 0.18, 0.23, 1),
                 text_color=(1, 1, 1, 1), inactive_text_color=None, **kwargs):
        super().__init__(padding=[dp(4), dp(6)], **kwargs)
        self.accent = accent
        self.inactive = inactive
        self.active_text_color = text_color
        self.inactive_text_color = inactive_text_color or text_color
        with self.canvas.before:
            self._color = Color(*inactive)
            self._rect = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._redraw, size=self._redraw)
        self.label = Label(text=text, bold=True, font_size=sp(13), color=text_color)
        self.add_widget(self.label)

    def _redraw(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set_active(self, active):
        self._color.rgba = self.accent if active else self.inactive
        self.label.color = self.active_text_color if active else self.inactive_text_color


def build_pill_tab_bar(specs, on_switch, height=46, spacing=dp(6), padding=dp(4)):
    """specs: list of (name, label, accent) tuples.
    Returns (bar_widget, buttons_dict) - buttons_dict maps name -> PillButton
    so the caller can call set_active on the right ones after a switch."""
    bar = BoxLayout(size_hint_y=None, height=height, spacing=spacing,
                     padding=[padding, padding])
    buttons = {}
    for name, label, accent in specs:
        btn = PillButton(label, accent)
        btn.bind(on_release=lambda inst, n=name: on_switch(n))
        bar.add_widget(btn)
        buttons[name] = btn
    return bar, buttons


class ModernInput(BoxLayout):
    """A rounded-corner input field wrapper. Exposes .text like a plain
    TextInput so existing `self.some_field.text` call sites keep working
    unchanged - only field-construction call sites need to swap to this."""

    def __init__(self, hint_text="", text="", multiline=False, height=None,
                 panel_color=(0.16, 0.18, 0.23, 1), text_color=(0.92, 0.94, 0.97, 1),
                 accent=(0.09, 0.68, 0.62, 1), font_size=sp(14), **kwargs):
        # Kwargs meant for the inner TextInput (readonly, input_filter, etc.) vs. the
        # outer BoxLayout wrapper (size_hint_x, etc.) - split by what TextInput accepts.
        ti_keys = ("readonly", "input_filter", "halign", "valign")
        ti_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in ti_keys}
        super().__init__(size_hint_y=None, height=(height or dp(44)), padding=dp(2), **kwargs)
        with self.canvas.before:
            Color(*panel_color)
            self._rect = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self._redraw, size=self._redraw)
        self.ti = TextInput(
            hint_text=hint_text, text=text, multiline=multiline,
            background_normal="", background_active="", background_color=(0, 0, 0, 0),
            foreground_color=text_color, hint_text_color=(text_color[0], text_color[1], text_color[2], 0.45),
            cursor_color=accent, font_size=font_size, padding=[dp(10), dp(10), dp(10), dp(10)],
            **ti_kwargs,
        )
        self.add_widget(self.ti)
        if multiline and height is None:
            self.height = dp(100)

    def _redraw(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    @property
    def text(self):
        return self.ti.text

    @text.setter
    def text(self, value):
        self.ti.text = value
