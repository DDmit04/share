"""Мэппинг «описание подшипника -> варианты поисковых запросов».

Данные лежат рядом с модулем; файл читается при первом обращении,
а не при импорте, чтобы пакет можно было импортировать без xlsx.
"""

from pathlib import Path

import pandas as pd

_DEFAULT_PATH = Path(__file__).resolve().parent / "имена_без_русских_слов_v3.xlsx"
_names: dict[str, list[str]] | None = None


def get_names(names_filepath: str | Path | None = None) -> dict[str, list[str]]:
    """Читает xlsx с колонками Description и Search (' | '-разделённые варианты)."""
    path = Path(names_filepath) if names_filepath else _DEFAULT_PATH
    df = pd.read_excel(path)
    names: dict[str, list[str]] = {}
    for _, row in df.iterrows():
        name = str(row["Description"]).strip()
        variants = [part.strip() for part in str(row["Search"]).split("|") if part.strip()]
        names[name] = variants
    return names


def _load() -> dict[str, list[str]]:
    global _names
    if _names is None:
        _names = get_names()
    return _names


def get_name_variants(name: str) -> list[str]:
    """Варианты поиска для описания; пустой список, если описания нет в мэппинге."""
    return _load().get(str(name).strip(), [])
