# Acquisition and Recordings

The device records like a high-speed EEG: four 24-bit channels from two stereo CODECs, streamed to the MicroSD card or over Wi-Fi at 0.4 to 0.9 MB/s.
EEG data is health data and can identify a person, so recordings are the primary asset (`doc/arch.md`).

## Hardware

| Part | Role |
|---|---|
| 2 × NAU88C22 (24-bit stereo CODEC) | Four acquisition channels; one CODEC's DAC and speaker driver also drives the alarm speaker |
| FPGA (PG2L50H; ECP5 fallback) | Masters both I2S buses and generates the CODECs' master clock; controls the CODECs over I2C; encrypts recordings; drives the LCD |
| LCD panel | Inside the enclosure, behind a window |
| Speaker | Inside the enclosure, for audible alarms |
| Enclosure | Tamper-evident seal |

The C5 has one I2S controller, so the FPGA provides the two I2S masters. Four channels at 48 kHz in 24 bits come to about 0.58 MB/s before framing.

## Data path

| Hop | Contents | Protection |
|---|---|---|
| CODEC → FPGA (I2S) | Samples | None possible; tamper-evident seal |
| Inside the FPGA | Samples, to the application (display, processing) and the recording engine | Inside the FPGA |
| FPGA → LCD | Displayed waveforms | Tamper-evident seal |
| FPGA → C5 (PARLIO) | Recording ciphertext | Encrypted to the host by the recording engine |
| C5 → MicroSD card or Wi-Fi | The same ciphertext | Encrypted to the host; TLS on Wi-Fi as well |

The C5 firmware, including the Wi-Fi and BLE stacks, only ever handles ciphertext. A bug in a network stack cannot leak the recording (R39).
Plaintext exists only in the sealed enclosure: on the I2S buses, the LCD bus, and inside the FPGA (R38). Someone who breaks the seal could also replay or substitute
samples on an I2S bus; nothing in the design detects that (R40).

## Recording encryption

Recordings are encrypted so that **the device can write them but not read them back.**

1. **Recipient keys.** The host (and optionally a clinic server) gives the device its ML-KEM-768 public key during an authenticated host session. The TEE stores it.
2. **Segments.** A recording is cut into segments, for example a few minutes each. For each segment the TEE draws a fresh 256-bit segment key. For each recipient it runs ML-KEM encapsulation to the
   recipient's public key and wraps the segment key with AES-256-GCM under a key derived from the shared secret. It then builds the segment header: device ID, recording ID, segment number, start sample index, build mode, and the encapsulations with their wrapped keys.
3. **Key to the FPGA.** The TEE sends the segment key to the FPGA over the link. The recording engine encrypts the stream in AES-256-GCM blocks, in the FPGA's hard AES block,
   (for example 4 KB) with the block number as the nonce and the segment header as associated data in the first block.
4. **Erase.** At the end of the segment, the TEE and the FPGA erase the segment key. Nothing on the device can decrypt that segment again.
5. **Order.** Block and segment numbers make dropped, reordered or substituted blocks and segments detectable at the host.
6. **Provenance (optional).** The TEE signs each segment's header and final block tag with a per-device ML-DSA key registered at enrollment, so anyone can check which device made a recording.

A thief who breaks the device, even both chips, gets the segment in progress at most, never earlier recordings. The host, holding the private key, decrypts and checks everything.

## Alarms

The speaker is driven through a CODEC by the FPGA. The TEE sends alarms over the link: sensor faults (`doc/sensor.md`) and security events.
Safety alarms do not need a path independent of the FPGA application.

## Open questions

See `doc/questions.md` (Acquisition rows).
