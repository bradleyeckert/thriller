# Flash Map

This document lays out the QSPI NOR flash: where each image lives, how the active slot is chosen, and how updates stay safe across power cuts.
Sizes are proposals, to be confirmed against real bitstream, loader and application sizes on each target.

## Assumptions

- A 256 Mbit (32 MB) QSPI NOR flash, such as the MX25L25645G that LiteForth's `doc/hdl.md` uses for its prefetch estimates.
- 4 KB erase sectors and 64 KB erase blocks. Every region starts on a 64 KB boundary.
- The flash holds only images. Update packages are staged on the MicroSD card, not in flash (see Staging).

## Regions

| Offset | Size | Region | Contents |
|---|---|---|---|
| `0x0000000` | 1 MB | Bitstream A | Encrypted (and on Tier A, signed) bitstream, including the boot ROM image |
| `0x0100000` | 1 MB | Bitstream B | The other bitstream slot |
| `0x0200000` | 64 KB | Boot record | Two copies of the active-slot record (see below); the rest reserved |
| `0x0210000` | 512 KB | Loader A | Loader image in XIP layout (`doc/xip.md`): a 72-byte header, then 64-byte lines with 8-byte tags. About 450 KB of loader code |
| `0x0290000` | 512 KB | Loader B | The other loader slot |
| `0x0310000` | 960 KB | Reserved | Future platform use |
| `0x0400000` | 12 MB | Application A | Application image in XIP layout. About 10.5 MB of application code and constants |
| `0x1000000` | 12 MB | Application B | The other application slot |
| `0x1C00000` | 4 MB | Reserved | Future use |

The XIP engine maps each port's CPU window onto one slot: port 0 onto the active loader slot, port 1 onto the active application slot
(`doc/hw.md`, Shared XIP engine). The plaintext window is 8/9 of the slot size, because every 64 bytes of code take 72 bytes of flash.

The bitstream slot sizes cover the supported parts with margin, to be checked per family: an uncompressed LFE5U-25 bitstream is well under 1 MB.
Where the FPGA reads its bitstream from a fixed address, slot selection for bitstreams uses the vendor's own dual-boot or multiboot
mechanism, which differs by family (Open Question 1).

## Boot record

The boot record says which loader slot and which application slot are active. It is kept in two copies in separate 4 KB sectors,
in the style of LiteForth's stage 1 security record:

- Each copy holds a sequence number, the active loader slot, the active application slot, and an HMAC-SHA256 under the application key
  (computed through the private key path).
- The copy with the highest sequence number and a valid HMAC wins. An update writes the new record into the *other* copy's sector,
  so a power cut leaves at least one valid copy.
- The record is a hint, not a security control. Every image is checked on its own (header HMAC, version against its counter, every line's tag),
  so an attacker who changes the record can at most make the device try the other slot, which must also pass every check.
- If the active slot fails its checks, the boot ROM (for the loader) or the loader (for the application) tries the other slot.

## Install order

An update never erases the active slot, so a power cut at any point leaves a bootable device:

1. Erase and write the inactive slot (bitstream, loader or application).
2. Read the slot back and check it: header HMAC, and every line's tag.
3. Advance the counter (counter 0 for a platform package, counter 1 for a production application package).
4. Write the new boot record, selecting the new slot.

A cut before step 3 leaves the old image active and the counter unchanged. A cut during step 3 leaves the counter partway; the new image's
version is not older than the counter, so it still boots once step 4 completes, and the old image can no longer roll anything back
(`doc/se.md`, Counters). A cut before step 4 leaves the old record, but if the counter has passed the old image's version, the old image now
fails its version check and boot falls back to the new slot, which is why step 2 must finish before step 3.

Pairing key rotation adds one more step for bitstream installs, whose order across power cuts is still open (`doc/arch.md`, Open Question 1).

## Staging

Update packages are not staged in flash. Reading a staged package back from flash would need QSPI direct mode, which stalls every XIP fetch,
including the loader's own code. Instead:

- A package received over the UART is written to a staging file on the MicroSD card (as LiteForth does with `lfstage.bin`).
- An offline package already on the card is used where it is.
- The loader reads the staged package from the card, verifies it, and writes the result into the inactive flash slot through the boot ROM's
  flash primitives. Only those writes need direct mode.

A device without a card can still be recovered: the boot ROM's UART recovery receives a signed loader package directly, in small blocks,
each written to flash as it arrives.

## Developer images

A production install erases any developer image left in the other application slot, after the new production image is checked and before
the boot record selects it (`doc/roles.md`). The device then holds no developer image that could become a fallback.

## Open questions

1. **Bitstream slot selection** on each FPGA family: ECP5, CrossLink-NX and Titanium each have their own dual-boot or multiboot scheme, with its own
   fixed addresses and golden-image rules. The bitstream regions may need to move to match.
2. **Region sizes,** from real bitstream, loader and application sizes.
3. **Flash part,** including its behavior on power loss during erase and program, and whether a smaller part suffices.
