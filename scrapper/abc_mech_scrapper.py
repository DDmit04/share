import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData


class AbcMechScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://ru.abcmechanics.com/bearings/?filter[name]=%s&filter[name_beginWith]=1&filter[name_suffix]=&filter[id_brand]=0&limit=10&filter[d_start]=&filter[dD_start]=&filter[bB_start]=&filter[d_end]=&filter[dD_end]=&filter[bB_end]=&filter[countSystem]=m',
            'https://ru.abcmechanics.com',
            'ru.abcmechanics.com'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('tr')
        for item in bearing_list_items:
            if 'title' in item.attrs:

                internal_d = bearing_list.find_next('div', {'class': 'js_listmm'})
                external_d = bearing_list.find_next('div', {'class': 'js_listmm'})
                width = bearing_list.find_next('div', {'class': 'js_listmm'})

                link = item.find('a').attrs.get('href')
                if link is not None:
                    bearing['source_link'] = link.attrs.get('href')
                else:
                    continue
                bearing['source_name'] = item.attrs['title'].strip()
                bearing['internal_d'] = float(internal_d.text)
                bearing['external_d'] = float(external_d.text)
                bearing['width'] = float(width.text)

                sim = bearing_similarity( bearing['source_name'], bearing['description'])
                if sim >= 0.85:
                    return bearing
                else:
                    print(f'Не подходит по имени: искомое - {bearing['description']}, полученное - {bearing['source_name']}')
        return None

    def scrap_by_url(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            bearing_list = soup.find('table', {'class': 'list-table stacktable large-only'})
            if bearing_list is not None:
                return self.scrap_bearing_list(
                    bearing=bearing,
                    bearing_list=bearing_list,
                )
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
