# Lattice ECP5

**Part:** LFE5U-25F-6BG256C: 24K LUTs, 1,008 Kbit (126 KB) of block RAM in 56 EBRs, 28 multipliers, speed grade 6, 256-ball BGA.
**Status: dropped.** With the Logos2 as the target and the Ti60 as a known-good fallback, a family without bitstream authentication has no role; this folder is kept for the record. The ECP5 fails wish-list item 1: it encrypts bitstreams (AES-128, key in eFuse)
but does not authenticate them, so its configuration engine is a confidentiality anchor only. Like every candidate it has no cipher block the fabric can use; the design's masked Ascon core is soft logic on it as on the others, and the LFE5U-25F is tight for it.

## What "encrypted but unauthenticated" means here

Without a MAC, an attacker who can write the flash can modify the ciphertext blindly. The secure element limits the damage: a bitstream whose pairing key was scrambled by an edit gets nothing,
and a bitstream that does not pass the configuration CRC does not configure. A targeted useful edit without the key is impractical but not proven impossible (R32, F10). Because the configuration engine
cannot refuse an old bitstream, the pairing-key ratchet is what makes a superseded ECP5 bitstream useless, exactly as on the Logos2.

## The wish list

| # | Requirement (`fpga/README.md`) | ECP5 |
|---|---|---|
| 1 | Encryption and authentication | **Encryption only.** AES-128 with the key in eFuse key storage, programmed at enrollment. No MAC, no signature (R32) |
| 2 | No fallback to unencrypted | The decrypt-only eFuse forces every incoming bitstream to be decrypted with the stored key |
| 3 | Readback disabled, key not readable | Readback disable is a bitstream preference setting; eFuse key storage (what JTAG can do to it afterwards is open question F10) |
| 4 | Master SPI self-configuration with multi-boot | Master SPI and dual-boot are supported (sysCONFIG); the golden-image rule and addresses are to be confirmed and the flash map adjusted (F10) |
| 5 | Per-device constants from a script | Lattice Diamond's ECO editor, from a headless Tcl script, writes the key EBRs' `INIT_00` to `INIT_3F` properties in the routed design |
| 6 | Room for a masked Ascon core | Tight on the LFE5U-25F (below); the LFE5U-45F is comfortable |
| 7 | Ring-oscillator TRNG | To confirm with Diamond's timing and DRC settings |
| 8 | Enough logic | About 13K to 24K LUTs for both cores, the masked Ascon and SHA-256 cores and the security blocks leaves little or nothing of 24K for the application; plan on the LFE5U-45F, or an unmasked Ascon core with the loss noted in R33 |
| 9 | QSPI and peripheral pins | General I/O |

JTAG boundary scan stays available after the security settings (R43).

## Toolchains

- **Production:** Lattice Diamond, with a free Lattice software licence. `bitgen` encrypts only designs placed and routed by Diamond (`.ncd`), so production bitstreams come from Diamond.
  Synthesis can be Yosys (EDIF into Diamond) or Diamond's own.
- **Development:** Yosys, nextpnr and `ecppack`, unencrypted, on unlocked boards.
- The same RTL, constraints and tests must run on both builds (F10).

## Enrollment

Replaces step 3 of `doc/enrollment.md`:

1. Over JTAG (Diamond Programmer), program the device's AES-128 configuration key, from the HSM, into eFuse key storage.
2. Burn the decrypt-only eFuse.
3. Readback disable is set in every production bitstream's preferences.

The key crosses the JTAG link once, inside the controlled area.

## Bitstream build

1. Diamond builds the common design once per FPGA release, with placeholder constants in the key-source EBRs, producing an `.ncd`.
2. For each device, a headless Diamond Tcl script opens a copy in the ECO editor, writes the device's inherited and own pairing keys and the version into the key EBRs' `INIT` properties,
   and runs `bitgen` with encryption under the device's configuration key. No re-place-and-route: seconds per device.
3. The bitstream build service erases the keys and the HSM signs the manifest (`doc/enrollment.md`).

The key EBRs are placed by constraint so the script can find them by name in every build.

## Bitstream size

About 0.6 to 0.7 MB, well within the flash's bitstream slots.

## Risks specific to the ECP5

- **R32:** no bitstream authentication; blind edits limited by the configuration CRC and the pairing key check.
- **R5:** the configuration decryptor is not hardened and accepts chosen ciphertexts (no authentication), so it is the weakest of the candidates against power analysis; a break exposes one device. R33 is the same as on every family: our masked cores.
- **R43:** boundary scan after locking.

Units built on the ECP5 should be counted and tracked in the enrollment database, so the fleet's exposure to these risks is known.

## Open questions

F10 in `doc/questions.md`: eFuse burn order and JTAG access afterwards, encryption mode and CRC width, master SPI dual-boot layout, and keeping the development and production flows equivalent.
