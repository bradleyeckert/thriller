# Architecture

This document covers the trust boundary, the threat model, the risk assessment and the algorithm bill of materials.
Chip configuration is in `doc/c5.md`, the sensor in `doc/sensor.md`, and enrollment and updates in `doc/enrollment.md`.

## Trust boundary

| Component | Trusted for | Notes |
|---|---|---|
| C5 boot ROM | Verifying the bootloader | Fixed silicon. Bugs cannot be patched (R25) |
| Second-stage bootloader | Verifying the TEE and application, anti-rollback, slot fallback | Signed; updatable through the C5's recovery bootloader mechanism (`doc/c5.md`) |
| **TEE** (ESP-TEE, machine mode) | Every key, every cryptographic protocol, update installation, secure storage, the event log | The only code that uses the device root key and the TEE storage key |
| Application (user mode) | Device function, within the limits the TEE enforces | Can be a developer build. Never sees a key; a bug in it must not expose one (R8) |
| External flash, PSRAM | Nothing | Encrypted by the C5; integrity comes from secure boot and the TEE's own checks |
| MicroSD card | Nothing | Everything on it is encrypted and authenticated by the TEE |
| ECP5 | Nothing | Holds no secrets. Its identity check catches mistakes, not attacks (`doc/fpga.md`) |
| Sensor link, UART, BLE and Wi-Fi | Nothing | Every session authenticated end to end by the TEE. The Wi-Fi and BLE stacks run in the application, so an exploit in them reaches the application but no key |
| Sensor | Its own readings, once its certificate and pairing check out | Replaceable; one broken sensor exposes only itself |
| Host | Its user's data | Holds the host key and the host data secret |
| HSMs, enrollment database, update server | Keys and records for the whole fleet | The crown jewels (R19) |

## Two signature schemes

The C5's ROM verifies RSA-3072 (secure boot v2) and nothing can change that. ECDSA is also offered, but Espressif's documentation says it does not work for
certain input vectors on the C5 and recommends RSA. So:

- **RSA-3072** signs every image, because the ROM and bootloader require it. The manufacturer's HSM holds the key, and the eFuses hold digests
  of a main and a backup key, either of which can be revoked.
- **LMS** (RFC 8554, NIST SP 800-208) signs every update package. The TEE checks it before it decrypts or installs anything.

A quantum-capable attacker could forge an RSA signature, but would still need to write the forged image into the device's flash, which takes physical access:
the update path accepts only LMS-signed packages. That residual risk is accepted (R24).
The sensor certificates use ML-DSA (FIPS 204) and the pairing uses ML-KEM (FIPS 203), so the sensor is quantum-safe too (`doc/sensor.md`).

## Threat model

### Assets

| Asset | Goal |
|---|---|
| User data on the MicroSD card | Confidentiality and integrity. **The primary asset.** |
| Temperature readings | Integrity and freshness: a reading the device acts on is genuine, from the paired sensor, and recent |
| Application and platform images | Only genuine signed versions run, and no older vulnerable version. Packages are encrypted so they show no plaintext, but code secrecy is not a goal of the base model (see Code Secrecy Profile) |
| Device identity | A unit cannot be cloned or impersonated, and an unknown unit is noticed |
| Sensor identity | A sensor cannot be cloned or counterfeited without being noticed |
| Signing keys and master keys | Never exposed; they stay in HSMs |
| The rest of the fleet | Compromising one unit or one sensor exposes nothing about another |

### Attackers

| Attacker | Capability |
|---|---|
| Remote | Talks to the device over the host link, or sends it a file on the MicroSD card |
| Link attacker | Can watch, inject, delay or cut traffic on the sensor cable or the UART |
| Radio attacker | Within BLE range, or on the same network as the device's Wi-Fi: can scan, connect, send malformed packets, and run a fake access point or server |
| Board prober | Opens the box: probes or interposes on the flash, SPI and sensor lines, reflashes the external flash, replaces parts |
| Thief | Has the device and unlimited time, but the legitimate host never connects to it again |
| Evil maid | Has the device for a while, then returns it to the legitimate user, who connects their host |
| Lab attacker | Power analysis and fault injection on one C5, as in Espressif advisory AR2023-007 |
| Insider | Has access to the factory, the HSMs or the enrollment database |
| Quantum-capable | Can break RSA and ECDSA, but not AES, SHA-256, HMAC, LMS, ML-KEM or ML-DSA |

### Outcomes

| Asset | Remote | Link attacker | Board prober | Thief | Evil maid | Lab attacker | Quantum-capable |
|---|---|---|---|---|---|---|---|
| User data | Safe | Safe (sessions encrypted and authenticated) | Safe (card and flash encrypted) | **Safe**: the data key needs the host's secret, which the device never stores | Safe unless the attacker also planted code that runs during the user's next session (needs a lab attack or a signing key) | Safe for a thief; the evil-maid case as left | Safe |
| Temperature readings | Safe | Safe from forgery and replay; can delay or cut them, which raises the alarm | Same as link attacker | n/a | Can swap the sensor for one the attacker controls only if it is a genuine paired sensor | Breaking one sensor lets it forge its own readings | Safe |
| Images | Safe | Safe | Can restore an old flash image; versions blocked by eFuse stay blocked | Same as board prober | Same as board prober | Can run modified code on that unit | Could forge RSA, but still needs physical flash access |
| Device identity | Safe | Safe | Safe | Can use it while holding the unit | Same | Can extract that unit's keys | Safe (symmetric) |
| Other units and sensors | Safe | Safe | Safe | Safe | Safe | Safe (per-device and per-sensor keys) | Safe |

A **radio attacker** has the link attacker's reach over CLI and server sessions, which are authenticated end to end, plus one thing more:
a bug in the Wi-Fi or BLE stack can give them code execution in the application (R23, R28). That reaches the device's function but not its keys, user data or images.
The application must therefore keep the sensor safety path independent of its network code.

### Not protected

- **Denial of service.** Anyone who can reach the board can erase the flash or cut the sensor cable. Cutting the cable or blocking readings
  is detected and puts the device in its safe state (`doc/sensor.md`), but it is not prevented.
- **Restoring an old flash image** with a programmer, for versions that were not security releases. Only security releases advance the anti-rollback
  eFuses, which have 9 bits in total (R4).
- **The C5 against a lab attacker.** Espressif lists no fix for AR2023-007 on the C3 and C6; the C5 adds glitch detectors and AES dummy rounds,
  but these raise the cost rather than remove the attack. Per-device keys keep it to one unit (R5).
- **Secrecy of the application code,** unless the Code Secrecy Profile is enabled.

## Risk Assessment

Each row is one attack, so each can be rated, owned and tracked. Ratings are for the base model.

**Impact:**
- **Critical:** user data exposed or forged, a forged temperature reading acted on, arbitrary code execution, or any fleet-wide compromise.
- **High:** a single unit compromised or rolled back to a vulnerable version.
- **Medium:** loss of service, a bricked unit, or a weakened but not broken protection.
- **Low:** exposure of information the model does not treat as secret.

**Likelihood:**
- **High:** needs only common tools (flash programmer, logic analyzer, JTAG pod) and public knowledge.
- **Medium:** needs physical access plus specialist skill, or sustained effort against one unit.
- **Low:** needs a well-equipped lab, an insider, or capabilities that do not yet exist.

FDA asks for an exploitability-based rating rather than likelihood; the table is to be re-scored in that form before a submission (`doc/fda.md`, gap 8).

| # | Asset / Component | Threat Actor | Attack Vector / Threat Description | Vulnerability Exploited | Impact | Likelihood | Mitigation / Countermeasure |
|---|---|---|---|---|---|---|---|
| R1 | MicroSD card: user data | Thief with a card reader | Remove the card and read or alter user data | The card is removable | Critical | High | AES-256-GCM under a key derived from both the device's data key and the host's data secret; the device never stores the secret |
| R2 | External flash: images and TEE storage | Hobbyist with a flash programmer | Dump the flash and read code or keys | The HR8 has no flash in the package | Medium | High | XTS-AES flash encryption with a per-device key generated on chip; keys in TEE storage are also encrypted under the TEE storage key |
| R3 | Update path | Remote attacker | Send a forged or modified package | Packages arrive from anyone, on the card or the host link | Critical | Medium | LMS signature checked by the TEE before decryption; the RSA image signature checked again by the bootloader at every boot |
| R4 | Version state | Board prober | Write an older, vulnerable image back into flash with a programmer | Flash has no freshness | High | Medium | The TEE refuses older packages on the update path. Security releases advance the anti-rollback eFuses (6 steps for the application, 3 for the TEE, 4 for the bootloader), which the bootloader enforces even after a flash restore. Restoring a non-security release is accepted |
| R5 | C5 secrets | Lab attacker | Power analysis on flash encryption, and voltage or EM glitches on secure boot (AR2023-007) | Published attacks with no silicon fix on the C3 and C6 | High | Low | C5 glitch detectors and AES pseudo-rounds enabled; per-device keys only, so one break exposes one unit; host data secret not on the device; tamper-evident enclosure |
| R6 | External flash at run time | Board prober with an interposer | Change flash contents after secure boot has checked them | XTS-AES has no per-read integrity check | High | Low | Edits produce unpredictable 16-byte blocks, not chosen code; TEE code and data are checked or authenticated by the TEE before use; a C5 with flash in the package would remove the probe point (open question) |
| R7 | Debug and download ports | Hobbyist | Attach JTAG or the ROM download mode to read memory or load code | Ports exist on every C5 | Critical | High | eFuses disable JTAG (pad and USB) and direct boot; download mode is secure download mode or permanently disabled (`doc/c5.md`) |
| R8 | Keys in the C5 | Malicious or buggy application, including a developer build | Read TEE memory or use key peripherals directly | Application and TEE share one core | Critical | Medium | ESP-TEE: the application runs in user mode; memory, the HMAC peripheral, eFuse and flash regions belong to the TEE by permission (APM/PMP); keys never leave the TEE |
| R9 | Host and CLI sessions | Link or radio attacker | Impersonate the host, or replay or alter session traffic on the UART or BLE | Both transports are open | Critical | Medium | Mutual authentication under the host key with nonces from both ends; every frame encrypted and authenticated with a counter |
| R10 | User data freshness | Thief or evil maid | Put an old copy of the card back | Every old record still authenticates | High | High | The device gives the host an authenticated digest of the data state at the end of each session; the host presents it at the next one, and a mismatch is reported |
| R11 | Temperature readings | Link attacker | Forge readings or commands on the sensor cable | The cable is outside the box | Critical | High | Every frame, in both directions, carries a MAC under a session key derived from the pairing key and fresh nonces from both ends |
| R12 | Temperature readings | Link attacker | Replay old readings, or delay them | MACs do not prove freshness or timeliness | Critical | Medium | Per-session nonces and frame counters; the TEE enforces a maximum reading age; late or missing readings put the device in its safe state |
| R13 | Temperature readings | Link attacker | Cut or jam the sensor link | Availability cannot be enforced | High | High | Detected within the maximum reading age; safe state and alarm. Not preventable |
| R14 | Sensor identity | Counterfeiter | Make sensors that pair as genuine | Sensors pair offline | Critical | Low | ML-DSA certificate from the sensor manufacturer's HSM, checked by the TEE; the sensor must prove it holds the certified ML-KEM key |
| R15 | Sensor identity | Lab attacker | Extract one sensor's key and clone it | A sensor is a small microcontroller | High | Low | Each sensor has its own key; the enrollment server sees the same serial paired to several devices and adds it to the denylist delivered with updates and online |
| R16 | Device identity | Counterfeiter or cloner | Build or clone devices that use the service | Devices may be offline for long periods | High | Low | Device root key in a read-protected eFuse; the server authenticates every device it sees and flags unknown identities; a device that was never enrolled has no distribution key, so it cannot install updates |
| R17 | ECP5 | Board prober | Replace or reprogram the FPGA, or interpose on its SPI link | The FPGA is a peripheral on the board | Medium | Medium | The FPGA holds no secrets and the sensor does not go through it; the identity register and self-test catch wrong or corrupted bitstreams. The FPGA's own function is trusted only as far as the application checks its results |
| R18 | Update packages in transit | Hobbyist | Hex dump a package | Packages travel over open channels | Low | High | AES-256-GCM under the fleet-wide distribution key (obfuscation). Code Secrecy Profile for real secrecy |
| R19 | HSMs, enrollment database, update server | Insider or intruder | Use master keys or records to derive any device's keys, unlock any host's data secret, or issue rogue sensors | Per-device keys are derived from master keys | Critical | Low | HSMs with dual control and audit; the database holds no secret key material; signing and derivation only inside HSMs; separate masters per key type |
| R20 | Host key | Thief of the host | Use a stolen host to open sessions | The host holds the keys | Critical | Medium | Host-side protection (user authentication, encrypted key storage) is the host's job; a compromised host means retiring the device, since its keys cannot be changed |
| R21 | Developer builds | Developer | Run a developer build on someone else's device, or read production user data | Developer builds are signed through the release signing service | High | Medium | Each developer build names one device and one developer epoch; the TEE refuses it anywhere else; developer builds use separate data keys (`doc/roles.md`) |
| R22 | Developer epoch | Developer with a programmer | Restore an old flash image to revive an expired developer build | The epoch record lives in TEE storage in flash | Medium | Medium | Accepted: it harms only the developer's own device, and production data keys never reach developer builds |
| R23 | Wi-Fi stack | Radio attacker on the network | Exploit a bug in the Wi-Fi, TCP/IP or TLS stack to run code in the application | Large network stacks | Critical | Medium | Enabled only if the application owner enables it; outbound connections only, no listening ports; stacks run in user mode, so keys stay in the TEE; stacks kept current by OTA; the sensor safety path does not depend on the application's network code (to be enforced by the application design) |
| R24 | Boot root | Quantum-capable attacker with flash access | Forge an RSA-3072 image signature | The ROM supports only RSA and ECDSA | High | Low | The update path needs LMS; a forged image still needs physical flash access. Accepted |
| R25 | C5 boot ROM | Researcher | A ROM bug (as in AR2023-007's buffer overflow) | ROM cannot be patched | High | Low | Follow Espressif advisories; per-device keys; eFuse settings chosen against published attacks |
| R26 | Event log | Evil maid or thief | Erase or alter the security event log | The log lives in flash or on the card | Medium | Medium | HMAC-chained entries under a TEE key; the host and the server read it and notice gaps |
| R27 | Signing keys | Insider, or loss | A signing key is lost or leaks | Keys are long-lived | Critical | Low | Main and backup RSA keys in eFuse, each revocable; main and backup LMS keys in the TEE image, replaceable by a TEE update signed with the other key; keys held in separate HSMs |
| R28 | BLE stack and CLI | Radio attacker within range | Exploit a BLE stack bug, or brute-force or abuse the CLI | BLE answers anyone in range; ESP-IDF has had BLE stack CVEs | Critical | Medium | Enabled only by the application owner; advertising only after a user action and for a limited time; one connection; every CLI session authenticated by the TEE under the host or developer key, with attempt limits and logging; stacks in user mode; kept current by OTA |
| R29 | OTA updates and server contact | Radio attacker running a fake access point or server | Offer old or forged packages, or block updates | The network is not trusted | High | Medium | Packages verified by LMS signature and version in the TEE whatever the source; the server proves itself under the device's identity key; TLS for privacy. Blocking updates cannot be prevented; the server reports units that fall behind |
| R30 | UART status | Anyone with a cable | Learn something from the unauthenticated status reports | Status needs no session | Low | High | Status limited to versions, build mode, faults and pairing state; no user data and no keys; everything else needs a session |

## Optional: Code Secrecy Profile

Flash contents are already encrypted under a key unique to each device. The weak point for code secrecy is the fleet-wide distribution key (R18):
breaking one device exposes every package. The profile replaces it with **per-device packages**: the update server wraps each package's content key
to the device's own key, derived from the device root. That needs the server, so offline updates would carry per-device packages too, prepared for
one device. The profile changes nothing else in the design.

## Algorithm bill of materials

| Algorithm | Standard | Runs in | Used for |
|---|---|---|---|
| RSA-3072 PSS | Secure boot v2 | C5 ROM and bootloader (hardware RSA accelerator) | Image signatures |
| XTS-AES-128 | IEEE 1619 | C5 flash and PSRAM encryption hardware | Everything in external flash and PSRAM |
| SHA-256, HMAC-SHA256 | FIPS 180-4, FIPS 198-1 | C5 SHA and HMAC peripherals | Key derivation from eFuse keys, MACs, hash chains |
| HKDF-SHA256 | RFC 5869 | TEE (software over the SHA peripheral) | Session keys, labelled key derivation |
| AES-256-GCM | SP 800-38D | TEE (C5 AES accelerator with pseudo-rounds) | User data, host sessions, update packages |
| LMS (HSS) | RFC 8554, SP 800-208 | TEE (Mbed TLS includes an LMS verifier) | Update package signatures |
| ML-DSA-44 | FIPS 204 | TEE (verify only) | Sensor certificates |
| ML-KEM-768 | FIPS 203 | TEE (encapsulate) and sensor (decapsulate) | Sensor pairing |
| Ascon-AEAD128, or HMAC-SHA256 | SP 800-232, FIPS 198-1 | TEE and sensor | Sensor link frames (choice open) |
| TRNG | | C5 RNG; a TRNG on the sensor | Nonces |

Implementations for ML-KEM and ML-DSA are to be chosen; portable C libraries such as the PQ Code Package's mlkem-native and mldsa-native are candidates.
The FPGA needs none of these.

## Open questions

All open questions are collected in `doc/questions.md`.
