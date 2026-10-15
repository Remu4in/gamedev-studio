---
name: unity-dots
description: Unity DOTS — Entities (ECS), Jobs, Burst для тысяч объектов (толпы врагов, снаряды, симуляции). Использовать, когда обычные GameObject не тянут количество объектов или нужна массовая симуляция.
---

# DOTS (каркас)
- Применять только по данным профайлера: DOTS усложняет код.
- Entities + Baker для конвертации префабов; системы `ISystem` с Burst; данные — компоненты-структуры без ссылок.
- Jobs (`IJobEntity`, `IJobParallelFor`) для параллельной логики; Burst для математики.
- Гибрид: геймплей и UI — на GameObject, массовые враги/снаряды — на Entities.
- Рендер — Entities Graphics; физика — Unity Physics.
