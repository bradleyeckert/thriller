# ICS55

ICS55 is an open-source chip design initiative built on the ECOS toolchain and PDKs from 55nm foundries.
It's conceptually similar to the 130nm open source flow launched previously by Google.

Preliminary research on its SRAM compiler gives a total macro area of 2 to 3 mm2/Mb.
Masked ROM would be quite a bit smaller.

Standardized floorplan blocks are 1.5 x 1.5, 2.0 x 2.0, and 2.5 x 2.5 mm.
These would fit chips with pin counts of 44-64, 80-100, and 144-208 pins.


## Commentary: `thriller` on ICS55

The ECP5 now runs the application and holds two per-device keys (the link key and the image key), carried in its encrypted bitstream (`doc/fpga.md`).
An ASIC replacing it would do the same job, but it has no bitstream to carry keys in, and the ICsprout 55nm open PDK lists no OTP, eFuse or embedded flash cells.
So the ASIC's one hard problem is the same one the earliest design faced: **where its per-device keys come from.** Everything else gets simpler.

### What stays the same

- The C5 remains the root of trust, installer and gateway. Version records, package checks, networking and storage do not move.
- The XIP engine, link engine, recording engine and key isolation are the same RTL.
- The link protocol and the boot image message are the same, so the C5's software does not change.

### What gets simpler

- No bitstream: no configuration bus to protect (R31), no blind bitstream edits (R32), no per-device bitstream builds (R42), no Lattice Diamond.
- Logic cannot be replaced or reconfigured on the board (R17).

### Where the keys come from

| Option | How | Cost |
|---|---|---|
| **SRAM PUF** (preferred) | At enrollment the ASIC derives a key from its SRAM's power-up pattern; the C5 stores the helper data (not secret) and the HSM records the derived link and image keys, or the ASIC and C5 agree them once and the C5 stores them in its TEE | Needs the SRAM to behave as a PUF on this process, and a fuzzy extractor in the ASIC; settled only on silicon |
| Mask ROM key | One key for every ASIC, in ROM | Fleet-wide: breaking one ASIC breaks all. Not acceptable for recordings |
| Keys from the C5 over the link at every boot | The C5 sends them in plaintext before any key exists | Visible on the board. Not acceptable |

With a PUF, the C5 pairs once with the ASIC at enrollment, matching how the C5 pairs with the ECP5 today.

### Memory budget

At 2 to 3 mm2 per Mb, SRAM is expensive: 64 KB (0.5 Mb) takes about 1 to 1.5 mm2. The XIP cache (about 4 KB), the CPU's stacks and data RAM,
and the recording and link buffers are the main users; the application's code stays in flash.

### Migration hooks in the FPGA design

| Hook | On the FPGA | On the ASIC |
|---|---|---|
| **Key source module.** The link and image keys reach the engines through one module with a fixed interface | Constants patched into block RAM | PUF key derivation |
| **Memory and clock wrappers.** Every block RAM and clock primitive sits in a thin module | FPGA primitives | ASIC macros or synthesized logic |
| **Secret-clear input.** All key registers and the cache share one clear input | Reset, reconfiguration, failures | Also scan entry and glitch detectors |
| **No reliance on initialized RAM** outside the key constants | No effect | SRAM powers up random, which the PUF needs |
| **Version report in the handshake** | Bitstream version | Silicon revision |

### Things only silicon can answer

- SRAM PUF reliability and uniqueness with the ICS55 SRAM compiler's cells.
- Ring-oscillator TRNG entropy.
- Side-channel leakage of the AES cores.

A small test chip on an early shuttle, carrying just these structures, would settle them before committing the full design.

### Open questions

1. Whether the ICS55 SRAM is usable as a PUF.
2. Whether OTP or eFlash IP will become available to open designs on this process.
3. Pin count and package, once the CODEC, LCD and C5 interfaces are fixed.

### Sources

- ICsprout 55nm Open Source PDK documentation: https://icsprout55-pdk-en.readthedocs.io/en/latest/
- ICsprout55 PDK release announcement: https://website-src-mkdocs.vercel.app/en/news/20251020_icsprout55_pdk_release
