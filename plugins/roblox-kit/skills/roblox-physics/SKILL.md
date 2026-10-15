---
name: roblox-physics
description: Физика в Roblox — constraints (верёвки, пружины, шарниры, AlignPosition/Orientation, LinearVelocity), Attachments, сетевое владение, группы коллизий, рэгдолл, лазание и падения, транспорт. Использовать для механик восхождения (в духе PEAK), верёвок, ловушек, транспорта, разрушений и рэгдолла.
---

# Физика в Roblox

## Основа
- Mover constraints вместо устаревших BodyMovers: `LinearVelocity`, `AngularVelocity`, `VectorForce`, `AlignPosition`, `AlignOrientation`.
- Связи: `RopeConstraint` (верёвка, длина), `SpringConstraint` (пружина), `RodConstraint`, `HingeConstraint` (двери, моторы), `BallSocketConstraint` (рэгдолл), `PrismaticConstraint` (лифты), `WeldConstraint` (склеить).
- Все constraints крепятся к `Attachment` внутри частей — позиция и ориентация задаются attachment'ом.
- `Anchored` для статики; меньше незакреплённых частей — меньше нагрузка.
- Группы коллизий: `PhysicsService:RegisterCollisionGroup` + `CollisionGroupsAreCollidable`, `BasePart.CollisionGroup` (например, игроки не сталкиваются друг с другом).

## Сетевое владение (главная ловушка)
- Незакреплённые части симулирует ближайший игрок (владелец) — это плавно, но клиент может их «читерить».
- Объекты, влияющие на исход (ловушки, общий груз, транспорт других игроков), — `SetNetworkOwner(nil)` или проверка на сервере.
- Персонаж — всегда во владении своего клиента: серверная проверка скорости/позиции для соревновательных режимов.

## Механики
- **Лазание/восхождение:** свой режим персонажа — рейкаст к стене, `AlignPosition` к точке захвата, выносливость тратится на висение и прыжки; срыв — падение с уроном по высоте. Кооп: верёвка между игроками (`RopeConstraint` между attachment'ами в персонажах), страховка, подтягивание.
- **Рэгдолл:** при падении/смерти `Motor6D` → `BallSocketConstraint`, `Humanoid:ChangeState(Physics)`; возврат — восстановить Motor6D.
- **Транспорт:** `VehicleSeat` + `HingeConstraint` с моторами или `LinearVelocity`.
- **Разрушения:** заранее разрезанные модели, «отпускание» частей (`Anchored = false`) и уборка через `Debris`.

## Подводные камни
- Нестабильность при большой разнице масс — `Massless`, `CustomPhysicalProperties`.
- Тысячи незакреплённых частей — просадки; ограничивай и убирай.
- Тестируй с несколькими игроками и задержкой: физика у владельца и у остальных выглядит по-разному.
