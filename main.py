# -*- coding: utf-8 -*-
"""
CM Toolkit - merged launcher

Combines five independent Kivy apps as screens in one APK, each keeping
its own internal logic untouched:
  - CM/DX          (cmdx_tab.py)   - condition monitoring diagnostics
  - Rotor Balance  (rotor_tab.py)  - single-plane balancing calculator
  - Bearing Freq   (bearing_tab.py)- bearing defect frequency scope
  - Laser Align    (laser_tab.py)  - shaft alignment calculator
  - Turbomachinery (turbo_tab.py)  - rotordynamics/turbo learning insights

The app opens on a Home screen with five cards. Tapping a card opens
that tool full-screen with its own back bar - none of them auto-opens
on launch.
"""
import traceback

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle
from theme import NavCard

# Background color per screen (matches each tool's own design)
TAB_BG = {
    "home": (0.055, 0.067, 0.098, 1),      # dark navy, matches the app icon
    "cmdx": (0.078, 0.09, 0.102, 1),       # CM/DX dark theme
    "rotor": (1, 1, 1, 1),                 # Rotor Balance white theme
    "bearing": (0.957, 0.969, 0.984, 1),   # Bearing Freq Scope light theme
    "laser": (0.043, 0.055, 0.078, 1),     # Laser Align dark theme
    "turbo": (0.078, 0.09, 0.102, 1),      # Turbomachinery Insights dark theme
}

WHITE = (1, 1, 1, 1)
MUTED = (0.58, 0.62, 0.70, 1)
CARD_BG = (0.11, 0.13, 0.18, 1)

CARD_SPECS = [
    ("cmdx", "CM/DX", "Vibration, oil, thermal & electrical diagnostics", (0.20, 0.55, 0.95, 1)),
    ("rotor", "Rotor Balance", "Single-plane influence-coefficient calculator", (0.09, 0.68, 0.62, 1)),
    ("bearing", "Bearing Freq", "Bearing defect frequency scope & lookup", (0.96, 0.62, 0.18, 1)),
    ("laser", "Laser Align", "Shaft alignment offset, angularity & soft foot", (0.65, 0.40, 0.95, 1)),
    ("turbo", "Turbomachinery", "Rotordynamics & turbo fault learning insights", (0.867, 0.267, 0.298, 1)),
]

TOOL_TITLES = {"cmdx": "CM/DX", "rotor": "Rotor Balance", "bearing": "Bearing Freq",
               "laser": "Laser Align", "turbo": "Turbomachinery"}


def _fit_label(label):
    """Make a Label wrap/align within whatever width its parent gives it."""
    label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    return label


class HomeScreen(Screen):
    def __init__(self, on_pick, **kwargs):
        super().__init__(name="home", **kwargs)
        with self.canvas.before:
            Color(*TAB_BG["home"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

        root = BoxLayout(orientation="vertical", padding=[dp(22), dp(48), dp(22), dp(20)], spacing=dp(22))

        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(66), spacing=dp(4))
        header.add_widget(Label(text="CM Toolkit", bold=True, font_size=sp(30), color=WHITE,
                                 halign="left", valign="bottom", size_hint_y=None, height=dp(40)))
        header.add_widget(_fit_label(Label(text="Condition Monitoring Suite", font_size=sp(14),
                                            color=MUTED, halign="left", valign="top",
                                            size_hint_y=None, height=dp(20))))
        root.add_widget(header)

        cards = BoxLayout(orientation="vertical", spacing=dp(14), size_hint_y=None)
        cards.bind(minimum_height=cards.setter("height"))
        for name, title, subtitle, accent in CARD_SPECS:
            card = NavCard(title, subtitle, accent, card_bg=CARD_BG,
                           title_color=WHITE, subtitle_color=MUTED, height=dp(96))
            card.bind(on_release=lambda inst, n=name: on_pick(n))
            cards.add_widget(card)
        root.add_widget(cards)

        root.add_widget(Widget())  # spacer pushes footer down

        root.add_widget(Label(text="Built by Gnaneswar", font_size=sp(12), color=MUTED,
                               size_hint_y=None, height=dp(28)))

        self.add_widget(root)

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


def _safe_build(build_fn, label):
    """Build a sub-app's root widget, catching any exception so one
    broken tool can't take down the whole merged app."""
    try:
        return build_fn()
    except Exception:
        err = traceback.format_exc()
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        box.add_widget(Label(
            text=f"{label} failed to load - screenshot this and send it in chat:",
            color=(1, 0.4, 0.4, 1), bold=True, font_size=sp(15),
            size_hint_y=None, height=dp(50), halign="left", valign="top",
        ))
        scroll = ScrollView()
        err_label = _fit_label(Label(text=err, color=(1, 1, 1, 1), font_size=sp(12),
                                      size_hint_y=None, halign="left", valign="top"))
        err_label.bind(texture_size=lambda w, ts: setattr(w, "height", ts[1]))
        scroll.add_widget(err_label)
        box.add_widget(scroll)
        return box


def _tool_screen(name, root_widget, on_back):
    """Wrap a tool's root widget with a slim back bar and its own Screen."""
    accent = next(a for n, _, _, a in CARD_SPECS if n == name)
    screen = Screen(name=name)
    wrapper = BoxLayout(orientation="vertical")

    bar = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(4), dp(4)], spacing=dp(8))
    with bar.canvas.before:
        Color(*accent)
        bar_bg = Rectangle(pos=bar.pos, size=bar.size)
    bar.bind(pos=lambda w, v: setattr(bar_bg, "pos", v), size=lambda w, v: setattr(bar_bg, "size", v))

    back_btn = Button(text="< Back", bold=True, size_hint_x=None, width=dp(96),
                       background_normal="", background_color=(0, 0, 0, 0), color=WHITE)
    back_btn.bind(on_release=lambda *a: on_back())
    bar.add_widget(back_btn)
    bar.add_widget(_fit_label(Label(text=TOOL_TITLES[name], bold=True, font_size=sp(17), color=WHITE,
                                     halign="left", valign="middle")))
    wrapper.add_widget(bar)
    wrapper.add_widget(root_widget)
    screen.add_widget(wrapper)
    return screen


class CMToolkitApp(App):
    title = "CM Toolkit"
    icon = "icon.png"

    def build(self):
        Window.clearcolor = TAB_BG["home"]

        self.sm = ScreenManager(transition=FadeTransition(duration=0.12))
        self.sm.add_widget(HomeScreen(on_pick=self.switch))

        try:
            import cmdx_tab
            cmdx_root = _safe_build(lambda: cmdx_tab.CMDXApp().build(), "CM/DX")
        except Exception:
            cmdx_root = _safe_build(lambda: (_ for _ in ()).throw(Exception(traceback.format_exc())), "CM/DX")

        try:
            import rotor_tab
            rotor_root = _safe_build(lambda: rotor_tab.BalanceApp().build(), "Rotor Balance")
        except Exception:
            rotor_root = _safe_build(lambda: (_ for _ in ()).throw(Exception(traceback.format_exc())), "Rotor Balance")

        try:
            import bearing_tab
            bearing_root = _safe_build(lambda: bearing_tab.BearingScopeApp().build(), "Bearing Freq")
        except Exception:
            bearing_root = _safe_build(lambda: (_ for _ in ()).throw(Exception(traceback.format_exc())), "Bearing Freq")

        try:
            import laser_tab
            laser_root = _safe_build(lambda: laser_tab.LaserAlignApp().build(), "Laser Align")
        except Exception:
            laser_root = _safe_build(lambda: (_ for _ in ()).throw(Exception(traceback.format_exc())), "Laser Align")

        try:
            import turbo_tab
            turbo_root = _safe_build(lambda: turbo_tab.TurboApp().build(), "Turbomachinery")
        except Exception:
            turbo_root = _safe_build(lambda: (_ for _ in ()).throw(Exception(traceback.format_exc())), "Turbomachinery")

        self.tool_roots = {"cmdx": cmdx_root, "rotor": rotor_root, "bearing": bearing_root,
                            "laser": laser_root, "turbo": turbo_root}

        for name, widget in (("cmdx", cmdx_root), ("rotor", rotor_root), ("bearing", bearing_root),
                              ("laser", laser_root), ("turbo", turbo_root)):
            self.sm.add_widget(_tool_screen(name, widget, on_back=lambda: self.switch("home")))

        self.sm.current = "home"
        Window.bind(on_keyboard=self._on_keyboard)
        return self.sm

    def _on_keyboard(self, window, key, *args):
        """Intercept the Android hardware/gesture back button (keycode 27).
        While inside a tool, back first asks that tool to handle its own
        internal navigation (e.g. CM/DX: go from a section back to its own
        menu); only if the tool has nothing more to go back to do we return
        to Home. On Home itself, let the event through so the OS can close
        the app normally."""
        if key != 27:
            return False
        if self.sm.current == "home":
            return False
        tool = self.tool_roots.get(self.sm.current)
        if tool is not None and hasattr(tool, "handle_back") and tool.handle_back():
            return True
        self.switch("home")
        return True

    def switch(self, name):
        Window.clearcolor = TAB_BG[name]
        self.sm.current = name


if __name__ == "__main__":
    CMToolkitApp().run()
