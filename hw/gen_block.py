#!/usr/bin/env python3
"""Generate hw/block.svg, the module/carrier block diagram, as an Inkscape SVG (A3 landscape, mm units, layers).
Run from anywhere: python3 hw/gen_block.py  ->  hw/block.svg (and hw/block.pdf if rsvg-convert is present)."""
import pathlib, subprocess, shutil, html

OUT = pathlib.Path(__file__).with_name('block.svg')
W, H = 420, 297  # A3 landscape, mm

FONT = "'DejaVu Sans', 'Liberation Sans', Arial, sans-serif"
COL = {  # line classes
    'cipher': '#1f5fbf', 'plain': '#c0392b', 'control': '#2e8b57', 'clock': '#7d3c98', 'power': '#000000', 'private': '#707070',
}
FILL = {'loader': '#fff3c4', 'sup': '#e1ecf9', 'app': '#e4f3e4', 'module': '#fbfbfb', 'carrier': '#ffffff', 'conn': '#f0e0f0', 'box': '#ffffff'}

layers = {k: [] for k in ['Regions', 'Module', 'FPGA', 'Carrier', 'Connectors', 'Nets', 'Labels', 'Legend']}

def esc(s): return html.escape(s, quote=True)

def rect(layer, x, y, w, h, fill='#fff', stroke='#000', sw=0.3, dash=None, rx=0):
    d = f';stroke-dasharray:{dash}' if dash else ''
    layers[layer].append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" style="fill:{fill};stroke:{stroke};stroke-width:{sw}{d}" />')

def text(layer, x, y, s, size=2.4, anchor='start', bold=False, color='#000', rotate=None, italic=False):
    st = f"font-size:{size}px;font-family:{FONT};fill:{color};text-anchor:{anchor};" + ('font-weight:bold;' if bold else '') + ('font-style:italic;' if italic else '')
    tr = f' transform="rotate({rotate} {x} {y})"' if rotate else ''
    layers[layer].append(f'<text x="{x}" y="{y}" style="{st}"{tr}>{esc(s)}</text>')

def box(layer, x, y, w, h, title, sub=None, fill='#fff', size=2.4, sub_size=1.9, sw=0.3, rx=0.8):
    rect(layer, x, y, w, h, fill=fill, sw=sw, rx=rx)
    cx, cy = x + w / 2, y + h / 2
    if sub:
        text('Labels', cx, cy - 0.3, title, size, 'middle', bold=True)
        text('Labels', cx, cy + sub_size + 0.4, sub, sub_size, 'middle')
    else:
        text('Labels', cx, cy + size * 0.35, title, size, 'middle', bold=True)

def line(cls, pts, arrow_end=False, arrow_start=False, width=0.45, dash=None, label=None, lx=None, ly=None, lanchor='middle', lsize=1.9):
    d = ' '.join(f'{x},{y}' for x, y in pts)
    st = f'fill:none;stroke:{COL[cls]};stroke-width:{width};stroke-linejoin:round'
    if dash: st += f';stroke-dasharray:{dash}'
    m = ''
    if arrow_end: m += ' marker-end="url(#arrow)"'
    if arrow_start: m += ' marker-start="url(#arrow_s)"'
    layers['Nets'].append(f'<polyline points="{d}" style="{st}"{m} />')
    if label:
        if lx is None: lx = (pts[0][0] + pts[-1][0]) / 2
        if ly is None: ly = (pts[0][1] + pts[-1][1]) / 2 - 1.0
        text('Labels', lx, ly, label, lsize, lanchor, color=COL[cls])

# ------------------------------------------------------------------ title
text('Labels', 12, 14, 'thriller: module and carrier block diagram', 5.5, bold=True)
text('Labels', 12, 20, 'Chipset on a potted DF40 mezzanine module (the FIPS 140-3 module); connectors, transducers and interfaces on the carrier. See hw/module.md, doc/hw.md, doc/fips.md.', 2.6)

# ------------------------------------------------------------------ regions
rect('Regions', 8, 28, 244, 230, fill=FILL['module'], sw=0.6, dash='3,1.5')
text('Labels', 18, 33, 'thriller module: potted; FIPS 140-3 module boundary = loader domain + TPM + flash (hw/module.md)', 3.0, bold=True)
rect('Regions', 280, 28, 132, 230, fill=FILL['carrier'], sw=0.4)
text('Labels', 283, 254.5, 'Carrier: outside the module, inside the application device\'s seal', 3.0, bold=True)

# ------------------------------------------------------------------ left column (module, loader-domain parts)
box('Module', 18, 64, 48, 12, '25 MHz oscillator', 'the module\'s only clock', fill=FILL['box'])
box('Module', 18, 95, 48, 16, 'QSPI NOR flash 32 MB', 'bitstreams, loader, supervisor, app; TPM blobs', fill=FILL['box'], sub_size=1.7)
box('Module', 18, 117, 48, 16, 'ST33KTPM2X TPM 2.0', 'SPI; reset from FPGA; CMVP #5570', fill=FILL['box'], sub_size=1.7)
rect('Module', 18, 150, 48, 40, fill=FILL['box'], sw=0.3, rx=0.8)
text('Labels', 42, 156, 'Regulators', 2.4, 'middle', bold=True)
for i, s_ in enumerate(['5 V in (always on)', '3V3_AO LDO: RTC, power control', 'bucks: 1.0 V VCC/VCC_DRM', '1.8 V VCCA, 3.3 V I/O + TPM', 'EN = WAKE | PB_N | RTC /INT', 'PGOOD, rail monitors -> security block']):
    text('Labels', 42, 161 + i * 4.6, s_, 1.8, 'middle')
text('Labels', 18, 199, 'Potting: whole card, both sides, except the two DF40', 1.8)
text('Labels', 18, 202.5, 'connectors; heatsink bonded to the FPGA before potting;', 1.8)
text('Labels', 18, 206, 'underfill on the BGA and the TPM.', 1.8)
text('Labels', 18, 212, 'PG2L50H-6IMBG324: 18x18 balls, 0.8 mm, 210 I/O.', 1.8)
text('Labels', 18, 215.5, 'Card 20 mm x ~40 mm, 6-layer (fpga/logos2/BGA.md).', 1.8)

# ------------------------------------------------------------------ FPGA
rect('FPGA', 76, 50, 138, 200, fill='#ffffff', sw=0.5, rx=1.2)
text('Labels', 145, 56.5, 'FPGA  PG2L50H-6IMBG324  (Pango Logos2)', 3.0, 'middle', bold=True)
L0, LP = 70, 11   # loader stack: first centre, pitch
rect('FPGA', 82, 60, 54, 128, fill=FILL['loader'], sw=0.35, dash='1.5,1', rx=0.8)
text('Labels', 109, 64.5, 'Loader core domain (the module)', 2.2, 'middle', bold=True)
loader = ['Loader core + boot ROM', 'Key source + key registers', 'Masked Ascon + SHA-256 cores', 'XIP engine: 3 ports + install port',
          'Security block: detectors, key gate,', 'TPM interface (SPI master)', 'QSPI direct mode (installs)', 'Recording engine (segment key)',
          'TRNG + HMAC_DRBG', 'Host UART (byte pipe; recovery)', 'Module watchdog, core control']
subs = {4: 'lockdown, PHY reset, WAKE, tamper inputs'}
for i, s_ in enumerate(loader):
    y = L0 + i * LP - 4
    box('FPGA', 86, y, 46, 8, s_, subs.get(i), size=2.0, sub_size=1.6)
Y_XIP, Y_SEC, Y_TPM, Y_REC, Y_UART = L0 + 3 * LP, L0 + 4 * LP, L0 + 5 * LP, L0 + 7 * LP, L0 + 9 * LP
rect('FPGA', 140, 60, 10, 148, fill='#eeeeee', sw=0.35, rx=0.8)
text('Labels', 146.5, 134, 'Mailboxes: A loader–supervisor, B loader–application, C supervisor–application (the module\'s service API, doc/api.md)', 1.8, 'middle', bold=True, rotate=-90)
rect('FPGA', 154, 60, 54, 80, fill=FILL['sup'], sw=0.35, rx=0.8)
text('Labels', 181, 64.5, 'Supervisor core domain', 2.2, 'middle', bold=True)
Y_ETH, Y_SD, Y_PSR, Y_SNS, Y_RTC = 83, 97, 109, 121, 133
sup = [(70, 'Supervisor core', None), (Y_ETH, 'Ethernet transport', 'RMII MAC, ARP, IPv4, ICMP, UDP demux'), (Y_SD, 'SD controller', None),
       (Y_PSR, 'Stream buffer controller', None), (Y_SNS, 'Sensor link', 'frames to the module, MAC checked'), (Y_RTC, 'RTC I2C, timers, scheduling', None)]
for y, t, s_ in sup:
    box('FPGA', 158, y - 4, 46, 8, t, s_, size=2.0, sub_size=1.6)
rect('FPGA', 154, 144, 54, 64, fill=FILL['app'], sw=0.35, rx=0.8)
text('Labels', 181, 148.5, 'Application core domain', 2.2, 'middle', bold=True)
Y_I2S, Y_LCD, Y_PWM, Y_CLK = 170, 181, 192, 203
app = [(156, 'Application core', 'samples -> recording engine (FIFO)'), (Y_I2S, 'I2S x2, MCLK, CODEC I2C', None), (Y_LCD, 'LCD SPI, touch I2C', None),
       (Y_PWM, 'Speaker PWM, carrier GPIO', None), (Y_CLK, 'Carrier clock inputs', 'through clock monitors; never the loader')]
for y, t, s_ in app:
    box('FPGA', 158, y - 4, 46, 8, t, s_, size=2.0, sub_size=1.6)
rect('FPGA', 82, 212, 126, 34, fill='#f4f4f4', sw=0.35, rx=0.8)
text('Labels', 145, 217.5, 'Configuration engine (vendor silicon)', 2.4, 'middle', bold=True)
for i, s_ in enumerate(['Master SPI from the QSPI flash at power-up; multi-boot fallback to the second bitstream slot',
                        'Bitstream authenticated (RSA-2048) before decryption (AES-256-GCM); keys in eFuse; JTAG locked at enrollment',
                        'The bitstream carries the boot ROM, the three cores and the pairing keys;',
                        'the loader, supervisor and application run from flash under per-line Ascon-AEAD128',
                        'Core clock: 25 MHz oscillator -> PLL; clock and PLL-lock monitors in the security block']):
    text('Labels', 145, 222.5 + i * 4.2, s_, 1.75, 'middle', italic=(i == 4))

# ------------------------------------------------------------------ right column (module, supervisor-side parts)
box('Module', 222, Y_ETH - 4, 26, 8, 'LAN8742A PHY', None, size=1.9)
text('Labels', 235, Y_ETH + 7.5, '25 MHz from XO; reset = network policy', 1.5, 'middle')
box('Module', 222, Y_PSR - 4, 26, 8, 'ESP-PSRAM64H', 'ciphertext ring', size=1.9, sub_size=1.5)
box('Module', 222, Y_RTC - 4, 26, 8, 'YSN8130E RTC', '/INT -> EN', size=1.9, sub_size=1.5)

# ------------------------------------------------------------------ connectors
J1T, J1B, J2T, J2B = 33, 140, 164, 210
rect('Connectors', 262, J1T, 10, J1B - J1T, fill=FILL['conn'], sw=0.5, rx=0.8)
text('Labels', 267.6, (J1T + J1B) / 2, 'J1  DF40C-80DP-0.4V(51): power, control, ciphertext, MAC\'d frames', 2.1, 'middle', bold=True, rotate=-90)
rect('Connectors', 262, J2T, 10, J2B - J2T, fill=FILL['conn'], sw=0.5, rx=0.8)
text('Labels', 267.6, (J2T + J2B) / 2, 'J2  DF40C-80DP: audio, display, clocks, GPIO', 1.9, 'middle', bold=True, rotate=-90)
text('Labels', 267, 216, 'A minimal carrier', 1.7, 'middle')
text('Labels', 267, 219, 'mates J1 only', 1.7, 'middle')

# ------------------------------------------------------------------ carrier
Y_PB, Y_JTAG, Y_5V, Y_UA = 36, 39.5, 43, 46.5          # J1 top lanes (module side)
C_PB, C_JTAG, C_5V, C_UA = 36, 47, 58, 69                # carrier box lanes
car = [
    (C_PB, 'Pushbutton, enclosure switch, seal loop', 'carrier identity EEPROM', 300, 104),
    (C_JTAG, 'JTAG header', 'fixture carrier only; unrouted in production', 300, 104),
    (C_5V, 'USB-C: 5 V in', 'the only power into the module', 300, 52),
    (C_5V, 'Carrier 3.3 V LDO', 'for carrier parts only', 356, 48),
    (C_UA, 'FT2232H: USB-UART', 'status, host sessions, CLI, updates', 300, 104),
    (Y_ETH, 'RJ45 with magnetics', '10/100; edge proxy to TLS 443 off-board', 300, 104),
    (Y_SD, 'MicroSD socket', 'TVS on data lines; ciphertext, log, packages', 300, 104),
    (Y_SNS, 'Sensor connector', 'two-way link, replaceable sensor', 300, 104),
    (Y_RTC, '2 x SR44 cells', 'RTC backup; loss = module removed', 300, 104),
    (Y_I2S, '2 x NAU88C22 CODECs', 'four mic channels; plaintext I2S', 300, 104),
    (Y_LCD, 'LCD + touch panel', '4-wire SPI, I2C touch', 300, 104),
    (Y_PWM, 'Speaker amplifier; carrier GPIO', None, 300, 104),
    (Y_CLK, 'SI5351A + 10 MHz reference in', 'application clocks only', 300, 104),
]
for y, t, s_, x, w in car:
    box('Carrier', x, y - 4.5, w, 9, t, s_, size=2.1, sub_size=1.6)
line('power', [(352, C_5V), (356, C_5V)], arrow_end=True, width=0.6)
for i, s_ in enumerate(['Everything on the carrier changes without touching the validated module.',
                        'Treat these parts as inside, or passing through, the application device\'s tamper-evident enclosure.',
                        'The module cannot authenticate its carrier: removal is detected (RTC backup loss, seal loop),',
                        'and an installed bit with a carrier identifier is checked at boot (R51, H13).']):
    text('Labels', 300, 222 + i * 3.8, s_, 1.8)

# ------------------------------------------------------------------ nets
# top lanes from J1: tamper inputs, JTAG, 5 V, UART
line('control', [(262, Y_PB), (11, Y_PB), (11, 240), (76, 240)], arrow_end=True, label='PB_N, enclosure switch, seal loop, carrier ID -> security block and supervisor', lx=18, ly=238.5, lanchor='start')
line('control', [(272, Y_PB), (300, C_PB)])
line('control', [(262, Y_JTAG), (13, Y_JTAG), (13, 232), (76, 232)], arrow_end=True, dash='2,1', label='JTAG -> configuration engine (fixture only)', lx=18, ly=230.5, lanchor='start')
line('control', [(272, Y_JTAG), (284, Y_JTAG), (284, C_JTAG), (300, C_JTAG)], dash='2,1')
line('power', [(262, Y_5V), (15, Y_5V), (15, 170), (18, 170)], arrow_end=True, width=0.8, label='5 V, always on', lx=140, ly=41.5)
line('power', [(272, Y_5V), (280, Y_5V), (280, C_5V), (300, C_5V)], width=0.8)
line('cipher', [(132, Y_UART), (137, Y_UART), (137, Y_UA), (262, Y_UA)], arrow_end=True, label='UART: session frames (ciphertext); status in recovery', lx=200, ly=45)
line('cipher', [(272, Y_UA), (276, Y_UA), (276, C_UA), (300, C_UA)])
line('power', [(66, 180), (76, 180)], arrow_end=True, width=0.7, label='rails', lx=71, ly=178, lsize=1.4)
line('clock', [(66, 70), (76, 70)], arrow_end=True, label='25 MHz', lx=71, ly=68, lsize=1.4)
line('cipher', [(66, Y_XIP), (86, Y_XIP)], arrow_start=True, arrow_end=True, label='QSPI', lx=76, ly=Y_XIP - 1.5, lsize=1.4)
line('cipher', [(66, Y_TPM), (86, Y_TPM)], arrow_start=True, arrow_end=True, label='SPI', lx=76, ly=Y_TPM - 1.5, lsize=1.4)
line('cipher', [(204, Y_ETH), (222, Y_ETH)], arrow_start=True, arrow_end=True, label='RMII', lx=213, ly=Y_ETH - 1.5, lsize=1.5)
line('cipher', [(248, Y_ETH), (262, Y_ETH)], arrow_start=True, arrow_end=True, label='MDI', lx=255, ly=Y_ETH - 1.5, lsize=1.5)
line('cipher', [(272, Y_ETH), (300, Y_ETH)])
line('cipher', [(204, Y_SD), (262, Y_SD)], arrow_start=True, arrow_end=True, label='SD: ciphertext, log, packages', lx=233, ly=Y_SD - 1.5, lsize=1.6)
line('cipher', [(272, Y_SD), (300, Y_SD)])
line('cipher', [(204, Y_PSR), (222, Y_PSR)], arrow_start=True, arrow_end=True, label='QSPI', lx=213, ly=Y_PSR - 1.5, lsize=1.5)
line('private', [(132, Y_REC), (139, Y_REC), (139, Y_PSR + 3), (158, Y_PSR + 3)], arrow_end=True, dash='1,0.8', label='ciphertext FIFO', lx=139.5, ly=Y_REC - 1.5, lanchor='start', lsize=1.5)
line('cipher', [(204, Y_SNS), (262, Y_SNS)], arrow_start=True, arrow_end=True, label='sensor link: MAC\'d frames', lx=233, ly=Y_SNS - 1.5, lsize=1.6)
line('cipher', [(272, Y_SNS), (300, Y_SNS)])
line('control', [(204, Y_RTC), (222, Y_RTC)], arrow_start=True, arrow_end=True, label='I2C', lx=213, ly=Y_RTC - 1.5, lsize=1.5)
line('power', [(248, Y_RTC), (262, Y_RTC)], arrow_start=True, label='VBAT', lx=255, ly=Y_RTC - 1.5, lsize=1.5)
line('power', [(272, Y_RTC), (300, Y_RTC)])
line('plain', [(204, Y_I2S), (262, Y_I2S)], arrow_start=True, arrow_end=True, label='I2S x2, MCLK, I2C (plaintext)', lx=233, ly=Y_I2S - 1.5, lsize=1.6)
line('plain', [(272, Y_I2S), (300, Y_I2S)])
line('plain', [(204, Y_LCD), (262, Y_LCD)], arrow_start=True, arrow_end=True, label='LCD SPI, touch I2C', lx=233, ly=Y_LCD - 1.5, lsize=1.6)
line('plain', [(272, Y_LCD), (300, Y_LCD)])
line('plain', [(204, Y_PWM), (262, Y_PWM)], arrow_start=True, arrow_end=True, label='PWM, GPIO', lx=233, ly=Y_PWM - 1.5, lsize=1.6)
line('plain', [(272, Y_PWM), (300, Y_PWM)])
line('clock', [(262, Y_CLK), (204, Y_CLK)], arrow_end=True, label='carrier clocks (untrusted)', lx=233, ly=Y_CLK - 1.5, lsize=1.6)
line('clock', [(300, Y_CLK), (272, Y_CLK)])

# ------------------------------------------------------------------ legend
ly0 = 268
rect('Regions', 8, 262, 404, 32, fill='#ffffff', sw=0.3, rx=0.8)
text('Labels', 12, ly0, 'Legend', 2.4, bold=True)
cols = [(12, [('cipher', 'ciphertext or MAC\'d: safe to expose (flash, card, network, UART, sensor, TPM bus)'),
              ('plain', 'plaintext: accepted inside the application device\'s seal (R38)'),
              ('control', 'control and tamper inputs; dashed = JTAG, fixture carrier only')]),
        (160, [('clock', 'clocks: the module\'s own 25 MHz inside; carrier clocks reach only the supervisor and application domains'),
               ('power', 'power: 5 V in; the module\'s rails never leave the card'),
               ('private', 'private connection inside the FPGA, never on a bus')])]
for x0, items in cols:
    for i, (cls, s_) in enumerate(items):
        y = ly0 + 5 + i * 4.6
        line(cls, [(x0, y - 0.8), (x0 + 12, y - 0.8)], width=0.6, dash='1,0.8' if cls == 'private' else None)
        text('Labels', x0 + 15, y, s_, 1.8)
text('Labels', 12, ly0 + 20, 'Fills: yellow = loader core domain (the FIPS module logic); blue = supervisor core domain; green = application core domain; grey = mailboxes.', 1.8)
text('Labels', 12, ly0 + 24, 'The dashed outline is the potted module and the FIPS 140-3 physical boundary; the TPM is an embedded validated module inside it; the flash holds only ciphertext and public data.', 1.8)

# ------------------------------------------------------------------ assemble
defs = '''<defs>
    <marker id="arrow" orient="auto" markerWidth="4" markerHeight="4" refX="3.2" refY="2" markerUnits="strokeWidth" style="overflow:visible">
      <path d="M0,0 L4,2 L0,4 z" style="fill:context-stroke;stroke:none" />
    </marker>
    <marker id="arrow_s" orient="auto" markerWidth="4" markerHeight="4" refX="0.8" refY="2" markerUnits="strokeWidth" style="overflow:visible">
      <path d="M4,0 L0,2 L4,4 z" style="fill:context-stroke;stroke:none" />
    </marker>
  </defs>'''
# Inkscape 1.0 lacks context-stroke; give each marker a plain black fill instead.
defs = defs.replace('fill:context-stroke', 'fill:#303030')
head = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:svg="http://www.w3.org/2000/svg"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
     width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" version="1.1" id="thriller_block" inkscape:version="1.0.1">
  <sodipodi:namedview id="namedview" pagecolor="#ffffff" bordercolor="#666666" borderopacity="1" inkscape:document-units="mm" showgrid="true" units="mm" inkscape:pageshadow="2">
    <inkscape:grid type="xygrid" id="grid" units="mm" spacingx="1" spacingy="1" empspacing="5" />
  </sodipodi:namedview>
  <title>thriller: module and carrier block diagram</title>
  {defs}
'''
body = ''
for i, (name, items) in enumerate(layers.items()):
    body += f'  <g inkscape:groupmode="layer" id="layer_{name.lower()}" inkscape:label="{name}">\n'
    body += ''.join(f'    {it}\n' for it in items)
    body += '  </g>\n'
OUT.write_text(head + body + '</svg>\n')
print('wrote', OUT)
if shutil.which('rsvg-convert'):
    subprocess.run(['rsvg-convert', '-f', 'pdf', '-o', str(OUT.with_suffix('.pdf')), str(OUT)], check=True)
    print('wrote', OUT.with_suffix('.pdf'))
