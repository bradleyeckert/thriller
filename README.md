# It's all about the ROT
Root-of-trust for ECP5 FPGAs.

## chipset

- An FPGA such as a LFE5U-25F-6BG256C
- Voltage regulators
- Oscillator module
- QSPI NOR flash (for bitstream and user)
- USB-UART bridge (for connection to host PC or terminal)
- JTAG port (for connection to ISP tools)

## Stage 0 (immutable)

The ECP-5 boots (in secure mode, with its eFuse key programmed) from an AES stream that size-invariant.
That's basically immutable, but root-of-trust also needs a signature.
That's where Asymmetric Code Signing comes in.

On the manufacturing side:

- Generate the bitstream image and put it in the boot flash.
- Append an asymetric bitstream signature (created using the manufacturer's private key) to the image in flash.
- Append a signed firmware image to flash.

In the field:

- The user logic contains two public keys (for bitstream and firmware). Nobody can change either.
- A small MCU in the user logic implements Ed25519 or ECDSA tests the bitstream signature against the public bitstream key.
- It also tests the firmware signature against the public firmware key. See Stage 1.

## Stage 1 (mutable)

This stage accepts firmware updates. User firmware is encrypted and stored in external Flash.
The Stage 0 ROT tests the signature against the public firmware key, but it does not handle encryption.

A PUF (physically unclonable function) acts as a hardware token to encrypt and decrypt data.
Plaintext data from a PC is encrypted onto the Flash chip, rendering it secure.
Only the UART connection is not secure: It would be protected by authentication to control access to secure data.
