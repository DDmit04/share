import asyncio
import os
import threading

import pandas as pd

from scrapper.abc_mech_scrapper import AbcMechScrapper
from scrapper.arpik_scrapper import ArpikScrapper
from scrapper.podgipnik_inform_scrapper import PodshipnikInformScrapper
from scrapper.podgipnik_ru_scrapper import PodshipnikRuScrapper
from scrapper.scrapper import Scrapper
from scrapper.spec_prom_scrapper import SpecPromScrapper


def process_scrapper(_scrapper: Scrapper, version: str):
    _i = 0
    for proc, unproc in _scrapper.scrap_dirty_xlsx(file_path, batch_size):
        _i += batch_size

        _df = pd.DataFrame(proc)
        os.makedirs(f'./data/{version}/processed/{_scrapper.name}/', exist_ok=True)
        _df.to_excel(f'./data/{version}/processed/{_scrapper.name}/processed_{_i}.xlsx', sheet_name='processed', index=False)

        _df = pd.DataFrame(unproc)
        os.makedirs(f'./data/{version}/unprocessed/{_scrapper.name}/', exist_ok=True)
        _df.to_excel(f'./data/{version}/unprocessed/{_scrapper.name}/unprocessed_{_i}.xlsx', sheet_name='unprocessed',
                     index=False)


file_path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\unprocessed.xlsx'
batch_size = 500

scrappers_list = {
    SpecPromScrapper(),
    PodshipnikRuScrapper(),
    PodshipnikInformScrapper(),
    AbcMechScrapper(),
    ArpikScrapper()
}
tasks = []
for scrapper in scrappers_list:
    task = threading.Thread(target=process_scrapper, args=(scrapper, 'v5',))
    task.start()
    tasks.append(task)

for task in tasks:
    task.join()

print('DONE')
