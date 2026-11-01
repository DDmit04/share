import os

import pandas as pd
import urllib3

from scrapper.bearings_online_scrapper import BearingsOnlineScrapper
from scrapper.tymoty_scrapper import TymotyScrapper

file_path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v5\\unprocessed.xlsx'
batch_size = 500

df = pd.read_excel(file_path)
i = 0

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

scrappers = [
    # SpecPromScrapper(),
    # PodshipnikRuScrapper(),
    # PodshipnikInformScrapper(),
    # AbcMechScrapper(),
    BearingsOnlineScrapper()
]
for scrapper in scrappers:
    i = 0
    for proc, unproc in scrapper.scrap_dirty_xlsx(file_path, batch_size):
        i += batch_size

        df = pd.DataFrame(proc)
        os.makedirs(f'./data/v7/processed/{scrapper.name}/', exist_ok=True)
        df.to_excel(f'./data/v7/processed/{scrapper.name}/processed_{i}.xlsx', sheet_name='processed', index=False)

        df = pd.DataFrame(unproc)
        os.makedirs(f'./data/v7/unprocessed/{scrapper.name}/', exist_ok=True)
        df.to_excel(f'./data/v7/unprocessed/{scrapper.name}/unprocessed_{i}.xlsx', sheet_name='unprocessed', index=False)
