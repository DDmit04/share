import re
from typing import TypeVar, Any

import regex
from charset_normalizer import from_bytes

def split_description(description: str) -> tuple[list[str], list[str]]:
    name_split = description.split(' ')
    type_parts = []
    name_parts = []
    for n_part in name_split:
        if regex.search(r'\p{IsCyrillic}', n_part) is not None and not re.search(r'\d', n_part):
            type_parts.append(n_part)
        else:
            name_parts.append(n_part)

    return type_parts, name_parts

def to_float(num: str) -> float:
    num = num.replace(',', '.')
    num = num.split(' ')[0]
    try:
        return float(num)
    except ValueError:
        return 0.0


_CHARSET_RE = re.compile(rb"""charset\s*=\s*["']?([\w\-]+)""", re.IGNORECASE)


def _declared_charset(raw_bytes: bytes, limit: int = 4096) -> str | None:
    """Кодировка из <meta charset=...> в начале документа (если она есть)."""
    match = _CHARSET_RE.search(raw_bytes[:limit])
    if match is None:
        return None
    try:
        name = match.group(1).decode("ascii").lower()
    except UnicodeDecodeError:
        return None
    # UTF-8 проверяется строгим декодированием, отдельно его не возвращаем.
    if name in ("utf-8", "utf8"):
        return None
    return name


def decode_page(raw_bytes: bytes) -> str:
    """Декодирует тело страницы, не доверяя заголовку `Content-Type`.

    `requests` берёт кодировку из заголовка ответа, а если `charset` в нём не
    указан — по умолчанию считает тело `ISO-8859-1`. Для русских страниц без
    явного charset это и даёт «кракозябры» вместо кириллицы. Поэтому байты
    декодируем сами, по порядку: строгий UTF-8 -> charset из `<meta>` ->
    cp1251 -> детектор `charset-normalizer` (зависимость `requests`, уже есть
    в requirements).

    Строгий UTF-8 идёт первым, потому что это надёжный признак: однобайтовая
    кириллица (cp1251/koi8-r) валидным UTF-8 не является и упадёт с
    `UnicodeDecodeError`, а вот обратное неверно — cp1251 декодирует почти
    любые байты, поэтому пробовать её раньше UTF-8 нельзя.
    """
    if not raw_bytes:
        return ""

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        pass

    declared = _declared_charset(raw_bytes)
    for encoding in (declared, "cp1251"):
        if not encoding:
            continue
        try:
            return raw_bytes.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    try:
        best = from_bytes(raw_bytes).best()
    except Exception:  # noqa: BLE001 — детектор не должен ронять скрапинг
        best = None
    if best is not None:
        return str(best)  # у CharsetMatch str() — уже декодированный текст
    return raw_bytes.decode("utf-8", errors="replace")


def to_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value)