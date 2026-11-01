# Open Questions

Every open question in the `thriller` documents, in one place. Each row links to where the question is discussed.
The question numbers are the ones each document uses (for example, Arch 13 is `doc/arch.md` Open Question 13).
Proposals for closing Arch 13 and Arch 1 follow the matrix.

**Priority:** **High** blocks RTL, firmware or provisioning design now; **Medium** must be settled before the first release;
**Low** concerns the ASIC, an optional profile, or a later product decision.

**How to close:**
- **Bench:** test on real parts (secure element, FPGA, flash).
- **Measure:** synthesize or run on the FPGA prototype.
- **Study:** a short design study, then a decision.
- **Decide:** a product or business decision.
- **Vendor:** read the vendor's security documentation, then confirm on the bench.

## Matrix

| ID | Question | Area | Priority | Blocks | How to close | Status |
|---|---|---|---|---|---|---|
| [Arch 1](arch.md#open-questions) | Pairing key rotation sequencing across power cuts | Platform updates | High | Boot ROM, platform installer | Study, then power-cut tests | **Proposal below** |
| [Arch 2](arch.md#open-questions) | Confirm the slot map and the GenDig, authenticated read and EncWrite behavior on the ATECC608B and the MOD8ID | Secure element | High | Configuration zone, provisioning | Bench | Open |
| [Arch 3](arch.md#open-questions) | GHASH multiplier area on the smallest target | Crypto hardware | Medium | Final area budget | Measure | Recommendation made (GCM) |
| [Arch 4](arch.md#open-questions) | Ring-oscillator TRNG reliability, or the counter fallback | Randomness | Medium | Nonce source design | Measure, on each FPGA family | Open |
| [Arch 5](arch.md#open-questions) | ASIC pairing key without on-chip NVM | ASIC | Low | ASIC only | Study, test chip | Proposal: SRAM PUF ([ics55.md](ics55.md#no-on-chip-nvm-where-per-device-secrets-come-from)) |
| [Arch 6](arch.md#open-questions) | A customer provisioning their own application LMS key | Roles, provisioning | Medium | Provisioning flow for customer-owned applications | Study, decide | Open |
| [Arch 7](arch.md#open-questions) | LMS parameter set, and which HSM or signing service keeps LMS state | Signing | Medium | First signed release | Decide | W = 4 assumed |
| [Arch 8](arch.md#open-questions) | Slot authorization (ReqAuth, AuthKey) on the ATECC608B; limiting PIN attempts | Secure element | High | Host sessions, slot configuration | Bench | Open |
| [Arch 9](arch.md#open-questions) | ECP5 AES mode, CRC width, fuse options, and encrypting Yosys-built bitstreams | Tier B | High (if the ECP5 is the first target) | ECP5 bring-up | Vendor, bench | Open |
| [Arch 10](arch.md#open-questions) | Code Secrecy Profile: per-device packages and masked AES area | Optional profile | Low | Only if the profile is wanted | Decide, measure | Open |
| [Arch 11](arch.md#open-questions) | Per-board or per-batch bitstream keys; eFuse flow; `ecpbram` on encrypted builds | Manufacturing | Medium | Production line | Decide, bench | Open |
| [Arch 12](arch.md#open-questions) | User data freshness: needed, and the secure element's write endurance for slot 11 | User data | Low | Per application | Decide, bench | Open |
| [Arch 13](arch.md#open-questions) | Host session protection after CheckMac (R29, Critical) | Host sessions | High | Host protocol, key paths | Study, bench | **Proposal below** |
| [HW 1](hw.md#open-questions) | AXI4-Lite latency against the CPU's memory timing | Interconnect | High | Bus RTL | Measure (RTL prototype) | Open |
| [HW 2](hw.md#open-questions) | Mailbox services, message formats, message RAM size | Firmware | Medium | Loader and application firmware | Study | Open |
| [HW 3](hw.md#open-questions) | SD card access for the application | Firmware | Low | Application features | Decide | Open |
| [HW 4](hw.md#open-questions) | Port numbering agreed with LiteForth's `iomap.h` | Interconnect | Medium | Any RTL with ports | Decide (with LiteForth) | Proposal in [hw.md](hw.md#port-maps) |
| [HW 5](hw.md#open-questions) | Loader cache size and boot ROM size | Memory | Medium | Block RAM and ASIC SRAM budget | Measure | Estimates in [hw.md](hw.md#resource-estimate-for-the-mirrored-boot-chain) |
| [XIP 1](xip.md#open-questions) | Line and cache sizes, from hit rates | Memory | Medium | ASIC SRAM budget | Measure | Open |
| [XIP 2](xip.md#open-questions) | GHASH multiplier area for the needed digit width | Crypto hardware | Medium | Final area budget | Measure | Same as Arch 3 |
| [XIP 3](xip.md#open-questions) | Constant data through the cache: own region or policy | Memory | Low | Application linker layout | Study | Open |
| [Flash 1](flash.md#open-questions) | Bitstream slot selection with each family's dual-boot or multiboot scheme | Flash, boot | High | Flash map, platform installer, Arch 1 | Vendor, bench | Open |
| [Flash 2](flash.md#open-questions) | Region sizes from real images | Flash | Medium | Final flash map | Measure | Proposal in [flash.md](flash.md#regions) |
| [Flash 3](flash.md#open-questions) | Flash part, and its behavior on power loss | Flash | Medium | Board design, Arch 1 | Bench | MX25L25645G assumed |
| [ICS55 1](ics55.md#open-questions) | ICS55 SRAM as a PUF; fuzzy extractor parameters | ASIC | Low | ASIC only | Test chip | Open |
| [ICS55 2](ics55.md#open-questions) | OTP or eFlash IP for open designs | ASIC | Low | ASIC only | Vendor | Open |
| [ICS55 3](ics55.md#open-questions) | ROM, SRAM and cache sizes for the ASIC | ASIC | Low | ASIC floorplan | Measure (on the FPGA) | Open |
| [ICS55 4](ics55.md#open-questions) | System in package with the secure element | ASIC | Low | ASIC packaging | Study | Open |
| [Test 1](test.md#9-open-questions) | Physical fault-injection pass threshold | Testing | Medium | Campaign D acceptance | Decide (with the integrator) | Open |
| [Test 2](test.md#9-open-questions) | How much of the ATECC608B to model; a second model for the MOD8ID | Testing | Medium | Software platform | Study, bench | Open |
| [FPGA: CrossLink-NX](../README.md#supported-fpgas) | Enforcement on every port, key storage, readback lockout, encryption enforced, tool licensing | Tier A | High (if chosen first) | CrossLink-NX bring-up | Vendor (FPGA-TN-02176), bench | Open |
| [FPGA: Titanium](../README.md#supported-fpgas) | Readback lockout, encryption enforced, tool licensing | Tier A | Medium | Titanium bring-up | Vendor, bench | Open |
| [FPGA: ECP5](../README.md#supported-fpgas) | Key storage, readback lockout, encryption enforced, tool licensing | Tier B | High (if chosen first) | ECP5 bring-up | Vendor, bench (with Arch 9) | Open |

### FDA submission gaps

These are not design questions, but they must be closed before a premarket submission ([fda.md, section 6](fda.md#6-gaps-for-a-submission)).

| Gap | Topic | Related |
|---|---|---|
| 1 | Security event logging: the full list of events, and how the host reads the log | R24 |
| 2 | Device-to-host authentication | R22; partly addressed by the Arch 13 proposal |
| 3 | Fault-injection hardening, implemented and tested | R16, [test.md](test.md#6-fault-injection) |
| 4 | Pairing key rotation sequencing | Arch 1 |
| 5 | Decommissioning procedure | [fda.md 4.6](fda.md#46-standby-sessions-ending-and-decommissioning) |
| 6 | Recovery of a trusted default configuration | — |
| 7 | SBOM | LiteForth's `mksbom.py` as a model |
| 8 | Testing evidence, including independent penetration testing | [test.md](test.md) |
| 9 | Risk assessment rescored in FDA's exploitability-based form | [arch.md](arch.md#risk-assessment) |
| 10 | Host session protection | Arch 13, R29 |

### Closing questions in batches

Many questions close together, using the same equipment:

| Batch | Closes | What it needs |
|---|---|---|
| Secure element bench | Arch 2, Arch 8, Arch 12 (endurance), Arch 13 (KDF behavior), Test 2 | ATECC608B and MOD8ID samples, an I2C adapter, cryptoauthlib, power-cut rig |
| First RTL prototype | HW 1, HW 5, XIP 1, ICS55 3 | The LiteForth CPU, the shared XIP engine and the loader cache on one FPGA board |
| Synthesis runs | Arch 3, XIP 2, Arch 10 (masked AES) | Yosys and each vendor's tools |
| FPGA vendor documentation and bench | Arch 9, Flash 1, the FPGA rows | The security user guide for each family, and a board of each |
| Flash power-cut bench | Arch 1, Flash 3 | The chosen flash part and the power-cut rig from `doc/test.md` |
| Decisions | Arch 6, Arch 7, Arch 11, Arch 12, HW 3, HW 4, Test 1 | Product owner and integrator |

## Proposal: closing Arch 13 (host session protection)

**Problem.** CheckMac proves once that the host holds the host authorization key. After that, the session's frames cross the UART unprotected,
so an attacker in the middle can read user data or take over the session (R29, Critical).

**Goal.** A session key that only the host and the device's hardware know, bound to this session, used to encrypt and authenticate every frame
in both directions. The loader's software should never see it, and the host authorization key must still never leave the secure element.

### Proposed design

1. **Fresh nonces from both sides.** The device's challenge already mixes the secure element's random number with the loader's own nonce.
   The host adds a fresh nonce of its own to its CheckMac response.
2. **Derive the session key inside the secure element.** After a successful CheckMac, the loader asks the secure element's KDF command (HKDF mode)
   to derive the session key from slot 1, the host authorization key:
   > session key = HKDF(host authorization key, device nonce ‖ host nonce, "thriller session v1")
   The host computes the same value with its copy of the host key.
3. **Get the key out without exposing it.** The secure element returns the KDF output encrypted under its IO protection key. If the configuration
   allows the IO protection key to be the pairing key (slot 0), the fabric already holds it, and the private key path unwraps the session key
   straight into an AES key register, as it does for EncRead today. Neither CPU sees the session key.
4. **Protect every frame with AES-256-GCM** under the session key:
   - Nonce: a direction bit and a 63-bit frame counter; each side rejects any counter that is not exactly the next one, which stops replay,
     reordering and deletion.
   - A full 128-bit tag on every frame. The UART's bandwidth makes the tag cost negligible.
   - Both channels on the UART (host protocol and forwarded terminal, `doc/hw.md`) run inside the session once it is open.
5. **End the session** on any tag failure, on timeout, on an explicit close, or when the frame counter would wrap. Clear the session key through the
   key gate. A new session needs a new CheckMac.

**Side benefit.** A device that produces valid frames under the session key has shown that its secure element holds this host's key, which is a
partial answer to FDA gap 2 (device-to-host authentication). It does not detect a compromised bitstream (R22).

### Fallback if the KDF route is not available

If the ATECC608B (or the MOD8ID) cannot encrypt KDF output under a key the fabric holds:

- Provision a per-device **session root key** in spare slot 12, readable only by EncRead under the pairing key, and give the host a copy
  along with its host authorization key.
- Derive the session key in the fabric's key path: HKDF(session root, device nonce ‖ host nonce ‖ CheckMac challenge, "thriller session v1").
- Including the CheckMac challenge ties the session to a successful host authorization.
- The weakness: a compromised bitstream holding the pairing key can read the session root, so it could impersonate the device to the host.
  It still cannot authenticate as the host, and it already sees session data on the device itself (the evil-maid row in `doc/arch.md`).

### Steps to close

1. **Bench (with Arch 2 and Arch 8):** confirm on the ATECC608B, through cryptoauthlib's configuration structure and real parts, that:
   - the KDF command accepts slot 1 as its source;
   - KDF output can be required to be encrypted;
   - the IO protection key can be slot 0.
   Repeat on the MOD8ID.
2. **Specify** the session protocol: frame format, labels, nonce layout, timeouts, and which fallback applies if step 1 fails.
3. **Reference model** in Python (`doc/test.md`, Layer 1), checked against bench captures.
4. **Hardware:** add "unwrap KDF output into an AES key register" to the key paths in `doc/hw.md` (the same mechanism as EncRead).
5. **Slot map:** update `doc/se.md`: slot 1's KDF permission, the chip options for KDF output and the IO protection key, or slot 12 for the fallback.
6. **Tests** (`doc/test.md`, Host sessions row): modified, replayed, reordered, deleted and injected frames; a session key never visible to software;
   a session from one CheckMac unusable after a new one.
7. **Close R29** in `doc/arch.md`, and FDA gap 10 in `doc/fda.md`.

## Proposal: closing Arch 1 (pairing key rotation sequencing)

**Problem.** A platform update that carries a bitstream rotates the pairing key. The key in the secure element must always match the key in the
bitstream that boots. If a power cut leaves the secure element holding the new key while the old bitstream boots, or the reverse, the boot ROM
cannot pair, cannot read counters or keys, and the device is stuck. Today's design has the *old* loader write the new key into the secure element
before the switch, which is exactly where this can go wrong.

### Proposed design: the new bitstream rotates its own key, after a trial boot

1. **The new bitstream carries both keys.** The HSM patches two pairing keys into the board's new bitstream: its own,
   KDF(pairing master, serial, new platform version), and the board's current one, KDF(pairing master, serial, current platform version).
   The board reports its counter 0, so the HSM knows the current version. The platform package then no longer needs to carry a wrapped next key.
2. **Install without touching the secure element.** The old loader writes the new bitstream and the restamped loader image into the inactive
   slots, reads them back and checks them, and switches the FPGA's boot selection to the new bitstream (`doc/flash.md`). It does not write the pairing
   key and does not advance counter 0.
3. **Trial boot with the old key.** The new bitstream's boot ROM tries its own key first. If the secure element does not answer to it, it pairs with
   the old key, which still works, and boots the loader and the application as a trial.
4. **Confirm by rotating.** Only after the trial succeeds does the new bitstream write its own key into slot 0, with an encrypted write authorized by
   the old key, then pair again with the new key to prove the write.
5. **Advance counter 0** to the new platform version. From then on, the old bitstream cannot pair and the old loader fails its version check.
6. **Finish on every boot.** Steps 3 to 5 are idempotent. A boot ROM that finds its old key still working, or counter 0 behind its own version,
   finishes them before doing anything else.

### Power-cut analysis

| Cut during or after | State | What the next boot does |
|---|---|---|
| Step 2 (install) | Active bitstream unchanged; inactive slot partial | The old bitstream boots normally; the installer starts over |
| Step 2, after switching | The FPGA boots the new bitstream; the secure element holds the old key | The new boot ROM pairs with the old key and continues the trial |
| Step 3 (trial) | Old key still in the secure element | Trial repeats. If the new bitstream cannot boot at all, the FPGA falls back to the old one, which still pairs |
| Step 4 (key write) | Old or new key in slot 0, if the write is atomic | The new boot ROM tries both keys and finishes the rotation |
| Step 5 (counter) | New key, counter partway to the new version | The new boot ROM finishes advancing the counter |
| After step 5 | Rotation complete | Normal boot. The old bitstream's key is retired, and its own copy of the old key is useless |

The design depends on two facts to confirm on the bench: that an ATECC608B slot write is atomic across a power cut (the slot holds either the old or the
new key, never a mix), and that each FPGA family falls back to the previous bitstream when the new one fails to configure (Flash 1).

### Consequences

- **Simpler packages.** The "next pairing key wrapped under the current one" disappears from platform packages.
  The loader image's content key is still wrapped under the *current* pairing key.
- **The old key lives on in the new bitstream,** but it is retired in the secure element by step 4, so extracting it later gains nothing.
- **The boot ROM gains** a "finish pending rotation" step and needs to drive an encrypted write of its own key without exposing it. In the key paths of
  `doc/hw.md`, that means producing the EncWrite ciphertext (key source XOR keyed digest) and its MAC in hardware, and letting software read only the result.
- **The ASIC is unaffected:** its pairing key is fixed and bound by the PUF, so there is no rotation.

### Steps to close

1. **Bench:** cut power during EncWrite to slot 0 thousands of times, and read the slot back to confirm atomicity (with Flash 3's power-cut rig).
2. **Vendor and bench:** confirm the fallback behavior of each family's dual-boot scheme (Flash 1).
3. **Specify** the boot ROM's rotation state machine and the installer's steps, as above.
4. **Model** it in the software platform with LiteForth's power-cut-at-every-step harness (`doc/test.md`, Power cuts row), cutting at every flash write,
   every secure element write and every counter increment.
5. **Hardware:** add the EncWrite path for the key source to the key paths in `doc/hw.md`.
6. **Update the documents:** the README's platform update section, `doc/arch.md` (Key wrap, the summary table and Open Question 1),
   `doc/fda.md`'s platform update sequence, and `doc/flash.md`'s install order.
