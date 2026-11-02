# ICS55

ICS55 is an open-source chip design initiative built on the ECOS toolchain and PDKs from 55nm foundries.
It's conceptually similar to the 130nm open source flow launched previously by Google.

Preliminary research on its SRAM compiler gives a total macro area of 2 to 3 mm2/Mb.
Masked ROM would be quite a bit smaller.

Standardized floorplan blocks are 1.5 x 1.5, 2.0 x 2.0, and 2.5 x 2.5 mm.
These would fit chips with pin counts of 44-64, 80-100, and 144-208 pins.


## Commentary: `thriller` on ICS55

With the root of trust in the ESP32-C5, the ASIC's job is the ECP5's job: a peripheral of the C5. That changes the migration completely.
The earlier design (on the `archive/fpga-rot-v0` branch) put the root of trust in the ASIC itself, which needed a mask ROM boot chain,
a PUF for per-device keys and decrypting caches, because the ICsprout 55nm open PDK lists no OTP, eFuse or embedded flash cells. None of that is needed now.

### What the ASIC needs

- **No secrets and no non-volatile memory.** Keys, versions, pairings and records all stay in the C5.
- **No security logic.** It holds no keys, so it needs no crypto cores, no side-channel or glitch hardening, no lifecycle states and no debug lockdown for security's sake.
- **A build ID register** in fixed logic, read by the C5 after reset, as the FPGA does now (`doc/fpga.md`). On an ASIC it identifies the silicon revision.
- **A self-test** the C5 can trigger.
- **The same SPI data link** as the FPGA, so the application talks to either without change.

### What changes from the FPGA

| | ECP5 | ASIC |
|---|---|---|
| Configuration | The C5 sends the bitstream at every power-up | None; the logic is fixed |
| Logic updates | Through application updates | Not possible; only the C5's software can change |
| Programmable parts | The whole design | Any programmable part (for example a small soft CPU) gets its code from the C5 over SPI at reset, into SRAM |
| Mask ROM | n/a | Only if a soft CPU needs boot code; no keys |

Because logic cannot be updated on the ASIC, anything that might need fixing in the field should stay in the C5's software or in loadable code.

### Memory budget

At 2 to 3 mm2 per Mb, SRAM is expensive: 64 KB (0.5 Mb) takes about 1 to 1.5 mm2. With no decrypting caches and no loader,
the ASIC needs SRAM only for its own function, and any loadable code it receives from the C5.

### Migration hooks in the FPGA design

| Hook | On the FPGA | On the ASIC |
|---|---|---|
| **Memory and clock wrappers.** Every block RAM and clock primitive sits in a thin module | Instantiates the FPGA primitive | Instantiates an ASIC macro or synthesized logic |
| **One register map** for the SPI link, including the build ID and self-test | Same | Same |
| **No reliance on initialized RAM** | No effect | SRAM powers up random |
| **Reset and configuration status** visible to the C5 | DONE and INITN | A ready flag after reset |

### Open questions

1. Whether the ASIC needs a programmable part at all, which depends on the FPGA's eventual function.
2. Pin count and package, once the SPI link and the device's I/O are known.

### Sources

- ICsprout 55nm Open Source PDK documentation: https://icsprout55-pdk-en.readthedocs.io/en/latest/
- ICsprout55 PDK release announcement: https://website-src-mkdocs.vercel.app/en/news/20251020_icsprout55_pdk_release
