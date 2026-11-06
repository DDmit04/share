from scrapper.model import EntityData

# --- Очки записи -----------------------------------------------------------
#
# Сходство и очки считает скрапер, а не сборка: так в чекпоинте лежит уже
# готовая к сравнению запись, и `--assemble-only` ничего не пересчитывает.
#
# Какие поля считать характеристиками, задаёт маппер модели: его `DIMENSIONS`
# и `ZERO_PENALTY` передаются сюда аргументами, поэтому формулы работают для
# любой модели, а не только для цепей.

#: Штраф по умолчанию за каждую незаполненную характеристику.
ZERO_PENALTY = 0.05


def is_zero(value) -> bool:
    """Пустая или нулевая характеристика: None, NaN, '' или 0."""
    if value is None:
        return True
    if value == '':
        return True
    try:
        number = float(value)
    except (TypeError, ValueError):
        return True
    return number == 0.0 or number != number  # NaN != NaN


def missing_dimensions(record: dict, dimensions: tuple) -> int:
    """Сколько характеристик из `dimensions` не заполнено."""
    return sum(1 for key in dimensions if is_zero(record.get(key)))


def has_dimensions(record: dict, dimensions: tuple) -> bool:
    """Есть ли у записи хотя бы одна ненулевая характеристика.

    Запись, у которой все характеристики пустые или нулевые, бесполезна: по ней
    не определить товар. Такая запись не должна попасть в processed и не должна
    вытеснять нормальную запись того же номера при выборе победителя. Если
    у модели характеристик нет (`dimensions` пуст), фильтра нет.
    """
    if not dimensions:
        return True
    return any(not is_zero(record.get(key)) for key in dimensions)


def candidate_points(record: EntityData, dimensions: tuple, zero_penalty: float = ZERO_PENALTY) -> float:
    """Итоговые очки: сходство минус штраф за каждую пустую характеристику."""
    similarity = float(record.get('name_similarity') or 0.0)
    return similarity - zero_penalty * missing_dimensions(record, dimensions)
