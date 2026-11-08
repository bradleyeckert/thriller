# Enrollment

Every device and every sensor is entered into the manufacturer's enrollment database when it is made. The ecosystem uses the database to:

- recognize genuine devices and sensors, and flag any identity it does not know;
- issue keys for hosts and developer builds;
- build each device's encrypted bitstream, and its platform packages;
- confirm sensor pairings and catch cloned sensors;
- refuse updates to anything not enrolled.

A device does not need to be online to work. It reports to the server when it can: over the network if the application owner has enabled the port, otherwise through the host.

## Keys held by the manufacturer

All keys stay inside HSMs. The database holds identities and records, never secret keys. Every per-device key is derived from a master and the secure element's serial number,
so the HSM can recompute any device's keys without storing them.

| Key | Used for |
|---|---|
| Pairing master | KDF(pairing master, serial, version): the pairing key of each bitstream release for each device |
| Device master | The application, data, developer, log and symmetric identity keys of each device: KDF(device master, serial, label) |
| FPGA configuration master | Each device's bitstream encryption key: KDF(master, serial), sized for the family (256 bits on the Logos2, 128 on the ECP5) |
| Host master | Each device's host authorization key |
| Host data master | Each device's host data secret. Separate from the device master because the device must never be able to compute it |
| Distribution key | Encrypting production application packages; written into each device at enrollment |
| Bitstream signing key | The vendor's bitstream signature (RSA-2048 on the Logos2); public key data in every FPGA's eFuses |
| Platform LMS keys, main and backup | Signing platform release manifests; public keys in the boot ROM |
| Application LMS keys, main and backup | Signing application packages; hashes in secure element slots 9 and 10. If the application owner is a different company, it holds these (`doc/roles.md`) |
| Device CA (ECDSA P-256), signer and root | Certifying each device's identity public key |
| Sensor CA keys (ML-DSA), main and backup | Signing sensor certificates. May belong to the sensor maker |

Separate masters per purpose, dual control and audit logging in the HSMs are the controls against an insider (R19).

## Device enrollment

At the end of the production line, inside the controlled area:

1. **Read the secure element's serial number** over its I2C bus, through the FPGA's factory bitstream or a station fixture.
2. **Provision the secure element** (`doc/se.md`). Either Microchip delivers TrustCUSTOM parts already configured and keyed from the HSM's derivations, or the station writes the configuration,
   the derived keys, the distribution key, the check values, the LMS key hashes and the record, locks the zones, has the part generate its identity key pair (GenKey, slot 7), reads the public key,
   obtains the device certificate from the device CA and writes it into slot 8.
3. **Program the FPGA** over JTAG: its configuration key (from the HSM) into eFuse, the bitstream signing public key data where the family authenticates, the settings that refuse unencrypted or unsigned
   bitstreams and disable readback (`fpga/<family>/`). The key crosses the JTAG link once.
4. **Build the bitstream.** The bitstream build service makes this device's release-1 bitstream (below), with pairing key version 1 as its own key and version 0 as its inherited key.
5. **Program the flash** with the bitstream in slot A, the loader image and the application image, each encrypted per line under this device's application key (the station derives the install keys
   the same way the loader will), and a boot record.
6. **First boot.** The device pairs with the secure element (slot 0 holds version 0), its loader confirms the install and ratchets slot 0 to version 1, the sensor and host records are empty.
7. **Check.** The station sends a nonce; the device answers with an attestation report under both identity keys; the HSM checks the MAC and the ECDSA signature against the new certificate.
   This proves the secure element, the bitstream's pairing key, the FPGA's configuration key and the flash images all agree.
8. **Permanently disable the FPGA's JTAG** where the family allows it, after the boundary-scan test.
9. **Record** the serial number, device certificate, date, station, image versions and an eFuse summary in the database.
10. **Close enrollment.** The loader writes the enrolled state into slot 13. The secure element's keys are locked, the FPGA's key and locks are one-time settings, so neither chip can be enrolled
    or paired again. Replacing either chip means returning the board to the factory.

## Bitstream build service

Each device has its own bitstream, because its pairing keys are inside it (`doc/fpga.md`). For each FPGA release:

1. The family's tools build the common design once, with placeholder constants in the key-source block RAM.
2. For each device, the HSM derives the inherited and own pairing keys for the versions the package covers, and the device's configuration key, and releases them to the build service for that job only.
3. A family-specific script writes them into the block RAM contents of the routed design, without placing and routing again, encrypts the bitstream under the device's configuration key,
   signs it with the vendor flow where the family authenticates, and erases the keys.
4. The platform package for the device (bitstream, loader image, version, inherited and own key versions) gets its inclusion proof in the release manifest, which the HSM signs once with the platform LMS key.

For the Logos2 this is Pango Design Suite from the command line; how it writes per-device block RAM contents into a routed design is open question F1. For the ECP5 fallback it is Lattice Diamond's
ECO editor from a headless Tcl script (`fpga/ecp5/`). The service handles per-device keys in plaintext, so it is isolated, audited, dual-controlled, and gets keys only per job (R42).

Because a device's bitstream must carry the pairing key the device currently holds, the server builds a device's platform package from the key version the device last reported, and
offline packages are prepared the same way for one device.

## Sensor enrollment

At the sensor factory, each sensor generates its ML-KEM key pair and receives an ML-DSA certificate (`doc/sensor.md`). The serial, model, certificate hash and date go into the database.

## Contact with the server

When the device reaches the enrollment server, either side proves itself under the device's symmetric identity key, over nonces from both (the secure element's MAC and CheckMac, slot 12).
After authentication, the exchange runs under a session key derived from both nonces, like a host session. During contact the device:

- sends its attestation report: versions, counters, pairing key version, lifecycle state (`doc/se.md`);
- uploads its event log since the last contact;
- reports unconfirmed sensor pairings, and receives *confirmed* or *rejected* for each;
- receives the current sensor denylist;
- can receive an update package built for its reported state.

## Detecting unknown identities

| Observation | Meaning |
|---|---|
| A serial number not in the database | A device that was never enrolled, or a counterfeit |
| A known serial whose MAC or signature fails | A forged identity |
| One serial reporting from two places, or with counters that went backward | A cloned secure element (R46); retire the identity |
| A device marked retired or stolen that makes contact | Recovered or misused device |
| A sensor serial not in the database, or whose certificate hash differs | Counterfeit sensor |
| One sensor serial confirmed on several devices at overlapping times | A cloned sensor; the serial goes on the denylist |

## Updates

Updates do not need a network, but they do need enrollment:

- **Offline packages** (on the MicroSD card or from the host): application packages are encrypted under the distribution key, which only enrolled devices hold;
  platform packages are built for one device and work nowhere else. The loader checks the LMS signature and the version.
- **Online updates** come from the update server after the device has authenticated. The server sends only to enrolled devices in good standing, and only current releases.
  A fake access point or server can withhold updates but cannot get a forged or old package past the loader (R29).
- **Developer builds** carry a MAC under one device's developer key and install only there (`doc/roles.md`).
- **Code Secrecy Profile:** application packages are wrapped to each device's own key instead (`doc/arch.md`).

## Hosts

A host is issued with the device's host authorization key and host data secret, both derived in the HSM. The host generates its own ML-KEM-768 key pair for recordings and gives the device its
public key in an authenticated host session; the private key never leaves the host. A replacement for a lost host is issued the same way after the owner is authorized. Recordings can only be
decrypted with the host's recording private key, so that key must be backed up by the host's owner (or recordings also encapsulated to a clinic server's key). A compromised host cannot be cut off,
since the device's host authorization key cannot change, so the device is retired (R20).

## Retirement

Retiring a device marks it in the database and, when the device is next reached, writes the retired state into slot 13; the loader then refuses sessions. The loader also offers a wipe,
authorized by the host or the server, which erases the records region and the user data on the card. Secure element keys cannot be erased, but without the host data secret the old data cannot be read.
