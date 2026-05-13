# 🥊 UFC Predictor — V4 vs V5 Results

_Generated: 2026-05-12 12:13_


## 📊 Aggregate Summary

| Version | Events | Fights Graded | Correct | Accuracy | Brier |
|---|---:|---:|---:|---:|---:|
| **V4** (10 lessons, baseline) | 14 | 176 | 107 | **60.8%** | 0.225 |
| **V5** (20 lessons + motivation) | 15 | 189 | 121 | **64.0%** | 0.214 |
| **Δ** | — | — | — | **+3.2pp** | **-0.010** |

## 📋 Per-Event Comparison

| Date | Event | V4 Acc | V5 Acc | Δ | V4 Brier | V5 Brier |
|---|---|---:|---:|---:|---:|---:|
| 2026-01-24 | UFC 324: Gaethje vs. Pimblett | 72.7% | 81.8% | 🟢 +9.1pp | 0.179 | 0.121 |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | 38.5% | 61.5% | 🟢 +23.1pp | 0.258 | 0.225 |
| 2026-02-07 | UFC Fight Night: Bautista vs. Oliveira | 53.8% | 46.2% | 🔴 -7.7pp | 0.277 | 0.237 |
| 2026-02-21 | UFC Fight Night: Strickland vs. Hernandez | 71.4% | 78.6% | 🟢 +7.1pp | 0.195 | 0.155 |
| 2026-02-28 | UFC Fight Night: Moreno vs. Kavanagh | 46.2% | 84.6% | 🟢 +38.5pp | 0.245 | 0.162 |
| 2026-03-07 | UFC 326: Holloway vs. Oliveira 2 | 75.0% | 50.0% | 🔴 -25.0pp | 0.186 | 0.263 |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallejos | 78.6% | 57.1% | 🔴 -21.4pp | 0.167 | 0.244 |
| 2026-03-21 | UFC Fight Night: Evloev vs. Murphy | 76.9% | 69.2% | 🔴 -7.7pp | 0.192 | 0.171 |
| 2026-03-28 | UFC Fight Night: Adesanya vs. Pyfer | 50.0% | 58.3% | 🟢 +8.3pp | 0.239 | 0.246 |
| 2026-04-04 | UFC Fight Night: Moicano vs. Duncan | 69.2% | 46.2% | 🔴 -23.1pp | 0.206 | 0.257 |
| 2026-04-11 | UFC 327: Procházka vs. Ulberg | 45.5% | 54.5% | 🟢 +9.1pp | 0.284 | 0.262 |
| 2026-04-18 | UFC Fight Night: Burns vs. Malott | 45.5% | 45.5% | +0.0pp | 0.255 | 0.270 |
| 2026-04-25 | UFC Fight Night: Sterling vs. Zalal | 61.5% | 69.2% | 🟢 +7.7pp | 0.238 | 0.211 |
| 2026-05-02 | UFC Fight Night: Della Maddalena vs. Prates | — | 92.3% | — | — | 0.151 |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | 61.5% | 61.5% | +0.0pp | 0.238 | 0.250 |

## 📖 Lessons Library (20 active)

**1. Антропометрия + KO power > раздутый рекорд против слабой оппозиции**
  _src: manual_  
  Если у бойца A reach/height/power значительно выше, а у B рекорд набит против низко-ранкованной оппозиции — A фаворит вопреки рекорду B. Признаки 'раздутого рекорда': все победы по решению, или нокаут…

**2. Старый ветеран (35+) с хрустальной челюстью vs молодой нокаутёр-проспект**
  _src: manual_  
  Если фаворит 33+, имеет ≥2 KO/TKO поражений в карьере или ≥1 KO поражение за последние 3 боя — его 'chin' деградирует. Молодой (<29) нокаутёр-проспект на восхождении против такого ветерана = сильная с…

**3. Home-country judge bias: бои в Австралии/UK/Бразилии**
  _src: manual_  
  Если бой проходит в Австралии (Perth/Sydney) → австралийцы получают примерно +5-10% к шансу на decision в близких боях. Те же правила: UK для англичан, Бразилия для бразильцев. Это НЕ повод флипать пр…

**4. Pure finisher (high finish rate) vs decision-fighter**
  _src: manual_  
  Если у одного бойца finish rate >70%, а у другого только decisions — finisher выигрывает 'fight IQ' матчей: один good punch меняет всё. Не ставь decision-prop в такой матчап. Если favourite-decision f…

**5. Неизвестный дебютант: не угадывай 50/50**
  _src: manual_  
  Если у бойца меньше 2 боёв в UFC и нет публичных данных о его стиле — НЕ давай уверенность выше 55%. В таких случаях явно пиши 'недостаточно данных' и ставь win_prob 0.50-0.55. Brier штрафует overconf…

**6. Падающий heavyweight-ветеран с серией KO-losses**
  _src: manual:post_v2_blindtest_  
  Tuivasa-pattern: heavy hitter, который ВЫГЛЯДИТ как нокаутёр но проиграл 3+ боя подряд KO/TKO. Чин и кардио убиты, момент уже ушёл. Молодой соперник с любым приличным выстрелом — фаворит. Если ветеран…

**7. Heavyweight с большим reach-disadvantage = glass chin trigger**
  _src: manual:post_v2_blindtest_  
  В тяжёлом весе reach + footwork решают часто больше чем сила. Если у фаворита (по имени) reach-disadvantage 4+ см и нет wrestling-base — он будет ловить контру весь бой. Не overconfident. Гейзиев/Перш…

**8. Старый Flyweight/BW (33+) в дивизионе скоростников**
  _src: manual:post_v2_blindtest_  
  В лёгких весах (FLY, BW, FW) скорость декаит к 32+ резче чем в средних. Tim Elliott / Meerschaert / Gorimbo патерны: ветеран 33+ против активного молодого скоростника = чаще проигрывает по очкам через…

**9. ‘Имя > форма’ ловушка: BMF/legend status overrides последние 3 боя**
  _src: manual:post_v2_blindtest_  
  Если у бойца ‘имя’ (звезда UFC, чемпион в прошлом, BMF), модель часто ставит его фаворитом ИГНОРИРУЯ последние 3 боя. Это самая частая ошибка. Правило: ВСЕГДА смотри последние 3 боя — если 2+ losses, …

**10. Calibration cap: не выходи за 65% без RAG-данных**
  _src: manual:post_v2_blindtest_  
  Если у тебя нет полных метрик бойцов (SLpM/TDAvg/etc), максимальная уверенность которую ты имеешь право выдать — 65%. Меньше уверенность → меньше Brier penalty при ошибке. Лучше быть систематически un…

**11. Не недооценивайте влияние сабмишенов у бойцов с низким SLpM**
  _src: auto_extracted_v1_  
  Бойцы с небольшим количеством ударов в минуту часто выигрывают за счёт высокого SubAvg, но модель часто предсказывает решение. При низком SLpM проверяйте SubAvg и TDDef; если они высоки, повышайте вер…

**12. Проверяйте дисбаланс в точности ударов при схожих SLpM**
  _src: auto_extracted_v1_  
  Когда два бойца имеют похожий SLpM, модель часто выбирает победителя по другим признакам, игнорируя разницу в StrAcc. Высокая точность может компенсировать меньший объём ударов, поэтому при схожем тем…

**13. Не полагайтесь только на общий win‑rate без контекста уровня оппонентов**
  _src: auto_extracted_v1_  
  Бойцы с высоким общим рекордом часто получают преимущество, но если их победы получены против низкоранжированных соперников, модель ошибается. При оценке win‑rate учитывайте средний рейтинг оппонентов…

**14. Остерегайтесь переоценки «домашних» фаворитов без статистики**
  _src: auto_extracted_v1_  
  Модель часто повышает шансы бойцов, выступающих в своей стране, даже если их статистика не подтверждает преимущество. При наличии домашнего преимущества проверяйте объективные метрики (ELO, StrAcc, TD…

**15. Не игнорируйте недавние KO‑losses у ветеранов**
  _src: auto_extracted_v1_  
  Ветераны старше 35 лет часто получают штраф в виде «хрустящей челюсти», но модель иногда пропускает их недавние KO‑losses, полагая, что опыт компенсирует. При оценке ветеранов проверяйте их последние …

**16. Учитывайте стиль борьбы при большом разнице в росте**
  _src: auto_extracted_v1_  
  Большой рост и размах дают преимущество в стойке, но если у более короткого соперника высокий TDAvg и SubAvg, модель часто ошибается, полагая, что размах решает бой. При значительном разнице в росте п…

**17. Не переоценивайте темп ударов без учёта защиты**
  _src: auto_extracted_v1_  
  Если один боец имеет значительно выше SLpM, но его StrDef ниже среднего, модель часто считает его фаворитом, игнорируя риск контратак. При высокой ударной активности проверяйте защитные показатели (St…

**18. Пост-loss-belt мотивация: бывший чемпион чаще проигрывает следующий бой**
  _src: manual_user_insight_  
  Бойцы, потерявшие пояс, в следующем бою проигрывают значительно чаще статистики. Кейсы: Leon Edwards (loss to Muhammad → loss next), Belal Muhammad (loss to JDM → loss next), Volkanovski (loss to Topu…

**19. Голодный challenger vs decline-чемпион**
  _src: manual_user_insight_  
  Когда молодой претендент (25-30 лет) идёт на восходящей форме (3+ wins подряд, KO/finish rate >50%) против стареющего чемпиона/бывшего чемпиона (33+ лет, признаки декая в ударной активности), претенде…

**20. Striker с реальной KO-силой бьёт TD-favourite-а**
  _src: manual_  
  Когда боец имеет реальную KO-power background (бывший кикбоксер/боксёр-чемпион, либо UFC-record с 70%+ KO-rate), его шансы на финиш ВЫШЕ чем показывает простой strike comparison. TD-defense оппонента …


## ❌ Top V5 Overconfident Misses

| Date | Event | Predicted | Conf | Actual |
|---|---|---|---:|---|
| 2026-04-18 | UFC Fight Night: Burns vs. Malott | Mandel Nallo | 73% | Jai Herbert |
| 2026-02-28 | UFC Fight Night: Moreno vs. Kavanag | Brandon Moreno | 72% | Lone'er Kavanagh |
| 2026-03-28 | UFC Fight Night: Adesanya vs. Pyfer | Ignacio Bahamondes | 72% | Tofiq Musayev |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | Khamzat Chimaev | 72% | Sean Strickland |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | Sangwook Kim | 68% | Dom Mar Fan |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | Benoît Saint‑Denis | 68% | Benoît Saint Denis |
| 2026-02-21 | UFC Fight Night: Strickland vs. Her | Yadier del Valle | 68% | Jordan Leavitt |
| 2026-03-07 | UFC 326: Holloway vs. Oliveira 2 | Rob Font | 68% | Raul Rosas Jr. |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallejo | Chris Curtis | 68% | Myktybek Orolbai |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallejo | Oumar Sy | 68% | Ion Cutelaba |
| 2026-03-14 | UFC Fight Night: Emmett vs. Vallejo | Amanda Lemos | 68% | Gillian Robertson |
| 2026-04-04 | UFC Fight Night: Moicano vs. Duncan | Azamat Bekoev | 68% | Tresean Gore |
| 2026-04-11 | UFC 327: Procházka vs. Ulberg | Francisco Prado | 68% | Charles Radtke |
| 2026-04-11 | UFC 327: Procházka vs. Ulberg | Patricio Pitbull | 68% | Aaron Pico |
| 2026-04-18 | UFC Fight Night: Burns vs. Malott | Gökhan Sariçam | 68% | Gokhan Saricam |
| 2026-04-25 | UFC Fight Night: Sterling vs. Zalal | Adrian Luna Martinetti | 68% | Davey Grant |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | William Gomis | 68% | Pat Sabatini |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | Jared Gordon | 68% | Jim Miller |
| 2026-05-09 | UFC 328: Chimaev vs. Strickland | Joaquin Buckley | 68% | Sean Brady |
| 2026-01-31 | UFC 325: Volkanovski vs. Lopes 2 | Torrez Finney | 66% | Jacob Malkoun |