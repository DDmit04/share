import re
from abc import ABC
from typing import Any

from pandas import Series

from utils.compare import comparable_text, levenshtein_norm
from utils.score import (
    candidate_points,
    has_dimensions as record_has_dimensions,
    missing_dimensions as record_missing_dimensions,
)


def _without_brand(text: Any, brand: Any) -> Any:
    """Название без бренда: «Ремень Gates 6PK1053» → «Ремень 6PK1053».

    Бренд ищется без учёта регистра и не внутри другого слова: «A» не
    вырезается из «SPA-1250», но «Gates» находится и в «Gates 6PK1053»,
    и в «Gates6PK1053». Многословный бренд («Gates Corporation») находится,
    даже если между словами несколько пробелов. Если название или бренд
    пусты/NaN, возвращается исходное название — сравнение само разберётся
    с пустой строкой.
    """
    if not isinstance(text, str) or not isinstance(brand, str):
        return text
    brand = ' '.join(brand.split())
    if not brand:
        return text
    # После бренда допускаем конец строки, пробел/пунктуацию или сразу
    # цифру: «Gates6PK1053» тоже встречается. Буква сразу после бренда
    # означает другое слово («Gatesy»), и такой бренд не вырезается.
    pattern = re.compile(
        r'(?<!\w)'
        + r'\s+'.join(re.escape(part) for part in brand.split())
        + r'(?![^\W\d])',
        re.IGNORECASE,
    )
    return ' '.join(pattern.sub(' ', text).split())


class ScrapperMapper[EntityData](ABC):
    """Соответствие между строкой входного xlsx и записью скрапинга.

    Здесь же лежит всё, что зависит от модели данных, а не от площадки: какие
    поля запись считает характеристиками (`DIMENSIONS`), какие колонки у неё
    во входном и итоговом xlsx (`COLUMNS` и `COLUMN_TITLES`) и по какому полю
    строки сопоставляются с входным файлом (`KEY_FIELD`). Поэтому `pipeline`
    работает не с конкретной моделью, а с переданным маппером: чтобы добавить
    другой товар, достаточно написать свой маппер и передать его в сборку.
    """

    #: Поля-характеристики записи: за каждое незаполненное снимаются очки.
    DIMENSIONS: tuple[str, ...] = ()

    #: Сколько очков снимается за каждую незаполненную характеристику.
    #: Ноль — штрафа нет, очки равны сходству названий.
    ZERO_PENALTY = 0.0

    #: Поле записи, по которому строка сопоставляется с входным файлом.
    KEY_FIELD = 'id'

    #: Внутренние имена полей записи в порядке колонок.
    COLUMNS: list[str] = []

    #: Заголовки тех же полей во входном xlsx и в итоговых файлах, в порядке
    #: `COLUMNS`. По этому словарю `from_row` читает вход, а `to_row` пишет
    #: итоговый xlsx, поэтому набор колонок у входного и выходных файлов
    #: совпадает.
    COLUMN_TITLES: dict[str, str] = {}

    def from_row(self, ser: Series) -> EntityData:
        pass

    def get_name_variants(self, data: EntityData) -> list[str]:
        pass

    @property
    def key_column(self) -> str:
        """Колонка входного xlsx, по которой записи сопоставляются с чекпоинтами."""
        return self.COLUMN_TITLES[self.KEY_FIELD]

    def key(self, record: dict) -> str:
        """Ключ записи для сопоставления с входным файлом (всегда строка)."""
        return str(record.get(self.KEY_FIELD, ''))

    def missing_dimensions(self, record: dict) -> int:
        """Сколько характеристик из `DIMENSIONS` не заполнено."""
        return record_missing_dimensions(record, self.DIMENSIONS)

    def has_dimensions(self, record: dict) -> bool:
        """Есть ли у записи хоть одна заполненная характеристика.

        Запись, у которой все характеристики пустые или нулевые, бесполезна: по
        ней не определить товар. Такая запись не должна попасть в processed и не
        должна вытеснять нормальную запись того же номера при выборе победителя.
        Если у модели характеристик нет (`DIMENSIONS` пуст), фильтра нет.
        """
        return record_has_dimensions(record, self.DIMENSIONS)

    def score(self, entity: EntityData) -> float:
        """Очки записи для выбора победителя среди площадок.

        Это сходство названий (`name_similarity`, его скрапер уже положил
        в запись) минус `ZERO_PENALTY` за каждую незаполненную характеристику
        из `DIMENSIONS`. Наследники задают свой `DIMENSIONS` и `ZERO_PENALTY`:
        у цепей незаполненный шаг или диаметр ролика снижают очки, у моделей
        без характеристик штрафа нет вовсе.

        Очки считаются один раз, при скрапинге (`Scrapper.scrap`), и лежат
        в чекпоинте рядом с записью — сборка их только читает.
        """
        return candidate_points(entity, self.DIMENSIONS, self.ZERO_PENALTY)

    def to_row(self, record: dict) -> dict:
        """Строка итогового xlsx: заголовки и порядок колонок входного файла.

        Служебные поля, которых нет в `COLUMN_TITLES` (`name_similarity`,
        `score`, `site`), сюда не попадают: они нужны для выбора победителя и
        остаются в чекпоинте `raw/<site>.jsonl`, а итоговый файл сохраняет
        набор колонок исходного xlsx.
        """
        return {title: record.get(key) for key, title in self.COLUMN_TITLES.items()}

    def name_similarity(self, desc: Any, data: EntityData) -> float:
        """Насколько найденное название подходит товару из строки xlsx.

        Сравнивается не только короткая «Ссылка» (`link`), но и полное
        внутреннее наименование (`full_link`): площадки иногда повторяют
        в заголовке то, чего нет в «Ссылке», и наоборот. Берётся большее
        из двух сходств, поэтому совпадения с любой из этих строк достаточно.

        Перед сравнением из `link` и `full_link` отбрасывается `brand`: он
        может быть записан иначе, чем в заголовке площадки, и не должен
        мешать совпадению маркировки. Найденное название `desc` не чистится.

        Само сравнение одной пары названий делает `_name_similarity`.
        Наследники переопределяют именно его, когда в названии есть
        структура, которую нужно понимать: `ChainScrapperMapper` сравнивает
        не слова, а обозначение цепи и номер, поэтому описательные слова,
        ГОСТ-аналог в скобках и бренд перестают мешать совпадению.

        `data` — запись товара (`EntityData`), `desc` — найденное название.
        Пустое или NaN-поле даёт 0.0 для своей пары; если пусты оба, сходства
        нет.
        """
        brand = data.get('brand')
        link = _without_brand(data.get('link'), brand)
        full_link = _without_brand(data.get('full_link'), brand)
        return max(
            self._name_similarity(desc, link),
            self._name_similarity(desc, full_link),
        )

    def _name_similarity(self, desc: Any, src: Any) -> float:
        """Сходство найденного названия с одной строкой товара, от 0.0 до 1.0.

        Базовая реализация сравнивает названия как строки: `comparable_text`
        приводит их к нижнему регистру и оставляет только буквы и цифры,
        а затем считается нормированное расстояние Левенштейна. Так можно
        сравнивать любой товар, не зная его маркировки.

        Оба аргумента могут быть `None`/`NaN` — тогда сходства нет (0.0).
        """
        left = comparable_text(desc)
        right = comparable_text(src)
        if not left or not right:
            return 0.0
        return levenshtein_norm(left, right)
