# Test Plan

How `thriller` is tested, from reference models to fault injection. Risk IDs (R1–R27) refer to `doc/arch.md`.

## 1. Approach

Most of the security now runs as software in the C5's TEE, on hardware Espressif has already characterized. Testing therefore concentrates on:

- **our protocols and their implementation:** packages, host sessions, sensor pairing and sessions, user data, the event log;
- **the C5 configuration:** eFuses, boot chain, TEE isolation;
- **fault injection and side channels** on the checks we write, and confirming that Espressif's countermeasures are enabled and effective.

### Layers

| Layer | What | Where |
|---|---|---|
| 1. Reference models | Python models of every format and protocol: package layout and signatures, key derivations, host session, sensor pairing and session, user data records, event log chain | Workstation; produce test vectors |
| 2. Unit tests | TEE and application components against the vectors | ESP-IDF unit tests (Unity) on the C5; portable logic also on ESP-IDF's Linux host target |
| 3. System tests | Whole device against simulated host, sensor, server and card | Hardware-in-the-loop rig |
| 4. Fault injection and side channels | Attacks on one unit | Lab bench |
| 5. Penetration test | Independent team, whole system | External |

### Evidence

Each test names the risk it covers. The catalogue below is the traceability matrix between risks and tests that an FDA submission needs (`doc/fda.md`).

## 2. Reference models

- **Formats:** update package (header, LMS signature, encrypted payload), developer package, build descriptor, sensor certificate, pairing transcript, session frames, user data records, log entries.
- **Cryptography:** known-answer tests for each algorithm from the standards (LMS from RFC 8554, ML-KEM and ML-DSA from the FIPS 203 and 204 vectors, Ascon from SP 800-232, AES-GCM, HKDF).
- **Protocols:** both ends of the host session and the sensor protocol, so each end of the device can be tested against a model of the other.

The sensor's firmware is tested against the same models.

## 3. Hardware-in-the-loop rig

- A production-configured C5 board with the ECP5 and a MicroSD card, plus boards with the eFuses left open for debugging.
- **Host simulator** on the host link, driven by test scripts.
- **Sensor simulator** on the sensor link: a microcontroller that runs the sensor protocol and can misbehave on command (bad certificates, wrong MACs, replays, delays, silence).
- **Link interposer** between the device and the sensor simulator, able to delay, drop, replay and alter frames with controlled timing.
- **Server simulator** reached through the host simulator.
- **Power control** for power cuts at chosen points during updates and pairing.
- A flash programmer on the external flash, for restore attacks.

## 4. Test catalogue

| Area | Tests | Risks |
|---|---|---|
| Boot chain | Unsigned, wrongly signed and revoked-key images refused at each stage; recovery bootloader used when the bootloader fails; slot fallback when an image fails | R3, R27 |
| Anti-rollback | Older packages refused by the TEE; equal accepted; after a security release, an older image written by programmer is refused by the bootloader; non-security restore boots (accepted risk, documented) | R4 |
| Updates | Forged LMS signature, altered ciphertext, wrong distribution key, truncated package, all refused before any flash write; power cut at every step leaves a bootable device; a new image that fails its self-test (including the FPGA check) is rolled back | R3, R18 |
| Debug lockdown | JTAG (pad and USB) unusable; download mode restricted or disabled as configured; direct boot disabled | R7 |
| TEE isolation | Application attempts to read TEE memory, use the HMAC peripheral, write eFuses, or write TEE flash regions: each faults | R8 |
| Host session | Wrong host key, replayed session, reordered, altered and replayed frames, all rejected; no user data access outside a session | R9 |
| User data | Card read offline shows no plaintext; altered records rejected; an old copy of the card detected through the host's digest; developer and production data mutually unreadable | R1, R10, R21 |
| Sensor pairing | Certificate signed by an unknown CA, altered certificate, denylisted serial, wrong private key (implicit rejection) all refused; power cut during pairing leaves the old pairing or none, never a half pairing; server rejection removes the pairing | R14, R15 |
| Sensor session | Forged, replayed, reordered and delayed frames rejected; readings older than the maximum age rejected; link cut puts the device in its safe state within the maximum age | R11, R12, R13 |
| FPGA | Wrong build ID, corrupted bitstream, configuration failure each detected and logged; an update with a bad bitstream rolls back | R17 |
| Enrollment | Unenrolled device cannot install updates or authenticate; enrollment cannot be repeated; server flags unknown and duplicate identities | R16 |
| Developer builds | Build for another device refused; old-epoch builds refused after an epoch release; version record and eFuses unchanged by developer installs; developer image cannot boot from a TEE slot | R21, R22 |
| Event log | Removed or altered entries detected by the host and the server | R26 |
| Radios | Production image does not initialize the radios (unless Wi-Fi is adopted) | R23 |

## 5. Fault injection

### Threat

A lab attacker glitches the C5 to skip a check: a signature comparison, a version check, the build descriptor check, a MAC comparison in the sensor or host protocol.
Espressif advisory AR2023-007 shows this works on the C3 and C6 with voltage glitches. The C5 adds glitch detectors, which these tests must also exercise.

### Countermeasures to build into our code

1. Compare MACs and signatures in constant time, and check each security decision twice, with the second check on a complemented value.
2. Encode success as a multi-bit value, never 0 or 1, so a single skipped instruction or zeroed register cannot produce it.
3. Count loop iterations in signature and MAC checks, and check the count at the end.
4. Random delays before critical checks (the TRNG is available).
5. On any inconsistency, log it and halt into the safe state; never retry silently.
6. Keep the glitch detectors enabled and log their resets.

### Campaigns

| Campaign | Method | Target | Pass |
|---|---|---|---|
| A. Package check | Voltage glitch (crowbar on the core supply) and EM pulses during the TEE's LMS check | Install a package with a bad signature | No bad package installed in the campaign budget; detections logged |
| B. Boot descriptor | Same, during the TEE's build descriptor check | Boot a developer build for another device | Never boots |
| C. Sensor MAC | Same, during frame verification | Accept a forged reading | Never accepted |
| D. Secure boot | Same, during the bootloader's check (ROM checks are Espressif's) | Boot an unsigned application | Never boots |
| E. Glitch detectors | Sweep glitch parameters | Find the detection boundary | Detectors fire before any of A to D succeed |

### Side channels

- **Flash encryption:** test-vector leakage assessment (TVLA) on the XTS-AES engine with pseudo-rounds at the chosen level, to confirm it removes the leakage AR2023-007 used.
- **AES and HMAC in the TEE:** TVLA on the operations that use the device root and the data key.
- **Sensor:** TVLA on the sensor's ML-KEM decapsulation and MAC. A broken sensor exposes only itself (R15), so a modest result may be acceptable.

## 6. Tools

| Tool | Use |
|---|---|
| ESP-IDF with its Unity test framework and Linux host target | Unit tests |
| Python (`cryptography`, reference implementations of LMS, ML-KEM, ML-DSA, Ascon) | Reference models and vectors |
| pytest-embedded | Driving the rig |
| ChipWhisperer-Husky, a voltage glitch stage, an EMFI probe | Fault injection |
| A scope or ChipWhisperer for power traces | TVLA |
| Verilator | The FPGA's register block and self-test logic |

## 7. Open questions

See `doc/questions.md` (Test rows).
