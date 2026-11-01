import re

import pandas as pd

from scrapper.utils import from_clean_bearing, res_from_clean_bearing
from utills import ResBearingData


def map_to_res(input_file: str, output_file: str):
    df = pd.read_excel(input_file)
    res_bearings: list[ResBearingData] = []
    _map = {}
    for index, row in df.iterrows():
        bearing = from_clean_bearing(row)
        res_bearing = res_from_clean_bearing(bearing)
        if str(res_bearing['type']) != 'nan':
            print(res_bearing['no'], str(res_bearing['type']), type(res_bearing['type']))
            res_bearing['type'] = res_bearing['type'].replace('Подшипники', 'Подшипник')
            res_bearing['type'] = res_bearing['type'].replace('шариковые', 'шариковый')
            res_bearing['type'] = res_bearing['type'].replace('радиальные', 'радиальный')
            res_bearing['type'] = res_bearing['type'].replace('радиально-упорные', 'радиально-упорный')
            res_bearing['type'] = res_bearing['type'].replace('конические', 'конический')
            res_bearing['type'] = res_bearing['type'].replace('сферические', 'сферический')
            res_bearing['type'] = res_bearing['type'].replace('Шариковый радиальный однорядный', 'Подшипник шариковый радиальный однорядный')
            res_bearing['type'] = res_bearing['type'].replace('Роликовый конический', 'Подшипник роликовый конический')
            res_bearing['type'] = res_bearing['type'].replace('Роликовый сферический', 'Подшипник роликовый сферический')
            res_bearing['type'] = res_bearing['type'].replace('Шариковый самоустанавливающийся', 'Подшипник шариковый самоустанавливающийся')
            res_bearing['type'] = res_bearing['type'].replace('Роликовый цилиндрический', 'Подшипник роликовый цилиндрический')
            res_bearing['type'] = res_bearing['type'].replace('Корпусной подшипник', 'Подшипник корпусной')
            res_bearing['type'] = res_bearing['type'].replace('Ступичный подшипник', 'Подшипник ступичный')
            res_bearing['type'] = res_bearing['type'].replace('Шариковый радиальный однорядный', 'Подшипник шариковый радиальный однорядный')
            res_bearing['type'] = res_bearing['type'].replace('Ступичный подшипник', 'Подшипник ступичный')
            res_bearing['type'] = res_bearing['type'].replace('Ступичный подшипник', 'Подшипник ступичный')
            res_bearing['type'] = res_bearing['type'].replace('упортные', 'упорный')

            if not bool(re.match(r'[\u0400-\u04FFА-ЯА]', res_bearing['source_name'])):
                res_bearing['source_name'] = str(res_bearing['type']) + ' ' + str(res_bearing['source_name'])

        res_bearings.append(res_bearing)
        _map[res_bearing['no']] = res_bearing

    df = pd.DataFrame({
        'Но.': [v['no'] for v in res_bearings],
        'Описание': [v['description'] for v in res_bearings],
        'Тип подшипника (Шариковый/Роликовый и т.д.)': [v['type'] for v in res_bearings],
        'Серия (6000/6200/6300 и т.д.)': ['' for v in res_bearings],
        'Внутренний диаметр (d), мм': [v['internal_d'] for v in res_bearings],
        'Наружный диаметр (D), мм': [v['external_d'] for v in res_bearings],
        'Ширина (B/T), мм': [v['width'] for v in res_bearings],
        'Исполнение, (Open, ZZ, 2RS и т.п.)': ['' for v in res_bearings],
        'Радиальный зазор, При наличии: С3, С4': ['' for v in res_bearings],
        'Источник, ссылка на сайт, с которого взята информация': ['' for v in res_bearings],
        'name': [v['source_name'] for v in res_bearings],
        'link': [v['source_link'] for v in res_bearings],
    })

    df.to_excel(output_file, sheet_name='processed', index=False)



if __name__ == '__main__':
    map_to_res(
        'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\data\\v5\\processed_no_copy.xlsx',
        'C:\\Users\\d.dmitrochenkov\\workspace\\scrapper\\result\\result.xlsx'
    )
