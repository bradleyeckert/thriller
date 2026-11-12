# Microchip PolarFire

**Status:** candidate, added for its security feature set and its country of origin (Microchip, Chandler, Arizona; the die is foundry-made, so the marked origin is the assembly site,
to confirm per part number). Not evaluated in depth; facts below are from Microchip's PolarFire security documentation and need confirming against the datasheet and Libero's capabilities.

## Why it is worth a column

PolarFire is a flash-based FPGA: the configuration lives in on-chip flash and the part is live at power-up, with no external bitstream read on every boot. Its security block was designed
for exactly the role `thriller` gives the FPGA:

- bitstream encryption (AES-256) and authentication, with the programming key in on-chip storage;
- DPA-resistant programming and crypto, under licensed countermeasures;
- an **SRAM PUF** that protects keys in the secure NVM (sNVM), so a user key can be stored wrapped under a PUF-derived key rather than as a bitstream constant;
- on-die tamper detectors (voltage, temperature, clock) with zeroization options;
- on "S" variants, a hardware crypto coprocessor (AES, SHA, ECC, RSA, DRBG) with DPA countermeasures, reached through the system controller;
- a digest-check service that lets the fabric verify its own configuration at run time.

## The wish list

| # | Requirement (`fpga/README.md`) | PolarFire |
|---|---|---|
| 1 | Encryption and authentication, per-device key | Yes: encrypted and authenticated programming bitstreams under per-device keys. Closes R32 |
| 2 | No fallback | Programming keys and security policies can lock the part against unencrypted or wrongly keyed bitstreams; to confirm the exact settings |
| 3 | Readback disabled, key not readable | Yes (claimed): no configuration readback; keys protected by the PUF |
| 4 | Self-configuration with fallback | **Different model:** configuration is in on-chip flash, so there is no power-up bitstream read. In-application programming from an external SPI flash with a golden and an update image gives the A/B behavior; `doc/flash.md` would change accordingly |
| 5 | Per-device constants from a script | The pairing keys could live in the sNVM under the PUF instead of in the bitstream, so a per-device bitstream might not be needed at all: one common bitstream, per-device sNVM data written at enrollment through the programmer. To confirm |
| 6 | Room for a masked Ascon core | Yes. PolarFire is also the one candidate with a DPA-hardened crypto coprocessor ("S" parts, through system controller services); its service latency rules it out for per-line XIP, but it could handle key unwrapping, which is what the wrapped-key route (F5) needs |
| 7 | Ring-oscillator TRNG | To confirm; the system controller also offers a certified DRBG |
| 8 | Enough logic | MPF100T class and up: ample |
| 9 | QSPI and peripheral pins | General I/O |

**Desirables met:** DPA-resistant configuration, on-die tamper detectors, a hardened PUF (which models the ASIC's key source directly: the key-source module becomes a read from sNVM), JTAG lockdown options.

## What would change in the design

- **The key source** reads the pairing keys from PUF-protected sNVM instead of block RAM constants. The ratchet then writes the next pairing key into sNVM as well as into the secure element,
  and a platform update no longer needs a per-device bitstream: the bitstream build service shrinks to a release build and a signature, which removes R42 from the FPGA side.
- **The flash map** loses the bitstream slots on the FPGA side and gains the IAP golden and update images for the configuration itself.
- **The boot ROM** gains a self-digest check through the system controller as a cheap extra integrity test.

## Costs

- Price: several times the PG2L50H or the LFE5U-25F.
- Libero SoC is the only toolchain; no open-source flow. Licence terms for the security features to confirm.
- The "S" crypto coprocessor's service model is too slow for XIP; lines use the design's own masked Ascon core here as everywhere, and the coprocessor's value is key unwrapping under the PUF-protected key (F5).

## Open questions

1. Settings that lock the part to encrypted and authenticated programming on every port.
2. sNVM as the pairing-key store: capacity, PUF protection mode, write endurance for the ratchet, and whether the fabric can read it without the key crossing a bus.
3. Crypto coprocessor latency and throughput from the fabric.
4. IAP golden and update image behavior on power loss.
5. Country of origin as marked, per part number.
