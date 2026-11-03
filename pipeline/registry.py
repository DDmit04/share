"""Реестр площадок: одна строка на сайт.

Ключ словаря — это `Scrapper.name` (он же имя папки/файла чекпоинта).
Чтобы добавить площадку, достаточно дописать её сюда.
"""

SITES = {
}


def resolve_sites(value: str) -> list[tuple[str, type]]:
    """'all' или 'bergab.ru,etm.ru' -> список (имя, класс скрапера)."""
    if value.strip() == "all":
        return list(SITES.items())
    names = [name.strip() for name in value.split(",") if name.strip()]
    unknown = [name for name in names if name not in SITES]
    if unknown:
        raise SystemExit(
            f"Неизвестные площадки: {', '.join(unknown)}.\n"
            f"Доступны: {', '.join(SITES)}"
        )
    return [(name, SITES[name]) for name in names]
