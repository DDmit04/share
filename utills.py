import re
from typing import TypedDict, Any

import regex
import requests
from bs4 import BeautifulSoup, Tag
from requests.compat import chardet

from compare.compare import bearing_similarity


class DirtyBearingData(TypedDict):
    No_: str
    Description: str
    Blocked: str
    b_type: str


class CleanBearingData(TypedDict):
    no: str
    description: str
    dirty_type: str
    type: str
    series: str
    internal_d: float
    external_d: float
    width: float
    factory: str
    c: str
    source_name: str
    source_link: str
    bearing_similarity: float


host = 'https://specprompodshipnik.ru'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 YaBrowser/25.12.0.0 Safari/537.36"
}


def to_float(num: str) -> float:
    num = num.replace(',', '.')
    try:
        return float(num)
    except ValueError:
        return 0.0


def decode_page(raw_bytes: bytes):
    detection = chardet.detect(raw_bytes)
    correct_encoding = detection['encoding']
    return raw_bytes.decode(correct_encoding, errors='replace')


def to_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value)


def scrap_bearing_data(_id: str, description: str, _type: str, orig_name: str, url: str) -> CleanBearingData | None:
    print(f'Переход по URL: {url}')
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    block = soup.find('div', {'class': 'preview'})
    new_clean = None
    if block is not None:
        rows = block.find_all('p')
        new_clean = CleanBearingData(
            no=_id,
            description=description,
            type='',
            dirty_type=_type,
            series='',
            internal_d=0,
            external_d=0,
            width=0,
            factory='',
            c='',
            source_name='',
            source_link=url,
            bearing_similarity=0.0
        )

        title_blocks = soup.find_all('div', {'class': 'bx-breadcrumb-item'})
        for title in title_blocks:
            if title.find('i') is not None:
                text = title.find('span')
                if text is not None:
                    new_clean['type'] = text.text.strip()

        title = soup.find('h1', {'id': 'pagetitle'})
        if title is not None:
            name = title.text.strip()
            sim = bearing_similarity(name, orig_name)
            new_clean['source_name'] = title.text.strip()
            new_clean['bearing_similarity'] = sim

        first_block = True
        for row in rows:
            if row is not None:
                if row.find('b') is None:
                    content = row.get_text(separator=' ', strip=True)
                    name = content.split(':')[0].strip()
                    value = content.split(':')[1].strip().replace(',', '.')
                    if name in ['Диаметр внутренний, мм', 'd - внутренний диаметр, мм']:
                        new_clean['internal_d'] = float(value)
                    if name in ['Диаметр наружный, мм', 'D - наружный диаметр, мм']:
                        new_clean['external_d'] = float(value)
                    if name in ['Высота, мм', 'B - ширина, мм']:
                        new_clean['width'] = float(value)

                if row.find('b') is not None:
                    if not first_block:
                        break
                    first_block = False
    return new_clean
