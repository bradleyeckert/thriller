# Potting: what it is for, and what it is not

The module is designed to be potted (`module.md`, Potting). This document is honest about why. FIPS 140-3 requires hard opaque potting, or a strong enclosure, for a multi-chip embedded module
at physical security Level 3, and that requirement does not depend on what the module's traces carry. The design's cryptography already protects every secret that touches copper. So the question
is what potting buys beyond compliance, what it costs, and when to apply it.

## What the cryptography already does without potting

Nothing secret is in plaintext on any trace of the module (`module.md`, the trace table), so an attacker with the bare card and a logic analyser learns no key:

| What crosses a trace | Protection | What an attacker on the trace gets |
|---|---|---|
| Unsealed keys and the next pairing key, FPGA ↔ TPM | XOR with a KDFa stream from a session key derived from the pairing key and two fresh nonces; every command and response HMAC'd | Nothing without the pairing key; replay fails on the nonces; alteration fails the HMAC |
| Code and records, FPGA ↔ flash | Per-line Ascon-AEAD128 under image keys; records under the application key; headers HMAC'd | Nothing but ciphertext; alteration fails the tag and causes a lockdown |
| TPM blobs in flash | The TPM's own wrapping under its storage seed | Useless without the TPM and the policy |
| Recording stream, FPGA ↔ PSRAM | Ascon-AEAD128 under per-segment keys | Ciphertext |
| Session frames, FPGA ↔ PHY and the UART | Ascon-AEAD128 under session keys | Ciphertext |

FIPS 140-3 calls the first two "not an approved method" (the TPM's XOR mode is not a listed key transport, and Ascon-AEAD128 is not listed for key wrapping), which is why the TPM and the
flash are inside the boundary and under the potting. That is a classification, not a weakness: a 256-bit keyed one-time stream and an approved AEAD under a 128-bit key are not what an
attacker breaks. **For confidentiality, potting is a formality.** Nothing it covers would yield a key if uncovered.

## What potting actually defends against

Potting is not useless; it is aimed at a different set of attacks, the ones cryptography cannot address because they target availability, authenticity of the hardware, or the physical
inputs the cryptography runs on:

| Attack on an unpotted module | Cost without potting | What potting does |
|---|---|---|
| **Interposer on the TPM bus, talking first after reset**: hold the FPGA in reset, drive the TPM's `RST` and SPI, `TPM2_Clear` it or evict its root key | A $20 adapter and an afternoon; the module is bricked (R36) | Requires removing hard compound from a fine-pitch QFN without destroying the board: destructive, slow, and evident |
| **Flash chip-off**: reprogram the flash to force the multi-boot fallback, corrupt slots, replay old images | A hot-air station; every outcome is a lockdown or recovery, never a key (R44), but it is a cheap denial of service and a way to exercise the recovery paths at will | Same: the part is not reachable without destroying the card |
| **Clock, reset and rail glitching**: drive the 25 MHz oscillator output, pulse `RSTN`, dip a core rail, to skip a check or fault a computation | Probe wires on exposed pads; the masked cores and the flow counters resist, but fault injection is the attack class the design is least able to prove against (R5, R33) | Removes the probe points; the monitors in the security block are the second line |
| **Power analysis on the core rails** | A shunt on a regulator output; the masked Ascon and SHA-256 cores are the defense, and their masking is what the TVLA campaign measures | Forces the attacker to the 5 V input, upstream of the switchers, where the signal is heavily filtered |
| **Part substitution**: a different TPM, a flash with a backdoored controller, a tapped oscillator | Rework; a substituted TPM fails the pairing, a substituted flash yields nothing, a tapped oscillator is a glitching tool | Prevents it without destruction, and makes the attempt visible |
| **Reading the markings and layout** to plan any of the above | Free | Opaque compound hides the parts and the routing |

The common thread: **potting converts cheap, reversible, deniable attacks into destructive, slow, evident ones.** It does not stop an attacker who is willing to destroy the module; it stops
the one who wants to use it afterwards, or to try repeatedly, or to leave no trace. For a device that will be returned, serviced and audited, evidence is worth having.

What potting does **not** do: it does not resist a laboratory (R46 stands on the TPM's own shield and the FPGA's eFuse protection, not on epoxy); it does not stop electromagnetic side
channels, which pass through compound; and it does not protect anything on the carrier, which is why the application device has its own seal (R38, R51).

## Levels, and what each requires

| | Level 2 | Level 3 |
|---|---|---|
| FIPS 140-3 physical security for a multi-chip embedded module | Tamper evidence: a coating, seal or enclosure such that opening leaves visible evidence | Hard opaque potting (or a strong enclosure with tamper response on removable covers); environmental failure protection or testing (voltage, temperature) |
| On this module | A conformal coating with a tamper-evident label set over the card; reworkable at the factory | The potting in `module.md`; underfill on the BGA and the TPM; rail and temperature monitors (H12) |
| Authentication | Role-based: the keys already give it | Identity-based: the per-host TPM indices already give it |
| Zeroization | On command (retire, wipe) | Also on tamper: the seal loop and enclosure switch from the carrier trigger the ratchet-to-random |
| Cost | Low; the card stays serviceable | Thermal path through compound; no rework; BGA stress under thermal cycling (hence the underfill); EFP/EFT evidence |

Nothing in the cryptography, the key management or the boundary differs between the two levels. The module is the same card; Level 3 adds compound and monitors.

## The decision

1. **Design the card to be pottable** (the geometry in `module.md`: keep-outs, the heatsink bonded first, underfill, no test points), so that Level 3 is a manufacturing option and not a redesign.
2. **Validate at Level 2 first** unless a customer requirement says otherwise. The coating gives the tamper evidence that matters for returns and audits; the cryptography carries the rest,
   and a Level 2 certificate arrives sooner and costs less, which matters more than the level given the filing-minimization priority (`doc/fips.md`).
3. **Pot for Level 3 when a market asks for it**, as a variant of the same card under the same certificate family, with the EFP monitors already on the board and the thermal design checked (H12).
4. Whatever the level, **the potting region could be reduced to the FPGA and the TPM** if the records region's CSPs were moved into TPM-sealed blobs (`module.md`); the flash would then be outside
   the boundary, holding only ciphertext and public data. Keep this in reserve for the day the compound's thermal or rework cost matters.

## In one sentence

Potting on this module is compliance as far as confidentiality goes, because no key is ever on a trace in a form an attacker can use; it is real protection against bricking, glitching,
substitution and silent tampering, which is a different and worthwhile thing, and it should be bought when a market pays for Level 3 rather than before.
