# The Module's Service API

The loader domain is the FIPS 140-3 cryptographic module, and this document is its interface: every message the module accepts and emits, in two layers.
Because the module is frozen at validation (`doc/fips.md`, Designing for few filings), this is the document to get right before the loader is coded (H9); afterwards,
adding a message is a module firmware change and waits for a platform release that was going to be filed anyway.

| Layer | Between | Carried by | Who parses |
|---|---|---|---|
| **Mailbox API** | The supervisor and application cores ↔ the module | Mailboxes A and B (`doc/hw.md`) | The module's message parser (R45) |
| **Session API** | A host, the server or a developer tool ↔ the module | Session frames the supervisor shuttles, opaque to it | The module, after decrypting a frame |

The CLI's command set, the transports, DHCP and everything the supervisor and application do with the plaintext they receive are **not** part of either layer and change freely.

## Conventions

- All integers are little-endian; all structures are 4-byte aligned; reserved fields are zero and are checked to be zero.
- A **message** is a header and a payload. Requests travel in a mailbox's request ring, responses and events in its response ring. Rings are in a dual-port message RAM: mailbox A has 8 KB
  per ring (it carries frames, package chunks, manifests, segment headers and sensor certificates), mailbox B 1 KB per ring. A message never wraps; the producer pads to the end of the ring and starts over.
- `MAX_PAYLOAD` is 4096 bytes on mailbox A and 256 bytes on mailbox B. The limits below were sized against the cryptography they carry: an LMS signature with SHA-256/32-byte parameters and
  height 10 is 1,452 bytes and a two-level HSS signature about 2.9 KB; an ML-KEM-768 ciphertext is 1,088 bytes; an ML-DSA-44 public key and signature are 1,312 and 2,420 bytes. Anything larger
  than one message is carried in numbered parts, and the rule for each is stated with the message.
- Every field has a fixed limit, checked before use; a message that fails any check is answered with an error and has no other effect. The parser is fuzzed on the software platform (`doc/test.md`).
- The module answers every request, in order, with exactly one response; it never blocks the ring on a slow operation (a TPM command, a flash erase) but answers `BUSY` or `PENDING` and finishes with an event.

### Message header (8 bytes)

| Offset | Size | Field | Meaning |
|---|---|---|---|
| 0 | 2 | `len` | Payload length in bytes |
| 2 | 1 | `op` | Operation code (tables below). In a response, the request's `op`; in an event, an `EVT_*` code |
| 3 | 1 | `status` | Zero in a request. In a response, a status code (below). In an event, zero |
| 4 | 4 | `tag` | Chosen by the requester and echoed in the response; events carry `0xFFFFFFFF` |

### Status codes

| Code | Name | Meaning |
|---|---|---|
| 0 | `OK` | |
| 1 | `BAD_LEN` | Length outside the message's fixed limits |
| 2 | `BAD_OP` | Unknown operation, or one not offered on this mailbox |
| 3 | `BAD_ARG` | A field outside its limits, or a reserved field not zero |
| 4 | `DENIED` | The caller or the current state does not permit this service (no session open, wrong session kind, wrong mailbox) |
| 5 | `BUSY` | Another operation of this kind is in progress (one install, one segment, one session per kind) |
| 6 | `PENDING` | Accepted; completion comes as an event with the same `tag` |
| 7 | `VERIFY_FAIL` | A signature, MAC, tag or certificate check failed |
| 8 | `VERSION_OLD` | A version older than its counter, or an API major version the module does not speak |
| 9 | `TPM_FAIL` | The TPM returned an error; `detail` carries the TPM response code |
| 10 | `FAULT` | The module is in the error state (self-test failure, lockdown pending); only `STATUS` is served |
| 11 | `NO_SPACE` | A record, log or slot is full |
| 12 | `TIMEOUT` | A multi-step exchange was not completed within its step budget and was discarded |

Responses with a non-zero status carry a 4-byte `detail` and nothing else.

### Versioning

`HELLO` returns the API version as `major.minor`. A change that alters an existing message's format or meaning increments `major`; adding a message or an optional trailing field increments
`minor`. The supervisor and application refuse to run against a `major` they do not know, and ignore trailing bytes beyond the fields they know. The module ignores `op` values it does not know
with `BAD_OP`, so a newer supervisor can probe. Both version numbers are part of the module's version string in the Security Policy.

## Mailbox API

Callers: **S** = supervisor (mailbox A), **A** = application (mailbox B). "Host session" means one is open; "server session" likewise. The module serves one host session, one server session
and one developer session at a time, one install, one recording segment.

### Status and control

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x01 | `HELLO` | S, A | — | `api_major` u8, `api_minor` u8, `mailbox` u8 (A or B), reserved u8; `module_version` 16 bytes (string) |
| 0x02 | `STATUS` | S, A | — | The status block (below) |
| 0x03 | `RANDOM` | S, A | `n` u16 ≤ 64 | `n` bytes from the DRBG |
| 0x04 | `POWER_RELEASE` | S | reserved u32 | `OK` and the module drops WAKE within 10 ms, or `BUSY` with `detail` = 1 (segment open), 2 (install in progress), 3 (TPM operation in flight) |
| 0x05 | `TIME_HINT` | S | `local_time` u64 (seconds), `source` u8 (RTC, host, server) | `OK`. Untrusted local time, used only to label log entries and the status block; never for recordings (R47) |

**Status block** (fixed layout, 128 bytes): module, supervisor and application versions (u32 each) and the platform (bitstream) release (u32); pairing key version (u32); counters 0, 1, 2 (u64 each);
build mode (u8: production, developer with epoch u16); approved-mode indicator (u8, always 1 in this module); self-test state (u8: passed, running, failed with the failing test in `fault_code`);
fault code (u16); lockdown count (u16) and last lockdown cause (u8); lifecycle bits (u8: enrolled, retired, wiped); network policy as read from the application header (u8); session state
(u8 bit field: host, server, developer open; host slot u8); segment state (u8); install state (u8); TPM state (u8: not started, started, platform hierarchy disabled, lockout active);
boot cause (u8); latest verified beacon time (u64, zero if none) and the sample count at that beacon (u64). The UART status report in recovery is the same block, in hexadecimal.

### Sessions

A session is opened in steps: the module produces a handshake message, the supervisor delivers it to the peer over whatever transport it uses, returns the peer's answer, and so on until the
module says the session is open. The supervisor never interprets handshake messages; the host relay for the TPM (`doc/tpm.md`, Host authentication) is simply two of these steps. Each step
has a budget of `STEP_TIMEOUT` (30 s, a fixed parameter) measured by the module's own tick; a late answer closes the attempt and counts toward the attempt limit (R28).

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x10 | `SESSION_OPEN` | S | `kind` u8 (1 host, 2 server, 3 developer), `transport` u8 (UART, network), `slot_hint` u8 (host slot, or 0xFF unknown), reserved u8, `peer_hello` (the peer's first message, ≤ 256 bytes) | `handshake_out` (≤ 512 bytes) to deliver to the peer, and `state` u8 (continuing, open, refused) |
| 0x11 | `SESSION_STEP` | S | `kind` u8, reserved ×3, `peer_msg` (≤ 512 bytes) | As above |
| 0x12 | `FRAME_IN` | S | `kind` u8, reserved ×3, `frame` (ciphertext, ≤ 1472 bytes) | `OK` and zero or more plaintext **session messages for the supervisor** (below), concatenated, each with its own 4-byte length prefix; messages the module consumes itself (key material, lifecycle, beacons) are not returned. `VERIFY_FAIL` on a bad tag or counter; after `MAX_BAD_FRAMES` (8) the session closes |
| 0x13 | `FRAME_OUT` | S | `kind` u8, reserved ×3, one or more plaintext messages with length prefixes (≤ 1400 bytes total) | `frame` (ciphertext) to send |
| 0x14 | `SESSION_CLOSE` | S | `kind` u8 | `OK`; keys for that session cleared |
| 0x15 | `SESSION_INFO` | S, A | `kind` u8 | `open` u8, `slot` u8, `peer_id` 16 bytes (host or server identifier, public), `frames_in` u32, `frames_out` u32 |

Frames carry a 32-bit counter per direction; a frame with a counter not greater than the last accepted one is dropped (R9). The ack-and-window layer that makes transfers reliable over UDP
is inside the plaintext (the supervisor sees acks as session messages and schedules retransmissions), so the module's frame format has no retransmission logic.

### User data (application, host session open)

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x20 | `RECORD_ENCRYPT` | A | `type` u16, `id` u32, `plaintext` (≤ 192 bytes) | `record` (ciphertext with header and tag, ≤ 240 bytes) to store on the card; the module updates its running freshness digest |
| 0x21 | `RECORD_DECRYPT` | A | `record` (≤ 240 bytes) | `type`, `id`, `plaintext`; `VERIFY_FAIL` if the tag fails or the record belongs to another host slot |
| 0x22 | `FRESH_CHECK` | A | `index_record` (the card's index record, ≤ 240 bytes) | `OK` if its chain head equals the TPM's freshness index; `VERIFY_FAIL` otherwise (R10). Called once when a session opens |
| 0x23 | `FRESH_COMMIT` | A | — | The module writes the running digest into the TPM freshness index (`PENDING`, then `EVT_DONE`) and returns the new `index_record` to store. Called when a session that changed data ends |

Records are Ascon-AEAD128 under the host's derived data key with `type`, `id` and the host slot in the associated data; the module never sees the card, only records. Developer sessions use the
developer data key and the same messages (`doc/roles.md`).

### Recording

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x30 | `SEG_START` | A | `recipients` u8 (1 to 4) and their record ids (u32 each), `channels` u8, `rate_code` u8, `app_meta` (≤ 64 bytes, carried in the header) | `PENDING`; then `EVT_SEG_HEADER` to the supervisor with the authenticated segment header, in numbered parts of ≤ 4096 bytes (the header is about 1.2 KB per recipient, so up to two parts), and `EVT_DONE` to the application; the sample FIFO opens |
| 0x31 | `SEG_STOP` | A | — | The engine finishes the last block; `EVT_SEG_TRAILER` to the supervisor with the final block count and tag; the segment key is erased |
| 0x32 | `SEG_STATUS` | S, A | — | `open` u8, `blocks` u32, `fifo_overruns` u16, `beacon_in_header` u8 |

The module requests a beacon from the server session, if one is open, when a segment starts (`doc/acquisition.md`). The supervisor drains ciphertext from the stream buffer on its own; the
module only counts blocks.

### Sensor

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x40 | `SENSOR_POLL` | S | — | `request_frame` (≤ 32 bytes) to send to the sensor; the module starts its round-trip timer |
| 0x41 | `SENSOR_FRAME_IN` | S | `frame` (≤ 64 bytes) | `OK` with the reading passed to the application, `VERIFY_FAIL`, or `TIMEOUT` if older than the maximum reading age (a parameter from the application header) |
| 0x42 | `SENSOR_PAIR_STEP` | S | `step` u8, `part` u8, `sensor_msg` (≤ 4096 bytes: the sensor's ML-DSA-44 certificate is about 3.7 KB and fits one part; the KEM messages are smaller) | `device_msg` (≤ 4096 bytes) for the sensor, `state` u8 (continuing, paired, refused) |
| 0x43 | `READING_GET` | A | — | `value` i32, `age_ms` u32, `status` u8 (fresh, late, none, sensor fault, unpaired, pairing unconfirmed), `serial` 8 bytes |
| 0x44 | `SENSOR_INFO` | S, A | — | `paired` u8, `confirmed` u8, `serial`, `cert_digest` 32 bytes |

Pairing confirmation and rejection arrive from the server inside a server session and are handled by the module (Session API); the supervisor learns the result through `SENSOR_INFO` and an event.

### Install

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x50 | `INSTALL_BEGIN` | S | `kind` u8 (1 platform, 2 supervisor, 3 application, 4 developer), `total_len` u32, `manifest` (≤ 4096 bytes: version, digest, the LMS or HSS signature, inclusion proof) | `OK`, `VERSION_OLD`, `VERIFY_FAIL` (manifest signature), `BUSY` |
| 0x51 | `INSTALL_DATA` | S | `offset` u32, `chunk` (≤ 1024 bytes) | `OK`; pass 1 hashes only |
| 0x52 | `INSTALL_VERIFY` | S | — | `OK` if the running digest matches the manifest; the inactive slot is erased (`PENDING`, then `EVT_DONE`) |
| 0x53 | `INSTALL_DATA2` | S | `offset` u32, `chunk` (≤ 1024 bytes) | `OK`; pass 2 re-hashes, decrypts and writes lines through the install port. The supervisor or application core being replaced is held in reset from here |
| 0x54 | `INSTALL_COMMIT` | S | — | Second digest checked, slot read back, counter advanced, boot record switched (`doc/flash.md`); `PENDING`, then `EVT_DONE` with the result. For a platform package the pending-ratchet flag is set and a reboot follows |
| 0x55 | `INSTALL_ABORT` | S | — | Discards the install; the inactive slot is left erased |

Chunks must arrive in order and cover the package exactly; anything else aborts the install.

### Attestation and log

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x60 | `ATTEST` | S | `kind` u8 (1 quote, 2 identity HMAC), `verifier_nonce` 32 bytes | `PENDING`; then `EVT_DONE` with the report, the PCR values, and the quote or MAC (≤ 2048 bytes) |
| 0x61 | `CERTS` | S | `which` u8 (AK certificate, EK certificate) | The certificate bytes, from the records region or the TPM's NV (public) |
| 0x70 | `LOG_APPEND` | S, A | `class` u8 (supervisor or application; the module's own classes are reserved), `payload` (≤ 64 bytes) | `entry` (payload, sequence number, local time hint, chain MAC; ≤ 112 bytes) to store |
| 0x71 | `LOG_HEAD` | S | — | `sequence` u32, `chain_head` 32 bytes |

The module appends its own entries (boot, installs, ratchets, sessions opened and refused, lockdowns, lifecycle changes) and emits each as `EVT_LOG` for the supervisor to store.

### Records (public contents)

| `op` | Name | Caller | Request | Response |
|---|---|---|---|---|
| 0x80 | `RECORD_GET` | S | `type` u8 (MAC address, network settings, server address, denylist digest, host slot table (identifiers only), sensor pairing summary) | The record's plaintext, if its type is marked public; `DENIED` otherwise |

Records are written only through the Session API (settings from a host, denylists from the server) or at enrollment; the supervisor reads what it needs to run the transports.

### Events (module → supervisor on mailbox A, module → application on mailbox B)

| `op` | Name | To | Payload |
|---|---|---|---|
| 0xE0 | `EVT_DONE` | Requester | `tag` of the pending request, `status`, result payload |
| 0xE1 | `EVT_SEG_HEADER` | S | Segment header bytes to write ahead of the ciphertext, `part` u8 of `parts` u8 |
| 0xE2 | `EVT_SEG_TRAILER` | S | Final block count and tag |
| 0xE3 | `EVT_LOG` | S | A module log entry to store |
| 0xE4 | `EVT_SESSION` | S, A | Session opened, closed, refused (with reason), attempt limit reached |
| 0xE5 | `EVT_SENSOR` | S, A | Pairing confirmed or rejected; reading late; sensor changed |
| 0xE6 | `EVT_ALARM` | S, A | Security alarm (class u8) that the application should show and sound; the overlay band is already driven in hardware |
| 0xE7 | `EVT_LIFECYCLE` | S, A | Retired, wiped, ratchet completed, host slot changed |
| 0xE8 | `EVT_BEACON` | S | A new verified beacon (time, for the supervisor's clock discipline and the display) |
| 0xE9 | `EVT_REBOOT` | S, A | A reboot follows in `delay_ms` (after a platform install or a lifecycle change) |

## Session API

Inside a session, plaintext is a sequence of messages with a 2-byte `len`, a 1-byte `kind` and a 1-byte reserved field. The module consumes some kinds itself and passes the rest to the
supervisor unchanged in `FRAME_IN`'s response; the supervisor sends its own kinds through `FRAME_OUT`. The kinds the module consumes are the security-relevant part of the protocol and are
frozen with it; the kinds it passes through (CLI commands, user data transfers, log export, recording downloads, settings dialogs) are defined by the supervisor and change freely.

| `kind` | Name | Direction | Consumed by | Contents |
|---|---|---|---|---|
| 0x01 | `KEY_MATERIAL` | Host → module | Module | The host data secret (32 bytes) for this session, straight into the derive path; never returned to the supervisor |
| 0x02 | `RECIPIENT_KEY` | Host → module | Module | A recording recipient's ML-KEM-768 public key and label; stored as a record under the application key |
| 0x03 | `SETTINGS` | Host → module | Module | Network settings, server address, local-time hint: written as records (public types), acknowledged with `SETTINGS_ACK` |
| 0x04 | `ATTEST_REQUEST` | Host or server → module | Module | A nonce; answered with `ATTEST_REPLY` in the same session (the mailbox `ATTEST` exists for verifiers reached outside a session) |
| 0x10 | `BEACON` | Server → module | Module | Time, nonce, MAC under the identity key (checked through the TPM); kept as the latest beacon (R47) |
| 0x11 | `BEACON_REQUEST` | Module → server | — | Sent when a segment starts or on the supervisor's request |
| 0x12 | `PAIRING_VERDICT` | Server → module | Module | Confirmed or rejected, per sensor serial (`doc/sensor.md`) |
| 0x13 | `DENYLIST` | Server → module | Module | A signed denylist; stored as a record |
| 0x14 | `LIFECYCLE` | Server → module | Module | Retire, wipe, host slot set (slot, new authorization value, encrypted end to end under the session), host slot revoke; each acknowledged with `LIFECYCLE_ACK` after the TPM operation |
| 0x15 | `PACKAGE_OFFER` | Server → module | Passed through | The supervisor fetches and installs through the mailbox; listed here because its manifest format is the module's |
| 0x20 to 0x7F | Supervisor-defined | Either | Passed through | CLI, user data transfer, log export, recording download, terminal, acknowledgements and windows |
| 0x80 to 0xFF | Reserved | | | |

The host and server session handshakes (nonces, the TPM relay inputs and the host's HMAC, the server's identity MAC exchange, key confirmation) are `SESSION_OPEN`/`SESSION_STEP` messages and
are specified with the reference model in `doc/test.md`; their byte layouts are part of this API and are frozen with it (E13).

## Parameters: data, not code

| Parameter | Where it lives | Changed by |
|---|---|---|
| Network policy (port enabled, pingable, DHCP or static) | Application image header (signed) | An application release |
| Maximum sensor reading age | Application image header | An application release |
| Session UDP port, server address, static addressing | Network settings record | A host session (`SETTINGS`) |
| Recording recipients | Records | A host session (`RECIPIENT_KEY`) |
| Sensor denylist | Record | The server (`DENYLIST`) |
| Host slots in use and their identifiers | TPM host indices and a record | The server (`LIFECYCLE`) |
| Segment length, recording schedule, sleep schedule, log retention | Supervisor and application logic | Their releases |

**Fixed in the module** (security parameters, part of the validation): key and tag sizes, frame counter width, `STEP_TIMEOUT` (30 s), `MAX_BAD_FRAMES` (8), session attempt limits
(5 failed handshakes, then a 60 s hold per transport, logged), the host slot count (8, set by TPM provisioning), record and chunk size limits, the recording block size (4 KB), the TPM
dictionary-attack parameters.

## Recovery (boot ROM, UART)

When the running bitstream cannot pair or no loader slot checks, the boot ROM speaks a third, smaller protocol on the host UART, with no session and no mailbox: `STATUS` (the status block in
hexadecimal), `REPAIR_BITSTREAM` (a bitstream repair package, streamed twice, verified against the platform public key in the boot ROM) and `REPAIR_LOADER` (a loader package, possible only
once the bitstream pairs). It is part of the module and frozen with it (`doc/flash.md`, Recovery).

## What a developer build can and cannot do

A developer session (`kind` 3) is authenticated by the loader under the working key (`doc/roles.md`) and gets the same mailbox services as a host session with the developer data key;
`LIFECYCLE`, `DENYLIST` and `PAIRING_VERDICT` are refused outside a server session whatever the build. The application's debug commands are supervisor-defined kinds and never reach the module.

## Open items

- H9: review this message set against the reference model as it is written; anything missing is cheaper to add now than after validation.
- E13: the handshake byte layouts.
- Whether `RECORD_GET` should also serve the application (currently supervisor only).
