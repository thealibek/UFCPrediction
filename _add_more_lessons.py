"""Добавить дополнительные уроки на основе оставшихся промахов V2."""
import sys, types
_st = types.ModuleType("streamlit")
sys.modules["streamlit"] = _st

from lessons import add_lesson

EXTRA = [
    {
        "title": "Падающий heavyweight-ветеран с серией KO-losses",
        "body": (
            "Tuivasa-pattern: heavy hitter, который ВЫГЛЯДИТ как нокаутёр но "
            "проиграл 3+ боя подряд KO/TKO. Чин и кардио убиты, момент уже "
            "ушёл. Молодой соперник с любым приличным выстрелом — фаворит. "
            "Если ветеран на серии 3+ losses → НЕ ставь на него независимо "
            "от имени. Heavy ‘Big Tai’-style фейды повторяются."
        ),
        "tags": ["heavyweight", "decline", "loss_streak"],
        "trigger_keywords": ["tuivasa", "heavyweight", "lose streak", "3 losses",
                             "падающий", "decline"],
    },
    {
        "title": "Heavyweight с большим reach-disadvantage = glass chin trigger",
        "body": (
            "В тяжёлом весе reach + footwork решают часто больше чем сила. "
            "Если у фаворита (по имени) reach-disadvantage 4+ см и нет "
            "wrestling-base — он будет ловить контру весь бой. Не overconfident. "
            "Гейзиев/Першич-pattern: мощный wrestler-нокаутер vs более "
            "длинный footwork-striker → striker часто берёт."
        ),
        "tags": ["heavyweight", "reach", "striking"],
        "trigger_keywords": ["heavyweight", "reach disadvantage", "wrestler", "striker"],
    },
    {
        "title": "Старый Flyweight/BW (33+) в дивизионе скоростников",
        "body": (
            "В лёгких весах (FLY, BW, FW) скорость декаит к 32+ резче чем "
            "в средних. Tim Elliott / Meerschaert / Gorimbo патерны: ветеран "
            "33+ против активного молодого скоростника = чаще проигрывает "
            "по очкам через активность. НЕ ставь heavy favorite на ветерана "
            "в лёгких дивизионах если соперник <30 и стилистически активный."
        ),
        "tags": ["age_decline", "small_divisions"],
        "trigger_keywords": ["flyweight", "bantamweight", "featherweight", "33+", "ветеран"],
    },
    {
        "title": "‘Имя > форма’ ловушка: BMF/legend status overrides последние 3 боя",
        "body": (
            "Если у бойца ‘имя’ (звезда UFC, чемпион в прошлом, BMF), "
            "модель часто ставит его фаворитом ИГНОРИРУЯ последние 3 боя. "
            "Это самая частая ошибка. Правило: ВСЕГДА смотри последние 3 "
            "боя — если 2+ losses, имя не спасает. Tuivasa, Dariush, "
            "Meerschaert — все попали под это."
        ),
        "tags": ["name_bias", "recency"],
        "trigger_keywords": ["legend", "former champion", "bmf", "имя", "звезда"],
    },
    {
        "title": "Calibration cap: не выходи за 65% без RAG-данных",
        "body": (
            "Если у тебя нет полных метрик бойцов (SLpM/TDAvg/etc), "
            "максимальная уверенность которую ты имеешь право выдать — 65%. "
            "Меньше уверенность → меньше Brier penalty при ошибке. "
            "Лучше быть систематически underconfident чем overconfident."
        ),
        "tags": ["calibration", "low_data"],
        "trigger_keywords": ["no data", "недостаточно", "уверенность", "calibration"],
    },
]


def main():
    added = 0
    for l in EXTRA:
        add_lesson(l["title"], l["body"], l["tags"], l["trigger_keywords"],
                   source="manual:post_v2_blindtest")
        added += 1
        print(f"✅ {l['title']}")
    print(f"\n📚 Добавлено уроков: {added}")


if __name__ == "__main__":
    main()
