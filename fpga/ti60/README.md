# Efinix Titanium Ti60

**Status:** candidate. Not evaluated in depth; facts below are from Efinix's bitstream security application note and need confirming against the Ti60 datasheet.

## Requirements

| # | Requirement (`fpga/README.md`) | Ti60 |
|---|---|---|
| 1 | Bitstream encryption, per-device key | AES-256, key programmed into eFuses |
| 2 | No fallback to unencrypted | **Only with authentication:** with just the AES key in eFuse, the device still accepts plaintext bitstreams. With RSA authentication enabled (RSA-4096 public key data in eFuse), it accepts only bitstreams signed with the matching private key |
| 3 | Readback disabled | To confirm; Efinix offers permanent JTAG disable options |
| 4 | Key not readable | eFuse; to confirm |
| 5 | Configured by the C5 | Passive SPI configuration, to confirm; pins for the link afterwards to confirm |
| 6 | Per-device constants from a script | Unknown: whether Efinity can update block RAM contents in a routed design from a script |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | Ti60 is a 60K-logic-element class part; ample |
| 9 | QSPI flash interface | General I/O |
| — | Bitstream authentication | **Yes, RSA-4096.** Closes R32 |

## How it would be used

Both features together: each device gets its own AES-256 key, and the fleet shares one RSA-4096 bitstream signing key held in the manufacturer's HSM.
Authentication makes requirement 2 hold and removes blind bitstream edits (R32). The RSA signing key is the vendor's root of trust for configuration; it is not quantum-safe,
but a forged bitstream would still need this device's link key to pass the handshake.

Efinix also offers a permanent JTAG disable that leaves only device-information instructions, which would remove the boundary-scan exposure (R43), at the cost of board test access.

## Open questions

1. Per-device block RAM contents in a routed Efinity design, from a script.
2. Passive configuration from the C5, and pin reuse for the link.
3. Readback and key read-out protection; behavior of the JTAG disable options.
4. Licence and headless operation of Efinity.
