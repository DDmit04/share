from pandas import Series, isna

from scrapper.chains.model import ChainData
from scrapper.scrapper import ScrapperMapper

#: Слово, с которого начинаются названия цепей на площадках.
CHAIN_TYPE_WORD = 'Цепь'


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


class ChainScrapperMapper(ScrapperMapper[ChainData]):
    def from_row(self, ser: Series) -> ChainData:
        return ChainData(
            id=ser['Номер материала'],
            link=ser['Ссылка'],
            full_link=ser['Полное наименование внутреннее'],
            model_num=ser['Номер детали производителя'],
            brand=ser['Производитель/Марка/Бренд'],
            model=ser['Модель'],
            chain_step=ser['Шаг цепи мм'],
            chain_val_d=ser['Диаметр валика мм'],
            chain_rol_d=ser['Диаметр ролика мм'],
            chain_val_len=ser['Длина валика мм'],
            chain_plate_height=ser['Высота пластины мм'],
            chain_plate_dist=ser['Расстояние между внутренними пластинами мм'],
            source_name=ser['Имя'],
            source_link=ser['Источник'],
        )

    def get_name_variants(self, data: ChainData) -> list[str]:
        """Возможные имена для поиска на площадке, от длинного к короткому.

        Длинные варианты точнее, поэтому пробуются первыми: полное внутреннее
        наименование и «Ссылка» содержат тип, бренд и номер детали. Если по ним
        ничего не нашлось, остаются короткие запросы: «Цепь + маркировка»
        («Цепь 5592312.100»), «Цепь + бренд + маркировка» и «Цепь + маркировка
        + бренд», «бренд + маркировка» в обоих порядках и, наконец, одна
        маркировка — номер детали производителя или «Модель».
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


