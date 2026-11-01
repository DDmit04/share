"""Проверка очков выбора победителя (без сети и без xlsx).

Запуск из корня проекта:
    python pipeline/test_scoring.py
    python -m pipeline.test_scoring
"""

from pipeline.assemble import ZERO_PENALTY, _candidate_score, candidate_points


def record(similarity: float, internal: float = 0, external: float = 0, width: float = 0) -> dict:
    return {
        "bearing_similarity": similarity,
        "internal_d": internal,
        "external_d": external,
        "width": width,
    }


def main() -> int:
    full = record(0.90, 25, 52, 15)
    all_zeros = record(0.95, 0, 0, 0)
    one_zero = record(0.90, 25, 52, 0)

    checks = [
        (
            "полные размеры обгоняют большее сходство с нулями",
            candidate_points(full) > candidate_points(all_zeros),
        ),
        (
            "один ноль = ровно минус один штраф",
            abs(candidate_points(one_zero) - (0.90 - ZERO_PENALTY)) < 1e-9,
        ),
        (
            "три нуля = три штрафа",
            abs(candidate_points(all_zeros) - (0.95 - 3 * ZERO_PENALTY)) < 1e-9,
        ),
        (
            "NaN считается нулевой характеристикой",
            abs(candidate_points(record(0.90, float("nan"), 52, 15)) - (0.90 - ZERO_PENALTY)) < 1e-9,
        ),
        (
            "при равных очках выигрывает запись с большим числом размеров",
            _candidate_score(full) > _candidate_score(record(0.95, 0, 52, 15)),
        ),
    ]

    failed = 0
    for label, passed in checks:
        failed += 0 if passed else 1
        print(f"{'OK  ' if passed else 'FAIL'} {label}")
    print(f"\nПровалено: {failed} из {len(checks)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
