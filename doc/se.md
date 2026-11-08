# Secure Element

The ATECC608B holds what the FPGA cannot keep for itself: per-device keys, the device's identity, and two monotonic counters. This document lays out its slots,
the protocol between the loader domain and the secure element, the pairing-key ratchet that kills superseded bitstreams, attestation, and the configuration that
must be frozen before the part is locked. It is a proposal: every access rule must be confirmed against cryptoauthlib's configuration structures and tested on real parts
before the configuration zone is locked, because a locked configuration cannot be changed (`doc/questions.md`, E5).

## Part

- **ATECC608B**, I2C, UDFN or SOIC, on a bus that stays inside the sealed enclosure (R36). Certified tamper-resistant (JIL high).
- **Custom configuration.** Microchip's TrustFLEX layout is built around ECC keys and TLS certificates; this design is mostly symmetric. Use TrustCUSTOM (Microchip provisions the
  configuration and keys from a definition the manufacturer supplies through the Trust Platform) or blank parts configured at enrollment (`doc/enrollment.md`). Either way, every per-device
  key is derived in the HSM from the part's serial number, so the database holds no key material.
- **Second source.** Pin-compatible parts that claim command compatibility exist; one must be qualified against this slot map before it is accepted (open question E6).
- **Who talks to it.** Only the loader core domain, through the I2C master in `doc/hw.md`. The boot ROM runs the pairing exchange and the counter 0 read; the loader runs everything else.
  Neither core ever sees a key: the SHA-256 core takes the pairing key straight from the key source, and unwrapped keys go straight into key registers (`doc/hw.md`, Key paths).

## Slots

The ATECC608B has 16 slots: slots 0 to 7 hold 36 bytes, slot 8 holds 416 bytes, and slots 9 to 15 hold 72 bytes. Symmetric keys are 32 bytes (key type "SHA/other").

| Slot | Size | Contents | Per device | Read | Write after lock | Used for |
|---|---|---|:-:|---|---|---|
| 0 | 36 | **Pairing key** (also the I/O protection key) | Yes, and per bitstream release | Never | Encrypted write, authorized by slot 0 itself | MAC key for every authenticated read and counter read; ReadKey of slots 2 to 6; AuthKey of slot 7; encrypts KDF output. Rotated by the ratchet below |
| 1 | 36 | **Host authorization key** | Yes | Never | Never | CheckMac of the host's response; AuthKey of slot 3; KDF source for the session key |
| 2 | 36 | **Application key** | Yes | Encrypted read under slot 0 | Never | Deriving each install's image key for the loader and the application, with separate labels (`doc/xip.md`); the header and boot-record HMACs; wrapping stored records (hosts' public keys, sensor pairings) |
| 3 | 36 | **Data key** | Yes | Encrypted read under slot 0, **only after CheckMac with slot 1** | Never | User data on the MicroSD card, for one host session |
| 4 | 36 | **Distribution key** | No (fleet-wide) | Encrypted read under slot 0 | Never | Decrypting production application packages. Under the Code Secrecy Profile, the per-device package key goes here instead |
| 5 | 36 | **Developer key** | Yes | Encrypted read under slot 0 | Never | Deriving the developer working key for the current epoch (`doc/roles.md`) |
| 6 | 36 | **Log key** | Yes | Encrypted read under slot 0 | Never | MACs and the hash chain of the security event log (R26) |
| 7 | 36 | **Device identity key, ECDSA P-256 private** | Yes | Never | Never | Sign command, only after CheckMac with slot 0 (ReqAuth): attestation reports (below). Generated on chip at provisioning; its public key is certified by the manufacturer's CA |
| 8 | 416 | **Key check values** (first 32 bytes), **provisioning record**, **device certificate** | Yes | Clear; the first 32 bytes authenticated (GenDig covers 32 bytes, then MAC under slot 0) | Never | 16-byte check values for the data key and the distribution key (`doc/hw.md`, Encrypted reads carry no MAC); configuration version, provisioning batch and date; the compressed device certificate (72 bytes) and the signer certificate's identifier |
| 9 | 72 | **SHA-256 of the application LMS public key** (32 bytes) | No | Clear, authenticated | Never | Checking the public key carried in each production application package |
| 10 | 72 | **SHA-256 of the backup application LMS public key** | No | Clear, authenticated | Never | A second key, provisioned at the factory and held offline in a separate HSM, so losing the main key does not end updates (R27). Never writable, so no bitstream can plant a key here |
| 11 | 72 | **User data freshness** | Yes | Clear, authenticated | Encrypted write, authorized by slot 0 | A digest of the latest user data, to detect an old copy of the card being restored (R10) |
| 12 | 72 | **Device identity key, symmetric** | Yes | Never | Never | MAC command, used in place: authenticating the device to the enrollment server and the server to the device, quantum-safe; the HSM derives it from the serial number |
| 13 | 72 | **Lifecycle and enrollment state** | Yes | Clear, authenticated | Encrypted write, authorized by slot 0 | Enrollment complete, retired, wiped; on the ASIC also the PUF enrollment state (`doc/ics55.md`) |
| 14, 15 | 72 | Spare | — | — | — | Future keys |

Notes:

- **"Never" readable means never.** The pairing, host authorization and both identity keys are only ever used inside the secure element.
  The other keys leave it only by encrypted read, into key registers in the fabric, never into software.
- **Every encrypted and authenticated read requires a fresh nonce** that includes the loader's own random value (below), so a recorded exchange cannot be replayed.
- **Slot 0 requires a random nonce for every use** (ReqRandom). Without it, a device on the bus could load a chosen TempKey and have the secure element MAC it under the pairing key,
  a MAC oracle that would forge counter reads.
- **Slot 0 is the I/O protection key.** The KDF command's output for the session key is encrypted under it, and so is any command the design needs encrypted on the bus.
- **The public key slots hold hashes, not keys.** GenDig covers only 32 bytes of a slot, so a 56-byte LMS public key could not be authenticated in place; its SHA-256 hash can.
- **Slots that are never written after lock** are also individually locked, where the slot configuration allows it.
- **Slot 7's private key never leaves the part.** It is generated on chip (GenKey) at provisioning and its public key exported once for certification; the host authorization key (slot 1)
  is likewise never writable, so a compromised host means retiring the device (R20).

## Protocol between the loader domain and the secure element

All messages follow the ATECC608B command set as cryptoauthlib implements it. The pairing key enters every computation through the SHA-256 core's key port, from the key source,
and the result goes to a comparator or a key register, so the Forth code on the loader core handles only ciphertext, nonces and MACs.

| Need | Commands | Protection |
|---|---|---|
| Fresh nonce | Nonce (random mode): the secure element returns its random, the loader supplies its own 20 bytes from the TRNG; both go into TempKey | Neither side can choose the nonce alone |
| Authenticated read of a clear slot (counters, slots 8 to 11, 13) | Read; then Nonce, GenDig (slot 0), MAC over the data; compare in the security block | Forged or replayed data fails the MAC |
| Counter read | Counter (read); then MAC under slot 0 with the counter value in the message | As above. Counter increments are not protected (R36) |
| Encrypted read of a key (slots 2 to 6) | Nonce, GenDig (slot 0), Read; the key arrives XORed with TempKey, and the SHA-256 core removes the mask straight into a key register | Confidential on the bus; **not** authenticated, so every unwrapped key is checked before use (`doc/hw.md`) |
| Release the data key | The host's CheckMac against slot 1 over the current nonce; then the encrypted read of slot 3 | The secure element itself decides; the loader only forwards bytes |
| Session key for a host or CLI session | KDF (slot 1, PRF mode) over both nonces, output encrypted under slot 0, unwrapped into the session key register | The host derives the same key from its copy of the host authorization key |
| Attestation signature | Nonce (pass-through of the report digest), CheckMac against slot 0 (ReqAuth), Sign (slot 7) | Only a bitstream holding the pairing key can obtain a signature |
| Server authentication | MAC (slot 12) over the report digest; and CheckMac (slot 12) of the server's response | Symmetric, quantum-safe |
| Ratchet | Nonce, GenDig (slot 0), Write (slot 0, encrypted): the next pairing key XORed with TempKey, with the data MAC | Only the holder of the current key can install the next |
| Freshness, lifecycle | Encrypted Write (slots 11, 13) as above | |
| Random | Random, mixed into the TRNG's conditioner | Two sources |

The authenticated reads and the CheckMac flows are exactly the ones in cryptoauthlib; the fabric reproduces them with its SHA-256 core instead of a host library.

### Encrypted reads carry no MAC

An encrypted read (Nonce, GenDig, Read, XOR with TempKey) is not authenticated: a key altered on the I2C bus unwraps to a wrong value without any error. Every unwrapped key is
therefore checked before it is trusted:

- the application key, by the loader header HMAC it must reproduce;
- the developer key, by the developer package MAC it must reproduce;
- the log key, by the existing log chain it must reproduce;
- the data key and the distribution key, by key check values: a MAC of a fixed string under each key, written at provisioning into the first 32 bytes of slot 8, which an authenticated read covers.

## The pairing-key ratchet

The configuration engine will load any bitstream that is correctly encrypted and signed, including an old release with a known bug; most FPGA families have no fuse to stop it.
So the design makes old bitstreams useless instead of unloadable: **each bitstream release has its own pairing key, and the secure element holds only the current one.**

| Where | Holds |
|---|---|
| Bitstream of release *N*, key source | The key it inherits, K(*N*−1), and its own key, K(*N*); the key version *N* in clear |
| Secure element slot 0 | K(*N*) once release *N* has confirmed itself; K(*N*−1) until then |
| HSM | KDF(pairing master, serial number, *N*) for any *N*; nothing is stored |

**Installing release *N*** (`doc/flash.md`, Install order):

1. The loader of release *N*−1 verifies the platform package, writes the new bitstream into the inactive bitstream slot and the new loader into the inactive loader slot,
   reads both back, advances counter 0, and points the boot record and the family's multi-boot at the new slots.
2. On the next power-up the configuration engine loads release *N*. Its boot ROM pairs with the secure element using K(*N*−1), which the new bitstream carries as its inherited key.
3. The loader of release *N* checks the loader and application images and starts the application: the new release has proved itself.
4. The loader then writes K(*N*) into slot 0 with an encrypted write authorized by K(*N*−1), marks the install confirmed in the boot record, and from then on pairs with K(*N*).

**What this gives:**

- Release *N*−1's bitstream holds K(*N*−2) and K(*N*−1). After step 4 neither opens the secure element, so an attacker who loads it (through the configuration pins, a flash restore,
  or by corrupting the active slot to force the multi-boot fallback, R44) gets a device that can boot only into recovery: no keys, no data, no identity.
- **Power cuts are safe.** Before step 4 both releases hold K(*N*−1), so whichever the configuration engine loads works. The encrypted write in step 4 is one command;
  if power fails during it, the new release tries K(*N*) first and K(*N*−1) second at its next boot, so it recovers either way.
- **A release that fails to configure** (a bad write, a corrupt slot) leaves K(*N*−1) in place; the configuration engine falls back to release *N*−1, whose loader sees an unconfirmed
  install and marks the slot bad.
- **Skipping releases.** A device at release *N* that updates straight to release *M* needs a bitstream carrying K(*N*) and K(*M*). The build service already builds a bitstream per
  device, and the device reports its key version in every attestation and session, so the server builds the package from the version the device has. Offline packages are prepared the same way.
- **No eFuse budget.** Unlike version fuses, the ratchet has no limit on the number of releases.

Rollback of the loader alone (without a new bitstream) is caught by counter 0; of the application, by counter 1.

## Counters

| Counter | Used for | Notes |
|---|---|---|
| 0 | Platform version: the bitstream and the loader under one version | Every platform package carries a loader image, restamped if unchanged, so the loader's version always matches counter 0. Bitstream rollback is also blocked by the ratchet |
| 1 | Application version, and the developer key epoch (epoch = counter 1 ÷ 1024, `doc/roles.md`) | Developer installs never touch it |

**Version rule:** a package is accepted if its version is **not older** than the counter. Equal is allowed, so a device can reinstall its current release, for example to repair a corrupted slot.
This is safe because each install uses a fresh install salt, so no nonce repeats (`doc/xip.md`).

**Advancing a counter:** the Counter command increments by one per call. Moving a counter to a new version takes one increment per version step, up to 1,024 for a release that starts
a new epoch, each a short write to the secure element's non-volatile memory. That is acceptable during an update, which already pauses for flash erases. A power cut partway through
leaves the counter between the old and new versions; since the counter only moves forward and the new image's version is not older than it, the device still boots the new image once the
install completes, and still refuses anything older. Each counter counts to 2,097,151.

**Counters are not protected.** The Counter command takes no authentication. Anything on the I2C bus can advance a counter, and a counter pushed past the installed versions, or to its
maximum, bricks the device for good (R36). The design accepts this: the bus is inside the seal, and the loader reports a counter far above the installed versions as a fault so the cause is visible.
Both counters are allocated, so neither is available to limit how many times a key can be used; CheckMac attempt limits are enforced by the loader (R28).

## Attestation

The device can prove what it is and what it runs. The loader builds a **report**:

| Field | Source |
|---|---|
| Report format version | Constant |
| Secure element serial number | Read at boot |
| Pairing key version | Key source (clear field) |
| Bitstream release and loader version | Boot ROM constant; loader header |
| Application version and mode | Application header: production, or developer with its epoch |
| Counter 0, counter 1 | Authenticated counter reads |
| Lockdown count, last lockdown cause | Boot record |
| Enrollment and lifecycle state | Slot 13 |
| Radio policy | Application header |
| Verifier's nonce; loader's nonce | The request; the TRNG |

and has the secure element sign its SHA-256 digest in one or both ways:

- **For the enrollment server:** MAC under the symmetric identity key (slot 12). The HSM derives the same key from the serial number, so the server checks it directly. Quantum-safe.
- **For hosts and third parties:** ECDSA P-256 under the device identity key (slot 7), checked against the device certificate in slot 8 and the manufacturer's signer and root certificates.
  Signing requires a prior CheckMac against slot 0, so only a bitstream that holds the current pairing key can obtain a signature: the report therefore attests the pairing and the bitstream
  release, not only the loader's claims.

The report is a measurement by the loader of what it has checked, under the configuration engine's authentication of the bitstream that contains the loader. A compromised application cannot
alter it, because the application has no path to the loader's state or to the secure element (R37, R45).

## User data freshness

Moving user data to the MicroSD card makes one attack easy: copy the card, and later put the old copy back. Every record still decrypts and authenticates,
because the data key has not changed, so the loader would accept data that has been rolled back (R10).

Slot 11 is the defense: at the end of each host session that changed user data, the loader writes a digest of the data's current state (the root of a hash over its records, or a session
sequence number) into slot 11 with an encrypted write. At the next session it compares the card with that digest and reports a mismatch to the host. The secure element's write endurance must be
checked against how often sessions change data (open question E7).

## Configuration zone

Settings outside the slots, to be specified with the access rules above:

- I2C address (the default unless the board needs another).
- KeyConfig for each slot: key type (SHA for 0 to 6 and 11 to 13; P-256 private for 7), IsSecret, the ReadKey and WriteKey assignments in the table, ReqRandom on slot 0 and 7, ReqAuth and AuthKey for slots 3 and 7.
- SlotConfig for each slot: read and write modes as in the table.
- ChipOptions: I/O protection key = slot 0; KDF output encryption required; anything unused left off.
- Lock order: configuration zone first, then the data zone after all keys are written, then individual slot locks.

## Decisions to freeze before locking

The configuration zone cannot change once locked, so these must be settled first, on real parts:

1. The access rules in the slot table, including ReqRandom on slot 0, ReqAuth with AuthKey on slots 3 and 7, and the encrypted write on slot 0 that the ratchet depends on (E5).
2. That the KDF command can take slot 1 as its source with encrypted output, and that the output is usable as a session key (E5).
3. Slot 11 write endurance against the session rate (E7).
4. The second-source part, if one is wanted (E6).
5. Chip options and the lock order.

## Provisioning

Slot contents come from the HSM, derived as KDF(master, serial number) for every per-device symmetric key; slot 7 is generated on chip and certified; slot 4 receives the fleet-wide distribution key;
slots 9 and 10 the hashes of the application owner's LMS public keys; slot 8 the check values, the record and the device certificate (`doc/enrollment.md`).
Slots 11 and 13 start empty, with write access configured as in the table.
