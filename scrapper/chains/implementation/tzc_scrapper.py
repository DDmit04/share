import requests
from bs4 import BeautifulSoup, Tag

from utils.compare import SIMILARITY_THRESHOLD
from scrapper.chains.chain_scrapper import ChainScrapper
from scrapper.chains.data.chain_model import ChainData
from utils.strings import to_str, to_float


class TzcScrapper(ChainScrapper):

    def __init__(self):
        super().__init__(
            'https://www.tzc.ru/search/?q=%s&s=Отправить',
            'https://www.tzc.ru',
            'www.tzc.ru'
        )

    def scrap_data(self, entity_data: ChainData, url: str) -> ChainData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('div', {'class': 'product-info__column'})
        if table is not None:
            rows = table.find_all('div', {'class': 'product-info__item'})
            for row in rows:
                title_col = row.find('span')
                if not title_col:
                    continue
                value_col = row.find('b')
                if not value_col:
                    continue
                name = title_col.get_text().replace('\xa0', ' ').strip()
                value = value_col.get_text().replace('\xa0', ' ').strip()

                if name in ['Шаг цепи:']:
                    entity_data['chain_step'] = to_float(value)
                if name in ['Диаметр валика:']:
                    entity_data['chain_val_d'] = to_float(value)
                if name in ['Диаметр ролика/ катка:']:
                    entity_data['chain_rol_d'] = to_float(value)
                if name in ['Минимальное расстояние между внутренними пластинами:']:
                    entity_data['chain_plate_dist'] = to_float(value)

            return entity_data

        return None

    def scrap_list(self, entity_data: ChainData, found: Tag) -> ChainData | None:
        items = found.find_all('div', {'class': 'search-page__item'})
        for item in items:
            title = item.find('a')
            if title:
                item_url = to_str(title.attrs.get('href'))
                name = title.get_text(separator=' ', strip=True)
                if item_url:
                    sim = self.mapper.name_similarity(name, entity_data)
                    entity_data['source_link'] = self.host + item_url
                    entity_data['source_name'] = name
                    entity_data['name_similarity'] = round(float(sim), 4)
                    if sim >= SIMILARITY_THRESHOLD:
                        new_clean = self.scrap_data(
                            entity_data=entity_data,
                            url=self.host + item_url,
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
            found = soup.find('div', {'class': 'search-page__items'})
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
