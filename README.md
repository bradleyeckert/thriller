# It's all about the ROT
Root-of-trust for FPGAs with bitstream encryption, with or without hardware bitstream authentication.

`thriller` is vendor-neutral. It protects **data confidentiality and integrity** on any FPGA whose
configuration engine decrypts the bitstream, and adds strong protection against bitstream tampering
on FPGAs that also authenticate it (see FPGA Tiers). Everything above the configuration engine is
plain logic: SHA-256, LMS signature verification (which is built from SHA-256), AES, MAC checks,
and I2C to a secure element.

The design assumes a bitstream may be compromised and limits what that can expose:
user data is unlocked only with a secret held outside the device. See `doc/arch.md` for the threat model.

## Documents

| Document | Contents |
|---|---|
| This README | Overview: chipset, FPGA tiers, keys, update chains, boot stages, supported FPGAs |
| `doc/arch.md` | Threat model, risk assessment, Code Secrecy Profile, algorithm bill of materials, Verilog/Forth partition |
| `doc/hw.md` | Hardware modules, buses, the two cores and mailbox, the shared XIP engine, key paths, boot sequence, resource estimate |
| `doc/xip.md` | Execute in place: per-line AES-GCM, flash layout, caches, install and boot, RAM budget |
| `doc/se.md` | Secure element slot map, counters, version rule |
| `doc/flash.md` | Flash map, boot record, install order, staging on the MicroSD card |
| `doc/roles.md` | Manufacturer, application owner, developer and user; developer keys and their rotation |
| `doc/test.md` | Test plan and fault-injection campaigns |
| `doc/fda.md` | FDA security architecture views |
| `doc/ics55.md` | ASIC migration to the ICS55 55 nm process |
| `doc/questions.md` | Every open question in one matrix, with proposals for the most urgent |

## chipset

- An FPGA with bitstream encryption, ideally also hardware bitstream authentication (see FPGA Tiers)
- A secure element such as an ATECC608B (or a pin-compatible MODSEMI MOD8ID as second source)
- Voltage regulators
- Oscillator module
- QSPI NOR flash (for bitstreams and encrypted loader and application images; written only during updates and development; see `doc/flash.md`)
- USB-UART bridge (for connection to host PC or terminal)
- JTAG port (for connection to ISP tools)
- MicroSD card socket (for encrypted user data, security event logs and offline update packages)

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
| Application key | Secure element (per device) | Pairing key | Encryption and integrity of the loader and application images in flash (separate labels), and the boot record |
| **Data key** | Secure element (per device) | Pairing key **and** host authorization | Encryption and integrity of user data on the MicroSD card |
| Host authorization key | Secure element (non-readable) and the host | Never leaves either | Proving the host is present, and UART access |
| Distribution key | Secure element (same on every unit) | Pairing key | Encrypting application packages in transit, so a hex dump shows no plaintext |
| Developer key | Secure element (per device) | Pairing key, into hardware only. The developer never gets this key, only a working key for the current epoch from the HSM | Sideloading developer builds onto that one device (`doc/roles.md`) |

The distribution key is the one key that is not per device, because one package must install on every unit.
It is obfuscation, not secrecy: a compromised bitstream on any unit can read it. Users who need real code
secrecy switch to per-device package keys (see the Code Secrecy Profile in `doc/arch.md`).

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
| What it is | The FPGA bitstream (hardware and boot ROM) and the updatable loader image in flash, in one package or separately | The code the device runs, stored encrypted in SPI NOR flash |
| Signing key | Platform LMS key | Application LMS key |
| Anti-rollback counter | Secure element counter 0 | Secure element counter 1 |
| Checked by | Loader (LMS) before install; at boot, the FPGA config engine (Tier A) and the boot ROM (loader header, counter 0), then every loader cache line as it is fetched | Loader (LMS) before install; every cache line's tag as it is fetched (`doc/xip.md`) |
| After an ASIC conversion | Gone, replaced by a smaller updatable-loader chain on counter 0 (`doc/ics55.md`) | Unchanged |

The two chains share nothing except the secure element. A platform update never touches the application,
and an application update never touches the platform. The application key can belong to a different
party than the platform key, for example a customer who ships their own application on our platform.

The ATECC608B has exactly two monotonic counters, one per chain.

## Signatures: LMS

Update packages are signed with LMS (Leighton-Micali Signatures, RFC 8554 and NIST SP 800-208),
a hash-based scheme that is secure against quantum computers.

- **Verification needs only SHA-256.** The loader verifies signatures itself with the same SHA-256 core it
  already has, so it needs no bignum or elliptic-curve arithmetic. The secure element does not support LMS
  and is not involved in signature checks.
- **Public keys are small (56 bytes) and must be trusted, not secret.**
  - The platform public key is built into the boot ROM (block RAM in the bitstream on the FPGA, mask ROM on the ASIC).
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

Stage 0 is the FPGA's configuration engine, followed by the boot ROM inside the bitstream.
On an ASIC, it is the silicon and its mask ROM.

- **Tier A:** the engine authenticates and decrypts the bitstream before the design runs,
  so a modified or forged bitstream never gets to execute.
- **Tier B:** the engine only decrypts. A modified bitstream may run. `thriller` tolerates this:
  a foreign bitstream has no pairing key, and even a modified genuine one cannot unlock user data without the host.
- **Boot ROM:** a small image (8 to 16 KB) in block RAM, configured with the bitstream. It checks the loader image in flash
  (header HMAC, version against counter 0) before running it, and holds the flash programming primitives, the lockdown path
  and UART recovery (full list in `doc/hw.md`).
  On the ASIC the same code is mask ROM (`doc/ics55.md`). The FPGA mirrors the ASIC's boot chain on purpose, so it is tested from the start (`doc/hw.md`).

On the manufacturing side:

- Program a unique bitstream encryption key into each FPGA's eFuses (or one key per batch of boards), then lock it.
  Derive it in the HSM as KDF(bitstream master key, secure element serial number), so no key database is needed.
  Disable readback, and enforce encrypted-only configuration where the device supports it.
- Generate one bitstream per release. For each board, patch that board's own pairing key into the bitstream's
  block RAM initialization, then encrypt it under that board's key (and on Tier A, sign it).
  On the ECP5, Project Trellis's `ecpbram` can patch block RAM contents without re-running place and route.
- Configure and lock the secure element (keys, slot policies, counters) according to the slot map in `doc/se.md`.
- Diversify every secure element key per device, so one compromised unit exposes nothing about another.
- Build the platform LMS public key into the boot ROM image in the bitstream, and store the application LMS public key in a locked secure element slot.
- Store the board's pairing key in its secure element (it is already in that board's bitstream). Pairing keys are derived as
  KDF(pairing master, secure element serial number, platform version at which the key is issued), so the HSM can recompute the key
  a board holds from the counter 0 value it reports.
- Put the encrypted bitstream, the loader image and the application image in flash (the images encrypted per cache line, `doc/xip.md`).

Because each board's bitstream is encrypted under its own key, a bitstream copied from one board will not
configure another, and extracting one FPGA's key exposes only that board (or that batch).

In the field:

- The FPGA and secure element share a pairing key. All counter reads and key reads are MAC'd
  over a fresh FPGA-generated nonce, so a device on the I2C bus cannot replay or forge them.

## Stage 1: the loader (part of the platform)

The loader runs on its own LiteForth core, separate from the core that runs the application, and acts as the application's
firewall (`doc/hw.md`). The boot ROM checks it and starts it, and it then executes in place from flash through its own cache
(`doc/xip.md`). It talks to the secure element, holds every key in hardware, protects user data, and accepts updates over the UART.
It is the same on every FPGA, and the ASIC runs the same boot ROM and loader.

### Platform updates

A platform package always carries a loader image, and may also carry a new bitstream, all under one platform version on counter 0.
A package that changes only the bitstream carries the current loader image restamped with the new version, so the boot ROM's check
against counter 0 still passes after the counter advances. On the ASIC a platform package carries only a loader image.

- The update server builds a platform package for each board (or batch), selected by the secure element serial number the loader reports.
  - A bitstream carries that board's next pairing key, KDF(pairing master, serial, new platform version), is encrypted under that board's
    bitstream key, and comes with the next pairing key wrapped under the current one. On Tier A it also carries the FPGA vendor's own signature, so it is signed twice.
  - A loader image is encrypted under a content key wrapped under the board's current pairing key. Platform packages are therefore
    per board even without a bitstream, so a stolen platform signing key alone cannot produce a package that installs fleet-wide.
  - Everything is signed with the platform LMS key.
- The loader verifies the LMS signature against the platform public key in the boot ROM.
- The version must not be older than counter 0.
- The loader writes the bitstream to the inactive bitstream slot and re-encrypts the loader image per cache line into the inactive loader slot,
  through the boot ROM's flash primitives, installs the next pairing key if the package carries a bitstream, and advances counter 0.

Platform rollback is blocked twice. An old bitstream can still configure the FPGA, but it holds a retired pairing key,
so the secure element will not give it the application key or the data key. An old loader image is refused by the boot ROM,
because its version is older than counter 0.

### Application updates

- The host sends an application package: the application image encrypted under the distribution key (AES-256-GCM), and its version, signed with the application LMS key over the ciphertext.
- The loader reads the application public key from the secure element over the MAC'd channel and verifies the LMS signature against it, before decrypting anything.
- The loader decrypts the image with the distribution key, read from the secure element over the MAC'd channel.
- The version is checked against counter 1. Older versions are refused.
- The loader re-encrypts the application per cache line with AES-256-GCM, under a fresh image key derived from the device-unique application key, writes it to the inactive flash slot, and advances counter 1 (`doc/xip.md`).

### Boot

- The boot ROM authenticates to the secure element, checks the loader image's header and its version against counter 0,
  derives the loader's image key, and starts the loader, which runs from flash through its own cache.
- The loader checks the application image header, derives its image key into the AES key registers, compares the version with counter 1,
  and then releases the application core, which executes from flash through its own cache.
- Every cache line's tag is checked as it is fetched, so flash changed after boot is caught (`doc/xip.md`).
- The application key is device-unique and reaches only the AES key registers, never software, so a flash image copied to another board will not run.
- The application key survives platform updates: each new bitstream reaches it through its own pairing key.

### Host sessions and user data

The UART is the one insecure channel, so the host authenticates to the secure element, not to the loader:

- The loader asks the secure element for a challenge, mixed with the loader's own fresh nonce, and passes it to the host.
- The host answers with a MAC over the challenge, using the host authorization key.
- The secure element checks the answer itself (CheckMac). Only on success does it release the data key to the loader.
- The loader then decrypts and authenticates user data on the MicroSD card for the rest of the session, and clears the data key when the session ends.
- **Not yet designed:** after CheckMac, the session's traffic over the UART must also be encrypted and authenticated, under a session key
  that the host and the secure element derive from the host authorization key and the session nonce. Until then, user data crosses the UART
  in clear and the session can be taken over by anyone in the middle (`doc/arch.md`, R29 and Open Question 13).

Use a high-entropy host key. If it is derived from a short PIN, the secure element offers no retry lockout,
so attempts must be limited another way; both secure element counters are already allocated (`doc/se.md`).

## ASIC conversion

An ASIC removes the bitstream: no bitstream key, no vendor signature, no pairing key rotation. Mask ROM holds the boot ROM code,
and verifies the same updatable loader in flash as on the FPGA, still under counter 0. Because the FPGA already runs this chain,
the ASIC's boot chain will have been tested long before tape-out.
The application chain, the host-authorized data key and the secure element carry over unchanged.

One thing does change. A pairing key in mask-programmed logic is identical on every chip and can be recovered
by reverse engineering one die, and the open ICS55 PDK has no one-time-programmable cells. The proposed answer is an
SRAM PUF that wraps a per-device pairing key stored in flash. See `doc/ics55.md`.

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
