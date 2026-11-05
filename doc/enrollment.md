# Enrollment

Every device and every sensor is entered into the manufacturer's enrollment database when it is made. The ecosystem uses the database to:

- recognize genuine devices and sensors, and flag any identity it does not know (a "mystery key");
- issue keys for hosts and developer builds;
- build each device's encrypted bitstream;
- confirm sensor pairings and catch cloned sensors;
- refuse updates to anything not enrolled.

A device does not need to be online to work. It reports to the server when it can: over Wi-Fi if the application owner has enabled it, otherwise through the host.

## Keys held by the manufacturer

All keys stay inside HSMs. The database holds identities and records, never secret keys.

| Key | Used for |
|---|---|
| Device master | Deriving each device's root key: KDF(device master, chip ID). Everything the device derives from its root (identity, host, data, log, developer, FPGA link and FPGA image keys) the HSM can derive too |
| ECP5 master | Deriving each device's ECP5 configuration key: KDF(ECP5 master, chip ID), truncated to 128 bits |
| Host data master | Deriving each device's host data secret: KDF(host data master, chip ID). Separate from the device master because the device must never be able to compute it |
| Distribution key | Encrypting production application packages; written into each device at enrollment |
| Release RSA keys, main and backup | Signing C5 images (secure boot) |
| Package LMS keys, main and backup | Signing update packages. If the application owner is a different company, it holds the application package keys (`doc/roles.md`) |
| Sensor CA keys (ML-DSA), main and backup | Signing sensor certificates. May belong to the sensor maker |

Separate masters per purpose, dual control and audit logging in the HSMs are the controls against an insider (R19).

## Device enrollment

At the end of the production line:

1. **Program** the C5's signed bootloader, recovery bootloader, TEE and firmware, using the C5's download mode before it is locked.
2. **First boot.** The bootloader burns the secure boot digests, generates the flash encryption key and the TEE storage key on chip, encrypts the flash,
   and burns the debug and download lockdown eFuses (`doc/c5.md`).
3. **Read the chip ID** over the factory link.
4. **Burn the device root key.** The HSM derives it from the chip ID. The station sends it to the TEE, which burns KEY4 with purpose HMAC_UP,
   read-protects and write-protects it, and erases its copy. The station's link must be inside the controlled area, since the root crosses it once.
5. **Write the distribution key** into TEE secure storage the same way.
6. **Check.** The station sends a nonce; the TEE answers with a MAC under the identity key; the HSM checks it. This proves the root key took.
7. **Program the ECP5** over JTAG: its AES configuration key (from the HSM), the "encrypted bitstreams only" setting, readback disable, and the key lock.
   The ECP5 key crosses the JTAG link once, inside the controlled area.
8. **Build the bitstream.** The bitstream build service makes this device's bitstream (below), and the station writes its signed package into the C5's bitstream slots.
9. **Check the pair.** The C5 configures the ECP5; the link handshake must succeed, which proves the ECP5 key, the bitstream's keys and the C5's root all agree.
10. **Install the application** through the TEE, which encrypts it per line under a fresh install salt and writes it over the link into the FPGA's flash (`doc/xip.md`).
11. **Record** the chip ID, serial number, date, station, image and bitstream versions and an eFuse summary in the database.
12. **Close enrollment.** The TEE records that enrollment is complete. It has no command to rewrite the root or the distribution key, KEY4
    is write-protected, and the ECP5's key is locked, so neither chip can be enrolled or paired again. Replacing either chip means returning the board to the factory.

## Bitstream build service

Each device has its own bitstream, because its link and image keys are inside it (`doc/fpga.md`). For each FPGA release:

1. One Yosys and nextpnr build produces the common bitstream, with placeholder key constants in block RAM.
2. For each device, the HSM derives its link key, image key and ECP5 key and releases them to the build service for that job only.
3. The service patches the keys into the block RAM contents with prjtrellis's `ecpbram`, encrypts the result with Lattice's `bitgen` under the ECP5 key, and erases the keys.
4. The HSM signs the package (device ID, bitstream version, link protocol version, the encrypted bitstream) with the manufacturer's LMS key.

Patching needs no re-place-and-route, so a per-device build takes seconds. The service handles per-device keys in plaintext, so it is isolated, audited, dual-controlled,
and gets keys only per job (R42). Whether `bitgen` runs headless on the build servers is an open question.

Bitstream packages are delivered online to the one device, or prepared for one device for offline delivery on a card or through the host.

A device that skipped enrollment boots, but has no root key and no distribution key, so it cannot decrypt an update package, prove its identity, or open a host session.

## Sensor enrollment

At the sensor factory, each sensor generates its ML-KEM key pair and receives an ML-DSA certificate (`doc/sensor.md`).
The serial, model, certificate hash and date go into the database. Nothing secret about the sensor is stored.

## Contact with the server

When the device reaches the enrollment server, either side proves itself under the device's identity key, over nonces from both:

- The server knows the identity key because the HSM can derive it from the chip ID.
- After authentication, the exchange runs under a session key derived from the identity key and both nonces, like a host session.

During contact the device:

- reports its image versions and the anti-rollback eFuse state;
- uploads its event log since the last contact;
- reports unconfirmed sensor pairings, and receives *confirmed* or *rejected* for each;
- receives the current sensor denylist;
- can receive an update package (see Updates).

## Detecting unknown identities

The server flags:

| Observation | Meaning |
|---|---|
| A chip ID not in the database | A device that was never enrolled, or a counterfeit |
| A known chip ID whose MAC fails | A forged identity |
| A device marked retired or stolen that makes contact | Recovered or misused device |
| A sensor serial not in the database, or whose certificate hash differs | Counterfeit sensor (it would already fail certificate checks unless the CA key leaked) |
| One sensor serial confirmed on several devices at overlapping times | A cloned sensor; the serial goes on the denylist |

## Updates

Updates do not need a network, but they do need enrollment:

- **Offline packages** (on the MicroSD card or from the host): application packages are encrypted under the distribution key, which only enrolled devices hold;
  bitstream packages are built for one device and work nowhere else. The TEE checks the LMS signature and the version (`doc/c5.md`, Anti-rollback).
- **Online updates** come from the update server after the device has authenticated, over Wi-Fi or through the host. The server sends only to enrolled
  devices in good standing, and only current releases. Over Wi-Fi the device connects out over TLS and never listens; a fake access point or server
  can withhold updates but cannot get a forged or old package past the TEE (R29).
- **Developer builds** carry a MAC under one device's developer key and install only there (`doc/roles.md`).
- **Code Secrecy Profile:** packages are wrapped to each device's own key instead (`doc/arch.md`).

## Hosts

A host is issued with the device's host key and host data secret, both derived in the HSM from the chip ID. The host generates its own ML-KEM-768 key pair for recordings
and gives the device its public key in an authenticated host session (`doc/acquisition.md`); the private key never leaves the host. A replacement for a lost host is issued the same way
after the owner is authorized. Because the HSM can re-derive both, losing a host does not lose the user data. Recordings, however, can only be decrypted with the host's
recording private key, so that key must be backed up by the host's owner (or recordings also encapsulated to a clinic server's key); the HSM cannot recover it. A compromised host cannot be cut off,
since the device's host key cannot change, so the device is retired (R20).

## Retirement

Retiring a device marks it in the database. The TEE also offers a wipe, authorized by the host or the server, which erases TEE secure storage
(distribution key, pairings, records) and the user data on the card. eFuse keys cannot be erased, but without the host data secret the old data cannot be read.
