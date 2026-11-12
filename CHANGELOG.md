# Changelog

All notable changes to Roots Auto Doctor are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.20.1] — 2026-11-12

### Fixed
- **Auto-Scan**: after **Clear faults in all**, the diagnostic assistant kept showing the fault that had just been
  cleared (`QTreeWidget.clear()` does not emit `itemSelectionChanged`, so the panel was never hidden). Rebuilding
  the list now hides it; covered by `test_clear_all_hides_the_advice_of_the_cleared_fault`.

## [1.20.0] — 2026-11-12
The last screens of the design pass.

### Changed
- **Modules page** (`rad/ui/pages/module_select.py`): instead of a flat grid of 44 identical buttons, modules are
  grouped by car system (engine and transmission; brakes, steering and suspension; safety and access; comfort and
  body; instruments, audio and communication), each with a title and a count. After an Auto-Scan, the modules
  that answered move to the top under **"In this car"**, with their result in colour; that is where the diagnosis
  goes on. The filter works across every section and hides empty ones.
- **Customer report**: the header has the workshop on the left and, on the right, the document title in the brand
  blue, the date and the number plate in large type, over a blue rule; the vehicle details are in two columns; the
  summary is a panel with the health score in large type and colour (green / amber / red) beside the verdict;
  section titles in small capitals; the footer is separated by a line. The preview no longer shows a horizontal
  scroll bar (100 % tables could be 1 px wider than the page).
- **Auto-Scan**: the module tiles above the list were removed — they repeated the vehicle map and the list — so the
  list and the diagnostic assistant below it get the room (before, the assistant was squeezed and long fault names
  were cut). The first fault is selected when the scan ends, so the assistant opens straight away. A
  double-click on a list row opens that module. "Vehicle map" title in normal case.
- **Text size**: the base font went from 10 to 10.5 pt (column titles, labels and tags up by half a point too), to
  read better from inside the car. The "large display" option in Options still scales everything further.

## [1.19.0] — 2026-11-12
Design pass over the other screens, after the new Home page (1.17.0).

### Changed
- **Sidebar**: the "Connected module" item only appears with a module connected, and then says which one
  ("01 · Engine electronics"); before it was always there, greyed out, and looked broken.
- **Module → Information**: below the identification, **"What you can do in this module"** — a card per function
  this module allows (measuring values, basic settings, adaptation, coding, login, outputs, TDI tests, changes),
  each with one line on what it does, that opens its tab. Functions the protocol or the identification do not
  allow are not shown. Replaces the empty half of the page.
- **TDI tests**: the three tests are cards (group and how the test stops), the selected one lit; the first test is
  selected from the start, so the instructions card is never empty and the start button is never greyed out.
- **Options**: every card has a title ("Connection to the car" was missing one) and the same label column, so the
  fields line up from card to card; labels are centred with their field; the PC ID is in a monospace font of normal
  size instead of a huge one.
- **Page titles** without the small cyan label above them (it was on every screen and stopped standing out).
- **Tables, everywhere**: no vertical grid lines, only a thin line between rows; column titles aligned left like the
  content, with a line under the header. Done when each table is created (the stylesheet cannot switch the grid
  off).
- **History**: the most recent diagnosis is selected when the page opens, so the modules and faults list below is
  never empty.

## [1.18.0] — 2026-11-12
### Changed
- **New logo**: the "R" of Roots whose leg is the needle of a rev counter entering the red zone — the brand (R),
  the car (the dial) and the diagnosis (the red zone, where the fault is). It replaces the heartbeat over a gauge,
  a common motif that also blurred at taskbar size. Below 48 px a heavier-stroke variant is used, so the R and the
  red needle still read at 16 px. New program icon (`icon.ico`, 16–256 px), application logo (sidebar, splash
  screen, default report logo) and README banner (the corner decoration was removed: a cleaner banner).
- `tools/make_brand.py` rewritten to use only the program's PySide6 (QtSvg): it no longer needs `rsvg-convert`
  or Pillow. The glow is made by blurring the drawing (scaled down and up) and clipping it to the tile; the `.ico`
  is written with PNG frames.

## [1.17.0] — 2026-11-12
### Changed
- **New Home page** (`rad/ui/pages/home.py`), built for starting work instead of presenting the program:
  - the large banner with the logo and name is gone (both are already in the sidebar); the page starts with a plain
    title and the version;
  - **connection first**: a card with two steps — **Cable** (selected / simulator / not set up) → **Car** (the real
    link state from the communication thread) — the selected equipment and the last communication, and the main
    actions right below: **Start Auto-Scan**, Choose module, OBD — all makes, Test connection; **Open simulator**
    only appears when the simulator is not already in use;
  - **vehicle being diagnosed** in a compact full-width strip, with the number plate large on the left (it is how
    the job starts) and client, make/model, VIN and mileage beside it; a known car is confirmed in green on the
    same line;
  - **latest vehicles** as real rows: number plate, model/client and date, and the result in colour (green no
    faults, amber faults, red five or more);
  - **this month's numbers** in a narrow column beside them instead of four large cards;
  - the four tiles that repeated the sidebar (VAG modules, Auto-Scan, OBD, customer report) and the simulator
    banner were removed.

### Fixed
- On-car validation: the block 001 values are shown with a decimal comma in Portuguese ("3,984 mg/H | 1,400 V"),
  like the rest of the program since 1.16.2.

### Tests
- `test_ui.test_home_leads_with_the_connection_and_shows_recent_cars_in_colour`. Unused English catalogue entries
  of the old Home page removed.

## [1.16.2] — 2026-11-11
Design fixes that make the screens easier to read. Nothing changes in the communication with the car.

### Fixed
- **Decimal comma in Portuguese** (`rad.i18n.decimal`, `rad.vag_data.display_number`): values were shown with a
  decimal point ("1.400 V", "12.4 V"), which in Portugal is the thousands separator — "1.400 V" reads as one thousand
  four hundred volts. On screen and in reports in Portuguese, decimals now use a comma (measuring values, gauges,
  charts and the recordings viewer, OBD live data and battery voltage, and every number formatted inside a
  translated text). Recorded data (CSV, history, recordings) keeps the decimal point, so it is read back unchanged.
- **Gauges**: the scale limits are drawn outside the ends of the arc and no longer overlap the value or the unit; a
  long unit line is shortened with "…" instead of running over the card.
- **Number boxes** (group, channel, value, workshop code): visible up/down arrows instead of two blank blocks, and
  the number is no longer stuck to the left border (Qt ignores the stylesheet padding there; the text margin is now
  set on every number box).
- **Faults**: with few faults the table is only as tall as its rows (four at least) and the diagnostic assistant uses
  the rest of the screen, instead of a large empty area under two rows. The assistant's title no longer touches the
  label above it, and its explanation is in a lighter colour that reads better.
- README screenshots taken again with the current version, in Portuguese and English.

## [1.16.1] — 2026-11-11
Three protections of the PC for the first test on a car. Nothing here changes what is sent to a controller.

### Changed
- **The communication thread is served on time while the window is busy** (`rad.kline._realtime`): with a real
  interface open, Python's thread switch interval goes from 5 ms to 1 ms and is restored when the last port closes.
  KW1281 confirms every byte of the controller with its complement, and while the window draws (e.g. the measuring
  charts) the communication thread waited for the GIL up to the end of the switch interval: measured on Windows with
  another busy Python thread, median 5 ms and up to ~32 ms per wake-up, which adds to the cable latency and could
  drop the session halfway through live measuring. With 1 ms: median 1 ms, worst ~6.5 ms. Simulators are unchanged.

### Added
- **The PC does not go to sleep while it talks to a car** (`rad.power.KeepAwake`): during a command or with a
  session open on a real interface (K-line, J2534, OBD adapter), the communication thread asks Windows not to suspend
  (`SetThreadExecutionState`); the request is released as soon as the session closes and when the thread ends. The
  screen may still turn off. A laptop on battery no longer cuts the cable's USB in the middle of an Auto-Scan.
- **A native crash leaves a trace** (`rad.applog.enable_fault_log`): a failure in the cable driver, Qt or a J2534 DLL
  closed the program without passing through the error handler and left nothing in the logs. `faulthandler` now
  writes the stack of every thread to `crash.log` (included in the support bundle).

### Tests
- New `tests/test_pc_guards.py` (11 tests): switch interval with ports opened and closed in any order, simulator
  unchanged, keep-awake requested/released only on change and released when the thread ends, simulator never blocks
  sleep, and a real native crash in a child process leaves the thread stacks in the log.

## [1.16.0] — 2026-11-09
Prepared for the first test on a car with a KKL cable. Nothing here has been confirmed on a vehicle yet: these are
the timing and robustness points that the simulators cannot show and that decide whether a first session holds.

### Changed
- **KW1281: 55 ms pause before each block the program sends** (`rad.kline.BLOCK_INTERVAL`; it was 3 ms). After its
  last byte an older controller needs time to switch from sending to receiving; with a pause of a few milliseconds
  it misses the first byte of the next block and the session drops. 55 ms is the safe reference value;
  `RAD_KW1281_BLOCK_MS` (10–200) overrides it for tests in technician mode. Simulators and recordings are not paced.
- **COM ports are no longer reprogrammed on every byte** (`rad.kline.SteadySerial`). With pyserial on Windows,
  changing the read timeout re-applies the whole port configuration (speed, format, DTR/RTS), and KW1281 alternates
  three timeouts, so the port was reconfigured twice per byte in the middle of the conversation: extra USB requests
  on every byte, and a risk of lost bytes with drivers that reset the receiver when reconfigured. The port now
  keeps one short OS timeout and the requested time is counted in the program; a read still returns as soon as the
  byte arrives, and a forced close still interrupts it. FTDI direct USB and D2XX ports were not affected.
- **The 5-baud init waits for a quiet K-line** (`KLine._wait_bus_idle`): instead of a fixed 350 ms pause, the
  program reads and drops whatever a controller is still sending and starts the init only after 350 ms of silence
  (3 s at most). On a quiet line it takes exactly as long as before.
- **Echo detection waits up to 200 ms** for the echo of the first byte sent (it was 60 ms). On a slow PC or with a
  high latency timer the echo arrived later, the cable was taken as "no echo" and the echo was then read as the
  controller's first byte. Waiting longer costs nothing: without echo the controller's first byte arrives within
  that time and is kept.
- **A session start that fails once is retried** on a real interface (`Worker._open_session`): when the controller
  answers the init but the identification does not arrive complete, the program waits 1.5 s and tries once more —
  in Connect, Auto-Scan, Connection check, Clear all and the on-car validation. No answer, an interface failure, a
  cancellation and the simulator are never retried, so empty addresses in Auto-Scan take as long as before.
- **The speed a controller answered at is remembered** while the program is open (per interface and address, only
  with the speed on automatic): the next connection starts at that speed, so a 9600-baud instrument cluster no
  longer costs a failed init (about 3 s) every time it is opened again. A remembered speed that turns out wrong
  (another car on the same cable) is corrected by the usual search and forgotten when a session does not start.
- **After a valid sync, only the neighbouring speed is tried** when the session does not start
  (`ECUSession.connect`): a correct sync at 10400 baud can only come from a controller at 10400 or 9600, so the
  other speeds are no longer walked through one by one (3–4 s each) before the error is shown.
- **On-car validation** reads block 001 ten times (it was three) and shows the readings per second, and has a new
  step, **keep the session open**: about 6 s of keep-alives only, then block 001 again — the test that catches a
  session that drops after a few seconds. The report has an **Interface** section (K-line echo, DTR/RTS, pause
  between blocks and, for FTDI COM ports, the latency timer, with what to do when it is still at the factory
  16 ms).
- **Recordings made on a real interface are written to disk byte by byte**, so a recording interrupted by a crash
  or a power cut still has the last bytes exchanged.
- Replaying a recording ignores stale bytes recorded before an init (they are what the bus-idle wait dropped), and
  no longer waits the KW1281 / KWP2000 pauses.

### Tests
- New `tests/test_car_rehearsal.py`: **a dress rehearsal of the on-car test**. A fake COM port behaves like a KKL
  cable on a car at the physical level — the 5-baud address is decoded from the BREAK timings, everything sent
  comes back as echo, the controller accepts the KB2 complement only in time, a KW1281 controller is deaf for
  20 ms after sending a block, a KWP2000 one needs the minimum time before a new request, and a session without
  traffic for 1.5 s is dropped. Over it run the whole on-car validation (engine KW1281 at 10400, cluster KW1281 at
  9600, ABS KWP2000), whose recording is then replayed with the current code, and a session with the communication
  thread running (idle keep-alives, live measuring of two blocks, faults, close). It also shows that with the old
  3 ms pause the same controller drops the session at the first block. About 25 s: the timings are real.
- New `tests/test_car_link.py` (18 tests): port timeouts without reconfiguration, forced close, bus-idle wait,
  late echo, no-echo cable, block pause, session-start retry (Connect and Auto-Scan), remembered speed, replay with
  stale bytes.
- `tests/test_baud_detect.py`: preferred speed, and only the neighbouring speed after a valid sync.
- `tests/captures/simulador_validacao.radrec` recorded again with the new validation steps.

## [1.15.1] — 2026-11-02
### Removed
- The comparison of the on-car validation with another program's scan log and the validation
  `.json` that only existed for it. The validation report lists each fault with the raw status byte and the
  code-type the program shows.

### Changed
- No text, report, document or code comment refers to other diagnostic programs or to the cable manufacturer's
  brand any more. The HEX-USB clone is still detected and supported: the brand Windows puts in its USB name is only
  used to recognise it and is never shown (`rad.cable._plain_name`; new test
  `test_hex_findings_never_show_the_brand_or_another_program`). The KKL cable is called "KKL 409.1".
- Unused English catalogue entries removed.

## [1.15.0] — 2026-11-02
### Added
- On-car validation: comparison with another program's scan log, with the validation data saved as `.json` (removed
  in 1.15.1).
- **K-line speeds 2400 and 1200 baud** in the automatic speed search.

### Changed
- **The wrong-speed byte picks the next speed** (`rad.kline.uart_reads` / `rank_bauds`): after a bad sync, the
  speeds whose 0x55 would be read as exactly that byte (an 8N1 UART model with ±2 % clock and 1/16-bit start
  tolerance) are tried first, so a 4800, 2400 or 1200 baud module answers on the second init instead of the fourth
  or fifth. The other speeds stay in the list in their usual order; a byte that says nothing keeps the old order
  (saved recordings replay unchanged). The simulator now sends the byte a real UART would read.
- **A sync that only looks right does not lose the module**: 9600 and 10400 baud are ~8 % apart, so at the edge of
  UART tolerance one speed's 0x55 can read correctly at the other and only the next bytes come out wrong. If the
  session then does not start (bad block, timeout, unknown keyword), the neighbouring speed is tried after 1 s
  before giving up; the error shown is the one from the start, not "does not answer". Interface errors and a fixed
  speed are never retried.

## [1.14.2] — 2026-11-01
### Fixed
- **Portable update and rollback scripts wait for the program to close on every PC**: they now call `tasklist`,
  `find`, `robocopy`, `ping` and `chcp` by their full path in `%SystemRoot%\System32`. With another tool of the same
  name earlier on the `PATH` (e.g. Git's `find`), the script did not see the program still open and copied over files
  in use straight away. New test: `test_update_scripts_wait_for_the_program_even_with_other_tools_on_the_path`.

## [1.14.1] — 2026-11-01
### Fixed
- **CI no longer fails with every test passing**: `tests/run_all.py` closes the windows and destroys the
  `QApplication` in order before exiting. Before, Python and Windows tore the Qt objects down in any order and the
  process sometimes crashed after the summary (exit code 1 on GitHub, 127/139 on Windows). A `sys.exit()` inside a
  test now counts as a failure instead of stopping the run.

### Changed
- GitHub Actions updated to Node 24 versions: `actions/checkout@v5`, `actions/setup-python@v6`,
  `actions/upload-artifact@v6`.

## [1.14.0] — 2026-11-01
### Added
- **Recordings viewer** (Measuring → **View recordings**, or "Recordings" in the command palette): opens a CSV saved
  with **Record CSV**, plots up to 4 channels at once (each on its own scale), shows min / max / average per channel
  and the values under the mouse, and compares with a second recording (before / after a repair) — the comparison is
  drawn dashed and the table shows the difference of the averages. Channels are paired by group and field
  (`rad/logview.py`, `rad/ui/logviewer.py`).
- **Alerts while reading measuring values** (`rad/live_alerts.py`): on engines with known groups (1.9 TDI EDC15,
  Bosch ME7) the Measuring tab shows a banner as soon as a value leaves the usual range — boost below or above
  specified under load, low air mass, injector deviation at idle, coolant overheating, battery voltage. A condition
  must last 1–3 s before it is shown, so a single spike never raises an alert; the alert goes away when the value
  recovers. Serious alerts (overboost, overheating) are red.
- **Recordings kept with the car** (`rad/recordings.py`): when a Record CSV stops and the plate (or VIN) is filled
  in, a copy goes to `historico/medicao/<plate>/`. **View recordings** then opens the recording already compared
  with the previous visit's recording of the same car and controller; with no recording in this session it opens
  the car's latest one. The open buttons start in the car's folder. The support package does not include these
  copies.
- **Measuring values in the report**: when measuring values were read during the visit, the report has a
  "Measuring values" section with the groups read and the alerts that appeared (or that everything stayed within
  the usual range, on engines the program can assess). The technical report adds min / max / average of each
  channel of the last recording and the average of the previous visit's recording with the difference. The summary
  is saved with the session in the history. Changing controller starts a new summary.

## [1.13.0] — 2026-11-01
### Added
- **Portable version updates itself**: it downloads the signed portable zip (`RootsAutoDoctor_<version>_portatil.zip`
  + `.sig`), checks it, extracts it to a staging folder and, after the program closes, a script backs up the current
  folder, copies the new version over it and restores the backup if the copy fails.
- **What's new before updating**: the update questions show customer-facing notes in the interface language, taken
  from `docs/NOVIDADES.md` (`tools/finish_build.py notes`) and placed between markers in the Release text. Anything
  else in the Release text (notes for the publisher) is never shown.
- **Updates install with nothing to click**: as soon as a new version is downloaded, if the customer has not started
  working yet (no connection, still on the start page, nothing typed, no dialog open), the program shows a notice,
  closes, installs with a progress bar and opens again. Otherwise it installs on close. If a downloaded version was
  left uninstalled (e.g. the PC was switched off), it is installed at the next start, before the window opens
  (first attempt only, so a failing install never traps the customer in a program that keeps closing).
- **Updates are always automatic**: the on/off option is gone; the program checks when it opens and every 6 hours
  while open, retries a failed download on the next check and never repeats the same notice. A portable copy in a
  read-only folder (e.g. Program Files) updates too: the script runs with Windows permission and reopens the program
  as the normal user.
- **Failed update recovery**: on the next start the program says whether the update finished; if not, it keeps
  working on the current version, says so once (permission refused or did not finish) and tries again on close.
  After 3 attempts it stops trying that version and points to a manual install and the support package.
- **Support package**: `LEIA-ME.txt`, safe connection settings, licence state, update state and the last install
  log; chassis numbers and number plates are removed from logs and reports (recordings stay byte-exact for replay).

- **Goes back by itself if a new version does not open**: a version installed by an automatic update that fails
  to start (an error before the window, or two starts in a row that never reach the window) is replaced by the
  previous one, which opens by itself and says so once. The installed version reruns the previous installer (kept
  from the last update or downloaded from its release, signature checked); the portable version copies back the
  backup taken before updating. That version is never installed again on that PC; the next one installs normally.
- **Test versions**: `tools/publicar_release.bat <version> teste` publishes a pre-release that only PCs with
  "Receive test versions" (technician mode) get; `tools/promover_release.bat <version>` then releases it to
  everyone.
- **Withdraw a release**: `tools/retirar_release.bat <version>` turns it back into a draft; copies that downloaded
  it but did not install it discard it.
- **Clean-Windows test before publishing**: `tools/publicar_release.bat` opens the portable version in Windows
  Sandbox, waits for its self-test and does not publish if it fails (`tools/finish_build.py cleanpc`).

### Fixed
- `tools/license_tool.py genkey` and `tools/update_key.py genkey` failed when the key folder was on a different drive
  from the project (e.g. the GitHub Actions runner: project on `D:`, temporary folder on `C:`).

### Changed
- `build_release.bat`, `tools/publicar_release.bat` and `.github/workflows/release.yml` sign the portable zip and
  write the Release text with the customer notes.

## [1.12.1] — 2026-11-01
### Fixed
- **Automatic updates never installed by themselves**: no GitHub Release had been published (only tags), so there
  was no installer or `.sig` to download and the program fell back to "new version available", sending the customer
  to a tag page with nothing to download. Versions are now announced only when a published Release has an
  installer; a tag on its own is ignored. Publishing a Release with the installer and its `.sig`
  (`.github/workflows/release.yml` + `tools/publicar_release.bat`, or by hand) is what turns automatic updates on
### Added
- **Update now**: once the new version is downloaded, the button "Update to version …" offers to install it
  straight away; the program closes, installs silently and opens again (`/RELAUNCH=1`, handled by the installer).
  Closing the program still installs it without reopening

## [1.12.0] — 2026-11-01
### Added
- **KWP2000 basic settings and output tests** (K-line, J2534 and CAN): basic settings enter the group once
  (`31 B8 00 <group>`), poll its values (`31 BA 00 <group>`) and leave it (`32 B8 00 <group>`) when the group changes or
  anything else is requested; output tests step through every output and activate it (`31 B8/B9/BA 01 02`), ending
  at the end-of-list code and closing the routine. The module page now offers every tab on KWP2000 modules
- **Writing over CAN (TP2.0)**: coding, adaptation, security access, basic settings and output tests on VAG modules
  from ~2004, with the same safeguards as the K-line (offered only with the known identification layout, every
  value read back)
- **Release workflow** (`.github/workflows/release.yml`): pushing a `v<version>` tag tests, compiles, self-tests and
  creates a draft GitHub Release with the installer and the portable zip; `tools/publicar_release.bat` signs the
  installer on the publisher's PC and publishes it. `build_release.bat` no longer waits for a key press when `CI` is
  set
- **Code signing** (`tools/finish_build.py codesign`): Authenticode signature of the program and the installer with
  `signtool` when a certificate is configured (`RAD_CODESIGN_PFX` / `RAD_CODESIGN_THUMBPRINT`); skipped with a warning
  otherwise
- `tools/screenshots.py --review`: captures every page and dialog into `build\ui_review\` for a visual review
- Generic fault descriptions P0237, P0238, P0404, P0405, P0406 and P0441 (titles checked against the Delaware DMV
  inspection code list)
### Changed
- VAG fault codes that map to a standard OBD-II code now also use the generic OBD-II description table, so many
  more of them show a description instead of "OBD-II code (see manual)"
- Simulated ABS (K-line) and engine (CAN) support basic settings and output tests; CAN engine has coding, workshop
  code, access code and adaptation channels
### Fixed
- Radio buttons (report version) showed no indicator when not selected
- Auto-Scan summary cut "· SIMULATION" when the panel was narrow (it now wraps)

## [1.11.0] — 2026-11-01
### Added
- **Communication recording** (`rad/capture.py`): Options → Support → *Record communication* writes every byte
  exchanged with the VAG cable or the OBD adapter, every J2534 request, the commands run and a stable summary of
  each result to a `.radrec` file (JSON lines). The support package includes the last three recordings
- **Replay** (`rad/replay.py`, ports `REPLAY:` / `J2534:REPLAY:`): re-runs a recording with the current code and
  reports byte divergences and changed results. `tests/test_captures.py` replays every file in `tests/captures/`,
  so each session recorded on a car becomes a permanent test; five reference recordings from the simulators are
  included. Technician mode: Options → *Check recording…*
- **On-car validation** (technician mode, `rad/validation.py`): cable and ignition, engine (identification,
  faults, block 001 three times, optional clear and re-read), instrument cluster and ABS, always recorded, with an
  HTML report listing each fault's **raw status byte** next to the code-type the program shows (settles the open KWP2000
  status byte question on the first KWP2000 car). Technician mode also shows the raw status byte in the fault list
- **KWP2000 coding, adaptation and security access** on the K-line and through J2534: coding `3B 9A` (keeps the
  module's workshop code and software version), adaptation read/test/save with the `31 B8…BB` routines, security
  access `27 03/04` (key = seed + code), following the EDC16 captures published by kw1281test (MIT). Every write is
  read back before it is reported as saved; offered only when the identification has the known layout. The module
  page enables only the tabs the module supports and shows 7-digit coding for KWP2000. Simulated ABS supports it
- **Raw CAN through J2534** (`J2534CanBus`): with the "OBD adapter" equipment and a J2534 interface, the OBD — all
  makes page (ISO-TP OBD-II/UDS) and VAG modules over CAN (TP2.0) work through the J2534 bridge; the J2534
  simulator imitates both
- **Reports in two versions** with a live preview (`rad/ui/pages/report_dialog.py`): customer (plain language) or
  technical (protocol, baud, coding, workshop code, fault type and raw status, interface); edit the vehicle details
  and notes, then save as PDF or web page, or print. Replaces the two separate questions asked before
- **Vehicle and customer register** (`rad/vehicles.py`, `vehicles` table in `historico.db`): each car once, kept
  up to date by every saved diagnostic (existing history imported on first use). The plate field completes as you
  type and fills the other fields of a known car; a VIN read over OBD finds the car too. History → *Vehicles* tab,
  searchable by plate, VIN, customer or model; history search also finds sessions by VIN
- **GitHub Actions** (`.github/workflows/ci.yml`): Ruff and the full test suite on Windows on every push and pull
  request; README badge
- **Ruff** configuration (`ruff.toml`); the code base passes `ruff check .`
- Tests: `test_captures`, `test_kwp2000_write`, `test_j2534_can`, `test_vehicles`, `test_report_variants`, UI tests
  for recording, validation, the report dialog and the vehicle register
### Changed
- Options: new *Support* card (record communication, support package; technician: on-car validation, check
  recording, logs folder)
- Compatibility matrix and `docs/COBERTURA.md` / `docs/COVERAGE.md`: KWP2000 writing and J2534 raw CAN
### Not yet
- None of the new communication paths has been confirmed on a car: KWP2000 writing, J2534 CAN and the recordings are
  tested with the simulators. Writing over CAN, KWP2000 basic settings and output tests are still not available

## [1.10.1] — 2026-10-31
### Changed
- **New brand**: logo, program icon, splash and README banner redrawn (`tools/make_brand.py` generates every size
  from one SVG); the old `make_logo.py` / `make_banner.py` were removed
- Home screen: more compact shortcut tiles
- README: screenshots section
### Added
- `tools/screenshots.py` / `tools/screenshots.bat`: generate the README screenshots with the simulator in a
  temporary profile (Portuguese and English)

## [1.10.0] — 2026-10-31
### Added
- **VAG over CAN (~2004 to ~2012)** with the OBD adapter (`rad/vagcan/`): VW TP 2.0 transport (channel setup on
  0x200, parameters, segmentation with ACK, channel test, disconnect) carrying KWP2000; identification, fault
  codes (read/clear), measuring blocks and Auto-Scan through the usual Modules and Auto-Scan pages
- ELM327 / OBDLink raw CAN mode (`ATCAF0`, `ATSH`, `ATCRA`, `ATMA`) as a CAN bus for TP2.0
- **VAG CAN simulator** (port "VAG CAN simulator"): engine, ABS/ESP, Climatronic, airbag, instruments and gateway
- Tests: `test_vagcan` (protocol frames, segmentation, absent module, missing ACK, Auto-Scan, ELM raw CAN,
  worker); compatibility matrix entry
### Changed
- With the OBD adapter selected, Modules and Auto-Scan now talk to VAG modules over CAN instead of being refused
- Equipment names in Options: "VAG cable — up to ~2005" and "OBD adapter — VAG from ~2004 and all makes"
### Not yet
- Writing over CAN (coding, adaptation, basic settings) and UDS-only modules (newer VAG); no validation on a car

## [1.9.0] — 2026-10-31
### Changed
- **Customer-facing language everywhere**: screens, dialogs, error messages, cable detection, the connection
  check and the customer report no longer show protocol, chip, driver, baud rate, bridge or port internals
  (KW1281/KWP2000, ELM327, J2534, UDS/ISO/SAE, FTDI/CH340, VID/PID, WinUSB/Zadig, D2XX, latency timer…).
  The equipment is called "VAG cable" or "OBD adapter"; the multi-make page is "OBD — all makes"
- Low-level errors keep their technical detail in the log and the support package; on screen,
  `rad.errors.client_text()` replaces them with a plain explanation of what happened and what to do
- Cable detection shows plain findings (`cable.plain()`): "cable found and ready", "Windows has not prepared it
  yet", "needs to be prepared", "incompatible equipment"
- Port list without VID/PID, driver or serial numbers; the J2534 simulator is only listed in technician mode
- Customer report: no interface/port line and no technical cause for modules without communication
- Options: only equipment, port, Detect cable, Test connection and Connection check; the compatibility matrix,
  speed, K-line echo, OBD protocol, HEX cable mode, detailed log and logs folder moved to technician mode
- README rewritten as a product page for workshops; the technical content moved to `docs/DEVELOPMENT.md`
### Added
- **Automatic updates** (`rad/autoupdate.py`): the installed version downloads a new GitHub release in the
  background, checks the installer's Ed25519 signature (`tools/update_key.py`, `Setup_…exe.sig` created by
  `build_release.bat`) and installs it silently when the program closes; the next start shows "Updated to
  version …". Files that fail the check are deleted; after three failed installs it falls back to the notice.
  Portable and source runs only notify
- Installer installs for the current user by default (no administrator prompt for updates); "all users" is
  still available
- **Technician mode** (`--tecnico` or `RAD_TECNICO=1`): communication log (Ctrl+L), advanced interface options
  and the raw technical messages, for development and support only
- **Portable version**: `build_release.bat` also creates `dist\RootsAutoDoctor_<version>_portatil.zip`
  (extract and run, nothing to install)
- `tools/finish_build.py`: copies any missing Visual C++ runtime DLLs into the build and stops the release if a
  required file is missing (Qt Windows plugin, bridges, portable Python); writes `build\teste_pc_limpo.wsb` to
  test the compiled app in a clean Windows Sandbox
- Self-test also checks the Qt interface and writes a test PDF (what fails first on a clean PC)
- Installer: refuses 32-bit Windows and Windows older than 10 1809 with a clear message; optional official FTDI
  driver added to the Windows driver store so new FTDI cables work on offline PCs without touching cables that
  already work (`installer/drivers/LEIA-ME.txt`); closes the running program during an update
- Tests: `test_build`, plain-language checks for the connection check, cable detection and echo messages

## [1.8.0] — 2026-10-24
### Added
- **English interface** (Options → Display → Language, applied at the next start): every screen, dialog and
  message, VAG module names, VAG and generic OBD-II fault descriptions, fault types, the diagnostic assistant,
  OBD-II parameters and readiness monitors, the compatibility matrix and the customer report. Fault search
  works in both languages. The technical communication log stays in Portuguese
- `rad/i18n.py` (`tr()` / `tr_data()`), English catalogue `rad/i18n_en.py` and `tools/i18n_check.py`; tests check
  that every text is translated, that translations keep the same placeholders and HTML tags, and that every
  `tr()` call passes exactly the values its text uses
- **Per-workshop licence with offline activation** (`rad/licensing.py`): a PC ID in Options → Licence, keys signed
  with Ed25519 (pure-Python implementation in `rad/ed25519.py`, checked against RFC 8032) and an optional expiry
  date. Without a valid licence the app runs in **demo mode**: it reads everything, the simulator has no limits,
  but writing to a real vehicle (coding, adaptation, basic settings, clearing faults, output tests, service reset)
  is refused by the communication thread and reports are marked as demo. A build without a public key
  (`rad/license_pubkey.py`, `PUBLIC_KEY = None`) has licensing switched off
- `tools/license_tool.py` (vendor only): `genkey` creates the key pair (the private key is kept outside the
  repository and is never overwritten), `issue` creates a workshop key and logs it; see `docs/LICENSING.md`
- **Update check** (`rad/updates.py`): at start-up (optional) and with "Check now" in Options, compares the
  installed version with the latest GitHub release (or the highest version tag). It only notifies and opens the
  download page; nothing is installed automatically, and offline PCs are not affected
- Tests: `test_i18n`, `test_licensing`, `test_updates`, plus UI tests for demo mode, the update notice and the
  English interface
### Fixed
- "Most severe fault" and the severity column showed the last word of the severity text; the assistant now
  returns a short severity label (`severity_short`), so "not assessed" shows as "—"
- Customer report: "1 avarias" when exactly one fault was found

## [1.7.0] — 2026-10-24
### Added
- Customer report: **"Interventions on the modules"** section listing the codings and adaptations written during
  the visit (same day, only the modules read in that visit, never mixing simulator and real car), with the
  previous value, the time and whether the module confirmed it. The list is stored with the history session,
  so a report regenerated later shows the same interventions
- Options → **Display**: interface size (100%, 115%, 130%, 150%) so text, buttons and gauges can be read from
  the car. Applied at the next start; a `QT_SCALE_FACTOR` set by the user is respected
- `journal.changes_for_visit()`, `history.update_session(meta=...)` and tests for both
## [1.6.0] — 2026-10-24
### Added
- **Change journal** (`rad/journal.py`, `alteracoes.db` next to the history): every coding and adaptation written
  to a module (including the service reset) is logged with the value it had before, the value the module
  returned, date and whether it came from the simulator. Only writes confirmed by the module or with an unknown
  result are logged; refused writes changed nothing and are not
- Module page: **Changes** tab listing the writes for that module (address + VAG part number), the original coding
  and "Prepare previous value", which fills the coding or adaptation tab with the old value. Nothing is written
  until it is confirmed there, with the workshop code
- Tests: `test_journal`, plus journal coverage in `test_worker_loop` and `test_ui`
### Changed
- Saving an adaptation reads the channel first to record its previous value (except channel 00); a refused read
  does not block the save. The service reset reads channel 02 before testing the value 0

## [1.5.1] — 2026-10-23
### Fixed
- Interface errors (bridges, FTDI/USB, serial port, K-line) now keep the original exception as their cause, so
  crash logs and support packages show the underlying driver/OS error
- ELM327: removed a class attribute `is_can` that was shadowed by the property of the same name

## [1.5.0] — 2026-10-22
### Added
- **OBD-II / EOBD for any make** through an ELM327 adapter (`rad/obd/`): ECUs and supported PIDs, VIN, calibration
  IDs and ECU names, MIL and readiness monitors, stored / pending / permanent faults, clearing (mode 04) with
  explicit confirmation and re-read, freeze frame, and live data limited to the PIDs each ECU declares
- Read-only **UDS** (ISO 14229) on CAN: standard identification DIDs and fault status (0x19 02) with failure type
  byte; "response pending" (NRC 0x78) handled. No security access, writing, routines or programming
- **ISO-TP** (ISO 15765-2) codec and a diagnostic link over a raw CAN bus, ready for raw CAN adapters
- Adapter-independent "link" contract: the OBD-II and UDS services, the session and the UI work with any interface
  that implements `request()`
- OBD-II page: connection steps (port → adapter → protocol → ECUs) showing exactly where it stops, summary (VIN,
  protocol, MIL, ECUs, voltage measured by the adapter), faults with the source of each description, live data
  table and chart, readiness, ECU list and UDS identification; reports and history for OBD sessions
- Options: interface type (KKL/J2534 for VAG or ELM327 for OBD-II) and OBD protocol; "Test interface" with an
  ELM327 checks the adapter only
- Home: connection centre driven by the real link state (`link_state`), OBD-II tile
- Compatibility matrix (`rad/coverage.py`, Options → Compatibility, `docs/COBERTURA.md`) with the evidence level of
  every interface/protocol stage; a test keeps the document in sync and forbids claiming ECU communication on
  hardware without evidence
- Simulated ELM327 (`ELM327:SIMULADOR`) and simulated raw CAN bus, always labelled as simulation
- Self-test (`--selftest`) also checks the OBD-II stack with the simulated ELM327
- Generic DTC descriptions (common SAE J2012 / ISO 15031-6 codes, summarised in Portuguese) with declared source;
  manufacturer codes show only their structural category. More databases can be added as `rad/obd/data/dtc_*.json`
  with a `_source` field
- Tests: `test_obd`, `test_obd_worker`, `test_ui_obd`, `test_coverage`
### Fixed
- D2XX / J2534 bridges: error messages from the bridge process were garbled when the environment set
  `PYTHONIOENCODING` (e.g. "DLL nÃ£o carregou"); both pipes now use UTF-8
- The detailed connection state (`link_state`) was emitted but never shown in the interface
### Changed
- VAG functions (modules, Auto-Scan) explain that a KKL cable or J2534 interface is needed when an ELM327 is selected,
  instead of failing to open the port
- Fault cards and reports no longer repeat the code when the VAG and OBD codes are the same
### Not verified
- No ELM327 or vehicle was available: the OBD-II/UDS stack is tested against the simulators only

## [1.4.0] — 2026-10-21
### Added
- Explicit connection states shared by every interface (`rad/connstate.py`): no interface, interface
  unreachable, interface open without an ECU, connecting, ECU connected, communication error. "ECU connected"
  is only reported after the ECU has answered with its identification — detecting or opening the cable never
  counts as connected
- The communication thread emits the detailed state (`link_state`) and logs every transition with its cause;
  the existing UI state signal is unchanged
- KW1281 fault reading validated against a real ECU response (Audi A3 8L 1.9 TDI, captured with USBPcap): the
  five codes and their intermittent/static status match the reference scan (`tests/test_capture_replay.py`)
- `docs/KKL.md`: audit of the KKL path and the on-car validation procedure
### Changed
- README: HEX-USB/HEX-V2 clones are listed as not supported for ECU access; KKL 409.1 (FTDI) is the
  recommended cable

## [1.3.0] — 2026-10-21
Technical audit: [docs/AUDITORIA.md](docs/AUDITORIA.md).
### Fixed
- Startup: Qt and the main window were imported before error logging was active, so on a PC where Qt fails
  to load the app closed without any message or crash.log. Startup errors are now logged and shown in a
  Windows error box
- "Detect cable" ran PowerShell (up to 20 s) on the UI thread and froze the window; it now runs in the
  background and the button shows "A procurar…"
- Device names from PowerShell with accents (e.g. "Porta série USB") were decoded with the wrong code page
- Adaptation: "saved" was shown even when the ECU only answered ACK (the app made up the result). The value
  the ECU returns is now compared with the one requested: a different value is a rejection, no value is
  "unknown — read the channel to confirm"
- Coding: "accepted by the controller" was shown without checking. The coding in the identification the ECU
  returns must now match the requested one; otherwise the app says it was rejected and shows the real value
- Service reminder reset: the save was queued together with the test and ran even if the test was refused. It is
  now one command that only saves after the cluster confirms the test value
- Login is reported as "sent" (KW1281 only acknowledges receipt; it does not say whether the code is right)
- Clearing faults when the re-read fails is now "not confirmed" instead of a failure
- Customer report: no longer says "no faults" when no controller was read; states controllers that did not
  answer and interrupted (partial) Auto-Scans; no health score without data; uses the session date when
  re-generated from the history; probable causes are labelled as the app's suggestions
- A refused keep-alive was retried in a tight loop (30 requests/s instead of one per interval)
- Exporting the report of an Auto-Scan saved a second copy of the session in the history
- J2534: driver errors (e.g. interface unplugged) were reported as "the controller does not answer"
- D2XX / J2534 bridges: an invalid line from the bridge gave "internal error"; it is now an interface error and
  the bridge is closed
- Output test: an unexpected answer was treated as the end of the test
### Added
- Simulation is always labelled: "MODO DE SIMULAÇÃO" in the sidebar, "(simulação)" on the connection, "Origem"
  column in the history (Simulação / Interface real / — for sessions saved before this version), and a
  "DADOS SIMULADOS" banner on reports
- Sessions store the interface used, whether it was simulated and the Auto-Scan coverage (history migration
  only adds a column; existing sessions are kept)
- Confirmation before output tests, basic settings and adaptation channel 00 (reset all adaptations)
- Simulator scenarios for refused coding/adaptation and ACK-only saves
- Tests: write safety, report honesty, history migration, worker loop, J2534/D2XX bridge errors, startup
  without Qt, background cable detection, PowerShell encoding
### Changed
- Dependencies are pinned to the tested versions (`requirements.txt`) and use `PySide6-Essentials` instead of
  the full `PySide6` (about 175 MB less: WebEngine and Add-ons were never used); build tools are pinned in
  `requirements-build.txt`
- `run.bat` prefers Python 3.13 64-bit, refuses a 32-bit Python, and updates the dependencies when
  `requirements.txt` changes (without internet it keeps the installed ones)
- `build_release.bat` deletes the previous build first, runs `RootsAutoDoctor.exe --selftest` on the compiled
  app and does not create the installer if it fails
- `build_exe.bat` (PyInstaller) is obsolete and now calls `build_release.bat`
- Supported systems documented: Windows 10 (21H2+) / 11, 64-bit; workshops install with the installer
  (no Python or internet needed)
- Accent colour #22D3C9
- Home page says "Interface escolhida" (chosen) instead of "pronta" (ready) until the interface is tested

## [1.2.0] — 2026-10-19
### Added
- `tools/hex_capture.py`: reads a Wireshark/USBPcap capture (.pcapng or .pcap) of an FTDI interface and prints, in order and with timestamps, the FTDI control requests (baud rate, DTR/RTS, BREAK, latency, purge) and the bytes exchanged with the cable, grouped into the HEX microcontroller's 53/4D frames with the command name; ends with the list of opcodes seen, marking those not implemented yet. Standard library only, read-only
- Tests with synthetic USBPcap captures (`tests/test_hex_capture.py`)

## [1.1.0] — 2026-10-19
### Fixed
- The HEX-USB clone (FTDI 0403:FA24, S/N RT000001) never reached the K-line: it is a HEX-USB+CAN clone with an ATmega162 between the FTDI chip and the OBD plug, which in its default "intelligent" mode swallows plain K-line bytes, so the echo test could never pass. All earlier "successful" readings in the history came from the simulator, not from the car
- The app asserted DTR on the HEX clone by default; on these boards DTR drives the microcontroller's RESET, so it was held in reset. HEX ports now run with DTR and RTS off and only try DTR-off combinations
### Added
- `rad/hexmcu.py`: talks to the clone's microcontroller directly: firmware version, boot mode, the cable's own K-line test and the boot-mode switch. The switch is only sent after the cable has answered a mode query with a valid, checksummed frame
- Connection check now reports separate steps: cable seen on USB, interface opened, adapter (microcontroller) answers, K-line seen by the cable, cable mode, K-line echo, ECU connection, fault reading
- Connect / Auto-Scan / Test interface on a HEX port without echo talk to the microcontroller and explain the real cause (adapter answers or not, K-line state seen by the cable, boot mode)
- K-line test done by the cable itself (opcode 0x82, read-only) shown in the connection check
- Options → "Cabo HEX": read the cable mode, restore the original intelligent mode (with confirmation)
- `tools/hex_probe.py`: `--mcu`, `--kline-test` (read-only), `--set-mode kkl|inteligente --yes`, `--no-echo`, `--raw`, `--lines`
- D2XX open failures say whether the cable is not on USB or is open in another program
- Tests with a simulated FT232R + ATmega162 (`tests/test_hexmcu.py`)
### Verified on the real cable (19/10/2026, cable in the car, ignition on)
- The microcontroller answers at 115200 baud: firmware 1.96, type 'F'; version, boot mode, mode switch (ACK `4D 04 FE B7`, persists across power cycles) and K-line test all work with the 53/4D framing
- KKL ("dumb") boot mode does NOT give a transparent K-line on this firmware: no echo and no ECU answer in either mode. The cable was put back in intelligent mode
- Reading ECUs with this cable needs the microcontroller's own K-line protocol (5-baud init opcode 0x84 and the block exchange), which is not implemented yet; the init payload flags are unknown

## [1.0.2] — 2026-10-19
### Fixed
- On another PC the HEX-USB clone (driver RT-USB, 32-bit DLL) asked to install a 32-bit Python. The app now ships the official Python "embeddable" runtime (python.org, 32 and 64 bits, stdlib only) in `runtime/py32` and `runtime/py64`, and the D2XX / J2534 bridges run on it: nothing to install
- Compiled build (Nuitka / PyInstaller): the bridge scripts were not included and a 64-bit J2534 driver tried to start the app's own .exe as the bridge; the bridges, the simulator they use and the runtime are now copied into the build, and a compiled app always uses the bundled runtime
### Added
- `tools/get_runtime.py`: downloads the embeddable zips from python.org, checks the pinned SHA-256 and extracts them to `runtime/`; used by `run.bat` (first start, or when missing), `build_release.bat` and `build_exe.bat`
- `RootsAutoDoctor.exe --selftest [file]`: checks the installation without a car (portable runtimes, J2534 and D2XX bridges with the simulators, and the RT-USB.DLL if the original RT-USB driver is installed) and writes a report (default `%APPDATA%\RootsAutoDoctor\registos\autoteste.txt`)
### Changed
- "Detectar cabo" and the connection error say which program component is missing instead of asking to install Python

## [1.0.1] — 2026-10-19
### Fixed
- Without K-line echo (cable not in the car, ignition off, or a HEX clone with a microcontroller) connecting took 7 s and an Auto-Scan over a minute before saying only "does not respond". Connect and Auto-Scan now check the echo first (0.3–1.5 s) and explain the cause, with the HEX/FTDI microcontroller case named explicitly. Skipped when "Eco da linha K" is set to "Sem eco" and on J2534
- Closing the app during a 5-baud init froze it for ~7 s; the init is now cancellable (0.1 s) and the D2XX bridge process is always closed
- Clicking a module (list, map, tile, palette) while the app was still talking to the car queued extra connections; now refused with a notice
- A connection that failed on the first attempt showed "Ligação ao controlador perdida"
- "Testar interface" on D2XX/FTDI ports gave the generic KKL message instead of the HEX explanation
- `tools/hex_probe.py` crashed on consoles without UTF-8 (cp1252) or when the output was redirected
- Layout at the minimum window size (1080×700): home page and Options overflowed horizontally, the vehicle map legend overlapped the health ring, the module tabs needed scroll arrows, guided tests and basic settings were squashed
- Auto-Scan left an empty tile area above the error message when nothing answered
- Injector balance gauges used the 0–60 mg/H scale, so a ±2 mg/H deviation barely moved the needle; they now use −4…+4
### Changed
- Options: "Detectar cabo", "Testar interface" and "Diagnóstico da ligação" moved into the interface card, under the port
- Module tabs: "Medição", "Saídas", "Testes TDI"
- Fault assistant card hidden when the module has no faults

## [1.0.0] — 2026-10-19
### Added
- **Vehicle map** in Auto-Scan: top view of the car with every control module where it sits; a scan line sweeps the car while it reads, each module lights up green / amber / red and the module being probed pulses. Click a module to connect
- **Diagnostic assistant** (`rad/fault_advice.py`): for each fault, severity (high / medium / low), system, probable causes and what to check, plus a hint from the fault type (open circuit, short to ground, implausible signal...). Shown under the fault list in the module page and in Auto-Scan; severity column in the fault table
- **Visit comparison**: after an Auto-Scan with a plate, the faults are compared with the previous visit of the same car (new / resolved / still present) and new faults are tagged NOVA; "Compare with previous" in History
- **Command palette** (Ctrl+K or the search box in the sidebar): go to any page, connect to any module, start actions, or look up a fault by code (00532, P0299) or description (turbo, abs)
- Customer report shows the severity and the two most likely causes of each fault
- Module list filter (name or address)
- `RAD_SETTINGS_INI` environment variable stores settings in an .ini file instead of the registry (used by the tests)
- Tests: diagnostic assistant, visit comparison, report advice and an end-to-end UI test with the simulator (offscreen)
### Changed
- New "night cockpit" look: deep blue gradients, cyan glow, gradient primary buttons, icon badges and status pills
- Live data gauges redrawn: blue→cyan gradient scale with glow, ticks that light up to the value, tapered needle with smooth animation and a filled history line
- Home page: animated hero banner (perspective road), statistics with icons, action tiles with icons
- Auto-Scan tiles, health ring, ECG connection indicator, charts, toasts (slide-in and fade) and splash screen redesigned
- History of the same plate is found ignoring dashes, spaces and case

## [0.12.0] — 2026-10-19
### Added
- "Connection check" and "Test interface" try the four DTR/RTS combinations when there is no K-line echo and remember the one that works for that port (some clones power or switch the K-line transceiver with these lines)
### Changed
- D2XX bridge requests 1 ms timer resolution (per-process since Windows 10 2004): read timeouts went from ~15.6 ms steps to 1 ms on the real cable
### Removed
- Licence activation: no activation key, licence card, "evaluation version" title or report banner; `rad/license.py`, `rad/ed25519.py`, `tools/keygen.py` and their tests removed (still in git history)

## [0.11.0] — 2026-10-19
### Added
- HEX-USB clone support (FTDI FT232R with PID 0403:FA24) as a K-line cable, through two transports:
  - `D2XX:<serial>` (`rad/d2xx.py`, `rad/d2xx_bridge.py`): uses the D2XX library shipped with the RT-USB driver (32-bit, runs in a bridge process like J2534); the driver stays as it is
  - `FTDI:<vid>:<pid>:<serial>` (`rad/ftdi_direct.py`): direct USB access with the WinUSB driver (Zadig) via pyftdi + libusb, 1 ms latency
- "Detect cable" identifies the FTDI chip from the USB revision and explains what each driver state needs (no driver, RT-USB, WinUSB, missing 32-bit Python or pyftdi) and selects the port
- `tools/hex_probe.py`: command-line probe for hardware tests (USB detection, open, K-line echo, read-only ECU identification, faults and group 1)
- `docs/HEX_USB.md`: driver installation, hardware test plan, supported protocols and verification status
- Tests for both transports without hardware, including 5-baud init decoded from BREAK timing
### Changed
- "Connection check" explains that no echo on a USB-direct/D2XX interface means it has a microcontroller and cannot be used as a KKL cable
- Requirements: `pyftdi`, `libusb-package`
- `build_exe.bat` ships the J2534 and D2XX bridge scripts

## [0.10.0] — 2026-10-19
### Added
- `erros.log`: errors the app recovers from (port, cable, J2534, end of session...) are now logged with their traceback instead of being silently ignored; included in the support package
- Licence expiry uses the latest date the app has seen, so turning the PC clock back no longer extends a time-limited licence
- `tests/run_all.py`: runs every test even when one fails and prints a summary; `run_tests.bat <name>` runs only matching tests
### Changed
- Diagnostic history is stored in SQLite (`historico.db`), so the history list and home statistics no longer open every session file; existing `.json` sessions are imported automatically and moved to `historico/importados`
- Two sessions saved in the same second no longer overwrite each other
- `rad/ui/pages.py` split into one module per page (`rad/ui/pages/`)
- "Detect cable" mentions J2534 interfaces as an alternative for KWP2000 modules when an unsupported interface is found

## [0.9.3] — 2026-10-18
### Changed
- Simplified README with a clearer, more professional structure: overview, features, getting started, compatibility and development

## [0.9.2] — 2026-10-18
### Changed
- Redesigned README: feature grid, hardware table, architecture diagram, roadmap progress and bug report guide

## [0.9.1] — 2026-10-18
### Added
- "Connection check" in Options: opens the interface, checks the K-line echo, connects to a module and reads faults, explaining which step failed and what to do
- "Support package" in Options: zip with recent communication logs, crash log, ports and detected cables (no licences or customer data)
### Changed
- 1 ms Windows timer resolution while a K-line port is open, for more precise 5-baud init and protocol timing
- Fault list no longer shows an empty "—" when a fault has no type text

## [0.9.0] — 2026-10-18
### Added
- J2534 (PassThru 04.04) interface support: installed J2534 interfaces appear in the port list
- KWP2000 over K-line (ISO 14230, 5-baud init) through J2534, with identification, fault codes, clearing and measuring blocks
- Out-of-process J2534 bridge, so 32-bit J2534 drivers work from the 64-bit app (uses a 32-bit Python when the driver needs it)
- Simulated J2534 interface to try the PassThru path without a car
### Notes
- KW1281 controllers cannot be used through J2534 (the standard cannot acknowledge each byte in time); they still need a KKL cable

## [0.8.1] — 2026-10-18
### Added
- "Detect cable" in Options: identifies FTDI / CH340 / PL2303 / CP210x cables, missing drivers, FTDI cables without a COM port (Load VCP), HEX clones that cannot work as KKL cables, and the FTDI latency timer; selects the COM port automatically
- J2534 (PassThru) driver detection in "Detect cable"
- Autocom / Delphi interfaces identified by name in "Detect cable"

## [0.8.0] — 2026-10-18
### Added
- Licensing: per-PC activation with Ed25519-signed keys, evaluation mode with watermarked reports, licence card in Options
- `tools/keygen.py` to issue licence keys (private key kept out of the repository)
- `build_release.bat`: Nuitka compiled build and Inno Setup installer (`installer/RootsAutoDoctor.iss`)
- Third-party licence notices (`LICENSES/THIRD_PARTY.txt`)
- Measuring group labels for Bosch ME7 petrol engines (1.8 20V / 1.8T)
- More VAG P1xxx fault descriptions
### Changed
- `run.bat` starts the app without a console window

## [0.7.0] — 2026-10-18
### Added
- Vehicle health score (0–100) after every Auto-Scan, shown as an animated ring and printed on the customer report
- "Start Auto-Scan" call to action on the home screen
- Hand-drawn line icons in the sidebar navigation
- `.gitignore` for the virtual environment, caches, builds and customer files

## [0.6.0] — 2026-10-18
### Added
- Workshop branding: pick your workshop logo in Options; it appears in the customer report header and the sidebar
- Home dashboard with diagnostics today / this month, faults found this month, vehicles on record and recent vehicles
- Redesigned module information tab: part number, component and coding highlighted, quick actions
- Technical log hidden by default, toggled from the status bar ("Technical log") or Ctrl+L
- Window opens maximised the first time and remembers its size and position
### Fixed
- Keep-alive and live data flooded the communication log (~60 lines/s), making it unreadable and growing the log file on disk; blocks are now only logged with "Detailed log" enabled
- Communication log now keeps following the newest lines
- Redundant "Group A / Group 1" labels on measuring group headers

## [0.5.1] — 2026-10-18
### Added
- GitHub README with banner, feature overview and protocol support table
- This changelog

## [0.5.0] — 2026-10-18
### Added
- Guided tests for 1.9 TDI engines: injector balance (group 013), boost pressure (group 011) and mass air flow (group 003)
- Large live chart with min / max / average (double-click a gauge)
- Peak value marker on the gauges
- Clear fault codes in all modules from the Auto-Scan page
- Service reminder reset for Golf IV / Bora / Passat B5 / Octavia I instrument clusters
- Simulator idle / acceleration cycle and group 013

## [0.4.0] — 2026-10-18
### Added
- Robustness test suite with fault injection and parser fuzzing
- Communication log and crash log saved to `%APPDATA%`
- `run_tests.bat`
### Fixed
- 5-baud init W4 timing could exceed 50 ms with FTDI latency
- Auto-Scan now waits for the ECU to time out after an error
- Auto-Scan text report crashed when the workshop code was missing
- Login code limited to 00000–65535
- CSV logging: file errors handled, field names in the header, groups locked while recording

## [0.3.0] — 2026-10-18
### Added
- Logo v2 and simplified 16–32 px icon
- Field names on the gauges for 1.9 TDI engines
- 30+ VAG fault codes and 40 OBD-II P-codes
- Diagnostic history searchable by plate or customer
- Last Auto-Scan result shown on the module buttons
- Reconnect button and automatic init retry
- Keyboard shortcuts

## [0.2.0] — 2026-10-18
### Added
- Logo, app icon and splash screen
- VAG instrument-cluster theme
- Gauges for measuring blocks
- Auto-Scan tiles
- Customer report in PDF / HTML
- Non-intrusive notifications

## [0.1.0] — 2026-10-18
### Added
- K-line communication with KKL cables: 5-baud init, echo and baud rate detection
- KW1281: identification, coding, fault codes, measuring blocks, basic settings, adaptation, coding, login, output tests
- KWP2000 over K-line: identification, fault codes, measuring blocks
- VAG module, fault code and measuring formula database
- PySide6 interface, ECU simulator and automated tests
