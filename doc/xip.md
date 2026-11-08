# Execute in Place

Both cores run directly from the QSPI flash, through small caches, instead of from block RAM. Each cache line is decrypted and authenticated as it is fetched, and only checked plaintext
enters a cache. The loader installs images; the hardware checks them.

## Requirements

| Requirement | Why |
|---|---|
| Decrypt any line independently | The CPU jumps around; a miss can be anywhere |
| Authenticate every line when it is fetched, not only at boot | A check at boot leaves a gap: the flash can be swapped or emulated afterward (R6) |
| Reject a line moved from another address or slot | Otherwise valid code could be rearranged |
| Reject a line from another install, including an older version | Otherwise old, vulnerable code could be mixed in line by line |
| Reject a whole older image | The counters in the secure element decide (R34, R35) |
| Add little latency to a miss | The flash read is already the dominant cost |

## Image header

Each slot starts with a header: image kind (loader or application), version, mode (production, or developer with the device's serial number and epoch), length, the 128-bit **install salt** *R*,
the network policy (applications), and an HMAC-SHA256 under the application key over all of it. The header is the only thing the boot chain reads before deciding to trust a slot:

| Check | Loader image (boot ROM) | Application image (loader) |
|---|---|---|
| HMAC | Under the application key, unwrapped from the secure element | Same |
| Version | Not older than counter 0 | Not older than counter 1 (production); developer builds: serial matches, epoch = counter 1 ÷ 1024 |
| Result | Pass token: derive the image key into XIP port 0 | Pass token: derive the image key into XIP port 1 |

An attacker who writes back a whole older image fails the version check; one who writes a header with a forged version fails the HMAC.

## Per-line GCM

For each install, the loader draws a fresh install salt *R* and derives the install key:

> install key = KDF(application key, label ‖ *R*), label "loader" or "application", with the SP 800-108 counter-mode KDF using AES-256-CMAC

For line *i* of the image in slot *s*:

- **Nonce (96 bits)** = *s* (8 bits) ‖ *i* (24 bits) ‖ 0 (64 bits).
- **Ciphertext** = plaintext XOR AES-256-CTR keystream from that nonce.
- **Tag** = GCM tag over the ciphertext, truncated to 64 bits, stored right after the line.

Lines are 64 bytes; each line and its tag (72 bytes) are fetched in one burst, so the flash overhead is 12.5%. All the AES work for a line depends only on its address, so the hard AES block
runs it during the flash read, and GHASH processes the data as it arrives: GCM adds only a few cycles to a miss.

**If the hard AES block cannot compute GHASH,** the line format switches to AES-CCM (CTR encryption plus a CBC-MAC tag), which uses nothing but the block (open question F4).

| Attack on the flash | Result |
|---|---|
| Modify a line | Tag fails |
| Move a line to another address or slot | Nonce differs; tag fails |
| Mix in a line from an earlier install | Different salt, different install key; tag fails |
| Write back a complete older image | Header version behind the counter; refused |
| Copy the flash to another board | Different application key; header HMAC fails |
| Replace the flash with an emulator after boot | Every line is still checked when fetched |

## Install

1. The loader receives a package from the staging area: production (LMS-signed, encrypted under the distribution key) or developer (MAC under the device's developer key).
2. It checks the signature or MAC, and the version against the counter (`doc/se.md`, Version rule). Nothing is decrypted before this passes.
3. It draws a new install salt, decrypts the package through the install port, and re-encrypts it per line under the new install key, streaming into the inactive slot through the flash bridge.
   The ciphertext is hashed as it is decrypted and must match the signed digest, so a package changed between verification and install cannot inject code.
4. It reads the slot back through the install port, checking every tag, then writes the header.
5. Counter and boot record, in the order in `doc/flash.md`. A cut at any point before leaves the old slot active.

The application core is held in reset during an application install; the loader keeps running from its own slot. The LCD overlay shows progress.

## Tag failure

A line whose tag fails never enters a cache. The XIP engine raises lockdown (`doc/hw.md`): keys are cleared, the slot is marked bad in the boot record, and the next boot falls back to the other slot.

## Caches

| Parameter | Loader | Application | Notes |
|---|---|---|---|
| Line size | 64 bytes | 64 bytes | Measure 32 bytes too |
| Size | 2 KB | 4 KB, 2-way set associative | Measure the hit rate on real applications |
| Contents | Plaintext, only after the tag passes | Same | Cleared on reset and on any failure |
| Writes | None | None | Variables live in block RAM |
| Prefetch | Next line on a sequential miss | Same; LiteForth's proposed `touch` instruction | |

## Flash writes

Flash is written only during installs and UART recovery, through QSPI direct mode, during which both caches stall rather than read a busy flash, which would fail a tag and look like tampering.
The loader runs install code from its cache while the flash is busy; the install routine is sized to stay resident, as LiteForth's stage 1 does.

## Timing

With a QSPI flash at 80 MHz, a 64-byte line and its tag take about 2 µs to read; the hard AES block produces the keystream and the tag mask during that time. A miss costs about 2 µs with GCM,
a little more with CCM; hits cost nothing extra.

## Open questions

See `doc/questions.md`: F6 (line, cache and slot sizes), F4 (GCM or CCM and hard-block throughput).
