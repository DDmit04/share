import re
from typing import Any

import pandas as pd
import regex

RUS_TO_LAT = str.maketrans({
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M',
    'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T',
    'У': 'Y', 'Х': 'X', 'Г': 'G', 'Д': 'D', 'З': 'Z',
    'И': 'I', 'Й': 'J', 'Л': 'L', 'Ф': 'F', 'Ц': 'C',
    'Ш': 'W', 'Щ': 'W', 'Ы': 'Y', 'Э': 'E', 'Ю': 'U', 'Я': 'Y',
    'Ь': '', 'Ъ': '', 'а': 'A', 'б': 'B', 'в': 'B', 'г': 'G',
    'д': 'D', 'е': 'E', 'ж': 'Z', 'з': 'Z', 'и': 'I', 'й': 'J',
    'к': 'K', 'л': 'L', 'м': 'M', 'н': 'H', 'о': 'O', 'п': 'P',
    'р': 'R', 'с': 'S', 'т': 'T', 'у': 'U', 'ф': 'F', 'х': 'X',
    'ц': 'C', 'ч': 'C', 'ш': 'W', 'щ': 'W', 'ы': 'Y', 'э': 'E',
    'ю': 'U', 'я': 'Y',
})

BRANDS = {
    'SKF', 'FAG', 'INA', 'NSK', 'NTN', 'KOYO', 'TIMKEN', 'NACHI',
    'CRAFT', 'MPZ', 'GPZ', 'AST', 'SNR', 'NMB', 'THK', 'IKO',
    'TORRINGTON', 'MRC', 'DODGE', 'ZKL', 'URB', 'ZVL', 'FLT',
    'PFI', 'KBC', 'FYH', 'PEER', 'IBC', 'GRW', 'GMN', 'BARDEN',
    'CX', 'ISB', 'FBJ', 'CYSD', 'NKE', 'ISO', 'FERSA', 'SIGMA',
    'KINEX', 'FKL', 'DEWULF', 'SCHMIDT', 'CARTIGLIANO', 'BAADER',
    'AKRON', 'TSA', 'RHP', 'ROLLWAY', 'MCGILL', 'AETNA',
    'SIGNAL-PACK', 'ASAM', 'NBS', 'HRB', 'BWA', 'KMR',
    'TREIF', 'YTO', 'SKL', 'ВОЛЖСКИЙ СТАНДАРТ', 'Feltre', 'МТЗ', 'John Deere', 'Claas',
    'AGCO', 'Amazone', 'CNH', 'Kuhn', 'Geringhoff', 'Krone'
}

RUS_DESC_WORDS = [
    'подшипник', 'роликовый', 'радиальный', 'шариковый', 'упорный',
    'линейный', 'сферический', 'конический', 'игольчатый', 'шарнирный',
    'роликовые', 'радиальные', 'шариковые', 'упорные', 'линейные',
    'сферические', 'конические', 'игольчатые', 'шарнирные',
    'радиально-упорные', 'радиально', 'опоры', 'опора',
    'режущий', 'шнек', 'зим', 'ooo', 'б/у', 'новый',
    'оригинал', 'натяжной', 'ступицы', 'задней', 'наружный',
    'конич', 'ролик', 'опорный', 'приводного', 'вала', 'выжимной', 'с муфтой',
    'сферический', 'цилиндрический', 'конический', 'на', 'коленвал',
    'бензопилы', 'расцепления', 'для', 'механического', 'прижима', 'передней',
    'колеса', 'флянцевый', 'скольжения', 'радиальный', 'радиально-упорный',
    'задний', 'без', 'АБС', 'внутренний', 'коренной', 'промежуточный', 'вторичного',
    'вала', 'редуктора', 'нижний', 'верхний', 'вилки', 'сцепления', 'подвесной', 'наружний',
    'выключения', 'внешний', 'внутренний', 'каретки', 'опорн', 'шквор', 'поворотный', 'с', 'шестигр',
    '.нарез', 'в', 'сборе', 'конич.ролик.', 'конич.ролиr.', 'дифференциала', 'трубы', 'опрыскивания',
    'муфтой', 'кулачкового', 'скольжения', 'ступичный', 'роликовы', 'ступ', 'Газель', 'натяжителя', ' (режущий шнек)',
    'Агрипартс', 'для', 'цепей', 'фланцевый', 'КПП'
]


def extract_bearing_codes(s):
    """Извлекает нормализованные коды подшипников из строки описания."""
    if not s or pd.isna(s):
        return []
    s = str(s).strip()

    # 1. Убираем (БРЕНД) в конце
    s = re.sub(r'\s*$[A-ZА-Я][A-ZА-Яa-zа-я\s/+\-.]*$\s*$', '', s)

    # 2. Убираем ГОСТ/DIN
    s = re.sub(r'\s+ГОСТ\s+\d+[\-]\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+ГОСТ\s+\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^ГОСТ\s+\d+\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+DIN\s+\d+', '', s)

    # 3. Убираем Grimme-коды
    s = re.sub(r'\s+Grimme\s+\S+', '', s, flags=re.IGNORECASE)

    # 4. Убираем внутренние коды компаний
    s = re.sub(r'\s+\d{8,}\b', '', s)
    s = re.sub(r'\s+\d{6,}-\d+\b', '', s)
    s = re.sub(r'\s+Е\d{7}', '', s)
    s = re.sub(r'\s+\d{3}Н\d{7}', '', s)
    s = re.sub(r'\s+С\s+\d{6}', '', s)
    s = re.sub(r'\s+\d{3}L\s+\d{6}', '', s)
    s = re.sub(r'\s+Akron\s+[\d.]+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+Signal-Pack\s+\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+Baader\s+\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+ООО\s+\S+', '', s)
    s = re.sub(r'\s+Treif\s+\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+YTO\s+\d+', '', s, flags=re.IGNORECASE)

    # 3+ компонента — БЕЗ обязательного "мм"
    s = re.sub(r'\s+\d{1,3}[хХxX]\d{1,3}[хХxX]\d{1,3}(?:[,.]\d+)?(?:\s*мм?)?\b', '', s)

    # 4c. Российский аналог (только после цифры)
    s = re.sub(r'(\d)\s+\d{4}[А-ЯH]\b', r'\1', s)

    # 4d. Короткие коды типа "9X02"
    s = re.sub(r'\s+\d[XХ]\d{2}\b', '', s)

    # 5. Убираем описательные слова
    for word in RUS_DESC_WORDS:
        s = re.sub(r'\b' + word + r'\b', '', s, flags=re.IGNORECASE)

    # 6. Конвертируем русские буквы в латиницу
    s = s.translate(RUS_TO_LAT)

    # 7. Альтернативные номера в скобках
    alt_codes = re.findall(r'$([A-Z0-9][A-Z0-9\-/]*)$', s.upper())
    s = re.sub(r'\s*$[A-Z0-9][A-Z0-9\-/]*$', '', s)

    # 8. Финальная очистка
    s = s.strip()
    if not s:
        return [c for c in alt_codes if c]
    tokens = s.upper().split()
    filtered = [t.strip('.,;:()') for t in tokens
                if t.strip('.,;:()') and t.strip('.,;:()') not in BRANDS]
    main_code = re.sub(r'-+', '-', '-'.join(filtered)).strip('-')
    result = [main_code] if main_code else []
    result.extend(c for c in alt_codes if c and c not in BRANDS)
    return result


def extract_primary_number(code: str) -> str | None:
    """Извлекает основной номер: первое число из 3+ цифр,
    при отсутствии — из 2+ цифр."""
    nums3 = re.findall(r'\d{3,}', code)
    if nums3:
        return nums3[0]
    nums2 = re.findall(r'\d{2,}', code)
    if nums2:
        return nums2[0]
    return None



def remove_bearing_type(text: str) -> str:
    i = 0
    while i < len(text) and (text[i].isalpha() and 'а' <= text[i].lower() <= 'я' or text[i] in 'ёЁ '):
        i += 1
    return text[i:]

def levenshtein_norm(a: str, b: str):
    """Нормализованное расстояние Левенштейна: 0 — разные, 1 — идентичны."""
    m, n = len(a), len(b)
    if m == 0 and n == 0:
        return 1.0
    if m == 0 or n == 0:
        return 0.0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return 1.0 - dp[m][n] / max(m, n)


def bearing_similarity(desc, src) -> float:
    """Сравнивает два описания подшипников.
    Возвращает (сходство, вердикт)."""
    desc = remove_bearing_type(desc)
    src = remove_bearing_type(src)

    codes1 = extract_bearing_codes(desc)
    codes2 = extract_bearing_codes(src)
    if not codes1 or not codes2:
        return 0.0

    best_sim = 0.0
    for c1 in codes1:
        for c2 in codes2:
            full_sim = levenshtein_norm(c1, c2)
            num1 = extract_primary_number(c1)
            num2 = extract_primary_number(c2)

            if num1 and num2:
                if num1 == num2:
                    combined = max(full_sim, 0.90)
                else:
                    num_sim = levenshtein_norm(num1, num2)
                    if num_sim < 0.95:
                        combined = min(full_sim, 0.75)
                    else:
                        combined = full_sim
            else:
                combined = full_sim

            if combined > best_sim:
                best_sim = combined

    return best_sim
