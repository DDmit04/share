import os
import pathlib

import pandas as pd

from utills import CleanBearingData


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
                    if row[id_name] in _map:
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

    merge_results(processed_files, output_file=processed_filepath, id_name='no')
    merge_results(unprocessed_files, output_file=unprocessed_filepath, id_name='No_')



