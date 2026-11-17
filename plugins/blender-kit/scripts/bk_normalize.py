# blender-kit: bk_normalize.py — приводит любой меш (CC0, магазин, AI, процедурный)
# к стандарту проекта: трансформы, масштаб, пивот, чистка, бюджет трисов,
# перекраска в палитру проекта, имя.
#
# Запуск: через execute_blender_code. Первой строкой агент вставляет
#   PARAMS = {...}
# затем весь этот файл. Совместим с BLENDER_MCP_SAFE_MODE=1:
# без open/os/exec/классов/lambda/генераторов, только bpy, bmesh, mathutils, math, json, array.
#
# PARAMS:
#   objects:   ["имя", ...]       — какие объекты (или collection: "имя", или selected: true)
#   name:      "crate_small"      — итоговое имя ассета (snake_case)
#   category:  "prop"             — ключ бюджета из profile.budgets
#   profile:   {...}              — содержимое docs/art/asset_profile.json
#   size:      {"height": 1.0}    — или {"longest": 2.0}; без size масштаб не трогаем
#   join:      true               — объединить объекты в один меш
#   recolor:   "palette" | "keep" — перекрасить в палитру профиля или оставить материалы
#   to_origin: true               — поставить ассет в начало координат

import bpy
import bmesh
import json
import math
import array
from mathutils import Vector, Matrix

RESULT = {"ok": True, "steps": [], "warnings": [], "errors": []}
TRIANGULATE_NGONS = bool(PARAMS.get("triangulate_ngons", True))


def log(step):
    RESULT["steps"].append(step)


def warn(msg):
    RESULT["warnings"].append(msg)


def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    return [int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0]


def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def rgb_to_lab(rgb):
    # rgb в sRGB 0..1 -> CIE Lab (D65)
    r = srgb_to_linear(rgb[0])
    g = srgb_to_linear(rgb[1])
    b = srgb_to_linear(rgb[2])
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722)
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    out = []
    for t in (x, y, z):
        if t > 0.008856:
            out.append(t ** (1.0 / 3.0))
        else:
            out.append(7.787 * t + 16.0 / 116.0)
    return [116.0 * out[1] - 16.0, 500.0 * (out[0] - out[1]), 200.0 * (out[1] - out[2])]


def lab_dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def shade(rgb, k):
    # k < 0 — темнее, k > 0 — светлее (в sRGB)
    if k < 0:
        return [c * (1.0 + k) for c in rgb]
    return [c + (1.0 - c) * k for c in rgb]


def collect_targets(p):
    objs = []
    if p.get("objects"):
        for n in p["objects"]:
            o = bpy.data.objects.get(n)
            if o is None:
                RESULT["errors"].append("нет объекта: " + n)
            else:
                objs.append(o)
    elif p.get("collection"):
        col = bpy.data.collections.get(p["collection"])
        if col is None:
            RESULT["errors"].append("нет коллекции: " + p["collection"])
        else:
            objs = list(col.all_objects)
    elif p.get("selected"):
        objs = list(bpy.context.selected_objects)
    return [o for o in objs if o.type == "MESH"]


def tri_count(me):
    t = 0
    for poly in me.polygons:
        t += len(poly.vertices) - 2
    return t


def bake_modifiers_and_transform(obj):
    # Применить модификаторы через evaluated mesh, затем трансформ в данные меша.
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    new_me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    mw = obj.matrix_world.copy()
    new_me.transform(mw)
    if mw.determinant() < 0:
        new_me.flip_normals()
    old = obj.data
    obj.modifiers.clear()
    obj.data = new_me
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    if old.users == 0:
        bpy.data.meshes.remove(old)


def join_objects(objs, name):
    if len(objs) == 1:
        return objs[0]
    root = objs[0]
    others = objs[1:]
    with bpy.context.temp_override(active_object=root, object=root,
                                   selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    return root


def clean_mesh(obj, merge_dist):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    before_v = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_dist)
    loose = [v for v in bm.verts if not v.link_edges]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.dissolve_degenerate(bm, dist=merge_dist * 0.5, edges=bm.edges)
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons and TRIANGULATE_NGONS:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    removed = before_v - len(bm.verts)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return removed


def scale_and_pivot(obj, size, pivot, to_origin):
    me = obj.data
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    if not xs:
        return
    mn = Vector((min(xs), min(ys), min(zs)))
    mx = Vector((max(xs), max(ys), max(zs)))
    dims = mx - mn
    k = 1.0
    if size:
        if size.get("height"):
            if dims.z > 1e-6:
                k = size["height"] / dims.z
        elif size.get("longest"):
            longest = max(dims.x, dims.y, dims.z)
            if longest > 1e-6:
                k = size["longest"] / longest
    if pivot == "center":
        piv = (mn + mx) * 0.5
    elif pivot == "keep":
        piv = Vector((0.0, 0.0, 0.0))
    else:
        piv = Vector(((mn.x + mx.x) * 0.5, (mn.y + mx.y) * 0.5, mn.z))
    me.transform(Matrix.Translation(-piv))
    if abs(k - 1.0) > 1e-6:
        me.transform(Matrix.Scale(k, 4))
    me.update()
    if not to_origin:
        obj.location = piv
    log("масштаб x%.4f, пивот %s" % (k, pivot))


def decimate_to_budget(obj, budget):
    me = obj.data
    tris = tri_count(me)
    if budget is None or tris <= budget:
        return tris
    ratio = max(0.01, float(budget) / float(tris) * 0.98)
    mod = obj.modifiers.new("BK_Decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    new_me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data
    obj.modifiers.remove(mod)
    obj.data = new_me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    after = tri_count(new_me)
    log("decimate %d -> %d трис (бюджет %d)" % (tris, after, budget))
    if after > budget:
        warn("после decimate всё ещё %d > %d трис — нужна ретопология или другой источник" % (after, budget))
    return after


def set_shading(obj, mode):
    me = obj.data
    n = len(me.polygons)
    if mode == "flat":
        me.polygons.foreach_set("use_smooth", [False] * n)
    elif mode == "smooth":
        me.polygons.foreach_set("use_smooth", [True] * n)
    else:
        return
    me.update()
    log("шейдинг: " + mode)


# ---------- палитра ----------

def image_sampler(img, max_size):
    # Возвращает (w, h, pixels array) — уменьшенная копия, чтобы не тянуть 16M флоатов
    if img is None or img.size[0] == 0 or img.size[1] == 0:
        return None
    work = img
    copied = False
    if img.size[0] > max_size or img.size[1] > max_size:
        work = img.copy()
        copied = True
        k = float(max_size) / float(max(img.size[0], img.size[1]))
        work.scale(max(1, int(img.size[0] * k)), max(1, int(img.size[1] * k)))
    w = work.size[0]
    h = work.size[1]
    buf = array.array("f", [0.0]) * (w * h * work.channels)
    work.pixels.foreach_get(buf)
    ch = work.channels
    if copied:
        bpy.data.images.remove(work)
    return (w, h, ch, buf)


def sample(smp, u, v):
    w, h, ch, buf = smp
    x = int((u % 1.0) * (w - 1))
    y = int((v % 1.0) * (h - 1))
    i = (y * w + x) * ch
    # pixels уже в линейном пространстве для sRGB-картинок? Blender отдаёт значения
    # в пространстве буфера: для sRGB-изображений это sRGB 0..1
    return [buf[i], buf[i + 1], buf[i + 2]]


def material_color_source(mat, max_size, cache):
    # (тип, данные): ("image", sampler) | ("color", rgb_srgb)
    if mat is None:
        return ("color", [0.6, 0.6, 0.6])
    if mat.name in cache:
        return cache[mat.name]
    res = ("color", [linear_to_srgb(c) for c in mat.diffuse_color[:3]])
    if mat.use_nodes and mat.node_tree:
        bsdf = None
        for nd in mat.node_tree.nodes:
            if nd.type == "BSDF_PRINCIPLED":
                bsdf = nd
                break
        if bsdf is not None:
            inp = bsdf.inputs.get("Base Color")
            if inp is not None:
                if inp.is_linked:
                    src = inp.links[0].from_node
                    if src.type == "TEX_IMAGE" and src.image is not None:
                        smp = image_sampler(src.image, max_size)
                        if smp is not None:
                            res = ("image", smp)
                else:
                    dv = inp.default_value
                    res = ("color", [linear_to_srgb(dv[0]), linear_to_srgb(dv[1]), linear_to_srgb(dv[2])])
    cache[mat.name] = res
    return res


def face_colors(obj, max_size):
    me = obj.data
    uv = me.uv_layers.active
    cache = {}
    vcol = None
    if me.color_attributes.active_color is not None:
        vcol = me.color_attributes.active_color
    cols = []
    for poly in me.polygons:
        mat = None
        if poly.material_index < len(obj.material_slots):
            mat = obj.material_slots[poly.material_index].material
        kind, data = material_color_source(mat, max_size, cache)
        if kind == "image" and uv is not None:
            acc = [0.0, 0.0, 0.0]
            n = 0
            cu = 0.0
            cv = 0.0
            for li in poly.loop_indices:
                c = uv.data[li].uv
                cu += c.x
                cv += c.y
                s = sample(data, c.x, c.y)
                acc[0] += s[0]
                acc[1] += s[1]
                acc[2] += s[2]
                n += 1
            cu /= n
            cv /= n
            s = sample(data, cu, cv)
            # центр весит как все углы вместе
            col = [(acc[0] + s[0] * n) / (2 * n), (acc[1] + s[1] * n) / (2 * n), (acc[2] + s[2] * n) / (2 * n)]
        elif vcol is not None and mat is None:
            acc = [0.0, 0.0, 0.0]
            n = 0
            for li in poly.loop_indices:
                if vcol.domain == "CORNER":
                    c = vcol.data[li].color_srgb
                else:
                    c = vcol.data[me.loops[li].vertex_index].color_srgb
                acc[0] += c[0]
                acc[1] += c[1]
                acc[2] += c[2]
                n += 1
            col = [acc[0] / n, acc[1] / n, acc[2] / n]
        else:
            col = data if kind == "color" else [0.6, 0.6, 0.6]
        cols.append(col)
    return cols


def build_palette(profile):
    pal = profile.get("palette", {})
    shades = profile.get("palette_shades", [-0.35, 0.0, 0.25])
    entries = []
    for role in sorted(pal.keys()):
        base = hex_to_rgb(pal[role])
        for k in shades:
            rgb = shade(base, k)
            entries.append({"role": role, "shade": k, "rgb": rgb, "lab": rgb_to_lab(rgb)})
    return entries


def palette_image(entries, name, cell):
    cols = len(entries)
    w = max(1, cols) * cell
    h = cell
    img = bpy.data.images.get(name)
    if img is not None and (img.size[0] != w or img.size[1] != h):
        bpy.data.images.remove(img)
        img = None
    if img is None:
        img = bpy.data.images.new(name, width=w, height=h, alpha=False)
    buf = array.array("f", [0.0]) * (w * h * 4)
    for y in range(h):
        for x in range(w):
            e = entries[x // cell]
            i = (y * w + x) * 4
            # images.new создаёт sRGB-буфер: пишем sRGB значения
            buf[i] = e["rgb"][0]
            buf[i + 1] = e["rgb"][1]
            buf[i + 2] = e["rgb"][2]
            buf[i + 3] = 1.0
    img.pixels.foreach_set(buf)
    img.update()
    img.pack()
    return img


def palette_material(img, profile):
    name = "M_" + profile.get("palette_material", "palette")
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    bsdf.inputs["Roughness"].default_value = float(profile.get("roughness", 0.8))
    bsdf.inputs["Metallic"].default_value = 0.0
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    out.location = (300, 0)
    tex.location = (-400, 0)
    return mat


def recolor_to_palette(obj, profile):
    entries = build_palette(profile)
    if not entries:
        warn("в профиле нет palette — перекраска пропущена")
        return
    cols = face_colors(obj, int(profile.get("sample_max_px", 256)))
    cell = int(profile.get("palette_cell_px", 4))
    img = palette_image(entries, "T_palette", cell)
    mat = palette_material(img, profile)
    me = obj.data
    picks = []
    err_sum = 0.0
    usage = {}
    for c in cols:
        lab = rgb_to_lab(c)
        best = 0
        bd = 1e9
        for i, e in enumerate(entries):
            d = lab_dist(lab, e["lab"])
            if d < bd:
                bd = d
                best = i
        picks.append(best)
        err_sum += bd
        key = entries[best]["role"]
        usage[key] = usage.get(key, 0) + 1
    uvl = me.uv_layers.new(name="UVPalette")
    n = len(entries)
    for pi, poly in enumerate(me.polygons):
        u = (picks[pi] + 0.5) / n
        for li in poly.loop_indices:
            uvl.data[li].uv = (u, 0.5)
    keep = profile.get("keep_original_uv", False)
    if not keep:
        names = [l.name for l in me.uv_layers if l.name != "UVPalette"]
        for nm in names:
            me.uv_layers.remove(me.uv_layers[nm])
    me.uv_layers.active = me.uv_layers["UVPalette"]
    me.uv_layers["UVPalette"].active_render = True
    me.materials.clear()
    me.materials.append(mat)
    for poly in me.polygons:
        poly.material_index = 0
    me.update()
    avg = err_sum / max(1, len(cols))
    RESULT["palette"] = {"colors": n, "usage": usage, "avg_lab_error": round(avg, 2)}
    log("перекраска в палитру: %d граней, средняя ошибка ΔE=%.1f" % (len(cols), avg))
    if avg > float(profile.get("palette_warn_delta_e", 25.0)):
        warn("средняя ΔE %.1f — исходник сильно вне палитры, проверь превью" % avg)


def snake(s):
    out = []
    prev_us = False
    for ch in s.strip():
        if ch.isalnum():
            out.append(ch.lower())
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    return "".join(out).strip("_") or "asset"


def run(p):
    profile = p.get("profile", {})
    objs = collect_targets(p)
    if not objs:
        RESULT["ok"] = False
        RESULT["errors"].append("нет мешей для нормализации")
        return RESULT
    for o in objs:
        bake_modifiers_and_transform(o)
    log("применены модификаторы и трансформы: %d объект(ов)" % len(objs))
    obj = objs[0]
    if p.get("join", True) and len(objs) > 1:
        obj = join_objects(objs, p.get("name"))
        log("объединено в один меш")
    removed = clean_mesh(obj, float(profile.get("merge_distance", 0.0001)))
    log("чистка: удалено %d вершин (дубли/висячие), нормали пересчитаны" % removed)
    scale_and_pivot(obj, p.get("size"), profile.get("pivot", "bottom_center"), p.get("to_origin", True))
    budgets = profile.get("budgets", {})
    cat = p.get("category", profile.get("default_category", "prop"))
    budget = budgets.get(cat)
    if budget is None:
        warn("нет бюджета для категории '%s' в профиле" % cat)
    tris = decimate_to_budget(obj, budget)
    if p.get("recolor", profile.get("recolor", "palette")) == "palette":
        recolor_to_palette(obj, profile)
    set_shading(obj, profile.get("shading", "keep"))
    prefix = profile.get("naming", {}).get("prefix", "")
    nm = prefix + snake(p.get("name", obj.name))
    obj.name = nm
    obj.data.name = nm
    d = obj.dimensions
    RESULT["asset"] = {"object": obj.name, "tris": tri_count(obj.data), "budget": budget,
                       "dims_m": [round(d.x, 3), round(d.y, 3), round(d.z, 3)]}
    RESULT["ok"] = not RESULT["errors"]
    return RESULT


print("\nBK_RESULT " + json.dumps(run(PARAMS), ensure_ascii=False))
