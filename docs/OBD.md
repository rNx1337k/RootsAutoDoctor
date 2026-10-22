# OBD-II / EOBD and UDS (any make)

Since v1.5.0 Roots Auto Doctor reads any vehicle with **OBD-II / EOBD** through an **ELM327** adapter (USB or
Bluetooth, shown as a COM port). It complements the VAG K-line functions (KW1281 / KWP2000), which still need a
KKL 409.1 cable or a J2534 interface.

## Setup

1. **Options → Interface type → "ELM327 adapter — OBD-II / EOBD"**, pick the adapter's COM port, **Save**.
2. Ignition on, engine off. Open **OBD-II** in the sidebar (Ctrl+5) and click **Connect to vehicle**.
3. The connection steps show exactly what was proven: port opened → adapter answered (version, voltage on pin 16)
   → vehicle protocol → OBD ECUs. If it stops, the failed step says why.

No car? **Options → Port → "Simulador ELM327"** (or the command palette: *Abrir simulador OBD-II*). Simulated data
is always labelled (sidebar, page badge, reports; the simulated VIN starts with `RADSML`).

## What it does

| Function | Standard | Notes |
|---|---|---|
| ECUs, supported PIDs | SAE J1979 mode 01 PID 00/20/40… | Only PIDs an ECU declares are ever requested |
| VIN, calibration IDs, ECU name | Mode 09 (02, 04, 0A) | VIN is validated (17 chars, no I/O/Q) and offered to the vehicle form |
| MIL, fault count, readiness monitors | Mode 01 PID 01 | Spark and compression-ignition monitor sets |
| Stored / pending / permanent faults | Modes 03 / 07 / 0A | Per ECU; generic descriptions show their source; manufacturer codes show only their category |
| Clear faults | Mode 04 | Explicit confirmation, then the faults are read again; a refusal (e.g. engine running, NRC 22) is reported, nothing is assumed |
| Freeze frame | Mode 02 | |
| Live data | Mode 01 | Up to 10 parameters, table with min/max and chart; formulas from SAE J1979 |
| UDS identification | ISO 14229 0x22 (F187, F189, F18C, F190, F197, …) | CAN only, read-only |
| UDS faults | ISO 14229 0x19 02 | Failure type byte and status bits decoded |

Deliberately **not** implemented: UDS SecurityAccess, writing data, routines, I/O control, ECU programming and
reset. These change the vehicle and need manufacturer documentation and dedicated safety controls.

## Architecture

```
rad/obd/
  elm327.py     ELM327 adapter (documented AT commands, headers on, ISO-TP reassembly of CAN frames)
  isotp.py      ISO 15765-2 codec + IsoTpLink over a raw CAN bus (Flow Control, STmin, NRC 0x78 pending)
  link.py       common "link" contract (request → [Response]) and negative response codes
  j1979.py      OBD-II services, independent of the adapter
  uds.py        read-only UDS client
  dtc.py        DTC decoding, categories, description sources (extensible with dtc_*.json files that declare "_source")
  pids.py       PID formulas and readiness monitors
  session.py    connection steps, results and report items
  simvehicle.py / sim_elm.py   simulators (tests and demo only)
```

Adding a new interface means implementing one `request()` method: the OBD-II and UDS services, the session, the
worker commands and the UI are reused unchanged. A raw CAN adapter (SLCAN, SocketCAN…) only needs a `CanBus`
driver — ISO-TP is already done and tested.

## Status (see docs/COBERTURA.md)

- Tested against the simulated ELM327 and a simulated raw CAN bus; adapter faults (not an ELM327, adapter stops
  answering, ignition off, low voltage) are covered by tests.
- **Not yet validated with a physical ELM327 or on a vehicle.** Cheap clones may not implement every command:
  optional commands that answer `?` are logged and ignored; essential ones (E0, H1, SP) are required.

## On-vehicle validation (when an ELM327 is available)

1. Options → enable **Detailed log**. Interface type ELM327, choose the port, **Test interface** (adapter only).
2. Ignition on, engine off → OBD-II → **Connect**. Note every step.
3. Read faults and compare with another tool; read VIN; start live data with RPM / coolant / voltage, then start
   the engine and check the values move plausibly.
4. Options → **Support package** and keep the zip. Only after the readings match, record the result in the
   CHANGELOG and raise the levels in `rad/coverage.py`.
