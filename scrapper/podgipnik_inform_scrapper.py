import regex
import requests
from bs4 import BeautifulSoup, Tag

from compare.compare import bearing_similarity
from scrapper.scrapper import Scrapper
from utills import CleanBearingData, to_str, decode_page, to_float


class PodshipnikInformScrapper(Scrapper):

    def __init__(self):
        super().__init__(
            'https://podshipnikinform.ru/search.php?str=%s',
            'https://podshipnikinform.ru/',
            'podshipnikinform.ru'
        )



    def scrap_bearing_data(self, bearing: CleanBearingData, url: str) -> CleanBearingData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            decoded_content = decode_page(response.content)
            soup = BeautifulSoup(decoded_content, 'html.parser')
            type_block = soup.find('strong')

            type_parts = []
            if type_block is not None:
                for part in type_block.text.split(' '):
                    if regex.search(r'\p{IsCyrillic}', part):
                        type_parts.append(part)
                    else:
                        break
                bearing['type'] = ' '.join(type_parts)
            type_parts.clear()

            block = soup.find('em')
            if block is not None:
                titles = block.find_all('div', {'class': 'first'})
                values = block.find_all('div', {'class': 'two_fifth'})
                pairs = zip(titles, values)
                for title, value in pairs:
                    title_text = title.text
                    value_formatted = value.text.replace(',', '.')
                    if title_text in ['Внутренний диаметр d, mm', 'Диаметр внутренний, мм', 'd - внутренний диаметр, мм', 'd - диаметр внутренний, мм']:
                        bearing['internal_d'] = to_float(value_formatted)
                    if title_text in ['Наружный диаметр D, mm', 'Диаметр наружный, мм', 'D - наружный диаметр, мм', 'D - диаметр внешний, мм']:
                        bearing['external_d'] = to_float(value_formatted)
                    if title_text in ['Ширина B, mm', 'Высота, мм', 'B - ширина, мм', 'B/c - высота, мм']:
                        bearing['width'] = to_float(value_formatted)
                return bearing

        return None

    def scrap_bearing_list(self, bearing: CleanBearingData, bearing_list: Tag) -> CleanBearingData | None:
        bearing_list_items = bearing_list.find_all('a')
        for bearing_link in bearing_list_items:
            bearing_url = to_str(bearing_link.attrs.get('href'))
            if bearing_url:
                if bearing_url in ['//podshipnikinform.ru/', "/allsearch.html"]:
                    continue
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
            decoded_content = decode_page(response.content)
            soup = BeautifulSoup(decoded_content, 'html.parser')
            bearing_list = soup.find('div', {'id': 'cont_txt'})
            if bearing_list is not None:
                return self.scrap_bearing_list(
                    bearing=bearing,
                    bearing_list=bearing_list,
                )
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
