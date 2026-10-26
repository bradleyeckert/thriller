# Architecture: Algorithm Bill of Materials

This document lists every cryptographic and support algorithm that `thriller` needs for signing,
provisioning, booting and updating, and where each one runs.

There are four places an algorithm can live:

| Location | What it is | Who provides it |
|---|---|---|
| **Host** | Manufacturer's signing and provisioning tools, and the field update client | Us (scripts) and the FPGA vendor (bitstream tools) |
| **Config engine** | The FPGA's hardened configuration logic | FPGA vendor, fixed in silicon |
| **Fabric** | RTL cores and the soft MCU firmware in the bitstream | Us |
| **Secure element** | ATECC608B (or MOD8ID) | Microchip / Modsemi, fixed in silicon |

The design goal is that the fabric needs **no public-key cryptography**. Every signature check is done by
the config engine or the secure element. The fabric only hashes, MACs, and decrypts.

## Summary

| Algorithm | Host | Config engine | Fabric | Secure element | Used for |
|---|:-:|:-:|:-:|:-:|---|
| Bitstream signature (ECDSA P-256 or RSA-4096, per family) | sign | verify | | | Stage 0 bitstream authentication |
| Bitstream encryption (AES-256, mode per family) | encrypt | decrypt | | | Bitstream confidentiality |
| ECDSA P-256 | sign | | | verify | Update package and firmware signatures |
| SHA-256 | yes | | **yes** | yes | Image digests, MACs, nonce and key derivation |
| SE MAC protocol (SHA-256 based) | | | **yes** | yes | Authenticated counter reads and verify results |
| HMAC-SHA256 | yes | | **yes** | yes | UART challenge-response |
| AES-256-GCM (or AES-CTR + HMAC) | | | **yes** | | Firmware encryption and authentication in flash |
| Key wrap / encrypted write | wrap | | **yes** | yes | Installing the next pairing key |
| Monotonic counter | | | | yes | Firmware and bitstream anti-rollback |
| TRNG | | | | yes | Key generation, SE nonces |
| Fabric nonce source | | | **yes** | | Freshness the SE and bus cannot control |
| CRC-16 (poly 0x8005) | | | **yes** | yes | SE I2C packet integrity |
| CRC-32 | yes | | yes | | UART transport framing (not security) |

## Host

**Bitstream signing and encryption.** Done by the FPGA vendor's tools, so the algorithm depends on the family:
ECDSA with AES-256 on Lattice Nexus, RSA-4096 with AES-GCM-256 on Efinix Titanium. We supply the keys and keep the private key offline, ideally in an HSM.

**Update package signing: ECDSA P-256 with SHA-256.** One firmware signing key covers every update package,
whether it holds firmware, a bitstream, or both. Because the secure element verifies this signature, a new
bitstream is checked before it is written to flash, not only by the config engine at the next boot.
This gives every update two signatures on any FPGA family, including RSA-only parts whose bitstream signature
the secure element cannot check.

**Provisioning.**
- Write and lock the secure element configuration zone.
- Write the firmware public key, the first pairing key, the UART authentication key and the firmware encryption key into their slots, then lock the data zone.
- Optional per-device diversification: pairing key = KDF(release pairing key, SE serial number), so extracting one device does not expose the fleet.
- Program and lock the FPGA's key fuses (see the FPGA Requirements in the README).

**Field update client.** Sends update packages over the UART and answers the HMAC-SHA256 challenge.

## Config engine

Fixed in silicon; we only choose and lock it.

- Bitstream signature verification (ECDSA or RSA, per family)
- Bitstream decryption (AES-256)
- Key storage in one-time fuses
- Port and readback lockout

## Fabric

This is the part we write. It should be small and identical across FPGA families.

**SHA-256 (required, RTL core recommended).** Everything else in the fabric is built on it: image digests,
the secure element MAC protocol, HMAC, and key derivation. A hardware core keeps boot time short when hashing
a whole firmware image. One shared core can serve all users.

**Secure element MAC protocol.** The fabric recomputes the MACs that the secure element returns, so the I2C bus
cannot forge or replay results. Needed for:
- Counter reads: Nonce, then GenDig over the counter, then MAC with the pairing key.
- Signature verify results: Verify, with the result MAC'd by the IO protection key.
- Encrypted reads and writes of keys (EncRead/EncWrite, which use SHA-256 derived keystreams).

The exact digest layouts are defined by Microchip's command formats. Implement them from cryptoauthlib
and test each one against real parts before any zone is locked.

**Fabric nonce source.** The fabric must put its own fresh value into each Nonce command (NumIn).
If it only uses the secure element's random output, a device on the bus can replay an old exchange.
Options, smallest first:
- A ring-oscillator TRNG with health tests (no external dependency).
- A free-running counter combined with the SE serial number and a boot count. This is weaker: it must never repeat across power cycles.

**AES-256-GCM, or AES-256-CTR with HMAC-SHA256.** Decrypts and authenticates firmware read from flash at boot,
and encrypts it on update. GCM needs an AES core plus a GHASH (GF(2^128) multiply). CTR plus HMAC reuses the
SHA-256 core and needs only the AES encrypt direction. Either is fine; CTR plus HMAC is likely smaller.
The secure element's AES is single-block over I2C and too slow for whole images.

**Key wrap for pairing key rotation.** The update package carries the next release's pairing key,
encrypted under the current one. The fabric unwraps it and writes it to the secure element with an
authorized encrypted write. Sequencing across power failures still needs to be designed (see Open Questions).

**HMAC-SHA256 for UART authentication.** The fabric issues a challenge from its nonce source and checks the
host's response, using a key read from the secure element.

**Support logic (not cryptographic).**
- I2C master with the secure element's CRC-16 (polynomial 0x8005, initial value 0, LSB first), wake, idle and sleep handling.
- QSPI flash driver with A/B image slots, so a failed update never leaves the device without a bootable image.
- UART framing with CRC-32.

## Secure element

Fixed in silicon; we only configure and lock it.

- ECDSA P-256 verify against a stored public key
- SHA-256 and the Nonce, GenDig, MAC, CheckMac, EncRead and EncWrite commands
- Two monotonic counters (maximum 2,097,151)
- IO protection key for MAC'd results
- TRNG
- Configuration and data zone locks

## Not needed

These are deliberately absent from the fabric:

- ECDSA, Ed25519 and RSA (no bignum or elliptic-curve arithmetic)
- PUF and fuzzy extractor (the secure element holds device-unique keys)
- Any algorithm specific to one FPGA family

## Open Questions

1. **Pairing key rotation sequencing.** The order of operations for writing a new bitstream, installing the next pairing key and advancing the counter, such that a power failure at any point leaves a bootable, non-rollbackable device.
2. **Secure element protocol details.** Confirm that GenDig over the counter zone, Verify with IO protection, and EncWrite of the pairing key slot all work as expected on the ATECC608B, and separately on the MOD8ID.
3. **AES mode choice.** GCM or CTR plus HMAC, decided by measured fabric area on the smallest target FPGA.
4. **Nonce source.** Whether a ring-oscillator TRNG is reliable enough across the supported FPGA families, or whether the counter fallback is acceptable.
