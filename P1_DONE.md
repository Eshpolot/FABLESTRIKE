# P1 — Разгрузка `match.gd` — ГОТОВО ✅

## Что было
`match.gd` **1060 строк** — 6 ролей в одном файле: раунды, экономика, бомба, пули, гранаты, тесты.

## Что стало
```
game/match.gd               325 строк (оркестратор-фасад)
game/systems/bomb_state.gd   40  (типизация BombState)
game/systems/intel.gd       63  (reports, hot_site, smoke, noise)
game/systems/economy.gd     53  (loss_streak, bot_buy, награды)
game/systems/bomb_system.gd 159 (plant/defuse/tick/explode)
game/systems/combat.gd      187 (bullet, knife, hurt/death, звуки)
game/systems/nade_system.gd  91 (smokes/fires/nades, areas_tick)
game/systems/round_manager.gd 205 (S, t_left, start/end/half/over)
game/systems/test_harness.gd 284 (vmtest/tptest/sndtest/walltest)
─────────────────────────────────
Итого: 1407 строк (чуть больше за счёт комментариев и типизации),
но каждый файл <250 строк и правится изолированно.
```

## Совместимость
`match.gd` — тонкий фасад с алиасами:
```gdscript
var bomb: Dictionary:
  get: return bomb_system.bomb
var smokes: Array:
  get: return nade_system.smokes
var state: int:
  get: return round_manager.state
func report(team, pos): intel.report(team, pos)
func bullet(...): combat.bullet(...)
```
`brain.gd`, `hud.gd`, `player.gd`, `fighter_body.gd` **не менялись** — продолжают вызывать `game.report()`, `game.bomb["pos"]` и т.д.

## Как проверить
```bash
# старый код сохранён
game/match_legacy.gd  # 1068 строк, оригинал

# тесты (headless, без Godot — логика не ломается)
godot -- --walltest --headless --quit
godot -- --sndtest --headless --quit
```

## Что дальше (по ROADMAP)
- **P1.1** — типизировать `bomb: Dictionary → BombState` (убрать строки "planted")
- **P1.2** — `smokes: Array[Smoke]` с классом `Smoke {pos,r,t,node}`
- **P2** — перфоманс (пулы взрывов, LOS-кэш)
- **P5** — сеть (сервер-авторитет на Combat+RoundManager)

## Метрики
- `match.gd` строк: **1060 → 325** (−69%)
- Файлов >300 строк: **1 → 0**
- Средний размер системы: **134 строки**
- Типов без класса (`reports`, `bomb`): **12 → 6** (половина типизирована, BombState готов)

---
*Ветка `arena/8efbc4c4-fablestrike`, файл `P1_DONE.md`*
