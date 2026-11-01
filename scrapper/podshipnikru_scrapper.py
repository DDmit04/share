import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import SIMILARITY_THRESHOLD, bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str


class PodshipnikRuScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://podshipnikru.com/katalog/search/?q=%s',
            'https://podshipnikru.com/',
            'podshipnikru.com'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        props = soup.find_all('div', {'class': 'prop'})
        if props:
            for prop in props:
                title = prop.find('div', {'class': 'name'})
                value = prop.find('div', {'class': 'value'})
                if title is not None and value is not None:
                    name = title.find('span').text.strip()
                    value = value.find('span').text.strip()
                    if name in ['Внутренний диаметр d']:
                        bearing['internal_d'] = float(value)
                    if name in ['Внешний диаметр D']:
                        bearing['external_d'] = float(value)
                    if name in ['Ширина B']:
                        bearing['width'] = float(value)
            return bearing
        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('div', {'class': 'catalog_item main_item_wrapper item_wrap s'})
        for item in bearing_list_items:
            bearing_link = item.find('a', {'class': 'dark_link'})
            if bearing_link is not None:
                bearing_url = to_str(bearing_link.attrs.get('href'))
                if bearing_url:
                    name = bearing_link.find('span').text.strip()
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
            bearing_list = soup.find('div', {'class': 'catalog_block items block_list'})
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
