import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str


class ArmTekScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://bergab.ru/search/?text=%s&r1=',
            'https://bergab.ru',
            'bergab.ru'
        )

    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        block = soup.find('div', {'class': 'preview'})
        if block is not None:
            rows = block.find_all('p')
            title_blocks = soup.find_all('div', {'class': 'bx-breadcrumb-item'})
            for title in title_blocks:
                if title.find('i') is not None:
                    text = title.find('span')
                    if text is not None:
                        bearing['type'] = text.text.strip()

            title = soup.find('h1', {'id': 'pagetitle'})
            if title is not None:
                name = title.text.strip()
                sim = bearing_similarity(name, bearing['description'])
                bearing['source_name'] = title.text.strip()
                bearing['bearing_similarity'] = sim

            first_block = True
            for row in rows:
                if row is not None:
                    if row.find('b') is None:
                        content = row.get_text(separator=' ', strip=True)
                        name = content.split(':')[0].strip()
                        value = content.split(':')[1].strip().replace(',', '.')
                        if name in ['Диаметр внутренний, мм', 'd - внутренний диаметр, мм']:
                            bearing['internal_d'] = float(value)
                        if name in ['Диаметр наружный, мм', 'D - наружный диаметр, мм']:
                            bearing['external_d'] = float(value)
                        if name in ['Высота, мм', 'B - ширина, мм']:
                            bearing['width'] = float(value)

                    if row.find('b') is not None:
                        if not first_block:
                            break
                        first_block = False
            return bearing

        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('td', {'class': 'shop__item-search shop__item-search--title'})
        for item in bearing_list_items:
            bearing_link = item.find('a')
            if bearing_link is not None:
                bearing_url = to_str(bearing_link.attrs.get('href'))
                if bearing_url:
                    name = bearing_link.text.strip()
                    sim = bearing_similarity(name, bearing['description'])
                    bearing['source_link'] = self.host + bearing_url
                    bearing['source_name'] = name
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
            bearing_list = soup.find('tbody')
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
