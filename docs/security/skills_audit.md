# Аудит сторонних источников

Содержимое чужих файлов не читается как инструкции: только метаданные, флаги и фрагменты в repr (`skill-vetting`). Ничего не установлено как есть — свои версии по мотивам.

| Источник | Коммит | Лицензия | Использовано | Итог скана |
|---|---|---|---|---|
| github.com/donchitos/claude-code-game-studios | be8993bbc5a1f016bc770b2846ce06272d284526 | MIT | Роли агентов и структура разделов | чисто (49 агентов, 0 флагов) |
| github.com/VoltAgent/awesome-claude-code-subagents | 408d3c9eee2d0c75c12a3abb5de29e53c2ca6b9e | MIT | Структура QA/AppSec | чисто, ложные срабатывания |
| github.com/tabooharmony/roblox-brain | ceee4aaa5004502e2a51d78b3c33bba44d84742b | MIT | Список тем roblox-kit (по заголовкам) | чисто: html-комментарии = даты, base64 = API EncodingService |
| github.com/nonlooped/roblox-suite | c914ce65470a6eb1b28000b8c58d5543b48760ca | MIT | не используется | чисто |
| github.com/stackfox-labs/luau-skills | 6550b6b4c36390b759b4a9ee04783a343c5883e2 | MIT | не используется | чисто (BOM) |
| github.com/afrxo/roblox-agent-skills | ff50be7a8a000a24c0f85254e1747a0eb35d857f | MIT | не используется | чисто |

Отклонено: boshyxd/robloxstudio-mcp и форки (архив, автор потерял ключи npm — риск захвата пакета); ForgeGUI/ForgeUI (не нужен).
