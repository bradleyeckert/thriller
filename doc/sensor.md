# Temperature Sensor

The temperature sensor sits outside the box, at the end of a two-way link to the C5. It is replaceable, and a new sensor must pair
**without a network**. Readings need authentication, not encryption.

## Requirements

1. A reading the device acts on came from a genuine sensor, the one paired with this device, and is recent.
2. Commands to the sensor are authenticated too.
3. Pairing works offline. The enrollment server confirms the pairing when the device is next online.
4. Breaking one sensor exposes only that sensor.
5. A missing, late or rejected reading puts the device in its safe state. It never quietly reuses an old value.
6. Quantum-safe, like the rest of the design.

## The sensor end

The sensor contains a small microcontroller with:

- a true random number generator;
- storage for its private key and pairing key that its debug port cannot read;
- ML-KEM-768 decapsulation (FIPS 203) and a MAC (Ascon-AEAD128 from NIST SP 800-232, or HMAC-SHA256; the choice is open);
- a unique serial number.

ML-KEM decapsulation needs on the order of a few hundred thousand cycles on a Cortex-M4 class part, and runs only when pairing.

## Sensor certificates

At the sensor factory:

1. The sensor generates its own ML-KEM-768 key pair. The private key never leaves it.
2. The sensor manufacturer's HSM signs a certificate with ML-DSA-44 (FIPS 204): format version, serial, model, manufacture date,
   a hash of the calibration data, the ML-KEM public key, and the signing key's ID.
3. The certificate is stored in the sensor, and the serial and certificate hash go into the enrollment database (`doc/enrollment.md`).

The public keys of the sensor CA (a main and a backup) are built into the TEE image. ML-DSA is used rather than LMS because the factory signs
one certificate per sensor, and LMS's one-time-key state is risky at that volume. LMS stays for firmware releases, which are few.

A certificate is about 3.7 KB (1,184-byte public key, 2,420-byte signature, and fields). It crosses the link once per pairing.

## Pairing

Pairing runs when the TEE sees a sensor whose serial does not match its stored pairing.

| Step | Device (TEE) | Sensor |
|---|---|---|
| 1 | Request the certificate | Send the certificate |
| 2 | Check the CA signature, the format, the model, and that the serial is not on the denylist | |
| 3 | Encapsulate to the sensor's public key: ciphertext *ct*, shared secret *ss*. Send *ct*, a fresh nonce *Nd*, and the device ID | Decapsulate *ct* to get *ss*. Pick a fresh nonce *Ns* |
| 4 | | Derive the pairing key and confirmation keys (below). Send *Ns* and its confirmation MAC |
| 5 | Derive the same keys, check the sensor's MAC, send the device's confirmation MAC | Check the device's MAC; store the pairing key, replacing any earlier one |
| 6 | Store the pairing record: serial, certificate hash, pairing key, time, state *unconfirmed*. Log it | |

> pairing key = HKDF(*ss*, salt = *Nd* ‖ *Ns*, info = "pair" ‖ device ID ‖ serial ‖ SHA-256(certificate) ‖ SHA-256(*ct*))

The confirmation MACs cover the whole transcript, with "sensor" and "device" labels so neither can be reflected. Only a sensor that holds the
certified private key can recover *ss*: with any other key, ML-KEM's implicit rejection yields an unrelated secret, and the sensor's MAC fails.

**The sensor does not authenticate the device.** Anyone can pair a genuine sensor to their own equipment. That exposes nothing, since readings
are not secret, and pairing a sensor away from a device shows up on the device as a failed session. Device certificates could close this later if the sensor accepts
commands that matter.

**One sensor at a time** in the base design. A new pairing replaces the old one, and both events are logged.

## Server confirmation

The next time the device reaches the enrollment server (through the host, or Wi-Fi if enabled), it reports each unconfirmed pairing:
serial, certificate hash and pairing time. The server checks that:

- the serial is enrolled and the certificate hash matches the database;
- the serial is not on the denylist;
- the same serial is not paired to other devices in a pattern that suggests a clone.

The server answers *confirmed* or *rejected*, authenticated under the device's identity key, together with the current denylist.
On *rejected*, the TEE removes the pairing, logs it, and the FPGA application raises an alert. Denylists also travel inside every update package,
so offline devices receive them too.

How long a pairing may stay unconfirmed, and what the device does meanwhile, is a clinical decision (open question).

## Sessions

A session starts at power-up, after a link fault, and periodically (for example hourly):

1. The TEE sends a fresh nonce *Nd'*; the sensor answers with *Ns'* and a MAC.
2. Each side derives a key per direction: HKDF(pairing key, salt = *Nd'* ‖ *Ns'*, info = "session" ‖ direction).
3. Every frame carries a type, a 32-bit counter, the payload and a tag (128-bit). The counter must strictly increase per direction within a session.

A CRC may protect the physical layer against noise, but it is not a security control.

## Freshness and timing

A MAC proves who sent a reading, not when. So:

- **The device asks.** Each reading request carries the request counter, and the sensor's answer is bound to it, along with the sample's age as the sensor reports it.
- **The TEE times the exchange** with a timer the C5 firmware cannot change: from issuing the request to receiving the answer. Age of the reading = that round-trip time + the sample age the sensor reports.
  The C5 firmware moves the frames (`doc/c5.md`, TEE), so it can only make a reading look older, never newer.
- **The TEE rejects a reading older than the maximum reading age,** a clinical parameter.

Anyone on the link can delay frames but not forge them, so the worst they can do is make readings late, and late readings are rejected.

## Failure handling

| Event | Response |
|---|---|
| A frame fails its MAC or counter check | Drop it; count it; log it. Several in a row restarts the session |
| No valid reading within the maximum reading age | Safe state and alarm |
| Session cannot be established | Safe state and alarm; log |
| Certificate invalid or denylisted | Refuse to pair; alarm; log |
| Pairing rejected by the server | Remove the pairing; alarm; log |

The TEE passes each reading, with its age and status, to the FPGA application over the authenticated link (`doc/fpga.md`). The application defines the safe state,
and must not act on a reading the TEE has not passed. The time a reading spends crossing the link is added to its age.

## Physical layer

The link runs on the C5's peripherals: a UART for a byte-oriented link, the RMT for a custom pulse protocol, or MCPWM capture (3 channels at 160 MHz)
and compare outputs where the protocol needs precise timing. ETM can connect GPIO edges and timers without software. The choice depends on the
sensor's existing interface and the cable (open question). The protocol above does not depend on it.

The sensor link is wired, and nothing in it depends on Wi-Fi or BLE being up.

## Calibration

If calibration coefficients live in the sensor, their hash is in the certificate, and the coefficients themselves come over an authenticated session.
A sensor cannot then be given someone else's calibration without failing the check.
