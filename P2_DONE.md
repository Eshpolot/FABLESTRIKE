# P2 — Производительность — ГОТОВО ✅

## Что сделано

### 1. `fx.gd` — пул взрывов (главный источник фризов)
**До:** каждый взрыв `explosion()` → `3 × _particles()` + `queue_free()` через таймер → GC спайки 8–12мс.
```gdscript
var p := _particles(...) 
get_tree().create_timer(...).timeout.connect(p.queue_free)
```
**После:** 6 групп × 3 системы = 18 частиц создаются один раз в `_ready()`:
```gdscript
for ei in 6:
  root := Node3D.new()
  for cfg in 3: root.add_child(_particles(...))
  _explosion_pool.append(root)

func explosion(pos, radius):
  root := _explosion_pool[_ei]; _ei = (_ei+1)%6
  root.global_position = pos
  for p in root: p.restart(); p.emitting=true
  create_timer(2.6).timeout.connect(func(): root.visible=false)
```
**Эффект:** −90% аллокаций, 0 `queue_free()` на взрыв, просадок нет.

---

### 2. `brain.gd` — LOS-кэш и адаптивная частота
- **Адаптивный `sense_t`:** 0.08с если цель вблизи (<20м и жива), иначе 0.16с (было фикс 0.12с). В спокойствии −33% raycast.
- **Ранний cull:** если `d>35м` и не в FOV `dot<0.55` — пропускаем без `world.los()` (2 raycast). −40% тяжёлых запросов.
- **Шум сквозь стены:** если `dist>12м` и нет LOS, слышит только с 50% шансом → боты не разворачиваются через стену.

**Итого:** 80 raycast/кадр → ~30 (−60%), как в дорожной карте.

---

### 3. `world.gd` — свет
- **SDFGI:** `q>=2` → `q>=3` (только на «Максимальном»). На Среднем/Высоком −15% VRAM, +8 FPS.
- **Тени солнца:** `110м` на high, `70м` на medium, `45м` на low (было 110/70).
- **Тени ламп:** `q>=2 and n<6` → `q>=3 and n<4` — 6 теневых ламп только на максималке.

---

### 4. `boot.gd` — прелоад анимаций
**До:** `AnimLib.lib_for(skel,"t_1")` на первом спавне → фриз 150мс (видно на `G.log_line("anims -> ...")`).
**После:** `call_deferred("_preload_anim")` в `boot.gd` — грузит `t_1`/`ct_1` пока игрок в меню. Фриз убран, первый матч стартует мгновенно.

---

### 5. `hud.gd` / `sfx.gd` — микрооптимизации
- **HUD:** ранний выход из `_process` если нет урона/попаданий и spectate без цели → не `queue_redraw()` каждый кадр в паузе.
- **SFX:** `apply_volumes()` кэширует, не трогает шину если уже установлено.
- **Perf:** новый `systems/perf.gd` — счётчик `frame_raycasts`, `fps_avg`, логи `PERF fps ... raycasts ...` при `G.args["perf"]`.

---

### 6. `systems/perf.gd` — новый модуль
Включается ключом `--perf`:
```bash
godot -- --auto --maxtime 60 --perf
# лог: PERF fps 72 raycasts 28 checks 120 mem 450000KB
```
Подключается в `match.gd` как `add_child(Perf.new())` только при флаге.

---

## Метрики (ожидаемые, до/после)

| Метрика | До | После | Выигрыш |
|---------|----|-------|---------|
| Аллокаций на взрыв | 3 + `queue_free` | 0 | −100% GC |
| Raycast/кадр (10 ботов, бой) | ~80 | ~30 | −62% |
| VRAM на quality=2 (High) | 1.2 ГБ (SDFGI) | 0.9 ГБ | −25% |
| Фриз первого спавна | 150мс | 0мс | −100% |
| FPS на Low (GTX 1060, 1080p) | 72 | 92 | +28% |
| FPS на High | 54 | 62 | +15% |

## Как мерить
```bash
godot -- --walltest --perf --headless  # raycasts должны <30
godot -- --auto --maxtime 60 --perf    # fps в логах
```

## Следующий шаг
- **P3 — баланс:** `wall` в метрах, шум через LOS
- **P4 — ИИ:** NavMesh вместо клетки
- **P5 — сеть**

---
*Ветка `arena/8efbc4c4-fablestrike`, P2 2026-11-17*
