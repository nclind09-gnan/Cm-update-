# CM Toolkit (merged app)

Merges three previously separate Kivy apps into one APK with a top nav bar:

- **CM/DX** (`cmdx_tab.py`) — condition monitoring diagnostics
- **Rotor Balance** (`rotor_tab.py`) — single-plane balancing calculator
- **Bearing Freq** (`bearing_tab.py` + `bearing_data.py`) — bearing defect frequency scope

`main.py` is the only new file with real logic — it's a thin launcher that
instantiates each original app's `App` subclass, grabs its `.build()` root
widget, and drops it into its own `Screen` inside one `ScreenManager`. None
of the three apps' internal code was rewritten; each keeps its own classes,
math, and UI logic completely separate in its own module.

## What changed vs. the original repos
- `rotor_tab.py`: removed one line — a module-level `Window.clearcolor = ...`
  that would have overridden the color of whichever tab loaded last. The
  merged app now sets the window background per-tab from `main.py` on switch.
- Everything else (bearing_tab.py, bearing_data.py, cmdx_tab.py) is byte-for-byte
  the original source, just renamed from `main.py` to `<name>_tab.py`.

## Setting this up as its own GitHub repo
1. Create a new repo (e.g. `CM-Toolkit`) on GitHub.
2. Upload every file in this folder, preserving the `.github/workflows/build.yml` path.
3. Push to `main` — the Action builds a debug APK and uploads it as an artifact
   named `cm-toolkit-apk` (Actions tab → latest run → Artifacts).

## Local sanity check (optional, no Android tooling needed)
```
python3 -c "import ast; [ast.parse(open(f).read()) for f in ['main.py','cmdx_tab.py','rotor_tab.py','bearing_tab.py','bearing_data.py']]"
python3 -c "import bearing_data; print(len(bearing_data.DATA['data']), 'brands loaded')"
```

## If a tab crashes on device
The launcher wraps each tab's build in a try/except, so one broken tab
shows a red error screen with the traceback instead of crashing the whole
app — screenshot that screen and it'll be easy to diagnose.

## Update 2: fault recommendations + editable library
- Added the gearbox recommendations to the **Gear mesh wear or misalignment**
  fault, and the base-rigidity recommendations to the **Structural / bolting
  looseness** fault, in `cmdx_tab.py`'s `BASE_FAULTS` list.
- The CM/DX Library tab now has:
  - **+ Add** button to create a brand-new fault entry (name, technique,
    causes, recommendations).
  - **Edit** button inside each fault's detail popup to change its name,
    causes, or recommendations.
  - Your edits and additions are saved to `cmdx_library_overrides.json` in
    the app's private data folder, so they survive app updates/restarts.
    `BASE_FAULTS` in the code stays untouched — edits are layered on top.
  - Note: newly-added faults are searchable in the Library but won't
    auto-match in the Wizard's spectrum-tag scoring (that requires wiring
    signature tags into the code) — editing an *existing* fault keeps its
    original tags, so its wizard matching still works.

## Update 3: app icon
- Replaced `icon.png` with the new "CM Toolkit" artwork (also used as
  `presplash.png`, shown while Android loads the app, with a matching white
  background via `android.presplash_color` in `buildozer.spec`).
- `main.py`'s `CMToolkitApp` now sets `icon = "icon.png"` so it's used
  consistently as the launcher icon, task icon, and window icon.

## Update 4: home screen + modern UI + presplash caption
- The app now opens on a **Home screen** with three flat, rounded cards
  (CM/DX, Rotor Balance, Bearing Freq) — none of the three tools auto-opens
  on launch anymore. Tap a card to go in; each tool screen has its own
  colored back bar (`< Back`) that returns to Home.
- Restyled with a modern flat-card look: dark navy home screen, rounded
  corners, colored accent stripe + chevron per card, consistent typography.
  This only changes `main.py` (the launcher shell) — nothing inside
  `cmdx_tab.py`, `rotor_tab.py`, or `bearing_tab.py` was touched, so each
  tool's own internal screens/tabs look exactly as they did before.
- `presplash.png` now has "Built by Gnaneswar" baked directly into the
  image (composited with PIL), since Android shows the presplash natively
  before Python/Kivy even starts — it can't render dynamic text at that
  point, so the caption has to be part of the image itself.

## Update 5: Laser Align tab (new)
- Added `laser_tab.py` — a 4th tool, fourth home card, purple accent.
- **Calculator**: enter coupling offset/angularity (horizontal + vertical)
  and foot distances, get front/back foot correction directions and
  magnitudes, plus a Good/Acceptable/Correct-before-running classification
  against a general RPM-based tolerance guideline.
- **Soft Foot**: enter the rise/gap measured at each of the 4 feet when
  its bolt is loosened; flags any foot over ~0.05 mm and suggests a shim
  thickness.
- **Guide**: reference tolerance table plus short explanations of
  offset vs. angularity misalignment and what soft foot is.
- Same pattern as the other three tools: self-contained module, own
  internal tab bar, wired into `main.py`'s home screen and back-bar system
  the same way. Tolerance numbers are general industry rule-of-thumb
  values, not a specific vendor/standard table — worth confirming against
  OEM/coupling tolerances for critical or high-speed machines.

## Update 6: Laser Align wording matched to Easy-Laser convention
- Vertical results now read **Add shim / Remove shim** instead of
  Raise/Lower — same underlying math, clearer field-standard wording.
- Foot labels renamed to **MF1 (near foot) / MF2 (far foot)**, matching
  Easy-Laser's own naming instead of generic "Front/Back foot".
- Results are now shown Vertical first, then Horizontal, matching the
  actual field procedure (shim first, then push sideways).
- Verified the sign/extrapolation math itself was already correct by
  tracing a real example through the formula — the earlier confusion was
  wording, not the calculation.

## Update 7: sensor-to-coupling distance + shim direction fix
- Added a **"Sensor to coupling (mm)"** input (default 100), matching the
  "100" measurement on Easy-Laser's setup diagram. It's added to the
  coupling→MF1 and coupling→MF2 distances before extrapolating, since the
  offset/angularity reading is anchored at the sensor rig, not the
  physical coupling face. Confirmed against 4 real Easy-Laser screenshots
  the user provided — predicted values landed within ~0.03mm of the
  actual MF1/MF2 corrections shown.
- **Flipped the vertical shim direction**: now `+ = Remove shim,
  - = Add shim` (previously the opposite). This was inferred from a
  consistent pattern across those same 4 screenshots (positive value →
  down arrow → remove; negative → up arrow → add), not from an official
  Easy-Laser spec, so it's worth a final sanity check against your own
  readings if anything looks off.
- Horizontal Left/Right direction was left unchanged — there wasn't
  enough evidence in the screenshots to confirm or flip it one way or
  the other.

## Update 8: field names matched to Easy-Laser, formula validated
- Added a **"Sensor to sensor (mm)"** field for reference/record-keeping
  (matches Easy-Laser's own setup screen) - it is *not* used in the
  correction math, since testing showed it isn't needed to reproduce
  Easy-Laser's results.
- Renamed **"Coupling to MF1"** to **"Sensor to nearest foot - MF1 (mm)"**
  to match Easy-Laser's actual field naming. The math is unchanged - this
  distance is still added to "Sensor to coupling" before extrapolating,
  since that combination is what matched real results.
- Validated the full formula (including the Update 7 sensor-to-coupling
  fix and Update 6 shim-direction fix) against **4 independent real
  Easy-Laser datasets** the user provided - predicted MF1/MF2 values
  landed within 0.01-0.02mm of the actual results in every case. This is
  now a well-tested match, not just a one-off check.

## Update 9: custom faults now wire into Wizard scoring
- The Add/Edit fault form in the Library tab (`cmdx_tab.py`) now includes
  the same signature-tag checklist used in the Wizard tab (grouped by
  Vibration/Oil/Thermography/Electrical). Whatever you check gets saved
  with the fault and used by `score_faults()`, so custom or edited faults
  now show up as Wizard suggestions too, not just Library search results.
- Editing an existing base fault now also lets you adjust its tags
  (previously fixed/disabled).
- `save_fault_edit()` and `add_custom_fault()` both take an optional
  `tags` argument now; omitting it keeps the previous behavior unchanged.

## Update 10: modern UI pass across all four tools
- New shared file **`theme.py`** with three reusable widgets: `ModernInput`
  (rounded text fields), `PillButton` (rounded toggle/nav buttons with
  configurable active/inactive fill + text color), and `RoundedButton`
  (rounded full-width action buttons like Diagnose/Calculate/Save).
- **laser_tab.py**: internal nav bar converted to rounded pill tabs, all
  fields converted to `ModernInput`, panels rounded, Calculate/Check
  buttons rounded.
- **bearing_tab.py**: `Card` panels now actually rounded (previously a
  sharp rectangle despite the docstring saying otherwise), all TextInputs
  converted to `ModernInput`, the unit (Hz/CPM/Orders) and mode
  (Catalog/Custom/Severity) toggle rows converted from flat `ToggleButton`
  to rounded `PillButton`.
- **rotor_tab.py**: its `Panel` class was already rounded - only
  `LabeledInput`'s field and the Phase Lag/Lead + Compute buttons needed
  converting.
- **cmdx_tab.py** (largest change): main Wizard/Spectrum/Library/Severity/
  Report tab bar converted to rounded pills; Wizard's Diagnose/Clear,
  Spectrum's signature toggles + Diagnose, Library's search/Add/Edit/
  Save/Cancel/Close, Severity's Calculate, and the entire Report screen
  (all text fields, sound/structural toggles, Generate/Copy buttons, and
  the report preview box) all converted.
- `ModernInput` exposes a `.text` property so every existing
  `self.some_field.text` read/write in each file's logic kept working
  unchanged - only the field-construction call sites changed, not the
  domain logic that reads/writes them.
- `theme.py` is imported by all four tool modules, so make sure it's
  included alongside them in your repo/CI.

## Update 11: CM/DX menu navigation + Android hardware back button
- **CM/DX's persistent 5-tab bar (Wizard/Spectrum/Library/Severity/Report)
  is gone.** Opening CM/DX now shows a `MenuScreen` with the same
  card-style layout as the app's top-level Home screen - tap one to open
  it full-screen with a slim "‹ CM/DX Menu" bar at the top to go back.
  This was a cramped 5-way tab row before; now it's one-at-a-time like
  every other navigation level in the app.
- **Hardware/gesture Android back button now works inside the app**
  instead of closing it immediately. `main.py` binds to `Window.on_keyboard`
  and intercepts keycode 27: while inside any tool, back first asks that
  tool if it has its own internal place to go back to (CM/DX: a section →
  its own menu; Bearing Freq: Custom/Severity mode → Catalog; Laser Align:
  Soft Foot/Guide → Calculator) via a shared `handle_back()` method each
  tool's root widget now exposes. If the tool has nothing more to unwind,
  back returns to the app's main Home screen. Pressing back while already
  on Home is left unhandled so Android closes/backgrounds the app normally
  - only one level of "trap" was added, not a full back-stack, to keep
  this predictable.
- Rotor Balance has no internal sub-navigation, so its `handle_back()`
  is effectively a no-op (falls through to Home) - nothing to add there.
- `theme.py` gained a new **`NavCard`** widget (rounded card + accent
  stripe + chevron), which both the Home screen and CM/DX's new
  `MenuScreen` now share - `main.py`'s previously-duplicated `Card` class
  was removed in favor of this one shared implementation.

## Update 12: Components tab (new)
- Added a new **Components** section in CM/DX's menu, right below Library
  - matches the "menu → tap → back bar" navigation pattern from Update 11.
- New file **`component_data.py`** with 14 machine components and 65 total
  faults, each with a signature, likely causes, and recommendations:
  Rotor/Unbalance, Shaft Alignment, Rolling Element Bearings, Journal
  (Sleeve) Bearings, Looseness, Resonance, Rotor Rub, Eccentricity,
  Pumps/Fans/Compressors, Induction Motors, Synchronous & DC Motors,
  Gearbox, Couplings, Belt Drives.
- Content is based on the "Analysis Definitions" section of the Mobius
  Institute Vibration Analysis Handbook (a different, more detailed part
  of the book than the A-Z dictionary section used earlier for the base
  fault library) - signatures and causes are paraphrased from the book's
  diagnostic descriptions, not quoted. The book itself is diagnostic
  (how to *recognize* a fault from vibration data), not prescriptive, so
  the recommendation bullets are written from standard field-maintenance
  practice rather than lifted from the source.
- Navigation: Components → tap a component card → see its fault list →
  tap a fault for the signature/causes/recommendations popup (same popup
  style as the Library tab). A "‹ Components" bar lets you step back to
  the component list, and the Android hardware back button now also
  understands this extra navigation level (one press: fault list → 
  component list; next press: component list → CM/DX menu).
- This is a separate, deeper reference from the flat Library list built
  earlier - Library stays as-is; Components organizes similar/overlapping
  fault knowledge by machine part instead, since that's how the user
  wanted to browse it.

## Update 13: recommendations cross-checked against report template PDF
- Compared the new "Harsha Observations & Recommendations" PDF (a report
  template with example recommendations per fault type) against everything
  already in the app. Most examples (Fan Unbalance, Gearbox, Pump
  Cavitation, Motor Soft Foot, Bearing Defects/Clearances, Structural/Base
  Rigidity) were already present near-verbatim from earlier updates - no
  changes needed there.
- Two genuinely new items were added:
  - **Roots blower lobe clearance** - new fault in both `cmdx_tab.py`
    (BASE_FAULTS, selectable in the Report screen) and `component_data.py`
    (under Pumps, Fans & Compressors).
  - **Pump off-design flow / impeller wear** - same, added to both files -
    distinct from the existing Cavitation fault (that one's about NPSH/
    suction; this one's about operating flow range and impeller wear/
    clearance from the casing).
- The PDF's "Report Process" structure (Motor status → component status →
  additional technologies → physical inspection → 1-2 recommendations for
  different problems) already matches how the Report screen is built, so
  no structural changes were needed there.
