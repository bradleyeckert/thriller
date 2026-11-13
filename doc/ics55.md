# ICS55

ICS55 is an open-source chip design initiative built on the ECOS toolchain and PDKs from 55 nm foundries, conceptually similar to the 130 nm open-source flow launched earlier by Google.
Preliminary research on its SRAM compiler gives a total macro area of 2 to 3 mm²/Mb; masked ROM would be quite a bit smaller.
Standardized floorplan blocks are 1.5 × 1.5, 2.0 × 2.0 and 2.5 × 2.5 mm, fitting pin counts of 44–64, 80–100 and 144–208.

## `thriller` on ICS55

The FPGA is a model of this ASIC. The ASIC runs the same boot ROM (now mask ROM), the same loader and application chain, talks to the same TPM and flash, and drives the same
peripherals. It loses the bitstream, and with it the one secret the bitstream carried: **the pairing keys.** The ICsprout 55 nm open PDK lists no OTP, eFuse or embedded flash cells,
so the ASIC gets them from a PUF behind the key-source interface that the FPGA design already uses (`doc/hw.md`).

### What stays the same

- The TPM, its NV layout, its objects and the ratchet. Counters, identity and the host's proof to the TPM do not move. If the TPM die is co-packaged with the ASIC, the two FIPS modules share one physical envelope (`doc/fips.md`).
- The flash map, the boot record, the loader and application chains, the XIP engine, the mailbox, the recording engine, the sensor and host protocols: the same RTL and the same Forth.
- The attestation report: the "bitstream release" field becomes the silicon revision, and the pairing key version keeps its meaning.

### What gets simpler

- No bitstream: no configuration bus to protect (R31), no blind bitstream edits (R32), no per-device bitstream builds (R42), no vendor tools.
- Logic cannot be replaced or reconfigured on the board (R17, R44).
- The boot ROM is truly immutable.

### What changes: the pairing key and the ratchet

On the FPGA each bitstream release carries its own pairing key, and the ratchet retires the previous one. The ASIC has no bitstream, so there is one PUF-derived pairing key for the life
of the chip, and the ratchet no longer applies: platform rollback is then counter 0 alone, exactly as the loader is protected today. The pairing index's `TPM2_NV_ChangeAuth` path stays available for a key
change at RMA.

### Where the key comes from

| Option | How | Cost |
|---|---|---|
| **SRAM PUF** (preferred) | At enrollment the ASIC derives its pairing key from an SRAM block's power-up pattern through a fuzzy extractor; the helper data (not secret) goes into the flash's ASIC key blob (`doc/flash.md`); the HSM records the derived key by setting it as the TPM pairing index's authorization value through the station, and keeps nothing else | Needs the SRAM to behave as a PUF on this process, and the extractor and its characterization logic in the ASIC; settled only on silicon |
| Mask ROM key | One key for every ASIC, in ROM | Fleet-wide: breaking one ASIC breaks all. Not acceptable |
| Key from the TPM | The TPM cannot release a key to a chip that has nothing to authenticate with | Circular. Not possible |

With the PUF, the HSM cannot derive the ASIC's pairing key from the serial number. That changes one thing in `doc/enrollment.md`: the pairing key is exported once, at the station, wrapped to
the HSM, instead of being derived. Everything the HSM derives from the device master is unchanged.

### The key-source module on the ASIC

Behind the interface in `doc/hw.md`:

- **PUF SRAM:** a dedicated block, powered up unused before the first read, with its own power gate so it can be cycled for characterization.
- **Fuzzy extractor:** a BCH or repetition-plus-BCH decoder over helper data read from flash by the boot ROM, producing the 256-bit key straight into the SHA-256 core's key port.
- **Characterization port (`char_*`):** read raw PUF responses, run repeated power cycles, count bit errors against the enrolled response, read the extractor's error count and margin,
  and set enrollment mode. Reachable only in the factory lifecycle state (the TPM's lifecycle index) and from the loader, so a characterized chip can be screened before its key is enrolled.
- **Enrollment mode:** generate the helper data for a fresh response and present the key once, wrapped to the HSM, for enrollment into the TPM.
- **`key_fault`:** raised when the decoder cannot correct the response; the boot ROM then stays in recovery.

On the FPGA the same port exists as a stub that returns fixed values, so the loader's characterization and enrollment code is written and tested before silicon.

### Memory budget

At 2 to 3 mm² per Mb, SRAM is expensive: 64 KB (0.5 Mb) takes about 1 to 1.5 mm². The two XIP caches (6 KB), both cores' stacks and data RAM, the mailbox, the recording buffer and the PUF block
are the main users; the application's code stays in flash.

### Things only silicon can answer

- SRAM PUF reliability and uniqueness with the ICS55 SRAM compiler's cells, across temperature and aging.
- Ring-oscillator TRNG entropy.
- Side-channel leakage of the masked Ascon and SHA-256 cores on this process (the same RTL as the FPGA).

A small test chip on an early shuttle, carrying the PUF block, the extractor, the TRNG and the two crypto cores, would settle them before committing the full design.

### Open questions

See `doc/questions.md` (ICS55 rows).

### Sources

- ICsprout 55nm Open Source PDK documentation: https://icsprout55-pdk-en.readthedocs.io/en/latest/
- ICsprout55 PDK release announcement: https://website-src-mkdocs.vercel.app/en/news/20251020_icsprout55_pdk_release
