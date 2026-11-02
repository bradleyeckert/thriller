# It's all about the ROT
Root of trust for an FPGA-based medical device, built on an Espressif ESP32-C5.

The ESP32-C5 is the root of trust and runs the application. It holds every key, verifies every update,
keeps the secure file system on the MicroSD card, authenticates the replaceable temperature sensor, and
configures the FPGA at power-up. The FPGA (a Lattice ECP5) is a peripheral: it holds no secrets, its bitstream
is built with the open Yosys flow, and nothing in the security design depends on it.

An earlier design put the root of trust in FPGA fabric with an ATECC608B secure element. Three review rounds showed
that much of its complexity came from building a root of trust out of parts that were not made for it. That design is kept on the
`archive/fpga-rot-v0` branch.

## Documents

| Document | Contents |
|---|---|
| This README | Overview: chipset, keys, boot, updates, sensor, host sessions |
| `doc/arch.md` | Trust boundary, threat model, risk assessment, algorithm bill of materials |
| `doc/c5.md` | ESP32-C5 configuration: eFuse key map, boot chain, TEE, flash partitions, anti-rollback, debug lockdown |
| `doc/sensor.md` | Replaceable temperature sensor: certificates, offline pairing, authenticated sessions, fail-safe behavior |
| `doc/enrollment.md` | Device and sensor enrollment, the enrollment database, detecting unknown devices and sensors, updates |
| `doc/fpga.md` | The ECP5 as a peripheral: configuration over SPI, identity check, data link |
| `doc/roles.md` | Manufacturer, application owner, developer and user; device-bound developer builds |
| `doc/test.md` | Test plan and fault-injection campaigns |
| `doc/fda.md` | FDA security architecture views |
| `doc/ics55.md` | ASIC migration to the ICS55 55 nm process |
| `doc/questions.md` | Every open question in one matrix, and the decisions taken by default |

## Chipset

- **ESP32-C5HR8**: single-core 240 MHz RISC-V, 384 KB SRAM, 8 MB PSRAM in the package, Wi-Fi 6, Bluetooth LE and 802.15.4 radios (unused by default).
  The HR8 has no flash in the package, so it needs an external part.
- **QSPI NOR flash**, external, 16 MB proposed: bootloader, TEE and application images (each in A/B slots), TEE secure storage. Encrypted by the C5 (`doc/c5.md`).
- **Lattice ECP5**, configured by the C5 over SPI at power-up, then used as an SPI peripheral (`doc/fpga.md`). Its configuration flash is no longer needed.
- **MicroSD card socket**: encrypted user data, the security event log, and offline update packages. It shares the C5's general-purpose SPI bus with the ECP5.
- **Sensor connector**: a two-way link to a replaceable temperature sensor outside the box, driven by the C5's UART, RMT or MCPWM capture/compare peripherals (`doc/sensor.md`).
- **Host link**: a UART, or the C5's built-in USB serial port, to the host PC.
- Voltage regulators, oscillators, and a test connector that is not populated in production (JTAG is disabled by eFuse).

No secure element: the C5's eFuses, HMAC peripheral and TEE take its place (`doc/c5.md`).

## Keys and what unlocks them

| Key | Held in | Per device | Protects |
|---|---|:-:|---|
| Release signing keys (RSA-3072, main and backup) | Manufacturer HSM; SHA-256 of each public key in C5 eFuse | No | Secure boot: every bootloader, TEE and application image |
| Package signing keys (LMS), main and backup | Manufacturer's HSM (platform packages) and the application owner's HSM (application packages); public keys in the TEE image | No | Update packages, verified before anything is decrypted or installed |
| Flash encryption key (XTS-AES) | C5 eFuse, generated on chip, never readable | Yes | Everything in external flash and PSRAM |
| TEE storage key | C5 eFuse, generated on chip, used only by the HMAC peripheral | Yes | TEE secure storage (keys and records listed below) |
| Device root key | C5 eFuse, from the HSM at enrollment, used only by the HMAC peripheral inside the TEE | Yes | Root of the device identity, host, data and developer keys, each derived with its own label |
| Distribution key | TEE secure storage, written at enrollment | No | Decrypting production update packages; a device that was never enrolled cannot install updates |
| Host key | Host, and derived on the device from the device root | Yes | Host sessions |
| Host data secret | Host only, never stored on the device; derived in the HSM from a separate master the device does not hold | Yes | Combined with the device's data key to unlock user data |
| Sensor pairing key | TEE secure storage and the sensor | Per pairing | Sessions with one paired sensor (`doc/sensor.md`) |

The HSM derives every per-device key from a master key and the C5's chip ID, so a replacement host can be issued without contacting the device,
and the enrollment server can authenticate any device it has enrolled (`doc/enrollment.md`).

## Boot

1. The C5's ROM checks the second-stage bootloader's RSA-3072 signature against the key digests in eFuse.
2. The bootloader checks the TEE and application images the same way, and checks their versions against the anti-rollback eFuses.
3. The TEE starts in machine mode, sets up memory and peripheral isolation, checks the application's build mode
   (production, or a developer build bound to this device), and starts the application in user mode.
4. The application configures the ECP5 from the bitstream embedded in its own signed image, then reads the FPGA's identity register and runs a self-test (`doc/fpga.md`).
5. The application opens a session with the paired sensor and waits for the host.

The application never sees a key. It asks the TEE for services: user data, sensor sessions, update installation, the event log.

## Updates

One chain covers everything on the device, because the bitstream is part of the application image:

- Each release image carries an RSA-3072 signature (for secure boot) and its package carries an LMS signature (for the update path, `doc/arch.md`).
- Packages arrive offline on the MicroSD card or through the host, or online from the update server.
- The TEE checks the LMS signature, decrypts the package with the distribution key, writes the inactive slot, and lets the bootloader try the new image.
  The new image is confirmed only after it passes its self-test, including the FPGA check; otherwise the bootloader falls back to the old one.
- The TEE refuses any package older than the newest version it has installed. Security fixes also advance the anti-rollback eFuses,
  so a vulnerable version stays blocked even if someone writes an old flash image back with a programmer.

## Sensor

The temperature sensor is replaceable and pairs offline. Each sensor carries a certificate from its manufacturer and an ML-KEM key pair.
The C5 checks the certificate, agrees a pairing key with the sensor, and later reports the pairing to the enrollment server, which detects
unknown or cloned sensors. Every frame in both directions carries a MAC under a fresh session key, and a missing, late or rejected reading
puts the device in its safe state (`doc/sensor.md`).

## Host sessions and user data

The host and the device authenticate each other with the host key and fresh nonces from both sides, and every frame is encrypted and authenticated
under a session key. User data on the MicroSD card is encrypted under a key derived from both the device's data key and a secret the host
sends in each session. The device never stores that secret, so a stolen device cannot decrypt its card, even if its chip is broken open.

A lost host is replaced by re-deriving its keys in the HSM. A compromised host means retiring the device (`doc/arch.md`, R20).

## ASIC conversion

The ECP5 is a peripheral, so an ASIC on the ICS55 process can take its place without changing the root of trust.
The ASIC needs no keys and no non-volatile memory (`doc/ics55.md`).
