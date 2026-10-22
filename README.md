<p align="center">
  <img src="docs/banner.png" alt="Roots Auto Doctor" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.5.0-4F8DFF?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows-0E1526?style=flat-square&logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.13-0E1526?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/status-beta-E8343A?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/license-proprietary-0E1526?style=flat-square" alt="License">
</p>

<p align="center">
  Workshop diagnostic software: VAG over the K-line, and any make with OBD-II / EOBD.<br>
  Fault codes, live data, adaptations and coding — straight from the ECU.
</p>

---

## Overview

Roots Auto Doctor communicates with VW, Audi, Seat and Škoda control modules using the
**KW1281** and **KWP2000** protocols, through an inexpensive KKL cable or a J2534 interface.
It also reads **any make with OBD-II / EOBD** (petrol from 2001, diesel from 2004 in the EU) through an
**ELM327** adapter, including read-only **UDS** identification on CAN.
It is designed for workshops: scan the car, review the results and hand the customer a report.

## Features

- **Auto-Scan with a vehicle map** showing where each module sits and its status, a vehicle health score and one-click fault clearing
- **Diagnostic assistant** with severity, probable causes and what to check for each fault
- **Visit comparison**: new, resolved and recurring faults since the car's last visit
- **Command palette** (Ctrl+K) to jump anywhere, connect to a module or look up any fault code
- **Fault codes** in VAG 5-digit and OBD-II format, with fault type and status
- **Live data** on gauges and charts, up to three measuring groups at once, with CSV logging
- **Guided tests** for 1.9 TDI engines: injector balance, boost pressure and mass air flow
- **Workshop functions**: basic settings, adaptation, coding, login, output tests and service reset
- **Customer reports** in PDF or web format, branded with your workshop logo, with probable causes
- **Diagnostic history** searchable by plate or customer
- **Cable detection and connection check** to identify drivers, latency and wiring problems
- **OBD-II / EOBD for any make** (ELM327): ECUs, VIN, MIL and readiness monitors, stored / pending /
  permanent faults, clearing with confirmation and re-read, freeze frame, live data limited to the PIDs each ECU
  declares, and read-only UDS identification and fault status on CAN
- **Connection centre** on the home screen showing the real link state: cable seen ≠ interface open ≠ ECU answering
- **Compatibility matrix** (Options → Compatibility, [docs/COBERTURA.md](docs/COBERTURA.md)) with the level of
  evidence for every interface and protocol
- **Built-in simulators** (K-line, J2534, ELM327) to use every feature without a car

## Installation

**Workshop PCs:** run `Setup_RootsAutoDoctor_<version>.exe`. The installer contains everything the app needs
(Python, Qt and the 32/64-bit bridges), so the PC needs **no Python and no internet connection**.

- Supported: **Windows 10 (21H2 or later) and Windows 11, 64-bit**
- Cable drivers are not included: FTDI/CH340 cables need the chip maker's driver (the app's
  **Detect cable** links to the official page)
- Self-test of an installation (no car needed):
  `"C:\Program Files\Roots Auto Doctor\RootsAutoDoctor.exe" --selftest "%USERPROFILE%\Desktop\autoteste.txt"`
- History, logs and the workshop logo are kept in `%APPDATA%\RootsAutoDoctor` (uninstalling keeps them)

To try the app without a car, click **Open simulator** on the home screen.

## Getting started

1. Connect the cable to the OBD port and turn the ignition on.
2. In **Options**, click **Detect cable**, then **Connection check**.
3. Select a module or run an **Auto-Scan**.

## Compatibility

**Vehicles:** VAG models up to around 2005 with a K-line diagnostic port, such as Golf IV, Bora,
Passat B5, Audi A3 8L / A4 B5–B6, Seat Leon 1M and Škoda Octavia I.

**Interfaces:**

| Interface | Support |
|---|---|
| KKL 409.1 / K-line cables (FTDI, CH340) | KW1281 and KWP2000 |
| J2534 PassThru (04.04) | KWP2000 only |
| ELM327 and compatibles (USB / Bluetooth) | OBD-II / EOBD (CAN, ISO 9141-2, ISO 14230-4, SAE J1850) and read-only UDS on CAN — see [docs/OBD.md](docs/OBD.md) |
| HEX-USB / HEX-V2 clones (FTDI, VID 0403 PID FA2x) | Not supported for ECU access: the app only reads the cable's own status (firmware, mode, K-line voltage) — see [docs/HEX_USB.md](docs/HEX_USB.md) |
| Genuine HEX-V2 / HEX-NET, other firmware-based interfaces | Not supported |

Recommended cable: **KKL 409.1 with an FTDI chip** — see [docs/KKL.md](docs/KKL.md) for the on-car validation procedure.

For FTDI cables, setting the latency timer to 1 ms in Device Manager makes live data much faster.

**Protocols:**

| Function | KW1281 | KWP2000 |
|---|:---:|:---:|
| Identification | ✓ | ✓ |
| Read and clear faults (clearing is confirmed by reading the memory again) | ✓ | ✓ |
| Measuring blocks | ✓ | ✓ |
| Basic settings, adaptation, coding (the value the ECU returns is checked) | ✓ | Planned |
| Login (sent; KW1281 does not report whether the code is correct) and output tests | ✓ | Planned |

OBD-II / EOBD and UDS (ELM327): see [docs/OBD.md](docs/OBD.md). The full matrix, with the evidence for each
stage (detection, initialisation, ECU communication, interpretation), is in [docs/COBERTURA.md](docs/COBERTURA.md).
**No interface has yet been confirmed on a vehicle with this app**: K-line fault decoding is validated against a
real ECU response captured over USB; everything else is tested against the simulators.

All functions are tested against the built-in simulator. Results from the simulator are always labelled as
simulated — in the sidebar, the history and the reports. See [docs/AUDITORIA.md](docs/AUDITORIA.md) for what has
and has not been verified on a vehicle.

## Development

Requires **Python 3.13, 64-bit** ([python.org](https://www.python.org/downloads/windows/)) and internet on the
first run.

```bat
git clone https://github.com/rNx1337k/RootsAutoDoctor.git
cd RootsAutoDoctor
run.bat
```

`run.bat` creates a virtual environment, installs the pinned dependencies (`requirements.txt`), prepares the
portable 32/64-bit Python used by the HEX-USB / J2534 bridges (`runtime/`) and starts the app.

| Command | Description |
|---|---|
| `run.bat` | Run the app from source |
| `run_tests.bat` | Run the test suite (simulator-based, no car needed) |
| `build_release.bat` | Build the compiled app, self-test it and create the Windows installer ([Inno Setup 6](https://jrsoftware.org/isdl.php)) |

Logs and crash reports are stored in `%APPDATA%\RootsAutoDoctor\registos`.
See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Status

The project is in **beta**. All features are tested against the simulator and on-vehicle testing
is in progress. To report a problem, attach the file from **Options → Support package**.

## License

Copyright © 2026. All rights reserved. This software is proprietary and may not be copied,
modified or redistributed without written permission.

<sub>VW, Audi, Seat, Škoda and VCDS are trademarks of their respective owners. Roots Auto Doctor is an
independent product and is not affiliated with Volkswagen AG or Ross-Tech LLC.</sub>
