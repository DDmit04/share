import pandas as pd

from scrapper.utils import from_clean_bearing


def split_zeros(filepath: str):
    df = pd.read_excel(filepath)
    res = []
    unres = []
    i = 0
    for index, table_item in df.iterrows():
        print(f'Обработано {i} из {len(df.index)}')
        item = from_clean_bearing(table_item)
        if item['internal_d'] == 0 or item['internal_d'] == 0 or item['width'] == 0:
            unres.append(item)
        else:
            res.append(item)

        i += 1

    return res, unres

if __name__ == '__main__':
    path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\reprocess\\reprocessed_3.xlsx'
    reprocessed, unreprocessed = split_zeros(filepath=path)

    df = pd.DataFrame(reprocessed)
    df.to_excel(f'./processed_splitted_4.xlsx', sheet_name='processed', index=False)

    if unreprocessed:
        df = pd.DataFrame(unreprocessed)
        df.to_excel(f'./unprocesed_splitted_4.xlsx', sheet_name='processed', index=False)