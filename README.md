# It's all about the ROT
Root-of-trust for FPGAs with bitstream encryption, with or without hardware bitstream authentication.

`thriller` is vendor-neutral. It protects **data confidentiality and integrity** on any FPGA whose
configuration engine decrypts the bitstream, and adds strong protection against bitstream tampering
on FPGAs that also authenticate it (see FPGA Tiers). Everything above the configuration engine is
plain logic: SHA-256, LMS signature verification (which is built from SHA-256), AES, MAC checks,
and I2C to a secure element.

The design assumes a bitstream may be compromised and limits what that can expose:
user data is unlocked only with a secret held outside the device. See `doc/arch.md` for the threat model.

## chipset

- An FPGA with bitstream encryption, ideally also hardware bitstream authentication (see FPGA Tiers)
- A secure element such as an ATECC608B (or a pin-compatible MODSEMI MOD8ID as second source)
- Voltage regulators
- Oscillator module
- QSPI NOR flash (for bitstream, encrypted application and encrypted user data)
- USB-UART bridge (for connection to host PC or terminal)
- JTAG port (for connection to ISP tools)

## FPGA Tiers

| | Tier A: authenticated configuration | Tier B: encrypted-only configuration |
|---|---|---|
| Examples | Lattice CrossLink-NX, Efinix Titanium | Lattice ECP5 |
| Bitstream protection | Vendor signature plus encryption, checked in hardware | Encryption only |
| Cost to compromise the bitstream | Break the vendor signature *and* the AES key | Get the AES key, or modify the encrypted bitstream blindly (see `doc/arch.md`) |
| User data on a stolen device | Safe | Safe |
| User data on a tampered-and-returned device | Safe unless the bitstream is compromised | Exposed if the attacker managed a bitstream compromise first |
| Open toolchain | No (vendor tools) | Yes: Yosys and nextpnr |

Both tiers use the same loader, the same secure element configuration and the same update chains.
Tier B trades protection against targeted tampering for lower cost and an open toolchain.

## Keys and what unlocks them

| Key | Held in | Unlocked by | Protects |
|---|---|---|---|
| Pairing key | Bitstream and secure element (per device) | The bitstream itself | The authenticated channel between the loader and the secure element |
| Application key | Secure element (per device) | Pairing key | Encryption and integrity of the application image in flash |
| **Data key** | Secure element (per device) | Pairing key **and** host authorization | Encryption and integrity of user data in flash |
| Host authorization key | Secure element (non-readable) and the host | Never leaves either | Proving the host is present, and UART access |

The important row is the data key. The secure element releases it only after the host proves knowledge of
the host authorization key **directly to the secure element** (CheckMac, with the data key slot configured
to require that authorization). The loader forwards the bytes but never sees the host secret.
A bitstream that has been replaced or modified still cannot unlock user data without the host.

The application image is protected for integrity and so that a flash copy will not run on another board.
Keeping the application code itself secret is not a goal.

## Two things get updated

`thriller` authenticates two independent kinds of update:

| | Platform | Application |
|---|---|---|
| What it is | The FPGA bitstream, including the `thriller` loader logic | The code the device runs, stored encrypted in SPI NOR flash |
| Signing key | Platform LMS key | Application LMS key |
| Anti-rollback counter | Secure element counter 0 | Secure element counter 1 |
| Checked by | Loader (LMS) before install; FPGA config engine at boot (Tier A) | Loader (LMS) before install; loader's authentication tag at boot |
| After an ASIC conversion | Gone: the platform is fixed in silicon | Unchanged |

The two chains share nothing except the secure element. A platform update never touches the application,
and an application update never touches the bitstream. The application key can belong to a different
party than the platform key, for example a customer who ships their own application on our platform.

The ATECC608B has exactly two monotonic counters, one per chain.

## Signatures: LMS

Update packages are signed with LMS (Leighton-Micali Signatures, RFC 8554 and NIST SP 800-208),
a hash-based scheme that is secure against quantum computers.

- **Verification needs only SHA-256.** The loader verifies signatures itself with the same SHA-256 core it
  already has, so it needs no bignum or elliptic-curve arithmetic. The secure element does not support LMS
  and is not involved in signature checks.
- **Public keys are small (56 bytes) and must be trusted, not secret.**
  - The platform public key is built into the bitstream.
  - The application public key is held in a locked secure element slot and read over the authenticated
    (MAC'd) channel, so it can be provisioned by a different party than the platform.
    On an ASIC it can instead live in ROM if the same party owns both.
- **Signing is stateful.** Each LMS one-time key may sign exactly once. The signer must never reuse a leaf,
  including after a crash or a restore from backup, and SP 800-208 expects that state to be kept in a hardware
  security module. Updates are infrequent, so a single tree of 2^10 to 2^15 signatures per key is plenty.

### Quantum safety

Everything that protects user data is symmetric (AES-256, SHA-256, HMAC) or hash-based (LMS),
so none of it falls to a quantum computer. The one exception is the Tier A vendor bitstream signature
(ECDSA or RSA). Against a quantum-capable attacker, a Tier A FPGA's bitstream protection reduces to its
encryption, the same position as Tier B, so `thriller` never depends on that signature for data safety.

## Stage 0 (immutable)

Stage 0 is the FPGA's configuration engine. On an ASIC, it is the silicon itself.

- **Tier A:** the engine authenticates and decrypts the bitstream before the design runs,
  so a modified or forged bitstream never gets to execute.
- **Tier B:** the engine only decrypts. A modified bitstream may run. `thriller` tolerates this:
  a foreign bitstream has no pairing key, and even a modified genuine one cannot unlock user data without the host.

On the manufacturing side:

- Generate the bitstream and encrypt it (and on Tier A, sign it), using the algorithms the FPGA family supports.
- Program the FPGA's key material, then lock it. Disable readback, and enforce encrypted-only configuration where the device supports it.
- Configure and lock the secure element (keys, slot policies, counters), using a published slot layout such as Microchip's TrustFLEX as the starting point.
- Diversify every secure element key per device, so one compromised unit exposes nothing about another.
- Build the platform LMS public key into the bitstream, and store the application LMS public key in a locked secure element slot.
- Store the first pairing key in both the bitstream and the secure element.
- Put the encrypted bitstream and the encrypted application in flash.

In the field:

- The FPGA and secure element share a pairing key. All counter reads and key reads are MAC'd
  over a fresh FPGA-generated nonce, so a device on the I2C bus cannot replay or forge them.

## Stage 1: the loader (part of the platform)

The loader is the `thriller` logic in the bitstream: a soft MCU or state machine that talks to the
secure element, decrypts the application and user data, and accepts updates over the UART. It is the same on
every FPGA, and it is what an ASIC conversion would put in silicon.

### Platform updates (FPGA only)

- The host sends a platform package: a new bitstream, its version, and the next pairing key wrapped under the current one, all signed with the platform LMS key.
  On Tier A, the bitstream also carries the FPGA vendor's own signature, so a platform update is signed twice.
- The loader verifies the LMS signature against the platform public key built into the current bitstream.
- The version is checked against counter 0. Older versions are refused.
- The loader writes the bitstream to the inactive flash slot, installs the next pairing key in the secure element, and advances counter 0.

An old bitstream can still configure the FPGA, but it holds a retired pairing key, so the secure element
will not give it the application key or the data key. That is what stops platform rollback.

### Application updates

- The host sends an application package: the application image and its version, signed with the application LMS key.
- The loader reads the application public key from the secure element over the MAC'd channel and verifies the LMS signature against it.
- The version is checked against counter 1. Older versions are refused.
- The loader encrypts and authenticates the application (for example AES-GCM) with the device-unique application key, writes it to the inactive flash slot, and advances counter 1.

### Boot

- The loader reads the application from flash and checks its authentication tag before running it.
- The application key is device-unique and stays in the secure element, so a flash image copied to another board will not run.
- The application key survives platform updates: each new bitstream reaches it through its own pairing key.

### Host sessions and user data

The UART is the one insecure channel, so the host authenticates to the secure element, not to the loader:

- The loader asks the secure element for a challenge, mixed with the loader's own fresh nonce, and passes it to the host.
- The host answers with a MAC over the challenge, using the host authorization key.
- The secure element checks the answer itself (CheckMac). Only on success does it release the data key to the loader.
- The loader then decrypts and authenticates user data in flash for the rest of the session, and erases the data key when the session ends.

Use a high-entropy host key. If it is derived from a short PIN, the secure element offers no retry lockout,
so attempts must be limited another way, such as a counter-limited key.

## ASIC conversion

An ASIC removes the platform chain completely: no bitstream, no platform key, no counter 0, no pairing key rotation.
The application chain, the host-authorized data key, the secure element and the loader carry over unchanged.

One thing does change. A pairing key in mask-programmed logic is identical on every chip and can be recovered
by reverse engineering one die. An ASIC should instead get a per-device pairing key at provisioning,
for example in one-time-programmable fuses (see `doc/arch.md`, Open Questions).

## FPGA Requirements

Before porting `thriller` to an FPGA family, answer these from the vendor's security documentation.
Items 1 and 2 decide the tier.

1. **Hardware authentication.** Does the configuration engine verify a signature over the bitstream before it enters user mode, and stop on failure? Yes means Tier A.
2. **Enforcement on every port.** Can the device be locked so it rejects unauthenticated bitstreams over every configuration path, including JTAG and slave interfaces? If not, treat the part as Tier B.
3. **Key storage.** Is the encryption key (and on Tier A, the public key or its hash) held in one-time fuses that cannot be read back or reprogrammed after locking? Required for both tiers.
4. **Readback lockout.** Can configuration readback be permanently disabled? Required for both tiers.
5. **Encryption enforced.** Can the device be locked to accept only encrypted bitstreams? Strongly preferred for both tiers.
6. **Tool licensing.** Can the toolchain you plan to use generate encrypted (and on Tier A, signed) bitstreams?

## Supported FPGAs

| | Lattice CrossLink-NX (e.g. LIFCL-17-9BG256C) | Efinix Titanium (e.g. Ti60) | Lattice ECP5 (e.g. LFE5U-25F) |
|---|---|---|---|
| Tier | A | A | B |
| Toolchain | Lattice Radiant (Base license) | Efinity | Yosys, nextpnr and Project Trellis |
| Encryption | AES-256 | AES-GCM-256, key in eFuses | AES (128-bit, to confirm) |
| Authentication | ECDSA (Radiant 2.2 or later) | RSA-4096, public key hash in eFuses | None |
| 1. Hardware authentication | Yes | Yes: configuration stops on an invalid signature | No |
| 2. Enforcement on every port | **Open.** JTAG has priority over the other modes | JTAG can be fused off (IDCODE, status, boundary scan and BYPASS remain) | Not applicable |
| 3. Key storage | **Open.** Expected OTP and P-256 | eFuses | **Open** |
| 4. Readback lockout | **Open** | **Open** | **Open** |
| 5. Encryption enforced | **Open** | **Open** | **Open** |
| 6. Tool licensing | **Open.** Confirm the Base license covers security features | **Open** | **Open.** The open toolchain builds the bitstream; encrypting it may need Lattice's own tools |
| Notes | ECDSA authentication disables Early I/O Release | Security is unavailable with compressed bitstreams and on W64 packages. Fuse JTAG off as the last manufacturing step | Blind-modification resistance depends on the bitstream CRC (see `doc/arch.md`) |
| Reference | *Advanced Configuration Security User Guide for Nexus Platform* (FPGA-TN-02176) | Efinix *Titanium Security Feature* application note | Lattice ECP5 sysCONFIG documentation; Project Trellis bitstream documentation |
