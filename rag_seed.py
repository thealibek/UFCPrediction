"""Сид-данные для RAG knowledge base: исторические бои UFC с разбором.

Используется при первой инициализации ChromaDB. Содержит ~25 громких боёв
с конкретными уроками — стилевыми, физическими, психологическими.
"""

HISTORICAL_FIGHTS = [
    {
        "id": "topuria_volkanovski_1",
        "fighter_a": "Ilia Topuria", "fighter_b": "Alexander Volkanovski",
        "event": "UFC 298", "date": "2024-02-17",
        "weight_class": "Featherweight",
        "winner": "Ilia Topuria",
        "method": "KO (punches)", "round": 2,
        "notes": "Topuria выключил Волка правым прямым после перехвата комбинации. "
                 "Волк поплыл от первого чистого попадания — признак того что чемпион "
                 "переехал в активность ниже 145lb после двух тяжёлых лосов на 155.",
        "stylistic_lessons": "Boxer-puncher с тяжёлой рукой против быстрого волюм-страйкера: "
                             "достаточно одного чистого удара, если у соперника просел подбородок. "
                             "Возраст 35+ + двойной weight cut = красные флаги.",
    },
    {
        "id": "makhachev_volkanovski_2",
        "fighter_a": "Islam Makhachev", "fighter_b": "Alexander Volkanovski",
        "event": "UFC 294", "date": "2023-10-21",
        "weight_class": "Lightweight",
        "winner": "Islam Makhachev",
        "method": "KO (head kick + punches)", "round": 1,
        "notes": "Хайкик в первом раунде. Volkanovski принял бой за 11 дней — без полного кэмпа. "
                 "Первый бой шёл 5 раундов вничью на ногах. Размерное преимущество Ислама решило.",
        "stylistic_lessons": "Short-notice replacement против действующего чемпиона = почти всегда минус. "
                             "Размер и reach в борьбе UFC решают сильнее чем техника.",
    },
    {
        "id": "strickland_adesanya",
        "fighter_a": "Sean Strickland", "fighter_b": "Israel Adesanya",
        "event": "UFC 293", "date": "2023-09-09",
        "weight_class": "Middleweight",
        "winner": "Sean Strickland",
        "method": "Decision (unanimous)", "round": 5,
        "notes": "Шок-апсет. Strickland задавил Adesanya плотным jab+pressure боксом. "
                 "Сбил его в первом раунде, забрал темп. Изи (Адесанья) выглядел демотивированным "
                 "после потери титула Pereira. Долгая инактивность не на пользу.",
        "stylistic_lessons": "Pressure-boxer-southpaw с iron chin против counter-striker: "
                             "первый сбой ритма у counter-striker = потеря всего боя. "
                             "Большие фавориты после поражения часто проседают мотивационно.",
    },
    {
        "id": "pereira_adesanya_2",
        "fighter_a": "Alex Pereira", "fighter_b": "Israel Adesanya",
        "event": "UFC 287", "date": "2023-04-08",
        "weight_class": "Middleweight",
        "winner": "Israel Adesanya",
        "method": "KO (punches)", "round": 2,
        "notes": "Реванш. Adesanya дождался ошибки Pereira во 2 раунде, поймал на отходе и "
                 "выключил серией справа. Подтвердил реверсию matchup при правильной тактике.",
        "stylistic_lessons": "Реванш против сильного фаворита часто работает: проигравший делает "
                             "конкретные тактические правки, фаворит самоуспокаивается.",
    },
    {
        "id": "pereira_adesanya_1",
        "fighter_a": "Alex Pereira", "fighter_b": "Israel Adesanya",
        "event": "UFC 281", "date": "2022-11-12",
        "weight_class": "Middleweight",
        "winner": "Alex Pereira",
        "method": "TKO (punches)", "round": 5,
        "notes": "Pereira отыгрался в 5 раунде после проигрыша по очкам. Жёсткие лефт-хуки "
                 "по чемпиону. Подтвердил кикбоксерское превосходство (3-0 в кикбоксинге vs Изи).",
        "stylistic_lessons": "Если у бойца есть прошлая история побед в кикбоксинге над соперником, "
                             "это сильный сигнал — мышечная память работает в стенд-апе.",
    },
    {
        "id": "khabib_mcgregor",
        "fighter_a": "Khabib Nurmagomedov", "fighter_b": "Conor McGregor",
        "event": "UFC 229", "date": "2018-10-06",
        "weight_class": "Lightweight",
        "winner": "Khabib Nurmagomedov",
        "method": "Submission (neck crank)", "round": 4,
        "notes": "Doг и пони шоу для McGregor — Khabib ground-and-pound, с минимальной угрозой "
                 "снизу. Cardio преимущество огромное. McGregor долгая инактивность 2 года.",
        "stylistic_lessons": "Wrestler-grappler с элитным top control против striker без TDD = "
                             "почти всегда minus. Долгий лэйоф у striker критичен.",
    },
    {
        "id": "chimaev_burns",
        "fighter_a": "Khamzat Chimaev", "fighter_b": "Gilbert Burns",
        "event": "UFC 273", "date": "2022-04-09",
        "weight_class": "Welterweight",
        "winner": "Khamzat Chimaev",
        "method": "Decision (unanimous)", "round": 3,
        "notes": "Лучший бой 2022 года. Chimaev выиграл по очкам, но Burns единственный довёл "
                 "его до 3-го раунда. Чимаев физически сдулся к 3-му — кардио на дистанции "
                 "сомнительно. Burns пробил его несколько раз чисто.",
        "stylistic_lessons": "Chimaev'у нельзя давать 3-й раунд против элитных борцов. "
                             "Если соперник переживает первые 10 минут под давлением — "
                             "появляется реальное окно.",
    },
    {
        "id": "jones_reyes",
        "fighter_a": "Jon Jones", "fighter_b": "Dominick Reyes",
        "event": "UFC 247", "date": "2020-02-08",
        "weight_class": "Light Heavyweight",
        "winner": "Jon Jones",
        "method": "Decision (unanimous)", "round": 5,
        "notes": "Близкий бой. Reyes выиграл первые 2-3 раунда чистым боксом и движением. "
                 "Jon Jones включил клинч и тейкдауны во 2-й половине. Спорные карточки судей.",
        "stylistic_lessons": "Athletic southpaw striker может проблемить даже элитного "
                             "GOAT'а в первой половине — но cardio + grappling решает в late rounds.",
    },
    {
        "id": "usman_edwards_2",
        "fighter_a": "Leon Edwards", "fighter_b": "Kamaru Usman",
        "event": "UFC 278", "date": "2022-08-20",
        "weight_class": "Welterweight",
        "winner": "Leon Edwards",
        "method": "KO (head kick)", "round": 5,
        "notes": "Один из самых драматичных финишей в истории. Edwards проигрывал "
                 "4 раунда подряд, был биткой по очкам. Хайкик за минуту до конца — "
                 "Usman потерял сознание стоя. Усмен переключился в авто-пилот.",
        "stylistic_lessons": "Lead-leg kick от southpaw в late rounds = классическая ловушка. "
                             "Wrestler-доминаторам опасно расслабляться, когда они уже выиграли.",
    },
    {
        "id": "edwards_usman_3",
        "fighter_a": "Kamaru Usman", "fighter_b": "Leon Edwards",
        "event": "UFC 286", "date": "2023-03-18",
        "weight_class": "Welterweight",
        "winner": "Leon Edwards",
        "method": "Decision (majority)", "round": 5,
        "notes": "Edwards подтвердил победу в реванше. Usman не смог адаптировать стратегию, "
                 "Edwards держал дистанцию и точно работал каунтерами. Цикл WW сменился.",
        "stylistic_lessons": "После трамирующего KO даже элитные wrestler'ы теряют агрессию "
                             "в шуте — психологический эффект сохраняется надолго.",
    },
    {
        "id": "holloway_volkanovski_3",
        "fighter_a": "Alexander Volkanovski", "fighter_b": "Max Holloway",
        "event": "UFC 276", "date": "2022-07-02",
        "weight_class": "Featherweight",
        "winner": "Alexander Volkanovski",
        "method": "Decision (unanimous)", "round": 5,
        "notes": "Третий бой. Volk доминировал чище чем в первых двух. Holloway узнал "
                 "что выше его уровень не пробить, плотность и кардио Волка элитные.",
        "stylistic_lessons": "Когда trilogy: третий бой обычно самый чистый — оба знают друг друга, "
                             "и доминирует тот у кого больше технических инструментов.",
    },
    {
        "id": "holloway_gaethje",
        "fighter_a": "Max Holloway", "fighter_b": "Justin Gaethje",
        "event": "UFC 300", "date": "2024-04-13",
        "weight_class": "Lightweight",
        "winner": "Max Holloway",
        "method": "KO (punches)", "round": 5,
        "notes": "BMF title. Holloway указал часами на 10 секунд до конца, разменялся "
                 "стоя посреди ринга и нокаутировал Gaethje прямым. Один из величайших "
                 "моментов истории UFC.",
        "stylistic_lessons": "Volume-striker с iron chin может ловить в обмене даже сильнейшего "
                             "хиттера, если тот соглашается на размен. Эго-ловушки работают.",
    },
    {
        "id": "oliveira_makhachev",
        "fighter_a": "Charles Oliveira", "fighter_b": "Islam Makhachev",
        "event": "UFC 280", "date": "2022-10-22",
        "weight_class": "Lightweight",
        "winner": "Islam Makhachev",
        "method": "Submission (arm-triangle)", "round": 2,
        "notes": "Ислам затейкдаунил Оливейру и закрыл arm-triangle во 2-м раунде. "
                 "Превосходство в борьбе абсолютное. Charles силен в шуте, но не против элиты "
                 "в дагестанской борьбе.",
        "stylistic_lessons": "BJJ black belt снизу не помогает против sambo grappler с top pressure. "
                             "Контроль позиции > субмишн скилл в современном MMA.",
    },
    {
        "id": "topuria_holloway",
        "fighter_a": "Ilia Topuria", "fighter_b": "Max Holloway",
        "event": "UFC 308", "date": "2024-10-26",
        "weight_class": "Featherweight",
        "winner": "Ilia Topuria",
        "method": "KO (punches)", "round": 3,
        "notes": "Topuria защитил титул жёстким нокаутом. Holloway выглядел медленнее "
                 "чем обычно — возможно эффект BMF битвы с Gaethje. Topuria прибил левым хуком.",
        "stylistic_lessons": "Boxer-puncher в фокусной форме vs volume-striker средней руки = "
                             "matchup для досрочки.",
    },
    {
        "id": "namajunas_zhang_1",
        "fighter_a": "Rose Namajunas", "fighter_b": "Zhang Weili",
        "event": "UFC 261", "date": "2021-04-24",
        "weight_class": "Strawweight",
        "winner": "Rose Namajunas",
        "method": "KO (head kick)", "round": 1,
        "notes": "Хайкик за 1:18 в первом раунде. Zhang переоценил свой пресс — Rose "
                 "поймала на отходе тайминг.",
        "stylistic_lessons": "Pressure fighter без head movement против technical striker "
                             "= риск head kick KO в первые минуты.",
    },
    {
        "id": "ngannou_gane",
        "fighter_a": "Francis Ngannou", "fighter_b": "Ciryl Gane",
        "event": "UFC 270", "date": "2022-01-22",
        "weight_class": "Heavyweight",
        "winner": "Francis Ngannou",
        "method": "Decision (unanimous)", "round": 5,
        "notes": "Ngannou шокировал планку — сбивал Gane всю вторую половину боя, несмотря на "
                 "повреждение колена. Wrestling от puncher'а никто не ждал.",
        "stylistic_lessons": "Никогда не недооценивай скрытый wrestling у power-puncher'а. "
                             "MMA-математ pre-fight игнорирует tactical adaptations.",
    },
    {
        "id": "diaz_mcgregor_1",
        "fighter_a": "Nate Diaz", "fighter_b": "Conor McGregor",
        "event": "UFC 196", "date": "2016-03-05",
        "weight_class": "Welterweight",
        "winner": "Nate Diaz",
        "method": "Submission (rear-naked choke)", "round": 2,
        "notes": "Diaz short-notice заменил Aldo. McGregor доминировал 1 раунд боксом, "
                 "сдулся в 2-м, попался на чёкер после серии его прямых.",
        "stylistic_lessons": "Конор всегда хрупок выше 145lb из-за cardio. Чем дальше от его "
                             "оптимального веса — тем выше шанс что соперник дотянет до сабмишена.",
    },
    {
        "id": "shevchenko_grasso_1",
        "fighter_a": "Alexa Grasso", "fighter_b": "Valentina Shevchenko",
        "event": "UFC 285", "date": "2023-03-04",
        "weight_class": "Flyweight",
        "winner": "Alexa Grasso",
        "method": "Submission (rear-naked choke)", "round": 4,
        "notes": "Шок-апсет. Shevchenko провалила спинку, Grasso закрыла чёкер. "
                 "Возрастной фактор + ригидная стратегия Шевченко = первое поражение за 6 лет.",
        "stylistic_lessons": "Долгие чемпионы (4+ защиты) часто становятся жертвой одной "
                             "технической ошибки — мышечная память на старых паттернах подвести.",
    },
    {
        "id": "poirier_mcgregor_2",
        "fighter_a": "Dustin Poirier", "fighter_b": "Conor McGregor",
        "event": "UFC 257", "date": "2021-01-23",
        "weight_class": "Lightweight",
        "winner": "Dustin Poirier",
        "method": "TKO (punches)", "round": 2,
        "notes": "Poirier разнёс Конору переднее бедро лоу-киками. Конор не смог двигаться, "
                 "сдался под pressure. Реванш через 7 лет после первой битвы на 145lb.",
        "stylistic_lessons": "Calf kicks за раунд могут уничтожить мобильность striker'а. "
                             "Возраст и инактивность ускоряют деградацию.",
    },
    {
        "id": "miocic_dc_3",
        "fighter_a": "Stipe Miocic", "fighter_b": "Daniel Cormier",
        "event": "UFC 252", "date": "2020-08-15",
        "weight_class": "Heavyweight",
        "winner": "Stipe Miocic",
        "method": "Decision (unanimous)", "round": 5,
        "notes": "Trilogy. Stipe выиграл 3-й бой работая по корпусу — DC ослаб. Все 3 боя "
                 "близкие, решающим был стиль, а не скилл.",
        "stylistic_lessons": "Body work — недооценённый инструмент в HW. Cardio в тяжёлом весе "
                             "проседает быстрее всего, body shots ускоряют это.",
    },
    {
        "id": "adesanya_du_plessis",
        "fighter_a": "Dricus du Plessis", "fighter_b": "Israel Adesanya",
        "event": "UFC 305", "date": "2024-08-17",
        "weight_class": "Middleweight",
        "winner": "Dricus du Plessis",
        "method": "Submission (face crank)", "round": 4,
        "notes": "DDP задушил Адесанью кранком после доминирующих позиций. Изи без grappling "
                 "ответа на жёсткий клинч-стиль южноафриканца.",
        "stylistic_lessons": "Pure striker с слабым GnD против physical wrestler с heart-rate "
                             "монстром = плохой matchup на 25 минут.",
    },
    {
        "id": "topuria_oliveira",
        "fighter_a": "Ilia Topuria", "fighter_b": "Charles Oliveira",
        "event": "UFC 317", "date": "2025-06-28",
        "weight_class": "Lightweight",
        "winner": "Ilia Topuria",
        "method": "KO (punches)", "round": 1,
        "notes": "Topuria переехал на 155, нокаутировал Оливейру в 1 раунде за чемпионский пояс. "
                 "Подтвердил статус P4P-элиты. Charles снова поплыл от первого чистого попадания.",
        "stylistic_lessons": "Topuria масштабируется на 155 без проблем — компактное тело, "
                             "элитный бокс. Иначе говоря: real power scales up, technique scales up.",
    },
    {
        "id": "pantoja_asakura",
        "fighter_a": "Alexandre Pantoja", "fighter_b": "Kai Asakura",
        "event": "UFC 310", "date": "2024-12-07",
        "weight_class": "Flyweight",
        "winner": "Alexandre Pantoja",
        "method": "Submission (rear-naked choke)", "round": 2,
        "notes": "Pantoja защитил пояс против дебютанта Asakura. Японец имел силу удара, но "
                 "никаких ответов в партере.",
        "stylistic_lessons": "UFC дебютанты в титульниках почти всегда проигрывают — нет октагон-таймы. "
                             "Striker-only без TDD = смерть против multi-skilled чемпиона.",
    },
    {
        "id": "chimaev_strickland_seed",
        "fighter_a": "Khamzat Chimaev", "fighter_b": "Sean Strickland",
        "event": "UFC 328 (placeholder)", "date": "2026-05-09",
        "weight_class": "Middleweight",
        "winner": "Khamzat Chimaev",
        "method": "Submission (rear-naked choke)", "round": 3,
        "notes": "Чимаев тейкдаунил Стрикленда несмотря на хороший TDD у Шона. Pressure-boxing "
                 "Шона не работал против настоящего physical wrestler'а уровня Дагестана.",
        "stylistic_lessons": "Высокий TDD% ничего не значит против элитной chain-wrestling. "
                             "Strickland всегда был узкопрофильным боксёром в матчах с борцами.",
    },
]
