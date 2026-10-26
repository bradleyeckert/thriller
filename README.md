# It's all about the ROT
Root-of-trust for any FPGA with hardware bitstream encryption and authentication.

`thriller` is vendor-neutral. The only thing it needs from the FPGA is a configuration engine that
decrypts and authenticates the bitstream before the design runs (see FPGA Requirements).
Everything above that is plain logic: SHA-256, MAC checks, and I2C to a secure element.

## chipset

- An FPGA with hardware bitstream encryption and authentication (see Supported FPGAs)
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

- Generate the bitstream, sign it with the manufacturer's bitstream private key, and encrypt it,
  using whatever algorithms the FPGA family supports.
- Program the bitstream key material (public key or its hash, and the encryption key) into the FPGA, then lock it.
- Lock the device so it accepts only authenticated bitstreams on every configuration port.
- Configure and lock the secure element (keys, slot policies, counters), using a published slot layout such as Microchip's TrustFLEX as the starting point.
- Store the first pairing key in both the bitstream and the secure element.
- Put the signed, encrypted bitstream and the signed firmware image in flash.

In the field:

- The FPGA rejects any bitstream that fails authentication.
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

This stage accepts firmware updates over the UART. It is the same on every FPGA.

Update:

- The host sends a firmware image signed with the manufacturer's firmware private key (P-256 ECDSA).
  This key is independent of the bitstream signing key, which may use a different algorithm.
- The soft MCU in the FPGA hashes the image (SHA-256) and asks the secure element to verify the signature against the stored firmware public key.
- The secure element returns a MAC'd pass/fail, so the soft MCU needs only SHA-256 and a MAC check, not an ECDSA implementation.
- The firmware version is checked against a secure-element monotonic counter. Older versions are refused and the counter advances on success.
- The firmware is encrypted and authenticated (for example AES-GCM) with a key held in the secure element, and then written to flash.

Boot:

- The soft MCU reads the firmware from flash and checks its authentication tag before running it.
- The device-unique key comes from the secure element, so a flash image copied to another board will not decrypt.

The UART is the one insecure channel. Access to secure data over the UART requires challenge-response
authentication against a key in the secure element.

## FPGA Requirements

Before porting `thriller` to an FPGA family, answer these from the vendor's security documentation:

1. **Hardware authentication.** Does the configuration engine verify a signature over the bitstream before it enters user mode, and stop on failure?
2. **Enforcement on every port.** Can the device be locked so it rejects unauthenticated bitstreams over every configuration path, including JTAG and slave interfaces? If any port can load an unsigned bitstream, Stage 0 can be bypassed.
3. **Key storage.** Is the public key (or its hash) and the encryption key held in one-time fuses that cannot be read back or reprogrammed after locking?
4. **Readback lockout.** Can configuration readback be permanently disabled?
5. **Tool licensing.** Can the toolchain tier you plan to use generate signed and encrypted bitstreams?

## Supported FPGAs

| | Lattice CrossLink-NX (e.g. LIFCL-17-9BG256C) | Efinix Titanium (e.g. Ti60) |
|---|---|---|
| Toolchain | Lattice Radiant (Base license) | Efinity |
| Encryption | AES-256 | AES-GCM-256, key in eFuses |
| Authentication | ECDSA (Radiant 2.2 or later) | RSA-4096, public key hash in eFuses |
| 1. Hardware authentication | Yes | Yes: configuration stops on an invalid signature |
| 2. Enforcement on every port | **Open.** JTAG has priority over the other modes | JTAG can be fused off (IDCODE, status, boundary scan and BYPASS remain) |
| 3. Key storage | **Open.** Expected OTP and P-256 | eFuses |
| 4. Readback lockout | **Open** | **Open** |
| 5. Tool licensing | **Open.** Confirm the Base license covers security features | **Open** |
| Notes | ECDSA authentication disables Early I/O Release | Security is unavailable with compressed bitstreams and on W64 packages. Fuse JTAG off as the last manufacturing step |
| Reference | *Advanced Configuration Security User Guide for Nexus Platform* (FPGA-TN-02176) | Efinix *Titanium Security Feature* application note |

Not supported: Lattice ECP5. It encrypts bitstreams but cannot authenticate them in hardware,
and user logic cannot meaningfully check the bitstream it is part of.
