"""Реестр площадок: одна строка на сайт.

Ключ словаря — это `Scrapper.name` (он же имя папки/файла чекпоинта).
Чтобы добавить площадку, достаточно дописать её сюда.
"""
from scrapper.chains.implementation.akmash_scrapper import AkmashScrapper
from scrapper.chains.implementation.aksdekom_scrapper import AksdekomScrapper
from scrapper.chains.implementation.euromehanika_scrapper import EuromehanikaScrapper
from scrapper.chains.implementation.ntg_scrapper import NtgScrapper
from scrapper.chains.implementation.privod_scrapper import PrivodScrapper
from scrapper.chains.implementation.rezon_scrapper import RezonScrapper
from scrapper.chains.implementation.tsepi_scrapper import TsepiScrapper
from scrapper.chains.implementation.tzc_scrapper import TzcScrapper

SITES = {
    "aksdekom": AksdekomScrapper,
    "ntg": NtgScrapper,
    "euromehanika": EuromehanikaScrapper,
    'rezon': RezonScrapper,
    'provod': PrivodScrapper,
    'tsepi': TsepiScrapper,
    'akmash': AkmashScrapper,
    'tzc': TzcScrapper
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
