"""Быстрая проверка bearing_similarity без pytest.

Запуск из корня проекта:
    python compare/test_similarity.py
    python -m compare.test_similarity
"""

from compare.compare import bearing_similarity

CASES = [
    # (запрос, найденное имя, описание ожидания, проверка)
    ("Подшипник 6205", "Подшипник 6205", "identical", lambda s: s == 1.0),
    ("Подшипник 6205", "Подшипник 06205", "leading zero", lambda s: s >= 0.85),
    ("Подшипник 06205", "Подшипник 6205", "leading zero (reverse)", lambda s: s >= 0.85),
    ("Подшипник 06205-2RS", "Подшипник 6205-2RS", "leading zero + suffix", lambda s: s >= 0.85),
    ("Подшипник 6205", "Подшипник 6205-2RS", "suffix ignored (as intended)", lambda s: s >= 0.90),
    ("Подшипник 6205", "Подшипник 6306", "different number", lambda s: s <= 0.75),
]


def main() -> int:
    failed = 0
    for left, right, label, check in CASES:
        score = bearing_similarity(left, right)
        ok = check(score)
        failed += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} {score:.2f}  {label}: {left!r} vs {right!r}")
    print(f"\nПровалено: {failed} из {len(CASES)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
