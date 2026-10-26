# It's all about the ROT
Root-of-trust for Lattice Nexus FPGAs.

## chipset

- An FPGA such as a LIFCL-17-9BG256C (CrossLink-NX), which supports AES-256 bitstream encryption and ECDSA bitstream authentication
- A secure element such as an ATECC608B (or a pin-compatible MODSEMI MOD8ID as second source)
- Voltage regulators
- Oscillator module
- QSPI NOR flash (for bitstream and user)
- USB-UART bridge (for connection to host PC or terminal)
- JTAG port (for connection to ISP tools)

## Stage 0 (immutable)

The FPGA authenticates its own bitstream in hardware before the design runs.
That is the root of trust: the check is done by the configuration engine, not by user logic,
so a modified or forged bitstream never gets to execute.

On the manufacturing side:

- Generate the bitstream, sign it with the manufacturer's bitstream private key (ECDSA), and encrypt it with AES-256.
- Program the bitstream public key and AES key into the FPGA, then lock them.
- Lock the device so it accepts only authenticated bitstreams on every configuration port (see Open Items).
- Configure and lock the secure element (keys, slot policies, counters), using a published slot layout such as Microchip's TrustFLEX as the starting point.
- Store the first pairing key in both the bitstream and the secure element.
- Put the signed, encrypted bitstream and the signed firmware image in flash.

In the field:

- The FPGA rejects any bitstream that fails ECDSA authentication.
- The secure element holds the firmware public key in a locked slot.
- The FPGA and secure element share a pairing key. All counter reads and verify results are MAC'd
  over a fresh FPGA-generated nonce, so a device on the I2C bus cannot replay or forge them.

### Bitstream rollback

Hardware authentication accepts any correctly signed bitstream, including an older one with a known bug.
The secure element blocks this:

- Each bitstream release carries its own pairing key.
- When an update is installed, the new bitstream writes the next pairing key into the secure element and advances its monotonic counter.
- An old bitstream can still configure the FPGA, but it can no longer authenticate to the secure element,
  so it never receives the firmware key or the UART authentication key.

## Stage 1 (mutable)

This stage accepts firmware updates over the UART.

Update:

- The host sends a firmware image signed with the manufacturer's firmware private key (P-256 ECDSA, the same curve as the bitstream).
- The soft MCU in the FPGA hashes the image (SHA-256) and asks the secure element to verify the signature against the stored firmware public key.
- The secure element returns a MAC'd pass/fail, so the soft MCU needs only SHA-256 and a MAC check, not an ECDSA implementation.
- The firmware version is checked against a secure-element monotonic counter. Older versions are refused and the counter advances on success.
- The firmware is encrypted and authenticated (for example AES-GCM) with a key held in the secure element, and then written to flash.

Boot:

- The soft MCU reads the firmware from flash and checks its authentication tag before running it.
- The device-unique key comes from the secure element, so a flash image copied to another board will not decrypt.

The UART is the one insecure channel. Access to secure data over the UART requires challenge-response
authentication against a key in the secure element.

## Open Items

These questions must be answered from Lattice's *Advanced Configuration Security User Guide for Nexus Platform* (FPGA-TN-02176) before the design is committed:

1. **Enforcement on every port.** Can the device be fused to reject unsigned bitstreams over JTAG and slave SPI, not only from boot flash? JTAG has priority over the other configuration modes; if it can load an unsigned bitstream, Stage 0 can be bypassed.
2. **Public key storage and curve.** Where is the bitstream public key stored (expected: OTP), and which curve is used (expected: P-256)?
3. **Lockout fuses.** Can readback and key reprogramming be permanently locked, and are those one-time fuses?
4. **Tool licensing.** Can the free Base license of Lattice Radiant generate signed and encrypted bitstreams, or do the security features need a paid license?

Also note: enabling ECDSA bitstream authentication disables the Early I/O Release feature.
