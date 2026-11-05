# FPGA Families

Everything that depends on the FPGA family lives here, one folder per family. The rest of `thriller` (`doc/fpga.md`, `doc/xip.md`, the RTL of the security blocks,
the C5 side) is family-neutral. Each family folder will hold its notes, its build and key-insertion scripts, its constraints, and its primitive wrappers
(block RAM, clocks, ring oscillator).

| Family | Folder | Status |
|---|---|---|
| Lattice ECP5 (LFE5U-25F-6BG256C) | [`ecp5/`](ecp5/README.md) | **Current choice** |
| Lattice CrossLink-NX (LIFCL) | [`lifcl/`](lifcl/README.md) | Candidate |
| Efinix Titanium (Ti60) | [`ti60/`](ti60/README.md) | Candidate |
| Pango Logos2 (PG2L50H-6IFBG484) | [`logos2/`](logos2/README.md) | Strong candidate |
| Pango Logos (PGL25G) | [`logos/`](logos/README.md) | Not usable: no bitstream encryption |

## What a family must provide

| # | Requirement | Why |
|---|---|---|
| 1 | **Bitstream encryption** under a key that the manufacturer programs into each device, decrypted only inside the FPGA | The link and image keys travel inside the bitstream (R31) |
| 2 | **No fallback** to an unencrypted bitstream (or, with authentication, to an unsigned one) | Otherwise anyone can load their own design (R17) |
| 3 | **Readback disabled** | Otherwise the configured keys can be read back |
| 4 | **Key storage that cannot be read out** over JTAG or from the fabric | The configuration key is the device's FPGA secret |
| 5 | **Configuration by an external microcontroller** (slave SPI or similar), with pins for the link afterwards | The C5 stores and chooses the bitstream |
| 6 | **Per-device constants in a routed design, from a script**, then encryption, without placing and routing again | The bitstream build service makes one bitstream per device (R42) |
| 7 | **Combinational loops allowed** for a ring-oscillator TRNG | The FPGA needs its own nonces (R36) |
| 8 | **Enough logic:** about 7K to 12K 4-input LUTs for the security blocks and CPU, plus the application; block RAM for a 4 KB cache, CPU memory and buffers | `doc/fpga.md`, Resource estimate |
| 9 | **A QSPI flash interface** for XIP | `doc/xip.md` |

**Desirable:** bitstream authentication (closes R32); hardening of the configuration decryptor against power analysis (R33); a free or low-cost licence that runs headless.

## What each family folder records

1. How each requirement above is met, or why it is not.
2. Enrollment steps for the FPGA (key programming, locks), replacing step 7 of `doc/enrollment.md`.
3. The build and key-insertion flow for the bitstream build service.
4. Device resources and the expected fit.
5. Changes to the risk assessment (`doc/arch.md`), and open questions.
