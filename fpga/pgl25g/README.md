# Pango Logos PGL25G

**Status:** under evaluation. The deciding question is whether the PGL25G has bitstream encryption under a key the manufacturer can program per device,
with a setting that refuses unencrypted bitstreams. Its datasheet, as quoted so far, offers something else.

## What the datasheet offers

> "unique identification number that is uniquely determined at the factory. Users can read the identification number via the UID interface and JTAG interface,
> and incorporate the results into the programming data stream after processing with their own unique encryption algorithm."

This describes a **UID-locking** scheme against cloning: at build time, compute a value from the chip's UID with a secret algorithm or key, put it in the bitstream,
and have the design read the UID at run time through the UID interface, recompute, and refuse to work if the two differ. A bitstream copied to another chip then stops working.

## Why it does not meet our requirements

1. **The UID is not a secret.** Anyone can read it over JTAG. It identifies the chip; it cannot protect anything by itself.
2. **The secret lives in the bitstream.** The "own unique encryption algorithm" and its key, and the comparison logic, are part of the design. If the bitstream is not
   encrypted, they cross the configuration bus and sit in flash in the clear. Anyone who can capture the bitstream can find the check and patch it out, or compute the
   expected value for any UID. The scheme then rests on how hard the bitstream format is to reverse engineer: obscurity, not cryptography.
3. **It protects the wrong asset.** UID locking stops a cloner copying a bitstream to a blank chip. Our bitstream carries per-device keys whose confidentiality matters (R31).
   A UID does nothing for confidentiality.
4. **Deriving our keys from the UID makes things worse.** One could ship a fleet-wide bitstream and derive each device's link key as f(secret, UID). But then one secret, inside every
   bitstream, gives every device's keys, because the UIDs are public. One extraction would break the fleet, where today one break exposes one device.
5. **Even with bitstream encryption, the UID adds little.** If the PGL25G encrypts bitstreams under a per-device key, that alone provides what UID locking was meant to,
   and our design needs nothing more. If it encrypts only under a fleet-wide key, UID locking stops copying but every device still shares that one key.

UID locking is a reasonable answer to IP cloning by a production subcontractor. It is not an answer to a board-level attacker reading keys, which is our threat.

## What would make the PGL25G usable

| # | Requirement (`fpga/README.md`) | PGL25G |
|---|---|---|
| 1 | Bitstream encryption, per-device key | Unknown; the deciding question |
| 2 | No fallback to unencrypted | Unknown |
| 3 | Readback disabled | Unknown |
| 4 | Key not readable | Unknown |
| 5 | Configured by the C5 | To confirm (slave serial or SPI configuration) |
| 6 | Per-device constants from a script | Unknown: whether Pango Design Suite can update block RAM contents in a routed design from a script |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | A 25K-class part, similar to the LFE5U-25F; to confirm |
| 9 | QSPI flash interface | General I/O |

## Without bitstream encryption

The design would degrade, not collapse. A board prober who captures the plaintext bitstream learns that device's link and image keys. They could then read and forge link traffic
(live data and future segment keys) and write their own application code into the FPGA's flash. Past recordings stay safe, because their segment keys were erased and only the host
can decrypt them, and the C5's keys and version records are untouched. That is a weaker tier than the ECP5 gives, and it would have to be stated as such in the risk assessment.

## Questions for Pango

1. Does the PGL25G support bitstream encryption? Algorithm and key size?
2. Where is the key stored (eFuse, OTP, battery-backed), and can it be read back or overwritten over JTAG?
3. Can the device be locked to refuse unencrypted bitstreams?
4. Can readback be disabled permanently?
5. Can Pango Design Suite change block RAM initialization in a routed design from a script, and encrypt the result?
