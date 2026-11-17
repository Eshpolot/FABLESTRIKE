# FABLE STRIKE 2 — Глубокий аудит проекта (версия «3 суток» / 9 ч 08 м)

> **Ветка:** `arena/8efbc4c4-fablestrike` (от `e063f24`)  
> **Движок:** Godot 4.6.2, Forward Plus, Jolt Physics, GDScript  
> **Размер кода:** ~8 900 строк GDScript + 2 700 Python (Blender), 24 файла игры, 7 системных  
> **Карта:** Kasbah 96×80, ~200 коллайдеров, nav-сетка AStarGrid2D  
> **Дата аудита:** 2026-11-17

---

## 1. Что за проект — взгляд сверху

FABLE STRIKE 2 — законченный тактический шутер 5×5 с закладкой бомбы, экономикой, ботами, закупкой, скинами и кейсами. Сделан за 9 часов нейросетью Fable 5.2. Это не прототип — это игра с полным циклом:

```
Boot → Menu (3D сцена + UI) → Match (раундовая логика) → Over → Menu
      ↘ кейсы/инвентарь/настройки                    ↗ экономика/скины
```

**Ключевые достоинства, которые нельзя ломать:**
- **CS-движение** (ускорение/трение/прыжок/присед) — ощущение CS, не аркады.
- **ViewModel как отдельный мир** — руки/оружие рендерятся своей камерой (SubViewport, слой 2) с отдельным светом и окружением. Это даёт чёткость оружия.
- **Процедурное оружие в Blender** — 17 моделей собираются кодом из JSON-контуров, а не лепятся руками. Повторяемо и расширяемо.
- **Ретаргетинг анимаций** — 82 миксамо-клипа переносятся на 4 скелета Tripo через `AnimLib`.
- **Пул эффектов** — трассеры/декали/дым/огонь не спавнятся, а переиспользуются.

---

## 2. Карта репозитория

```
FABLE_STRIKE_2_для_подписчиков/3_сутки/исходники/
├── project.godot          # 1920×1080, canvas_items, MSAA, Jolt, 3 слоя физики
├── export_presets.cfg     # Windows x64, embed_pck=true, только *.json в фильтр
├── game/                  # 23 файла, 6 500 строк
│   ├── main.gd    (G)     # Autoload: настройки, профиль, смена сцен, args
│   ├── sfx.gd     (Sfx)   # Autoload: пул 2D/3D звуков, музыка, ambient
│   ├── db.gd      (DB)    # Таблицы оружия/экономики/скинов/кейсов
│   ├── match.gd           # Сердце игры — 1060 строк, 6 ролей одновременно
│   ├── actor.gd           # База бойца: движение, оружие, урон, инвентарь
│   ├── player.gd          # Ввод, камера, spectate, тряска, FOV
│   ├── bot.gd             # Тонкая обёртка над Brain
│   ├── brain.gd           # ИИ 455 строк: зрение, стрельба, навигация, роли
│   ├── world.gd           # Карта: glb + json (коллайдеры/nav/свет/зоны)
│   ├── viewmodel.gd       # FP-руки/оружие 537 строк, пружины отдачи
│   ├── fighter_body.gd    # TP-модель: поза, оружие в руке, Aim/Gun модификаторы
│   ├── anim_lib.gd        # Ретаргетинг 82 клипов (K-поправки)
│   ├── fx.gd              # Пулы: 28 трейсеров, 90 декалей, 18 дымов, 10 вспышек
│   ├── nade.gd            # Баллистика гранат с отскоками
│   ├── hud.gd             # Весь HUD 421 строка (рисуется в _draw)
│   ├── buy_menu.gd        # Закупка 5 колонок + инфо-панель
│   ├── menu.gd            # Главное меню: 3D строй + панели Play/Cases/Inv/Settings
│   ├── ui.gd              # Стиль: цвета, шрифты, кнопки, иконки
│   ├── skins.gd           # Шейдер скинов (чипы, 5 видов рисунка)
│   └── ... boot.gd, pause_menu.gd, settings_panel.gd
├── blender/               # 9 скриптов сборки моделей
│   ├── cs2_tools.py        # Ядро: new_asset, add_part, запись кадров
│   ├── cs2_weapons.py      # 17 стволов/гранат/бомба
│   ├── cs2_mat.py          # Материалы (Principled, VIEW_COL)
│   ├── cs2_fighter.py      # Тела + руки
│   └── cs2_map.py          # Карта Kasbah (коллайдеры из Blender)
└── assets/                # glb + текстуры + иконки + радар
```

**Тяжесть:** `match.gd` (1060), `actor.gd` (619), `blender/cs2_tools.py` (680), `blender/cs2_mat.py` (597) — на них 40% логики.

---

## 3. Пофайловый разбор — что хорошо, что болит

### 3.1 `game/main.gd` (G — синглтон)
**Хорошо:**
- `CFG`/`SAVE` в `user://`, JSON с `to_json`, `nosave`/`mute` для тестов.
- `apply_settings()` корректно переключает `VSync`, `MSAA`, `scaling_3d`.
- `_prep_weapons()` — хак против чёрных стволов (отключение AO) — умно.

**Болит — КРИТИЧНО:**
```gdscript
# Сейчас:
m.ao_enabled = false
m.albedo_color = Color(lift,lift,lift)
# Проблема: m — shared ресурс. Меняя его, вы красите ВСЕ инстансы
# этого материала в игре (и в FighterBody, и в ViewModel, и на земле).
```
Нужно `m = m.duplicate()` перед правкой.

**Мелко:**
- `InputMap` создаётся каждый запуск, но не очищается от старых биндов → дубли.
- `get_tree().root.content_scale_factor = 1.2` — хардкод, ломает 4K.

---

### 3.2 `game/db.gd` — база данных игры
**Хорошо:** Все цифры в одном месте. Экономика близка к CS (loss streak 1400→3400, win 3250/3500).

**Болит:**
- Нет валидации: если `Rar_ODDS` не суммируется в 1.0, кейс ломается.
- Цены и `price_of("helmet")` с учётом уже купленного кевлара — логика размазана между `DB` и `Actor`.
- Жёсткие строки: `"t"`, `"ct"`, `"ak"` — опечатка = молчаливый баг. Нужен `enum`.

---

### 3.3 `game/match.gd` — монолит
**Это самая тяжёлая точка.** Файл делает 6 ролей:
1. `S` машина состояний раунда (FREEZE/LIVE/PLANTED/END/HALF/OVER)
2. Экономика (`_bot_buy`, `loss_streak`, `PLANT_BONUS`)
3. Бомба (`plant_t`, `defuse_t`, `_bomb_tick`)
4. Бой (`bullet`, `knife_hit`, `on_hurt/on_death`)
5. Гранаты/зоны (`nade_burst`, `_areas_tick`, `smoke_blocks`)
6. Тесты (`_vm_test`, `_tp_test`, `_snd_test`, `_wall_test`, `_hud_test`, `_loop_shot`)

**Проблемы:**
- Состояние `state` — int-enum без `class_name MatchState`, легко спутать.
- `bomb` — Dictionary с 7 полями без типа. Опечатка `bomb["cariier"]` не поймается.
- `smokes: Array`, `fires: Array` — словари без класса, `s["r"]`/`f["tick"]` — магия.
- `bullet()` — pen_left считается в метрах, но `wall=2.2` у AWP > толщины стены 0.3 — AWP шьёт всё. Баланс?
- `noise()` + `hear()` — бот слышит сквозь стены.
- `_physics_process` делает `_check_win()` каждый кадр, даже в `FREEZE` — лишнее.
- Автотесты (`auto`, `maxtime`, `loop`) намешаны в прод-код.

**Риск:** Любое изменение экономики затрагивает `bullet()`, потому что всё в одном файле.

---

### 3.4 `game/actor.gd` — физика бойца
**Хорошо:** CS-точные константы (`ACCEL 5.6`, `FRICTION 5.2`, `AIR_CAP 0.76`), отдельный `crouch_t` с `_headroom()`.

**Болит:**
- `_headroom()` — луч, а не капсула. В углу с низким потолком боец застрянет.
- `punch` (отдача) суммируется без `clamp` → при зажатии может улететь в `±20°`.
- `hit_rids` включает `self` + 4 хитбокса, но не `body` (FighterBody) — по TP-модели пуля не проходит? Проверьте.
- `take_damage()` — `pen` для `fall/fire` = 0.5, но `wid != "fall"` уже проверен, `fall` всё равно получает 50% урона через броню — странно.

---

### 3.5 `game/brain.gd` — ИИ
**Хорошо:**
- `skill = [0.28,0.55,0.82][d] + [-0.06…0.06][idx]` — баланс команд, не рандом.
- `react_time() 0.2–0.62с` + `hold_adv` 2.5с — держащий угол реагирует быстрее.
- `aim_err` затухает `exp(-see_t * skill)` + `sin` дрожь — живо.
- `hot_site()` — команда помнит, где видели врага (reports 9с).

**Болит — СРЕДНЕ:**
- `_sense()` — `fov 0.38` (~68°) + `smoke_blocks()` — дым блокирует, но `hear()` нет → бот слышит сквозь дым.
- `path = world.path(...)` каждый репас, без кэша → при 10 ботах 10× A* каждый 0.7с.
- `stuck_t` — патч от застревания прыжком, но `jump` в `move_step` не проверяет, что впереди стена → бот прыгает на месте.
- `nade_t` — бросает гранату, но не проверяет, что `last_seen` за стеной → граната в стену.
- `reports` растёт до 24, но не чистится по времени → через 2 минуты 80% мусора.

---

### 3.6 `game/world.gd`
**Хорошо:** `w()`/`m()` конверсия, `AStarGrid2D` с `weight_scale` у стен, `ramps` через `ConvexPolygonShape3D`.

**Болит:**
- `colliders` 200+ `BoxShape3D` — каждый отдельный `StaticBody` → 200 объектов. Лучше один `StaticBody` с 200 шейпами.
- `props_body` помечен `wood=true`, но `bullet()` проверяет `col.has_meta("wood")` — стена 1.0 vs дерево 0.2, но `wood` стоит на всём `props_body`, даже на металле.
- `ramps` — 8 точек `ConvexPolygon`, порядок важен, но генерится `(x0,y0,z0)...` без проверки winding → иногда нормаль внутрь.
- `_lights()` — `SDFGI` включается при `quality>=2`, но `min_cell_size 0.4` — тяжело для низких ПК.

---

### 3.7 `game/viewmodel.gd` — жемчужина и тяжесть
**Хорошо:** `ELBOWS`/`HANDS`/`CURLS` таблицы, `PALM` оффсет, `grip_cam`, пружины `kick_pos/kick_vel` с микшагами 0.006с, `muzzle_world()` с учётом FOV.

**Болит:**
- `tick()` — 200 строк, 6 секций (`draw_t`, `rel_t`, `cycle_t`, `inspect_t`, `swing_t`, `throw_t`) — читать тяжело.
- `HOLD["awp"]` оффсет + `HOLD_W` — два места для одной настройки.
- `_hand_xf()` — `w_linv` считается каждый кадр, хотя константа.
- `weapon.visible = false` при броске, но `skel` руки остаются — видно пустые ладони 0.3с.

---

### 3.8 `game/fighter_body.gd` + `anim_lib.gd`
**Хорошо:** `AimMod` (spine 1-3) + `GunMod` (двуручный хват), `GripCache`, `is_loop()` фильтр.

**Болит:**
- `scene()` кэширует `PackedScene`, но не `instantiate` → каждый бот грузит `glb` снова (хотя Godot кэширует, но явный кэш лучше).
- `die()` — `front = fwd.dot(to) >0` — если `to.length()<0.1` считается `front=true`, но `from==self` даёт `to=0` → всегда front. Голова сзади = front-смерть — баг.
- `lib_for()` — тяжёлый ретаргетинг считается на первом спавне → фриз 100–200мс. Нужен прелоад.

---

### 3.9 `game/fx.gd` / `sfx.gd` / `nase.gd` / `skins.gd`
- **Fx:** Пулы отличные, но `explosion()` создаёт *новые* `CPUParticles3D` каждый взрыв (не из пула) → GC спайки.
- **Sfx:** `_scan()` грузит все `wav/ogg` в RAM. При 30 звуках × 2 варианта = 60 стримов — ок, но при 200 будет тяжело. `has("shot_far")` проверяется каждый выстрел.
- **Nade:** `PhysicsRayQuery` с `mask=1` — ловит только мир, но не других бойцов → граната пролетает сквозь бота.
- **Skins:** Шейдер с `opos = VERTEX` — работает, но `chips=0.18` хардкод, нет износа (float).

---

### 3.10 `game/hud.gd` / `buy_menu.gd` / `menu.gd` / `ui.gd`
- **HUD:** Весь рендер через `root.draw` каждый кадр — 30+ `draw_*` вызовов. На 4K это дорого. Лучше `Control` ноды.
- **Radar:** `load("radar.png")` каждый HUD, без кэша в `UI`.
- **Menu:** 4 бойца в `menu.gd` + `world.load_map("kasbah")` — та же карта грузится и в матче → 2× память текстур.
- **Buy:** `price_of("helmet")` логика дублируется в `Actor`.

---

### 3.11 `blender/` — сборка моделей
**Хорошо:** `cs2_tools.new_asset()`, `vmat()`, `VIEW_COL` — консистентно.

**Болит:**
- Абсолютные пути `C:\\Users\\User\\Downloads\\CS2_FABLE` — не работает нигде кроме автора.
- `DL`, `ROOT`, `MODELS` — глобальные, меняются руками.
- Нет `requirements.txt`, нет `pyproject.toml`.
- `from_pydata(p["v"], [], p["f"])` без проверки `len(v)` → краш на битой json.

---

## 4. Производительность — где теряем FPS

| Место | Проблема | Влияние | Как мерить |
|-------|----------|---------|------------|
| `match.bullet()` 4× raycast + `exit_at` loop 0.12м шагами | 10 выстрелов/с × 10 бойцов = 100+ raycast/с | CPU | `Engine.get_frames_per_second()` + `RENDERING_INFO_TOTAL_DRAW_CALLS` (уже логируется в `_auto_shots`) |
| `brain._sense()` 10× LOS (`world.los` = raycast) каждые 0.12с | 80+ raycast/с | CPU | профайлер `Performance` → Physics |
| `fx.explosion()` создаёт новые ноды | GC, 3× `CPUParticles` на взрыв | Микрофриз | `OS.get_static_memory_usage()` |
| `hud._draw_hud()` 30+ draw каждый кадр | Fill-rate на 4K | GPU | `Viewport.scaling_3d_scale` уже есть, но 0.77 на low мало |
| `world._lights()` SDFGI + Volumetric Fog на `quality=2` | VRAM + шадов | GPU | `RenderingServer.get_rendering_info(RENDERING_INFO_TEXTURE_MEM_USED)` |
| `anim_lib.lib_for()` на первом спавне | Фриз 150мс | Загрузка | `Time.get_ticks_msec()` уже логируется |

**Бюджет кадра (цель 144 FPS):**
- Физика 64 tick → 15.6мс бюджет, но `move_and_slide()` 10 тел = ~2мс — ок.
- Рендер: `kasbah.glb` ~200k verts, 4K теней 4096 — тяжело. Нужно LOD.

---

## 5. Баги и острые углы (приоритет)

| # | Файл:строка | Баг | Тяжесть |
|---|-------------|-----|---------|
| 1 | `main.gd: _prep_weapons` | Мутация shared материала | 🔴 Крит |
| 2 | `actor.gd: _headroom()` | Луч вместо капсулы, застревание в дверях | 🟠 Выс |
| 3 | `match.gd: bullet()` `exit_at` | Шаг 0.12м, `lim=0.12` → `while s <= lim` 1 итерация, но `pen_left -= exit_at*5` → стена 0.3м = пен 0.3*5=1.5 > `wall=0.5` → не пробивается даже тонкая стена деревом | 🟠 Выс |
| 4 | `fighter_body.gd: die()` | `to.length()<0.1 → front=true` → смерть сзади = лицом | 🟡 Средн |
| 5 | `nades.gd: launch` | `mask=1` игнорит бойцов → граната сквозь них | 🟡 Средн |
| 6 | `brain.gd: reports` | Не чистится, 9с окно, но массив 24 → через 2 мин 70% мусора | 🟡 Средн |
| 7 | `player.gd: _unhandled_input` | `scoped` снижает sens 0.42, но не возвращает при `try_fire` промахе → залипание | 🟡 Средн |
| 8 | `match.gd: _bomb_tick` `drop` | `carrier` подбирает бомбу на расстоянии 1.1, но `dropped_c4.position.y=0.02` → на рампе бомба под землёй | 🟡 Средн |
| 9 | `export_presets.cfg` | `embed_pck=true` → exe 500+ МБ, нет `export_filter=resources` | 🟢 Низ |

---

## 6. Что улучшить — дорожная карта

### Фаза 0 — Гигиена (1 день, без риска)
1. **Починить шаред-материал** (`main.gd` → `duplicate()`).
2. **Добавить `.gitignore`** (`*.pck`, `user://`, `.godot/`, `blender/__pycache__`).
3. **Нормализовать пути**: вынести `FABLE_STRIKE_2_для_подписчиков/3_сутки/исходники/` → `src/` + симлинк, убрать кириллицу из путей (ломает CI на Linux).
4. **README**: управление, требования, как открыть в Godot 4.6.2, как запустить тесты (`--auto --maxtime 60`).
5. **Валидация `DB`**: `assert RAR_ODDS.sum()≈1.0`.

### Фаза 1 — Разгрузка монолита (3 дня)
6. **Разбить `match.gd`** на системы:
   ```
   match.gd          → RoundManager (S, t_left, _start_round, _end_round)
   economy.gd        → Economy (WIN/LOSS, _bot_buy, money)
   bomb_system.gd    → Bomb (state, _bomb_tick, plant/defuse)
   combat.gd         → Combat (bullet, knife_hit, on_hurt/death)
   nade_system.gd    → NadeSystem (throw, burst, _areas_tick)
   test_harness.gd   → все _*_test вынесены
   ```
   Каждая система — `Node` с `setup(match)`, `tick(dt)`.
7. **Типизировать `bomb`/`smokes`/`fires`**: `class_name BombState`, `Smoke{pos,r,t,node}`, `Fire{pos,r,t,owner}`.
8. **Вынести `hot_site`/`report` в `Intel` синглтон**.

### Фаза 2 — Производительность (2 дня)
9. **Пул взрывов**: не `new CPUParticles`, а 6 заранее созданных.
10. **LOS кэш**: `world.los` с `exclude` уже есть, добавить `PhysicsServer` batch query.
11. **HUD на нодах**: `Crosshair`, `HealthBar`, `AmmoCounter` как `Control`, а не `draw_*`.
12. **LOD карты**: `kasbah.glb` → 2 уровня (дальние здания без интерьера).

### Фаза 3 — Геймплей (3 дня)
13. **Баланс пробития**: `wall` в метрах, а не в попугаях. Таблица: стена 0.3м, AWP шьёт 0.6м, AK 0.3м.
14. **Шум сквозь стены**: `noise()` → `world.los` check, `hear()` только если LOS или <8м.
15. **Гранаты**: `mask=5` (мир+бойцы), отскок от бойца с потерей 0.7.
16. **Экономика**: `plant` бонус 300 только если `alive` на момент взрыва (сейчас всегда).

### Фаза 4 — ИИ (2 дня)
17. **Навмеш вместо AStarGrid2D**: `NavigationServer3D` с бэйком — плавные пути, без 1м клетки.
18. **Memory-decay**: `reports` чистить `now - t > 9000`, не `size>24`.
19. **Grenade aim**: проверка `world.los(eye, last_seen)` перед броском.
20. **Skill кривая**: `skill` влияет не только на `react_time`, но и на `burst_pause` (сейчас `lerp 1.5→0.9`, можно 2.0→0.7).

### Фаза 5 — Сеть и платформа (5 дней)
21. **Rollback netcode** или хотя бы `MultiplayerAPI` + `SceneReplication` (Godot 4).
22. **Dedicated server**: `export_presets.cfg` → `Linux/X11` headless, `args --headless --server`.
23. **Античит**: `Actor` на сервере авторитет, клиент только `Player` ввод.
24. **Кроссплатформа**: нормализовать кейсы (`KEY_W` → `InputEventJoypadButton`).

### Фаза 6 — Контент и DX (3 дня)
25. **Blender: убрать `C:\\`**, `argparse`, `pathlib`, `requirements.txt`.
26. **Карта JSON → Tiled/ldtk**: редактировать визуально, а не руками.
27. **Локализация**: `tr("Победа")` + `en.csv`/`ru.csv`.
28. **CI**: GitHub Actions → `godot --headless --export-release` + `_wall_test`/`_snd_test` как pytest.

---

## 7. Архитектура «после» (предложение)

```
Autoloads:  G (settings/profile) • Sfx (audio) • Intel (reports) • DB (data)
Scenes:    Boot → Menu (World+Fighters+UI) → Match
Match
 ├── RoundManager  (S, timers, halftime, win_target)
 ├── Economy       (money, loss_streak, buy)
 ├── BombSystem    (plant/defuse/explode)
 ├── Combat        (raycast, damage, hitbox)
 ├── NadeSystem    (smokes/fires/nades)
 ├── World         (colliders, nav, lights)
 ├── Fx/Sfx        (pools)
 └── Actors (10× Actor → Body + Brain)
        └── Player (input, cam, ViewModel)
```

**Плюсы:** Тесты можно запускать на `Combat` без `Match`, баланс править в `economy.gd`, сеть — только `Combat` + `RoundManager`.

---

## 8. Что делать прямо сейчас (приоритет 1)

- [ ] Починить `main.gd` шаред-материал (1 строка).
- [ ] Вынести `_wall_test` в `tools/tests/` + CI.
- [ ] Добавить `src/` симлинк и `.gitignore`.
- [ ] Написать `docs/CONTRIBUTING.md` с `godot --headless --run` командами.
- [ ] Профилировать `bullet` + `sense` raycasts (включить `PhysicsServer` debug).

---

## 9. Оценка «тяжести»

| Метрика | Сейчас | После Фазы 1-2 |
|---------|--------|----------------|
| Строк в `match.gd` | 1060 | ~300 + 5×150 |
| Типов `Dictionary` без класса | 12 | 0 |
| Raycast/кадр (10 ботов, бой) | ~80 | ~30 (кэш LOS) |
| Время загрузки меню | ~1.2с | ~0.6с (прелоад anims) |
| Размер exe | ~600 МБ (embed_pck) | ~180 МБ (pck отдельно) |

**Вывод:** Проект тяжёл не зря — он цельный. Но монолит `match.gd` и шаред-ресурсы — главные риски. Разгрузка монолита даст +50% к скорости доработки новых фич (оружие, карты, режимы).

---

## 10. Приложения

- **Как запустить тесты:** `godot -- --auto --maxtime 60 --maxtime` (уже в `match.gd`), `godot -- --walltest --headless`.
- **Как мерить баланс:** `G.args["seed"]=123` + `G.log_line("round X")` → парсить логи.
- **Где править скорость:** `DB.W[*]["speed"]` (м/с), `Actor.ACCEL/FRICTION`.

---
*Аудит подготовлен на ветке `arena/8efbc4c4-fablestrike`. Готов помочь с реализацией любой фазы — скажи, с какой начнём.*
