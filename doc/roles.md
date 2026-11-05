# Roles

This document defines who can do what to a `thriller` device, and how developer builds work:
a developer can run their own application on their own device, and nowhere else.

## Roles

| Role | Holds | Can |
|---|---|---|
| **Manufacturer** | The HSMs: device, ECP5 and host data masters, release RSA keys, platform LMS keys, distribution key, sensor CA keys (unless the sensor maker holds them); the bitstream build service | Build and sign the C5 platform and each device's bitstream; enroll devices; issue host and developer keys |
| **Application owner** | The application LMS keys (in an HSM) | Sign production LiteForth application releases, including their radio policy (Wi-Fi and BLE on or off). May be the manufacturer or a customer (open question) |
| **Developer** | A developer key for each device they own, for the current epoch | Build, sign and install applications for those devices only |
| **User** | A host, with its host key, host data secret and recording key pair | Open host sessions, read recordings and user data, pair sensors, install signed updates |

A person can hold several roles. A developer is usually also the user of their own device.

## What a developer can change

Only the **application**: the LiteForth code that runs from the FPGA's flash. The C5's bootloader, TEE and firmware, and the FPGA's bitstream, are platform,
signed by the manufacturer. Because applications are verified by the C5's TEE, not by the C5's secure boot, a developer needs no RSA signature and no signing service:
a symmetric key bound to one device is enough, and it works offline.

## The developer key

> developer key = HMAC(device root, "developer" ‖ epoch)

The TEE derives it on the device; the HSM derives the same value when it issues a key to a developer who has shown they own the device.
How ownership is shown is a business process. A leaked developer key exposes only its own device, so no revocation is needed.

## Developer packages

A developer package carries:

- the application image, encrypted with Ascon-AEAD128 under a package key derived from the developer key;
- a header naming the target device's chip ID and the epoch, marked as a developer build, with the developer's chosen radio policy;
- a MAC over the whole package under a MAC key derived from the developer key.

The developer's tools derive both package keys from the developer key with labels, so one key from the HSM is all a developer needs.
Symmetric keys keep the tools simple and stateless (LMS needs careful one-time-key state, reasonable for a few releases a year, not for many builds a day), and they are quantum-safe.

## Installing a developer build

| Step | Production package | Developer package |
|---|---|---|
| Authenticate | LMS signature from the application owner | MAC under this device's developer key for the current epoch |
| Decrypt | Distribution key | Package key derived from the developer key |
| Version check | Not older than the TEE's record | None; the record is not touched |
| Install | Re-encrypted per line under a fresh install salt into the FPGA's flash (`doc/xip.md`) | Same |
| Boot | Mode *production* in the TEE's record | Mode *developer*, with the epoch it was installed under; refused once the epoch has moved on |

Packages arrive over BLE or the UART from the developer's tools, over Wi-Fi, or on a card.

**Developer builds never move the version record or the anti-rollback eFuses.** Developers pick version numbers freely; a build numbered 9999 must not block production releases.

## Rotating developer keys

Each production application release says whether it **starts a new epoch**. When the TEE installs such a release, it advances the developer epoch in its secure storage. From then on:

- every developer key issued for the old epoch stops matching;
- every developer build installed under the old epoch is refused at boot;
- developer-mode user data from the old epoch is unreadable, because the developer data key includes the epoch;
- developers must ask for new keys.

The epoch lives in TEE secure storage, not in eFuse. A developer who restores an old C5 flash image could revive an old epoch on their own device. That harms only their own device,
so it is accepted (R22).

## Running a developer build

- **Separate data.** The TEE uses a separate data key, with a "developer" label and the epoch, so a developer build cannot read data written under a production build, and the reverse.
  Recordings made under a developer build are marked as such in their segment headers.
- **Visible state.** The TEE reports developer mode to the host and the CLI, and tells the FPGA, which shows it on the LCD where the application cannot hide it.
  Labeling should say that a device running a developer build is not for clinical use.
- **CLI.** A developer session (BLE or UART, authenticated with the developer key) adds the application's debug commands. Production builds do not offer them.
- **Same isolation.** The developer application runs on the same FPGA CPU, with no read path to any key (R37), and cannot change the C5 or the bitstream.

## Returning to production

Installing any production application replaces the developer build. The TEE then erases any developer image left in the FPGA's other slot, so no developer build can become a fallback.

## What developers cannot do

- Run a build on a device whose developer key they do not have.
- Change the C5's software, the bitstream, or the anti-rollback state.
- Read keys, production user data, or recordings made for someone else's host.
- Produce a package that installs on any other device.

## Tests

In `doc/test.md`: a developer package for another device is refused; a developer build cannot read production data, and the reverse; the version record and eFuses
are unchanged after developer installs; a release that starts a new epoch makes old developer builds and keys fail; the LCD shows developer mode whatever the application does.
