# Trusted Platform Module

The TPM holds what the FPGA cannot keep for itself: per-device keys, the device's identity, and the monotonic counters. This document lays out its NV indices and objects,
the sessions between the loader domain and the TPM, the pairing-key ratchet that kills superseded bitstreams, host authentication, attestation, and provisioning. It replaces the
ATECC608C design: the TPM was chosen when FIPS 140-3 became the target, because it is itself a validated module (CMVP certificate #4737), which lets the device's own module boundary shrink
to the loader domain (`doc/fips.md`, boundary B). Every detail below is a proposal to be checked against the TPM 2.0 Library specification and tested on real parts before a configuration is
frozen (`doc/questions.md`, E5).

## Part

- **ST33KTPM2X32DKG9** (STMicroelectronics), UFQFPN32 5 × 5 mm, 1.8 or 3.3 V, SPI to 66 MHz or I2C to 1 Mb/s on the same die (a pull-down on `GPI_I2C_Select` picks I2C at boot;
  left open, the part is SPI). Firmware 9.257, which is firmware version [A] on **CMVP certificate #4737**: FIPS 140-3, overall Level 1, physical security Level 3, single-chip, validated
  2024-07-25. The CAVP list behind the certificate covers AES (CBC, CFB128, CTR, ECB, OFB), ECDSA and KAS-ECC, Hash_DRBG, HMAC with SHA-2 and SHA-3, the SP 800-108 KDF, RSA including KTS-IFC,
  and SHA-2 and SHA-3. The other order codes are **DKJ1** (firmware 9.512, adds an optional FIPS 140-3 Level 2 authentication mode; minimum order quantity applies) and **CKE3** (firmware 9.256,
  the former ST33KTPM2XI2C line, same features, different production site). The order code must stay on the certificate's hardware and firmware list, so a change of code is a change to check (E6).
- **Inside:** an SP 800-90B noise source, LMS-signed firmware updates, an active shield, environmental monitors, and fault-injection and side-channel countermeasures; Common Criteria EAL4+
  with AVA_VAN.5 targeted. Four endorsement keys with ST-issued certificates (RSA-2048, RSA-3072, ECC P-256, ECC P-384) are provisioned at ST's factory.
- **Interface: SPI**, in the TCG PC Client Platform TPM Profile (PTP) FIFO protocol: a 4-byte header, wait states signalled by the TPM on the fourth header byte, locality 0 only, the
  `TPM_ACCESS`, `TPM_STS` and `TPM_DATA_FIFO` registers. The SPI master and the wait-state handling are RTL in the loader domain (`doc/hw.md`); command marshalling (TPM2B structures, big-endian,
  the session and authorization areas) is loader firmware. The bus stays inside the sealed enclosure (R36), and nothing else is on it.
- **Reset.** `RST` is driven by the FPGA with a pull-down, so the TPM is held in reset while the FPGA configures and until the boot ROM is running; the boot ROM releases it, issues
  `TPM2_Startup` and immediately disables the platform hierarchy (below). The window in which anything but the boot ROM could talk to a freshly started TPM is thereby the boot ROM's first
  two commands, on a bus inside the seal.
- **Power:** on the FPGA's 3.3 V domain, not the always-on rail. All TPM state is non-volatile, so nothing is lost by powering it down with the FPGA, and the 66 mW maximum would be
  wasted on the always-on budget. `PIRQ` is left unconnected (polling), `GPIO_PP` (physical presence) is left at its internal pull-down, and the exposed pad is soldered to ground.
- **Who talks to it.** Only the loader core domain. The boot ROM runs the startup, the pairing session, the counter 0 read and the application key's unseal; the loader runs everything else.
  No core ever sees a key: session keys and HMACs are computed in the SHA-256 core with the pairing key taken straight from the key source, and keys the TPM releases are decrypted by the
  session cipher straight into key registers (`doc/hw.md`, Key paths).
- **Sourcing.** A high-volume part: Mouser holds tens of thousands in stock with more scheduled; DigiKey, RS and Future list it too. LCSC does not, so JLCPCB builds take it as a consigned part (E8).

## What lives where

The TPM stores three kinds of thing: **NV indices** (data, counters or bit fields in its own non-volatile memory, each with an authorization value and a policy), **objects** (keys and sealed
secrets, which the TPM wraps under its storage root key and hands back as blobs that live in our flash and are loaded when needed), and **PCRs** (volatile measurement registers, reset at startup).

### NV indices

All indices are created at provisioning under the platform hierarchy (`TPMA_NV_PLATFORMCREATE`), so a `TPM2_Clear` cannot remove them and, once the boot ROM has disabled the platform
hierarchy, nothing at run time can define, undefine or relock them. Sizes are in bytes.

| Index | Type | Size | Auth value | Read | Write | Used for |
|---|---|---|---|---|---|---|
| **Pairing** | Ordinary | 32 | **Pairing key** K(*N*), per device and per bitstream release | Auth | Written once at provisioning (the provisioning record: configuration version, batch, date), then write-locked | The anchor of every session: proving the pairing key, deriving session keys, and the entity every key's policy refers to. `NO_DA`, so a lockout can never stop the device from booting. Policy: PolicyAuthValue, PolicyCommandCode(`TPM2_NV_ChangeAuth`), which is the ratchet |
| **Host** *h* (eight, for up to eight enrolled hosts) | Ordinary | 8 | **Host authorization key** H*h*, per device and host; random until a host is enrolled | Auth | Written once (the host slot number), then write-locked | The host proves knowledge of H*h* to the TPM through a relayed HMAC session; data key *h*'s policy refers to this index. Policy: PolicySecret(pairing), PolicyCommandCode(`TPM2_NV_ChangeAuth`), so the loader can set H*h* when a host is enrolled over a server session, replace it for a replacement host, or randomize it to cut a compromised host off (R20). Dictionary-attack protected (R28) |
| **Counter 0** | Counter | 8 | None | Policy | Policy: PolicySecret(pairing) | Platform version: the bitstream and the loader under one version. Increment only; 64 bits |
| **Counter 1** | Counter | 8 | None | Policy | Policy: PolicySecret(pairing) | Application version and the developer key epoch (epoch = counter 1 ÷ 1024, `doc/roles.md`) |
| **Counter 2** | Counter | 8 | None | Policy | Policy: PolicySecret(pairing) | Supervisor image version (`doc/flash.md`) |
| **Freshness** | Ordinary | 32 | None | Policy | Policy: PolicySecret(pairing) | A digest of the latest user data state, to detect an old copy of the card being restored (R10) |
| **Lifecycle** | Bit field | 8 | None | Policy | Set-only bits, policy: PolicySecret(pairing) | Enrollment complete, retired, wiped; on the ASIC also the PUF enrollment state (`doc/ics55.md`). Bits can be set and never cleared |
| **Application LMS public key**, main | Ordinary | 56 | None | Auth, empty | Written at provisioning, then write-locked for good | Checking the public key carried in each production application package |
| **Application LMS public key**, backup | Ordinary | 56 | None | Auth, empty | Written at provisioning, then write-locked for good | A second key held offline in a separate HSM, so losing the main key does not end updates (R27). Never writable, so no bitstream can plant a key here |

Notes:

- **Authenticated reads for free.** Every `TPM2_NV_Read` runs in a session whose response HMAC covers the data returned, under a key only the pairing-key holder and the TPM share. Counter reads,
  key hashes and the lifecycle bits are therefore authenticated without any extra command, and a fresh `nonceTPM` in every exchange makes replay impossible. The ATECC608C's unauthenticated counters
  (the old R36) are gone: incrementing a counter now needs the pairing policy.
- **The pairing index's Name is fixed after provisioning.** A policy that refers to an NV index binds to its Name, which covers the public area including the *written* attribute, so the index is
  written and locked before any policy that mentions it is computed. Its authorization value is not part of the Name, which is exactly what lets the ratchet change the pairing key without
  touching any sealed object.
- **LMS public keys are stored whole.** A 56-byte LMS public key fits an index, so the loader compares the package's key against the stored key directly, no hash needed.

### Objects

Objects are created at provisioning under the **storage root key** (an ECC P-256 primary under the storage hierarchy, from the TCG standard template, made persistent) and the **attestation key**
under the endorsement hierarchy. Their private parts come back from the TPM as blobs, encrypted and integrity-protected by the TPM, and are stored twice in the flash records region
(`doc/flash.md`); the loader loads a blob with `TPM2_Load` when it needs the key. Sealed data objects release their contents with `TPM2_Unseal`; keyed-hash keys compute with `TPM2_HMAC`;
the attestation key signs with `TPM2_Quote`.

| Object | Kind | Per device | Policy (userWithAuth clear: policy only) | Used for |
|---|---|---|:-:|---|
| **Application key** | Sealed, 32 bytes | Yes | PolicySecret(pairing) | Deriving each install's image key for the loader and the application, with separate labels (`doc/xip.md`); the header and boot-record HMACs; wrapping stored records (hosts' public keys, sensor pairings) |
| **Data key** *h*, one per enrolled host | Sealed, 64 bytes: the data key and the host session secret S*h* | Yes | PolicySecret(pairing) **and** PolicySecret(host *h*) | User data on the MicroSD card for host *h*'s sessions, after derivation with the host data secret; S*h* = HMAC(H*h*, "session") derives the session key |
| **Distribution key** | Sealed, 32 bytes | No (fleet-wide) | PolicySecret(pairing) | Decrypting production application packages. Under the Code Secrecy Profile, the per-device package key instead |
| **Developer key** | Sealed, 32 bytes | Yes | PolicySecret(pairing) | Deriving the developer working key for the current epoch (`doc/roles.md`) |
| **Log key** | Sealed, 32 bytes | Yes | PolicySecret(pairing) | MACs and the hash chain of the security event log (R26) |
| **Symmetric identity key** | Keyed-hash, HMAC-SHA256, sign | Yes | PolicySecret(pairing) | Authenticating the device to the enrollment server and the server to the device, quantum-safe; the HSM derives it from the TPM's identifier. Never leaves the TPM: `TPM2_HMAC` computes, and the security block compares |
| **Attestation key (AK)** | ECDSA P-256, restricted signing, under the endorsement hierarchy | Yes | PolicySecret(pairing) | `TPM2_Quote` over the PCRs for hosts and third parties. Generated in the TPM at provisioning; its public key is certified by the manufacturer's device CA after the TPM's endorsement key certificate has been checked |
| **Endorsement key (EK)** | ECC P-256, ST-provisioned, with ST's certificate in NV | Yes | ST's standard EK policy | Proves the TPM is a genuine ST33KTPM2X; binds the AK to this TPM at enrollment (`TPM2_ActivateCredential`). The EK certificate's identifier is the device's hardware serial number |

Notes:

- **Sealed keys are released only under a policy**, never by an authorization value, and every policy contains PolicySecret(pairing): the TPM demands proof of the current pairing key in the
  same policy session before it unseals. A bitstream without the current key gets nothing.
- **Sealed data comes back encrypted and authenticated.** The unseal runs in a session with parameter encryption (AES-128-CFB under the session key) and a response HMAC, so a key altered on the
  SPI bus is detected rather than silently unwrapped to a wrong value. The ATECC608C's key check values and "encrypted reads carry no MAC" workaround are gone.
- **Blobs are not secrets.** A blob leaks nothing and cannot be used by another TPM; losing one costs a key, which is why they are stored twice and why the HSM can regenerate every per-device key
  from the TPM's identifier and re-seal it over a server session.
- **The private parts of the AK and EK never leave the TPM.** The symmetric identity key never leaves it either, which is one better than the ATECC608C's slot 12 gave: the TPM computes and the
  loader only compares.

### PCRs

The loader domain measures what it has checked into the SHA-256 bank:

| PCR | Extended by | With |
|---|---|---|
| 0 | Boot ROM | Report format version; bitstream release and pairing key version (from the key source); boot cause |
| 1 | Boot ROM | The loader image header: version, digest |
| 1 | Loader | The supervisor image header: version, digest |
| 2 | Loader | The application image header: version, mode (production, or developer with its epoch), digest |
| 3 | Loader | Network policy; counters 0, 1 and 2 as read; lockdown count and last cause from the boot record; lifecycle bits |
| 4 | Loader | Each ratchet step, install, and enrollment event as it happens |

A PCR can only be extended, never set, and all are zero after `TPM2_Startup`. What they hold is a measurement by the authenticated bitstream of what it checked; a compromised application cannot
alter them because it has no path to the TPM (R37, R45).

## Sessions

Every exchange with the TPM runs inside a TPM 2.0 **HMAC session** or **policy session**, started with `TPM2_StartAuthSession`. The security of the whole arrangement is in how the session key is formed:

- **Bound to the pairing index.** The loader's sessions are *bound* to the pairing index, so the session key is KDFa(pairing key ‖ salt, nonces) and every command HMAC and response HMAC in the
  session is under a key only the holder of the current pairing key can compute. The TPM's acceptance of the first command HMAC is the device proving its pairing key; the TPM's valid response HMAC
  is the TPM proving it holds the same one. That is the **pairing exchange**, and it is also what makes every NV read authenticated.
- **Unsalted.** A salt would add entropy independent of the pairing key, but encrypting one to a TPM key needs a public-key operation in the boot ROM (ECDH for an ECC key; RSA-2048
  OAEP with a pre-provisioned RSA key would be about seventeen modular multiplications in firmware, feasible if a laboratory asks for it). The pairing key is a 256-bit secret and both nonces
  are fresh, so the design does without; the station's sessions at provisioning are salted, because a fresh TPM shares no secret with it yet.
- **Parameter encryption** with the session's symmetric algorithm, **AES-128-CFB**, on the first parameter of a command or response: the sealed data an unseal returns, and the next pairing key a
  ratchet sends. Together with the response HMAC this is an approved key transport (AES plus HMAC, FIPS 140-3 IG D.G), which is what lets the loader domain be the FIPS module and the TPM a separate one
  (`doc/fips.md`). The TPM also offers XOR obfuscation with no cipher, but that is not an approved method (E12).
- **Nonces** from both sides in every round trip (`nonceTPM`, `nonceCaller`), so no exchange can be replayed.

KDFa is SP 800-108 in counter mode with HMAC-SHA256: the SHA-256 core already does it, with the pairing key on its key port (`doc/hw.md`, Key paths). The session key and the AES key it yields go into
key registers, never into software; the session cipher is a small unmasked AES-128 core in encrypt direction only (CFB decryption uses the forward cipher), keyed per session from the derive path,
so no key sees more than one session's traffic (`doc/hw.md`, Resource estimate).

### Commands the loader domain uses

| Need | Commands | Protection |
|---|---|---|
| Start-up | `TPM2_Startup(CLEAR)`; `TPM2_HierarchyControl(platform, disable)`; `TPM2_SelfTest` | Disabling the platform hierarchy first means that for the rest of the power cycle nobody can use the empty platform authorization the TPM boots with (below) |
| Pairing exchange | `TPM2_StartAuthSession` (HMAC, bound to the pairing index, salted); `TPM2_NV_Read` of the pairing index | First with the bitstream's own key, then its inherited key (ratchet below). The response HMAC authenticates the provisioning record |
| Counter read | `TPM2_NV_Read` in the pairing session | Authenticated by the response HMAC (replaces the old authenticated counter read, and closes R36) |
| Counter advance | Policy session; `TPM2_PolicySecret(pairing)`; `TPM2_NV_Increment` | Only the pairing-key holder can advance a counter |
| Release a key (application, distribution, developer, log) | `TPM2_Load` of the blob; policy session with PolicySecret(pairing); `TPM2_Unseal` with response encryption | Confidential and authenticated; decrypted by the session cipher straight into a key register |
| Release the data key for host *h* | As above, plus `TPM2_PolicySecret(host h)` authorized by the host's own HMAC (Host authentication, below) | The TPM itself decides; the loader only forwards bytes |
| Session key for a host or CLI session | S*h* from the same unseal, into the SHA-256 key input; derive mode over both nonces | The host derives the same key from its own H*h* |
| Attestation | `TPM2_PCR_Extend` as the chain runs; `TPM2_Load` of the AK blob; policy session with PolicySecret(pairing); `TPM2_Quote` over PCRs 0 to 4 with the verifier's nonce as qualifying data | Only a bitstream holding the pairing key can obtain a quote |
| Server authentication, time beacons | `TPM2_Load` of the identity key; `TPM2_HMAC` over the message; the security block compares with the server's MAC, or the result is sent | Symmetric, quantum-safe |
| Ratchet | Policy session with PolicyAuthValue and PolicyCommandCode(`NV_ChangeAuth`) under the current key; `TPM2_NV_ChangeAuth` with the next key as the encrypted parameter | Only the holder of the current key can install the next; the new key never crosses the bus in clear |
| Freshness, lifecycle | `TPM2_NV_Write`, `TPM2_NV_SetBits` in a policy session with PolicySecret(pairing) | |
| Random | `TPM2_GetRandom`, mixed into the DRBG as additional input | Two sources; the TPM's is on a CMVP certificate |

About fifteen commands in all, including the four policy commands (PolicySecret, PolicyAuthValue, PolicyCommandCode, PolicyPCR). Each is a fixed message layout, so the loader's marshalling code is
a table of formats rather than a TPM software stack; the Python reference model in `doc/test.md` produces the vectors it is tested against.

### The platform hierarchy and `TPM2_Clear`

A TPM boots with an **empty platform authorization**: anyone who talks to it first after reset could use the platform hierarchy to clear the TPM (which changes the storage seed and so kills
every sealed object) or redefine NV. Three things close that:

1. The TPM's `RST` is held low by a pull-down until the boot ROM drives it, so the TPM does not start until the authenticated bitstream is running.
2. The boot ROM's second command, right after `TPM2_Startup`, is `TPM2_HierarchyControl` disabling the platform hierarchy for the rest of the power cycle; it can only be re-enabled by a TPM reset.
   The platform *NV* enable stays set, so our platform-created indices remain usable.
3. `TPM2_ClearControl(disable)` is set at provisioning, so `TPM2_Clear` is refused even with the lockout authorization, until a provisioning station with the platform authorization re-enables it.

A board prober who drives `RST` and talks to the TPM before the FPGA can still clear it. That is denial of service, equivalent to desoldering the part, and is accepted (R36).

## Host authentication

The host proves itself **to the TPM, not to the loader**, exactly as the ATECC608C's CheckMac did, by supplying the HMAC for one TPM command:

1. The loader opens a policy session for the data key and satisfies PolicySecret(pairing) in it.
2. The loader starts a plain HMAC session (unbound, unsalted) for the host index and sends the host, over the UART or the network: the TPM's `nonceTPM`, the loader's own `nonceCaller`, and the
   inputs of the command parameter hash for `TPM2_PolicySecret(host h)` in the policy session (command code, the index's Name, the policy session's `nonceTPM`).
3. The host computes the command HMAC under H*h* (the HMAC key of an unbound, unsalted session is the entity's authorization value) and returns it.
4. The loader issues `TPM2_PolicySecret(host h)` with that HMAC. The TPM verifies it against the index's authorization value; a failure counts against the dictionary-attack lockout.
5. The loader unseals data key *h* under the completed policy.

The host never learns the pairing key; the loader never learns H*h*; and both nonces are fresh, so a recorded exchange is useless. The loader's own attempt limits and logging (R28) sit in front
of this relay, so a network attacker reaches the TPM rarely; the TPM's lockout (set to 32 tries and a ten-minute recovery at provisioning) is the second layer and affects host indices only, never the
pairing index. Because each host has its own index and its own sealed data key, authentication is identity-based, which is what FIPS 140-3 Level 3 asks for (E10 closed).

## The pairing-key ratchet

The configuration engine will load any bitstream that is correctly encrypted and signed, including an old release with a known bug; most FPGA families have no fuse to stop it.
So the design makes old bitstreams useless instead of unloadable: **each bitstream release has its own pairing key, and the TPM holds only the current one.**

| Where | Holds |
|---|---|
| Bitstream of release *N*, key source | The key it inherits, K(*N*−1), and its own key, K(*N*); the key version *N* in clear |
| TPM pairing index, authorization value | K(*N*) once release *N* has confirmed itself; K(*N*−1) until then |
| HSM | KDF(pairing master, TPM identifier, *N*) for any *N*; nothing is stored |

**Installing release *N*** (`doc/flash.md`, Install order):

1. The loader of release *N*−1 verifies the platform package, writes the new bitstream into the inactive bitstream slot and the new loader into the inactive loader slot,
   reads both back, advances counter 0, and points the boot record and the family's multi-boot at the new slots.
2. On the next power-up the configuration engine loads release *N*. Its boot ROM opens a session bound to the pairing index under K(*N*−1), which the new bitstream carries as its inherited key.
3. The loader of release *N* checks the loader and application images and starts the application: the new release has proved itself.
4. The loader then runs `TPM2_NV_ChangeAuth` on the pairing index, authorized by K(*N*−1) and carrying K(*N*) encrypted under the session, marks the install confirmed in the boot record, and from
   then on pairs with K(*N*).

**What this gives:**

- Release *N*−1's bitstream holds K(*N*−2) and K(*N*−1). After step 4 neither satisfies any policy in the TPM, so an attacker who loads it (through the configuration pins, a flash restore,
  or by corrupting the active slot to force the multi-boot fallback, R44) gets a device that can boot only into recovery: no keys, no data, no identity, no quote.
- **Nothing else changes.** Every sealed object's policy names the pairing index, not its authorization value, so a ratchet is one NV write and no blob is touched.
- **Power cuts are safe.** Before step 4 both releases hold K(*N*−1), so whichever the configuration engine loads works. `TPM2_NV_ChangeAuth` is one command, atomic in the TPM's NV;
  if power fails around it, the new release tries K(*N*) first and K(*N*−1) second at its next boot, so it recovers either way.
- **A release that fails to configure** (a bad write, a corrupt slot) leaves K(*N*−1) in place; the configuration engine falls back to release *N*−1, whose loader sees an unconfirmed
  install and marks the slot bad.
- **Skipping releases.** A device at release *N* that updates straight to release *M* needs a bitstream carrying K(*N*) and K(*M*). The build service already builds a bitstream per
  device, and the device reports its key version in every attestation and session, so the server builds the package from the version the device has. Offline packages are prepared the same way.
- **No eFuse budget.** Unlike version fuses, the ratchet has no limit on the number of releases.

Rollback of the loader alone (without a new bitstream) is caught by counter 0; of the application, by counter 1; of the supervisor, by counter 2.

## Counters

| Counter | Used for | Notes |
|---|---|---|
| 0 | Platform version: the bitstream and the loader under one version | Every platform package carries a loader image, restamped if unchanged, so the loader's version always matches counter 0. Bitstream rollback is also blocked by the ratchet |
| 1 | Application version, and the developer key epoch (epoch = counter 1 ÷ 1024, `doc/roles.md`) | Developer installs never touch it |
| 2 | Supervisor image version | The supervisor is manufacturer firmware outside the FIPS module, updated without a filing, so it has its own counter rather than sharing the platform's |

**Version rule:** a package is accepted if its version is **not older** than the counter. Equal is allowed, so a device can reinstall its current release, for example to repair a corrupted slot.
This is safe because each install uses a fresh install salt, so no nonce repeats (`doc/xip.md`).

**Advancing a counter:** `TPM2_NV_Increment` adds one per call. Moving a counter to a new version takes one increment per version step, up to 1,024 for a release that starts a new epoch, each
a short NV write. That is acceptable during an update, which already pauses for flash erases. A power cut partway through leaves the counter between the old and new versions; since the counter
only moves forward and the new image's version is not older than it, the device still boots the new image once the install completes, and still refuses anything older. The counters are 64 bits.
A TPM initializes a new counter index to at least the highest value any deleted counter ever reached, so deleting and recreating one (which the platform hierarchy lock prevents anyway) could not
roll it back.

**Counters are authenticated and authorized.** Reading runs in the pairing session; incrementing needs the pairing policy. Nothing on the bus can advance or forge a counter (the old R36 is closed).

## Attestation

The device can prove what it is and what it runs. The loader asks the TPM for a **quote**: `TPM2_Quote` under the attestation key over PCRs 0 to 4, with the verifier's nonce and the loader's
own as qualifying data. The quote is a TPM-formatted structure signed with ECDSA P-256, carrying the PCR digest, the TPM's firmware version and clock, and the qualifying data. With it the loader sends
the values it extended (so the verifier can recompute the PCR digest), the AK certificate from the manufacturer's device CA, and, on request, the EK certificate from ST.

| What the verifier learns | From |
|---|---|
| This is a genuine ST33KTPM2X | The EK certificate chain to ST's root, and the AK certificate that the device CA issued only after `TPM2_ActivateCredential` bound the AK to that EK |
| This is device *X*, enrolled by the manufacturer | The AK certificate |
| The quote is fresh | The verifier's nonce in the qualifying data |
| The bitstream holds the current pairing key | The AK's policy: the TPM signs only after PolicySecret(pairing) |
| Bitstream release, pairing version, boot cause | PCR 0 |
| Loader and application versions, mode, epoch | PCRs 1 and 2 |
| Counters, lockdown history, network policy, lifecycle | PCR 3 |
| What happened since boot | PCR 4 |

For the **enrollment server**, the same report is authenticated instead with `TPM2_HMAC` under the symmetric identity key, which the HSM derives from the TPM's identifier and checks directly;
that path is quantum-safe. The server may also ask for a quote, and verifies the AK through the device CA it runs itself.

The report is a measurement by the loader of what it has checked, under the configuration engine's authentication of the bitstream that contains the loader. A compromised application cannot
alter it, because the application has no path to the loader's state or to the TPM (R37, R45).

## User data freshness

Moving user data to the MicroSD card makes one attack easy: copy the card, and later put the old copy back. Every record still decrypts and authenticates,
because the data key has not changed, so the loader would accept data that has been rolled back (R10).

The freshness index is the defense: at the end of each host session that changed user data, the loader writes a digest of the data's current state (the root of a hash over its records, or a
session sequence number) into the index under the pairing policy. At the next session it compares the card with that digest and reports a mismatch to the host. The TPM's NV write endurance must
be checked against how often sessions change data (E7); the TPM's flash is error-corrected and its NV management is its own, so the figure to check is the one in ST's datasheet, not a raw cell count.

## Dictionary-attack protection

The TPM counts failed authorizations against entities that are not marked `NO_DA` and locks them out after `maxTries` failures for `recoveryTime` seconds (`TPM2_DictionaryAttackParameters`,
set at provisioning with the lockout authorization). The host indices are protected; the pairing index is not, because a 256-bit key gains nothing from a lockout and the device must always be
able to boot. A lockout therefore blocks host sessions for ten minutes and nothing else, and is logged. The lockout authorization is HSM-held, per device, and is never on the device.
Zeroization in the field is the ratchet to a random key, which the device performs itself (`doc/fips.md`); `TPM2_Clear` is a station operation, possible only after the station has re-enabled
clearing through the platform hierarchy on a TPM it holds in reset.

## Provisioning

At the enrollment station (`doc/enrollment.md`), over an SPI fixture or the FPGA's factory bitstream, with every secret in an encrypted, salted session whose salt is encrypted to the EK or
the storage root key (so only the genuine TPM whose certificate the station has just checked can read it):

1. `TPM2_Startup`; read the EK certificates from NV and check the chain to ST's root; the EK certificate's identifier becomes the device's hardware serial number, from which the HSM derives every per-device key.
2. `TPM2_Clear` to a known state; `TPM2_HierarchyChangeAuth` to set the owner, endorsement and lockout authorizations to HSM-derived values; `TPM2_DictionaryAttackParameters`.
3. Create the storage root key (`TPM2_CreatePrimary`, standard ECC template) and make it persistent (`TPM2_EvictControl`).
4. Define the NV indices in the table, platform-created; write the provisioning record into the pairing index with K(0) as its authorization value, the host indices for the hosts enrolled at
   the factory (if any), the LMS public keys; write-lock what the table says is locked.
5. Create the sealed objects with HSM-derived contents and the policies in the table (each policy digest computed from the Names of the written indices), and the symmetric identity key;
   store the blobs in the flash records region.
6. Create the AK under the endorsement hierarchy, read its public part, prove it belongs to this TPM (`TPM2_MakeCredential` on the station, `TPM2_ActivateCredential` on the TPM), and obtain
   its certificate from the device CA; store the certificate with the blobs.
7. `TPM2_ClearControl(disable)`; then the station's last act is to drop the platform hierarchy (`TPM2_HierarchyControl`), as the boot ROM will at every later boot.

The lifecycle bits start clear and the freshness index empty. Counters start at zero (or at the TPM's floor for new counters, which the version rule tolerates).

## Decisions to freeze before locking

The NV layout and the policies are fixed once the platform hierarchy is locked in the field, so these must be settled first, on real parts:

1. The policy digests and the Name-binding of the pairing and host indices, including the NV_ChangeAuth policy the ratchet depends on and the two-PolicySecret policy of the data key (E5).
2. That the ST33KTPM2X accepts the bound, encrypted session configuration above with AES-128-CFB, and the command set in the table, in the FIPS-approved configuration its Security Policy describes (E5, E12).
3. Freshness index write endurance against the session rate (E7).
4. The order code against the certificate's hardware and firmware list, and the sourcing route (E6, E8).
5. NV budget: eight host indices plus the rest is well under 2 KB, and the blobs are in flash; confirm against the part's NV capacity and persistent-object limits (E5).
