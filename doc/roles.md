# Roles

This document defines who can do what to a `thriller` device, and how developer builds work:
a developer can run their own application on their own device, and nowhere else.

## Roles

| Role | Holds | Can |
|---|---|---|
| **Manufacturer** | The HSMs: pairing, device, FPGA configuration, host and host data masters, the bitstream signing key, platform LMS keys, the device CA, the distribution key, sensor CA keys (unless the sensor maker holds them); the bitstream build service | Build and sign each device's platform packages; enroll devices; issue host and developer keys |
| **Application owner** | The application LMS keys (in an HSM) | Sign production LiteForth application releases, including their network policy. May be the manufacturer or a customer (open question A1) |
| **Developer** | A developer key for each device they own, for the current epoch | Build, sign and install applications for those devices only |
| **User** | A host, with its host authorization key, host data secret and recording key pair | Open host sessions, read recordings and user data, pair sensors, install signed updates |

A person can hold several roles. A developer is usually also the user of their own device.

## What a developer can change

Only the **application**: the LiteForth code that runs on the application core from its flash slot. The bitstream, the boot ROM and the loader are platform, signed by the manufacturer.
Because applications are verified by the loader, not by the configuration engine, a developer needs no bitstream signature and no signing service: a symmetric key bound to one device is enough,
and it works offline.

## The developer key

> working key = KDF(developer key, "developer" ‖ epoch), with epoch = counter 1 ÷ 1024

The developer key is a secure element slot the loader unwraps into hardware; the working key for the current epoch is derived from it in the derive path (`doc/hw.md`).
The HSM derives the same values when it issues a key to a developer who has shown they own the device. How ownership is shown is a business process.
A leaked developer key exposes only its own device, so no revocation is needed.

## Developer packages

A developer package carries:

- the application image, encrypted with AES-256-GCM under a package key derived from the working key;
- a header naming the target device's serial number and the epoch, marked as a developer build, with the developer's chosen network policy;
- a MAC over the whole package under a MAC key derived from the working key.

The developer's tools derive both package keys from the working key with labels, so one key from the HSM is all a developer needs.
Symmetric keys keep the tools simple and stateless, and they are quantum-safe.

## Installing a developer build

| Step | Production package | Developer package |
|---|---|---|
| Authenticate | LMS signature from the application owner, public key hash in secure element slot 9 or 10 | MAC under this device's working key for the current epoch |
| Decrypt | Distribution key | Package key derived from the working key |
| Version check | Not older than counter 1 | None; the counter is not touched |
| Install | Re-encrypted per line under a fresh install salt into the inactive slot (`doc/xip.md`) | Same |
| Header mode | *Production*, version | *Developer*, serial number, epoch; refused once the epoch has moved on |

Packages arrive over the UART from the developer's tools, over the network, or on a card.

**Developer builds never move counter 1.** Developers pick version numbers freely; a build numbered 9999 must not block production releases.

## Rotating developer keys

Each production application release says whether it **starts a new epoch**: its version number crosses a multiple of 1,024. When the loader installs such a release and advances counter 1 past it:

- every working key issued for the old epoch stops matching;
- every developer build installed under the old epoch is refused at boot;
- developer-mode user data from the old epoch is unreadable, because the developer data key includes the epoch;
- developers must ask for new keys.

The epoch lives in the secure element's counter, so a flash restore cannot revive an old one (R22).

## Running a developer build

- **Separate data.** The loader uses a separate data key, derived with a "developer" label and the epoch, so a developer build cannot read data written under a production build, and the reverse.
  Recordings made under a developer build are marked as such in their segment headers.
- **Visible state.** The loader reports developer mode to the host, the CLI and the attestation report, and the security block drives the LCD overlay band where the application cannot draw over it (F8).
  Labeling should say that a device running a developer build is not for clinical use.
- **CLI.** A developer session (authenticated by the loader under the working key, in the fabric) adds the application's debug commands. Production builds do not offer them.
- **Same isolation.** The developer application runs on the application core, with no path to any key (R37), and cannot change the loader or the bitstream.

## Returning to production

Installing any production application replaces the developer build. The loader then erases any developer image left in the other slot, so no developer build can become a fallback.

## What developers cannot do

- Run a build on a device whose developer key they do not have.
- Change the bitstream, the loader, or the counters.
- Read keys, production user data, or recordings made for someone else's host.
- Produce a package that installs on any other device.

## Tests

In `doc/test.md`: a developer package for another device is refused; a developer build cannot read production data, and the reverse; counter 1 is unchanged after developer installs;
a release that starts a new epoch makes old developer builds and keys fail; the overlay shows developer mode whatever the application draws.
