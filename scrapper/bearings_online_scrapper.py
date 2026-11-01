import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import SIMILARITY_THRESHOLD, bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str


class BearingsOnlineScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://www.bearings-online.co.uk/browse?search-filter=%s',
            'https://www.bearings-online.co.uk',
            'www.bearings-online.co.uk'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        block = soup.find('div', {'class': 'productDetailsSection'})
        if block is not None:
            rows = block.find_all('div', {'class': 'productStatItem'})
            for row in rows:
                if row is not None:
                    title =  row.find('ya-tr-span')
                    name = title.get_text().strip()
                    value = row.find_next('ya-tr-span').get_text().strip()
                    if name in ['Dimension Bore:']:
                        bearing['internal_d'] = float(value)
                    if name in ['Dimension OD:']:
                        bearing['external_d'] = float(value)
                    if name in ['Dimension Width:']:
                        bearing['width'] = float(value)

            return bearing

        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('div', {"class": 'itemSmall'})
        for item in bearing_list_items:
            bearing_url = to_str(item.find('a').attrs.get('href'))
            if bearing_url:
                name = item.find('h3', {'class': "itemSmallTitle"}).find('ya-tr-span').text.strip()
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
            bearing_list = soup.find('div', {'class':"filterContent mainContent"})
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
