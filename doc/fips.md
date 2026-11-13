# FIPS 140-3

The long-term target is a FIPS 140-3 validation through the CMVP. This document records what that target changes in the design now, so that nothing has to be undone later,
and what it leaves for the validation project itself. It is a design note, not a Security Policy; the Security Policy is written against the finished module.

Level 2 is the baseline (role-based authentication, tamper evidence). Level 3 (identity-based authentication, tamper response with zeroization) is reachable with the enclosure switch (Q7)
and is noted where it would add a requirement.

## Module boundary

Where the boundary falls decides most of the rest. Three candidates:

| Boundary | What is inside | Consequence |
|---|---|---|
| A. Multi-chip embedded module: the FPGA, the TPM and the flash, on a defined board region | Both cores, the configuration engine, the TPM, the flash. The PSRAM, RTC, CODECs, PHY and card are outside | The FPGA-to-TPM bus is internal. The application image is firmware inside the boundary: each application release is a firmware change filed with the CMVP. Tamper evidence over the region. The TPM's own certificate is not used |
| **B. Sub-chip cryptographic subsystem: the loader domain alone (IG 2.3.B), with the TPM as a separately validated module** | The loader core, key registers, Ascon, SHA-256 and session-cipher cores, XIP engine, security block, TPM interface | The application domain is outside and its releases need no filing. Every CSP crossing the boundary does so under an approved method: keys from the TPM arrive by AES-128-CFB parameter encryption with an HMAC-SHA256 response authenticator (key transport per IG D.G), keys to the TPM leave the same way, and everything else that leaves is ciphertext or a MAC. The TPM is used as what it is: a module with its own CMVP certificate (#4737), whose services the device's module consumes |
| C. The whole device | Everything | Every component becomes security-relevant; the CODECs and display drag clinical function into the validation. Not attractive |

**Decision: B.** The TPM made it possible: the ATECC608C's key transport (XOR with a SHA-256 TempKey) was not an approved method, which forced boundary A and the per-release filing;
TPM 2.0 sessions provide an approved one. The module is the loader domain exactly as `doc/hw.md` draws it, its boundary the netlist connectivity that is already checked (R37). The application
core, its memories and peripherals, the mailbox and the application's XIP port are outside the module and are not security-relevant; the configuration engine is the firmware-load mechanism.
Physical security at Level 2 is tamper evidence over the FPGA and the TPM (a seal or conformal coating), at Level 3 the enclosure switch and the zeroization below. On the ASIC the same boundary
becomes a sub-chip subsystem of a single-chip package, and if the TPM die is co-packaged (`doc/ics55.md`) the two modules share one physical envelope.

What B costs: an unmasked AES-128 core in the loader domain for the session cipher, about 1K LUTs (`doc/hw.md`), keyed per session so no key sees more than one session's traffic; and a
laboratory's agreement that the sub-chip subsystem and the two-module arrangement are acceptable (E12). If that agreement does not come, A remains available with the same hardware.

## Approved algorithms and what each needs

| Algorithm | Standard | Status | What the validation needs |
|---|---|---|---|
| Ascon-AEAD128 | SP 800-232 | Approved (2025) | CAVP certificate for our core. ACVP test vectors for Ascon are recent; confirm coverage (A11). **Tag truncation to 64 bits for XIP lines must be checked against SP 800-232's minimum**; if 128-bit tags are required, the line format becomes 64 + 16 bytes (F6) |
| SHA-256, HMAC-SHA256 | FIPS 180-4, FIPS 198-1 | Approved | CAVP for the SHA-256 core, in both plain and HMAC use; HMAC is also the TPM session authenticator |
| KDF, HMAC mode | SP 800-108r1 | Approved | CAVP (KBKDF). The TPM's KDFa is the same construction, so one implementation serves both |
| AES-128, CFB mode | FIPS 197, SP 800-38A | Approved | CAVP for the session-cipher core (encrypt direction, CFB128). Used only for TPM session parameter encryption |
| KTS: AES-CFB with HMAC-SHA256 | IG D.G | Approved key transport | Built from the two certificates above; 128 bits of strength. Covers every key that enters the module from the TPM and every key that leaves it for the TPM |
| HMAC_DRBG | SP 800-90Ar1 | Approved | CAVP; the DRBG is new to the design (below) |
| Entropy source | SP 800-90B | Required | An ESV certificate for the ring-oscillator source, from the restart and sequential data the RTC campaign produces (`doc/test.md`) |
| LMS / HSS | SP 800-208 | Approved | CAVP (verification only, in the loader) |
| ML-KEM-768 | FIPS 203 | Approved | CAVP (encapsulation in the loader; decapsulation on the host and sensor are outside the module) |
| ML-DSA-44 | FIPS 204 | Approved | CAVP (verification only) |
| TPM services: ECDSA P-256 quotes, HMAC-SHA256 identity, Hash_DRBG, NV, sessions | TCG TPM 2.0 Library; CMVP #4737 | Provided by a separately validated module | Nothing to test; the Security Policy cites the TPM's certificate and operates it in the configuration its own Security Policy describes. The CAVP list behind #4737 covers AES, ECDSA, KAS-ECC, Hash_DRBG, HMAC, the SP 800-108 KDF, RSA and SHA-2/3 (`doc/tpm.md`, Part) |
| Vendor bitstream cipher and signature | Pango or Efinix | Vendor silicon | The configuration engine's AES-GCM and RSA are not the module's services; they are the firmware-load mechanism for the bitstream and are assessed as such (an approved integrity technique: AES-GCM and RSA-2048/4096 both qualify) |

**Non-approved algorithms:** none in the module. Nothing runs in a non-approved mode, so there is a single approved mode and the status indicator is static. The TPM's XOR parameter
obfuscation is never selected.

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
- Cryptographic algorithm self-tests (CASTs), known-answer tests run by the boot ROM: Ascon-AEAD128 encrypt and decrypt, SHA-256, HMAC-SHA256, KBKDF, HMAC_DRBG (instantiate, generate, reseed), AES-128-CFB,
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
| Unauthenticated | Anyone on the UART or the network | None | Show status (versions, build mode, faults, pairing state); the session handshake; power cycling |

Level 2 asks for role-based authentication, which these keys give. Level 3 asks for identity-based authentication: each host has its own key and its own TPM index, so the design already meets it
(E10 closed). Authentication strength: 256-bit keys, 32-byte HMACs; attempt limits in the loader and the TPM's dictionary-attack lockout make the one-minute false-acceptance bound trivial to meet.

**Zeroization.** A FIPS zeroization service destroys all CSPs. The key registers, caches and SRAM are cleared by the secret-clear fan-out. The TPM's keys cannot be erased from the loader, but the
pairing key can be **ratcheted to a random value that is never recorded**, after which no policy in the TPM can ever be satisfied again and the device is dead; the flash records region, with the
sealed-object blobs, is erased. That is the zeroization service, invoked by the Crypto Officer (retire) or, at Level 3, by the enclosure switch. At the station, `TPM2_Clear` additionally destroys
the storage seed and every object under it.

**Show status.** The UART status report and the LCD overlay carry the approved-mode indicator (always "approved" in this module), the self-test results and the error state.

## CSP list

Pairing keys (both), TPM session keys and the AES keys derived from them, application key, data keys and the derived data keys, host session secrets, distribution key, developer key and working key,
log key, image keys, install keys, session keys, segment keys, sensor pairing and session keys, DRBG state and seed, the entropy source's raw output. Inside the TPM, outside the module: the
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
7. **The TPM in place of the ATECC608C** (`doc/tpm.md`), and with it the AES-128-CFB session cipher and the sub-chip boundary (E12); E9 is closed by the choice.
8. **Test builds are unvalidated firmware**, kept separate from production images in the build system and never installable on a fused production device (they lack the production LMS signature).

## What waits for the validation project

The Security Policy, the finite state model, the CAVP test campaigns, the ESV submission, the physical security evidence for the chosen level, the operational and life-cycle documentation,
and the choice of laboratory. None of these should change the hardware or the key management described in the rest of this repository; that is the point of settling the eight items above now.

## Sources

- NIST, *FIPS 140-3: Security Requirements for Cryptographic Modules*, and its Implementation Guidance, in particular IG 2.3.B (sub-chip cryptographic subsystems), IG D.G (key transport methods)
  and the firmware-load and entropy sections.
- CMVP certificate #4737, STMicroelectronics ST33KTPM2X, and its Security Policy.
- Trusted Computing Group, *TPM 2.0 Library Specification*, Parts 1 to 4; *PC Client Platform TPM Profile*.
- NIST SP 800-232, *Ascon-Based Lightweight Cryptography Standards for Constrained Devices*.
- NIST SP 800-90A Rev. 1, SP 800-90B, and SP 800-90C.
- NIST SP 800-140 series (CMVP derived test requirements).
