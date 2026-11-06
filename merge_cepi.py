"""Заменяет данные в Цепи_ДД.xlsx данными из processed.xlsx по совпадению «Номер материала».

- обновляются только строки, где «Номер материала» найден в processed.xlsx;
- значения копируются целиком (пустая ячейка в processed затирает старую);
- колонки «Тип цепи», «Стандарт/Профиль», «Примечание» остаются как были;
- колонки, которых нет в Цепи_ДД.xlsx («Имя», «Источник»), добавляются справа;
- результат сохраняется в новый файл Цепи_ДД_обновлённый.xlsx.
"""

from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).resolve().parent
PROCESSED = BASE_DIR / "processed.xlsx"
TARGET = BASE_DIR / "Цепи_ДД.xlsx"
OUTPUT = BASE_DIR / "Цепи_ДД_обновлённый.xlsx"

KEY_COLUMN = "Номер материала"
PROTECTED_COLUMNS = {"Тип цепи", "Стандарт/Профиль", "Примечание"}
NEW_COLUMN_WIDTHS = {"Имя": 25, "Источник": 50}


def normalize_key(value):
    """Приводит номер материала к строке: 3000910587 и '3000910587' — одно и то же."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def header_key(value):
    """Имя колонки без лишних пробелов."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def first_free_column(ws):
    """Первая колонка справа от последней непустой, в которой нет данных."""
    last = 0
    for col in range(1, ws.max_column + 1):
        if ws.cell(1, col).value not in (None, ""):
            last = col
    col = last + 1
    while any(ws.cell(row, col).value not in (None, "") for row in range(2, ws.max_row + 1)):
        col += 1
    return col


def main():
    processed_wb = openpyxl.load_workbook(PROCESSED, data_only=True)
    processed_rows = list(processed_wb.active.iter_rows(values_only=True))
    processed_wb.close()

    processed_header, processed_data = processed_rows[0], processed_rows[1:]
    p_index = {header_key(name): i for i, name in enumerate(processed_header) if header_key(name)}
    processed_map = {normalize_key(row[p_index[KEY_COLUMN]]): row for row in processed_data}
    processed_map.pop("", None)

    wb = openpyxl.load_workbook(TARGET)
    ws = wb.active
    t_index = {
        header_key(cell.value): i
        for i, cell in enumerate(ws[1])
        if header_key(cell.value)
    }

    copy_columns = [
        name for name in p_index
        if name != KEY_COLUMN and name not in PROTECTED_COLUMNS
    ]

    added = []
    for name in copy_columns:
        if name in t_index:
            continue
        col = first_free_column(ws)
        ws.cell(1, col).value = name
        ws.column_dimensions[get_column_letter(col)].width = NEW_COLUMN_WIDTHS.get(name, 25)
        t_index[name] = col - 1
        added.append(name)

    replaced = 0
    used = set()
    for row in range(2, ws.max_row + 1):
        key = normalize_key(ws.cell(row, t_index[KEY_COLUMN] + 1).value)
        source = processed_map.get(key)
        if not source:
            continue
        for name in copy_columns:
            ws.cell(row, t_index[name] + 1).value = source[p_index[name]]
        replaced += 1
        used.add(key)

    try:
        wb.save(OUTPUT)
    except PermissionError:
        wb.close()
        print(f"Не удалось записать {OUTPUT.name}: файл открыт в Excel. Закройте его и запустите скрипт снова.")
        return
    wb.close()

    missing = sorted(set(processed_map) - used)
    print(f"Обновлено строк: {replaced}")
    print(f"Колонок скопировано: {len(copy_columns)} из processed.xlsx")
    if added:
        print(f"Добавлены новые колонки: {', '.join(added)}")
    print(f"Файл: {OUTPUT.name}")
    if missing:
        print(f"Номеров из processed.xlsx, которых нет в Цепи_ДД.xlsx: {len(missing)}")
        print("  " + ", ".join(missing))


if __name__ == "__main__":
    main()
