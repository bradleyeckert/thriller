# FPGA

The ECP5 is a peripheral of the C5. It holds no secrets, has no role in any security protocol, and is outside the trust boundary (`doc/arch.md`).
The temperature sensor connects to the C5, not to the FPGA (`doc/sensor.md`).

## Bitstream

- **Built with the open flow:** Yosys, nextpnr and `ecppack`. No bitstream encryption and no vendor tools are needed.
- **The same for every device.** It is embedded in the application image as a binary, so secure boot and the update signature cover it,
  and the flash encryption hides it at rest. Updating the FPGA is an application update.
- **Not secret.** It crosses the SPI bus in plaintext at every power-up, which is acceptable because it contains no secrets and the design's IP is not an asset.
- Any FPGA that can be configured over SPI by a microcontroller would work the same way, and so would an ASIC (`doc/ics55.md`).

## Configuration

1. The ECP5's configuration pins select slave SPI mode.
2. At power-up the application pulses PROGRAMN, waits for INITN, and sends the bitstream from its image over the C5's general-purpose SPI controller (SPI2).
   At 40 MHz an LFE5U-25 bitstream takes well under a second.
3. It checks DONE, then switches the bus to the data link.

SPI2 is the C5's only general-purpose SPI controller (SPI1 is taken by the flash and PSRAM), so the ECP5 and the MicroSD card share it with separate chip selects.

**To confirm on the ECP5:** whether the slave SPI configuration pins can be kept as user I/O after configuration, and whether user logic can read CCLK.
If not, the board routes the C5's SPI clock to a user I/O pin as well, or the data link uses its own pins.

## Identity check and self-test

After configuration the application reads a small register block from the FPGA:

| Register | Contents |
|---|---|
| Build ID | The first 16 bytes of SHA-256 over the build's source and settings, fixed at synthesis |
| Version | The FPGA design version |
| Status | Self-test results, error flags |

The application compares the build ID with the value recorded in its own image, then runs a functional self-test. A mismatch or failure is logged and handled as a device fault.
A new application image is confirmed only after this check passes, so a broken bitstream in an update falls back to the previous image.

This check is not authentication. Anyone who replaces or reprograms the FPGA can make it return the expected build ID. What it does provide is
evidence that the device runs the intended logic and catches assembly errors, corrupted images and wrong board variants. A regulator will expect that evidence (`doc/fda.md`).

## Data link

Once configured, SPI2 carries register reads and writes and data transfers between the application and the FPGA's logic. The link is not encrypted or authenticated:
nothing secret crosses it, and the FPGA's results are trusted only as far as the application checks them (R17). If the FPGA later takes on a function whose
integrity matters and cannot be checked by the C5, this decision has to be revisited.

## JTAG

The ECP5's JTAG port stays usable for development. In production it gives no access to anything secret. Someone with board access could load
a different bitstream through it, which is the same capability as replacing the chip (R17).

## Open questions

See `doc/questions.md` (FPGA rows).
