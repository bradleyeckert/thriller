"""Minimal KiCad 9 schematic s-expression toolkit: parse, query geometry, delete with pruning, add items, serialize."""
import re, math, uuid as _uuid

TOK = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)', re.S)

def parse(text):
    pos, stack, root = 0, [[]], None
    for m in TOK.finditer(text):
        t = m.group(1)
        if t == '(': stack.append([])
        elif t == ')':
            x = stack.pop(); stack[-1].append(x)
        else: stack[-1].append(t)
    assert len(stack) == 1 and len(stack[0]) == 1, "unbalanced"
    return stack[0][0]

def q(s):  # quote a string token (KiCad escapes: \\ \" \n)
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def unq(t):
    if not (isinstance(t, str) and t.startswith('"')): return t
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), t[1:-1])

def serialize(node, depth=0):
    """One list per line, children indented; matches eeschema's style closely enough."""
    if not isinstance(node, list): return node
    head = []
    i = 0
    # inline leading atoms and small inline lists (like (at x y) (effects ...)) until a list containing lists appears
    parts = []
    inline = True
    out_lines = []
    cur = '('
    first = True
    for item in node:
        if isinstance(item, list):
            if any(isinstance(c, list) for c in item) or item and item[0] in ('symbol', 'property', 'pin', 'wire', 'label', 'global_label', 'junction', 'no_connect', 'sheet', 'text', 'instances', 'lib_symbols', 'polyline', 'rectangle', 'title_block', 'kicad_sch', 'kicad_symbol_lib', 'project', 'path', 'pts', 'effects', 'stroke', 'fill', 'font'):
                inline = False
        if inline:
            cur += ('' if first else ' ') + (serialize(item) if isinstance(item, list) else item)
        else:
            if not isinstance(item, list):
                cur += ('' if first else ' ') + item
            else:
                s = serialize(item, depth + 1)
                if '\n' in s or len(s) > 100 or (item and item[0] in ('symbol', 'property', 'pin', 'wire', 'label', 'global_label', 'junction', 'no_connect', 'sheet', 'text', 'instances', 'lib_symbols', 'polyline', 'rectangle', 'title_block', 'project', 'path', 'kicad_sch')):
                    out_lines.append(cur); cur = ''
                    out_lines.append(s)
                else:
                    cur += (' ' if cur else '') + s
        first = False
    if cur: out_lines.append(cur)
    out_lines[-1] += ')'
    return '\n'.join(out_lines)

def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]

def find1(node, key):
    f = find(node, key); return f[0] if f else None

def new_uuid():
    return str(_uuid.uuid4())

# ---------------------------------------------------------------- geometry
def rot_mirror(px, py, rot, mirror):
    # library coords (y up) -> schematic offset (y down)
    if mirror == 'x': py = -py
    if mirror == 'y': px = -px
    r = math.radians(rot)
    c, s = round(math.cos(r)), round(math.sin(r))
    rx, ry = px * c - py * s, px * s + py * c
    return rx, -ry

class Sheet:
    def __init__(self, text):
        self.tree = parse(text)
        assert self.tree[0] == 'kicad_sch'
        self.libs = {}
        ls = find1(self.tree, 'lib_symbols')
        for sym in find(ls, 'symbol'):
            name = unq(sym[1])
            pins = []  # (unit, number, name, x, y)
            for sub in find(sym, 'symbol'):
                m = re.search(r'_(\d+)_\d+"?$', sub[1]); unit = int(m.group(1))
                for p in find(sub, 'pin'):
                    at = find1(p, 'at'); num = unq(find1(p, 'number')[1]); nm = unq(find1(p, 'name')[1])
                    pins.append((unit, num, nm, float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0, float(find1(p, 'length')[1]) if find1(p, 'length') else 0))
            self.libs[name] = pins

    def symbols(self):
        return [c for c in self.tree if isinstance(c, list) and c and c[0] == 'symbol']

    @staticmethod
    def prop(sym, name):
        for p in find(sym, 'property'):
            if unq(p[1]) == name: return unq(p[2])
        return None

    def pin_points(self, sym):
        lib = unq(find1(sym, 'lib_id')[1]); at = find1(sym, 'at')
        x, y, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0
        mir = find1(sym, 'mirror'); mir = mir[1] if mir else None
        unit = int(find1(sym, 'unit')[1]) if find1(sym, 'unit') else 1
        pts = []
        for (u, num, nm, px, py, prot, plen) in self.libs[lib]:
            if u not in (0, unit): continue
            dx, dy = rot_mirror(px, py, rot, mir)
            pts.append((round(x + dx, 3), round(y + dy, 3), num, nm))
        return pts

    def items(self, key):
        return [c for c in self.tree if isinstance(c, list) and c and c[0] == key]

    def remove(self, item):
        self.tree.remove(item)

    def dump(self):
        return serialize(self.tree) + '\n'

def wire_ends(w):
    pts = find1(w, 'pts'); xy = find(pts, 'xy')
    return (float(xy[0][1]), float(xy[0][2])), (float(xy[1][1]), float(xy[1][2]))

def on_segment(p, a, b, eps=0.01):
    (px, py), (ax, ay), (bx, by) = p, a, b
    if abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) > eps: return False
    return min(ax, bx) - eps <= px <= max(ax, bx) + eps and min(ay, by) - eps <= py <= max(ay, by) + eps

def label_pos(l):
    at = find1(l, 'at'); return (float(at[1]), float(at[2]))

# ---------------------------------------------------------------- connectivity
class Net:
    def __init__(self, sheet):
        self.sh = sheet
        self.parent = {}
        self.names = {}
        wires = sheet.items('wire')
        self.wires = wires
        pts = []
        for w in wires:
            a, b = wire_ends(w); pts += [a, b]
        for p in pts: self.parent.setdefault(p, p)
        # wire ends connect; ends on other wire interiors connect
        for w in wires:
            a, b = wire_ends(w); self.union(a, b)
        for p in list(self.parent):
            for w in wires:
                a, b = wire_ends(w)
                if p != a and p != b and on_segment(p, a, b): self.union(p, a)
        # pins
        self.pin_at = {}
        for s in sheet.symbols():
            ref = sheet.prop(s, 'Reference')
            for (x, y, num, nm) in sheet.pin_points(s):
                p = (x, y); self.parent.setdefault(p, p)
                self.attach_point(p)
                self.pin_at.setdefault(p, []).append((s, ref, num, nm))
        for l in sheet.items('label') + sheet.items('global_label'):
            p = label_pos(l); self.parent.setdefault(p, p); self.attach_point(p)
            self.names.setdefault(self.find(p), set()).add(unq(l[1]))
    def attach_point(self, p):
        for w in self.wires:
            a, b = wire_ends(w)
            if on_segment(p, a, b): self.union(p, a); break
    def find(self, p):
        while self.parent[p] != p:
            self.parent[p] = self.parent[self.parent[p]]; p = self.parent[p]
        return p
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.parent[ra] = rb
    def net_of(self, p):
        return self.find(p)
    def members(self):
        groups = {}
        for p in self.parent: groups.setdefault(self.find(p), []).append(p)
        return groups
    def describe(self, root):
        pins = []
        for p in self.members().get(root, []):
            for (s, ref, num, nm) in self.pin_at.get(p, []):
                pins.append(f"{ref}.{num}({nm})" if not ref.startswith('#') else f"{self.sh.prop(s,'Value')}")
        return sorted(set(pins)), sorted(self.names.get(root, set()))
