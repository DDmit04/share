import os

import pandas as pd

from scrapper.abc_mech_scrapper import AbcMechScrapper
from scrapper.arpik_scrapper import ArpikScrapper
from scrapper.podgipnik_inform_scrapper import PodshipnikInformScrapper
from scrapper.podshipnik_ru_scrapper import PodshipnikRuScrapper
from scrapper.spec_prom_scrapper import SpecPromScrapper


def merge_results(filepaths: list[str], output_file, id_name: str):
    if not filepaths:
        return
    print(f"Файлов: {len(filepaths)}")

    _map = {}
    rows = []
    for filepath in filepaths:
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
            print(f"Ошибка при обработке файла {filepath}: {e}")

    print(f'Строк: {len(rows)}')
    df = pd.DataFrame(rows)
    df.to_excel(output_file, index=False)
    print(f"\nГотово! Объединённый файл: {output_file}")


if __name__ == "__main__":

    scrappers = [
        SpecPromScrapper(),
        PodshipnikRuScrapper(),
        PodshipnikInformScrapper(),
        AbcMechScrapper(),
        ArpikScrapper()
    ]

    curr_version = 'v6'
    processed_files = []
    unprocessed_files = []
    for scrapper in scrappers:
        folder = scrapper.name
        base_path = f"C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\merge\\data\\{curr_version}\\{folder}"
        filepath = f"{base_path}\\processed.xlsx"
        if os.path.exists(filepath):
            processed_files.append(filepath)

        filepath = f"{base_path}\\unprocessed.xlsx"
        if os.path.exists(filepath):
            unprocessed_files.append(filepath)

    res_folder = f'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\merge\\data\\{curr_version}'
    processed_filepath = f'{res_folder}\\processed.xlsx'
    unprocessed_filepath = f'{res_folder}\\unprocessed.xlsx'

    merge_results(processed_files, output_file=processed_filepath, id_name='no')
    merge_results(unprocessed_files, output_file=unprocessed_filepath, id_name='No_')



