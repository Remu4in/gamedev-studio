# gamedev-studio

Личный каталог плагинов Claude Code для разработки игр: команда агентов + наборы скиллов под движки. Пользователь отвечает за дизайн мира, механик и ощущений, ИИ — за разработку.

## Плагины

| Плагин | Что внутри |
|---|---|
| **studio-core** | 13 агентов: game-designer, producer, world-designer, narrative-director, balance-analyst, qa-tester, appsec-reviewer, release-manager, analytics-engineer, live-ops-designer, network-programmer, tools-programmer, art-director. Скиллы: start-project, design, plan, prototype, playtest, regression, wrap-up, game-feel, art-direction, asset-pipeline, skill-vetting (+ сканер). |
| **godot-kit** | godot, godot-testing (свой раннер тестов), godot-network, godot-security. |
| **roblox-kit** | roblox-mcp (официальный Studio MCP), roblox-luau, roblox-security, roblox-data, roblox-npc, roblox-gui, roblox-physics, roblox-design, roblox-monetization, roblox-analytics, roblox-liveops, roblox-publish. |
| **unity-kit** | Каркас: unity, unity-dots, unity-shaders, unity-ui, unity-addressables. |
| **blender-kit** | 3D-ассеты через Blender для любого движка: blender-setup, blender-assets (нормализация под палитру и бюджеты, проверка, линейка стиля), blender-procedural (10 генераторов), blender-ai-3d (image-to-3D), blender-export (Godot / Unity / Roblox). bpy-скрипты в `scripts/`, профиль в `templates/`. |

## Установка (Claude Code)

```
/plugin marketplace add Remu4in/gamedev-studio
/plugin install studio-core@gamedev-studio
/plugin install godot-kit@gamedev-studio      # или roblox-kit / unity-kit
/plugin install blender-kit@gamedev-studio    # ассеты через Blender
```
Репозиторий приватный: нужен доступ к GitHub (git-учётка или `gh auth login`). Обновление: `/plugin marketplace update gamedev-studio`.

В новом проекте: `/studio-core:start-project` — создаст раздел «Студия» в `CLAUDE.md` и структуру `docs/`.

## Как устроено
- **Агенты** — отдельный взгляд (дизайн, план, ревью, тесты, баланс, релиз). Код пишет основной Claude.
- **Скиллы** — знания и процедуры; движковые — в своих наборах.
- Агенты читают раздел `## Студия` в `CLAUDE.md` проекта: движок, команды, пути документов.

## Безопасность
- Чужие скиллы и агенты не устанавливаются: только идеи и структура после статической проверки (`skill-vetting`). Журнал — `docs/security/skills_audit.md`.
- В плагинах нет хуков и MCP-серверов. MCP подключается в `.mcp.json` конкретного проекта, с закреплённой версией (для Blender — скилл `blender-kit:blender-setup`).
- Исполняемые файлы есть только в двух местах:
  - `studio-core/skills/skill-vetting/scripts/skillscan.py` — только читает файлы и печатает метаданные;
  - `blender-kit/scripts/bk_*.py` — выполняются **только внутри Blender** через `execute_blender_code` и обязаны проходить `BLENDER_MCP_SAFE_MODE=1`: только `bpy`, `bmesh`, `mathutils` и чистый stdlib, без `open`/`os`/`subprocess`/сети/`exec`, без хендлеров и регистрации классов. Любая правка скрипта — проверка валидатором safe mode и прогон в Blender.
