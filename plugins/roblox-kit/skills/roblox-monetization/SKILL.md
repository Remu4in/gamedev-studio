---
name: roblox-monetization
description: Монетизация Roblox-игры — геймпассы, Developer Products, премиум-выплаты, подписки, цены в Robux, безопасная обработка покупок (ProcessReceipt), DevEx. Использовать при проектировании магазина, добавлении покупок и вместе с balance-analyst при оценке экономики.
---

# Монетизация в Roblox

Правила и курсы меняются — актуальные условия (DevEx, комиссии, подписки) проверяй в документации Roblox через веб.

## Что продавать
- **Game Pass** — разовая постоянная покупка: x2 валюты, VIP-зона, доп. слот, косметика. Проверка: `MarketplaceService:UserOwnsGamePassAsync` при входе (кэшировать) + `PromptGamePassPurchaseFinished`.
- **Developer Product** — расходуемое: валюта, бусты, возрождение, ящики (с открытыми шансами). Обработка только через `ProcessReceipt`.
- **Premium Payouts** — выплаты за время игроков с Premium: мягкие бонусы для Premium.
- **Подписки** — если доступны в регионе и для игры (проверить актуальные правила).
- Лестница цен: дешёвый вход (25–100 Robux), средние (200–500), «кит» для фанатов; значение покупки понятно с первого взгляда.

## ProcessReceipt (правильно)
```lua
MarketplaceService.ProcessReceipt = function(receipt)
    local player = Players:GetPlayerByUserId(receipt.PlayerId)
    if not player then return Enum.ProductPurchaseDecision.NotProcessedYet end
    -- идемпотентность: PurchaseId уже обработан? → PurchaseGranted
    -- выдать товар и СОХРАНИТЬ профиль (UpdateAsync) вместе с PurchaseId
    -- при ошибке сохранения → NotProcessedYet (Roblox повторит)
    return Enum.ProductPurchaseDecision.PurchaseGranted
end
```
- Только один обработчик `ProcessReceipt` на игру.
- ID товаров — в конфиге на сервере; цену и товар не принимать от клиента.

## Дизайн магазина
- Покупка улучшает опыт, но бесплатный игрок может всё получить игрой (дольше).
- Показ предложения в момент нужды (после проигрыша — «возродиться»), но без навязчивости.
- Стартовый набор и первые покупки — очень выгодные.

## Деньги
- DevEx: требования (возраст, минимальный порог заработанных Robux, верификация, налоговая форма) и курс — смотри актуальные на сайте Roblox перед планированием дохода.
- Учитывай комиссию платформы при расчёте выручки.
