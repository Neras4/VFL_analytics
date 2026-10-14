# VFL Analytics Engine v0.2.3

Расширяемое математическое ядро VFL с явной неопределённостью. Использует
опубликованные таблицы и проверенные отдельные компоненты; полная сила
закрытого генератора и вероятности исхода матча не воспроизводятся.

## Установка и запуск

Python 3.11 или 3.12. Зависимости закреплены; CI устанавливает проект из
pyproject.toml и выполняет тесты, проверку таблиц/JSON и benchmark.

```bash
python -m venv .venv
# Активируйте .venv или используйте её интерпретатор явно.
python -m pip install -c requirements-lock.txt -e '.[test]'
python -m pytest -q -p no:cacheprovider
python -m vfl_analytics.rule_data
python -m vfl_analytics.cli examples/evaluate_player.json
python benchmarks/optimizer.py
```

Windows PowerShell: вместо python используйте `.\.venv\Scripts\python.exe`.
Linux/macOS: `.venv/bin/python`. Расчёты и CI работают офлайн, без VFL login.

## Возможности

| CLI action | Результат | Достоверность |
|---|---|---|
| position | Профиль/совмещение/непрофильная/специальная позиция | EXACT отдельный коэффициент; категория командного стиля отдельно |
| weather | Любимый стиль игрока, номинальная сила, погода/температура | EXACT опубликованная ячейка или UNKNOWN неподдерживаемый вход |
| ability / catalog | Все21 спецвозможностей, уровни1–4, параметры и условия | Отдельные коэффициенты; разные фазы, без общей суммы силы |
| captain | Возраст/Ка, сила на позиции и средняя сила | EXACT при подтверждённых реальных базах, иначе UNKNOWN |
| cohesion | История участников последних нетоварищеских игр | EXACT или BOUNDED/UNKNOWN при неполной истории |
| evaluate_player | PlayerEvaluation со всеми компонентами | ESTIMATED/BOUNDED partial, UNKNOWN full force |
| lineup | Быстрый поиск и сравнение кандидатов | Эвристика; known_components / conservative / pareto |
| transfer | Сохранение прежнего состава, сравнимый search delta | ESTIMATED известной части; UNKNOWN полный эффект/ROI |
| adapt | Контракт Assistant0.5.11, joins и null-семантика | OBSERVED structural fixtures; 21 own + 27 opponent приняты без потерь |
| opponent / strategy | Прежняя модель стилей и явные collision scenarios | Непроверенные статистические предположения |
| collision / usefulness | Направление коллизии и сезонные границы минут | Опубликованные отдельные правила |
| validate_rules | SHA256, версии, структуры упакованных таблиц | Офлайн-проверка целостности |

Примеры: `examples/position.json`, `weather.json`, `ability.json`, `captain.json`,
`cohesion.json`, `evaluate_player.json`, `lineup.json`, `strategy.json`, `transfer.json`.
Все игровые входы в примерах SYNTHETIC.

## Контракты и ограничения

EXACT, BOUNDED, ESTIMATED, UNKNOWN, NOT_APPLICABLE сохраняются через Python API
и CLI JSON. Неизвестное значение не становится нулём, единицей или midpoint.
Неизвестный стиль/форма не исключают законного игрока: для поиска используется
явный proxy; окончательная сила остаётся неопределённой. Captain/И/Л требуют
отдельно подтверждённых реальных сил на назначенных позициях. `realStrength`
из коллектора не является автоматической заменой этих баз.

Позиционное соответствие и цвет командного стиля — разные компоненты.
Взаимопонимание и история сыгранности — разные компоненты. Погода использует
**любимый стиль игрока**, а не выбранный командный стиль, и возвращает силу,
а не процентный множитель. Native table не содержит нормального стиля.

21 спецвозможность доступна в каталоге и через изолированные selectors;
моментные, экономические, вероятностные и fatigue-эффекты не складываются
в prematch strength. Полный порядок всех модификаторов неизвестен.
`partial_total`/`ranking_score` — условная модель, не официальная реальная сила.
Pareto и lower-bound режимы относятся к этой модели. Глобальный нелинейный
оптимум и окончательная рекомендация не заявляются.

Normal/Deep Assistant 0.5.11 проверены на девяти локальных снимках от 14.10.2026.
Это проверка импорта и отдельных компонентов; историческое сопоставление с генератором не выполнено.
VFL Assistant не изменён; модель не входит на сайт, не отправляет составы
и не выполняет трансферы.

## Проверка источников

Research manifest проверен:30/30. Все21 таблицы спецвозможностей сверены с
официальным page64:385 числовых ячеек. Погодные таблицы двух школ сверены
полностью:19488 ячеек, представляющих58464 логических ячейки шести стилей.
Таблицы упакованы с provenance, версиями и SHA256; большая погода сжата gzip
и загружается через cache. Цветная позиционная матрица остаётся качественной.

Источники: [позиции](https://vfliga.com/rules.php?page=159),
[спецвозможности](https://vfliga.com/rules.php?page=64),
[управление](https://vfliga.com/rules.php?page=40),
[сыгранность](https://vfliga.com/rules.php?page=167),
[погода](https://vfliga.com/weather.php),
[сезон](https://vfliga.com/rules.php?page=70).

## Документация

- [Изменения и checkpoints](docs/v0.2.2_changes.md)
- [Покрытие правил](docs/rule_coverage.md)
- [Pipeline и ranking modes](docs/calculation_pipeline.md)
- [Математические API](docs/mathematical_contracts.md)
- [Контракт Assistant и пробелы](docs/data_gaps.md)
- [Ограничения](docs/known_limitations.md)
- [План v0.2.3](docs/v0.2.3_backlog.md)
- [Проверенные числовые ячейки источников](docs/source_verification.json)
- [Benchmark](benchmarks/results_v0.2.2.json)

SPEC_RU.md и v0.2.1 baseline сохраняют исторический контекст, а актуальный
rules_registry.json и package data отражают реализованные v0.2.2 компоненты.

## Реальные выгрузки v0.2.3 Phase 1

Исходные JSON храните в исключённом из Git `local_data/kariari/`.
Воспроизводимый офлайн-анализ (подробный результат содержит приватные данные):

```bash
python -m vfl_analytics.local_validation local_data/kariari --output local_data/reports/v0.2.3 --detailed
```

Выход: `validation.json`, `inventory.md`; консоль содержит только агрегаты.
CLI `merge_snapshots` принимает массив team snapshots и сохраняет provenance;
`adapt_market` проверяет отдельный market/bids snapshot, без модели полезности.
Пары Normal/Deep объединяются по времени и ID, club sections не теряются.
Снимки заявок остаются независимыми наблюдениями.

[Инвентаризация](docs/validation/kariari_inventory.md),
[адаптер](docs/validation/kariari_adapter_report.md),
[правила](docs/validation/kariari_rules_report.md),
[составы](docs/validation/kariari_lineup_report.md),
[рынок и заявки](docs/validation/market_bids_report.md),
[пробелы](docs/validation/kariari_data_gaps.md),
[изменения Phase 1](docs/v0.2.3_phase1_changes.md).

Review D–F: all seven team styles, source-aware opponent fatigue, completed scouting,
lineup explanations and isolated kind/ID/season groups are supported. Use
`--team-id 13202` to filter (repeat for several IDs), `--detailed` for player and
alternative calculations, `--raw-diagnostics` only for private debugging. Output
must be inside this project's real `local_data/` tree. See
[review fixes](docs/validation/phase1_review_fixes.md).
