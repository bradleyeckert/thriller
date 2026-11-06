# Lattice ECP5

**Part:** LFE5U-25F-6BG256C: 24K LUTs, 1,008 Kbit (126 KB) of block RAM in 56 EBRs, 28 multipliers, speed grade 6, 256-ball BGA.
This is the **fallback**; the current choice is the Pango Logos2 PG2L50H (`fpga/logos2/`). The ECP5 has no hard AES block, so its AES-256 cores and GHASH are soft logic, unprotected against power analysis.

## Requirements

| # | Requirement (`fpga/README.md`) | ECP5 |
|---|---|---|
| 1 | Bitstream encryption, per-device key | AES-128 with the key in eFuse key storage, programmed at enrollment |
| 2 | No fallback to unencrypted | The decrypt-only eFuse forces every incoming bitstream to be decrypted with the stored key |
| 3 | Readback disabled | Bitstream preference setting |
| 4 | Key not readable | eFuse key storage (what JTAG can do to it afterwards is open question F10) |
| 5 | Configured by the C5 | Slave SPI port; the same pins carry the link after configuration |
| 6 | Per-device constants from a script | Lattice Diamond's ECO editor, from a headless Tcl script, writes the key EBRs' `INIT_00` to `INIT_3F` properties in the routed design |
| 7 | Ring-oscillator TRNG | To confirm with Diamond's timing and DRC settings |
| 8 | Enough logic | About 11K to 16K LUTs for the security blocks (with soft AES) and CPU leaves roughly 6K to 13K for the application |
| 9 | QSPI flash interface | General I/O |
| — | Bitstream authentication | **None.** Encryption has no MAC, so an encrypted bitstream could be edited blindly (R32) |

JTAG boundary scan stays available after the security settings (R43).

## Toolchains

- **Production:** Lattice Diamond, with a free Lattice software licence. `bitgen` encrypts only designs placed and routed by Diamond (`.ncd`), so production bitstreams
  come from Diamond. Synthesis can be Yosys (EDIF into Diamond) or Diamond's own.
- **Development:** Yosys, nextpnr and `ecppack`, unencrypted, on unlocked boards.
- The same RTL, constraints and tests must run on both builds (open question F10).

## Enrollment

Replaces step 7 of `doc/enrollment.md`:

1. Over JTAG (Diamond Programmer), program the device's AES-128 configuration key, from the HSM, into eFuse key storage.
2. Burn the decrypt-only eFuse.
3. Readback disable is set in every production bitstream's preferences.

The key crosses the JTAG link once, inside the controlled area.

## Bitstream build

1. Diamond builds the common design once per FPGA release, with placeholder key constants in dedicated EBRs, producing an `.ncd`.
2. For each device, a headless Diamond Tcl script opens a copy in the ECO editor, writes the device's link and image keys into the key EBRs' `INIT` properties,
   and runs `bitgen` with encryption under the device's configuration key. No re-place-and-route: seconds per device.
3. The bitstream build service erases the keys and the HSM signs the package (`doc/enrollment.md`).

The key EBRs should be placed with constraints so the script can find them by name in every build.

## Bitstream size

About 0.6 to 0.7 MB, well within the C5's bitstream slots.

## Risks specific to the ECP5

- **R32:** no bitstream authentication; blind edits limited by the configuration CRC (width and mode: open question F10).
- **R33:** neither the configuration decryptor nor the soft AES cores are hardened against power analysis; a break exposes one device.
- **R43:** boundary scan after locking.

## Open questions

F10 in `doc/questions.md`: eFuse burn order and JTAG access afterwards, encryption mode and CRC width, and keeping the development and production flows equivalent.
