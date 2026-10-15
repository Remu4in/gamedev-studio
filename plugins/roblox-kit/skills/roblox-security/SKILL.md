---
name: roblox-security
description: Безопасность Roblox-игры — валидация RemoteEvents, авторитет сервера, античит, защита экономики и покупок, бэкдоры в моделях и плагинах из Creator Store, фильтрация текста, правила для детской аудитории. Использовать вместе с агентом appsec-reviewer, при любом сетевом коде, покупках и вставке сторонних ассетов.
---

# Безопасность Roblox

**Клиент полностью под контролем эксплойтера:** он может вызывать любые RemoteEvent с любыми аргументами, менять свои LocalScript, позицию персонажа, читать всё, что реплицировано клиенту.

## Валидация каждого OnServerEvent
```lua
Remotes.Attack.OnServerEvent:Connect(function(player: Player, targetId: unknown)
    if typeof(targetId) ~= "number" then return end          -- тип
    if not RateLimit.allow(player, "Attack", 5) then return end -- частота (раз/с)
    local char = player.Character
    local target = Enemies.get(targetId)
    if not char or not target then return end                  -- состояние
    if (char:GetPivot().Position - target:GetPivot().Position).Magnitude > MAX_RANGE then return end -- дистанция
    Combat.damage(player, target)                               -- урон считает сервер
end)
```
- Проверяй: `typeof` каждого аргумента, NaN/inf у чисел, длину строк и таблиц, частоту, дистанцию, кулдауны, владение предметом, текущее состояние раунда.
- Никогда не принимай от клиента: урон, награду, цену, количество валюты, ID «купленного» предмета без проверки.

## Авторитет
- Валюта, инвентарь, урон, HP врагов, таймеры, награды — только на сервере.
- Движение игрока клиентское (сетевое владение) → серверные проверки скорости/телепортов для соревновательных режимов; NPC — `SetNetworkOwner(nil)`.
- В `ServerStorage`/`ServerScriptService` — всё, что клиент не должен видеть.

## Покупки и данные
- `MarketplaceService.ProcessReceipt` — выдача **после** сохранения, идемпотентность по `PurchaseId`, возврат `NotProcessedYet` при ошибке. Детали — `roblox-monetization`, `roblox-data`.
- Защита от дюпа: сессионная блокировка данных, атомарные `UpdateAsync`.

## Сторонние ассеты и плагины (бэкдоры)
- Модели из Toolbox/Creator Store часто содержат скрытые скрипты: `require(<число>)`, `getfenv/setfenv`, `loadstring`, обфусцированные строки, `HttpService`, скрипты глубоко внутри мешей.
- После вставки: найти все `LuaSourceContainer` в модели и удалить, если поведение не нужно. Grep по месту: `require%(%d+%)`, `getfenv`, `loadstring`.
- `ServerScriptService.LoadStringEnabled` — выключен. `HttpService.HttpEnabled` — только если реально нужен.
- Studio-плагины из магазина — через `skill-vetting`; плагины имеют полный доступ к месту.

## Текст и дети
- Любой текст от игрока, показываемый другим (имена питомцев, таблички) — через `TextService:FilterStringAsync`; чат — `TextChatService`.
- Не собирай персональные данные; соблюдай правила Roblox для возрастов и Maturity-анкету.

## Ревью (Grep)
`OnServerEvent`, `OnServerInvoke`, `InvokeClient`, `require(`, `loadstring`, `getfenv`, `HttpService`, `ProcessReceipt`, `SetAsync`, `:Kick(`, `PlayerAdded`.
