import re
from typing import Any

from pandas import Series, isna

from utils.compare import comparable_code, levenshtein_norm
from scrapper.chains.data.chain_model import ChainData
from scrapper.scrapper_mapper import ScrapperMapper

#: Слово, с которого начинаются названия цепей на площадках.
CHAIN_TYPE_WORD = 'Цепь'

#: Сходство, когда обозначения цепей заведомо разные: это разные товары, и
#: совпадение описательных слов их не роднит.
CHAIN_MISMATCH_SIMILARITY = 0.0

#: Потолок сходства для номеров, которые не совпали: похожий, но другой
#: артикул не должен проходить `SIMILARITY_THRESHOLD`, иначе в processed
#: попадёт не та цепь.
CHAIN_NUMBER_CEILING = 0.80

#: Шаг цепи (мм) → обозначение ISO 606 серии B. Шаги ГОСТ 13568 (ПР-9,525,
#: ПР-12,7, ПР-15,875 …) совпадают с серией B, поэтому «ПР-9,525-9,1» и
#: «06B-1» — одна и та же цепь.
ISO_B_BY_PITCH = {
    8.0: '05B', 9.525: '06B', 12.7: '08B', 15.875: '10B', 19.05: '12B',
    25.4: '16B', 31.75: '20B', 38.1: '24B', 44.45: '28B', 50.8: '32B',
    63.5: '40B', 76.2: '48B',
}

#: Номер цепи по ANSI → обозначение ISO 606 серии A: #40 и 08A — одна цепь.
#: Номеров без пары в серии A (#25, #35, #41, #180) тут нет: у них другие
#: ролик и ширина, приравнивать их к ISO нельзя.
ISO_A_BY_ANSI = {
    40: '08A', 50: '10A', 60: '12A', 80: '16A', 100: '20A',
    120: '24A', 140: '28A', 160: '32A', 200: '40A', 240: '48A',
}

#: Обозначение по ISO 606: калибр + серия (`06B`, `08A`) и число рядов через
#: дефис (`06B-2`). Однорядная цепь пишется без суффикса.
ISO_MARKING_RE = re.compile(
    r'(?<![0-9A-Z])(0[5-9]|[1-5][0-9])([AB])(?:-([1-9]))?(?![0-9A-Z])',
    re.IGNORECASE,
)

#: Обозначение по ГОСТ 13568: ПР (однорядная), ПРД (двухрядная), ПРТ
#: (трёхрядная) и шаг в миллиметрах: «ПР-9,525-9,1», «ПРД-12,7-36».
GOST_MARKING_RE = re.compile(r'\bПР([ДТ])?[\s-]*(\d+(?:[.,]\d+)?)', re.IGNORECASE)

#: Номер по ANSI с явной приставкой: «#40», «ANSI 40», «ASA 40-2».
ANSI_MARKED_RE = re.compile(r'(?:#|ANSI|ASA)\s*(\d{2,3})(?:-([1-9]))?(?!\d)', re.IGNORECASE)

#: Номер по ANSI с числом рядов: «40-1». Одиночное число без приставки не
#: считается: «Цепь 40 звеньев» — это длина, а не номер цепи.
ANSI_ROWS_RE = re.compile(r'(?<![\w.,])(\d{2,3})-([1-9])(?![\w.,])', re.IGNORECASE)

#: Слова, по которым видно, что продают не цепь: у звездочки и звена то же
#: обозначение, что у цепи, но это другой товар.
NOT_CHAIN_RE = re.compile(
    r'зв[её]зд(?:оч|а)|спрокет|\bsprocket\b|звен(?:о|ья)|полузвен|зам(?:ок|к)|\blink\b',
    re.IGNORECASE,
)

#: Слово, с которого начинается название самой цепи.
CHAIN_WORD_RE = re.compile(r'\bцеп(?:ь|и|ью)\b|\bchain\b', re.IGNORECASE)

#: Сколько укороченных вариантов полного названия генерировать: каждый вариант —
#: отдельный поисковый запрос к площадке, поэтому их число ограничено.
TAIL_VARIANTS_LIMIT = 4

#: Знаки, которые остаются висеть в конце после отброшенного слова.
TAIL_PUNCT_RE = re.compile(r'[\s,;:\-–—]+$')

#: Хвостовые слова, после отбрасывания которых запрос бесполезен: числа и
#: единицы измерения («…, 5», «…, м»).
TAIL_JUNK_RE = re.compile(r'^[\d.,]+$|^(?:м|мм|см|шт|кг|г|л)$', re.IGNORECASE)

#: Слово целиком по-русски: только кириллица и дефис, в конце допускается знак
#: препинания. Обозначение цепи под шаблон не попадает: «ПР-9,525» содержит
#: цифры, а «Цепь» отсеивается отдельно.
RUSSIAN_WORD_RE = re.compile(r'^[а-яё][а-яё\-]*[,.;:)]?$', re.IGNORECASE)


def _pitch(value: str) -> float:
    """Шаг из обозначения ГОСТ: «9,525» → 9.525."""
    return round(float(value.replace(',', '.')), 3)


def _ansi_marking(number: str, rows: str | None) -> tuple[str, int]:
    """Ключ цепи по номеру ANSI: #40 → ("ISO:08A", 1), #35 → ("ANSI:35", 1)."""
    iso = ISO_A_BY_ANSI.get(int(number))
    code = f'ISO:{iso}' if iso else f'ANSI:{int(number)}'
    return (code, int(rows or 1))


def chain_markings(text: Any) -> set[tuple[str, int]]:
    """Канонические обозначения цепи, найденные в названии.

    Обозначения разных систем приводятся к одному ключу — (система со
    обозначением, число рядов), поэтому одна и та же цепь, записанная
    по-разному, даёт одинаковый ключ:

    * «06B-1»        → ("ISO:06B", 1);
    * «06B»          → ("ISO:06B", 1) — однорядная пишется без суффикса;
    * «ПР-9,525-9,1» → ("ISO:06B", 1) — шаги ГОСТ 13568 равны серии B;
    * «ПРД-12,7-36»  → ("ISO:08B", 2) — ПРД двухрядная, ПРТ трёхрядная;
    * «ANSI 40-2»    → ("ISO:08A", 2) — #40 и 08A это одна цепь;
    * «#35»          → ("ANSI:35", 1) — пары в серии A нет, у #35 другой ролик.

    Грузоподъёмность ГОСТ (второе число, «-9,1») в ключ не входит: обозначение
    ISO её тоже не различает.
    """
    if not text:
        return set()
    value = str(text).lower()
    markings: set[tuple[str, int]] = set()

    for size, series, rows in ISO_MARKING_RE.findall(value):
        markings.add(('ISO:' + (size + series).upper(), int(rows or 1)))

    for row_letter, pitch in GOST_MARKING_RE.findall(value):
        rows = {'д': 2, 'т': 3}.get(row_letter, 1)
        iso = ISO_B_BY_PITCH.get(_pitch(pitch))
        if iso:
            markings.add(('ISO:' + iso, rows))
        else:
            # Шага нет в таблице — оставляем его обозначением ГОСТ как есть.
            markings.add(('ГОСТ:' + pitch.replace(',', '.'), rows))

    for number, rows in ANSI_MARKED_RE.findall(value):
        markings.add(_ansi_marking(number, rows))

    for number, rows in ANSI_ROWS_RE.findall(value):
        markings.add(_ansi_marking(number, rows))

    return markings


#: Токен-артикул: цифры и буквы с разделителями внутри («5592312.100», «125-2»).
CODE_TOKEN_RE = re.compile(r'[0-9a-z]+(?:[.\-_/][0-9a-z]+)*', re.IGNORECASE)


def chain_codes(text: Any) -> set[str]:
    """Номера-артикулы цепи: «Цепь Акмаш 5592312.100» → {"5592312100"}.

    Артикулом считается только токен с цепочкой из трёх цифр: «06B-1» и «D3»
    номерами не являются — обозначение цепи разбирается отдельно, в
    `chain_markings`. Слова без цифр («Цепь», бренд) отсеиваются сами собой,
    поэтому список брендов не нужен. Номер сравнивается без разделителей,
    поэтому «5592312.100» и «5592312-100» — один артикул.
    """
    if not text:
        return set()
    return {
        comparable_code(token)
        for token in CODE_TOKEN_RE.findall(str(text).lower())
        if re.search(r'\d{3,}', token)
    }


def _product_kind(text: str) -> str | None:
    """«Цепь» это или «звездочка»/«звено».

    Русские названия начинаются с главного слова, поэтому решает то, которое
    встретилось первым: «Звено цепи 06B-1» — звено, «Цепь 06B-1 звено
    соединительное» — цепь. `None` — в названии нет ни того, ни другого.
    """
    found = [(match.start(), 'other') for match in NOT_CHAIN_RE.finditer(text)]
    found += [(match.start(), 'chain') for match in CHAIN_WORD_RE.finditer(text)]
    return min(found)[1] if found else None


def _name_text(value: Any) -> str:
    """Название для сравнения: NaN/None → '', остальное в нижнем регистре."""
    if value is None or isna(value):
        return ''
    return str(value).lower()


def _text(value) -> str:
    """Ячейка xlsx как строка: NaN/None → '', лишние пробелы схлопываются."""
    if value is None or isna(value):
        return ''
    return ' '.join(str(value).split())


def _join(*parts: str) -> str:
    """Склеивает непустые части через пробел."""
    return ' '.join(part for part in parts if part)


def _with_brand(brand: str, code: str) -> str:
    """Код с брендом впереди, если бренд ещё не входит в сам код."""
    if not brand or brand.casefold() in code.casefold():
        return code
    return _join(brand, code)


def _with_brand_after(code: str, brand: str) -> str:
    """Код с брендом в конце, если бренд ещё не входит в сам код."""
    if not brand or brand.casefold() in code.casefold():
        return code
    return _join(code, brand)


def _tail_variants(name: str, limit: int = TAIL_VARIANTS_LIMIT) -> list[str]:
    """Название без хвоста: варианты, отбрасывающие последние слова.

    Площадки дописывают к обозначению цепи уточнения, которых нет в запросе:
    «Цепь 06B-1 D3 DH», «Цепь 06B-1, EMT, 5 м», «Цепь 06B-1 (ПР-9,525-9,1)».
    Отбрасывая хвост по одному слову, получаем запросы, которые совпадают
    с заголовками площадок: «Цепь 06B-1, EMT» → «Цепь 06B-1».

    Вариант берётся, пока в нём остаётся число — обозначение цепи всегда
    с цифрами, — и хотя бы два слова: «Цепь роликовая» уже мусорный запрос.
    Числа и единицы измерения в конце («…, 5», «…, м») пропускаются, но
    отбрасывание после них продолжается.
    """
    tokens = name.split()
    variants: list[str] = []
    while len(tokens) > 2:
        tokens.pop()
        if TAIL_JUNK_RE.match(tokens[-1].strip(',;.')):
            continue
        tail = TAIL_PUNCT_RE.sub('', ' '.join(tokens))
        if not re.search(r'\d', tail):
            break
        variants.append(tail)
        if len(variants) >= limit:
            break
    return variants


def _drop_russian_words(name: str) -> str:
    """Название без русских описательных слов: «Цепь» и обозначение цепи.

    Площадки редко повторяют описательную часть названия — «роликовая»,
    «приводная», «тяжёлая серия», — поэтому запрос без неё находит больше:
    «Цепь роликовая приводная 06B-1 D3 DH» → «Цепь 06B-1 D3 DH».

    Остаётся слово «Цепь» и всё, что содержит цифры: «ПР-9,525-9,1» записано
    кириллицей, но это обозначение цепи, а не описание. Если после отбрасывания
    цифр в названии не осталось, вариант бесполезен — возвращается пустая строка.
    """
    kept = [
        token for token in name.split()
        if not RUSSIAN_WORD_RE.match(token) or CHAIN_WORD_RE.search(token)
    ]
    result = ' '.join(kept)
    return result if re.search(r'\d', result) else ''


class ChainScrapperMapper(ScrapperMapper[ChainData]):
    #: Заголовки полей в том же порядке, что и внутренние имена `COLUMNS`.
    #: Один список работает в обе стороны: `from_row` читает по нему входной
    #: xlsx, `to_row` пишет по нему `processed.xlsx`. Поэтому набор колонок
    #: у входного и выходного файлов совпадает, и итог можно сравнивать с
    #: исходником построчно.
    COLUMN_TITLES = {
        "id": "Номер материала",
        "link": "Ссылка",
        "full_link": "Полное наименование внутреннее",
        "model_num": "Номер детали производителя",
        "brand": "Производитель/Марка/Бренд",
        "model": "Модель",
        "chain_step": "Шаг цепи мм",
        "chain_val_d": "Диаметр валика мм",
        "chain_rol_d": "Диаметр ролика мм",
        "chain_val_len": "Длина валика мм",
        "chain_plate_height": "Высота пластины мм",
        "chain_plate_dist": "Расстояние между внутренними пластинами мм",
        "source_name": "Имя",
        "source_link": "Источник",
    }

    #: Внутренние имена полей записи (ключи `ChainData`) в порядке колонок.
    COLUMNS = list(COLUMN_TITLES)

    DIMENSIONS = (
        "chain_step",
        "chain_val_d",
        "chain_rol_d",
        "chain_val_len",
        "chain_plate_height",
        "chain_plate_dist",
    )

    #: Незаполненная характеристика цепи снижает очки записи.
    ZERO_PENALTY = 0.05

    def from_row(self, ser: Series) -> ChainData:
        return ChainData(
            **{key: ser[title] for key, title in self.COLUMN_TITLES.items()},
            # Заполняются при скрапинге: сходство — в `scrap_list` площадки,
            # очки — в `Scrapper.scrap`. 0.0 значит «ещё не посчитано».
            name_similarity=0.0,
            score=0.0,
        )

    def get_name_variants(self, data: ChainData) -> list[str]:
        """Возможные имена для поиска на площадке, от длинного к короткому.

        Длинные варианты точнее, поэтому пробуются первыми: полное внутреннее
        наименование и «Ссылка» содержат тип, бренд и номер детали. Полное
        наименование дополнительно укорачивается — варианты без хвостовых
        уточнений («Цепь 06B-1 D3 DH» → «Цепь 06B-1 D3» → «Цепь 06B-1»)
        переживают суффиксы, которых нет в заголовке площадки: «EMT», «5 м»,
        ГОСТ-аналог в скобках. Из него же убираются русские описательные слова:
        «Цепь роликовая приводная 06B-1 D3 DH» → «Цепь 06B-1 D3 DH» (и его
        укороченные варианты). Если по ним ничего не нашлось, остаются короткие
        запросы: «Цепь + маркировка» («Цепь 5592312.100»), «Цепь + бренд +
        маркировка» и «Цепь + маркировка + бренд», «бренд + маркировка» в обоих
        порядках и, наконец, одна маркировка — номер детали производителя или
        «Модель».
        Такие запросы переживают расхождения в описательных словах («модульная»,
        «без крюков»), которых на площадке может не быть.

        Пустые и NaN-поля пропускаются, одинаковые варианты (без учёта регистра
        и лишних пробелов) схлопываются, результат отсортирован по длине по
        убыванию.
        """
        full_name = _text(data.get('full_link'))
        name = _text(data.get('link'))
        brand = _text(data.get('brand'))
        model_num = _text(data.get('model_num'))
        model = _text(data.get('model'))

        candidates = [full_name, name]
        # Уточнения в конце полного названия: «Цепь 06B-1 D3 DH» → «Цепь 06B-1».
        candidates.extend(_tail_variants(full_name))
        # Русские описания перед маркировкой: «Цепь роликовая приводная 06B-1»
        # → «Цепь 06B-1», плюс укороченные варианты уже без описаний.
        # Пустые и совпавшие варианты схлопнутся ниже, лишних запросов не будет.
        for text in (full_name, name):
            squeezed = _drop_russian_words(text)
            if squeezed:
                candidates.append(squeezed)
                candidates.extend(_tail_variants(squeezed))
        for code in (model_num, model):
            if code:
                # «Цепь 5592312.100» — как начинаются заголовки товаров на площадках
                candidates.append(_join(CHAIN_TYPE_WORD, code))
                # «Цепь Акмаш 5592312.100» и «Цепь 5592312.100 Акмаш»
                candidates.append(_join(CHAIN_TYPE_WORD, _with_brand(brand, code)))
                candidates.append(_join(CHAIN_TYPE_WORD, _with_brand_after(code, brand)))
                candidates.append(_with_brand(brand, code))
                candidates.append(_with_brand_after(code, brand))
                candidates.append(code)

        unique: dict[str, str] = {}
        for candidate in candidates:
            if candidate:
                unique.setdefault(candidate.casefold(), candidate)

        return sorted(unique.values(), key=len, reverse=True)

    def _name_similarity(self, desc: Any, src: Any) -> float:
        """Насколько найденное название и строка товара обозначают одну и ту же цепь.

        Сравнивается не текст названия, а обозначение цепи: «Цепь роликовая
        06B-1 (ПР-9,525-9,1), EMT» и «Цепь 06B-1 D3 DH» — один товар, потому
        что обозначение у них одно и то же. `chain_markings` приводит к общему
        виду 06B, ГОСТ ПР-9,525 и ANSI 40, поэтому одна и та же цепь совпадает,
        в какой бы системе её ни записали.

        Это сравнение одной пары названий; максимум по `link` и `full_link`
        берёт `ScrapperMapper.name_similarity`.

        Порядок решений:

        * одно из названий не про цепь (звездочка, звено) — 0.0;
        * обозначения есть у обоих — 1.0 при общем, 0.0 при разных: 06B-1 и
          08B-2 не взаимозаменяемы, и общие слова вроде «Цепь роликовая»
          этого не перевешивают;
        * обозначения нет — сравниваются номера-артикулы («5592312.100»):
          равные дают 1.0, разные — не больше `CHAIN_NUMBER_CEILING`;
        * ни обозначения, ни номера — базовое сравнение строк.
        """
        desc = _name_text(desc)
        src = _name_text(src)
        if not desc or not src:
            return 0.0

        # «Звездочка 06B-1» несёт обозначение цепи, но цепью не является.
        kind_desc = _product_kind(desc)
        kind_src = _product_kind(src)
        if {kind_desc, kind_src} == {'chain', 'other'}:
            return CHAIN_MISMATCH_SIMILARITY

        markings_desc = chain_markings(desc)
        markings_src = chain_markings(src)
        if markings_desc and markings_src:
            if markings_desc & markings_src:
                return 1.0
            return CHAIN_MISMATCH_SIMILARITY

        codes_desc = chain_codes(desc)
        codes_src = chain_codes(src)
        if codes_desc and codes_src:
            if codes_desc & codes_src:
                return 1.0
            best_sim = max(
                levenshtein_norm(code_desc, code_src)
                for code_desc in codes_desc
                for code_src in codes_src
            )
            return min(best_sim, CHAIN_NUMBER_CEILING)

        return super()._name_similarity(desc, src)

