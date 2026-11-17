# blender-kit: bk_generators.py — процедурные пропсы и модули окружения.
# Стиль задаётся профилем проекта: цвета ролей (wood, metal, stone, ...) из palette,
# фаска, плоский шейдинг. Сгенерированное сразу «в стиле», дальше — bk_normalize
# (сборка в атлас палитры), bk_validate, bk_export.
#
# Запуск: первой строкой PARAMS = {...}, затем этот файл, через execute_blender_code.
# Совместим с BLENDER_MCP_SAFE_MODE=1.
#
# PARAMS:
#   kind:     "crate" | "barrel" | "rock" | "fence" | "wall" | "floor_tile" |
#             "pillar" | "tree" | "crystal" | "stairs"
#   name:     базовое имя объектов (по умолчанию = kind)
#   seed:     целое — повторяемость
#   variants: сколько вариантов (раскладываются по оси X)
#   opts:     параметры генератора (см. GEN_DEFAULTS)
#   profile:  {...} — docs/art/asset_profile.json
#   collection: в какую коллекцию положить (создастся)

import bpy
import bmesh
import json
import math
import random
from mathutils import Vector, Matrix

GEN_DEFAULTS = {
    "crate": {"size": 0.8, "frame": 0.08, "roles": ["wood", "wood_dark"]},
    "barrel": {"height": 1.0, "radius": 0.32, "bulge": 0.06, "segments": 10, "roles": ["wood", "metal"]},
    "rock": {"size": 1.0, "detail": 1, "roughness": 0.25, "flatten": 0.6, "roles": ["stone"]},
    "fence": {"length": 2.0, "height": 1.0, "posts": 3, "post": 0.1, "rails": 2, "roles": ["wood"]},
    "wall": {"width": 4.0, "height": 3.0, "thickness": 0.3, "opening": "none",
             "door_w": 1.2, "door_h": 2.2, "win_w": 1.2, "win_h": 1.0, "win_z": 1.2, "trim": 0.15,
             "roles": ["stone", "stone_dark"]},
    "floor_tile": {"size": 2.0, "thickness": 0.15, "roles": ["stone"]},
    "pillar": {"height": 3.0, "radius": 0.25, "segments": 8, "base": 0.2, "roles": ["stone", "stone_dark"]},
    "tree": {"height": 4.0, "trunk_r": 0.15, "style": "round", "crown": 1.2, "layers": 3,
             "roles": ["bark", "foliage"]},
    "crystal": {"height": 1.2, "count": 5, "spread": 0.35, "segments": 6, "roles": ["crystal"]},
    "stairs": {"width": 1.5, "steps": 6, "step_h": 0.18, "step_d": 0.3, "roles": ["stone"]},
}

RESULT = {"ok": True, "objects": [], "warnings": []}


def hex_to_lin(h):
    h = h.strip().lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def role_material(role, profile):
    pal = profile.get("palette", {})
    hexc = pal.get(role)
    if hexc is None:
        # wood_dark -> wood, stone_dark -> stone
        base = role.split("_")[0]
        hexc = pal.get(base)
        if hexc is not None and role.endswith("_dark"):
            rgb = hex_to_lin(hexc)
            lin = [c * 0.45 for c in rgb]
            return make_mat("M_" + role, lin, profile)
    if hexc is None:
        RESULT["warnings"].append("в палитре нет роли '%s' — серый" % role)
        return make_mat("M_" + role, [0.35, 0.35, 0.35], profile)
    return make_mat("M_" + role, hex_to_lin(hexc), profile)


def make_mat(name, lin, profile):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = None
    for nd in mat.node_tree.nodes:
        if nd.type == "BSDF_PRINCIPLED":
            bsdf = nd
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (lin[0], lin[1], lin[2], 1.0)
        bsdf.inputs["Roughness"].default_value = float(profile.get("roughness", 0.8))
    mat.diffuse_color = (lin[0], lin[1], lin[2], 1.0)
    return mat


def faces_of(verts):
    out = set()
    for v in verts:
        for f in v.link_faces:
            out.add(f)
    return out


def tag(faces, idx):
    for f in faces:
        f.material_index = idx


def add_box(bm, center, size, idx, rot=None):
    m = Matrix.Translation(Vector(center))
    if rot is not None:
        m = m @ rot
    m = m @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    tag(faces_of(res["verts"]), idx)
    return res["verts"]


def add_cyl(bm, center, r1, r2, depth, seg, idx, rot=None):
    m = Matrix.Translation(Vector(center))
    if rot is not None:
        m = m @ rot
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                radius1=r1, radius2=r2, depth=depth, matrix=m)
    tag(faces_of(res["verts"]), idx)
    return res["verts"]


def add_ico(bm, center, radius, subdiv, idx, scale=(1.0, 1.0, 1.0)):
    m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius, matrix=m)
    tag(faces_of(res["verts"]), idx)
    return res["verts"]


# ---------- генераторы: bm, opts, rng -> None (геометрия от z=0 вверх) ----------

def gen_crate(bm, o, rng):
    s = o["size"] * rng.uniform(0.92, 1.08)
    f = o["frame"]
    add_box(bm, (0, 0, s / 2), (s - f * 0.6, s - f * 0.6, s - f * 0.6), 0)
    h = s / 2 - f / 2
    for x in (-h, h):
        for y in (-h, h):
            add_box(bm, (x, y, s / 2), (f, f, s), 1)
    for z in (f / 2, s - f / 2):
        for y in (-h, h):
            add_box(bm, (0, y, z), (s, f, f), 1)
        for x in (-h, h):
            add_box(bm, (x, 0, z), (f, s, f), 1)
    if rng.random() < 0.5:
        rot = Matrix.Rotation(math.atan2(s - 2 * f, s - 2 * f), 4, "Y")
        for y in (-h, h):
            add_box(bm, (0, y, s / 2), (math.sqrt(2) * (s - 2 * f), f * 0.9, f * 0.9), 1, rot)


def gen_barrel(bm, o, rng):
    h = o["height"] * rng.uniform(0.92, 1.08)
    r = o["radius"]
    b = o["bulge"]
    seg = int(o["segments"])
    q = h / 4.0
    add_cyl(bm, (0, 0, q / 2), r, r + b, q, seg, 0)
    add_cyl(bm, (0, 0, q * 2), r + b, r + b, q * 2, seg, 0)
    add_cyl(bm, (0, 0, h - q / 2), r + b, r, q, seg, 0)
    for z in (q * 0.9, h - q * 0.9):
        add_cyl(bm, (0, 0, z), r + b * 0.85 + 0.015, r + b * 0.85 + 0.015, h * 0.05, seg, 1)


def gen_rock(bm, o, rng):
    s = o["size"]
    verts = add_ico(bm, (0, 0, 0), s / 2, int(o["detail"]), 0,
                    (rng.uniform(0.8, 1.2), rng.uniform(0.8, 1.2), rng.uniform(0.55, 0.85)))
    for v in verts:
        n = v.co.normalized()
        v.co = v.co + n * (rng.uniform(-1.0, 1.0) * o["roughness"] * s / 2)
    zmin = min(v.co.z for v in verts)
    cut = zmin + (0.0 - zmin) * o["flatten"]
    for v in verts:
        if v.co.z < cut:
            v.co.z = cut
    for v in verts:
        v.co.z -= cut


def gen_fence(bm, o, rng):
    L = o["length"]
    H = o["height"]
    p = o["post"]
    n = max(2, int(o["posts"]))
    for i in range(n):
        x = -L / 2 + L * i / (n - 1)
        hh = H * rng.uniform(0.95, 1.05)
        add_box(bm, (x, 0, hh / 2), (p, p, hh), 0)
    rails = max(1, int(o["rails"]))
    for j in range(rails):
        z = H * (0.3 + 0.5 * j / max(1, rails - 1)) if rails > 1 else H * 0.6
        add_box(bm, (0, 0, z), (L + p, p * 0.6, p * 0.8), 0)


def gen_wall(bm, o, rng):
    W = o["width"]
    H = o["height"]
    T = o["thickness"]
    op = o["opening"]
    tr = o["trim"]
    if op == "door":
        ow, oh, oz = o["door_w"], o["door_h"], 0.0
    elif op == "window":
        ow, oh, oz = o["win_w"], o["win_h"], o["win_z"]
    else:
        ow = 0.0
    if ow > 0:
        side = (W - ow) / 2
        add_box(bm, (-W / 2 + side / 2, 0, H / 2), (side, T, H), 0)
        add_box(bm, (W / 2 - side / 2, 0, H / 2), (side, T, H), 0)
        top = H - (oz + oh)
        if top > 1e-3:
            add_box(bm, (0, 0, oz + oh + top / 2), (ow, T, top), 0)
        if oz > 1e-3:
            add_box(bm, (0, 0, oz / 2), (ow, T, oz), 0)
        add_box(bm, (0, 0, oz + oh + tr / 2), (ow + tr * 2, T + tr * 0.5, tr), 1)
    else:
        add_box(bm, (0, 0, H / 2), (W, T, H), 0)
    if tr > 0:
        add_box(bm, (0, 0, tr / 2), (W, T + tr * 0.6, tr), 1)
        add_box(bm, (0, 0, H - tr / 2), (W, T + tr * 0.6, tr), 1)


def gen_floor_tile(bm, o, rng):
    s = o["size"]
    t = o["thickness"]
    add_box(bm, (0, 0, t / 2), (s, s, t), 0)


def gen_pillar(bm, o, rng):
    H = o["height"]
    r = o["radius"]
    b = o["base"]
    seg = int(o["segments"])
    add_box(bm, (0, 0, b / 2), (r * 3, r * 3, b), 1)
    add_cyl(bm, (0, 0, H / 2), r * 1.05, r * 0.92, H - 2 * b, seg, 0)
    add_box(bm, (0, 0, H - b / 2), (r * 3, r * 3, b), 1)


def gen_tree(bm, o, rng):
    H = o["height"] * rng.uniform(0.85, 1.15)
    tr = o["trunk_r"]
    crown = o["crown"] * rng.uniform(0.85, 1.15)
    if o["style"] == "pine":
        trunk_h = H * 0.3
        add_cyl(bm, (0, 0, trunk_h / 2), tr, tr * 0.7, trunk_h, 6, 0)
        layers = max(1, int(o["layers"]))
        lh = (H - trunk_h) / layers * 1.4
        for i in range(layers):
            z = trunk_h + i * (H - trunk_h) / layers + lh / 2
            rr = crown * (1.0 - i / (layers + 0.5))
            add_cyl(bm, (0, 0, z), rr, 0.0, lh, 7, 1)
    else:
        trunk_h = H * 0.5
        add_cyl(bm, (0, 0, trunk_h / 2), tr, tr * 0.6, trunk_h, 6, 0)
        blobs = max(1, int(o["layers"]))
        for i in range(blobs):
            ang = rng.uniform(0, math.tau)
            off = crown * 0.35 * (0 if i == 0 else 1)
            c = (math.cos(ang) * off, math.sin(ang) * off, H - crown * 0.8 + rng.uniform(-0.2, 0.2) * crown)
            v = add_ico(bm, c, crown * rng.uniform(0.6, 0.85), 1, 1, (1.0, 1.0, 0.85))
            for vv in v:
                vv.co = vv.co + vv.co.normalized() * rng.uniform(-0.06, 0.06) * crown


def gen_crystal(bm, o, rng):
    H = o["height"]
    n = max(1, int(o["count"]))
    seg = int(o["segments"])
    for i in range(n):
        h = H * (1.0 if i == 0 else rng.uniform(0.35, 0.75))
        r = h * rng.uniform(0.12, 0.18)
        ang = rng.uniform(0, math.tau)
        d = 0.0 if i == 0 else o["spread"] * rng.uniform(0.4, 1.0)
        tilt = 0.0 if i == 0 else rng.uniform(0.25, 0.6)
        rot = Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(tilt, 4, "Y")
        base = Vector((math.cos(ang) * d, math.sin(ang) * d, 0.0))
        body = h * 0.8
        tip = h * 0.2
        c1 = base + (rot @ Vector((0, 0, body / 2)))
        add_cyl(bm, tuple(c1), r, r, body, seg, 0, rot)
        c2 = base + (rot @ Vector((0, 0, body + tip / 2)))
        add_cyl(bm, tuple(c2), r, 0.0, tip, seg, 0, rot)


def gen_stairs(bm, o, rng):
    w = o["width"]
    n = max(1, int(o["steps"]))
    sh = o["step_h"]
    sd = o["step_d"]
    for i in range(n):
        h = sh * (i + 1)
        add_box(bm, (0, -i * sd - sd / 2 + n * sd / 2, h / 2), (w, sd, h), 0)


GENERATORS = ["crate", "barrel", "rock", "fence", "wall", "floor_tile", "pillar",
              "tree", "crystal", "stairs"]


def build(kind, bm, o, rng):
    # Явная диспетчеризация: safe mode не пропускает вызов через словарь функций.
    if kind == "crate":
        gen_crate(bm, o, rng)
    elif kind == "barrel":
        gen_barrel(bm, o, rng)
    elif kind == "rock":
        gen_rock(bm, o, rng)
    elif kind == "fence":
        gen_fence(bm, o, rng)
    elif kind == "wall":
        gen_wall(bm, o, rng)
    elif kind == "floor_tile":
        gen_floor_tile(bm, o, rng)
    elif kind == "pillar":
        gen_pillar(bm, o, rng)
    elif kind == "tree":
        gen_tree(bm, o, rng)
    elif kind == "crystal":
        gen_crystal(bm, o, rng)
    elif kind == "stairs":
        gen_stairs(bm, o, rng)


def bevel_hard_edges(bm, width):
    if width <= 0:
        return
    edges = []
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(40):
            edges.append(e)
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type="OFFSET", segments=1,
                        profile=0.5, affect="EDGES", clamp_overlap=True)


def run(p):
    kind = p.get("kind")
    if kind not in GENERATORS:
        return {"ok": False, "errors": ["неизвестный kind: %s; есть: %s" % (kind, sorted(GENERATORS))]}
    profile = p.get("profile", {})
    opts = dict(GEN_DEFAULTS[kind])
    for k in p.get("opts", {}):
        opts[k] = p["opts"][k]
    seed = int(p.get("seed", 1))
    n = max(1, int(p.get("variants", 1)))
    name = p.get("name", kind)
    colname = p.get("collection", "BK_Generated")
    col = bpy.data.collections.get(colname)
    if col is None:
        col = bpy.data.collections.new(colname)
        bpy.context.scene.collection.children.link(col)
    mats = [role_material(r, profile) for r in opts["roles"]]
    bevel = float(p.get("bevel", profile.get("bevel", 0.0)))
    flat = profile.get("shading", "flat") == "flat"
    spacing = float(p.get("spacing", 0.0))
    x = 0.0
    for i in range(n):
        rng = random.Random(seed + i)
        bm = bmesh.new()
        build(kind, bm, opts, rng)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        if kind in ("crate", "fence", "wall", "floor_tile", "pillar", "stairs"):
            bevel_hard_edges(bm, bevel)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        objname = name if n == 1 else "%s_%02d" % (name, i + 1)
        me = bpy.data.meshes.new(objname)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        me.polygons.foreach_set("use_smooth", [not flat] * len(me.polygons))
        me.uv_layers.new(name="UVMap")
        me.update()
        ob = bpy.data.objects.new(objname, me)
        col.objects.link(ob)
        w = ob.dimensions.x if ob.dimensions.x > 0 else 1.0
        gap = spacing if spacing > 0 else max(0.5, w * 0.5)
        ob.location = (x + w / 2, 0.0, 0.0)
        x += w + gap
        tris = 0
        for poly in me.polygons:
            tris += len(poly.vertices) - 2
        d = ob.dimensions
        RESULT["objects"].append({"name": ob.name, "tris": tris,
                                  "dims_m": [round(d.x, 3), round(d.y, 3), round(d.z, 3)]})
    RESULT["kind"] = kind
    RESULT["seed"] = seed
    return RESULT


print("\nBK_RESULT " + json.dumps(run(PARAMS), ensure_ascii=False))
