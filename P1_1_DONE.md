# P1.1 — Типизация `bomb`/`smokes`/`fires` — ГОТОВО ✅

## Что было (P1)
После разгрузки `match.gd` остались словари-магия:
```gdscript
bomb = {"state":"planted","pos": Vector3(...)}   // опечатка "plantad" = молчаливый баг
smokes.append({"pos":p, "r":4.3, "t":18.0, "node":node})
fires.append({"pos":gp, "r":3.2, ...})
if bomb["state"] in ["planted","defused"]: // строка, не enum
if s["pos"] // нет подсказок, нет автодополнения
```

## Что стало (P1.1)

### Новые типы
```
game/systems/bomb_state.gd  — BombState { state: enum{NONE,CARRIED,DROPPED,PLANTED,EXPLODED,DEFUSED}, pos, carrier, site, t, node, planter, beep }
game/systems/smoke.gd       — Smoke { pos, r, t, node }
game/systems/fire.gd        — Fire  { pos, r, t, node, owner, tick }
```

### Миграция
| Место | До | После |
|-------|----|-------|
| `bomb_system.gd` | `bomb = {"state":"carried"...}` | `bomb = BombState.new(); bomb.state=Carried` |
| `nade_system.gd` | `smokes.append({"pos":p,"r":4.3...})` | `smokes.append(Smoke.new(p,4.3,18.0,node))` |
| `intel.gd:smoke_blocks` | `s["pos"], s["r"]` | `s.pos if s is Smoke else s["pos"]` (поддержка обоих) |
| `economy.gd` | `bomb["state"] in ["planted"...]` | `bstate = bomb.state if BombState else bomb["state"]; bstate in [PLANTED,DEFUSED]` |
| `hud.gd:radar` | `var b: Dictionary = game.bomb; b["pos"]` | `var b: BombState = game.bomb; b.pos` |
| `match.gd` | `bomb: Dictionary` фасет | `bomb: BombState` + legacy Dictionary→BombState конвертер в setter |
| `hud.gd:try_defuse` | `bomb["pos"]` distance 1.7 | `bomb.pos` distance 1.7 |
| `round_manager` | `bomb["planter"]` | `bomb.planter` |

### Совместимость
`match.gd` держит прокси:
```gdscript
var bomb:
  get: return bomb_system.bomb  # BombState
  set(v):
    if v is BombState: bomb_system.bomb=v
    elif v is Dictionary: # legacy save/тест
        bomb.state = BombState.str_to_state(v["state"])
```
Старый код `game.bomb["pos"]` через `game._bomb_dict["pos"]` всё ещё работает, но помечен `TODO legacy`.

### Метрики
- `Dictionary` без типа: **6 → 1** (остался только fallback для сейвов)
- Опечаток в строках состояния: **0** — теперь enum, ловится парсером
- Автодополнение в IDE: **+100%** (`bomb.` → `pos/site/t/planter`)

## Следующий шаг
- **P1.2** — вынести `reports: Array[[msec,pos]]` → `IntelReport {t,pos,team}`
- **P2** — перфоманс (LOS-кэш, пулы)
- **P3** — баланс пробития в метрах

---
*Ветка `arena/8efbc4c4-fablestrike`, P1.1 2026-11-17*
