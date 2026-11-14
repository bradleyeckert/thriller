# Open Questions

Every open question in one place. Earlier architectures are kept in git history (commits `cecf901`, `8c54b84` and `eb63f10`); questions from them that still apply are carried over here.

**Priority:**
- **1:** blocks something irreversible (eFuse burning, TPM provisioning, enrollment) or the board design.
- **2:** needed before implementation of that part.
- **3:** needed before a submission.

## Matrix

| ID | Question | Where | How to close | Priority |
|---|---|---|---|:-:|
| **FPGA** | | | | |
| F1 | **Per-device bitstreams on the Logos2, the plan now that F5 is closed.** Key changes do not invalidate PnR and `gen_bit_stream` reruns in about a minute, so per-device encryption is cheap. To settle first: **whether a DRM INIT change forces re-synthesis** (if it does, the pairing keys need another per-device carrier, or per-device PnR); then the `.nky` format (HSM-derived keys in, or escrow PDS-generated ones), keeping the RSA signing key fixed as a named file, and scripting the `.pds` key path | [logos2](../fpga/logos2/README.md#per-device-keys-what-the-tcl-guide-says) | Try in PDS; Pango support | 1 |
| F2 | Confirm on a fused sample that a plaintext bitstream, and one encrypted under another key, are refused; record which enable bits (locked by DECLOCK, AUTLOCK, KEYENLOCK) the `.nky` sets. The configuration guide says only the corresponding encrypted bitstream loads after keying, with one ambiguous sentence about eFuse keys | [logos2](../fpga/logos2/README.md#f2-does-the-efuse-key-force-encryption) | Bench, during station bring-up; Pango support in parallel | 1 |
| F3 | Multi-boot on the PG2L50H: stream format and generation are known (`cfg_gen_multi_file`, 8 KB headers, sector-aligned starts, watchdog fallback, status bit 22). Open: whether the golden image is fixed at the base address or the boot address can be redirected by the fabric or the loader; master SPI mode pins | [logos2](../fpga/logos2/README.md#flash-and-multi-boot), [flash.md](flash.md#regions) | Pango documentation; bench | 1 |
| F4 | The masked Ascon core: masking order (first-order TI as the baseline), round unrolling, mask-randomness consumption and the DRBG-seeded PRNG rate behind it, sharing among three users, and TVLA results. Also: HMAC_DRBG as a hardware sequencer (preferred: its state never enters software; about 0.3K LUTs) or as loader firmware | [hw.md](hw.md#the-ascon-core) | RTL design; TVLA on hardware (`doc/test.md`) | 2 |
| F5 | Wrapped pairing keys need a vendor engine the fabric can drive under the eFuse or a PUF-protected key. **Closed for the Logos2** (no such engine; its DPA protection is authenticate-before-decrypt); open as the natural route on PolarFire. Reopen only if Pango shows otherwise | [fpga.md](fpga.md#wrapped-pairing-keys-the-alternative-to-per-device-bitstreams), [polarfire](../fpga/polarfire/README.md) | Pango support, low priority | 3 |
| F6 | XIP line and cache sizes, loader, supervisor and application slot sizes. The tag-length part is closed: SP 800-232's floor is 32 bits with a risk analysis asked only below 64, so 64-bit tags stand | [xip.md](xip.md#caches) | Measure on real LiteForth code | 2 |
| F7 | Ring-oscillator TRNG design and health-test thresholds on the FPGA | [fpga.md](fpga.md#trng) | Characterize on hardware | 2 |
| F8 | The LCD overlay band for developer mode and alarms that the application cannot draw over | [hw.md](hw.md#application-core-domain) | RTL design | 3 |
| F9 | PG2L50H bitstream size, for the flash's bitstream slots | [flash.md](flash.md#regions) | Build | 2 |
| F10 | Ti60 fallback: headless Efinity flow, active SPI multi-image layout, readback and key protection, R5 assessment; the items in its folder | [ti60](../fpga/ti60/README.md) | Only if the fallback is used | 3 |
| F11 | PolarFire and CrossLink-NX as alternatives: the open items in their folders, and the country-of-origin requirements of the target markets | [fpga/](../fpga/README.md) | Vendor documentation; business decision | 3 |
| F12 | Module partition stability in PDS: no partition flow, but the module can be isolated as one hierarchy node, held in a locked region with fixed pins, and its placed-and-routed netlist locked by script; remaining: write the lock-and-compare Tcl, prove it on two builds with a supervisor-only change, and settle the evidence a laboratory accepts (a netlist digest, since encrypted per-device bitstreams are never byte-comparable) | [logos2](../fpga/logos2/README.md#keeping-the-modules-partition-stable-f12) | PDS Tcl; trial builds; laboratory (E12) | 2 |
| **Hardware** | | | | |
| H1 | AXI4-Lite latency: whether the decoder and slaves answer in the cycles LiteForth's memory state machine expects, or whether ROM and SRAM need a tightly coupled path | [hw.md](hw.md#bus-choice) | RTL and simulation | 2 |
| H2 | Mailbox message set, formats and message RAM size: drafted in `doc/api.md`; folded into H9 | [api.md](api.md) | See H9 | 2 |
| H3 | Port numbering agreed with LiteForth's `iomap.h` before any RTL fixes them | [hw.md](hw.md#modules) | Agree | 2 |
| H4 | Side-channel resistance of the SHA-256 core, which carries the pairing key and runs the KDF; first-order masking as the baseline, confirmed by TVLA | [arch.md](arch.md#algorithm-bill-of-materials) | TVLA on hardware (`doc/test.md`) | 2 |
| H5 | Speed of LMS verification, ML-KEM-768 encapsulation and ML-DSA-44 verification as Forth on the loader core with the SHA-256 core | [arch.md](arch.md#algorithm-bill-of-materials) | Build and measure in `vm.c`, then on hardware | 2 |
| H6 | Whether the segment key's wrap for ML-KEM encapsulation moves from masked Forth into hardware | [hw.md](hw.md#two-output-modes) | Decide after H5 | 3 |
| H7 | Flash part, its behavior on power loss during erase and program, and whether 32 MB is right | [flash.md](flash.md#assumptions) | Part selection | 2 |
| H8 | The supervisor as a third core, or as a manufacturer-supplied layer inside the application image on the application core (saves a core, a cache and an image, at the cost of mixing manufacturer and application-owner code and losing the separate update path); matters most if the Ti60 fallback is used | [hw.md](hw.md#principles) | Decide after the first synthesis fit on the PG2L50H | 2 |
| H9 | The module's service API is drafted in `doc/api.md` (mailbox and session layers, status block, events, parameters as data); review it against the reference model as it is written, settle the handshake byte layouts (E13), and freeze | [api.md](api.md) | Reference model (`doc/test.md`), then freeze before the loader is coded | 1 |
| H10 | The ML-KEM shared secret is computed by loader Forth (encapsulation for segment keys and sensor pairing) before it reaches the derive path: the one secret that passes through software. Decide whether to move the final hash of ML-KEM's K into the SHA-256 core so Forth only handles the ciphertext, or accept and document it | [hw.md](hw.md#key-paths) | Decide with the loader's ML-KEM implementation | 2 |
| **TPM** | | | | |
| E5 | Confirm the NV layout, policies and sessions on real parts before provisioning: the Name-binding of the pairing and host indices, the NV_ChangeAuth policies the ratchet and host enrollment depend on, the two-PolicySecret data-key policy, bound sessions with XOR parameter encryption, `POLICY_DELETE` with the PolicyOR station branch (and the delete-and-recreate attack demonstrated on the simulator against an index without it), the NV budget and persistent-object limits | [tpm.md](tpm.md#decisions-to-freeze-before-locking) | The TPM reference simulator, then an ST33KTPM2X evaluation board with tpm2-tools | 1 |
| E6 | The certificate moved: #4737 (which listed firmware 9.257) is historical, replaced by #5570 (initial validation 2026-11-09, sunset 2029-07-24), whose hardware and firmware list is in its Security Policy, not on the certificate page. Confirm DKG9's firmware 9.257 is on #5570 before ordering; DKJ1 (9.512) and CKE3 (9.256) likewise before any substitution; track the certificate's status over the product's life | [tpm.md](tpm.md#part) | #5570 Security Policy; ST | 1 |
| E7 | Freshness index write endurance against the session rate | [tpm.md](tpm.md#user-data-freshness) | ST datasheet NV endurance figure and the expected session rate | 2 |
| E12 | Boundary B with a laboratory: a multi-chip embedded module made of a sub-chip portion (IG 2.3.B, loader domain) on a die shared with excluded logic, plus the TPM (an embedded validated module, #5570) and the flash; non-module firmware (supervisor, application) stored on the module's flash as excluded components; the mailboxes and XIP ports as the declared interfaces; the host data secret's entry inside an Ascon-AEAD128 session frame under a KDF-derived key as approved key entry (or ML-KEM under IG D.S instead); and what the TPM's Security Policy requires of how it is operated. Context: the 19 August 2026 IG D.G revision recommends against the AES-plus-HMAC combination method, which closed the earlier B′ (loader domain alone) | [fips.md](fips.md#module-boundary) | Laboratory consultation | 1 |
| E13 | Host-relay protocol details: the exact byte layout the host needs to compute the `TPM2_PolicySecret` command HMAC, its timeout against the TPM session's lifetime, and the host-side library | [tpm.md](tpm.md#host-authentication) | Reference model, then `vm.c` | 2 |
| E14 | TPM boot-time budget: `TPM2_Startup`, self-test, the pairing session, counter read, blob load and unseal on the ST33KTPM2X, against the boot-time target | [tpm.md](tpm.md#commands-the-loader-domain-uses) | Measure on the evaluation board | 2 |
| E8 | Sourcing: the ST33KTPM2X32DKG9 is a high-volume part (Mouser: about 31,000 in stock, 27,000 more due December 2026) but LCSC does not carry it, so prototypes take it as a consigned part at JLCPCB; confirm the consignment route before the board order | [tpm.md](tpm.md#part) | JLCPCB consignment | 2 |
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
| A5 | CLI command set per session type, and attempt limits | [README](../README.md#network-and-the-cli) | Specification | 2 |
| A6 | Ethernet PHY (LAN8742A or LAN8720A), magnetics isolation grade, and whether to power the device over PoE | [README](../README.md#network-and-the-cli) | Board design | 2 |
| A7 | Addressing: DHCP client in loader Forth with static fallback, how the server or proxy address is provisioned, and whether ICMP echo stays enabled | [hw.md](hw.md#ethernet-transport) | Specification | 2 |
| A8 | The session protocol's ack-and-window layer for updates and uploads over UDP, keepalive interval for NAT, and maximum datagram size | [README](../README.md#network-and-the-cli) | Specification | 2 |
| A9 | Edge proxy: the UDP-to-TLS relay for sites that only allow port 443, as software or an appliance, and how a device finds it | [README](../README.md#network-and-the-cli) | Specification; check target sites' network policies | 2 |
| **Test** | | | | |
| A10 | Real-time clock: the YSN8130E is chosen; /INT is open-drain and survives a VDD cycle (block diagram); backup is two SR44 cells with charging disabled. Remaining: backup life at 0.9 µA plus the /INT pull-up's draw while asserted, the I2C address, and whether it is pin- and register-compatible with the Epson RX8130CE as a second source; then the regulator-enable and power-hold wiring on the FPGA board, the RST_N wiring on the ASIC, and which rails stay up in deep sleep | [hw.md](hw.md#real-time-clock) | Part selection | 2 |
| A11 | FIPS 140-3 (long-term target, `doc/fips.md`): confirm CAVP coverage for Ascon (SP 800-232); confirm SP 800-232's minimum tag length for the 64-bit XIP tags (F6); choose Level 2 or 3; pick the laboratory and the validation timeline | [fips.md](fips.md) | Check NIST's ACVP coverage; business decision | 2 |
| T1 | Fault-injection and side-channel lab: in house or contracted | [test.md](test.md#5-fault-injection) | Decide | 3 |
| T2 | Independent penetration test supplier | [fda.md](fda.md#6-gaps-for-a-submission) | Decide | 3 |
| **ICS55** | | | | |
| I1 | Whether the ICS55 SRAM is usable as a PUF for the ASIC's pairing key | [ics55.md](ics55.md#where-the-key-comes-from) | Test chip | 3 |
| I2 | Whether OTP or eFlash IP becomes available to open designs on this process | [ics55.md](ics55.md#open-questions) | Watch the PDK | 3 |
| I3 | Pin count and package, once the CODEC, LCD, card, PSRAM, RTC, sensor and RMII interfaces are fixed | [ics55.md](ics55.md) | Board design | 3 |

Closed:
- **From the C5 architecture:** every C5 question (C1 to C14): there is no microcontroller. The link protocol and its message set (A8 in that architecture) are replaced by the mailbox (H2).
- **FPGA:** a PUF built in fabric (set aside: the FPGA's pairing keys are constants in its encrypted bitstream, and the ASIC uses a hardened PUF behind the same interface); Pango's answers on DPA coverage
  (authenticate-before-decrypt only; no hardened engine for the fabric), JTAG (permanently disabled when locked) and command-line PDS; the Pango Logos PGL25G (no bitstream encryption; not usable).
- **Secure element:** the earlier questions on whether to use one (yes), on the MAC-oracle risk and on how to protect host sessions, all of which belonged to the ATECC608C; E9 (a validated secure element with approved key wrapping) closed by the move to the ST33KTPM2X TPM, and E10 (per-host keys for Level 3) closed by its per-host indices (`doc/tpm.md`).
- **Other:** D1 (developer signing: a per-device developer key, no signing service), E1 (server path: Ethernet when enabled, otherwise the host), E2 (pairing keys derived in the HSM on the FPGA;
  exported once from the PUF on the ASIC), the watermark (removed), Q6 (safety alarms need no path independent of the application beyond the overlay), S1 (sensor frames use Ascon-AEAD128).

## Decisions taken

### By you

- **Chipset: an FPGA with an authenticated bitstream, one QSPI flash, and an ST33KTPM2X TPM** (replacing the ATECC608C when FIPS 140-3 became the target). No external microcontroller. The FPGA models the ASIC; family specifics live in `fpga/<family>/`.
- **The application runs on the FPGA,** in LiteForth, executing in place from the flash.
- **FPGA family:** the Pango Logos2 PG2L50H-6IFBG484 is the target; the Efinix Ti60 is the fallback. The ECP5 and the Gowin GW5A were dropped for lacking bitstream authentication.
- **Private keys travel in the bitstream rather than coming from a PUF in fabric.** The ASIC implements a hardened PUF with characterization hardware behind the same interface.
- Recordings encrypted in the FPGA with segment keys erased at segment end, so nothing on the device can read them back.
- Four channels from two NAU88C22 CODECs; LCD and speaker inside a tamper-evident enclosure.
- No watermark; replay or substitution on I2S is left to the tamper-evident seal (R40).
- The temperature sensor is replaceable and must pair without a network.
- Enrollment in the manufacturer's database is required for updates, and the ecosystem flags unknown identities.
- **No radios.** One wired Ethernet port, with the network side implemented as a UDP-only transport in hardware; a local edge proxy meets any port-443 requirement. The application owner enables or disables the port through the signed application package.

### By default (change any of these)

- **Three LiteForth cores:** a loader core that owns every key path and is the FIPS module, a supervisor core for the manufacturer's transports, scheduling and CLI outside the module, and an application core; both reach the loader only through mailboxes (H8 for the two-core variant).
- **The boot ROM is in the bitstream** and mirrors the ASIC's mask ROM; the loader, the supervisor and the application are in flash under per-line Ascon-AEAD128.
- **Keys live in the TPM** as sealed objects, released only under policies that name the pairing key, into hardware key registers; the bitstream carries only the pairing keys.
- **Bitstream rollback by the pairing-key ratchet;** loader and application rollback by the two counters. Equal versions are accepted so a damaged slot can be repaired.
- **Attestation two ways:** a MAC under a symmetric identity key for the server (quantum-safe), a TPM quote under a certified attestation key for hosts.
- **The host authenticates to the TPM** through a relayed HMAC session, and the TPM unseals the data key and the host session secret only then.
- **Ascon-AEAD128 in a masked core of our own** for lines, recordings, sessions and records; an HMAC-SHA256 KDF in the SHA-256 core; no vendor cipher block and no AES anywhere in the fabric (F4); TPM session parameters are protected by the TPM's XOR mode from a KDFa stream, which is enough inside the module boundary. A ring-oscillator TRNG with the TPM's as additional input, also seeding the mask PRNG.
- **LMS on every package,** one signature per release over a manifest; ML-DSA certificates and ML-KEM pairing for the sensor; ML-KEM segment-key encapsulation to the host.
- **Developer builds as applications** with a per-device developer key and an epoch from counter 1; offline, no signing service.
- **The network is a second transport for the session protocol,** with no stack on any core; the PHY is held in reset by the network policy; **UART status is read-only.**
- **Per-device platform packages** built by the bitstream build service from each device's reported key version.
- **FIPS 140-3 module boundary B:** the module is the loader domain (a sub-chip portion, IG 2.3.B) plus the TPM (embedded validated module, #5570) and the flash, with the supervisor and application outside as excluded components; the TPM bus and the flash are internal, so no approved key transport is needed on them. The earlier B′ (loader domain alone, keys crossing by AES-CFB plus HMAC) was withdrawn when the August 2026 IG D.G revision recommended against that method. Boundary A stays available with the same hardware if a laboratory objects (E12).
- **Minimize CMVP filings:** the module is a frozen crypto kernel with a fixed service API; everything that changes from release to release lives in the supervisor and application images, outside the module; bitstream releases are rare and preserve the module's partition (`doc/fips.md`, Designing for few filings).
- **Every TPM NV index is undeletable** (`TPMA_NV_POLICY_DELETE`, with a deletion branch only the HSM-held owner authorization satisfies): without it, anyone holding the empty platform authorization after a TPM reset could delete and recreate the pairing index with a known authorization value and unseal every key (R36).
- **Recovery repairs bitstreams**: a superseded fallback bitstream can install a bitstream repair package without a TPM exchange, so a failed current slot is repairable (R44, `doc/flash.md`).
