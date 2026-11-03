import logging
from abc import ABC
from typing import Generator, TypeVar

import pandas as pd
from bs4 import Tag

from net import configure_proxies
from model import EntityData
from scrapper_mapper import ScrapperMapper

TEntity = TypeVar('TEntity', bound=EntityData)

class Scrapper[TEntity](ABC):

    def __init__(self, url: str, host: str, name: str, mapper: ScrapperMapper):
        configure_proxies()
        self.host = host
        self.url = url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 YaBrowser/25.12.0.0 Safari/537.36"
        }
        self.name = name
        self.log = logging.getLogger(name)
        #: Сколько ошибок скрапинга проглочено (они пишутся в лог, но строку не роняют).
        self.errors = 0
        self.mapper = mapper

    def scrap_xlsx(
            self,
            path: str,
            batch_size: int | None = None
    ) -> Generator[tuple[list[TEntity], list[TEntity]]]:
        df = pd.read_excel(path)
        processed = []
        unprocessed = []
        i = 0
        for index, table_item in df.iterrows():
            i += 1
            new_bearing = self.mapper.from_row(table_item)
            scrapped = self.scrap(new_bearing)
            if scrapped is not None:
                processed.append(scrapped)
            else:
                unprocessed.append(new_bearing)

            if batch_size is not None and batch_size % i == 0:
                yield processed, unprocessed

        yield processed, unprocessed
        raise StopIteration()

    def scrap(self, new_entity: TEntity) -> TEntity | None:
        print(f'Поиск: {new_entity['description']}')
        variants = self.mapper.get_name_variants(new_entity)
        print(f'Варианты {variants}')
        for name_inv in variants:
            url = self.url % name_inv.replace(' ', '+')
            print(f'Название: {new_entity['link']}')
            print(f'Поиск: {name_inv}')
            print(f'Поиск по URL: {url}')
            try:
                res = self.scrap_by_url(new_entity, url)
                if res is not None:
                    return res
            except Exception as e:
                self.errors += 1
                self.log.error(f'[{self.name}] ошибка исполнения - {new_entity["link"]}, e - {e}')

        return None

    def scrap_data(self, entity_data: TEntity, url: str) -> TEntity | None:
        pass

    def scrap_list(self, entity_data: TEntity, bearing_list: Tag) -> TEntity | None:
        pass

    def scrap_by_url(self, entity_data: TEntity, url: str) -> TEntity | None:
        pass
