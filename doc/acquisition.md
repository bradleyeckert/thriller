# Acquisition and Recordings

One foreseen application streams digitized audio or video to the MicroSD card, whose files are sent to a server.
Assuming the data is biometric, recordings are the primary asset (`doc/arch.md`).

## Hardware

| Part | Role |
|---|---|
| 24-bit stereo CODEC(s) | One CODEC's DAC and speaker driver also drives the alarm speaker |
| FPGA, application core domain | Masters both I2S buses and generates the CODECs' master clock; controls the CODECs over their own I2C bus; drives the LCD |
| FPGA, loader core domain | The recording engine, segment keys, the card |
| LCD panel | Inside the enclosure, behind a window |
| Speaker | Inside the enclosure, for audible alarms |
| Enclosure | Tamper-evident seal |

## Data path

| Hop | Contents | Protection |
|---|---|---|
| CODEC → FPGA (I2S) | Samples | None possible; tamper-evident seal |
| Application core domain | Samples, for display and processing | Inside the FPGA |
| Application → recording engine (sample FIFO) | Samples the application wants recorded | A one-way FIFO into the loader domain; the engine accepts samples only while a segment key is loaded |
| FPGA → LCD | Displayed waveforms | Tamper-evident seal |
| Recording engine → card or network | Recording ciphertext | Encrypted to the host |

Plaintext exists only in the sealed enclosure: on the I2S buses, the LCD bus, and inside the FPGA (R38). Someone who breaks the seal could also replay or substitute samples on an I2S bus;
nothing in the design detects that (R40). An enclosure-crossing data link, when present, carries only ciphertext (R39).

## Recording encryption

Recordings are encrypted so that **the device can write them but not read them back.**

1. **Recipient keys.** The host (and optionally a clinic server) gives the device its ML-KEM-768 public key during an authenticated host session. The loader stores it in the records region of the flash, under the application key.
2. **Segments.** A recording is cut into segments, for example a few minutes each. For each segment the loader draws a fresh 256-bit segment key from the TRNG into the recording engine's key register.
   For each recipient it runs ML-KEM encapsulation to the recipient's public key and wraps the segment key with AES-256-GCM under a key derived from the shared secret (the one place the loader's code
   handles key material, masked; `doc/hw.md`). It then writes the segment header: device serial, recording ID, segment number, start sample index, build mode, and the encapsulations with their wrapped keys.
3. **Stream.** The application feeds samples into the sample FIFO; the recording engine encrypts them in AES-256-GCM blocks (for example 4 KB) in the hard AES block, with the block number as the nonce
   and the segment header as associated data in the first block, and the loader writes the ciphertext to the card or sends it over the network.
4. **Erase.** At the end of the segment the engine's key register is cleared. Nothing on the device can decrypt that segment again.
5. **Order.** Block and segment numbers make dropped, reordered or substituted blocks and segments detectable at the host.
6. **Provenance (optional).** The loader signs each segment's header and final block tag with a per-device ML-DSA key kept in the records region, registered at enrollment (open question Q5).

A thief who breaks the device gets the segment in progress at most, never earlier recordings. The host, holding the private key, decrypts and checks everything.

## Alarms

The speaker is driven through a CODEC by the application. The loader raises alarms through the mailbox (sensor faults, security events) and also drives the LCD overlay band directly,
so an alarm and the developer-mode mark are visible whatever the application draws (F8). Safety alarms do not need a path independent of the application beyond that.

## Open questions

See `doc/questions.md` (Acquisition rows).
