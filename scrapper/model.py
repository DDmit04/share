from typing import TypedDict


class EntityData(TypedDict):
    """Строка результата скрапинга: что искали и что в итоге нашли.

    `name_similarity` и `score` заполняет сам скрапер, а не сборка: сходство
    считается в `scrap_list` в момент выбора кандидата, очки — в `Scrapper.scrap`
    сразу после того, как площадка отдала характеристики. Оба поля по умолчанию
    `0.0`, то есть «ещё не посчитано»: у записей старых чекпоинтов этих полей
    нет, и сборка (`pipeline.assemble`) досчитывает их сама.
    """

    id: int
    link: str
    full_link: str
    model_num: str
    brand: str
    model: str
    #: Насколько найденное название совпало с искомым, от 0.0 до 1.0.
    name_similarity: float
    #: Очки записи для выбора победителя среди площадок (`ScrapperMapper.score`).
    score: float
