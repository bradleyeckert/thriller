# Test Plan

How `thriller` is tested, from reference models to fault injection. Risk IDs (R1–R46) refer to `doc/arch.md`.

## 1. Approach

Security lives in three places: the FPGA's configuration engine (the vendor's, characterized by the vendor), the secure element (certified), and our own RTL and Forth in the loader domain.
Testing therefore concentrates on:

- **our protocols and their implementation:** packages, the secure element exchanges, the ratchet, host sessions, recordings, sensor pairing and sessions, user data, the event log, attestation;
- **our RTL:** the XIP engine, key paths and the key gate, the recording engine, the mailbox, the TRNG, the security block;
- **the chip configurations:** FPGA eFuses and locks, the secure element's slot configuration;
- **fault injection and side channels** on the checks we write, and on the vendor's claimed countermeasures.

### Layers

| Layer | What | Where |
|---|---|---|
| 1. Reference models | Python models of every format and protocol: package layout and signatures, key derivations, per-line GCM (and CCM), headers and boot record, secure element exchanges, ratchet, recording segments, host session, sensor pairing and session, user data records, event log chain, attestation report | Workstation; produce test vectors |
| 2. Unit tests | RTL modules against the vectors in Verilator; loader Forth against the same vectors in LiteForth's `vm.c` with modeled peripherals; cryptoauthlib against a real secure element for the exchanges | Workstation and bench |
| 3. System tests | Whole device against simulated host, sensor, server, network and card | Hardware-in-the-loop rig |
| 4. Fault injection and side channels | Attacks on one unit | Lab bench |
| 5. Penetration test | Independent team, whole system | External |

### Evidence

Each test names the risk it covers. The catalogue below is the traceability matrix between risks and tests that an FDA submission needs (`doc/fda.md`).

## 2. Reference models

- **Formats:** platform and application packages, manifests and inclusion proofs, developer packages, image headers, XIP lines and tags, the boot record, records in flash, secure element command and response frames, recording segment headers and blocks, sensor certificates and transcripts, session frames, user data records, log entries, attestation reports.
- **Cryptography:** known-answer tests for each algorithm from the standards (LMS from RFC 8554, ML-KEM and ML-DSA from the FIPS 203 and 204 vectors, AES-GCM and AES-CMAC from the NIST vectors, the ATECC608C's SHA-256 message formats from cryptoauthlib); the same vectors drive the RTL and the Forth.
- **Protocols:** both ends of the host session, the sensor protocol and the server exchange, so each end can be tested against a model of the other; a secure element model that enforces the slot configuration, so a configuration mistake shows up in simulation before a part is locked.

The sensor's firmware is tested against the same models.

## 3. Hardware-in-the-loop rig

- A production-configured board (locked FPGA, locked secure element, flash, CODECs, LCD, card), plus boards with the eFuses left open, an unlocked FPGA and an unlocked secure element for debugging.
- **Interposers** on the QSPI flash (or a flash emulator), on the secure element's I2C bus, and on one I2S bus, able to record, replay and alter traffic.
- **Signal source** on the CODEC inputs: synthetic EEG at known levels.
- **Host simulator** on the UART and on the LAN, driven by test scripts.
- **Network test harness:** a switch, a packet generator and a server simulator able to act as the edge proxy, the DHCP server or a fake server, and to drop, delay, replay and flood.
- **Sensor simulator** on the sensor link, able to misbehave on command (bad certificates, wrong MACs, replays, delays, silence), and a **link interposer** between it and the device.
- **Power control** for power cuts at chosen points during installs, the ratchet write and pairing.
- A flash programmer, and a JTAG pod on unlocked FPGAs.

## 4. Test catalogue

| Area | Tests | Risks |
|---|---|---|
| Bitstream | Configuration bus capture shows only ciphertext; an unencrypted, unsigned or altered bitstream is refused; one encrypted for another device fails to configure; an older bitstream of the same device, after an update, pairs with neither key and stays in recovery; corrupting the active slot falls back to the other slot with the same result; blind bit flips in the encrypted bitstream (ECP5) do not yield a working pairing | R17, R31, R32, R44 |
| Ratchet | Power cut before, during and after the slot 0 write at each boot leaves a device that boots; a release that fails to configure leaves the old release working; a skipped-release package built for the wrong inherited key is refused by the secure element and reported | R4, R17 |
| Boot chain | Forged or old loader header refused by the boot ROM; forged or old application header refused by the loader; slot fallback when an image fails; recovery when both fail; a header for another device's application key fails | R2, R4, R34, R35 |
| XIP | Each attack in `doc/xip.md`: modified, moved, other-slot and earlier-install lines; a whole older image written back; flash copied from another board; an emulator swapping lines after boot; all fail and lock down, and the next boot falls back | R6 |
| Updates | Forged LMS signature, bad inclusion proof, altered ciphertext, wrong distribution key, truncated package: all refused before any flash write, for both chains; a platform package for another device refused; power cut at every step leaves a bootable device; a new image that fails its checks is never selected | R3, R18 |
| Secure element | Every authenticated read with a replayed or forged response is rejected; an altered encrypted read is caught by the check value or the header HMAC; a MAC-oracle attempt with a chosen nonce is refused (ReqRandom); the data key is not released without the host's CheckMac; counters advanced from the bus are detected and reported; the configuration dump matches `doc/se.md` before and after lock | R1, R36 |
| Key isolation | No instruction sequence or bus access on either core reads a key (simulation over every register address, and on hardware); the application core's buses have no path into the loader domain (netlist connectivity check); no debug port in production bitstreams; keys cleared on reset, reconfiguration and failures | R8, R37 |
| Mailbox | Parser fuzzing on the software platform; oversized, misaligned and racing requests rejected; a request changed after submission has no effect | R45 |
| Debug lockdown | JTAG unusable after enrollment (ECP5: boundary scan reaches no key or fabric state); UART recovery accepts only signed loader packages and reads out nothing | R7, R43 |
| Host session | Wrong host key, replayed challenge, reordered, altered and replayed frames, all rejected; no user data access outside a session; attempt limits and logging | R9, R28 |
| User data | Card read offline shows no plaintext; altered records rejected; an old copy of the card detected through slot 11; developer and production data mutually unreadable | R1, R10, R21 |
| Attestation | A report with a stale nonce, a forged signature or a wrong MAC is rejected by the verifier model; a report from a bitstream with a retired pairing key cannot be obtained; the report's versions match the installed images | R16 |
| Sensor pairing | Certificate signed by an unknown CA, altered certificate, denylisted serial, wrong private key (implicit rejection) all refused; power cut during pairing leaves the old pairing or none; server rejection removes the pairing | R14, R15 |
| Sensor session | Forged, replayed, reordered and delayed frames rejected; readings older than the maximum age rejected; link cut puts the device in its safe state within the maximum age | R11, R12, R13 |
| Recordings | Card and network capture show no plaintext; the loader's memory holds a segment key only in masked form and only during encapsulation; the recording engine accepts no samples without a key; the host detects dropped, reordered and substituted blocks and segments; segment keys erased at segment end | R39, R41 |
| Enrollment | Unenrolled device cannot install updates or authenticate; enrollment cannot be repeated; server flags unknown and duplicate identities | R16 |
| Developer builds | Package for another device refused; old-epoch builds refused after an epoch release; counter 1 unchanged by developer installs; developer mode shown on the overlay whatever the application draws | R21, R22 |
| Event log | Removed or altered entries detected by the host and the server | R26 |
| Network policy and transport | A release with the port disabled holds the PHY in reset, and no software path releases it; RTL fuzzing of the Ethernet transport (malformed ARP, IP, ICMP and UDP headers, bad checksums, runt and giant frames, floods) in simulation and on hardware never delivers a payload that is not a well-formed UDP datagram to our port, and never wedges the transport beyond a re-initialization; ARP and DHCP spoofing cause only loss of connectivity; CLI refuses commands without a session; developer commands absent from production builds | R23, R28 |
| Over-the-air updates | Fake access point and fake server: forged, old and truncated packages refused; interrupted download leaves the old image active; server authentication failure stops the exchange | R29 |
| UART status | Status output contains no user data or keys | R30 |
| Coexistence | Sensor timing and safe-state behavior unaffected by recording, card and network load, including floods | R13 |

## 5. Fault injection

### Threat

A lab attacker glitches the FPGA to skip a check: a header comparison, a version comparison, a MAC comparison in the secure element, sensor or host protocol, a tag comparison in the XIP engine.
On the configuration engine, a glitch could make it accept a bad bitstream; that is the vendor's countermeasure to test.

### Countermeasures to build into our RTL and Forth

1. Compare MACs, tags and signatures in constant time, in hardware comparators, and check each security decision twice, with the second check on a complemented value.
2. Encode success as a multi-bit pass token, never 0 or 1, so a single skipped instruction or zeroed register cannot produce it; keys load only on pass tokens.
3. Count loop iterations in signature and MAC checks, and check the count at the end (the flow counter in the security block).
4. Random delays before critical checks (the TRNG is available).
5. On any inconsistency, lock down; never retry silently.
6. Encoded state machines in the fill, key gate and secure element sequencers that a single bit flip cannot advance.
7. Clock checker and supply monitor inputs to the security block; their events are logged.

### Campaigns

| Campaign | Method | Target | Pass |
|---|---|---|---|
| A. Package check | Voltage glitch (crowbar on the core supply) and EM pulses during the loader's LMS check | Install a package with a bad signature | No bad package installed in the campaign budget; detections logged |
| B. Header and version | Same, during the boot ROM's and loader's header checks | Boot an old or forged image | Never boots |
| C. Secure element MACs | Same, during MAC comparison | Accept a forged counter or key read | Never accepted |
| D. Sensor and host MACs | Same, during frame verification | Accept a forged reading or frame | Never accepted |
| E. XIP tag check | Voltage and clock glitches during line fills; first in Verilator with injected faults, then on hardware | Execute a line whose tag failed | Never executed |
| F. Configuration engine | Voltage and EM glitches during configuration | Configure an unsigned or altered bitstream | Never configures; the vendor's detectors fire where present |
| G. Key gate | Glitches during key loading | Load a key without its pass token | Never loads |

### Side channels

- **Configuration decryption:** test-vector leakage assessment (TVLA) on the configuration engine as far as the family allows, to check the vendor's DPA claim (R5).
- **Hard AES block:** TVLA as used by the XIP engine, the recording engine and the install port, including key loading into it (R33).
- **SHA-256 core:** TVLA with the pairing key and the HMAC keys; the result decides whether the core must be masked (H4).
- **Secure element:** the part's certification covers it; the I2C exchanges are tested for timing leaks in the fabric's comparators.
- **Sensor:** TVLA on the sensor's ML-KEM decapsulation and MAC. A broken sensor exposes only itself (R15).

## 6. Tools

| Tool | Use |
|---|---|
| Verilator | The security RTL, with fault injection, against the vectors |
| LiteForth `vm.c` and `stage1sim` | The loader and application Forth with modeled peripherals; two cores and the mailbox |
| cryptoauthlib and a Microchip development kit | Exercising the slot configuration on real secure elements before locking |
| Python (`cryptography`, reference implementations of LMS, ML-KEM, ML-DSA) | Reference models and vectors |
| A packet generator (Scapy or similar) and a managed switch | Network transport fuzzing and the edge proxy, DHCP and fake-server cases |
| ChipWhisperer-Husky, a voltage glitch stage, an EMFI probe | Fault injection |
| A scope or ChipWhisperer for power traces | TVLA |
| The family's programmer and tools | eFuse state, encrypted bitstream generation |

## 7. Open questions

See `doc/questions.md` (Test rows).
