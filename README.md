<p align="center">
  <img src="docs/banner.png" alt="Roots Auto Doctor" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.7.0-4F8DFF?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows-0E1526?style=flat-square&logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.10%2B-0E1526?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/UI-PySide6%20%2F%20Qt%206-0E1526?style=flat-square&logo=qt" alt="PySide6">
  <img src="https://img.shields.io/badge/status-beta-E8343A?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/license-proprietary-0E1526?style=flat-square" alt="License">
</p>

<p align="center">
  <b>Read fault codes, live data, adaptations and coding on VAG cars — straight from the ECU, over the K-line.</b>
</p>

---

## Why Roots Auto Doctor

Older VW, Audi, Seat and Škoda models talk to diagnostic tools over the **K-line** using the
same protocols dealer tools have always used: **KW1281** and **KWP2000**. Roots Auto Doctor
speaks those protocols natively through an inexpensive KKL cable, wrapped in an interface built
for the workshop floor — clear gauges, one-click Auto-Scan and a report you can hand to the customer.

## Highlights

| | |
|---|---|
| 🔍 **Auto-Scan** | Scans every common module, shows results as colour-coded tiles and clears faults across all modules in one go |
| ⚠️ **Fault codes** | VAG 5-digit codes with OBD-II P-code equivalent, fault type and intermittent/permanent status |
| 📈 **Live data** | Up to three measuring groups at once on cluster-style gauges with peak markers, live charts and CSV logging |
| 🧪 **Guided tests** | Injector balance, boost pressure and mass air flow checks for 1.9 TDI engines, with a plain-language verdict |
| 🛠️ **Workshop functions** | Basic settings, adaptation (read / test / save), coding, login, output tests and service reminder reset |
| 📄 **Customer reports** | Branded PDF or web report with workshop details, vehicle data, faults per module and technician notes |
| 🗂️ **History** | Every scan and report is saved locally and searchable by plate or customer |
| 🧩 **Simulator** | Built-in virtual ECUs (engine, ABS, cluster) to explore every feature without a car |

## Protocol support

| Feature | KW1281 | KWP2000 (K-line) |
|---|:---:|:---:|
| Identification (part number, component) | ✅ | ✅ |
| Coding / workshop code (read) | ✅ | — |
| Read & clear fault codes | ✅ | ✅ |
| Measuring blocks | ✅ | ✅ |
| Basic settings | ✅ | 🔜 |
| Adaptation | ✅ | 🔜 |
| Coding | ✅ | 🔜 |
| Login | ✅ | 🔜 |
| Output tests | ✅ | 🔜 |

Typical coverage: VAG vehicles up to around 2005 with a K-line diagnostic port — for example
Golf IV, Bora, Passat B5, Audi A3 8L / A4 B5–B6, Seat Leon 1M and Škoda Octavia I.

## Hardware

- **Supported:** "dumb" K-line cables (KKL 409.1 and K-line VCDS clones) with an **FTDI** or **CH340** chip
  that show up as a standard COM port.
- **Not supported:** HEX-USB+CAN / HEX-V2 interfaces (genuine or clone) — their firmware is closed
  and only works with Ross-Tech software.
- **Tip:** on FTDI cables set *Device Manager → Port → Advanced → Latency Timer* to **1 ms** for much faster live data.

## Quick start

```bat
git clone https://github.com/<your-user>/roots-auto-doctor.git
cd roots-auto-doctor
run.bat
```

`run.bat` creates a virtual environment, installs the dependencies (PySide6, pyserial) and starts the app.

1. Plug the cable into the OBD port and turn the **ignition on**.
2. Open **Options**, select the COM port and click **Test interface**.
3. Pick a module (for example **01 Engine**) or run an **Auto-Scan**.

No car nearby? On the home screen click **Open simulator** and try addresses `01`, `03` and `17`.

### Build a Windows executable

```bat
build_exe.bat
```

The app is created in `dist\RootsAutoDoctor\`.

## Testing

```bat
run_tests.bat
```

The test suite runs entirely against the simulator and covers:

- full KW1281 and KWP2000 sessions, including automatic baud rate and echo detection;
- fault injection: line noise, dropped bytes, cables without echo and ECUs dropping out mid-session;
- long live-data sessions and fuzzing of every decoder;
- guided test verdicts and diagnostic history.

Communication logs and crash reports are written to `%APPDATA%\RootsAutoDoctor\registos`.

## Project structure

```
main.py                     application entry point
rad/kline.py                serial port, echo handling, 5-baud init
rad/protocols/kw1281.py     KW1281 block protocol
rad/protocols/kwp2000.py    KWP2000 over K-line
rad/session.py              init, protocol detection and unified ECU API
rad/vag_data.py             modules, fault codes, fault types, measuring formulas
rad/guided.py               guided engine tests
rad/simulator.py            byte-level virtual ECUs
rad/worker.py               background communication thread
rad/ui/                     PySide6 interface
tests/                      automated tests
```

## Roadmap

- [ ] Basic settings, adaptation and coding over KWP2000 (EDC16)
- [ ] Measuring group labels for petrol engines (1.8T, 2.0) and automatic gearboxes
- [ ] Licence activation and compiled builds for distribution
- [ ] CAN / UDS support for newer vehicles

## Status

Roots Auto Doctor is in **beta**. All features are validated against the built-in simulator;
on-vehicle testing is in progress. Bug reports with the communication log attached are very welcome.

## License

Copyright © 2026. All rights reserved. This software is proprietary and may not be copied,
modified or redistributed without written permission.

<sub>VW, Audi, Seat, Škoda and VCDS are trademarks of their respective owners. Roots Auto Doctor is an
independent product and is not affiliated with or endorsed by Volkswagen AG or Ross-Tech LLC.</sub>
