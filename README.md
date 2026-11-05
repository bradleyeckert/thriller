# It's all about the ROT
Root of trust for an FPGA-based medical recording device, built on an Espressif ESP32-C5 and a Lattice ECP5.

The device records like a high-speed EEG: four 24-bit channels from two CODECs, streamed to a MicroSD card or over Wi-Fi.
Recordings are health data that can identify a person, so they are the primary asset.

- **The ESP32-C5 is the root of trust and the gateway.** It holds the device's root keys, verifies every update, keeps the version records,
  configures the FPGA, authenticates the replaceable temperature sensor, and does all storage and networking. Its own firmware never sees a recording in plaintext.
- **The ECP5 runs the application:** a LiteForth CPU executing in place from the FPGA's own QSPI flash, the acquisition front end, the LCD and the speaker.
  Its per-device keys travel in a bitstream encrypted by the ECP5's own eFuse key, and it encrypts recordings to the host before they leave it.

The design has been through two earlier architectures: a root of trust in FPGA fabric with an ATECC608B secure element (commit `cecf901`),
then the C5 alone running the application (commit `8c54b84`). This one keeps the C5 as root of trust and puts the application back in the FPGA.

## Documents

| Document | Contents |
|---|---|
| This README | Overview: chipset, keys, boot, updates, recordings, sensor, host sessions, radios and the CLI |
| `doc/arch.md` | Trust boundary, threat model, risk assessment, algorithm bill of materials |
| `doc/c5.md` | ESP32-C5 configuration: eFuse key map, boot chain, TEE, flash partitions, anti-rollback, radios |
| `doc/fpga.md` | The ECP5: per-device encrypted bitstream, key isolation, the link to the C5, TRNG, resources |
| `doc/xip.md` | Execute in place: per-line AES-GCM, with the C5 as installer |
| `doc/acquisition.md` | CODECs, data path, recording encryption, watermark, LCD, speaker and alarms |
| `doc/sensor.md` | Replaceable temperature sensor: certificates, offline pairing, authenticated sessions, fail-safe behavior |
| `doc/enrollment.md` | Device and sensor enrollment, the bitstream build service, detecting unknown identities, updates |
| `doc/roles.md` | Manufacturer, application owner, developer and user; device-bound developer builds |
| `doc/test.md` | Test plan and fault-injection campaigns |
| `doc/fda.md` | FDA security architecture views |
| `doc/ics55.md` | ASIC migration to the ICS55 55 nm process |
| `doc/questions.md` | Every open question in one matrix, and the decisions taken |

## Chipset

- **ESP32-C5HR8**: 240 MHz RISC-V, 384 KB SRAM, 8 MB PSRAM in the package, Wi-Fi 6 and Bluetooth LE (enabled by the application owner; see Radios).
- **QSPI NOR flash for the C5**, 16 MB proposed: C5 bootloader, TEE and firmware (A/B), the FPGA's per-device bitstreams (A/B), TEE secure storage. Encrypted by the C5.
- **Lattice ECP5** (LFE5U-25 or larger), configured by the C5 over SPI at every power-up with its encrypted bitstream (`doc/fpga.md`).
- **QSPI NOR flash for the ECP5**: the application images (A/B), encrypted and authenticated per cache line (`doc/xip.md`).
- **2 × NAU88C22** stereo CODECs: four acquisition channels, and the speaker driver (`doc/acquisition.md`).
- **LCD panel and speaker** inside the enclosure, which carries a tamper-evident seal.
- **MicroSD card socket**: encrypted recordings and user data, the event log, offline update packages. On the C5's SPI2 bus, shared with FPGA configuration and the link.
- **Sensor connector**: a wired, two-way link to a replaceable temperature sensor, driven by the C5 (`doc/sensor.md`).
- **UART** (USB-UART bridge or the C5's built-in USB serial port): status reports, and a wired fallback for host sessions, updates and the CLI.
- One oscillator for the C5, the ECP5 and the CODECs' master clock; voltage regulators; test connectors not populated in production.

## Keys and what unlocks them

| Key | Held in | Per device | Protects |
|---|---|:-:|---|
| Release signing keys (RSA-3072, main and backup) | Manufacturer HSM; digests in C5 eFuse | No | Secure boot of the C5's bootloader, TEE and firmware |
| Package signing keys (LMS), main and backup | Manufacturer HSM (C5 and bitstream packages); application owner's HSM (application packages); public keys in the TEE image | No | Every update package, checked before anything is decrypted or installed |
| C5 flash encryption key (XTS-AES) | C5 eFuse, generated on chip | Yes | The C5's external flash and PSRAM |
| TEE storage key | C5 eFuse, generated on chip | Yes | TEE secure storage |
| Device root key | C5 eFuse, from the HSM at enrollment, used only inside the TEE | Yes | Root of the identity, host, data, developer, FPGA link and FPGA image keys |
| ECP5 configuration key (AES-128) | ECP5 eFuse; HSM | Yes | The bitstream, at rest and on the configuration bus |
| FPGA link key | In the encrypted bitstream, and derived by the TEE | Yes | The C5–FPGA link |
| FPGA image key | In the encrypted bitstream, and derived by the TEE | Yes | Application images in the FPGA's flash |
| Distribution key | TEE secure storage, written at enrollment | No | Production application packages; a device never enrolled cannot install them |
| Host key | Host, and derived by the TEE | Yes | Host and CLI sessions |
| Host data secret | Host only; from a separate HSM master | Yes | Unlocks user data together with the device's data key |
| Host recording key pair (ML-KEM-768) | Private key on the host; public key in TEE storage | Per host | Recordings: the device can encrypt them but not decrypt them |
| Segment key | TEE and the FPGA's recording engine, for one segment, then erased | Per segment | One segment of a recording |
| Sensor pairing key | TEE storage and the sensor | Per pairing | Sessions with one paired sensor |

The HSM derives every per-device key from a master key and the C5's chip ID (`doc/enrollment.md`). The FPGA's keys are never readable by its CPU (`doc/fpga.md`).

## Boot

1. The C5's ROM checks its bootloader; the bootloader checks the TEE and the C5 firmware (RSA-3072, anti-rollback eFuses).
2. The TEE starts, isolates its memory and peripherals, and starts the C5 firmware in user mode.
3. The C5 firmware configures the ECP5 with the bitstream slot the TEE chooses. The bitstream is decrypted inside the ECP5 only.
4. The FPGA and the TEE run the link handshake: each proves it holds the link key, over nonces from both sides, and the TEE checks the bitstream's version.
5. The TEE sends the boot image message (slot, version, install salt). The FPGA derives that install's key and releases the LiteForth CPU, which runs the application from flash,
   checking every cache line.
6. The C5 opens the sensor session and passes readings to the application over the link.

Any failure falls back: to the other C5 image, the other bitstream, or the other application slot, each chosen by the C5.

## Updates

Three kinds of package, all checked by the TEE before anything is decrypted or installed:

| Package | Contents | Scope | Signed by |
|---|---|---|---|
| C5 platform | Bootloader, TEE, C5 firmware | Fleet | RSA-3072 images (secure boot) inside an LMS-signed package (manufacturer) |
| FPGA bitstream | One device's encrypted bitstream | Per device, built by the bitstream build service | LMS (manufacturer) |
| Application | The LiteForth application, and its radio policy | Fleet; encrypted under the distribution key | LMS (application owner); developer builds: a MAC under the device's developer key |

Packages arrive over Wi-Fi, through the host, or on the MicroSD card; per-device bitstream packages for offline delivery are prepared for the one device.
The TEE refuses anything older than its version record; security releases also advance the anti-rollback eFuses. Applications are re-encrypted per line by the TEE
into the FPGA's flash (`doc/xip.md`).

## Recordings

The TEE gives each recording segment a fresh key, encapsulates it with ML-KEM to the host's public key, and hands it to the FPGA, which encrypts the stream.
The segment key is then erased, so the device cannot read its own past recordings, and neither can a thief. The C5 firmware, with its network stacks, only moves ciphertext.
A keyed, frequency-hopping watermark injected at LSB level into the CODEC inputs lets the host detect replayed or substituted data (`doc/acquisition.md`).

## Sensor

The temperature sensor is replaceable and pairs offline with an ML-DSA certificate and ML-KEM. Every frame carries a MAC, readings older than the maximum age are rejected,
and the server later confirms each pairing and catches clones (`doc/sensor.md`).

## Host sessions and user data

The host and the TEE authenticate each other with the host key and fresh nonces, and every frame is encrypted and authenticated. User data other than recordings
is encrypted under a key derived from both the device's data key and a secret the host sends in each session, which the device never stores.
A lost host is re-issued from the HSM. A compromised host means retiring the device (`doc/arch.md`, R20).

## Radios and the CLI

**The application owner decides** whether Wi-Fi and BLE are enabled, through a radio policy in the signed application package. The radio stacks run in the C5 firmware,
never in the TEE, and never see plaintext recordings.

- **Wi-Fi** carries over-the-air updates, recording uploads (already encrypted to the host) and server contact. Outbound connections only.
- **BLE** carries the CLI through a serial service over GATT (the C5 has no Bluetooth Classic, so no true SPP). Every CLI session runs our own authenticated, encrypted session;
  advertising only after a user action, for a limited time, one connection, rotating private addresses.
- **The UART** gives read-only status to anyone with a cable, and the same authenticated sessions as a wired fallback.

| Session | Commands |
|---|---|
| None (UART status only) | Versions, build mode, faults, pairing state |
| Host (host key) | User data, recordings, sensor pairing, updates, log export, Wi-Fi credentials |
| Developer (developer key, developer builds only) | The above, plus the application's debug commands |

## ASIC conversion

An ASIC on the ICS55 process could replace the ECP5, but it now needs per-device keys and has no non-volatile memory to keep them in (`doc/ics55.md`).
