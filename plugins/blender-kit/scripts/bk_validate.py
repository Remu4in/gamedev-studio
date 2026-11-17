# blender-kit: bk_validate.py — проверяет ассет перед экспортом и печатает вердикт
# PASS / WARN / FAIL с конкретными причинами. Ничего не меняет в сцене.
#
# Запуск: первой строкой PARAMS = {...}, затем этот файл, через execute_blender_code.
# Совместим с BLENDER_MCP_SAFE_MODE=1.
#
# PARAMS:
#   objects / collection / selected — что проверять (как в bk_normalize)
#   category: "prop"     — ключ бюджета из profile.budgets
#   engine:   "godot" | "unity" | "roblox" | null — добавить проверки движка
#   profile:  {...}      — docs/art/asset_profile.json
#   size:     {"height": [0.4, 0.6]} — необязательный ожидаемый диапазон габаритов, м

import bpy
import bmesh
import json
import math

ENGINE_LIMITS = {
    # Жёсткие лимиты платформ. Roblox: 20k треугольников на меш (импортёр
    # иначе автоматически упрощает). Остальные — без жёсткого лимита.
    "roblox": {"max_tris_per_mesh": 20000, "max_bone_influences": 4},
    "godot": {},
    "unity": {},
}


def collect_targets(p):
    objs = []
    if p.get("objects"):
        for n in p["objects"]:
            o = bpy.data.objects.get(n)
            if o is not None:
                objs.append(o)
    elif p.get("collection"):
        col = bpy.data.collections.get(p["collection"])
        if col is not None:
            objs = list(col.all_objects)
    elif p.get("selected"):
        objs = list(bpy.context.selected_objects)
    return [o for o in objs if o.type == "MESH"]


def check_object(obj, p, profile):
    issues = []

    def add(level, code, msg):
        issues.append({"level": level, "code": code, "msg": msg})

    me = obj.data
    tris = 0
    ngons = 0
    for poly in me.polygons:
        k = len(poly.vertices)
        tris += k - 2
        if k > 4:
            ngons += 1

    budgets = profile.get("budgets", {})
    cat = p.get("category", profile.get("default_category", "prop"))
    budget = budgets.get(cat)
    if budget is not None and tris > budget:
        level = "FAIL" if tris > budget * 1.25 else "WARN"
        add(level, "tris_budget", "%d трис при бюджете %d (%s)" % (tris, budget, cat))
    eng = p.get("engine")
    lim = ENGINE_LIMITS.get(eng or "", {})
    if lim.get("max_tris_per_mesh") and tris > lim["max_tris_per_mesh"]:
        add("FAIL", "engine_tris", "%d трис > лимита %s %d на меш" % (tris, eng, lim["max_tris_per_mesh"]))
    if ngons:
        add("WARN", "ngons", "%d n-gon (>4 вершин): экспорт триангулирует по-своему" % ngons)

    # трансформы
    loc = obj.location
    rot = obj.rotation_euler
    sc = obj.scale
    if any(abs(s - 1.0) > 1e-4 for s in sc):
        add("FAIL", "scale_not_applied", "масштаб объекта %s не применён" % [round(s, 4) for s in sc])
    if any(abs(r) > 1e-4 for r in rot):
        add("WARN", "rotation_not_applied", "поворот объекта не применён")
    if obj.parent is not None:
        add("WARN", "has_parent", "у объекта есть родитель: " + obj.parent.name)

    # топология
    bm = bmesh.new()
    bm.from_mesh(me)
    nonman = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    loose_v = sum(1 for v in bm.verts if not v.link_edges)
    zero_faces = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
    bm.free()
    if nonman:
        # Пересекающиеся детали (кит-баш, процедурные пропсы) дают такие рёбра — для игр
        # это нормально; критично только для замкнутых мешей (Roblox-аксессуары, 3D-печать).
        lvl = "WARN" if profile.get("require_watertight", False) else "INFO"
        add(lvl, "non_manifold", "%d неманифолдных рёбер (пересекающиеся детали)" % nonman)
    if boundary and profile.get("require_watertight", False):
        add("WARN", "open_mesh", "%d открытых рёбер (меш не замкнут)" % boundary)
    if loose_v:
        add("WARN", "loose_verts", "%d висячих вершин" % loose_v)
    if zero_faces:
        add("WARN", "zero_area", "%d вырожденных граней" % zero_faces)

    # габариты и пивот
    xs = [v.co.x for v in me.vertices] or [0.0]
    ys = [v.co.y for v in me.vertices] or [0.0]
    zs = [v.co.z for v in me.vertices] or [0.0]
    dims = [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]
    pivot = profile.get("pivot", "bottom_center")
    tol = max(dims) * 0.02 + 1e-4
    if pivot == "bottom_center":
        if abs(min(zs)) > tol or abs((max(xs) + min(xs)) * 0.5) > tol or abs((max(ys) + min(ys)) * 0.5) > tol:
            add("WARN", "pivot", "пивот не в центре низа (ожидается %s)" % pivot)
    if max(dims) < 0.01:
        add("FAIL", "tiny", "габарит < 1 см — похоже на ошибку единиц")
    if max(dims) > float(profile.get("max_size_m", 200.0)):
        add("FAIL", "huge", "габарит %.1f м — похоже на ошибку единиц" % max(dims))
    exp = p.get("size") or {}
    if exp.get("height"):
        lo, hi = exp["height"]
        if not (lo <= dims[2] <= hi):
            add("WARN", "height_range", "высота %.3f м вне ожидаемого [%s, %s]" % (dims[2], lo, hi))

    # UV и материалы
    if not me.uv_layers:
        add("FAIL", "no_uv", "нет UV — текстуры и палитра не лягут")
    mats = [s.material for s in obj.material_slots]
    if not mats or any(m is None for m in mats):
        add("WARN", "empty_material_slot", "нет материала или пустой слот")
    max_mats = int(profile.get("max_materials", 2))
    if len(mats) > max_mats:
        add("WARN", "too_many_materials", "%d материалов > %d (лишние draw calls)" % (len(mats), max_mats))
    for m in mats:
        if m is None or not m.use_nodes or m.node_tree is None:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == "TEX_IMAGE":
                img = nd.image
                if img is None:
                    add("FAIL", "missing_image", "в материале %s пустая текстура" % m.name)
                elif img.packed_file is None and not img.filepath:
                    add("WARN", "image_unsaved", "текстура %s не упакована и не сохранена" % img.name)
                elif img.size[0] == 0:
                    add("FAIL", "missing_image", "текстура %s не найдена на диске" % img.name)
                else:
                    mx = int(profile.get("max_texture_px", 2048))
                    if max(img.size[0], img.size[1]) > mx:
                        add("WARN", "texture_size", "текстура %s %dx%d > %d" % (img.name, img.size[0], img.size[1], mx))
            elif nd.type in ("TEX_NOISE", "TEX_VORONOI", "TEX_WAVE", "TEX_MUSGRAVE", "TEX_MAGIC",
                             "TEX_GRADIENT", "TEX_BRICK", "TEX_CHECKER", "SCRIPT"):
                add("WARN", "procedural_shader", "узел %s в %s не экспортируется — запеки в текстуру" % (nd.type, m.name))

    # имя
    prefix = profile.get("naming", {}).get("prefix", "")
    nm = obj.name
    if prefix and not nm.startswith(prefix):
        add("WARN", "naming", "имя %s без префикса %s" % (nm, prefix))
    body = nm[len(prefix):] if nm.startswith(prefix) else nm
    if body != body.lower() or " " in body or "." in body:
        add("WARN", "naming", "имя %s не snake_case (точки от дубликатов тоже)" % nm)

    # риг
    arm_mod = [m for m in obj.modifiers if m.type == "ARMATURE"]
    if arm_mod and lim.get("max_bone_influences"):
        over = 0
        for v in me.vertices:
            if sum(1 for g in v.groups if g.weight > 1e-4) > lim["max_bone_influences"]:
                over += 1
        if over:
            add("FAIL", "bone_influences", "%d вершин с > %d костями" % (over, lim["max_bone_influences"]))

    verdict = "PASS"
    if any(i["level"] == "FAIL" for i in issues):
        verdict = "FAIL"
    elif any(i["level"] == "WARN" for i in issues):
        verdict = "WARN"
    return {"object": obj.name, "verdict": verdict, "tris": tris, "budget": budget,
            "dims_m": [round(d, 3) for d in dims], "materials": len(mats), "issues": issues}


def run(p):
    profile = p.get("profile", {})
    objs = collect_targets(p)
    if not objs:
        return {"verdict": "FAIL", "objects": [], "errors": ["нет мешей для проверки"]}
    reps = [check_object(o, p, profile) for o in objs]
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    worst = "PASS"
    for r in reps:
        if order[r["verdict"]] > order[worst]:
            worst = r["verdict"]
    return {"verdict": worst, "engine": p.get("engine"), "objects": reps}


print("\nBK_RESULT " + json.dumps(run(PARAMS), ensure_ascii=False))
