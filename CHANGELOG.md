# Changelog

All notable changes to Roots Auto Doctor are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

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
  five codes and their intermittent/static status match VCDS (`tests/test_capture_replay.py`)
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
- `rad/hexmcu.py`: talks to the clone's microcontroller directly (no VCDS): firmware version, boot mode, the cable's own K-line test and the boot-mode switch. The switch is only sent after the cable has answered a mode query with a valid, checksummed frame
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
- `RootsAutoDoctor.exe --selftest [file]`: checks the installation without a car (portable runtimes, J2534 and D2XX bridges with the simulators, and the RT-USB.DLL if the Ross-Tech driver is installed) and writes a report (default `%APPDATA%\RootsAutoDoctor\registos\autoteste.txt`)
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
- HEX-USB clone support (FTDI FT232R with Ross-Tech PID 0403:FA24) as a K-line cable, through two transports:
  - `D2XX:<serial>` (`rad/d2xx.py`, `rad/d2xx_bridge.py`): uses the D2XX library shipped with the RT-USB driver (32-bit, runs in a bridge process like J2534); VCDS keeps working
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
- "Detect cable" in Options: identifies FTDI / CH340 / PL2303 / CP210x cables, missing drivers, FTDI cables without a COM port (Load VCP), Ross-Tech HEX clones that cannot work as KKL cables, and the FTDI latency timer; selects the COM port automatically
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
