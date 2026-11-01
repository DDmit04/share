from typing import TypedDict, Any

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

