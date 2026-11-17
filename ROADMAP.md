# FABLE STRIKE 2 — Дорожная карта улучшений

> Основано на аудите `AUDIT.md`. Приоритеты: P0 — гигиена/криты, P1 — разгрузка монолита, P2 — перфоманс, P3 — геймплей/ИИ, P4 — сеть.

## P0 — Гигиена (1–2 дня) — ✅ часть уже внесена

| # | Задача | Файл | Статус | Кому |
|---|--------|------|--------|------|
| P0-1 | `duplicate()` материала оружия (шаред-ресурс не мутировать) | `main.gd:_prep_weapons` | ✅ Исправлено | — |
| P0-2 | `.gitignore` + убрать `embed_pck` в релизе | `export_presets.cfg`, `.gitignore` | ✅/TODO | DevOps |
| P0-3 | Валидация `DB.RAR_ODDS == 1.0` | `db.gd` | ✅ | — |
| P0-4 | `_headroom()` луч → капсула | `actor.gd` | ✅ | — |
| P0-5 | `die(front)` при `to==0` | `fighter_body.gd` | ✅ | — |
| P0-6 | Граната `mask 1 → 1|2` (не сквозь бойцов) | `nade.gd` | ✅ | — |
| P0-7 | `reports` чистка по времени (9с), а не по размеру 24 | `match.gd`/`brain.gd` | ✅ | — |
| P0-8 | Нормализовать пути: `FABLE_.../исходники/` → `src/` симлинк, убрать кириллицу из `res://` | проект | TODO | Lead |
| P0-9 | `README.md` с управлением, `godot --headless -- --walltest` | корень | TODO | Docs |

## P1 — Разгрузка монолита `match.gd` (3–4 дня)

`match.gd` 1060 строк → 6 систем. Каждая — `Node` с `setup(match)` + `tick(dt)`.

```
src/game/systems/
  round_manager.gd   S, t_left, _start_round/_end_round/_halftime, win_target
  economy.gd         WIN/LOSS, _bot_buy, money, loss_streak
  bomb_system.gd     BombState, plant/defuse/_bomb_tick/_explode
  combat.gd          bullet/knife_hit/on_hurt/on_death (raycast + zone)
  nade_system.gd     smokes/fires/nades, _areas_tick, smoke_blocks()
  intel.gd           reports, hot_site, noise/hear (заменить словари)
  test_harness.gd    vmtest/tptest/sndtest/walltest/hudtest/loop
```

**Типизация:**
```gdscript
class_name BombState extends RefCounted
enum State { NONE, CARRIED, DROPPED, PLANTED, EXPLODED, DEFUSED }
var state: State
var pos: Vector3
var carrier: Actor
var site: String # "a"|"b"
var t: float
var node: Node3D
var planter: Actor
```

`smokes: Array[Smoke]` где `Smoke {pos:Vector3, r:float, t:float, node:Node3D}`.

**Критерий готовности:** `match.gd` < 350 строк, `match.tscn` без изменений, все `_*_test` проходят.

## P2 — Производительность (2 дня)

| # | Что | Где | Ожидаемый эффект |
|---|-----|-----|------------------|
| P2-1 | Пул взрывов: 6× `CPUParticles` заранее, не `new` каждый раз | `fx.gd: explosion()` | −80% GC спайков |
| P2-2 | `LOS` батч: `PhysicsServer` `intersect_ray` в один вызов на всех ботов | `brain.gd:_sense` | −60% raycast |
| P2-3 | HUD на `Control` нодах вместо `draw_*` каждый кадр | `hud.gd` | −40% fill-rate на 4K |
| P2-4 | LOD карты: `kasbah.glb` → `kasbah_lod1.glb` (дальние дома без интерьера) | `world.gd` + Blender | +15 FPS на low |
| P2-5 | Прелоад `AnimLib.lib_for()` в `Boot` (фон), не на первом спавне | `anim_lib.gd`, `boot.gd` | убрать фриз 150мс |
| P2-6 | `SDFGI`/`VolumetricFog` только на `quality==3` | `world.gd:_lights` | +20% VRAM на low |

## P3 — Геймплей и баланс (3 дня)

- **Пробитие:** `wall` в метрах. Таблица: стена 0.15м (фанера), 0.30м (кирпич), 0.50м (бетон). `AK wall=0.35`, `AWP=0.60`, `deagle=0.45`. Формула `pen_left -= exit_at * (wood?1:5)` → `exit_at / wall`.
- **Шум:** `noise()` только если `world.los(from, listener) || dist<8`.
- **Гранаты:** отскок от бойца `vel*0.35`, `rest` если `vel<1 && n.y>0.7`.
- **Экономика:** `PLANT_BONUS` только `alive` на момент `plant`, `PLANT_LOSS_BONUS` только если `bomb.state==planted`.
- **Разброс:** `spread_deg()` — вынести в `DB.W[*]["spread_standing"]` + `spread_moving`.

## P4 — ИИ (2 дня)

- `NavigationServer3D` + `NavigationMesh` вместо `AStarGrid2D` (плавные диагонали, рампы без `ConvexPolygon`).
- `Memory` класс: `last_seen`, `alert`, `reports` с decay `exp(-t/3)`, не `>9000` хардкод.
- `Grenade aim`: `if not world.los(eye, last_seen): skip`.
- `Strafe` — добавить `peek` (выглядывание) вместо вечного `strafe=-strafe`.

## P5 — Сеть (5–7 дней, опционально)

- `MultiplayerAPI` + `MultiplayerSynchronizer` (Godot 4) для `Actor` (pos/yaw/pitch/hp/cur).
- Авторитет сервера: `Actor.move_step` + `Combat.bullet` только на сервере, клиент — предикция + `rollback`.
- `Dedicated server` export: `Linux headless`, `args --server --port 7777`.
- Античит: `money`/`ammo` только сервер, клиент шлёт `try_fire()` RPC.

## P6 — Контент и DX (3 дня)

- Blender: `argparse`, `pathlib.Path`, `requirements.txt`, убрать `C:\\Users\\...`.
- Карта: `kasbah.json` → `kasbah.ldtk` (LDtk) или Tiled, редактор визуальный.
- Локализация: `tr()` + `localization/ru.csv`, `en.csv`.
- CI: GitHub Actions `godot --headless --export-release Windows` + `walltest`/`sndtest` как gate.

## Как начать — команды

```bash
# Открыть в Godot 4.6.2
godot --path "FABLE_STRIKE_2_для_подписчиков/3_сутки/исходники" .

# Тесты
godot -- --walltest --headless --quit
godot -- --sndtest --headless --quit --shots ./_shots

# Замеры FPS (в матче)
godot -- --auto --maxtime 60
tail -f _shots/log.txt | grep FPS

# Профилирование (в игре Tab покажет FPS если show_fps=true)
```

## Метрики успеха

- `match.gd` строк: 1060 → 300
- Типов `Dictionary` без класса: 12 → 0
- Raycast/кадр в бою: ~80 → ~30
- `exe` размер: ~600 МБ → ~180 МБ (pck отдельно, `export_filter=resources`)
- Загрузка меню: 1.2с → 0.6с

---
*Следующий шаг: выбрать фазу — начнём с P1 (разгрузка) или P2 (перфоманс)?*
