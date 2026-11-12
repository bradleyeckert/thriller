# It's all about the ROT
Root of trust for an FPGA-based device platform, built from three parts: an FPGA with an encrypted and authenticated bitstream,
one QSPI NOR flash, and an ATECC608C secure element. The FPGA is a model of the ASIC that replaces it
at volume (`doc/ics55.md`), so everything the FPGA does is generic RTL and firmware, and everything that depends on the FPGA family lives in `fpga/<family>/`.

- **The FPGA is the root of trust and the application.** Its configuration engine authenticates and decrypts the bitstream with the device's own eFuse key;
  the bitstream holds a boot ROM, a loader core that owns every key path and security decision, and an application core that runs the LiteForth application
  and can reach nothing secret. Both cores execute in place from the flash through a decrypting, authenticating cache (`doc/xip.md`).
- **The secure element holds what must survive the bitstream:** the device's keys, its identity, and the two monotonic counters that stop rollback.
  It releases a key only to a bitstream that holds the current pairing key, and the data key only after the host has proved itself to the secure element directly (`doc/se.md`).
- **The flash is untrusted storage** for the bitstream, the loader and the application, every line of code authenticated as it is fetched (`doc/flash.md`).

The platform will encrypt files, so the ATECC608C is provisioned accordingly.
To support DSP applications, audio CODECs are planned for.

## Documents

| Document | Contents |
|---|---|
| This README | Overview: chipset, keys, boot, updates, recordings, sensor, host sessions, the network and the CLI |
| `doc/arch.md` | Trust boundary, threat model, risk assessment, algorithm bill of materials |
| `doc/hw.md` | Hardware modules: the two cores, the mailbox, the shared XIP engine, key paths, boot and lockdown, the key-source interface |
| `doc/se.md` | Secure element: slot map, counters, the pairing-key ratchet, attestation, the I2C protocol |
| `doc/flash.md` | Flash map: bitstream slots and multi-boot, loader and application slots, boot record, install order, staging |
| `doc/fpga.md` | The FPGA, family-neutral: configuration from flash, per-device bitstreams, fallback, TRNG, resources |
| `fpga/` | Everything family-specific, one folder per FPGA family, and the wish list a family must meet |
| `doc/xip.md` | Execute in place: per-line Ascon-AEAD128 for the loader and the application |
| `doc/acquisition.md` | CODECs, data path, recording encryption, LCD, speaker and alarms |
| `doc/sensor.md` | Replaceable temperature sensor: certificates, offline pairing, authenticated sessions, fail-safe behavior |
| `doc/enrollment.md` | Device and sensor enrollment, secure element provisioning, the bitstream build service, detecting unknown identities, updates |
| `doc/roles.md` | Manufacturer, application owner, developer and user; device-bound developer builds |
| `doc/test.md` | Test plan and fault-injection campaigns |
| `doc/fda.md` | FDA security architecture views |
| `doc/network.md` | Network security posture: why the device cannot be a network attack vector, for IT departments and the FDA |
| `doc/fips.md` | FIPS 140-3 as the long-term target: module boundary, approved algorithms, DRBG, self-tests, roles, zeroization, and what it changes now |
| `doc/ics55.md` | ASIC migration to the ICS55 55 nm process: the PUF behind the key-source interface |
| `doc/questions.md` | Every open question in one matrix, and the decisions taken |

## Chipset

- **FPGA with an encrypted and authenticated bitstream.** Current choice: **Pango Logos2 PG2L50H-6IFBG484** (50K-class), which authenticates bitstreams before decrypting them
  (`fpga/logos2/`). No family offers a hardened cipher usable from the fabric, so all symmetric cryptography runs in a masked Ascon core of our own (`doc/hw.md`). It configures itself from the flash at power-up in master SPI mode, with the vendor's multi-boot fallback to a second bitstream. Fallback: **Efinix Titanium Ti60** (`fpga/ti60/`), which meets the same hard requirements with RSA-4096 authentication
  and a scripted BRAM content updater. Candidates: Microchip PolarFire, Lattice CrossLink-NX. The ECP5 and Gowin GW5A were evaluated and dropped for lacking bitstream authentication. The requirements a family must meet are in `fpga/README.md`.
- **QSPI NOR flash**, 32 MB proposed: bitstream slots, loader images (A/B), application images (A/B), the boot record and a recovery staging area (`doc/flash.md`). Nothing in it is trusted.
- **ATECC608C** secure element (Microchip), on an I2C bus that never leaves the sealed enclosure. The 608C rather than the 608B for its NIST SP 800-90A/B/C-certified random number generator and its updated physical countermeasures. Custom configuration (TrustCUSTOM, or blank parts provisioned at enrollment); the Trust Platform
  provisioning service can carry the per-device key material and the device certificate. Second source: pin-compatible parts claiming compatibility, to be qualified.
- **2 × NAU88C22** stereo CODECs: four acquisition channels, and the speaker driver (`doc/acquisition.md`).
- **LCD panel and speaker** inside the enclosure, which carries a tamper-evident seal.
- **MicroSD card socket**, driven by the FPGA: encrypted recordings and user data, the event log, offline update packages.
- **ESP-PSRAM64H** (8 MB QSPI PSRAM): a ring buffer for the encrypted recording stream between the recording engine and the card or the network, riding out card write latency and network stalls.
  It holds ciphertext only, about ten seconds of it at the full rate, and is outside the trust boundary like the card (`doc/acquisition.md`, Stream buffer).
- **Sensor connector**: a wired, two-way link to a replaceable temperature sensor, driven by the loader core (`doc/sensor.md`).
- **UART** (USB-UART bridge): status reports, and the wired path for host sessions, updates and the CLI.
- **Ethernet**, 10/100 over RMII to a PHY such as the LAN8742A: the path to the server for attestation, updates, uploads and sensor-pairing confirmation. The FPGA speaks only UDP on one port,
  implemented in hardware; there is no network stack anywhere in the device (see Network). An untrusted edge proxy on site relays the datagrams to the server over TLS where IT requires port 443.
- **YXC YSN8130E real-time clock** (3225 module with built-in crystal, 0.9 µA, open-drain /INT that survives a VDD cycle), backed by two SR44 cells; A10 for the remaining checks. Its time is untrusted and never stands in for the server's time beacons (`doc/acquisition.md`); its job is
  scheduling and local display, and **its alarm output wakes the device from deep sleep** (the regulators' enables on the FPGA board, RST_N on the ASIC), so every scheduled wake is a cold start through the
  entire trust chain; the alarm is also an input pin, so the loader sees it as an interrupt when awake. It also automates NIST SP 800-90B restart testing of the TRNG: a thousand wakes, each logging its first raw samples (`doc/hw.md`, Real-time clock).
- Oscillator, voltage regulators, and test connectors not populated in production. The FPGA's JTAG is permanently disabled at enrollment where the family allows it.

## Keys and what unlocks them

| Key | Held in | Per device | Unlocked by | Protects |
|---|---|---|---|---|
| Bitstream configuration key | FPGA eFuse; HSM | Yes | The FPGA alone | The bitstream at rest in flash and on the configuration bus |
| Bitstream signing key | Manufacturer HSM; public key data in FPGA eFuse | No | — | Only manufacturer bitstreams configure the FPGA (where the family authenticates) |
| **Pairing key** | The bitstream (key source) and secure element slot 0 | Yes, and per bitstream release | The bitstream itself | Every exchange with the secure element: MACs, encrypted reads, counter reads. Rotated with each bitstream release, which is what kills old bitstreams (`doc/se.md`, Ratchet) |
| Application key | Secure element | Yes | Pairing key | Headers and per-line keys of the loader and application images in flash; the boot record |
| **Data key** | Secure element | Yes | Pairing key **and** the host's proof to the secure element (CheckMac) | User data on the MicroSD card |
| Host authorization key | Secure element (never readable) and the host | Yes | Never leaves either | Proving the host is present; the session key derivation |
| Device identity key (symmetric) | Secure element (never readable); HSM | Yes | Used in place | Authenticating the device to the enrollment server, quantum-safe |
| Device identity key (ECDSA P-256) | Secure element (never readable); certificate chained to the manufacturer CA | Yes | Pairing key | Signed attestation reports for hosts and third parties |
| Distribution key | Secure element | No | Pairing key | Production application packages in transit; a device never enrolled cannot install them |
| Developer key | Secure element | Yes | Pairing key, into hardware only | Developer builds for that one device (`doc/roles.md`) |
| Log key | Secure element | Yes | Pairing key | The security event log's MAC chain |
| Release LMS keys (platform; application), main and backup | HSMs; platform public key in the boot ROM, hashes of the application keys in the secure element | No | — | Every update package, checked before anything is decrypted or installed |
| Host data secret | Host only; from a separate HSM master | Yes | — | Unlocks user data together with the device's data key |
| Host recording key pair (ML-KEM-768) | Private key on the host; public key in flash, under the application key | Per host | — | Recordings: the device can encrypt them but not decrypt them |
| Segment key | Loader domain and the recording engine, for one segment, then erased | Per segment | — | One segment of a recording |
| Sensor pairing key | Flash (under the application key) and the sensor | Per pairing | — | Sessions with one paired sensor |

The HSM derives every per-device key from a master key and the secure element's serial number (`doc/enrollment.md`). No key ever reaches software on either core: keys move from the
secure element or the key source into hardware key registers (`doc/hw.md`, Key paths).

## Boot

1. The FPGA's configuration engine loads the active bitstream from flash, checks its signature and decrypts it with the device's eFuse key; anything else is refused. On failure it falls back to the other
   bitstream slot (the family's multi-boot).
2. The **boot ROM** (block RAM in the bitstream) starts on the loader core with the application core in reset. It authenticates to the secure element with the pairing key, reads counter 0,
   unwraps the application key, checks the loader image's header and version, derives the loader's image key into the XIP engine, and jumps to the loader in flash.
   If the secure element refuses the pairing key, this bitstream has been superseded: the boot ROM stops in recovery.
3. The **loader** reads counter 1, checks the application image's header and version (or, for a developer build, device and epoch), derives its image key, and releases the application core.
   Every cache line of either image is authenticated as it is fetched.
4. The loader opens the sensor session and, if the network policy allows, releases the Ethernet PHY from reset and brings up its address.
5. The application runs. It reaches user data, recordings, the host, the sensor and the log only through the loader's mailbox services.

Any check that fails falls back to the other slot of that image, or stops in the safe state with a record in the boot record (`doc/hw.md`, Boot and lockdown).

## Updates

Two signed chains, sharing nothing but the secure element:

| Package | Contents | Scope | Signed by | Counter |
|---|---|---|---|---|
| Platform | This device's encrypted bitstream with its next pairing key, and a loader image | Per device, built by the bitstream build service | LMS (manufacturer), one signature per release over a manifest | 0 |
| Application | The LiteForth application, and its network policy | Fleet; encrypted under the distribution key | LMS (application owner); developer builds: a MAC under the device's developer key | 1 |

Packages arrive on the MicroSD card, over the UART from the host, or over the network. The loader checks the signature and the version before decrypting anything, writes into the
inactive slot, reads it back, advances the counter and switches the boot record (`doc/flash.md`, Install order). A bitstream update ends with the new bitstream, once it has booted,
replacing the pairing key in the secure element with its next key, after which the old bitstream can no longer open the secure element.

## Recordings

The loader draws a fresh key for each segment, encapsulates it with ML-KEM to the host's public key, and loads it into the recording engine, which encrypts the stream in the FPGA's
masked Ascon core and writes ciphertext to the card. The segment key is then erased, so the device cannot read its own past recordings, and neither can a thief (`doc/acquisition.md`).

## Sensor

The temperature sensor is replaceable and pairs offline with an ML-DSA certificate and ML-KEM. Every frame carries a MAC, readings older than the maximum age are rejected,
and the server later confirms each pairing and catches clones (`doc/sensor.md`).

## Host sessions and user data

The host proves itself to the secure element, not to the loader: the secure element checks the host's response (CheckMac) and only then releases the data key, and derives the session key
in place so that every frame is encrypted and authenticated. User data other than recordings is encrypted under a key derived from both the device's data key and a secret the host sends in each
session, which the device never stores. A lost host is re-issued from the HSM. A compromised host means retiring the device (`doc/arch.md`, R20).

## Attestation and identity

The device proves what it is and what it runs in two ways (`doc/se.md`, Attestation):

- to the enrollment server, with a MAC under its symmetric identity key over the server's nonce and a report of its versions and counters: quantum-safe, and the HSM can derive the key;
- to a host or a third party, with an ECDSA P-256 signature by the secure element over the same report, under a per-device certificate chained to the manufacturer's CA.

The secure element signs only for a bitstream that holds the current pairing key, so a report proves the pairing, the bitstream release, and the versions the loader measured.

## Network and the CLI

There are no radios. The device has one wired Ethernet port, and the FPGA implements the whole of its network side in hardware (`doc/hw.md`, Ethernet transport): an RMII MAC, an ARP
responder for its own address, IPv4 without fragments or options, ICMP echo, and a UDP demultiplexer that delivers datagrams on one port into the loader domain and drops everything else.
The payload is the same authenticated, encrypted session frame the loader already parses from the UART, so the network is a second transport for one protocol, with no TCP, DNS, TLS or HTTP
anywhere in the device. Flows are outbound only, with keepalives; the ack-and-window layer that makes updates and uploads reliable over a lossy path is part of the session protocol.

Where a site's IT policy only allows TCP on port 443, a small **edge proxy** (software on a PC or a gateway appliance on the same LAN) relays the device's datagrams to the server over TLS.
It is outside the trust boundary and sees only ciphertext: it can drop, delay or replay, and every one of those is already handled by the session protocol.

**The application owner decides** whether the port is enabled, through a network policy in the signed application package; the loader holds the PHY in reset when it is disabled.
Addressing is by DHCP, with static addresses settable in a host session; the server (or proxy) address is set the same way.

- **The UART** gives read-only status to anyone with a cable, and authenticated sessions.
- **The network** carries authenticated sessions with the server, and with a host on the same LAN.

| Session | Commands |
|---|---|
| None (UART status only) | Versions, build mode, faults, pairing state |
| Host (host authorization key) | User data, recordings, sensor pairing, updates, log export, network settings, attestation |
| Developer (developer key, developer builds only) | The above, plus the application's debug commands |

The PHY choice, PoE and the edge proxy are open items (`doc/questions.md`, A6 to A9).

## ASIC conversion

The ASIC keeps the boot ROM (now mask ROM), the loader, the application chain, the secure element and the flash, and loses the bitstream. The one thing the bitstream carried,
the pairing key, comes instead from a PUF behind the same key-source interface the FPGA build already uses, with the hardware to characterize it on silicon (`doc/ics55.md`).
