# Network Security Posture

A one-page statement of what the device does and does not do on a network, written for the people who have to approve plugging it in: hospital or enterprise IT, and the reviewers of an
FDA submission. The engineering is in `doc/hw.md` (Ethernet transport), the risks in `doc/arch.md` (R23, R28, R29, R39), and the tests in `doc/test.md`.

## The claim

**The device cannot be used as a network attack vector.** It has no network stack, so there is no code on it that a network packet can exploit, no shell to reach, no files to encrypt,
and no foothold from which to move to anything else on the network. The worst a network attacker can do to it is stop it talking.

## Why the claim holds

1. **The network interface is hardware, not software.** Inside the FPGA, the Ethernet port is a fixed logic block that recognizes exactly five things: Ethernet frames to its own address,
   ARP requests for its own IP address, IPv4 packets to its own address without options or fragments, ICMP echo requests, and UDP datagrams to one port. Everything else is discarded before
   any processor sees it. There is no TCP, no DNS, no TLS, no HTTP, no web interface, no remote shell and no file sharing anywhere in the device.
2. **A hardware parser cannot be made to run code.** A malformed packet can at most confuse the logic block, which the firmware detects and resets. It cannot alter what the device executes,
   because the device's code is in authenticated flash that is checked line by line as it runs, and no processor has a write path into it from the network or from anywhere else.
3. **The payload goes to one parser, behind authentication.** A UDP datagram that passes the hardware filter becomes an encrypted, authenticated session frame checked by the loader against a
   per-device key held in a TPM. An unauthenticated sender gets no further than the session handshake, which has attempt limits and is logged.
4. **The processor that owns security has no network exposure.** The application processor, which runs the device's function, has no connection to the network at all; the supervisor
   processor, which moves datagrams between the hardware transport and the cryptographic module, runs no network stack, only framing; and the loader processor, which owns every key, sees only
   authenticated frames. The boundaries between them are enforced by wiring in the chip, not by an operating system.
5. **Outbound only.** The device opens flows to its server (or to a local relay); it listens for nothing but the replies, and the port can be disabled entirely by the application owner,
   leaving an air-gapped device that works from its MicroSD card and USB connection.

## What the network can still do to it

- **Deny service.** A flood, ARP or DHCP spoofing, or a severed cable stops uploads, updates and pairing confirmations until the condition clears. Nothing on the device depends on the network to
  perform its function; it records and alarms locally and reports when connectivity returns.
- **Watch ciphertext.** Every byte leaving the port is encrypted to the intended recipient and authenticated. Recordings are encrypted to the receiving host's key inside the FPGA before they leave it.

Connectivity also adds something: while connected, the server stamps the device's recordings with authenticated time beacons, so a streamed recording is provably made when the server says,
and an offline one is bracketed between the last contact and the next (`doc/acquisition.md`, When a recording was made).

## The edge proxy

Sites that only permit outbound TCP on port 443 run a small relay on their network that wraps the device's datagrams in TLS to the server. The relay is deliberately untrusted:
it sees only ciphertext, holds no key, and if it is compromised the device is unaffected except for connectivity. It is ordinary software on ordinary infrastructure and is managed like any
other network service.

## For IT departments

| Question | Answer |
|---|---|
| Open ports | None listening for connections. One UDP port receives replies to the device's own outbound traffic, plus ICMP echo for commissioning (can be disabled) |
| Protocols | ARP, IPv4, ICMP echo, UDP, DHCP client. No TCP |
| Firewall rules needed | Outbound UDP to the server or relay address; or nothing beyond LAN access if a relay is used |
| Credentials on the device | Per-device keys in a FIPS 140-3 validated TPM; none usable on any other device or system |
| Remote management interfaces | None. Updates are signed packages verified on the device |
| Can it spread malware | No: it contains no executable it did not boot with, and nothing on the network can change that |
| Can it be ransomed | No: no network-reachable code, no mutable files reachable from the network, and recordings are already encrypted to their owner |
| Logging | A tamper-evident event log readable by the device owner and uploaded to the manufacturer's server |

## For an FDA submission

This statement supports the Global System View and the Security Use Case Views in `doc/fda.md`. The evidence behind it is:

- the netlist connectivity check showing the application processor has no path to the network and the loader processor none to the network transport (`doc/test.md`, Key isolation);
- RTL fuzzing of the Ethernet transport and protocol fuzzing from the network with boofuzz, in simulation and on hardware (`doc/test.md`, Network policy and transport);
- the per-line code authentication that makes any change to executing code impossible from any source (`doc/xip.md`);
- the risk rows R23, R28, R29 and R39 in `doc/arch.md`, each rated with its residual risk (denial of service) stated.

The network is not required for the device's intended use. A lost link affects uploads, updates and pairing confirmations only.
