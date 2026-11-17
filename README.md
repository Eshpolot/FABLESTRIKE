# FABLE STRIKE 2 — аудит и улучшения

Проект внутри: `FABLE_STRIKE_2_для_подписчиков/3_сутки/исходники/` (Godot 4.6.2)

## Документы аудита (ветка arena/8efbc4c4-fablestrike)

- **[AUDIT.md](AUDIT.md)** — полный разбор 10 систем, 24 файлов, 9000 строк. Пофайлово: что хорошо, что болит, баги, перфоманс.
- **[ROADMAP.md](ROADMAP.md)** — дорожная карта P0→P6 (гигиена → сеть). С оценкой дней и метриками.
- **[FIXES_APPLIED.md](FIXES_APPLIED.md)** — уже внесённые безопасные патчи (7 шт).

## Быстрый старт

```bash
# Открыть в Godot 4.6.2
godot --path "FABLE_STRIKE_2_для_подписчиков/3_сутки/исходники" .

# Тесты (headless)
godot -- --walltest --headless --quit
godot -- --sndtest --headless --quit
godot -- --auto --maxtime 60  # 60с автобоя, логи FPS
```

## Внесённые фиксы (P0)

- шаред-материал оружия → duplicate()
- валидация DB.RAR_ODDS
- _headroom луч → капсула
- die(front) при нулевой дистанции
- граната mask 1|2
- reports чистка по времени
- .gitignore

Следующий шаг — P1: разбить match.gd 1060→300 строк (см. ROADMAP.md).
