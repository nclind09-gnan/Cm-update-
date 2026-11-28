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
  - Vibration Basics (basics_tab.py) - foundational vibration-analysis reference
  - Simulation     (simulation_tab.py) - interactive balance demo and teaching tools

The app opens on a Home screen: the four field tools as one grouped list,
learning and simulation as tiles below. Tapping one opens that tool under a
shared header (back, title, where you are). Look and tokens: theme.py. Each tool is built the
first time it is opened (a short "Opening ..." screen shows meanwhile), not
at launch, so the app starts quickly; after that it stays in memory.
"""
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, RoundedRectangle, Rectangle
import theme as T
from theme import IconTile, Icon

# every screen sits on the same graphite background now
TAB_BG = {k: T.BG for k in ("home", "cmdx", "rotor", "bearing", "laser", "turbo", "basics", "sim")}

WHITE = T.TEXT
MUTED = T.TEXT_3

# (name, title, one-line description, accent, icon, group)
CARD_SPECS = [
    ("cmdx", "CM/DX Diagnostics", "Fault wizard, spectrum, severity, report", T.ACCENTS["cmdx"], "pulse", "field"),
    ("rotor", "Rotor Balance", "Single & two plane, trial weight, split, trim", T.ACCENTS["rotor"], "rotor", "field"),
    ("bearing", "Bearing Freq", "14,535 bearings - BPFO BPFI BSF FTF", T.ACCENTS["bearing"], "bearing", "field"),
    ("laser", "Laser Align", "Foot corrections, soft foot, tolerances", T.ACCENTS["laser"], "align", "field"),
    ("basics", "Basics", "14 topics", T.ACCENTS["basics"], "book", "learn"),
    ("turbo", "Turbo", "32 insights", T.ACCENTS["turbo"], "turbine", "learn"),
    ("sim", "Simulation", "6 labs", T.ACCENTS["sim"], "wave", "learn"),
]

TOOL_TITLES = {"cmdx": "CM/DX", "rotor": "Rotor Balance", "bearing": "Bearing Freq",
               "laser": "Laser Align", "turbo": "Turbomachinery", "basics": "Vibration Basics",
               "sim": "Simulation"}


TOOL_MODULES = {"cmdx": ("cmdx_tab", "CMDXApp"), "rotor": ("rotor_tab", "BalanceApp"),
                "bearing": ("bearing_tab", "BearingScopeApp"), "laser": ("laser_tab", "LaserAlignApp"),
                "turbo": ("turbo_tab", "TurboApp"), "basics": ("basics_tab", "BasicsApp"),
                "sim": ("simulation_tab", "SimulationApp")}


def _accent(name):
    return T.ACCENTS[name]


def _fit_label(label):
    """Make a Label wrap/align within whatever width its parent gives it."""
    label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    return label


class _Row(ButtonBehavior, BoxLayout):
    """One field-tool row inside the grouped Home card."""

    def __init__(self, title, subtitle, accent, icon, divider, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(72),
                         padding=[T.S4, T.S3, T.S3, T.S3], spacing=T.S3, **kwargs)
        with self.canvas.before:
            self._press = Color(1, 1, 1, 0)
            self._press_rect = Rectangle()
            if divider:
                Color(*T.LINE)
                self._div = Line(width=1)
            else:
                self._div = None
        self.bind(pos=self._redraw, size=self._redraw,
                  state=lambda w, v: setattr(self._press, "a", 0.06 if v == "down" else 0))
        anchor = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(40))
        anchor.add_widget(Widget())
        anchor.add_widget(IconTile(icon, accent))
        anchor.add_widget(Widget())
        self.add_widget(anchor)
        col = BoxLayout(orientation="vertical", spacing=dp(2))
        col.add_widget(Widget())
        col.add_widget(_fit_label(Label(text=title, bold=True, font_size=T.FS_TITLE, color=T.TEXT,
                                        halign="left", valign="middle", size_hint_y=None, height=dp(22))))
        col.add_widget(_fit_label(Label(text=subtitle, font_size=T.FS_BODY, color=T.TEXT_2,
                                        halign="left", valign="middle", size_hint_y=None, height=dp(20),
                                        shorten=True, shorten_from="right")))
        col.add_widget(Widget())
        self.add_widget(col)
        chev = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(20))
        chev.add_widget(Widget())
        chev.add_widget(Icon("chevron", T.ICON, dp(20)))
        chev.add_widget(Widget())
        self.add_widget(chev)

    def _redraw(self, *a):
        self._press_rect.pos, self._press_rect.size = self.pos, self.size
        if self._div is not None:
            self._div.points = [self.x + T.S4 + dp(40) + T.S3, self.y, self.x + self.width, self.y]


class _Tile(ButtonBehavior, BoxLayout):
    """A compact learn/simulate tile on Home."""

    def __init__(self, title, subtitle, accent, icon, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(116),
                         padding=[T.S3, T.S3, T.S3, T.S3], spacing=T.S1, **kwargs)
        with self.canvas.before:
            Color(*T.CARD)
            self._bg = RoundedRectangle(radius=[T.R_CARD])
            Color(*T.LINE)
            self._line = Line(width=1)
            self._press = Color(1, 1, 1, 0)
            self._press_rect = RoundedRectangle(radius=[T.R_CARD])
        self.bind(pos=self._redraw, size=self._redraw,
                  state=lambda w, v: setattr(self._press, "a", 0.06 if v == "down" else 0))
        self.add_widget(IconTile(icon, accent, dp(36)))
        self.add_widget(Widget())
        self.add_widget(_fit_label(Label(text=title, bold=True, font_size=T.FS_BODY, color=T.TEXT,
                                         halign="left", valign="bottom", size_hint_y=None, height=dp(18))))
        self.add_widget(_fit_label(Label(text=subtitle, font_size=T.FS_CAPTION, color=T.TEXT_2,
                                         halign="left", valign="top", size_hint_y=None, height=dp(16))))

    def _redraw(self, *a):
        self._bg.pos = self._press_rect.pos = self.pos
        self._bg.size = self._press_rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, T.R_CARD)


class _Group(BoxLayout):
    """A rounded card holding rows separated by hairlines."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*T.CARD)
            self._bg = RoundedRectangle(radius=[T.R_CARD])
            Color(*T.LINE)
            self._line = Line(width=1)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *a):
        self._bg.pos, self._bg.size = self.pos, self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, T.R_CARD)


class HomeScreen(Screen):
    """Field tools first, as one grouped list; learning and simulation as
    three tiles below. The thing you came to do is one tap away."""

    def __init__(self, on_pick, **kwargs):
        super().__init__(name="home", **kwargs)
        with self.canvas.before:
            Color(*T.BG)
            self._bg = Rectangle(pos=(0, 0), size=self.size)
        self.bind(size=lambda w, v: setattr(self._bg, "size", v))

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        col = BoxLayout(orientation="vertical", size_hint_y=None, spacing=T.S6,
                        padding=[T.S4, T.S8, T.S4, T.S4])
        col.bind(minimum_height=col.setter("height"))

        head = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(62), spacing=dp(2),
                         padding=[T.S2, 0, T.S2, 0])
        head.add_widget(_fit_label(Label(text="CONDITION MONITORING SUITE", bold=True,
                                         font_size=T.FS_CAPTION, color=T.TEXT_3, halign="left",
                                         valign="bottom", size_hint_y=None, height=dp(20))))
        head.add_widget(_fit_label(Label(text="CM Toolkit", bold=True, font_size=T.FS_DISPLAY,
                                         color=T.TEXT, halign="left", valign="top",
                                         size_hint_y=None, height=dp(40))))
        col.add_widget(head)

        field = [c for c in CARD_SPECS if c[5] == "field"]
        learn = [c for c in CARD_SPECS if c[5] == "learn"]

        sec = BoxLayout(orientation="vertical", size_hint_y=None, spacing=T.S2)
        sec.bind(minimum_height=sec.setter("height"))
        sec.add_widget(self._caption("Field tools"))
        group = _Group()
        for i, (name, title, sub, acc, icon, _g) in enumerate(field):
            row = _Row(title, sub, acc, icon, divider=i < len(field) - 1)
            row.bind(on_release=lambda w, n=name: on_pick(n))
            group.add_widget(row)
        sec.add_widget(group)
        col.add_widget(sec)

        sec = BoxLayout(orientation="vertical", size_hint_y=None, spacing=T.S2)
        sec.bind(minimum_height=sec.setter("height"))
        sec.add_widget(self._caption("Learn & simulate"))
        grid = GridLayout(cols=3, spacing=T.S2, size_hint_y=None, height=dp(116))
        for name, title, sub, acc, icon, _g in learn:
            tile = _Tile(title, sub, acc, icon)
            tile.bind(on_release=lambda w, n=name: on_pick(n))
            grid.add_widget(tile)
        sec.add_widget(grid)
        col.add_widget(sec)

        col.add_widget(Label(text="Built by Gnaneswar", font_size=T.FS_CAPTION, color=T.TEXT_3,
                             size_hint_y=None, height=dp(32)))
        scroll.add_widget(col)
        self.add_widget(scroll)

    @staticmethod
    def _caption(text):
        return _fit_label(Label(text=text.upper(), bold=True, font_size=T.FS_CAPTION, color=T.TEXT_3,
                                halign="left", valign="middle", size_hint_y=None, height=dp(20),
                                padding=[T.S2, 0]))


class LoadingScreen(Screen):
    """Shown for a moment the first time a tool is opened, while it is built."""

    def __init__(self, **kwargs):
        super().__init__(name="loading", **kwargs)
        with self.canvas.before:
            self._bg_color = Color(*T.BG)
            self._bg = Rectangle(pos=(0, 0), size=self.size)
        self.bind(size=lambda w, v: setattr(self._bg, "size", v))
        self.label = Label(text="", font_size=T.FS_TITLE, bold=True, color=T.TEXT_2)
        self.add_widget(self.label)

    def show(self, title, bg, accent):
        self._bg_color.rgba = bg
        self.label.color = accent
        self.label.text = "Opening %s..." % title


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


class _BackButton(ButtonBehavior, Widget):
    """48 dp back target with a chevron; dims while pressed."""

    def __init__(self, on_back, **kwargs):
        super().__init__(size_hint=(None, None), size=(T.TOUCH, T.TOUCH), **kwargs)
        self.bind(pos=self._draw, size=self._draw, state=self._draw)
        self.bind(on_release=lambda *a: on_back())

    def _draw(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 0.08 if self.state == "down" else 0)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[T.R_CARD])
            T.draw_icon("back", self.center_x, self.center_y, dp(24), T.TEXT)


class ToolBar(BoxLayout):
    """The one header every tool shows: back, title, a subtitle that follows
    where you are inside the tool, and the tool's accent dot. A tool drives
    the title/subtitle through bind_bar, so tools have no header of their own."""

    def __init__(self, name, on_back, **kwargs):
        super().__init__(size_hint_y=None, height=dp(64), padding=[dp(4), dp(8), T.S4, dp(8)],
                         spacing=dp(4), **kwargs)
        accent = _accent(name)
        with self.canvas.before:
            Color(*T.BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*T.LINE)
            self._div = Line(width=1)
        self.bind(pos=self._redraw, size=self._redraw)

        self.back = _BackButton(on_back)
        self.add_widget(self.back)

        col = BoxLayout(orientation="vertical", padding=[dp(4), 0, 0, 0])
        self.title_lbl = _fit_label(Label(text=TOOL_TITLES[name], bold=True, font_size=T.FS_HEADER,
                                          color=T.TEXT, halign="left", valign="middle",
                                          shorten=True, shorten_from="right"))
        self.sub_lbl = _fit_label(Label(text="", font_size=T.FS_CAPTION, color=T.TEXT_2,
                                        halign="left", valign="top", size_hint_y=None, height=0,
                                        shorten=True, shorten_from="right"))
        col.add_widget(self.title_lbl)
        col.add_widget(self.sub_lbl)
        self.add_widget(col)

        dot = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
        with dot.canvas:
            Color(*accent)
            d = RoundedRectangle(size=(dp(10), dp(10)), radius=[dp(5)])
        dot.bind(pos=lambda w, v: setattr(d, "pos", v))
        wrap = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(10))
        wrap.add_widget(Widget())
        wrap.add_widget(dot)
        wrap.add_widget(Widget())
        self.add_widget(wrap)

    def _redraw(self, *a):
        self._bg.pos, self._bg.size = self.pos, self.size
        self._div.points = [self.x, self.y, self.x + self.width, self.y]

    def set(self, title=None, subtitle=None):
        if title is not None:
            self.title_lbl.text = title
        if subtitle is not None:
            self.sub_lbl.text = subtitle
            self.sub_lbl.height = dp(16) if subtitle else 0


def _tool_screen(name, root_widget, on_back):
    """Wrap a tool's root widget with the header bar and its own Screen."""
    screen = Screen(name=name)
    wrapper = BoxLayout(orientation="vertical")
    bar = ToolBar(name, on_back)
    wrapper.add_widget(bar)
    wrapper.add_widget(root_widget)
    screen.add_widget(wrapper)
    # tools that know about the bar hide their own header and drive this one
    hook = getattr(root_widget, "bind_bar", None)
    if callable(hook):
        try:
            hook(bar.set)
        except Exception:
            traceback.print_exc()
    return screen


class CMToolkitApp(App):
    title = "CM Toolkit"
    icon = "icon.png"

    def build(self):
        Window.clearcolor = TAB_BG["home"]

        self.sm = ScreenManager(transition=FadeTransition(duration=0.12))
        self.sm.add_widget(HomeScreen(on_pick=self.switch))
        self.sm.add_widget(LoadingScreen())

        # Tools are built the first time they are opened, not at launch, so
        # the Home screen appears straight away. Once built a tool is kept,
        # so opening it again is instant and keeps whatever you entered.
        self.tool_roots = {}
        self._pending = None

        self.sm.current = "home"
        Window.bind(on_keyboard=self._on_keyboard)
        return self.sm

    def _build_tool(self, name):
        module, cls = TOOL_MODULES[name]
        label = TOOL_TITLES[name]

        def make():
            mod = __import__(module)
            return getattr(mod, cls)().build()

        root = _safe_build(make, label)
        self.tool_roots[name] = root
        self.sm.add_widget(_tool_screen(name, root, on_back=self.go_back))

    def go_back(self):
        """One step back: inside a tool, its own back first (e.g. from a
        section to that tool's menu); otherwise to Home. Used by both the
        Back button in the header and the phone's back button."""
        cur = self.sm.current
        if cur == "home":
            return False
        if cur == "loading":
            self.switch("home")
            return True
        tool = self.tool_roots.get(cur)
        if tool is not None and hasattr(tool, "handle_back"):
            try:
                if tool.handle_back():
                    return True
            except Exception:
                traceback.print_exc()
        self.switch("home")
        return True

    def _on_keyboard(self, window, key, *args):
        """Intercept the Android hardware/gesture back button (keycode 27).
        While inside a tool, back first asks that tool to handle its own
        internal navigation (e.g. CM/DX: go from a section back to its own
        menu); only if the tool has nothing more to go back to do we return
        to Home. On Home itself, let the event through so the OS can close
        the app normally."""
        if key != 27:
            return False
        return self.go_back()

    def switch(self, name):
        if name != "home" and name not in self.tool_roots:
            # show "Opening ..." first, then build on a later frame so the
            # message is on screen while the tool is being made
            self._pending = name
            Window.clearcolor = TAB_BG[name]
            loading = self.sm.get_screen("loading")
            loading.show(TOOL_TITLES[name], TAB_BG[name], _accent(name))
            self.sm.current = "loading"
            Clock.schedule_once(lambda dt: self._finish_open(name), 0.18)
            return
        self._pending = None
        Window.clearcolor = TAB_BG[name]
        self.sm.current = name

    def _finish_open(self, name):
        if self._pending != name:
            return                       # user went back before it opened
        if name not in self.tool_roots:
            self._build_tool(name)
        self.switch(name)


if __name__ == "__main__":
    CMToolkitApp().run()
