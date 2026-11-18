#!/usr/bin/env python3
"""Rough SVG/PNG preview of a KiCad schematic sheet (symbol bodies, pins, wires, labels) for checking generated sheets without KiCad."""
import sys, re, html, pathlib, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ksch import *

def render(path, out_png, scale=4):
    sh = Sheet(open(path).read())
    paper = unq(find1(sh.tree, 'paper')[1]); W, H = {'A2': (594, 420), 'A3': (420, 297), 'A4': (297, 210)}.get(paper, (420, 297))
    S = scale; el = []
    # library graphics: rectangles and polylines per lib symbol
    ls = find1(sh.tree, 'lib_symbols'); gfx = {}
    for sym in find(ls, 'symbol'):
        name = unq(sym[1]); g = []
        for sub in find(sym, 'symbol'):
            m = re.search(r'_(\d+)_\d+"?$', sub[1]); unit = int(m.group(1))
            for r in find(sub, 'rectangle'):
                a, b = find1(r, 'start'), find1(r, 'end'); g.append((unit, 'rect', float(a[1]), float(a[2]), float(b[1]), float(b[2])))
            for pl in find(sub, 'polyline'):
                pts = [(float(p[1]), float(p[2])) for p in find(find1(pl, 'pts'), 'xy')]; g.append((unit, 'poly', pts))
        gfx[name] = g
    for s in sh.symbols():
        lib = unq(find1(s, 'lib_id')[1]); at = find1(s, 'at'); x, y, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0
        mir = find1(s, 'mirror'); mir = mir[1] if mir else None
        unit = int(find1(s, 'unit')[1]) if find1(s, 'unit') else 1
        for g in gfx.get(lib, []):
            if g[0] not in (0, unit): continue
            if g[1] == 'rect':
                (ax, ay), (bx, by) = rot_mirror(g[2], g[3], rot, mir), rot_mirror(g[4], g[5], rot, mir)
                x0, x1 = sorted((x + ax, x + bx)); y0, y1 = sorted((y + ay, y + by))
                el.append(f'<rect x="{x0*S}" y="{y0*S}" width="{(x1-x0)*S}" height="{(y1-y0)*S}" fill="#fff8dc" stroke="#800" stroke-width="1"/>')
            else:
                pts = ' '.join(f'{(x+dx)*S},{(y+dy)*S}' for (px, py) in g[2] for (dx, dy) in [rot_mirror(px, py, rot, mir)])
                el.append(f'<polyline points="{pts}" fill="none" stroke="#800" stroke-width="1"/>')
        ref = sh.prop(s, 'Reference'); val = sh.prop(s, 'Value')
        el.append(f'<text x="{x*S+3}" y="{y*S-3}" font-size="{2.0*S}" fill="#600" font-family="sans-serif">{html.escape(ref if not ref.startswith("#") else val)}</text>')
        # pins
        for (u, num, nm, px, py, prot, plen) in sh.libs[lib]:
            if u not in (0, unit): continue
            dx, dy = rot_mirror(px, py, rot, mir); ex, ey = rot_mirror(px + plen * round(__import__('math').cos(__import__('math').radians(prot))), py + plen * round(__import__('math').sin(__import__('math').radians(prot))), rot, mir)
            el.append(f'<line x1="{(x+dx)*S}" y1="{(y+dy)*S}" x2="{(x+ex)*S}" y2="{(y+ey)*S}" stroke="#a00" stroke-width="1"/>')
            el.append(f'<circle cx="{(x+dx)*S}" cy="{(y+dy)*S}" r="1.5" fill="#a00"/>')
            if len(sh.libs[lib]) < 400:
                el.append(f'<text x="{(x+ex)*S}" y="{(y+ey)*S+2}" font-size="{1.1*S}" fill="#444" font-family="sans-serif">{html.escape(nm if nm != "~" else "")}</text>')
    for w in sh.items('wire'):
        a, b = wire_ends(w); el.append(f'<line x1="{a[0]*S}" y1="{a[1]*S}" x2="{b[0]*S}" y2="{b[1]*S}" stroke="#064" stroke-width="1.2"/>')
    for l in sh.items('global_label') + sh.items('label'):
        x, y = label_pos(l); rot = int(float(find1(l, 'at')[3])); nm = unq(l[1])
        anchor = 'end' if rot == 180 else 'start'
        tr = f' transform="rotate(-90 {x*S} {y*S})"' if rot in (90, 270) else ''
        col = '#036' if l[0] == 'global_label' else '#630'
        el.append(f'<text x="{x*S + (4 if rot == 0 else -4 if rot == 180 else 0)}" y="{y*S - 2}" font-size="{1.6*S}" fill="{col}" text-anchor="{anchor}" font-family="sans-serif"{tr}>{html.escape(nm)}</text>')
    for n in sh.items('no_connect'):
        x, y = label_pos(n); el.append(f'<text x="{x*S-4}" y="{y*S+4}" font-size="{2*S}" fill="#00a">x</text>')
    for t in sh.items('text'):
        x, y = label_pos(t)
        for i, line in enumerate(unq(t[1]).replace('\\n', '\n').split('\n')):
            el.append(f'<text x="{x*S}" y="{y*S + (i+1)*1.8*S}" font-size="{1.5*S}" fill="#000" font-family="sans-serif">{html.escape(line)}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*S}" height="{H*S}" style="background:#fff">' + '\n'.join(el) + '</svg>'
    svgp = pathlib.Path(out_png).with_suffix('.svg'); svgp.write_text(svg)
    subprocess.run(['rsvg-convert', '-o', out_png, str(svgp)], check=True)

if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 4)
