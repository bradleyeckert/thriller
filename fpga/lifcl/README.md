# Lattice CrossLink-NX (LIFCL)

**Status:** candidate. The LIFCL-17 was the second choice in the earliest design, which used its hardware bitstream authentication. Facts below need confirming
against Lattice's *Advanced Configuration Security User Guide for Nexus Platform* (FPGA-TN-02176).

## The wish list

| # | Requirement (`fpga/README.md`) | CrossLink-NX |
|---|---|---|
| 1 | Encryption and authentication, per-device key | AES-256 encryption with a user-programmed key, and **ECDSA authentication** checked by the configuration engine (Radiant 2.2 or later). Closes R32 |
| 2 | No fallback | To confirm: whether the part can be set to require encrypted and signed bitstreams on every port; JTAG has priority over the other modes |
| 3 | Readback disabled, key not readable | To confirm; OTP key storage expected |
| 4 | Master SPI self-configuration with multi-boot | Master SPI and dual-boot are Nexus features; addresses and golden-image rules to confirm. ECDSA authentication disables Early I/O Release |
| 5 | Per-device constants from a script | Unknown: whether Radiant can update block RAM contents in a routed design from a script |
| 6 | Hard AES block | **None** known to be usable from the fabric. Soft AES, unprotected (R33) |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | LIFCL-17 is a 17K-logic-cell part: too tight for two cores plus soft AES. The LIFCL-40 is the realistic choice |
| 9 | QSPI and peripheral pins | General I/O |

## Toolchain

Lattice Radiant; its free Base licence covers the LIFCL-17 (confirm that it covers the security features). Open-source support (nextpnr for Nexus) is experimental and would not produce encrypted bitstreams.

## Open questions

1. Encryption key storage, and the settings that force encrypted and authenticated configuration on every port.
2. Per-device block RAM contents in a routed Radiant design, from a script.
3. Fit on the LIFCL-40 with soft AES.
4. Master SPI dual-boot layout.
