# Development

Technical documentation for Roots Auto Doctor: interfaces, protocols, building and testing. The
[README](../README.md) is the product page for workshops and deliberately leaves all of this out.

## Architecture in one paragraph

Python 3.13 (64-bit) with PySide6 (Qt). All communication with the car runs in a worker thread
(`rad/worker.py`); the UI talks to it through Qt signals. VAG modules are reached over the K-line with **KW1281**
and **KWP2000** (`rad/protocols/`), through a KKL cable (`rad/kline.py`), an FTDI chip without a COM port
(`rad/ftdi_direct.py`, `rad/d2xx.py`) or a **J2534** PassThru interface (`rad/j2534.py`). Any make is read with
**OBD-II / EOBD** through an **ELM327** adapter, plus read-only **UDS** identification on CAN (`rad/obd/`).
VAG cars from ~2004 are reached over CAN with **VW TP 2.0** carrying KWP2000 (`rad/vagcan/`): the same ELM327 /
OBDLink adapter in raw CAN mode (`elmcan.py`), a TP2.0 channel per module (`tp20.py`) and the K-line KWP2000
decoding reused on top (`kwp.py`); `simbus.py` simulates the modules (port `VAGCAN:SIMULADOR`).
32-bit drivers (RT-USB.DLL, many J2534 DLLs) are loaded by a bridge process running on a portable 32/64-bit
Python shipped in `runtime/` (`rad/bridge.py`, `rad/*_bridge.py`).

## Interfaces

| Interface | Support |
|---|---|
| KKL 409.1 / K-line cables (FTDI, CH340) | KW1281 and KWP2000 |
| J2534 PassThru (04.04) | KWP2000 only |
| ELM327 and compatibles (USB / Bluetooth) | OBD-II / EOBD (CAN, ISO 9141-2, ISO 14230-4, SAE J1850) and read-only UDS on CAN — see [OBD.md](OBD.md) |
| HEX-USB / HEX-V2 clones (FTDI, VID 0403 PID FA2x) | Not supported for ECU access: only the cable's own status (firmware, mode, K-line voltage) — see [HEX_USB.md](HEX_USB.md) |
| Genuine HEX-V2 / HEX-NET, other firmware-based interfaces | Not supported |

Recommended cable: **KKL 409.1 with an FTDI chip** — see [KKL.md](KKL.md) for the on-car validation procedure.
For FTDI cables, a latency timer of 1 ms (Device Manager) makes live data much faster.

## Protocols

| Function | KW1281 | KWP2000 |
|---|:---:|:---:|
| Identification | ✓ | ✓ |
| Read and clear faults (clearing is confirmed by reading the memory again) | ✓ | ✓ |
| Measuring blocks | ✓ | ✓ |
| Basic settings, adaptation, coding (the value the ECU returns is checked) | ✓ | Planned |
| Login (sent; KW1281 does not report whether the code is correct) and output tests | ✓ | Planned |

The full matrix, with the evidence for each stage (detection, initialisation, ECU communication, interpretation),
is in [COVERAGE.md](COVERAGE.md). **No interface has yet been confirmed on a vehicle with this app**: K-line fault
decoding is validated against a real ECU response captured over USB; everything else is tested against the
simulators. [AUDITORIA.md](AUDITORIA.md) is the technical audit of v1.2.0.

## Customer-facing language

The interface the customer sees uses workshop language only: no protocol, chip, driver, baud rate or bridge
names. The rules:

- Texts written for the customer go straight into `tr("…")`.
- Low-level errors keep their technical detail (it goes to the log and the support package). Before an error
  reaches the screen it passes through `rad.errors.client_text()`, which replaces any text with technical terms by
  a plain explanation of what happened and what to do. `rad.errors.is_technical()` is the same check, used by the
  tests.
- Cable detection (`rad/cable.py`) keeps its technical findings; `cable.plain()` turns each one into a customer
  message.

### Technician mode

Start the program with `--tecnico` (or set `RAD_TECNICO=1`) to see everything the customer does not: the
communication log (Ctrl+L), speed / echo / OBD protocol / HEX cable options, the detailed log, the compatibility
matrix, J2534 details in cable detection, the J2534 simulator, protocol and baud rate on the module page, and the
raw error messages.

```bat
.venv\Scripts\pythonw.exe main.py --tecnico
"C:\Program Files\Roots Auto Doctor\RootsAutoDoctor.exe" --tecnico
```

## Running from source

Requires **Python 3.13, 64-bit** ([python.org](https://www.python.org/downloads/windows/)) and internet on the
first run.

```bat
git clone https://github.com/rNx1337k/RootsAutoDoctor.git
cd RootsAutoDoctor
run.bat
```

`run.bat` creates a virtual environment, installs the pinned dependencies (`requirements.txt`), prepares the
portable 32/64-bit Python used by the bridges (`runtime/`) and starts the app.

| Command | Description |
|---|---|
| `run.bat` | Run the app from source |
| `run_tests.bat` | Run the test suite (simulator-based, no car needed) |
| `build_release.bat` | Build the compiled app, check it, self-test it, and create the installer and the portable zip |
| `python tools/i18n_check.py` | List interface texts that still have no English translation |
| `python tools/license_tool.py` | Create licence keys (vendor only, see [LICENSING.md](LICENSING.md)) |

## Building a release

`build_release.bat` produces two files in `dist\`, both self-contained (Python, Qt, Visual C++ runtime, bridges,
portable Python) so a workshop PC needs nothing else:

- `Setup_RootsAutoDoctor_<version>.exe` — installer ([Inno Setup 6](https://jrsoftware.org/isdl.php) must be
  installed on the build PC). Refuses 32-bit Windows and versions older than Windows 10 1809 with a clear
  message, instead of installing a program that would not start.
- `RootsAutoDoctor_<version>_portatil.zip` — portable version: extract and run.

Steps: Nuitka compiles the app → `tools/finish_build.py check` copies any missing Visual C++ runtime DLLs into
the build and fails if something the app needs is missing (Qt Windows plugin, bridges, portable Python) → the
compiled app runs its self-test (`--selftest`: bridges, simulators, Qt and a test PDF) → the portable zip and the
installer are created.

**FTDI driver (optional):** put the official FTDI WHQL driver in `installer\drivers\ftdi\` (see
`installer\drivers\LEIA-ME.txt`). The installer then adds it to the Windows driver store, so a new FTDI cable is
recognised on an offline PC; cables that already work are not touched.

**Clean-PC test:** the build writes `build\teste_pc_limpo.wsb`. On Windows 10/11 Pro with Windows Sandbox
enabled, open it: a fresh Windows (no Python, no Visual C++, no drivers) starts with the compiled app and runs the
self-test; the result is saved in `build\pc_limpo\autoteste.txt`.

**Automatic updates:** once, run `python tools\update_key.py genkey`. It writes the public key to
`rad/update_pubkey.py` (commit it) and keeps the private key outside the repository
(`%USERPROFILE%\RootsAutoDoctor_licencas\update.key`; back it up). From then on `build_release.bat` signs each
installer (`Setup_RootsAutoDoctor_<version>.exe.sig`: Ed25519 over the version and the installer's SHA-256).
To release, create a GitHub Release with tag `v<version>` and attach the installer, its `.sig` and the portable
zip. Installed copies (`rad/autoupdate.py`) see the release at start-up, download the installer in the
background, check the signature, and run it silently (`/VERYSILENT`) when the program closes; the next start
shows "Updated to version …". A file that fails the check is deleted and never runs. The portable version and
source runs only show a notice. The installer installs for the current user by default, so updates need no
administrator prompt; for an all-users install Windows asks once per update.

**SmartScreen:** without a code-signing certificate, Windows shows "Windows protected your PC" the first time the
installer or the program is opened (More info → Run anyway). Signing the installer and the `.exe` removes this.

Self-test of an installed copy (no car needed):

```bat
"C:\Program Files\Roots Auto Doctor\RootsAutoDoctor.exe" --selftest "%USERPROFILE%\Desktop\autoteste.txt"
```

## Translations

Interface text is written in Portuguese and wrapped in `tr("…")` (`rad/i18n.py`); the English catalogue is
`rad/i18n_en.py`. A test fails if any text is missing from the catalogue or if a translation does not keep the
same `{placeholders}` and HTML tags.

## Data and logs

History, logs, the change journal, the licence and the workshop logo are kept in `%APPDATA%\RootsAutoDoctor`
(uninstalling keeps them); settings are in the Windows registry (`HKCU\Software\Roots\RootsAutoDoctor`). Logs and
crash reports are in `%APPDATA%\RootsAutoDoctor\registos`; **Options → Support package** zips them for support.

See [CHANGELOG.md](../CHANGELOG.md) for release notes.
