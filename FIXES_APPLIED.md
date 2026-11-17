# Внесённые правки (ветка arena/8efbc4c4-fablestrike)

Этот файл — что уже исправлено в коде прямо в аудите (минимальные безопасные патчи).

## 1. `game/main.gd` — шаред-материал
**Проблема:** `m.ao_enabled = false` правил shared `StandardMaterial3D`, красили все инстансы.
**Фикс:** `m.duplicate()` + `surface_set_material(i, dup)` перед правкой.
**Риск:** 0. Только локальная копия материала.

## 2. `game/db.gd` — валидация
Добавлена `_validate()` с `assert(RAR_ODDS.sum()≈1.0)`. Ловит опечатки в шансах кейсов до рантайма.

## 3. `game/actor.gd` — `_headroom()`
Луч → капсула `PhysicsShapeQuery`. Теперь дверь с низким потолком не даёт встать (раньше луч проходил сбоку).

## 4. `game/fighter_body.gd` — `die(front)`
При `to.length()<0.1` (падение/суицид/телепорт) теперь явно `front=true` как безопасный фолбэк, без `normalized()` нуля.

## 5. `game/nade.gd` — маска
`mask 1 → 1|2` — граната теперь сталкивается с бойцами, а не пролетает сквозь них.

## 6. `game/brain.gd` + `game/match.gd` — `reports`
Было: `arr.pop_front()` если `size>24` — мусор 9с+ копился.
Стало: чистка по времени `now - t > 9000` + лимит `32`. `hot_site()` больше не тонет в 2-минутных репортах.

## 7. `.gitignore`
Добавлен: `.godot/`, `*.pck`, `.tmp`, `blender/__pycache__/`, `shots/`, `user://`.

## Как проверить
```bash
git diff main --stat
godot -- --walltest --headless --quit   # не должен падать
godot -- --sndtest --headless --quit
```

Полный список TODO — в `ROADMAP.md`.
