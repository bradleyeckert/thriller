#!/usr/bin/env python3
"""Small text-level edits to KiCad 9 sheets that keep eeschema's formatting: remove a global label and its stub
wire at a pin, add a stub wire and global label at a pin, add or remove a no-connect flag. Used for the pin
moves of 2026-11-20 (see main); import it for others."""
import re, sys, uuid, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ksch import Sheet, Net, find1, unq, label_pos, wire_ends, on_segment

PRJ = pathlib.Path(__file__).resolve().parents[1] / 'thriller'
STUB = 5.08

def g(v): return f'{v:g}'
def U(tag): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'thriller/edit_pins/' + tag))

def block_re(kind, x, y):
    """Regex for one top-level (kind ...) block whose first (at x y ...) or (xy x y) is at the point."""
    return re.compile(r'\t\(' + kind + r'\b(?:(?!\n\t\)).)*?\n\t\)\n', re.S)

class SheetText:
    def __init__(self, name):
        self.path = PRJ / f'{name}.kicad_sch'; self.text = self.path.read_text(); self.name = name
    def save(self): self.path.write_text(self.text)
    def _remove_blocks(self, kind, pred):
        n = 0
        def sub(m):
            nonlocal n
            if pred(m.group(0)): n += 1; return ''
            return m.group(0)
        self.text = block_re(kind, 0, 0).sub(sub, self.text); return n
    def pin(self, ref, num):
        sh = Sheet(self.text)
        for s in sh.symbols():
            if sh.prop(s, 'Reference') != ref: continue
            for (x, y, n, nm) in sh.pin_points(s):
                if n == num:
                    at = find1(s, 'at'); return (x, y, nm, x < float(at[1]))
        raise KeyError((ref, num))
    def remove_no_connect(self, x, y):
        return self._remove_blocks('no_connect', lambda b: f'(at {g(x)} {g(y)})' in b)
    def add_no_connect(self, x, y, tag):
        self.text = self.text.rstrip()[:-1].rstrip('\n') + f'\n\t(no_connect\n\t\t(at {g(x)} {g(y)})\n\t\t(uuid "{U("nc/" + tag)}")\n\t)\n)\n'
    def remove_label_and_stub(self, name, x, y, left):
        ex = x - STUB if left else x + STUB
        a = self._remove_blocks('global_label', lambda b: b.startswith(f'\t(global_label "{name}"') and f'(at {g(ex)} {g(y)} ' in b)
        b = self._remove_blocks('wire', lambda w: f'(xy {g(x)} {g(y)}) (xy {g(ex)} {g(y)})' in w or f'(xy {g(ex)} {g(y)}) (xy {g(x)} {g(y)})' in w)
        return a, b
    def add_label_and_stub(self, name, x, y, left, shape, tag):
        ex = x - STUB if left else x + STUB
        rot, just = (180, 'right') if left else (0, 'left')
        wire = (f'\t(wire\n\t\t(pts\n\t\t\t(xy {g(x)} {g(y)}) (xy {g(ex)} {g(y)})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
                f'\t\t(uuid "{U("wire/" + tag)}")\n\t)\n')
        lab = (f'\t(global_label "{name}"\n\t\t(shape {shape})\n\t\t(at {g(ex)} {g(y)} {rot})\n\t\t(fields_autoplaced yes)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.143 1.143)\n\t\t\t)\n'
               f'\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U("label/" + tag)}")\n\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n\t\t\t(at {g(ex)} {g(y)} 0)\n'
               f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)\n')
        self.text = self.text.rstrip()[:-1].rstrip('\n') + '\n' + wire + lab + ')\n'

def main():
    ua = SheetText('th_userA')
    # 1. SENS_DET and CARRIER_ID: nets removed, balls become no-connects
    for name, ball in (('SENS_DET', 'H2'), ('CARRIER_ID', 'E1')):
        x, y, nm, left = ua.pin('U1', ball)
        a, b = ua.remove_label_and_stub(name, x, y, left); assert a == 1 and b == 1, (name, a, b)
        ua.add_no_connect(x, y, f'userA/{ball}'); print('removed', name, 'at', ball)
    # 2. U1 G16 no-connect
    x, y, nm, left = ua.pin('U1', 'G16'); ua.add_no_connect(x, y, 'userA/G16'); print('no-connect G16')
    # 3. GPIO32..59: the ten L3 I/O, then R5 (plain and DQS pins, leaving its VREF and clock-capable pins free)
    l3 = ['D9', 'C9', 'B9', 'B8', 'A8', 'C11', 'C10', 'A10', 'A9', 'D10']
    r5 = ['U2', 'V5', 'V4', 'P2', 'R2', 'M4', 'N4', 'R1', 'T1', 'M6', 'N6', 'R6', 'V7', 'V6', 'U9', 'V9', 'U7', 'U6']
    for i, ball in enumerate(l3 + r5):
        name = f'GPIO{32 + i}'
        x, y, nm, left = ua.pin('U1', ball)
        n = ua.remove_no_connect(x, y); assert n == 1, (ball, n)
        ua.add_label_and_stub(name, x, y, left, 'bidirectional', f'userA/{ball}'); print(name, '->', ball, nm)
    ua.save()
    # 4. SENS_27M off J2 35: label and stub go, contact becomes reserved
    c = SheetText('th_conn')
    x, y, nm, left = c.pin('J2', '35')
    a, b = c.remove_label_and_stub('SENS_27M', x, y, left); assert a == 1 and b == 1, (a, b)
    c.add_no_connect(x, y, 'conn/J2/35'); c.save(); print('removed SENS_27M from J2 35')

if __name__ == '__main__':
    main()
