# Pango Logos2 (PG2L50H)

**Part under consideration:** PG2L50H-6IFBG484 (50K-class logic, speed grade 6, industrial temperature, 484-ball BGA).
**Status:** current choice, with the ECP5 as fallback. Its bitstream security meets the hard requirements of the wish list, and its DPA-protected hard AES block carries all of the FPGA's cryptography.
The deciding unknowns are the build flow (item 5, F1) and the master SPI multi-boot behavior (item 4, F3).

## What the datasheet claims

From the *Logos2 Family FPGAs Device Datasheet*:

- AES-256-GCM bitstream encryption with "self-authentication", plus RSA-2048 bitstream signatures over a SHA-3 digest.
- Key storage in eFuse or battery-backed RAM (BB-RAM).
- Protection against bitstream readback.
- JTAG security management, including permanently disabling JTAG.
- Protection against differential power analysis (DPA) of the key.

## The wish list

| # | Requirement (`fpga/README.md`) | Logos2 |
|---|---|---|
| 1 | Encryption and authentication, per-device key | AES-256-GCM with the key in eFuse, programmed per device at enrollment, and RSA-2048 signatures. **Yes, twice.** Closes R32 |
| 2 | No fallback | **Assumed:** both encryption and signing are supported in hardware, so both are enforced (to confirm, F2) |
| 3 | Readback disabled, key not readable | Yes (claimed); eFuse; JTAG permanently disabled when locked |
| 4 | Master SPI self-configuration with multi-boot | Master SPI is a standard mode on the family; the multi-boot or golden-image mechanism, its addresses and how the fabric points at the other slot are **to confirm (F3)** |
| 5 | Per-device constants from a script | **Not in the Tcl guide** (see Per-device keys below). The primary plan is now wrapped pairing keys under the eFuse key through the hard AES block (F5), which needs no per-device bitstream |
| 6 | Hard AES block, DPA-protected, usable from the fabric | Yes (claimed). Open (F4): AES-256 support, GHASH, throughput for three users, instances, key-loading interface |
| 7 | Ring-oscillator TRNG | To confirm |
| 8 | Enough logic | A 50K-class part: ample room for both cores, the security blocks and the application. LUT size and block RAM to confirm |
| 9 | QSPI and peripheral pins | General I/O; 484 balls |

## What it improves over the ECP5

| Risk | ECP5 | Logos2 |
|---|---|---|
| R32: blind edits to an encrypted bitstream | Open: no MAC, only the CRC | **Closed:** AES-GCM authenticates every bitstream under the device's own key; RSA-2048 adds an origin signature |
| R5, R33: power analysis | Neither configuration nor soft AES hardened | **DPA protection** for configuration and for the hard AES block |
| R43: boundary scan after locking | Remains available | **Can be removed** by permanently disabling JTAG, after the board's boundary-scan test at the factory |
| Bitstream key size | AES-128 | AES-256 |
| Fit | 24K LUTs, tight | 50K class, roomy |

## The hard AES block

Pango's DPA protection covers configuration and the **hard AES block in the fabric**. That is why the design uses AES-256 rather than Ascon: the XIP engine, the recording engine and the install
port all run their cryptography in that block, and the key registers feed it directly. Open (F4): AES-256 support, whether the block computes GHASH (if not, AES-CCM so that no key-dependent step
runs in unprotected fabric), throughput, number of instances, and the key-loading interface. Also open (F5): whether the block can use the eFuse key, or a key derived from it, which would let the pairing
keys be wrapped rather than stored in the bitstream.

## Key storage: eFuse or BB-RAM

- **eFuse (base choice):** permanent, needs no battery, matches every other family here.
- **BB-RAM:** the key lives in battery-backed RAM and can be erased instantly, which would allow a tamper response from the enclosure switch (Q7). The cost is a coin cell, and a device whose
  battery dies also stops working, which is probably unacceptable for a medical device.

## Enrollment

Replaces step 3 of `doc/enrollment.md`:

1. Run the board's boundary-scan test.
2. Program the device's AES-256 key (from the HSM) into eFuse, and the RSA-2048 public key data.
3. Set whatever forces encrypted and signed configuration, and disables readback (to confirm, F2).
4. After the first boot and the attestation check, permanently disable JTAG.

## Flash and multi-boot

To be written from Pango's configuration documentation (F3): the master SPI mode pins, the bitstream address, the multi-boot or fallback mechanism, and how the loader redirects it to the other slot.
The bitstream slots in `doc/flash.md` are sized at 4 MB pending F9.

## Toolchain

Pango Design Suite (PDS), proprietary, runs from the command line. There is no open-source place-and-route for Logos2, so the development flow is PDS too.
Scripted block RAM updates with encryption and signing (F1) are open; see Per-device keys below.
License is free, but getting set up is not obvious. The steps are:

1. Create an account at https://www.pangomicro.com/en/
1. Once approved, log in using your email address and password (the password field is labeled PIN)
1. Apply for a node-locked license for PDS.
1. Download PDS. It is 2.0 GB, so it will take a while.
1. You will get an email about your MAC being approved. That means your license file is ready. 
1. Download the PDS license file from https://www.pangomicro.com/en/member/license/
1. Create a new environmental variable PANGO_LICENSE_FILE that points to it.
1. Launch PDS.

## Per-device keys: what the Tcl guide says

Read against the *Tcl Command User Guide* v2.0 (October 2023, 119 pages), the only version in hand:

**Present.** `pds_shell -file script.tcl` and `pds_shell -project design.pds -run gen_bit_stream` run headless. `gen_bit_stream` accepts `-input_db_file`, so a bitstream can be generated from a saved
place-and-route database without re-running PnR. That is the half of F1 that works.

**Absent.**
1. Any command that sets bitstream options. `gen_bit_stream` takes only `-of_flow`, `-force_to_run` and `-input_db_file`; there is no `set_property` or equivalent for encryption, key files, signing or
   security bits among the guide's commands. Those are project settings made in the GUI and stored in the `.pds` file; `import_project_settings -gen_bit_stream` copies them between projects, and
   `export_project_tcl` and `open_config` (the Configuration component) are marked "only supported in the GUI interface."
2. Any command that changes memory initialization in a routed design. The Design Editor commands (`move_cell`, `manual_route`, `new_net`, `copy_inst`, `save_adif`) edit placement and routing;
   `define_attribute` handles only `PAP_REGION` and `PAP_LOC`. There is no equivalent of Xilinx `updatemem`, Efinix's BRAM Initial Content Updater, or Diamond's ECO INIT edit.

**Consequences, in order of preference:**
1. **Wrapped pairing keys (F5), the primary plan.** If the hard AES block can decrypt under the eFuse key or a derivative, the bitstream is common to the fleet and no per-device build is needed
   (`doc/fpga.md`, Wrapped pairing keys).
2. **Ask Pango support** for what the Tcl guide omits: a DRM memory-update tool for a routed DB or a bitstream; a standalone encrypt-and-sign step on a plaintext bitstream file; whether a key file referenced
   by path in the `.pds` project can be swapped per device and `gen_bit_stream -input_db_file` rerun to re-encrypt without PnR.
3. **Patch the bitstream.** Generate an unencrypted bitstream from the DB, locate the key DRM frames by diffing two builds with different placeholder constants, patch per device, then encrypt and sign.
   Workable only if step 2 yields a standalone encrypt-and-sign step; reimplementing Pango's AES-256-GCM-plus-RSA bitstream format is not realistic.
4. **Per-device synthesis and PnR** with the keys as Verilog parameters: minutes per device and different routing per unit. Not acceptable at fleet scale.

## Other considerations

- Documentation is mostly in Chinese; some details may only be available through Pango's support.
- Supply chain, availability and **country of origin** for the target markets should be checked alongside the technical evaluation (F11). PolarFire is the candidate to compare against if origin matters.
- It fits the ICS55 direction (`doc/ics55.md`): a domestic Chinese FPGA now, a domestic 55 nm ASIC later.

## Answers so far, and what remains

| Question | Answer |
|---|---|
| Encrypted-only and signed-only configuration | Unknown; both are supported in hardware, so the design assumes both are enforced (F2) |
| Master SPI self-configuration and multi-boot | **Open (F3)** |
| JTAG access to the eFuse key before JTAG is disabled | Unknown; a locked device has JTAG permanently disabled |
| DPA protection | Covers configuration and the hard AES block in the fabric |
| PDS from the command line | Yes |
| Block RAM contents in a routed design, from a script, then encrypt and sign | **Not in the Tcl guide v2.0;** three questions for Pango support (F1, now the fallback) |
| Hard AES block: AES-256, GHASH, throughput, instances, key loading | **Open (F4)** |
| Hard AES block using the eFuse key | **Open (F5), now the primary plan** for per-device keys |
