# ICS55

ICS55 is an open-source chip design initiative built on the ECOS toolchain and PDKs from 55nm foundries.
It's conceptually similar to the 130nm open source flow launched previously by Google.

Preliminary research on its SRAM compiler gives a total macro area of 2 to 3 mm2/Mb.
Masked ROM would be quite a bit smaller.

Standardized floorplan blocks are 1.5 x 1.5, 2.0 x 2.0, and 2.5 x 2.5 mm.
These would fit chips with pin counts of 44-64, 80-100, and 144-208 pins.


## Commentary: `thriller` on ICS55

These notes assume ICS55 is the ultimate target, and look at what changes when the loader moves from an FPGA to an
ASIC with mask ROM but no on-chip non-volatile memory.

As of its first public release, the ICsprout 55nm open PDK contains IO and standard cell libraries. It lists no OTP,
eFuse or anti-fuse cells. The foundry offers 55nm embedded flash as a process option, but it is not part of the open release.
These notes therefore assume **no on-chip NVM of any kind**: every per-device secret and every piece of state must live off chip
(in the secure element or external flash), or be derived from the die itself.

### What gets simpler

An ASIC removes a whole class of problems that the FPGA tiers exist to manage:

- **No bitstream.** The platform update chain, the bitstream encryption key, readback, JTAG configuration and Tier A versus Tier B all disappear.
- **No vendor signature.** The non-quantum-safe ECDSA or RSA bitstream signature (R21) is gone. Every signature in the system is LMS.
- **Malleable bitstreams are gone** (R11, R12, R13, R14).
- **Counter 0 is freed** in the secure element, which turns out to be useful (see below).

### Mask ROM

Mask ROM is the ASIC's Stage 0. It is truly immutable, which is both its strength and its risk.

**Nothing secret in ROM.** Mask ROM bits can be read from a die by delayering and imaging, and every chip in the run has the same contents.
A secret in ROM is a fleet-wide secret recoverable from one die. ROM may hold only code and public values: the root LMS public key
(56 bytes), the secure element's expected configuration, and constants.

**Keep ROM small, and make the rest updatable.** A bug in ROM is permanent for the whole production run, and FDA's patchability view will
ask how it gets fixed. So ROM should hold only what must be immutable:

| In mask ROM (immutable) | In external flash (signed, updatable) |
|---|---|
| Reset, clocking, SRAM test | The rest of the loader: host sessions, application updates, logging, the MicroSD path |
| SHA-256 and AES-256 core drivers, LMS verification | The application |
| Secure element protocol: authenticated counter read | |
| Verify and decrypt the next stage from flash | |
| Recovery: receive a signed loader over the UART if flash holds no valid one | |

This brings back a two-stage chain, but a cheap one: the ROM verifies an updatable loader with LMS, and the loader's anti-rollback counter
is the secure element's counter 0, which the ASIC no longer needs for bitstreams. The updatable loader plays the role the bitstream
played on the FPGA, without a bitstream's attack surface.

**Recovery must be in ROM.** If the flash loader is corrupt and there is no recovery path in ROM, the chip is a brick. LiteForth's stage 1
recovery terminal on the CH32H417 (YMODEM into a staging file, then install) is the model: small, signed input only, nothing else.

**Code density helps.** LiteForth's 16-bit instructions are dense, and the ROM's job is narrow, so a ROM of 8 to 16 KB looks plausible.
Mask ROM's smaller area per bit makes that cheap.

### No on-chip NVM: where per-device secrets come from

The FPGA design needed per-device secrets on the FPGA side for one thing above all: the **pairing key** that authenticates the secure element's
responses on the I2C bus (R7, R8). On the FPGA it was patched into each board's bitstream. On an ASIC with only mask ROM, there is nowhere
to put a per-device secret. This is `doc/arch.md` Open Question 5, and it is the central problem of an ICS55 port.

Options, in order of preference:

1. **SRAM PUF.** On an FPGA the PUF was dropped because configuration initializes block RAM. On an ASIC, SRAM powers up uninitialized,
   so an SRAM PUF becomes available, and it needs no special cells. The PUF yields a device-unique key on every power-up:
   - A fuzzy extractor (for example a repetition code concatenated with a BCH or Golay code) corrects bit errors, using public helper data stored in external flash.
   - The PUF key does not itself become the pairing key. At provisioning, the factory station derives the pairing key in the HSM as
     KDF(master, secure element serial number), writes it to the secure element, and gives it to the ASIC, which wraps it under the PUF key
     and stores the wrapped blob in external flash. On each boot the ASIC regenerates the PUF key and unwraps the pairing key.
   - A wrapped blob copied to another board will not unwrap there.
   - Risks: the reliability of the open SRAM compiler's cells as a PUF is unknown (bit error rate across temperature, voltage and aging),
     and helper data manipulation is a known attack class. Both need characterization on silicon.
2. **Poly fuses or anti-fuses designed from standard layers.** Possible in principle, but nothing like this is in the open PDK today,
   and it would be its own research project. The foundry's own OTP or eFlash IP, if it is ever licensed for open designs, would be the practical version.
3. **No device secret on the ASIC side.** The I2C channel is then unauthenticated, and R7 and R8 reopen. Putting the secure element in the same
   package as the ASIC (a system in package) makes probing much harder but does not remove the attack. Not recommended.

**Why not a key in ROM or in gate-level constants?** A common zero-flash approach stores a unique wrapped header in external flash and
hardcodes the unwrapping key in mask ROM or synthesized logic. The headers differ per chip, but the key that opens them is the same on
every chip, so recovering it from one die (ROM imaging, or netlist extraction for logic constants, which is harder but routine for a lab)
opens every header in the fleet. That is obfuscation, not a per-device secret. A **public-key hash** in ROM is fine and is what this design
uses for the root LMS key, because it is not secret. The SRAM PUF keeps the wrapped-header structure but makes the unwrapping key unique to the die.
A ROM constant can still be mixed into the PUF key derivation, so that an attacker needs both the die's PUF response and the ROM contents.

The PUF does not replace the secure element. The secure element still provides the monotonic counters, the host-authorized data key and key storage.
The PUF only replaces the per-board bitstream key's role of binding the pairing key to one die.

### Lifecycle and debug without fuses

FPGAs and MCUs usually lock debug access with a one-time fuse. Without one:

- **Scan chains are an attack path.** Entering scan mode must clear every security register (keys, tokens, PUF output, the AES key) before scan
  clocks are applied. This is a standard ASIC countermeasure and must be designed in from the start.
- **Debug unlock by challenge-response.** Any debug port stays locked unless the requester answers a challenge signed by the HSM.
  The ASIC keeps no lock state; it is locked on every reset by default.
- **Lifecycle state in the secure element.** Whether a device is in manufacturing or in the field can be held in a secure element slot and read over
  the authenticated channel, in place of a fuse.
- **Unbonded test pads.** Production packages can leave the test pads unbonded, so scan and test access are not reachable without opening the package.

### Memory budget and executing the application

At 2 to 3 mm2 per Mb, SRAM is expensive: 64 KB (0.5 Mb) takes about 1 to 1.5 mm2, a large share of a 1.5 x 1.5 mm or 2.0 x 2.0 mm block
if those dimensions are the core area. A whole application cannot be decrypted into SRAM unless it is small. That suggests:

- **Execute in place from QSPI flash, through a small decrypting and authenticating cache.** The design is worked out in `doc/xip.md`:
  AES-256-GCM per cache line, with a nonce that binds each line to its address, slot and image version, so lines are checked on every fill
  without a Merkle tree, and the loader plus a 4 KB cache need about 7 to 8 KB of SRAM.

### Things only silicon can answer

Several parts of the security design depend on the process, and the FPGA prototypes cannot validate them:

- SRAM PUF reliability and uniqueness with the ICS55 SRAM compiler's cells.
- Ring-oscillator TRNG entropy and its health-test thresholds.
- Delay-line glitch detector sensitivity and false alarm rate.
- Power and EM side-channel leakage of the AES core (for the Code Secrecy Profile).

A small test chip on an early shuttle, carrying just these structures, would settle them before committing the full design.

### Migration hooks in the FPGA design

The FPGA design is not complicated for the sake of the ASIC. It only leaves hooks: choices that cost nothing on the FPGA
and avoid rework later. Everything else in this document (the two-stage chain, the PUF, scan clearing, the decrypting cache)
is built only for the ASIC.

| Hook | On the FPGA | On the ASIC |
|---|---|---|
| **Memory and clock wrappers.** Every block RAM, ROM, S-box table and clock primitive sits in a thin module | Instantiates the FPGA primitive | Instantiates an ASIC macro or synthesized logic |
| **Pairing key source.** The pairing key reaches the loader through one module with a fixed interface | A constant patched into the bitstream's block RAM, as now | PUF key derivation and unwrapping of the blob in flash |
| **Secret-clear input.** The security registers (keys, pass tokens, AES key) share one clear input | Tied off | Driven by scan entry and by the glitch detectors |
| **Boot code at the bottom of the loader.** The code that would become mask ROM (core drivers, LMS verification, counter read, UART recovery) is kept together and has no calls into the rest of the loader | No effect: it is all one image | Moves to mask ROM unchanged |
| **Package component types.** The update package format reserves a component type for "loader" alongside "bitstream" and "application" | Unused | Used for the updatable loader, protected by counter 0 |
| **No reliance on initialized RAM.** Nothing except the boot code's image assumes block RAM starts with known contents | No effect | SRAM powers up random, and is needed that way for the PUF |

### Open questions

1. Whether the ICS55 SRAM is usable as a PUF, and the fuzzy extractor's parameters for its error rate.
2. Whether OTP or eFlash IP will become available to open designs on this process.
3. ROM size, SRAM size and cache size, from measurements on the FPGA prototype.
4. Whether a system in package with the secure element is practical for the target packages.

### Sources

- ICsprout 55nm Open Source PDK documentation: https://icsprout55-pdk-en.readthedocs.io/en/latest/
- ICsprout55 PDK release announcement: https://website-src-mkdocs.vercel.app/en/news/20251020_icsprout55_pdk_release
