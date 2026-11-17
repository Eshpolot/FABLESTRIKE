# CONTRIBUTING

## Структура
Исходники: `FABLE_STRIKE_2_для_подписчиков/3_сутки/исходники/game/`
Карта: `assets/maps/kasbah.json` + `kasbah.glb`
Сборка моделей: `blender/*.py` (требуют Blender 4.x, см. blender/README)

## Правила
- GDScript: snake_case, type hints, `class_name`.
- Коммиты: `feat:`, `fix:`, `perf:`.
- Не коммитить `*.pck`, `.godot/`, `user://` — в .gitignore.

## Тесты
`godot -- --walltest|vmtest|hudtest|sndtest|tptest|loop --headless`
Каждый тест пишет PNG в `--shots ./shots`.

## Профилирование
`Debug → Profiler`, `Performance → Physics 3D`, `Rendering → Draw Calls`.
Логи FPS уже в `match.gd:_auto_shots` → `G.log_line("fps ...")`.
