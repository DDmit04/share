import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import SIMILARITY_THRESHOLD, bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str, to_float


class TymotyScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://www.tymoty.cz/hledani/?q=%s',
            'https://www.tymoty.cz',
            'www.tymoty.cz'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        block = soup.find('span', {'class': 'in-user-text__block'}).find('table')
        if block is not None:
            rows = block.find_all('tr')
            for row in rows:
                if row is not None:
                    title = row.find('td')
                    if not title:
                        continue
                    name = title.get_text().strip()
                    value = title.find_next().get_text().strip()
                    if name in ['Vnitřní průměr (d)']:
                        bearing['internal_d'] = to_float(value)
                    if name in ['Vnější průměr (D)', 'Vnější rozměr / Délka (D/L)']:
                        bearing['external_d'] = to_float(value)
                    if name in ['Šířka (B)', 'Celková šířka (B)']:
                        bearing['width'] = to_float(value)

            return bearing

        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('a')
        for item in bearing_list_items:
            bearing_url = to_str(item.attrs.get('href'))
            if bearing_url:
                name = item.text.strip()
                sim = bearing_similarity(name, bearing['description'])
                bearing['source_link'] = self.host + bearing_url
                bearing['source_name'] = name
                if sim >= SIMILARITY_THRESHOLD:
                    new_clean = self.scrap_bearing_data(
                        bearing=bearing,
                        url=bearing_url,
                    )
                    if new_clean is not None:
                        return new_clean
                else:
                    print(f'Не подходит по имени: искомое - {bearing['description']}, полученное - {name}')
        return None

    def scrap_by_url(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        response = requests.get(url, headers=self.headers, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            bearing_list = soup.find('ul', {'class': "list-products-row js-product-list"})
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
