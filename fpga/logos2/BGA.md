# BGA breakout

The PG2L50H-6IMBG324 is in a BGA-324(15x15) package, with a ball pitch of 0.8 mm.
A 0.20mm drill centered in a 0.40mm pad provides a 0.10mm annular ring per side.
Keep general vias at 0.30mm hole / 0.45mm pad, and only apply the 0.20mm drill to the BGA.
The standard JLCPCB 6-layer PCB can handle a breakout using 0.1mm traces.
Use 0.15mm traces outside of breakout for a 50-ohm impedance.
On ground planes, 0.60mm anti-pads leave a 0.20mm web of copper plane between adjacent vias.

18 x 18 balls: The outer two rows are pad-only, so they have no inner layer holes.
Rows 1 and 2 break out through L1 only.
Many unused I/Os are allowed (not all 210 I/Os are used), so the best use of these no-connects is in Row 3.
Each no-connect omits a via-in-pad hole to provide a fat breakout channel.
Other rows have no-connects as needed to allow routing on a 6-layer PCB.

The PCB is 1.0 mm thick. It follows a SODIMM (260-pin) form factor to fit a TE 2309407-1 or 2309409-1 socket:
69.6mm x 40.0mm. So, it is wider than the standard 30.0mm SODIMM.
