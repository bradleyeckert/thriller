#!/usr/bin/env python3
"""Turn the thriller board project into the module: strip carrier parts, replace the FPGA with the MBG324, add the two DF40 connectors
and the TPM. Run once from the committed board state: python3 tools/rework_module.py  (from fpga/logos2/KiCAD)."""
import sys, re, json, pathlib, uuid as _uuid
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ksch import *

ROOT = pathlib.Path(__file__).resolve().parents[1]          # fpga/logos2/KiCAD
PRJ = ROOT / 'thriller'
ROOT_UUID = '02a4128e-5284-4df4-bd95-50d9619a72c4'
PINS = json.load(open(ROOT.parent / 'pinout324.json')) if (ROOT.parent / 'pinout324.json').exists() else None

_ucount = [0]
def U():   # deterministic UUIDs so reruns of the script produce identical files
    _ucount[0] += 1
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, f'thriller/rework/{_ucount[0]}'))

# ------------------------------------------------------------------ library symbols (new-format text, embedded in sheets and added to thriller.kicad_sym)
def load_fpga324():
    s = (ROOT / 'FPGA_Pango_Logos2.kicad_sym').read_text()
    body = s.split('(symbol "PG2L50H-6IMBG324"')[1]
    # cut at the end of this symbol: the library ends right after it
    body = body[:body.rstrip().rfind(')')]          # drop the library's closing paren
    body = '(symbol "FPGA_Pango_Logos2:PG2L50H-6IMBG324"' + body
    body = re.sub(r' \(id \d+\)', '', body)
    body = body.replace('(symbol "PG2L50H-6IMBG324_', '(symbol "PG2L50H-6IMBG324_')
    return body.strip()

DF40_SYM = None
def df40_symbol():
    L = []
    L.append('(symbol "thriller:DF40C-80DP" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)')
    L.append('(property "Reference" "J" (at 0 55.88 0) (effects (font (size 1.27 1.27))))')
    L.append('(property "Value" "DF40C-80DP-0.4V(51)" (at 0 -55.88 0) (effects (font (size 1.27 1.27))))')
    L.append('(property "Footprint" "Connector_Hirose:Hirose_DF40C-80DP-0.4V_2x40_P0.40mm" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    L.append('(property "Datasheet" "https://www.hirose.com/product/document?clcode=CL0684-4064-6-51" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    L.append('(property "Description" "Hirose DF40 board-to-board header, 80 contacts, 2x40, 0.4 mm pitch, 1.5 mm stack (module side)" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    L.append('(property "MPN" "DF40C-80DP-0.4V(51)" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    L.append('(property "LCSC" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    L.append('(symbol "DF40C-80DP_0_1" (rectangle (start -7.62 53.34) (end 7.62 -53.34) (stroke (width 0.254) (type default)) (fill (type background))))')
    L.append('(symbol "DF40C-80DP_1_1"')
    for i in range(40):
        y = 49.53 - i * 2.54
        L.append(f'(pin passive line (at -12.7 {y:g} 0) (length 5.08) (name "{i+1}" (effects (font (size 1.27 1.27)))) (number "{i+1}" (effects (font (size 1.27 1.27)))))')
        L.append(f'(pin passive line (at 12.7 {y:g} 180) (length 5.08) (name "{i+41}" (effects (font (size 1.27 1.27)))) (number "{i+41}" (effects (font (size 1.27 1.27)))))')
    L.append(')')
    L.append('(embedded_fonts no)')
    L.append(')')
    return '\n'.join(L)

def tpm_symbol():
    pins_l = [('VPS', '1', 'power_in', 12.7), ('VPS', '22', 'power_in', 10.16), ('RST', '17', 'input', 5.08), ('PIRQ', '18', 'open_collector', 2.54),
              ('GPIO_PP', '7', 'input', -2.54), ('GPI_I2C_Select', '6', 'input', -5.08), ('GND', '2', 'power_in', -10.16), ('GND', '16', 'power_in', -12.7)]
    pins_r = [('SPI_CLK', '19', 'input', 7.62), ('SPI_CS', '20', 'input', 5.08), ('SPI_MOSI', '21', 'input', 2.54), ('SPI_MISO', '24', 'output', 0),
              ('I2C_SDA/GPIO_6', '29', 'bidirectional', -5.08), ('I2C_SCL/GPIO_5', '30', 'bidirectional', -7.62), ('EP', '33', 'passive', -12.7)]
    nic = [n for n in range(1, 33) if str(n) not in [p[1] for p in pins_l + pins_r]]
    L = ['(symbol "thriller:ST33KTPM2X" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)',
         '(property "Reference" "U" (at -12.7 17.78 0) (effects (font (size 1.27 1.27))))',
         '(property "Value" "ST33KTPM2X32DKG9" (at -12.7 -17.78 0) (effects (font (size 1.27 1.27))))',
         '(property "Footprint" "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '(property "Datasheet" "https://www.st.com/en/secure-mcus/st33ktpm2x.html" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '(property "Description" "ST33KTPM2X TPM 2.0, SPI, UFQFPN32 5x5 mm, CMVP #5570. Pinout per DB5174 rev 3 figure 1; NiC pins 3-5, 8-15, 23, 25-28, 31, 32 not drawn" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '(property "MPN" "ST33KTPM2X32DKG9" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '(property "LCSC" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
         '(symbol "ST33KTPM2X_0_1" (rectangle (start -12.7 15.24) (end 12.7 -15.24) (stroke (width 0.254) (type default)) (fill (type background))))',
         '(symbol "ST33KTPM2X_1_1"']
    for nm, num, kind, y in pins_l:
        L.append(f'(pin {kind} line (at -17.78 {y:g} 0) (length 5.08) (name "{nm}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
    for nm, num, kind, y in pins_r:
        L.append(f'(pin {kind} line (at 17.78 {y:g} 180) (length 5.08) (name "{nm}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
    for i, n in enumerate(nic):   # NiC pins along the bottom, hidden-ish: short stubs so ERC sees them as no-connect
        L.append(f'(pin no_connect line (at {-11.43 + i * 1.27:g} -20.32 90) (length 5.08) (name "NiC" (effects (font (size 1.27 1.27)))) (number "{n}" (effects (font (size 1.27 1.27)))))')
    L += [')', '(embedded_fonts no)', ')']
    return '\n'.join(L)

# ------------------------------------------------------------------ helpers to build schematic items (as text, parsed into trees)
def item(text): return parse(text)

def sym_instance(lib_id, ref, value, x, y, rot, unit, sheet_uuid, pins, props=None, in_bom=True):
    props = props or {}
    L = [f'(symbol (lib_id "{lib_id}") (at {x:g} {y:g} {rot}) (unit {unit}) (exclude_from_sim no) (in_bom {"yes" if in_bom else "no"}) (on_board {"yes" if in_bom else "no"}) (dnp no) (uuid "{U()}")']
    L.append(f'(property "Reference" "{ref}" (at {x:g} {y - 2.54:g} 0) (effects (font (size 1.27 1.27)){" (hide yes)" if ref.startswith("#") else ""}))')
    L.append(f'(property "Value" "{value}" (at {x:g} {y + 2.54:g} 0) (effects (font (size 1.27 1.27))))')
    for k in ['Footprint', 'Datasheet', 'Description', 'LCSC', 'MPN']:
        if k in props:
            L.append(f'(property "{k}" {q(props[k])} (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    for p in pins:
        L.append(f'(pin "{p}" (uuid "{U()}"))')
    L.append(f'(instances (project "thriller" (path "/{ROOT_UUID}/{sheet_uuid}" (reference "{ref}") (unit {unit}))))')
    L.append(')')
    return item('\n'.join(L))

def wire(a, b):
    return item(f'(wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) (stroke (width 0) (type default)) (uuid "{U()}"))')

def glabel(name, x, y, rot):
    just = {0: 'left', 180: 'right', 90: 'left', 270: 'right'}[rot]
    return item(f'(global_label "{name}" (shape passive) (at {x:g} {y:g} {rot}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{U()}"))')

def llabel(name, x, y, rot):
    just = {0: 'left bottom', 180: 'right bottom', 90: 'left bottom', 270: 'right bottom'}[rot]
    return item(f'(label "{name}" (at {x:g} {y:g} {rot}) (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{U()}"))')

def noconn(x, y):
    return item(f'(no_connect (at {x:g} {y:g}) (uuid "{U()}"))')

def text_item(s, x, y, size=1.5):
    return item(f'(text {q(s)} (exclude_from_sim no) (at {x:g} {y:g} 0) (effects (font (size {size} {size})) (justify left top)) (uuid "{U()}"))')

def power_sym(net, x, y, sheet_uuid):
    return sym_instance(f'thriller:{net}', '#PWR', net, x, y, 0, 1, sheet_uuid, ['1'], in_bom=False)

# ------------------------------------------------------------------ generic: attach labels/power/nc to every pin of a placed symbol
def outward(rot):
    return {0: (-1, 0), 180: (1, 0), 270: (0, -1), 90: (0, 1)}[int(rot) % 360]

def junction(x, y):
    return item(f'(junction (at {x:g} {y:g}) (diameter 0) (color 0 0 0 0) (uuid "{U()}"))')

def connect_pins(sheet, inst, lib_pins, assign, sheet_uuid, stub=5.08, text_rot=None):
    """assign: pin number -> ('g', net) | ('l', net) | ('p', powernet) | ('nc',)
    Vertical runs of adjacent pins on the same power net (ground rows on connectors and the FPGA) are joined by one
    wire with a single power symbol at the bottom instead of a stack of overlapping symbols."""
    at = find1(inst, 'at'); x, y, rot = float(at[1]), float(at[2]), float(at[3])
    unit = int(find1(inst, 'unit')[1])
    power_runs = {}   # (ox, net) -> list of (Y, E)
    ends = {}         # pin number -> stub end, for callers that add parts of their own ('w' draws the stub only)
    for (u, num, nm, px, py, prot, plen) in lib_pins:
        if u not in (0, unit): continue
        dx, dy = rot_mirror(px, py, rot, None)
        X, Y = round(x + dx, 3), round(y + dy, 3)
        ox, oy = outward((prot + rot) % 360)
        a = assign.get(num, ('nc',))
        if a[0] == 'nc':
            sheet.tree.append(noconn(X, Y)); continue
        E = (round(X + ox * stub, 3), round(Y + oy * stub, 3))
        sheet.tree.append(wire((X, Y), E)); ends[num] = E
        if a[0] == 'w': continue
        if a[0] == 'p':
            if ox:  # horizontal pin: collect for run merging
                power_runs.setdefault((ox, E[0], a[1]), []).append(E)
            else:
                sheet.tree.append(power_sym(a[1], E[0], E[1], sheet_uuid))
        else:
            lrot = {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}[(ox, oy)]
            sheet.tree.append((glabel if a[0] == 'g' else llabel)(a[1], E[0], E[1], lrot))
    for (ox, ex, net), pts in power_runs.items():
        pts.sort(key=lambda e: e[1])
        runs, cur = [], [pts[0]]
        for e in pts[1:]:
            if abs(e[1] - cur[-1][1] - 2.54) < 0.01: cur.append(e)
            else: runs.append(cur); cur = [e]
        runs.append(cur)
        for run in runs:
            if len(run) > 1:
                sheet.tree.append(wire(run[0], run[-1]))
                for e in run[1:-1]: sheet.tree.append(junction(*e))
            # positive rails point up: symbol at the top of the run; grounds at the bottom
            top = net.startswith('+') or net.startswith('VCC')
            e = run[0] if top else run[-1]
            sheet.tree.append(power_sym(net, e[0], e[1], sheet_uuid))
    return ends

# ------------------------------------------------------------------ deletion with pruning
def delete_refs(sheet, refs, lib_ids=()):
    for s in list(sheet.symbols()):
        if sheet.prop(s, 'Reference') in refs or unq(find1(s, 'lib_id')[1]) in lib_ids:
            sheet.remove(s)

def delete_on_nets(sheet, netnames, keep_refs=(), include_power=False):
    """delete symbols that have any pin on a net carrying one of these label names"""
    net = Net(sheet)
    victims = []
    for s in sheet.symbols():
        ref = sheet.prop(s, 'Reference')
        if ref in keep_refs or (ref.startswith('#') and not include_power): continue
        for (x, y, num, nm) in sheet.pin_points(s):
            names = net.names.get(net.net_of((x, y)), set())
            if names & set(netnames): victims.append(s); break
    for s in victims: sheet.remove(s)
    return victims

def prune(sheet, passes=6):
    """Remove wires, labels, junctions and no-connects that no longer touch a symbol pin; trim dangling stubs; drop orphan passives."""
    for _ in range(passes):
        changed = False
        pinpts = {}
        for s in sheet.symbols():
            for (x, y, num, nm) in sheet.pin_points(s): pinpts.setdefault((x, y), []).append(sheet.prop(s, 'Reference'))
        net = Net(sheet)
        groups = net.members()
        # components with no pins at all: delete their wires and labels
        dead_roots = set()
        lbl_roots = set(net.find(p) for p in net.names)
        for root, pts in groups.items():
            # dead: no pin of a real component and no label (a net made only of power symbols and wire is dead too)
            real = any(r for p in pts for r in pinpts.get(p, []) if not r.startswith('#'))
            pwr = any(r for p in pts for r in pinpts.get(p, []) if r.startswith('#'))
            if not real and not (pwr and root in lbl_roots): dead_roots.add(root)
        for w in list(sheet.items('wire')):
            a, b = wire_ends(w)
            if net.find(a) in dead_roots: sheet.remove(w); changed = True
        for l in list(sheet.items('label') + sheet.items('global_label')):
            p = label_pos(l)
            if p in net.parent and net.find(p) in dead_roots: sheet.remove(l); changed = True
        # dangling stubs: a wire end touching nothing else
        wires = sheet.items('wire')
        labels = set(label_pos(l) for l in sheet.items('label') + sheet.items('global_label'))
        def touches(p, me):
            if p in pinpts or p in labels: return True
            for w in wires:
                if w is me: continue
                a, b = wire_ends(w)
                if p == a or p == b or on_segment(p, a, b): return True
            return False
        for w in list(wires):
            a, b = wire_ends(w)
            if not touches(a, w) or not touches(b, w):
                sheet.remove(w); changed = True
        # junctions and no-connects with nothing under them
        wires = sheet.items('wire')
        for j in list(sheet.items('junction')):
            p = label_pos(j)
            n = sum(1 for w in wires for e in wire_ends(w) if e == p) + sum(1 for w in wires if on_segment(p, *wire_ends(w)))
            if n < 3: sheet.remove(j); changed = True
        for nc in list(sheet.items('no_connect')):
            if label_pos(nc) not in pinpts: sheet.remove(nc); changed = True
        # orphan passives: any pin touching nothing
        wires = sheet.items('wire')
        for s in list(sheet.symbols()):
            ref = sheet.prop(s, 'Reference')
            if ref.startswith('#') or not re.match(r'(R|C|FB|L|D|Q)\d', ref): continue
            for (x, y, num, nm) in sheet.pin_points(s):
                p = (x, y)
                others = [r for r in pinpts.get(p, []) if r != ref]
                if not others and p not in labels and not any(p == a or p == b or on_segment(p, a, b) for w in wires for a, b in [wire_ends(w)]):
                    sheet.remove(s); changed = True; break
        # power symbols touching nothing
        for s in list(sheet.symbols()):
            if not sheet.prop(s, 'Reference').startswith('#'): continue
            (x, y, num, nm), = sheet.pin_points(s)
            p = (x, y)
            if len(pinpts.get(p, [])) < 2 and p not in labels and not any(p == a or p == b or on_segment(p, a, b) for w in sheet.items('wire') for a, b in [wire_ends(w)]):
                sheet.remove(s); changed = True
        if not changed: break

def ensure_lib(sheet, name, text):
    ls = find1(sheet.tree, 'lib_symbols')
    if not any(unq(s[1]) == name for s in find(ls, 'symbol')):
        ls.append(parse(text))
        sheet.libs[name] = Sheet.pins_of(parse(text)) if hasattr(Sheet, 'pins_of') else None
        # refresh lib table
        sym = parse(text)
        pins = []
        for sub in find(sym, 'symbol'):
            m = re.search(r'_(\d+)_\d+"?$', sub[1]); unit = int(m.group(1))
            for p in find(sub, 'pin'):
                at = find1(p, 'at'); num = unq(find1(p, 'number')[1]); nm = unq(find1(p, 'name')[1])
                pins.append((unit, num, nm, float(at[1]), float(at[2]), float(at[3]), float(find1(p, 'length')[1])))
        sheet.libs[name] = pins

def lib_text_from_project(name):
    """pull a symbol definition out of thriller.kicad_sym (project library), renamed with the lib prefix"""
    s = (PRJ / 'thriller.kicad_sym').read_text()
    i = s.index(f'(symbol "{name}"')
    depth = 0; j = i
    while True:
        c = s[j]
        if c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: break
        j += 1
    body = s[i:j + 1]
    return body.replace(f'(symbol "{name}"', f'(symbol "thriller:{name}"', 1)

def set_prop(sym, name, value):
    for p in find(sym, 'property'):
        if unq(p[1]) == name: p[2] = q(value); return
    sym.insert(len([c for c in sym if not isinstance(c, list)]) + len(find(sym, 'property')) + 1, parse(f'(property "{name}" {q(value)} (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))'))

# ------------------------------------------------------------------ FPGA pin assignment (ball -> net), from the module pinout contract (hw/module.md)
def fpga_assignment():
    pins = json.load(open(ROOT.parent / 'pinout324.json'))        # ball -> (bank, name, pair)
    byname = {v[1]: b for b, v in pins.items()}
    A = {}                                                          # ball -> ('g'|'p'|'nc', net)
    def g(name, net):
        if name not in byname:
            cands = [n for n in byname if n.startswith(name + '_') or n == name]
            assert len(cands) == 1, (name, cands)
            name = cands[0]
        assert byname[name] not in A, name
        A[byname[name]] = ('g', net)
    # bank L5: configuration flash (fixed functions), TPM, PSRAM, RTC, the module clock
    g('DIFFIO_L5_G0_00P_MOSI_D0', 'FLASH_D0'); g('DIFFIO_L5_G0_00N_MISO_D1_DI', 'FLASH_D1')
    g('DIFFIO_L5_G0_01P_D2', 'FLASH_D2'); g('DIFFIO_L5_G0_01N_D3', 'FLASH_D3')
    g('DIFFIO_L5_G0_05P_FCS_N', 'FLASH_CS_N'); g('DIFFIO_L5_G0_02P_DQS_IO_STATUS_C', 'IO_STATUS_C')
    g('DIFFIO_L5_G0_03P_D4', 'FLASH_CLK_USR')
    g('DIFFIO_L5_G1_10P_GSCLK', 'SYS_CLK')
    for nm, net in zip(['DIFFIO_L5_G1_06P_D9', 'DIFFIO_L5_G1_06N_D10', 'DIFFIO_L5_G1_07P_D11', 'DIFFIO_L5_G1_07N_D12', 'DIFFIO_L5_G1_09P_D14', 'DIFFIO_L5_G1_09N_D15'],
                       ['TPM_CLK', 'TPM_CS_N', 'TPM_MOSI', 'TPM_MISO', 'TPM_RST_N', 'TPM_PIRQ_N']): g(nm, net)
    for nm, net in zip(['DIFFIO_L5_G2_16P_D30_A14', 'DIFFIO_L5_G2_16N_D29_A13', 'DIFFIO_L5_G2_17P_D28_A12', 'DIFFIO_L5_G2_17N_D27_A11', 'DIFFIO_L5_G3_18P_D26_A10', 'DIFFIO_L5_G3_19P_D24_A8'],
                       ['PSRAM_CLK', 'PSRAM_CS_N', 'PSRAM_D0', 'PSRAM_D1', 'PSRAM_D2', 'PSRAM_D3']): g(nm, net)
    for nm, net in zip(['DIFFIO_L5_G3_19N_D23_A7', 'DIFFIO_L5_G3_21P', 'DIFFIO_L5_G3_21N'], ['RTC_SCL', 'RTC_SDA', 'RTC_INT_N']):
        g(nm, net)
    # bank R4: PHY (RMII), card, UART, sensor, control: J1's signals
    g('DIFFIO_R4_G1_10P_GSCLK', 'ETH_REFCLK')
    r4 = ['ETH_TXD0', 'ETH_TXD1', 'ETH_TXEN', 'ETH_RXD0', 'ETH_RXD1', 'ETH_CRS_DV', 'ETH_RXER', 'ETH_MDC', 'ETH_MDIO', 'ETH_RST_N',
          'SD_CLK', 'SD_CMD', 'SD_D0', 'SD_D1', 'SD_D2', 'SD_D3', 'SD_CD_N', 'HOST_UART_TX', 'HOST_UART_RX',
          'SENS_TX', 'SENS_RX', 'SENS_PWR_EN', 'SENS_DET', 'PB_N', 'TAMPER_N', 'SEAL_IN', 'SEAL_OUT', 'CARRIER_ID', 'PWR_HOLD', 'PGOOD']
    # bank L4: J2's audio, display, speaker, carrier clocks, first GPIO
    g('DIFFIO_L4_G1_10P_GSCLK', 'CLK_REF10M'); g('DIFFIO_L4_G2_13P_GSCLK', 'CLK_SI0'); g('DIFFIO_L4_G1_11P_GMCLK', 'CLK_SI1')
    l4 = [f'AUD{i}_{s}' for i in (1, 2) for s in ('MCLK', 'BCLK', 'FS', 'ADCOUT', 'DACIN', 'SCL', 'SDA')] + \
         ['LCD_SCK', 'LCD_MOSI', 'LCD_DC', 'LCD_CS_N', 'LCD_RST_N', 'LCD_BL_PWM', 'TP_SCL', 'TP_SDA', 'TP_INT_N', 'SPK_PWM'] + [f'GPIO{i}' for i in range(0, 14)]
    r5 = [f'GPIO{i}' for i in range(14, 32)]
    def pool(bank):
        names = sorted((v[1] for b, v in pins.items() if v[0] == bank and byname[v[1]] not in A),
                       key=lambda n: (0 if n.startswith('SIO') else 1, n))
        return [n for n in names if '_VREF' not in n and 'GSCLK' not in n and 'GMCLK' not in n]
    for bank, nets in (('R4', r4), ('L4', l4), ('R5', r5)):
        p = pool(bank)
        assert len(p) >= len(nets), (bank, len(p), len(nets))
        for nm, net in zip(p, nets): g(nm, net)
    # power
    for b, v in pins.items():
        n = v[1]
        if n in ('VCC', 'VCC_DRM'): A[b] = ('p', '+1V0')
        elif n == 'VCCA': A[b] = ('p', '+1V8')
        elif n.startswith('VCCIO') or n == 'SCBV': A[b] = ('p', '+3V3')
        elif n == 'VCCB': A[b] = ('g', 'VCCB')
        elif n == 'VCCADC': A[b] = ('g', 'VCCADC')
        elif n in ('VSS', 'VSSADC'): A[b] = ('p', 'GND')
        elif n == 'VAADC_P': A[b] = ('g', 'ADC_5V_MON')
        elif n == 'VAADC_N': A[b] = ('p', 'GND')
        elif n in ('VREFADC_P', 'VREFADC_N', 'TSDP', 'TSDN'): A[b] = ('nc',)
        elif n.startswith('MODE_'): A[b] = ('g', 'CFG_MODE' + n[-1])
        elif n == 'RSTN': A[b] = ('g', 'FPGA_RST_N')
        elif n == 'INIT_FLAG_N': A[b] = ('g', 'CFG_INIT_N')
        elif n == 'CFG_DONE': A[b] = ('g', 'CFG_DONE')
        elif n == 'CFG_CLK': A[b] = ('g', 'CFG_CLK')
        elif n in ('TCK', 'TMS', 'TDI', 'TDO'): A[b] = ('g', 'JTAG_' + n)
    return A, pins

def j1_assignment():
    """DF40 J1: power, control, ciphertext, MAC'd. pin -> ('g', net) | ('p', power)"""
    sig = {}
    def put(pins_, nets):
        for p, n in zip(pins_, nets): sig[p] = n
    # power on the first contacts of both rows; grounds interleaved by the rule "a ground next to every group"
    put([1, 2, 3, 41, 42, 43], ['+5V_IN'] * 6)
    put([5, 6], ['HOST_UART_TX', 'HOST_UART_RX'])
    put([8, 9, 10, 11], ['JTAG_TCK', 'JTAG_TMS', 'JTAG_TDI', 'JTAG_TDO'])
    put([13, 14, 15, 16, 17, 18, 19], ['SD_CLK', 'SD_CMD', 'SD_D0', 'SD_D1', 'SD_D2', 'SD_D3', 'SD_CD_N'])
    put([21, 22, 24, 25], ['ETH_TXP', 'ETH_TXN', 'ETH_RXP', 'ETH_RXN'])
    put([27, 28], ['ETH_LED1', 'ETH_LED2'])
    put([30, 31, 32, 33], ['SENS_TX', 'SENS_RX', 'SENS_PWR_EN', 'SENS_DET'])
    put([35], ['VBAT_CELL'])
    put([45, 46, 47, 48, 49], ['PB_N_AO', 'TAMPER_N', 'SEAL_IN', 'SEAL_OUT', 'CARRIER_ID'])
    # TPM_PIRQ_N stays inside the module (it is a loader-domain signal); contact 51 is reserved
    put([53, 54], ['RTC_INT_N_AO', 'PWR_HOLD'])     # test and carrier-side observation only
    A = {}
    for p in range(1, 81):
        if p in sig:
            n = sig[p]; A[str(p)] = ('g', n)
        else:
            A[str(p)] = ('p', 'GND')
    # reserved contacts: leave the last ten of the second row unconnected rather than grounded
    for p in [51] + list(range(71, 81)): A[str(p)] = ('nc',)
    return A

def j2_assignment():
    sig = {}
    def put(pins_, nets):
        for p, n in zip(pins_, nets): sig[p] = n
    put([1, 2, 3, 4, 5, 6, 7], [f'AUD1_{s}' for s in ('MCLK', 'BCLK', 'FS', 'ADCOUT', 'DACIN', 'SCL', 'SDA')])
    put([9, 10, 11, 12, 13, 14, 15], [f'AUD2_{s}' for s in ('MCLK', 'BCLK', 'FS', 'ADCOUT', 'DACIN', 'SCL', 'SDA')])
    put([17, 18, 19, 20, 21, 22], ['LCD_SCK', 'LCD_MOSI', 'LCD_DC', 'LCD_CS_N', 'LCD_RST_N', 'LCD_BL_PWM'])
    put([24, 25, 26], ['TP_SCL', 'TP_SDA', 'TP_INT_N'])
    put([28], ['SPK_PWM'])
    put([30, 32, 34], ['CLK_REF10M', 'CLK_SI0', 'CLK_SI1'])
    put(list(range(41, 57)), [f'GPIO{i}' for i in range(0, 16)])
    put(list(range(58, 74)), [f'GPIO{i}' for i in range(16, 32)])
    A = {}
    for p in range(1, 81):
        A[str(p)] = ('g', sig[p]) if p in sig else ('p', 'GND')
    for p in (36, 37, 38, 39, 40, 75, 76, 77, 78, 79, 80): A[str(p)] = ('nc',)
    return A

# ------------------------------------------------------------------ sheet construction
SHEET_HEAD = '''(kicad_sch
(version 20250114)
(generator "eeschema")
(generator_version "9.0")
(uuid "{uuid}")
(paper "{paper}")
(title_block (title {title}) (date "2026-11-18") (rev "0.2") (company "thriller: FPGA root-of-trust platform (github.com/bradleyeckert/thriller)"))
(lib_symbols
)
)'''

def new_sheet(title, paper='A3'):
    return Sheet(SHEET_HEAD.format(uuid=U(), paper=paper, title=q(title)))

def embed_common(sheet):
    for n in ['+3V3', '+1V0', '+1V8', '+3V3_AO', 'GND', 'C', 'R', 'PWR_FLAG']:
        ensure_lib(sheet, f'thriller:{n}', lib_text_from_project(n))

CAP_PROPS = {'100n': {'Footprint': 'Capacitor_SMD:C_0402_1005Metric', 'Description': 'Capacitor 100 nF 16 V X7R 0402', 'LCSC': 'C1525'},
             '4u7': {'Footprint': 'Capacitor_SMD:C_0603_1608Metric', 'Description': 'Capacitor 4.7 uF 10 V X5R 0603', 'LCSC': 'C19666'},
             '1u': {'Footprint': 'Capacitor_SMD:C_0402_1005Metric', 'Description': 'Capacitor 1 uF 10 V X5R 0402', 'LCSC': 'C52923'},
             '56p': {'Footprint': 'Capacitor_SMD:C_0402_1005Metric', 'Description': 'Capacitor 56 pF 50 V C0G 0402, TPM SPI_CS filter (DB5174 4.2); may be omitted', 'LCSC': ''},
             '470n': {'Footprint': 'Capacitor_SMD:C_0402_1005Metric', 'Description': 'Capacitor 470 nF 10 V X5R/X7R 0402 (UG040012 Table 2-6)', 'LCSC': ''},
             '100u': {'Footprint': 'Capacitor_SMD:C_1206_3216Metric', 'Description': 'Capacitor 100 uF 6.3 V X5R 1206', 'LCSC': 'C15008'}}

class RefCounter:
    def __init__(self, start): self.n = dict(start)
    def next(self, prefix):
        self.n[prefix] = self.n.get(prefix, 0) + 1
        return f'{prefix}{self.n[prefix]}'

def add_cap(sheet, refs, value, rail, x, y, sheet_uuid):
    ref = refs.next('C')
    inst = sym_instance('thriller:C', ref, value, x, y, 0, 1, sheet_uuid, ['1', '2'], CAP_PROPS[value])
    sheet.tree.append(inst)
    # C pins: 1 at (0, 3.81) lib -> schematic (x, y-3.81); 2 at (x, y+3.81)
    sheet.tree.append(power_sym(rail, x, y - 3.81, sheet_uuid))
    sheet.tree.append(power_sym('GND', x, y + 3.81, sheet_uuid))

def place_fpga_unit(sheet, unit, x, y, assign, sheet_uuid, lib_pins):
    inst = sym_instance('FPGA_Pango_Logos2:PG2L50H-6IMBG324', 'U1', 'PG2L50H-6IMBG324', x, y, 0, unit, sheet_uuid,
                        [num for (u, num, nm, *_rest) in lib_pins if u == unit],
                        {'Footprint': 'Package_BGA:BGA-324_18x18_15.0x15.0mm_Pitch0.8mm', 'Datasheet': 'Pango PK04006 V1.1 (PG2L50H_MBG324)', 'MPN': 'PG2L50H-6IMBG324', 'LCSC': ''})
    sheet.tree.append(inst)
    connect_pins(sheet, inst, lib_pins, assign, sheet_uuid)
    return inst

def unit_extent(lib_pins, unit):
    xs = [px for (u, num, nm, px, py, *_r) in lib_pins if u == unit]
    ys = [py for (u, num, nm, px, py, *_r) in lib_pins if u == unit]
    return min(xs), max(xs), min(ys), max(ys)

def drop_texts(sheet, needles):
    for t in list(sheet.items('text')):
        if any(n in unq(t[1]) for n in needles): sheet.remove(t)

def edit_texts(sheet, pairs):
    for t in sheet.items('text'):
        v = unq(t[1])
        for a, b in pairs:
            v = v.replace(a, b)
        t[1] = q(v)

def prune_libs(sheet):
    used = set(unq(find1(x, 'lib_id')[1]) for x in sheet.symbols())
    ls = find1(sheet.tree, 'lib_symbols')
    for sym in list(find(ls, 'symbol')):
        if unq(sym[1]) not in used: ls.remove(sym)

# ------------------------------------------------------------------ main
def load(name): return Sheet((PRJ / name).read_text())
def save(sheet, name): (PRJ / name).write_text(sheet.dump())

def root_sheet_uuids():
    root = load('thriller.kicad_sch')
    m = {}
    for sh in root.items('sheet'):
        f = Sheet.prop(sh, 'Sheetfile'); m[f] = unq(find1(sh, 'uuid')[1])
    return root, m

def main():
    root, suuid = root_sheet_uuids()
    fpga_sym = load_fpga324()
    df40 = df40_symbol(); tpm = tpm_symbol()

    # ---- project library: add the two new symbols
    lib = (PRJ / 'thriller.kicad_sym').read_text().rstrip()
    assert lib.endswith(')')
    adds = ''
    for txt in (df40, tpm):
        nm = re.match(r'\(symbol "thriller:([^"]+)"', txt).group(1)
        if f'(symbol "{nm}"' not in lib:
            adds += '\n' + txt.replace(f'(symbol "thriller:{nm}"', f'(symbol "{nm}"', 1)
    (PRJ / 'thriller.kicad_sym').write_text(lib[:-1].rstrip() + adds + '\n)\n')

    # ---- th_power: no input connector, no buttons, no 5V_SW switch, no FPGA units
    sh = load('th_power.kicad_sch')
    delete_refs(sh, {'J1', 'SW1', 'Q3', 'Q4', 'R16', 'C23', 'C24', 'U1'})
    # the 484's core/aux decoupling banks (C25..C67) go with the FPGA units; the 324's set is on th_fpga and the user-bank sheets
    delete_refs(sh, {f'C{i}' for i in range(25, 68)})
    delete_refs(sh, set(), lib_ids={'thriller:+5V_SW'})
    prune(sh)
    # 5 V arrives from J1 (DF40): label the PTC's input
    net = Net(sh)
    for s in sh.symbols():
        if sh.prop(s, 'Reference') == 'F1':
            (x1, y1, n1, _), (x2, y2, n2, _) = sh.pin_points(s)[:2]
            (x, y) = (x1, y1) if n1 == '1' else (x2, y2)
            sh.tree.append(wire((x, y), (x - 7.62, y))); sh.tree.append(glabel('+5V_IN', x - 7.62, y, 180))
    drop_texts(sh, ['5V_SW:', 'FPGA core and auxiliary supplies', 'VCC (14 balls)', 'VCC_DRM (3 balls)', 'VCCA (5 balls)', 'VCCIOL6', 'FPGA ground and no-connect'])
    edit_texts(sh, [('for the RTC, secure element and power control', 'for the RTC and power control (the TPM is on the switched 3V3)'),
                    ('Load: RTC, ATECC608C, pull-ups (uA).', 'Load: RTC, pull-ups (uA).'),
                    ('Start: SW1 or the RTC /INT pulls PWR_ON_N low', 'Start: the carrier button (PB_N_AO) or the RTC /INT pulls PWR_ON_N low'),
                    ('5 V input (always on): fuse, TVS, reverse-polarity FET', '5 V input from J1 (always on): fuse, TVS, reverse-polarity FET')])
    prune_libs(sh)
    tb = find1(sh.tree, 'title_block'); find1(tb, 'title')[1] = q('Power: 5 V from J1, 3V3_AO LDO, 1V0/1V8/3V3 bucks, power control')
    sh.tree.append(text_item('Module: 5 V comes from the carrier through J1 (+5V_IN). The power button and the RTC alarm arrive as PB_N_AO and RTC_INT_N_AO; the switched 5 V rail is gone (the carrier powers its own parts).', 20, 20, 1.5))
    save(sh, 'th_power.kicad_sch')

    # ---- th_base: FPGA units out, ATECC608C and its level shifters out, cells, reset button, JTAG header, mode jumper, DONE LED out; TPM in
    sh = load('th_base.kicad_sch')
    delete_refs(sh, {'U1', 'U7', 'BT1', 'BT2', 'SW2', 'J2', 'JP1', 'D4', 'Q5', 'R28', 'Q6', 'Q7', 'R43', 'R44', 'R47', 'R48', 'R21'})
    delete_on_nets(sh, {'HSST_AVCC', 'HSST_AVCCPLL'}, include_power=True)
    prune(sh)
    # the configuration unit now lives on th_fpga: its straps and filters here become global nets
    for l in list(sh.items('label')):
        nm = unq(l[1]); x, y = label_pos(l); rot = int(float(find1(l, 'at')[3]))
        if nm in ('CFG_MODE0', 'CFG_MODE1', 'CFG_MODE2', 'CFG_INIT_N', 'CFG_DONE', 'CFG_CLK', 'FPGA_RST_N', 'VCCB', 'VCCADC', 'ADC_5V_MON'):
            sh.remove(l); sh.tree.append(glabel(nm, x, y, rot))
    # the oscillator is now 25 MHz and clocks the PHY too
    for s in sh.symbols():
        if sh.prop(s, 'Reference') == 'Y1':
            set_prop(s, 'Value', '25MHz'); set_prop(s, 'LCSC', ''); set_prop(s, 'MPN', '25 MHz 3225 CMOS XO, 3.3 V (choose LCSC part)')
            set_prop(s, 'Description', 'Crystal oscillator 25 MHz 3225, the module clock: FPGA PLL and the PHY (CLKIN)')
    # VBAT from J1: a global label on the VBAT_CELL net; JTAG as global nets
    for l in list(sh.items('label')):
        nm = unq(l[1]); x, y = label_pos(l); at = find1(l, 'at'); rot = int(float(at[3]))
        if nm in ('VBAT_CELL', 'JTAG_TCK', 'JTAG_TMS', 'JTAG_TDI', 'JTAG_TDO', 'OSC_OUT'):
            sh.remove(l); sh.tree.append(glabel(nm if nm != 'OSC_OUT' else 'SYS_CLK', x, y, rot))
    ensure_lib(sh, 'thriller:ST33KTPM2X', tpm)
    embed_common(sh)
    su = suuid['th_base.kicad_sch']
    refs = RefCounter({'C': 270, 'R': 100})
    tx, ty = 330, 240
    inst = sym_instance('thriller:ST33KTPM2X', 'U7', 'ST33KTPM2X32DKG9', tx, ty, 0, 1, su, [str(n) for n in range(1, 34)],
                        {'Footprint': 'Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.6x3.6mm', 'MPN': 'ST33KTPM2X32DKG9', 'LCSC': '', 'Description': 'TPM 2.0, SPI, CMVP #5570; pinout per DB5174 rev 3'})
    sh.tree.append(inst)
    ends = connect_pins(sh, inst, sh.libs['thriller:ST33KTPM2X'],
                 {'1': ('p', '+3V3'), '22': ('p', '+3V3'), '2': ('p', 'GND'), '16': ('p', 'GND'), '33': ('p', 'GND'),
                  '17': ('g', 'TPM_RST_N'), '18': ('g', 'TPM_PIRQ_N'), '19': ('w',), '20': ('g', 'TPM_CS_N'), '21': ('w',), '24': ('w',)}, su)
    add_cap(sh, refs, '100n', '+3V3', tx - 40, ty - 22, su); add_cap(sh, refs, '1u', '+3V3', tx - 30, ty - 22, su)
    def res(value, x, y, rot, desc):
        r = sym_instance('thriller:R', refs.next('R'), value, x, y, rot, 1, su, ['1', '2'], {'Footprint': 'Resistor_SMD:R_0402_1005Metric', 'LCSC': 'C25744' if value == '10k' else '', 'Description': desc})
        sh.tree.append(r); return [(px, py) for (px, py, _, _) in sh.pin_points(r)[:2]]
    # 33 R series on CLK, MOSI, MISO (DB5174 figure 3: line adaptation; fit 0 R if the layout is short and clean)
    for num, net in (('19', 'TPM_CLK'), ('21', 'TPM_MOSI'), ('24', 'TPM_MISO')):
        ex, ey = ends[num]
        p1, p2 = res('33R', ex + 3.81, ey, 90, 'Resistor 33 Ohm 0402, TPM SPI series (DB5174 4.3)')
        assert p1 == (ex, ey), (p1, ends[num])
        sh.tree.append(glabel(net, p2[0], p2[1], 0))
    # RST pull-down so the TPM stays in reset until the boot ROM drives the line (DB5174: RST must not float; the FPGA drives it)
    p1, p2 = res('10k', tx + 38, ty + 12.7, 0, 'Resistor 10 kOhm 0402, TPM RST pull-down')
    sh.tree.append(glabel('TPM_RST_N', p1[0], p1[1], 90)); sh.tree.append(power_sym('GND', p2[0], p2[1], su))
    # PIRQ pull-up, mandatory for standby current (DB5174 figure 3)
    p1, p2 = res('10k', tx + 48, ty + 12.7, 0, 'Resistor 10 kOhm 0402, TPM PIRQ pull-up (mandatory, DB5174 4.3)')
    sh.tree.append(power_sym('+3V3', p1[0], p1[1], su)); sh.tree.append(glabel('TPM_PIRQ_N', p2[0], p2[1], 270))
    # 56 pF on CS so CLK is low when CS falls (DB5174 4.2); optional
    c = sym_instance('thriller:C', refs.next('C'), '56p', tx + 58, ty + 12.7, 0, 1, su, ['1', '2'], CAP_PROPS['56p']); sh.tree.append(c)
    sh.tree.append(glabel('TPM_CS_N', tx + 58, ty + 12.7 - 3.81, 90)); sh.tree.append(power_sym('GND', tx + 58, ty + 12.7 + 3.81, su))
    sh.tree.append(text_item('ST33KTPM2X TPM on SPI from the loader domain (DB5174 rev 3, figure 3).\nRST driven by the FPGA with a 10k pull-down; 10k pull-up on PIRQ (mandatory).\n33R series on CLK/MOSI/MISO and 56p on CS: optional, fit as the layout requires.\nGPIO_PP, GPI_I2C_Select, I2C and NiC pins open (SPI mode). VPS slew 2 V/ms min (table 4).', tx - 45, ty - 44, 1.5))
    drop_texts(sh, ['Fit JP1', 'JTAG: not fitted', 'HSST quad', 'Supplies left floating', 'Secure element (always-on', 'Nothing else on this bus', '2 x SR44', 'FPGA configuration, JTAG, ADC, clock'])
    edit_texts(sh, [('ATECC608C', 'ST33KTPM2X TPM'), ('6. The secure element and the RTC each have their own I2C bus. Pull-ups to 3V3_AO on their side,\n   to +3V3 on the FPGA side. RTC_INT_N and PB_N tell the boot ROM the boot cause.', '6. The TPM is on its own SPI bus from the loader domain. The RTC I2C bus has pull-ups to 3V3_AO on its side,\n   to +3V3 on the FPGA side. RTC_INT_N and PB_N tell the boot ROM the boot cause.'), ('Real-time clock: wake alarm, local time (untrusted)', 'Real-time clock: wake alarm, local time (untrusted). Backup cells are on the carrier (VBAT_CELL via J1); keep CHGEN = 0.')])
    prune_libs(sh)
    tb = find1(sh.tree, 'title_block'); find1(tb, 'title')[1] = q('Base: FPGA configuration support, QSPI flash, TPM, RTC, 25 MHz oscillator')
    save(sh, 'th_base.kicad_sch')

    # ---- th_storage: the card socket leaves; the PSRAM stays
    sh = load('th_storage.kicad_sch')
    delete_refs(sh, {'J4'})
    delete_on_nets(sh, {'SD_VDD', 'SD_CLK_R', 'SD_CLK', 'SD_CMD', 'SD_D0', 'SD_D1', 'SD_D2', 'SD_D3', 'SD_CD_N'})
    prune(sh)
    drop_texts(sh, ['MicroSD:', 'SPI mode first', 'Notes'])
    sh.tree.append(text_item('The MicroSD socket is on the carrier (J1: SD_CLK, SD_CMD, SD_D0..3, SD_CD_N). The PSRAM holds ciphertext only and is outside the trust boundary.', 20, 100, 1.5))
    prune_libs(sh)
    tb = find1(sh.tree, 'title_block'); find1(tb, 'title')[1] = q('Storage: PSRAM stream buffer (the MicroSD socket is on the carrier)')
    save(sh, 'th_storage.kicad_sch')

    # ---- th_ext: only the PHY remains; MDI pairs go to J1; the PHY takes its 25 MHz from the module oscillator
    sh = load('th_ext.kicad_sch')
    delete_refs(sh, {'J5', 'J6', 'J7', 'J8', 'U11', 'U12', 'U13', 'Y2', 'Q8', 'Q9', 'F2', 'C131', 'C142', 'C143'})   # C131: crystal load cap; C142/C143: CH340 decoupling
    delete_on_nets(sh, {'USB_VBUS', 'USB_DP', 'USB_DM', 'USB_CC1', 'USB_CC2', 'CH340_TXD', 'HOST_UART_TX', 'HOST_UART_RX', 'USB_VBUS_DET',
                        'SENS_A', 'SENS_B', 'SENS_VOUT', 'SENS_VSW', 'SENS_SW_G', 'SENS_PWR_EN', 'SENS_TX', 'SENS_RX', 'RJ_LED_G', 'RJ_LED_Y', 'CHASSIS', 'PHY_XO'}, keep_refs={'U10'})
    prune(sh)
    for l in list(sh.items('label')):
        nm = unq(l[1]); x, y = label_pos(l); rot = int(float(find1(l, 'at')[3]))
        if nm in ('ETH_TXP', 'ETH_TXN', 'ETH_RXP', 'ETH_RXN'):
            sh.remove(l); sh.tree.append(glabel(nm, x, y, rot))
        if nm in ('PHY_LED1', 'PHY_LED2'):
            sh.remove(l); sh.tree.append(glabel('ETH_LED' + nm[-1], x, y, rot))
        if nm == 'PHY_XI':   # crystal input becomes the module clock input; the crystal load cap goes with the crystal
            sh.remove(l); sh.tree.append(glabel('SYS_CLK', x, y, rot))
        if nm == 'PHY_XO':
            sh.remove(l)
    prune(sh)
    for s_ in sh.symbols():
        if sh.prop(s_, 'Reference') == 'U10':
            for (x, y, num, nm) in sh.pin_points(s_):
                if num == '4': sh.tree.append(noconn(x, y))
    drop_texts(sh, ['Host UART over USB-C', 'CH340N runs', 'Sensor port:', 'Physical layer is open'])
    edit_texts(sh, [('from its 25 MHz cry', 'from the 25 MHz module oscillator on XTAL1/CLKIN (check REF_CLK out mode with an external clock in the LAN8742A data sheet) rather than a cry'),
                    ('VDDA_PHY: analog supply and magnetics centre taps', 'VDDA_PHY: analog supply. The magnetics centre taps are fed on the carrier')])
    prune_libs(sh)
    tb = find1(sh.tree, 'title_block'); find1(tb, 'title')[1] = q('Ethernet PHY (RMII); magnetics and RJ45 on the carrier')
    sh.tree.append(text_item('Module: the RJ45 with magnetics is on the carrier (J1: ETH_TXP/N, ETH_RXP/N, ETH_LED1/2). The PHY is clocked by the module oscillator on XTAL1/CLKIN (SYS_CLK); XTAL2 open. USB, UART bridge, sensor connector and switch moved to the carrier.', 20, 20, 1.5))
    save(sh, 'th_ext.kicad_sch')

    # ---- FPGA sheets: banks L (A), banks R (B), configuration and power (new th_fpga)
    A, pins = fpga_assignment()
    lib_pins = None
    def fpga_sheet(title, units, name, paper='A3'):
        nonlocal lib_pins
        sh = new_sheet(title, paper)
        ensure_lib(sh, 'FPGA_Pango_Logos2:PG2L50H-6IMBG324', fpga_sym); embed_common(sh)
        lib_pins = sh.libs['FPGA_Pango_Logos2:PG2L50H-6IMBG324']
        return sh
    # th_userA
    sh = fpga_sheet('FPGA banks L3, L4, L5 (3.3 V): configuration flash, TPM, PSRAM, RTC, J2 audio/display', [1, 2, 3], 'th_userA.kicad_sch', 'A2')
    su = suuid['th_userA.kicad_sch']
    x = 15
    for unit in (1, 2, 3):
        x0, x1, y0, y1 = unit_extent(lib_pins, unit)
        X = x - x0 + 45
        place_fpga_unit(sh, unit, X, 200, A, su, lib_pins)
        x = X + x1 + 45
    refs = RefCounter({'C': 200})
    for i, (val, rail) in enumerate([('4u7', '+3V3')] * 3 + [('100n', '+3V3')] * 9):
        add_cap(sh, refs, val, rail, 40 + i * 12, 360, su)
    sh.tree.append(text_item('Bank decoupling (VCCIOL3/L4/L5): 4.7 uF + 3 x 100 nF per bank, placed at the balls. Unused pins carry no-connect flags; VREF pins are left open (3.3 V single-ended banks).', 20, 20, 1.5))
    save(sh, 'th_userA.kicad_sch')
    # th_userB
    sh = fpga_sheet('FPGA banks R4, R5 (3.3 V): PHY, card, UART, sensor, control (J1); GPIO (J2)', [4, 5], 'th_userB.kicad_sch', 'A2')
    su = suuid['th_userB.kicad_sch']
    x = 15
    for unit in (4, 5):
        x0, x1, y0, y1 = unit_extent(lib_pins, unit)
        X = x - x0 + 45
        place_fpga_unit(sh, unit, X, 200, A, su, lib_pins)
        x = X + x1 + 45
    refs = RefCounter({'C': 220})
    for i, (val, rail) in enumerate([('4u7', '+3V3')] * 2 + [('100n', '+3V3')] * 6):
        add_cap(sh, refs, val, rail, 40 + i * 12, 360, su)
    sh.tree.append(text_item('Bank decoupling (VCCIOR4/R5): 4.7 uF + 3 x 100 nF per bank. GPIO0..31 go to J2; the rest of R5 is unused.', 20, 20, 1.5))
    save(sh, 'th_userB.kicad_sch')
    # th_fpga (new): config/JTAG/ADC, core power, ground
    sh = fpga_sheet('FPGA configuration, JTAG, core power and ground', [6, 7, 8], 'th_fpga.kicad_sch')
    fpga_uuid = str(_uuid.uuid5(_uuid.NAMESPACE_URL, 'thriller/th_fpga'))
    su = fpga_uuid
    x = 15
    for unit in (6, 7, 8):
        x0, x1, y0, y1 = unit_extent(lib_pins, unit)
        X = x - x0 + 40
        place_fpga_unit(sh, unit, X, 130, A, su, lib_pins)
        x = X + x1 + 40
    refs = RefCounter({'C': 240})
    # UG040012 table 2-3 scaled to the 324: VCC (14) + VCC_DRM (2) on 1V0, VCCA (4) on 1V8; bulk at the regulators is on th_power
    for i, (val, rail) in enumerate([('100u', '+1V0')] + [('4u7', '+1V0')] * 3 + [('470n', '+1V0')] * 4 + [('100n', '+1V0')] * 6
                                    + [('4u7', '+1V8')] * 2 + [('470n', '+1V8')] * 2 + [('100n', '+1V8')] * 3):
        add_cap(sh, refs, val, rail, 40 + i * 12, 240, su)
    sh.tree.append(text_item('Configuration: MODE[2:0] = 001 (master SPI) strapped on the Base sheet; VCCIOCFG = VCCIOL5 = 3.3 V; SCBV tied to VCCIOCFG. JTAG goes to J1 (fixture carrier only; eFuse-locked after enrollment). VCC/VCC_DRM 1.0 V, VCCA 1.8 V, VCCB and VCCADC filtered from 1.8 V on the Base sheet. Core/aux decoupling below (UG040012 tables 2-3/2-6 scaled to the 324): 1V0: 100u + 3 x 4u7 + 4 x 470n + 6 x 100n; 1V8: 2 x 4u7 + 2 x 470n + 3 x 100n; placed at the balls. Check against the table before layout.', 20, 20, 1.5))
    save(sh, 'th_fpga.kicad_sch')

    # ---- connectors (new th_conn)
    sh = new_sheet('Module connectors J1 and J2 (Hirose DF40C-80DP-0.4V(51), 2 x 80 contacts)', 'A3')
    ensure_lib(sh, 'thriller:DF40C-80DP', df40); embed_common(sh)
    conn_uuid = str(_uuid.uuid5(_uuid.NAMESPACE_URL, 'thriller/th_conn')); su = conn_uuid
    lp = sh.libs['thriller:DF40C-80DP']
    for ref, X, assign, note in (('J1', 90, j1_assignment(), 'J1: power, control, ciphertext and MAC\'d signals. A minimal carrier mates J1 only.'),
                                 ('J2', 260, j2_assignment(), 'J2: audio (plaintext I2S), display, speaker, carrier clocks, GPIO0..31.')):
        inst = sym_instance('thriller:DF40C-80DP', ref, 'DF40C-80DP-0.4V(51)', X, 150, 0, 1, su, [str(n) for n in range(1, 81)],
                            {'Footprint': 'Connector_Hirose:Hirose_DF40C-80DP-0.4V_2x40_P0.40mm', 'MPN': 'DF40C-80DP-0.4V(51)', 'LCSC': ''})
        sh.tree.append(inst)
        connect_pins(sh, inst, lp, assign, su)
        sh.tree.append(text_item(note, X - 40, 80, 1.5))
    sh.tree.append(text_item('Pinout per hw/module.md (H11): nothing but signals leaves the module; +5V_IN on 1-3 and 41-43; a ground next to every signal group; JTAG on J1 is unrouted on production carriers; contacts marked no-connect are reserved. VBAT_CELL: RTC backup from the carrier cells. ETH_LED1/2 are the PHY LED outputs for the carrier jack.', 20, 20, 1.5))
    save(sh, 'th_conn.kicad_sch')

    # ---- root sheet: sheet list and the description text
    for shx in list(root.items('sheet')):
        if Sheet.prop(shx, 'Sheetfile') in ('th_audio.kicad_sch', 'th_display.kicad_sch'):
            root.remove(shx)
    def rename(file, name):
        for shx in root.items('sheet'):
            if Sheet.prop(shx, 'Sheetfile') == file:
                for p in find(shx, 'property'):
                    if unq(p[1]) == 'Sheetname': p[2] = q(name)
    rename('th_userA.kicad_sch', 'FPGA banks L'); rename('th_userB.kicad_sch', 'FPGA banks R'); rename('th_ext.kicad_sch', 'Ethernet PHY')
    rename('th_storage.kicad_sch', 'PSRAM'); rename('th_base.kicad_sch', 'Base: config, flash, TPM, RTC, clock')
    def sheet_entry(name, file, x, y, uid, page):
        return parse(f'''(sheet (at {x} {y}) (size 60 10) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid "{uid}")
(property "Sheetname" "{name}" (at {x} {y - 0.7} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
(property "Sheetfile" "{file}" (at {x} {y + 10.6} 0) (effects (font (size 1.27 1.27)) (justify left top)))
(instances (project "thriller" (path "/{ROOT_UUID}" (page "{page}")))))''')
    root.tree.append(sheet_entry('FPGA config and power', 'th_fpga.kicad_sch', 30, 130, fpga_uuid, '8'))
    root.tree.append(sheet_entry('Module connectors J1, J2', 'th_conn.kicad_sch', 120, 130, conn_uuid, '9'))
    # project file: sheet list (KiCad rewrites it on save; keep it consistent)
    import json
    pro = json.loads((PRJ / 'thriller.kicad_pro').read_text())
    keep = [e for e in pro.get('sheets', []) if e[1] not in ('Audio', 'Display and UI')]
    pro['sheets'] = keep + [[fpga_uuid, 'FPGA config and power'], [conn_uuid, 'Module connectors J1, J2']]
    (PRJ / 'thriller.kicad_pro').write_text(json.dumps(pro, indent=2) + '\n')
    for t in list(root.items('text')): root.remove(t)
    root.tree.insert(root.tree.index(find1(root.tree, 'lib_symbols')) + 1, text_item(
        'thriller module: PG2L50H-6IMBG324 + QSPI flash + ST33KTPM2X TPM + PSRAM + RTC + LAN8742A PHY + 25 MHz XO + regulators, on a potted 20 x ~40 mm card\n'
        'with two Hirose DF40C-80DP-0.4V(51) connectors (J1 power/control/ciphertext, J2 audio/display/clocks/GPIO). See hw/module.md.\n\n'
        'Power: 5 V always on from J1 -> 3V3_AO (RTC, power control). EN_PWR (PB_N_AO | RTC alarm | PWR_HOLD) -> 1V0 -> 1V8 -> 3V3 -> PGOOD.\n'
        'All I/O banks at 3.3 V. Everything with a connector, transducer or user interface is on the carrier.\n'
        'Symbols: thriller.kicad_sym (project) and FPGA_Pango_Logos2.kicad_sym. Nets between pages use global labels.', 20, 25, 1.5))
    tb = find1(root.tree, 'title_block'); find1(tb, 'title')[1] = q('Logos2 Thriller module'); find1(tb, 'rev')[1] = q('0.2')
    save(root, 'thriller.kicad_sch')
    for f in ('th_audio.kicad_sch', 'th_display.kicad_sch'):
        if (PRJ / f).exists(): (PRJ / f).unlink()
    print('done')

if __name__ == '__main__':
    main()
