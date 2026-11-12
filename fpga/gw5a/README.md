# Gowin Arora V (GW5A-25 / GW5AT-25)

**Part:** GW5A-LV25 (GW5AT-LV25 for the automotive grade): 23,040 LUT4, 1,008 Kb BSRAM in 56 blocks, 28 DSP (27×18), 22 nm SRAM process,
packages from LQ100 and LQ144 (QFP) up to UG324 (239 I/O).
**Status:** evaluated November 2026 from the public datasheets; **a fallback at best, behind the ECP5, not a target.** Its security features stop where the ECP5's do:
AES-128 bitstream encryption with no authentication, and no hardened crypto block. It is included so nobody repeats the evaluation.

## What the datasheets say

From the GW5A (DS1103) and GW5AT (DS1111) datasheets:

- "Bitstream data encryption with 128-bit AES encryption algorithm." The key is programmed through the eFuse voltage pin (VEFUSE "for programming AES key, changing the boot address of Multiboot related golden image").
- CRC and "security bits" are added to the bitstream by default; the device "cannot be woken up by incorrect data"; after a bitstream with the security bit is configured, "data readback cannot be performed."
- A 128-bit OTP: 32 user bits, a 64-bit device DNA, the rest reserved.
- Configuration modes: JTAG, SSPI, **MSPI**, Master and Slave CPU, Master and Slave SERIAL, PCIe on larger parts. Multi-boot with a golden image whose boot address can be set by eFuse; background upgrade.
- An SEU handler (ECC and CRC over configuration memory).

**Not mentioned anywhere:** bitstream authentication or signatures, DPA or glitch countermeasures, a JTAG lock, a hard AES or other crypto block usable from the fabric, a TRNG or PUF.
Configuration detail is deferred to UG714E (*Arora V 25K FPGA Products Programming and Configuration User Guide*), which is behind Gowin's document login and was not consulted;
a vendor with ECDSA or RSA bitstream authentication would list it in the datasheet features, and Gowin does not.

## The wish list

| # | Requirement (`fpga/README.md`) | GW5A-25 |
|---|---|---|
| 1 | Encryption and authentication, per-device key | **Encryption only.** AES-128 with the key in eFuse; integrity by CRC. Fails the hard requirement, as the ECP5 does (R32) |
| 2 | No fallback to unencrypted | Unknown: whether programming the AES key forces every bitstream to be encrypted, or a separate eFuse does (UG714E) |
| 3 | Readback disabled, key not readable | Security bit disables readback; key in eFuse; JTAG lock not mentioned, so boundary scan presumably remains (R43) |
| 4 | MSPI self-configuration with multi-boot | **Yes.** Multi-boot with an eFuse-settable golden-image address, which fits the ratchet-and-fallback scheme in `doc/flash.md` |
| 5 | Per-device constants from a script | Gowin EDA has a Tcl interface; whether it can rewrite BSRAM initialization in a routed design and re-encrypt is unknown. Try it |
| 6 | Room for a masked Ascon core | Tight, as on the LFE5U-25F; the GW5A-60 would be comfortable (R33) |
| 7 | Ring-oscillator TRNG | Probably; confirm the DRC and timing tools tolerate the loop |
| 8 | Enough logic | Nearly identical to the LFE5U-25F, so the same tightness with the masked cores (`doc/hw.md`, Resource estimate); the GW5A-60 (59,904 LUT4) would be the comfortable size |
| 9 | Pins | Up to 239 I/O; the QFP packages suit a low-cost board |

## Compared with the ECP5

| | ECP5 LFE5U-25F | GW5A-LV25 |
|---|---|---|
| Process | 40 nm | 22 nm: lower power, faster |
| Bitstream security | AES-128, no MAC | AES-128, no MAC |
| Multi-boot | Dual boot | Multi-boot, golden address in eFuse |
| Hard crypto | None | None |
| DSP | 28 multipliers | 28 DSP slices |
| Packages | BGA only | QFP and BGA |
| Open-source flow | Mature (Yosys, nextpnr, Project Trellis) | Early (Apicula covers older families; Arora V support incomplete) |
| Encrypted-bitstream flow | Diamond, scripted ECO | Gowin EDA; untested |
| Documentation | Full, in English | Thinner in English; configuration guide behind login |
| Origin | Lattice (US), fab in Asia | Gowin (Guangdong, China) |

Same security tier; cheaper and more modern silicon; less certain tooling. On origin it sits in Pango's column, and in that column the Logos2 is the stronger part by a wide margin
(authentication before decryption, 50K logic), so the GW5A makes sense only where its price or its QFP package decides.

## If it were used

Everything in `fpga/ecp5/README.md` applies: the ratchet is what makes a superseded bitstream useless since the configuration engine cannot refuse it; blind edits are limited by the CRC
and the pairing-key check; the masked Ascon and SHA-256 cores carry the fabric's side-channel defense as on every family; units should be counted in the enrollment database. Add to F10's list: what UG714E says about forcing encrypted configuration,
JTAG after the security bit, the golden-image eFuse and how the fabric redirects multi-boot, and whether Gowin EDA can patch BSRAM contents in a routed design.

## Sources

- [GW5A series datasheet DS1103-1.0.8E](https://cdn.gowinsemi.com.cn/DS1103E.pdf)
- [GW5AT series (automotive) datasheet DS1111-1.0.8E](https://cdn.gowinsemi.com.cn/DS1111E.pdf)
- [Arora V product page](https://www.gowinsemi.com/en/product/arora-v-fpga/)
