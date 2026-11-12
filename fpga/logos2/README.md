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
| 2 | No fallback | **Not automatic.** The eFuse key alone does not refuse plaintext bitstreams; separate deciphering and authentication enables must be set and locked (see The F2 caveat) |
| 3 | Readback disabled, key not readable | Encrypted bitstreams cannot be read back or verified (guide 4.3.9.1); eFuse key; JTAGLOCK and SCANLOCK fuse bits |
| 4 | Master SPI self-configuration with multi-boot | Yes: multi-boot stream with golden and application images, built by `cfg_gen_multi_file`; a status-register fallback flag. Golden-image rule and mode pins to confirm (F3) |
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

Replaces step 3 of `doc/enrollment.md`. Everything below is scriptable through the Fabric Configuration tool (`cdt_cfg`), from its *Fabric Configuration User Guide*; see Headless station flow.

1. Run the board's boundary-scan test.
2. Program the device's `.nky` key file into eFuse: the AES-256 key (from the HSM) and the RSA-2048 public key digest (`cfg_program_key_file -key_location 1`).
3. Confirm that decryption and authentication are mandatory (F2, see the caveat below), then lock the key, the digest, and the authentication, decryption and DPA enables (`cfg_efuse_lock`).
4. After the first boot and the attestation check, lock JTAG and scan mode (`cfg_efuse_lock -lock C`, `-lock D`), or lock everything with `-lock FF`.

### Headless station flow

The Fabric Configuration tool runs without its GUI: `cdt_cfg.exe -ip <jtag server> -port 65420 -file station.tcl -args {dev.sbit dev.nky dev_mul.sfc}`, where `%s` placeholders in the
script are filled in order from `-args`; `cdt_cfg_shell.exe` is the terminal version. It talks to the Jtag Server, a TCP service on the station PC (or a remote host) that drives the cable.
A per-device script, from the commands the guide documents (section 4.5):

```tcl
cfg_connect -ip 127.0.0.1 -port 65420
cfg_add_device -file %s                              ;# this device's encrypted .sbit
cfg_read_device_property -mode 1                     ;# device UID, for the enrollment record
cfg_program_key_file -key_location 1 -file %s        ;# .nky into eFuse: 0 = temporary register, 1 = eFuse, 2 = BBRAM
cfg_efuse_lock -lock <index> -password 000000 -status 1   ;# per lock bit, or FF for all; the password is a fixed interlock, not a secret
cfg_read_device_property -mode 4                     ;# eFuse value, for the record
cfg_read_device_property -mode 3                     ;# status register: bit 23 key_lock, bit 22 fallback
cfg_flash_scan_device                                ;# SPI flash through the cable; cfg_jtag_flash_* goes through the FPGA instead
cfg_flash_assign_file -file %s                       ;# the multi-boot .sfc
cfg_flash_program
cfg_flash_verify_checksum
cfg_disconnect
```

Conversions are Tcl too: `cfg_gen_sfc -sbit x.sbit -opcode 107 -device_name <flash>` makes a flash image (opcodes 0x0B/0x3B/0x6B for 24-bit, 0x0C/0x3C/0x6C for 32-bit, single/dual/quad read),
and `cfg_gen_multi_file -type 0 -infile {golden.sfc app.sfc} -outfile dev_mul.sfc -sbit_start_address …` builds the multi-boot stream. The GUI's Tcl record function (Operations → TCL Record File)
writes the commands for any manual sequence, and `cfg_xxx -help` prints each command's options.

`-key_location 0` loads the key into a volatile register, so encrypted bitstreams can be tested on unlocked boards without fusing anything; BBRAM (location 2) can change the AES key later but not the RSA digest.

### eFuse lock bits (Logos2 and Titan2, Table 5-21)

| Index | Name | Locks |
|---|---|---|
| 0 | KEYLOCK | Program key |
| 1 | UIDPLOCK | Program UID |
| 2 | FUSEPLOCK | Program user fuse |
| 3 | EDLOCK | Public key abstract (the RSA digest) |
| 4 | FUSELOCK | User fuse |
| 5 | OBFUSLOCK | Obscure enable |
| 6 | AUTLOCK | Authentication enable |
| 7 | DPALOCK | DPA enable |
| 8 | DRMDPALOCK | DRM DPA enable |
| 9 | DECLOCK | Deciphering enable |
| A | BBKEYLOCK | Power-source (BBRAM) key |
| B | KEYENLOCK | eFuse key enable |
| C | JTAGLOCK | JTAG |
| D | SCANLOCK | Scan mode |
| E | EFUSELOCK | eFuse enable |
| F | IDLOCK | IDCODE program |
| 10 | PRCFGLOCK | Partial reconfiguration |
| 11 | TRIMLOCK | Trim |
| 12 | ID2LOCK | IDCODE2 program |
| FF | all | Every bit above |

JTAGLOCK and SCANLOCK are the permanent JTAG disable the design relies on (R43): documented, one command. The 32 user eFuse bits (`cfg_program_user_efuse -value <32 binary digits>`) are
available for a lifecycle mark if wanted.

### The F2 caveat: does the eFuse key force encryption?

Section 4.3.9.1 says that after a *temporary* key is loaded, "subsequent bitstream files must be encrypted with the key from the .nky file to download successfully; unencrypted bitstreams will fail.
**This restriction does not apply to eFuse key .nky files.**" Read literally, programming the eFuse key does not by itself refuse plaintext bitstreams. The lock table's DECLOCK ("Lock Deciphering Enable")
and KEYENLOCK ("Lock Efuse Key Enable") imply separate enable bits, presumably carried in the `.nky` or set at bitstream generation, that make decryption (and, with AUTLOCK, authentication) mandatory and are then
locked. **Which bit does it, and how the `.nky` sets it, must be answered by Pango before any production part is fused.** Until then wish-list item 2 is open, and the station should verify on a fused sample that a
plaintext bitstream is refused.

## Flash and multi-boot

From the configuration guide (section 4.3.20.3), answering the layout half of F3:

- The multi-boot data stream (Logos, Logos2, Titan2) is built by `cfg_gen_multi_file -type 0` from a golden stream and one or more application streams, each with a settable start address.
- Each application stream has an 8 KB header; each stream gets 108 bytes of desynchronization data appended; every start address must be on a flash sector boundary; a watchdog field follows each stream
  and triggers the fallback to the golden stream when the application stream fails to configure. The status register's bit 22 (`fallback`) reports that the golden stream was used.
- Other types: 1 SPI remote-update stream, 4 remote-upgrade stream, 5 and 7 dual-boot streams (Compact only).

Still open in F3: whether the golden stream must be the fixed image at the base address (then bitstream A in `doc/flash.md` is the enrollment-time image, retired by the ratchet after the first platform update,
and updates alternate between B and a third region) or whether the fabric or the loader can redirect the boot address; and the master SPI mode pins. The bitstream slots in `doc/flash.md` are sized at 4 MB pending F9.

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
place-and-route database without re-running PnR. **Changing the AES or RSA key settings in the project does not invalidate place-and-route; only Generate Bitstream reruns, in about a minute on a
moderate design** (observed in PDS). With blank key names the project draws fresh random keys at each run. So a per-device *encryption* step is cheap, and that step is needed in both plans, since the eFuse
key is per device whether the pairing keys ride in the bitstream or in flash.

**Absent.**
1. Any command that sets bitstream options. `gen_bit_stream` takes only `-of_flow`, `-force_to_run` and `-input_db_file`; there is no `set_property` or equivalent for encryption, key files, signing or
   security bits among the guide's commands. Those are project settings made in the GUI and stored in the `.pds` file; `import_project_settings -gen_bit_stream` copies them between projects, and
   `export_project_tcl` and `open_config` (the Configuration component) are marked "only supported in the GUI interface."
2. Any command that changes memory initialization in a routed design. The Design Editor commands (`move_cell`, `manual_route`, `new_net`, `copy_inst`, `save_adif`) edit placement and routing;
   `define_attribute` handles only `PAP_REGION` and `PAP_LOC`. There is no equivalent of Xilinx `updatemem`, Efinix's BRAM Initial Content Updater, or Diamond's ECO INIT edit.

**Consequences, in order of preference:**
1. **Wrapped pairing keys (F5), the primary plan.** If the hard AES block can decrypt under the eFuse key or a derivative, the bitstream is common to the fleet and no per-device build is needed
   (`doc/fpga.md`, Wrapped pairing keys).
2. **Per-device encryption from the project.** Per device, the station either edits the key file path in the `.pds` (its format to confirm) or leaves the key names blank and harvests the `.nky` PDS generates.
   To settle: the `.nky` format, so HSM-derived AES keys can be written into one (letting PDS's RNG pick them and escrowing the `.nky` is acceptable, since the station is already the trusted build service, R42);
   and the RSA signing key, which must be a fixed named file and never regenerated, and which therefore lives on the isolated station rather than in an HSM. Remaining question for Pango: whether a DRM INIT
   change forces re-synthesis (irrelevant under wrapped keys).
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
| Encrypted-only and signed-only configuration | **Not automatic:** the configuration guide says the eFuse key alone does not refuse plaintext bitstreams; the deciphering and authentication enables (locked by DECLOCK, AUTLOCK, KEYENLOCK) must be set and locked. How the `.nky` sets them: ask Pango (F2) |
| Master SPI self-configuration and multi-boot | Multi-boot stream format and generation known (above); golden-image rule and mode pins open (F3) |
| JTAG access to the eFuse key before JTAG is disabled | Key read-out not offered by the tool (only `cfg_read_device_property -mode 4`, the eFuse value, to confirm what it shows); JTAGLOCK and SCANLOCK fuse bits disable JTAG permanently |
| DPA protection | Covers configuration and the hard AES block in the fabric |
| PDS from the command line | Yes |
| Block RAM contents in a routed design, from a script, then encrypt and sign | **Not in the Tcl guide v2.0;** three questions for Pango support (F1, now the fallback) |
| Hard AES block: AES-256, GHASH, throughput, instances, key loading | **Open (F4)** |
| Hard AES block using the eFuse key | **Open (F5), now the primary plan** for per-device keys |
