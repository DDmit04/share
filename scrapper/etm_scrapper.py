import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import SIMILARITY_THRESHOLD, bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str


class EtmScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://www.etm.ru/catalog?searchValue=%s',
            'https://www.etm.ru',
            'etm.ru'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'tss-v361x0-specificationsContainer'})
        if table:
            for row in table.find_all('tr'):
                title = row.find('td')
                if title is not None:
                    value = title.find_next('td')
                    if value is not None:
                        name = title.find('span').text.strip()
                        value = value.text.strip()
                        if name in ['Внутренний диаметр подшипника, мм']:
                            bearing['internal_d'] = float(value)
                        if name in ['Наружный диаметр подшипника, мм']:
                            bearing['external_d'] = float(value)
                        if name in ['Ширина подшипника, мм']:
                            bearing['width'] = float(value)
                        if name in ['Тип изделия']:
                            bearing['type'] = value
            return bearing
        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('div', {'class': 'tss-1vfn0d1-listItem-item'})
        for item in bearing_list_items:
            bearing_link = item.find('a')
            if bearing_link is not None:
                bearing_url = to_str(bearing_link.attrs.get('href'))
                if bearing_url:
                    name = bearing_link.text.strip()
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
            bearing_list = soup.find('div', {'data-testid': 'link-product-name'})
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
