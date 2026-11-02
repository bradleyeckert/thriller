# Enrollment

Every device and every sensor is entered into the manufacturer's enrollment database when it is made. The ecosystem uses the database to:

- recognize genuine devices and sensors, and flag any identity it does not know (a "mystery key");
- issue keys for hosts and developer builds;
- confirm sensor pairings and catch cloned sensors;
- refuse updates to anything not enrolled.

A device does not need to be online to work. It reports to the server when it can: over Wi-Fi if the application owner has enabled it, otherwise through the host.

## Keys held by the manufacturer

All keys stay inside HSMs. The database holds identities and records, never secret keys.

| Key | Used for |
|---|---|
| Device master | Deriving each device's root key: KDF(device master, chip ID). Everything the device derives from its root (identity, host, data, log, developer keys) the HSM can derive too |
| Host data master | Deriving each device's host data secret: KDF(host data master, chip ID). Separate from the device master because the device must never be able to compute it |
| Distribution key | Encrypting production update packages; written into each device at enrollment |
| Release RSA keys, main and backup | Signing images (secure boot) |
| Package LMS keys, main and backup | Signing update packages. If the application owner is a different company, it holds the application package keys (`doc/roles.md`) |
| Sensor CA keys (ML-DSA), main and backup | Signing sensor certificates. May belong to the sensor maker |

Separate masters per purpose, dual control and audit logging in the HSMs are the controls against an insider (R19).

## Device enrollment

At the end of the production line:

1. **Program** the signed bootloader, recovery bootloader, TEE and application, using the C5's download mode before it is locked.
2. **First boot.** The bootloader burns the secure boot digests, generates the flash encryption key and the TEE storage key on chip, encrypts the flash,
   and burns the debug and download lockdown eFuses (`doc/c5.md`).
3. **Read the chip ID** over the factory link.
4. **Burn the device root key.** The HSM derives it from the chip ID. The station sends it to the TEE, which burns KEY4 with purpose HMAC_UP,
   read-protects and write-protects it, and erases its copy. The station's link must be inside the controlled area, since the root crosses it once.
5. **Write the distribution key** into TEE secure storage the same way.
6. **Check.** The station sends a nonce; the TEE answers with a MAC under the identity key; the HSM checks it. This proves the root key took.
7. **Record** the chip ID, serial number, date, station, image versions and an eFuse summary in the database.
8. **Close enrollment.** The TEE records that enrollment is complete. It has no command to rewrite the root or the distribution key, and KEY4
   is write-protected, so a device cannot be enrolled twice ("the C5 will not re-pair").

The ECP5 needs no enrollment. Its bitstream is the same for every device (`doc/fpga.md`).

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

- **Offline packages** (on the MicroSD card or from the host) are encrypted under the distribution key, which only enrolled devices hold.
  The TEE checks the LMS signature and the version (`doc/c5.md`, Anti-rollback).
- **Online updates** come from the update server after the device has authenticated, over Wi-Fi or through the host. The server sends only to enrolled
  devices in good standing, and only current releases. Over Wi-Fi the device connects out over TLS and never listens; a fake access point or server
  can withhold updates but cannot get a forged or old package past the TEE (R29).
- **Developer builds** are delivered over the air to the one device they were signed for (`doc/roles.md`).
- **Code Secrecy Profile:** packages are wrapped to each device's own key instead (`doc/arch.md`).

## Hosts

A host is issued with the device's host key and host data secret, both derived in the HSM from the chip ID. A replacement for a lost host is issued the same way
after the owner is authorized. Because the HSM can re-derive both, losing a host does not lose the data. A compromised host cannot be cut off,
since the device's host key cannot change, so the device is retired (R20).

## Retirement

Retiring a device marks it in the database. The TEE also offers a wipe, authorized by the host or the server, which erases TEE secure storage
(distribution key, pairings, records) and the user data on the card. eFuse keys cannot be erased, but without the host data secret the old data cannot be read.
