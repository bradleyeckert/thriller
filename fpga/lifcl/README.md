# Lattice CrossLink-NX (LIFCL)

**Status:** candidate. The LIFCL-17 was the second choice in the earliest design, which used its hardware bitstream authentication. Facts below need confirming
against Lattice's CrossLink-NX security documentation.

## Requirements

| # | Requirement (`fpga/README.md`) | CrossLink-NX |
|---|---|---|
| 1 | Bitstream encryption, per-device key | AES encryption with a user-programmed key; key size and storage to confirm |
| 2 | No fallback to unencrypted | To confirm: whether the part can be set to require encrypted and signed bitstreams |
| 3 | Readback disabled | To confirm |
| 4 | Key not readable | To confirm |
| 5 | Configured by the C5 | Slave SPI configuration, to confirm; pins for the link afterwards to confirm |
| 6 | Per-device constants from a script | Unknown: whether Lattice Radiant can update block RAM contents in a routed design from a script |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | LIFCL-17 is a 17K-logic-cell part: tight against 7K to 12K for the security blocks and CPU. The LIFCL-40 leaves room |
| 9 | QSPI flash interface | General I/O |
| — | Bitstream authentication | **Yes, ECDSA**, checked by the configuration engine. Closes R32 |

## Toolchain

Lattice Radiant; its free Base licence covers the LIFCL-17. Open-source support (nextpnr for Nexus) is experimental and would not produce encrypted bitstreams.

## Open questions

1. Encryption key size, key storage, and the settings that force encrypted and authenticated configuration.
2. Per-device block RAM contents in a routed Radiant design, from a script.
3. Fit on the LIFCL-17, or move to the LIFCL-40.
