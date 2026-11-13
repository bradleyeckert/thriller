# Architecture

This document covers the trust boundary, the threat model, the risk assessment and the algorithm bill of materials.
The hardware is in `doc/hw.md`, the TPM in `doc/tpm.md`, the flash in `doc/flash.md`, the FPGA in `doc/fpga.md`, recordings in `doc/acquisition.md`,
the sensor in `doc/sensor.md`, and enrollment and updates in `doc/enrollment.md`.

## Trust boundary

| Component | Trusted for | Notes |
|---|---|---|
| FPGA configuration engine | Authenticating and decrypting the bitstream with its eFuse keys; refusing unencrypted or unsigned configurations; falling back to the other bitstream slot | Vendor silicon. On the Logos2, AES-256-GCM and RSA-2048, signature checked before decryption; on the Ti60, AES-256-GCM and RSA-4096. Bugs cannot be patched (R25) |
| Boot ROM | Starting the TPM and pairing with it, checking the loader image, deriving its key, recovery over the UART | Block RAM in the bitstream, so it changes only with a platform update; mask ROM on the ASIC |
| **Loader core domain** | Every key path, every package check, versions, installs, host, sensor and server sessions, segment keys, the event log, the network policy | The only logic connected to the TPM, the key registers and flash writing (`doc/hw.md`) |
| Application core domain | Device function, recordings in plaintext, display | Can be a developer build. Reaches the loader only through the mailbox; has no path to any key (R8, R37) |
| TPM (ST33KTPM2X) | Holding keys, counters and identity; releasing keys only under policies that name the pairing key; verifying the host's HMAC; signing quotes | A FIPS 140-3 validated module (CMVP #4737, physical Level 3), Common Criteria EAL4+ targeted. Its counters are authenticated and authorized; the residual is denial of service by whoever talks to it first after reset (R36) |
| QSPI flash | Nothing | Bitstream encrypted and (where the family can) signed; every loader and application line authenticated on fetch; boot record authenticated under the application key |
| MicroSD card | Nothing | Everything on it is encrypted and authenticated by the loader |
| Sensor link, UART | Nothing | Every session authenticated end to end by the loader |
| **Everything from the RMII pins outward:** PHY, magnetics, cable, site network, edge proxy, Internet | Nothing | The trust boundary is the FPGA's pins. The Ethernet transport inside them is hardware that delivers UDP payloads and nothing else; everything beyond carries only ciphertext and can at most drop, delay or replay, which the session protocol handles |
| Sensor | Its own readings, once its certificate and pairing check out | Replaceable; one broken sensor exposes only itself |
| Host | Its user's data | Holds the host authorization key and the host data secret |
| HSMs, enrollment database, update server, bitstream build service | Keys and records for the whole fleet | The crown jewels (R19, R42) |
| Inside the sealed enclosure | Plaintext on the I2S buses and the LCD bus; the TPM's SPI bus, which carries only ciphertext, HMACs and public data | Protected only by the tamper-evident seal (R36, R38) |

## Signature schemes

- **The vendor's bitstream signature** (RSA-2048 on the Logos2, ECDSA or RSA on other families) is checked by the configuration engine and nothing can change that. It stops a forged
  bitstream from running at all. It is not quantum-safe (R24), and the design never depends on it alone: a bitstream without the current pairing key gets nothing from the TPM.
- **LMS** (RFC 8554, NIST SP 800-208) signs every update package: platform and application. The loader verifies it with its SHA-256 core before it decrypts or installs anything.
  Each release takes one signature over a manifest, a Merkle tree over every package's digest; per-device platform packages carry their inclusion proof.
- **ECDSA P-256** is used in one place: the TPM signs quotes with the device's certified attestation key, for hosts and third parties that expect a certificate chain.
  The server's view of identity is the symmetric identity key, so the quantum-safe path exists for everything that matters to the fleet.
- The sensor certificates use ML-DSA (FIPS 204) and the pairing uses ML-KEM (FIPS 203), so the sensor is quantum-safe too (`doc/sensor.md`).

## Threat model

### Assets

| Asset | Goal |
|---|---|
| Recordings | Confidentiality (health data that can identify a person), integrity, and the time they were made. **The primary asset.** |
| Other user data on the MicroSD card | Confidentiality and integrity |
| Temperature readings | Integrity and freshness: a reading the device acts on is genuine, from the paired sensor, and recent |
| Bitstreams, loader and application images | Only genuine signed versions run, and no older vulnerable version. Packages are encrypted so they show no plaintext, but code secrecy is not a goal of the base model (see Code Secrecy Profile) |
| Device identity | A unit cannot be cloned or impersonated, and an unknown unit is noticed |
| Sensor identity | A sensor cannot be cloned or counterfeited without being noticed |
| Signing keys and master keys | Never exposed; they stay in HSMs |
| The rest of the fleet | Compromising one unit or one sensor exposes nothing about another |

### Attackers

| Attacker | Capability |
|---|---|
| Remote | Talks to the device over the UART or the network, or sends it a file on the MicroSD card |
| Link attacker | Can watch, inject, delay or cut traffic on the sensor cable or the UART |
| Network attacker | On the same LAN, in the edge proxy, or anywhere on the path to the server: can send any frame to the device, flood it, spoof ARP or DHCP, or impersonate the proxy or the server |
| Board prober | Breaks the seal: probes or interposes on the flash, the TPM's SPI bus, I2S and sensor lines; reflashes the flash; tries to reconfigure the FPGA; replaces parts |
| Thief | Has the device and unlimited time, but the legitimate host never connects to it again |
| Evil maid | Has the device for a while, then returns it to the legitimate user, who connects their host |
| Lab attacker | Power analysis and fault injection on one FPGA, or decapsulation of one TPM |
| Insider | Has access to the factory, the HSMs or the enrollment database |
| Quantum-capable | Can break RSA and ECDSA, but not Ascon-AEAD128 at a practical cost (Grover against a 128-bit key), nor SHA-256, HMAC, LMS, ML-KEM or ML-DSA |

### Outcomes

| Asset | Remote | Link attacker | Board prober | Thief | Evil maid | Lab attacker | Quantum-capable |
|---|---|---|---|---|---|---|---|
| Recordings | Safe | Safe (encrypted to the host before leaving the FPGA) | Can read live data on the I2S buses while the device records; past recordings safe; can replay or substitute samples on I2S undetected (R40) | **Safe**: the device cannot decrypt its past recordings | Can watch the next recording live with taps inside the enclosure; seal evidence | Can extract that unit's keys, and so read segments recorded while it holds them, never earlier ones | Safe |
| Other user data | Safe | Safe (sessions encrypted and authenticated) | Safe (card and flash encrypted); can clear the TPM by talking to it before the FPGA does, and brick the unit (R36) | **Safe**: the data key needs the host's secret, which the device never stores, and the TPM releases it only to the host | Safe unless the attacker also planted code that runs during the user's next session (needs a lab attack or a signing key) | Safe for a thief; the evil-maid case as left | Safe |
| Temperature readings | Safe | Safe from forgery and replay; can delay or cut them, which raises the alarm | Same as link attacker | n/a | Can swap the sensor only for a genuine paired sensor | Breaking one sensor lets it forge its own readings | Safe |
| Images | Safe | Safe | Can restore an old flash image; versions behind the counters stay blocked; an old bitstream holds a retired pairing key | Same as board prober | Same as board prober | Can run modified code on that unit | Could forge the vendor bitstream signature, but still needs the device's bitstream key and pairing key |
| Device identity | Safe | Safe | Safe | Can use it while holding the unit | Same | Can extract that unit's TPM keys with a decapsulation attack | Could forge ECDSA attestations; the server's symmetric identity is safe |
| Other units and sensors | Safe | Safe | Safe | Safe | Safe | Safe (per-device and per-sensor keys) | Safe |

A **network attacker** has the link attacker's reach over server and host sessions, which are authenticated end to end, and nothing more: there is no network stack to exploit,
only a hardware transport whose parsers are ARP, IPv4 and UDP headers (R23). A bug there is a hardware bug, found by fuzzing the RTL, and cannot yield code execution. They can still flood the port,
spoof ARP or DHCP to black-hole traffic, or drop frames in a compromised proxy, all of which deny service and nothing else.

### Not protected

- **Denial of service.** Anyone who can reach the board can erase the flash, clear the TPM ahead of the boot ROM, or cut the sensor cable. Cutting the cable or blocking readings
  is detected and puts the device in its safe state (`doc/sensor.md`), but it is not prevented.
- **Restoring an old flash image** of the same release, or of a release whose version equals the counter. Counters only move forward; equal versions are accepted so a damaged slot can be repaired (R4).
- **The FPGA against a lab attacker.** Power analysis of configuration decryption and glitching of the configuration engine depend on the family's countermeasures; per-device keys keep a break to one unit (R5, R33).
- **The TPM's availability** against anyone who drives its reset and talks to it before the boot ROM (R36).
- **Plaintext inside the enclosure.** I2S and the LCD bus carry plaintext; the tamper-evident seal is the only protection (R38). Replayed or substituted samples on I2S are not detected (R40).
- **Secrecy of the application code,** unless the Code Secrecy Profile is enabled.

## Risk Assessment

Each row is one attack, so each can be rated, owned and tracked. Ratings are for the base model on the Logos2; where the Ti60 fallback differs, it is noted.

**Impact:**
- **Critical:** recordings or user data exposed or forged, a forged temperature reading acted on, arbitrary code execution, or any fleet-wide compromise.
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
| R1 | MicroSD card: user data | Thief with a card reader | Remove the card and read or alter user data | The card is removable | Critical | High | Ascon-AEAD128 under a key derived from both the device's data key and the host's data secret; the device never stores the secret; the TPM unseals the data key only after the host's proof to it |
| R2 | QSPI flash: images | Hobbyist with a flash programmer | Dump the flash and read code or keys | The flash is an external part | Medium | High | The bitstream is encrypted under the FPGA's eFuse key; loader and application lines are encrypted and tagged under per-install keys from the application key; the boot record holds no key |
| R3 | Update path | Remote attacker | Send a forged or modified package | Packages arrive from anyone, on the card, the UART or the network | Critical | Medium | LMS signature and manifest inclusion checked by the loader before decryption; version checked against the counter; the ciphertext re-hashed during install must match |
| R4 | Version state | Board prober | Write an older, vulnerable image back into flash with a programmer | Flash has no freshness | High | Medium | Image versions are checked against the TPM's monotonic counters at every boot (loader: counter 0; application: counter 1); an older bitstream holds a retired pairing key (`doc/tpm.md`, Ratchet). Restoring the current release is accepted |
| R5 | FPGA configuration secrets | Lab attacker | Power analysis on bitstream decryption, or glitches on the configuration engine | Hardening varies by family | High | Low | On the Logos2 the signature is checked before decryption, so an attacker cannot feed chosen ciphertexts to the decryptor; the fixed legitimate bitstream still yields repeated traces, so the protection is partial. Glitch detectors where the family has them; per-device bitstream keys, so one break exposes one unit; tamper-evident enclosure. On the Ti60, to be assessed |
| R6 | Flash at run time | Board prober with an interposer or emulator | Modify, move or mix lines of the loader or application during execution | Flash is external | Critical | Medium | Per-line Ascon-AEAD128 with the slot and line address in the nonce and a per-install key, checked on every fetch; a failed tag locks down (`doc/xip.md`) |
| R7 | Debug and recovery ports | Hobbyist | Attach JTAG or use UART recovery to read memory or load code | Ports exist on every FPGA | Critical | High | JTAG permanently disabled at enrollment (Logos2 JTAGLOCK; Ti60 JTAG disable); no CPU debug port in production bitstreams; UART recovery accepts only LMS-signed loader packages and never reads out memory |
| R8 | Keys in the loader domain | Malicious or buggy application, or an exploit in the loader | Read a key from a register, the TPM or SRAM | Two cores share one FPGA | Critical | Medium | Keys move from the TPM and the key source into hardware key registers and never through either core (`doc/hw.md`, Key paths); the application core's buses have no connection to the loader domain except the mailbox |
| R9 | Host and CLI sessions | Link or network attacker | Impersonate the host, or replay or alter session traffic on the UART or the network | Both transports are open | Critical | Medium | The host proves itself to the TPM (the HMAC of one TPM command, over the TPM's nonce and the loader's); the TPM unseals the data key and the host session secret only then; every frame encrypted and authenticated with a counter |
| R10 | User data freshness | Thief or evil maid | Put an old copy of the card back | Every old record still authenticates | High | High | The loader writes an authenticated digest of the data state into the TPM's freshness index at the end of each session that changed data, and compares at the next one (`doc/tpm.md`, User data freshness) |
| R11 | Temperature readings | Link attacker | Forge readings or commands on the sensor cable | The cable is outside the box | Critical | High | Every frame, in both directions, carries a MAC under a session key derived from the pairing key and fresh nonces from both ends |
| R12 | Temperature readings | Link attacker | Replay old readings, or delay them | MACs do not prove freshness or timeliness | Critical | Medium | Per-session nonces and frame counters; the loader times each exchange with its own timer and enforces a maximum reading age; late or missing readings put the device in its safe state |
| R13 | Temperature readings | Link attacker | Cut or jam the sensor link | Availability cannot be enforced | High | High | Detected within the maximum reading age; safe state and alarm. Not preventable |
| R14 | Sensor identity | Counterfeiter | Make sensors that pair as genuine | Sensors pair offline | Critical | Low | ML-DSA certificate from the sensor manufacturer's HSM, checked by the loader; the sensor must prove it holds the certified ML-KEM key |
| R15 | Sensor identity | Lab attacker | Extract one sensor's key and clone it | A sensor is a small microcontroller | High | Low | Each sensor has its own key; the server sees the same serial paired to several devices and adds it to the denylist delivered with updates and online |
| R16 | Device identity | Counterfeiter or cloner | Build or clone devices that use the service | Devices may be offline for long periods | High | Low | Identity keys in the TPM, never readable, the attestation key bound to ST's endorsement key certificate; the server authenticates every device it sees and flags unknown identities; a device never enrolled has no distribution key, so it cannot install updates; a cloned TPM shows up as one identity in two places |
| R17 | FPGA | Board prober | Replace the FPGA, or load a different or older bitstream through JTAG or the configuration pins | The configuration pins are on the board | High | Medium | The FPGA accepts only bitstreams encrypted under its own key and signed by the manufacturer (Logos2 and Ti60: both enforced once authentication is enabled); JTAG permanently disabled on the Logos2; a bitstream without the current pairing key gets nothing from the TPM; an older bitstream of the same device holds a retired pairing key |
| R18 | Update packages in transit | Hobbyist | Hex dump a package | Packages travel over open channels | Low | High | Ascon-AEAD128 under the fleet-wide distribution key (obfuscation). Code Secrecy Profile for real secrecy |
| R19 | HSMs, enrollment database, update server | Insider or intruder | Use master keys or records to derive any device's keys, unlock any host's data secret, or issue rogue sensors | Per-device keys are derived from master keys | Critical | Low | HSMs with dual control and audit; the database holds no secret key material; signing and derivation only inside HSMs; separate masters per key type |
| R20 | Host key | Thief of the host | Use a stolen host to open sessions | The host holds the keys | Critical | Medium | Host-side protection (user authentication, encrypted key storage) is the host's job. A compromised host is cut off by the server: the loader changes that host's TPM index to a new HSM-derived key for the replacement host, or to a random one (`doc/tpm.md`); other hosts and the device itself are unaffected |
| R21 | Developer builds | Developer | Run a developer application on someone else's device, or read production data | Developers install their own builds | High | Medium | Developer packages carry a MAC under one device's developer key for the current epoch; the loader refuses them anywhere else; developer builds get separate data keys and recordings marked as developer recordings (`doc/roles.md`) |
| R22 | Developer epoch | Developer with a programmer | Restore an old flash image to revive an expired developer build | The epoch is counter 1 ÷ 1024 | Medium | Low | Counter 1 is in the TPM and only moves forward; a developer who advances it harms only their own device |
| R23 | Ethernet transport | Network attacker on the LAN | Malformed ARP, IP or UDP frames to break the hardware transport, or floods to deny service | A parser on an open port | Medium | Medium | No software stack: the transport is RTL that parses fixed headers and drops everything not addressed to its port, fuzzed in simulation; a fault in it cannot execute code; the loader re-initializes it on error; the PHY is held in reset unless the network policy enables it. Floods are denial of service only |
| R24 | Vendor bitstream signature, ECDSA attestation | Quantum-capable attacker | Forge the bitstream signature or an attestation | RSA and ECDSA | High | Low | A forged bitstream still needs the device's bitstream encryption key and the current pairing key; the server trusts the symmetric identity key, not ECDSA. Accepted |
| R25 | Configuration engine and boot ROM | Researcher | A silicon bug in the configuration engine, or a bug in the boot ROM | The engine cannot be patched; the boot ROM only with a platform update | High | Low | Follow the vendor's advisories; per-device keys; the boot ROM is small and tested by fault campaigns; on the FPGA it can be replaced by a platform update |
| R26 | Event log | Evil maid or thief | Erase or alter the security event log | The log lives on the card | Medium | Medium | HMAC-SHA256-chained entries under the log key; the host and the server read it and notice gaps |
| R27 | Signing keys | Insider, or loss | A signing key is lost or leaks | Keys are long-lived | Critical | Low | Main and backup LMS keys for the platform in the boot ROM and for the application in two write-locked TPM NV indices; keys held in separate HSMs; the vendor bitstream signing key revocable where the family supports it |
| R28 | CLI over the network | Network attacker on the LAN | Brute-force or abuse the CLI from the network | The port answers anyone on the LAN | High | Medium | Every CLI session authenticated through the TPM under the host key (or by the loader under the developer key), with attempt limits and logging in the loader and the TPM's dictionary-attack lockout behind them; the unauthenticated surface is the session handshake only; the port can be disabled by the application owner |
| R29 | Updates and server contact over the network | Network attacker running a fake proxy, server, or DHCP | Offer old or forged packages, redirect or block traffic | The network, the proxy and DHCP are not trusted | High | Medium | Packages verified by LMS signature and version in the loader whatever the source; the server proves itself under the device's identity key before anything else is accepted; session frames are encrypted, so the proxy and the path see ciphertext. Redirection and blocking deny service only; the server reports units that fall behind |
| R30 | UART status | Anyone with a cable | Learn something from the unauthenticated status reports | Status needs no session | Low | High | Status limited to versions, build mode, faults and pairing state; no user data and no keys; everything else needs a session |
| R31 | Bitstream and its keys | Board prober with a logic analyzer | Capture the bitstream on the configuration bus or in flash | The flash and the bus are on the board | Critical | High | The bitstream is encrypted under the FPGA's own per-device eFuse key and decrypted only inside the FPGA; the pairing key inside it is never in plaintext outside the FPGA and the HSM |
| R32 | Bitstream integrity | Board prober | Flip bits in the encrypted bitstream to alter the logic blindly | Possible only where bitstream encryption has no MAC | High | Low | **Closed on the Logos2:** AES-256-GCM authenticates every bitstream under the device's own key, and RSA-2048 signs it. On the Ti60, RSA-4096 over the bitstream does the same |
| R33 | FPGA keys in the fabric | Lab attacker | Power analysis on the FPGA's Ascon core, SHA-256 core or key loading | Soft logic leaks | High | Low | Both key-dependent cores are first-order masked (threshold implementations) with fresh randomness from the TRNG-seeded mask PRNG, and assessed by TVLA (`doc/test.md`); per-device keys, so one break exposes one unit. No family provides a hardened cipher usable from the fabric, so this does not vary by family |
| R34 | Application version in flash | Board prober with a programmer | Write an older application image back into flash | Flash keeps no freshness | High | Medium | The application header's version is checked against counter 1 at every boot, and its lines are keyed by a per-install salt in that header, authenticated under the application key |
| R35 | Loader version in flash | Board prober with a programmer | Write an older loader image back | Same | High | Medium | The boot ROM checks the loader header's version against counter 0 at every boot |
| R36 | TPM SPI bus | Board prober with an interposer | Read, forge or replay TPM traffic; advance the counters; clear the TPM | The bus is on the board; a TPM boots with an empty platform authorization | High (clearing: Medium) | Medium | Every command and response runs in a session keyed from the pairing key with fresh nonces from both sides: reads are authenticated, sealed data is encrypted and authenticated, counters need the pairing policy to advance. The TPM's reset is held by the FPGA and the boot ROM disables the platform hierarchy as its second command, so only an attacker who drives the reset and talks first can clear the TPM, which bricks the unit (denial of service, equivalent to removing the part). Accepted |
| R37 | Keys versus the application | Malicious or buggy application, including a developer build | Read a key | The application runs on the same FPGA | Critical | Medium | The application core has no bus path to the loader domain; keys live in registers with no CPU read path on either core; the mailbox is the only interface, and its parser is fuzzed (R45) |
| R38 | Plaintext inside the enclosure | Board prober during a recording | Read samples on the I2S buses or the LCD bus | CODECs and LCDs cannot encrypt | High | Medium | Tamper-evident seal; optional enclosure switch logged by the loader. Accepted |
| R39 | Live recordings | Network attacker, compromised edge proxy | Read recordings as they are uploaded | The network carries the upload | Critical | Medium | The recording engine encrypts to the host before any byte leaves the loader domain; the network and the proxy carry ciphertext only |
| R40 | Recording integrity at the source | Board prober | Replay or substitute samples on an I2S bus | I2S is plaintext | Critical | Medium | Tamper-evident seal only. Accepted |
| R41 | Stored and uploaded recordings | Thief, network attacker, cloud intruder | Read recordings on the card, in transit or in storage | Recordings leave the device | Critical | High | Ascon-AEAD128 per segment, segment keys encapsulated with ML-KEM-768 to the host and erased on the device; block and segment numbers; optional ML-DSA provenance signature |
| R42 | Bitstream build service | Insider or intruder | Collect per-device pairing and bitstream keys from the build service | The service handles them in plaintext to patch and encrypt bitstreams | Critical | Low | Keys released by the HSM per job and erased after; the service is isolated, audited and dual-controlled; outputs signed in the HSM |
| R43 | FPGA pins | Board prober with a JTAG pod | Use boundary scan to sample or drive the FPGA's pins while it runs | Boundary scan may stay available after the security settings | High | Medium | **Closed on the Logos2:** the JTAGLOCK and SCANLOCK eFuse bits disable JTAG permanently at enrollment, after the factory boundary-scan test (`fpga/logos2/`). On the Ti60 the permanent JTAG disable leaves only device-information instructions. JTAG connector not populated, inside the seal |
| R44 | Bitstream fallback | Board prober | Corrupt the active bitstream slot to force the multi-boot fallback to an older bitstream | Multi-boot picks the other slot on failure | High | Medium | The fallback bitstream holds a retired pairing key once an update has completed, so it boots into recovery, not into service; the loader then reinstalls the current platform package from the card or the host |
| R45 | Mailbox | Malicious application | Exploit the loader's message parser | The mailbox is the one interface between the cores | Critical | Medium | Fixed message set, lengths and offsets checked against fixed limits, every request copied out of shared RAM before use, parser fuzzed on the software platform (`doc/hw.md`, Mailbox) |
| R46 | TPM | Lab attacker | Decapsulate one TPM and read its keys | Any chip can be attacked in a lab | High | Low | A part validated to FIPS 140-3 physical security Level 3 with an active shield and environmental monitors, Common Criteria EAL4+ with AVA_VAN.5 targeted; keys per device, so one break exposes one unit and its hosts' data keys, never the host data secret, never past recordings |
| R47 | Recording time | Board prober, or a user with the device | Backdate or postdate a recording, or pass off an old one as new, by setting a clock | The device has no trusted clock | High | Medium | Recording headers carry the latest server-issued time beacon (MAC'd under the identity key, verified through the TPM) and the sample count since it, and the first segment after a reconnection carries the next beacon, so every recording is bracketed by server-attested instants; no device clock is trusted (`doc/acquisition.md`, When a recording was made). Residual: a recording made before the device ever contacted the server is undated |
| R48 | Stream buffer (PSRAM) | Board prober | Read or alter the recording stream in the PSRAM | An external memory on a bus | Low | Medium | It holds only authenticated ciphertext blocks already encrypted to the host; reading yields nothing, alteration is rejected by the host like any damaged block (R41); power loss costs at most the buffered tail of one segment, visibly |
| R49 | Real-time clock | Board prober | Set the clock, or drive its alarm line, to force wakes, prevent them, or mislead scheduling | The RTC is an ordinary I2C part that controls power | Medium | Medium | A wake is a cold start through the authenticated chain, so a forced one changes nothing but uptime: denial of service only, equivalent to cycling power. The RTC's time is never trusted (R47 covers recording time); a reboot during a recording ends the segment visibly (`doc/hw.md`, Real-time clock) |

## Optional: Code Secrecy Profile

Flash contents are already encrypted under keys unique to each device. The weak point for code secrecy is the fleet-wide distribution key (R18):
breaking one device exposes every package. The profile replaces it with **per-device packages**: the update server wraps each package's content key
to the device's own key, derived from its application key. That needs the server, so offline updates would carry per-device packages too, prepared for
one device. The profile changes nothing else in the design.

## Algorithm bill of materials

| Algorithm | Standard | Runs in | Used for |
|---|---|---|---|
| Bitstream encryption and signature | Vendor | FPGA configuration engine | Logos2: AES-256-GCM and RSA-2048 over SHA-3. Ti60: AES-256-GCM and RSA-4096 |
| **Ascon-AEAD128** | NIST SP 800-232 | The FPGA's masked Ascon core (XIP, recordings, install port, sessions, user data); sensor; host | XIP lines, recordings, host and CLI sessions, user data, update and developer packages, sensor frames |
| **HMAC-SHA256 KDF** | SP 800-108 (HMAC mode), FIPS 198-1 | FPGA SHA-256 core (derive mode); sensor; host | Key derivation after an unwrapped key: install keys, data keys, pairing keys, segment-key wraps; TRNG conditioning |
| SHA-256, HMAC-SHA256 | FIPS 180-4, FIPS 198-1 | FPGA SHA-256 core, loader domain | TPM session key derivation (KDFa) and command and response HMACs, LMS verification, header HMACs, certificate and transcript hashes, the event log's MAC chain |
| LMS (HSS) | RFC 8554, SP 800-208 | Loader core, on the SHA-256 core | Update package signatures |
| ML-DSA-44 | FIPS 204 | Loader core (verify only); optionally sign, for recording provenance | Sensor certificates |
| ML-KEM-768 | FIPS 203 | Loader core (encapsulate), sensor (decapsulate), host (decapsulate) | Sensor pairing; recording segment keys |
| ECDSA P-256, SHA-256 | FIPS 186-5 | TPM only | Quotes under the attestation key; the attestation and endorsement key certificates |
| AES-128-CFB | FIPS 197, SP 800-38A | FPGA session cipher (encrypt direction only, unmasked, one key per session); TPM | TPM session parameter encryption: sealed keys out, the next pairing key in. With the session HMAC, an approved key transport (`doc/fips.md`) |
| TPM 2.0 sessions, policies, NV, HMAC, Quote | TCG TPM 2.0 Library | ST33KTPM2X | Pairing, key release, counters, host authentication, server authentication, attestation (`doc/tpm.md`) |
| TRNG | SP 800-90A/B/C | Ring-oscillator TRNG in the FPGA with SP 800-90B health tests, with the TPM's SP 800-90B source and Hash_DRBG (CMVP #4737) as additional input; a TRNG on the sensor | Nonces, segment keys, install salts |

**Ascon everywhere we choose the symmetric cipher.** No candidate FPGA offers a power-analysis-hardened cipher usable from the fabric: the Logos2's "DPA protection" means the configuration engine
authenticates a bitstream before decrypting it, which denies an attacker chosen ciphertexts but hardens nothing the fabric can use. So the cipher is soft logic on every family and on the ASIC, and must carry
its own countermeasures. Ascon-AEAD128 was chosen because a first-order masked implementation costs a few times its small unprotected area, where a masked AES costs an order of magnitude more, and because one
permutation core serves every user (`doc/hw.md`, The Ascon core). The one AES in the fabric is the TPM session cipher, because TPM 2.0 parameter encryption offers AES-CFB or an unapproved XOR and nothing else; it is unmasked, since each of its keys lives for one session.

**Two key-dependent soft blocks, both masked.** The Ascon core, and the SHA-256 core, which derives and authenticates the TPM sessions under the pairing key and runs the HMAC-SHA256 KDF and the header and log MACs.
Both need side-channel assessment (R33, H4), and both are the same RTL on the ASIC. The third key-dependent block, the AES-128 session cipher for the TPM, is unmasked: its key is derived per session, so an attacker never sees two sessions' traffic under one key.

**Key sizes.** Ascon-AEAD128 is a 128-bit-security algorithm: 128-bit keys, nonces and tags. The roots those keys are derived from (pairing, identity, application, data and HSM master keys) are 256 bits, as are
the hashes, MACs and KDF outputs, and recordings are additionally protected at the key-encapsulation level by ML-KEM-768. The design therefore claims NIST post-quantum category 1 for bulk data and category 5
for the key hierarchy, rather than category 5 throughout; NIST treats 128-bit symmetric keys as adequate against Grover's algorithm, and SP 800-232 was standardized for exactly this class of device.

**Post-quantum code on a soft core.** LMS verification, ML-KEM encapsulation and ML-DSA verification run as Forth on the loader core, with the SHA-256 core doing the hashing.
None is on a hot path: LMS at install, ML-KEM once per recording segment and once per sensor pairing, ML-DSA once per pairing. Their speed on LiteForth is an open question (H5).

**P-256** only where the TPM dictates it.

**FIPS 140-3 through the CMVP is the long-term target.** Every algorithm above is approved and CAVP-testable (Ascon's coverage is recent and to be confirmed, A11); the TRNG is an SP 800-90B source
feeding an SP 800-90A HMAC_DRBG; the module boundary, self-tests, roles, zeroization and the design changes the target forces now are in `doc/fips.md`.

## Open questions

All open questions are collected in `doc/questions.md`.
