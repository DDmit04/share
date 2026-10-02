import logging
from abc import ABC
from typing import Generator

import pandas as pd
from bs4 import Tag

from compare.name_gen import get_name_variants
from scrapper.utils import from_clean_bearing, from_dirty_bearing, dirty_from_row
from utills import CleanBearingData, DirtyBearingData


class Scrapper(ABC):

    def __init__(self, url: str, host: str, name: str):
        self.host = host
        self.url = url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 YaBrowser/25.12.0.0 Safari/537.36"
        }
        self.name = name
        self.log = logging.getLogger(name)

    def scrap_dirty_xlsx(
            self,
            path: str,
            batch_size: int | None = None) -> Generator[tuple[list[CleanBearingData], list[DirtyBearingData]]]:
        df = pd.read_excel(path)
        i = 0
        processed = []
        unprocessed = []
        for index, table_item in df.iterrows():
            print(f'[{self.name}] Обработано {i} из {len(df.index)}')
            i += 1
            new_bearing = dirty_from_row(table_item)
            new_bearing = from_dirty_bearing(new_bearing)
            scrapped = self.scrap(new_bearing)
            if scrapped is not None:
                processed.append(scrapped)
            else:
                unprocessed.append(table_item)

            if batch_size is not None and i % batch_size == 0:
                yield processed, unprocessed

        yield processed, unprocessed
        raise StopIteration()

    def scrap_xlsx(
            self,
            path: str,
            batch_size: int | None = None) -> Generator[tuple[list[CleanBearingData], list[CleanBearingData]]]:
        df = pd.read_excel(path)
        i = 0
        processed = []
        unprocessed = []
        for index, table_item in df.iterrows():
            print(f'Обработано {i} из {len(df.index)}')
            i += 1
            new_bearing = from_clean_bearing(table_item)
            scrapped = self.scrap(new_bearing)
            if scrapped is not None:
                processed.append(scrapped)
            else:
                unprocessed.append(new_bearing)

            if batch_size is not None and batch_size % i == 0:
                yield processed, unprocessed

        yield processed, unprocessed
        raise StopIteration()

    def scrap(self, new_bearing: CleanBearingData) -> CleanBearingData | None:
        print(f'Поиск для подшипника: {new_bearing['description']}')
        variants = get_name_variants(new_bearing["description"])
        print(f'Варианты {variants}')
        for name_inv in variants:
            url = self.url % name_inv.replace(' ', '+')
            print(f'Название: {new_bearing['description']}')
            print(f'Поиск: {name_inv}')
            print(f'Поиск по URL: {url}')
            try:
                res =  self.scrap_by_url(new_bearing, url)
                if res is not None:
                    return res
            except Exception as e:
                self.log.error(f'Ошибка исполнения - {new_bearing["description"]}, e - {e}')

        return None

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        pass

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        pass

    def scrap_by_url(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        pass
