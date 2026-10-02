import re
import pandas as pd

# ─── ТРАНСЛИТЕРАЦИЯ ─────────────────────────────────────────────
RUS_TO_LAT = str.maketrans({
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M',
    'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T',
    'У': 'Y', 'Х': 'X', 'Л': 'L', 'а': 'A', 'в': 'B',
    'е': 'E', 'к': 'K', 'м': 'M', 'н': 'H', 'о': 'O',
    'р': 'P', 'с': 'C', 'т': 'T', 'у': 'Y', 'х': 'X', 'л': 'L',
})

# ─── РУССКИЕ СЛОВА ───────────────────────────────────────────────
RUS_DESC = {
    'радиально-упорные', 'самосмазывающийся', 'самосмазывающиеся',
    'комбинированный',
    'шестигр.нарез.',
    'игольчатыми', 'сферические', 'сферический', 'отверстиями',
    'поворотный', 'первичного', 'конический', 'посадочные', 'радиальный', 'посадочный',
    'радиальные', 'скольжения', 'двухрядный', 'игольчатый', 'конические', 'игольчатые',
    'шариковые', 'шариковый', 'фланцевые', 'корпусный', 'радиально', 'роликовый',
    'шарнирные', 'подшипник', 'шарнирный', 'корпусной', 'корпусные', 'роликовые',
    'фланцевый',
    'оригинал', 'открытый', 'корпусом', 'линейные', 'линейный',
    'опорный', 'режущий', 'патриот', 'упорные', 'корпуса', 'роликам', 'упорный',
    'осевой', 'аналог', 'хантер', 'корпус',
    'опора', 'двумя', 'сборе', 'опоры', 'новый',
    'шнек', 'нерж', 'вала',
    'б/у', 'шар', 'зим', 'кпп', 'ooo',
    'на', 'уз', 'шп', 'мм', 'ст',
    'и', 'в', 'с',
}


# ─── БРЕНДЫ ─────────────────────────────────────────────────────
_BRANDS_RAW = [
    'SKF', 'FAG', 'INA', 'NSK', 'NTN', 'KOYO', 'TIMKEN', 'NACHI',
    'CRAFT', 'MPZ', 'GPZ', 'AST', 'SNR', 'NMB', 'THK', 'IKO',
    'TORRINGTON', 'MRC', 'DODGE', 'ZKL', 'URB', 'ZVL', 'FLT',
    'PFI', 'KBC', 'FYH', 'PEER', 'IBC', 'GRW', 'GMN', 'BARDEN',
    'CX', 'ISB', 'FBJ', 'CYSD', 'NKE', 'ISO', 'FERSA', 'SIGMA',
    'KINEX', 'FKL', 'DEWULF', 'SCHMIDT', 'CARTIGLIANO', 'BAADER',
    'AKRON', 'TSA', 'RHP', 'ROLLWAY', 'MCGILL', 'AETNA',
    'SIGNAL-PACK', 'ASAM', 'NBS', 'HRB', 'BWA', 'KMR', 'TREIF',
    'YTO', 'REXNORD', 'MTM', 'VBF', 'VEMAG', 'NTE', 'YEL', 'YET',
    'ART', 'SILOKING', 'HAARSLIV', 'PBSNO', 'SAMICK', 'ZEN',
    'JTEKT', 'RBC', 'ZARESS', 'DPI', 'EASE', 'LINKBELT',
    'SEALMASTER', 'BROWNING', 'GRIMME', 'SCHAEFFLER',
    'NADCELLA', 'ROTHE', 'HGF', 'DYMOS', 'GEA', 'KSB', 'BIZERBA',
    'SEW', 'SEW-EURODRIVE', 'MONOSEM', 'KRONE', 'ILAPAK',
    'SEYDELMANN', 'DINROLL', 'APZ', 'DIN', 'ROLL', 'AGCO', 'CLAAS'
]
BRANDS = set()
for b in _BRANDS_RAW:
    BRANDS.add(b.upper())
    BRANDS.add(b.capitalize())
    BRANDS.add(b)


def _is_dimensions(code: str) -> bool:
    """Проверяет, выглядит ли код как размеры (10X17X12, 40X80X23MM)."""
    return bool(re.fullmatch(r'\d{1,3}X\d{1,3}(?:X\d{1,3})?(?:MM)?', code))


def extract_bearing_number(text: str) -> list[str]:
    """
    Извлекает возможные номера подшипников из произвольной строки описания.

    Возвращает список нормализованных кодов. Может быть несколько,
    если в строке есть альтернативные номера в скобках.

    Этапы:
      1. Удаление бренда в скобках в конце: (SKF), (CRAFT)
      2. Удаление ГОСТ / DIN
      3. Удаление внутренних кодов предприятий (Grimme, Akron, Vemag, ООО…)
      4. Удаление размеров (90х110х35мм, D=100мм, d=50мм)
      5. Удаление русских описательных слов
      6. Транслитерация русских букв → латиница
      7. Извлечение альтернативных номеров из скобок
      8. Сборка основного кода из оставшихся токенов

    Примеры:
        >>> extract_bearing_number("Подшипник 6306 RS")
        ['6306-RS']
        >>> extract_bearing_number("Подшипник SKF 32022")
        ['32022']
        >>> extract_bearing_number("Подшипник 6-7208А (30208)")
        ['6-7208A', '30208']
        >>> extract_bearing_number("Подшипник YAR 209-2RF Grimme B96.00073")
        ['YAR-209-2RF']
        >>> extract_bearing_number("Подшипник 80107 ГОСТ 7242-81")
        ['80107']
        >>> extract_bearing_number("Подшипник 40х80х23 мм 2208-2RS")
        ['2208-2RS']
        >>> extract_bearing_number("Подшипник 1000817")
        ['1000817']
    """
    if not text or (isinstance(text, float) and pd.isna(text)):
        return []

    s = str(text).strip()

    # ── 5. Русские описательные слова ──
    for word in RUS_DESC:
        if '.' in word:
            s = s.replace(word, '')
        else:
            s = re.sub(r'\b' + word + r'\b', '', s, flags=re.IGNORECASE)

    # ── 1. Бренд в скобках в конце ──
    s = re.sub(r'\s*$([A-ZА-Я][A-Za-zА-Яа-я]{1,15})$\s*$', '', s)

    # ── 2. ГОСТ / DIN ──
    s = re.sub(r'\s+ГОСТ\s+\d+[\-/]\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+ГОСТ\s+\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+DIN\s*\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^Din\s+Roll\s+', '', s, flags=re.IGNORECASE)

    # ── 3. Внутренние коды предприятий ──
    s = re.sub(r'\s+Grimme\s+[\w.]+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+[ЕE]\d{7}\b', '', s)
    s = re.sub(r'\s+\d[А-ЯA-Z]\d{6,}\b', '', s)
    s = re.sub(r'\s+ООО\s+\S+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+Akron\s+[\d.]+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+SILOKING\s+\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+Pbsno:\s*\d+\s+[\d.]+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+Haarslev\s+', ' ', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+С\s+\d{6}\b', '', s)
    s = re.sub(r'\s+\d{4}\.[A-Z]{2}\d{2}\.\d{3}\.\d{2}\b', '', s)
    s = re.sub(r'\s+Vemag\s+\d+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+\d{3}-\d{2}-\d{3}\b', '', s)

    # ── 4. Размеры ──
    s = re.sub(
        r'\s+\d{1,3}[хХxX]\d{1,3}(?:[хХxX]\d{1,3})?(?:[,.]\d+)?\s*мм?\b',
        '', s,
    )
    s = re.sub(
        r'\s+\d{1,3}\s*мм\s*D\s*=\s*\d{1,3}\s*мм\s*d\s*=\s*\d{1,3}\s*мм',
        '', s, flags=re.IGNORECASE,
    )
    s = re.sub(r'\s+\d{1,3}x\d{1,3}\s*мм?\b', '', s)
    s = re.sub(
        r'\s+\d{1,3}x\d{1,3}x\d{1,3}[,.]?\d*\s*мм?\b',
        '', s,
    )
    s = re.sub(r'\s*[dD]\s*=\s*\d{1,3}(?:\s*мм?)?', '', s, flags=re.IGNORECASE)

    # ── 6. Транслитерация ──
    s = s.translate(RUS_TO_LAT)

    # ── 7. Альтернативные номера в скобках ──
    alt_codes = []
    for m in re.finditer(r'([A-Z0-9][A-Z0-9\-. ]*)', s.upper()):
        raw = m.group(1).strip()
        code = re.sub(r'\s+', '-', raw)
        code = re.sub(r'-+', '-', code).strip('-')
        if code and code not in BRANDS and not _is_dimensions(code):
            alt_codes.append(code)
    s = re.sub(r'\s*$[^)]*$', '', s)

    # ── 8. Сборка ──
    s = s.strip()
    if not s:
        seen, result = set(), []
        for c in alt_codes:
            if c not in seen:
                seen.add(c)
                result.append(c)
        return result

    tokens = s.upper().split()
    filtered = [t.strip('.,;:()=') for t in tokens
               if t.strip('.,;:()=') and t.strip('.,;:()=') not in BRANDS]
    main_code = '-'.join(filtered)
    main_code = re.sub(r'-+', '-', main_code).strip('-')

    result = []
    if main_code:
        result.append(main_code)
    seen = {main_code} if main_code else set()
    for c in alt_codes:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result if result else []
