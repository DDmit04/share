import os
import pathlib

import pandas as pd

from utills import CleanBearingData


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
                    if row[id_name] in _map:
                        continue
                    else:
                        rows.append(row)
                        _map[row[id_name]] = True
        except Exception as e:
            print(f"Ошибка при обработке файла {filename}: {e}")

    print(f'Строк: {len(rows)}')
    df = pd.DataFrame(rows)
    df.to_excel(output_file, sheet_name='processed', index=False)
    print(f"\nГотово! Объединённый файл: {output_file}")

if __name__ == "__main__":

    curr_version = 'v4'
    for folder in ['1', '2', '3', '4']:
        input_directory = f"C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\{curr_version}\\processed\\{folder}"
        if os.path.exists(input_directory):
            output_filename = f"./data/{curr_version}/{folder}/processed.xlsx"
            os.makedirs(pathlib.Path(output_filename).parent, exist_ok=True)
            merge_excel_files(input_directory, output_filename, 'no')

        input_directory = f"C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\{curr_version}\\unprocessed\\{folder}"
        if os.path.exists(input_directory):
            output_filename = f"./data/{curr_version}/{folder}/unprocessed.xlsx"
            os.makedirs(pathlib.Path(output_filename).parent, exist_ok=True)
            merge_excel_files(input_directory, output_filename, 'No_')
