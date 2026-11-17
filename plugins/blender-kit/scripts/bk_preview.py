# blender-kit: bk_preview.py — «линейка стиля»: новые ассеты рядом с эталонными
# при одинаковом свете и камере. Картинку смотрит агент (Read) или арт-директор —
# сразу видно, кто выбивается по цвету, масштабу и детализации.
#
# Запуск: первой строкой PARAMS = {...}, затем этот файл, через execute_blender_code.
# Совместим с BLENDER_MCP_SAFE_MODE=1. Сцена после рендера возвращается как была
# (временные камера и свет удаляются, исходные позиции объектов восстанавливаются).
#
# PARAMS:
#   objects:    ["новые", ...]        — что показать
#   references: ["эталонные", ...]    — с чем сравнить (могут быть пустыми)
#   out_path:   абсолютный путь .png
#   engine:     "WORKBENCH" (быстро, по умолчанию) | "EEVEE" | "CYCLES"
#   resolution: [1600, 800]
#   gap:        расстояние между объектами, м (по умолчанию 0.4)

import bpy
import json
import math
from mathutils import Vector


def get_objs(names):
    out = []
    for n in names or []:
        o = bpy.data.objects.get(n)
        if o is not None:
            out.append(o)
    return out


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def set_engine(scene, name):
    if name == "EEVEE":
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except TypeError:
            scene.render.engine = "BLENDER_EEVEE"
    elif name == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 32
        scene.cycles.device = "CPU"
    else:
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "TEXTURE"
        scene.display.shading.show_cavity = False


def run(p):
    scene = bpy.context.scene
    refs = get_objs(p.get("references"))
    news = get_objs(p.get("objects"))
    lineup = refs + news
    if not lineup:
        return {"ok": False, "errors": ["нет объектов"]}
    gap = float(p.get("gap", 0.4))
    bpy.context.view_layer.update()
    saved = {}
    for o in lineup:
        saved[o.name] = o.location.copy()
    hidden = []
    for o in scene.objects:
        if o not in lineup and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    x = 0.0
    top = 0.0
    for o in lineup:
        mn, mx = world_bbox(o)
        w = mx.x - mn.x
        o.location.x += x - mn.x
        o.location.y += -(mn.y + mx.y) / 2
        o.location.z += -mn.z
        x += w + gap
        top = max(top, mx.z - mn.z)
    total_w = x - gap
    cam_data = bpy.data.cameras.new("BK_PreviewCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(total_w, top * 2.2) * 1.12
    cam = bpy.data.objects.new("BK_PreviewCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (total_w / 2, -max(total_w, top) * 3.0, top * 0.55 + max(total_w, top) * 0.9)
    target = Vector((total_w / 2, 0.0, top * 0.45))
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sun_data = bpy.data.lights.new("BK_PreviewSun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("BK_PreviewSun", sun_data)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(30))
    scene.collection.objects.link(sun)
    tmp_world = None
    if scene.world is None:
        tmp_world = bpy.data.worlds.new("BK_PreviewWorld")
        tmp_world.color = (0.8, 0.8, 0.8)
        scene.world = tmp_world
    old_cam = scene.camera
    old_engine = scene.render.engine
    old_res = (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    old_path = scene.render.filepath
    res = p.get("resolution", [1600, 800])
    try:
        scene.camera = cam
        set_engine(scene, p.get("engine", "WORKBENCH"))
        scene.render.resolution_x = int(res[0])
        scene.render.resolution_y = int(res[1])
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = p["out_path"]
        bpy.ops.render.render(write_still=True)
    finally:
        scene.camera = old_cam
        scene.render.engine = old_engine
        scene.render.resolution_x = old_res[0]
        scene.render.resolution_y = old_res[1]
        scene.render.resolution_percentage = old_res[2]
        scene.render.filepath = old_path
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
        bpy.data.objects.remove(sun, do_unlink=True)
        bpy.data.lights.remove(sun_data)
        for o in lineup:
            o.location = saved[o.name]
        for o in hidden:
            o.hide_render = False
        if tmp_world is not None:
            scene.world = None
            bpy.data.worlds.remove(tmp_world)
        bpy.context.view_layer.update()
    return {"ok": True, "image": p["out_path"], "order": [o.name for o in lineup],
            "references": len(refs)}


print("\nBK_RESULT " + json.dumps(run(PARAMS), ensure_ascii=False))
