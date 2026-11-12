# FIPS 140-3

The long-term target is a FIPS 140-3 validation through the CMVP. This document records what that target changes in the design now, so that nothing has to be undone later,
and what it leaves for the validation project itself. It is a design note, not a Security Policy; the Security Policy is written against the finished module.

Level 2 is the baseline (role-based authentication, tamper evidence). Level 3 (identity-based authentication, tamper response with zeroization) is reachable with the enclosure switch (Q7)
and is noted where it would add a requirement.

## Module boundary

Where the boundary falls decides most of the rest. Three candidates:

| Boundary | What is inside | Consequence |
|---|---|---|
| **A. Multi-chip embedded module: the FPGA, the secure element and the flash**, on a defined board region | Both cores, the configuration engine, the secure element, the flash. The PSRAM, RTC, CODECs, PHY and card are outside | The FPGA-to-secure-element bus is internal, so the secure element's key transport needs no approved wrapping. The application image is firmware inside the boundary: integrity-tested as it already is, and each application release is a firmware change filed with the CMVP (a non-security-relevant change letter if the application has no security function). Tamper evidence over the region |
| B. Sub-chip cryptographic subsystem: the loader domain alone (IG 2.3.B) | The loader core, key registers, Ascon and SHA-256 cores, XIP engine, security block | The application domain is outside and its releases need no filing. But every CSP leaving the sub-chip, including every key the secure element releases and every key written to it, must cross the boundary under an approved method, and the ATECC608 protocol's masking (XOR with a SHA-256 TempKey) is not one. Requires a different secure element, or none |
| C. The whole device | Everything | Every component becomes security-relevant; the CODECs and display drag clinical function into the validation. Not attractive |

**Decision: A.** It matches the design's own trust boundary extended by the two chips it already trusts, it keeps the secure element's protocol as it is, and the per-application-release filing is
a known, inexpensive process. The region must be tamper-evident (a seal or conformal coating over the FPGA, secure element and flash, Level 2) or tamper-responsive (Level 3: the enclosure switch
triggers zeroization). Inside the boundary the application core is a *non-security-relevant* component: it provides no approved service, and the netlist connectivity check (R37) is the evidence that
it cannot affect one.

If the secure element later changes to a part that supports approved key wrapping (a validated secure element, question E9), option B becomes possible and the application leaves the boundary.

## Approved algorithms and what each needs

| Algorithm | Standard | Status | What the validation needs |
|---|---|---|---|
| Ascon-AEAD128 | SP 800-232 | Approved (2025) | CAVP certificate for our core. ACVP test vectors for Ascon are recent; confirm coverage (A11). **Tag truncation to 64 bits for XIP lines must be checked against SP 800-232's minimum**; if 128-bit tags are required, the line format becomes 64 + 16 bytes (F6) |
| SHA-256, HMAC-SHA256 | FIPS 180-4, FIPS 198-1 | Approved | CAVP for the SHA-256 core, in both plain and HMAC use |
| KDF, HMAC mode | SP 800-108r1 | Approved | CAVP (KBKDF) |
| HMAC_DRBG | SP 800-90Ar1 | Approved | CAVP; the DRBG is new to the design (below) |
| Entropy source | SP 800-90B | Required | An ESV certificate for the ring-oscillator source, from the restart and sequential data the RTC campaign produces (`doc/test.md`) |
| LMS / HSS | SP 800-208 | Approved | CAVP (verification only, in the loader) |
| ML-KEM-768 | FIPS 203 | Approved | CAVP (encapsulation in the loader; decapsulation on the host and sensor are outside the module) |
| ML-DSA-44 | FIPS 204 | Approved | CAVP (verification only) |
| ECDSA P-256, SHA-256 | FIPS 186-5 | Approved | Performed by the secure element inside the boundary; CAVP testing through its interface (the SHA command takes arbitrary messages; Sign takes a digest, which the component tests cover). If this proves impractical, E9 |
| ATECC608C MAC, GenDig, CheckMac, KDF | Microchip command set | **Not approved as such** | Inside boundary A these are internal key handling, not cryptographic services offered by the module; they must still be documented as the CSP transport they are. The CheckMac host authentication is role authentication, assessed as an authentication mechanism (its strength: a 256-bit key, a 32-byte MAC) |
| Vendor bitstream cipher and signature | Pango or Efinix | Vendor silicon | The configuration engine's AES-GCM and RSA are not the module's services; they are the firmware-load mechanism for the bitstream and are assessed as such (an approved integrity technique: AES-GCM and RSA-2048/4096 both qualify) |

**Non-approved algorithms:** none in the module. Nothing runs in a non-approved mode, so there is a single approved mode and the status indicator is static.

## Entropy and the DRBG

FIPS separates the entropy source (SP 800-90B, validated by ESV) from the random bit generator that consumes it (SP 800-90A). The design therefore gains an **HMAC_DRBG** on the SHA-256 core,
seeded from the ring-oscillator source through the SHA-256 vetted conditioning function, with the secure element's Random output as additional input (not credited for entropy unless its ESV
certificate is carried over, which SP 800-90C allows under conditions and which the validation can decide). All keys, nonces, salts and segment keys come from the DRBG. The mask PRNG that feeds the
threshold implementations is seeded from the DRBG but is not itself a security service and needs no approval.

The entropy source's health tests (repetition count and adaptive proportion) run continuously, and the DRBG runs its own health tests at power-up and on demand. The restart campaign in `doc/test.md`
is the ESV data collection; its raw-sample logging exists only in the test build, which is a separate, unvalidated firmware.

## Self-tests

**Pre-operational** (before any service, in the boot ROM and the first loader code):

- Firmware integrity: the configuration engine's authentication of the bitstream covers the boot ROM; the loader image gets a whole-image check at boot (an HMAC-SHA256 or LMS verification over the
  slot, in addition to the per-line tags), because the standard wants an integrity test of the firmware before it is used, not only as it is fetched.
- Cryptographic algorithm self-tests (CASTs), known-answer tests run by the boot ROM: Ascon-AEAD128 encrypt and decrypt, SHA-256, HMAC-SHA256, KBKDF, HMAC_DRBG (instantiate, generate, reseed), LMS verify,
  ML-KEM encapsulate (with a fixed seed), ML-DSA verify, ECDSA verify through the secure element. A failure enters the error state: the lockdown path, with the cause recorded.

**Conditional:**

- Entropy source health tests, continuously; DRBG health tests on reseed.
- Firmware load test: every package is LMS-verified before installation (already the design). The bitstream is verified by the configuration engine. Both count.
- Pairwise consistency: not applicable; the module generates no asymmetric key pairs (the secure element's identity key is generated once at the factory, before the module is operational).
- Critical function tests: the netlist's key gate and pass-token logic are design-time controls; the flow counter and comparators in the security block are the run-time ones.

## Roles, services, authentication

| FIPS role | Who | Authenticated by | Services |
|---|---|---|---|
| Crypto Officer | The manufacturer's enrollment station and update server | The symmetric identity key (slot 12): MAC and CheckMac through the secure element | Enrollment, platform and application updates, ratchet, lifecycle (retire, wipe), time beacons |
| User | The host (and, on developer builds, the developer) | Host authorization key (slot 1) through CheckMac; developer working key through the loader | Sessions, user data, recordings, sensor pairing, attestation, log export |
| Unauthenticated | Anyone on the UART or the network | None | Show status (versions, build mode, faults, pairing state); the session handshake; power cycling |

Level 2 asks for role-based authentication, which the two keys give. Level 3 asks for identity-based authentication: each host would need its own key, which the current design, with one host authorization
key per device, does not provide (E10). Authentication strength: 256-bit keys, 32-byte MACs; attempt limits in the loader make the one-minute false-acceptance bound trivial to meet.

**Zeroization.** A FIPS zeroization service destroys all CSPs. The key registers, caches and SRAM are cleared by the secret-clear fan-out. The secure element's keys cannot be erased, but the pairing
key can be **ratcheted to a random value that is never recorded**, after which no key it holds can ever be released again, and the device is dead; the flash records region is erased. That is the
zeroization service, invoked by the Crypto Officer (retire) or, at Level 3, by the enclosure switch.

**Show status.** The UART status report and the LCD overlay carry the approved-mode indicator (always "approved" in this module), the self-test results and the error state.

## CSP list

Pairing keys (both), application key, data key and the derived data keys, distribution key, developer key and working key, log key, identity keys (both), image keys, install keys, session keys,
segment keys, sensor pairing and session keys, DRBG state and seed, the entropy source's raw output. Public and non-secret: LMS public keys and their hashes, device and signer certificates, host recording
public keys, the RSA digest in eFuse, the MAC address, pairing key versions, time beacons. Each CSP's generation, entry, storage, use and destruction is already described in `doc/se.md` and `doc/hw.md`;
the Security Policy collects them into the required table.

## What changes in the design now

1. **HMAC_DRBG** on the SHA-256 core, with the entropy source behind a vetted conditioning function (`doc/hw.md`, `doc/fpga.md`).
2. **Power-up CASTs and a whole-image loader integrity check** in the boot ROM (`doc/hw.md`, Boot ROM contents).
3. **A static approved-mode indicator and self-test status** in the status report.
4. **Zeroization as a named service**: the ratchet-to-random plus records erase.
5. **A tamper-evident region** over the FPGA, secure element and flash, independent of the enclosure seal (board design).
6. **XIP tag length** confirmed against SP 800-232 before the line format is frozen (F6).
7. **Secure element choice** reviewed for CAVP testability of its ECDSA and SHA-256 through its interface, or replaced by a validated part (E9).
8. **Test builds are unvalidated firmware**, kept separate from production images in the build system and never installable on a fused production device (they lack the production LMS signature).

## What waits for the validation project

The Security Policy, the finite state model, the CAVP test campaigns, the ESV submission, the physical security evidence for the chosen level, the operational and life-cycle documentation,
and the choice of laboratory. None of these should change the hardware or the key management described in the rest of this repository; that is the point of settling the eight items above now.

## Sources

- NIST, *FIPS 140-3: Security Requirements for Cryptographic Modules*, and its Implementation Guidance, in particular IG 2.3.B (sub-chip cryptographic subsystems) and the firmware-load and entropy sections.
- NIST SP 800-232, *Ascon-Based Lightweight Cryptography Standards for Constrained Devices*.
- NIST SP 800-90A Rev. 1, SP 800-90B, and SP 800-90C.
- NIST SP 800-140 series (CMVP derived test requirements).
