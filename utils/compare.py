"""Примитивы сравнения названий: строки, коды и расстояние между ними.

Здесь нет никакой предметной логики: как именно сравнивать названия, решает
маппер (`ScrapperMapper.name_similarity` и `_name_similarity` его наследников).
Этот модуль даёт только то, чем они пользуются — общую нормализацию строк,
расстояние Левенштейна, код без разделителей и порог приёмки.
"""

import re
from typing import Any

import pandas as pd

#: Минимальное сходство, при котором найденная запись считается рабочим результатом.
SIMILARITY_THRESHOLD = 0.85


def levenshtein_norm(a: str, b: str) -> float:
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


CODE_SEPARATORS_RE = re.compile(r'[\s\-_.]+')


def comparable_code(code: str) -> str:
    """Код без разделителей: «5592312.100» и «5592312-100» — один артикул."""
    return CODE_SEPARATORS_RE.sub('', code or '')


NON_ALNUM_RE = re.compile(r'[^0-9a-zа-яё]+')


def comparable_text(text: Any) -> str:
    """Название товара в виде, пригодном для построчного сравнения.

    Нижний регистр, вместо разделителей — один пробел, всё, кроме букв и
    цифр, выброшено: «Цепь 06B-1, EMT» → «цепь 06b 1 emt».

    Это самая общая нормализация: она не знает ни обозначений цепей, ни
    номеров-артикулов. Так сравнивает названия базовая реализация
    `ScrapperMapper._name_similarity`; наследники разбирают маркировку.
    """
    if text is None or pd.isna(text):
        return ''
    return ' '.join(NON_ALNUM_RE.sub(' ', str(text).lower()).split())
