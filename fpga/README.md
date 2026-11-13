# FPGA Families

Everything that depends on the FPGA family lives here, one folder per family. The rest of `thriller` (`doc/hw.md`, `doc/xip.md`, `doc/tpm.md`, the RTL and the Forth) is family-neutral,
and is also the ASIC design. Each family folder holds its notes, its build and key-insertion scripts, its constraints, and its primitive wrappers (block RAM, clocks, ring oscillator).

| Family | Folder | Status |
|---|---|---|
| Efinix Titanium (Ti60) | [`ti60/`](ti60/README.md) | **Known good: fallback.** Meets items 1 to 5 (RSA-4096 authentication, BRAM Initial Content Updater) |
| Pango Logos2 (PG2L50H-6IFBG484) | [`logos2/`](logos2/README.md) | **Known good: target.** Items 1 to 4 met; item 5 pending the DRM INIT test (F1) |
| Microchip PolarFire | [`polarfire/`](polarfire/README.md) | Candidate |
| Lattice CrossLink-NX (LIFCL) | [`lifcl/`](lifcl/README.md) | Candidate |

## The wish list

What a family must provide, in order of how much the design depends on it. Items 1 to 4 are hard requirements; a family that fails any of them is a fallback at best.

| # | Requirement | Why |
|---|---|---|
| 1 | **Bitstream encryption and authentication** by the configuration engine, under a key the manufacturer programs into each device, decrypted and checked only inside the FPGA | The configuration engine is the sole integrity anchor for what the device runs: there is no external verifier (R17, R31, R32). Authentication is what separates a target from a fallback |
| 2 | **No fallback** to an unencrypted or unsigned bitstream, on every configuration port | Otherwise anyone can load their own design (R17) |
| 3 | **Readback disabled, key storage that cannot be read out** over JTAG or from the fabric | The pairing keys are constants in the bitstream (R31) |
| 4 | **Self-configuration from a QSPI flash in master SPI mode, with a multi-boot or dual-boot fallback** to a second bitstream image | There is no microcontroller to choose a slot; a bad update must not brick the unit (R44, `doc/flash.md`) |
| 5 | **Per-device constants in a routed design, from a script**, then encryption and signing, without placing and routing again; **or** a vendor engine the fabric can drive under the eFuse or a PUF-protected key, so the pairing keys can be wrapped in flash and the bitstream kept common | The bitstream build service makes one bitstream per device (R42, `doc/enrollment.md`), unless wrapped keys remove the need (`doc/fpga.md`, Wrapped pairing keys). Efinix has a BRAM Initial Content Updater; Diamond has ECO INIT edits; PDS's Tcl guide has neither (F1) |
| 6 | **Room and freedom for a masked Ascon core:** no vendor cipher block is assumed (none of the candidates offers one the fabric can use with power-analysis hardening), so the family must only not get in the way: ordinary LUT logic, no DRC objection to the share registers, and a TRNG rate sufficient for mask refresh | All of the FPGA's key-dependent symmetric work runs in our own masked core (R33, `doc/hw.md`) |
| 7 | **Combinational loops allowed** for a ring-oscillator TRNG | The FPGA needs its own nonces (`doc/fpga.md`) |
| 8 | **Enough logic:** about 17K to 30K 4-input-LUT equivalents for the three cores, the masked Ascon and SHA-256 cores, the TPM session cipher and the security blocks, plus the application; block RAM for the boot ROM (8 to 16 KB), two caches, CPU memory and buffers | `doc/hw.md`, Resource estimate |
| 9 | **A QSPI flash interface** shared between the configuration engine at power-up and the fabric afterwards, plus pins for the TPM's SPI and reset, the RTC's I2C, the card, three UARTs, two I2S buses, the CODEC I2C and the LCD | `doc/hw.md` |

**Desirable:** hardening of the configuration decryptor against power analysis and glitching (R5); on-die voltage and clock monitors; permanent JTAG disable (R43); revocation of the vendor signing key;
a vendor-provided hardened PUF that wraps the configuration key or user keys (it costs nothing to use and models the ASIC); a licence that runs headless; a country of origin acceptable in the target markets (F11).

## What each family folder records

1. How each item above is met, or why it is not.
2. Enrollment steps for the FPGA (key programming, locks), replacing step 3 of `doc/enrollment.md`.
3. The master SPI configuration and multi-boot layout, replacing the generic bitstream slots in `doc/flash.md`.
4. The build and key-insertion flow for the bitstream build service.
5. Device resources and the expected fit.
6. Changes to the risk assessment (`doc/arch.md`), and open questions.

## Module

Each FPGA type has a demo module, about 80-100 cm2, with a pair of 100-pin mezzanine (Board to Board) connectors.
A mating bench board contains connectors for power, UART, ISP, magjack, etc. Some mezzanine connectors are:

- GT-B0403FSV14-100B1101, 0.4mm pitch, 1.4mm height
- GT-B0403FSV29-100B1101, 0.4mm pitch, 2.9mm height
- GT-B0403FSV39-100B1101, 0.4mm pitch, 3.9mm height
- GT-B0403MSV11-100B1101, 0.4mm pitch, 1.1mm height

Depending on how you pair the above, the board stacking height is 2.5, 4, or 5 mm.
The module uses a pair of GT-B0403MSV11-100B1101.

