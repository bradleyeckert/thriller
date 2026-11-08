# Efinix Titanium Ti60

**Status:** candidate. Not evaluated in depth; facts below are from Efinix's *Titanium Security Feature* application note and need confirming against the Ti60 datasheet.

## The wish list

| # | Requirement (`fpga/README.md`) | Ti60 |
|---|---|---|
| 1 | Encryption and authentication, per-device key | AES-GCM-256 with the key in eFuses, and **RSA-4096 authentication** with the public key hash in eFuses. Closes R32 |
| 2 | No fallback | **Only with authentication:** with just the AES key in eFuse, the device still accepts plaintext bitstreams. With RSA authentication enabled it accepts only bitstreams signed with the matching private key |
| 3 | Readback disabled, key not readable | eFuse; to confirm. Efinix offers a permanent JTAG disable that leaves only device-information instructions (removes R43) |
| 4 | Master SPI self-configuration with multi-boot | Active SPI configuration from flash and multi-image support are Titanium features; addresses and fallback rules to confirm |
| 5 | Per-device constants from a script | Unknown: whether Efinity can update block RAM contents in a routed design from a script |
| 6 | Hard AES block | **None** known to be usable from the fabric. Soft AES, unprotected (R33) |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | Ti60 is a 60K-logic-element class part; ample even with soft AES |
| 9 | QSPI and peripheral pins | General I/O. Security is unavailable with compressed bitstreams and on W64 packages |

## How it would be used

Both features together: each device gets its own AES-256 key, and the fleet shares one RSA-4096 bitstream signing key held in the manufacturer's HSM. The RSA key is the vendor's root of trust for
configuration; it is not quantum-safe (R24), but a forged bitstream would still need this device's encryption key and pairing key.

## Open questions

1. Per-device block RAM contents in a routed Efinity design, from a script.
2. Active SPI multi-image layout and fallback behavior.
3. Readback and key read-out protection; behavior of the JTAG disable options.
4. Licence and headless operation of Efinity.
