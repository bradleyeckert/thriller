# Test Plan

How `thriller` is tested, from reference models to fault injection. Risk IDs (R1–R43) refer to `doc/arch.md`.

## 1. Approach

Security runs in two places: as software in the C5's TEE, on hardware Espressif has characterized, and as RTL in the ECP5. Testing therefore concentrates on:

- **our protocols and their implementation:** packages, host sessions, the C5–FPGA link, recordings, sensor pairing and sessions, user data, the event log;
- **our RTL:** the XIP engine, the link and recording engines, key isolation and the TRNG;
- **the C5 and ECP5 configuration:** eFuses, boot chain, TEE isolation, the ECP5's security settings;
- **fault injection and side channels** on the checks we write, and confirming that Espressif's countermeasures are enabled and effective.

### Layers

| Layer | What | Where |
|---|---|---|
| 1. Reference models | Python models of every format and protocol: package layout and signatures, key derivations, per-line GCM, link handshake and frames, recording segments, host session, sensor pairing and session, user data records, event log chain | Workstation; produce test vectors |
| 2. Unit tests | TEE and C5 firmware components against the vectors; RTL modules against the same vectors | ESP-IDF unit tests (Unity) on the C5 and its Linux host target; Verilator for the RTL; LiteForth's `vm.c` for application code |
| 3. System tests | Whole device against simulated host, sensor, server and card | Hardware-in-the-loop rig |
| 4. Fault injection and side channels | Attacks on one unit | Lab bench |
| 5. Penetration test | Independent team, whole system | External |

### Evidence

Each test names the risk it covers. The catalogue below is the traceability matrix between risks and tests that an FDA submission needs (`doc/fda.md`).

## 2. Reference models

- **Formats:** update packages (C5, bitstream, application), developer package, boot image message, XIP lines and tags, link frames, recording segment headers and blocks, sensor certificate, pairing transcript, session frames, user data records, log entries.
- **Cryptography:** known-answer tests for each algorithm from the standards (LMS from RFC 8554, ML-KEM and ML-DSA from the FIPS 203 and 204 vectors, Ascon from SP 800-232, AES-GCM, HKDF).
- **Protocols:** both ends of the host session, the C5–FPGA link and the sensor protocol, so each end can be tested against a model of the other.

The sensor's firmware is tested against the same models.

## 3. Hardware-in-the-loop rig

- A production-configured board (C5, locked ECP5, both flashes, CODECs, LCD, MicroSD card), plus boards with the eFuses left open and an unlocked ECP5 for debugging.
- **Interposers** on SPI2 (configuration and link), on the FPGA's QSPI flash (or a flash emulator), and on one I2S bus, able to record, replay and alter traffic.
- **Signal source** on the CODEC inputs: synthetic EEG at known levels.
- **Host simulator** on the UART and over BLE, driven by test scripts.
- **Controllable Wi-Fi access point and server simulator**, able to impersonate the real server.
- **Sensor simulator** on the sensor link: a microcontroller that runs the sensor protocol and can misbehave on command (bad certificates, wrong MACs, replays, delays, silence).
- **Link interposer** between the device and the sensor simulator, able to delay, drop, replay and alter frames with controlled timing.
- **Server simulator** reached through the host simulator.
- **Power control** for power cuts at chosen points during updates and pairing.
- Flash programmers on both external flashes, for restore attacks, and a JTAG pod on the ECP5.

## 4. Test catalogue

| Area | Tests | Risks |
|---|---|---|
| Boot chain | Unsigned, wrongly signed and revoked-key images refused at each stage; recovery bootloader used when the bootloader fails; slot fallback when an image fails | R3, R27 |
| Anti-rollback | Older packages refused by the TEE; equal accepted; after a security release, an older image written by programmer is refused by the bootloader; non-security restore boots (accepted risk, documented) | R4 |
| Updates | Forged LMS signature, altered ciphertext, wrong distribution key, truncated package, all refused before any flash write, for all three package kinds; a bitstream package for another device refused; power cut at every step leaves a bootable device; a new C5 image, bitstream or application that fails its self-test is rolled back | R3, R18 |
| Debug lockdown | JTAG (pad and USB) unusable; download mode restricted or disabled as configured; direct boot disabled | R7 |
| TEE isolation | C5 firmware attempts to read TEE memory, use the HMAC peripheral, write eFuses, or write TEE flash regions: each faults | R8 |
| Host session | Wrong host key, replayed session, reordered, altered and replayed frames, all rejected; no user data access outside a session | R9 |
| User data | Card read offline shows no plaintext; altered records rejected; an old copy of the card detected through the host's digest; developer and production data mutually unreadable | R1, R10, R21 |
| Sensor pairing | Certificate signed by an unknown CA, altered certificate, denylisted serial, wrong private key (implicit rejection) all refused; power cut during pairing leaves the old pairing or none, never a half pairing; server rejection removes the pairing | R14, R15 |
| Sensor session | Forged, replayed, reordered and delayed frames rejected; readings older than the maximum age rejected; link cut puts the device in its safe state within the maximum age | R11, R12, R13 |
| Bitstream | Production bitstreams built through Diamond behave like the development builds (same RTL tests run on both); configuration bus capture shows only ciphertext; an unencrypted or foreign bitstream fails the link handshake; an older bitstream of the same device, loaded through JTAG, fails the TEE's version check; a reconfiguration while running ends the link and is logged; blind bit flips in the encrypted bitstream do not yield a working link | R17, R31, R32 |
| XIP | Each attack in `doc/xip.md`: modified, moved, other-slot and earlier-install lines; a whole older image written back; flash copied from another board; an emulator swapping lines after boot; all fail their tags and the CPU stays in reset; the C5 then boots the other slot | R34, R35 |
| C5–FPGA link | Wrong link key, replayed handshake, replayed, reordered and altered frames rejected; the FPGA's TRNG health tests stop the link on a stuck or biased source | R36 |
| ECP5 boundary scan | Boundary scan reaches no key and no fabric state; documented as equivalent to pin probing | R43 |
| FPGA key isolation | No CPU instruction sequence or bus access reads a key (simulation over every register address, and on hardware); debug port absent in production bitstreams; keys cleared on reset, reconfiguration and failures | R37 |
| Recordings | Card and Wi-Fi capture show no plaintext; the C5 firmware's memory never holds plaintext samples or a segment key; the host detects dropped, reordered and substituted blocks and segments; segment keys erased at segment end | R39, R41 |
| Enrollment | Unenrolled device cannot install updates or authenticate; enrollment cannot be repeated; server flags unknown and duplicate identities | R16 |
| Developer builds | Package for another device refused; old-epoch builds refused after an epoch release; version record and eFuses unchanged by developer installs; developer mode shown on the LCD whatever the application does | R21, R22 |
| Event log | Removed or altered entries detected by the host and the server | R26 |
| Radio policy | A release with a radio disabled never initializes it; the TEE withholds Wi-Fi credentials when Wi-Fi is off | R23, R28 |
| BLE and CLI | Fuzz the GATT serial service and the BLE stack (malformed PDUs, connection floods); no advertising without the user action; CLI refuses commands without a session; attempt limits and logging; developer commands absent from production builds | R28 |
| Over-the-air updates | Fake access point and fake server: forged, old and truncated packages refused; interrupted download leaves the old image active; server authentication failure stops the exchange | R29 |
| UART status | Status output contains no user data or keys | R30 |
| Wireless coexistence | Sensor timing and safe-state behavior unaffected by Wi-Fi and BLE load | R13, R23 |

## 5. Fault injection

### Threat

A lab attacker glitches the C5 to skip a check: a signature comparison, a version check, the build mode check, a MAC comparison in the sensor, host or link protocol.
Espressif advisory AR2023-007 shows this works on the C3 and C6 with voltage glitches. The C5 adds glitch detectors, which these tests must also exercise.
On the ECP5, a glitch could make the XIP engine accept a line whose tag failed, or the link engine accept a bad frame.

### Countermeasures to build into our code

1. Compare MACs and signatures in constant time, and check each security decision twice, with the second check on a complemented value.
2. Encode success as a multi-bit value, never 0 or 1, so a single skipped instruction or zeroed register cannot produce it.
3. Count loop iterations in signature and MAC checks, and check the count at the end.
4. Random delays before critical checks (the TRNG is available).
5. On any inconsistency, log it and halt into the safe state; never retry silently.
6. Keep the glitch detectors enabled and log their resets.
7. In the RTL, a line enters the cache and a frame is accepted only on a multi-bit pass constant from the comparator, and the fill and link state machines use encoded states that a single bit flip cannot advance.
8. Tag and link failures clear the FPGA's keys and are reported to the TEE, which counts them.

### Campaigns

| Campaign | Method | Target | Pass |
|---|---|---|---|
| A. Package check | Voltage glitch (crowbar on the core supply) and EM pulses during the TEE's LMS check | Install a package with a bad signature | No bad package installed in the campaign budget; detections logged |
| B. Build mode | Same, during the TEE's developer-mode check | Boot a developer build installed under an old epoch | Never boots |
| C. Sensor MAC | Same, during frame verification | Accept a forged reading | Never accepted |
| D. Secure boot | Same, during the bootloader's check (ROM checks are Espressif's) | Boot an unsigned application | Never boots |
| E. Glitch detectors | Sweep glitch parameters | Find the detection boundary | Detectors fire before any of A to D succeed |
| F. XIP tag check | Voltage and clock glitches on the ECP5 during line fills; first in Verilator with injected faults, then on hardware | Execute a line whose tag failed | Never executed |
| G. Link frames | Same, during frame verification in the FPGA | Accept a forged boot image message or key frame | Never accepted |

### Side channels

- **Flash encryption:** test-vector leakage assessment (TVLA) on the XTS-AES engine with pseudo-rounds at the chosen level, to confirm it removes the leakage AR2023-007 used.
- **AES and HMAC in the TEE:** TVLA on the operations that use the device root and the data key.
- **ECP5:** TVLA on the fabric's AES cores (XIP, link, recording) and, as far as possible, on bitstream decryption. Per-device keys limit the impact (R33).
- **Sensor:** TVLA on the sensor's ML-KEM decapsulation and MAC. A broken sensor exposes only itself (R15), so a modest result may be acceptable.

## 6. Tools

| Tool | Use |
|---|---|
| ESP-IDF with its Unity test framework and Linux host target | Unit tests |
| Python (`cryptography`, reference implementations of LMS, ML-KEM, ML-DSA, Ascon) | Reference models and vectors |
| pytest-embedded | Driving the rig |
| A BLE fuzzer and a controllable Wi-Fi access point | Radio tests |
| ChipWhisperer-Husky, a voltage glitch stage, an EMFI probe | Fault injection |
| A scope or ChipWhisperer for power traces | TVLA |
| Verilator | The FPGA's security RTL, with fault injection |
| LiteForth `vm.c` | Application code before hardware |

## 7. Open questions

See `doc/questions.md` (Test rows).
