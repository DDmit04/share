import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import SIMILARITY_THRESHOLD, bearing_similarity
from scrapper.chains.chain_scrapper import ChainScrapper
from scrapper.chains.model import ChainData
from scrapper.utils import to_str, to_float


class EuromehanikaScrapper(ChainScrapper):

    def __init__(self):
        super().__init__(
            'https://nt-g.ru/product/?q=%s&where=0',
            'https://nt-g.ru/',
            'nt-g.ru'
        )

    def scrap_data(self, entity_data: ChainData, url: str) -> ChainData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'props_block__wrapper'})
        if table is not None:
            rows = table.find_all('tr')
            for row in rows:
                title_col = row.find('span')
                if not title_col:
                    continue
                value_col = title_col.find_next()
                if not value_col:
                    continue
                name = title_col.get_text().strip()
                value = value_col.get_text().strip()

                if name in ['Шаг (мм.):']:
                    entity_data['chain_step'] = to_float(value)
                if name in ['Диаметр валика, мм']:
                    entity_data['chain_val_d'] = to_float(value)
                if name in ['Диаметр ролика/ катка, мм']:
                    entity_data['chain_rol_d'] = to_float(value)
                if name in ['Минимальное расстояние между внутренними пластинами, мм']:
                    entity_data['chain_plate_dist'] = to_float(value)
            
            return entity_data

        return None

    def scrap_list(self, entity_data: ChainData, bearing_list: Tag) -> ChainData | None:
        bearing_list_items = bearing_list.find_all('a', {'class': 'dark_link switcher-title js-popup-title js-replace-link'})
        for item in bearing_list_items:
            bearing_url = to_str(item.attrs.get('href'))
            title = item.find('span')
            if title and bearing_url:
                name = title.get_text().strip()
                sim = bearing_similarity(name, entity_data['link'])
                entity_data['source_link'] = self.host + bearing_url
                entity_data['source_name'] = name
                if sim >= SIMILARITY_THRESHOLD:
                    new_clean = self.scrap_data(
                        entity_data=entity_data,
                        url=self.host + bearing_url,
                    )
                    if new_clean is not None:
                        return new_clean
                else:
                    print(f'Не подходит по имени: искомое - {entity_data['link']}, полученное - {name}')
        return None

    def scrap_by_url(self, entity_data: ChainData, url: str) -> ChainData | None:
        response = requests.get(url, headers=self.headers, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            bearing_list = soup.find('div', {'id': "table-scroller-wrapper"})
            if bearing_list is not None:
                return self.scrap_list(
                    entity_data=entity_data,
                    bearing_list=bearing_list,
                )
            else:
                print('Не найдено')
                return None
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
