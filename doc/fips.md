# FIPS 140-3

The long-term target is a FIPS 140-3 validation through the CMVP. This document records what that target changes in the design now, so that nothing has to be undone later,
and what it leaves for the validation project itself. It is a design note, not a Security Policy; the Security Policy is written against the finished module.

Level 2 is the baseline (role-based authentication, tamper evidence). Level 3 (identity-based authentication, tamper response with zeroization) is reachable with the enclosure switch (Q7)
and is noted where it would add a requirement.

## Designing for few filings

A CMVP filing is expensive, and it waits: on the laboratory's backlog and then on the CMVP's queue, each measured in months. So after the boundary, the design's second FIPS priority is
**that the validated module changes as rarely as possible**, which means knowing exactly what counts as a change and keeping everything else out.

**What triggers a filing.** The module is the loader domain: its hardware (part of the bitstream's netlist) and its firmware (the boot ROM in the bitstream, and the loader image). A change to
either changes the module. A change that is not security-relevant (a bug fix in a non-security function, a change confined to logic outside the module's partition of the bitstream) is the
cheapest scenario: the laboratory reviews the change, affirms it, and the certificate's version list is updated. A security-relevant change (any cryptographic function, key management, a
service, an interface) means regression testing of the affected requirements, and a large enough change is a new validation. All of them go through the laboratory and the queue; none is free.

**What the design does about it:**

1. **The module is a crypto kernel with a fixed service API, and nothing else** (`doc/api.md`). The services are the ones the Security Policy will
   list: sessions, key release, user data records, recording segments, sensor frame checks, installs, attestation, log MACs, lifecycle, power-hold, random. The message formats are frozen with the module.
2. **Product logic lives outside the module, on the supervisor core and the application core** (`doc/hw.md`, Principles). Transports, DHCP, the CLI command set, scheduling, sleep and wake,
   the LCD's contents, sensor policy, the user interface: all of it ships in the supervisor and application images, which are LMS-signed, version-counted and line-authenticated like everything
   else, but are **not module firmware**. A supervisor or application release is not a filing.
3. **Nothing that will change is wired into the module as code.** Parameters the module needs but that may vary (the session port, host slot count, log capacity, recording block size,
   network policy) come from signed headers or records as data. Security parameters (attempt limits, tag lengths, key sizes) are fixed and are part of the validation.
4. **Bitstream releases are rare, and the module's partition is preserved across them.** The whole bitstream is the module's firmware image as far as the configuration engine's integrity check
   is concerned, so every bitstream release is at least an affirmation. New peripherals for the supervisor or application are therefore designed in up front, and the build flow keeps the module's
   part of the netlist placed and routed identically across releases (an incremental or partition flow), so that a release which changes only non-module logic can be shown not to touch the
   module (F12; PDS has no partition flow, so this is a locked region, fixed pins and scripted netlist locking, `fpga/logos2/README.md`). Per-device key constants patched into the key source are CSPs in a fixed design, not a firmware change; the laboratory must agree (E12).
5. **Every algorithm the product will ever need is in the module from the first validation**: Ascon, SHA-256 and HMAC, the KBKDF, HMAC_DRBG, LMS, ML-KEM, ML-DSA.
   Adding an algorithm later is a revalidation; the post-quantum ones are there now so no transition forces one.
6. **The module's version is its own.** The loader image and the bitstream carry a module version, independent of the product, supervisor and application versions, and the status report shows all four.
7. **The entropy source is frozen too.** The ring-oscillator source and its health tests have their own ESV certificate; a change there is its own submission.
8. **Test builds are unvalidated firmware** that never reaches a production device, so the test-only modules can change freely.

The TPM's certificate is ST's to maintain. Its firmware is never updated in the field by this design, and E6 tracks that the order code stays on the certificate.

## Module boundary

Where the boundary falls decides most of the rest. The candidates, and what happened to them:

| Boundary | What is inside | Consequence |
|---|---|---|
| A. Multi-chip embedded module: the whole FPGA, the TPM and the flash, on a defined board region | All three cores, the configuration engine, the TPM, the flash | Every bus is internal. But the supervisor and application images are firmware inside the boundary: each release of either is a filing (Designing for few filings). Not acceptable |
| **B. Multi-chip embedded module with a sub-chip portion: the loader domain (IG 2.3.B), the TPM and the flash** | The loader core, boot ROM, key registers, Ascon and SHA-256 cores, XIP engine, security block, TPM interface, host UART, recording engine; the TPM; the flash | The supervisor and application domains are outside, as excluded logic on the same die, and their images are non-module firmware stored on the module's flash: their releases need no filing. The TPM's SPI bus and the flash are internal, so keys moving between the loader domain, the TPM and the flash are internal handling, not key transport. The TPM is an embedded validated module (certificate #5570) whose certificate and CAVP entries the Security Policy cites |
| B′. Sub-chip subsystem alone, with the TPM and the flash outside | The loader domain only | Every key leaving the TPM or stored in flash is key transport and needs an approved method. The method available on a TPM 2.0 bus is AES-CFB parameter encryption with an HMAC authenticator, the "combination method" of IG D.G, which the 19 August 2026 IG revision now strongly recommends against, and which the draft SP 800-131A Rev. 3 plans to deprecate. Withdrawn |
| C. The whole device | Everything | Every component becomes security-relevant; the CODECs and display drag clinical function into the validation. Not attractive |

**Decision: B.** The module is the loader domain exactly as `doc/hw.md` draws it, plus the TPM and the flash; its logical boundary on the die is the netlist connectivity that is already
checked (R37), its physical boundary the tamper-evident region on the board (`hw/`). The supervisor and application cores, their memories and peripherals, the mailboxes and their XIP ports are
excluded components, not security-relevant; their images in flash are not module firmware; the configuration engine is the firmware-load mechanism for the module's own firmware (the bitstream).
The supervisor core exists for this reason: it takes everything that changes often out of the module (Designing for few filings). Physical security at Level 2 is tamper evidence over the region,
at Level 3 the enclosure switch and the zeroization below. On the ASIC the same boundary becomes a sub-chip subsystem of a single-chip package, and if the TPM die is co-packaged (`doc/ics55.md`)
the module is one package.

What B needs from a laboratory (E12): agreement that a multi-chip embedded module may have a sub-chip portion on a die shared with excluded logic, with the mailboxes and XIP ports as the
declared interfaces; and that non-module firmware stored on the module's flash is an excluded component. If that agreement does not come, the fallback is A, which costs filings for every
supervisor and application release but changes no hardware.

**What this means for the TPM link.** With the bus internal, the sessions' parameter encryption is defense in depth rather than approved key transport, so the TPM's XOR obfuscation (a
one-time stream from KDFa over the session key and both nonces) is sufficient, and the design has **no AES in the fabric** (F4). An earlier revision added an AES-128-CFB session cipher to
make B′ work; the IG D.G change removed the reason, and the core with it.

**What crosses the boundary**, and how: the host data secret enters inside an authenticated, encrypted session frame (Ascon-AEAD128 under a session key derived from secrets both ends hold,
SP 800-108), and nothing else secret ever leaves or enters; what leaves is ciphertext (recordings, records, frames), MACs, signatures and public data. Whether the session frame's key entry is an
approved method in its own right (an AEAD under a KDF-derived key, as IG D.G allows for AES-GCM; Ascon-AEAD128's standing for this use is to be confirmed) is part of E12; the alternative is
to carry the host data secret under ML-KEM-768, a key encapsulation method IG D.S covers, which the module already implements.

## Approved algorithms and what each needs

| Algorithm | Standard | Status | What the validation needs |
|---|---|---|---|
| Ascon-AEAD128 | SP 800-232 | Approved (2025) | CAVP certificate for our core. ACVP test vectors for Ascon are recent; confirm coverage (A11). 64-bit tags on XIP lines are within SP 800-232, whose floor is 32 bits and which asks for a risk analysis only below 64 (F6 closed) |
| SHA-256, HMAC-SHA256 | FIPS 180-4, FIPS 198-1 | Approved | CAVP for the SHA-256 core, in both plain and HMAC use; HMAC is also the TPM session authenticator |
| KDF, HMAC mode | SP 800-108r1 | Approved | CAVP (KBKDF). The TPM's KDFa is the same construction, so one implementation serves both |
| HMAC_DRBG | SP 800-90Ar1 | Approved | CAVP; the DRBG is new to the design (below) |
| Entropy source | SP 800-90B | Required | An ESV certificate for the ring-oscillator source, from the restart and sequential data the RTC campaign produces (`doc/test.md`) |
| LMS / HSS | SP 800-208 | Approved | CAVP (verification only, in the loader) |
| ML-KEM-768 | FIPS 203 | Approved | CAVP (encapsulation in the loader; decapsulation on the host and sensor are outside the module) |
| ML-DSA-44 | FIPS 204 | Approved | CAVP (verification only) |
| TPM services: ECDSA P-256 quotes, HMAC-SHA256 identity, Hash_DRBG, NV, sessions | TCG TPM 2.0 Library; CMVP #5570 | Provided by an embedded validated module | Nothing to test; the Security Policy cites the TPM's certificate and its CAVP entries (A2547 to A2555: Hash_DRBG, SHA-2/3, SP 800-108 KDF, HMAC, AES, RSA with KTS-IFC, ECDSA and KAS-ECC) and operates it in the configuration its own Security Policy describes (`doc/tpm.md`, Part) |
| Vendor bitstream cipher and signature | Pango or Efinix | Vendor silicon | The configuration engine's AES-GCM and RSA are not the module's services; they are the firmware-load mechanism for the bitstream and are assessed as such (an approved integrity technique: AES-GCM and RSA-2048/4096 both qualify) |

**Non-approved algorithms:** none in the module. Nothing runs in a non-approved mode, so there is a single approved mode and the status indicator is static. The TPM's XOR parameter
obfuscation is internal handling inside the boundary, not a security service, and is listed as such.

## Entropy and the DRBG

FIPS separates the entropy source (SP 800-90B, validated by ESV) from the random bit generator that consumes it (SP 800-90A). The design therefore has an **HMAC_DRBG** on the SHA-256 core,
seeded from the ring-oscillator source through the SHA-256 vetted conditioning function, with the TPM's `TPM2_GetRandom` output as additional input (not credited for entropy unless the TPM's
SP 800-90B source is carried over, which SP 800-90C allows under conditions and which the validation can decide). All keys, nonces, salts and segment keys come from the DRBG. The mask PRNG that feeds the
threshold implementations is seeded from the DRBG but is not itself a security service and needs no approval.

The entropy source's health tests (repetition count and adaptive proportion) run continuously, and the DRBG runs its own health tests at power-up and on demand. The restart campaign in `doc/test.md`
is the ESV data collection; its raw-sample logging exists only in the test build, which is a separate, unvalidated firmware.

## Self-tests

**Pre-operational** (before any service, in the boot ROM and the first loader code):

- Firmware integrity: the configuration engine's authentication of the bitstream covers the boot ROM; the loader image gets a whole-image check at boot (an HMAC-SHA256 or LMS verification over the
  slot, in addition to the per-line tags), because the standard wants an integrity test of the firmware before it is used, not only as it is fetched.
- Cryptographic algorithm self-tests (CASTs), known-answer tests run by the boot ROM: Ascon-AEAD128 encrypt and decrypt, SHA-256, HMAC-SHA256, KBKDF, HMAC_DRBG (instantiate, generate, reseed),
  LMS verify, ML-KEM encapsulate (with a fixed seed), ML-DSA verify. A failure enters the error state: the lockdown path, with the cause recorded. The TPM runs its own self-tests (`TPM2_SelfTest`),
  and the boot ROM checks their result before using it.

**Conditional:**

- Entropy source health tests, continuously; DRBG health tests on reseed.
- Firmware load test: every package is LMS-verified before installation (already the design). The bitstream is verified by the configuration engine. Both count.
- Pairwise consistency: not applicable; the module generates no asymmetric key pairs (the TPM's attestation key is generated once at the factory, inside the TPM).
- Critical function tests: the netlist's key gate and pass-token logic are design-time controls; the flow counter and comparators in the security block are the run-time ones.

## Roles, services, authentication

| FIPS role | Who | Authenticated by | Services |
|---|---|---|---|
| Crypto Officer | The manufacturer's enrollment station and update server | The symmetric identity key: `TPM2_HMAC` over both nonces, compared in the security block | Enrollment, platform and application updates, ratchet, lifecycle (retire, wipe), time beacons |
| User | Each enrolled host (and, on developer builds, the developer) | The host's own authorization key, proved to the TPM through the relayed HMAC session (`doc/tpm.md`, Host authentication); developer working key through the loader | Sessions, user data, recordings, sensor pairing, attestation, log export |
| Unauthenticated | The supervisor and application cores, and through them anyone on the UART or the network | None | Show status (versions, build mode, faults, pairing state); the session handshake; recording segments (encrypt-only, to keys the module holds); sensor frame checks; log entry MACs; random; power-hold release |

The supervisor and application cores are operators of the module like any other caller: they reach it only through the mailboxes, and the services they can invoke without an authenticated
session are the ones that release nothing. `doc/api.md` is the Security Policy's service list, message by message.

Level 2 asks for role-based authentication, which these keys give. Level 3 asks for identity-based authentication: each host has its own key and its own TPM index, so the design already meets it
(E10 closed). Authentication strength: 256-bit keys, 32-byte HMACs; attempt limits in the loader and the TPM's dictionary-attack lockout make the one-minute false-acceptance bound trivial to meet.

**Zeroization.** A FIPS zeroization service destroys all CSPs. The key registers, caches and SRAM are cleared by the secret-clear fan-out. The TPM's keys cannot be erased from the loader, but the
pairing key can be **ratcheted to a random value that is never recorded**, after which no policy in the TPM can ever be satisfied again and the device is dead; the flash records region, with the
sealed-object blobs, is erased. That is the zeroization service, invoked by the Crypto Officer (retire) or, at Level 3, by the enclosure switch. At the station, `TPM2_Clear` additionally destroys
the storage seed and every object under it.

**Show status.** The UART status report and the LCD overlay carry the approved-mode indicator (always "approved" in this module), the self-test results and the error state.

## CSP list

Pairing keys (both), TPM session keys and their obfuscation streams, application key, data keys and the derived data keys, host session secrets, distribution key, developer key and working key,
log key, image keys, install keys, session keys, segment keys, sensor pairing and session keys, DRBG state and seed, the entropy source's raw output. Inside the TPM, inside the module: the
symmetric identity key, the attestation and endorsement private keys, the host authorization keys (as authorization values). Public and non-secret: LMS public keys, the AK and EK certificates,
host recording public keys, the RSA digest in eFuse, the MAC address, pairing key versions, time beacons, sealed-object blobs. Each CSP's generation, entry, storage, use and destruction is already
described in `doc/tpm.md` and `doc/hw.md`; the Security Policy collects them into the required table.

## What changes in the design now

1. **HMAC_DRBG** on the SHA-256 core, with the entropy source behind a vetted conditioning function (`doc/hw.md`, `doc/fpga.md`).
2. **Power-up CASTs and a whole-image loader integrity check** in the boot ROM (`doc/hw.md`, Boot ROM contents).
3. **A static approved-mode indicator and self-test status** in the status report.
4. **Zeroization as a named service**: the ratchet-to-random plus records erase.
5. **A tamper-evident region** over the FPGA and the TPM, independent of the enclosure seal (board design).
6. **XIP tag length** confirmed against SP 800-232 before the line format is frozen (F6).
7. **The TPM in place of the ATECC608C** (`doc/tpm.md`), inside the module boundary with the flash (E12); E9 is closed by the choice.
8. **Test builds are unvalidated firmware**, kept separate from production images in the build system and never installable on a fused production device (they lack the production LMS signature).
9. **A supervisor core outside the module**, carrying the transports, scheduling and the CLI, so that releases of those never touch the module (`doc/hw.md`); the module's service API frozen and versioned.
10. **A partition flow for the bitstream** that keeps the module's netlist identical across releases that change only supervisor or application hardware (F12).

## What waits for the validation project

The Security Policy, the finite state model, the CAVP test campaigns, the ESV submission, the physical security evidence for the chosen level, the operational and life-cycle documentation,
and the choice of laboratory. None of these should change the hardware or the key management described in the rest of this repository; that is the point of settling the ten items above now.

## Sources

- NIST, *FIPS 140-3: Security Requirements for Cryptographic Modules*, and its Implementation Guidance, in particular IG 2.3.B (sub-chip cryptographic subsystems), IG D.G (key transport methods),
  IG D.S (key encapsulation) and the firmware-load and entropy sections.
- CMVP certificate #5570 (9 November 2026, replacing #4737, now historical), STMicroelectronics ST33KTPM2X, and its Security Policy.
- CMVP, *FIPS 140-3 IG announcements*: the 19 August 2026 revision of IG D.G (the "combination method" recommendation) and the 27 February 2026 revision of IG 2.3.B.
- NIST, draft SP 800-131A Rev. 3 (planned deprecation of key wrapping built from encryption plus separate authentication).
- Trusted Computing Group, *TPM 2.0 Library Specification*, Parts 1 to 4; *PC Client Platform TPM Profile*.
- NIST SP 800-232, *Ascon-Based Lightweight Cryptography Standards for Constrained Devices*.
- NIST SP 800-90A Rev. 1, SP 800-90B, and SP 800-90C.
- NIST SP 800-140 series (CMVP derived test requirements).
