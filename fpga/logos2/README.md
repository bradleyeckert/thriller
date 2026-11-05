# Pango Logos2 (PG2L50H)

**Part under consideration:** PG2L50H-6IFBG484 (50K-class logic, speed grade 6, industrial temperature, 484-ball BGA).
**Status:** strong candidate. On paper its bitstream security is better than the ECP5's on every count; the deciding unknown is the build flow (requirement 6).

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
| 2 | No fallback to unencrypted | To confirm: a setting that forces encrypted (or signed) configuration. Likely tied to enabling authentication, as on the Ti60 |
| 3 | Readback disabled | Yes (claimed) |
| 4 | Key not readable | eFuse; to confirm what JTAG can do to it before JTAG is disabled |
| 5 | Configured by the C5 | To confirm: slave serial or SPI configuration, and reusing those pins for the link |
| 6 | Per-device constants from a script | **Unknown, and the deciding question:** whether Pango Design Suite can change block RAM initialization in a routed design from a script, then encrypt |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | A 50K-class part: ample room for the security blocks, the CPU and the application. LUT size and block RAM to confirm |
| 9 | QSPI flash interface | General I/O |
| — | Bitstream authentication | **Yes, twice:** the GCM tag under the per-device key, and the RSA-2048 signature. Closes R32 |

## What it improves over the ECP5

| Risk | ECP5 | Logos2 |
|---|---|---|
| R32: blind edits to an encrypted bitstream | Open: no MAC, only the CRC | **Closed:** AES-GCM authenticates every bitstream under the device's own key; RSA-2048 adds an origin signature |
| R33: power analysis on bitstream decryption | Not hardened | **Claimed DPA protection** for the configuration key. Our own Ascon cores in the fabric are still unprotected |
| R43: boundary scan after locking | Remains available | **Can be removed** by permanently disabling JTAG, after the board's boundary-scan test at the factory |
| Bitstream key size | AES-128 | AES-256 |
| Fit | 24K LUTs, tight for a large application | 50K class, roomy |

The GCM tag alone is enough for our purposes, because it is under a key unique to each device. RSA-2048 (about 112-bit classical strength, not quantum-safe) adds little
on top, but costs nothing to use: the fleet signing key would live in the manufacturer's HSM.

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

Pango Design Suite (PDS), proprietary. There is no open-source place-and-route for Logos2, so the development flow would be PDS too. Licence terms, headless operation, and scripting
of block RAM updates and encryption are open.

## Other considerations

- Documentation is mostly in Chinese; some details may only be available through Pango's support.
- Supply chain and availability for the target markets should be checked alongside the technical evaluation.
- It fits the ICS55 direction (`doc/ics55.md`): a domestic Chinese FPGA now, a domestic 55 nm ASIC later.

## Questions for Pango

1. Which setting forces the device to accept only encrypted, or only signed, bitstreams? Is it an eFuse?
2. Can Pango Design Suite change block RAM initialization in a routed design from a script, and then encrypt and sign the bitstream, without placing and routing again?
3. Slave configuration from a microcontroller: which modes, and can the configuration pins become user I/O afterwards?
4. Before JTAG is disabled, can the eFuse key be read, verified or overwritten over JTAG?
5. What does the DPA protection cover, and is there evaluation data?
6. PDS licence for production use, and headless (command-line) operation.
