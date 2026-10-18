# Changelog

All notable changes to Roots Auto Doctor are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

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
