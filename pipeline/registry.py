"""Реестр площадок: одна строка на сайт.

Ключ словаря — это `Scrapper.name` (он же имя папки/файла чекпоинта).
Чтобы добавить площадку, достаточно дописать её сюда.
"""

from scrapper.abc_mech_scrapper import AbcMechScrapper
from scrapper.armtek_scrapper import ArmTekScrapper
from scrapper.arpik_scrapper import ArpikScrapper
from scrapper.consbrgs_scrapper import ConsbrgsScrapper
from scrapper.etm_scrapper import EtmScrapper
from scrapper.podgipnik_inform_scrapper import PodshipnikInformScrapper
from scrapper.podshipnik_ru_scrapper import PodshipnikRuScrapper as PodshipnikRuScrapper
from scrapper.podshipnikru_scrapper import PodshipnikRuScrapper as PodshipnikRuComScrapper
from scrapper.podtrade_scrapper import PodtradeScrapper
from scrapper.spec_prom_scrapper import SpecPromScrapper

SITES = {
    "bergab.ru": ArmTekScrapper,
    "etm.ru": EtmScrapper,
    "arpik.ru": ArpikScrapper,
    "podshipnik.ru": PodshipnikRuScrapper,
    "podshipnikru.com": PodshipnikRuComScrapper,
    "podtrade.ru": PodtradeScrapper,
    "specprompodshipnik.ru": SpecPromScrapper,
    "consbrgs.com": ConsbrgsScrapper,
    "podshipnikinform.ru": PodshipnikInformScrapper,
    "ru.abcmechanics.com": AbcMechScrapper,
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
