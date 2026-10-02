import pandas as pd


def split_unprocessed(processed_filepath: str, unprocessed_filepath: str):
    df = pd.read_excel(processed_filepath)
    processed_map = {}
    res = []
    i = 0
    for index, table_item in df.iterrows():
        processed_map[table_item['no']] = table_item
        
    df = pd.read_excel(unprocessed_filepath)
    for index, table_item in df.iterrows():
        if not table_item['No_'] in processed_map:
            res.append(table_item)

    return res

if __name__ == '__main__':
    processed_path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v5\\processed.xlsx'
    unprocessed_path = 'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data.xlsx'

    unreprocessed = split_unprocessed(processed_path, unprocessed_path)

    df = pd.DataFrame(unreprocessed)
    df.to_excel(f'./unreprocessed.xlsx', sheet_name='processed', index=False)