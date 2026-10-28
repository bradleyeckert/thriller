# Roles

This document defines who can do what to a `thriller` device, and how the developer role works:
a developer can sideload their own encrypted, authenticated application onto their own device, and nowhere else.

## Roles

| Role | Holds | Can |
|---|---|---|
| **Manufacturer** | The HSM: KDF master keys, the platform LMS key, the developer master key | Build and sign platform updates; provision devices; issue developer keys |
| **Application owner** | The production application LMS key (in an HSM) | Sign production application releases for the whole fleet. May be the manufacturer or a customer (`doc/arch.md`, Open Question 6) |
| **Developer** | A developer key for each device they own | Sideload developer builds onto those devices only |
| **User** | The host authorization key for their device | Open host sessions, which unlock user data; install signed updates |

A person can hold several roles. A developer is usually also the user of their own device.

## The developer key

**One key per device.** A device's developer key is derived in the HSM:

> developer key = KDF(developer master key, secure element serial number)

It is written into a locked, non-readable slot of every secure element at provisioning, so any device can later be used for development
without being changed. The HSM gives a device's developer key to a developer when they show they own that device; how ownership is shown is a business process.

**It works only on that device.** A developer package is authenticated and encrypted under keys derived from that device's developer key.
No other device holds the same key, so the package is rejected everywhere else. A leaked developer key exposes only the one device it belongs to,
which is why no revocation is needed.

**It is symmetric.** Developer packages use HMAC-SHA256 and AES-256, not LMS. That keeps the developer's tools simple and stateless:
LMS needs careful one-time-key state management (`doc/arch.md`, LMS signing), which is reasonable for an HSM producing a few releases a year,
but not for a developer building many times a day. Symmetric keys are also quantum-safe.

## Developer packages

A developer package carries:
- the application image, encrypted with AES-256-GCM under a package encryption key derived from the developer key;
- a header naming the target device's secure element serial number, marked as a developer build;
- an HMAC-SHA256 over the whole package under a package MAC key derived from the developer key.

The developer's build tools derive both keys from the developer key with KDF labels, so one key from the HSM is all the developer needs.

## Installing a developer build

The loader handles a developer package like a production one, with four differences:

| Step | Production package | Developer package |
|---|---|---|
| Authenticate | LMS signature against the application public key | HMAC-SHA256 under this device's developer key, checked through the private key path |
| Decrypt | Distribution key | Package key derived from this device's developer key |
| Rollback check | Version must be above counter 1, which then advances | No check, and counter 1 is not touched |
| Mark | Header mode: production | Header mode: developer |

In both cases the loader re-encrypts the image per line into the inactive slot under a fresh install salt (`doc/xip.md`, Per-line GCM),
and records the install in the security event log.

**Counter 1 must not move for developer builds.** Developers pick version numbers freely. If a developer build could advance counter 1, a build marked
version 9999 would block every future production release. Rollback protection is for users, and a developer installing their own old build harms only themselves.

## Running a developer build

- **Separate user data.** While a developer build runs, the loader's user data service uses a separate data key, derived from the data key with a "developer" label.
  A developer build cannot read data written under a production build, and the reverse. A device that was used in production and then for development
  does not hand its production data to sideloaded code.
- **Visible state.** The loader tells the application, through the mailbox status service, that it is running a developer build, and can drive a status
  indicator the application cannot control. For a medical device, labeling should say that a device running a developer build is not for clinical use.
- **Everything else is unchanged.** The application core has the same isolation as for a production build, and the loader's protections all still apply.

## Returning to production

Installing any production package replaces the developer build, with the usual rule: its version must be above counter 1.
Since developer builds never moved counter 1, the device accepts the same production releases it would have accepted before.

## What developers cannot do

- Install a developer build on a device whose developer key they do not have.
- Change the platform (bitstream or loader). Platform updates are signed by the manufacturer only.
- Read or change counters, keys, or production user data.
- Produce a package that installs on any other device.

## Hardware and test impact

- **Hardware:** the SHA-256 core's key insertion (`doc/hw.md`, Key paths) must accept a key unwrapped from the secure element, not only the pairing key,
  so developer-package HMACs and the image key derivation run without exposing keys. No other new hardware is needed.
- **Tests** (to add to `doc/test.md`): a developer package for another device is rejected; a developer build cannot read production user data, and the reverse;
  counter 1 is unchanged after any number of developer installs; a production release installs normally after developer builds;
  two developer builds with the same version number produce different image keys.
