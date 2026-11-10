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
| KWP2000 (K-line and J2534): identification, faults, groups | `rad/protocols/kwp2000.py` | Implemented |
| Speed search (10400 / 9600 / 4800 / 2400 / 1200, next speed picked from the wrong-speed byte) | `rad/session.py`, `rad/kline.py:rank_bauds` | Implemented |
| KWP2000 writing (coding, adaptation, security access, basic settings, outputs) | `rad/protocols/kwp2000.py` | Implemented, simulator only (every write is read back) |
| Communication outside the UI (thread), keep-alive, disconnections, forced close | `rad/worker.py` | Implemented |
| Real-car timing: quiet K-line before an init, 55 ms before each KW1281 block, COM port never reconfigured mid-session, one retry of a failed session start, speed remembered per controller | `rad/kline.py`, `rad/protocols/kw1281.py`, `rad/worker.py` | Implemented (rehearsed over a fake COM port with real timings, `tests/test_car_rehearsal.py`; not yet on a car) |

**Audit conclusion:** KKL support is complete at code level and tested against the simulator and against a
**real ECU response** (see below). Only the physical validation on a car with the KKL cable is missing — which
needs the hardware.

## Evidence from real data (no car)

`tests/test_capture_replay.py` uses the plain KW1281 response from an **Audi A3 8L 1.9 TDI** ("EDC SG 1536"),
recorded with USBPcap on 21/10/2026. The reference scan tool showed 5 faults at the same moment; Roots Auto Doctor's
`read_faults()`, on the same bytes, returns exactly the same ones:

| ECU bytes | Roots Auto Doctor | Reference (photo) |
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

The quickest way is the built-in validation (start the app with `--tecnico`, then **Options → On-car validation**):
it runs the steps below on its own, records every byte and writes a report with the raw status byte of each fault
next to the code-type the program shows. It takes about one minute: cable and ignition; engine — identification,
faults, block 001 ten times (with the readings per second), about 6 s with keep-alives only and block 001 again;
instrument cluster and ABS — identification and faults. The report ends with how the interface was working
(K-line echo, DTR/RTS, pause between blocks, latency timer). Send the `.radrec` recording and the report; the recording then goes into `tests/captures/` as a permanent test. The manual procedure:

1. Plug the cable into a USB port. In **Options → Detect cable**, check that it shows up as a COM port
   (FTDI/CH340). For FTDI, set the Latency Timer to 1 ms (Device Manager → Ports (COM & LPT) → Properties →
   Advanced).
2. In **Options**, pick that port and turn on the **Detailed log** (it keeps every byte for the support package).
3. Cable in the OBD socket, **ignition on, engine off**.
4. **Options → Connection check** with address `01`:
   - You should see: cable on the COM port → port open → **K-line echo OK** → connection to 01 → identification.
   - No echo with the ignition on: try Baud rate = 9600 / 10400 in Options; check the OBD socket.
5. **01-Engine → read faults.** On this reference car the 5 faults in the table above should appear.
   Compare with the table above: the codes and the status (35-10 / 35-00) must be the same.
6. Read the identification (it should contain "EDC" and "1536") and measuring group 001.
7. At the end: **Options → Support package** and save the zip. Send it with the result of each step.

At this stage, read only: do not clear faults or use coding/adaptation until reading is confirmed.

## If the first test does not go well

| What you see | What to try |
|---|---|
| "Cable and ignition" fails | Ignition on (engine off), cable pushed fully into the OBD socket, the right COM port in Options. Without 12 V from the car there is no K-line echo. |
| Engine does not answer, but the cable step passes | Run it again (some ECUs need a few seconds after ignition on). Then **Options → Connection check** with address `17`. |
| The engine identifies, then a step fails with a timeout | Send the recording as it is: it shows the exact byte where it stopped. To try a slower pace, start the app with `RAD_KW1281_BLOCK_MS=80` set; to try the fast pace, `25`. |
| "Keep the session open" fails | The same: recording first, then repeat with `RAD_KW1281_BLOCK_MS=80`. |
| Very few readings per second (below 2) | FTDI latency timer at 16 ms: set it to 1 ms (step 1 of the manual procedure below). |

## What still needs validating with hardware

- K-line echo, 5-baud init and KW1281/KWP2000 with a real ECU through the KKL cable (so far only the simulator
  and the recorded response above).
- Rare measuring formulas (`rad/vag_data.py`) and the KWP2000 fault status byte (it uses the KW1281 table;
  confirm on a KWP2000 car with known faults).

## Recommended next task

Get a KKL 409.1 cable with FTDI and run the "On-car validation" section on this Audi A3 8L. With the 5 faults
confirmed by the app, diagnostic reading is proven on real hardware — the step still missing to close Phase 1
and to present the app to workshops.
