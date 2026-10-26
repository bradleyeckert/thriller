# thriller
Secure boot for ECP5 FPGA. It's all about the ROT.

## concept

The ECP-5 can boot from an AES stream that size-invariant. Because the ECP5's AES bitstream decryption engine is baked into silicon and enforced by hardware fuse locks,
a properly encrypted binary file acts as an immutable, cryptographically bound container.
Once flashed, you can mathematically guarantee that the exact hardware netlist you compiled is the exact hardware netlist executing on the silicon.
No one can tamper with a single gate without tripping the CRC and killing the boot sequence.
However, viewing it as a root-of-trust introduces one critical architectural nuance you have to account for: The Bootstrapping Paradox.

The Root-of-Trust Paradox
A true hardware Root-of-Trust (RoT) must be able to authenticate its environment and establish trust outward (e.g., verifying external firmware, issuing session keys,
or proving to a host server that the device hasn't been cloned). 

### How to Build a True RoT on This Architecture

To bridge the gap between an "immutable bitstream" and a fully functional "Root-of-Trust," designers typically use the encrypted bitstream as the secure container
that boots a trusted soft-core, which then anchors to your PUF:

- The Immutable Core (Encrypted Bitstream): Protects your proprietary soft-core IP, state machines, and cryptographic algorithms from being reverse-engineered or modified off the SPI flash.

- The Dynamic Root (The PUF): On every boot, your immutable soft-core instantly executes your intrinsic PUF routine to generate a device-unique, un-clonable 256-bit seed.

- The Key Derivation / Authentication Layer: That PUF seed is fed into a soft cryptographic engine (like an HMAC or AES-CMAC block) to sign challenges, derive session keys, or decrypt your application-layer payloads stored in the rest of the SPI user flash.

By combining the hardware-enforced confidentiality of the ECP5 bitstream with a fabric-implemented PUF, you get the best of both worlds:
a protected hardware container that boots securely and generates its own dynamic, un-clonable root identity at runtime.

## chipset

An FPGA such as a LFE5U-25F-6BG256C
Voltage regulators
Oscillator module
2 x SPI NOR flash (bitstream and user)
USB-UART bridge for connection to host PC or terminal
JTAG port for connection to ISP tools (Lattice, etc.)

The PUF acts as a hardware token to encrypt and decrypt data. Plaintext data from a PC is encrypted onto the Flash chip, rendering it secure.
Only the UART connection is not secure: It would be protected by authentication to control access to secure data.
