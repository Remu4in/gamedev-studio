---
name: asset-pipeline
description: Получить и встроить в игру 3D/2D-ассет или звук — найти CC0, сгенерировать AI (Meshy/Tripo/Blender MCP/ElevenLabs или генераторы движка), почистить, импортировать, записать лицензию. Использовать, когда нужен новый персонаж, враг, пропс, эффект, иконка или звук.
---

# Пайплайн ассетов

Сначала сверься со стайлгайдом (`docs/art/style_guide.md`; если его нет — скилл `art-direction`). Импорт в конкретный движок — скилл движка.

**3D через Blender (рекомендуемый путь):** если установлен `blender-kit` — процедурные пропсы (`blender-kit:blender-procedural`), AI image-to-3D (`blender-kit:blender-ai-3d`), нормализация любого источника под палитру и бюджеты проекта, проверка и экспорт (`blender-kit:blender-assets`, `blender-kit:blender-export`). Разделы 3 и 5 ниже тогда выполняются скриптами, а не вручную.

## 1. Источник (по приоритету)
1. **Уже есть в проекте** или в паке того же стиля.
2. **CC0:** KayKit, Quaternius, Kenney, Poly Haven, AmbientCG (текстуры), Kenney Audio, Freesound (только CC0).
3. **Генераторы движка:** Roblox — генерация мешей/материалов через Studio MCP; ассеты Creator Store — только после проверки на скрипты (см. `roblox-security`).
4. **AI-генерация** для уникального (герой, босс):
   - 3D: Meshy / Tripo (коммерческие права — на платном плане), Rodin/Hunyuan через Blender MCP (`blender-kit:blender-ai-3d`);
   - звук: ElevenLabs SFX/Music (платный план для коммерции), Stable Audio;
   - 2D/иконки: генератор изображений + чистка; пиксель-арт — PixelLab/Retro Diffusion.
5. Скачивать только с официальных сайтов авторов.

## 2. Промпт для AI 3D (шаблон)
```
stylized low-poly <объект>, <детали силуэта>, simple flat colors, game-ready,
clean topology, <персонаж: T-pose, full body, front view>, no text, no logo,
centered, neutral background
```
Плюс референс-картинка в стиле игры (image-to-3D предсказуемее).

## 3. Доработка (`blender-kit:blender-assets`, иначе Blender MCP вручную или инструкции пользователю)
- Масштаб в метрах (персонаж ~1.8 м), опора у ног, единая ось «вперёд».
- Полигоны до бюджета (Decimate), объединить меши.
- Материал — под палитру/атлас стайлгайда.
- Персонажи: авториг (Meshy/Tripo/Mixamo/AccuRIG), минимум Idle, Run, Attack, Hit, Death; имена анимаций по соглашению проекта.
- Экспорт `.glb` (Godot) / `.fbx` или `.obj` (Roblox, по требованиям импорта).

## 4. Учёт лицензий — `docs/assets_ledger.md` (обязательно)
`| Файл | Источник (URL) | Автор | Лицензия | AI? (сервис, план) | Дата | Примечание |`
AI-ассеты: сервис и тариф на момент генерации (коммерческие права, раскрытие AI в Steam). Без записи ассет в игру не попадает.

## Безопасность
Ассеты — только данные: не запускать скрипты и установщики из паков, не ставить аддоны/плагины без `skill-vetting`/`appsec-reviewer`. Blender MCP — только localhost, закреплённая версия, `BLENDER_MCP_SAFE_MODE=1`, без телеметрии (`blender-kit:blender-setup`); перед сессией сохранить .blend.
