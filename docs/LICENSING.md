# Licensing

Roots Auto Doctor is licensed per workshop PC. Activation is **offline**: neither the workshop nor the vendor
needs an internet connection.

## How it works

- Each PC has an ID derived from the Windows machine GUID, shown in **Options → Licence** (e.g. `ABCD-EFGH-JKLM`).
- A licence key contains the workshop name, the PC ID, the issue date and an optional expiry date, signed with
  the vendor's **Ed25519 private key**. The app only contains the public key (`rad/license_pubkey.py`), so keys
  cannot be forged from the app.
- Without a valid licence the app runs in **demo mode**: identification, fault reading, measuring values, OBD-II
  and the simulator all work, but nothing is written to a real vehicle (coding, adaptation, basic settings,
  clearing faults, output tests, service reset) and reports are marked as a demo version.
- While `PUBLIC_KEY` is `None` licensing is switched off (development builds).

> The check runs inside the app, so someone who modifies the program can bypass it. It controls normal
> distribution; it is not protection against determined copying. The Nuitka build makes this harder.

## Vendor workflow

1. **Once:** create the key pair.

   ```bat
   .venv\Scripts\python.exe tools\license_tool.py genkey
   ```

   The private key is written to `%USERPROFILE%\RootsAutoDoctor_licencas\private.key` (outside the repository;
   `*.key` is also in `.gitignore`) and the public key to `rad/license_pubkey.py`. **Back up the private key**:
   without it you cannot issue new keys for this public key. The tool never overwrites an existing private key.
   Commit `rad/license_pubkey.py` and build a new release.

2. **For each workshop:** ask for the PC ID shown in Options → Licence and issue a key.

   ```bat
   .venv\Scripts\python.exe tools\license_tool.py issue --machine ABCD-EFGH-JKLM --workshop "Oficina Silva"
   .venv\Scripts\python.exe tools\license_tool.py issue --machine ABCD-EFGH-JKLM --workshop "Oficina Silva" --expires 2027-12-31
   ```

   The key (starting with `RAD1-`) is printed and logged in `licencas_emitidas.csv` next to the private key.
   The workshop pastes it into Options → Licence → Activate licence.

3. **Changing PC:** the key is tied to the PC ID. Issue a new key for the new PC ID.

## Updates

The update check (Options → Updates) reads the latest GitHub release of the repository. To deliver a version to
workshops, publish a GitHub release for the tag and attach `Setup_RootsAutoDoctor_<version>.exe`; the app opens
the installer link. Without releases the app falls back to the highest version tag and opens the releases page.
If the repository is private, the check cannot see it and reports the GitHub error.
