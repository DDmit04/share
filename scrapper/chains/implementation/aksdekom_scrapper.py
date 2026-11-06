import requests
from bs4 import BeautifulSoup, Tag

from utils.compare import SIMILARITY_THRESHOLD
from scrapper.chains.chain_scrapper import ChainScrapper
from scrapper.chains.data.chain_model import ChainData
from utils.strings import decode_page, to_str, to_float


class AksdekomScrapper(ChainScrapper):

    def __init__(self):
        super().__init__(
            'https://www.aksdekom.ru/search/?search_string=%s',
            'https://www.aksdekom.ru',
            'www.aksdekom.ru'
        )

    def scrap_data(self, entity_data: ChainData, url: str) -> ChainData | None:
        print(f'Переход по URL: {url}')
        response = requests.get(url, headers=self.headers, verify=False)
        # response.text декодировал бы тело как ISO-8859-1 (если сервер не прислал
        # charset в заголовке) и русский текст превращался бы в «кракозябры».
        # Названия параметров сравниваются по кириллице, поэтому без этого
        # сравнение не срабатывало и поля оставались пустыми.
        html = decode_page(response.content)
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('div', {'class': 'row option'})
        if table is not None:
            rows = table.select('div:not(.hidden)')
            rows = [r for r in rows if r.find(True)]

            for i in range(0, len(rows), 2):
                title_col = rows[i].find('span')
                if not title_col:
                    continue
                value_col = rows[i + 1].find('span')
                if not value_col:
                    continue
                name = title_col.get_text().strip()
                value = value_col.get_text().strip()

                if name in ['Шаг (мм.):']:
                    entity_data['chain_step'] = to_float(value)
                if name in ['Диаметр ролика (мм.):']:
                    entity_data['chain_rol_d'] = to_float(value)
                if name in ['Высота пластины q мм']:
                    entity_data['chain_plate_height'] = to_float(value)
                if name in ['Расстояние между внутренними пластинами b1 мм']:
                    entity_data['chain_plate_dist'] = to_float(value)

            return entity_data

        return None

    def scrap_list(self, entity_data: ChainData, found: Tag) -> ChainData | None:
        items = found.find_all('a')
        for item in items:
            item_url = to_str(item.attrs.get('href'))
            title = item.find('h5')
            if title and item_url:
                name = title.get_text().strip()
                sim = self.mapper.name_similarity(name, entity_data)
                entity_data['source_link'] = self.host + item_url
                entity_data['source_name'] = name
                entity_data['name_similarity'] = round(float(sim), 4)
                if sim >= SIMILARITY_THRESHOLD:
                    new_clean = self.scrap_data(
                        entity_data=entity_data,
                        url=self.host + item_url,
                    )
                    if new_clean is not None:
                        return new_clean
                else:
                    print(f'Не подходит по имени: искомое - {entity_data['link']}, полученное - {name}')
        return None

    def scrap_by_url(self, entity_data: ChainData, url: str) -> ChainData | None:
        response = requests.get(url, headers=self.headers, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(decode_page(response.content), 'html.parser')
            found = soup.find('div', {'class': "search"})
            if found is not None:
                return self.scrap_list(
                    entity_data=entity_data,
                    found=found,
                )
            else:
                print('Не найдено')
                return None
        else:
            print(f'Ошибка при запросе: {response.status_code}')
        return None
