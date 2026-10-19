# Changelog

All notable changes to Roots Auto Doctor are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

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
