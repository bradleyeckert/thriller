# Pango Logos2 (PG2L50H)

**Part under consideration:** PG2L50H-6IFBG484 (50K-class logic, speed grade 6, industrial temperature, 484-ball BGA).
**Status:** current choice, with the ECP5 as fallback. Its bitstream security meets the hard requirements of the wish list, and its DPA-protected hard AES block carries all of the FPGA's cryptography.
The deciding unknowns are the build flow (item 5, F1) and the master SPI multi-boot behavior (item 4, F3).

## What the datasheet claims

From the *Logos2 Family FPGAs Device Datasheet*:

- AES-256-GCM bitstream encryption with "self-authentication", plus RSA-2048 bitstream signatures over a SHA-3 digest.
- Key storage in eFuse or battery-backed RAM (BB-RAM).
- Protection against bitstream readback.
- JTAG security management, including permanently disabling JTAG.
- Protection against differential power analysis (DPA) of the key.

## The wish list

| # | Requirement (`fpga/README.md`) | Logos2 |
|---|---|---|
| 1 | Encryption and authentication, per-device key | AES-256-GCM with the key in eFuse, programmed per device at enrollment, and RSA-2048 signatures. **Yes, twice.** Closes R32 |
| 2 | No fallback | **Assumed:** both encryption and signing are supported in hardware, so both are enforced (to confirm, F2) |
| 3 | Readback disabled, key not readable | Yes (claimed); eFuse; JTAG permanently disabled when locked |
| 4 | Master SPI self-configuration with multi-boot | Master SPI is a standard mode on the family; the multi-boot or golden-image mechanism, its addresses and how the fabric points at the other slot are **to confirm (F3)** |
| 5 | Per-device constants from a script | PDS runs from the command line. **Still the deciding question:** whether it can change block RAM initialization in a routed design from a script, then encrypt and sign (F1) |
| 6 | Hard AES block, DPA-protected, usable from the fabric | Yes (claimed). Open (F4): AES-256 support, GHASH, throughput for three users, instances, key-loading interface |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | A 50K-class part: ample room for both cores, the security blocks and the application. LUT size and block RAM to confirm |
| 9 | QSPI and peripheral pins | General I/O; 484 balls |

## What it improves over the ECP5

| Risk | ECP5 | Logos2 |
|---|---|---|
| R32: blind edits to an encrypted bitstream | Open: no MAC, only the CRC | **Closed:** AES-GCM authenticates every bitstream under the device's own key; RSA-2048 adds an origin signature |
| R5, R33: power analysis | Neither configuration nor soft AES hardened | **DPA protection** for configuration and for the hard AES block |
| R43: boundary scan after locking | Remains available | **Can be removed** by permanently disabling JTAG, after the board's boundary-scan test at the factory |
| Bitstream key size | AES-128 | AES-256 |
| Fit | 24K LUTs, tight | 50K class, roomy |

## The hard AES block

Pango's DPA protection covers configuration and the **hard AES block in the fabric**. That is why the design uses AES-256 rather than Ascon: the XIP engine, the recording engine and the install
port all run their cryptography in that block, and the key registers feed it directly. Open (F4): AES-256 support, whether the block computes GHASH (if not, AES-CCM so that no key-dependent step
runs in unprotected fabric), throughput, number of instances, and the key-loading interface. Also open (F5): whether the block can use the eFuse key, or a key derived from it, which would let the pairing
keys be wrapped rather than stored in the bitstream.

## Key storage: eFuse or BB-RAM

- **eFuse (base choice):** permanent, needs no battery, matches every other family here.
- **BB-RAM:** the key lives in battery-backed RAM and can be erased instantly, which would allow a tamper response from the enclosure switch (Q7). The cost is a coin cell, and a device whose
  battery dies also stops working, which is probably unacceptable for a medical device.

## Enrollment

Replaces step 3 of `doc/enrollment.md`:

1. Run the board's boundary-scan test.
2. Program the device's AES-256 key (from the HSM) into eFuse, and the RSA-2048 public key data.
3. Set whatever forces encrypted and signed configuration, and disables readback (to confirm, F2).
4. After the first boot and the attestation check, permanently disable JTAG.

## Flash and multi-boot

To be written from Pango's configuration documentation (F3): the master SPI mode pins, the bitstream address, the multi-boot or fallback mechanism, and how the loader redirects it to the other slot.
The bitstream slots in `doc/flash.md` are sized at 4 MB pending F9.

## Toolchain

Pango Design Suite (PDS), proprietary, runs from the command line. There is no open-source place-and-route for Logos2, so the development flow is PDS too.
Licence terms and scripted block RAM updates with encryption and signing (F1) are open.

## Other considerations

- Documentation is mostly in Chinese; some details may only be available through Pango's support.
- Supply chain, availability and **country of origin** for the target markets should be checked alongside the technical evaluation (F11). PolarFire is the candidate to compare against if origin matters.
- It fits the ICS55 direction (`doc/ics55.md`): a domestic Chinese FPGA now, a domestic 55 nm ASIC later.

## Answers so far, and what remains

| Question | Answer |
|---|---|
| Encrypted-only and signed-only configuration | Unknown; both are supported in hardware, so the design assumes both are enforced (F2) |
| Master SPI self-configuration and multi-boot | **Open (F3)** |
| JTAG access to the eFuse key before JTAG is disabled | Unknown; a locked device has JTAG permanently disabled |
| DPA protection | Covers configuration and the hard AES block in the fabric |
| PDS from the command line | Yes |
| Block RAM contents in a routed design, from a script, then encrypt and sign | **Open (F1)** |
| Hard AES block: AES-256, GHASH, throughput, instances, key loading | **Open (F4)** |
| Hard AES block using the eFuse key | Open (F5) |
