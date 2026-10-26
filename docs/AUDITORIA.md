# Technical audit — Roots Auto Doctor

> **Historical document.** This is the audit of **v1.2.0** (21/10/2026) that started the hardening work. The
> findings below were fixed in v1.3.0 and the code has changed a lot since then. For the current state of
> each interface and protocol see [COVERAGE.md](COVERAGE.md); for later changes see the
> [CHANGELOG](../CHANGELOG.md).

**Date:** 21/10/2026 · **Audited base:** `main` @ `4baa7e7` (v1.2.0), identical to the local copy in
`Desktop\RootsAutoDoctor` (same source code; the local copy only adds scripts and test results with the HEX
cable).

Line references are those of the audited version (before the fixes). Severity: **CRITICAL** (may cause damage or
unintended operations), **HIGH** (major functional failure or misleading information), **MEDIUM**
(reliability, usability), **LOW** (maintenance).

## 1. Inventory

| Area | Files | Lines |
|---|---|---|
| Start-up | `main.py` | 114 |
| Physical layer | `rad/kline.py`, `rad/ftdi_direct.py`, `rad/d2xx.py`, `rad/d2xx_bridge.py`, `rad/hexmcu.py`, `rad/j2534.py`, `rad/j2534_bridge.py`, `rad/cable.py` | ~2,180 |
| Protocols | `rad/protocols/kw1281.py`, `rad/protocols/kwp2000.py`, `rad/session.py` | ~660 |
| Communication thread | `rad/worker.py` | 513 |
| VAG data / assistant | `rad/vag_data.py`, `rad/fault_advice.py`, `rad/guided.py`, `rad/ui_score.py` | ~990 |
| History / reports / logs | `rad/history.py`, `rad/report.py`, `rad/applog.py`, `rad/settings.py`, `rad/selftest.py` | ~530 |
| Simulator | `rad/simulator.py` | 356 |
| Interface | `rad/ui/` (window, 7 pages, widgets, style, palette) | ~4,200 |
| Tests | `tests/` (15 files, 88 tests) | ~2,100 |
| Tools / build | `tools/`, `*.bat`, `installer/RootsAutoDoctor.iss` | — |

Entry points: `main.py` (window; `--selftest` for the self-test), `tools/hex_probe.py`, `tools/hex_capture.py`,
`tools/get_runtime.py`. Flow: UI → `Worker.submit()` → `QThread` → `ECUSession` → `KW1281`/`KWP2000` →
`KLine` (pyserial / D2XX / direct FTDI / simulator) or `J2534Link` (bridge in a separate process) → Qt signals → UI.

**Initial test state**
- On the user's PC (`resultado_testes2.txt`, a slightly earlier version): 80/80.
- In the audit environment (Linux, no PyPI access, therefore no PySide6): 73 OK / 10 failures, all
  environmental (missing PySide6; the self-test needs the Windows `runtime/py32`). With a minimal `QtCore` stub
  outside the project (only to run the Worker logic): 84 OK / 4 failures (3 UI tests that need `QtWidgets` +
  the Windows runtime self-test).

## 2. What is good (kept)

- Solid K-line layer: 5-baud init with BREAK and absolute timing (`kline.py:214-287`), echo detection, init
  cancellation, DTR/RTS search and per-port memory.
- The HEX-USB+CAN clone was handled rigorously: the mode change is only sent after a valid response with a
  checksum (`hexmcu.py:180-196`); the app states clearly that reading ECUs through that cable does not exist yet.
  **The HEX-V2 / HEX-USB+CAN is not presented as working** — correct, and it stays that way.
- D2XX/J2534 bridges in a separate process (32/64-bit), with simulators for tests without hardware.
- The history's `compare()` already only compares modules read in both visits (`history.py:195-207`).
- Robustness tests with fault injection and parser fuzzing.

## 3. Problems found

### HIGH

| # | File:lines | Problem | Status |
|---|---|---|---|
| A1 | `protocols/kw1281.py:227-230` | `adaptation_save` made up a success result (the requested `{"channel", "value"}`) when the ECU only answered ACK; the UI showed "Channel saved with value X" without confirmation. | Fixed |
| A2 | `session.py:144-148`, `ui/main_window.py:521-524` | "Coding accepted by the module" without comparing the coding returned with the one requested. An ECU that refuses returns the identification with the old coding — the app said "accepted". | Fixed |
| A3 | `report.py:27-31`, `ui_score.py:7-8` | The report said "No faults stored in the modules read" and gave a health score even with **0 modules read**, with modules that did not answer, or with an **interrupted** Auto-Scan ("interrupted" never reached the report or the history). | Fixed |
| A4 | `history.py`, `report.py`, `session.py` | Sessions and reports **did not tell the simulator apart from a real interface**. CHANGELOG 1.1.0 itself records that "successful" readings in the history came from the simulator. A report generated in simulation looked like a real diagnosis. | Fixed |

### MEDIUM

| # | File:lines | Problem | Status |
|---|---|---|---|
| M1 | `ui/pages/module.py:152-157` | Service reset: `adaptation_test` and `adaptation_save` were queued together — the **save ran even if the test was refused**. | Fixed (`ECUSession.service_reset`) |
| M2 | `ui/pages/module.py:331, 614-620, 704-707` | Output tests and basic settings started without confirmation; channel 00 (resets **all** adaptations) had the same prompt as any other channel. | Fixed |
| M3 | `ui/main_window.py:525-526`, `kw1281.py:232-235` | "Login accepted": KW1281 only acknowledges receipt (ACK); it does not say whether the code is right. | Fixed ("Login sent…") |
| M4 | `worker.py:99-113` | A refused keep-alive (negative response) did not update `last` → repeated in a tight loop. **Measured: 30 requests in 1.1 s** with a 0.2 s interval (should be ~5), and a traceback per request in `erros.log`. | Fixed + test |
| M5 | `session.py:122-124`, `worker.py:415-437` | Clearing faults: if the request was accepted but the re-read failed, the error looked as if clearing had failed. Real result unknown. | Fixed (`OperationUnconfirmed`, "to be confirmed" state) |
| M6 | `kw1281.py:247-255` | Output tests: an unexpected response was treated as "end of test". | Fixed (explicit error) |
| M7 | `ui/main_window.py:402-407` | Exporting an Auto-Scan report saved a **second session** in the history (the Auto-Scan is already saved when it ends) → duplicates and inflated statistics. | Fixed (`history.update_session`) |
| M8 | `report.py:21`, `ui/main_window.py:409-410` | A report regenerated from the history showed **today's date** instead of the date of the diagnosis. | Fixed |
| M9 | `j2534_bridge.py:115` | `n.value == 0` was checked before the error code: a disconnected J2534 interface / driver error showed as "the module did not answer". | Fixed + test |
| M10 | `j2534.py:137`, `d2xx.py:136` | A non-JSON line from the bridge (e.g. a J2534 DLL writing to stdout) caused a `JSONDecodeError` → "Internal error", and the exchange went out of sync. | Fixed (interface error, bridge closed) + test |
| M11 | `ui/main_window.py:313-315` | "Interface ready: COMx" as soon as the port was chosen, without having talked to anything. | Fixed ("Selected interface") |
| M12 | `ui/pages/home.py:216` | Recent vehicles: "no faults" for sessions where no module was read. | Fixed |

### LOW

| # | File:lines | Problem | Status |
|---|---|---|---|
| B1 | `ui/pages/history.py:147-151` | Plate and descriptions inserted into HTML (rich text) without escaping. | Fixed |
| B2 | `report.py:62`, `ui/pages/common.py:141` | "Probable causes" shown without saying they are a suggestion from the app. | Fixed ("Possible causes — suggested by the app") |
| B3 | `protocols/kw1281.py:11` | Unused `import time`. | Fixed |
| B4 | `worker.py:60-69` | If the thread did not finish within 12 s on close, the window closed with the `QThread` still alive (Qt warns/may abort). Only happens with a blocked driver. | Fixed (`Worker.stop()` force-closes the interface) + test |
| B5 | `j2534.py:125`, `d2xx.py:124` | `readline()` without a timeout: a driver that blocks inside `PassThruReadMsgs`/`FT_Read` blocks the communication thread. | Fixed (`rad/bridge.py`: reader thread and a maximum time per request) + test |
| B6 | `tests/test_usb_transports.py:10` | Unused `import collections`. | Fixed |

### To be verified (needs a car or documentation)

- **KWP2000 — fault status byte** (`kwp2000.py:165`): decoded with the same table as KW1281
  (`vag_data.decode_fault`). On VAG KWP2000 the meaning of the bits may differ; confirm on a car with a KWP2000
  ECU and known faults.
- **KW1281 — login response**: some ECUs answer NAK to a wrong code, others ACK. The app no longer claims it was
  accepted.
- **KW1281 — adaptation save response**: the ECU is assumed to return the saved channel/value in a 0xE6 block
  (as the simulator does). If a real ECU only answers ACK, the app shows "unknown result" and asks to read the
  channel — safe behaviour, but to be confirmed on the car.
- **Measuring formulas** 4/27 (APMS/AAPMS) and other rare ones in `vag_data.py:352-423`: not checked against a
  source; they need a side-by-side reading on a car.

## 4. Protocols — what really works

| Function | KW1281 (KKL cable) | KWP2000 (KKL) | KWP2000 (J2534) |
|---|---|---|---|
| Identification | Implemented; tested on the simulator | Implemented (0x1A 0x9B); simulator | Implemented; J2534 simulator |
| Read faults | Implemented; simulator | Implemented (0x18); simulator | Implemented; J2534 simulator |
| Clear faults | Implemented + confirmation re-read | Implemented (0x14) + re-read | Implemented + re-read |
| Measuring blocks / live data | Implemented (0x29), up to 3 groups | Implemented (0x21) | Implemented |
| Basic settings | Implemented (0x28), with confirmation | Not implemented (`NotSupported`) | Not implemented |
| Adaptation | Read / test / save with verification of the returned value | Not implemented | Not implemented |
| Coding | Implemented with verification of the returned coding | Not implemented | Not implemented |
| Login | Sent; the protocol does not confirm the code | Not implemented | Not implemented |
| Output tests | Implemented, with confirmation | Not implemented | Not implemented |
| Security access (seed/key) | — | Not implemented | Not implemented |
| CAN / UDS | Not implemented | — | — |

**None of these functions was validated on a vehicle in this audit** — all were exercised against the simulator.
The project history had no verified record of a real reading (the cable tested was a HEX-USB+CAN in intelligent
mode; see `docs/HEX_USB.md`).

## 5. Interfaces

| Interface | Real status |
|---|---|
| KKL 409.1 (FTDI/CH340, COM port) | Implemented. No recorded validation on a car. |
| HEX-USB+CAN clone (0403:FA24) via D2XX or WinUSB | The app **talks to the cable's microcontroller** (version, mode, K-line test — verified on the real cable on 19/10/2026). **It does not read ECUs**: the microcontroller's own K-line protocol is missing. Not advertised as working. |
| Genuine HEX-V2 / HEX-NET | Not supported (closed firmware). Detection says so. |
| J2534 04.04 | KWP2000 over ISO 14230 with 5-baud init. KW1281 refused (correct: the standard does not allow per-byte timing). Tested only with the J2534 simulator. |

USB detection ≠ port open ≠ communication with an ECU: the Connection check already separates these steps
(`worker.py:308-382`) and the home page no longer says "ready" just because a port was chosen.

## 6. Next recommendations (not implemented in this round)

1. **On-car validation** (top priority): a KKL 409.1 cable with FTDI, on a Golf IV TDI: read 01/17/03, measure
   group 001, clear faults. Record the result in the CHANGELOG before announcing compatibility.
2. ~~Read timeout on the bridges (B5) and safe thread shutdown (B4).~~ Done in 1.3.0.
3. Customers/vehicles: the history stores plate/customer/model in every session; a separate vehicles table
   (with VIN and search by VIN) would avoid repeating the data — a simple migration in the same `historico.db`.
4. Two-layer report (technical / customer) from the same data, with a preview.
5. Deeper visual redesign: only once the UI tests run in an environment with PySide6 (in this round interface
   changes were kept minimal because they could not be tested here).
6. CAN/UDS as new protocols next to `protocols/`, with their own adapter — without mixing them with the K-line.

## 7. Readiness for other PCs (21/10/2026)

| # | Problem | Status |
|---|---|---|
| P1 | The executable in `build\main.dist` was from v1.0.2 and had never been checked | `build_release.bat` deletes the previous build and runs `--selftest` on the `.exe`; without an OK it does not create the installer |
| P2 | `run.bat` needs Python and internet | Documented: development only; workshops use the installer (no Python, no internet) |
| P3 | Unpinned dependencies and full PySide6 (+175 MB) | Pinned versions; `PySide6-Essentials`; `requirements-build.txt` |
| P4 | A start-up failure closed the app with no message and no `crash.log` | Fixed + tests (`tests/test_startup.py`) |
| P5 | "Detect cable" froze the window | Runs in the background + test (`tests/test_options_detect.py`) |
| P6 | PowerShell names with accents corrupted | UTF-8 forced + test |

To be validated (at the time): building the 1.3.0 installer and a clean install (Windows Sandbox / VM / another
PC without Python).
