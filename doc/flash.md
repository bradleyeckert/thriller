# Flash Map

This document lays out the QSPI NOR flash: where each image lives, how the active slot is chosen, and how updates stay safe across power cuts.
Sizes are proposals, to be confirmed against real bitstream, loader and application sizes on each target.

## Assumptions

- A 256 Mbit (32 MB) QSPI NOR flash, such as the MX25L25645G that LiteForth's `doc/hdl.md` uses for its prefetch estimates.
- 4 KB erase sectors and 64 KB erase blocks. Every region starts on a 64 KB boundary.
- The FPGA configures itself from this flash in master SPI mode at power-up; afterwards the XIP engine owns the QSPI pins.
- The flash holds only images and the boot record. Update packages are staged on the MicroSD card, except in UART recovery (see Staging).

## Regions

| Offset | Size | Region | Contents |
|---|---|---|---|
| `0x0000000` | 4 MB | Bitstream A | Encrypted, signed bitstream, including the boot ROM image |
| `0x0400000` | 4 MB | Bitstream B | The other bitstream slot |
| `0x0800000` | 64 KB | Boot record | Two copies of the active-slot record (below); the rest reserved |
| `0x0810000` | 512 KB | Loader A | Loader image in XIP layout (`doc/xip.md`): a header, then 64-byte lines with 8-byte tags |
| `0x0890000` | 512 KB | Loader B | The other loader slot |
| `0x0910000` | 512 KB | Recovery staging | Raw ciphertext of a loader package received by UART recovery, before it is verified |
| `0x0990000` | 64 KB | Records | Hosts' recording public keys, sensor pairing records, the denylist, the radio policy, the event log head: each record encrypted and authenticated under the application key |
| `0x09A0000` | 64 KB | ASIC key blob | On the ASIC: PUF helper data (`doc/ics55.md`). Reserved on the FPGA |
| `0x09B0000` | 320 KB | Reserved | |
| `0x0A00000` | 11 MB | Application A | Application image in XIP layout |
| `0x1500000` | 11 MB | Application B | The other application slot |

The XIP engine maps each port's CPU window onto one slot: port 0 onto the active loader slot, port 1 onto the active application slot (`doc/hw.md`). The plaintext window is 8/9 of the slot size.

**Bitstream slots and multi-boot.** The configuration engine reads its bitstream from a fixed address, and each family has its own dual-boot or multi-boot scheme for choosing between two
(`fpga/<family>/`). Where the scheme treats the image at address 0 as a fixed fallback, bitstream A is the enrollment-time bitstream, never overwritten, and updates alternate between B and
further regions; the loader then has to treat A's pairing key as permanently retired once the first platform update completes (R44). The slot sizes cover the PG2L50H with margin (F9).

## Boot record

The boot record says which loader slot and which application slot are active, and whether a platform install is confirmed. It is kept in two copies in separate 4 KB sectors:

- Each copy holds a sequence number, the active loader slot, the active application slot, the active bitstream slot as the loader last set it, slots marked bad, a pending-ratchet flag,
  a lockdown count and any pending lockdown record, and an HMAC-SHA256 under the application key (MAC mode, `doc/hw.md`).
- The lockdown path writes its record and bad-slot mark without a key, since it runs after the keys are cleared; those fields are outside the HMAC. They can only cause logging and a fallback.
- The copy with the highest sequence number and a valid HMAC wins. An update writes the new record into the *other* copy's sector, so a power cut leaves at least one valid copy.
- The record is a hint, not a security control. Every image is checked on its own (header HMAC, version against its counter, every line's tag), so an attacker who changes the record
  can at most make the device try the other slot, which must also pass every check.

## Install order

An update never erases the active slot, so a power cut at any point leaves a bootable device.

**Application package** (counter 1):

1. Erase and write the inactive application slot through the install port, under a fresh install salt.
2. Read the slot back and check it: header HMAC and every line's tag.
3. Advance counter 1 to the new version (production packages only).
4. Write the new boot record, selecting the new slot. Erase any developer image left in the other slot after a production install (`doc/roles.md`).

**Platform package** (counter 0):

1. Erase and write the inactive loader slot (re-encrypted per line) and the inactive bitstream slot (the encrypted bitstream as delivered).
2. Read both back: the loader's header HMAC and every line's tag; the bitstream's digest against the manifest.
3. Advance counter 0.
4. Write the new boot record selecting the new loader slot and the new bitstream slot, with the pending-ratchet flag set, and point the family's multi-boot at the new bitstream.
5. Reboot. The new bitstream pairs with its inherited key, its loader confirms the install, writes the next pairing key into the secure element, and clears the pending-ratchet flag (`doc/se.md`, Ratchet).

A cut before step 3 leaves the old images active and the counter unchanged. A cut during step 3 leaves the counter partway; the new image's version is not older than it, so it still boots
once step 4 completes, and the old image can no longer roll anything back. A cut before step 4 leaves the old record, but if the counter has passed the old image's version, the old image now
fails its version check and boot falls back to the new slot, which is why step 2 must finish before step 3. A cut around step 5 is covered by the ratchet's own recovery rule.

## Staging

Update packages are not staged in flash. Reading a staged package back from flash would need QSPI direct mode, which stalls every XIP fetch, including the loader's own code. Instead:

- A package received over the UART or the modem is written to a staging file on the MicroSD card.
- An offline package already on the card is used where it is.
- The loader reads the staged package from the card, verifies it, and writes the result into the inactive flash slot. Only those writes need direct mode.

A device without a card can still be recovered. The boot ROM's UART recovery writes the raw ciphertext of a signed loader package into the recovery staging region as it arrives;
nothing is decrypted or installed yet. It then verifies the package by reading it back, and installs it in a second pass that re-hashes the ciphertext and must reproduce the verified digest.

## Open questions

See `doc/questions.md`: F9 (bitstream size and multi-boot layout per family), F6 (slot sizes), H7 (flash part and its power-loss behavior).
