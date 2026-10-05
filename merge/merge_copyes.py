import os
import pathlib

import pandas as pd

from compare.compare import bearing_similarity
from scrapper.utils import from_clean_bearing
from utills import CleanBearingData


def merge_copyes(filepath: str, output_file):
    if not filepath:
        return
    print(f"Файлов: {len(filepath)}")

    _map = {}
    rows = []
    try:
        df = pd.read_excel(filepath)
        if len(df.index) > 0:
            for i, row in df.iterrows():
                _id = row['no']
                if _id in _map:
                    prev_value = from_clean_bearing(_map[_id])
                    row_clean = from_clean_bearing(row)
                    prev_score = map(lambda elem: 0 if elem == 0 else 0.3, [prev_value['internal_d'], prev_value['external_d'], prev_value['width']])
                    prev_score = sum(prev_score) + bearing_similarity(prev_value['source_name'], row_clean['description'])

                    row_score = map(lambda elem: 0 if elem == 0 else 0.3, [row_clean['internal_d'], row_clean['external_d'], row_clean['width']])
                    row_score = sum(row_score) + bearing_similarity(row_clean['source_name'], row_clean['description'])

                    if row_score > prev_score:
                        _map[_id] = row_clean
                    else:
                        _map[_id] = prev_score
                else:
                    rows.append(row)
                    _map[_id] = row
    except Exception as e:
        print(f"Ошибка при обработке файла {filepath}: {e}")

    print(f'Строк: {len(rows)}')
    df = pd.DataFrame(rows)
    df.to_excel(output_file, index=False)
    print(f"\nГотово! Объединённый файл: {output_file}")


if __name__ == "__main__":

    curr_version = 'v4'
    processed_files = []
    unprocessed_files = []
    for folder in ['1', '2', '3', '4']:
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

    merge_copyes(processed_files, output_file=processed_filepath, id_name='no')
    merge_copyes(unprocessed_files, output_file=unprocessed_filepath, id_name='No_')
