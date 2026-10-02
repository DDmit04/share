import os

import pandas as pd

from scrapper.podgipnik_inform_scrapper import PodshipnikInformScrapper
from scrapper.scrapper import Scrapper
from scrapper.utils import from_clean_bearing


def reprocess(processor: Scrapper, filepath: str):
    df = pd.read_excel(filepath)
    res = []
    unres = []
    i  = 0
    for index, table_item in df.iterrows():
        print(f'Обработано {i} из {len(df.index)}')
        item = from_clean_bearing(table_item)
        url = item['source_link']
        reprocessed = processor.scrap_bearing_data(item, url)
        if reprocessed:
            res.append(reprocessed)
        else:
            unres.append(item)
        i += 1
    return res, unres


if __name__ == "__main__":
    path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\split\\unprocesed_splitted_4.xlsx'
    reprocessed, unreprocessed = reprocess(processor=PodshipnikInformScrapper(), filepath=path)

    df = pd.DataFrame(reprocessed)
    df.to_excel(f'./reprocessed_4.xlsx', sheet_name='processed', index=False)

    if unreprocessed:
        df = pd.DataFrame(unreprocessed)
        df.to_excel(f'./unreprocessed_4.xlsx', sheet_name='processed', index=False)
