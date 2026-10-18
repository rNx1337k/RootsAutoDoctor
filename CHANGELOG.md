# Changelog

All notable changes to Roots Auto Doctor are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

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
