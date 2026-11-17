# blender-kit: bk_export.py — экспорт ассета под движок с подготовкой
# LOD и коллизий по соглашениям движка. Работает на временных копиях:
# исходная сцена после экспорта остаётся как была.
#
# Запуск: первой строкой PARAMS = {...}, затем этот файл, через execute_blender_code.
# Совместим с BLENDER_MCP_SAFE_MODE=1 (экспорт через bpy-операторы разрешён).
#
# PARAMS:
#   objects / collection / selected — что экспортировать
#   engine:    "godot" | "unity" | "roblox" | "gltf" | "fbx"
#   out_dir:   абсолютный путь к папке вывода (например <проект>/assets/models)
#   name:      имя файла без расширения (по умолчанию — имя первого объекта)
#   profile:   {...}  — docs/art/asset_profile.json (секция engines.<engine> переопределяет умолчания)
#   lods:      [0.5, 0.25] — доли трисов для LOD1.. (по умолчанию из профиля движка)
#   collision: "hull" | "box" | "none"

import bpy
import bmesh
import json
from mathutils import Vector, Matrix

DEFAULTS = {
    # Godot 4: glTF/GLB — основной формат; LOD генерирует сам импортёр;
    # коллизии — суффиксы имён узлов (-convcolonly, -colonly).
    "godot": {"format": "GLB", "lods": [], "collision": "hull",
              "col_suffix_hull": "-convcolonly", "col_suffix_box": "-colonly"},
    # Unity: FBX, -Z вперёд / Y вверх, FBX Units Scale; меши *_LOD0.._LODn
    # Unity собирает в LODGroup при импорте. Коллайдер — отдельный меш *_collider,
    # MeshCollider вешается в Unity.
    "unity": {"format": "FBX", "lods": [0.5, 0.25], "collision": "none",
              "col_suffix_hull": "_collider", "col_suffix_box": "_collider"},
    # Roblox: GLB в метрах (в 3D Importer выставить Scale Unit = Meter),
    # LOD Roblox делает сам, коллизии — CollisionFidelity в Studio.
    "roblox": {"format": "GLB", "lods": [], "collision": "none",
               "col_suffix_hull": "", "col_suffix_box": ""},
    "gltf": {"format": "GLB", "lods": [], "collision": "none", "col_suffix_hull": "", "col_suffix_box": ""},
    "fbx": {"format": "FBX", "lods": [], "collision": "none", "col_suffix_hull": "", "col_suffix_box": ""},
}

RESULT = {"ok": True, "files": [], "steps": [], "warnings": [], "errors": []}
MAX_HULL_FACES = int(PARAMS.get("max_hull_faces", 64))


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
        if col is not None:
            objs = list(col.all_objects)
    elif p.get("selected"):
        objs = list(bpy.context.selected_objects)
    return [o for o in objs if o.type in ("MESH", "ARMATURE", "EMPTY")]


def tri_count(me):
    t = 0
    for poly in me.polygons:
        t += len(poly.vertices) - 2
    return t


def make_copy(obj, name, col):
    cp = obj.copy()
    if obj.data is not None:
        cp.data = obj.data.copy()
    cp.name = name
    if cp.data is not None:
        cp.data.name = name
    col.objects.link(cp)
    return cp


def decimated_copy(obj, name, ratio, col):
    cp = make_copy(obj, name, col)
    mod = cp.modifiers.new("BK_LOD", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    ev = cp.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = cp.data
    cp.modifiers.remove(mod)
    cp.data = me
    me.name = name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return cp


def collision_copy(obj, name, kind, col):
    me_src = obj.data
    bm = bmesh.new()
    if kind == "box":
        xs = [v.co.x for v in me_src.vertices]
        ys = [v.co.y for v in me_src.vertices]
        zs = [v.co.z for v in me_src.vertices]
        mn = Vector((min(xs), min(ys), min(zs)))
        mx = Vector((max(xs), max(ys), max(zs)))
        bmesh.ops.create_cube(bm, size=1.0)
        size = mx - mn
        cen = (mn + mx) * 0.5
        for v in bm.verts:
            v.co = Vector((v.co.x * size.x + cen.x, v.co.y * size.y + cen.y, v.co.z * size.z + cen.z))
    else:
        # Вершины прореживаются по сетке (1/8 габарита), чтобы оболочка была лёгкой.
        xs = [v.co.x for v in me_src.vertices]
        ys = [v.co.y for v in me_src.vertices]
        zs = [v.co.z for v in me_src.vertices]
        g = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) / 8.0
        seen = {}
        for v in me_src.vertices:
            key = (round(v.co.x / g), round(v.co.y / g), round(v.co.z / g))
            if key not in seen:
                seen[key] = v.co.copy()
        if len(seen) < 4:
            for v in me_src.vertices:
                seen[(v.index,)] = v.co.copy()
        for co in seen.values():
            bm.verts.new(co)
        res = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
        keep = set(res["geom"])
        drop = [e for e in bm.verts if e not in keep]
        if drop:
            bmesh.ops.delete(bm, geom=drop, context="VERTS")
        # Упростить оболочку: для физики хватает десятков граней.
        for ang in (0.17, 0.35, 0.52, 0.7):
            if len(bm.faces) <= MAX_HULL_FACES:
                break
            bmesh.ops.dissolve_limit(bm, angle_limit=ang, verts=bm.verts, edges=bm.edges)
        bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    cp = bpy.data.objects.new(name, me)
    cp.matrix_world = obj.matrix_world.copy()
    col.objects.link(cp)
    return cp


def select_only(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def export_glb(path, objs):
    select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_animations=True,
    )


def export_fbx(path, objs):
    select_only(objs)
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
        use_space_transform=True,
        bake_space_transform=False,
        object_types={"MESH", "ARMATURE", "EMPTY"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
        path_mode="COPY",
        embed_textures=True,
        bake_anim=True,
    )


def run(p):
    engine = p.get("engine", "gltf")
    if engine not in DEFAULTS:
        RESULT["ok"] = False
        RESULT["errors"].append("неизвестный engine: %s" % engine)
        return RESULT
    cfg = dict(DEFAULTS[engine])
    prof = p.get("profile", {}).get("engines", {}).get(engine, {})
    for k in prof:
        cfg[k] = prof[k]
    lods = p.get("lods", cfg.get("lods", []))
    coll = p.get("collision", cfg.get("collision", "none"))
    out_dir = p.get("out_dir")
    if not out_dir:
        RESULT["ok"] = False
        RESULT["errors"].append("не задан out_dir (абсолютный путь)")
        return RESULT
    out_dir = bpy.path.abspath(out_dir).rstrip("/\\")
    objs = collect_targets(p)
    if not objs:
        RESULT["ok"] = False
        RESULT["errors"].append("нечего экспортировать")
        return RESULT
    base = p.get("name", objs[0].name)

    tmp = bpy.data.collections.new("BK_ExportTmp")
    bpy.context.scene.collection.children.link(tmp)
    to_export = []
    try:
        for o in objs:
            if o.type != "MESH":
                to_export.append(o)
                continue
            if lods:
                lod0 = make_copy(o, o.name + "_LOD0", tmp)
                to_export.append(lod0)
                n_before = len(to_export)
                prev = tri_count(lod0.data)
                for i, r in enumerate(lods):
                    c = decimated_copy(o, "%s_LOD%d" % (o.name, i + 1), float(r), tmp)
                    t = tri_count(c.data)
                    d0 = o.dimensions
                    d1 = c.dimensions
                    drift = max(abs(d1.x - d0.x) / max(d0.x, 1e-6), abs(d1.y - d0.y) / max(d0.y, 1e-6),
                                abs(d1.z - d0.z) / max(d0.z, 1e-6))
                    if drift > 0.05:
                        RESULT["warnings"].append("LOD%d пропущен: упрощение исказило габариты на %d%% (меш из отдельных деталей)" % (i + 1, int(drift * 100)))
                        me_tmp = c.data
                        bpy.data.objects.remove(c, do_unlink=True)
                        bpy.data.meshes.remove(me_tmp)
                        break
                    if t > prev * 0.85:
                        # Меш уже минимальный (low-poly из отдельных деталей) — уровень бессмыслен.
                        RESULT["warnings"].append("LOD%d пропущен: %d трис почти как у предыдущего (%d)" % (i + 1, t, prev))
                        me_tmp = c.data
                        bpy.data.objects.remove(c, do_unlink=True)
                        bpy.data.meshes.remove(me_tmp)
                        break
                    to_export.append(c)
                    prev = t
                    RESULT["steps"].append("LOD%d: %d трис" % (i + 1, t))
                if len(to_export) == n_before:
                    # Ни одного полезного LOD — экспортируем без суффикса _LOD0.
                    lod0.name = o.name + "_BKTMP"
                    to_export.remove(lod0)
                    to_export.append(o)
            else:
                to_export.append(o)
            if coll in ("hull", "box"):
                suffix = cfg["col_suffix_hull"] if coll == "hull" else cfg["col_suffix_box"]
                if not suffix:
                    RESULT["warnings"].append("для %s коллизия настраивается в движке — меш коллизии не создан" % engine)
                else:
                    c = collision_copy(o, o.name + suffix, coll, tmp)
                    to_export.append(c)
                    RESULT["steps"].append("коллизия %s: %s (%d граней)" % (coll, c.name, len(c.data.polygons)))
        for o in to_export:
            if o.type == "MESH":
                t = tri_count(o.data)
                if engine == "roblox" and t > 20000:
                    RESULT["errors"].append("%s: %d трис > 20000 — Roblox упростит меш сам" % (o.name, t))
        ext = ".glb" if cfg["format"] == "GLB" else ".fbx"
        path = out_dir + "/" + base + ext
        try:
            if cfg["format"] == "GLB":
                export_glb(path, to_export)
            else:
                export_fbx(path, to_export)
        except RuntimeError as e:
            msg = str(e)
            if "No such file or directory" in msg:
                msg = "папка %s не существует — создай её (FBX-экспортёр не создаёт папки)" % out_dir
            RESULT["errors"].append("экспорт не удался: " + msg[-300:])
            RESULT["ok"] = False
            return RESULT
        RESULT["files"].append(path)
        RESULT["steps"].append("экспорт %s: %s (%d объект(ов))" % (cfg["format"], path, len(to_export)))
    finally:
        for o in list(tmp.objects):
            data = o.data
            is_mesh = o.type == "MESH"
            bpy.data.objects.remove(o, do_unlink=True)
            if is_mesh and data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
        bpy.data.collections.remove(tmp)
    notes = {
        "godot": "Godot: положи .glb в проект; LOD создаст импортёр; узлы с -convcolonly станут StaticBody3D с выпуклой коллизией.",
        "unity": "Unity: Model → Scale Factor 1, Convert Units вкл, Bake Axis Conversion вкл; *_LOD0..n соберутся в LODGroup.",
        "roblox": "Roblox: 3D Importer → Scale Unit = Meter; проверь размер рядом со стандартным Part; CollisionFidelity — Box/Hull.",
    }
    if engine in notes:
        RESULT["import_notes"] = notes[engine]
    RESULT["ok"] = not RESULT["errors"]
    return RESULT


print("\nBK_RESULT " + json.dumps(run(PARAMS), ensure_ascii=False))
