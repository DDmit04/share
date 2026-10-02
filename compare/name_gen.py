import pandas as pd



def get_names(names_filepath: str):
    name_df = pd.read_excel(names_filepath)
    for i, row in name_df.iterrows():
        name = row['Description']
        names_variants = row['Search'].split(' | ')
        NAMES[name] = names_variants

NAMES = {}
get_names('C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\compare\\имена_поиска_без_брендов.xlsx')

def get_name_variants(name: str) -> list[str]:
    return NAMES.get(name, [])