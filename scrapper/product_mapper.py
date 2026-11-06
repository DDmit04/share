"""Общая часть мапперов товаров: варианты поискового запроса по строке xlsx.

У цепей, ремней, шлангов и лент разная маркировка, но запрос на площадке
строится одинаково: тип товара + обозначение, плюс варианты без описательных
слов и без хвостовых уточнений, которые площадки дописывают к заголовку.
Поэтому конкретный маппер задаёт только то, чем товары различаются:

* `TYPE_WORDS` — слова, с которых начинаются названия товара на площадке
  («Ремень», «Шланг», «Рукав», «Лента»); с каждым из них строятся запросы
  «тип + маркировка»;
* `TYPE_WORD_RE` — те же слова в любых падежах: их нельзя выбрасывать вместе
  с описательными словами;
* `KEEP_WORDS` — короткие обозначения без цифр («РВД», «Ду», «ГРМ»), которые
  тоже являются частью названия товара, а не описанием.

Сам `get_name_variants` живёт здесь, чтобы ремни, шланги и ленты не
копировали его трижды. `ChainScrapperMapper` пока пользуется своей копией:
его `_name_similarity` разбирает обозначения цепей, и перевести его на этот
класс можно отдельным шагом, не меняя работающий скрапинг.
"""

import re
from typing import Any

from pandas import Series, isna

from scrapper.model import EntityData
from scrapper.scrapper_mapper import ScrapperMapper

#: Сколько укороченных вариантов полного названия генерировать: каждый вариант —
#: отдельный поисковый запрос к площадке, поэтому их число ограничено.
TAIL_VARIANTS_LIMIT = 4

#: Знаки, которые остаются висеть в конце после отброшенного слова.
TAIL_PUNCT_RE = re.compile(r'[\s,;:\-–—()\[\]"«»]+$')

#: Хвостовые слова, после отбрасывания которых запрос бесполезен: числа и
#: единицы измерения («…, 5», «…, м», «…, бар»).
TAIL_JUNK_RE = re.compile(
    r'^[\d.,]+$'
    r'|^(?:'
    r'м|мм|см|м2|м3|м²|м³|м/п|пог\.?м\.?|шт|кг|г|л|мл'
    r'|бар|атм|мпа|кпа|°c|°с|руб'
    r')\.?$',
    re.IGNORECASE,
)

#: Слово целиком по-русски: только кириллица и дефис, в конце допускается знак
#: препинания. Обозначение товара под шаблон не попадает: «1SN-08» содержит
#: цифры, а «Ремень», «Шланг», «Лента» отсеиваются отдельно.
RUSSIAN_WORD_RE = re.compile(r'^[а-яё][а-яё\-]*[,.;:)]?$', re.IGNORECASE)

#: Пунктуация по краям токена: «(РВД)» и «РВД,» — одно и то же слово.
WORD_EDGE_PUNCT_RE = re.compile(r'^[^\w]+|[^\w]+$')


def _text(value: Any) -> str:
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


def _word_key(token: str) -> str:
    """Слово без пунктуации по краям, в нижнем регистре: «(РВД)» → «рвд»."""
    return WORD_EDGE_PUNCT_RE.sub('', token).casefold()


def _tail_variants(name: str, limit: int = TAIL_VARIANTS_LIMIT) -> list[str]:
    """Название без хвоста: варианты, отбрасывающие последние слова.

    Площадки дописывают к обозначению уточнения, которых нет в запросе:
    «Ремень 6PK1053 Gates», «Шланг 10x14, 20 м», «Лента 2-500-3 (ГОСТ 20-2018)».
    Отбрасывая хвост по одному слову, получаем запросы, которые совпадают
    с заголовками площадок: «Ремень 6PK1053, Gates» → «Ремень 6PK1053».

    Вариант берётся, пока в нём остаётся число — обозначение товара всегда
    с цифрами, — и хотя бы два слова: «Лента конвейерная» уже мусорный запрос.
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


class ProductScrapperMapper[Data](ScrapperMapper[Data]):
    """Маппер товара, у которого запрос строится вокруг типа и маркировки.

    Наследник задаёт `TYPE_WORDS`, `TYPE_WORD_RE` и `KEEP_WORDS`, а модель
    данных и колонки добавляются позже: у ремней, шлангов и лент ещё нет
    своих `*Data`, поэтому `from_row` поднимает ошибку. `get_name_variants`
    уже работает, а сходство названий наследуется из `ScrapperMapper`:
    сравниваются `link` и `full_link` без бренда, в результат идёт большее
    значение. Когда появятся маркировки, наследники уточнят `_name_similarity`.
    """

    #: Слова типа товара, с которых начинаются заголовки на площадках.
    #: С каждым строятся запросы «тип + маркировка»: у шлангов это и
    #: «Шланг», и «Рукав».
    TYPE_WORDS: tuple[str, ...] = ()

    #: Те же слова в любых падежах: их нельзя выбрасывать вместе с описанием.
    TYPE_WORD_RE: re.Pattern[str] = re.compile(r'(?!x)x')

    #: Обозначения без цифр, которые тоже входят в название товара
    #: («РВД», «Ду», «ГРМ»). Слова записаны в нижнем регистре.
    KEEP_WORDS: frozenset[str] = frozenset()

    def from_row(self, ser: Series) -> Data:
        """Строка входного xlsx в запись товара.

        Модели ремней, шлангов и лент ещё не описаны, поэтому здесь пока
        явная ошибка: `None` уронил бы скрапер позже и без объяснения.
        """
        raise NotImplementedError(
            f'{type(self).__name__}: модель товара ещё не описана — '
            'нужны COLUMN_TITLES и from_row'
        )

    def get_name_variants(self, data: EntityData) -> list[str]:
        """Возможные имена для поиска на площадке, от длинного к короткому.

        Длинные варианты точнее, поэтому пробуются первыми: полное внутреннее
        наименование и «Ссылка» содержат тип, бренд и номер детали. Полное
        наименование дополнительно укорачивается — варианты без хвостовых
        уточнений («Ремень 6PK1053 Gates» → «Ремень 6PK1053») переживают
        суффиксы, которых нет в заголовке площадки: «EMT», «5 м», ГОСТ-аналог
        в скобках. Из него же убираются русские описательные слова:
        «Ремень клиновой приводной Gates 6PK1053» → «Ремень Gates 6PK1053»
        (и его укороченные варианты). Если по ним ничего не нашлось, остаются
        короткие запросы: «тип + маркировка», «тип + бренд + маркировка» и
        «тип + маркировка + бренд», «бренд + маркировка» в обоих порядках и,
        наконец, одна маркировка — номер детали производителя или «Модель».

        Слова типа задаёт наследник: у шлангов запросы строятся и со словом
        «Шланг», и со словом «Рукав». Пустые и NaN-поля пропускаются,
        одинаковые варианты (без учёта регистра и лишних пробелов)
        схлопываются, результат отсортирован по длине по убыванию.
        """
        full_name = _text(data.get('full_link'))
        name = _text(data.get('link'))
        brand = _text(data.get('brand'))
        model_num = _text(data.get('model_num'))
        model = _text(data.get('model'))

        candidates = [full_name, name]
        # Уточнения в конце полного названия: «Ремень 6PK1053 Gates» →
        # «Ремень 6PK1053».
        candidates.extend(_tail_variants(full_name))
        # Русские описания перед маркировкой: «Ремень клиновой Gates 6PK1053»
        # → «Ремень Gates 6PK1053», плюс укороченные варианты уже без описаний.
        # Пустые и совпавшие варианты схлопнутся ниже, лишних запросов не будет.
        for text in (full_name, name):
            squeezed = self._drop_russian_words(text)
            if squeezed:
                candidates.append(squeezed)
                candidates.extend(_tail_variants(squeezed))
        for code in (model_num, model):
            if code:
                for type_word in self.TYPE_WORDS:
                    # «Ремень 6PK1053» — как начинаются заголовки товаров
                    candidates.append(_join(type_word, code))
                    # «Ремень Gates 6PK1053» и «Ремень 6PK1053 Gates»
                    candidates.append(_join(type_word, _with_brand(brand, code)))
                    candidates.append(_join(type_word, _with_brand_after(code, brand)))
                # Без типа товара: «Gates 6PK1053», «6PK1053 Gates», «6PK1053»
                candidates.append(_with_brand(brand, code))
                candidates.append(_with_brand_after(code, brand))
                candidates.append(code)

        unique: dict[str, str] = {}
        for candidate in candidates:
            if candidate:
                unique.setdefault(candidate.casefold(), candidate)

        return sorted(unique.values(), key=len, reverse=True)

    def _drop_russian_words(self, name: str) -> str:
        """Название без русских описательных слов: тип товара и маркировка.

        Площадки редко повторяют описательную часть названия — «клиновой»,
        «приводной», «напорный», «конвейерная», — поэтому запрос без неё
        находит больше: «Ремень клиновой приводной 6PK1053» →
        «Ремень 6PK1053».

        Остаются слова типа (`TYPE_WORD_RE`), обозначения без цифр
        (`KEEP_WORDS`, например «РВД») и всё, что содержит цифры:
        «10x14» и «2-500-3» — это маркировка, а не описание. Если после
        отбрасывания цифр в названии не осталось, вариант бесполезен —
        возвращается пустая строка.
        """
        kept = [
            token for token in name.split()
            if not RUSSIAN_WORD_RE.match(token)
            or self.TYPE_WORD_RE.search(token)
            or _word_key(token) in self.KEEP_WORDS
        ]
        result = ' '.join(kept)
        return result if re.search(r'\d', result) else ''
