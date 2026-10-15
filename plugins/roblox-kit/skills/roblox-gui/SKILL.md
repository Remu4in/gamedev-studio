---
name: roblox-gui
description: Интерфейс, ввод и камера в Roblox — ScreenGui, адаптация под телефон/ПК/консоль (Scale, UIAspectRatioConstraint, безопасные зоны), анимации TweenService, ContextActionService, мобильные кнопки, game feel интерфейса. Использовать при создании HUD, меню, магазина, уведомлений, управления и камеры.
---

# GUI, ввод, камера

## Раскладка
- `ScreenGui` в `StarterGui`, `ResetOnSpawn = false` для постоянного HUD; `ScreenInsets = DeviceSafeInsets` — не залезать под вырезы и системные кнопки.
- Размеры и позиции в **Scale**, не Offset; `UIAspectRatioConstraint` для квадратных элементов; `UISizeConstraint`/`UITextSizeConstraint` для крайних размеров; `UIListLayout`/`UIGridLayout`/`UIPadding` вместо ручной расстановки.
- Мобильные — большая часть аудитории: кнопки не меньше ~44 px на телефоне, важное — в зоне большого пальца, текст крупный и контрастный.
- Проверяй на телефоне, планшете, ПК и консоли через Device Simulator (скилл Assistant `rbx-device-simulator-lua`) и скриншоты MCP.

## Поведение
- Логика интерфейса — на клиенте; данные (валюта, инвентарь) приходят с сервера через атрибуты/реплицируемые значения/события. Кнопка «купить» шлёт запрос, сервер решает.
- Анимации — `TweenService` (появление 0.15–0.25 с, `Quad`/`Back` Out), отклик на наведение и нажатие (масштаб 1.05/0.95), звук клика.
- Уведомления о наградах — всплывающие, с очередью, не перекрывают центр экрана в бою.
- Онбординг — подсказки по месту (стрелка, подсветка цели), а не стена текста.

## Ввод
- `ContextActionService:BindAction` — одно действие для клавиатуры, геймпада и экранной кнопки (`createTouchButton = true`); `UserInputService` для особых случаев.
- Проверка платформы: `UserInputService.TouchEnabled`, `GamepadEnabled`, `GuiService:IsTenFootInterface()`.

## Камера
- Своя камера — `Camera.CameraType = Scriptable` в `RenderStepped`/`BindToRenderStep`; плавное следование (lerp), коллизии со стенами рейкастом.
- Тряска камеры — на клиенте, сила из настроек (`game-feel`).
