# Architecture: Algorithm Bill of Materials

This document lists every cryptographic and support algorithm that `thriller` needs for signing,
provisioning, booting and updating, and where each one runs.

## Two update chains

`thriller` authenticates two independent kinds of update:

- **Platform updates** replace the FPGA bitstream, including the `thriller` loader. They exist only on FPGAs.
- **Application updates** replace the code and data stored encrypted in SPI NOR flash. They exist on FPGAs and on an ASIC conversion.

Each chain has its own LMS signing key, its own secure element counter and its own package format.
The rows marked "platform only" below disappear in an ASIC conversion; everything else carries over.

## Where algorithms run

| Location | What it is | Who provides it |
|---|---|---|
| **Host** | Signing and provisioning tools, and the field update client | Us (scripts and an HSM) and the FPGA vendor (bitstream tools) |
| **Config engine** | The FPGA's hardened configuration logic | FPGA vendor, fixed in silicon (platform only) |
| **Loader** | RTL cores and soft MCU code in the bitstream, or in silicon on an ASIC | Us |
| **Secure element** | ATECC608B (or MOD8ID) | Microchip / Modsemi, fixed in silicon |

The design goal is that every algorithm in the loader is built from **SHA-256 and AES**: no bignum or
elliptic-curve arithmetic. LMS signatures make this possible, because verifying one is just hashing.

## Summary

| Algorithm | Host | Config engine | Loader | Secure element | Used for | ASIC |
|---|:-:|:-:|:-:|:-:|---|:-:|
| Bitstream signature (ECDSA P-256 or RSA-4096, per family) | sign | verify | | | Stage 0 bitstream authentication | — |
| Bitstream encryption (AES-256, mode per family) | encrypt | decrypt | | | Bitstream confidentiality, and quantum-safe Stage 0 | — |
| LMS (RFC 8554), platform key | sign (stateful, HSM) | | **verify** | | Platform package signatures | — |
| LMS (RFC 8554), application key | sign (stateful, HSM) | | **verify** | | Application package signatures | ✓ |
| SHA-256 | yes | | **yes** | yes | LMS, package digests, MACs, nonce and key derivation | ✓ |
| SE MAC protocol (SHA-256 based) | | | **yes** | yes | Authenticated counter reads and public key reads | ✓ |
| HMAC-SHA256 | yes | | **yes** | yes | UART challenge-response | ✓ |
| AES-256-GCM (or AES-CTR + HMAC) | | | **yes** | | Application encryption and authentication in flash | ✓ |
| Key wrap / encrypted write | wrap | | **yes** | yes | Installing the next pairing key | — |
| Monotonic counter 0 | | | | yes | Platform anti-rollback | — |
| Monotonic counter 1 | | | | yes | Application anti-rollback | ✓ |
| TRNG | | | | yes | Key generation, SE nonces | ✓ |
| Loader nonce source | | | **yes** | | Freshness the SE and bus cannot control | ✓ |
| CRC-16 (poly 0x8005) | | | **yes** | yes | SE I2C packet integrity | ✓ |
| CRC-32 | yes | | yes | | UART transport framing (not security) | ✓ |

## Host

**Bitstream signing and encryption (platform only).** Done by the FPGA vendor's tools, so the algorithm depends on the family:
ECDSA with AES-256 on Lattice Nexus, RSA-4096 with AES-GCM-256 on Efinix Titanium. These signatures are not
quantum-safe, so the device must also be locked to accept only encrypted bitstreams (README, FPGA Requirements item 6).

**LMS signing (both chains).** Each chain has its own LMS key pair. Platform packages hold a bitstream, its version,
and the next pairing key wrapped under the current one. Application packages hold the application image and its version.
Because the loader verifies the platform signature before writing a bitstream to flash, every platform update is signed
twice: LMS by us, and the vendor's own format checked by the config engine at boot.

LMS is stateful, and the signing side must be built around that:
- Each one-time key (leaf) signs exactly once. Reusing a leaf lets an attacker forge signatures.
- The signer's state (next leaf index) must survive crashes and must never be restored from an older backup.
- SP 800-208 expects key generation and signing in a hardware security module that enforces this.
- A tree of 2^10 to 2^15 leaves covers far more updates than a product line will ever ship. HSS
  (multi-level trees, also in RFC 8554) is available if one key must last longer.

The application key can be held by a different party than the platform key, for example a customer who ships
their own application on our platform.

**Provisioning.**
- Write and lock the secure element configuration zone.
- Write the application LMS public key, the first pairing key, the UART authentication key and the device-unique
  application encryption key into their slots, then lock the data zone.
- The platform LMS public key needs no provisioning: it is built into the bitstream.
- Optional per-device diversification: pairing key = KDF(release pairing key, SE serial number), so extracting one device does not expose the fleet.
- Program and lock the FPGA's key fuses (see the FPGA Requirements in the README).

**Field update client.** Sends platform and application packages over the UART and answers the HMAC-SHA256 challenge.

## Config engine (platform only)

Fixed in silicon; we only choose and lock it.

- Bitstream signature verification (ECDSA or RSA, per family)
- Bitstream decryption (AES-256)
- Key storage in one-time fuses
- Port and readback lockout, and encrypted-only configuration

## Loader

This is the part we write. It should be small, identical across FPGA families, and suitable for an ASIC.

**SHA-256 (required, RTL core strongly recommended).** Everything else in the loader is built on it:
LMS verification, package digests, the secure element MAC protocol, HMAC, and key derivation.
LMS verification alone runs hundreds to thousands of SHA-256 compressions, so a hardware core matters.
One shared core can serve all users.

**LMS verification.** Recomputes the one-time public key from the signature by walking the Winternitz hash
chains, then climbs the Merkle tree to the root and compares it with the stored public key. Only SHA-256 is needed.
Sizes for the common parameter sets (n = 32, SHA-256):

| Parameter set | Signature size | Max chain hashes to verify | Signatures per key |
|---|---|---|---|
| LMS_SHA256_M32_H10 + LMOTS_SHA256_N32_W4 | 2,508 bytes | about 1,000 | 1,024 |
| LMS_SHA256_M32_H10 + LMOTS_SHA256_N32_W8 | 1,452 bytes | about 8,700 | 1,024 |
| LMS_SHA256_M32_H15 + LMOTS_SHA256_N32_W4 | 2,668 bytes | about 1,000 | 32,768 |

W = 4 is the natural choice: signatures are larger but still small next to an image, and verification is about
eight times faster. Public keys are 56 bytes for every parameter set. SP 800-208 also defines 192-bit (M24/N24)
variants with smaller signatures.

Where the public keys come from:
- **Platform key:** a constant in the bitstream, authenticated by Stage 0.
- **Application key:** read from its secure element slot over the MAC'd channel at each use, so a device on the I2C bus cannot substitute its own.

**Secure element MAC protocol.** The loader recomputes the MACs that the secure element returns, so the I2C bus
cannot forge or replay results. Needed for:
- Counter reads: Nonce, then GenDig over the counter, then MAC with the pairing key.
- Public key reads: an authenticated read of the application LMS public key slot.
- Encrypted reads and writes of keys (EncRead/EncWrite, which use SHA-256 derived keystreams).

The exact digest layouts are defined by Microchip's command formats. Implement them from cryptoauthlib
and test each one against real parts before any zone is locked.

**Loader nonce source.** The loader must put its own fresh value into each Nonce command (NumIn).
If it only uses the secure element's random output, a device on the bus can replay an old exchange.
Options, smallest first:
- A ring-oscillator TRNG with health tests (no external dependency).
- A free-running counter combined with the SE serial number and a boot count. This is weaker: it must never repeat across power cycles.

**AES-256-GCM, or AES-256-CTR with HMAC-SHA256.** Decrypts and authenticates the application read from flash at boot,
and encrypts it on update. GCM needs an AES core plus a GHASH (GF(2^128) multiply). CTR plus HMAC reuses the
SHA-256 core and needs only the AES encrypt direction. Either is fine; CTR plus HMAC is likely smaller.
The secure element's AES is single-block over I2C and too slow for whole images. AES-256 is quantum-safe.

**Key wrap for pairing key rotation (platform only).** The platform package carries the next release's pairing key,
encrypted under the current one. The loader unwraps it and writes it to the secure element with an
authorized encrypted write. Sequencing across power failures still needs to be designed (see Open Questions).

**HMAC-SHA256 for UART authentication.** The loader issues a challenge from its nonce source and checks the
host's response, using a key read from the secure element.

**Support logic (not cryptographic).**
- I2C master with the secure element's CRC-16 (polynomial 0x8005, initial value 0, LSB first), wake, idle and sleep handling.
- QSPI flash driver with A/B slots for the bitstream and for the application, so a failed update never leaves the device without a bootable image.
- UART framing with CRC-32.

## Secure element

Fixed in silicon; we only configure and lock it. With LMS, it no longer checks signatures. Its jobs are:

- Two monotonic counters (maximum 2,097,151): counter 0 for the platform, counter 1 for the application
- Key storage: application LMS public key, pairing key, UART authentication key, device-unique application encryption key
- SHA-256 and the Nonce, GenDig, MAC, CheckMac, EncRead and EncWrite commands for the authenticated channel
- TRNG
- Configuration and data zone locks

Its ECDSA engine goes unused. On an ASIC, counter 0 is free for other uses.

## Not needed

These are deliberately absent from the loader:

- ECDSA, Ed25519 and RSA (no bignum or elliptic-curve arithmetic, and none are quantum-safe)
- PUF and fuzzy extractor (the secure element holds device-unique keys)
- Any algorithm specific to one FPGA family

## Open Questions

1. **Pairing key rotation sequencing (platform only).** The order of operations for writing a new bitstream, installing the next pairing key and advancing counter 0, such that a power failure at any point leaves a bootable, non-rollbackable device.
2. **Secure element protocol details.** Confirm that GenDig over the counter zone, authenticated reads of the public key slot, and EncWrite of the pairing key slot all work as expected on the ATECC608B, and separately on the MOD8ID.
3. **AES mode choice.** GCM or CTR plus HMAC, decided by measured fabric area on the smallest target FPGA.
4. **Nonce source.** Whether a ring-oscillator TRNG is reliable enough across the supported FPGA families and an ASIC process, or whether the counter fallback is acceptable.
5. **ASIC pairing key.** A pairing key in mask logic is the same on every chip and can be recovered from one die. An ASIC needs a per-device pairing key, written at provisioning into one-time-programmable fuses or another per-device store.
6. **Separate key owners.** If the application key belongs to a customer, how they provision their LMS public key into the secure element without needing access to the platform key, and whether the application chain needs its own UART authentication key.
7. **LMS parameter set and signing infrastructure.** Final choice of tree height and Winternitz parameter (W = 4 assumed), whether to use SHA-256/192, and which HSM or signing service manages LMS state for each key owner.
