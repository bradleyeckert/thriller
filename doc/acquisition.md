# Acquisition and Recordings

The device records like a high-speed EEG: four 24-bit channels from two stereo CODECs, streamed to the MicroSD card or over Wi-Fi at 0.4 to 0.9 MB/s.
EEG data is health data and can identify a person, so recordings are the primary asset (`doc/arch.md`).

## Hardware

| Part | Role |
|---|---|
| 2 × NAU88C22 (24-bit stereo CODEC) | Four acquisition channels; one CODEC's DAC and speaker driver also drives the alarm speaker |
| ECP5 | Masters both I2S buses and generates the CODECs' master clock; controls the CODECs over I2C; generates the watermark; encrypts recordings; drives the LCD |
| LCD panel | Inside the enclosure, behind a window |
| Speaker | Inside the enclosure, for audible alarms |
| Enclosure | Tamper-evident seal |

The C5 has one I2S controller, so the ECP5 provides the two I2S masters. Four channels at 48 kHz in 24 bits come to about 0.58 MB/s before framing.

**One clock.** The C5 and the ECP5 run from the same oscillator, and the ECP5 derives the CODECs' master clock from it. The watermark generator, the sample clock and the C5
then share one timebase.

## Data path

| Hop | Contents | Protection |
|---|---|---|
| CODEC → ECP5 (I2S) | Samples | None possible; tamper-evident seal; watermark |
| Inside the ECP5 | Samples, to the application (display, processing) and the recording engine | Inside the FPGA |
| ECP5 → LCD | Displayed waveforms | Tamper-evident seal |
| ECP5 → C5 (PARLIO) | Recording ciphertext | Encrypted to the host by the recording engine |
| C5 → MicroSD card or Wi-Fi | The same ciphertext | Encrypted to the host; TLS on Wi-Fi as well |

The C5 firmware, including the Wi-Fi and BLE stacks, only ever handles ciphertext. A bug in a network stack cannot leak the recording (R39).
Plaintext exists only in the sealed enclosure: on the I2S buses, the LCD bus, the watermark injection nets, and inside the ECP5 (R38).

## Recording encryption

Recordings are encrypted so that **the device can write them but not read them back.**

1. **Recipient keys.** The host (and optionally a clinic server) gives the device its ML-KEM-768 public key during an authenticated host session. The TEE stores it.
2. **Segments.** A recording is cut into segments, for example a few minutes each. For each segment the TEE draws a fresh AES-256 segment key, encapsulates it to each recipient's
   public key, and builds the segment header: device ID, recording ID, segment number, start sample index, the watermark schedule's parameters, and the encapsulations.
3. **Keys to the FPGA.** The TEE sends the segment key and the watermark key (below) to the FPGA over the link. The recording engine encrypts the stream in AES-256-GCM blocks
   (for example 4 KB) with the block number as the nonce and the segment header as associated data in the first block.
4. **Erase.** At the end of the segment, the TEE and the FPGA erase the segment key. Nothing on the device can decrypt that segment again.
5. **Order.** Block and segment numbers make dropped, reordered or substituted blocks and segments detectable at the host.
6. **Provenance (optional).** The TEE signs each segment's header and final block tag with a per-device ML-DSA key registered at enrollment, so anyone can check which device made a recording.

A thief who breaks the device, even both chips, gets the segment in progress at most, never earlier recordings. The host, holding the private key, decrypts and checks everything.

## Watermark

**Purpose.** Detect data that did not come live through this device's CODECs: a replay or substitution on an I2S bus, or anywhere after it.

**What it is.** Each CODEC input gets a sum of several sine waves whose frequencies and phases come from a keyed schedule and change every hop:

- Watermark key = HKDF(segment key, "watermark"), computed by the TEE and sent to the FPGA with the segment key; the host derives the same from the segment key it decrypts.
- For each CODEC and each hop *h*: frequencies and phases = AES-CTR(watermark key, CODEC ‖ *h*), mapped into the EEG band.
- Hops are short (about 10 to 50 ms), and the amplitude is so low that no single hop rises above the noise, even in its own FFT bin.
  Each peak really could be noise. The host, knowing the schedule, integrates hundreds of hops coherently: about a second of data gives roughly 30 to 40 dB of gain.
- The FPGA generates it with phase accumulators and a sine table, through a sigma-delta output per CODEC, an RC filter and a large resistor into the CODEC input,
  **after** the front-end amplifier and away from any node connected to the patient (IEC 60601-1 leakage limits).
- At LSB level it adds a negligible amount of noise (a watermark 30 dB below the noise raises it by about 0.004 dB), so it is left in, not subtracted.

**Why it holds against spoofing.** An attacker on the I2S bus sees nothing to estimate in any one hop, cannot predict the next hop without the key, and cannot transplant the
watermark from live data onto forged data, because it is spread through the same band as the signal. Delaying the stream puts it out of step with the schedule, which follows the
sample counter.

**Detecting a bad watermark, not just a good one.** The host tests each window against every schedule it knows, and classifies:

| What the host finds | Meaning |
|---|---|
| This CODEC's schedule, in step | Genuine |
| This recording's schedule, out of step | Replay or delay; the offset identifies the reused segment |
| The other CODEC's schedule | The buses were swapped |
| A schedule from an earlier recording | Replay from an old recording |
| No known schedule | Foreign data, analog substitution, or an injection fault |
| Narrowband energy that fits no schedule | An attempt to fake a watermark |

**Live check.** The FPGA can run the same correlation in hardware for the current schedule and report a missing or misaligned watermark to the application and the TEE,
which can sound the alarm during the recording. The correlator reports only results; the CPU never sees the schedule.

**Fault or attack.** The C5's ADC monitors the injection nets. A watermark present at the net but missing from the data points to the bus or the CODEC; one missing at the net points
to the injection hardware.

**Limits.**

- The injection nets carry the watermark in the clear. Someone inside the enclosure who taps both an I2S bus and an injection net could re-synthesize it onto forged data in real time.
  Short, inner-layer, shielded routing ending at the CODEC pin makes that harder; the seal makes it evident. The watermark is a strong obstacle, not cryptographic proof.
- It proves the data passed through this CODEC recently. It does not prove the analog input came from the patient, and a small edit shorter than the integration window survives.
- The watermark must not come from the CODECs' own DACs, whose samples would cross the I2S bus it protects.

## Alarms

The speaker is driven through a CODEC by the FPGA. The TEE sends alarms over the link: sensor faults (`doc/sensor.md`), watermark failures, tamper events.
Whether a safety alarm needs a path that does not depend on the FPGA application, such as a C5-driven tone into the speaker amplifier, is an open question.

## Open questions

See `doc/questions.md` (Acquisition rows).
