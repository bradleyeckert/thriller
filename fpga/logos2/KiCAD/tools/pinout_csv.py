#!/usr/bin/env python3
"""Regenerate hw/module-pinout.csv from the schematic.

Contact, net, FPGA ball and bank come from the sheets (J1/J2 on th_conn, the PG2L50H-6IMBG324 wherever its units
are); group, class and note are kept from the existing CSV by net name, so they can be edited by hand and survive.
Also writes fpga/logos2/pinout324-assignment.csv (every ball with its net). Run from fpga/logos2/KiCAD; pass
--check to report differences without writing."""
import csv, glob, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ksch import *

KICAD = pathlib.Path(__file__).resolve().parents[1]
PRJ = KICAD / 'thriller'
CSV = KICAD.parents[2] / 'hw' / 'module-pinout.csv'
BALLS = KICAD.parent / 'pinout324.json'
ASSIGN = KICAD.parent / 'pinout324-assignment.csv'

def net_name(net, p, ncs):
    pins, names = net.describe(net.find(p))
    if names: return sorted(names, key=len)[0]
    pw = [q for q in pins if '.' not in q]           # power symbols
    if pw: return pw[0]
    return '' if p in ncs else '???'

def main(check=False):
    # connector contacts
    sh = Sheet(open(PRJ / 'th_conn.kicad_sch').read()); net = Net(sh)
    ncs = set(label_pos(n) for n in sh.items('no_connect'))
    contacts = []
    for s in sh.symbols():
        ref = sh.prop(s, 'Reference')
        if ref not in ('J1', 'J2'): continue
        for (x, y, num, nm) in sh.pin_points(s):
            contacts.append((ref, int(num), net_name(net, (x, y), ncs)))
    contacts.sort()
    # FPGA balls
    balls = json.load(open(BALLS)); ball_of = {}; net_of_ball = {}
    for f in glob.glob(str(PRJ / '*.kicad_sch')):
        S = Sheet(open(f).read()); N = Net(S)
        for s in S.symbols():
            if not unq(find1(s, 'lib_id')[1]).endswith('PG2L50H-6IMBG324'): continue
            for (x, y, num, nm) in S.pin_points(s):
                pins, names = N.describe(N.find((x, y)))
                n = sorted(names, key=len)[0] if names else next((q for q in pins if '.' not in q), '')
                if n: net_of_ball[num] = n; ball_of.setdefault(n, []).append(num)
    # annotations from the existing CSV
    old = {}
    if CSV.exists():
        for r in csv.DictReader(open(CSV)):
            key = r['net'] or ('', r['connector'], r['contact'])
            old.setdefault(key, r)
    rows = []
    for ref, num, n in contacts:
        a = old.get(n) or old.get(('', ref, str(num))) or {}
        b = ball_of.get(n, [])
        if n in ('GND', '+5V', '') or n.startswith('+'): b = []
        note = a.get('note', '')
        if n == '': grp, cls, note = 'Reserved', '', 'unconnected on both sides'
        else:
            grp, cls = a.get('group', ''), a.get('class', '')
            if not b and n not in ('GND', '+5V') and not n.startswith('+') and n not in ('VBAT_CELL', 'PB_N_AO', 'RTC_INT_N_AO', 'ETH_TXP', 'ETH_TXN', 'ETH_RXP', 'ETH_RXN', 'ETH_LED1', 'ETH_LED2'):
                note = 'FPGA ball not wired yet'
            elif note == 'FPGA ball not wired yet': note = ''
        rows.append({'connector': ref, 'contact': num, 'net': n, 'group': grp, 'class': cls,
                     'fpga_ball': ','.join(b), 'fpga_bank': ','.join(sorted({balls[x][0] for x in b if x in balls})), 'note': note})
    fields = ['connector', 'contact', 'net', 'group', 'class', 'fpga_ball', 'fpga_bank', 'note']
    if check:
        cur = list(csv.DictReader(open(CSV))) if CSV.exists() else []
        diffs = [(c, r) for c, r in zip(cur, rows) if {k: str(v) for k, v in r.items()} != c]
        for c, r in diffs: print('csv:', c, '\nsch:', r, '\n')
        print(len(diffs), 'rows differ' if diffs else 'rows differ: CSV matches the schematic')
        return
    with open(CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    with open(ASSIGN, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['ball', 'bank', 'pin_name', 'net'])
        for b in sorted(balls, key=lambda k: (k[0], int(k[1:]))):
            w.writerow([b, balls[b][0], balls[b][1], net_of_ball.get(b, '')])
    print('wrote', CSV, 'and', ASSIGN)
    unwired = [n for _, _, n in contacts if n and n not in ball_of and not n.startswith(('+', 'GND'))]
    print('contacts without an FPGA ball:', unwired)

if __name__ == '__main__':
    main(check='--check' in sys.argv)
