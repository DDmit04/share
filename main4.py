import os

import pandas as pd

from scrapper.abc_mech_scrapper import AbcMechScrapper
from scrapper.podgipnik_inform_scrapper import PodshipnikInformScrapper
from scrapper.podgipnik_ru_scrapper import PodshipnikRuScrapper

file_path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\unprocessed.xlsx'
batch_size = 500

df = pd.read_excel(file_path)
i = 0

scrappers = [
    # SpecPromScrapper(),
    # PodshipnikRuScrapper(),
    # PodshipnikInformScrapper(),
    AbcMechScrapper()
]
for scrapper in scrappers:
    i = 0
    for proc, unproc in scrapper.scrap_dirty_xlsx(file_path, batch_size):
        i += batch_size

        df = pd.DataFrame(proc)
        os.makedirs(f'./data/v4/processed/4/', exist_ok=True)
        df.to_excel(f'./data/v4/processed/4/processed_{i}.xlsx', sheet_name='processed', index=False)

        df = pd.DataFrame(unproc)
        os.makedirs(f'./data/v4/unprocessed/4/', exist_ok=True)
        df.to_excel(f'./data/v4/unprocessed/4/unprocessed_{i}.xlsx', sheet_name='unprocessed', index=False)
