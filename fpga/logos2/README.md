# Pango Logos2 (PG2L50H)

**Part under consideration:** PG2L50H-6IFBG484 (50K-class logic, speed grade 6, industrial temperature, 484-ball BGA).
**Status:** current choice, with the ECP5 as fallback. Its bitstream security is better than the ECP5's on every count, and its DPA-protected hard AES block now carries all of the FPGA's cryptography.
The deciding unknown is the build flow (requirement 6, open question F1).

## What the datasheet claims

From the *Logos2 Family FPGAs Device Datasheet*:

- AES-256-GCM bitstream encryption with "self-authentication", plus RSA-2048 bitstream signatures over a SHA-3 digest.
- Key storage in eFuse or battery-backed RAM (BB-RAM), BB-RAM offering chip-level protection.
- Protection against bitstream readback.
- JTAG security management, including permanently disabling JTAG.
- Protection against differential power analysis (DPA) of the key.

## Requirements

| # | Requirement (`fpga/README.md`) | Logos2 |
|---|---|---|
| 1 | Bitstream encryption, per-device key | AES-256-GCM with the key in eFuse, programmed per device at enrollment |
| 2 | No fallback to unencrypted | **Assumed:** both encryption and signing are supported in hardware, so both are enforced (to confirm, F2) |
| 3 | Readback disabled | Yes (claimed) |
| 4 | Key not readable | eFuse; JTAG is permanently disabled when the device is locked, so what JTAG could do before that matters only inside the factory |
| 5 | Configured by the C5 | **Slave serial**, like most FPGAs. Reusing those pins for the link is probably possible; otherwise the board gives the link its own pins (F3) |
| 6 | Per-device constants from a script | PDS runs from the command line. **Still the deciding question:** whether it can change block RAM initialization in a routed design from a script, then encrypt and sign (F1) |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | A 50K-class part: ample room for the security blocks, the CPU and the application. LUT size and block RAM to confirm |
| 9 | QSPI flash interface | General I/O |
| — | Bitstream authentication | **Yes, twice:** the GCM tag under the per-device key, and the RSA-2048 signature. Closes R32 |

## What it improves over the ECP5

| Risk | ECP5 | Logos2 |
|---|---|---|
| R32: blind edits to an encrypted bitstream | Open: no MAC, only the CRC | **Closed:** AES-GCM authenticates every bitstream under the device's own key; RSA-2048 adds an origin signature |
| R33: power analysis | Neither configuration nor soft AES hardened | **DPA protection** for configuration and for the hard AES block in the fabric, which runs all the FPGA's key-dependent work |
| R43: boundary scan after locking | Remains available | **Can be removed** by permanently disabling JTAG, after the board's boundary-scan test at the factory |
| Bitstream key size | AES-128 | AES-256 |
| Fit | 24K LUTs, tight for a large application | 50K class, roomy |

The GCM tag alone is enough for our purposes, because it is under a key unique to each device. RSA-2048 (about 112-bit classical strength, not quantum-safe) adds little
on top, but costs nothing to use: the fleet signing key would live in the manufacturer's HSM.

## The hard AES block

Pango's DPA protection covers configuration and the **hard AES block in the fabric**. That is why the design uses AES-256 rather than Ascon: the XIP, link and recording engines
all run their cryptography in that block, and the key registers feed it directly. Open (F4): AES-256 support, whether the block computes GHASH (if not, the FPGA uses AES-CCM so
that no key-dependent step runs in unprotected fabric), throughput, number of instances, and the key-loading interface. Also open (F5): whether the block can use the eFuse key, or a key
derived from it, which would let the link and image keys stay out of the bitstream.

## Key storage: eFuse or BB-RAM

- **eFuse (base choice):** permanent, needs no battery, matches every other family here.
- **BB-RAM:** the key lives in battery-backed RAM and can be erased instantly. That would allow a **tamper response**: the enclosure switch (open question Q7) clears the key,
  after which the FPGA can no longer load its bitstream, and the device is permanently disabled. Past recordings stay safe either way. The cost is a coin cell, and a device whose battery
  dies also stops working, which is probably unacceptable for a medical device unless the battery is inside a serviced, monitored part.

## Enrollment

Would replace step 7 of `doc/enrollment.md`:

1. Run the board's boundary-scan test.
2. Program the device's AES-256 key (from the HSM) into eFuse, and the RSA-2048 public key data if authentication is used.
3. Set whatever forces encrypted or authenticated configuration (to confirm).
4. Permanently disable JTAG.

## Toolchain

Pango Design Suite (PDS), proprietary, runs from the command line. There is no open-source place-and-route for Logos2, so the development flow is PDS too.
Licence terms and scripted block RAM updates with encryption and signing (F1) are open.

## Other considerations

- Documentation is mostly in Chinese; some details may only be available through Pango's support.
- Supply chain and availability for the target markets should be checked alongside the technical evaluation.
- It fits the ICS55 direction (`doc/ics55.md`): a domestic Chinese FPGA now, a domestic 55 nm ASIC later.

## Answers so far, and what remains

| Question | Answer |
|---|---|
| Encrypted-only and signed-only configuration | Unknown; both are supported in hardware, so the design assumes both are enforced (F2) |
| Configuration from a microcontroller | Slave serial. Pin reuse for the link probably possible; a PCB decision (F3) |
| JTAG access to the eFuse key before JTAG is disabled | Unknown; a locked device has JTAG permanently disabled |
| DPA protection | Covers configuration and the hard AES block in the fabric |
| PDS from the command line | Yes |
| Block RAM contents in a routed design, from a script, then encrypt and sign | **Open (F1)** |
| Hard AES block: AES-256, GHASH, throughput, instances, key loading | **Open (F4)** |
| Hard AES block using the eFuse key | Open (F5) |
