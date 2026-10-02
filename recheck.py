import pandas as pd

def test1():
    processed_df = pd.read_excel('C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\processed.xlsx')
    unprocessed_df = pd.read_excel('C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\unprocessed.xlsx')
    unprocessed_orig_df = pd.read_excel('C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data.xlsx')

    orig_map = {}

    for index, table_item in unprocessed_orig_df.iterrows():
        orig_map[table_item['No_']] = table_item

    for index, table_item in unprocessed_df.iterrows():
        _id = table_item['No_']
        if _id in orig_map:
            del orig_map[_id]

    for index, table_item in processed_df.iterrows():
        _id = table_item['no']
        if _id in orig_map:
            del orig_map[_id]

    print(len(list(orig_map.keys())))

    df = pd.DataFrame(orig_map.values())
    df.to_excel(f'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\unprocessed_lost.xlsx',
                sheet_name='processed', index=False)

def test():
    processed_df = pd.read_excel('C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\processed.xlsx')
    unprocessed_df = pd.read_excel('C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\unprocessed.xlsx')

    processed_map = {}

    res_unprocessed = []
    for index, table_item in processed_df.iterrows():
        processed_map[table_item['no']] = table_item

    i = 0
    for index, table_item in unprocessed_df.iterrows():
        _id = table_item['No_']
        if _id not in processed_map:
            res_unprocessed.append(table_item)
        else:
            i += 1

    print(i)
    df = pd.DataFrame(res_unprocessed)
    df.to_excel(f'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v4\\unprocessed_checked.xlsx', sheet_name='processed', index=False)

if __name__ == "__main__":
    test1()