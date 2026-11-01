# Open Questions

Every open question in the `thriller` documents, in one place. Each row links to where the question is discussed.
The question numbers are the ones each document uses (for example, Arch 13 is `doc/arch.md` Open Question 13).
Decisions taken by default, which can still be reversed, follow the matrix, and then proposals for closing Arch 13 and Arch 1.

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
| [Arch 4](arch.md#open-questions) | Ring-oscillator TRNG reliability (there is no fallback source) | Randomness | Medium | Nonces, install salts | Measure, on each FPGA family | Open |
| [Arch 5](arch.md#open-questions) | ASIC pairing key without on-chip NVM | ASIC | Low | ASIC only | Study, test chip | Proposal: SRAM PUF ([ics55.md](ics55.md#no-on-chip-nvm-where-per-device-secrets-come-from)) |
| [Arch 6](arch.md#open-questions) | A customer provisioning their own application LMS key | Roles, provisioning | Medium | Provisioning flow for customer-owned applications | Study, decide | Open |
| [Arch 7](arch.md#open-questions) | LMS parameter set, and which HSM or signing service keeps LMS state | Signing | Medium | First signed release | Decide | W = 4 assumed; one signature per release |
| [Arch 8](arch.md#open-questions) | Slot authorization (ReqAuth, AuthKey) on the ATECC608B; limiting PIN attempts | Secure element | High | Host sessions, slot configuration | Bench | Open |
| [Arch 9](arch.md#open-questions) | ECP5 AES mode, CRC width, fuse options, and encrypting Yosys-built bitstreams | Tier B | High (if the ECP5 is the first target) | ECP5 bring-up | Vendor, bench | Open |
| [Arch 10](arch.md#open-questions) | Code Secrecy Profile: per-device packages | Optional profile | Low | Only if the profile is wanted | Decide | Open |
| [Arch 11](arch.md#open-questions) | Per-board or per-batch bitstream keys; eFuse flow; per-board block RAM patching on each vendor's tools | Manufacturing | Medium | Production line | Decide, bench | Open |
| [Arch 12](arch.md#open-questions) | User data freshness and a log anchor: needed, and the secure element's write endurance for slot 11 | User data, logging | Low | Per application | Decide, bench | Open |
| [Arch 13](arch.md#open-questions) | Host session protection after CheckMac (R29, Critical) | Host sessions | High | Host protocol, key paths, configuration zone | Study, bench | **Proposal below** |
| [Arch 14](arch.md#open-questions) | Masked AES: scheme, area, and leakage evaluation (R17) | Crypto hardware | High | AES core RTL, area budget | Study, measure | Masking now in the base design |
| [Arch 15](arch.md#open-questions) | Release manifest format and inclusion proofs | Signing, packages | High | Package format, installer | Study | Open |
| [HW 1](hw.md#open-questions) | AXI4-Lite latency against the CPU's memory timing | Interconnect | High | Bus RTL | Measure (RTL prototype) | Open |
| [HW 2](hw.md#open-questions) | Mailbox services, message formats, message RAM size | Firmware | Medium | Loader and application firmware | Study | Open |
| [HW 3](hw.md#open-questions) | SD card access for the application | Firmware | Low | Application features | Decide | Open |
| [HW 4](hw.md#open-questions) | Port numbering agreed with LiteForth's `iomap.h` | Interconnect | Medium | Any RTL with ports | Decide (with LiteForth) | Proposal in [hw.md](hw.md#port-maps) |
| [HW 5](hw.md#open-questions) | Loader cache size and boot ROM size | Memory | Medium | Block RAM and ASIC SRAM budget | Measure | Estimates in [hw.md](hw.md#resource-estimate-for-the-mirrored-boot-chain) |
| [XIP 1](xip.md#open-questions) | Line and cache sizes, from hit rates | Memory | Medium | ASIC SRAM budget | Measure | Open |
| [XIP 2](xip.md#open-questions) | GHASH multiplier area for the needed digit width | Crypto hardware | Medium | Final area budget | Measure | Same as Arch 3 |
| [XIP 3](xip.md#open-questions) | Constant data through the cache: own region or policy | Memory | Low | Application linker layout | Study | Open |
| [Flash 1](flash.md#open-questions) | Bitstream slot selection with each family's dual-boot or multiboot scheme, including fixed golden images | Flash, boot | High | Flash map, platform installer, Arch 1 | Vendor, bench | Open |
| [Flash 2](flash.md#open-questions) | Region sizes from real images | Flash | Medium | Final flash map | Measure | Proposal in [flash.md](flash.md#regions) |
| [Flash 3](flash.md#open-questions) | Flash part, and its behavior on power loss | Flash | Medium | Board design, Arch 1 | Bench | MX25L25645G assumed |
| [ICS55 1](ics55.md#open-questions) | ICS55 SRAM as a PUF; fuzzy extractor parameters | ASIC | Low | ASIC only | Test chip | Open |
| [ICS55 2](ics55.md#open-questions) | OTP or eFlash IP for open designs | ASIC | Low | ASIC only | Vendor | Open |
| [ICS55 3](ics55.md#open-questions) | ROM, SRAM and cache sizes for the ASIC | ASIC | Low | ASIC floorplan | Measure (on the FPGA) | Open |
| [ICS55 4](ics55.md#open-questions) | System in package with the secure element | ASIC | Low | ASIC packaging, R30 | Study | Open |
| [Test 1](test.md#9-open-questions) | Physical fault-injection pass threshold | Testing | Medium | Campaign D acceptance | Decide (with the integrator) | Open |
| [Test 2](test.md#9-open-questions) | How much of the ATECC608B to model; a second model for the MOD8ID | Testing | Medium | Software platform | Study, bench | Open |
| [Freeze](se.md#decisions-to-freeze-before-locking) | Configuration-zone decisions that must be frozen before any unit is locked | Secure element | High | Provisioning | Bench (Arch 2, 8, 13) | Open |
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
| Secure element bench | Arch 2, Arch 8, Arch 12 (endurance), Arch 13 (KDF behavior), Freeze, Test 2 | ATECC608B and MOD8ID samples, an I2C adapter, cryptoauthlib, power-cut rig |
| First RTL prototype | HW 1, HW 5, XIP 1, ICS55 3 | The LiteForth CPU, the shared XIP engine and the loader cache on one FPGA board |
| Synthesis and leakage runs | Arch 3, XIP 2, Arch 14 | Yosys and each vendor's tools; an oscilloscope or ChipWhisperer for TVLA |
| FPGA vendor documentation and bench | Arch 9, Flash 1, the FPGA rows | The security user guide for each family, and a board of each |
| Flash power-cut bench | Arch 1, Flash 3 | The chosen flash part and the power-cut rig from `doc/test.md` |
| Design studies | Arch 1, Arch 13, Arch 15, HW 2 | Desk work, then the software platform |
| Decisions | Arch 6, Arch 7, Arch 10, Arch 11, Arch 12, HW 3, HW 4, Test 1 | Product owner and integrator |

## Decisions taken by default

These were decided by default during review, on the recommended option. Each is easy to reverse.

| Decision | Instead of | Where |
|---|---|---|
| **Accept the counter brick risk** (R30): anyone on the I2C bus can advance the secure element's counters. Rely on physical protection of the secure element and its bus | A design change; none was found that the chip supports | [arch.md R30](arch.md#risk-assessment), [se.md](se.md#counters) |
| **Masked AES in the base design**, for every cache fill | Masking only under the Code Secrecy Profile | [arch.md R17](arch.md#risk-assessment), Arch 14 |
| **Backup application signing key**, its hash in never-writable slot 10, held offline in a separate HSM | No recovery from losing the main key | [se.md](se.md#slots), R31 |
| **Host key loss:** re-derive from the HSM master for an authorized replacement host. **Host key compromise:** retire the device | A writable host key slot, which a compromised bitstream could rewrite | [se.md](se.md#slots), README |

## Proposal: closing Arch 13 (host session protection)

**Problem.** CheckMac proves once that the host holds the host authorization key. After that, the session's frames cross the UART unprotected,
so an attacker in the middle can read user data or take over the session (R29, Critical).

**Goal.** A session key that only the host and the device's hardware know, bound to this session, used to encrypt and authenticate every frame
in both directions. The loader's software should never see it, and the host authorization key must still never leave the secure element.

### Proposed design

1. **Fresh nonces from both sides.** The device's nonce mixes the secure element's random number with the loader's own TRNG value, as for CheckMac today.
   The host sends its own fresh nonce in the session-open frame. (It does not fit in CheckMac's own fields, and does not need to.)
2. **Derive the session key inside the secure element.** After a successful CheckMac, the loader asks the secure element's KDF command, in HKDF mode with
   slot 1 as the source key, for:
   > session key = HKDF(host authorization key, device nonce ‖ host nonce, "thriller session v1")

   The host computes the same value with its copy of the host key. cryptoauthlib defines the KDF modes this needs: a slot as the source,
   HKDF, and output encrypted in the output buffer. Whether slot 1 may serve as a KDF source on a locked part is a bench item.
3. **Get the key out without exposing it.** The KDF output comes back encrypted under the secure element's IO protection key. If the configuration allows
   the IO protection key to be the pairing key (slot 0), the fabric already holds it, and the private key path unwraps the session key straight into its
   key register (`doc/hw.md`, Key registers). Neither CPU sees the session key.
4. **Restrict KDF on slot 1** if the chip allows, so it works only after an authorization. If it does not, a holder of the pairing key (the genuine loader,
   or a compromised bitstream) can derive session keys for nonces of its choosing. That yields session keys, never the host key, and does not let anyone
   pass CheckMac; but it should be stated as an accepted property.
5. **Confirm the key.** The session key's pass token is set when the host's first frame authenticates under it. Until then the key encrypts nothing.
6. **Protect every frame with AES-256-GCM** on the engine's install port:
   - **Nonce (96 bits):** a direction bit, 31 zero bits, and a 64-bit frame counter.
   - **Ordering:** each side accepts only the next counter value, which stops replay, reordering and deletion.
   - **Retransmission:** a frame that is not acknowledged is resent unchanged (same counter, same ciphertext, which reuses no nonce with a different
     plaintext). A duplicate of the last accepted frame is acknowledged and discarded.
   - **Tags:** a full 128-bit tag on every frame; the UART's bandwidth makes the cost negligible.
   - **Channels:** once a session is open, both UART channels (host protocol and forwarded terminal, `doc/hw.md`) run inside it.
7. **End the session** on any tag failure, on timeout, on an explicit close, or before the frame counter would wrap. Clear the session key through the
   key gate. A new session needs a new CheckMac.

**Before a session.** Update packages are protected by their own signatures and need no session. Terminal traffic before a session is in the clear;
an integrator can require a session for the terminal channel.

**Side benefit.** A device that produces valid frames under the session key has shown that its secure element holds this host's key, which is a
partial answer to FDA gap 2 (device-to-host authentication). It does not detect a compromised bitstream (R22).

### Fallback, only if the KDF route is not available

If the bench shows the ATECC608B (or the MOD8ID) cannot encrypt KDF output under a key the fabric holds:

- Provision a per-device **session root key** in spare slot 12, readable only by encrypted read under the pairing key, **never writable after lock**,
  and give the host a copy with its host authorization key.
- Derive the session key in the fabric's key path: HKDF(session root, device nonce ‖ host nonce, "thriller session v1").
- **This is clearly weaker.** The session key no longer depends on CheckMac at all; the host key only gates the data key. And a compromised bitstream
  that reads the session root once can decrypt every later session passively, even after genuine firmware is restored. Use it only if the main route
  is impossible, and record the residual risk against R29.

### Steps to close

1. **Bench (with Arch 2 and Arch 8), before any unit is locked:** confirm that slot 1 can be a KDF source with HKDF, that KDF output can be required to be
   encrypted, which slot can be the IO protection key, and whether KDF on slot 1 can require authorization. Repeat on the MOD8ID. These are configuration-zone
   decisions ([se.md, Decisions to freeze before locking](se.md#decisions-to-freeze-before-locking)).
2. **Specify** the session protocol: frames, labels, nonce layout, acknowledgment and retransmission, timeouts, and the fallback if step 1 fails.
3. **Reference model** in Python (`doc/test.md`, Layer 1), checked against bench captures.
4. **Hardware:** the KDF output unwrap into the session key register, and the install port's GCM for frames (`doc/hw.md`).
5. **Tests** (`doc/test.md`, Host sessions row): modified, replayed, reordered, deleted and injected frames; retransmitted frames; a session key never
   visible to software; a session from one CheckMac unusable after a new one.
6. **Close R29** in `doc/arch.md`, and FDA gap 10 in `doc/fda.md`.

## Proposal: closing Arch 1 (pairing key rotation sequencing)

**Problem.** A platform update that carries a bitstream rotates the pairing key. The key in the secure element must match the key in the bitstream
that boots. If a power cut leaves the secure element holding the new key while the old bitstream boots, or the reverse, the boot ROM cannot pair,
cannot read counters or keys, and the device is stuck. Today's design has the *old* loader write the new key into the secure element before the
switch, which is exactly where this can go wrong.

### Proposed design: trial boot, then confirm

1. **The new bitstream carries both keys, with their versions.** The HSM patches two pairing keys into the board's new bitstream: its own
   (key version V+1) and the board's current one (key version V, as the loader reports it; counter 0 cannot tell it). The platform package then no
   longer needs to carry a wrapped next key.
2. **Bind each loader to its bitstream.** A loader image's header names the bitstream (boot ROM) version it requires, and a boot ROM refuses a loader
   that requires a newer one. The loader in the package, including a restamped one, names the new bitstream.
3. **Install without touching the secure element.** The old loader writes the new bitstream and loader into the inactive slots, checks them, switches
   the FPGA's boot selection to the new bitstream, and arms a trial in the boot record. It does not write the pairing key or advance counter 0.
4. **Trial boot.** While a trial is armed, the new boot ROM may pair with key version V if version V+1 is not yet in the secure element. Outside a trial,
   a pairing failure is a detection, as countermeasure rule 8 requires.
5. **Watchdog fallback.** During the trial, the loader watchdog is armed for the whole boot. If the new bitstream configures but cannot pair or boot
   (a boot ROM bug, a mis-patched key), the watchdog triggers a reconfiguration from the old bitstream slot, which still pairs because nothing in the
   secure element has changed. The installer then marks the new slot bad. This needs a reconfiguration-from-address mechanism on each family (Flash 1).
6. **Define success.** The trial succeeds when the loader has booted the application and the application (or the loader's own self-test) confirms
   through a mailbox service within a time limit. The loader then calls the boot ROM's confirm routine.
7. **Confirm: counter first, then key.** The confirm routine:
   1. advances counter 0 to the new platform version. From now on the old bitstream has no loader it accepts: old loaders are below the counter,
      and new loaders require the new bitstream. Rollback is blocked whatever happens next;
   2. writes key version V+1 into slot 0, with an encrypted write authorized by key version V;
   3. pairs again with V+1 to prove the write, and clears the trial.
8. **Finish on every boot.** If the counter has advanced but slot 0 still holds V, the boot ROM retries step 7.2 on every boot until it succeeds,
   and the loader logs repeated failures. Someone on the I2C bus who blocks the write only delays the rotation: the old key stays valid in the secure
   element, but no bitstream that holds it has a loader it will run.

### Power-cut analysis

| Cut during or after | State | What the next boot does |
|---|---|---|
| Step 3 (install) | Active bitstream unchanged; inactive slots partial | The old bitstream boots normally; the installer starts over |
| Step 3, after switching | The FPGA boots the new bitstream; trial armed; old key in the secure element | The new boot ROM pairs with key version V and runs the trial |
| Steps 4 to 6 (trial) | Nothing in the secure element changed | The trial repeats, or the watchdog falls back to the old bitstream, which still pairs |
| Step 7.1 (counter) | Counter partway to the new version | The confirm routine finishes the counter |
| Step 7.2 (key write) | Slot 0 holds V or V+1, if the write is atomic | The boot ROM tries V+1, then V (trial still armed), and finishes the write |
| After step 7.3 | Rotation complete | Normal boot; key version V is retired |

**Residual risk:** if the new bitstream stops working after a successful trial but before the key write, the device cannot fall back, because the
old bitstream has no loader it accepts. UART recovery in the new bitstream's boot ROM still works. The trial makes this unlikely.

The design depends on facts to confirm on the bench: that an ATECC608B slot write is atomic across a power cut, and that each FPGA family can be
reconfigured from a chosen address and falls back when a bitstream fails to configure (Flash 1). On a family whose image at address 0 is a fixed
golden image, the switch in step 3 must never rewrite that region.

### Consequences

- **Simpler packages:** no wrapped next key. The loader image's content key is still wrapped, authenticated, under the board's current pairing key.
- **The old key lives on in the new bitstream,** but it is retired in the secure element by step 7.2, so extracting it later gains nothing.
- **The boot ROM gains** the trial logic, the confirm routine and an encrypted write of its own key. In the key paths of `doc/hw.md`, that means producing
  the EncWrite ciphertext (key source XOR derive-mode digest) and its MAC in hardware, and letting software read only those.
- **The ASIC is unaffected:** its pairing key is fixed and bound by the PUF, so there is no rotation.

### Steps to close

1. **Bench:** cut power during an encrypted write to slot 0 thousands of times, and read the slot back to confirm atomicity (with Flash 3's power-cut rig).
2. **Vendor and bench:** confirm reconfiguration from an address and fallback on each family's dual-boot scheme (Flash 1).
3. **Specify** the boot ROM's trial and confirm state machine, the boot record's trial flag, and the loader header's bitstream requirement.
4. **Model** it in the software platform with LiteForth's power-cut-at-every-step harness (`doc/test.md`, Power cuts row), cutting at every flash write,
   every secure element write and every counter increment, and with a bus interposer dropping the key write.
5. **Hardware:** add the EncWrite path for the key source to the key paths in `doc/hw.md`.
6. **Update the documents:** the README's platform update section and keys table, `doc/arch.md` (Key wrap, the summary table, Open Question 1),
   `doc/fda.md`'s platform update sequence, `doc/flash.md`'s install order, and `doc/test.md`'s Platform updates row.
