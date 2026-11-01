import os
import pathlib

import pandas as pd

from scrapper.abc_mech_scrapper import AbcMechScrapper
from scrapper.arpik_scrapper import ArpikScrapper
from scrapper.etm_scrapper import EtmScrapper
from scrapper.podgipnik_inform_scrapper import PodshipnikInformScrapper
from scrapper.podshipnik_ru_scrapper import PodshipnikRuScrapper
from scrapper.podtrade_scrapper import PodtradeScrapper
from scrapper.spec_prom_scrapper import SpecPromScrapper


def merge_excel_files(input_dir, output_file, id_name: str):
    xlsx_files = [
        f for f in os.listdir(input_dir)
        if f.lower().endswith('.xlsx') and os.path.isfile(os.path.join(input_dir, f))
    ]

    if not xlsx_files:
        print("В указанной директории нет .xlsx файлов.")
        return

    print(f"Найдено файлов: {len(xlsx_files)}")

    _map = {}
    rows = []
    for filename in xlsx_files:
        filepath = os.path.join(input_dir, filename)
        try:
            df = pd.read_excel(filepath)
            if len(df.index) > 0:
                for i, row in df.iterrows():
                    if row[id_name] in _map and id_name == 'No_':
                        continue
                    else:
                        rows.append(row)
                        _map[row[id_name]] = True
        except Exception as e:
            print(f"Ошибка при обработке файла {filename}: {e}")

    print(f'Строк: {len(rows)}')
    df = pd.DataFrame(rows)
    df.to_excel(output_file, sheet_name='processed', index=False)
    print(f"\\nГотово! Объединённый файл: {output_file}")

if __name__ == "__main__":

    scrappers = [
        SpecPromScrapper(),
        PodshipnikRuScrapper(),
        PodshipnikInformScrapper(),
        AbcMechScrapper(),
        ArpikScrapper(),
        EtmScrapper(),
        PodtradeScrapper(),
    ]

    base_path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data'
    curr_version = 'v6'
    for scrapper in scrappers:
        folder = scrapper.name
        input_directory = f"{base_path}\\{curr_version}\\processed\\{folder}"
        if os.path.exists(input_directory):
            output_filename = f"./data/{curr_version}/{folder}/processed.xlsx"
            os.makedirs(pathlib.Path(output_filename).parent, exist_ok=True)
            merge_excel_files(input_directory, output_filename, 'no')

        input_directory = f"{base_path}\\{curr_version}\\unprocessed\\{folder}"
        if os.path.exists(input_directory):
            output_filename = f"./data/{curr_version}/{folder}/unprocessed.xlsx"
            os.makedirs(pathlib.Path(output_filename).parent, exist_ok=True)
            merge_excel_files(input_directory, output_filename, 'No_')
