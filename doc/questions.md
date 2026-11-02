# Open Questions

Every open question in one place. Questions from the earlier FPGA-based design are on the `archive/fpga-rot-v0` branch; those that still apply are carried over here.

**Priority:**
- **1:** blocks something irreversible (eFuse burning, enrollment) or the board design.
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
| C5 | C5HR8 (external flash, probe point) or C5HF4 (flash in the package, no PSRAM) | [c5.md](c5.md#part) | Leaning HR8: its PSRAM leaves room for the Wi-Fi and BLE stacks (C13) | 1 |
| C6 | Flash size and partition sizes | [c5.md](c5.md#flash-partitions) | Real image and bitstream sizes | 2 |
| C7 | ESP-TEE maturity on the C5: release status, and that APM covers the HMAC peripheral, eFuse controller and TEE flash regions as needed | [c5.md](c5.md#tee) | ESP-IDF release notes; isolation tests (`doc/test.md`) | 1 |
| C8 | LMS verification in ESP-IDF's Mbed TLS build; library choices for ML-KEM, ML-DSA and Ascon in the TEE | [arch.md](arch.md#algorithm-bill-of-materials) | Build and size them in the TEE | 2 |
| C9 | That a signed application image cannot be loaded from a TEE slot (image type bound into what is signed) | [roles.md](roles.md#why-developer-builds-go-through-the-signing-service) | ESP-IDF image format; test | 1 |
| C10 | Glitch detector settings on the C5 and how their resets are reported | [c5.md](c5.md#part) | Technical reference manual; campaign E (`doc/test.md`) | 2 |
| C11 | Whether the TEE's hardware timer and the anti-rollback eFuse update behave as assumed | [c5.md](c5.md#anti-rollback) | Bench | 2 |
| C12 | Can the TEE deny the application access to the radio hardware through the APM, so a compromised application cannot enable a radio the policy disables? | [c5.md](c5.md#radios) | Technical reference manual; test | 2 |
| C13 | RAM budget with the TEE, Wi-Fi and BLE stacks, and the application | [c5.md](c5.md#part) | Build and measure | 2 |
| **Sensor** | | | | |
| S1 | Frame MAC: Ascon-AEAD128 or HMAC-SHA256 | [sensor.md](sensor.md#sessions) | Sensor microcontroller's performance and code size | 2 |
| S2 | Physical layer: the sensor's existing interface, cable, and which C5 peripheral drives it | [sensor.md](sensor.md#physical-layer) | Sensor and cable specification | 1 |
| S3 | Sensor microcontroller: TRNG, read-out protection, ML-KEM-768 speed | [sensor.md](sensor.md#the-sensor-end) | Part selection | 1 |
| S4 | Clinical parameters: maximum reading age, safe state, behavior while a pairing is unconfirmed | [sensor.md](sensor.md#server-confirmation) | Clinical and risk management decision | 2 |
| S5 | Should the sensor authenticate the device (device certificates)? | [sensor.md](sensor.md#pairing) | Depends on whether sensor commands matter | 3 |
| S6 | Sensor firmware updates | [fda.md](fda.md#3-updateabilitypatchability-view) | Design with the sensor maker | 3 |
| S7 | Who holds the sensor CA keys: the manufacturer or the sensor maker | [enrollment.md](enrollment.md#keys-held-by-the-manufacturer) | Business decision | 2 |
| **Enrollment and server** | | | | |
| E1 | ~~How the device reaches the server~~ Closed: over Wi-Fi when the application owner enables it, otherwise through the host | [enrollment.md](enrollment.md#contact-with-the-server) | | |
| E2 | Device root key: derived in the HSM and burned over the factory link (base), or generated on chip and exported wrapped to the HSM | [enrollment.md](enrollment.md#device-enrollment) | Decide; the second removes the root from the factory link but the HSM must then store every root | 1 |
| E3 | Server and host relay protocols in detail | [enrollment.md](enrollment.md#contact-with-the-server) | Specification | 2 |
| E4 | Who may authorize a wipe | [enrollment.md](enrollment.md#retirement) | Decide | 3 |
| **Architecture** | | | | |
| A1 | Is the application owner a different company from the manufacturer? (Then two LMS key sets, and the signing service checks owner approval before signing) | [roles.md](roles.md#roles) | Business decision | 2 |
| A2 | Host session protocol: frame format, timeouts, how the host stores its keys | [README](../README.md#host-sessions-and-user-data) | Specification | 2 |
| A3 | The full list of logged events | [fda.md](fda.md#6-gaps-for-a-submission) | Specification | 3 |
| A4 | Adopt the Code Secrecy Profile? | [arch.md](arch.md#optional-code-secrecy-profile) | Business decision | 3 |
| A5 | CLI command set per session type, and attempt limits | [README](../README.md#radios-and-the-cli) | Specification | 2 |
| A6 | BLE host tool: phone app, Web Bluetooth page, or desktop tool | [README](../README.md#radios-and-the-cli) | Decide | 2 |
| A7 | Wi-Fi provisioning and TLS server authentication (pinned CA or key) | [README](../README.md#radios-and-the-cli) | Specification | 2 |
| **Developer builds** | | | | |
| D1 | ~~Developer signing model~~ Closed: the signing service, since developers always have a network; builds are delivered over the air | [roles.md](roles.md#why-developer-builds-go-through-the-signing-service) | | |
| **FPGA** | | | | |
| F1 | ECP5 slave SPI pins after configuration, and whether user logic can read CCLK | [fpga.md](fpga.md#configuration) | ECP5 sysCONFIG documentation; bench | 1 |
| F2 | What the FPGA does, and whether any of its results need integrity the C5 cannot check | [fpga.md](fpga.md#data-link) | Device design | 2 |
| F3 | ECP5 size, which sets the bitstream size | [fpga.md](fpga.md#bitstream) | Device design | 2 |
| **Test** | | | | |
| T1 | Fault-injection and side-channel lab: in house or contracted | [test.md](test.md#5-fault-injection) | Decide | 3 |
| T2 | Independent penetration test supplier | [fda.md](fda.md#6-gaps-for-a-submission) | Decide | 3 |
| **ICS55** | | | | |
| I1 | Does the ASIC need a programmable part? | [ics55.md](ics55.md#open-questions) | Follows F2 | 3 |

## Decisions taken

### By you

- ESP32-C5HR8 as the root of trust; the application runs on it.
- No ATECC608B.
- The ECP5 is a peripheral; nothing secret crosses its SPI link, so the link is not encrypted.
- The temperature sensor connects to the C5, is replaceable, and must pair without a network.
- Enrollment in the manufacturer's database is required for updates, and the ecosystem flags unknown identities.
- Developers always have a network: developer builds go through the signing service and arrive over the air.
- Over-the-air updates over Wi-Fi, and the CLI over a BLE serial service; the application owner enables or disables each radio.
- The UART stays, for status reports and as a wired fallback.

### By default (change any of these)

- **Secure boot with RSA-3072,** not ECDSA, because of the C5's ECDSA erratum. LMS on update packages on top.
- **XTS-AES-128 flash encryption** from an eFuse key generated on chip, until the Key Manager is supported (C4).
- **ESP-TEE** isolates keys from the application, and the application does all link and card I/O on ciphertext.
- **Device root key from the HSM,** so hosts, developer keys and server authentication can be derived centrally (E2).
- **Host data secret** from a separate HSM master, never stored on the device.
- **Anti-rollback in three layers:** the TEE's version record, eFuse steps for security releases only, and the server.
- **Plain, fleet-wide FPGA bitstream** from the open toolchain, embedded in the application image, with a build ID check.
- **Sensor:** ML-DSA certificates, ML-KEM pairing, per-frame MACs with session keys, device-timed reading age, server confirmation and denylists.
- **Radio policy in the signed build descriptor;** radio stacks in the application, never in the TEE.
- **BLE as an untrusted transport:** our own authenticated sessions over it; advertising only after a user action; one connection; rotating private addresses.
- **UART status is read-only** and holds nothing secret.
