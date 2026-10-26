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
- QSPI NOR flash (for bitstream and encrypted application)
- USB-UART bridge (for connection to host PC or terminal)
- JTAG port (for connection to ISP tools)

## Two things get updated

`thriller` authenticates two independent kinds of update:

| | Platform | Application |
|---|---|---|
| What it is | The FPGA bitstream, including the `thriller` loader logic | The code and data the device runs, stored encrypted in SPI NOR flash |
| Signing key | Platform key | Application key |
| Anti-rollback counter | Secure element counter 0 | Secure element counter 1 |
| Checked by | FPGA config engine at boot; secure element before install | Secure element before install; loader's authentication tag at boot |
| After an ASIC conversion | Gone: the platform is fixed in silicon | Unchanged |

The two chains share nothing except the secure element. A platform update never touches the application,
and an application update never touches the bitstream. The application key can belong to a different
party than the platform key, for example a customer who ships their own application on our platform.

The ATECC608B has exactly two monotonic counters, one per chain.

## Stage 0 (immutable)

The FPGA authenticates its own bitstream in hardware before the design runs.
That is the root of trust: the check is done by the configuration engine, not by user logic,
so a modified or forged bitstream never gets to execute. On an ASIC, Stage 0 is the silicon itself.

On the manufacturing side:

- Generate the bitstream, sign it with the bitstream private key, and encrypt it,
  using whatever algorithms the FPGA family supports.
- Program the bitstream key material (public key or its hash, and the encryption key) into the FPGA, then lock it.
- Lock the device so it accepts only authenticated bitstreams on every configuration port.
- Configure and lock the secure element (keys, slot policies, counters), using a published slot layout such as Microchip's TrustFLEX as the starting point.
- Store the platform and application public keys in locked secure element slots.
- Store the first pairing key in both the bitstream and the secure element.
- Put the signed, encrypted bitstream and the encrypted application in flash.

In the field:

- The FPGA rejects any bitstream that fails authentication.
- The FPGA and secure element share a pairing key. All counter reads and verify results are MAC'd
  over a fresh FPGA-generated nonce, so a device on the I2C bus cannot replay or forge them.

## Stage 1: the loader (part of the platform)

The loader is the `thriller` logic in the bitstream: a soft MCU or state machine that talks to the
secure element, decrypts the application, and accepts updates over the UART. It is the same on every FPGA,
and it is what an ASIC conversion would put in silicon.

### Platform updates (FPGA only)

- The host sends a platform package: a new bitstream, its version, and the next pairing key wrapped under the current one, all signed with the platform key (P-256 ECDSA).
  The bitstream also carries the FPGA vendor's own signature, so a platform update is signed twice.
- The loader hashes the package (SHA-256) and the secure element verifies the signature against the platform public key, returning a MAC'd pass/fail.
- The version is checked against counter 0. Older versions are refused.
- The loader writes the bitstream to the inactive flash slot, installs the next pairing key in the secure element, and advances counter 0.

An old bitstream can still configure the FPGA, but it holds a retired pairing key, so the secure element
will not give it the application key or the UART authentication key. That is what stops platform rollback.

### Application updates

- The host sends an application package: the application image and its version, signed with the application key (P-256 ECDSA).
- The loader hashes the package and the secure element verifies the signature against the application public key, returning a MAC'd pass/fail.
- The version is checked against counter 1. Older versions are refused.
- The loader encrypts and authenticates the application (for example AES-GCM) with the device-unique application key from the secure element, writes it to the inactive flash slot, and advances counter 1.

### Boot

- The loader reads the application from flash and checks its authentication tag before running it.
- The application key is device-unique and stays in the secure element, so a flash image copied to another board will not decrypt.
- The application key survives platform updates: each new bitstream reaches it through its own pairing key.

The UART is the one insecure channel. Access to secure data over the UART requires challenge-response
authentication against a key in the secure element.

## ASIC conversion

An ASIC removes the platform chain completely: no bitstream, no platform key, no counter 0, no pairing key rotation.
The application chain, the secure element and the loader carry over unchanged.

One thing does change. A pairing key in mask-programmed logic is identical on every chip and can be recovered
by reverse engineering one die. An ASIC should instead get a per-device pairing key at provisioning,
for example in one-time-programmable fuses (see `doc/arch.md`, Open Questions).

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
