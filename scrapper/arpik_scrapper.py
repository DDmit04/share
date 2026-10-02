import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str


class ArpikScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://arpik.ru/catalog?q=%s',
            'https://arpik.ru',
            'arpik.ru'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        block = soup.find('dl', {'class': 'spec-section__list'})
        if block is not None:
            props_blocks = block.find_all('div')
            for prop in props_blocks:
                title_block =  prop.find('dt')
                value_block = prop.find('dd')
                if value_block is not None and title_block is not None:
                    title = title_block.text.strip()
                    value = value_block.text.strip()
                    if title in ['Внутренний диаметр (d)']:
                        bearing['internal_d'] = float(value.split(' ')[0])
                    if title in ['Наружный диаметр (D)']:
                        bearing['external_d'] = float(value.split(' ')[0])
                    if title in ['Ширина (B)']:
                        bearing['width'] = float(value.split(' ')[0])
                    if title in ['Тип']:
                        bearing['type'] = value

            return bearing

        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('article', {'class': 'mobile-product-row'})
        for item in bearing_list_items:
            bearing_title = item.find('a', {'class': 'card-link-overlay'})
            if bearing_title is not None:
                bearing_url = to_str(bearing_title.attrs.get('href'))
                if bearing_url:
                    name = bearing_title.attrs.get('aria-label')
                    sim = bearing_similarity(name, bearing['description'])
                    bearing['source_link'] = self.host + bearing_url
                    bearing['source_name'] = name
                    if sim >= 0.85:
                        return self.scrap_bearing_data(
                            bearing=bearing,
                            url=self.host + bearing_url,
                        )
                    else:
                        print(f'Не подходит по имени: искомое - {bearing['description']}, полученное - {name}')
        return None

    def scrap_by_url(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            bearing_list = soup.find('div', {'class': 'compact-list'})
            if bearing_list is not None:
                return self.scrap_bearing_list(
                    bearing=bearing,
                    bearing_list=bearing_list,
                )
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
