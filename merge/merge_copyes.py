import os

import pandas as pd

from compare.compare import bearing_similarity
from scrapper.utils import from_clean_bearing


def merge_copy(filepath: str, output_file: str):
    if not filepath:
        return

    _map = {}
    try:
        df = pd.read_excel(filepath)
        if len(df.index) > 0:
            for i, row in df.iterrows():
                _id = str(row['no'])
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
                        _map[_id] = prev_value
                else:
                    _map[_id] = row
    except Exception as e:
        print(f"Ошибка при обработке файла {filepath}: {e}")
        raise e

    rows = list(_map.values())
    print(f'Строк: {len(rows)}')
    df = pd.DataFrame(rows)
    df.to_excel(output_file, index=False)
    print(f"\nГотово! Объединённый файл: {output_file}")


if __name__ == "__main__":

    curr_version = 'v6'
    processed_files = []
    base_path = f"C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\merge\\data\\{curr_version}"
    filepath = f"{base_path}\\processed.xlsx"
    output_filepath = f"{base_path}\\processed_no_copy.xlsx"

    merge_copy(filepath, output_filepath)
