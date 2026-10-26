# Architecture: Algorithm Bill of Materials

This document lists every cryptographic and support algorithm that `thriller` needs for signing,
provisioning, booting and updating, and where each one runs.

## Two update chains

`thriller` authenticates two independent kinds of update:

- **Platform updates** replace the FPGA bitstream, including the `thriller` loader. They exist only on FPGAs.
- **Application updates** replace the code and data stored encrypted in SPI NOR flash. They exist on FPGAs and on an ASIC conversion.

Each chain has its own LMS signing key, its own secure element counter and its own package format.
The rows marked "platform only" below disappear in an ASIC conversion; everything else carries over.

## Threat model

### Assets

| Asset | Goal |
|---|---|
| User data in flash | Confidentiality and integrity. **The primary asset.** |
| Application image | Integrity, and only the genuine signed versions run. Packages are encrypted in transit so they show no plaintext, but keeping the code secret from a determined attacker is not a goal of the base model; see the optional Code Secrecy Profile. |
| Device identity | A unit cannot be cloned or impersonated. |
| Update signing keys | Never exposed. They stay offline in an HSM. |
| The rest of the fleet | Compromising one unit exposes nothing about another. |

### Attackers

| Attacker | Capability |
|---|---|
| Remote | Talks to the device over the UART only. |
| Bus prober | Can watch and inject traffic on the I2C bus to the secure element. |
| Thief | Has the device and unlimited time, but the legitimate host never connects to it again. |
| Evil maid | Has the device for a while, then returns it to the legitimate user, who connects their host. |
| Quantum-capable | Can break ECDSA and RSA, but not AES-256, SHA-256 or LMS. |

The design assumes the bitstream **may be compromised**: replaced with a foreign design, or a genuine encrypted
bitstream modified blindly (on Tier B, AES-CBC style encryption without a MAC can allow targeted bit flips).
It limits what a compromised bitstream can reach rather than relying on preventing it.

### Outcomes

| Asset | Remote | Bus prober | Thief | Evil maid | Quantum-capable |
|---|---|---|---|---|---|
| User data | Safe | Safe (MAC'd and encrypted transfers, loader nonce) | **Safe on both tiers**: the data key needs the host | Tier A: safe unless the bitstream is compromised. Tier B: exposed if a bitstream compromise succeeds | Same as without the quantum computer (all symmetric) |
| Application image | Safe | Safe | Can run modified code on that unit only | Can run modified code on that unit | Same |
| Device identity | Safe | Safe | Can use the identity while holding the unit, cannot clone it | Same | Same (symmetric keys) |
| Update signing keys | Safe | Safe | Safe | Safe | Safe (LMS) |
| Other units | Safe | Safe | Safe (per-device keys) | Safe | Safe |

The difference between the tiers is only the evil-maid column: how expensive it is to plant a compromised
bitstream that will be running when the user next authenticates.

### Bitstream compromise on Tier B

Without the AES key, an attacker can only flip bits in the encrypted bitstream. In CBC mode each targeted
edit also turns a whole 16-byte block into unpredictable garbage, and the result must still pass the
configuration engine's CRC. How hard that is depends on the CRC:

- A 16-bit CRC can be satisfied by brute force in about 65,000 configuration attempts, which is minutes.
- A 32-bit CRC makes blind edits impractical.

The ECP5's encryption mode and CRC width are open questions. Even a successful edit is targeted at one unit,
and the attacker must then return it and wait for the user to authenticate.

### Not protected

- User data on a unit while the evil maid's compromised bitstream is running a legitimate session.
  Mitigation: tamper-evident enclosures and custody of the hardware.
- Remote attestation. A compromised bitstream that holds the pairing key looks identical to a good one,
  so a host cannot tell from the protocol alone.
- Denial of service. A compromised bitstream can burn counter values or erase flash; it cannot roll counters back.
- Secrecy of the application code, unless the Code Secrecy Profile is enabled.

## Risk Assessment

The Outcomes table above summarizes which assets survive each attacker. This table breaks the same ground
down into individual risks, one per attack, so each can be rated, owned and tracked.

Ratings are for the base model (no Code Secrecy Profile) unless a row says otherwise.

**Impact:**
- **Critical:** user data exposed or forged, arbitrary code execution, or any fleet-wide compromise.
- **High:** a single unit compromised or rolled back to a vulnerable version.
- **Medium:** loss of service, a bricked unit, or a weakened but not broken protection.
- **Low:** exposure of information the model does not treat as secret.

**Likelihood:**
- **High:** needs only common tools (flash programmer, logic analyzer, JTAG pod) and public knowledge.
- **Medium:** needs physical access plus specialist skill, or sustained effort against one unit.
- **Low:** needs a well-equipped lab, an insider, or capabilities that do not yet exist.

| # | Asset / Component | Threat Actor | Attack Vector / Threat Description | Vulnerability Exploited | Impact | Likelihood | Mitigation / Countermeasure |
|---|---|---|---|---|---|---|---|
| R1 | External SPI flash: user data | Thief with a flash programmer | Desolder or clip the flash and read user data offline | Flash is external and readable | Critical | High | AES-256-GCM under a per-device data key that the secure element releases only after host authorization (CheckMac) |
| R2 | External SPI flash: application image | Casual hobbyist with a flash programmer | Dump the flash and inspect the application | Flash is external and readable | Low | High | AES-256-GCM under a per-device application key; a copied image will not run on another board |
| R3 | External SPI flash: version state | Insider or thief with physical access | Restore an older, vulnerable bitstream or application image | Flash contents are not bound to a version | High | Medium | Secure element monotonic counters (0: platform, 1: application); pairing key rotation retires old bitstreams |
| R4 | UART update path | Advanced remote attacker | Send a forged or modified update package | UART accepts update packages from anyone | Critical | Medium | LMS signature verified by the loader over the ciphertext, before decrypting or installing anything |
| R5 | Update packages in transit | Casual hobbyist | Hex dump an update file or capture it on the UART | Packages travel over open channels | Low | High | AES-256-GCM under the fleet-wide distribution key (obfuscation). For real secrecy, per-device package keys (Code Secrecy Profile) |
| R6 | Distribution key | Attacker with one compromised unit | Read the distribution key and decrypt all past and future packages | Key is the same on every unit and readable by the loader | Low (High with the Code Secrecy Profile) | Medium | Accepted in the base model. Code Secrecy Profile replaces it with per-device package keys |
| R7 | I2C bus to the secure element | Casual hobbyist with a logic analyzer | Sniff keys as the loader reads them | Bus is external and unencrypted | High | High | Encrypted key reads (EncRead) under the pairing key; keys never cross the bus in clear |
| R8 | I2C bus to the secure element | Insider with a bus interposer | Replay or forge counter values and read results | Bus is external; responses could be replayed | High | Medium | Every response MAC'd under the pairing key over a fresh loader-generated nonce |
| R9 | UART host session | Advanced remote attacker | Guess or brute-force the host authorization to unlock user data | UART is an open channel; the secure element has no retry lockout | Critical | Low (high-entropy key); High (short PIN) | High-entropy host authorization key checked inside the secure element; if a PIN is ever used, a counter-limited key caps attempts |
| R10 | Bitstream (Tier A) | Advanced attacker with a lab | Forge or modify a bitstream that the FPGA will accept | Requires breaking the vendor signature and the AES key | Critical | Low | Vendor signature plus AES-256 with encrypted-only configuration. Damage limited by the pairing key and host-authorized data key |
| R11 | Bitstream (Tier B, ECP5) | Skilled attacker with physical access | Blind bit-flip edits to the encrypted bitstream, brute-forcing the configuration CRC | No hardware authentication; CBC-style encryption without a MAC | High (code execution on that unit; user data exposed in a later evil-maid session) | Medium (Low if the CRC is 32-bit; see Open Question 9) | Host-authorized data key (a stolen unit still protects data), per-device keys, tamper-evident enclosure |
| R12 | Bitstream: foreign design | Casual hobbyist with a JTAG pod | Load their own design and talk to the secure element and flash | JTAG configuration open, or plaintext bitstreams accepted | Medium (denial of service, burned counters) | High on Tier B, Low on Tier A | Pairing key gates every secure element key; encrypted-only configuration and JTAG lockout where the FPGA supports them |
| R13 | Bitstream: configuration readback | Casual hobbyist with a JTAG pod | Read back the running configuration and extract the pairing key | Readback left enabled | Critical | High if enabled, Low once fused | Readback permanently disabled at manufacturing (FPGA Requirement 4) |
| R14 | FPGA bitstream encryption key | Advanced attacker with a lab | Side-channel or invasive extraction of the AES key from the FPGA | Physical access to the configuration engine | Critical (every bitstream decryptable; with the same key fleet-wide, every unit's pairing secret is exposed) | Low | Per-device pairing key diversification limits each pairing key to one unit; host-authorized data key keeps stolen-unit data safe |
| R15 | Loader: soft CPU debug paths | Casual hobbyist with a JTAG pod | Use a soft CPU debug port or user-JTAG primitive to read keys from internal memory | Debug logic left in a production bitstream | Critical | Medium | No debug ports or user-JTAG primitives in production bitstreams |
| R16 | Loader: security checks | Advanced attacker with physical access | Voltage or clock glitching to skip the LMS check, the counter check or the tag check | A single check is a single point of failure | Critical | Low | Planned: duplicated checks with independent code paths, and failing closed. Not yet designed |
| R17 | Loader: AES core | Thief with an oscilloscope | Power or EM side-channel analysis during application decryption | AES core is not masked | Low (High with the Code Secrecy Profile) | Medium | Accepted in the base model. Code Secrecy Profile adds a masked AES core and decrypts once per boot |
| R18 | Secure element | Advanced attacker with a lab | Invasive or side-channel attack on the ATECC608B to extract its keys | Physical access to the secure element | High (one unit only) | Low | Per-device key diversification limits the result to one unit |
| R19 | Update process | Any user, or an attacker cutting power | Power failure during a platform or application update | Update is not atomic | Medium (bricked unit) | Medium | A/B flash slots. Pairing key rotation sequencing is still open (Open Question 1) |
| R20 | LMS signing infrastructure | Insider, or an operator error | Reuse an LMS leaf (for example after restoring the signer from backup), enabling forgery | LMS is stateful | Critical (fleet-wide forged updates) | Low | Signing state kept in an HSM that enforces one-time use (SP 800-208); no restores of signer state |
| R21 | Vendor bitstream signature (Tier A) | Future quantum-capable attacker | Break the vendor's ECDSA or RSA signature with Shor's algorithm | Vendor signature is not quantum-safe | Medium (Tier A falls back to Tier B protection) | Low (today) | Encrypted-only configuration (AES-256), LMS for all of our own signatures, all data protection symmetric |
| R22 | Remote attestation | Advanced remote attacker controlling a compromised unit | Pass a compromised unit off as genuine to a host or server | A bitstream holding the pairing key is indistinguishable from a good one | High | Low | Accepted. Not protected by this design (see Not protected) |

## Optional: Code Secrecy Profile

The base model protects the application's integrity, not its secrecy. Some users will also want to keep
their code secret. This profile lists what that adds and what it costs. Enable it only if code secrecy is a requirement.

### Why code is harder than user data

User data is per device and per user. Application code is the **same plaintext on every unit**, so breaking
any one unit leaks it for the whole fleet. Per-device key diversification does not help: it stops one unit's key
from decrypting another unit's flash, but every unit's flash holds the same code.

User data is also gated by the host authorization key. Code cannot be: the loader must decrypt the application
at boot with no host present, or the device cannot run on its own. A compromised bitstream on any unit
can therefore reach the code.

### Added asset

| Asset | Goal | Scope |
|---|---|---|
| Application confidentiality | The plaintext application never leaves the device | Fleet-wide: one leak exposes every unit |

### Outcomes for application confidentiality

| Tier | Remote | Bus prober | Thief | Evil maid | Quantum-capable |
|---|---|---|---|---|---|
| Tier A | Safe | Safe | Safe unless the bitstream is compromised | Same as thief | Reduces to the bitstream encryption mode: still strong with authenticated encryption (Ti60 AES-GCM), unconfirmed for CrossLink-NX |
| Tier B | Safe | Safe | **Exposed if a blind bitstream modification succeeds** | Same as thief | Same as without the quantum computer |
| ASIC | Safe | Safe | Safe against bitstream attacks; side channels remain | Same as thief | Safe |

The thief is now the main attacker. For user data, a Tier B bitstream compromise only mattered to an evil maid
who also had to return the unit and wait for the user. For code, a thief with any unit and unlimited time
needs only one success, and the reward is the whole fleet's code. The ECP5's configuration CRC (Open Question 9)
becomes the entire defense of the code on Tier B.

**Recommendation:** use Tier A for code secrecy, preferably an FPGA with an authenticated-encryption bitstream
format such as the Ti60's, or an ASIC. On Tier B, code secrecy is best effort only.

### Changes the profile requires

**Per-device package keys.** The base model already encrypts application packages in transit, but under a
fleet-wide distribution key that the loader reads from the secure element. That stops a casual hex dump, not
an attacker: a compromised bitstream on one unit can decrypt every future release. The profile replaces it:

| | Base model | Code Secrecy Profile |
|---|---|---|
| Package key | Fleet-wide distribution key, the same in every secure element | Package key = KDF(distribution master key, SE serial number). The master stays in the HSM |
| Packages built | One per release | One per unit per release |
| One compromised unit exposes | Every release, past and future | Only the releases that unit received |

Both are symmetric, so both are quantum-safe. In both, the package is signed (LMS) over the ciphertext,
so the loader can reject a forged package before decrypting anything.

**Side-channel hardening.** A thief can reboot a unit thousands of times and record power or EM traces while the
loader's AES core decrypts the application. Recovering one unit's key reveals the fleet's code. Options:
- A masked or otherwise side-channel-hardened AES core in the loader.
- Decrypt the application once per boot into internal RAM, never streaming it repeatedly from flash.
- Optionally, a counter-limited application key in the secure element, which caps how many times it is released, at the cost of a fixed boot budget.

**No in-use readout paths.** These become hard requirements instead of hygiene:
- No debug port on the soft CPU in production bitstreams.
- No user-JTAG primitives in the design (for example the ECP5's JTAGG) that can reach internal memory.
- Configuration readback permanently disabled (already required).
- Fabric JTAG disabled where the FPGA allows it.

**Separate key owners.** If a customer owns the application and needs it secret from the platform vendor too,
the profile cannot provide that: the platform's loader decrypts the customer's code, so the customer must trust
the platform. The profile can only protect the code from everyone else.

### Added algorithms

| Algorithm | Host | Loader | Secure element | Used for |
|---|:-:|:-:|:-:|---|
| KDF (HMAC-SHA256 based, for example HKDF) | derive from master | | | Per-device package keys |
| Side-channel-hardened AES core | | yes | | Application decryption at boot |
| Package key slot | | read over MAC'd channel | store | Per-device package key, replacing the fleet-wide distribution key |

Package encryption itself (AES-256-GCM) is already in the base model.

## Where algorithms run

| Location | What it is | Who provides it |
|---|---|---|
| **Host** | Signing and provisioning tools, and the field update client | Us (scripts and an HSM) and the FPGA vendor (bitstream tools) |
| **Config engine** | The FPGA's hardened configuration logic | FPGA vendor, fixed in silicon (platform only) |
| **Loader** | RTL cores and soft MCU code in the bitstream, or in silicon on an ASIC | Us |
| **Secure element** | ATECC608B (or MOD8ID) | Microchip / Modsemi, fixed in silicon |

The design goal is that every algorithm in the loader is built from **SHA-256 and AES**: no bignum or
elliptic-curve arithmetic. LMS signatures make this possible, because verifying one is just hashing.

## Summary

| Algorithm | Host | Config engine | Loader | Secure element | Used for | ASIC |
|---|:-:|:-:|:-:|:-:|---|:-:|
| Bitstream signature (ECDSA P-256 or RSA-4096, per family; Tier A only) | sign | verify | | | Stage 0 bitstream authentication | — |
| Bitstream encryption (AES-256, mode per family) | encrypt | decrypt | | | Bitstream confidentiality, and quantum-safe Stage 0 | — |
| LMS (RFC 8554), platform key | sign (stateful, HSM) | | **verify** | | Platform package signatures | — |
| LMS (RFC 8554), application key | sign (stateful, HSM) | | **verify** | | Application package signatures | ✓ |
| SHA-256 | yes | | **yes** | yes | LMS, package digests, MACs, nonce and key derivation | ✓ |
| SE MAC protocol (SHA-256 based) | | | **yes** | yes | Authenticated counter reads and public key reads | ✓ |
| SE host authorization (CheckMac, SHA-256 based) | yes | | forwards only | **check** | Host proves itself to the SE; unlocks the data key | ✓ |
| AES-256-GCM (or AES-CTR + HMAC) | | | **yes** | | Application and user data encryption and authentication in flash | ✓ |
| AES-256-GCM, distribution key | encrypt | | **decrypt** | store | Application packages in transit (obfuscation) | ✓ |
| Key wrap / encrypted write | wrap | | **yes** | yes | Installing the next pairing key | — |
| Monotonic counter 0 | | | | yes | Platform anti-rollback | — |
| Monotonic counter 1 | | | | yes | Application anti-rollback | ✓ |
| TRNG | | | | yes | Key generation, SE nonces | ✓ |
| Loader nonce source | | | **yes** | | Freshness the SE and bus cannot control | ✓ |
| CRC-16 (poly 0x8005) | | | **yes** | yes | SE I2C packet integrity | ✓ |
| CRC-32 | yes | | yes | | UART transport framing (not security) | ✓ |

## Host

**Bitstream signing and encryption (platform only).** Done by the FPGA vendor's tools, so the algorithm depends on the family:
ECDSA with AES-256 on Lattice Nexus, RSA-4096 with AES-GCM-256 on Efinix Titanium. These signatures are not
quantum-safe, so the device must also be locked to accept only encrypted bitstreams (README, FPGA Requirements item 5).

**LMS signing (both chains).** Each chain has its own LMS key pair. Platform packages hold a bitstream, its version,
and the next pairing key wrapped under the current one. Application packages hold the application image, encrypted
under the distribution key (AES-256-GCM), and its version; the LMS signature covers the ciphertext.
Because the loader verifies the platform signature before writing a bitstream to flash, every platform update is signed
twice: LMS by us, and the vendor's own format checked by the config engine at boot.

LMS is stateful, and the signing side must be built around that:
- Each one-time key (leaf) signs exactly once. Reusing a leaf lets an attacker forge signatures.
- The signer's state (next leaf index) must survive crashes and must never be restored from an older backup.
- SP 800-208 expects key generation and signing in a hardware security module that enforces this.
- A tree of 2^10 to 2^15 leaves covers far more updates than a product line will ever ship. HSS
  (multi-level trees, also in RFC 8554) is available if one key must last longer.

The application key can be held by a different party than the platform key, for example a customer who ships
their own application on our platform.

**Provisioning.**
- Write and lock the secure element configuration zone.
- Write the application LMS public key, the first pairing key, the host authorization key, the distribution key,
  the device-unique application key and the device-unique data key into their slots, then lock the data zone.
- Configure the data key slot to require authorization by the host authorization key, and make the host
  authorization key non-readable, so it can only be used inside the secure element.
- The platform LMS public key needs no provisioning: it is built into the bitstream.
- Diversify every key per device, for example pairing key = KDF(release pairing key, SE serial number).
  This is mandatory: it is what keeps a compromised unit from exposing the rest of the fleet.
  The one exception is the distribution key, which must be the same on every unit so one package installs everywhere.
- Give the host its copy of the host authorization key (or the means to derive it) over a channel separate from the device.
- Program and lock the FPGA's key fuses (see the FPGA Requirements in the README).

**Field update client and host session.** Sends platform and application packages over the UART, and answers
the secure element's challenge with a MAC under the host authorization key to open a data session.

## Config engine (platform only)

Fixed in silicon; we only choose and lock it.

- Bitstream signature verification (ECDSA or RSA, per family; Tier A only)
- Bitstream decryption (AES, per family; both tiers)
- Key storage in one-time fuses
- Port and readback lockout, and encrypted-only configuration

## Loader

This is the part we write. It should be small, identical across FPGA families, and suitable for an ASIC.

**SHA-256 (required, RTL core strongly recommended).** Everything else in the loader is built on it:
LMS verification, package digests, the secure element MAC protocol, HMAC, and key derivation.
LMS verification alone runs hundreds to thousands of SHA-256 compressions, so a hardware core matters.
One shared core can serve all users.

**LMS verification.** Recomputes the one-time public key from the signature by walking the Winternitz hash
chains, then climbs the Merkle tree to the root and compares it with the stored public key. Only SHA-256 is needed.
Sizes for the common parameter sets (n = 32, SHA-256):

| Parameter set | Signature size | Max chain hashes to verify | Signatures per key |
|---|---|---|---|
| LMS_SHA256_M32_H10 + LMOTS_SHA256_N32_W4 | 2,508 bytes | about 1,000 | 1,024 |
| LMS_SHA256_M32_H10 + LMOTS_SHA256_N32_W8 | 1,452 bytes | about 8,700 | 1,024 |
| LMS_SHA256_M32_H15 + LMOTS_SHA256_N32_W4 | 2,668 bytes | about 1,000 | 32,768 |

W = 4 is the natural choice: signatures are larger but still small next to an image, and verification is about
eight times faster. Public keys are 56 bytes for every parameter set. SP 800-208 also defines 192-bit (M24/N24)
variants with smaller signatures.

Where the public keys come from:
- **Platform key:** a constant in the bitstream, authenticated by Stage 0.
- **Application key:** read from its secure element slot over the MAC'd channel at each use, so a device on the I2C bus cannot substitute its own.

**Secure element MAC protocol.** The loader recomputes the MACs that the secure element returns, so the I2C bus
cannot forge or replay results. Needed for:
- Counter reads: Nonce, then GenDig over the counter, then MAC with the pairing key.
- Public key reads: an authenticated read of the application LMS public key slot.
- Encrypted reads and writes of keys (EncRead/EncWrite, which use SHA-256 derived keystreams).

The exact digest layouts are defined by Microchip's command formats. Implement them from cryptoauthlib
and test each one against real parts before any zone is locked.

**Loader nonce source.** The loader must put its own fresh value into each Nonce command (NumIn).
If it only uses the secure element's random output, a device on the bus can replay an old exchange.
Options, smallest first:
- A ring-oscillator TRNG with health tests (no external dependency).
- A free-running counter combined with the SE serial number and a boot count. This is weaker: it must never repeat across power cycles.

**AES-256-GCM, or AES-256-CTR with HMAC-SHA256.** Decrypts and authenticates the application read from flash at boot,
and encrypts it on update. GCM needs an AES core plus a GHASH (GF(2^128) multiply). CTR plus HMAC reuses the
SHA-256 core and needs only the AES encrypt direction. Either is fine; CTR plus HMAC is likely smaller.
The secure element's AES is single-block over I2C and too slow for whole images. AES-256 is quantum-safe.

**Key wrap for pairing key rotation (platform only).** The platform package carries the next release's pairing key,
encrypted under the current one. The loader unwraps it and writes it to the secure element with an
authorized encrypted write. Sequencing across power failures still needs to be designed (see Open Questions).

**Host authorization relay.** The loader does not check the host itself. It asks the secure element for a
challenge, mixes in its own nonce, passes the challenge to the host, and forwards the host's answer to the
secure element's CheckMac. Only after a successful CheckMac will the secure element release the data key.
The loader never sees the host authorization key, so a compromised bitstream cannot learn it.
The loader must erase the data key when the session ends.

**Support logic (not cryptographic).**
- I2C master with the secure element's CRC-16 (polynomial 0x8005, initial value 0, LSB first), wake, idle and sleep handling.
- QSPI flash driver with A/B slots for the bitstream and for the application, so a failed update never leaves the device without a bootable image.
- UART framing with CRC-32.

## Secure element

Fixed in silicon; we only configure and lock it. With LMS, it no longer checks signatures. Its jobs are:

- Two monotonic counters (maximum 2,097,151): counter 0 for the platform, counter 1 for the application
- Key storage: application LMS public key, pairing key, host authorization key, distribution key, device-unique application key, device-unique data key
- Host authorization: CheckMac against the non-readable host authorization key, gating use of the data key slot
- SHA-256 and the Nonce, GenDig, MAC, CheckMac, EncRead and EncWrite commands for the authenticated channel
- TRNG
- Configuration and data zone locks

Its ECDSA engine goes unused. On an ASIC, counter 0 is free for other uses.

## Not needed

These are deliberately absent from the loader:

- ECDSA, Ed25519 and RSA (no bignum or elliptic-curve arithmetic, and none are quantum-safe)
- PUF and fuzzy extractor (the secure element holds device-unique keys)
- Any algorithm specific to one FPGA family

## Open Questions

1. **Pairing key rotation sequencing (platform only).** The order of operations for writing a new bitstream, installing the next pairing key and advancing counter 0, such that a power failure at any point leaves a bootable, non-rollbackable device.
2. **Secure element protocol details.** Confirm that GenDig over the counter zone, authenticated reads of the public key slot, and EncWrite of the pairing key slot all work as expected on the ATECC608B, and separately on the MOD8ID.
3. **AES mode choice.** GCM or CTR plus HMAC, decided by measured fabric area on the smallest target FPGA.
4. **Nonce source.** Whether a ring-oscillator TRNG is reliable enough across the supported FPGA families and an ASIC process, or whether the counter fallback is acceptable.
5. **ASIC pairing key.** A pairing key in mask logic is the same on every chip and can be recovered from one die. An ASIC needs a per-device pairing key, written at provisioning into one-time-programmable fuses or another per-device store.
6. **Separate key owners.** If the application key belongs to a customer, how they provision their LMS public key into the secure element without needing access to the platform key.
7. **LMS parameter set and signing infrastructure.** Final choice of tree height and Winternitz parameter (W = 4 assumed), whether to use SHA-256/192, and which HSM or signing service manages LMS state for each key owner.
8. **Host authorization on the ATECC608B.** Confirm that a slot can require authorization by another key
   (the ReqAuth and AuthKey configuration fields in cryptoauthlib), how long the authorization lasts, and how it is cleared
   at session end. Also decide how to limit attempts if the host key is ever derived from a PIN.
9. **ECP5 bitstream security.** The ECP5's AES key size and mode, the width of the configuration CRC
   (Project Trellis documents the bitstream format), whether encrypted-only configuration and readback lockout can be fused,
   and whether a bitstream built with Yosys and nextpnr can be encrypted, and with which tool.
10. **Code Secrecy Profile.** Whether per-device package keys fit the intended update distribution (one build per unit),
   how much area a masked AES core costs on the smallest target, and whether the application fits in internal RAM
   so it is decrypted only once per boot.
