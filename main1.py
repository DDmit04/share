import os
import sys

import pandas as pd

from scrapper.abc_mech_scrapper import AbcMechScrapper
from scrapper.arpik_scrapper import ArpikScrapper
from scrapper.podgipnik_inform_scrapper import PodshipnikInformScrapper
from scrapper.podgipnik_ru_scrapper import PodshipnikRuScrapper
from scrapper.spec_prom_scrapper import SpecPromScrapper

version = 'v6'
file_path = f'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v5\\unprocessed.xlsx'
batch_size = 500

df = pd.read_excel(file_path)
i = 0

scrappers = {
    '1': SpecPromScrapper(),
    '2': PodshipnikRuScrapper(),
    '3': PodshipnikInformScrapper(),
    '4': AbcMechScrapper(),
    '5': ArpikScrapper()
}
scrapper = scrappers[sys.argv[1]]
for proc, unproc in scrapper.scrap_dirty_xlsx(file_path, batch_size):
    i += batch_size

    df = pd.DataFrame(proc)
    os.makedirs(f'./data/{version}/processed/{scrapper.name}/', exist_ok=True)
    df.to_excel(f'./data/{version}/processed/{scrapper.name}/processed_{i}.xlsx', sheet_name='processed', index=False)

    df = pd.DataFrame(unproc)
    os.makedirs(f'./data/{version}/unprocessed/{scrapper.name}/', exist_ok=True)
    df.to_excel(f'./data/{version}/unprocessed/{scrapper.name}/unprocessed_{i}.xlsx', sheet_name='unprocessed',
                index=False)
