# Open Questions

Every open question in one place. Earlier architectures are kept in git history (commits `cecf901` and `8c54b84`); questions from them that still apply are carried over here.

**Priority:**
- **1:** blocks something irreversible (eFuse burning, ECP5 key programming, enrollment) or the board design.
- **2:** needed before implementation of that part.
- **3:** needed before a submission.

## Matrix

| ID | Question | Where | How to close | Priority |
|---|---|---|---|:-:|
| **C5** | | | | |
| C1 | Confirm every eFuse setting and its effect on real C5 parts, including the order they are burned in | [c5.md](c5.md#other-efuse-settings) | Bench, with sacrificial parts | 1 |
| C2 | Secure download mode, or download mode disabled entirely | [c5.md](c5.md#other-efuse-settings) | Decide: keeping secure download mode allows reflashing a bricked unit at the factory | 1 |
| C3 | Use of KEY5: blank, or a soft-JTAG re-enable key for failure analysis of returned units | [c5.md](c5.md#efuse-key-blocks) | Decide; a per-device JTAG token is a new secret to manage | 1 |
| C4 | XTS-AES-256 through the Key Manager, once ESP-IDF supports it on the C5 | [c5.md](c5.md#efuse-key-blocks) | Watch ESP-IDF; the choice is made at first boot and cannot change later | 1 |
| C5 | C5HR8 (external flash, probe point) or C5HF4 (flash in the package, no PSRAM) | [c5.md](c5.md#part) | Leaning HR8: PSRAM for the radio stacks and SD write buffering (C13) | 1 |
| C6 | C5 flash size and partition sizes | [c5.md](c5.md#flash-partitions) | Real image and bitstream sizes | 2 |
| C7 | ESP-TEE maturity on the C5: release status, and that APM covers the HMAC peripheral, eFuse controller and TEE flash regions as needed | [c5.md](c5.md#tee) | ESP-IDF release notes; isolation tests (`doc/test.md`) | 1 |
| C8 | LMS verification in ESP-IDF's Mbed TLS build; library choices for ML-KEM, ML-DSA and Ascon in the TEE | [arch.md](arch.md#algorithm-bill-of-materials) | Build and size them in the TEE | 2 |
| C10 | Glitch detector settings on the C5 and how their resets are reported | [c5.md](c5.md#part) | Technical reference manual; campaign E (`doc/test.md`) | 2 |
| C11 | Whether the TEE's hardware timer and the anti-rollback eFuse update behave as assumed | [c5.md](c5.md#anti-rollback) | Bench | 2 |
| C12 | Can the TEE deny the C5 firmware access to the radio hardware through the APM, so a compromised firmware cannot enable a radio the policy disables? | [c5.md](c5.md#radios) | Technical reference manual; test | 2 |
| C13 | RAM budget with the TEE, Wi-Fi and BLE stacks, SD buffering and the link | [c5.md](c5.md#part) | Build and measure | 2 |
| C14 | PARLIO receive from the FPGA at the recording rate, alongside SPI2 traffic and Wi-Fi | [fpga.md](fpga.md#the-link-to-the-c5) | Bench | 2 |
| **FPGA** | | | | |
| F1 | Burn order and verification of the ECP5's key and decrypt-only eFuses, and whether the key's eFuses can be read or reprogrammed over JTAG afterwards | [enrollment.md](enrollment.md#device-enrollment) | Lattice documentation; bench with sacrificial parts | 1 |
| F3 | ECP5 bitstream encryption mode and CRC width, to bound blind edits (R32) | [fpga.md](fpga.md#bitstream) | Lattice documentation; analysis | 2 |
| F5 | Whether the LFE5U-25F's 24K LUTs fit the security blocks (about 8.5K to 15K) plus the application's logic | [fpga.md](fpga.md#resource-estimate) | Synthesis | 2 |
| F6 | XIP line and cache sizes, GHASH width, FPGA flash size | [xip.md](xip.md#open-questions) | Measure on real LiteForth applications | 2 |
| F7 | Ring-oscillator TRNG design and health-test thresholds on the ECP5 | [fpga.md](fpga.md#trng) | Characterize on hardware | 2 |
| F8 | An LCD overlay for developer mode and alarms that the application cannot draw over | [roles.md](roles.md#running-a-developer-build) | RTL design | 3 |
| F9 | Keeping the development flow (Yosys, nextpnr) and the production flow (Diamond) equivalent: same RTL, constraints and tests, and Yosys EDIF into Diamond or Diamond's own synthesis | [enrollment.md](enrollment.md#bitstream-build-service) | Run the RTL tests on both builds | 2 |
| **Acquisition and recordings** | | | | |
| Q3 | Sample rate per channel and segment length | [acquisition.md](acquisition.md#hardware) | Device design | 2 |
| Q4 | Recording recipients: the host only, or also a clinic server; how the host backs up its recording private key | [acquisition.md](acquisition.md#recording-encryption) | Decide | 2 |
| Q5 | Provenance signatures on segments (per-device ML-DSA key) | [acquisition.md](acquisition.md#recording-encryption) | Decide | 3 |
| Q7 | Enclosure-open switch logged by the TEE | [arch.md](arch.md#risk-assessment) | Decide | 3 |
| **Sensor** | | | | |
| S1 | Frame MAC: Ascon-AEAD128 or HMAC-SHA256 | [sensor.md](sensor.md#sessions) | Sensor microcontroller's performance and code size | 2 |
| S2 | Physical layer: the sensor's existing interface, cable, and which C5 peripheral drives it | [sensor.md](sensor.md#physical-layer) | Sensor and cable specification | 1 |
| S3 | Sensor microcontroller: TRNG, read-out protection, ML-KEM-768 speed | [sensor.md](sensor.md#the-sensor-end) | Part selection | 1 |
| S4 | Clinical parameters: maximum reading age, safe state, behavior while a pairing is unconfirmed | [sensor.md](sensor.md#server-confirmation) | Clinical and risk management decision | 2 |
| S5 | Should the sensor authenticate the device (device certificates)? | [sensor.md](sensor.md#pairing) | Depends on whether sensor commands matter | 3 |
| S6 | Sensor firmware updates | [fda.md](fda.md#3-updateabilitypatchability-view) | Design with the sensor maker | 3 |
| S7 | Who holds the sensor CA keys: the manufacturer or the sensor maker | [enrollment.md](enrollment.md#keys-held-by-the-manufacturer) | Business decision | 2 |
| **Enrollment and server** | | | | |
| E2 | Device root key: derived in the HSM and burned over the factory link (base), or generated on chip and exported wrapped to the HSM | [enrollment.md](enrollment.md#device-enrollment) | Decide; the second removes the root from the factory link, but the HSM could then no longer derive the FPGA keys for bitstream builds without storing every root | 1 |
| E3 | Server and host relay protocols in detail | [enrollment.md](enrollment.md#contact-with-the-server) | Specification | 2 |
| E4 | Who may authorize a wipe | [enrollment.md](enrollment.md#retirement) | Decide | 3 |
| **Architecture** | | | | |
| A1 | Is the application owner a different company from the manufacturer? (Then two LMS key sets) | [roles.md](roles.md#roles) | Business decision | 2 |
| A2 | Host session protocol: frame format, timeouts, how the host stores its keys | [README](../README.md#host-sessions-and-user-data) | Specification | 2 |
| A3 | The full list of logged events | [fda.md](fda.md#6-gaps-for-a-submission) | Specification | 3 |
| A4 | Adopt the Code Secrecy Profile? | [arch.md](arch.md#optional-code-secrecy-profile) | Business decision | 3 |
| A5 | CLI command set per session type, and attempt limits | [README](../README.md#radios-and-the-cli) | Specification | 2 |
| A6 | BLE host tool: phone app, Web Bluetooth page, or desktop tool | [README](../README.md#radios-and-the-cli) | Decide | 2 |
| A7 | Wi-Fi provisioning and TLS server authentication (pinned CA or key) | [README](../README.md#radios-and-the-cli) | Specification | 2 |
| A8 | C5–FPGA link message set and framing | [fpga.md](fpga.md#the-link-to-the-c5) | Specification | 2 |
| **Test** | | | | |
| T1 | Fault-injection and side-channel lab: in house or contracted | [test.md](test.md#5-fault-injection) | Decide | 3 |
| T2 | Independent penetration test supplier | [fda.md](fda.md#6-gaps-for-a-submission) | Decide | 3 |
| **ICS55** | | | | |
| I1 | Whether the ICS55 SRAM is usable as a PUF for the ASIC's keys | [ics55.md](ics55.md#where-the-keys-come-from) | Test chip | 3 |

Closed: C9 (developer images in TEE slots: developer builds are now FPGA applications, outside secure boot), D1 (developer signing: a per-device developer key, no signing service),
E1 (server path: Wi-Fi when enabled, otherwise the host), the old F1 (`bitgen` needs Diamond's `.ncd`: production bitstreams come from Diamond),
the old F2 (the AES key and a decrypt-only setting are eFuses; readback disable is a bitstream setting; boundary scan stays), the per-device key update (a headless Diamond Tcl script with the ECO editor writes the EBR `INIT` properties), F4 (the slave SPI pins carry the link), the watermark (removed),
Q6 (safety alarms need no path independent of the FPGA application).

## Decisions taken

### By you

- ESP32-C5HR8 as the root of trust, installer and gateway. No ATECC608B.
- **The application runs on the ECP5,** in LiteForth, executing in place from a QSPI flash attached to the FPGA.
- **LFE5U-25F-6BG256C.** Per-device keys in the bitstream, encrypted under the ECP5's own key with Lattice Diamond's `bitgen` (which needs a Diamond place-and-route and a free Lattice licence), with per-device keys written by a Diamond ECO Tcl script; decrypt-only eFuse; per-device bitstream packages from the server, including for offline delivery.
- The ECP5's slave SPI configuration pins carry the link after configuration.
- Recordings encrypted in the FPGA with segment keys from the C5, so the C5's network side never sees plaintext.
- Four channels from two NAU88C22 CODECs, with the FPGA providing both I2S masters; LCD and speaker inside a tamper-evident enclosure.
- No watermark; replay or substitution on I2S is left to the tamper-evident seal (R40).
- Safety alarms go through the FPGA application; no independent path.
- The temperature sensor connects to the C5, is replaceable, and must pair without a network.
- Enrollment in the manufacturer's database is required for updates, and the ecosystem flags unknown identities.
- Over-the-air updates over Wi-Fi, and the CLI over a BLE serial service; the application owner enables or disables each radio. The UART stays for status and fallback.

### By default (change any of these)

- **The C5 installs, the FPGA executes:** the TEE verifies application packages and encrypts them per line; the FPGA has no LMS, SHA-256 or install path.
- **The TEE's record decides** which bitstream is configured and which install salt is sent, so neither flash can roll the FPGA back on its own.
- **Link and image keys derived from the device root,** so the HSM can build bitstreams and the TEE can derive the same keys.
- **AES-only FPGA crypto:** AES-256-GCM for lines, link and recordings, an AES-256-CMAC KDF, a ring-oscillator TRNG.
- **Recording key pair generated by the host;** the device holds only the public key.
- **Developer builds as FPGA applications** with a per-device symmetric developer key; offline, no signing service.
- **Secure boot with RSA-3072,** not ECDSA, because of the C5's ECDSA erratum. LMS on every package.
- **XTS-AES-128 flash encryption** from an eFuse key generated on chip, until the Key Manager is supported (C4).
- **ESP-TEE** isolates the C5's keys from the C5 firmware, which does all I/O on ciphertext.
- **Device root key from the HSM** (E2). **Host data secret** from a separate HSM master, never stored on the device.
- **Anti-rollback in three layers:** the TEE's version record, eFuse steps for security releases only, and the server.
- **Sensor:** ML-DSA certificates, ML-KEM pairing, per-frame MACs with session keys, device-timed reading age, server confirmation and denylists.
- **Radio policy in the signed application package;** radio stacks in the C5 firmware, never in the TEE.
- **BLE as an untrusted transport;** **UART status is read-only.**
