# -*- coding: utf-8 -*-
"""
CM/DX - Condition Monitoring Diagnostics
A single-file Kivy app. Copy this whole file into Pydroid3 as main.py and press Run.
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import BooleanProperty
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
import theme as T
from theme import ModernInput, PillButton, RoundedButton, NavCard
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.base import ExceptionManager, ExceptionHandler

import os
import json
import re

from component_data import COMPONENTS

# ------------------------------------------------------------------
# COLORS - mapped onto the shared design tokens (theme.py)
# ------------------------------------------------------------------
BG = T.BG
PANEL = T.CARD
BORDER = T.LINE
TEXT = T.TEXT
TEXT_2 = T.TEXT_2
MUTED = T.TEXT_3
ACCENT = T.ACCENTS["cmdx"]      # the tool accent (was amber)
AMBER = ACCENT                  # old name kept for the accent role
TEAL = ACCENT
LIME = T.GOOD
ORANGE = T.ALERT
RED = T.DANGER_TEXT

# ------------------------------------------------------------------
# KNOWLEDGE BASE
# ------------------------------------------------------------------
TAGS = {
    "v1": "Dominant peak at 1x running speed, radial direction",
    "v2": "Strong 2x running-speed peak, especially axial",
    "v3": "Multiple harmonics (3x-5x+) with raised noise floor",
    "v4": "Sidebands spaced at running speed around a mesh frequency",
    "v5": "High-frequency peaks unrelated to running speed (bearing tones)",
    "v6": "Non-synchronous peak between 0.42x-0.48x running speed",
    "v7": "Sharp amplitude rise near a speed, ~90 deg phase shift (resonance)",
    "v8": "1x peak with ~180 deg phase difference across the coupling",
    "v9": "Peak at belt-pass frequency and harmonics",
    "v10": "Broadband random/impacting high-frequency noise (pump)",
    "v11": "Peak at 2x line frequency (100/120 Hz) on an electric motor",
    "v12": "Sidebands around line frequency spaced at pole-pass frequency",
    "v13": "Amplitude modulation / slow beating pattern",
    "v22": "Sideband spacing matches bearing outer-race defect frequency (BPFO)",
    "v23": "Sideband spacing matches bearing inner-race defect frequency (BPFI)",
    "v24": "High-frequency energy concentrated in the 1-20 kHz band",
    "v21": "Peak at gear mesh frequency (number of teeth x shaft speed)",
    "o1": "Elevated iron (Fe) in wear debris",
    "o2": "Elevated copper/lead/tin (bronze or babbitt wear)",
    "o3": "Water content above spec, hazy or milky oil",
    "o4": "Viscosity outside the specified range",
    "o5": "Rising particle count / ISO cleanliness code exceeded",
    "o6": "Falling TAN/TBN or rising oxidation markers",
    "o7": "Silicon present, indicating dirt ingress",
    "t1": "Localized hot spot at an electrical connection or terminal",
    "t2": "Bearing housing running hotter than baseline",
    "t3": "Uneven heating across the three motor phases",
    "t4": "Cooler-than-expected zone suggesting blocked flow or low lubricant",
    "e1": "Pole-pass sidebands around running speed (broken rotor bar pattern)",
    "e3": "High-frequency fluting pattern from VFD-induced shaft current",
    "e4": "Current imbalance measured across phases",
}

TAG_GROUPS = [
    ("Vibration signature", ["v1","v2","v3","v4","v5","v6","v7","v8","v9","v10","v11","v12","v13",
                             "v21","v22","v23","v24"]),
    ("Oil analysis", ["o1","o2","o3","o4","o5","o6","o7"]),
    ("Thermography", ["t1","t2","t3","t4"]),
    ("Electrical signature", ["e1","e3","e4"]),
]

# id, technique, name, tags, causes, actions
BASE_FAULTS = [
    dict(id="unbalance", technique="Vibration", name="Rotor unbalance", tags=["v1"],
         causes=["Uneven mass distribution", "Missing/loose balance weight", "Material buildup or erosion on rotor"],
         actions=["Clean the impeller/rotor to remove dust or material buildup.",
                  "If vibration persists after cleaning, implement dynamic balancing.",
                  "Check for a bent shaft if unbalance recurs quickly after balancing."]),
    dict(id="misalign-angular", technique="Vibration", name="Angular misalignment", tags=["v2","v8"],
         causes=["Coupling faces not parallel", "Thermal growth not accounted for at alignment",
                 "Bent, worn, or damaged coupling element"],
         actions=["Check the coupling and achieve precision alignment between driver and driven equipment.",
                  "Verify alignment at normal operating temperature.",
                  "Inspect the coupling element for wear before re-aligning."]),
    dict(id="misalign-parallel", technique="Vibration", name="Parallel (offset) misalignment", tags=["v1","v2"],
         causes=["Shaft centerlines offset but parallel", "Soft foot at the machine base"],
         actions=["Check the motor base for soft foot and align driver to driven equipment.",
                  "Re-torque base bolts before taking final alignment readings.",
                  "Verify baseplate flatness and correct soft foot with shims."]),
    dict(id="loose-structural", technique="Vibration", name="Structural / bolting looseness", tags=["v3"],
         causes=["Loose hold-down bolts", "Cracked frame, base, or grout",
                 "Corroded or cracked mounting hardware"],
         actions=["Ensure proper tightness at the base fixing locations; torque all bolts to spec.",
                  "Check and improve machine grouting for stable, rigid support.",
                  "Inspect the base frame and welds for cracking.",
                  "Strengthen the machine base frame by adding extra stiffeners.",
                  "Ensure proper tightness at the machine base fixing locations, and tighten all bolts to the specified torque.",
                  "Ensure adequate contact area between the foundation and machine base frame, and between the machine base frame and motor or pump base.",
                  "Check and improve machine grouting to maintain stable and rigid support of the machine base.",
                  "Check the motor base for soft foot and ensure precise alignment between the motor and pump."]),
    dict(id="loose-internal", technique="Vibration", name="Internal / rotating-clearance looseness", tags=["v3","v13"],
         causes=["Worn bearing fits", "Excessive internal running clearance",
                 "Loose pedestal bolts or a cracked bearing pedestal"],
         actions=["Check bearing clearances and the interference fit with the housing; correct if excessive.",
                  "Inspect shaft and housing fits for wear or oversize bore.",
                  "Replace worn sleeves/bushings/bearings showing excessive clearance."]),
    dict(id="bearing-defect", technique="Vibration", name="Rolling-element bearing defect", tags=["v5","v22","v23","v24"],
         causes=["Fatigue spall on race or rolling element", "Contamination ingress",
                 "Inadequate or wrong lubrication", "Bearing cocked on the shaft or in the housing"],
         actions=["Bearing defects identified; inspect and replace the bearing.",
                  "Run envelope/HFD analysis to confirm which component is affected.",
                  "Check lubrication condition and quantity at replacement.",
                  "Investigate a root cause (misalignment/unbalance/contamination)."]),
    dict(id="gear-mesh", technique="Vibration", name="Gear mesh wear or misalignment", tags=["v4","v21","v24"],
         causes=["Tooth wear or pitting", "Excessive backlash", "Gearbox shaft misalignment",
                 "Eccentric gear or bent gear shaft"],
         actions=["Inspect gearbox internals for backlash, root clearances, and tooth alignment.",
                  "Sample gearbox oil for wear metals.",
                  "Note: gearbox internal component details are needed for further analysis.",
                  "Inspect the girth gear to pinion root clearances and backlash, and rectify the same.",
                  "Check and inspect girth gear to pinion backlash setting and correct the gearbox alignment.",
                  "Check the girth and pinion teeth mating using blue matching.",
                  "Check the clearances and tolerances between the girth gear and pinion."]),
    dict(id="oil-whirl", technique="Vibration", name="Oil whirl / whip instability", tags=["v6","v13"],
         causes=["Insufficient bearing load", "Oil viscosity too low", "Worn journal bearing clearance"],
         actions=["Verify oil viscosity and operating temperature against spec.",
                  "Inspect journal bearing clearance for excessive wear.",
                  "Check bearing load is within design range; light loading promotes whirl."]),
    dict(id="resonance", technique="Vibration", name="Structural resonance", tags=["v7"],
         causes=["Operating speed close to a structural natural frequency",
                 "Natural frequency coinciding with vane pass or a bearing tone"],
         actions=["Confirm the natural frequency with a bump/modal test.",
                  "Stiffen the structure or shift the operating speed away from it.",
                  "Add damping if changing speed/stiffness is not practical."]),
    dict(id="belt", technique="Vibration", name="Belt wear or pulley misalignment", tags=["v9"],
         causes=["Worn, glazed, or mismatched belts", "Pulleys misaligned or loose",
                 "Incorrect belt tension", "Belt natural frequency coinciding with sheave RPM"],
         actions=["Inspect belt condition and tension; check pulley alignment.",
                  "Replace belts as a matched set if worn.",
                  "Re-tension per OEM specification, not by feel alone."]),
    dict(id="cavitation", technique="Vibration", name="Pump cavitation", tags=["v10"],
         causes=["Insufficient NPSH available", "Restricted or blocked suction",
                 "Entrained air in suction line"],
         actions=["Ensure the pump operates within its recommended flow range.",
                  "Check suction line for restrictions, air leaks, or blockages.",
                  "Verify suction pressure and NPSH available against pump design."]),
    dict(id="roots-blower", technique="Vibration", name="Roots blower lobe clearance", tags=[],
         causes=["Excessive clearance between the two lobed rotors (rotor-to-rotor and rotor-to-casing)", "Lobe wear from contamination",
                 "Timing gear wear affecting lobe synchronization"],
         actions=["Verify rotor-to-rotor and rotor-to-casing clearances and correct any deviations."]),
    dict(id="pump-flow", technique="Vibration", name="Pump off-design flow / impeller wear", tags=[],
         causes=["Pump operating outside its designed flow/pressure window", "Impeller wear or corrosion",
                 "Excessive clearance between impeller and casing"],
         actions=["Maintain the pump's operating flow and pressure within the designed parameters.",
                  "If the flow is within specifications, inspect the pump impeller for signs of corrosion.",
                  "Measure the air gaps between the impeller and the casing to ensure proper clearances."]),
    dict(id="eccentricity", technique="Vibration", name="Rotor / stator eccentricity", tags=["v11"],
         causes=["Non-uniform air gap between rotor and stator",
                 "Eccentric stator from soft foot or a warped base"],
         actions=["Check air gaps between rotor and stator for uniformity.",
                  "Verify bearing fit and housing bore concentricity.",
                  "Run electrical signature analysis (ESA) to corroborate."]),
    dict(id="broken-rotor-bar", technique="Vibration", name="Broken or cracked rotor bar", tags=["v12","e1"],
         causes=["Cracked, broken, or high-resistance rotor bar joints",
                 "Shorted end rings or rotor laminations"],
         actions=["Inspect rotor bars for damage; confirm with motor current signature analysis.",
                  "Trend pole-pass sidebands over time.",
                  "Plan rotor repair/replacement at the next outage."]),
    dict(id="vfd-edm", technique="Electrical", name="VFD-induced bearing fluting / EDM", tags=["e3","v5"],
         causes=["Shaft currents from VFD common-mode voltage discharging through bearings"],
         actions=["Install a shaft grounding ring; verify motor frame bonding.",
                  "Check the VFD output filter and cable shielding/bonding.",
                  "Consider insulated bearings on the non-drive end if recurring."]),
    dict(id="wear-metals", technique="Oil", name="Abnormal component wear", tags=["o1","o2","o5"],
         causes=["Accelerated wear of gears, bearings, or bushings"],
         actions=["Identify the source of wear debris; inspect the associated component.",
                  "Compare wear-metal ratios against baseline trends.",
                  "Shorten the oil sampling interval until the trend stabilizes."]),
    dict(id="water-contam", technique="Oil", name="Water contamination", tags=["o3"],
         causes=["Seal failure", "Condensation in the reservoir/breather",
                 "Washdown or ingress during maintenance"],
         actions=["Inspect seals and breathers for the source of ingress; change the oil.",
                  "Add a desiccant breather if recurring.",
                  "Retest oil after changing to confirm water content is within spec."]),
    dict(id="lube-degradation", technique="Oil", name="Lubricant degradation", tags=["o4","o6"],
         causes=["Oxidation from age or overheating", "Wrong lubricant grade in service"],
         actions=["Change the oil; verify the correct lubricant grade for the application.",
                  "Check operating temperature against the lubricant's thermal limits.",
                  "Shorten the sampling interval until oxidation markers stabilize."]),
    dict(id="dirt-ingress", technique="Oil", name="Dirt / particulate contamination", tags=["o7"],
         causes=["Failed breather or seal allowing ingress"],
         actions=["Inspect breathers and seals for the source of contamination.",
                  "Upgrade filtration if required.",
                  "Flush the system if cleanliness code is far out of spec."]),
    dict(id="loose-connection", technique="Thermal", name="Loose or degraded electrical connection", tags=["t1"],
         causes=["Loose terminal lug", "Corrosion at a connection point"],
         actions=["Check and re-torque the electrical connection to spec.",
                  "Clean or replace the terminal if corroded.",
                  "Re-scan under normal load to confirm the hot spot has cleared."]),
    dict(id="bearing-overheat", technique="Thermal", name="Bearing overheating", tags=["t2","v5"],
         causes=["Lubrication failure or wrong grease", "Overload", "Misalignment driving up bearing load"],
         actions=["Check lubrication type and quantity.",
                  "Verify alignment and coupling load.",
                  "Cross-check against vibration bearing-tone data."]),
    dict(id="winding-insulation", technique="Thermal", name="Winding insulation issue / phase imbalance", tags=["t3","e4"],
         causes=["Insulation breakdown on one phase", "Unequal supply voltage across phases"],
         actions=["Check winding insulation resistance.",
                  "Verify current balance across all three phases.",
                  "Investigate supply voltage balance at the panel."]),
    dict(id="lube-starvation", technique="Thermal", name="Lubrication starvation", tags=["t4"],
         causes=["Blocked lubrication line", "Low oil level", "Degraded or hardened grease"],
         actions=["Verify the lubrication supply line, oil level, and grease condition.",
                  "Check for a blocked line, failed pump, or clogged fitting.",
                  "Re-scan after replenishment to confirm resolution."]),
]

# ------------------------------------------------------------------
# FAULT LIBRARY PERSISTENCE
# BASE_FAULTS above is fixed. User edits and additions are stored in a
# small JSON file and layered on top at runtime, so app updates never
# wipe out anything the user has customized.
# ------------------------------------------------------------------

def _library_file():
    try:
        app = App.get_running_app()
        base_dir = app.user_data_dir if app else "."
    except Exception:
        base_dir = "."
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base_dir, "cmdx_library_overrides.json")


def _load_overrides():
    path = _library_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                data.setdefault("overrides", {})
                data.setdefault("custom", [])
                return data
        except Exception:
            pass
    return {"overrides": {}, "custom": []}


def _save_overrides(data):
    path = _library_file()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return True
    except Exception:
        return False


def rebuild_faults():
    """Rebuild the global FAULTS list from BASE_FAULTS + saved overrides/custom faults."""
    data = _load_overrides()
    overrides = data.get("overrides", {})
    combined = []
    for base in BASE_FAULTS:
        f = dict(base)
        if f["id"] in overrides:
            f.update(overrides[f["id"]])
        combined.append(f)
    combined.extend(data.get("custom", []))
    FAULTS[:] = combined


def save_fault_edit(fault_id, name, causes, actions, tags=None):
    """Persist an edit to an existing fault (base or custom) and refresh FAULTS."""
    data = _load_overrides()
    custom_list = data.get("custom", [])
    for c in custom_list:
        if c["id"] == fault_id:
            c["name"], c["causes"], c["actions"] = name, causes, actions
            if tags is not None:
                c["tags"] = tags
            _save_overrides(data)
            rebuild_faults()
            return
    override = {"name": name, "causes": causes, "actions": actions}
    if tags is not None:
        override["tags"] = tags
    data.setdefault("overrides", {})[fault_id] = override
    _save_overrides(data)
    rebuild_faults()


def add_custom_fault(name, technique, causes, actions, tags=None):
    """Add a brand-new fault to the library and persist it. Returns the new id."""
    data = _load_overrides()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "custom"
    existing_ids = {f["id"] for f in FAULTS} | {c["id"] for c in data.get("custom", [])}
    fid, n = "custom-" + slug, 2
    while fid in existing_ids:
        fid = "custom-%s-%d" % (slug, n)
        n += 1
    entry = dict(id=fid, technique=technique, name=name, tags=(tags or []), causes=causes, actions=actions)
    data.setdefault("custom", []).append(entry)
    _save_overrides(data)
    rebuild_faults()
    return fid


FAULTS = []
rebuild_faults()


CLASS_BOUNDARIES = {
    "I": (0.71, 1.8, 4.5),
    "II": (1.12, 2.8, 7.1),
    "III": (1.8, 4.5, 11.2),
    "IV": (2.8, 7.1, 18.0),
}
CLASS_META = {
    "I": ("Class I - Small machines", "up to 15 kW"),
    "II": ("Class II - Medium machines", "15-75 kW"),
    "III": ("Class III - Large rigid foundations", "large rotating masses on rigid, heavy foundations"),
    "IV": ("Class IV - Large soft foundations", "large prime movers on relatively soft foundations"),
}
# ISO 10816-1 zones: text colour (with the zone word) and the bar fill
ZONE_INFO = {
    "A": ("Good", T.GOOD_TEXT, "Typical of a newly commissioned machine. Continue normal monitoring."),
    "B": ("Acceptable", T.GOOD_TEXT, "Suitable for unrestricted long-term operation."),
    "C": ("Unsatisfactory", T.ALERT_TEXT, "Generally unsatisfactory for long-term operation. Plan corrective action."),
    "D": ("Unacceptable", T.DANGER_TEXT, "Vibration severity is likely to cause damage. Investigate or shut down promptly."),
}
ZONE_FILL = {"A": T.GOOD, "B": T.soft(T.GOOD, 0.55), "C": T.ALERT, "D": T.DANGER}


def get_zone(rms, cls):
    ab, bc, cd = CLASS_BOUNDARIES[cls]
    if rms <= ab:
        return "A"
    if rms <= bc:
        return "B"
    if rms <= cd:
        return "C"
    return "D"


def zone_range_label(cls, zone):
    ab, bc, cd = CLASS_BOUNDARIES[cls]
    if zone == "A":
        return "<= %s" % ab
    if zone == "B":
        return "%s - %s" % (ab, bc)
    if zone == "C":
        return "%s - %s" % (bc, cd)
    return "> %s" % cd


EXCLUSIVE_TAGS = [{"v22", "v23"}]


def score_faults(selected_tags, technique_filter=None):
    results = []
    for f in FAULTS:
        if technique_filter and f["technique"] != technique_filter:
            continue
        matched = [t for t in f["tags"] if t in selected_tags]
        if not matched:
            continue
        # tags that cannot occur together (an outer race defect shows BPFO,
        # an inner race one BPFI, never both) count once in the denominator,
        # so a fault listing both alternatives is not capped below 100%
        total = len(f["tags"])
        for group in EXCLUSIVE_TAGS:
            n_in = len(group.intersection(f["tags"]))
            if n_in > 1:
                total -= n_in - 1
        results.append((len(matched) / float(total), len(matched), f))
    results.sort(key=lambda r: (-r[0], -r[1]))
    return results


# ------------------------------------------------------------------
# SMALL UI HELPERS
# ------------------------------------------------------------------

def section_label(text, color=None):
    """Group caption (upper-case, tracked) when no colour is given; a plain
    field label in the given colour otherwise."""
    if color is None:
        lbl = T.section_label(text)
        lbl.height = dp(32)
        lbl.valign = "bottom"
        return lbl
    lbl = Label(text=text, color=color, bold=True, font_size=T.FS_BODY, size_hint_y=None,
                height=dp(28), halign="left", valign="bottom")
    lbl.bind(width=lambda inst, val: setattr(lbl, "text_size", (val, None)))
    lbl.bind(texture_size=lambda inst, ts: setattr(lbl, "height", max(dp(28), ts[1] + dp(6))))
    return lbl


def field_label(text):
    return section_label(text, TEXT_2)


def body_label(text, color=TEXT, markup=False, font_size=None, font_name=None):
    lbl = Label(text=text, color=color, size_hint_y=None, halign="left", valign="top",
                markup=markup, font_size=font_size or T.FS_BODY)
    if font_name:
        lbl.font_name = font_name
    lbl.bind(width=lambda inst, val: setattr(lbl, "text_size", (val, None)))
    lbl.bind(texture_size=lambda inst, val: setattr(lbl, "height", val[1] + dp(6)))
    return lbl


class _Option(SpinnerOption):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = T.RAISED
        self.color = TEXT
        self.font_size = T.FS_BODY
        self.height = T.TOUCH


def make_spinner(text, values):
    """A Spinner on the dark tokens (field fill, hairline border)."""
    sp_ = Spinner(text=text, values=values, size_hint_y=None, height=T.TOUCH,
                  background_normal="", background_down="", background_color=(0, 0, 0, 0),
                  color=TEXT, font_size=T.FS_TITLE, option_cls=_Option,
                  halign="left", valign="middle", padding=[T.S3, 0])
    sp_.bind(size=lambda w, s: setattr(w, "text_size", (s[0], s[1])))
    with sp_.canvas.before:
        Color(*BG)
        rect = RoundedRectangle(radius=[T.R_FIELD])
        Color(*T.FIELD_LINE)
        line = Line(width=dp(1))

    def _redraw(w, *a):
        rect.pos, rect.size = w.pos, w.size
        line.rounded_rectangle = (w.x, w.y, w.width, w.height, T.R_FIELD)
    sp_.bind(pos=_redraw, size=_redraw)
    with sp_.canvas.after:
        Color(*T.ICON)
        chev = Line(width=dp(1.4), cap="round", joint="round")

    def _chev(w, *a):
        cx, cy, s = w.right - dp(20), w.center_y, dp(4)
        chev.points = [cx - s, cy + s / 2, cx, cy - s / 2, cx + s, cy + s / 2]
    sp_.bind(pos=_chev, size=_chev)
    return sp_


def make_popup(title, content, size_hint):
    return Popup(title=title, content=content, size_hint=size_hint,
                 background="", background_color=PANEL, title_color=TEXT,
                 title_size=T.FS_TITLE, separator_color=BORDER,
                 overlay_color=(0, 0, 0, 0.6))


def secondary_button(text, height=None, **kw):
    return RoundedButton(text=text, accent=ACCENT, outline=True, text_color=TEXT,
                         height=height, **kw)


class TagRow(ButtonBehavior, BoxLayout):
    """A tappable checklist row: square check box + wrapped text. Has an
    `active` property like a CheckBox so the existing toggle code works."""
    active = BooleanProperty(False)

    def __init__(self, text, active=False, **kw):
        super().__init__(size_hint_y=None, height=T.TOUCH, spacing=T.S3,
                         padding=[T.S3, T.S2, T.S3, T.S2], **kw)
        with self.canvas.before:
            self._fill = Color(*T.soft(ACCENT, 0.0))
            self._bg = RoundedRectangle(radius=[T.R_FIELD])
        box = Widget(size_hint=(None, None), size=(dp(22), dp(22)))
        anchor = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(22))
        anchor.add_widget(Widget())
        anchor.add_widget(box)
        anchor.add_widget(Widget())
        self._box = box
        self.add_widget(anchor)
        self.label = body_label(text, TEXT)
        self.label.valign = "middle"
        self.label.pos_hint = {"center_y": 0.5}
        self.label.bind(height=self._fit)
        self.add_widget(self.label)
        self.bind(pos=self._redraw, size=self._redraw, active=self._redraw)
        box.bind(pos=self._redraw)
        self.active = active
        self._redraw()

    def _fit(self, *a):
        self.height = max(T.TOUCH, self.label.height + T.S2 * 2)

    def on_release(self):
        self.active = not self.active

    def _redraw(self, *a):
        self._bg.pos, self._bg.size = self.pos, self.size
        self._fill.rgba = T.soft(ACCENT, 0.12 if self.active else 0.0)
        b = self._box
        b.canvas.clear()
        with b.canvas:
            if self.active:
                Color(*ACCENT)
                RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(5)])
                Color(*T.ON_ACCENT)
                x, y, s = b.x, b.y, b.width
                Line(points=[x + s * 0.24, y + s * 0.52, x + s * 0.43, y + s * 0.32,
                             x + s * 0.78, y + s * 0.70], width=dp(1.8), cap="round", joint="round")
            else:
                Color(*T.ICON)
                Line(rounded_rectangle=(b.x, b.y, b.width, b.height, dp(5)), width=dp(1.2))


class ListRow(ButtonBehavior, BoxLayout):
    """A tappable list row on a card: title, optional caption, chevron."""

    def __init__(self, text, caption=None, **kw):
        super().__init__(size_hint_y=None, height=dp(56), spacing=T.S3,
                         padding=[T.S4, T.S2, T.S3, T.S2], **kw)
        with self.canvas.before:
            Color(*PANEL)
            self._bg = RoundedRectangle(radius=[T.R_CARD])
            Color(*BORDER)
            self._line = Line(width=dp(1))
            self._press = Color(1, 1, 1, 0)
            self._prect = RoundedRectangle(radius=[T.R_CARD])
        self.bind(pos=self._redraw, size=self._redraw,
                  state=lambda *a: setattr(self._press, "a", 0.08 if self.state == "down" else 0))
        col = BoxLayout(orientation="vertical", size_hint_y=None)
        self._title = body_label(text, TEXT)
        self._title.bold = True
        col.add_widget(self._title)
        self._cap = None
        if caption:
            self._cap = body_label(caption, MUTED, font_size=T.FS_CAPTION)
            col.add_widget(self._cap)
        self._col = col
        for w in (self._title, self._cap):
            if w is not None:
                w.bind(height=self._fit)
        wrap = BoxLayout(orientation="vertical")
        wrap.add_widget(Widget())
        wrap.add_widget(col)
        wrap.add_widget(Widget())
        self.add_widget(wrap)
        chev = BoxLayout(size_hint_x=None, width=dp(20), orientation="vertical")
        chev.add_widget(Widget())
        chev.add_widget(T.Icon("chevron", T.ICON, dp(20)))
        chev.add_widget(Widget())
        self.add_widget(chev)

    def _fit(self, *a):
        h = self._title.height + (self._cap.height if self._cap is not None else 0)
        self._col.height = h
        self.height = max(dp(56), h + T.S2 * 2 + dp(4))

    def _redraw(self, *a):
        self._bg.pos = self._prect.pos = self.pos
        self._bg.size = self._prect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, T.R_CARD)


class ColorBar(Widget):
    """A simple 4-segment colored severity bar (A/B/C/D) with an optional marker."""
    def __init__(self, class_key, rms=None, **kwargs):
        super().__init__(**kwargs)
        self.class_key = class_key
        self.rms_value = rms
        self.size_hint_y = None
        self.height = dp(14)
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        try:
            self.canvas.clear()
            ab, bc, cd = CLASS_BOUNDARIES[self.class_key]
            maxv = cd * 1.4
            widths = [ab / maxv, (bc - ab) / maxv, (cd - bc) / maxv, (maxv - cd) / maxv]
            x = self.x
            gap = dp(2)
            with self.canvas:
                for zone, w in zip(["A", "B", "C", "D"], widths):
                    Color(*ZONE_FILL[zone])
                    RoundedRectangle(pos=(x, self.y), size=(max(0, w * self.width - gap), self.height),
                                     radius=[dp(3)])
                    x += w * self.width
                if self.rms_value is not None:
                    marker_x = self.x + min(self.rms_value / maxv, 1) * self.width
                    Color(*BG)
                    Rectangle(pos=(marker_x - dp(3), self.y - dp(3)), size=(dp(6), self.height + dp(6)))
                    Color(*TEXT)
                    Rectangle(pos=(marker_x - dp(1.5), self.y - dp(3)), size=(dp(3), self.height + dp(6)))
        except Exception as e:
            print("ColorBar redraw failed:", e)


def result_card(score, matched, fault):
    box = T.Card(padding=[T.S4, T.S3], spacing=T.S2)
    box.add_widget(body_label(
        "[b]%s[/b]\n[size=%d][color=%s]%s  |  %d/%d signs[/color][/size]" % (
            fault["name"], int(T.FS_CAPTION), T.hex_of(ACCENT), fault["technique"],
            matched, len(fault["tags"])),
        TEXT, markup=True, font_size=T.FS_TITLE))
    box.add_widget(body_label("Likely causes:\n- " + "\n- ".join(fault["causes"]), TEXT_2))
    box.add_widget(body_label("Recommendations:\n" +
                               "\n".join("%d. %s" % (i + 1, a) for i, a in enumerate(fault["actions"])), TEXT))
    return box


def _action_bar(*buttons):
    """Bottom action strip on the screen background with a hairline above."""
    row = BoxLayout(size_hint_y=None, height=T.BUTTON_H + T.S2 * 2,
                    padding=[T.S4, T.S2], spacing=T.S2)
    with row.canvas.before:
        Color(*BG)
        bg = Rectangle()
        Color(*BORDER)
        ln = Line(width=1)

    def _r(w, *a):
        bg.pos, bg.size = w.pos, w.size
        ln.points = [w.x, w.top, w.right, w.top]
    row.bind(pos=_r, size=_r)
    for b in buttons:
        row.add_widget(b)
    return row


def _results_area():
    scroll = ScrollView(size_hint_y=0.45)
    col = GridLayout(cols=1, size_hint_y=None, spacing=T.S2, padding=[T.S4, T.S2, T.S4, T.S4])
    col.bind(minimum_height=col.setter("height"))
    scroll.add_widget(col)
    return scroll, col


def _page_col(spacing=None):
    col = GridLayout(cols=1, size_hint_y=None, spacing=spacing if spacing is not None else T.S2,
                     padding=[T.S4, T.S3, T.S4, T.S4])
    col.bind(minimum_height=col.setter("height"))
    return col


# ------------------------------------------------------------------
# SCREENS
# ------------------------------------------------------------------

class WizardScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True
        self.selected = set()
        root = BoxLayout(orientation="vertical")
        scroll = ScrollView()
        col = _page_col(spacing=dp(2))

        col.add_widget(body_label(
            "Check every observation that applies. Then tap Diagnose.", TEXT_2))

        self.checks = {}
        for title, tags in TAG_GROUPS:
            col.add_widget(section_label(title))
            for t in tags:
                cb = TagRow(TAGS[t])
                cb.bind(active=self.make_toggle(t))
                self.checks[t] = cb
                col.add_widget(cb)

        scroll.add_widget(col)
        root.add_widget(scroll)

        diag_btn = RoundedButton(text="Diagnose", accent=ACCENT)
        diag_btn.bind(on_release=self.diagnose)
        clear_btn = secondary_button("Clear")
        clear_btn.bind(on_release=self.clear_all)
        root.add_widget(_action_bar(diag_btn, clear_btn))

        self.results_scroll, self.results_col = _results_area()
        root.add_widget(self.results_scroll)

        self.add_widget(root)

    def make_toggle(self, tag):
        def _toggle(instance, value):
            if value:
                self.selected.add(tag)
            else:
                self.selected.discard(tag)
        return _toggle

    def clear_all(self, *a):
        for cb in self.checks.values():
            cb.active = False
        self.selected.clear()
        self.results_col.clear_widgets()

    def diagnose(self, *a):
        self.results_col.clear_widgets()
        results = score_faults(self.selected)
        if not results:
            self.results_col.add_widget(body_label("No matches yet - select some observations above.", MUTED))
            return
        for score, matched, fault in results[:8]:
            self.results_col.add_widget(result_card(score, matched, fault))


class SpectrumScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True
        self.toggle_tags = ["v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12", "v13"]
        self.toggle_labels = {
            "v4": "Sidebands around mesh frequency", "v5": "High-freq bearing tone",
            "v6": "Peak at 0.42x-0.48x speed", "v7": "Sharp rise, ~90 deg phase shift",
            "v8": "180 deg phase across coupling", "v9": "Peak at belt-pass frequency",
            "v10": "Broadband random/impacting noise", "v11": "Peak at 2x line frequency",
            "v12": "Sidebands at pole-pass frequency", "v13": "Slow amplitude beating",
        }
        self.toggle_state = {t: False for t in self.toggle_tags}

        root = BoxLayout(orientation="vertical")
        scroll = ScrollView()
        col = _page_col()

        col.add_widget(body_label("Enter the spectrum reading, then tap Diagnose.", TEXT_2))

        self.amp1x = self._num_field(col, "1x amplitude (mm/s)")
        self.amp2x = self._num_field(col, "2x amplitude (mm/s)")
        self.amp3x = self._num_field(col, "3x+ amplitude (mm/s)")
        self.rms = self._num_field(col, "Overall velocity RMS (mm/s)")

        col.add_widget(field_label("Machine class"))
        self.cls_spinner = make_spinner("II", list(CLASS_BOUNDARIES.keys()))
        col.add_widget(self.cls_spinner)

        col.add_widget(section_label("Additional signature present"))
        self.toggle_buttons = {}
        for t in self.toggle_tags:
            b = PillButton(self.toggle_labels[t], ACCENT, size_hint_y=None, height=T.TOUCH)
            b.set_active(False)
            b.bind(on_release=self.make_flip(t))
            self.toggle_buttons[t] = b
            col.add_widget(b)

        scroll.add_widget(col)
        root.add_widget(scroll)

        btn = RoundedButton(text="Diagnose", accent=ACCENT)
        btn.bind(on_release=self.diagnose)
        root.add_widget(_action_bar(btn))

        self.results_scroll, self.results_col = _results_area()
        root.add_widget(self.results_scroll)

        self.add_widget(root)

    def _num_field(self, col, label):
        col.add_widget(field_label(label))
        ti = ModernInput(text="0", multiline=False, input_filter="float", accent=ACCENT, mono=True)
        col.add_widget(ti)
        return ti

    def make_flip(self, tag):
        def _flip(instance):
            self.toggle_state[tag] = not self.toggle_state[tag]
            instance.set_active(self.toggle_state[tag])
        return _flip

    def diagnose(self, *a):
        self.results_col.clear_widgets()

        def f(ti):
            try:
                return float(ti.text)
            except ValueError:
                return 0.0

        a1, a2, a3, rms = f(self.amp1x), f(self.amp2x), f(self.amp3x), f(self.rms)
        tags = set()
        m = max(a1, a2, a3)
        if m > 0:
            if a1 == m:
                tags.add("v1")
            if a2 >= 0.5 * a1 and a2 > 0:
                tags.add("v2")
            if a3 >= 0.3 * m and a3 > 0:
                tags.add("v3")
        for t, state in self.toggle_state.items():
            if state:
                tags.add(t)

        if rms > 0:
            cls = self.cls_spinner.text
            zone = get_zone(rms, cls)
            label, color, desc = ZONE_INFO[zone]
            sev = T.Card(padding=[T.S4, T.S3], spacing=T.S2)
            sev.add_widget(body_label(
                "[b]ISO 10816-1 severity (Class %s): Zone %s - %s[/b]" % (cls, zone, label),
                color, markup=True, font_size=T.FS_TITLE))
            sev.add_widget(body_label(desc, TEXT_2))
            sev.add_widget(ColorBar(cls, rms))
            sev.add_widget(Widget(size_hint_y=None, height=dp(2)))
            self.results_col.add_widget(sev)

        results = score_faults(tags, "Vibration")
        if not results:
            self.results_col.add_widget(body_label("No vibration pattern matched yet.", MUTED))
            return
        for score, matched, fault in results[:6]:
            self.results_col.add_widget(result_card(score, matched, fault))


class LibraryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True
        root = BoxLayout(orientation="vertical")

        search_row = BoxLayout(size_hint_y=None, height=T.TOUCH + T.S3 * 2,
                               padding=[T.S4, T.S3, T.S4, T.S3], spacing=T.S2)
        self.search = ModernInput(hint_text="Search faults...", multiline=False, accent=ACCENT)
        self.search.ti.bind(text=self.refresh)
        search_row.add_widget(self.search)
        add_btn = RoundedButton(text="+ Add", accent=ACCENT, size_hint_x=None, width=dp(96),
                                height=T.TOUCH)
        add_btn.bind(on_release=lambda *a: self.open_form())
        search_row.add_widget(add_btn)
        root.add_widget(search_row)

        self.scroll = ScrollView()
        self.col = GridLayout(cols=1, size_hint_y=None, spacing=T.S2, padding=[T.S4, 0, T.S4, T.S4])
        self.col.bind(minimum_height=self.col.setter("height"))
        self.scroll.add_widget(self.col)
        root.add_widget(self.scroll)

        self.add_widget(root)
        self.refresh()

    def refresh(self, *a):
        self.col.clear_widgets()
        query = self.search.text.lower().strip()
        for f in FAULTS:
            if query and query not in f["name"].lower():
                continue
            btn = ListRow(f["name"], f["technique"])
            btn.bind(on_release=self.make_open(f))
            self.col.add_widget(btn)

    def make_open(self, fault):
        def _open(*a):
            content = BoxLayout(orientation="vertical", padding=T.S3, spacing=T.S3)
            sc = ScrollView()
            inner = GridLayout(cols=1, size_hint_y=None, spacing=T.S3)
            inner.bind(minimum_height=inner.setter("height"))
            sig_text = ("- " + "\n- ".join(TAGS.get(t, t) for t in fault["tags"])
                        if fault["tags"] else "(custom entry - no auto-match signature)")
            inner.add_widget(body_label("Signature:\n" + sig_text))
            inner.add_widget(body_label("Likely causes:\n- " + "\n- ".join(fault["causes"]), TEXT_2))
            inner.add_widget(body_label("Recommendations:\n" +
                                         "\n".join("%d. %s" % (i + 1, x) for i, x in enumerate(fault["actions"]))))
            sc.add_widget(inner)
            content.add_widget(sc)

            btn_row = BoxLayout(size_hint_y=None, height=T.BUTTON_H, spacing=T.S2)
            edit_btn = RoundedButton(text="Edit", accent=ACCENT)
            close = secondary_button("Close")
            btn_row.add_widget(edit_btn)
            btn_row.add_widget(close)
            content.add_widget(btn_row)

            popup = make_popup(fault["name"], content, (0.92, 0.85))
            close.bind(on_release=popup.dismiss)

            def _edit(*a):
                popup.dismiss()
                self.open_form(fault)
            edit_btn.bind(on_release=_edit)
            popup.open()
        return _open

    def open_form(self, fault=None):
        """Add/Edit form. fault=None means adding a brand-new entry."""
        is_edit = fault is not None
        content = BoxLayout(orientation="vertical", padding=T.S3, spacing=T.S3)
        sc = ScrollView()
        inner = GridLayout(cols=1, size_hint_y=None, spacing=T.S2)
        inner.bind(minimum_height=inner.setter("height"))

        inner.add_widget(field_label("Fault name"))
        name_in = ModernInput(text=fault["name"] if is_edit else "", multiline=False, accent=ACCENT)
        inner.add_widget(name_in)

        inner.add_widget(field_label("Technique"))
        tech_spinner = make_spinner(fault["technique"] if is_edit else "Vibration",
                                    ["Vibration", "Oil", "Thermal", "Electrical"])
        inner.add_widget(tech_spinner)

        inner.add_widget(field_label("Likely causes (one per line)"))
        causes_in = ModernInput(text="\n".join(fault["causes"]) if is_edit else "",
                                 multiline=True, height=dp(112), accent=ACCENT, font_size=T.FS_BODY)
        inner.add_widget(causes_in)

        inner.add_widget(field_label("Recommendations (one per line)"))
        actions_in = ModernInput(text="\n".join(fault["actions"]) if is_edit else "",
                                  multiline=True, height=dp(152), accent=ACCENT, font_size=T.FS_BODY)
        inner.add_widget(actions_in)

        inner.add_widget(field_label("Wizard signature tags (optional)"))
        inner.add_widget(body_label(
            "Check any observations that should auto-match this fault in the Wizard tab. "
            "Leave unchecked and it'll still be searchable in the Library, just won't "
            "auto-suggest.", MUTED))
        existing_tags = set(fault["tags"]) if is_edit else set()
        tag_checks = {}
        for title, tags in TAG_GROUPS:
            inner.add_widget(section_label(title))
            for t in tags:
                cb = TagRow(TAGS[t], active=(t in existing_tags))
                tag_checks[t] = cb
                inner.add_widget(cb)

        if not is_edit:
            inner.add_widget(body_label(
                "New entries are searchable here in the Library either way; checking "
                "signature tags above also lets them auto-suggest in the Wizard.", MUTED))

        sc.add_widget(inner)
        content.add_widget(sc)

        btn_row = BoxLayout(size_hint_y=None, height=T.BUTTON_H, spacing=T.S2)
        save_btn = RoundedButton(text="Save", accent=ACCENT)
        cancel_btn = secondary_button("Cancel")
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        popup = make_popup("Edit fault" if is_edit else "Add new fault", content, (0.92, 0.9))
        cancel_btn.bind(on_release=popup.dismiss)

        def _save(*a):
            name = name_in.text.strip()
            causes = [c.strip() for c in causes_in.text.split("\n") if c.strip()]
            actions = [x.strip() for x in actions_in.text.split("\n") if x.strip()]
            tags = [t for t, cb in tag_checks.items() if cb.active]
            if not name or not causes or not actions:
                return  # required fields missing - leave the form open
            if is_edit:
                save_fault_edit(fault["id"], name, causes, actions, tags=tags)
            else:
                add_custom_fault(name, tech_spinner.text, causes, actions, tags=tags)
            popup.dismiss()
            self.refresh()
        save_btn.bind(on_release=_save)
        popup.open()


class ComponentsScreen(Screen):
    """Machine components -> faults -> signature/causes/recommendations.
    Two-level drill-down: tap a component to see its faults, tap a fault
    for the detail popup (same style as the Library screen's popup)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(self._build_component_list())
        for comp_name, subtitle, faults in COMPONENTS:
            self.sm.add_widget(self._build_fault_list(comp_name, faults))
        self.add_widget(self.sm)

    def _build_component_list(self):
        screen = Screen(name="__components_root")
        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=T.S2, padding=[T.S4, T.S3, T.S4, T.S4],
                        size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))
        col.add_widget(body_label(
            "Reference library organized by machine component - tap one to see its "
            "common faults, signatures, and recommendations.", TEXT_2))
        for comp_name, subtitle, faults in COMPONENTS:
            card = NavCard(comp_name, "%s (%d faults)" % (subtitle, len(faults)), ACCENT)
            card.bind(on_release=lambda inst, n=comp_name: self.open_component(n))
            col.add_widget(card)
        root.add_widget(col)
        screen.add_widget(root)
        return screen

    def _build_fault_list(self, comp_name, faults):
        screen = Screen(name=comp_name)
        root = BoxLayout(orientation="vertical")

        bar = BoxLayout(size_hint_y=None, height=T.TOUCH + T.S2 * 2,
                        padding=[T.S4, T.S2], spacing=T.S3)
        back_btn = secondary_button("< Components", height=T.TOUCH, size_hint_x=None, width=dp(148))
        back_btn.label.font_size = T.FS_BODY
        back_btn.bind(on_release=lambda *a: self.open_component_list())
        bar.add_widget(back_btn)
        name_lbl = body_label("[b]%s[/b]" % comp_name, TEXT, markup=True, font_size=T.FS_TITLE)
        name_lbl.size_hint_y = 1
        name_lbl.valign = "middle"
        bar.add_widget(name_lbl)
        root.add_widget(bar)

        scroll = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=T.S2, padding=[T.S4, T.S2, T.S4, T.S4],
                        size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))
        for f in faults:
            btn = ListRow(f["name"])
            btn.bind(on_release=self.make_open_fault(f))
            col.add_widget(btn)
        scroll.add_widget(col)
        root.add_widget(scroll)
        screen.add_widget(root)
        return screen

    def make_open_fault(self, fault):
        def _open(*a):
            content = BoxLayout(orientation="vertical", padding=T.S3, spacing=T.S3)
            sc = ScrollView()
            inner = GridLayout(cols=1, size_hint_y=None, spacing=T.S3)
            inner.bind(minimum_height=inner.setter("height"))
            inner.add_widget(body_label("Signature:\n" + fault["signature"]))
            inner.add_widget(body_label("Likely causes:\n- " + "\n- ".join(fault["causes"]), TEXT_2))
            inner.add_widget(body_label("Recommendations:\n" +
                                         "\n".join("%d. %s" % (i + 1, x) for i, x in enumerate(fault["actions"]))))
            sc.add_widget(inner)
            content.add_widget(sc)
            close = secondary_button("Close")
            content.add_widget(close)
            popup = make_popup(fault["name"], content, (0.92, 0.85))
            close.bind(on_release=popup.dismiss)
            popup.open()
        return _open

    def open_component(self, comp_name):
        self.sm.current = comp_name

    def open_component_list(self):
        self.sm.current = "__components_root"


class SeverityScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True
        root = BoxLayout(orientation="vertical")
        scroll = ScrollView()
        col = _page_col()

        col.add_widget(body_label(
            "ISO 10816/20816 velocity severity zones (RMS, mm/s). "
            "A = good, B = acceptable, C = unsatisfactory, D = unacceptable.", TEXT_2))

        col.add_widget(field_label("Overall velocity RMS (mm/s)"))
        self.rms = ModernInput(text="2.8", multiline=False, input_filter="float", accent=ACCENT,
                               mono=True)
        col.add_widget(self.rms)

        col.add_widget(field_label("Machine class"))
        self.cls_spinner = make_spinner("II", list(CLASS_BOUNDARIES.keys()))
        col.add_widget(self.cls_spinner)

        col.add_widget(Widget(size_hint_y=None, height=T.S1))
        btn = RoundedButton(text="Calculate", accent=ACCENT)
        btn.bind(on_release=self.calculate)
        col.add_widget(btn)
        col.add_widget(Widget(size_hint_y=None, height=T.S1))

        self.output = GridLayout(cols=1, size_hint_y=None, spacing=T.S3)
        self.output.bind(minimum_height=self.output.setter("height"))
        col.add_widget(self.output)

        scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)
        self.calculate()

    def calculate(self, *a):
        self.output.clear_widgets()
        try:
            rms = float(self.rms.text)
        except ValueError:
            rms = 0.0
        sel_cls = self.cls_spinner.text
        zone = get_zone(rms, sel_cls)
        label, color, desc = ZONE_INFO[zone]
        res = T.Card(padding=[T.S4, T.S3], spacing=T.S1)
        res.add_widget(body_label("RESULT", MUTED, font_size=T.FS_CAPTION))
        res.add_widget(body_label("[b]Zone %s - %s[/b]" % (zone, label), color, markup=True,
                                  font_size=T.FS_HEADER))
        res.add_widget(body_label(desc, TEXT))
        self.output.add_widget(res)

        for cls in CLASS_BOUNDARIES:
            title, subtitle = CLASS_META[cls]
            hi = (cls == sel_cls)
            card = T.Card(border=ACCENT if hi else None, padding=[T.S4, T.S3], spacing=dp(2))
            card.add_widget(body_label("[b]%s[/b]" % title, ACCENT if hi else TEXT, markup=True,
                                       font_size=T.FS_TITLE))
            card.add_widget(body_label(subtitle, MUTED))
            for z in ["A", "B", "C", "D"]:
                l, c, _ = ZONE_INFO[z]
                card.add_widget(body_label(
                    "%s: %s mm/s (%s)" % (z, zone_range_label(cls, z), l), c, font_name=T.MONO))
            card.add_widget(Widget(size_hint_y=None, height=T.S1))
            card.add_widget(ColorBar(cls, rms if hi else None))
            card.add_widget(Widget(size_hint_y=None, height=T.S1))
            self.output.add_widget(card)

        self.output.add_widget(body_label(
            "Figures are general guidance from ISO 10816-1 (Annex B, machine Classes I-IV). Confirm against the current "
            "standard and any OEM limits before run/stop decisions.", MUTED))


class ReportScreen(Screen):
    SOUND_SOURCES = ["Coupling", "Bearing", "Gearbox", "Motor"]
    EQUIPMENT_TYPES = ["Motor", "Pump", "Fan", "Gearbox", "Blower", "Mill", "Compressor"]

    def __init__(self, **kw):
        super().__init__(**kw)
        self._built = False

    def build(self):
        if self._built:
            return
        self._built = True
        self.selected_faults = []
        self.sound_state = {s: False for s in self.SOUND_SOURCES}
        self.structural_damage = False

        root = BoxLayout(orientation="vertical")
        scroll = ScrollView()
        col = _page_col()

        col.add_widget(field_label("Equipment tag"))
        self.tag = ModernInput(multiline=False, accent=ACCENT)
        col.add_widget(self.tag)

        col.add_widget(field_label("Equipment type"))
        self.eq_type = make_spinner("Motor", self.EQUIPMENT_TYPES)
        col.add_widget(self.eq_type)

        col.add_widget(field_label("Bearing position"))
        self.bearing_pos = ModernInput(text="NDE", multiline=False, accent=ACCENT)
        col.add_widget(self.bearing_pos)

        col.add_widget(field_label("Vibration status"))
        self.vib_status = make_spinner("Within allowable limits", ["Within allowable limits", "High"])
        col.add_widget(self.vib_status)

        col.add_widget(field_label("Overall vibration (mm/s)"))
        self.overall_vib = ModernInput(multiline=False, input_filter="float", accent=ACCENT, mono=True)
        col.add_widget(self.overall_vib)

        col.add_widget(field_label("Dominant frequency (Hz)"))
        self.dom_freq = ModernInput(multiline=False, input_filter="float", accent=ACCENT, mono=True)
        col.add_widget(self.dom_freq)

        col.add_widget(field_label("Order"))
        self.dom_order = make_spinner("1X", ["1X", "2X", "3X", "Non-synchronous"])
        col.add_widget(self.dom_order)

        col.add_widget(field_label("Additional technology note"))
        self.tech_note = ModernInput(multiline=True, height=dp(72), accent=ACCENT, font_size=T.FS_BODY)
        col.add_widget(self.tech_note)

        col.add_widget(section_label("Physical inspection"))
        self.sound_buttons = {}
        for s in self.SOUND_SOURCES:
            b = PillButton("Sound: %s" % s, ACCENT, size_hint_y=None, height=T.TOUCH)
            b.bind(on_release=self.make_sound_flip(s))
            self.sound_buttons[s] = b
            col.add_widget(b)
        self.struct_btn = PillButton("Structural damage at base", ACCENT, size_hint_y=None,
                                     height=T.TOUCH)
        self.struct_btn.bind(on_release=self.flip_structural)
        col.add_widget(self.struct_btn)

        col.add_widget(field_label("Extra note"))
        self.extra_note = ModernInput(multiline=True, height=dp(72), accent=ACCENT, font_size=T.FS_BODY)
        col.add_widget(self.extra_note)

        col.add_widget(section_label("Problem(s) identified - pick up to 2"))
        self.fault_checks = {}
        for f in FAULTS:
            cb = TagRow(f["name"])
            cb.bind(active=self.make_fault_toggle(f["id"]))
            self.fault_checks[f["id"]] = cb
            col.add_widget(cb)

        col.add_widget(Widget(size_hint_y=None, height=T.S2))
        gen_btn = RoundedButton(text="Generate report", accent=ACCENT)
        gen_btn.bind(on_release=self.generate)
        col.add_widget(gen_btn)

        col.add_widget(section_label("Report preview"))
        self.output = ModernInput(text="", readonly=True, multiline=True, height=dp(300),
                                  accent=ACCENT, font_size=T.FS_BODY)
        col.add_widget(self.output)

        copy_btn = secondary_button("Copy report")
        copy_btn.bind(on_release=self.copy_report)
        col.add_widget(copy_btn)

        scroll.add_widget(col)
        root.add_widget(scroll)
        self.add_widget(root)

    def make_sound_flip(self, s):
        def _flip(instance):
            self.sound_state[s] = not self.sound_state[s]
            instance.set_active(self.sound_state[s])
        return _flip

    def flip_structural(self, instance):
        self.structural_damage = not self.structural_damage
        instance.set_active(self.structural_damage)

    def make_fault_toggle(self, fid):
        def _toggle(instance, value):
            if value:
                if len(self.selected_faults) >= 2:
                    instance.active = False
                    return
                self.selected_faults.append(fid)
            else:
                if fid in self.selected_faults:
                    self.selected_faults.remove(fid)
        return _toggle
    def generate(self, *a):
        eq = self.eq_type.text.lower()
        tag = self.tag.text.strip()
        eq_full = ("%s %s" % (tag, eq)).strip() if tag else eq

        lines = ["Observations:"]
        l1 = "The overall vibration amplitude of the %s %s bearing is %s" % (
            self.bearing_pos.text, eq_full, self.vib_status.text.lower())
        if self.overall_vib.text.strip():
            l1 += " at %s mm/s" % self.overall_vib.text.strip()
        l1 += "."
        if self.dom_freq.text.strip():
            l1 += " FFT spectrum indicates major amplitude at %s Hz (%s order)." % (
                self.dom_freq.text.strip(), self.dom_order.text)
        lines.append(l1)

        if self.tech_note.text.strip():
            note = self.tech_note.text.strip()
            lines.append(note if note.endswith(".") else note + ".")

        physical = []
        active_sounds = [s for s, v in self.sound_state.items() if v]
        if active_sounds:
            physical.append("Abnormal sound is observed from the %s." % "/".join(active_sounds).lower())
        if self.structural_damage:
            physical.append("Structural damage found at the %s base." % eq)
        if physical:
            lines.append(" ".join(physical))

        if self.extra_note.text.strip():
            note = self.extra_note.text.strip()
            lines.append(note if note.endswith(".") else note + ".")

        lines.append("")
        lines.append("Recommendations:")
        if not self.selected_faults:
            lines.append("(select 1-2 problems above)")
        else:
            for i, fid in enumerate(self.selected_faults):
                fault = next(f for f in FAULTS if f["id"] == fid)
                lines.append("%d. %s" % (i + 1, fault["name"]))
                for act in fault["actions"][:2]:
                    lines.append("   %s" % act)

        self.output.text = "\n".join(lines)
        self.output.ti.cursor = (0, 0)   # show the report from its first line

    def copy_report(self, *a):
        Clipboard.copy(self.output.text)


# ------------------------------------------------------------------
# APP ROOT WITH TOP NAV
# ------------------------------------------------------------------

class MenuScreen(Screen):
    """CM/DX's internal 'home' - lists its five sections as tappable cards,
    matching the top-level Home screen's card style, instead of a cramped
    5-button tab bar."""

    SECTIONS = [
        ("wizard", "Wizard", "Guided checklist - check observations, get ranked fault matches"),
        ("spectrum", "Spectrum", "Enter 1x/2x/3x amplitudes for a quick automatic read"),
        ("library", "Library", "Browse, search, add, and edit fault reference entries"),
        ("components", "Components", "Browse machine components, then their faults - signature, causes & fixes"),
        ("severity", "Severity", "ISO 10816-style vibration severity classification"),
        ("report", "Report", "Build a shareable diagnosis report for an asset"),
    ]
    ICONS = {"wizard": "dot", "spectrum": "wave", "library": "book",
             "components": "bearing", "severity": "pulse", "report": "dot"}

    def __init__(self, on_pick, **kwargs):
        super().__init__(name="menu", **kwargs)
        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=T.S2, padding=[T.S4, T.S3, T.S4, T.S4],
                        size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        # only shown when run standalone; main.py's header replaces it
        self.heading = Label(text="[b]CM/DX[/b]  condition monitoring diagnostics", markup=True,
                             color=TEXT, font_size=T.FS_TITLE, size_hint_y=None, height=dp(40))
        col.add_widget(self.heading)

        col.add_widget(section_label("Sections"))
        for name, title, subtitle in self.SECTIONS:
            card = NavCard(title, subtitle, ACCENT, icon=self.ICONS.get(name, "dot"))
            card.bind(on_release=lambda inst, n=name: on_pick(n))
            col.add_widget(card)

        root.add_widget(col)
        self.add_widget(root)

    def _redraw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


class RootWidget(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        with self.canvas.before:
            Color(*BG)
            self._root_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda w, v: setattr(self._root_bg, "pos", v),
                  size=lambda w, v: setattr(self._root_bg, "size", v))

        self._bar = None
        self.sm = ScreenManager(transition=NoTransition())
        self.menu = MenuScreen(on_pick=self.enter)
        self.sm.add_widget(self.menu)
        self.sm.add_widget(WizardScreen(name="wizard"))
        self.sm.add_widget(SpectrumScreen(name="spectrum"))
        self.sm.add_widget(LibraryScreen(name="library"))
        self.sm.add_widget(ComponentsScreen(name="components"))
        self.sm.add_widget(SeverityScreen(name="severity"))
        self.sm.add_widget(ReportScreen(name="report"))

        # subbar is only visible while inside a section (not on the menu);
        # collapsed to zero height/opacity when on the menu itself
        self.subbar = BoxLayout(size_hint_y=None, height=0, opacity=0,
                                 padding=[T.S4, T.S1], spacing=T.S2)
        with self.subbar.canvas.before:
            Color(*BG)
            self._subbar_bg = Rectangle(pos=self.subbar.pos, size=self.subbar.size)
        self.subbar.bind(pos=lambda w, v: setattr(self._subbar_bg, "pos", v),
                          size=lambda w, v: setattr(self._subbar_bg, "size", v))
        back_btn = secondary_button("< CM/DX Menu", height=dp(44))
        back_btn.bind(on_release=lambda *a: self.go_menu())
        self.subbar.add_widget(back_btn)
        self.subbar.disabled = True
        self.add_widget(self.subbar)
        self.add_widget(self.sm)

        footer = Label(text="Built by Gnaneswar", color=MUTED, font_size=T.FS_CAPTION,
                       size_hint_y=None, height=dp(24))
        self.add_widget(footer)

    def enter(self, screen_name):
        try:
            self.sm.get_screen(screen_name).build()
        except Exception:
            import traceback
            self.show_error(traceback.format_exc())
            return
        self.sm.current = screen_name
        if self._bar:
            # the app header shows where you are; its Back returns here
            title = dict((n, t) for n, t, _ in MenuScreen.SECTIONS).get(screen_name, "CM/DX")
            self._bar("CM/DX  >  " + title, "")
        else:
            self.subbar.height = dp(52)
            self.subbar.opacity = 1
            self.subbar.disabled = False

    def go_menu(self):
        self.sm.current = "menu"
        self.subbar.height = 0
        self.subbar.opacity = 0
        self.subbar.disabled = True
        if self._bar:
            self._bar("CM/DX", "Condition monitoring diagnostics")

    def bind_bar(self, set_bar):
        """Called by main.py: use the app's header bar instead of our own
        heading and '< CM/DX Menu' strip."""
        self._bar = set_bar
        # the collapsed strip's button sat invisibly over the header Back
        # button and swallowed taps, so drop the strip entirely here
        if self.subbar.parent is not None:
            self.subbar.parent.remove_widget(self.subbar)
        if self.menu.heading.parent is not None:
            self.menu.heading.parent.remove_widget(self.menu.heading)
        if self.sm.current == "menu":
            self.go_menu()
        else:
            self.enter(self.sm.current)

    def handle_back(self):
        """Called by main.py on the Android hardware back button. Return
        True if handled internally (returned to CM/DX's own menu, or one
        level up within a section that has its own sub-navigation), False
        to let main.py fall back to returning to the app's Home screen."""
        if self.sm.current == "components":
            comp_screen = self.sm.get_screen("components")
            if getattr(comp_screen, "sm", None) is not None and comp_screen.sm.current != "__components_root":
                comp_screen.open_component_list()
                return True
        if self.sm.current != "menu":
            self.go_menu()
            return True
        return False

    def show_error(self, message):
        content = BoxLayout(orientation="vertical", padding=T.S3, spacing=T.S3)
        sc = ScrollView()
        lbl = Label(text=message, color=T.DANGER_TEXT, font_size=T.FS_CAPTION, font_name=T.MONO,
                    size_hint_y=None, halign="left", valign="top")
        lbl.bind(texture_size=lambda inst, val: setattr(lbl, "height", val[1]))
        lbl.bind(width=lambda inst, val: setattr(lbl, "text_size", (val, None)))
        sc.add_widget(lbl)
        content.add_widget(sc)
        close = secondary_button("Close")
        content.add_widget(close)
        popup = make_popup("Error building this tab", content, (0.95, 0.85))
        close.bind(on_release=popup.dismiss)
        popup.open()


import os

class GlobalErrorHandler(ExceptionHandler):
    def __init__(self, root_widget):
        super().__init__()
        self.root_widget = root_widget

    def handle_exception(self, inst):
        import traceback
        msg = "".join(traceback.format_exception(type(inst), inst, inst.__traceback__))
        print(msg)
        try:
            self.root_widget.show_error(msg)
        except Exception:
            pass
        return ExceptionManager.PASS


class CMDXApp(App):
    _icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.exists(_icon_path):
        icon = _icon_path

    def build(self):
        try:
            Window.clearcolor = BG
        except Exception:
            pass
        root = RootWidget()
        ExceptionManager.add_handler(GlobalErrorHandler(root))
        return root


if __name__ == "__main__":
    CMDXApp().run()
