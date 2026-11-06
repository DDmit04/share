import requests
from bs4 import BeautifulSoup, Tag

from utils.compare import SIMILARITY_THRESHOLD
from utils.antibot import ChallengeError, apply_cookies, looks_like_challenge
from scrapper.chains.chain_scrapper import ChainScrapper
from scrapper.chains.data.chain_model import ChainData
from utils.strings import to_str, to_float


class EuromehanikaScrapper(ChainScrapper):

    #: Имя переменной окружения с готовым заголовком Cookie.
    COOKIE_ENV = 'EUROMEHANIKA_COOKIE'

    #: Строка Cookie из браузера. Вставлять сюда проще, чем в переменную
    #: окружения: в значении есть `%` и `$`, которые подставляет cmd/PowerShell.
    COOKIES = 'PHPSESSID=8h5icizkocxMSBpTJSlgNARVAxspcMy4; pa_js_passed=eyJ0eXBlIjoianNfcGFzc2VkIiwic2l0ZSI6InMxIiwiY2xpZW50X2tleSI6ImUyZGUxZDM1OGI5MmM0ZDc4OGQ4NGVlODNhZGM3ZDA5Y2YwMThmYzdkM2Y4MTU1MThhYzI1NWQwMzkwZTQwZTUiLCJ0cyI6MTc5Mzg2MzQyMCwibm9uY2UiOiIzYjdmYTM1NDI3M2M4NDVlOWZjYjRjZGI4YWRhZDJlOCJ9.080721167c2faadc3a1756222bea7f1d8abef639b57cacfca0f526148dcf799c; agci_webp_accept=Y; BITRIX_SM_PK=aspro_next_standart; BITRIX_SM_GUEST_ID=7181201; BITRIX_SM_AG_SMSE_H=%D0%A6%D0%B5%D0%BF%D1%8C%2006B-1%20D3%20DH; _ym_debug=null; _ym_uid=1793863425734301932; _ym_isad=2; _ga=GA1.1.762318976.1793863425; mdd=1; mycookie=777; _ga_VRNFG8KKLW=GS2.1.s1793863424$o1$g1$t1793864467$j59$l0$h0; _ym_d=1793864468; BITRIX_SM_LAST_VISIT=05.11.2026%2010%3A41%3A08'

    def __init__(self):
        super().__init__(
            'https://euromehanika.ru/catalog/?faction_type=variant&faction_word=&faction_site=variant2&form_text_name_1=&q=%s&s=Найти',
            'https://euromehanika.ru',
            'euromehanika.ru'
        )
        # Одна сессия на площадку: cookie, полученные после проверки браузера,
        # должны переиспользоваться и для страницы поиска, и для карточек товаров.
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })

    def _request(self, url: str) -> tuple[int, str]:
        """GET с ручным обходом антибот-заглушки. Возвращает пару (статус, HTML)."""
        response = self.session.get(url, headers=self.headers, verify=False, timeout=60)
        if not looks_like_challenge(response.content):
            return response.status_code, response.text
        apply_cookies(self.session, url, cookie_raw=self.COOKIES, cookie_env=self.COOKIE_ENV)
        response = self.session.get(url, headers=self.headers, verify=False, timeout=60)
        if looks_like_challenge(response.content):
            raise ChallengeError(
                'проверка браузера вернулась и с cookie: строка устарела или не '
                'подходит (привязана к IP/User-Agent). Скопируйте свежий Cookie '
                f'из браузера и обновите {self.__class__.__name__}.COOKIES.'
            )
        return response.status_code, response.text

    def scrap_data(self, entity_data: ChainData, url: str) -> ChainData | None:
        print(f'Переход по URL: {url}')
        status, html = self._request(url)
        if status != 200:
            print(f'Ошибка при запросе: {status} — {url}')
            return None
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', {'class': 'props_list nbg'})
        if table is not None:
            rows = table.find_all('tr')
            for row in rows:
                title_col = row.find('span')
                if not title_col:
                    continue
                value_col = title_col.find_next()
                if not value_col:
                    continue
                name = title_col.get_text().strip()
                value = value_col.get_text().strip()

                if name in ['Шаг (мм.):']:
                    entity_data['chain_step'] = to_float(value)
                if name in ['Диаметр валика d2 мм']:
                    entity_data['chain_val_d'] = to_float(value)
                if name in ['Диаметр ролика (мм.):']:
                    entity_data['chain_rol_d'] = to_float(value)
                if name in ['Высота пластины q мм']:
                    entity_data['chain_plate_height'] = to_float(value)
                if name in ['Расстояние между внутренними пластинами b1 мм']:
                    entity_data['chain_plate_dist'] = to_float(value)
                if name in ['Шаг цепи']:
                    entity_data['chain_step'] = to_float(value)

            return entity_data

        return None

    def scrap_list(self, entity_data: ChainData, found: Tag) -> ChainData | None:
        items = found.find_all('a', {'class': 'dark_link js-notice-block__title'})
        for item in items:
            item_url = to_str(item.attrs.get('href'))
            title = item.find('span')
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
        status, html = self._request(url)
        if status == 200:
            soup = BeautifulSoup(html, 'html.parser')
            found = soup.find('div', {'class': "ajax_load block"})
            if found is not None:
                return self.scrap_list(
                    entity_data=entity_data,
                    found=found,
                )
            else:
                print('Не найдено')
                return None
        else:
            print(f'Ошибка при запросе: {status}')
        return None
