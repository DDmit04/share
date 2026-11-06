"""Сборка итоговых processed.xlsx / unprocessed.xlsx из чекпоинтов всех площадок.

Модуль не знает конкретной модели данных: всё, что от неё зависит, приходит
готовым маппером (`ScrapperMapper`) — какие поля считать характеристиками
(`DIMENSIONS`), какие колонки у входного и итоговых файлов (`COLUMNS`,
`COLUMN_TITLES`), по какому полю сопоставлять строки с входом (`KEY_FIELD`)
и как считать очки выбора победителя (`score`). У цепей это
`ChainScrapperMapper`; для другого товара достаточно передать в `assemble`
свой маппер.

Сначала запись должна пройти «годность»: у неё есть хотя бы одна ненулевая
характеристика из `mapper.DIMENSIONS` (у цепей — шаг, диаметры валика и ролика,
длина валика, высота пластины, расстояние между пластинами). Записи, у которых
все характеристики пустые или нулевые, отбрасываются ещё при чтении чекпоинтов
(`mapper.has_dimensions`): в `processed.xlsx` они не попадают никогда — даже со
сходством 1.0 — и не мешают выбрать нормальную запись того же номера с другой
площадки.

Правило выбора одной записи среди всех найденных для одной и той же цепи:

1. максимум итоговых очков `mapper.score`: сходство названий минус штраф
   `ZERO_PENALTY` за каждую незаполненную характеристику;
2. при равенстве очков — больше заполненных характеристик;
3. при равенстве и этого — больше сходство.

Сходство и очки считает сам скрапер и пишет их в запись: `name_similarity` —
в `scrap_list` в момент выбора кандидата, `score` — в `Scrapper.scrap` сразу
после того, как площадка отдала характеристики. Сборка их только читает;
пересчитывает лишь у записей старых чекпоинтов, где этих полей не было, — иначе
`--assemble-only` по ним получил бы сходство 0.

Набор колонок у входного и выходных файлов одинаковый: `processed.xlsx`
собирается по заголовкам входа (`mapper.to_row`), а `unprocessed.xlsx` — это
необработанные строки входа как есть.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scrapper.scrapper_mapper import ScrapperMapper
from utils.compare import SIMILARITY_THRESHOLD
from utils.excel import copy_style


def read_input(path: str | Path, mapper: ScrapperMapper) -> pd.DataFrame:
    """Читает входной xlsx и проверяет, что в нём есть колонка с номером записи.

    Без неё сопоставить чекпоинты с входным файлом нечем, поэтому лучше упасть
    здесь с понятным сообщением, чем позже с `KeyError` посреди сборки.
    """
    df = pd.read_excel(path)
    column = mapper.key_column
    if column not in df.columns:
        raise KeyError(
            f'во входном xlsx нет колонки «{column}»: по ней записи '
            'сопоставляются с чекпоинтами'
        )
    return df


def _candidate_score(mapper: ScrapperMapper, record: dict) -> tuple[float, int, float]:
    """Ключ сравнения: очки, затем полнота характеристик, затем сходство."""
    return (
        round(mapper.score(record), 4),
        len(mapper.DIMENSIONS) - mapper.missing_dimensions(record),
        float(record.get("name_similarity") or 0.0),
    )


def load_candidates(raw_dir: str | Path, mapper: ScrapperMapper) -> tuple[dict[str, dict], int]:
    """Читает все *.jsonl из raw_dir и оставляет лучшую запись на каждый ключ.

    Ключ записи — `mapper.key` (у цепей это `id`, «Номер материала»). Записи без
    единой заполненной характеристики отбрасываются до выбора победителя: иначе
    такая запись с высоким сходством могла бы «затенить» нормальную запись того
    же номера с другого сайта.

    Возвращает `(кандидаты, сколько записей отброшено без характеристик)`.
    """
    candidates: dict[str, dict] = {}
    skipped_no_dimensions = 0
    for path in sorted(Path(raw_dir).glob("*.jsonl")):
        site = path.stem
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                # недописанная строка после аварийного завершения — пропускаем,
                # площадка допишет её при следующем запуске
                continue
            record["site"] = record.get("site") or site
            # Ключ — поле `mapper.KEY_FIELD`. Строкой он только для
            # сопоставления: в самой записи остаётся исходным, чтобы в
            # processed.xlsx колонка сохранила свой тип. У записей старых
            # чекпоинтов есть ещё поле `no` с тем же значением — оно
            # игнорируется.
            key = mapper.key(record)
            if not key:
                continue
            if not mapper.has_dimensions(record):
                # все характеристики нулевые — запись ничего не даёт, отбрасываем
                skipped_no_dimensions += 1
                continue

            # Сходство и очки посчитал скрапер и положил в запись. Пересчитываем
            # только записи старых чекпоинтов, где этих полей ещё не было.
            similarity = record.get("name_similarity")
            if not similarity:
                source_name = record.get("source_name") or ""
                # `name_similarity` сам достаёт из записи `link` и `full_link`
                # и берёт большее сходство: отдельного поля с искомым
                # названием в чекпоинте нет, запись — это `dict(EntityData)`.
                similarity = mapper.name_similarity(source_name, record) if source_name else 0.0
            record["name_similarity"] = round(float(similarity), 4)
            record["score"] = round(float(record.get("score") or mapper.score(record)), 4)

            current = candidates.get(key)
            if current is None or _candidate_score(mapper, record) > _candidate_score(mapper, current):
                candidates[key] = record
    return candidates, skipped_no_dimensions


def assemble(
    input_path: str | Path,
    raw_dir: str | Path,
    out_dir: str | Path,
    mapper: ScrapperMapper,
) -> dict:
    """Собирает два итоговых файла и возвращает статистику.

    `mapper` задаёт модель данных: его `DIMENSIONS` решают, что считать
    характеристикой, `COLUMN_TITLES` — какие колонки писать и в каком порядке,
    `COLUMN_TITLES[KEY_FIELD]` — по какой колонке искать строку во входном xlsx,
    `score` — очки выбора победителя.
    """
    df = read_input(input_path, mapper)
    candidates, rejected_no_dimensions = load_candidates(raw_dir, mapper)

    accepted: dict[str, dict] = {}
    rejected_low_similarity = 0
    for key, record in candidates.items():
        # Записи без характеристик уже отфильтрованы в load_candidates; проверка
        # оставлена как страховка, чтобы такая запись не попала в processed
        # ни при каких изменениях ниже.
        if not mapper.has_dimensions(record):
            rejected_no_dimensions += 1
        elif record["name_similarity"] >= SIMILARITY_THRESHOLD:
            accepted[key] = record
        else:
            rejected_low_similarity += 1

    order = {}
    for index, value in enumerate(df[mapper.key_column].astype(str)):
        order.setdefault(value, index)

    # Набор колонок у входного и выходных файлов одинаковый: processed
    # собирается по тем же заголовкам и в том же порядке (`mapper.to_row`),
    # а unprocessed — это просто необработанные строки входа как есть.
    rows = [
        mapper.to_row(accepted[key])
        for key in sorted(accepted, key=lambda key: order.get(key, 10**9))
    ]
    processed = pd.DataFrame(rows, columns=list(df.columns))

    mask = ~df[mapper.key_column].astype(str).isin(set(accepted))
    unprocessed = df.loc[mask].copy()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    processed_path = out_dir / "processed.xlsx"
    unprocessed_path = out_dir / "unprocessed.xlsx"
    processed.to_excel(processed_path, index=False)
    unprocessed.to_excel(unprocessed_path, index=False)
    # pandas пишет только значения — оформление переносим со входного файла,
    # чтобы итоговые таблицы выглядели так же, как исходная.
    copy_style(input_path, processed_path)
    copy_style(input_path, unprocessed_path)

    return {
        "input_rows": int(len(df.index)),
        "candidates": len(candidates),
        "processed": int(len(processed.index)),
        "rejected_low_similarity": rejected_low_similarity,
        "rejected_no_dimensions": rejected_no_dimensions,
        "unprocessed": int(len(unprocessed.index)),
        "processed_path": str(processed_path),
        "unprocessed_path": str(unprocessed_path),
    }
