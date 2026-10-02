import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str


class PodshipnikRuScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://www.podshipnik.ru/catalog/?q=%s',
            'https://www.podshipnik.ru',
            'podshipnik.ru'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        block = soup.find('div', {'class': 'classifier-new__info'})
        if block is not None:
            rows = block.find_all('div', {'class': 'classifier-new__desc'})
            for row in rows:
                value = row.find('b')
                if value:
                    title = row.contents[0].text.strip()
                    value = value.text.strip()
                    if title in ['Внутренний диаметр d, mm:']:
                        bearing['internal_d'] = float(value)
                    if title in ['Наружный диаметр D, mm:']:
                        bearing['external_d'] = float(value)
                    if title in ['Ширина B, mm:']:
                        bearing['width'] = float(value)
                    if title in ['Вид товара:']:
                        bearing['type'] = value
            return bearing

        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('div', {'class': 'new-search__item-bodies'})
        for item in bearing_list_items:
            bearing_link = item.find('a', {'class': 'new-search__item-name'})
            if bearing_link is not None:
                bearing_url = to_str(bearing_link.attrs.get('href'))
                if bearing_url:
                    name = bearing_link.text.strip()
                    sim = bearing_similarity(name, bearing['description'])
                    bearing['source_link'] = self.host + bearing_url
                    bearing['source_name'] = name
                    bearing['bearing_similarity'] = sim
                    if sim >= 0.85:
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
            bearing_list = soup.find('div', {'class': 'new-search__content'})
            if bearing_list is not None:
                return self.scrap_bearing_list(
                    bearing=bearing,
                    bearing_list=bearing_list,
                )
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
