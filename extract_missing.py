"""Отделяет от 4_Цепь.xlsx записи, которых нет в Цепи_ДД_обновлённый.xlsx.

Сопоставление идёт по первой колонке «Номер материала».
Результат сохраняется в 4_Цепь_отсутствующие.xlsx — те же колонки,
только строки, чьих номеров нет в Цепи_ДД_обновлённый.xlsx.
"""

from pathlib import Path

import openpyxl

BASE_DIR = Path(__file__).resolve().parent
SOURCE = BASE_DIR / "4_Цепь.xlsx"
REFERENCE = BASE_DIR / "Цепи_ДД_обновлённый.xlsx"
OUTPUT = BASE_DIR / "4_Цепь_отсутствующие.xlsx"


def normalize_key(value):
    """Номер материала строкой: 3000852071 и '3000852071' считаются одним номером."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def main():
    ref_wb = openpyxl.load_workbook(REFERENCE, data_only=True)
    known = {
        normalize_key(row[0])
        for row in ref_wb.active.iter_rows(min_row=2, values_only=True)
    }
    ref_wb.close()
    known.discard("")

    wb = openpyxl.load_workbook(SOURCE)
    ws = wb.active

    missing = []
    removed = 0
    for row in range(ws.max_row, 1, -1):
        key = normalize_key(ws.cell(row, 1).value)
        if key in known:
            ws.delete_rows(row)
            removed += 1
        else:
            missing.append(key)

    wb.save(OUTPUT)
    wb.close()

    print(f"Строк в {SOURCE.name}: {removed + len(missing)}")
    print(f"Найдено в {REFERENCE.name}: {removed}")
    print(f"Осталось (нет в справочнике): {len(missing)}")
    print(f"Файл: {OUTPUT.name}")
    if missing:
        print("Номера: " + ", ".join(reversed(missing)))


if __name__ == "__main__":
    main()
