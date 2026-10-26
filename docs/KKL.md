# KKL 409.1 cable (FTDI) with Roots Auto Doctor

An independent diagnostic path with no proprietary software: a **KKL 409.1** cable with an **FTDI** chip
(or CH340) shows up as a normal COM port and Roots Auto Doctor talks to the K-line directly
(KW1281 and KWP2000). It is the recommended way to validate real readings on VAG cars up to ~2005.

## What is already implemented (audited on 2026-10-21)

Audit of the full path in the code, not in the README:

| Stage | Where | Status |
|---|---|---|
| COM port + chip detection (FTDI/CH340) and Latency Timer | `rad/cable.py`, `rad/kline.py:list_serial_ports` | Implemented |
| Opening/closing the serial port, baud rate, BREAK, DTR/RTS, timeouts | `rad/kline.py` (pyserial) | Implemented |
| 5-baud init (absolute timing with BREAK), echo detection, DTR/RTS search | `rad/kline.py:_five_baud_init`, `find_lines` | Implemented |
| Port errors → a specific message (not a generic "Connection error") | `rad/kline.py` → `KLineError`/`InterfaceError` | Implemented |
| Connection states (no interface / inaccessible / open with no ECU / connected / error) | `rad/connstate.py` + `rad/worker.py` | Implemented |
| KW1281: identification, faults, groups, basic settings, adaptation, login, coding, output tests | `rad/protocols/kw1281.py` | Implemented |
| KWP2000 (K-line and J2534): identification, faults, groups | `rad/protocols/kwp2000.py` | Implemented (read-only) |
| KWP2000 writing (adaptation, coding, login, outputs) | `rad/protocols/kwp2000.py` | **Not implemented** (`NotSupported`) — by design |
| Communication outside the UI (thread), keep-alive, disconnections, forced close | `rad/worker.py` | Implemented |

**Audit conclusion:** KKL support is complete at code level and tested against the simulator and against a
**real ECU response** (see below). Only the physical validation on a car with the KKL cable is missing — which
needs the hardware.

## Evidence from real data (no car)

`tests/test_capture_replay.py` uses the plain KW1281 response from an **Audi A3 8L 1.9 TDI** ("EDC SG 1536"),
recorded with USBPcap on 21/10/2026. VCDS showed 5 faults at the same moment; Roots Auto Doctor's
`read_faults()`, on the same bytes, returns exactly the same ones:

| ECU bytes | Roots Auto Doctor | VCDS (photo) |
|---|---|---|
| `44 90 A3` | 17552 · 35 · intermittent | 17552 P1144 35-10 |
| `46 8E A3` | 18062 · 35 · intermittent | 18062 P1654 35-10 |
| `46 7B A3` | 18043 · 35 · intermittent | 18043 P1635 35-10 |
| `46 7C 23` | 18044 · 35 · static | 18044 P1636 35-00 |
| `46 7D A3` | 18045 · 35 · intermittent | 18045 P1637 35-10 |

These bytes are the ECU's own response (KW1281 block 0xFC), the same a KKL cable delivers. They contain nothing
from the HEX cable's proprietary protocol. When replayed by the emulator the source is always labelled
**simulation** — never presented as a live reading.

## On-car validation (once you have the KKL cable)

1. Plug the cable into a USB port. In **Options → Detect cable**, check that it shows up as a COM port
   (FTDI/CH340). For FTDI, set the Latency Timer to 1 ms (Device Manager → Ports (COM & LPT) → Properties →
   Advanced).
2. In **Options**, pick that port and turn on the **Detailed log** (it keeps every byte for the support package).
3. Cable in the OBD socket, **ignition on, engine off**.
4. **Options → Connection check** with address `01`:
   - You should see: cable on the COM port → port open → **K-line echo OK** → connection to 01 → identification.
   - No echo with the ignition on: try Baud rate = 9600 / 10400 in Options; check the OBD socket.
5. **01-Engine → read faults.** On this reference car the 5 faults in the table above should appear.
   Compare with the VCDS photo: the codes and the status (35-10 / 35-00) must be the same.
6. Read the identification (it should contain "EDC" and "1536") and measuring group 001.
7. At the end: **Options → Support package** and save the zip. Send it with the result of each step.

At this stage, read only: do not clear faults or use coding/adaptation until reading is confirmed.

## What still needs validating with hardware

- K-line echo, 5-baud init and KW1281/KWP2000 with a real ECU through the KKL cable (so far only the simulator
  and the recorded response above).
- Rare measuring formulas (`rad/vag_data.py`) and the KWP2000 fault status byte (it uses the KW1281 table;
  confirm on a KWP2000 car with known faults).

## Recommended next task

Get a KKL 409.1 cable with FTDI and run the "On-car validation" section on this Audi A3 8L. With the 5 faults
confirmed by the app, diagnostic reading is proven on real hardware — the step still missing to close Phase 1
and to present the app to workshops.
