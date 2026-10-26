# HEX-USB clone (VID 0403 / PID FA24) with Roots Auto Doctor

## What this cable is (measured on the development PC on 2026-10-19)

| Field | Value | Source |
|---|---|---|
| USB name | `Ross-Tech HEX-USB` (no driver) / `Ross-Tech Direct USB Interface` (with driver) | `Get-PnpDevice` |
| VID / PID | `0403` / `FA24` | HardwareID |
| bcdDevice | `0600` → **FTDI FT232R** chip | HardwareID `REV_0600` |
| Serial number | `RT000001` | InstanceId |
| USB class | `FF/FF/FF` (vendor-specific, typical of FTDI) | CompatibleID |
| Current driver | `RT-USB` service, `oem28.inf`, Ross-Tech 2.10.0.0 (2014), **unsigned** | `Win32_PnPSignedDriver` |
| Driver DLL | `C:\Windows\System32\RT-USB.DLL` — **32-bit**, exports the FTDI D2XX API (`FT_OpenEx`, `FT_SetBaudRate`, `FT_SetBreakOn`…) | PE header + export table |

Despite the "HEX-V2" name, the cable identifies itself as **HEX-USB** (the older product) and is an FT232R with
Ross-Tech's PID. It is not a HEX-V2: no CAN is reachable this way.

**What is inside:** the serial number `RT000001`, the LEDs and PID FA24 are those of the **HEX-USB+CAN** clones:
FT232R → ATmega162 microcontroller → K/CAN transceivers. In **intelligent mode** (the factory mode) the
microcontroller swallows the K-line bytes, so the KKL echo test always fails — this is why the cable never
talked to the car (the readings in the history came from the simulator). The FTDI's DTR is wired to the
microcontroller's RESET: the app works with DTR and RTS off.

The firmware has a **KKL ("dumb") mode** in which the K-line is meant to pass straight through. Roots Auto Doctor
talks to the microcontroller without VCDS (`rad/hexmcu.py`):

| Request | Bytes (PC → cable) | Expected response |
|---|---|---|
| Version | `53 04 02 55` | `4D 07 02 <major> <minor> <type> xx` |
| Start-up mode | `53 04 0D 5A` | `4D 05 0D <mode> xx` (00 KKL, 02 intelligent) |
| Switch to KKL | `53 05 0E 00 58` | `4D 04 FE B7` |
| Restore intelligent | `53 05 0E 02 5A` | `4D 04 FE B7` |

Source: public reverse engineering of VCDS (github.com/guns96x/vcds-android, `docs/research/vcds_fa24_dumb_mode_protocol.md`).
**Confirmed on this cable on 19/10/2026** (real responses: `4D 07 02 01 60 46 6F` = firmware 1.96 'F';
`4D 05 0D 02 47` = intelligent mode). But this firmware's KKL mode does **not** give direct access to the K-line. **Reading ECUs through this cable is not supported by Roots Auto Doctor:** the app only reads the cable's own status (firmware, mode, K-line test). For diagnostics use a KKL 409.1 cable with FTDI — see [KKL.md](KKL.md).

### Next step: USB capture (once, for study only)

1. Install Wireshark with the **USBPcap** component.
2. Open Wireshark, choose the USBPcap interface the cable is on and start capturing.
3. With the cable on the car and the ignition on, in the reference program: Options → Test; then
   01-Engine → Fault codes; close.
4. Stop and save as `captura_hex.pcapng`.
5. Analyse:

```powershell
.venv\Scripts\python.exe tools\hex_capture.py captura_hex.pcapng -o analise_hex.txt
```

`tools/hex_capture.py` keeps only the cable (FTDI), strips the chip's 2 status bytes from each packet, shows the
control requests in order (baud rate, DTR/RTS, BREAK) and the 53/4D packets with the command name, and lists at
the end the opcodes that are not yet implemented.

Roots Auto Doctor does not become dependent on any other program: the capture only serves to learn the bytes
the cable expects.

## How the app talks to it

The FTDI chip behaves like a UART. Roots Auto Doctor uses it like a KKL cable: the same `KLine`
(5-baud init with BREAK, KW1281, KWP2000), only the way of reaching the UART changes.

| Port in the list | Module | Driver needed | Notes |
|---|---|---|---|
| `D2XX:RT000001` | `rad/d2xx.py` + `rad/d2xx_bridge.py` | RT-USB (the one already installed) | `RT-USB.DLL` is 32-bit → the bridge runs on the **portable 32-bit Python shipped with the app** (`runtime/py32`). VCDS keeps working. |
| `FTDI:0403:FA24:RT000001` | `rad/ftdi_direct.py` (pyftdi + libusb) | **WinUSB** (Zadig) | Runs in the app's own process, 1 ms latency. VCDS no longer recognises the cable while it has WinUSB. |

Only standard FTDI chip requests are used (baud rate, 8N1, BREAK, DTR/RTS, latency, purge, read/write).
There are no proprietary Ross-Tech commands, no EEPROM writes and no firmware changes.

## Installation

```powershell
cd $env:USERPROFILE\Desktop\RootsAutoDoctor
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Option A — keep the RT-USB driver (D2XX)

1. Nothing to install: the installer ships the portable 32-bit Python (`runtime\py32`). From source,
   `run.bat` prepares it the first time (or `.venv\Scripts\python.exe tools\get_runtime.py`).
2. Options → **Detect cable** → it should say "ready through the RT-USB driver" and select `D2XX:RT000001`.

If `RT-USB.DLL` is somewhere else: `$env:RAD_D2XX_DLL = "C:\path\RT-USB.DLL"`.

### Option B — WinUSB (direct USB access)

1. Download Zadig from https://zadig.akeo.ie/ (official page).
2. Options → List All Devices → choose **Ross-Tech Direct USB Interface** (USB ID `0403 FA24`).
3. Target driver **WinUSB** → *Replace Driver*.
4. Options → **Detect cable** → it should say "ready through direct USB" and select `FTDI:0403:FA24:RT000001`.

To go back to the Ross-Tech driver: Device Manager → the device → Driver → *Roll Back Driver* (or uninstall
it and plug the cable in again).

### Check the driver

```powershell
Get-PnpDevice -PresentOnly | Where-Object InstanceId -match 'VID_0403&PID_FA24' | Format-List Status,Service,FriendlyName,InstanceId
```

`Service` = `RT-USB` (option A) or `WinUSB` (option B); `Status` = `OK`.

## Hardware tests

The `tools\hex_probe.py` probe runs the steps from the command line and shows everything that happens (its
output is in Portuguese). Steps 3–5 are also in the app under Options → **Connection check**.

| # | Step | Command | Needs a car | Expected result |
|---|---|---|---|---|
| 1 | USB detection | `.venv\Scripts\python.exe tools\hex_probe.py` | no | VID/PID, FT232R chip, driver and proposed port |
| 2 | Open the interface | `... tools\hex_probe.py --port D2XX:RT000001` | no | "aberta em N ms" (opened in N ms) + type/serial read through D2XX |
| 3 | K-line echo | `... --port D2XX:RT000001 --echo` | **yes, ignition ON** | "OK — o cabo vê a linha K" (the cable sees the K-line) |
| 4 | Identification | `... --port D2XX:RT000001 --ecu 01` | yes | protocol, baud rate, part number, coding |
| 5 | Faults + group 1 | (included in step 4) | yes | fault list and the 4 values of group 1 |

Try at least `01` (engine), `17` (instruments) and `03` (ABS). With option B, replace the port with
`FTDI:0403:FA24:RT000001`.

**Step 2b — microcontroller (USB only, no car):** `... tools\hex_probe.py --port D2XX:RT000001 --mcu`
→ it should show the cable microcontroller found at N baud, its firmware and its start-up mode. Keep the
output: it is the first real confirmation of the protocol.

**If step 3 fails with the ignition on** (no echo), the Connection check talks to the microcontroller and puts
it in KKL mode; if the microcontroller does not answer at any baud rate, send the `--mcu` output.

## Verification status

| What | Status |
|---|---|
| USB identification (VID/PID, chip, serial, driver) | **Verified on hardware** |
| Detection in the app (`Detect cable`, `D2XX:RT000001` in the port list) | **Verified on hardware** |
| Opening the chip through D2XX (FT232R, 1 ms latency, driver 2.10.00, library 3.02.07) | **Verified on hardware** |
| BREAK, baud rate change, writing and read timeouts through D2XX | **Verified on hardware** (timings below) |
| Connection check in the app up to the echo step | **Verified on hardware** (no car: "no echo", as expected) |
| 5-baud init through the D2XX bridge (bit timings measured on the real cable, address 01) | **Verified on hardware**: 200.0 ms bits (±0.1 ms), line idle for 363 ms before |
| App with the real cable and no car (1.0.1): Test interface, Connection check, Connect, Auto-Scan | **Verified on hardware**: they fail in 1.4–1.6 s with the echo explanation; closing in the middle of an init takes 0.1 s |
| Opening the chip through WinUSB | Not verified — the current driver is RT-USB |
| Clone microcontroller: version (1.96 'F' at 115200 baud), mode, mode change, K-line test | **Verified on hardware** (19/10, 22:07–22:16) |
| KKL mode gives a direct K-line | **No** — on the car, ignition on, LEDs lit: no echo and no ECU response; cable restored to intelligent mode |
| 5-baud init through the microcontroller (0x84) | Answers with error `FF 03` and flags 00 — request format still to be confirmed |
| K-line echo, 5-baud init, KW1281/KWP2000 with a real ECU | Not verified — needs the car |
| KLine + KW1281 over `FtdiSerial` (5-baud init decoded from the BREAK timings) | Tested with a simulated chip |
| KLine + KW1281/KWP2000 over the D2XX bridge (separate process) | Tested with a simulated backend |

## Checklist for the first test on the car

1. Options → **Detailed log** on (the support package then has every byte).
2. Options → port `D2XX:RT000001` (or **Detect cable**).
3. Cable in the OBD socket, **ignition on** (engine off).
4. Options → **Connection check** with address `01`:
   - ✖ at the "K-line echo" step with the ignition on → the clone has a microcontroller; stop here (there is no
     way to use it as a KKL cable).
   - ✔ echo and ✖ on the connection → try `17` (instruments) and Baud rate = 9600 / 10400 in Options.
5. If the check passes: Auto-Scan, open 01, read faults and measuring values (groups 1 and 3).
6. At the end: Options → **Support package** and save the zip, with the result of each step.

## Timings measured on the D2XX bridge (real cable, no car)

| Operation | Median | Maximum | Limit that matters |
|---|---|---|---|
| Write 1 byte | 0.85 ms | 1.2 ms | the KW1281 complement must arrive in < ~50 ms |
| BREAK on/off | 1.9 ms | 2.3 ms | 200 ms bits of the 5-baud init |
| Read with a 1 / 25 / 60 ms timeout | 1.0 / 25.0 / 60.1 ms | 2 / 26 / 61 ms | init W4: 25–50 ms |
| Purge buffer (FT_Purge) | 12 ms | 12 ms | only used during the 200 ms stop bit |

Without `timeBeginPeriod(1)` in the bridge, timeouts were rounded up to 15.6 ms — fixed.

## DTR / RTS

Some clones power or switch the K-line transceiver through DTR/RTS. If the first echo test fails, the
Connection check and Test interface try the 4 combinations and save the one that gives an echo for that
port (`lines/<port>` in the settings). If none gives an echo with the ignition on, the cable cannot be used as KKL.

## Protocols

| Layer | This cable (if it were "dumb") | Notes |
|---|---|---|
| USB ↔ PC | FTDI (D2XX or WinUSB/libusb) | transport, not a diagnostic protocol |
| K-line, 5-baud init | yes | ISO 9141-2 / ISO 14230 physical layer |
| KW1281 | yes | needs every byte acknowledged — works over a UART, not over J2534 |
| KWP2000 (ISO 14230) over the K-line | yes (read-only in this version: identification, faults, groups) | |
| CAN / ISO-TP (ISO 15765) / UDS (ISO 14229) | **no** | the FT232R has no CAN. Only with a J2534 interface that declares ISO15765 — not implemented in this version |
