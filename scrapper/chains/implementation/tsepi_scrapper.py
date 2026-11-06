import requests
from bs4 import BeautifulSoup, Tag

from utils.compare import SIMILARITY_THRESHOLD
from scrapper.chains.chain_scrapper import ChainScrapper
from scrapper.chains.data.chain_model import ChainData
from utils.strings import to_str, to_float


class TsepiScrapper(ChainScrapper):

    def __init__(self):
        super().__init__(
            'https://tsepi.su/?s=%s',
            'https://tsepi.su',
            'tsepi.su'
        )

    def scrap_data(self, entity_data: ChainData, url: str) -> ChainData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'responsive'})
        if table is not None:
            headers = table.find('tr')
            if not headers:
                return None
            values = headers.find_next('tr')
            if not values:
                return None

            headers = headers.find_all('td')
            values = values.find_all('td')
            _map = zip(headers, values)
            for title_col, value_col in _map:
                name = title_col.get_text().replace('\xa0', ' ').strip()
                value = value_col.get_text().replace('\xa0', ' ').strip()

                if name in ['Шаг  P  mm']:
                    entity_data['chain_step'] = to_float(value)
                if name in ['Диаметр ролика  d1 max  mm']:
                    entity_data['chain_rol_d'] = to_float(value)
                if name in ['Ширина между внутренними пластинами  b1 min  mm']:
                    entity_data['chain_plate_dist'] = to_float(value)
                if name in ['Диаметр валика  d2 max  mm']:
                    entity_data['chain_val_d'] = to_float(value)
                if name in ['Высота пластины  h2 max  mm']:
                    entity_data['chain_plate_height'] = to_float(value)

            return entity_data

        return None

    def scrap_list(self, entity_data: ChainData, found: Tag) -> ChainData | None:
        items = found.find_all('article')
        for item in items:
            title = item.find('a')
            if title:
                item_url = to_str(title.attrs.get('href'))
                name = title.get_text().strip()
                if item_url:
                    sim = self.mapper.name_similarity(name, entity_data)
                    entity_data['source_link'] = self.host + item_url
                    entity_data['source_name'] = name
                    entity_data['name_similarity'] = round(float(sim), 4)
                    if sim >= SIMILARITY_THRESHOLD:
                        new_clean = self.scrap_data(
                            entity_data=entity_data,
                            url=item_url,
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
            found = soup.find('div', {'class': 'search-page'})
            if found is not None:
                return self.scrap_list(
                    entity_data=entity_data,
                    found=found,
                )
            else:
                print('Не найдено')
                return None
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
