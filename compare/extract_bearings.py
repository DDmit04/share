#!/usr/bin/env python3
"""
Извлечение поисковых идентификаторов подшипников из файла с названиями.

Файл names.txt содержит записи вида:
    "Подшипник роликовый LASKA 31681, Подшипник SKF 6209.2RS1, ..."

Скрипт:
1. Разделяет записи по заголовку "Подшипник"
2. Для каждой записи извлекает все возможные поисковые идентификаторы:
   - Основной артикул (бренд + номер)
   - Чистый номер (без бренда)
   - Альтернативные номера из скобок
   - Размеры (25x52x15)
3. Сохраняет результат в JSON

Использование:
    python extract_bearings.py [input_file] [output_file]
    python extract_bearings.py names.txt bearings_search_terms.json
"""

import re
import json
import sys
from collections import Counter


# ─── Стоп-слова: описательные слова, которые не являются артикулами ───
STOP_WORDS_LOWER = {
    # Русские — тип подшипника
    'подшипник', 'подшипники', 'подшипниковый', 'узел',
    'роликовый', 'роликовые', 'шариковый', 'шариковые',
    'радиальный', 'радиальные', 'упорный', 'упорные',
    'конический', 'конические', 'сферический', 'сферические',
    'игольчатый', 'игольчатые', 'шарнирный', 'шарнирные',
    'скольжения', 'линейный', 'линейные', 'корпусной',
    'корпусный', 'корпусные', 'фланцевый', 'фланцевые',
    'двухрядный', 'комбинированный', 'открытый', 'закрытый',
    'самосмазывающийся', 'самосмазывающиеся',
    'радиально-упорный', 'радиально-упорные', 'осевой',
    # Русские — назначение / расположение
    'опорный', 'опора', 'опоры', 'поворотный', 'направляющий',
    'натяжной', 'подвесной', 'выжимной', 'ступичный', 'ступицы',
    'каретки', 'маховика', 'шатуна', 'шатунный', 'основной',
    'режущий', 'шнек', 'цепи', 'диска', 'вала', 'компрессора',
    'генератора', 'хвостовика', 'мост', 'моста', 'колеса',
    'кулачкового', 'втулки', 'лезвия', 'мотора', 'внутренний',
    'внутринний', 'спупичный', 'ступечный', 'задний', 'передний',
    'задней', 'передней', 'наружный', 'первичного', 'вторичного',
    'дозирующего', 'шнека', 'направляющей', 'разгрузочный',
    'конечный', 'натяжения', 'эжекторной', 'дуги',
    'механического', 'прижима', 'трубы', 'опрыскивания',
    'приводного', 'коленвала', 'каленвала',
    # Русские — материал / свойство
    'нержавеющий', 'нержавеющей', 'нержавейка', 'стали',
    'бронзовый', 'бронзы', 'порошковой', 'нейлон',
    'высокотемпературный', 'пластиковый', 'цельнолитой',
    'разъемный', 'антифрикционный', 'самоустанавливающийся',
    'самоустнавливающийся', 'сдвоенный', 'рефленый',
    # Русские — предлоги / частицы / сокращения
    'в', 'с', 'и', 'на', 'без', 'из', 'для', 'от', 'одной',
    'стороны', 'двумя', 'отверстиями', 'сборе', 'корпусом',
    'корпусе', 'бортика', 'фланцем', 'к-т', 'компл', 'ак',
    'внутр.', 'часть', 'задн.', 'передн.', 'задн', 'перед',
    'ступ', 'опорн', 'шквор', 'пром-го', 'шару', 'шар.',
    'шаров.', 'шаровый', 'радиа.', 'шруса', 'гл.жел',
    'уплотн.', 'отводкой', 'мод.', 'мод', 'абс', 'abs',
    'короткий', 'длинный', 'специальный', 'кольца',
    'фланц.', 'фланц', 'ролик', 'ролиr', 'роликовы',
    'игольчитый', 'шестигр.нарез.', 'конич.',
    # Прочие
    'b/у', 'б/у', 'ooo', 'мм', 'м.',
    'gost', 'гост', ' гост',
    # Английские
    'bearing', 'thrust', 'ball', 'roller', 'needle', 'cylindrical',
    'tapered', 'spherical', 'angular', 'contact', 'radial', 'axial',
    'double', 'single', 'row', 'self', 'aligning', 'deep', 'groove',
    'miniature', 'precision', 'stainless', 'steel', 'sealed',
    'shielded', 'open', 'slide', 'plain', 'bushing', 'sleeve',
    'washer', 'insert', 'flange', 'housing', 'unit', 'block',
    'plummer', 'cartridge', 'adapter', 'nut', 'set', 'of',
    'new', 'used', 'oem', 'original', 'genuine', 'analog',
    'bore', 'hole', 'holes', 'assembly', 'for', 'life', 'with',
    'two', 'four', 'special', 'upgraded', 'upgrade',
    'bearing-thrust', 'fast', 'floating',
    # Короткие служебные
    'd', 'id', 'ad', 'lg', 'bone', 'brg', 'crc',
    'tipper', 'tie', 'd4bf', 'd4al', 'hd72', 'gen',
}


def extract_search_terms(entry: str) -> list[str]:
    """
    Извлекает все возможные поисковые идентификаторы подшипника из строки.

    Возвращает список уникальных поисковых запросов, отсортированных
    от наиболее полных (бренд + артикул) к наиболее коротким (чистый номер).

    Примеры:
        "Подшипник роликовый LASKA 31681"
            → ['LASKA 31681', '31681']
        "Подшипник 25x52x15 6205-2RSH Treif 10269"
            → ['25x52x15 6205-2RSH Treif 10269', '25x52x15', '6205-2RSH', '10269']
        "Подшипник 6-7313 ак (30313)"
            → ['6-7313', '30313']
    """
    terms = []

    # Убираем префикс "Подшипник" / "Подшипники" / "Подшипниковый узел"
    text = re.sub(r'^Подшипник[и]?\s*', '', entry, flags=re.IGNORECASE).strip()
    text = re.sub(r'^Подшипниковый\s+узел\s*', '', text, flags=re.IGNORECASE).strip()

    # 1. Альтернативные номера из скобок: "6-7313 ак (30313)"
    parens = re.findall(r'\(([^)]+)\)', text)
    skip_in_parens = {
        'мост', 'нержавеющий', 'нержавеющий.', 'нерж', 'нержавеющей стали',
        'аналог', 'аналог.', 'нержавеющей', 'стали', 'нерж.',
    }
    for p in parens:
        p = p.strip()
        if p.lower() in skip_in_parens:
            continue
        for part in re.split(r'[,;+]', p):
            part = part.strip()
            if len(part) >= 2 and re.search(r'[0-9А-Яа-яA-Za-z]', part):
                terms.append(part)

    # 2. Убираем скобки
    text_clean = re.sub(r'\s*\([^)]*\)', '', text).strip()

    # 3. Извлекаем размеры: 25x52x15, 25х52х20,6
    dim_pattern = r'\b(\d+(?:[.,]\d+)?\s*[хx×]\s*\d+(?:[.,]\d+)?(?:\s*[хx×]\s*\d+(?:[.,]\d+)?)*)\b'
    dims = re.findall(dim_pattern, text_clean)
    for d in dims:
        terms.append(re.sub(r'\s*', '', d))

    # 4. Токенизируем
    tokens = re.split(r'[\s,]+', text_clean)

    # 5. Фильтруем стоп-слова и описательные токены
    filtered = []
    for t in tokens:
        t = t.strip('.,;:«»""\'')
        if not t:
            continue
        # Убираем префикс "фланц."
        if t.lower().startswith('фланц.'):
            t = t[6:]
        if not t:
            continue
        if t.lower() in STOP_WORDS_LOWER:
            continue
        # Русское слово 4+ букв — описание, не бренд/артикул
        if re.match(r'^[а-яё]+$', t, re.IGNORECASE) and len(t) >= 4:
            continue
        if len(t) < 2:
            continue
        # Пропускаем "6mm", "20мм"
        if re.match(r'^\d+\s*mm$', t, re.IGNORECASE):
            continue
        # Пропускаем однобуквенные латинские
        if re.match(r'^[A-Za-z]$', t):
            continue
        filtered.append(t)

    # 6. Собираем поисковые запросы
    if filtered:
        # Полная строка (бренд + артикул + всё)
        terms.insert(0, ' '.join(filtered))
        # Отдельные токены с цифрами — чистые артикулы
        if len(filtered) > 1:
            for t in filtered:
                if re.search(r'[0-9]', t) and len(t) >= 2:
                    terms.append(t)

    # 7. Дедупликация с сохранением порядка
    seen = set()
    unique = []
    for t in terms:
        t = t.strip()
        if t and t not in seen and len(t) >= 2:
            seen.add(t)
            unique.append(t)

    return unique


def process_file(input_path: str, output_path: str = None) -> list[dict]:
    """
    Обрабатывает файл с названиями подшипников.

    Args:
        input_path: путь к файлу с записями
        output_path: путь для JSON-результата (None — не сохранять)

    Returns:
        Список словарей {raw, search_terms}
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # Разделяем по "Подшипник" в начале записи
    # (некоторые записи содержат внутренние запятые)
    raw_entries = re.split(
        r',\s*(?=Подшипник[и]?\s)',
        content,
        flags=re.IGNORECASE,
    )
    raw_entries = [e.strip().rstrip(',') for e in raw_entries if e.strip()]

    results = []
    for entry in raw_entries:
        terms = extract_search_terms(entry)
        results.append({'raw': entry, 'search_terms': terms})

    # Статистика
    print(f"Всего записей: {len(results)}")
    print(f"С поисковыми термами: {len([r for r in results if r['search_terms']])}")
    print(f"Без термов: {len([r for r in results if not r['search_terms']])}")

    tc = Counter(len(r['search_terms']) for r in results)
    print("\nРаспределение кол-ва термов:")
    for n in sorted(tc.keys()):
        print(f"  {n}: {tc[n]} записей")

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nРезультат сохранён: {output_path}")

    return results


if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'names.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'bearings_search_terms.json'
    process_file(input_file, output_file)
