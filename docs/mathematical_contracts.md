# Математические контракты v0.2.2

## Изменения v0.2.2

`rule_data.load_rule_data/validate_all` загружают versioned package resources,
проверяют SHA256/schema/domain и возвращают caller-owned copies. Повреждения —
RuleDataError, никакого численного fallback. Software version не заменяет rule version.

`position_modifier(native_positions,slot)` — EXACT fraction либо NOT_APPLICABLE
для GK/outfield. Native позиции игроков: одна/две изGK/LD/CD/RD/LM/CM/RM/LF/CF/RF,
совмещения только опубликованные. DM/AM/... — tactical slots, не native profiles.
`style_position_category` отдельно возвращает category/categories и численный UNKNOWN.

`ability_definition/catalog` —21 источников/условий; `ability_lookup` выбирает
изолированный numeric parameter по level1–4, style/age/category/vector index.
Результаты moment/fatigue/economic имеют отдельные units/scopes. `ability_components`
не вычисляет суммарную силу. `captain_coefficient/contribution`,
`donor_contributions`, `penalty_bonus`, `idol_attendance`, `commercial_ticket_price`
реализуют применимые отдельные зависимости; комбинирование всех эффектов UNKNOWN.
Реальные bases требуют explicit strength_basis_verified. Collector realStrength
не подставляется автоматически. Ka не сводится к обычной возрастной формуле.

`weather_strength(player_style,nominal_strength,weather,temperature_c)` —
EXACT displayed strength_points, не multiplier; style означает любимый стиль
игрока. Неподдерживаемая strength/weather/temp либо normal дают UNKNOWN;
неизвестные названия и некорректные численные типы отклоняются.
`cohesion_bonus(ids,history,history_complete=False)` — latest-first same-season
competitive participants; точная сумма, conservative trailing bounds или UNKNOWN.

`evaluate_player` возвращает PlayerEvaluation с компонентами и UNKNOWN full force.
Partial estimate — явная legacy-product гипотеза. `optimize_lineups` теперь
принимает mode/context/incumbents, сохраняет неизвестных игроков и источники.
Стилевые интервалы не заменяются midpoint. Три режима описаны в pipeline.
Отсутствие captain base даёт UNKNOWN candidate, не пропуск игроков с Ка.

API изменения: form75–125; native special profiles вроде('DM',) отклоняются.
`Player.specials_known` различает отсутствующий экспорт и подтверждённый список.
Bare collector code нормализуется в level1; core tokens остаются явными code1–4.
`included_age_captain_bonus` может быть null; капитан возвращается только по
отдельному подтверждённому компоненту. `partial_total` остаётся условным subtotal,
при bounded/unknown core inputs — null. Legacy baseline_strength возвращает
None при неизвестном стиле, но eligibility больше не зависит от этого ответа.
Transfer legacy numeric partial delta сопровождается typed ESTIMATED/UNKNOWN;
полная economic_value всегда UNKNOWN. До full order нет официальной общей силы.

Ниже сохранены контракты v0.2.1, кроме явно переопределённых пунктов выше.

`CalculationResult` — неизменяемый dataclass, `ResultStatus` — строковый enum.
`to_dict()` выдаёт JSON-совместимый объект. Численного приведения нет.

| status | Числовые поля | Значение |
|---|---|---|
| EXACT | value | Определённый компонент при заданных достоверных входах |
| BOUNDED | lower, upper; value=null | Достоверные границы, без распределения вероятностей |
| ESTIMATED | value | Явно обозначенная оценка модели |
| UNKNOWN | все null | Недостаточно данных или нулевой знаменатель |
| NOT_APPLICABLE | все null | Правило не применяется |

Результат содержит `unit`, `source`, `reason`. Неупорядоченные границы,
NaN/Infinity, числа в UNKNOWN/NOT_APPLICABLE и смешение точки с интервалом
отклоняются. Совпадающие границы нормализуются в EXACT. EXACT относится к
изолированному компоненту, а не к силе скрытого генератора VFL.

## Полезность и минуты

Источник: https://www.vfliga.com/rules.php?page=70, версия 14.0, §2–3.
`u = floor(100*m/M + 1/2)`. Используется точная рациональная арифметика;
дробное представление не проходит через двоичный float. Прямой процент
в `round_usefulness`, `youth_growth` и `veteran_useful` переводится из его
десятичного строкового представления. Полезность не ограничена 100%.

`usefulness(m,M)` возвращает EXACT в целых процентах либо UNKNOWN при
отсутствии числителя/знаменателя и M=0. Отрицательные, дробные минуты,
NaN/Infinity и bool — ошибки валидации. Целые значения вида 90.0 допустимы.
Входные минуты должны уже соответствовать правилам: официальные игры,
игрок — со всеми клубами/сборными и добавочным временем; знаменатель —
клуб владельца на конец сезона, 90/120 минут без добавочного времени.

Для целого порога T и M>0:
`target = max(0, ceil((T - 0.5)*M/100))`, `required=max(0,target-m)`.
Расчёт точен относительно сценария M; точность арифметики не подтверждает
календарь. `future_official_team_minutes=null` сохраняет неизвестную цель.
`per_player_feasible=null` по умолчанию. Переданный
`available_future_player_minutes` позволяет сравнить required с бюджетом;
результат остаётся условным на достоверность этого бюджета.

## Изученность и взаимопонимание

Источник: https://vfliga.com/rules.php?page=40, версия 19.2, §2.10–2.12.
Процент изученности: null=данные отсутствуют, 0=не изучен,
20/40/60/80=частично изучен, 100 вместе с названием=полностью известен.
`Player.style_knowledge` возвращает MISSING, UNKNOWN, PARTIALLY_STUDIED
или FULLY_KNOWN. 100 без названия не определяет идентичность стиля.

`favorite_style_verified=True` — отдельное явное утверждение вызывающей
стороны о достоверном реальном стиле, независимо от процента изученности.
Оно нужно, например, для SYNTHETIC вектора с заданным истинным same_style
при изученности 20%. Адаптер никогда не выводит этот флаг из текста.

`line_chemistry(receiver,other)` возвращает CalculationResult. При полной
информации: одинаковый стиль — 0.125*study_other/100; коллизия — -0.05;
иначе 0. Одинаковая известная национальность устанавливает нижний предел
0.05. Неполная идентичность стиля допускает шесть опубликованных стилей;
отсутствующий процент допускает опубликованные 0/20/.../100. Неизвестная
национальность допускает одинаковую и разную национальности. Min/max этих
возможностей образуют консервативный интервал, а не среднее.

Примеры: одинаковая национальность и неизвестные стили [0.05,0.125];
разная национальность, неизвестная изученность [-0.05,0.125]; сосед
точно не изучен и национальности разные [-0.05,0]. Оба конца с полностью
известным одинаковым стилем: 0.125. None и `is_league_player=True` на любом
конце дают EXACT(0), сохраняя линию в числе связей.

`chemistry_for_player` возвращает `(CalculationResult, uncertain_line_count)`.
Границы усредняются с учётом всех линий; без линий — NOT_APPLICABLE.
Сумма границ нескольких связей консервативна: совместная достижимость
экстремумов и зависимость скрытых стилей не гарантируются.

## Потребители и совместимость

- `style_effect` теперь возвращает CalculationResult вместо `(float,bool)`.
  Неизвестный стиль не заменяется множителем 1. `baseline_strength` выдаёт
  None и предупреждение; игрок не допускается к численной оптимизации этого
  стиля. Нормальный стиль и игрок от Лиги имеют точный стилевой множитель 1.
- `line_chemistry`: число/None заменены CalculationResult. Все потребители
  обновлены. Старые вызовы обязаны проверить status перед чтением value.
- Поля `current_pct`/`projected_pct_no_more_play` теперь округлённые целые,
  при неизвестности null. Добавлены структурированные результаты и сценарий.
- В составе при BOUNDED-взаимопонимании `partial_total` и
  `included_chemistry_bonus` равны null. Границы сохраняются отдельно.
  `ranking_score` — явно обозначенный ESTIMATED subtotal известных
  компонентов, для сохранения прежней эвристики, не midpoint интервала.
- Без геометрии `chemistry_bonus_result=UNKNOWN`, численный partial subtotal
  сохраняет прежний контракт с предупреждением об исключённой механике.
- Decision/Transfer при null partial_total возвращают
  `abstain_uncertain_lineup_strength`, без рекомендации/численной прибавки.
- Возраст Player, капитана и сезонного расчёта — целое 16–34. Недопустимые
  значения отклоняются. Ка и база реальной позиционной силы остаются backlog.
