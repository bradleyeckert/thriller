# Open Questions

Every open question in one place. Earlier architectures are kept in git history (commits `cecf901`, `8c54b84` and `eb63f10`); questions from them that still apply are carried over here.

**Priority:**
- **1:** blocks something irreversible (eFuse burning, secure element locking, enrollment) or the board design.
- **2:** needed before implementation of that part.
- **3:** needed before a submission.

## Matrix

| ID | Question | Where | How to close | Priority |
|---|---|---|---|:-:|
| **FPGA** | | | | |
| F1 | Pango Design Suite: write each device's pairing keys into block RAM contents of a routed design from a script, then encrypt and sign, without placing and routing again; otherwise per-device place-and-route time | [logos2](../fpga/logos2/README.md) | Pango documentation and support; try it | 1 |
| F2 | Confirm that the PG2L50H can be set to accept only encrypted and only signed bitstreams | [logos2](../fpga/logos2/README.md) | Pango documentation; bench with sacrificial parts | 1 |
| F3 | Master SPI configuration from the QSPI flash and the multi-boot mechanism on the PG2L50H: addresses, golden-image rules, how the loader points at the other slot | [flash.md](flash.md#regions) | Pango documentation; bench | 1 |
| F4 | The hard AES block: AES-256 support, whether it computes GHASH (GCM) or only the block cipher (then CCM), throughput shared by three users, number of instances, and how keys are loaded into it | [hw.md](hw.md#the-hard-aes-block) | Pango documentation | 1 |
| F5 | Can the hard AES block use the eFuse key, or a key derived from it, without exposing it? (Then the pairing keys could be wrapped rather than stored in the bitstream) | [logos2](../fpga/logos2/README.md) | Pango documentation | 3 |
| F6 | XIP line and cache sizes, loader and application slot sizes | [xip.md](xip.md#caches) | Measure on real LiteForth code | 2 |
| F7 | Ring-oscillator TRNG design and health-test thresholds on the FPGA | [fpga.md](fpga.md#trng) | Characterize on hardware | 2 |
| F8 | The LCD overlay band for developer mode and alarms that the application cannot draw over | [hw.md](hw.md#application-core-domain) | RTL design | 3 |
| F9 | PG2L50H bitstream size, for the flash's bitstream slots | [flash.md](flash.md#regions) | Build | 2 |
| F10 | ECP5 fallback: eFuse burn order, CRC width against blind edits (R32), master SPI and dual-boot layout, and keeping its Yosys/nextpnr and Diamond flows equivalent | [ecp5](../fpga/ecp5/README.md) | Only if the fallback is used | 3 |
| F11 | PolarFire, CrossLink-NX and Titanium as alternatives: the open items in their folders, and the country-of-origin requirements of the target markets | [fpga/](../fpga/README.md) | Vendor documentation; business decision | 3 |
| **Hardware** | | | | |
| H1 | AXI4-Lite latency: whether the decoder and slaves answer in the cycles LiteForth's memory state machine expects, or whether ROM and SRAM need a tightly coupled path | [hw.md](hw.md#bus-choice) | RTL and simulation | 2 |
| H2 | Mailbox message set, formats and message RAM size | [hw.md](hw.md#mailbox) | Specification | 2 |
| H3 | Port numbering agreed with LiteForth's `iomap.h` before any RTL fixes them | [hw.md](hw.md#modules) | Agree | 2 |
| H4 | Side-channel resistance of the SHA-256 core, which carries the pairing key; whether it must be masked | [arch.md](arch.md#algorithm-bill-of-materials) | TVLA on hardware (`doc/test.md`) | 2 |
| H5 | Speed of LMS verification, ML-KEM-768 encapsulation and ML-DSA-44 verification as Forth on the loader core with the SHA-256 core | [arch.md](arch.md#algorithm-bill-of-materials) | Build and measure in `vm.c`, then on hardware | 2 |
| H6 | Whether the segment key's wrap for ML-KEM encapsulation moves from masked Forth into hardware | [hw.md](hw.md#two-output-modes) | Decide after H5 | 3 |
| H7 | Flash part, its behavior on power loss during erase and program, and whether 32 MB is right | [flash.md](flash.md#assumptions) | Part selection | 2 |
| **Secure element** | | | | |
| E5 | Confirm the slot configuration on real parts before locking: ReqRandom on slot 0, ReqAuth on slots 3 and 7, the encrypted write on slot 0 that the ratchet needs, the KDF command with slot 1 as source and encrypted output | [se.md](se.md#decisions-to-freeze-before-locking) | cryptoauthlib on a development kit | 1 |
| E6 | A second-source part, qualified against the slot map | [se.md](se.md#part) | Qualification | 3 |
| E7 | Slot 11 write endurance against the session rate | [se.md](se.md#user-data-freshness) | Datasheet and the expected session rate | 2 |
| E8 | TrustCUSTOM parts from Microchip, or blank parts provisioned at the station | [enrollment.md](enrollment.md#device-enrollment) | Business decision; volume | 1 |
| **Acquisition and recordings** | | | | |
| Q3 | Sample rate per channel and segment length | [acquisition.md](acquisition.md#hardware) | Device design | 2 |
| Q4 | Recording recipients: the host only, or also a clinic server; how the host backs up its recording private key | [acquisition.md](acquisition.md#recording-encryption) | Decide | 2 |
| Q5 | Provenance signatures on segments (per-device ML-DSA key) | [acquisition.md](acquisition.md#recording-encryption) | Decide | 3 |
| Q7 | Enclosure-open switch as a security block input, logged | [arch.md](arch.md#risk-assessment) | Decide | 3 |
| **Sensor** | | | | |
| S2 | Physical layer: the sensor's existing interface, cable, and the sensor-link module that drives it | [sensor.md](sensor.md#physical-layer) | Sensor and cable specification | 1 |
| S3 | Sensor microcontroller: TRNG, read-out protection, ML-KEM-768 speed | [sensor.md](sensor.md#the-sensor-end) | Part selection | 1 |
| S4 | Clinical parameters: maximum reading age, safe state, behavior while a pairing is unconfirmed | [sensor.md](sensor.md#server-confirmation) | Clinical and risk management decision | 2 |
| S5 | Should the sensor authenticate the device (device certificates)? | [sensor.md](sensor.md#pairing) | Depends on whether sensor commands matter | 3 |
| S6 | Sensor firmware updates | [fda.md](fda.md#3-updateabilitypatchability-view) | Design with the sensor maker | 3 |
| S7 | Who holds the sensor CA keys: the manufacturer or the sensor maker | [enrollment.md](enrollment.md#keys-held-by-the-manufacturer) | Business decision | 2 |
| **Enrollment and server** | | | | |
| E3 | Server and host relay protocols in detail | [enrollment.md](enrollment.md#contact-with-the-server) | Specification | 2 |
| E4 | Who may authorize a wipe | [enrollment.md](enrollment.md#retirement) | Decide | 3 |
| **Architecture** | | | | |
| A1 | Is the application owner a different company from the manufacturer? (Then two LMS key sets) | [roles.md](roles.md#roles) | Business decision | 2 |
| A2 | Host session protocol: frame format, timeouts, how the host stores its keys | [README](../README.md#host-sessions-and-user-data) | Specification | 2 |
| A3 | The full list of logged events | [fda.md](fda.md#6-gaps-for-a-submission) | Specification | 3 |
| A4 | Adopt the Code Secrecy Profile? | [arch.md](arch.md#optional-code-secrecy-profile) | Business decision | 3 |
| A5 | CLI command set per session type, and attempt limits | [README](../README.md#radios-and-the-cli) | Specification | 2 |
| A6 | BLE host tool: phone app, Web Bluetooth page, or desktop tool | [README](../README.md#radios-and-the-cli) | Decide | 2 |
| A7 | Wi-Fi provisioning and TLS server authentication in the modem (pinned CA or key) | [README](../README.md#radios-and-the-cli) | Specification | 2 |
| A8 | Modem interface: command set, framing over its UART, and how its firmware updates are forwarded | [hw.md](hw.md#loader-core-domain) | Part selection; specification | 2 |
| A9 | Whether the product carries a radio modem at all, and which module | [README](../README.md#radios-and-the-cli) | Integrator's decision | 1 |
| **Test** | | | | |
| T1 | Fault-injection and side-channel lab: in house or contracted | [test.md](test.md#5-fault-injection) | Decide | 3 |
| T2 | Independent penetration test supplier | [fda.md](fda.md#6-gaps-for-a-submission) | Decide | 3 |
| **ICS55** | | | | |
| I1 | Whether the ICS55 SRAM is usable as a PUF for the ASIC's pairing key | [ics55.md](ics55.md#where-the-key-comes-from) | Test chip | 3 |
| I2 | Whether OTP or eFlash IP becomes available to open designs on this process | [ics55.md](ics55.md#open-questions) | Watch the PDK | 3 |
| I3 | Pin count and package, once the CODEC, LCD, card, sensor and modem interfaces are fixed | [ics55.md](ics55.md) | Board design | 3 |

Closed:
- **From the C5 architecture:** every C5 question (C1 to C14): there is no microcontroller. The link protocol and its message set (A8 in that architecture) are replaced by the mailbox (H2).
- **FPGA:** a PUF built in fabric (set aside: the FPGA's pairing keys are constants in its encrypted bitstream, and the ASIC uses a hardened PUF behind the same interface); Pango's answers on DPA coverage
  (configuration and the hard AES block), JTAG (permanently disabled when locked) and command-line PDS; the Pango Logos PGL25G (no bitstream encryption; not usable).
- **Secure element:** the earlier questions on whether to use one (yes), on the MAC-oracle risk (ReqRandom on slot 0), and on how to protect host sessions (session key from the secure element's KDF).
- **Other:** D1 (developer signing: a per-device developer key, no signing service), E1 (server path: the modem when enabled, otherwise the host), E2 (pairing keys derived in the HSM on the FPGA;
  exported once from the PUF on the ASIC), the watermark (removed), Q6 (safety alarms need no path independent of the application beyond the overlay), S1 (sensor frames use AES-256-GCM).

## Decisions taken

### By you

- **Chipset: an FPGA with an authenticated bitstream, one QSPI flash, and an ATECC608B.** No external microcontroller. The FPGA models the ASIC; family specifics live in `fpga/<family>/`.
- **The application runs on the FPGA,** in LiteForth, executing in place from the flash.
- **FPGA family:** the Pango Logos2 PG2L50H-6IFBG484 is the target; the ECP5 LFE5U-25F is the fallback for a limited number of units.
- **Private keys travel in the bitstream rather than coming from a PUF in fabric.** The ASIC implements a hardened PUF with characterization hardware behind the same interface.
- Recordings encrypted in the FPGA with segment keys erased at segment end, so nothing on the device can read them back.
- Four channels from two NAU88C22 CODECs; LCD and speaker inside a tamper-evident enclosure.
- No watermark; replay or substitution on I2S is left to the tamper-evident seal (R40).
- The temperature sensor is replaceable and must pair without a network.
- Enrollment in the manufacturer's database is required for updates, and the ecosystem flags unknown identities.
- The application owner enables or disables each radio through the signed application package.

### By default (change any of these)

- **Two LiteForth cores:** a loader core that owns every key path, and an application core that reaches it only through the mailbox.
- **The boot ROM is in the bitstream** and mirrors the ASIC's mask ROM; the loader and the application are in flash under per-line AES-256-GCM.
- **Keys live in the secure element**, released only to the holder of the pairing key, into hardware key registers; the bitstream carries only the pairing keys.
- **Bitstream rollback by the pairing-key ratchet;** loader and application rollback by the two counters. Equal versions are accepted so a damaged slot can be repaired.
- **Attestation two ways:** a MAC under a symmetric identity key for the server (quantum-safe), an ECDSA P-256 signature under a certified key for hosts.
- **The host authenticates to the secure element** (CheckMac), which releases the data key and derives the session key.
- **AES-256-GCM in the hard AES block** for lines, recordings, sessions and records; an AES-256-CMAC KDF; AES-CCM instead if the block cannot compute GHASH (F4). A ring-oscillator TRNG mixed with the secure element's.
- **LMS on every package,** one signature per release over a manifest; ML-DSA certificates and ML-KEM pairing for the sensor; ML-KEM segment-key encapsulation to the host.
- **Developer builds as applications** with a per-device developer key and an epoch from counter 1; offline, no signing service.
- **Radios, if fitted, in an untrusted modem** outside the trust boundary, held in reset by the radio policy; **UART status is read-only.**
- **Per-device platform packages** built by the bitstream build service from each device's reported key version.
