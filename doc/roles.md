# Roles

This document defines who can do what to a `thriller` device, and how developer builds work:
a developer can run their own application build on their own device, and nowhere else.

## Roles

| Role | Holds | Can |
|---|---|---|
| **Manufacturer** | The HSMs: device and host data masters, release RSA keys, platform LMS keys, distribution key, sensor CA keys (unless the sensor maker holds them) | Build and sign the bootloader and TEE; sign every image for secure boot; enroll devices; issue host and developer keys |
| **Application owner** | The application LMS keys (in an HSM) | Approve production application releases. May be the manufacturer or a customer (open question) |
| **Developer** | A developer key for each device they own, for the current epoch | Have builds signed for those devices only, and install them |
| **User** | A host, with its host key and host data secret | Open host sessions, which unlock user data; pair sensors; install signed updates |

A person can hold several roles. A developer is usually also the user of their own device.

## Why developer builds go through the signing service

Secure boot accepts only images signed with a release RSA key, and those keys must stay in the manufacturer's HSM, because an image signed with them
would boot on every device. So a developer cannot sign their own builds. Instead:

1. The developer builds their application with the normal toolchain.
2. They submit it to the manufacturer's **developer signing service**, with the target device's ID and a MAC under that device's developer key.
3. The service checks the MAC (the HSM derives the same key), writes a build descriptor into the image (mode *developer*, the device ID, the current epoch),
   signs it with the release RSA key, and returns it with a package MAC under the developer key.
4. The developer installs the package on their device, offline if they like.

The device-binding is enforced on the device, by the TEE, at install and at every boot: a developer build whose device ID or epoch does not match is refused,
and the bootloader falls back to the other slot. An image signed for one device is useless on any other.

Signing needs the service to be reachable from the developer's workstation, but installing does not.
Developers never hold a key that would work on another device, and no revocation is needed: a leaked developer key exposes only its own device.

The service signs only application images in developer mode, never a bootloader or TEE image. The image type is part of the signed descriptor,
and the bootloader checks it, so a developer image cannot be placed in a TEE slot (to confirm in ESP-IDF's image format, `doc/questions.md`).

## The developer key

> developer key = HMAC(device root, "developer" ‖ epoch)

The TEE derives it on the device; the HSM derives the same value when it issues a key to a developer who has shown they own the device. How ownership is shown is a business process.

## Rotating developer keys

A production release can invalidate every developer key in the field. Each production release says whether it **starts a new epoch**.
When the TEE installs such a release, it advances the developer epoch in its secure storage. From then on:

- every developer key issued for the old epoch stops matching;
- every developer build signed for the old epoch is refused at boot;
- developer-mode user data from the old epoch is unreadable, because the developer data key includes the epoch;
- developers must ask for new keys.

The epoch lives in TEE secure storage, not in eFuse, because eFuse anti-rollback bits are too few. A developer who restores an old flash image with a programmer
could revive an old epoch on their own device. That harms only their own device, and production data never reaches developer builds, so it is accepted (R22).

## Installing a developer build

| Step | Production package | Developer package |
|---|---|---|
| Authenticate the package | LMS signature from the application owner | MAC under this device's developer key |
| Decrypt | Distribution key | Key derived from the developer key |
| Version check | Not older than the newest installed version | None; the TEE's version record is not touched |
| Boot check (TEE) | Descriptor says *production* | Descriptor says *developer*, with this device's ID and the current epoch |
| Secure boot (bootloader) | Release RSA signature | Release RSA signature (from the signing service) |

**Developer builds never move the version record or the anti-rollback eFuses.** Developers pick version numbers freely; a build numbered 9999 must not
block production releases.

## Running a developer build

- **Separate user data.** The TEE derives a separate data key with a "developer" label and the epoch, so a developer build cannot read data written by a
  production build, and the reverse.
- **Visible state.** The TEE reports developer mode to the application and to the host, and can drive a status indicator the application cannot control.
  Labeling should say that a device running a developer build is not for clinical use.
- **Same isolation.** The developer build runs in user mode under the TEE like any application. It cannot reach keys, change the TEE, or move counters.

## Returning to production

Installing any production package replaces the developer build. The TEE then erases any developer image left in the other slot, so no developer build can
become a fallback.

## What developers cannot do

- Run a build on a device whose developer key they do not have.
- Change the bootloader, the TEE, or the anti-rollback state.
- Read keys or production user data.
- Produce an image that runs on any other device.

## Tests

In `doc/test.md`: a developer build for another device is refused; a developer build cannot read production data, and the reverse; the version record and eFuses
are unchanged after developer installs; a release that starts a new epoch makes old developer builds and keys fail; a developer image cannot boot from a TEE slot.
