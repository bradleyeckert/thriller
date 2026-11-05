# Execute in Place

The FPGA's LiteForth application runs directly from the FPGA's QSPI flash, through a small cache, instead of being copied into block RAM.
Each cache line is decrypted and authenticated as it is fetched, and only checked plaintext enters the cache.

The work is split: **the C5 installs, the FPGA executes.** The C5's TEE verifies every package, encrypts the image per line, and keeps the authoritative
record of which image is installed. The FPGA only decrypts and checks lines, with keys it cannot export. This is a trimmed version of the XIP design in the
earlier FPGA-only architecture (commit `cecf901`, `doc/xip.md`), without the boot ROM, the second core, the install port and the secure element.

## Requirements

| Requirement | Why |
|---|---|
| Decrypt any line independently | The CPU jumps around; a miss can be anywhere |
| Authenticate every line when it is fetched, not only at boot | A check at boot leaves a gap: the flash can be swapped or emulated afterward |
| Reject a line moved from another address | Otherwise valid code could be rearranged |
| Reject a line from another install, including an older version | Otherwise old, vulnerable code could be mixed in line by line |
| Reject a whole older image | The FPGA keeps no state, so the C5 must say which image is current |
| Add little latency to a miss | The flash read is already the dominant cost |

## Per-line GCM

For each install, the TEE draws a fresh 128-bit **install salt** *R* and derives the install key:

> install key = KDF(image key, "install" ‖ *R*), with the SP 800-108 counter-mode KDF using AES-256-CMAC

For line *i* of the image in slot *s*:

- **Nonce (96 bits)** = *s* (8 bits) ‖ *i* (24 bits) ‖ 0 (64 bits).
- **Ciphertext** = plaintext XOR AES-256-CTR keystream from that nonce.
- **Tag** = GCM tag over the ciphertext, truncated to 64 bits, stored right after the line.

Lines are 64 bytes; each line and its tag (72 bytes) are fetched in one burst, so the flash overhead is 12.5%. All the AES work for a line depends only on its address,
so it runs during the flash read, and GHASH processes the data as it arrives: GCM adds only a few cycles to a miss.

## Binding to the C5's record

The FPGA does not trust anything in its own flash to tell it which image is current. At every boot, after the link handshake, the TEE sends the **boot image** message:
slot, version, install salt, length and mode. The XIP engine derives the install key from that salt, and the CPU is released from reset only then.

| Attack on the FPGA's flash | Result |
|---|---|
| Modify a line | Tag fails |
| Move a line to another address or slot | Nonce differs; tag fails |
| Mix in a line from an earlier install | Different salt, different install key; tag fails |
| Write back a complete older image | Its lines carry an old salt; the TEE sends the current salt, so every tag fails |
| Copy the flash to another board | Different image key; every tag fails |
| Replace the flash with an emulator after boot | Every line is still checked when fetched |

A header at the start of each slot repeats the version, salt, length and mode for diagnostics, but nothing depends on it.

## Install

1. The C5 receives a package: production (LMS-signed by the application owner, encrypted under the distribution key) or developer (MAC under the device's developer key).
2. The TEE checks the signature or MAC and, for production, that the version is not older than its record (`doc/c5.md`, Anti-rollback).
3. The TEE draws a new install salt, decrypts the package, and re-encrypts it per line under the new install key, streaming.
4. The C5 sends the lines to the FPGA's flash bridge over the link, into the inactive slot. The FPGA's CPU is held in reset during the install, and the LCD shows progress driven by the bridge.
5. The bridge reads the slot back through the XIP engine, which checks every tag under the new key, and reports the result.
6. Only then does the TEE record the new slot, version and salt as current. A cut at any point before leaves the old record, so the old slot keeps booting.

Packages larger than RAM stream from the MicroSD card, or from Wi-Fi, through these steps. The ciphertext is hashed as it is decrypted, and the install is abandoned
if the hash differs from the signed one, so a package changed between verification and install cannot inject code.

## Tag failure

A line whose tag fails never enters the cache. The XIP engine holds the CPU in reset, clears the install key, and reports the failure over the link. The TEE logs it,
marks the slot bad in its record, and boots the other slot by sending its boot image message. The C5 decides; the FPGA needs no lockdown path of its own.

## Cache

| Parameter | Proposal | Notes |
|---|---|---|
| Line size | 64 bytes (16 cells, 32 instructions) | Measure 32 bytes too |
| Size | 4 KB, 2-way set associative | Measure the hit rate on real applications |
| Contents | Plaintext, only after the tag passes | Cleared on reset and on any failure |
| Writes | None: the XIP region is read-only | Variables live in block RAM |
| Prefetch | Next line on a sequential miss; LiteForth's proposed `touch` instruction | |

## Flash writes

The FPGA's flash is written only during installs, with the CPU in reset, so nothing executes from it while it is busy. A miss while the bridge is in direct mode stalls
rather than reading a busy flash, which would fail a tag and look like tampering.

## Timing

With a QSPI flash at 80 MHz, a 64-byte line and its tag take about 2 µs to read; an iterative AES-256 core at 50 MHz produces the four keystream blocks and the tag mask during
that time. A miss costs about 2 µs; hits cost nothing extra.

## Open questions

1. Line and cache sizes, from hit rates of real LiteForth applications.
2. GHASH multiplier width that keeps pace with the flash on the chosen ECP5.
3. FPGA flash size, from the application size (two slots).
