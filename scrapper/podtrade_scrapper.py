import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import SIMILARITY_THRESHOLD, bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str


class PodtradeScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://podtrade.ru/search/?q=%s',
            'https://podtrade.ru/',
            'podtrade.ru'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'product-params__table'})
        if table:
            for row in table.find_all('tr'):
                title = row.find('span', {'class': 'product-params__cell-decor'})
                value = row.find('td', {'class': 'product-params__cell'})
                if title is not None and value is not None:
                    name = title.find('span').text.strip()
                    value = value.text.strip()
                    if name in ['d внутренний']:
                        bearing['internal_d'] = float(value)
                    if name in ['D внешний']:
                        bearing['external_d'] = float(value)
                    if name in ['B ширина']:
                        bearing['width'] = float(value)
                    if name in ['Группа']:
                        bearing['type'] = value
            return bearing
        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('div', {'class': 'sv-product-card'})
        for item in bearing_list_items:
            bearing_link = item.find('a')
            if bearing_link is not None:
                bearing_url = to_str(bearing_link.attrs.get('href'))
                if bearing_url:
                    name = item.find('span', {'class': 'sv-product-card__name'}).text.strip()
                    sim = bearing_similarity(name, bearing['description'])
                    bearing['source_link'] = self.host + bearing_url
                    bearing['source_name'] = name
                    if sim >= SIMILARITY_THRESHOLD:
                        new_clean = self.scrap_bearing_data(
                            bearing=bearing,
                            url=self.host + bearing_url,
                        )
                        if new_clean is not None:
                            return new_clean
                    else:
                        print(f'Не подходит по имени: искомое - {bearing['description']}, полученное - {name}')
        return None

    def scrap_by_url(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            bearing_list = soup.find('div', {'class': 'catalog-section bx-blue'})
            if bearing_list is not None:
                return self.scrap_bearing_list(
                    bearing=bearing,
                    bearing_list=bearing_list,
                )
            else:
                print('Не найдено')
                return None
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
