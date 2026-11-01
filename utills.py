from typing import TypedDict, Any

from charset_normalizer import from_bytes

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

class ResBearingData(TypedDict):
    no: str
    description: str
    type: str
    internal_d: float
    external_d: float
    width: float
    source_name: str
    source_link: str

def to_float(num: str) -> float:
    num = num.replace(',', '.')
    try:
        return float(num)
    except ValueError:
        return 0.0


def decode_page(raw_bytes: bytes) -> str:
    """Декодирует тело страницы в строку, подбирая кодировку.

    Раньше здесь вызывался `chardet`, который не был ни импортирован, ни
    установлен, поэтому любой вызов падал с `NameError: name 'chardet' is not
    defined`. Теперь используется `charset-normalizer` — зависимость `requests`,
    уже указанная в requirements.
    """
    if not raw_bytes:
        return ""
    try:
        best = from_bytes(raw_bytes).best()
    except Exception:  # noqa: BLE001 — детектор не должен ронять скрапинг
        best = None
    if best is not None:
        return str(best)  # у CharsetMatch str() — уже декодированный текст
    for encoding in ("utf-8", "cp1251"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def to_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value)

