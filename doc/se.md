# Secure Element Slot Map

This document lays out the ATECC608B's slots, counters and access rules for `thriller`. It is a proposal: every access rule must be
confirmed against cryptoauthlib's configuration structures and tested on real parts before the configuration zone is locked,
because a locked configuration cannot be changed (`doc/arch.md`, Open Questions 2 and 8). The same map applies to the MOD8ID if
its compatibility claim holds.

Microchip's TrustFLEX layout, suggested earlier as a starting point, is built around ECC private keys and certificates that this design
no longer uses. `thriller` needs a custom configuration (TrustCUSTOM, or blank parts configured at provisioning).

## Slots

The ATECC608B has 16 slots: slots 0 to 7 hold 36 bytes, slot 8 holds 416 bytes, and slots 9 to 15 hold 72 bytes.
All keys below are 32-byte symmetric keys (key type "SHA/other"); none is an ECC key.

| Slot | Size | Contents | Per device | Read | Write after lock | Used for |
|---|---|---|:-:|---|---|---|
| 0 | 36 | **Pairing key** | Yes | Never | Encrypted write, authorized by slot 0 itself (FPGA: rotated with each platform update) | MAC key for every authenticated read and counter read; the encryption key for every encrypted read (it is the ReadKey of slots 2 to 6) |
| 1 | 36 | **Host authorization key** | Yes | Never | Never | CheckMac of the host's response; the authorization key (AuthKey) of slot 3 |
| 2 | 36 | **Application key** | Yes | Encrypted read under slot 0 | Never | Deriving each install's image key (`doc/xip.md`); the header HMAC |
| 3 | 36 | **Data key** | Yes | Encrypted read under slot 0, **only after CheckMac with slot 1** | Never | User data on the MicroSD card, for one host session |
| 4 | 36 | **Distribution key** | No (fleet-wide) | Encrypted read under slot 0 | Never | Decrypting application packages. Under the Code Secrecy Profile, the per-device package key goes here instead |
| 5 | 36 | **Developer key** | Yes | Encrypted read under slot 0 | Never | Deriving the developer working key for the current epoch (`doc/roles.md`) |
| 6 | 36 | **Log key** | Yes | Encrypted read under slot 0 | Never | MACs and the hash chain of the security event log (R24) |
| 7 | 36 | *Reserved:* **device identity key** | Yes | Never | Never | Device-to-host authentication with the MAC command, used in place (`doc/fda.md`, gap 2) |
| 8 | 416 | **Provisioning record** | Yes | Clear, authenticated (GenDig over the slot, then MAC under slot 0) | Never | Configuration version, provisioning batch and date, the board's FPGA identity (TraceID on the ECP5) for traceability |
| 9 | 72 | **Application LMS public key** (56 bytes) | No | Clear, authenticated | Never | Verifying production application packages |
| 10 | 72 | *Reserved:* **next application LMS public key** | No | Clear, authenticated | Encrypted write, authorized by slot 0 | Rolling over to a new LMS key when the current one runs low on signatures, or on a change of application owner (Open Question 6) |
| 11 | 72 | *Reserved:* **user data freshness** | Yes | Clear, authenticated | Encrypted write, authorized by slot 0 | A digest of the latest user data, to detect an old copy of the card being restored (see below) |
| 12 to 15 | 72 | Spare | — | — | — | Lifecycle state on the ASIC (`doc/ics55.md`), future keys |

Notes:

- **"Never" readable means never.** The pairing, host authorization and device identity keys are only ever used inside the secure element.
  The other keys leave it only by encrypted read, and they go into the AES key registers or the SHA-256 key input in the fabric, never into software (`doc/hw.md`, Key paths).
- **Every encrypted and authenticated read requires a fresh nonce** that includes the loader's own random value (`doc/arch.md`, Loader nonce source),
  so a recorded exchange cannot be replayed.
- **Slots that are never written after lock** should also be individually locked, where the slot configuration allows it, so a configuration mistake
  cannot make them writable later.
- **The public key slots are not secret,** but they are read with authentication so that a device on the I2C bus cannot substitute its own key.

## Counters

| Counter | Used for | Notes |
|---|---|---|
| 0 | Platform (bitstream) anti-rollback on the FPGA; the updatable loader on the ASIC (`doc/ics55.md`) | |
| 1 | Application anti-rollback, and the developer key epoch (epoch = counter 1 ÷ 1024, `doc/roles.md`) | Developer installs never touch it |

**Version rule:** a package is accepted if its version is **not older** than the counter. Equal is allowed, so a device can reinstall its current release,
for example to repair a corrupted slot. This is safe because each install uses a fresh image key (`doc/xip.md`, Nonce uniqueness).

**Advancing a counter:** as far as the public documentation shows, the Counter command increments by one per call. Moving a counter to a new version
therefore takes one increment per version step, up to 1,024 for a release that starts a new epoch, each a short write to the secure element's
non-volatile memory. That is acceptable during an update, which already pauses for flash erases. A power cut partway through leaves the counter
between the old and new versions; since the counter only moves forward and the new image's version is not older than it, the device still
boots the new image once the install completes, and still refuses anything older.

Both counters are allocated, so neither is available to limit how many times a key can be used. If a host key is ever derived from a short PIN,
attempts must be limited another way (`doc/arch.md`, Open Question 8).

## User data freshness

Moving user data to the MicroSD card makes one attack easy: copy the card, and later put the old copy back. Every record still decrypts and authenticates,
because the data key has not changed, so the loader would accept data that has been rolled back. The same attack was possible with user data in QSPI flash,
but it took a flash programmer instead of a card reader.

Slot 11 is reserved for a defense: at the end of each host session that changed user data, the loader writes a digest of the data's current state (for example,
the root of a hash over its records, or a session sequence number) into slot 11 with an encrypted write. At the next session it compares the card with that digest.
Whether this is needed depends on the application, and the secure element's write endurance must be checked against how often sessions change data
(`doc/arch.md`, Open Question 12).

## Configuration zone

Settings outside the slots, to be specified with the access rules above:

- I2C address (the default unless the board needs another).
- KeyConfig for each slot: key type, IsSecret, the ReadKey and WriteKey assignments in the table, ReqRandom (nonce required), ReqAuth and AuthKey for slot 3.
- SlotConfig for each slot: read and write modes as in the table.
- Chip options: anything not used (ECC, KDF output to the bus) left off.
- Lock order: configuration zone first, then the data zone after all keys are written, then individual slot locks.

## Provisioning

The slot contents come from the HSM, derived as KDF(master key, secure element serial number) for every per-device key (`doc/arch.md`, Provisioning;
`doc/fda.md`, section 4.5). Slot 4 receives the fleet-wide distribution key, and slot 9 the application owner's LMS public key.
Reserved slots are left empty, with write access configured as in the table so they can be filled later.
