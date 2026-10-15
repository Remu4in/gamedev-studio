---
name: unity
description: Практики Unity (C#) — структура проекта, MonoBehaviour и ScriptableObject, сцены и префабы, жизненный цикл, производительность, тесты (Unity Test Framework), MCP для Unity. Использовать при любой работе с кодом и сценами Unity-проекта.
---

# Unity

> Набор в стадии каркаса: уточняется на первом Unity-проекте. Версии пакетов и MCP проверяй через веб.

## Код и структура
- `Assets/_Project/{Scripts,Prefabs,Scenes,Data,Art,Audio}`; сторонние пакеты — отдельно.
- Данные (враги, оружие, предметы) — `ScriptableObject`; логика читает данные.
- Минимум логики в `Update`: один менеджер обновляет много объектов; события (`UnityEvent`/C# events) вместо поиска объектов.
- `[SerializeField] private` вместо публичных полей; без `GameObject.Find` в рантайме.
- Assembly Definitions для скорости компиляции и тестов.

## Производительность
- Пулы (`UnityEngine.Pool.ObjectPool<T>`) для снарядов, врагов, эффектов.
- GPU instancing / SRP Batcher; Profiler и Frame Debugger перед оптимизацией.
- Тысячи однотипных объектов — см. `unity-dots`.
- Без аллокаций в горячих циклах (LINQ, строки, замыкания).

## Тесты
Unity Test Framework: EditMode (логика, данные) и PlayMode (сценарии); запуск из командной строки `-runTests -batchmode`.

## MCP
Для связки с Claude — MCP-сервер для Unity Editor; выбрать и проверить через `skill-vetting` при старте проекта (официальные варианты предпочтительнее).
