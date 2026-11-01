"""Сборка итоговых processed.xlsx / unprocessed.xlsx из чекпоинтов всех площадок.

Правило выбора одной записи среди всех найденных для одного и того же подшипника:

1. максимум итоговых очков: `bearing_similarity(source_name, description)`
   минус штраф `ZERO_PENALTY` за каждую нулевую/пустую характеристику (d/D/B);
2. при равенстве очков — больше заполненных размеров;
3. при равенстве и этого — заполненный тип, затем сходство.

Порог `SIMILARITY_THRESHOLD = 0.85` применяется к сходству, а не к очкам:
штраф за нули влияет только на выбор победителя и не отправляет найденную
запись в unprocessed.

`no` в чекпоинтах — всегда строка (как `No_` во входном xlsx).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from compare.compare import SIMILARITY_THRESHOLD, bearing_similarity

COLUMNS = [
    "no",
    "description",
    "type",
    "dirty_type",
    "series",
    "internal_d",
    "external_d",
    "width",
    "factory",
    "c",
    "source_name",
    "source_link",
    "bearing_similarity",
    "site",
    "score",
]

DIMENSIONS = ("internal_d", "external_d", "width")

#: Сколько очков снимается за каждую незаполненную (нулевую) характеристику.
ZERO_PENALTY = 0.05


def read_input(path: str | Path) -> pd.DataFrame:
    """Читает входной xlsx и проверяет обязательные колонки."""
    df = pd.read_excel(path)
    for column in ("No_", "Description"):
        if column not in df.columns:
            raise ValueError(f"Во входном файле {path} нет колонки {column!r}")
    if "Blocked" not in df.columns:
        df["Blocked"] = ""
    return df


def _is_zero(value) -> bool:
    """Пустая или нулевая характеристика: None, NaN или 0."""
    if value is None:
        return True
    try:
        number = float(value)
    except (TypeError, ValueError):
        return True
    return number == 0.0 or number != number  # NaN != NaN


def candidate_points(record: dict) -> float:
    """Итоговые очки: сходство минус штраф за каждую нулевую характеристику."""
    similarity = float(record.get("bearing_similarity") or 0.0)
    zeros = sum(1 for key in DIMENSIONS if _is_zero(record.get(key)))
    return similarity - ZERO_PENALTY * zeros


def _candidate_score(record: dict) -> tuple[float, int, int, float]:
    """Ключ сравнения: очки, затем полнота размеров, тип, сходство."""
    filled = sum(1 for key in DIMENSIONS if not _is_zero(record.get(key)))
    has_type = 1 if str(record.get("type") or "").strip() else 0
    return (
        round(candidate_points(record), 4),
        filled,
        has_type,
        float(record.get("bearing_similarity") or 0.0),
    )


def load_candidates(raw_dir: str | Path) -> dict[str, dict]:
    """Читает все *.jsonl из raw_dir и оставляет лучшую запись на каждый no."""
    candidates: dict[str, dict] = {}
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
            record["no"] = str(record.get("no", ""))
            if not record["no"]:
                continue

            source_name = record.get("source_name") or ""
            description = record.get("description") or ""
            similarity = bearing_similarity(source_name, description) if source_name else 0.0
            record["bearing_similarity"] = round(float(similarity), 4)
            record["score"] = round(candidate_points(record), 4)

            current = candidates.get(record["no"])
            if current is None or _candidate_score(record) > _candidate_score(current):
                candidates[record["no"]] = record
    return candidates


def assemble(
    input_path: str | Path,
    raw_dir: str | Path,
    out_dir: str | Path,
) -> dict:
    """Собирает два итоговых файла и возвращает статистику."""
    df = read_input(input_path)
    candidates = load_candidates(raw_dir)

    accepted: dict[str, dict] = {}
    rejected_low_similarity = 0
    for no, record in candidates.items():
        if record["bearing_similarity"] >= SIMILARITY_THRESHOLD:
            accepted[no] = record
        else:
            rejected_low_similarity += 1

    order = {}
    for index, value in enumerate(df["No_"].astype(str)):
        order.setdefault(value, index)

    rows = [accepted[no] for no in sorted(accepted, key=lambda key: order.get(key, 10**9))]
    processed = pd.DataFrame(rows, columns=COLUMNS)

    mask = ~df["No_"].astype(str).isin(set(accepted))
    unprocessed = df.loc[mask].copy()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    processed_path = out_dir / "processed.xlsx"
    unprocessed_path = out_dir / "unprocessed.xlsx"
    processed.to_excel(processed_path, index=False)
    unprocessed.to_excel(unprocessed_path, index=False)

    return {
        "input_rows": int(len(df.index)),
        "candidates": len(candidates),
        "processed": int(len(processed.index)),
        "rejected_low_similarity": rejected_low_similarity,
        "unprocessed": int(len(unprocessed.index)),
        "processed_path": str(processed_path),
        "unprocessed_path": str(unprocessed_path),
    }
