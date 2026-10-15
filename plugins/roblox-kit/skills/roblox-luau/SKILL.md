---
name: roblox-luau
description: Код и архитектура Roblox на Luau — клиент/сервер, где какой скрипт, модули, строгая типизация, RemoteEvents, производительность, StreamingEnabled, инструменты (Rojo, rokit, luau-lsp, selene, StyLua). Использовать при написании и ревью любого Luau-кода и при настройке Roblox-проекта.
---

# Luau и архитектура Roblox

## Где что живёт
- `ServerScriptService` — серверная логика (Script). `ServerStorage` — то, что клиент не должен видеть.
- `ReplicatedStorage` — общие модули, конфиги, RemoteEvents/RemoteFunctions (папка `Remotes`).
- `StarterPlayerScripts` / `StarterCharacterScripts` — клиент (LocalScript). `StarterGui` — интерфейс.
- Один входной Script на сервере и один LocalScript на клиенте, которые подключают ModuleScript-сервисы. Без десятков разрозненных скриптов в моделях.

## Код
- `--!strict` в каждом файле, типы для публичных функций и таблиц данных.
- `game:GetService("…")` всегда; `WaitForChild` — только для того, что реплицируется и может прийти позже (на клиенте), с таймаутом в отладке.
- `task.spawn/task.delay/task.wait`, не устаревшие `spawn/wait/delay`.
- Конфиги (враги, предметы, цены) — таблицами в `ReplicatedStorage/Shared/Config`; логика читает конфиги.
- Подключения (`:Connect`) — отключать при уничтожении объекта/выходе игрока; `Instance:Destroy()` для очистки.
- Теги (`CollectionService`) и атрибуты (`SetAttribute`) — для пометки объектов вместо поиска по именам.

## Сеть (детали безопасности — `roblox-security`)
- Клиент шлёт намерения через RemoteEvent, сервер проверяет и применяет. `RemoteFunction` от сервера к клиенту не использовать (клиент может не ответить).
- `UnreliableRemoteEvent` — для частых некритичных обновлений (эффекты, позиции).
- Эффекты, звуки, UI-анимации — на клиенте по событиям сервера.

## Производительность
- Один цикл `RunService.Heartbeat` на систему (например, все NPC), а не по скрипту на объект.
- Пулы для часто создаваемых объектов (снаряды, эффекты); не создавать и уничтожать сотни Part в секунду.
- `StreamingEnabled` для больших карт; критичное — `ModelStreamingMode`/`Persistent`.
- Профилирование — MicroProfiler (скилл `rbx-perf-profiling`), Developer Console (F9) → память/сеть/скрипты.
- Мобильные устройства — основная аудитория: проверяй на слабом устройстве через Device Simulator.

## Инструменты проекта
- **Rojo** — код в файлах и git, синхронизация со Studio; **rokit** — менеджер версий инструментов (`rokit.toml`).
- **luau-lsp** (подсказки, типы), **selene** (линтер), **StyLua** (формат).
- Встроенный **Script Sync** — простой вариант без Rojo (только скрипты).
- Пакеты Wally и сторонние модули — только через `skill-vetting`.
