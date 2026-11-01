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
decoding reused on top (`kwp.py`); `simbus.py` simulates the modules (port `VAGCAN:SIMULADOR`). A J2534 interface
can also open a **raw CAN channel** (`J2534CanBus` in `rad/j2534.py`): with the "OBD adapter" equipment selected,
the same ISO-TP (OBD-II/UDS) and TP2.0 (VAG) code runs over it.
32-bit drivers (RT-USB.DLL, many J2534 DLLs) are loaded by a bridge process running on a portable 32/64-bit
Python shipped in `runtime/` (`rad/bridge.py`, `rad/*_bridge.py`).

## Interfaces

| Interface | Support |
|---|---|
| KKL 409.1 / K-line cables (FTDI, CH340) | KW1281 and KWP2000 |
| J2534 PassThru (04.04) | KWP2000 over the K-line ("VAG cable" equipment); raw CAN for OBD-II/UDS and VAG over CAN ("OBD adapter" equipment) |
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
| Adaptation and coding (the value is read back from the ECU before it is reported as saved) | ✓ | ✓ (K-line and J2534) |
| Login — KW1281: login block (the ECU does not report whether the code is correct); KWP2000: security access 27 03/04 (key = seed + code) | ✓ | ✓ |
| Basic settings and output tests | ✓ | ✓ |

KWP2000 writing follows the EDC16 captures published by [kw1281test](https://github.com/gmenounos/kw1281test)
(MIT): coding is `3B 9A` with the workshop code and software version the ECU itself returned in `1A 9B`; adaptation
uses the `31 B8`…`BB` / `32 B8` routines with the fixed `01 03` selector; basic settings use `31 B8/BA 00 <group>`
and output tests `31 B8/B9/BA 01 02`. The open routine is always closed (`32 B8 …`) before any other request. Writing
is offered only when the `1A 9B` record has that known layout — on the K-line, through J2534 and over CAN (TP2.0)
alike.

The full matrix, with the evidence for each stage (detection, initialisation, ECU communication, interpretation),
is in [COVERAGE.md](COVERAGE.md). **No interface has yet been confirmed on a vehicle with this app**: K-line fault
decoding is validated against a real ECU response captured over USB; everything else is tested against the
simulators. [AUDITORIA.md](AUDITORIA.md) is the technical audit of v1.2.0.

## Recordings and on-car validation

**Recording** (`rad/capture.py`): while a recording is active, every byte sent and received through the VAG cable
or the OBD adapter, and every J2534 bridge request, is written to a `.radrec` file (JSON lines, readable in a text
editor) together with the commands the program ran and a stable summary of each result. **Options → Record
communication** starts and stops it; recordings live in `%APPDATA%\RootsAutoDoctor\gravacoes` and the latest three
go into the support package.

**Replay** (`rad/replay.py`): the port `REPLAY:<file>` (or `J2534:REPLAY:<file>`) answers with the recording and
checks that the program sends exactly the same bytes. `replay.run(path)` re-runs the recorded commands with the
current code and reports byte divergences and changed results. **Every file in `tests/captures/` is replayed by
`tests/test_captures.py`**, so a session recorded on a real car becomes a permanent regression test: copy the
`.radrec` there and commit it. In technician mode, **Options → Check recording…** does the same from the app.

**On-car validation** (`rad/validation.py`, technician mode → **Options → On-car validation**): a fixed sequence —
cable and ignition, engine (identification, faults, block 001 three times, optional clear and re-read),
instrument cluster, ABS — always recorded, with an HTML report next to the recording. The report lists each fault
with the **raw status byte** and how VCDS should show it, which is how the open question about the KWP2000 status
byte gets settled on the first KWP2000 car.

## Quality checks

- `run_tests.bat` (or `python tests/run_all.py`) runs every test; the UI tests run without a screen
  (`QT_QPA_PLATFORM=offscreen`).
- `ruff check .` — style and common errors (`ruff.toml`).
- **GitHub Actions** (`.github/workflows/ci.yml`) runs Ruff and the whole test suite on Windows for every push and
  pull request; the README badge shows the result.

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
| `ruff check .` | Style and common errors (also run by GitHub Actions) |
| `tools\screenshots.bat` | Regenerate the README screenshots (`docs/screenshots/`) with the simulator |
| `python tools/make_brand.py` | Regenerate the logo, icon and banner from the SVG source |
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

**Code signing (SmartScreen):** without a code-signing certificate, Windows shows "Windows protected your PC" the
first time the installer or the program is opened (More info → Run anyway). `build_release.bat` signs the program and
the installer with Authenticode when a certificate is configured, and skips it with a warning otherwise:

| Variable | Meaning |
|---|---|
| `RAD_CODESIGN_PFX` + `RAD_CODESIGN_PASSWORD` | Certificate in a `.pfx` file (keep it outside the repository) |
| `RAD_CODESIGN_THUMBPRINT` | Or a certificate installed in Windows / on a USB token (EV), by thumbprint |
| `RAD_CODESIGN_TIMESTAMP` | Timestamp server (default `http://timestamp.digicert.com`) |
| `RAD_SIGNTOOL` | Path to `signtool.exe` if it is not found in the Windows SDK |

The update signature (`.sig`) is created after the Authenticode signature, so it covers the final file.

### Publishing a release

1. Bump `rad/__init__.py` → `VERSION`, update `CHANGELOG.md`, commit, then `git tag v<version>` and
   `git push origin main v<version>`.
2. GitHub Actions (`.github/workflows/release.yml`) runs the tests, compiles the program on a clean Windows runner,
   runs its self-test and creates a **draft** Release with the installer and the portable zip. It fails if the tag
   does not match `VERSION`.
3. On the publisher's PC (which holds the update key and the certificate), run
   `tools\publicar_release.bat <version>`: it downloads the installer from the draft, signs it (Authenticode, if
   configured), creates the `.sig`, uploads both and publishes the Release. Installed copies then update
   themselves. Requires the GitHub CLI (`winget install GitHub.cli`, then `gh auth login`).

`build_release.bat` still builds everything locally, as before.

Self-test of an installed copy (no car needed):

```bat
"C:\Program Files\Roots Auto Doctor\RootsAutoDoctor.exe" --selftest "%USERPROFILE%\Desktop\autoteste.txt"
```

## Translations

Interface text is written in Portuguese and wrapped in `tr("…")` (`rad/i18n.py`); the English catalogue is
`rad/i18n_en.py`. A test fails if any text is missing from the catalogue or if a translation does not keep the
same `{placeholders}` and HTML tags.

## Data and logs

History, the vehicle and customer register (`vehicles` table in `historico.db`, `rad/vehicles.py`), logs,
recordings, the change journal, the licence and the workshop logo are kept in `%APPDATA%\RootsAutoDoctor`
(uninstalling keeps them); settings are in the Windows registry (`HKCU\Software\Roots\RootsAutoDoctor`). Logs and
crash reports are in `%APPDATA%\RootsAutoDoctor\registos`; **Options → Support package** zips them for support.

See [CHANGELOG.md](../CHANGELOG.md) for release notes.
